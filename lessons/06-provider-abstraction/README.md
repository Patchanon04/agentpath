[อ่านภาษาไทย](README.th.md)

# Lesson 06. Provider abstraction

This is the last chapter of part one. It is also the first chapter where you
change the shape of code that already works, without adding a single new
feature the user can see.

By the end you will have one agent loop that can talk to two completely
different HTTP APIs, and you will have run the same prompt through both of
them and got the same answer. Nothing in the loop will know which one it used.

Files in this folder.

```text
lessons/06-provider-abstraction/
  tools.py       unchanged from lesson 03, the toy tools and their schemas
  providers.py   two classes that speak two dialects behind one method
  agent.py       the lesson 05 loop, now handed a provider instead of importing one
  check.py       runs the same prompt through both providers
  README.md      this file
```

## 1. The problem left over from lesson 05

Look at the top of `lessons/05-streaming/agent.py`.

```python
import tools
from llm import complete_stream


def run(user_input, max_turns=10):
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete_stream(
            messages, tools.SCHEMAS, on_text=lambda piece: print(piece, end="", flush=True)
        )
```

That `from llm import complete_stream` line is the whole problem in eight
words. The loop does not ask for a way to talk to a model. It reaches out and
grabs one specific way, by name, at import time. There is exactly one
`complete_stream` in the world as far as this file is concerned.

Now open `lessons/05-streaming/llm.py` and notice how much of it is not
general at all.

```python
    payload = {"model": model, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools

    with httpx.Client(timeout=120) as client:
        with client.stream(
            "POST", f"{base_url}/chat/completions", json=payload, headers=headers
        ) as response:
            ...
                delta = json.loads(data)["choices"][0].get("delta", {})
```

Four separate assumptions are baked into those lines, and every one of them is
false for some real provider you might want to use tomorrow.

- The path is `/chat/completions`.
- The reply is a JSON object with a `choices` list.
- The first element of that list has a `delta` object.
- Tool call fragments live inside `delta.tool_calls` with an `index` per call.

None of that is a standard. It is one company's request format, which several
other companies then copied because compatibility was cheaper than being
different. Ollama, OpenRouter, Groq, Together, vLLM, and many local servers
all speak it, which is exactly why part one of this course used it. You can
change one environment variable and hit any of them.

But not every provider copied it. Anthropic's own API, the one that serves
Claude, has a different request shape, a different response shape, and a
different streaming format. It is not worse and it is not better. It is
different, and the differences fall in exactly the places `llm.py` hard coded.

So here is the situation you are actually in at the end of lesson 05. You have
a working streaming agent that calls tools in a loop. If somebody asks you to
run it against Claude instead, you cannot change a base URL. You have to open
`llm.py` and rewrite the payload builder, the URL, and the stream parser. And
if you want to support both, you now need an `if` statement inside every one of
those places, which is the beginning of a mess that grows every time a fifth
provider appears.

The point of this lesson is to move that difference out of the loop and into a
place where it can be swapped, and to do it while the codebase is still small
enough that the surgery takes twenty minutes.

```text
lesson 05
  agent.py  ->  llm.complete_stream  ->  one HTTP dialect, welded in

lesson 06
  agent.py  ->  provider.stream      ->  OpenAICompatProvider  ->  dialect A
                                     ->  AnthropicProvider     ->  dialect B
```

## 2. The real differences between the two APIs

Before designing anything, look at what actually differs. This matters,
because the temptation when you hear the word abstraction is to invent a huge
general framework for differences you have not seen. The honest way round is
to look at two concrete APIs, list what really disagrees, and hide only that.

There are three differences in the shape of the request and the conversation,
plus one more in the streaming format. That is all. Everything else, the model
name, the messages list, the idea of a tool call with an id, is the same.

### Difference one, where the system prompt lives

A system prompt is the standing instruction you give a model before the
conversation starts, something like "You are a careful assistant that always
shows its working." Part one has not used one yet, and lesson 10 in part two is
entirely about writing them. What matters here is where it goes on the wire.

In the OpenAI compatible format it is a message like any other, with the role
`system`, sitting at the front of the `messages` list.

```json
{
  "model": "mock",
  "stream": true,
  "messages": [
    {"role": "system", "content": "You are a careful assistant."},
    {"role": "user", "content": "What is 2 plus 3?"}
  ]
}
```

In the Anthropic format there is no `system` role. The system prompt is a top
level field next to `messages`, and putting a message with the role `system`
into the list is an error.

```json
{
  "model": "mock",
  "max_tokens": 4096,
  "stream": true,
  "system": "You are a careful assistant.",
  "messages": [
    {"role": "user", "content": "What is 2 plus 3?"}
  ]
}
```

Notice the second small thing in that block. `max_tokens` is required by the
Anthropic API and optional in the OpenAI compatible one. That is why
`providers.py` hard codes `4096` in one class and never mentions the field in
the other.

### Difference two, the key that holds the argument schema

You already know the tool schema format from lesson 03. Both APIs use JSON
Schema for the arguments. They disagree about the key it hangs from, and about
how deeply the whole thing is nested.

OpenAI compatible, where the tool is wrapped in an object with a `type`
discriminator, and the schema sits under `function.parameters`.

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "add",
        "description": "Add two numbers together and return the sum.",
        "parameters": {
          "type": "object",
          "properties": {
            "a": {"type": "number", "description": "The first number"},
            "b": {"type": "number", "description": "The second number"}
          },
          "required": ["a", "b"]
        }
      }
    }
  ]
}
```

Anthropic, where the tool is flat and the schema sits under `input_schema`.

```json
{
  "tools": [
    {
      "name": "add",
      "description": "Add two numbers together and return the sum.",
      "input_schema": {
        "type": "object",
        "properties": {
          "a": {"type": "number", "description": "The first number"},
          "b": {"type": "number", "description": "The second number"}
        },
        "required": ["a", "b"]
      }
    }
  ]
}
```

Stare at the two schema objects themselves. They are byte for byte identical.
The difference is entirely in the envelope, which is a good sign that a small
translation layer is all you need rather than a rewrite of `tools.py`.

### Difference three, how a tool result travels back

This is the biggest of the three and the one that causes real bugs.

In lesson 04 you learned that a tool result goes back to the model as a new
message with the role `tool`, carrying the `tool_call_id` of the call it
answers. Here is a complete three message exchange in that format, exactly as
`agent.py` builds it in memory.

```json
[
  {"role": "user", "content": "What is 2 plus 3?"},
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_mock_1",
        "type": "function",
        "function": {"name": "add", "arguments": "{\"a\": 2, \"b\": 3}"}
      }
    ]
  },
  {"role": "tool", "tool_call_id": "call_mock_1", "content": "5"}
]
```

The Anthropic format has no `tool` role at all. There are only two roles,
`user` and `assistant`. A message's `content` can be a plain string or a list
of typed blocks, and both the request for a tool and the answer to it are
blocks. The request is a `tool_use` block inside an assistant message. The
answer is a `tool_result` block inside a **user** message, because from the
model's point of view the result is something the outside world told it.

```json
[
  {"role": "user", "content": "What is 2 plus 3?"},
  {
    "role": "assistant",
    "content": [
      {"type": "tool_use", "id": "call_mock_1", "name": "add", "input": {"a": 2, "b": 3}}
    ]
  },
  {
    "role": "user",
    "content": [
      {"type": "tool_result", "tool_use_id": "call_mock_1", "content": "5"}
    ]
  }
]
```

Three things changed at once, so read them one at a time.

The role of the result message changed from `tool` to `user`. The id field
changed name from `tool_call_id` to `tool_use_id`. And the arguments changed
from a JSON string under `function.arguments` to a real parsed object under
`input`. That last one is worth a second look, because lesson 03 spent a
whole section on the fact that `arguments` arrives as a string containing
JSON. In the Anthropic message format the assistant's own tool call is sent
back to the server as a parsed object, so the translation layer has to call
`json.loads` on the way out. You will see that line in section 6.

### Difference four, the streaming format

Lesson 05 taught you that a streamed reply arrives as a series of
`data: ` lines over a single long HTTP response, and that you have to glue
the pieces back together yourself. Both APIs do that. They disagree completely
about what is inside each line.

Every JSON block below is copied from this project's fake server at
`src/agentpath/testing/mock_server.py`, which produces both dialects so the
lesson checks can run offline. They are the real event shapes, not sketches.

The OpenAI compatible stream is a series of near identical objects. Each one
carries a `choices` list, and the interesting part is a `delta` that says what
to append. Text arrives like this.

```json
{"choices": [{"index": 0, "delta": {"content": "Hello "}}]}
{"choices": [{"index": 0, "delta": {"content": "from t"}}]}
{"choices": [{"index": 0, "delta": {"content": "he moc"}}]}
```

A tool call arrives as the same shape, with the delta carrying `tool_calls`
instead of `content`. The first fragment announces the id and the name, and
every fragment after it carries a slice of the argument string.

```json
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "call_mock_1", "type": "function", "function": {"name": "add", "arguments": ""}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"a\":"}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": " 2, \""}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "b\": 3"}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]}}]}
{"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
```

Everything is untyped in the sense that you find out what a chunk means by
probing for keys. Is there a `content`? Is there a `tool_calls`? That is why
the lesson 05 parser is a stack of `if` statements over `.get(...)` calls.

The Anthropic stream is the opposite design. Every line is a typed event with
a `type` field, and the events describe a small state machine over numbered
content blocks. A message starts, blocks open and close by index, and the
message ends.

Here is a text reply, complete.

```json
{"type": "message_start", "message": {"id": "mock-1", "role": "assistant", "content": []}}
{"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello "}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "from t"}}
{"type": "content_block_stop", "index": 0}
{"type": "message_delta", "delta": {"stop_reason": "end_turn"}}
{"type": "message_stop"}
```

And here is a tool call, complete. Note that the argument fragments have their
own delta type, `input_json_delta`, and the fragment field is called
`partial_json`.

```json
{"type": "message_start", "message": {"id": "mock-1", "role": "assistant", "content": []}}
{"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "call_mock_1", "name": "add", "input": {}}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{\"a\":"}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": " 2, \""}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "b\": 3"}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "}"}}
{"type": "content_block_stop", "index": 0}
{"type": "message_delta", "delta": {"stop_reason": "tool_use"}}
{"type": "message_stop"}
```

Two observations that will save you time later.

First, notice `"input": {}` in the `content_block_start` event. The server
sends an empty object there and then streams the real arguments as text
fragments. If you read the start event and trust its `input` field, you get an
empty dictionary and a tool call that does nothing, which is a maddening bug
to chase. The arguments only exist once you have concatenated every
`partial_json` piece.

Second, both dialects stream tool arguments as text fragments that are not
valid JSON until the last one lands. That is not a coincidence in the format.
It is a consequence of how the model generates. The characters come out one at
a time and the provider forwards them as they appear. Lesson 05 already taught
you to buffer and parse once at the end, and that lesson transfers to the new
dialect unchanged.

Here is the whole comparison in one table, so you have something to point at.

| Concern | OpenAI compatible | Anthropic |
| --- | --- | --- |
| Path | `/chat/completions` | `/messages` |
| Auth header | `Authorization` with a bearer value | `x-api-key` plus `anthropic-version` |
| System prompt | a message with role `system` | a top level `system` field |
| Max tokens | optional | required, as `max_tokens` |
| Tool schema key | `function.parameters` | `input_schema` |
| Model asks for a tool | `tool_calls` on an assistant message | a `tool_use` block |
| Tool arguments on the wire | a JSON string | a parsed object under `input` |
| You return a result | a message with role `tool` | a `tool_result` block in a user message |
| Streaming text | `choices[0].delta.content` | `content_block_delta` with `text_delta` |
| Streaming tool arguments | `choices[0].delta.tool_calls[].function.arguments` | `content_block_delta` with `input_json_delta` |

## 3. Thinking blocks, and the field you must not drop

Section 2 counted three differences in the shape of the conversation and one
more in the shape of the stream. That count is honest for the code in this
lesson, and the conversation gains a fourth entry the moment you ask a model to
think before it answers.

This one gets a section of its own because it does not behave like the others.
The three differences in section 2 announce themselves the first time you run
the code. A wrong key gives you a 400 straight away, you fix it, you move on.
This one is completely invisible while you do not use the feature. Then, on the
first day somebody turns it on, a request that looks identical to the ones that
have been working for months is rejected outright, and the cause is a field
that every instinct you have says is safe to throw away.

### What a thinking block is

Several current models can be asked to do their working before they answer. You
turn it on with a field in the request, called `thinking` in the Anthropic
dialect, carrying an effort level or a budget in tokens. The model then spends
part of its output producing the reasoning that leads up to the answer, rather
than the answer itself.

What matters here is not what is inside that reasoning. It is where it lands.
The working does not arrive folded into the assistant's text. It arrives as its
own kind of content block, a sibling of the text block and of the `tool_use`
block you met in section 2, inside the same assistant message.

Here is a realistic assistant message from a turn where the model thought and
then called a tool.

```json
{
  "role": "assistant",
  "content": [
    {
      "type": "thinking",
      "thinking": "The user is asking for 2 plus 3. I have an add tool and arithmetic is exactly what it is for, so I should call it rather than answer from memory.",
      "signature": "ErUBCkYIBBgCIkBub3RfYV9yZWFsX3NpZ25hdHVyZV9leGFtcGxlEgxzaWduYXR1cmUtdjEaDGV4YW1wbGUtb25seQ"
    },
    {
      "type": "tool_use",
      "id": "call_mock_1",
      "name": "add",
      "input": {"a": 2, "b": 3}
    }
  ]
}
```

Read the shape rather than the words. The block has a `type` of `thinking`, the
readable working under a key of the same name, and a third key, `signature`,
holding an opaque string the model did not write and you cannot interpret. It
sits in the same list as the `tool_use` block, at the same level, in the order
the model produced them.

The OpenAI compatible dialect has no equivalent block. Some servers that speak
it attach reasoning text to the delta under a field of their own invention, no
two of them agree on the name, and none of them carry anything like a
signature. That absence is itself the difference. One dialect gives reasoning a
first class place in the message with rules attached, and the other has not
standardised it at all.

### The rule

Every request to either API carries the whole conversation. The server keeps
nothing between turns, which is the same fact lesson 02 built the history list
on. So when the model produces a thinking block on one turn and you want a
second turn, that block has to travel back to the server inside the history you
send.

The rule is that it goes back exactly as it arrived.

Not summarised down to its first sentence because it was long. Not stripped out
because your internal history format has nowhere to put it. Not re-serialised
into a shape of your own with the keys renamed, the order changed, or the
whitespace normalised. The block you received is the block you send, field for
field, in the same position in the same message, in the same order relative to
the other thinking blocks of that turn.

That is stricter than most of an API, and it is worth knowing why it is that
strict rather than merely strict. A thinking block is not ordinary conversation
text that the model simply reads again. It is a record of a computation the
server performed, and the server needs to be able to tell that the record it is
handed back is the one it produced. Ordinary text it can read and take on
trust. This it verifies.

### The signature field

Which brings us to the field that causes the bug.

`signature` is that verification value. You cannot read it, you cannot generate
it, and nothing in your own code will ever have a reason to look inside it. It
is, in other words, exactly the kind of field a careful author decides is
provider noise and drops on the way into their own internal format. It is the
single most commonly dropped field in this whole area, and it is dropped by
people being tidy rather than by people being careless.

Here is what makes that expensive. If a thinking block goes back without its
signature, or with a signature that no longer matches the thinking beside it,
and there is a tool call in play on that same turn, the API does not ignore the
missing field and carry on. It rejects the whole request. You get a 400 on a
conversation that worked perfectly the turn before, pointing at a message you
did not think you had touched, from code that has been correct since the day
you wrote it.

That is why it is worth knowing before you meet it. Everything else in this
chapter you could rediscover in ten minutes from an error message and a schema.
This one presents as a request that used to work and now does not, over a field
you deliberately removed for good reasons, and the link between the cause and
the symptom is not something a stack trace will hand you.

### Redacted blocks

There is a second kind of the same thing. Sometimes the working is not returned
in readable form at all, and what arrives is a `redacted_thinking` block,
carrying a single opaque `data` field and no text you can read.

```json
{
  "role": "assistant",
  "content": [
    {
      "type": "redacted_thinking",
      "data": "EroBCkYIBBgCKkBub3RfYV9yZWFsX3JlZGFjdGVkX3BheWxvYWQSDHJlZGFjdGVkLXYxGgxleGFtcGxlLW9ubHk"
    },
    {
      "type": "tool_use",
      "id": "call_mock_1",
      "name": "add",
      "input": {"a": 2, "b": 3}
    }
  ]
}
```

The temptation is stronger here, because a block you cannot read looks even
more like something safe to discard. The rule does not change. It goes back
untouched, in place, exactly as it arrived. Your agent does not need to
understand a block in order to carry it, and carrying things it does not
understand is a large part of what a well behaved client does.

### The caching consequence, which costs money instead of erroring

The second half of this topic never produces an error at all, which is what
makes it worse.

Providers cache the front of your conversation. If the first several thousand
tokens of this request are byte for byte the same as the first several thousand
tokens of the last one, the server can reuse the work it already did on them
and charge you much less for that part. An agent loop is close to the perfect
case for it, because every turn resends the same system prompt, the same tool
schemas, and the same history with a little added on the end.

The catch is that the match has to be exact and it has to start at the
beginning. Change anything near the front of the request and everything after
the change is a miss.

Turning thinking on, turning it off, moving the effort level, or raising the
budget all change the shape of what gets sent. From that request onward the
prefix stops matching what was cached, and every later request in the session
pays full price for tokens that were nearly free the turn before. Nothing
fails. Nothing logs a warning. The only place it appears is the bill, and by
then nobody remembers which afternoon somebody nudged a budget from one number
to another.

So the practical rule is to choose the thinking setting when a session starts
and leave it alone for the life of that session. If you need a different
setting, that is a different session. Lesson 15 is where this gets measured
properly, with real numbers pulled out of the usage fields and the full list of
things that quietly break a cached prefix. For now, take the rule and the
reason for it.

### What our provider actually does, and does not

Now the honest part.

Look at the parse loop in `AnthropicProvider.stream` again. It handles exactly
two kinds of content block. A `content_block_start` whose type is `tool_use`
opens a slot, and a `content_block_delta` carrying `text_delta` or
`input_json_delta` feeds visible text or argument fragments. Everything else
falls through and is ignored, which section 6 will praise as the reason this
parser survives a provider adding new event types.

A thinking block is one of the things that falls through. It is not collected,
it is not returned, and `stream` has nowhere in its return value to put it,
because the agreement in section 4 promises text and calls and nothing else.
`_to_wire` then rebuilds each assistant turn out of a text string and a list of
tool calls, so even if a thinking block had survived the parser, there would be
no way for it to get back onto the wire.

That is a real limitation and this chapter is not going to pretend otherwise.
It is fine here for one specific reason. Nothing in this course ever turns
extended thinking on. `providers.py` never sends a `thinking` field, so no
model ever produces a thinking block, so no block is ever dropped. The code is
correct for the requests it actually makes.

It would be a bug on the first day somebody changed that. Add a `thinking`
field to the payload against a real model, let it call a tool, and the second
turn fails, for exactly the reason given above.

Naming that is better than papering over it. A half fix, where the parser
collects thinking blocks and the loop still has nowhere to keep them, would be
worse than nothing, because it would look handled. The real fix is not a patch
to `_to_wire` either. It needs the internal conversation format to have a place
to hold opaque provider blocks verbatim and hand them back untouched, which is
precisely the neutral internal format that exercise three at the end of this
chapter asks you to build. If you do that exercise, this is the requirement
that makes it worth doing properly.

### Why this belongs in this chapter

Because it is a fourth real difference between the two dialects, of exactly the
kind this chapter exists to isolate. One dialect has a content block with
strict handling rules and a verification field on it. The other has nothing
standard in that place at all. That difference has to live somewhere, and the
only sane somewhere is inside a provider class.

And because it teaches what the other three differences cannot. A missing
`input_schema` tells you what is wrong the first time you run the code. A
dropped signature tells you nothing until a feature you were not using gets
switched on months later. A changed thinking budget never tells you anything at
all. Those are the differences that decide whether an abstraction survives
contact with a real product, and the honest way to handle the ones you have not
implemented is to write them down where the next reader will find them.

## 4. What an interface is

You now have a list of differences and a loop that must not care about any of
them. The tool for that job is an interface.

An interface is an agreement about the shape of a call. It says what the
function is named, what arguments go in, and what comes back. It says nothing
about how the work gets done. Code written against the agreement can be
handed anything that honours the agreement, and it will work, because it only
ever depends on the parts that were promised.

You have used this idea for years without naming it. When you write
`open(path)` and then `handle.read()`, you do not know whether the bytes come
off a spinning disk, an SSD, a network share, or a RAM disk. `read` is an
agreement. Somebody honours it. Your code is written against the agreement and
survives every change underneath.

In Python the agreement is usually not written down as a separate declaration
at all. If an object has a method with the right name that accepts the right
arguments, it qualifies. That is all `agent.py` needs.

Here is our agreement, stated in one sentence. A provider is any object with a
method named `stream` that accepts a list of messages, an optional list of
tool schemas, and an optional `on_text` callback, and that returns a tuple of
the complete text and a list of tool calls.

Written as a signature.

```python
def stream(self, messages, tools=None, on_text=None):
    """Returns (text, calls).

    text  is the complete assistant text for this turn, "" if there was none
    calls is a list of dicts with the keys id, name, arguments, error
    """
```

The four keys in a call are worth pinning down, because they are the other
half of the agreement. `id` is the identifier the model gave the call, which
you must send back with the result. `name` is the tool name. `arguments` is a
real Python dictionary, already parsed. `error` is an empty string when all
went well, and a human readable reason when the argument fragments did not add
up to valid JSON. That last key came from lesson 05, where you learned that
feeding a parse error back to the model is far better than crashing.

Notice what the agreement does not mention. No URLs. No headers. No `choices`,
no `content_block_delta`, no `input_schema`. Those words appear only inside the
two classes in `providers.py`, and nowhere else in the lesson. That is the
test of a good interface. If a word from one provider's documentation shows up
in your agent loop, the abstraction has a hole in it.

### Why an agreement and not the alternatives

You could solve the same problem three other ways. It is worth seeing why they
are worse, because you will meet all three in real codebases.

**A flag inside one function.** Add a `provider="openai"` argument to
`complete_stream` and branch on it. This works for exactly two providers and
one afternoon. Then the function has four branches in the payload builder,
three in the URL, and two whole parse loops, all in one file, all sharing local
variables. Adding a third provider means editing code that the other two
depend on, so a mistake in the new one can break the old ones. That is the
specific failure a shared function with flags always produces.

**Translate everything into one format at the edges.** Keep a single HTTP
client and write functions that convert requests and responses. This is closer
to right, and in fact section 6 does exactly this conversion. The difference is
where the converters live. Loose functions have to be selected by a caller,
which puts a branch back into the caller. Attaching each converter to the class
that needs it means selection happens once, when the object is constructed.

**Inherit from a base class with shared code.** Write a `BaseProvider` with the
HTTP handling and let each provider override the parts that differ. This is
tempting and it is how a lot of code ends up unreadable. The two `stream`
methods here share almost nothing structurally. They differ in the payload,
the URL, the headers, and the entire parse loop. What is left to share is the
`with httpx.Client(...)` line. Hoisting one line into a parent class in
exchange for making the reader jump between two files is a bad trade. Both
classes in `providers.py` are written flat, top to bottom, and duplicate a
little on purpose so that each one can be read on its own.

That last decision is worth stating as a rule, because it goes against the
instinct most people are taught. Duplication is cheap. Wrong shared code is
expensive. Two hundred lines you can read straight through beat a hundred
lines you have to assemble in your head.

## 5. Why the interface is streaming first

The single method in the agreement is called `stream`, not `complete`. There
is no non streaming method at all. That is a deliberate choice and it is the
reason this lesson comes after lesson 05 rather than before it.

Imagine we had done it the other way round. Lesson 05 taught streaming, so
picture a version of this course where the abstraction came at lesson 05 and
streaming at lesson 06. The agreement would have been designed against what
existed at the time, which is the lesson 04 function.

```python
def complete(self, messages, tools=None):
    """Returns (text, calls) once the whole reply has arrived."""
```

That agreement is perfectly reasonable and it is a trap. Text arriving in
pieces is not a detail you can add underneath a promise like that, because the
promise has no place for a piece to go. There is one return value and it
happens once, at the end. To add streaming you would have to change the
agreement itself, and changing the agreement means changing every
implementation and every caller.

Count the edits in each order.

```text
abstraction first, streaming second
  change the agreement            1 edit
  rewrite OpenAICompatProvider    1 edit
  rewrite AnthropicProvider       1 edit
  update agent.py                 1 edit
  update check.py                 1 edit
                                  5 edits, two of them full parser rewrites

streaming first, abstraction second   (this course)
  rewrite llm.py as a stream      1 edit   (lesson 05, one parser)
  split it into two classes       1 edit   (lesson 06)
  update agent.py                 1 edit
                                  the second parser is written once, correctly
```

The general rule behind this is worth carrying with you. When you design an
interface, put the hardest capability you know you will need into the
agreement from the start, even if today only one implementation supports it.
Capabilities that change the shape of control flow are the ones that cannot be
retrofitted. Streaming is the classic example, because it turns one return
value into a sequence of events over time. Asynchrony is another. Cancellation
is a third.

There is a second reason streaming first is the right way round, and it is
about what fits inside what. A streaming call can pretend to be a batch call
trivially. You ignore the callback and read the return value, which is exactly
what `check.py` does when it does not care about live output. A batch call
cannot pretend to be a streaming one, because the information about when each
piece arrived has already been thrown away.

That is why the return value is still the complete text. The agreement gives
you both. The callback is for the caller who wants pieces as they land, and
the return value is for the caller who just wants the answer. Neither caller
pays for the other one's needs.

It also means a future provider without a streaming endpoint still fits the
agreement. Its `stream` method calls the plain endpoint, gets the whole reply,
calls `on_text` once with all of it, and returns. The output is less pleasant
to watch and the interface does not have to change. That is the sign that the
agreement was drawn at the right place.

## 6. Writing providers.py class by class

Open `providers.py`. It has one shared helper and two classes, in that order.

### The shared helper

```python
def parse_arguments(raw):
    """Return (arguments, error). See lesson 05 for why we do not hide this."""
    try:
        return json.loads(raw or "{}"), ""
    except json.JSONDecodeError as problem:
        return {}, f"arguments were not valid JSON ({problem})"
```

This is lifted straight out of lesson 05's parse loop and given a name, for
the plain reason that both classes need exactly the same behaviour at exactly
the same moment. Both accumulate argument text fragment by fragment, and both
must turn the accumulated string into a dictionary at the end.

The `or "{}"` handles a tool that takes no arguments, where a provider may send
an empty string that `json.loads` would reject. Returning the error as a value
rather than raising is the lesson 05 decision preserved. A model that produced
broken JSON can be told so and asked to try again, and `agent.py` does exactly
that. A model that produced broken JSON and crashed your process cannot.

This one function is the only code the two classes share. That is honest, and
it is why there is no base class.

### OpenAICompatProvider

```python
class OpenAICompatProvider:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]
```

The constructor is where all the configuration now lives. In lesson 05 those
three environment variables were read inside `complete_stream`, which meant
they were read again on every single request and could not be overridden
without changing the process environment. Now they are read once, and any of
the three can be passed in directly. That is what lets `check.py` build two
providers with different settings in the same process, and it is what will let
part three run a cheap model for a summarising subtask alongside a strong one
for the main loop.

Read the `api_key` line carefully, because the pattern differs from the other
two. It is `api_key if api_key is not None else ...` rather than
`api_key or ...`. The difference shows up when you pass an empty string. With
`or`, an empty string is falsy and would silently fall back to the environment
variable. With the explicit `is not None` check, passing an empty string means
you deliberately want no key, which is the normal case for a local Ollama
server. Small distinction, real bug avoided.

`rstrip("/")` on the base URL means a trailing slash in the environment
variable does not produce a double slash in the request path. This is the kind
of thing that produces a confusing 404 and half an hour of staring.

```python
    def stream(self, messages, tools=None, on_text=None):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
```

The `Authorization` header is only added when there is a key, so a local
server that rejects unexpected auth headers stays happy.

The `tools` line is the schema translation for this dialect, and it is one
line because we chose the interface's tool format to be the inner function
object, the part with `name`, `description` and `parameters`. This provider
wraps each one in the `{"type": "function", ...}` envelope from section 2.
`agent.py` unwraps `tools.SCHEMAS` down to that inner object before calling,
which you will see in section 7.

```python
        text_parts = []
        partial = {}
        with httpx.Client(timeout=120) as client:
            with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        break
                    delta = json.loads(data)["choices"][0].get("delta", {})
                    if delta.get("content"):
                        text_parts.append(delta["content"])
                        if on_text:
                            on_text(delta["content"])
                    for chunk in delta.get("tool_calls", []):
                        slot = partial.setdefault(
                            chunk.get("index", 0), {"id": "", "name": "", "arguments": ""}
                        )
                        if chunk.get("id"):
                            slot["id"] = chunk["id"]
                        function = chunk.get("function", {})
                        if function.get("name"):
                            slot["name"] = function["name"]
                        if function.get("arguments"):
                            slot["arguments"] += function["arguments"]
```

This body is lesson 05's parser, moved into a method and otherwise untouched.
That is intentional, and you should check it against `lessons/05-streaming/llm.py`
line by line to convince yourself. Refactoring is much easier to trust when
one part of the change is provably zero.

The one idea worth re-reading is `partial`. It is a dictionary keyed by the
call index that the provider supplies, because a model can ask for several
tools in one turn and their fragments are interleaved in the stream. The index
is how you know which half finished argument string a fragment belongs to.

```python
        calls = []
        for _, s in sorted(partial.items()):
            arguments, error = parse_arguments(s["arguments"])
            calls.append({"id": s["id"], "name": s["name"], "arguments": arguments, "error": error})
        return "".join(text_parts), calls
```

`sorted` puts the calls back in index order, because dictionary insertion
order follows whichever call's first fragment arrived first, which is not
guaranteed to be call zero. Then every accumulated string is parsed once, and
the result is the shape the agreement promised.

### AnthropicProvider, the constructor and the payload

The constructor is identical to the other one, deliberately, so the two
classes are interchangeable at the point of construction.

```python
    def stream(self, messages, tools=None, on_text=None):
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
```

Two header differences from section 2 appear here. The key goes in `x-api-key`
rather than an `Authorization` bearer value, and there is a required
`anthropic-version` header. That version string is a date, and it pins the
request to a particular version of the API's behaviour so that changes on the
server do not silently change what your code receives. It is a good design and
more APIs should copy it.

Note also that unlike the other class, this one sends the header
unconditionally even when the key is empty. That is fine, because there is no
realistic local server speaking this dialect that would object.

```python
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "stream": True,
            "messages": self._to_wire(messages),
        }
        if system:
            payload["system"] = system
```

Here is difference one being handled. Every message with the role `system` is
pulled out of the list, the texts are joined with newlines so that more than
one still works, and the result becomes a top level field. The field is only
added when there is something to put in it, because sending
`"system": ""` is noise at best.

The matching half of this is inside `_to_wire`, which drops those messages
from the list so they do not travel twice.

```python
        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]
```

And there is difference two, in four lines. The same schema object that the
other provider passed through as `parameters` is passed through here as
`input_schema`. `tools.py` never changes, and neither does `agent.py`. Only
this list comprehension knows the word `input_schema` exists.

### The _to_wire method

This is the most interesting code in the lesson, so it gets its own reading.
Its job is to take the conversation in the format `agent.py` keeps in memory,
which is the OpenAI shaped one, and produce the Anthropic wire format.

```python
    def _to_wire(self, messages):
        wire = []
        for message in messages:
            if message["role"] == "system":
                continue
```

System messages were already extracted into the top level field, so they are
dropped here. If you forget this line, the request fails with a complaint
about an unknown role, and the error message will not obviously point at this
function.

```python
            if message["role"] == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": message["tool_call_id"],
                    "content": message["content"],
                }
                if wire and wire[-1]["role"] == "user" and isinstance(wire[-1]["content"], list):
                    wire[-1]["content"].append(block)
                else:
                    wire.append({"role": "user", "content": [block]})
                continue
```

This is difference three, and the `if` in the middle is the part that deserves
real attention.

Start with what is easy. A message with the role `tool` becomes a
`tool_result` block, `tool_call_id` becomes `tool_use_id`, and the result text
stays as it is. The block has to be carried by a message with the role `user`,
because that role is the only one the Anthropic format has for input coming
from outside the model.

Now the hard part. Why does a second consecutive tool result get appended into
the existing user message rather than added as a new one?

The reason is that the Anthropic API requires the roles in `messages` to
alternate. A user message, then an assistant message, then a user message, and
so on. Two user messages in a row are rejected by the server.

Look at what `agent.py` produces when a model asks for two tools in one turn.
The loop appends one assistant message with both calls, and then one message
with the role `tool` per call, because that is what the OpenAI compatible
format demands.

```python
[
  {"role": "user",      "content": "Roll two dice."},
  {"role": "assistant", "content": "", "tool_calls": [call_1, call_2]},
  {"role": "tool", "tool_call_id": "call_1", "content": "4"},
  {"role": "tool", "tool_call_id": "call_2", "content": "6"},
]
```

Translate each of those `tool` messages into its own user message and you get
this, which the server refuses.

```json
[
  {"role": "user", "content": "Roll two dice."},
  {"role": "assistant", "content": [ ... two tool_use blocks ... ]},
  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": "4"}]},
  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_2", "content": "6"}]}
]
```

Merge them, which is what the code does, and you get the correct shape. One
assistant turn asking for two tools, one user turn answering both.

```json
[
  {"role": "user", "content": "Roll two dice."},
  {"role": "assistant", "content": [ ... two tool_use blocks ... ]},
  {
    "role": "user",
    "content": [
      {"type": "tool_result", "tool_use_id": "call_1", "content": "4"},
      {"type": "tool_result", "tool_use_id": "call_2", "content": "6"}
    ]
  }
]
```

This is not an arbitrary rule you have to memorise. It follows from the two
formats disagreeing about what a message is. In the OpenAI shape a message is
one thing that happened, so two results are two messages. In the Anthropic
shape a message is one turn in the conversation, and a turn can contain
several things. Translating between them therefore has to change the number
of messages, and merging is where that happens.

The condition guarding the merge has three parts and every one of them
matters.

`wire` must be non empty, otherwise `wire[-1]` raises `IndexError` on the very
first message. A tool result cannot legitimately be first, but a translation
function that crashes on malformed input is harder to debug than one that
produces a request the server rejects with a clear message.

`wire[-1]["role"] == "user"` stops a result being appended onto an assistant
turn.

`isinstance(wire[-1]["content"], list)` is the subtle one. The first user
message in any conversation is a plain string, since it is the human's typed
question. Appending a block to a string would raise `AttributeError`, and even
if Python allowed it the result would be meaningless. This check distinguishes
"the previous user message is a block list I built, so extend it" from "the
previous user message is ordinary text, so start a new one."

```python
            if message["role"] == "assistant" and message.get("tool_calls"):
                blocks = []
                if message.get("content"):
                    blocks.append({"type": "text", "text": message["content"]})
                for call in message["tool_calls"]:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call["id"],
                            "name": call["function"]["name"],
                            "input": json.loads(call["function"]["arguments"] or "{}"),
                        }
                    )
                wire.append({"role": "assistant", "content": blocks})
                continue
```

This is the other half of difference three, the assistant's own request for a
tool. The text block is added first and only when there is text, because some
models say a sentence before calling a tool and others say nothing. Sending
`{"type": "text", "text": ""}` is rejected by the API, so the `if` is load
bearing rather than tidiness.

Then `json.loads(call["function"]["arguments"] or "{}")`. Remember from
section 2 that the OpenAI format carries arguments as a JSON string and the
Anthropic format carries them as a parsed object. `agent.py` stored them as a
string with `json.dumps`, and here they are parsed back.

That round trip is real waste, and it is worth naming rather than hiding. It
exists because this course chose to keep the agent's internal conversation in
the OpenAI shape, since that is the shape you have been reading since lesson
02 and changing it now would obscure the actual lesson. A production harness
would define its own neutral internal format that is neither provider's, and
translate both ways at the edges. If you want to know what that looks like,
the exercise at the end of this chapter is to try it.

```python
            wire.append({"role": message["role"], "content": message["content"]})
        return wire
```

The fall through case. A plain user message or a plain assistant text message
passes across unchanged, because the two formats agree on that shape.

### AnthropicProvider, the stream parser

```python
        text_parts = []
        blocks = {}
        with httpx.Client(timeout=120) as client:
            with client.stream(
                "POST", f"{self.base_url}/messages", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
```

The transport handling is identical. Long lived HTTP response, lines prefixed
with `data: `, everything else skipped. Only the path changed, from
`/chat/completions` to `/messages`.

```python
                    if event.get("type") == "content_block_start":
                        block = event["content_block"]
                        if block.get("type") == "tool_use":
                            blocks[event["index"]] = {
                                "id": block["id"],
                                "name": block["name"],
                                "json": "",
                            }
```

A `content_block_start` for a tool opens a slot. The id and name are known
immediately, and the `json` field starts empty and will be filled by the
fragments. Text blocks are not stored at all, because their content goes
straight into `text_parts`, so `blocks` holds only tool calls and can be
turned into the `calls` list without filtering.

The `event["index"]` here plays the same role as `chunk["index"]` in the other
provider. Two dialects, same problem, same solution.

```python
                    elif event.get("type") == "content_block_delta":
                        delta = event["delta"]
                        if delta.get("type") == "text_delta":
                            text_parts.append(delta["text"])
                            if on_text:
                                on_text(delta["text"])
                        elif delta.get("type") == "input_json_delta":
                            blocks[event["index"]]["json"] += delta["partial_json"]
```

Both kinds of fragment arrive as `content_block_delta`, and the inner `type`
says which. `text_delta` is the visible answer and goes to the callback the
moment it arrives, which is what makes output appear live. `input_json_delta`
is a slice of the argument string and is appended to the slot opened earlier.

Every event type the code does not handle is simply ignored. `message_start`,
`content_block_stop`, `message_delta` and `message_stop` all pass through
without a branch. That is on purpose. We already know the reply is finished
when the response body ends, so consuming the end markers would add code that
proves nothing. Ignoring unknown events is also how this parser survives the
provider adding new event types later.

```python
        calls = []
        for _, s in sorted(blocks.items()):
            arguments, error = parse_arguments(s["json"])
            calls.append({"id": s["id"], "name": s["name"], "arguments": arguments, "error": error})
        return "".join(text_parts), calls
```

The ending is character for character the same idea as the other class. Sort by
index, parse each accumulated string once, build the four key dictionaries the
agreement promised. Two very different streams, one shape at the door.

## 7. Changing the agent loop

Open `agent.py` and compare it with lesson 05's. Two things changed, and one
of them is an import that vanished.

```python
"""The same loop again, now taking whichever provider it is handed."""
import json

import tools


def run(provider, user_input, max_turns=10):
    messages = [{"role": "user", "content": user_input}]
    schemas = [t["function"] for t in tools.SCHEMAS]

    for _ in range(max_turns):
        text, calls = provider.stream(
            messages, schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )
```

**Change one.** `from llm import complete_stream` is gone, and `provider` is
now the first parameter of `run`. The loop no longer chooses who answers. It
is told, by whoever called it.

That is the entire technique, and it has a name that sounds far grander than
the idea. It is called dependency injection, and if you have avoided the term
because it sounded like something requiring a framework and a configuration
file, here is the whole of it in one sentence. Instead of a function reaching
out and creating or importing the thing it needs, the thing it needs is passed
in as an argument.

That is it. `run(provider, ...)` is dependency injection. You have almost
certainly written it a hundred times without calling it that. Every function
that takes a file handle instead of opening a path is doing the same thing.

**Change two.** `schemas = [t["function"] for t in tools.SCHEMAS]`. Lesson 05
passed `tools.SCHEMAS` straight through, envelope and all, because the only
provider that existed wanted that envelope. Now the envelope is one dialect's
opinion, so the loop unwraps it down to the neutral inner object with `name`,
`description` and `parameters`, and each provider adds its own wrapping. The
OpenAI class puts the `{"type": "function", ...}` envelope back on. The
Anthropic class renames `parameters` to `input_schema`.

Everything else in the file is untouched. The bookkeeping after a tool call is
identical to lesson 05.

```python
        for call in calls:
            if call["error"]:
                result = f"Error: {call['error']}. Send the tool call again."
                print(f"\n[{call['name']} was not run because {call['error']}]")
            else:
                print(f"\n[calling {call['name']} with {call['arguments']}]")
                result = tools.run(call["name"], call["arguments"])
                print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
```

The loop still writes `{"role": "tool", "tool_call_id": ...}` even when the
provider is the Anthropic one, which has no such role. That is not an
oversight. The loop keeps the conversation in one internal shape and the
provider translates on the way out, which is `_to_wire` doing its job. If the
loop had to know which shape to record, the abstraction would have failed at
the last step, which is a common way for this kind of refactor to go wrong.

One more difference is easy to miss. Lesson 05's `agent.py` ended with this.

```python
if __name__ == "__main__":
    run("What is 2 plus 3?")
```

Lesson 06's does not, and cannot, because `run` can no longer produce a
provider out of thin air. Somebody outside has to decide. That is not a loss.
It is the point of the change made visible. The decision about which service
to call has moved out of the loop and up to the caller, where it belongs.

### What this buys you

The payoff is not the ability to use Claude. That is a nice side effect. The
payoff is that the loop now has a seam.

**It can be tested without a network.** A test can hand `run` a small object
with a `stream` method that returns canned answers from a list, and check that
the loop appends messages correctly, that it stops when there are no calls,
that it feeds a parse error back, and that `max_turns` raises. All in
microseconds, with no HTTP, no server, and no fake process to start. The
project's fake server is excellent and still slower and heavier than a five
line stub object.

```python
class ScriptedProvider:
    def __init__(self, turns):
        self.turns = list(turns)
        self.seen = []

    def stream(self, messages, tools=None, on_text=None):
        self.seen.append(list(messages))
        return self.turns.pop(0)
```

Hand that to `run` and you can assert on the exact conversation the loop built.
That object is a valid provider by the only standard that matters, which is
that it honours the agreement.

**It can be reused unchanged.** A future lesson that runs a cheap model to
summarise a long conversation calls the same `run` with a different provider.
A test that needs deterministic output calls it with a scripted one. A
benchmark that runs the same prompt against four services calls it four times
in a loop. None of those requires editing `agent.py`.

**Providers can be developed independently.** A new provider is a new class in
`providers.py`. Nothing already working is touched, so nothing already working
can break. Compare that to adding a fourth branch to a shared function.

## 8. Running check.py

`check.py` is the smallest program that could demonstrate the claim of this
lesson.

```python
"""Check that lesson 06 works.

The point of this lesson is that one agent loop serves two different APIs.
So this check runs the same prompt through both providers and expects the
same outcome.
"""
import os
import sys

from agent import run
from providers import AnthropicProvider, OpenAICompatProvider

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    base_url = os.environ["AGENTPATH_BASE_URL"]
    model = os.environ["AGENTPATH_MODEL"]
    api_key = os.environ.get("AGENTPATH_API_KEY", "")

    for name, provider in [
        ("openai", OpenAICompatProvider(base_url, api_key, model)),
        ("anthropic", AnthropicProvider(base_url, api_key, model)),
    ]:
        answer = run(provider, PROMPT)
        if "5" not in answer:
            print(f"FAIL the {name} provider did not complete the tool round trip. Got {answer!r}")
            sys.exit(1)
        print(f"OK the same loop worked with the {name} provider")
```

Read the loop at the bottom. One `PROMPT`, one `run`, two providers built from
the same three environment variables. The assertion is the same for both,
because the whole claim is that the outcome does not depend on the dialect.
Note also that `check.py` passes no `on_text` of its own. It does not have to.
`agent.py` supplies the printing callback, and `check.py` only cares about the
returned string.

Run it from inside the lesson folder, or run every lesson at once from the
repository root.

```bash
cd lessons/06-provider-abstraction
python check.py
```

```bash
python ci/run_lessons.py
```

A passing run looks like this.

```text

[calling add with {'a': 2, 'b': 3}]
[add returned 5]
The tool returned 5.
OK the same loop worked with the openai provider

[calling add with {'a': 2, 'b': 3}]
[add returned 5]
The tool returned 5.
OK the same loop worked with the anthropic provider
```

The two halves are identical apart from the last word, which is the result you
wanted. The blank line at the top of each half comes from the `\n` at the
front of the `[calling ...]` message, which normally separates the streamed
answer from the tool trace. On a turn where the model went straight to a tool
call there was no text before it, so the newline lands on an empty line.

### Why this passes without a network

The reason both halves work is that this project's fake server, at
`src/agentpath/testing/mock_server.py`, speaks both dialects. Its request
handler branches on the path.

```python
    def do_POST(self):
        payload = self._read_json()
        text, tool_calls = decide(payload.get("messages", []))
        streaming = bool(payload.get("stream"))
        path = self.path.rstrip("/")
        if path.endswith("/chat/completions"):
            if streaming:
                self._send_sse(openai_stream_events(text, tool_calls))
            else:
                self._send_json(openai_body(text, tool_calls))
            return
        if path.endswith("/messages"):
            if streaming:
                self._send_sse(anthropic_stream_events(text, tool_calls))
            else:
                self._send_json(anthropic_body(text, tool_calls))
            return
```

One `decide` function works out what to answer, and then two different
formatters render that same answer in two different dialects. That is the
mirror image of what you just built in `providers.py`, which is a pleasing
symmetry and also the reason the check is a genuine test rather than a
tautology. If your translation is wrong in either direction, one half fails
and the other passes, and the difference tells you where to look.

`decide` also handles both shapes of tool result, which is worth seeing,
because it proves the merge logic from section 6 arrived correctly.

```python
    if role == "tool":
        return f"The tool returned {content}.", []

    if isinstance(content, list):
        for block in content:
            if block.get("type") == "tool_result":
                return f"The tool returned {block.get('content', '')}.", []
```

The first branch catches the OpenAI shaped result message. The second catches
the Anthropic shaped user message with a `tool_result` block in it. Both
produce the same sentence, which is why both halves of the check print
`The tool returned 5.` and both contain a `5`.

### Running it against a real service

Everything above runs offline. To point at something real, set the three
environment variables and run the same file.

For an OpenAI compatible service, including a local Ollama, the base URL is
the one ending in `/v1` and the key goes in as a bearer token.

```bash
cd lessons/06-provider-abstraction
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen2.5:14b
export AGENTPATH_API_KEY=
python check.py
```

```powershell
cd lessons\06-provider-abstraction
$env:AGENTPATH_BASE_URL = "http://localhost:11434/v1"
$env:AGENTPATH_MODEL = "qwen2.5:14b"
$env:AGENTPATH_API_KEY = ""
python check.py
```

For Anthropic's own API the base URL and the model name are different, and a
real key is required.

```bash
cd lessons/06-provider-abstraction
export AGENTPATH_BASE_URL=https://api.anthropic.com/v1
export AGENTPATH_MODEL=claude-sonnet-4-5
export AGENTPATH_API_KEY=your-key-here
python check.py
```

```powershell
cd lessons\06-provider-abstraction
$env:AGENTPATH_BASE_URL = "https://api.anthropic.com/v1"
$env:AGENTPATH_MODEL = "claude-sonnet-4-5"
$env:AGENTPATH_API_KEY = "your-key-here"
python check.py
```

Never commit that key. Keep it in your shell profile or in a local file listed
in `.gitignore`.

### The warning, read this before you file a bug

When you point at one real service, only the matching provider will work. The
other one will fail, and that is correct behaviour, not a defect in your code.

The reason is plain once you say it out loud. There is one `AGENTPATH_BASE_URL`
and it names one company's endpoint. A real endpoint speaks one dialect. The
fake server is unusual precisely because it speaks two, which is a luxury only
a test double can afford.

So expect this shape of outcome against a real OpenAI compatible endpoint.

```text
OK the same loop worked with the openai provider
Traceback (most recent call last):
  ...
httpx.HTTPStatusError: Client error '404 Not Found' for url '.../v1/messages'
```

And this shape against real Anthropic.

```text
Traceback (most recent call last):
  ...
httpx.HTTPStatusError: Client error '404 Not Found' for url '.../v1/chat/completions'
```

The first provider passes, the second gets a 404 or a 401 from
`raise_for_status`, and the script stops. A 404 means the path does not exist
on that host, which is exactly the point. A 401 means the auth header was the
wrong kind, which is the same point wearing a different number.

To test one provider against one real service, comment out the other line in
the list in `check.py`.

```python
    for name, provider in [
        ("openai", OpenAICompatProvider(base_url, api_key, model)),
        # ("anthropic", AnthropicProvider(base_url, api_key, model)),
    ]:
```

If you want both to run against real services at the same time, that needs a
second set of environment variables and a second base URL, which is a genuinely
useful exercise. The constructors already accept everything explicitly, so it
is a change in `check.py` alone. Nothing in `providers.py` or `agent.py` needs
to move, which is one more piece of evidence that the seam was cut in the
right place.

Two other failures are worth naming in advance.

If a real model answers `5` in words without calling the tool, you get the
`FAIL` line about the round trip, and section 9 of lesson 03 is the right place
to go. Small local models often do this and it is a model capability problem,
not a plumbing problem.

If you see `KeyError: 'AGENTPATH_BASE_URL'`, the variable is not set in this
shell. Setting it in one terminal does not set it in another.

## 9. The end of part one

Stop and look at what you have.

Six lessons ago you had nothing. Now you have a program that does all of the
following, in about three hundred lines of Python you can read from top to
bottom, with no framework anywhere in it.

- It sends a conversation to a language model over HTTP and reads the reply.
- It keeps history, so the model appears to remember, and you know exactly why
  that appearance exists and what it costs.
- It describes your Python functions in JSON Schema and sends them along.
- It reads back a structured request for one of those functions, and runs the
  function itself, in code you wrote and can inspect.
- It sends the result back into the conversation and loops, so the model can
  use what it learned, chain one tool into the next, and recover from an error
  it caused.
- It stops when the model answers in words, and it refuses to loop forever.
- It streams, so text appears as it is produced, and it reassembles tool
  arguments from fragments of JSON that are invalid until the last piece lands.
- It talks to two entirely different provider APIs through one interface, and
  the loop cannot tell them apart.

That last line is what makes the rest durable. The provider landscape will keep
changing. Companies will appear, formats will drift, a service you depend on
will raise its prices or go down on the morning of your demo. Your agent loop
does not care, because the only thing it knows how to do is call `stream` and
read a tuple.

More importantly, you now know what an agent actually is. It is a loop, a list
of messages, a dictionary of functions, and an `if` statement. There is no
hidden machinery. When you next read a framework's documentation, you will be
able to point at each of its concepts and say which of these five things it is
wrapping. That is a permanent advantage over people who learned the framework
first.

### What part two adds

Everything so far has been safe by accident. The tools are a calculator and a
dice roll. The worst thing a bug could do is return the wrong number.

Part two gives the agent hands. You will build tools that read, write, list
and edit real files on your disk, including an edit that replaces a piece of
text rather than rewriting a whole file, because making a model retype an
entire file to change one line is slow, expensive and error prone, and every
serious harness avoids it. You will build a tool that runs real shell
commands with a timeout and captures the output. You will build search tools,
a file name matcher and a content grep, so the agent can find things in a
codebase instead of being told where to look. Then a chapter on what belongs in
a system prompt, what belongs in a user message, and what belongs in a tool
description, which is the chapter that turns a working agent into a useful
one. Part two ends with all of it assembled into a small coding agent that can
actually change code in a folder.

And this is where the safety questions start, because they have to.

Lesson 03 made a promise about this and it is time to collect on it. The gap
between the model asking and the code running is entirely yours, and up to now
you have had no reason to use it. From the moment a tool can delete a file or
run a command, that gap is the only thing standing between a confident wrong
guess and a bad afternoon. So the shell tool in part two ships with a
confirmation prompt on the first day it exists, not as a later improvement.
You will also meet the escape hatch that makes automated checks possible,
`AGENTPATH_AUTO_APPROVE`, and you will see that a switch which turns off the
question is itself a design decision worth thinking about carefully. That
switch grows into the full permission system in part three.

You will also meet a threat that surprises people. Once an agent reads files
and command output, text written by somebody else flows into the conversation
and the model treats it as input. A file in a repository can contain a
sentence addressed to the agent. That is prompt injection, and it arrives
through the tool results, not through the user. Part two introduces it and
part three deals with it properly.

None of that requires changing what you built here. The loop stays. The
provider interface stays. Only the tools get real.

### Exercises before you move on

Three, in increasing order of difficulty. All of them are optional and all of
them teach something the reading alone cannot.

**One.** Write the `ScriptedProvider` from section 7 and use it to test `run`
with no network at all. Make it return a tool call on the first turn and text
on the second, and assert on the exact list of messages the loop built. Then
make it return a call whose arguments failed to parse, and check that the loop
sends the error back rather than crashing.

**Two.** Add a third provider class for a service you actually use, or invent
a dialect and add a branch for it to the fake server. Time yourself. If it
takes more than half an hour, the interface has a hole in it, and finding the
hole is the real exercise.

**Three.** Replace the internal conversation format. Right now `agent.py`
keeps history in the OpenAI shape, which makes `OpenAICompatProvider` almost
free and makes `_to_wire` do all the work, including that `json.dumps` and
`json.loads` round trip on tool arguments. Define a neutral format of your own,
something with a role, some text, and a list of tool calls with real
dictionaries for arguments, and give both providers a `_to_wire` method. The
code gets slightly longer and considerably more symmetrical, and you will
understand why real harnesses do it that way.

On to part two.
