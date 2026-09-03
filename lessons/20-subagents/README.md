[อ่านภาษาไทย](README.th.md)

# Lesson 20. Subagents

Lesson 19 gave the agent tools it did not write. This chapter takes something
away from it instead, and the thing it takes away is work.

Here is what is in the folder and where each file came from.

```text
lessons/20-subagents/
  subagent.py         new. sixty one lines, and sixteen of them are the docstring
  check.py            new. six claims, and the last one is a warning
  agent.py            identical to lesson 19
    tools.py            identical to lesson 19
  grep_worker.py      identical to lesson 19

  prompt.py           identical to lesson 19
  permissions.py      identical to lesson 19
  session.py          identical to lesson 19
  context.py          identical to lesson 19
  providers.py        identical to lesson 19
  usage.py            identical to lesson 19
  retrieval.py        identical to lesson 19
  retry.py            identical to lesson 19
  cancel.py           identical to lesson 19
  main.py             identical to lesson 19
  mcp.py              identical to lesson 19
  mock_mcp_server.py  identical to lesson 19
  README.md           this file
```

Every folder from lesson 19 onward carries the whole course, so a chapter can
be opened on its own and run without first copying files in from a neighbour.
That is why `mcp.py`, `mock_mcp_server.py`, and `main.py` are sitting here even
though this chapter never mentions them.

Fifteen of the seventeen Python files are byte for byte what they were last
chapter. That is checkable rather than assertable.

```bash
cd lessons
for f in agent.py tools.py permissions.py context.py providers.py; do
  diff -qs 19-mcp-client/$f 20-subagents/$f
done
```

```text
Files 19-mcp-client/agent.py and 20-subagents/agent.py are identical
Files 19-mcp-client/tools.py and 20-subagents/tools.py are identical
Files 19-mcp-client/permissions.py and 20-subagents/permissions.py are identical
Files 19-mcp-client/context.py and 20-subagents/context.py are identical
Files 19-mcp-client/providers.py and 20-subagents/providers.py are identical
```

Hold on to that result. Section 3 is entirely about what it means, and it means
more than it looks like it means.

## 1. The problem left over from lesson 19

Say what the problem is in one sentence first, then make it concrete, because
the abstract version of this complaint is so common that it has stopped meaning
anything.

**One agent doing everything in one conversation fills its own context, and the
thing that fills it fastest is the work it does not need to remember.**

Now the concrete shape. Give the agent from lesson 18 a real question. Something
like this, which is an ordinary Tuesday afternoon question and not a stress test.

```text
Where does the retry delay come from, and is it configurable?
```

Watch what it does. It greps for `retry`, gets nine hits across six files, reads
`retry.py`, reads the two call sites, greps for `sleep`, finds a fixture in a
check that shadows the real one, reads that check to rule it out, reads
`providers.py` because that is where the wrapping was supposed to go, greps for
`attempts`, and reads three more files to see whether anything passes it. Call
it fifteen file reads and a handful of searches. Then it answers in two
sentences.

Those two sentences are what you wanted. Everything above them is scaffolding
that existed only to produce them.

But look at where the scaffolding now lives. Lesson 04 established the shape of
a turn and nothing since has changed it. Every tool result is appended to
`messages` as a message, and `messages` is resent in full on every subsequent
request. So the fifteen file contents are not a thing that happened and
finished. They are now permanent residents of the conversation, re-uploaded on
every turn for the rest of the run, competing for attention with everything that
comes after them.

Nothing in part 3 fixes this, and it is worth being precise about why, because
each piece looks like it should.

`fit_to_budget` from lesson 14 does not fix it. It is triggered by the problem
rather than being a solution to it, and when it fires it drops the oldest blocks
first. The oldest blocks are your original question, the first file it read, and
the reason it chose this approach. So fifteen file contents that were needed for
ninety seconds evict the instruction that has to survive for the whole run. That
is not a bug in the trimmer. The trimmer was told to make room and it made room,
and the only thing it knows about relevance is position.

`Usage` from lesson 15 does not fix it either. It tells you afterwards that the
prompt token count climbed every turn, which is true and useless, because
knowing what a thing cost is not the same as having somewhere else to put it.

And lesson 19 made it measurably worse rather than better. Connect four MCP
servers and forty tool schemas are serialised into every single request before
the conversation even starts. The window was already the scarce resource, and
the chapter that arrived just before this one spent more of it.

So there are two different pressures on the same fixed budget. Tool schemas,
which are charged per request and are lesson 19's problem, and tool results,
which accumulate and are this chapter's. The second one is worse, because
schemas at least stay a constant size.

Here is the shape of the failure this produces, and it is nastier than a crash.
The agent does not fall over. It gets slowly stupider across a long run,
forgetting the earliest and most load bearing parts of its own reasoning, while
every log line looks fine and no exception is ever raised. You find out because
the answer on turn thirty contradicts the plan from turn four.

The real problem underneath all of it is that one conversation is being asked to
hold a task that does not fit in one conversation. You cannot trim your way out
of that, and a bigger window only moves the wall.

## 2. What a subagent is, and what it is not

Start with what it is not, because almost everything written about this word
gets it wrong in the same direction.

A subagent is **not** a new mechanism. It is not a framework feature. It is not
a different or smaller or specialised kind of model. There is no orchestration
layer here, no supervisor class, no agent registry, and nothing in `agent.py`
knows that any of this exists.

Here is what it actually is, and the module docstring says it in the first two
sentences.

```python
"""Turning a whole agent into a single tool the parent can call.

There is no new machinery here. A subagent is a tool whose implementation
happens to run another agent. The parent sees a tool with a name and a
description, exactly like read_file, and the loop does not change at all.
That is the point worth noticing rather than the code.
"""
```

**A subagent is a tool whose implementation happens to run another agent.**

That is the whole definition and every consequence in this chapter follows from
it. Since lesson 03, a tool has been two things. A JSON schema with a name, a
description and a parameter list, which is what the model sees, and a Python
function, which is what actually runs. Nothing anywhere requires that the
function be small, or fast, or free of network calls. `run_shell` starts an
entire operating system process. `search_notes` from lesson 16 builds an
embedding and scores a vector index. The MCP tools from lesson 19 talk to a
different program over a pipe.

So the function is allowed to run an agent. Look at what `run_subagent` is.

```python
    def run_subagent(task):
        try:
            answer, _ = build_child()(task)
        except Exception as error:
            return f"Error: the subagent failed, {type(error).__name__}: {error}"
        return answer or "The subagent finished without saying anything."
```

Three meaningful lines. Build a child, call it with a string, return the string
it produced. And here is its schema, which is the half the model sees.

```python
    schema = {
        "type": "function",
        "function": {
            "name": "run_subagent",
            "description": DEFAULT_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The complete job, written so it makes sense on its own",
                    }
                },
                "required": ["task"],
            },
        },
    }
```

Compare that against the schema for `read_file` in `tools.py` and there is no
structural difference at all. A name, a description, one required string
parameter. The model choosing between them is making one kind of choice, not
two, and it has no way of knowing that one of these opens a file and the other
starts a conversation with a language model.

Registration is two lines, and they are the two lines every tool has used since
lesson 03.

```python
    run_subagent, schema = run_subagent_factory(build_child)
    tools.SCHEMAS.append(schema)
    tools.FUNCTIONS["run_subagent"] = run_subagent
```

`tools.SCHEMAS` is the list serialised into the request. `tools.FUNCTIONS` is
the dictionary `tools.run` looks a name up in. That is the same registry
`register_mcp` extended in lesson 19 and the same one `read_file` has lived in
since lesson 07.

Why frame it this way rather than building a real orchestration layer? Because
of what the framing buys, which is everything that already works. The subagent
call goes through `Permissions` like any other call, so it can be gated,
refused, or remembered. It is written to the session file as an ordinary
assistant message and an ordinary tool result, so a run that used one is
debuggable by opening a text file. It counts toward `max_turns`. It is subject
to the repeat detection from lesson 15. It appears in `usage`. None of that was
designed for subagents. All of it applies to subagents because a subagent is
shaped like a tool, and a special mechanism would have had to earn every one of
those properties separately.

## 3. Why that matters more than the code

Go back to the `diff -qs` output at the top of the file and read the first line
again.

```text
Files 19-mcp-client/agent.py and 20-subagents/agent.py are identical
```

The agent can now start other agents, and the agent loop did not change. Not a
parameter, not a branch, not a line.

This is the fourth time in this course that something significant has arrived
without the loop noticing, and the list is worth having in one place because the
pattern is the argument.

| What arrived | Lessons | What happened to `agent.py` |
| --- | --- | --- |
| Seven real tools. Files, shell, glob, grep | 07, 08, 09 | identical to lesson 06 |
| Retrieval, with an embedder and a vector index | 16 | identical to lesson 15 |
| Tools from another process, over MCP | 19 | identical to lesson 18 |
| An agent that can start other agents | 20 | identical to lesson 19 |

Four times. Each of those was, at the time, the largest new capability in its
part of the course. Retrieval is the one people build as a special system with
hooks in the middle of everything. MCP is a network protocol with a handshake
and a lifecycle. Subagents are the thing every framework gives a whole
subsystem to. All four went in as a name in a dictionary.

Now the other half of the pattern, from lesson 18's table. Permissions changed
the loop. Sessions changed the loop. Trimming changed the loop. Token counting
and the doom loop guard changed the loop. Cancellation changed the loop. Five
subsystems, five changes.

The rule is exact and it has held for fourteen chapters. **Tools never touch the
loop. Subsystems always do.** Which means the useful question to ask about any
new capability is not how big it is, it is which side of that line it falls on,
because a capability that can be expressed as a tool costs you a file and a
capability that cannot costs you a parameter on the most dangerous function in
the program.

Why this is worth a section of its own rather than a sentence. Picture the
version of this chapter where `agent.py` grows a `subagents` parameter, a branch
that checks whether the requested call is a delegation, a separate dispatch path
for children, and a depth counter to stop infinite recursion. Every one of those
is a reasonable thing to write. Together they mean the loop now knows what a
subagent is, which means the loop has to be edited again when subagents change,
which means the file that permissions, sessions, trimming, counting and
cancellation all pass through has a sixth reason to be opened.

The depth counter is the interesting one, because it is the one you would
genuinely want, and the framing gives it to you for free anyway. A child built
by `build_child` gets whatever tools the builder registers. Do not register
`run_subagent` for the child and a child cannot spawn a grandchild, ever, with
no counter and no check. The limit is expressed by what is in a dictionary
rather than by a rule in the loop.

That is what a boundary cut in the right place buys. Not tidiness. The ability
to add the fourth major capability the same way you added the first.

## 4. Context isolation, which is the entire point

Everything so far has been about shape. This section is about the number, and
the number is the reason to do any of it.

`check.py` prints it directly.

```text
OK the child had a 4 message conversation of its own
Hello from the mock server.
OK none of it landed in the parent, which kept 2 messages
```

Take those apart, because both numbers are exact and both are checked.

The child ran this task.

```python
WRITE = 'Write it. [[tool:write_file:{"path": "made-by-child.txt", "content": "hello"}]]'
```

Its conversation is four messages. The user message carrying the task. An
assistant message carrying the tool call. A tool result saying the file was
written. And a final assistant message with the answer. That is a complete
agent run with a real tool call in the middle of it, and here is the assertion
that it happened.

```python
    if not children or len(children[0]) < 4:
        fail(f"the child conversation looks wrong. Got {children!r}")
```

The parent then does something else entirely.

```python
    parent_answer, parent_messages = run(
        provider(), "Say hello.", permissions=Permissions(auto_approve=True)
    )
    if any("made-by-child" in (m.get("content") or "") for m in parent_messages):
        fail("the child conversation leaked into the parent")
```

Two messages. One user, one assistant. The check does not merely count them, it
searches every message for the string `made-by-child`, which is the name of the
file the child wrote, and fails if it appears anywhere. Counting alone would
pass if the two lists happened to be the same length while sharing a mutable
list underneath, which is a real way to get this wrong. Searching for the string
proves the child's work is genuinely absent rather than coincidentally
uncounted.

Four and two. Those two numbers are the chapter.

Now scale them back up to the retry question from section 1. Fifteen file reads
and a handful of searches happen inside the child, which means they land in the
child's `messages` list, which is a local variable inside a function call that
returns. When `run_subagent` returns, that list has nothing referring to it and
Python frees it. What reaches the parent is one string.

Say the consequence plainly. **The parent gets the conclusion and not the
investigation.** The parent's conversation grows by one assistant message
containing a tool call and one tool result containing two sentences. Without the
child it would have grown by fifteen file contents and nine grep results, all of
which would then be resent on every remaining turn of the run and all of which
would be candidates for the trimmer to evict something else to make room for.

Two things follow that are easy to miss.

The saving is not in tokens sent once, it is in tokens sent repeatedly. A file
read costs its own size once no matter who reads it. The difference is that a
file read by the parent is paid for again on every subsequent request for the
rest of the run, and a file read by the child is paid for only during the
child's own short life. On a forty turn run that is the difference between
paying for something once and paying for it thirty five times.

And the child is sharper than the parent would have been on the same job, for
the same reason. Its context contains one task and the evidence for that task,
with none of the earlier conversation, none of the dead ends from an unrelated
part of the work, and no competing instructions. A narrow question asked in a
clean context is a different question from a narrow question asked on turn
thirty of a long run.

## 5. Why build_child is a function rather than an agent

Look at the parameter name in the factory and notice what it is not.

```python
def run_subagent_factory(build_child):
    """Build the function the parent will call, plus its schema.

    build_child is a function returning a fresh agent rather than an agent
    itself. That is deliberate. A subagent that kept its history between
    calls would slowly accumulate the same clutter it exists to prevent, and
    the second call would start wherever the first one happened to stop.
    """
```

`build_child` is a factory. It is called inside `run_subagent`, once per
delegation, and the agent it returns is discarded when the call ends.

```python
            answer, _ = build_child()(task)
```

Read that line carefully because it does two things. `build_child()` makes a new
child. The `(task)` then runs it. A fresh one every single time.

The alternative is one line shorter and it is the obvious thing to write. Pass
in a child, keep it, call it whenever the parent delegates.

```python
def run_subagent_factory(child):          # the version that is wrong
    def run_subagent(task):
        answer, _ = child(task)           # same child, same conversation
        return answer
```

That reintroduces the exact problem the chapter exists to solve, one level down.
Delegate three investigations to a persistent child and its conversation now
holds all three. The third delegation is answered by an agent carrying the
transcript of the first two, and the child's context is filling up the same way
the parent's was. You would have moved the clutter rather than removed it, and
you would have added a second place for it to accumulate where nothing is
watching.

There is a second failure and it is worse, because it is not about size. **The
second call would start wherever the first one happened to stop.** A child that
just spent four turns concluding that the retry delay is hardcoded now receives
a completely unrelated task about the session format, with that conclusion
sitting above it as established fact. Models condition on what is in the window.
That is the entire mechanism. So the answer to the second question is now shaped
by the first, and there is no error, no warning, and no way to tell from the
outside. You get a plausible answer that was contaminated by a question nobody
asked.

The same argument produces a property worth naming. Every delegation is
independent of every other. Call the tool three times with the same task and you
get three runs that cannot influence each other, which is what makes the results
comparable and what makes a failed delegation safe to simply try again.
Lesson 21 needs this and could not be written without it, because running four
children at once over threads requires that no two of them share state.

Note also what the factory does not decide. It has no opinion about which
provider the child uses, what system prompt it gets, which tools it can reach,
or what its permission object allows. All of that lives in whatever `build_child`
the caller supplies, which in `check.py` is this.

```python
    def build_child():
        def child(task):
            answer, messages = run(
                provider(), task, permissions=Permissions(auto_approve=True)
            )
            children.append(messages)
            return answer, messages

        return child
```

A closure over `children` so the check can inspect what the child did, which is
only possible because the builder is supplied from outside. A real program would
put a cheaper model here, or a read only `Permissions`, or a narrower tool
registry, and `subagent.py` would not need to change for any of those. The
factory's whole contract is that you hand it something callable that returns a
fresh agent, in the same way `with_retries` from lesson 17 takes a callable and
has no opinion about what is inside it.

## 6. Writing the description for the parent

This is the part that is easiest to skip and most likely to be the reason a
subagent does not work. Here it is in full, exactly as it ships.

```python
DEFAULT_DESCRIPTION = (
    "Hand a self contained job to a separate agent and get back only its final "
    "answer. Use this for work that needs many steps of searching or reading, "
    "when you want the conclusion and not the whole investigation. Describe the "
    "job completely, because the other agent cannot see this conversation."
)
```

Four sentences, each doing a different job.

The first says what the tool does. Hand over a job, get back only the final
answer. The word `only` is load bearing. It tells the model not to expect a
transcript, so it does not write a task asking the child to show its work step
by step, which would defeat the purpose by pulling the investigation back into
the parent's context through the return value.

The second says when to reach for it. Work that needs many steps of
searching or reading. This is the sentence that has to compete with the
alternative, because the model is choosing between this tool and calling
`grep_files` itself, and calling `grep_files` itself is what it has done in
every previous chapter. A description that only says what a tool does leaves the
model to infer when, and a tool the model never selects is a tool that does not
exist. Lesson 09 made the same argument about search and lesson 16 made it about
`search_notes`. The description is not documentation, it is the only instruction
the model has about selection.

The third names the trade. The conclusion and not the whole investigation.
That is the cost stated honestly, and stating it lets the model make a real
choice rather than being pushed. If it needs the intermediate steps for what it
is doing next, it should not delegate, and this sentence is what tells it so.

The fourth is the one that cannot be left out. The other agent cannot see
this conversation.

Sit with why that sentence has to be there. From the model's side, every tool it
has ever called shares its context by default. `read_file` reads from the
workspace it was told about in its system prompt. `grep_files` searches the same
tree. When it calls `edit_file` with `old` text, that text came from something
it read earlier in this same conversation. Continuity is the background
assumption for every tool in the program.

`run_subagent` breaks that assumption and nothing about the schema signals it.
The parameter is a string called `task`. There is nothing in a string parameter
that says the reader of this string starts from nothing.

So a parent that is not told writes the task it would write for itself.

```text
task = "Find out where that delay comes from and check the other one too"
```

Every word of which is a reference to something the child cannot see. Which
delay. Which other one. The child receives that as its entire universe, has no
option to ask a clarifying question because there is nobody to ask, and produces
a plausible answer to a question it had to guess. **A parent that writes a vague
task gets a vague answer back**, and it gets it in the confident tone of a
finished investigation, which is worse than an error because it looks like a
result.

Told about the isolation, the parent writes this instead.

```text
task = "In retry.py, find where the delay between attempts is calculated,
        report whether the number is hardcoded or configurable, and name every
        file that passes an attempts or sleep argument to with_retries."
```

Self contained. Names the file, names the question, names what the answer should
contain.

The same requirement is repeated on the parameter itself rather than only in the
tool description.

```python
"description": "The complete job, written so it makes sense on its own",
```

Both places, deliberately. The tool description is read when the model is
deciding whether to call the tool. The parameter description is read when it is
deciding what to put in the field. Those are two different moments, the second
one is where the mistake actually gets made, and a requirement stated only at
the first moment is a requirement stated too early.

## 7. A child that fails must not take the parent down

The whole body of `run_subagent` sits inside a try.

```python
    def run_subagent(task):
        try:
            answer, _ = build_child()(task)
        except Exception as error:
            # A child that fails must not take the parent with it. The parent
            # can read this, decide the approach did not work, and try
            # something else, which is what a person would do.
            return f"Error: the subagent failed, {type(error).__name__}: {error}"
        return answer or "The subagent finished without saying anything."
```

Two decisions here and both go against normal advice, so both need defending.

The exception handler is deliberately broad. A bare `except Exception`
is usually a code smell, and it is usually a code smell for a good reason, which
is that it hides bugs you wanted to see. It is right here because of what is
inside the try. A whole agent run is inside the try. That means an HTTP timeout
from the provider, a malformed JSON payload, a `KeyError` from a response shape
that changed, the `RuntimeError` that `agent.py` raises when a run exceeds
`max_turns`, a tool raising something nobody predicted, and an MCP server from
lesson 19 that died mid session. Enumerating that list is not possible, and an
enumeration that is wrong fails in the worst way, which is that one unlisted
exception type propagates and kills a parent run that was forty turns deep and
had a perfectly good alternative available.

Which is the second half of the argument. The blast radius of catching too much
here is one bad tool result, and the parent reads tool results for a living. The
blast radius of catching too little is the entire parent run.

The error comes back as text rather than being raised. This is the more
interesting decision and it is the same one lesson 08 made for `run_shell`,
which captures stderr and the exit code and hands both to the model instead of
raising. The comment states the reasoning.

```text
The parent can read this, decide the approach did not work, and try
something else, which is what a person would do.
```

Raise, and the parent is dead. It has no chance to react, its session ends, and
whatever it had figured out in the previous forty turns is gone. Return a
string, and the failure enters the conversation as an ordinary tool result,
which is the one kind of input the agent loop is built entirely around
responding to. The parent reads that the delegation failed, and it can do the
obvious human things. Do the investigation itself with `grep_files`. Try the
delegation again with a narrower task. Report to the user that this part could
not be completed and carry on with the rest.

Notice what is in the string, because the content is doing work too.

```python
    return f"Error: the subagent failed, {type(error).__name__}: {error}"
```

The exception class name and the message. A `TimeoutError` invites a retry. A
`RuntimeError` about `max_turns` says the task was too big and should be split
rather than repeated. A `FileNotFoundError` says the child was pointed
somewhere that does not exist and repeating it will fail identically. The model
can only distinguish those if you tell it which one happened, and `Error, the
subagent failed` on its own tells it nothing it can act on.

The last line is the same principle applied to a quieter failure.

```python
        return answer or "The subagent finished without saying anything."
```

A child that ends with an empty final message is not an exception. Nothing threw.
But returning an empty string to the parent produces a tool result with no
content, and a model that receives an empty tool result has to guess whether the
tool succeeded silently, returned nothing meaningful, or is broken. A sentence
saying explicitly that the child finished without saying anything is a fact the
parent can act on, and it costs six words.

## 8. The trap that comes with the isolation

This is the most important section in the chapter and it is the one to read
twice. Everything above sells you a technique. This is the bill.

The module docstring puts it in three sentences.

```text
The same isolation is also the trap. The child and the parent hold separate
views of the world, so a file the child changed is still the old file as far
as the parent is concerned. Nothing tells the parent it is now wrong.
```

`check.py` does not describe this. It demonstrates it, and the demonstration
runs on every push.

```python
    shared = workspace / "shared.txt"
    shared.write_text("original", encoding="utf-8")
    parent_saw = tools.run("read_file", {"path": "shared.txt"})
    tools.run(
        "run_subagent",
        {"task": 'Rewrite. [[tool:write_file:{"path": "shared.txt", "content": "changed"}]]'},
    )
    now = shared.read_text(encoding="utf-8")
    if parent_saw == now:
        fail("this demonstration is broken, the file should have changed")
```

Four steps. Write a file with known contents. The parent reads it and the
contents go into `parent_saw`, which stands for the parent's context. Delegate a
job that rewrites the same file. Read the disk again.

Here is what it prints, from a real run against the mock server.

```text
[calling write_file with {'path': 'shared.txt', 'content': 'changed'}]
[write_file returned Wrote 7 characters to shared.txt]
The tool returned Wrote 7 characters to shared.txt.
OK the trap is real, the parent still believes 'original' while the file now says 'changed'
```

Read that last line slowly. **The parent still believes `original` while the
file now says `changed`.**

There was no error. There was no warning. The parent's tool result from the
child says the delegation succeeded, which is true. Nowhere in the parent's
conversation is there anything at all indicating that a file it read earlier is
no longer what it read.

And now think about what the parent does next, because that is where the damage
is. It is holding `original` in its context as a fact about the world. Suppose
it now calls `edit_file`.

```python
tools.run("edit_file", {"path": "shared.txt", "old": "original", "new": "improved"})
```

`edit_file` from lesson 07 searches for `old` and refuses when it does not find
it, so this particular call fails loudly and that is lesson 07 earning its keep.
Now suppose the parent calls `write_file` instead, reconstructing the file from
what it remembers with one improvement applied. That succeeds, and it silently
destroys everything the child did. The parent is not confused about the edit it
is making. It is confused about the file it is editing.

Now the part that makes this a section rather than a footnote.

**The isolation that makes subagents useful is exactly what causes this.**

They are not two facts, they are one fact seen from two sides. Section 4
celebrated the child's fifteen file reads not reaching the parent. This section
complains that the child's one file write did not reach the parent either. There
is no version of the design where the first is true and the second is false,
because the mechanism is the same mechanism. The child has its own `messages`
list. Nothing in the parent's `messages` list is written by the child. That is
the feature and that is the bug, and they are the same line of code.

So this is not something to fix. It is a property to design around, and the
difference matters because people waste a lot of time trying to fix it. The
fixes all sound reasonable and all fail. Share the message list and you have
deleted the entire benefit and rebuilt the one conversation from section 1.
Have the parent re read every file after every delegation and you have pulled
the file contents back into the parent's context, which is the same cost you
were avoiding, paid at a worse time. Diff the workspace before and after and
inject the changes, and you have written a mechanism that only handles files,
that misses database rows and network calls and anything else with side effects,
and that puts a whole new subsystem in a chapter whose thesis is that nothing
new was needed.

Two practical habits work, and they are habits rather than mechanisms.

Have the child report what it changed. This is a sentence in the task the
parent writes, and it costs nothing.

```text
task = "Update the retry delay in retry.py to start at two seconds.
        End your answer with a list of every file you modified and
        exactly what you changed in each."
```

Now the child's own final answer, which is the one thing that does cross the
boundary, carries the information the parent needs. The channel already exists.
The return value was always going to end up in the parent's context, so putting
the change list in it costs one line instead of a subsystem. This is also a
sentence you can put permanently in the child's system prompt through
`build_child`, so every child does it without the parent having to remember.

Re read anything the parent is about to act on. Not everything, and not on a
schedule. Specifically the thing it is about to change, immediately before
changing it, after any delegation that could have touched it. One targeted
`read_file` before one `edit_file` is a cost you can measure and it is small.
Re reading the world after every delegation is not.

The general form of this is worth carrying past this chapter, because it is what
lesson 21 is going to hit much harder. **Anything with more than one agent in it
has more than one view of the world, and those views go stale silently.** The
disk is shared. The context is not. Every fact an agent holds about a mutable
resource has a timestamp attached to it that nobody wrote down, and the moment a
second actor exists, that timestamp starts to matter.

Lesson 18 gave the same warning in a different register when it noted that
`session.py` documents itself as supporting a single writer. Two agents
appending to one file interleave and corrupt it. Two agents holding one view of
a file corrupt something less visible.

## 9. When not to use one

Be fair to the alternative, because the alternative is usually right.

A subagent is not free and it is not cheap. Count what one call actually costs.

A whole second conversation, with its own system prompt sent on every one of the
child's turns. Its own copy of every tool schema, which after lesson 19 might be
forty of them. Its own multi turn loop, where each turn is a separate round trip
to the model. And all of that is paid before the child does anything useful at
all, because the system prompt and the schemas go out on the child's very first
request.

So compare honestly.

Doing it yourself, for a small job, is three tool calls in an existing
conversation whose system prompt and schemas were going to be sent anyway.
Delegating the same job is a fresh system prompt, a fresh schema list, three
tool calls, plus the extra turn on the parent's side to issue the delegation and
the extra turn to read the answer.

For a job of two or three steps, a subagent is more expensive and slower than
doing it yourself. Not marginally. The fixed cost of starting a conversation
dominates completely at that size, and you have added latency on top, because
the parent sits blocked while the child does its round trips one after another.

There is a second cost that does not show up in tokens. Everything the parent
knows has to be written into the task string by hand. On a small job that
description is most of the work, and the risk of writing it badly, from section
6, is a confident wrong answer rather than a visible error. You pay a real
translation cost and you take a real correctness risk, to save context you were
not short of.

And a third. The child's transcript is gone. If the parent's answer is wrong,
the reasoning that produced the wrong part is in a `messages` list that was
freed when the function returned. `check.py` only sees the child's conversation
at all because `build_child` was written with a closure that captures it. On a
small job you have traded away debuggability for a saving you did not need.

So the test is a ratio rather than a size. Delegate when the investigation is
much larger than the conclusion. Fifteen file reads producing two sentences is
overwhelmingly worth it. Three file reads producing three sentences is not, and
neither is anything where the parent needs the intermediate results in order to
do the next thing.

One more case where the answer is no regardless of size. Do not delegate work
whose intermediate steps the parent must reason about. If the parent has to
compare two files it asked the child to examine, it needs both files, and a
child that returns a summary of them has thrown away the thing the comparison
needed. Delegate a question. Do not delegate a step.

## 10. Running check.py

From inside the lesson folder with an endpoint configured.

```bash
cd lessons/20-subagents
python check.py
```

Or every lesson at once against the built in mock server, which is what CI runs.

```bash
python ci/run_lessons.py
```

Here is the real output for this lesson.

```text
OK a subagent is an ordinary tool as far as the parent is concerned

[calling write_file with {'path': 'made-by-child.txt', 'content': 'hello'}]
[write_file returned Wrote 5 characters to made-by-child.txt]
The tool returned Wrote 5 characters to made-by-child.txt.
OK the child did real work that reached the disk
OK the child had a 4 message conversation of its own
Hello from the mock server.
OK none of it landed in the parent, which kept 2 messages
OK a child that blew up left the parent standing

[calling write_file with {'path': 'shared.txt', 'content': 'changed'}]
[write_file returned Wrote 7 characters to shared.txt]
The tool returned Wrote 7 characters to shared.txt.
OK the trap is real, the parent still believes 'original' while the file now says 'changed'
```

Six `OK` lines, and the file's own docstring is explicit that the last one is a
different kind of thing from the other five.

```text
Five things must be true. A subagent is an ordinary tool as far as the
parent is concerned. It does real work that reaches the disk. It holds a
conversation of its own. None of that conversation lands in the parent,
which is the reason to use one at all. And a child that blows up leaves the
parent standing.

The sixth thing this file demonstrates is not a feature. It is the trap that
comes with the isolation, which is that the parent keeps believing whatever
it read before the child changed it.
```

Take them one at a time.

One. A subagent is an ordinary tool as far as the parent is concerned. The
check reads the name out of the schema and appends the schema and the function
to `tools.SCHEMAS` and `tools.FUNCTIONS`. If a subagent needed anything the
registry does not offer, this is where it would show up, and it does not.

Two. The child did real work that reached the disk. This is the habit lesson
18 argued for at length. The assertion is on the filesystem, not on any message.

```python
    answer = tools.run("run_subagent", {"task": WRITE})
    if not (workspace / "made-by-child.txt").exists():
        fail(f"the child did no real work. It said {answer!r}")
```

`tools.run` by name, exactly the call path the loop uses, so the delegation goes
through the same dispatch a real run would use. Then the disk is checked. A
child that said it wrote the file and did not would fail here, which is the
whole reason to assert on the side effect rather than the prose.

Three and four are the pair from section 4. Four messages in the child, two
in the parent, with a string search proving no leak.

**Five. A child that blew up left the parent standing.**

```python
    def build_broken():
        def child(task):
            raise RuntimeError("the child could not start")

        return child

    broken_tool, _ = run_subagent_factory(build_broken)
    result = broken_tool("anything")
```

A builder returning a child that raises immediately, which is possible only
because the builder is injected. Then the tool is called directly and the check
survives to look at the return value, which is itself the proof, because if the
exception had propagated the check would have died on that line instead of
printing anything.

Both halves of that assertion do real work.

```python
    if not result.startswith("Error") or "could not start" not in result:
```

The result has to start with `Error`, and it has to still carry the child's own
message. Either half failing fails the check. So the shape of the return value
and its content are both pinned down, which matters because the two failures are
different. A handler that stopped prefixing `Error` would leave the parent unable
to tell a failure from an answer. A handler that caught the exception and threw
away what it said would leave the parent unable to tell a timeout worth retrying
from a `max_turns` error worth splitting, which is the argument section 7 makes
about why the exception class name and the message are in the string at all.

Six. The trap is real. It prints its own `OK` line like the other five, and
the demonstration behind it has a guard.

```python
    if parent_saw == now:
        fail("this demonstration is broken, the file should have changed")
```

That fails when the file did not change, which would mean the demonstration
proved nothing. A warning that stops warning is worse than no warning, so the
warning tests itself.

If the third or fourth claim fails, something is sharing state between parent and
child, and the place to look is whether `build_child` is really constructing a
new agent per call or closing over one. If the fifth fails with a traceback
rather than a `FAIL` line, the exception handler in `run_subagent` has been
narrowed and something is now getting past it.

## 11. What you cannot do yet

One limit, and it is the whole of the next chapter.

**The children run one after another.**

Look at where a delegation happens in the loop and the reason is immediate.
`tools.run` is an ordinary synchronous function call. The loop calls it, and the
loop does not proceed until it returns. Inside it, `build_child()(task)` runs a
complete agent, which is itself a sequence of blocking HTTP requests. So a
parent that wants three investigations done issues three tool calls and waits
through three full agent runs end to end.

Put numbers on it. Three delegations of four turns each, at three seconds a
turn, is thirty six seconds of wall clock, and for essentially all of it the
process is sitting in a socket read doing nothing. The work is not CPU bound and
it is not bound by anything you own. It is bound by waiting, which is the one
kind of slowness that parallelism actually fixes.

And the three investigations in section 1's example are genuinely independent.
Where the delay is calculated, which files pass an `attempts` argument, and
whether anything overrides it in a check, are three questions that do not need
each other's answers. They are serialised purely because a Python function call
blocks.

Notice what is already true, though, because it is the reason the next chapter
is possible. Section 5 established that every delegation builds a fresh agent
and that no two children share anything. That is exactly the precondition for
running them at the same time, and it was bought in this chapter for a completely
different reason.

Lesson 21 covers multi agent patterns, an orchestrator and parallel workers
over threads and a queue. It is also where you find out which parts of the harness
quietly assumed there would only ever be one agent, and `session.py` is first in
the queue, because its own docstring says it supports a single writer and two
workers appending to one file will interleave their lines and corrupt it. The
trap from section 8 gets worse there too, because with four agents running at
once the stale view is not just the parent's, and the thing that changed
underneath you might still be changing.

On to lesson 21.
