[อ่านภาษาไทย](README.th.md)

# Lesson 14. Context management

This chapter contains the single most important trap in the course.

Not the hardest idea. The trap. There is a bug in this chapter that almost
everybody who writes an agent harness writes at least once, that produces a
`400` from the provider, that appears on a request other than the one that
caused it, and that therefore looks like it came from nowhere. People lose
whole afternoons to it. The fix is eight lines. The whole of this chapter is
about earning those eight lines.

The subject is what to do when the conversation no longer fits. Lesson 02
established the fact that causes the problem, which is that the model is
stateless and the entire conversation is resent on every single request. Lesson
13 made it worse in a way that is easy to miss. Now that sessions persist, a
conversation is no longer bounded by how long you are willing to sit at the
keyboard. You can resume yesterday's session and keep going, and the file only
ever grows.

So something has to be dropped. This chapter is about which something.

Files in this folder.

```text
lessons/14-context-management/
  context.py     new. estimate_tokens, split_into_blocks, fit_to_budget
  agent.py       lesson 13's loop plus a budget parameter and to_send
  check.py       five checks, one of which is the reason the module exists
  permissions.py unchanged from lesson 12
  session.py     unchanged from lesson 13
  prompt.py      unchanged from lesson 10
  providers.py   unchanged from lesson 06
  tools.py       unchanged from lesson 09
  README.md      this file
```

One new file of eighty one lines, and four changed lines in `agent.py`.

## 1. The problem lesson 13 left you with

Take the agent you finished lesson 13 with and give it a real task on a real
repository. It reads a file. It greps. It reads two more files. It runs your
tests, gets a failure, reads the failing test, edits something, runs the tests
again.

Count what is in `messages` at that point. Every one of those tool results is
still there, in full, and every one of them is sent again on the next request.
`read_file` in `tools.py` truncates at `MAX_OUTPUT = 4000` characters, so one
file read is about four thousand characters, call it a thousand tokens. Six
reads is six thousand tokens of file contents that ride along in every request
for the rest of the session.

Add the fixed overhead, which nobody thinks about. The system prompt from
lesson 10 is about six hundred characters. The seven tool schemas serialise to
2595 characters, which is roughly six hundred and fifty tokens, and they are
sent on every request whether or not the model uses a single one of them.

On a model with an eight thousand token window you will hit the wall in about
ten turns of ordinary work. Not on a pathological task. On a normal one.

Here is what hitting it looks like. This is an OpenAI compatible endpoint,
which is what `OpenAICompatProvider` talks to.

```json
{
  "error": {
    "message": "This model's maximum context length is 8192 tokens. However, your messages resulted in 9317 tokens. Please reduce the length of the messages.",
    "type": "invalid_request_error",
    "param": "messages",
    "code": "context_length_exceeded"
  }
}
```

And the same failure from the native Anthropic endpoint, which
`AnthropicProvider` talks to.

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "prompt is too long: 213558 tokens > 200000 maximum"
  }
}
```

Two things about those bodies are worth noticing before we go further.

**The number in the message is the provider's number, not yours.** It is
9317 because that provider's tokeniser said 9317. Nothing you can compute
locally will reproduce it exactly. Section 6 is entirely about the consequences
of that.

**The status is 400, not 413 or 429.** It is a malformed request as far as the
API is concerned, in exactly the same category as sending a field it does not
recognise. That matters for lesson 17, because a `400` is not worth retrying.
Sending the identical oversized conversation again gets the identical
rejection, and a naive retry loop will do it three times with exponential
backoff before giving up, which wastes eight seconds proving something that was
knowable immediately.

What you actually see on your terminal is less helpful than either JSON body,
because `providers.py` streams and calls `response.raise_for_status()` on a
response whose body has not been read.

```text
Traceback (most recent call last):
  File "main.py", line 60, in <module>
    run(provider, task, system=system)
  File "agent.py", line 48, in run
    text, calls = provider.stream(
  File "providers.py", line 46, in stream
    response.raise_for_status()
httpx.HTTPStatusError: Client error '400 Bad Request' for url 'http://localhost:11434/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400
```

The explanation was in the body. You got the status line. Remember this,
because it is going to matter a great deal in section 3.

There is a third failure mode that is worse than either error, and you should
know it exists. Several local runtimes do not reject an oversized prompt at
all. They quietly truncate it to fit the context length they were configured
with, usually from the front, and answer. No error, no warning, no line in any
log. The agent simply becomes confused about what you asked it, and you spend
half an hour wondering why it forgot the task. An error is a gift compared to
that.

## 2. The obvious approach, and why it is a disaster

The instinct is immediate and it is the right shape. The conversation is too
big, the newest messages matter most, so drop messages off the front until the
total fits.

Written out, it is about ten lines, and it looks completely reasonable.

```python
def fit_to_budget_the_wrong_way(messages, budget):
    """Do not do this."""
    system = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]

    kept = []
    used = estimate_tokens(system)
    for message in reversed(rest):
        cost = estimate_tokens([message])
        if kept and used + cost > budget:
            break
        kept.insert(0, message)
        used += cost
    return system + kept
```

Read it against the real `fit_to_budget` in `context.py` and notice how close
they are. Same structure, same guard, same accumulator, same reversal. The
difference is one word. This version walks `rest`. The real one walks
`split_into_blocks(rest)`.

Now run it on the conversation from `check.py`, which is deliberately the
smallest conversation that can demonstrate the bug.

```python
CONVERSATION = [
    {"role": "system", "content": "be terse"},
    {"role": "user", "content": "first question"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "add", "arguments": "{}"}}
        ],
    },
    {"role": "tool", "tool_call_id": "c1", "content": "result"},
    {"role": "assistant", "content": "first answer"},
    {"role": "user", "content": "second question"},
    {"role": "assistant", "content": "second answer"},
]
```

Seven messages. Under `estimate_tokens` they cost 6, 7, 24, 5, 7, 7 and 7
tokens, sixty three in total. The assistant message with the tool call is the
expensive one at 24, because the serialised call object is counted along with
the content.

Give the wrong version a budget of 40 and this is what comes back.

```json
[
  {
    "role": "system",
    "content": "be terse"
  },
  {
    "role": "tool",
    "tool_call_id": "c1",
    "content": "result"
  },
  {
    "role": "assistant",
    "content": "first answer"
  },
  {
    "role": "user",
    "content": "second question"
  },
  {
    "role": "assistant",
    "content": "second answer"
  }
]
```

Look at the second message.

There is a message with role `tool` and `tool_call_id` of `c1`, and there is no
longer any message anywhere in that list containing a tool call with the id
`c1`. The expensive assistant message that made the call cost 24 tokens and was
the first thing over the line, so it was dropped. Its answer, at 5 tokens, was
cheap, so it survived.

That is an orphaned tool result, and it is not a cosmetic problem.

## 3. The orphaned tool result

This is the heart of the chapter. Read it slowly, because everything about how
this bug presents itself is designed to send you looking in the wrong place.

### The rule the API actually enforces

Every provider that supports tool calling enforces the same structural rule,
whatever the surface differences in their formats. A tool result must be
preceded by the tool call it answers. The pairing is by id. It is not a
convention, not a recommendation and not something the model merely prefers.
It is validated on the server before a single token is generated.

The reason is not arbitrary. A tool result is not a standalone fact. On its
own, `{"role": "tool", "tool_call_id": "c1", "content": "result"}` is a string
called `result` with no name, no arguments and no context. Nothing in that
object says what tool ran or what it was asked. All of that lives in the
assistant message that made the call. Take the call away and what remains is
genuinely meaningless, and the API refuses to pretend otherwise.

### What the API does with a stray result

Here is the part people get wrong when they reason about it in the abstract. A
stray tool result is not ignored. It is not skipped. It does not produce a
warning or a degraded answer. The entire request is rejected.

From an OpenAI compatible endpoint.

```json
{
  "error": {
    "message": "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.",
    "type": "invalid_request_error",
    "param": "messages.[1].role",
    "code": null
  }
}
```

The misspelling of `preceeding` is theirs, and it has been there for years. If
you ever search the web for this error, search for it with the typo.

From the native Anthropic endpoint, where results are content blocks rather
than messages, so the wording differs while the rule does not.

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "messages.0: unexpected `tool_use_id` found in `tool_result` blocks: toolu_01A09q90qw90lq917835lq9. Each `tool_result` block must have a corresponding `tool_use` block in the previous message."
  }
}
```

And the mirror image of the same bug, which is what you get when you drop the
result and keep the call. Trimming from the front will not usually produce
this, but truncating from the back will, and so will a crash between the two
appends.

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "messages.1: `tool_use` ids were found without `tool_result` blocks immediately after: toolu_01A09q90qw90lq917835lq9. Each `tool_use` block must have a corresponding `tool_result` block in the next message."
  }
}
```

Note `param` in the first body and the `messages.0` prefix in the other two.
The provider is telling you the index of the offending message. That is the
single most useful field in the response, and in section 1 you saw why you will
probably never see it, because `raise_for_status()` on an unread streaming
response gives you the status line and nothing else.

### Why it looks like it came from nowhere

Now the part that makes this expensive rather than merely annoying.

Follow the timeline through the loop in `agent.py`.

```text
turn 6   messages is 5,800 tokens. Under budget. Sent whole. Fine.
         The model calls read_file. The call and its result are appended.
turn 7   messages is now 6,900 tokens. Over budget.
         to_send() trims. The assistant message holding the turn 3 tool call
         goes over the line and is dropped. Its result, being small, is kept.
         The request is sent. It is accepted. The model answers normally.
         Nothing appears on your screen. You notice nothing at all.
turn 8   messages is trimmed again, the same way, and sent.
         400 Bad Request
```

Read turn 7 again. The trim that created the broken list did not fail. Whether
the request that carries an orphan is rejected depends on which messages happen
to fall on which side of the budget on that particular turn, and the specific
arrangement that trips the validator may not appear for another turn or two.

So the error surfaces at turn 8. What was on your screen at turn 8 was a tool
result and some model prose. Your instinct will be that whatever the agent just
did caused the failure, and you will go and read the tool that ran most
recently. It is not that tool. The damage was done a turn ago by a function
that did not error, did not print, and left the conversation you can see in
`messages` completely intact, because the trimmed list is a copy that is thrown
away as soon as the request is built. Section 7 explains why that copy is right
to be a copy, and it is also why you cannot find the broken list by opening the
session file afterwards.

To find this bug you have to suspect a function that produced no error, on a
turn before the one that failed, whose output was never written down anywhere.
That is a genuinely nasty combination.

### It is common, and it is common in real code

This is not a beginner's mistake that experienced people are above. It is one
of the most frequently reported bugs in agent harnesses, and it has shipped in
serious ones. The reason is structural rather than a matter of care.

Trimming and pairing are written at different times by people thinking about
different things. Whoever writes the loop is thinking about tool calls, and
they naturally append the assistant message and the tool message together,
adjacent, correct. Weeks later, someone is thinking about token budgets, and a
budget is a number, and a list of messages each of which has a size is exactly
the kind of thing a number gets applied to. Nothing in the shape of the problem
suggests the elements are not independent. The list is a list. It has no marker
in it saying that indices 2 and 3 are one thing.

Three properties then conspire to keep the bug alive. It only appears when a
conversation is long enough to need trimming, so it never shows up in
development on short examples. It only appears at some budgets and not others,
so a test with one hardcoded number will pass. And it reports itself one
request late, so the traceback points away from the cause. Section 9 is about
the shape of the check that catches it despite all three.

### The lesson underneath it

The general form of this is worth carrying beyond agents. Some lists are not
lists. They look like sequences of independent elements, and they are actually
sequences of records that happen to have been flattened, with an invariant
holding some of the elements together.

A message list is one of those. So is a stream of database operations inside a
transaction, and a sequence of log lines belonging to one traceback. In every
case, the moment you write code that indexes, slices, filters, reverses or
paginates the flattened form, you have to ask which groups you have just cut
through. And the durable fix is never to be more careful with the indices. It
is to stop working in the flattened form.

## 4. Blocks instead of messages

Which is the fix. Do not look at a single message. Look at exchanges.

An exchange begins at a user message and runs up to just before the next user
message. Everything the assistant said in between, and every tool it called,
and every result that came back, belongs to the question that prompted it.
Fifteen lines of `context.py` do it.

```python
def split_into_blocks(messages):
    """Group messages into exchanges that each begin with a user message.

    Everything the assistant said and every tool it ran belongs to the
    question that prompted it, so the question and its consequences travel
    together or not at all.
    """
    blocks = []
    for message in messages:
        if message["role"] == "user" or not blocks:
            blocks.append([message])
        else:
            blocks[-1].append(message)
    return blocks
```

Walk it on the six non system messages of the fixture.

| Message | Role | `blocks` after this message |
| --- | --- | --- |
| `first question` | user | one block, holding it |
| the `c1` tool call | assistant | that block, now two messages |
| the `c1` result | tool | that block, now three messages |
| `first answer` | assistant | that block, now four messages |
| `second question` | user | a second block starts |
| `second answer` | assistant | second block, now two messages |

Two blocks. The first is `["user", "assistant", "tool", "assistant"]` and costs
43 tokens. The second is `["user", "assistant"]` and costs 14. The system
message is handled separately, so it is not in either.

Three details in those fifteen lines deserve a sentence each.

**`or not blocks` is not a formality.** It is what happens when the first
message you are handed is not a user message. That is a real case rather than a
hypothetical one, because a resumed session might begin anywhere, and lesson 13
lets you resume. Without that clause, `blocks[-1]` on an empty list raises
`IndexError`. With it, whatever arrives first opens a block. The rule is that
this function must never crash on a conversation it did not expect, because the
alternative is that resuming a session becomes a coin toss.

**The boundary is the user message and nothing else.** Not the assistant
message, not the tool result, not a turn counter. The reason is that the user
message is the only role that never has a partner. An assistant message can
have a result pointing back at it. A tool message always points back at an
assistant message. A user message points at nothing and nothing points at it,
so it is the only safe place to cut.

**A block can be arbitrarily large.** Ask one question that sends the agent
through fifteen tool calls and that is one block. This is not a flaw and it is
not something to fix by splitting large blocks. A fifteen call investigation is
one unit of meaning, and half of it is not much use anyway. Section 5 deals
with what happens when the newest block on its own is bigger than the budget.

Now `fit_to_budget` reads almost the same as the disaster in section 2.

```python
def fit_to_budget(messages, budget: int):
    system = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]
    blocks = split_into_blocks(rest)

    kept = []
    used = estimate_tokens(system)
    for block in reversed(blocks):
        cost = estimate_tokens(block)
        if kept and used + cost > budget:
            break
        kept.insert(0, block)
        used += cost
    return system + [message for block in kept for message in block]
```

Newest first, because the recent past is what the model needs to continue. Stop
at the first block that does not fit, rather than skipping it and trying an
older one, because a conversation with a hole in the middle is worse than a
shorter one that is continuous. And the last line flattens back into the list
of messages the provider wants, which is the only place the flattened form is
allowed to exist.

The property that matters is now structural rather than something you have to
remember. A tool call and its result are in the same block by construction. A
block is kept whole or dropped whole. Therefore no sequence of trims can
separate them. You are not being careful about the invariant, you have made it
impossible to violate.

## 5. What must never be dropped

Two things are exempt, and each has a reason that only shows itself when you
consider what happens without it.

### The system message

```python
    system = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]
```

It is pulled out before anything is measured and put back unconditionally at
the end. It cannot be dropped because it is never a candidate.

The system message is also, in this program, one of the oldest messages in the
conversation. `run` appends it first. Under any policy of dropping the oldest
thing, it goes first, and it is the last thing you want to lose.

Think about which failure you would rather debug. An agent that has forgotten
the beginning of the conversation still knows how to behave, still knows which
directory it is confined to, still knows the facts about the workspace that
`build_system_prompt` gave it. It has lost history. It will ask you to remind
it what you wanted, which is annoying and recoverable.

An agent that has forgotten its instructions half way through a task is a
different animal. It is a raw model with a set of tools that can edit files and
run shell commands, and no statement anywhere about what it is supposed to be
doing or how it is supposed to behave. It does not announce that it has lost
its instructions, because it has no memory of ever having had them. It just
starts behaving differently, mid task, with your files in reach.

The two failures are not comparable, so the cheap one is chosen every time.

`check.py` makes it a rule.

```python
    if fit_to_budget(CONVERSATION, budget=1)[0]["role"] != "system":
        fail("the system message was dropped, so the agent forgot its instructions")
```

A budget of one token. Nothing else can possibly fit. The system message must
still be first.

### The newest block, even when it alone is over budget

This is the `kept and` in the condition, and it is easy to read past.

```python
        if kept and used + cost > budget:
            break
```

On the first iteration `kept` is empty, so the whole condition is false
regardless of the cost, and the newest block is appended no matter how large it
is. Only from the second iteration onwards does the budget have any authority.

Delete those two words and the function becomes correct in the arithmetic sense
and useless in practice. On the fixture, with the system message costing 6 and
the newest block costing 14, every budget from 1 to 19 would return the system
message and nothing else. You would send a system prompt, seven tool schemas,
and no conversation.

Compare the two failures again, because the reasoning is the same shape as
before.

Send an oversized request and you get the `400` from section 1, which names the
limit and the size you exceeded. It is unambiguous, it points at the right
problem, and the fix is obvious.

Send a conversation containing no user message and you get a `200`. The model
answers. It has a system prompt telling it it is a coding agent in a specific
directory with seven tools, and nothing to do, so it invents something. It
greets you. It asks what you would like. It picks a file and starts describing
it. Whatever it does, it is fluent and it is untethered, and nothing in the
response indicates that anything went wrong. The user's report will be that the
agent has gone mad, and it will be correct, and it will not be actionable.

Never trade a clear error for a confident wrong answer. A model handed nothing
does not fail loudly, and that is precisely why an empty conversation is the
worse outcome.

## 6. Why the estimate is deliberately rough

Now `estimate_tokens`, which is the piece most likely to be mistaken for a
weakness in this module.

```python
CHARACTERS_PER_TOKEN = 4
PER_MESSAGE_OVERHEAD = 4


def estimate_tokens(messages):
    total = 0
    for message in messages:
        total += len(message.get("content") or "") // CHARACTERS_PER_TOKEN
        for call in message.get("tool_calls") or []:
            total += len(str(call)) // CHARACTERS_PER_TOKEN
        total += PER_MESSAGE_OVERHEAD
    return total
```

Divide characters by four, add four per message for the role and framing the
provider adds around each one, count the serialised tool calls as well because
they are large and they are sent. That is the whole thing.

It is wrong, and it is wrong on purpose, and there is no version of it that is
right.

**Every provider counts differently.** A token is whatever a particular
tokeniser says it is. OpenAI has used different tokenisers across model
generations, so the same string is a different number of tokens on two models
from the same company. Anthropic's tokeniser is different again and is not
published. Open weight models ship their own. There is no universal count of
tokens in a string, only counts relative to a tokeniser.

**A tokeniser built for one company does not count another company's tokens.**
This is the mistake worth naming explicitly, because it is the one that looks
like diligence. You install `tiktoken`, which is a real tokeniser written by
OpenAI, you run it over your messages, and you get a precise number. It is
precise and it is about the wrong model. Point that agent at Claude, or at a
local Qwen, and you are computing an exact answer to a question nobody asked.
The precision makes it worse, because a rough number invites you to leave
headroom and an exact one invites you to trust it.

**Four characters per token is only true for English prose.** Code tokenises
worse, because identifiers, punctuation and indentation fragment. JSON
tokenises worse again. Thai, Japanese and Chinese are dramatically worse,
frequently approaching one token per character, so an estimate that is roughly
right for an English conversation can be off by a factor of three for a Thai
one. Since the tool results in this agent are mostly source code and JSON, the
estimate here leans towards undercounting.

**And it does not count everything that is sent.** This is the biggest gap and
it is not in the function at all. `estimate_tokens` measures messages. The
request also carries the seven tool schemas, which serialise to 2595 characters
in this lesson, roughly six hundred and fifty tokens, on every single request.
Nothing in `context.py` knows they exist.

So the rule for using it is the one in the docstring.

```python
    """A rough count, deliberately not exact.

    Every provider counts differently and none of them count the way a
    character estimate does. Use this to decide when to start trimming, then
    use the number the provider reports afterwards to know what actually
    happened. Trusting a local estimate to be exact is how people end up
    trimming to ninety percent of a window and still getting rejected.
    """
```

Using it to decide when to trim is fine. Trimming is not a precise operation.
You need to know roughly when the conversation is getting large, and being
twenty percent wrong means you trim slightly early or slightly late, and both
are survivable.

Using it as an exact number is how people end up rejected at ninety percent of
the window. The reasoning goes that the window is 8192, so trim to 7372, which
leaves ten percent of headroom and that is surely plenty. Then the estimate
undercounts by fifteen percent because the conversation is full of JSON, and
the schemas add six hundred and fifty tokens that were never in the sum, and
the request is 9317 tokens, and you get the error from section 1 while looking
at a log line that says 7372. Which sends you hunting for a bug in your
arithmetic that does not exist, because the arithmetic was never the kind of
thing that could be right.

So pick a budget with real headroom, treat the number as a signal rather than a
measurement, and get the truth from the provider afterwards. Every response
carries a usage block with the counts that were actually charged. Reading it,
acting on it, and making the cost visible is lesson 15.

## 7. What travels is not what is remembered

The change to `agent.py` is four lines, and one design decision.

```python
    def to_send():
        """What travels is not what is remembered.

        The whole conversation stays in messages because the session file
        and anyone debugging later need all of it. Only the copy handed to
        the provider is trimmed.
        """
        return messages if budget is None else fit_to_budget(messages, budget)
```

And at the call site.

```python
        text, calls = provider.stream(
            to_send(), schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )
```

`messages` is never trimmed. It grows for the whole run and holds everything.
`fit_to_budget` returns a new list, `provider.stream` gets that, and it is
discarded when the request is done.

The alternative is to trim in place, which is one line shorter and destroys
things you need.

**The session file would lose messages.** `remember` calls `on_message`, which
in lesson 13 is `session.append`. If trimming mutated `messages`, the session
file would still contain the dropped lines, because they were written when they
happened, but the in memory conversation and the file would drift apart, and
resuming would reload messages the running agent had already decided to forget.
Two sources of truth about the same conversation is a bug generator.

**Debugging would become impossible.** Lesson 13 argued that the highest value
of a session file is not resuming, it is that when an agent does something
inexplicable you can open the file and read exactly what it saw. That argument
only holds if the file is complete. An agent that drops a file read at turn 7
and then contradicts that file at turn 9 is behaving perfectly reasonably, and
you can only work that out if turn 7 is still on disk.

**Trimming is a property of a request, not of a conversation.** This is the
cleanest way to hold it. The budget belongs to the model you are talking to
right now. Switch from an eight thousand token local model to a two hundred
thousand token hosted one halfway through a session and the same history should
suddenly fit. It can, because the history was never damaged. Only the copies
were smaller.

**And the trim is recomputed every turn.** `to_send` is a function, not a value
computed once before the loop. Each turn it looks at the current `messages` and
decides again. Blocks that were dropped on turn 7 come back on turn 8 if the
budget allows, which it will if the newest block was small. The trim has no
memory and needs none.

There is one honest cost, and section 3 already named it. The list that was
actually sent exists only inside the `stream` call. If you need to see it, and
when you are debugging a trimming bug you do, you have to print it there. That
is the price of keeping the record complete, and it is the right side of the
trade.

The default is `budget=None`, which means no trimming at all. Every earlier
lesson's behaviour is unchanged unless you ask for the new one.

## 8. Summarising instead of dropping, and why not here

There is a better answer than dropping, and it deserves a fair hearing rather
than a dismissal, because you are going to reach for it.

The idea is that instead of discarding the oldest blocks, you send them to the
model with a request to summarise, and replace them with the summary. Twelve
thousand tokens of exploration become four hundred tokens saying which files
were read, what was in them, what was tried and what failed. Every real harness
does some version of this, and the reason is real.

**What it buys.** Dropping loses information permanently. If the agent read a
config file on turn 2 and needs a value from it on turn 20, dropping means it
reads the file again, which costs a turn and the same tokens. Summarising keeps
a compressed trace of everything, so the agent still knows the file exists and
roughly what was in it. On long tasks that difference is large.

**What it costs, and this is why it is not in this lesson.**

It costs an extra model call, with the whole span you are summarising as input.
That call is not free in money, and it is not free in time either. It happens
mid task, while you are watching, and the agent stops for several seconds to
think about its own history rather than about your problem.

It can lose the exact detail that mattered. A summary is a lossy compression
chosen by a model that does not know which detail you will need at turn 20. The
failure is characteristic and unpleasant. The summary says the tests were run
and two failed. The exact assertion message, which contained the number that
explained everything, is gone. Dropping loses a lot obviously. Summarising
loses a little invisibly, and invisible loss is harder to reason about because
the agent now confidently believes a slightly wrong version of its own past.

And it makes the conversation non reproducible. Run the same session twice with
the same inputs and you get two different summaries, because the summariser is
a language model. From that point the two runs have different histories and
diverge. For a course where every `check.py` must give the same answer every
time, that alone rules it out. For a real system it means a session file no
longer explains a run, because replaying it would produce something else.

There is a fourth issue that is worth knowing about and rarely mentioned. The
summary enters the conversation as text, and if the span being summarised
contained a tool result with injected instructions in it, the summariser may
faithfully carry those instructions into the summary, where they now look like
part of the agent's own notes rather than like file contents. Lesson 12's
argument about the difficulty of separating instructions from data applies with
extra force to anything that rewrites the conversation.

**So the default is dropping whole exchanges.** It is deterministic. It costs
nothing. It is about eighty lines with no model call in them. It is trivially
testable, which is what section 9 exercises. And the information it loses is
lost in an obvious way, which the agent can recover from by reading a file
again.

Summarising is a reasonable thing to add, and adding it on top of this design
is straightforward, because `split_into_blocks` has already given you the unit
to summarise. Replace a run of old blocks with one synthesised block instead of
deleting them, keep the newest blocks verbatim, and keep the system message
exempt as it already is. The block boundary is the right seam for both
policies, which is a good sign that the seam is in the right place.

Do the simple thing first and measure whether you need the complicated one.

## 9. Running check.py

From the lesson folder. No endpoint and no API key, because nothing here calls
a model.

```bash
cd lessons/14-context-management
python check.py
```

```text
OK a tool call and its result stay together in one block
OK the system message is never dropped
OK the newest exchange is the one that is kept
OK no budget produces an orphaned tool result, which is the bug this prevents
OK a full conversation of about 63 tokens is left alone
```

Five lines. The first three are about the pieces, the fifth is a sanity check
that a large budget is a no op, and the fourth is the reason the module exists.

**One. Blocks hold pairs together.**

```python
    blocks = split_into_blocks(CONVERSATION[1:])
    if len(blocks) != 2:
        fail(f"expected two exchanges, got {len(blocks)}")
    if [m["role"] for m in blocks[0]] != ["user", "assistant", "tool", "assistant"]:
        fail("a tool call and its result did not stay in the same block")
```

The slice drops the system message, which `fit_to_budget` handles separately.
Two blocks, and the first one contains the tool call and its result adjacent,
which is the property everything else rests on.

**Two and three. The exemptions from section 5.** A budget of one still returns
the system message first. A budget of 20 still ends with `second answer`, which
proves that the newest exchange is what survives rather than the oldest. Twenty
is chosen because it is exactly the system message plus the newest block, so it
is the tightest budget at which a real choice is made.

**Four. The sweep.**

```python
    for budget in range(1, 60):
        kept = fit_to_budget(CONVERSATION, budget=budget)
        if not result_ids(kept) <= call_ids(kept):
            fail(f"a tool result was left with no tool call at budget {budget}")
        if not any(m["role"] == "user" for m in kept):
            fail(f"nothing was left to answer at budget {budget}")
```

`result_ids(kept) <= call_ids(kept)` is a subset test on two sets of ids. Every
`tool_call_id` that appears in a result must appear as the id of a call that is
still present. That is the API's rule from section 3, restated as one line of
Python that runs in a check instead of on a server.

The question worth answering is why this is a loop from 1 to 59 rather than one
well chosen budget, since a single number is shorter and looks like it tests
the same thing.

It does not test the same thing, and the naive implementation from section 2
shows exactly why. Run it against this fixture at every budget and record which
ones produce an orphan.

```text
budgets 1 to 31    no orphan. the newest block alone, or nothing much
budgets 32 to 55   ORPHAN. the tool result survives, its call does not
budgets 56 to 63   no orphan. both survive
```

Twenty four budgets out of sixty three expose it, and thirty nine hide it. Had
the check picked 20, it passes. Had it picked 60, it passes. Both are
reasonable looking numbers, and both certify a broken implementation as
correct. The bug is not present or absent, it is present in a window, and a
test that samples one point outside the window learns nothing.

That window is wide because the naive version is badly wrong. A subtle version
is much narrower. Change the comparison in `fit_to_budget` from
`used + cost > budget` to `used + cost >= budget` and the two implementations
disagree at exactly one budget value out of every value you could pick, which
for this fixture is 63, the point where the two blocks plus the system message
exactly equal the budget. Off by one errors live on boundaries, and a boundary
is one value wide. Guessing which value is not a strategy. Sweeping is.

The second assertion in the loop is section 5's other rule as a check. At every
budget, however small, something must remain for the model to answer. That is
what catches the deletion of `kept and`, which on this fixture would empty the
conversation for every budget from 1 to 19.

**Five. A large budget changes nothing.**

```python
    if fit_to_budget(CONVERSATION, budget=100000) != CONVERSATION:
        fail("a large budget changed the conversation")
```

Equality against the original list, not a length comparison. It proves the
order was preserved, the system message went back in the right place, and
nothing was duplicated by the flatten at the end. A trimmer that quietly
reorders a conversation when it has no work to do is a trimmer you will not
trust later.

The printed count of 63 tokens is the estimate from section 6 for the whole
fixture. It is in the output as a reminder that the number exists and is
approximate, which is exactly how it should be read.

If the fourth line ever fails on a change you have made, read the budget in the
message and run `fit_to_budget` at that budget by hand. The broken list it
returns will show you, in one glance, which half of a pair went missing.

## 10. What you cannot do yet

You can now keep a conversation inside a window without breaking it. Two things
are still missing, and they are the same thing said twice.

**You are trimming against a guess.** `budget` is a number you chose. The
estimate that decides when to act is a division by four. Nothing in the program
has ever compared either of them against reality. You could be trimming at
sixty percent of the window and throwing away context you did not need to lose,
or at ninety five percent and still getting rejected, and you have no way to
tell which because no true number has ever entered the program.

**You have no idea what any of this costs.** Not one token count has been
printed by anything in fourteen lessons. You cannot say whether the task you
just ran cost a tenth of a cent or forty cents. You cannot say which part of it
was expensive. And without that, every optimisation is superstition. You will
shorten the system prompt, which is about a hundred and fifty tokens, and feel
that you have done something, while a `grep_files` result of a hundred and
eighty lines rides along in every request for the rest of the session and costs
you thirty times more.

There is a specific irony worth sitting with. This chapter added machinery to
manage a resource, and the machinery cannot see the resource. `estimate_tokens`
does not count the tool schemas, so about six hundred and fifty tokens of every
request are invisible to the thing whose job is to keep requests small.

Lesson 15 is token economy. Where the money actually goes, measured from the
usage the provider reports rather than guessed. Prompt caching and the ordering
rule it depends on, which is that stable content goes first and changing content
goes last, and what happens to your bill when a timestamp near the front
invalidates the cache on every request. Trimming tool output before it is sent
rather than after it has been paid for. And not shipping schemas for tools this
task cannot use, which is the six hundred and fifty tokens from the paragraph
above.

On to lesson 15.
