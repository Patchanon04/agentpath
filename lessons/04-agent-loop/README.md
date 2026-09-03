[อ่านภาษาไทย](README.th.md)

# Lesson 04. The agent loop

This is the lesson where you build an agent.

Not a chat program that happens to know about functions. An actual agent. A
program that receives a request in English, decides on its own that it needs
to run something, runs it, reads the result, and keeps going until it has an
answer. Everything in the previous three lessons was a part being machined.
This is the lesson where the parts get bolted together and the thing starts
turning.

The remarkable part is how small it is. The whole idea fits in about thirty
lines of Python, and once you have read them you will never again be impressed
by a diagram of an agent architecture. There is a `for` loop, a list of
dictionaries, and an `if` statement. That is the machine.

Files in this folder.

```text
lessons/04-agent-loop/
  tools.py    unchanged from lesson 03, two toy tools and their schemas
  llm.py      unchanged from lesson 03, sends tools and parses tool calls
  agent.py    new, the loop itself
  check.py    a script that proves the whole loop works end to end
  README.md   this file
```

Notice that only one file is new. `tools.py` and `llm.py` are byte for byte
what you already have. All the new capability in this lesson comes from
`agent.py`, and `agent.py` is mostly a `for` loop. Keep that in mind whenever
somebody tells you agents are complicated.

## 1. The problem left over from lesson 03

Lesson 03 ended on a deliberately unsatisfying note. Here is the last thing it
printed.

```text
OK the model asked for add(2, 3) and the tool returned 5
```

The tool returned `5`. To whom?

To `check.py`. The number went into a Python variable in a script that then
exited. Look at the shape of the code that produced that line.

```python
text, calls = complete([{"role": "user", "content": PROMPT}], tools.SCHEMAS)
call = calls[0]
result = tools.run(call["name"], call["arguments"])
print("OK the model asked for add(2, 3) and the tool returned 5")
```

Count the HTTP requests. There is exactly one. We sent the question, the model
asked for `add`, we ran `add`, and then the program stopped. The model asked us
a question and we never answered it. From the model's point of view the
conversation ended mid sentence.

Two separate things are broken here, and it helps to name them separately
because they need different fixes.

The result never travelled back. There is no second call to `complete`.
The string `"5"` exists only inside our process. The model that requested the
addition has no memory of the request and no knowledge of the answer, because
the API is stateless. Everything the model knows arrives in the `messages`
list of the request we send, and we never sent another request.

We hardcoded the number of steps. `check.py` assumes exactly one tool call,
takes `calls[0]`, runs it, and stops. That works because the prompt was rigged
to produce one call. It falls apart the moment a real question needs two.

Because of those two failures, all of the following are impossible with lesson
03's code.

- The agent cannot answer in a sentence. Only the model writes sentences, and
  the model does not know the result.
- The agent cannot chain. Deciding what to do second requires knowing what
  happened first.
- The agent cannot recover from an error. `tools.run` carefully turns every
  exception into a readable error string, and then that string goes nowhere.

Every one of those is the same missing piece wearing a different hat. The
result has to go back into the conversation, and then we have to ask again.

Asking again is the whole lesson.

## 2. Why this has to be a loop and not one more function call

The obvious fix is to write one more call and be done.

```python
text, calls = complete(messages, tools.SCHEMAS)
result = tools.run(calls[0]["name"], calls[0]["arguments"])
messages.append(...)                       # put the result in
final, _ = complete(messages, tools.SCHEMAS)   # ask one more time
print(final)
```

That is a real improvement. It also breaks on the second question anybody
asks.

### The model cannot know the answer until we run the tool

Start from the constraint that makes everything else follow. A language model
produces text based on the text it has been given. It cannot run your `add`
function. It cannot see your file system. It cannot know that a dice landed on
4, because the dice has not been rolled yet, and it will not be rolled until
our Python calls `random.randint`.

So when the model wants a fact it does not have, the only move available to it
is to stop generating and ask. That request comes back to us as data. We run
the tool. Now we know something the model does not, and the only way to tell it
is to send another HTTP request containing that new fact.

That single exchange is one round trip. Question in, tool request out, tool
result in, answer out. The two `complete` calls above handle exactly one round
trip.

### The number of round trips is not knowable in advance

Now watch how quickly one round trip stops being enough.

```text
"What is 2 plus 3?"
  round trip 1   add(2, 3) -> 5
  round trip 2   the model answers in words
  total: 2 calls to the model
```

```text
"Roll a six sided dice and add 10 to whatever it shows."
  round trip 1   roll_dice(6) -> 4
  round trip 2   add(4, 10) -> 14        the model could not have written
                                          this call before seeing the 4
  round trip 3   the model answers in words
  total: 3 calls to the model
```

```text
"Roll a dice, then add that many again, and tell me if it beats 20."
  round trip 1   roll_dice(6) -> 2
  round trip 2   add(2, 2) -> 4
  round trip 3   the model answers in words, no it does not beat 20
  total: 3 calls, but a different 3 every time you run it
```

The second example is the important one. The model literally could not produce
`add(4, 10)` in its first turn, because the number 4 did not exist anywhere in
the universe at that moment. It has to see the dice result before it can write
the next call. The steps are not merely many, they are dependent, and each one
unlocks the next.

And in the third example, run it twice and you can get a different number of
steps. Roll a 6 and the model might decide to check something else. Roll a 1
and it might answer immediately. The count depends on values that do not exist
until runtime.

### That unknown count is the definition of a loop

Here is the plain programming argument, with no AI in it at all.

If you know how many times to repeat something, you can write it out. Twice is
two lines. Five times is five lines, or a `for` over `range(5)`. Ugly but
possible.

If you do not know how many times, you cannot write it out. You need a
construct that repeats until a condition is met. That is what a loop is for,
and it is the only reason loops exist in any language.

We do not know how many round trips a question needs. We cannot know, because
the answer depends on what the tools return, and the tools have not run yet.
Therefore this is a loop. Not by style preference. By necessity.

### Why not recursion, or a state machine, or a graph

Those are the usual alternatives, and it is worth saying why a plain loop wins
here.

Recursion would work. A function that calls itself with a longer message
list is exactly equivalent. It is worse for a beginner because the growing
state is hidden in the call stack instead of sitting in a variable you can
print, and because Python's recursion limit becomes a second failure mode you
have to reason about on top of the one you already have.

A state machine or a graph is what several popular frameworks give you.
Nodes, edges, conditional transitions. Those become genuinely useful when you
have branching workflows, human approval steps, and parallel sub agents, which
is part 4 of this course. Reaching for one now would bury a five line idea
under a hundred lines of framework, and you would learn the framework instead
of the idea.

A plain `for` loop keeps every piece of state in one visible list, keeps
the control flow readable top to bottom, and gives you a turn limit for free
because `range` already counts. Start here. The fancier shapes are refinements
of this shape, and they are much easier to understand once you know what they
are refining.

## 3. The four steps in plain language

Before any code, learn the loop as four sentences. If you remember nothing else
from this chapter, remember these. Every agent ever built, including the ones
running in production at large companies, is this with more error handling.

1. **Ask the model.** Send the whole conversation so far, along with the list
   of tools it is allowed to request.
2. **If it asked for tools, run them.** Look up each requested name in your own
   dictionary of functions and call it. This is the only step that touches the
   real world.
3. **Put the results back into the conversation.** Append what the model asked
   for and what each tool returned, so the next request carries both.
4. **Ask again.** Go back to step one with the longer conversation.

And the exit condition, which is one more sentence.

> Stop when the model answers in words instead of asking for a tool.

That is the whole thing. Read the four steps again and notice what is not in
them. There is no planning phase, no memory system, no reasoning engine, no
scheduler. An agent is a conversation you keep feeding until the other side
stops asking questions.

Here is the same loop as a picture, for one round trip.

```text
  user: "What is 2 plus 3?"
        |
        v
  [1] ask the model  ------------------> model
                                          |
        <---------------------------------+  "run add with a=2 b=3"
        |
        v
  [2] run the tool           add(2, 3) -> 5
        |
        v
  [3] append to the conversation
        assistant: (I want add(2,3))
        tool:      5
        |
        v
  [4] ask again  ---------------------> model
                                          |
        <---------------------------------+  "2 plus 3 is 5."
        |
        v
  no tool calls, so return the text and stop
```

The loop body ran once. For the dice example it would run twice. For a question the model can answer from memory the tool steps run zero times, because step one comes
back with words on the first try and we return immediately.

## 4. Why the assistant message with tool_calls must go back into the history

This is the subtle part of the lesson, and it is where almost everyone writing
their first agent gets stuck. Read this section slowly.

When the model asks for a tool, two messages have to be appended to the
conversation, not one.

```python
# the model's request, in the model's voice
{"role": "assistant", "content": "", "tool_calls": [ ... ]}

# our answer to that request
{"role": "tool", "tool_call_id": "call_mock_1", "content": "5"}
```

The instinct is to append only the second one. You have the result, the result
is the new information, so you push the result and move on. That instinct is
wrong, and it is wrong for a reason worth understanding rather than
memorising.

### A tool result is meaningless on its own

Imagine reading only the second message. Here is the whole conversation as the
model would receive it if you skipped the first.

```json
[
  {"role": "user", "content": "What is 2 plus 3?"},
  {"role": "tool", "tool_call_id": "call_mock_1", "content": "5"}
]
```

Now put yourself in the model's position. You see a question. Then you see a
bare `5` labelled as the result of something, referring to a call id you have
never encountered. Five what? The result of which function? With which
arguments? Did somebody add, or multiply, or roll a five sided dice?

The message says it is a response, but there is no request anywhere in the
transcript for it to be a response to. The `tool_call_id` points at nothing.
It is a reply to an email that was never sent.

The assistant message carrying `tool_calls` is the request. It is the only
record in the conversation of what was asked, of which function, and with what
arguments. Delete it and the result loses all of its meaning, because the
meaning was never in the number. It was in the pairing.

### The API does not merely dislike this, it rejects it

This is not a quality issue where the model gives a vaguer answer. The request
fails outright. The rule is part of the message format, and providers validate
it before any generation happens.

If you skip the assistant message, `complete` posts a body like the one above
and the endpoint replies with HTTP 400 and a body that looks like this.

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

Because `llm.py` calls `response.raise_for_status()`, that arrives in your
terminal as an exception rather than as JSON.

```text
Traceback (most recent call last):
  File "agent.py", line 54, in <module>
    print(run("What is 2 plus 3?"))
  File "agent.py", line 21, in run
    text, calls = complete(messages, tools.SCHEMAS)
  File "llm.py", line 29, in complete
    response.raise_for_status()
httpx.HTTPStatusError: Client error '400 Bad Request' for url 'http://localhost:11434/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400
```

Two things about that traceback are worth noting, because they will save you
time later.

The error surfaces inside `llm.py`, on the line that checks the status code.
Your bug is in `agent.py`, in the append you did not write. The traceback
points at the messenger. This is normal with HTTP APIs and it is why reading
the response body matters more than reading the stack.

The exact wording varies by provider. Some say the tool message must follow an
assistant message with tool calls. Some name the offending index, as this one
does with `messages.[1].role`. Some complain that a `tool_call_id` was not
found. They are all the same rule. If you see the words `tool` and `tool_calls`
in a 400 response, you have an unpaired message.

### The mirror image of the same rule

The rule cuts both ways, and the other direction bites too. If you append an
assistant message containing `tool_calls` and then do not append a `tool`
message for every id in it, the next request is also invalid. Ask two tool
calls, answer one, and you get a 400 naming the id you left hanging.

State the rule once, in the form you should keep.

> Every tool call needs its result, and every tool result needs its call. They
> travel together or the request is rejected.

Look at `agent.py` with that in mind and you can see the invariant being
maintained. The assistant message is appended once, before the tool loop
starts. Then the `for` loop appends exactly one `tool` message per call, using
`call["id"]` as the `tool_call_id`. By the time the loop body ends, every id in
the assistant message has a matching answer, and the history is valid for the
next request.

### Why this comes back to bite people in part 3

Right now the conversation is tiny. Two messages become four, four become six,
and nothing ever gets removed. That works until it does not, because every
model has a context window, a hard cap on how much text one request may
contain. A long running agent will hit it.

The obvious fix is to drop old messages. Keep the first user message, keep the
last handful, throw away the middle. It is the first thing everybody tries, and
it breaks agents in a way that is genuinely confusing to debug.

You can see why from here. Slice a conversation at an arbitrary point and there
is every chance your cut lands between an assistant message and its tool
results. The assistant message falls off the front of the window and its `tool`
messages stay. Now you have exactly the orphan from the start of this section,
except you did not write it deliberately, and the agent that worked perfectly
for twenty turns starts throwing 400 errors on turn twenty one.

The correct approach is to treat a tool call and its results as one indivisible
unit when trimming, and to summarise old sections rather than slicing them.
That is a chapter of its own. It is the context management lesson in part 3,
and when you get there the pairing rule you just learned is the reason the
chapter exists.

## 5. Why max_turns is not optional

Look at the loop header in `agent.py`.

```python
for _ in range(max_turns):
```

and at the line after the loop.

```python
raise RuntimeError(f"agent stopped after max turns ({max_turns})")
```

A beginner reads a `while True` as the natural shape here, since we want to run
until the model answers in words. Do not write that. Here is what happens when
you do.

### The runaway loop

Models get stuck. Not occasionally, routinely, and in a particular way. The
model asks for a tool. The tool fails or returns something the model did not
expect. The model tries again. It fails again. The model tries a third time
with the argument spelled slightly differently. And so on, forever.

```text
[calling roll_dice with {'sides': 'six'}]
[roll_dice returned Error: TypeError: randint() argument must be int, not str]
[calling roll_dice with {'sides': 'six'}]
[roll_dice returned Error: TypeError: randint() argument must be int, not str]
[calling roll_dice with {'sides': '6'}]
[roll_dice returned Error: TypeError: randint() argument must be int, not str]
[calling roll_dice with {'sides': 'six'}]
...
```

Nothing in that trace is a crash. Every line is a successful HTTP request and a
successful tool dispatch. The program is working exactly as written. It will
keep working exactly as written until you notice and press Ctrl-C, and if you
started it and went to lunch, that is two hours of requests.

### This costs real money

An infinite loop in ordinary code costs you a hot CPU. An infinite loop in an
agent costs you money, because every pass makes a paid API call.

Worse, the cost of each pass grows. The conversation gets longer every turn,
you resend the entire history every time, and providers charge by token. Pass
one sends a short message list. Pass fifty sends fifty rounds of accumulated
tool calls and error strings. So the spend per turn climbs while the loop makes
no progress at all. This pattern has produced a lot of memorable invoices, and
the people who received them were mostly running code that looked correct.

The `for` over `range(max_turns)` makes the worst case bounded and knowable
before you press enter. Ten turns is ten model calls. You can put a number on
the damage, and the number is small.

Notice also that we raise rather than return. Hitting the cap is not an answer.
Returning whatever text happened to be lying around would let a failure look
like a success to whatever called `run`, and a silent wrong answer is much
worse than a loud stop.

### Now the honest part, a turn cap is a blunt instrument

A turn cap prevents unlimited damage. It does not prevent the damage.

Look again at that dice trace. With `max_turns=10` the program stops after ten
passes instead of never. But it still made ten pointless model calls, still
paid for ten growing requests, still took ten round trips of wall clock time,
and still ended with a `RuntimeError` and no answer for the user. The cap
turned an unbounded failure into a bounded one. It did not turn a failure into
a success, and it did not notice anything was wrong.

That is the flaw. A turn cap counts. It does not think. It cannot tell the
difference between an agent doing ten pieces of genuine work and an agent
repeating the same broken call ten times, because from `range`'s point of view
those are identical. A model can burn the entire budget producing slightly
different versions of one failing call, and the cap will let it, right up to
the last one.

What production harnesses do instead is watch for the thing the cap cannot
see, which is lack of progress.

- **Repeated call detection.** Hash the tool name together with its arguments.
  If the identical call appears twice with the identical result, stop, or feed
  the model an explicit message telling it that it already tried this and got
  that, which frequently unsticks it.
- **Consecutive error counting.** Cap the number of failures in a row for one
  tool, separately from the total turn count. Three strikes on `read_file` is a
  broken path, not bad luck.
- **A budget rather than a turn count.** Track tokens spent or money spent or
  seconds elapsed, since those are the resources you actually care about. A
  turn is a poor proxy for any of them.
- **Escalating to a human.** When progress stalls, stop and ask. Cheaper than
  another ten turns and usually faster.

All of that belongs in part 3, in the chapter on reliability and control. It
does not belong in `agent.py` today, because thirty lines you can hold in your
head are worth more right now than a robust loop you cannot. Keep the cap,
understand that it is a fuse and not a diagnosis, and know that better tools
are coming.

## 6. Writing agent.py line by line

Here is the whole file, with its docstring shortened. Read it once end to
end, then read the walkthrough.

```python
"""The agent loop."""
import json

import tools
from llm import complete


def run(user_input, max_turns=10):
    """Run the agent until it produces a final answer. Returns the answer."""
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete(messages, tools.SCHEMAS)

        if not calls:
            return text

        messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"]),
                        },
                    }
                    for call in calls
                ],
            }
        )

        for call in calls:
            print(f"[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")


if __name__ == "__main__":
    print(run("What is 2 plus 3?"))
```

Thirty lines of body. Now piece by piece.

### The imports

```python
import json

import tools
from llm import complete
```

`json` is here for one reason, which is `json.dumps` further down. That call
gets its own subsection because it deserves it.

`tools` and `complete` are the two files from lesson 03, unchanged. This is a
good moment to appreciate the layering. `llm.py` knows about HTTP and knows
nothing about tools running. `tools.py` knows about running functions and
knows nothing about HTTP. `agent.py` knows about neither and only orchestrates.
Each file can be read on its own, and each could be swapped for a different
implementation without touching the other two.

### The signature and the starting state

```python
def run(user_input, max_turns=10):
    """Run the agent until it produces a final answer. Returns the answer."""
    messages = [{"role": "user", "content": user_input}]
```

`run` takes a string and returns a string. That is the entire public interface
of your agent. Everything else is internal.

`max_turns=10` has a default so that callers do not have to think about it, and
is a parameter rather than a constant so that a caller who knows the task is
long can raise it. Section 5 is the argument for why it exists.

`messages` starts as a one item list holding the user's question. It is a plain
Python list, it lives on the stack of this function, and it is the agent's
entire memory. When `run` returns, that memory is discarded. Persisting it
across calls is a later lesson.

There is no system message here. Lesson 10 adds one, and it changes agent
behaviour considerably. For now the model gets the question and the tool
schemas and nothing else.

### The loop header

```python
    for _ in range(max_turns):
```

The underscore is the conventional Python name for a loop variable you do not
use. We only want the counting, not the count.

Using `for` rather than `while` means the limit is structural. There is no way
to accidentally skip the check, no counter to forget to increment, and no
`break` condition to get wrong. The loop cannot run more than `max_turns`
times, and you can see that by looking at one line.

### Step one, ask the model

```python
        text, calls = complete(messages, tools.SCHEMAS)
```

One line for the entire HTTP exchange. This is the payoff for having written
`llm.py` first. It builds the request body, adds the bearer header, posts,
checks the status, parses the response, and hands back a tuple of text and a
list of tool call dictionaries with the arguments already turned into real
Python dicts by `json.loads`.

Note that `tools.SCHEMAS` is passed on every single pass through the loop.
There is no registration step and no server side memory. If you sent the
schemas on the first request and left them off the second, the model would
simply stop knowing that any tools exist, and it would answer from guesswork.
The full tool list travels with every request, exactly like the full message
history does.

### The exit condition

```python
        if not calls:
            return text
```

This is the stop rule from section 3, in code. An empty list of tool calls
means the model answered in words, so the words are the answer and we hand them
back.

Checking `if not calls` is deliberately chosen over checking
`finish_reason == "stop"`. Providers vary in how they set `finish_reason`, and
some local servers set it inconsistently. The presence or absence of tool calls
is the thing we actually care about, so we test that directly.

One consequence worth noticing. If the model answers in words on the very first
pass, the loop body runs once, `calls` is empty, and `run` returns without ever
calling a tool. An agent asked a question it can answer from memory behaves
exactly like a chat program, which is correct.

### Step three, part one, putting the model's request back

```python
        messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [ ... ],
            }
        )
```

Section 4 is the full argument for this block. In short, we are writing the
model's own request into the transcript so that the results we are about to
append have something to refer to.

Two details in the message.

`"role": "assistant"` because this message is the model speaking. We are not
inventing anything. We are transcribing what came back over HTTP into the
history so the next request contains it.

`"content": text` rather than an empty string. On a pure tool call turn `text`
is usually empty, and `llm.py` already normalised a `null` content into `""`.
But some models write a sentence and request a tool in the same turn, something
like "Let me calculate that for you" alongside the `add` call. Passing `text`
through preserves that sentence. Throwing it away would quietly lose part of
the model's own reasoning from the transcript.

Notice this append happens **before** any tool runs. That ordering is
intentional. The request is recorded first, then the answers follow it, which
is both the order the API requires and the order the conversation actually
happened in.

### The json.dumps, and why it is the mirror of lesson 03

```python
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"]),
                        },
                    }
                    for call in calls
                ],
```

Lesson 03 had a section called "The JSON string that surprises everyone". This
is that surprise coming back the other way, and it surprises people a second
time.

Recall the shape. Over the wire, `arguments` is not a JSON object. It is a
**string containing JSON**.

```json
{
  "id": "call_mock_1",
  "type": "function",
  "function": {
    "name": "add",
    "arguments": "{\"a\": 2, \"b\": 3}"
  }
}
```

In lesson 03 we called `json.loads` on that string to get a usable Python
dictionary, because `**arguments` needs a mapping.

```python
"arguments": json.loads(raw["function"]["arguments"] or "{}")
```

So by the time `agent.py` sees a call, `call["arguments"]` is a real dict like
`{"a": 2, "b": 3}`. Convenient for us. Wrong for the wire. To put that call
back into the message history in the format the API defined, it has to become a
string again.

```python
"arguments": json.dumps(call["arguments"])
```

`json.loads` on the way in, `json.dumps` on the way out. String to dict, then
dict back to string. Two functions whose names differ by one letter, doing
exactly opposite jobs, five lines apart in a codebase.

Why go through the round trip at all rather than stashing the original string
and reusing it? Because the parsed dictionary is what the rest of the program
needs, and keeping a second copy of the raw text purely for replay means
carrying two representations of one value and keeping them in sync. Re-encoding
is one cheap call and there is only ever one source of truth. It also makes the
door open for something you will want later, which is inspecting or modifying
arguments before they are recorded. Redacting a secret out of a logged tool
call, for instance, is easy when you hold a dict and awkward when you hold a
string.

Forget the `json.dumps` and the failure is not subtle, which is a mercy. The
request body contains an object where the format promises a string, and the
provider rejects it.

```text
httpx.HTTPStatusError: Client error '400 Bad Request' for url '.../chat/completions'
```

with a body along the lines of

```json
{
  "error": {
    "message": "Invalid type for 'messages[1].tool_calls[0].function.arguments': expected a string, but got an object instead.",
    "type": "invalid_request_error",
    "param": "messages[1].tool_calls[0].function.arguments",
    "code": "invalid_type"
  }
}
```

The other two fields are simple. `"type": "function"` is the same boilerplate
discriminator you wrote in the schemas. `call["id"]` is the id lesson 03 told
you to keep even though nothing used it yet. This is where it starts being
used, and the next block is where it earns its place.

### Step two and step three, part two, running the tools and recording results

```python
        for call in calls:
            print(f"[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
```

The inner loop. Four lines, and it is where the program touches the world.

The two `print` calls are not decoration. They are the agent's trace, and they
are the only window you have into what it is doing. When an agent behaves
strangely, this output is the first thing you read, because it shows you the
exact arguments the model chose and the exact string it got back. Print
generously in agents. The interesting failures are all in the gap between what
you assumed the model asked for and what it actually asked for.

`tools.run` is unchanged from lesson 03. It looks the name up in `FUNCTIONS`,
returns an error string for a name it does not recognise, calls the function
with `**arguments`, wraps everything in a `try`, and converts the result with
`str`. That broad `except Exception` is doing quiet, important work here. A
tool that raises inside this loop would kill the agent mid turn. A tool that
returns `"Error: TypeError: ..."` becomes a `tool` message like any other, goes
back to the model, and gives the model a chance to fix its own mistake. Lesson
03 promised that this would matter in lesson 04. This is the line where it
matters.

The append is the second half of the pairing rule. `"role": "tool"` is a
message role you have not used before, and it exists purely to carry tool
output. `tool_call_id` is copied from `call["id"]`, which is how the model
knows which of its requests this answers. `content` is the result as a string,
because messages carry text, which is why `tools.run` calls `str()` on
everything it returns.

Because this inner loop runs once per call, every id in the assistant message
gets exactly one `tool` message. The history is valid again by the time the
loop body ends.

### The exit that is not an answer

```python
    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
```

Reached only when the `for` completes without returning, which means the model
asked for a tool on every single pass and never produced a final answer.
Section 5 is the argument for raising instead of returning something plausible.

### The entry point

```python
if __name__ == "__main__":
    print(run("What is 2 plus 3?"))
```

So you can run the file directly and watch it work.

## 7. Running it and reading the trace

Set the environment and run from inside the lesson folder.

```bash
cd lessons/04-agent-loop
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen2.5:7b
export AGENTPATH_API_KEY=
python agent.py
```

On Windows PowerShell.

```powershell
cd lessons\04-agent-loop
$env:AGENTPATH_BASE_URL = "http://localhost:11434/v1"
$env:AGENTPATH_MODEL = "qwen2.5:7b"
python agent.py
```

Here is the output.

```text
[calling add with {'a': 2, 'b': 3}]
[add returned 5]
2 plus 3 is 5.
```

Three lines. Stare at them, because a great deal happened.

Line one is the model choosing. Nowhere in `agent.py` does the string
`"add"` appear, and nowhere does the number 2 or 3. The model read a sentence
in English, read a JSON Schema it had never seen before this HTTP call, decided
those two things were related, and produced a structured request naming the
function and filling in both arguments. Then our Python printed what it asked
for.

Line two is our program acting. `tools.run` looked `add` up in a dictionary
we control and called it with keyword arguments. The number 5 was computed by
CPython on your machine, not by a model on somebody's GPU.

Line three is the payoff, and it is the thing lesson 03 could not do. The
model wrote a sentence containing a fact it did not know one second earlier.
That number came from our process, went out over HTTP inside a `tool` message,
and came back embedded in prose.

### The two requests, in full

The trace hides the HTTP. Here it is.

The first request body is what lesson 03 already sent. One user message plus
the schemas. It is long because of the schemas, so here it is with the tool
list abbreviated.

```json
{
  "model": "mock",
  "messages": [
    {"role": "user", "content": "What is 2 plus 3?"}
  ],
  "tools": [ "... the add and roll_dice schemas, unchanged ..." ]
}
```

The response asks for the tool.

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_mock_1",
            "type": "function",
            "function": {
              "name": "add",
              "arguments": "{\"a\": 2, \"b\": 3}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

Now the second request, which is the new thing this lesson built. This is the
`messages` list after both appends, and it is worth reading carefully because
it is the exact structure section 4 was arguing about.

```json
{
  "model": "mock",
  "messages": [
    {"role": "user", "content": "What is 2 plus 3?"},
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "id": "call_mock_1",
          "type": "function",
          "function": {
            "name": "add",
            "arguments": "{\"a\": 2, \"b\": 3}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_mock_1",
      "content": "5"
    }
  ],
  "tools": [ "... the same schemas, sent again ..." ]
}
```

Four things to read in that body.

The conversation grew from one message to three. The user turn is still there
unchanged, because we resend everything every time.

The assistant message and the tool message are a matched pair. `call_mock_1`
appears twice, once as `id` and once as `tool_call_id`. That is the pairing
rule holding.

The `arguments` field is a string again, complete with escaped quotes. That is
`json.dumps` doing its job.

The schemas were sent a second time. The model needs them on this pass too,
because it may want another tool.

And the response to that second request has no tool calls in it.

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "2 plus 3 is 5."
      },
      "finish_reason": "stop"
    }
  ]
}
```

`complete` parses that into `("2 plus 3 is 5.", [])`, the `if not calls` check
fires, and `run` returns the string. The loop body ran once.

### Running the check

`check.py` is the automated version of the same run.

```python
"""Check that lesson 04 works."""
import sys

from agent import run

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    answer = run(PROMPT)
    if "5" not in answer:
        print(f"FAIL the final answer did not mention the tool result. Got {answer!r}")
        sys.exit(1)
    print(f"OK the agent ran the tool and answered with {answer.strip()[:60]}")


if __name__ == "__main__":
    main()
```

Compare it to lesson 03's check and notice how much shorter it got. Lesson 03
imported `tools`, called `complete`, inspected `calls[0]`, verified the name,
verified the arguments, and ran the tool by hand. This one imports `run`, calls
it once, and looks at the answer.

That shrinkage is the lesson. All of that machinery moved inside `agent.py`,
which is what it means to have built an agent. The caller now asks a question
and gets an answer, and the tool calling has become an implementation detail.

The assertion is also different in kind. Lesson 03 checked that the model
*asked* for the right thing. Lesson 04 checks that the tool's result *reached*
the final answer, which is the thing that was impossible before. The bracketed
`[[tool:add:...]]` directive is the same fake server marker explained in lesson
03 section 9, and it is ignored by a real model.

```bash
python check.py
```

```text
[calling add with {'a': 2, 'b': 3}]
[add returned 5]
OK the agent ran the tool and answered with The tool returned 5.
```

The trace lines appear because `agent.py` prints them, and the `OK` line comes
from `check.py`.

Run the whole course against the deterministic server from the repository root
with this.

```bash
python ci/run_lessons.py
```

### Try changing the question

The single best way to feel what you have built is to edit the last line of
`agent.py` and rerun against a real model.

```python
print(run("Roll a six sided dice and add 10 to whatever it shows."))
```

```text
[calling roll_dice with {'sides': 6}]
[roll_dice returned 4]
[calling add with {'a': 4, 'b': 10}]
[add returned 14]
You rolled a 4, and 4 plus 10 is 14.
```

The loop body ran twice, and nobody told it to. The second tool call contains
the number 4, which did not exist when the first request was sent. That is the
argument from section 2 happening in front of you, and it is the moment where a
program stops feeling like a script and starts feeling like an agent.

## 8. Why the tools run one after another rather than all at once

Look at the inner loop again.

```python
        for call in calls:
            result = tools.run(call["name"], call["arguments"])
            messages.append(...)
```

`calls` is a list because a model can ask for several tools in a single turn.
Ask "roll a six sided dice and a twenty sided dice" and a capable model will
often produce two `roll_dice` calls in one response, since neither depends on
the other.

```json
"tool_calls": [
  {"id": "call_1", "type": "function",
   "function": {"name": "roll_dice", "arguments": "{\"sides\": 6}"}},
  {"id": "call_2", "type": "function",
   "function": {"name": "roll_dice", "arguments": "{\"sides\": 20}"}}
]
```

Our loop runs `call_1`, waits for it to finish, then runs `call_2`, and appends
two `tool` messages in order. Strictly one after the other.

### Running them at the same time is a real optimisation

For independent tools this is genuinely wasteful, and the waste is large when
tools are slow. Sequential execution costs the sum of the durations. Concurrent
execution costs the maximum.

```text
three file reads at 200ms each
  sequential   200 + 200 + 200  =  600ms
  concurrent   max(200,200,200) =  200ms

three API calls at 2s each
  sequential   6s
  concurrent   2s
```

Our tools take microseconds, so the difference is invisible here. Once tools
are web requests, database queries, or shell commands, the difference is most
of the agent's wall clock time. Production harnesses do exactly this. Claude
Code runs independent reads and searches concurrently, and so do the major
frameworks. In Python you would reach for `asyncio.gather` or a
`ThreadPoolExecutor`, collect the results, and then append the `tool` messages
in the original order so the ids still line up.

### Why we are not doing it here

Two reasons, and the second is the interesting one.

It hides the trace. Concurrent output interleaves. Your careful
`[calling ...]` and `[returned ...]` lines arrive out of order, and the clean
sequential story you just read in section 7 becomes a jumble. While you are
learning the shape of the loop, being able to read the trace top to bottom is
worth more than the milliseconds.

Parallel tools create conflicts. This is the real reason, and it is not
about performance at all. Concurrency is safe when operations are independent
and unsafe when they are not, and the model asking for two tools in one turn is
no guarantee whatsoever that they are independent.

Consider the failure shapes.

- Two tools write to the same file. Run them at once and whichever finishes
  last wins, silently, and which one that is varies run to run.
- One tool writes a file and another reads it. Sequentially the reader sees the
  new content. Concurrently it sees the old content, the new content, or a half
  written file, depending on timing.
- Two tools each want the same limited resource, a database connection or a
  rate limited API quota, and now you have contention or a 429 that would never
  have happened one at a time.
- A tool with a confirmation prompt runs beside another that also wants the
  terminal, and the user is asked two questions at once with no way to tell
  which is which.

Every one of those is a race condition, and race conditions are the class of
bug that appears once in fifty runs, never reproduces while you are watching,
and cannot be found by reading the code. Introducing that in the lesson where
you are also meeting the pairing rule and the turn cap for the first time would
be a bad trade.

The real answer is not to pick sequential or parallel globally. It is to know
which tools are safe to overlap, run those together, and force the rest into
order. A read only tool can generally run beside anything. A tool that mutates
shared state generally cannot. That classification, and the scheduling that
follows from it, is part 4, which covers concurrency along with parallel sub
agents.

For today, sequential is correct because it is obviously correct, and obviously
correct is what you want under a loop you are still learning to read.

## 9. What you cannot do yet

You have an agent. Now run it against a real model, a large one, on a question
that needs a few steps, and watch what your terminal actually does.

```bash
python agent.py
```

```text
_
```

Nothing. A blinking cursor.

Wait. Still nothing. Several seconds pass. Then, all at once.

```text
[calling roll_dice with {'sides': 6}]
[roll_dice returned 4]
[calling add with {'a': 4, 'b': 10}]
[add returned 14]
You rolled a 4, and 4 plus 10 is 14.
```

Every line arrived in the same instant, after a silence long enough that you
were starting to wonder whether the program had hung.

Nothing is broken. `complete` posts a request and blocks until the entire
response body has arrived. The model generated that final sentence one token at
a time over several seconds, and our code sat waiting for the last one before
it knew anything at all. `httpx.post` returns once, with everything, and only
then does `print` run.

That is fine for a script. It is unusable for anything a person watches.

- On a large hosted model a multi step answer can take fifteen seconds. That is
  fifteen seconds of blank terminal.
- On a local model on a laptop it can be a minute or more.
- The user cannot tell a slow answer from a crash, so they press Ctrl-C, and
  now you have both a bad experience and a wasted paid request.
- You cannot see the model changing its mind or heading in a useless direction
  until it has finished heading there and you have paid for all of it.

Compare it to any chat interface you have used. Text appears word by word as it
is produced. That is not a cosmetic flourish. It is the difference between a
program that feels alive and a program that feels hung, and it costs nothing
extra, because the tokens were already being produced one at a time. We are
simply throwing away the opportunity to show them.

The fix is streaming. Instead of asking the endpoint for one complete response,
you ask it to send the tokens as they are generated, over a long lived HTTP
response, and you print each fragment as it arrives. It changes `llm.py`
considerably, because a streamed tool call arrives in fragments too and has to
be reassembled before you can dispatch it. It does not change `agent.py` at
all, because the four steps of the loop are the same four steps whether the
response arrived in one piece or a thousand.

That is lesson 05.
