[อ่านภาษาไทย](README.th.md)

# Lesson 18. Milestone. The harness

Nothing in this chapter is new.

Say that sentence again slowly, because it is not an apology. It is the
measurement this chapter exists to take. Lessons 12 to 17 built a permission
system, a session file, a context trimmer, a token counter, a retrieval tool, a
retry helper and a cancellation token. Each one arrived alone, in its own
folder, proved by its own `check.py`, with no other subsystem in the room. This
chapter puts all of them into one process at the same time, gives that process a
command line, points it at a real directory with a real bug in it, and then
checks the disk afterwards.

Not one line of new mechanism is invented to make that work. If it did have to
be invented, the seams of part 3 would have been cut in the wrong place, and
that is exactly the thing a milestone is for finding out.

A milestone chapter has three jobs, all different from the job of a normal
chapter. Assembly, which is showing that the parts fit. Reflection, which is
looking back at the seams and asking whether they were cut where they should
have been. And an honest accounting of what the thing still cannot do, because a
milestone that only celebrates is an advertisement rather than a lesson.

Here is what is in this folder and where each file came from.

```text
lessons/18-the-harness/
  main.py         new. argument parsing, wiring, and the interrupt handler
  check.py        new. the milestone check for part 3
  agent.py        identical to lesson 17
  prompt.py       identical to lesson 10
  permissions.py  identical to lesson 12
  session.py      identical to lesson 13
  context.py      identical to lesson 14
  providers.py    identical to lesson 15
  usage.py        identical to lesson 15
  retrieval.py    identical to lesson 16
  tools.py        identical to lesson 16
  retry.py        identical to lesson 17
  cancel.py       identical to lesson 17
  README.md       this file
```

Eleven of the thirteen Python files are byte for byte what they were in an
earlier lesson. That is not a claim, it is checkable, and it was checked.

```bash
cd lessons
for f in agent.py permissions.py session.py context.py usage.py retry.py; do
  diff -qs 17-errors-and-retries/$f 18-the-harness/$f
done
```

```text
Files 17-errors-and-retries/agent.py and 18-the-harness/agent.py are identical
Files 17-errors-and-retries/permissions.py and 18-the-harness/permissions.py are identical
Files 17-errors-and-retries/session.py and 18-the-harness/session.py are identical
Files 17-errors-and-retries/context.py and 18-the-harness/context.py are identical
Files 17-errors-and-retries/usage.py and 18-the-harness/usage.py are identical
Files 17-errors-and-retries/retry.py and 18-the-harness/retry.py are identical
```

The two new files are `main.py`, which contains no agent logic whatsoever, and
`check.py`, which contains no agent logic either.

## 1. What a harness is, now that you have built one

Every course that uses this word defines it in the abstract, and the abstract
definition is useless because it fits anything. So define it against the thing
sitting in this folder instead.

At the end of part 2 you had an agent. `run` in `agent.py` plus seven tools plus
a system prompt. It could be pointed at a folder, work out where the code was,
read it, change one line, and run a command to check the change. That is a real
capability and it is not nothing.

What it could not do was be used twice.

Close the process and everything it learned was gone. Approve a command and it
asked you the same question the next time. Work for long enough and the
conversation stopped fitting in the window, and the run ended with an HTTP error
mid task. Nothing anywhere told you what any of it cost. A five second network
blip produced a traceback and lost twenty minutes of work. Press the interrupt
key and you got a stack trace out of the middle of a stream.

Those five sentences are the definition. **A harness is everything that stands
around the agent so the agent can be run more than once, on work that matters,
by somebody who is not the person who wrote it.**

Now name the parts of the one you built, because that is the definition made
concrete.

| Piece | File | Lesson | What it makes possible |
| --- | --- | --- | --- |
| `Permissions` | `permissions.py` | 12 | a gate you still read at the fortieth prompt |
| `Session` | `session.py` | 13 | leaving and coming back, and reading what happened |
| `fit_to_budget` | `context.py` | 14 | long tasks that do not die at the window edge |
| `Usage` | `usage.py` | 15 | knowing what a run cost instead of guessing |
| `search_notes` | `retrieval.py` | 16 | retrieval as an ordinary tool, not a special system |
| `with_retries` | `retry.py` | 17 | a bad network afternoon that does not lose work |
| `Cancellation` | `cancel.py` | 17 | an interrupt that stops the work and not just the screen |

Read the fourth column. Not one entry there is a new thing the agent can do. Not
one is a new tool. Every single one is about what happens when the agent runs
again, or runs long, or runs badly, or runs while somebody is watching.

That is the distinction the word carries. Part 2 made the agent more **capable**.
Part 3 made it **operable**. They are different axes and adding to one does not
add to the other.

### Two things that are not a harness

Worth stating plainly, because both get called one.

**A better system prompt is not a harness.** Lesson 10 wrote a good one and
lesson 12 then demonstrated that you cannot instruct your way out of prompt
injection, because your instruction and the attacker's text are the same kind of
thing in the same list competing for the same attention. A control that lives
inside the conversation can be argued with by anything else in the conversation.
Every piece in the table above lives outside it.

**More tools is not a harness either.** This is the easier mistake to make
because it feels like progress. Lesson 16 is the proof. It added a whole
retrieval tool, vector index and all, and section 3 shows what that did to the
loop, which was nothing at all.

## 2. Where each piece lives, and why that matters

Look at where the responsibilities sit, one at a time. Each of these is a
sentence about a boundary, and each boundary was a decision that could have gone
the other way.

### Permissions decide, and do not run

`permissions.py` has one method that matters and it returns a boolean.

```python
    def check(self, name, arguments):
        """Say whether this call may run, asking a person only when needed."""
        if name in SAFE_TOOLS:
            return True
        if self.auto_approve:
            return True
        if signature(name, arguments) in self.remembered:
            return True
        if self.ask is None:
            return False
        answer = self.ask(name, arguments)
        if answer == ALLOW_ALWAYS:
            self.remembered.add(signature(name, arguments))
            return True
        return answer == ALLOW_ONCE
```

There is no `tools.run` in that file. There is no `subprocess`. There is no
`open`. `Permissions` has never executed anything in its life and cannot, and
the only reason it knows tool names at all is so it can look them up in a set.

The alternative design is the obvious one, where the permission object wraps the
tool call and runs it if allowed. It looks tidier at first because the caller
then has one line instead of two. What it costs you is that permission becomes
untestable without side effects, because you cannot ask it what it would have
decided without it doing the thing. Look at what that buys `check.py` in section
6, which builds a `Permissions` that refuses everything and passes it straight
into a real run.

Notice also where `confirm` went. Lesson 08 put the question inside `run_shell`.
Lesson 12 took it out, and the comment left behind in `tools.py` says why.

```python
def run_shell(command):
    # The confirmation that used to live here moved to permissions.py in
    # lesson 12. Asking in both places would ask the same question twice,
    # and a tool that asks its own questions cannot be reused by anything
    # that is not a terminal.
```

That last clause is the whole argument. A tool that calls `input` has a terminal
baked into it. When lesson 20 runs a tool inside a subagent with nobody at a
keyboard, a tool that asks its own questions hangs forever.

### The session records, and does not decide

`Session.append` writes one line and returns nothing.

```python
    def append(self, message):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")
```

It never inspects the message. It does not care about roles, it does not skip
tool results to save space, it does not summarise, and it does not decide when a
conversation is worth keeping. It takes a dictionary and it puts it on disk.

The loop reaches it through a callback that knows nothing about files.

```python
    def remember(message):
        messages.append(message)
        if on_message:
            on_message(message)
```

`on_message` is a function of one argument. In `main.py` it happens to be
`session.append`. In `check.py` it is sometimes `denied.append` for a second
session object. It could be a function that posts to a socket or appends to a
list in a test, and the loop would never know.

The reason this matters more than it looks is debugging. A session file is only
useful for answering the question of why the agent did something if it records
what actually happened rather than an edited version of it. The moment the
recorder starts making decisions, it starts having opinions about what is worth
recording, and the line you needed is the line it dropped.

### Context management shrinks what is sent, without touching what is remembered

This is the sharpest boundary in the program and it is five lines.

```python
    def to_send():
        """What travels is not what is remembered.

        The full conversation stays in messages because the session file and
        anyone debugging later need all of it. Only the copy handed to the
        provider is trimmed.
        """
        return messages if budget is None else fit_to_budget(messages, budget)
```

`fit_to_budget` returns a new list. `messages` is never mutated. So the session
file gets every message, forever, and the provider gets whatever fits.

Get this backwards and you get the bug that is impossible to diagnose later.
Trim `messages` itself and the session file now contains a conversation that
never happened, with a hole in the middle where the trimmer took a block out.
Then, three days later, you open that file to work out why the agent did
something insane on turn nine, and the evidence you need was deleted by the
thing that made it behave insanely. The one artifact that could explain the
failure has been edited by the failure.

Separating the two also makes `fit_to_budget` a pure function, which is why
lesson 14 could test it by handing it a list and looking at the list that came
back, with no agent and no model anywhere.

### Retry wraps the network call, and nothing else

`retry.py` is a function that takes a callable.

```python
def with_retries(call, attempts=4, sleep=time.sleep):
```

It does not know about tools. It does not know about the loop. Its entire
contract is that you hand it something safe to repeat and it repeats it. The
module docstring is explicit about why that restriction exists.

```text
Not everything may be retried. Asking the model again is safe because it
changes nothing outside the conversation. Running a tool that sent an email
is not, which is why nothing in this module wraps a tool call.
```

Be honest about the state of the wiring, because it matters. Nothing in this
folder calls `with_retries` yet. Lesson 17 said where it goes and why, and the
place is inside the provider.

```python
from retry import with_retries

# in OpenAICompatProvider
def stream(self, messages, tools=None, on_text=None):
    return with_retries(lambda: self._stream_once(messages, tools, on_text))
```

The provider is the only object in this program that knows it is speaking HTTP.
It is where `httpx` is imported and where `raise_for_status` is called, so it is
the only place where `httpx.HTTPStatusError` is a meaningful type to catch. Put
the retry in the loop instead and `agent.py` has to import `httpx` in order to
know which failures are worth repeating, and the loop staying ignorant of the
wire is the property lesson 06 bought and lesson 11 measured. Exercise three in
section 8 wires it in for real.

### Cancellation says stop, and everybody else asks it

```python
class Cancellation:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()
```

Three methods around a `threading.Event`. It starts nothing and stops nothing
by force. It is a flag that more than one thread can read safely, and the
stopping is done by whoever reads it.

The loop reads it in two places.

```python
    def stop_requested():
        return cancellation is not None and cancellation.cancelled
```

Section 4 covers what that does and does not achieve when you actually press the
key, because it is less than the docstring implies and you should know exactly
where the gap is.

### Usage counts what the provider said, and estimates nothing

`Usage.add` takes the dictionary the provider reported and adds it up. It does
not tokenise anything. `context.py` has an estimator, `estimate_tokens`, and
those two numbers are deliberately never mixed, because the estimate exists to
decide when to start trimming and the reported number exists to tell you what
actually happened.

### Why this is not tidiness

Here is the payoff, and it is a measurement rather than an aesthetic preference.

Between lesson 06 and lesson 11 you added seven tools. Between lesson 12 and
lesson 17 you added five subsystems and a retrieval tool. Every one of those
went in as a new file plus, at most, one new parameter on `run`. Not one of them
required rewriting how the loop works.

Now picture the version where the seams are somewhere else, because it is very
easy to end up there and it always starts reasonably. The shell tool needs to
ask before it runs, and the loop owns the terminal, so the asking goes in the
loop. Now the loop has a branch that names one tool. Then the session needs
writing, and the loop is where messages appear, so file handling goes in the
loop. Then trimming, because the loop is where the request is built. Then usage.
Then the retry, so the loop imports `httpx`. Then cancellation.

Six chapters later the loop is four hundred lines, every subsystem has a branch
in it, and the one file every feature must pass through is the file nobody dares
edit. Adding the seventh subsystem now means changing the most dangerous code in
the program, and every change risks the six that already work.

Both designs run the same agent on the day you finish them. They diverge on day
thirty, and the next section measures exactly how far.

## 3. Comparing the loop with lesson 04

Lesson 11 made this comparison at the end of part 2 and the answer was that the
loop was almost unchanged. Making the same comparison now would be dishonest if
it claimed the same result, because part 3 did change the loop. So be precise
about how, and about what caused it.

Here is lesson 04, the first agent you ever had, before real tools, before
streaming, before providers.

```python
def run(user_input, max_turns=10):
    """Run the agent until it produces a final answer. Returns the answer."""
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete(messages, tools.SCHEMAS)

        if not calls:
            return text

        messages.append({...assistant message with tool_calls...})

        for call in calls:
            print(f"[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": result}
            )

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
```

Fifty four lines with the docstring. Here is the signature it has today.

```python
def run(
    provider,
    user_input,
    system=None,
    permissions=None,
    on_message=None,
    history=None,
    budget=None,
    cancellation=None,
    usage=None,
    max_turns=10,
):
```

One hundred and forty lines. That is not a small change and pretending it is
would be the wrong lesson.

### Every difference, and the lesson that caused it

Complete list. If it were not complete the argument at the end would be worth
nothing.

| Difference | Lesson |
| --- | --- |
| `complete(...)` became `provider.stream(...)` | 05 gave it streaming, 06 gave it a provider argument |
| the `on_text` callback that prints as text arrives | 05 |
| `tools.SCHEMAS` unwrapped with `[t["function"] for t in ...]` | 06, where the provider does the wrapping |
| the `call["error"]` branch for unparseable arguments | 05 |
| the `system=None` parameter and the message it prepends | 10 |
| returning `(text, messages)` instead of `text` | 10, so a caller can inspect the conversation |
| the `permissions` parameter and the `permissions.check` branch | 12 |
| the `on_message` parameter and the `remember` helper | 13 |
| the `history` parameter and `messages = list(history or [])` | 13 |
| `if system and not messages`, so a resumed run does not get two system messages | 13 |
| the `budget` parameter and the `to_send` helper | 14 |
| `provider.stream` returning three values, and `usage.add(reported)` | 15 |
| repeat detection with `signature`, `recent`, `warned` and `REPEAT_LIMIT` | 15 |
| the `cancellation` parameter and the two `stop_requested` checks | 17 |

Fourteen differences. Now sort them by cause rather than by line number.

Two came from streaming. Two from the provider abstraction. Two from the system
prompt. One from permissions. Three from sessions. One from context management.
Two from token economy. One from errors and interruption.

Zero came from adding a tool.

That is the sentence the whole comparison exists to produce. Fourteen changes to
the most important function in the program, across fourteen chapters, and not
one of them was caused by teaching the agent to do something new.

### The evidence, measured rather than asserted

You do not have to take the table on faith. Hash the file at every lesson.

```bash
cd lessons
for d in 06-provider-abstraction 07-file-tools 08-shell-tool 09-search-tools \
         10-anatomy-of-a-prompt 11-mini-coding-agent 12-permissions 13-sessions \
         14-context-management 15-token-economy 16-retrieval \
         17-errors-and-retries 18-the-harness; do
  printf "%-28s %s  %s lines\n" "$d" "$(md5sum $d/agent.py | cut -c1-32)" \
         "$(wc -l < $d/agent.py)"
done
```

```text
06-provider-abstraction      b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
07-file-tools                b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
08-shell-tool                b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
09-search-tools              b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
10-anatomy-of-a-prompt       02cf3a892d2e8c2e885b0c1af078b6c9  52 lines
11-mini-coding-agent         02cf3a892d2e8c2e885b0c1af078b6c9  52 lines
12-permissions               a01da24bdf59c0d570e8e24179b10c54  60 lines
13-sessions                  f12dce1e312f8d0c91814d07d3813fb4  80 lines
14-context-management        3b5ff3dc951bedc2578f8c81ab330d7d  91 lines
15-token-economy             7751a3e429e71a0f305ccfeb0ddc6519  130 lines
16-retrieval                 7751a3e429e71a0f305ccfeb0ddc6519  130 lines
17-errors-and-retries        3fb92af29d8aa02403e0e76984b74aa4  140 lines
18-the-harness               3fb92af29d8aa02403e0e76984b74aa4  140 lines
```

Read that table twice, because it says two different things.

**Lessons 07, 08 and 09 are the same bytes as lesson 06.** Four file tools, a
shell with a timeout, glob and grep, path confinement, a secret file refusal,
output truncation, an ambiguous edit refusal and a subprocess timeout, and the
loop did not change once.

**Lesson 16 is the same bytes as lesson 15.** That is the one to sit with,
because retrieval is the feature most likely to be built as a special system
with its own hooks in the middle of everything. Lesson 16 built a vector index,
an embedder and a scorer, and delivered them as `search_notes` in `tools.py`,
which meant the loop had nothing to say about it.

**Every lesson that did change the loop added a subsystem.** Permissions in 12,
sessions in 13, trimming in 14, counting and the doom loop guard in 15,
cancellation in 17. Five subsystems, five changes to `agent.py`.

The pattern is exact. Tools never touched the loop. Subsystems always did.

### Same shape, more parameters

The last honest point. Line count grew by a factor of three, but put the two
functions side by side and the skeleton is identical.

```python
    for _ in range(max_turns):        # same loop, same bound
        ...                           # ask the model
        if not calls:                 # same early return
            return ...
        remember({...assistant...})   # same append
        for call in calls:            # same inner loop
            result = ...              # decide, then run
            remember({...tool...})    # same append
    raise RuntimeError(...)           # same bottom
```

Every one of the fourteen differences is either a parameter or a branch inside
that skeleton. None of them changed how a turn works. Ask, run, feed back, ask
again, stop when it answers in words, is the same four steps it was in lesson
04, and it is why the loop could gain permissions, sessions, trimming, counting
and cancellation one at a time without any of them interfering with each other.

The growth is real. The shape did not move.

## 4. Walking through main.py

Now the new file. It is around eighty lines and it contains no agent logic at
all. Five of its decisions are worth more than their line count suggests.

### Argument parsing

```python
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("task", nargs="?", help="What you want the agent to do")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--session", default=None)
    parser.add_argument("--resume", default=None, help="Name of a session to carry on from")
    parser.add_argument("--budget", type=int, default=100000)
    parser.add_argument("--yes", action="store_true", help="Approve everything without asking")
    arguments = parser.parse_args()
```

```bash
python main.py --help
```

```text
usage: harness [-h] [--workspace WORKSPACE] [--session SESSION]
               [--resume RESUME] [--budget BUDGET] [--yes]
               [task]

positional arguments:
  task                  What you want the agent to do

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
  --session SESSION
  --resume RESUME       Name of a session to carry on from
  --budget BUDGET
  --yes                 Approve everything without asking
```

`argparse` is in the standard library, for the same reason `fnmatch` and `re`
were the right answer in lesson 09. A course that makes you install a CLI
framework before the milestone has spent a dependency on something the standard
library does adequately, and every dependency is another place a reader can get
stuck on something that is not the subject.

`task` is positional and optional. Supply it and the agent starts immediately,
which is what you want when scripting. Leave it out and you get asked, which is
what you want when you are still deciding. Making it a flag would put four extra
characters of ceremony on the most common thing you ever type.

`--budget` takes an integer and defaults to a hundred thousand. Note carefully
what it is measured in, because it is not the same unit as the number printed at
the end of the run. It is fed to `fit_to_budget`, which counts with
`estimate_tokens`, which is a character estimate. The usage line at the end
reports what the provider counted. Lesson 15 spent a whole section on why those
two numbers must never be confused, and this is where the confusion would
happen, so the estimate is used only to decide when to trim and never to decide
what anything cost.

`--yes` exists so a machine can run this. There is a second door for the same
thing, and both are honoured.

```python
    permissions = Permissions(
        ask=ask_in_terminal,
        auto_approve=arguments.yes or os.environ.get("AGENTPATH_AUTO_APPROVE") == "1",
    )
```

The environment variable has been in the project since lesson 08 and is what
`ci/run_lessons.py` sets. The flag is for you at a keyboard. They mean the same
thing, so they set the same field, rather than there being two switches with
subtly different behaviour.

### The two lines whose order is load bearing

This is the part that bites people who tidy it.

```python
    workspace = Path(arguments.workspace).resolve()
    os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

    from agent import run
    from cancel import Cancellation
    from permissions import Permissions, ask_in_terminal
    from prompt import build_system_prompt
    from providers import OpenAICompatProvider
    from session import Session
    from usage import Usage
```

The imports are at the bottom of the function rather than at the top of the
file, deliberately. Look at what `tools.py` does when Python loads it.

```python
WORKSPACE = Path(os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()
```

That line runs once, at import time, and never again. `from agent import run`
imports `agent`, which imports `tools`, which runs that line. By the time `run`
exists as a name in `main.py`, the workspace is fixed for the life of the
process.

Set the environment variable after the import and it does nothing at all. The
program would not crash. It would not warn you. It would resolve every path
against whatever directory you happened to be standing in, so
`--workspace ../other-project` would read, write and edit files in the wrong
tree while printing the right directory at the top of the screen. A confinement
rule that is announced but not applied is worse than no rule, because you relax
around it.

`resolve()` before storing it, because three separate things downstream need an
absolute path. `resolve_inside` compares candidates against `WORKSPACE` with
`is_relative_to`, which is meaningless when `WORKSPACE` is `.`. `run_shell`
passes `cwd=WORKSPACE` to `subprocess.run`. And `build_system_prompt` puts the
directory in the system prompt as a fact about the world, and a model told it is
working in `.` has been told nothing.

`check.py` does the same thing for the same reason and marks it.

```python
os.environ["AGENTPATH_HOME"] = str(home)
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from agent import run  # noqa: E402
```

`# noqa: E402` is the honest way to break the style rule. E402 is the linter
complaining that an import is not at the top of the file. It is right that this
is unusual, and we are telling it that we know, on purpose, here.

### How a session name is chosen

One line, three cases.

```python
    session = Session(arguments.resume or arguments.session or new_session_name())
    history = session.load() if arguments.resume else []
```

`--resume` wins outright, and it wins by supplying the same name, which is what
makes the resumed run append to the file it just read rather than starting a new
one. That property is worth pausing on. Resuming is not a copy. The session file
is the one continuous record of the whole piece of work, however many times you
walked away from it.

`--session` is next, for when you want a name you chose. Naming a session
`refactor-auth` is the difference between finding it in a month and not.

And when neither is given, a timestamp.

```python
def new_session_name():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
```

Three properties, each one a reason it is not something else. It never
collides in practice, which a counter would require reading the directory to
achieve. It sorts chronologically as a string, so `ls` in the sessions folder is
in order with no work. And it is UTC, because a name that shifts when you cross
a timezone or when daylight saving ends produces two sessions that sort wrongly
against each other, and the sessions folder is the only place that ordering
shows up.

The obvious alternative is a UUID. A UUID is unique and completely
unrecognisable, and the session file is a thing you open in a text editor when
you want to know why the agent did something. `20260901-142233` tells you when
you ran it. `f47ac10b-58cc-4372-a567-0e02b2c3d479` tells you nothing at all.

### How resume loads a history and passes it in

Two lines in `main.py`, plus one line in `agent.py` that makes them correct.

```python
    history = session.load() if arguments.resume else []
```

`Session.load` reads the JSONL file and returns a list of dictionaries. Those go
straight into `run`.

```python
        run(
            provider,
            task,
            system=build_system_prompt(workspace),
            ...
            history=history,
```

Now notice something that looks like a bug and is not. `main.py` always passes a
system prompt, even when resuming, even though the loaded history already starts
with one. The loop handles it.

```python
    messages = list(history or [])
    ...
    if system and not messages:
        remember({"role": "system", "content": system})
```

`and not messages` is the whole safeguard. On a fresh run `messages` is empty and
the system prompt is prepended. On a resumed run `messages` already holds the
whole conversation, so the system prompt is skipped and the one that was saved
at the top of the file is used instead.

Both alternatives are worse and it is worth knowing why. Prepending the new
system prompt anyway gives you a conversation with two system messages, and
providers differ in how they treat that, which means a bug that appears on one
model and not another. Replacing the old one silently changes the instructions
mid task, so a session resumed after you edited `prompt.py` would behave
differently from the one you saved, with nothing in the file recording that the
rules changed underneath it.

`list(history or [])` is a copy rather than the list itself, so the caller's
list is not mutated by the run. `check.py` depends on that in its fourth claim,
where it compares the length before against the length after.

### How the interrupt handler is installed

```python
    def handle_interrupt(signum, frame):
        if cancellation.cancelled:
            raise KeyboardInterrupt
        print("\nStopping after the current step. Press Ctrl+C again to force it.")
        cancellation.cancel()

    try:
        signal.signal(signal.SIGINT, handle_interrupt)
    except ValueError:
        pass
```

Two presses, two behaviours, and that is the entire design.

The first press sets the flag and tells you what it did. The loop notices at its
next checkpoint and raises `KeyboardInterrupt` from a place where the
conversation is in a consistent state, so `main` catches it, prints `stopped`,
and still gets to the two lines that report the session path and the usage. You
interrupted the agent and you kept the work.

The second press raises immediately, from inside the signal handler, wherever
the program happens to be. That is deliberately violent. It exists because the
polite stop can only take effect at a checkpoint, and if the program is wedged
somewhere with no checkpoint ahead of it, the polite stop never arrives. A stop
button that can itself hang is not a stop button.

The `try` around `signal.signal` is not defensive noise. `signal.signal` raises
`ValueError` when it is not called from the main thread of the main interpreter,
and this exact `main` function is importable and callable from a test runner or
another program. Without the guard, `main()` would crash on a line that has
nothing to do with the task, in an environment where nobody was going to press
Ctrl+C anyway.

Now the honest part, because the docstring in `cancel.py` promises more than
this program delivers.

```text
The same token is checked by the agent loop between turns and by the shell
tool before it starts a process
```

Grep `tools.py` for the cancellation token and you will not find it. `run_shell`
does not consult it. The loop checks in two places, before each turn and before
each call.

```python
    for _ in range(max_turns):
        if stop_requested():
            raise KeyboardInterrupt("cancelled")
        ...
        for call in calls:
            if stop_requested():
                raise KeyboardInterrupt("cancelled")
```

So press Ctrl+C once while a sixty second `run_shell` is going, and the
subprocess runs to completion. The stop takes effect afterwards, before the next
call. It is a real gap, it is exactly the gap `cancel.py` was written to warn
about, and the honest thing is to name it here rather than let the docstring
imply it is closed. Exercise four in section 8 closes it.

### The last four lines

```python
    print(f"\nsession {session.name} saved to {session.path}")
    print(f"usage {usage.summary()}")
    return 0
```

These print after the `try` that catches `KeyboardInterrupt`, which is the point
of them being where they are. An interrupted run still tells you where its
transcript is and what it spent. A harness that prints the receipt only on
success hides the number exactly when a run went sideways, which is precisely
when you wanted it.

`raise SystemExit(main())` at the bottom of the file makes `main` return the exit
code rather than calling `sys.exit` from inside it, which keeps `main` an
ordinary function another program can call without it killing the interpreter.

## 5. Running it on a real task

Enough reading. Build something broken and point the harness at it.

Make a folder outside this repository with two files in it.

```bash
mkdir -p ~/code/salestool
cd ~/code/salestool
```

`stats.py`, with a bug in it that you should not fix.

```python
"""Small helpers for summarising a list of numbers."""


def total(numbers):
    return sum(numbers)


def average(numbers):
    if not numbers:
        return 0
    return total(numbers) / (len(numbers) + 1)


def largest(numbers):
    return max(numbers)
```

`report.py`, which uses it.

```python
from stats import average, largest, total

SALES = [120, 80, 100]

print("total", total(SALES))
print("average", average(SALES))
print("largest", largest(SALES))
```

Run it and see the symptom.

```bash
python report.py
```

```text
total 300
average 75.0
largest 120
```

Two of three numbers are right. Three hundred over three values should average a
hundred, not seventy five. The bug is `len(numbers) + 1`, an off by one that
produces a plausible number rather than a crash, which is the kind that survives
a code review.

Set your environment. These are the same three variables from lesson 00.

```bash
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen3
export AGENTPATH_API_KEY=

cd /path/to/agentpath/lessons/18-the-harness
python main.py "The average is wrong in this project. Find it, fix it, and prove the fix." \
  --workspace ~/code/salestool --session salestool-1
```

On Windows PowerShell the exports are `$env:AGENTPATH_BASE_URL = "..."` and the
line continuation is a backtick rather than a backslash.

### The trace

```text
Working in /home/you/code/salestool

[calling grep_files with {'pattern': 'def average', 'glob': '*.py'}]
[grep_files returned stats.py:8: def average(numbers):]

[calling read_file with {'path': 'stats.py'}]
[read_file returned """Small helpers for summarising a list of numbers."""


def total(numbers):
    return sum(numbers)


def average(numbers):
    if not numbers:
        return 0
    return total(numbers) / (len(numbers) + 1)


def largest(numbers):
    return max(numbers)
]

The agent wants to run edit_file
  path = 'stats.py'
  old = 'return total(numbers) / (len(numbers) + 1)'
  new = 'return total(numbers) / len(numbers)'
Allow? [y]es once, [a]lways for this exact call, [N]o y

[calling edit_file with {'path': 'stats.py', 'old': 'return total(numbers) / (len(numbers) + 1)', 'new': 'return total(numbers) / len(numbers)'}]
[edit_file returned Edited stats.py]

The agent wants to run run_shell
  command = 'python report.py'
Allow? [y]es once, [a]lways for this exact call, [N]o y

[calling run_shell with {'command': 'python report.py'}]
[run_shell returned total 300
average 100.0
largest 120
]
The tool returned total 300
average 100.0
largest 120
.

session salestool-1 saved to /home/you/.agentpath/sessions/salestool-1.jsonl
usage 5 calls, 1629 prompt tokens, 87 completion tokens
```

Read it as five lessons arriving in order.

**`grep_files` is lesson 09.** You did not name a file. You said the average was
wrong and it searched for `def average` restricted to `*.py`, and got one hit
with a path and a line number.

**`read_file` is lesson 07.** It took the path from the previous result and
handed it to the next tool with no transformation, which is the property lesson
09 argued for when it explained why search returns paths rather than a summary.

**The two permission prompts are lesson 12, and they are the visible difference
from part 2.** Notice which calls were gated and which were not. `grep_files`
and `read_file` went through without a question because they are in `SAFE_TOOLS`
and cannot destroy anything. `edit_file` and `run_shell` both stopped and waited.
In part 2 only `run_shell` was gated, and an injected instruction that said to
write a file rather than run a command met no gate at all.

Notice also what the prompt prints. Not a rendered command string but the
argument dictionary, one key per line. `ask_in_terminal` does not know what
`edit_file` is, so it cannot format it specially, and printing every argument is
the only thing it can do that is guaranteed to be complete. A gate that
summarises what it is about to allow is a gate that can leave out the part that
mattered.

The `[a]lways` option is the answer to the fatigue problem from lesson 12. Say
`a` to `python report.py` once and the third and fourth times it runs, it will
not ask. What gets remembered is the full signature including arguments, so
allowing `python report.py` forever does not allow `rm -rf .` even once.

**`run_shell` is lesson 08, and it is the point of the trace.** The agent did not
announce a fix. It ran the program. `average 100.0` is the proof, and it was
produced by executing code rather than by asserting anything.

**The last two lines are lessons 13 and 15.** A file path you can open, and a
number you can compare against the next run. Neither existed at the end of part
2.

Three honest notes. This transcript was captured by running `main.py` for real
against the project's mock server rather than a paid model, with the home
directory and workspace paths shortened for reading. Everything printed by the
harness is exactly what came out, and the one visible consequence of the mock is
that the tool call ids in the session file below read `call_mock_1` and
`call_mock_2` where a real provider would put its own.

The model's own sentences between tool calls are not shown,
because they vary from run to run and from model to model. Small local models
often say nothing at all between calls and larger ones narrate, and that
variation is normal. And the exact order can differ. A model that reads before
grepping, or runs the program first to see the failure for itself, has done
nothing wrong. There is no single correct trace, which is why the next section
proves the outcome rather than the path.

One environment note that is not hypothetical, because it happened while this
chapter was being written. If `python` is not on the `PATH` inside the shell
`subprocess.run` uses, that fourth call comes back like this.

```text
[run_shell returned 'python' is not recognized as an internal or external command,
operable program or batch file.

[exit code 1]]
```

Which is `run_shell` doing exactly the right thing. It captured stderr and the
exit code and handed both to the model as a tool result instead of raising, so
the agent gets to read the failure and try `py report.py` or a full interpreter
path. This is lesson 08's design showing up as a good afternoon rather than a
traceback.

### What is on disk afterwards

The file, changed by one character and a pair of parentheses.

```python
def average(numbers):
    if not numbers:
        return 0
    return total(numbers) / len(numbers)
```

The docstring is intact and `total` and `largest` are untouched, which is
`edit_file` from lesson 07 doing the job it exists for. Had the agent used
`write_file` it would have had to reproduce the whole module from memory, and a
model reproducing code it does not need to change is a model that quietly drops
a line of it.

And the session, which is the thing part 3 added.

```bash
wc -l ~/.agentpath/sessions/salestool-1.jsonl
cut -c1-72 ~/.agentpath/sessions/salestool-1.jsonl | head -6
```

```text
11 salestool-1.jsonl
{"role": "system", "content": "You are a careful software assistant work
{"role": "user", "content": "The average is wrong in this project. Find
{"role": "assistant", "content": "", "tool_calls": [{"id": "call_mock_1"
{"role": "tool", "tool_call_id": "call_mock_1", "content": "stats.py:8:
{"role": "assistant", "content": "", "tool_calls": [{"id": "call_mock_2"
{"role": "tool", "tool_call_id": "call_mock_2", "content": "\"\"\"Small
```

One JSON object per line, in the order things happened, written as they
happened rather than at the end. There is no query language and no viewer. Every
question you will ever have about that run is answered by opening a text file.

### Carrying on from it

Now the thing that was impossible at the end of part 2. Close the terminal, come
back tomorrow, and ask a follow up.

```bash
python main.py "What did you change, and why?" \
  --workspace ~/code/salestool --resume salestool-1
```

```text
Working in /home/you/code/salestool
Resumed salestool-1 with 11 messages

...the model's answer...

session salestool-1 saved to /home/you/.agentpath/sessions/salestool-1.jsonl
usage 1 calls, 384 prompt tokens, 6 completion tokens
```

`Resumed salestool-1 with 11 messages` is `Session.load` handing eleven
dictionaries to `run`, which copies them into `messages` and skips prepending a
second system prompt. The model can answer the question because the edit it made
yesterday is sitting in its context as a tool call and a tool result, exactly as
it was when it made it.

Check the file again and it is longer.

```bash
wc -l ~/.agentpath/sessions/salestool-1.jsonl
```

```text
13 salestool-1.jsonl
```

Eleven from yesterday, two more from today. One session, one file, two sittings.

## 6. What the milestone check proves

Every `check.py` so far has tested one piece. Lesson 12's built a `Permissions`
object and asked it questions. Lesson 13's wrote a session and read it back.
Lesson 14's handed `fit_to_budget` a list and looked at the list that came out.
Lesson 17's called `with_retries` against a mock server that returned a 429.
Each one deliberately kept everything else out of the room, which is what makes
a unit test readable when it fails.

This one is different, and the difference is the whole point of a milestone.
Subsystems that each work alone can still fail together. The session can be
correct and the loop can call it at the wrong moment. Permissions can decide
correctly and the loop can ignore the answer. Trimming can be correct and
mutate the list the session is writing from.

None of those is findable by testing the pieces apart, because none of them is a
defect in a piece. They are defects in the wiring, and the only thing that
exercises the wiring is running everything at once.

So `check.py` here does one real task, in a real directory, with a real bug, a
real permission object, a real session on disk, a real budget, real usage
counting, a real provider over a real socket, and then it inspects the
filesystem afterwards. The only thing that is not real is the model.

### The fixture

```python
home = Path(tempfile.mkdtemp(prefix="agentpath-lesson18-home-"))
workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson18-ws-"))
os.environ["AGENTPATH_HOME"] = str(home)
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)
```

Two temporary directories rather than one, and they are separate on purpose.
`AGENTPATH_WORKSPACE` is where the agent may touch files.
`AGENTPATH_HOME` is where sessions are written, and `session.py` reads it in
`default_directory`. Point the check at your real home and it litters
`~/.agentpath/sessions` with a file called `milestone.jsonl` that grows every
time you run it, and worse, the third claim below starts failing because the
session already had messages in it before the run started.

```python
BUGGY = 'def add(a, b):\n    """Return the sum."""\n    return a - b\n'
```

`a - b` where `a + b` was meant. A bug a person spots instantly and a model
spots instantly, so the check is not secretly a test of how clever the model is.

### Steering the model without a model

```python
TASK = (
    "Fix the bug in calc.py. "
    '[[tool:grep_files:{"pattern": "def add", "glob": "*.py"}]]'
    '[[tool:read_file:{"path": "calc.py"}]]'
    '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]'
)
```

The `[[tool:name:{...}]]` directives are read by the mock server in
`src/agentpath/testing/mock_server.py`, which you met in lesson 06. It counts how
many tool results have come back and answers with the next directive, so three
directives produce three tool calls in order and then a final text answer.

This deserves a defence, because it looks like scripting the answer.

What is scripted is only which tools get called with which arguments. That is
the part a real model decides, and it is the part that is not deterministic and
therefore cannot be asserted on. Everything downstream is real. The provider
serialises the schemas and streams a real HTTP response over a real socket. The
loop accumulates the streamed argument fragments, builds the assistant message,
consults `Permissions`, and dispatches through `tools.run`. `edit_file` opens the
file and writes to the disk. `Session` writes every message to a real file as it
goes. If any of that is broken the check fails, for the same reason it would
fail against a paid model.

What you give up is confidence that a model would choose those three calls. What
you buy is a check that runs on every push, costs nothing, needs no API key,
finishes in well under a second and gives the same answer every time.

### The five claims

Run it against the mock server the way CI does.

```bash
python ci/run_lessons.py
```

```text
[calling grep_files with {'pattern': 'def add', 'glob': '*.py'}]
[grep_files returned calc.py:1: def add(a, b):]

[calling read_file with {'path': 'calc.py'}]
[read_file returned def add(a, b):
    """Return the sum."""
    return a - b
]

[calling edit_file with {'path': 'calc.py', 'old': 'return a - b', 'new': 'return a + b'}]
[edit_file returned Edited calc.py]
The tool returned Edited calc.py.
OK the agent fixed a real bug in a real file
OK the session was written as it happened, 9 messages
OK the run counted what it cost, 4 calls, 875 prompt tokens, 40 completion tokens
Hello from the mock server.
OK the session was resumed and carried on from, now 11 messages

[edit_file was refused]
The tool returned The user refused this call. Do not try it again, do something else..
OK a refused tool call really did not touch the file
```

Five `OK` lines. Take them one at a time, because each one covers a different
subsystem and the last one covers something none of the others can.

**One. The agent fixed a real bug in a real file.**

```python
    if "return a + b" not in (workspace / "calc.py").read_text(encoding="utf-8"):
        fail("the bug was not fixed on disk")
```

The file is reopened and read after `run` returns. Nothing about the agent's own
account of events is consulted. This is the claim that covers the whole pipeline
from schema serialisation through streamed argument reassembly to the write, and
every step of it has been broken during development.

**Two. The session was written as it happened.**

```python
    saved = session.load()
    if [m["role"] for m in saved[:3]] != ["system", "user", "assistant"]:
        fail(f"the session was not written as the run happened. Got {...}")
```

Note what it asserts. Not that the file exists, and not that it has nine lines,
but that the first three roles are `system`, `user`, `assistant` in that order.

That specific assertion is what catches a subtle failure. A harness that
buffered messages and wrote them at the end would pass a test that only counted
lines, and would then lose everything on a crash. It would also very plausibly
write them in a different order, because the natural way to write at the end is
to walk whatever structure you accumulated. Checking the order proves the
callback fired inside the loop, message by message, in sequence.

Nine messages, which is one system, one user, and then three pairs of an
assistant message with tool calls followed by a tool result, plus the final
answer.

**Three. The run counted what it cost.**

```python
    if usage.calls < 2 or usage.prompt_tokens <= 0:
        fail(f"usage was not counted. Got {usage.summary()}")
```

Two conditions, and the second is the interesting one. `usage.calls` alone would
pass if `Usage.add` were called every turn with an empty dictionary, which is
exactly what happens when a provider stops reporting usage or when the
`stream_options` that request it get dropped from the payload. The failure is
silent, because a counter that counts zeros looks identical to a cheap run.
Requiring `prompt_tokens > 0` proves numbers actually came back from the wire.

Four calls, because the run made three tool calls and then answered.

**Four. The session was resumed and carried on from.**

```python
    carried_on = Session("milestone").load()
    _, messages = run(
        provider(),
        "Say thank you.",
        permissions=Permissions(auto_approve=True),
        history=carried_on,
        on_message=session.append,
        usage=usage,
    )
    if len(messages) <= len(carried_on):
        fail("resuming did not carry the old conversation forward")
```

Look at the first line. It builds a **new** `Session` object with the same name
and loads from disk, rather than reusing the messages the previous `run`
returned in memory. That is the difference between testing resume and testing a
variable. The only thing connecting the two runs is a file, which is precisely
the claim being made.

Nine messages became eleven, one user and one assistant.

Note also what is deliberately not passed. No `system`. The loaded history
already carries the system prompt as its first message, and `if system and not
messages` in the loop is what makes that safe. Section 4 covered why.

**Five. A refused tool call really did not touch the file.**

This is the one to read carefully, and it is last because it is the most
important.

```python
    denied = Session("denied")
    (workspace / "other.py").write_text("x = 1\n", encoding="utf-8")
    run(
        provider(),
        'Change it. [[tool:edit_file:{"path": "other.py", "old": "x = 1", "new": "x = 2"}]]',
        permissions=Permissions(ask=lambda name, arguments: DENY),
        on_message=denied.append,
    )
    if (workspace / "other.py").read_text(encoding="utf-8") != "x = 1\n":
        fail("a refused edit changed the file anyway, which is the bug this check exists for")
```

A file is written with known contents. A `Permissions` is built whose `ask`
function refuses everything, which is possible only because `check` returns a
boolean instead of running the call itself. The model asks for an edit. Then the
file is read back and compared against the original bytes.

Now the weak version of this test, which is easy to write and looks fine.

```python
if "refused" not in result:
    fail("the call was not refused")
```

That asserts that a string appeared in a message. A string appearing in a
message is the cheapest thing in this entire program to make happen. It requires
no gate to work. It requires no file to stay unmodified. It requires nothing
except a `print` statement in the right branch, and a branch that prints the
refusal and then falls through to run the tool anyway would pass it.

That is not a hypothetical bug shape. It is one of the most common real defects
in permission code, and it appears in a specific way. Somebody refactors the
chain of `if` and `elif` in the loop, or adds a new branch above the permission
check, and the refusal branch stops being exclusive with the execution branch.
The screen still says refused. The file changes anyway. Every log line looks
correct.

So this claim asserts on the bytes. `x = 1\n`, exactly, compared against what is
on the disk after a full real run with a real loop and a real `tools.run` in the
program. For that to pass, the refusal must have been the reason the call did
not happen, not a message printed alongside it happening.

The habit generalises far past this check. When you test anything with a
language model inside it, find the side effect and assert on that. Assertions on
prose are assertions on the one part of the system that can be convincingly
wrong, and a refusal that is only printed is a refusal that has not happened.

### Running it yourself

From inside the lesson folder with an endpoint configured.

```bash
cd lessons/18-the-harness
python check.py
```

Or every lesson at once against the built in mock server, which is what CI runs.

```bash
python ci/run_lessons.py
```

If the first `OK` fails and the file still says `return a - b`, the edit did not
reach the disk, and the place to look is whether `AGENTPATH_WORKSPACE` was set
before the imports. If the second fails, the session callback is not firing
inside the loop. If the third reports zero prompt tokens, usage is not coming
back from the provider. If the fourth fails, `history` is not being copied into
`messages`. And if the fifth fails, stop and read the branch structure in
`agent.py`, because something is running a call the user refused.

## 7. Honest limits, and what part 4 does about each

You have a harness. Three things it cannot do, each one a chapter of part 4.
These are not oversights, they are the syllabus.

### It can only use the tools you wrote

Count them. `read_file`, `write_file`, `edit_file`, `list_files`, `run_shell`,
`glob_files`, `grep_files`, `search_notes`. Eight, all of them in `tools.py`, all
of them written by you.

That sounds like a lot until you want a ninth. Ask this agent to look at a row in
your database, or open a page in a browser, or read a ticket, or post to a chat,
and the answer is that you go and write a tool. Then you write another one, and
another, and each one needs a schema, a dispatch entry, error handling and a
`check.py`. Meanwhile someone else has already written a perfectly good tool for
that database and there is no way at all to use theirs, because a tool in this
program is a Python function in a module that must be imported into this
process.

The seam that made part 2 work is exactly the seam that closes here.
`tools.run(name, arguments)` looks up a name in a dictionary of Python
functions, so anything that is not a Python function in that dictionary does not
exist as far as the agent is concerned. The world is full of capability that
this design cannot reach.

**Lesson 19, the MCP client.** A protocol where tools live in a separate process
and are described over a pipe, so a tool becomes something you connect to rather
than something you write. You write the client yourself, synchronously, stdio
only, because the point is understanding the protocol rather than importing
somebody's SDK. And it comes with a cost that is not obvious until you have four
servers connected at once, which is that tool schemas are sent on every single
request. Connect enough servers and half your context is gone before the task
starts, and the model also picks the wrong tool more often, because forty tools
with overlapping descriptions is a harder choice than eight.

### It does everything itself, in one conversation

Every message goes in one list. The system prompt, your task, every file it
read, every tool result, every dead end.

Lesson 14 made that survivable rather than solved. Watch what `fit_to_budget`
actually does when the budget is reached. It drops the oldest blocks. Those are
the ones containing your original task, the file it read first, and the reason it
chose the approach it is currently three quarters of the way through.

So on a genuinely large job, the shape of the failure is not a crash. It is
worse. The agent gets slowly stupider as the run goes on, forgetting the earliest
and most load bearing parts of its own reasoning, and there is no error anywhere
because trimming worked exactly as designed. It just quietly threw away the
instructions.

Trimming cannot fix this, and neither can a bigger window, because both are
answers to the wrong question. The real problem is that one conversation is
being asked to hold a task that does not fit in one conversation.

**Lesson 20, subagents.** An agent that can start another agent with its own
fresh context, hand it one narrow piece of work, and get back an answer instead
of a transcript. The parent's conversation grows by one short result rather than
by forty tool calls. That chapter also has the failure mode that comes free with
it, which is that parent and child now see different versions of the world. The
child edited a file, the parent is still reasoning from what it read before, and
isolating the child's context, which is the thing that made it sharp, is exactly
what makes this worse.

**Lesson 21, multi agent patterns.** An orchestrator and parallel workers over
threads and a queue, which is where you find out which parts of your harness were
quietly assuming one agent. The session file, for one. `session.py` says
in its own docstring that it supports a single writer, and two workers appending
to the same file will interleave their lines and corrupt it.

### You cannot tell whether a change made it better or worse

This is the limit that should bother you most, and it is invisible because
nothing about it produces an error.

Open `prompt.py` and change `BEHAVIOUR`. Add a sentence telling the agent to
always run the tests before saying it is done. Now answer one question. Did that
help?

You cannot. You can run it on a task and watch, but a model is not deterministic,
so the run you just watched would have gone differently a second time with no
change at all. You can run it twice and prefer the second, which is measuring
noise. What you actually have is a feeling, and a feeling formed from two runs on
one task, on one model, with one phrasing.

That is not a small gap. It means every improvement you make to the most
important text in the program is unfalsifiable. It means you cannot tell whether
a cheaper model would do this job just as well, so you either pay for the
expensive one everywhere out of superstition or switch to the cheap one and find
out from a user. And it means that when the agent starts behaving worse after
three weeks of small changes, you have no way to find which change did it.

**Lesson 22, evals and choosing a model.** A task runner that executes a fixed
set of tasks and checks the outcome, and an LLM as judge for the outcomes that
cannot be checked mechanically. The mock server makes the machinery free to test.
And the reason model selection lives in that chapter rather than its own is that
the two questions are the same question. Saying one model is better than another
without a test set is guessing, and once you have a test set, choosing a model
becomes an experiment you run rather than an opinion you hold. It also covers
tiering, since summarising a file or classifying an error does not need your most
expensive model.

## 8. Exercises

These are worth doing. Each one is small enough to finish in an evening and each
one makes you touch a seam from a direction the chapters did not.

### One. A read only permission mode

Add a mode that allows every read and refuses everything else, with no
questions asked in either direction.

The obvious use is running the agent on a repository you do not trust, or letting
it explain a codebase to you with a guarantee that it cannot change anything
while it does. It is also the mode you want the very first time you point this
thing at something you care about.

Sketch. Give `Permissions` a `mode` and make `check` respect it.

```python
class Permissions:
    def __init__(self, ask=None, auto_approve=False, mode="normal"):
        self.mode = mode
        ...

    def check(self, name, arguments):
        if name in SAFE_TOOLS:
            return True
        if self.mode == "read_only":
            return False
        ...
```

Then a flag in `main.py`, and it should be a closed choice so a typo is caught
by argparse rather than by silently getting the wrong mode.

```python
    parser.add_argument("--mode", choices=["normal", "read-only"], default="normal")
```

Four things to think about while you do it, and they are the actual exercise.

**Where the check goes in the order.** Put `read_only` above the `SAFE_TOOLS`
test and reading stops working, so the agent can do nothing at all. Put it below
`auto_approve` and `--yes --mode read-only` silently allows writes, which is the
worst possible combination because the person who typed both flags believed the
stricter one won. Decide which flag wins and write a comment saying so.

**What the model is told.** The loop already sends back a sentence saying the
user refused. That sentence is wrong here, because no user refused anything and
the model will keep trying variations hoping for a different answer. A refusal
that says the reason is a refusal a model can plan around, and it should probably
say that this session is read only and that writing is not available at all.

**Whether the model should know before it tries.** The other approach is to not
send the write tool schemas at all in read only mode, so the model never sees
that `edit_file` exists. That is a real design decision with a real trade off.
It is cleaner and saves tokens, which is lesson 15's argument. It also means the
model cannot tell you what it would have changed, which is often the thing you
wanted from a read only run.

**How you would prove it.** Write the check before the code. It should look like
claim five in section 6. Write a file, run the agent with a task that tries to
change it, and compare the bytes afterwards. Do not assert on any message.

### Two. Make the session record how long each turn took

Right now a session tells you what happened and says nothing about when. Add
timing, so you can open a session file and see that the run took ninety seconds
and that eighty of them were one `run_shell` call.

The naive version is one line in `Session.append`.

```python
    def append(self, message):
        message = dict(message, at=time.time())
        ...
```

Do that first, then notice the four problems, which are the exercise.

**It changes the message.** `append` currently writes what it was given. Now it
adds a field, so the file no longer matches what was sent to the provider.
Reload that session with `--resume` and you are sending the provider messages
with an `at` key it did not ask for. Some providers ignore unknown fields and
some reject the request, so this is a bug that appears on one model and not
another. Decide whether `load` strips it, or whether the timestamp lives
somewhere other than inside the message.

**A timestamp is not a duration.** What you want to know is how long a step took,
and that is a subtraction between two timestamps. Which two, exactly? The gap
between the assistant message and the tool result before it is thinking and
network time. The gap between a tool call and its result is the tool. Those are
different numbers with different causes and lumping them together tells you
nothing about which one to fix.

**Which clock.** Use `time.time()` and you get a wall clock number you can read
as a date, which drifts and can jump backwards when the system clock is adjusted,
occasionally producing a negative duration. Use `time.monotonic()` and your
durations are always correct and the number is meaningless on its own. The
answer is probably both, and knowing why is the point.

**Where the boundary is.** `Session` currently knows nothing about turns. It
receives messages. If you want per turn timing, either the session starts
inferring turn boundaries from roles, which gives it opinions and breaks the rule
from section 2 that the recorder does not decide, or the loop tells it, which
means a new parameter and a wider contract. Both are defensible. Pick one and be
able to say why.

When it works, run the agent on something real and look at the file. The number
that surprises you is the thing to optimise, and it will almost certainly not be
the thing you would have guessed.

### Three. Make the retry helper say what it is doing

`with_retries` currently waits in complete silence. A run that hits three 429s
with exponential backoff sits there for something like fourteen seconds with a
blank screen, and the person watching cannot tell the difference between a retry
and a hang. So they press Ctrl+C, and now you have lost a run that was about to
succeed.

Give it a callback in exactly the way the rest of this program gives things
callbacks.

```python
def with_retries(call, attempts=4, sleep=time.sleep, on_retry=None):
    ...
            if on_retry:
                on_retry(attempt, attempts, wait, error)
            sleep(wait)
```

The reason it is a callback rather than a `print` is the whole point of the
exercise, and it is the same reason `on_message` is a callback. A module that
prints has a terminal baked into it. This one is going to be called from CI,
from a test, and in lesson 21 from four worker threads at once, where four
modules all printing to the same stream produces interleaved nonsense.

Then wire it in properly, which is the second half.

```python
from retry import with_retries

def stream(self, messages, tools=None, on_text=None):
    return with_retries(lambda: self._stream_once(messages, tools, on_text))
```

Rename the existing method to `_stream_once` and you will immediately meet the
complication lesson 17 warned about. A retried stream restarts from the
beginning, so any text already printed through `on_text` prints again, and the
user sees half an answer twice. Two honest fixes exist. Buffer in the caller and
print only when the stream completes, which costs you the streaming feel that
lesson 05 built. Or only retry before the first byte arrives, which keeps the
feel and gives up on recovering from a mid stream failure. Pick one, write down
what you gave up.

Prove it against the mock server, which can be told to fail on demand with the
`X-Mock-Fail` header that lesson 17's check uses. Assert that `on_retry` fired
the number of times you expected and that the delays it reported grew. Pass a
fake `sleep` that appends to a list, the way lesson 17 does, so your check
finishes instantly instead of actually waiting fourteen seconds.

### Four, if you want a harder one

Close the cancellation gap from section 4. Make `run_shell` consult the
cancellation token so that Ctrl+C during a sixty second command actually kills
the subprocess rather than waiting for it.

This is harder than it looks and that is why it is here. `subprocess.run` blocks
until the process exits, so there is no place to check a flag. You will need
`subprocess.Popen`, a loop that polls with a timeout while checking the token,
and a `terminate` followed by a `kill` when the polite request is ignored. Then
you need to get the token into `tools.py` without giving every tool a new
parameter, which is a seam question rather than a threading question, and it is
the real subject of the exercise.

## 9. This is the end of part 3

Three parts done. Look at what each one was actually for.

**Part 1, lessons 00 to 06, was foundations.** It started with one HTTP request
to a model and finished with an agent loop that streams, calls tools, and talks
to two different wire formats through one interface. The important thing it
taught is that a language model is text in and text out, that everything else is
a convention built on top of that, and that a conversation is resent in full on
every single request. Almost every cost and limit in the rest of the course
follows from that last fact.

**Part 2, lessons 07 to 11, was real tools.** Files with one gate for every path.
A shell with a person standing in front of it. Glob and grep, with the argument
for why that is the right answer for code rather than a placeholder for something
fancier. A system prompt that tells the model both how to behave and where it is.
It ended with an agent that could be pointed at a folder it had never seen and
fix a bug in it. The thing it taught, more than any individual tool, was that the
seam between the loop and the tools is what lets you add the eighth tool as
easily as the first.

**Part 3, lessons 12 to 18, was the harness.** Permission that remembers what you
decided, so the gate still works at the fortieth prompt. Sessions as plain JSONL,
which turn out to be the best debugging tool in the project. Context management,
including the trap where trimming between a tool call and its result gets the
next request rejected outright. Token economy, where the money actually goes and
why anything that changes goes last. Retrieval, and the four questions you ask
before reaching for it. Errors, retries, idempotency and an interrupt that stops
the work rather than the screen. And this chapter, where all of it runs at once
against a real directory and the disk is checked afterwards.

Part 3 did not make your agent more capable. It made it operable. Those are
different things and this was the part that made the difference visible.

**Part 4, lessons 19 to 23, is about the limits of one agent with tools you
wrote.** Every limit in section 7 has the same shape. The agent is alone, it can
only use what is in `tools.py`, it works in one conversation, and you have no
instrument for telling whether any change you make is an improvement.

Lesson 19 connects it to tools it did not write, over MCP, with a client you
build yourself. Lesson 20 lets it start other agents so a large job stops being
one conversation. Lesson 21 runs several of them at once and makes you find out
which parts of your harness quietly assumed there would only ever be one. Lesson
22 gives you the instrument, which is a task runner and a judge, and turns
choosing a model from an opinion into an experiment. Lesson 23 packages the
whole thing so somebody else can install it.

Before you go on, do two things.

Run `python ci/run_lessons.py` from the repository root and watch every check
pass, including this one.

Then run `main.py` on something of your own that is genuinely broken, with a real
session name, and let it work for longer than feels comfortable. Afterwards, open
the session file and read the whole thing. That file is the most useful artifact
part 3 produced, and the first moment in it where the agent did something you did
not expect is the best possible preparation for part 4.

On to lesson 19.
