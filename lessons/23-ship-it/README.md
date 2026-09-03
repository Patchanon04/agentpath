[อ่านภาษาไทย](README.th.md)

# Lesson 23. Ship it

This is the last chapter, and it invents nothing.

Lesson 18 opened with the same sentence and meant it as a measurement. This one
means it as a closing statement. There is no new mechanism left to add, because
the thing is finished. What remains is to look at what you actually built, name
the one idea that survived all twenty four chapters, turn the code into
something another person can install, and be honest about the edges.

Here is the folder and where every file came from.

```text
lessons/23-ship-it/
  tools.py             621 lines   identical to lesson 19
  providers.py         208 lines   identical to lesson 18
  mcp.py               189 lines   identical to lesson 19
  evals.py             205 lines   identical to lesson 22
  agent.py             140 lines   identical to lesson 18
  retrieval.py         169 lines   identical to lesson 16
  check.py             117 lines   new
  main.py              115 lines   identical to lesson 18
  mock_mcp_server.py   104 lines   identical to lesson 19
  context.py            80 lines   identical to lesson 18
  fanout.py             80 lines   identical to lesson 21
  permissions.py        94 lines   identical to lesson 18
  retry.py              67 lines   identical to lesson 18
  subagent.py           61 lines   identical to lesson 20
  session.py            56 lines   identical to lesson 18
  usage.py              48 lines   identical to lesson 18
  prompt.py             55 lines   identical to lesson 10
  cancel.py             31 lines   identical to lesson 18
grep_worker.py        51 lines   identical to lesson 09

  README.md                        this file
```

Eighteen modules, one new file, and that new file is a check.

## 1. What you have

Be plain about it, because the temptation at the end of a course is to inflate,
and an inflated ending teaches you to misjudge the next thing you build.

You have 2374 lines of Python across eighteen files. Add the chapter's check
and it is 2491. That is smaller than most single source files in the frameworks
people install to avoid writing this, and it is small enough that you could
read the whole thing in an afternoon, which is the only property that made it
worth teaching.

The only dependency outside the Python standard library is `httpx`. Not one
thing in this folder imports an agent framework, a model provider SDK, an
embedding library, a vector database, a CLI toolkit, a retry library, or a
tokeniser. The check enforces that rather than trusting it.

```python
ALLOWED_OUTSIDE_THE_STANDARD_LIBRARY = {"httpx"}
```

It reaches that verdict by walking every `.py` file in the folder, collecting
the top level name of every `import` and `from` statement, subtracting anything
in `sys.stdlib_module_names` and anything that is one of the course's own
modules, and comparing what is left against that set.

```python
    third_party = {
        name
        for name in imported
        if name not in sys.stdlib_module_names
        and name not in {m for m in MODULES}
        and name not in {"__future__"}
    }
    if not third_party <= ALLOWED_OUTSIDE_THE_STANDARD_LIBRARY:
        fail(f"something reaches for an unexpected dependency, {third_party}")
```

That is a stricter claim than a `requirements.txt` with one line in it, because
a requirements file records what you meant and this records what the code does.
If somebody adds `import tiktoken` in a helper three chapters back, this fails
on the next push.

Run the whole check the way continuous integration does.

```bash
python ci/run_lessons.py
```

The part of the output that belongs to this chapter is exactly this, and it was
captured by running it.

```text
OK all 15 modules import cleanly

[calling read_file with {'path': 'calc.py'}]
[read_file returned def add(a, b):
    return a - b
]

[calling edit_file with {'path': 'calc.py', 'old': 'return a - b', 'new': 'return a + b'}]
[edit_file returned Edited calc.py]
The tool returned Edited calc.py.
OK the finished agent still fixes a real bug in a real file
OK the session and the usage counter are working, 3 calls, 118 prompt tokens, 30 completion tokens
OK all 8 tools from parts 2 and 3 are present
OK the only dependency outside the standard library is {'httpx'}
```

Five claims, and none of them is about a new feature. This chapter's check asks
a different question from every other one in the course. Not does the new thing
work, but is the whole thing shippable. Every module imports on its own with no
hidden ordering. The finished agent still does the exact job it could do in
lesson 11, which is the regression test for eleven chapters of additions. The
session and the counter from part 3 are alive inside a full run. Every tool from
parts 2 and 3 is present. And nothing reaches for a dependency the reader was
never told to install.

Named plainly, this is what those files are.

| What | Where | Chapter |
| --- | --- | --- |
| An agent loop that streams and calls tools | `agent.py` | 04, 05 |
| Two wire formats behind one interface | `providers.py` | 06 |
| Eight tools, files, shell and search | `tools.py`, `retrieval.py` | 07, 08, 09, 16 |
| A system prompt that says where it is | `prompt.py` | 10 |
| A gate that decides and does not run | `permissions.py` | 12 |
| The conversation on disk as JSONL | `session.py` | 13 |
| Trimming that never touches what is remembered | `context.py` | 14 |
| A counter that reports rather than estimates | `usage.py` | 15 |
| Retries around the network call only | `retry.py` | 17 |
| An interrupt that stops work, not the screen | `cancel.py` | 17 |
| A hand written MCP client over stdio | `mcp.py` | 19 |
| A whole agent presented as one tool | `subagent.py` | 20 |
| Parallel runs over threads and a queue | `fanout.py` | 21 |
| A task runner and a judge | `evals.py` | 22 |
| A command line | `main.py` | 18 |

## 2. The four parts, told as one story

Four parts, one line of argument. Read them in order and the shape of the course
is a single claim being extended.

Part 1, lessons 00 to 06, said that a model is an HTTP endpoint. Lesson 01
sent one POST request with a list of messages in the body and got a list of
messages back with one more on the end. There was no library in the way, so
there was nowhere for magic to hide. Lesson 02 discovered that the model
remembers nothing and that the whole conversation is resent on every request,
which is the fact almost every cost and limit later in the course descends from.
Lesson 03 showed that a tool call is not a special capability, it is the model
emitting a name and a JSON argument object and waiting for you to hand back a
string. Lesson 04 wrapped that in a `for` loop. That loop was the first agent,
and it is the same loop you have today.

Part 2, lessons 07 to 11, gave it hands, and introduced the first real
danger. Reading and editing files, running shell commands, glob and grep. The
capability arrived with the problem attached, because the moment an agent can
write to your disk and run commands in your shell, the text it reads becomes a
security boundary. Lesson 08 put a person in front of the shell tool on the
first day rather than as a later hardening pass. Lesson 09 made the case that
grep beats a vector index for code and made you feel why. Lesson 10 pointed out
that a tool description is prompt engineering that most people never edit.
Lesson 11 pointed the whole thing at a folder with a real bug and it fixed it.

Part 3, lessons 12 to 18, turned an agent into something survivable. Not
more capable, survivable. A permission gate that remembers your answer so it
still gets read at the fortieth prompt. Sessions as plain JSONL, which turned
out to be the best debugging tool in the project. Context management, including
the trap where trimming between a tool call and its result gets the next request
rejected outright. Token economy, where the money actually goes. Retrieval, and
the four questions you ask before reaching for it. Errors, retries, and an
interrupt that stops the work rather than the screen. Lesson 18 ran all of it at
once against a real directory and then checked the disk.

Part 4, lessons 19 to 23, connected it outward and let you measure it.
Lesson 19 wrote an MCP client by hand so a tool became something you connect to
rather than something you write, and then priced it honestly, because tool
schemas are resent on every request and four servers can eat your context before
the task starts. Lesson 20 made a whole agent into one tool so a long
investigation stops filling the parent's conversation, and named the trap that
comes free with it, which is that the parent and child now hold different views
of the world. Lesson 21 ran several at once over threads and a queue and made
you find out which parts of your harness quietly assumed there would only ever
be one. Lesson 22 gave you the instrument, so a change to the system prompt
became something you can test rather than something you can feel.

## 3. The one idea worth carrying away

If you keep one sentence from twenty four chapters, keep this one.

**Across nineteen chapters of new capability, the agent loop changed only when a
subsystem was added, and never when a tool was added.**

That is not a slogan. It is a measurement, it was taken twice, and the second
time is in this folder.

### The measurement

Lesson 18 listed every difference between the loop in lesson 04 and the loop at
the end of part 3. Fourteen differences. Two came from streaming, two from the
provider abstraction, two from the system prompt, one from permissions, three
from sessions, one from context management, two from token economy, one from
errors and interruption. Zero came from adding a tool, and that included lesson
16, which built a vector index, an embedder and a scorer, and left `agent.py`
byte for byte unchanged.

Part 4 is the second half of the measurement and it is a harder test, because
part 4 added the four things most likely to demand changes at the centre. Tools
that live in another process. Agents that start agents. Several agents running
at the same time. A test harness that runs the agent many times over.

```bash
cd lessons
for d in 19-mcp-client 20-subagents 21-multi-agent 22-evals 23-ship-it; do
  diff -q 18-the-harness/agent.py $d/agent.py > /dev/null 2>&1 \
    && echo "agent.py in $d is identical to 18-the-harness" \
    || echo "agent.py in $d DIFFERS"
done
```

```text
agent.py in 19-mcp-client is identical to 18-the-harness
agent.py in 20-subagents is identical to 18-the-harness
agent.py in 21-multi-agent is identical to 18-the-harness
agent.py in 22-evals is identical to 18-the-harness
agent.py in 23-ship-it is identical to 18-the-harness
```

Five chapters, four major features, and the most important function in the
program was not opened once. The only file that moved was `tools.py`, from 604
lines to 621, when lesson 19 taught it to accept a tool whose implementation
lives behind a pipe.

Look at how each part 4 feature landed, because the pattern is the same four
times.

| Feature | How it arrived | What the loop saw |
| --- | --- | --- |
| MCP servers | schemas and a dispatch entry added to `tools.py` | more tools |
| Subagents | `run_subagent`, a tool whose body calls `run` | one more tool |
| Parallel agents | `fanout.py`, which calls `run` from threads | nothing, it is above the loop |
| Evals | `evals.py`, which calls `run` many times | nothing, it is above the loop |

`subagent.py` says it in its own first paragraph.

```text
There is no new machinery here. A subagent is a tool whose implementation
happens to run another agent. The parent sees a tool with a name and a
description, exactly like read_file, and the loop does not change at all.
That is the point worth noticing rather than the code.
```

### Why this is a law and not a coincidence

It would be easy to read that table as luck, or as the author choosing
convenient examples. It is neither, and the reason is structural. The two
categories differ in exactly one property, which is what the new thing needs to
see.

A tool needs only its own arguments, and returns a value. `read_file` gets a
path. `grep_files` gets a pattern and a glob. `run_shell` gets a command. None
of them needs to know that a conversation exists, how many turns have happened,
what the budget is, or what the model said last. They take input and produce a
string. That contract already existed after lesson 03, so a new tool is a new
row in a dictionary and a new entry in a list of schemas. There is nowhere for
it to touch the loop, because it never learns the loop is there.

That is why an MCP tool and a subagent both slid in without a fight. An MCP tool
is a function that writes JSON down a pipe and reads JSON back. A subagent is a
function that runs another agent. Both are arbitrary Python behind the same
contract, and the contract was never about what the function does.

A subsystem needs to observe or intercept something the loop owns, at a moment
only the loop controls. Permissions must run in the gap between the model
asking for a call and the call happening, and nothing outside the loop can stand
in that gap. Sessions must see each message at the instant it is created, which
is why writing the file at the end is a different and worse program. Context
management must alter the payload after the message list exists and before it is
sent. Cancellation must be read between turns. Usage must be added after the
provider reports it.

Those five things cannot be done from outside, so each of them required a seam
in `run`. That is the whole difference. Not importance, not size, not how hard
the code was. Just whether the new thing needs access to the engine's private
moments.

### The rule for recognising it elsewhere

Ask one question of anything you are about to add to a system with a loop, a
dispatcher or a scheduler at the middle of it.

**Does this need to see state the engine owns, at a moment the engine chooses?**

If the answer is no, it is a leaf. It goes behind a contract that already
exists, and the engine must not learn its name. If you find yourself adding a
branch that mentions the new thing by name, you have misclassified a leaf, and
lesson 12 is the example. The shell confirmation started inside `run_shell`,
where it made the tool untestable and unusable without a terminal, and moving it
out to `permissions.py` is what lets lesson 22 run the whole suite from CI with nobody at a
keyboard.

If the answer is yes, it is a subsystem, and it needs a seam. Design the seam so
it is generic rather than specific to the feature that motivated it, because
that is what stops the count of seams growing with the count of features.
`on_message` is a function of one argument, so it serves the session file, a
test that appends to a list, and a socket, identically. `permissions.check`
returns a boolean, so a test can build one that refuses everything and hand it
into a real run. `fit_to_budget` returns a new list, so trimming can never
corrupt the record.

The same boundary is everywhere once you have a name for it.

- **A web framework.** Adding a route never changes the dispatcher, because a
  handler takes a request and returns a response. Adding authentication,
  request logging, rate limiting or tracing does, because each needs to sit
  between the dispatcher and the handler. Every mature framework answers with
  middleware, which is `on_message` and `permissions.check` under another name.
- **A build tool.** Adding a task is data. Adding caching, parallelism or a
  progress display touches the scheduler, because each needs to know when a task
  starts and finishes.
- **A database client.** Adding a query is data. Adding connection pooling,
  retries or query timing is a subsystem, because each needs the moment before
  and after the wire call.
- **A game engine.** Adding an entity is data. Adding pause, replay or a
  deterministic seed touches the frame loop.

The failure mode is never that you cannot add the subsystem. It is that you add
it as a branch instead of a seam. The first branch is reasonable and the second
one is too. By the fifth, the engine is the file every feature must pass
through, it is four hundred lines long, nobody dares edit it, and adding the
sixth feature risks the five that already work. Both designs run the same
program on the day you finish them. They diverge on day thirty, and this course
is the thirty day version of that experiment, run in public, with the hashes
kept.

## 4. Packaging it

The lessons folder is deliberately a pile of flat files, because a course where
chapter four silently depends on an edit you made in chapter two is a course
people abandon. But a pile of flat files is not something you can give to
somebody. `src/agentpath/` is the same ideas written once and properly, and this
is the file that turns it into an installable package.

Here is the whole thing.

```toml
[project]
# The distribution is agentpath-kit and the package it installs is
# agentpath, which is a mismatch on purpose. PyPI refused the bare name as
# too close to agent_path, an abandoned PDM template placeholder. Splitting
# the two is the ordinary Python answer, the same way scikit-learn installs
# sklearn, and it leaves the import, the command and the environment
# variables alone.
name = "agentpath-kit"
version = "1.0.6"
description = "Learn how AI agents actually work by building a real one, from a single LLM call to a full agent harness."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
dependencies = ["httpx>=0.27"]
# Labels for the PyPI page and its filters. They change nothing about
# the install, and leaving them out leaves the page blank where it
# should say which Python and which license.
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Education",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Topic :: Education",
]

[project.urls]
Homepage = "https://github.com/Patchanon04/agentpath"
Changelog = "https://github.com/Patchanon04/agentpath/blob/main/CHANGELOG.md"

[project.scripts]
agentpath = "agentpath.cli:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
# numpy is used by the foundations track and by the numpy demos in the
# training track. The package and the twenty four lessons stay on httpx
# alone, and a person who wants only those never installs it.
foundations = ["numpy>=1.26"]
# Part 4 of the book. The numpy demos in training/ need only the group
# above. The real fine tuning scripts need these, and a GPU, and are not
# run in CI.
training = ["torch>=2.2", "transformers>=4.46", "peft>=0.12", "trl>=0.20", "datasets>=2.20"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# The sdist is what pip falls back to, so it carries only what building
# the package needs. The course itself lives in the repository, and the
# README says where.
[tool.hatch.build.targets.sdist]
include = ["/src", "/README.md", "/CHANGELOG.md", "/LICENSE"]

[tool.hatch.build.targets.wheel]
packages = ["src/agentpath"]

[tool.ruff]
line-length = 100
exclude = ["lessons"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Sixty six lines, ten tables, and every line is doing something. Take them one
at a time.

### The project table

This is the standardised metadata table. The reason it is worth learning rather
than copying is that it is declarative and tool independent. Ten years ago this
information lived in `setup.py`, which was a Python script that ran at install
time and could do anything at all, including inspect your machine and decide
what your package was. Moving it to static data in `pyproject.toml` means a tool
can read what your package is without executing your code, and that is why
installers can now resolve dependencies without downloading and running
arbitrary source.

`name` is the identity. It is what somebody types after `pip install`, and
it must be unique across the whole of the Python Package Index. Section 5 is
about that being harder than it sounds.

`version` was `1.0.0` when part 4 shipped and reads `1.0.6` today after six
patch releases, and the first three numbers follow the course rather than the
calendar. The design document made one part equal one release, so part 1 shipped
as `0.1.0`, part 2 as `0.2.0`, part 3 as `0.3.0`, and part 4, which is the part
this chapter closes, as `1.0.0`. The reason for tying releases to parts rather
than to chapters is that a part is the smallest unit of the course that is
useful on its own. Shipping a version whose value only appears three chapters
later is shipping a half built thing. The reason the last one is `1.0.0` rather
than `0.4.0` is that the course is finished at twenty four chapters, and a `1.0`
is a statement that the shape is settled rather than a claim that the code is
flawless.

The version also appears in `src/agentpath/__init__.py` as `__version__`, and
keeping two copies in step by hand is a known way to publish a package that
reports the wrong number. Hatchling can read the version out of the source file
instead, and the reason this project has not done that yet is that it is one
more piece of build magic between the reader and the file, which is a trade the
project's second principle usually loses.

`description` is one line and it is the tagline. It becomes the sentence
under the name in search results, so it is the only prose most people will ever
read about the project.

`readme` points at `README.md`, whose entire contents get copied into the
package metadata at build time and rendered as the project page. That is worth
knowing because it means the README is shipped inside the wheel, not linked
from it. Here is the top of the metadata from the wheel this chapter built.

```text
Metadata-Version: 2.5
Name: agentpath-kit
Version: 1.0.6
Summary: Learn how AI agents actually work by building a real one, from a single LLM call to a full agent harness.
Project-URL: Homepage, https://github.com/Patchanon04/agentpath
Project-URL: Changelog, https://github.com/Patchanon04/agentpath/blob/main/CHANGELOG.md
License: MIT
License-File: LICENSE
Classifier: Development Status :: 5 - Production/Stable
Classifier: Intended Audience :: Education
Classifier: License :: OSI Approved :: MIT License
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3 :: Only
Classifier: Topic :: Education
Requires-Python: >=3.10
Requires-Dist: httpx>=0.27
Provides-Extra: dev
Requires-Dist: pytest>=8.0; extra == 'dev'
Requires-Dist: ruff>=0.6; extra == 'dev'
Provides-Extra: foundations
Requires-Dist: numpy>=1.26; extra == 'foundations'
Provides-Extra: training
Requires-Dist: datasets>=2.20; extra == 'training'
Requires-Dist: peft>=0.12; extra == 'training'
Requires-Dist: torch>=2.2; extra == 'training'
Requires-Dist: transformers>=4.46; extra == 'training'
Requires-Dist: trl>=0.20; extra == 'training'
Description-Content-Type: text/markdown
```

Every one of those lines came from the project table.

`requires-python` is a promise that gets enforced by the installer rather
than discovered by the user. Without it, somebody on Python 3.8 installs the
package successfully and then gets a `SyntaxError` or an `AttributeError` from
the middle of your code, which reads like your package is broken. With it, `pip`
refuses the install and says why.

The bound is `>=3.10` for concrete reasons rather than fashion. `check.py` in
this folder uses `sys.stdlib_module_names`, which arrived in 3.10 and is what
lets the dependency claim above be checked at all. The path confinement in
`tools.py` uses `Path.is_relative_to`, which arrived in 3.9. Setting the floor
by finding the newest thing you actually use is the right method. Setting it to
whatever you happen to be running is how you exclude half your users for nothing.

`license` matters more than it looks in a teaching project. MIT means
somebody can take this code into a commercial product without asking. A project
with no license at all is not public domain, it is fully copyrighted with no
permission granted, so an unlicensed tutorial is legally unusable by exactly the
people it was written for.

### Dependencies

```toml
dependencies = ["httpx>=0.27"]
```

One line, and getting there was the point of the whole course. Every chapter
that could have added a dependency instead built the thing and explained it.
`argparse` rather than a CLI framework, because the standard library is
adequate. `fnmatch` and `re` rather than a search library. A hand rolled
embedder in lesson 16 rather than a vector database. A hand written MCP client
in lesson 19 rather than the official SDK. Each of those is a place a reader
could have got stuck on something that was not the subject.

The specifier is a lower bound and not a pin, and the difference matters. Pin it
with `==0.27.2` and anybody who installs your package alongside something else
that needs a newer `httpx` gets an unresolvable conflict, and the only fix is
for you to publish a new version. A library should express the oldest version it
is known to work with and let the application decide the rest. Pinning exactly
is correct for an application you deploy, and wrong for a package other people
install.

Now the honest part. One dependency line is not one package. Here is what a
clean environment actually contains after installing this wheel.

```text
Package           Version
----------------- ---------
agentpath         1.0.0
anyio             4.14.2
certifi           2026.7.22
h11               0.16.0
httpcore          1.0.9
httpx             0.28.1
idna              3.19
pip               22.3.1
setuptools        65.5.0
typing_extensions 4.16.0
```

Seven packages arrived because of one line. That is not an argument against
`httpx`, it is an argument for knowing what your dependency list expands to
before you claim to be small. `certifi` alone is a bundle of root certificates
that your program now trusts. Run this on your own projects and the number will
usually surprise you.

### The console script entry point

```toml
[project.scripts]
agentpath = "agentpath.cli:main"
```

Two words and a colon on the right hand side. The left is the command name that
will exist on the user's `PATH`. The right is an import path and a callable,
separated by a colon, meaning import the module `agentpath.cli` and call the
function `main` in it with no arguments.

What the installer does with that is generate a small executable at install time
and put it in the environment's scripts directory. That is why it works
immediately with no shell configuration and no `chmod`, and why it points at the
right Python even when three versions are installed. It is recorded in the wheel
as a plain text file.

```text
[console_scripts]
agentpath = agentpath.cli:main
```

Two obvious alternatives lose. Shipping a shell script means writing it twice,
once for `sh` and once for Windows, and hardcoding an interpreter path that is
wrong on every machine but yours. Telling people to run `python -m agentpath` is
free and works, but it makes the tool feel like a script rather than a program,
and it puts the interpreter in every command a user ever types or writes into a
makefile. The entry point costs one line and removes both problems.

The one thing to be careful about is that `main` must be callable with no
arguments and should return an exit code rather than call `sys.exit`. That is
why `cli.py` and `main.py` both end the same way.

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

### Optional dependencies

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]
```

`pytest` and `ruff` are needed to work on the project and are not needed to use
it. Putting them in `dependencies` would install a test runner and a linter into
the environment of every person who ever installed this package to run an agent,
which is rude and, in a container image, measurable.

They are still declared rather than written in a contributing guide, because a
declared group can be installed by one command that cannot go stale.

```bash
uv pip install -e ".[dev,foundations]"
```

That is the same line the README gives contributors and the same line
continuous integration runs, and the `foundations` extra is numpy for the
two tracks either side of the course, which is the property that matters. A setup step
that only humans follow drifts away from the one the machine follows, and the
drift is discovered on the day somebody's pull request fails for a reason they
cannot reproduce.

### The build system table

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

This is the table people copy without reading, so it is worth being clear about
what it means. It says that in order to turn this directory into a distributable
package, a tool should first create an isolated environment, install `hatchling`
into it, and then call the standardised build interface at `hatchling.build`.

The reason this exists as a declaration rather than an assumption is history.
For years the build tool was `setuptools`, universally, implicitly, and any
project that wanted a different one had a bootstrapping problem, because the
instructions for how to build it were written in the thing you had to build. The
standard fixed that by making the build backend a piece of static data that any
frontend can read first. `pip`, `build` and `uv` all understand this table, so
the package builds identically no matter which one you use.

`hatchling` rather than `setuptools` for two reasons that are both about the
reader. It needs no `setup.py` and no `MANIFEST.in`, so this file is the only
build configuration in the project, and its defaults for a `src` layout are
close enough to correct that the only override needed is one line.

That one line is the next table.

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/agentpath"]
```

This is required because of the `src` layout. The importable package is
`agentpath`, but on disk it is at `src/agentpath`, and without this line the
backend would have to guess whether to ship a top level directory called `src`
or a top level directory called `agentpath`. The line says ship the contents of
`src/agentpath` as the package `agentpath`.

The `src` layout is worth the extra line for a reason that shows up in exactly
one situation, which is testing. With the package at the repository root,
`import agentpath` from the root directory finds the source tree whether or not
the package is installed, because the current directory is on `sys.path`. So
your tests pass against your working copy and tell you nothing about whether the
thing you are about to publish is complete. With a `src` layout the source is
not importable by accident, so tests run against the installed package, and a
module you forgot to include fails immediately instead of after publishing.

### Tool configuration

```toml
[tool.ruff]
line-length = 100
exclude = ["lessons"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Every `[tool.*]` table is namespaced for one tool, which is the mechanism that
lets one file hold configuration for everything instead of a repository root
full of dotfiles.

`exclude = ["lessons"]` is the interesting entry, and it encodes a decision from
the design document rather than a preference. Lesson code is duplicated across
twenty four folders on purpose, so a linter pointed at it would report the same
finding twenty four times and an import sorting rule would fight the deliberate
bottom of function imports that lesson 18 spent a section explaining. The
framework in `src/` is held to the linter. The teaching snapshots are held to
the checks instead.

`testpaths = ["tests"]` stops `pytest` from collecting the lessons folder, where
twenty four files named `check.py` would be found, and imported, and would
promptly start talking to a model.

## 5. Publishing, honestly

Packaging metadata is a description. Publishing is the act. There are four
steps, and the order of two of them is where people get hurt.

### Build the artifacts

```bash
python -m build
```

```text
* Creating isolated environment: venv+pip...
* Installing packages in isolated environment:
  - hatchling
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist
* Creating isolated environment: venv+pip...
* Installing packages in isolated environment:
  - hatchling
* Getting build dependencies for wheel...
* Building wheel...
Successfully built agentpath_kit-1.0.0.tar.gz and agentpath_kit-1.0.0-py3-none-any.whl
```

Read what it did, because it explains the `[build-system]` table from the last
section. It created a fresh environment, installed `hatchling` into it, built a
source distribution, and then built the wheel from that source distribution
rather than from your working directory. That last detail is deliberate on the
tool's part. Building the wheel from the sdist proves the sdist is complete,
because if a file is missing from it the wheel build fails right there instead
of six months later when somebody tries to build your package from source.

Two artifacts came out and they are different things.

The **wheel**, ending in `.whl`, is a zip file of the tree exactly as it should
appear once installed. Installing it is an unzip and a metadata write. There is
no build step on the user's machine, which is why wheels made Python installs
fast and reliable.

The **sdist**, ending in `.tar.gz`, is the source. It exists for the people and
systems that need to build the package themselves, such as a distribution
packager, an air gapped build, or an architecture you did not publish a wheel
for.

### Look inside before you publish

Open the wheel. It is a zip file, so nothing special is needed.

```bash
python -c "
import zipfile
z = zipfile.ZipFile('dist/agentpath_kit-1.0.0-py3-none-any.whl')
for name in sorted(z.namelist()):
    print(name)
"
```

```text
agentpath_kit-1.0.0.dist-info/METADATA
agentpath_kit-1.0.0.dist-info/RECORD
agentpath_kit-1.0.0.dist-info/WHEEL
agentpath_kit-1.0.0.dist-info/entry_points.txt
agentpath_kit-1.0.0.dist-info/licenses/LICENSE
agentpath/__init__.py
agentpath/agent.py
agentpath/cancel.py
agentpath/cli.py
agentpath/context.py
agentpath/evals/__init__.py
agentpath/evals/runner.py
agentpath/fanout.py
agentpath/mcp.py
agentpath/permissions.py
agentpath/prompt.py
agentpath/providers/__init__.py
agentpath/providers/anthropic.py
agentpath/providers/base.py
agentpath/providers/openai_compat.py
agentpath/retry.py
agentpath/session.py
agentpath/subagent.py
agentpath/testing/__init__.py
agentpath/testing/mock_mcp_server.py
agentpath/testing/mock_server.py
agentpath/tools/__init__.py
agentpath/tools/base.py
agentpath/tools/files.py
agentpath/tools/retrieval.py
agentpath/tools/search.py
agentpath/tools/shell.py
agentpath/tools/workspace.py
agentpath/types.py
agentpath/usage.py
```

That is the whole framework and nothing else. No `lessons`, no `tests`, no
`docs`, no `.github`. Fifty one kilobytes.

Now look at the sizes of the two files together, because this is where this
project found a real problem by looking.

```text
agentpath_kit-1.0.0-py3-none-any.whl  50.7K
agentpath_kit-1.0.0.tar.gz            1.3M
```

The source distribution is more than twenty five times the size of the wheel.
Count what is in it.

```text
  242  lessons
   30  src
   25  tests
    6  docs
    2  ci
```

The sdist swept the entire repository, including all twenty four lesson folders
in both of the languages the course ships in. There is an argument that the
lessons are the source here, but somebody installing the package wants the
package, and the course is one click away in the repository, so this project
trimmed it.

The fix is a `[tool.hatch.build.targets.sdist]` table listing what to include,
and it has one trap in it that cost a build.

```toml
[tool.hatch.build.targets.sdist]
include = ["/src", "/README.md", "/CHANGELOG.md", "/LICENSE"]
```

Every one of those patterns starts with a slash, and the first attempt did not.
Hatchling reads these the way git reads `.gitignore`, so a bare `README.md`
means a file called README.md at any depth, and this repository has twenty six
of them. The sdist came out at three hundred and fifty files instead of thirty
six, and it looked plausible enough that only counting the files caught it. The
leading slash anchors the pattern to the root.

The lesson is bigger than the fix. **Look at what you built before you publish
it**, because the default for what goes into a source distribution is generous,
the patterns that narrow it do not mean what they look like they mean, and
nobody discovers a two hundred megabyte sdist until a stranger complains.

### Test the install in a clean environment, before publishing rather than after

This is the step that gets skipped, and skipping it is why so many first
releases are followed within an hour by a second one.

The reason it must be a clean environment is specific. Your package builds from
your working tree, but it is imported from `sys.path`, and on your machine those
overlap. A module you forgot to list, a data file that never made it into the
wheel, a dependency you use but never declared because it was already installed
for something else, all of these work perfectly on the machine that built them
and fail on the first machine that did not. Your development environment is the
one place in the world that cannot detect this class of bug.

So build a venv with nothing in it, install the wheel by path, and drive the
thing.

```bash
python -m venv fresh
./fresh/bin/pip install dist/agentpath_kit-1.0.0-py3-none-any.whl
./fresh/bin/agentpath --help
```

On Windows the scripts live in `fresh/Scripts/` rather than `fresh/bin/`, which
is where this chapter's run was captured.

```text
usage: agentpath [-h] {chat,run,eval,resume} ...

positional arguments:
  {chat,run,eval,resume}
    chat                Talk to an agent in the terminal
    run                 Do one task and exit
    eval                Run a file of tasks and report which ones passed
    resume              Continue a saved session, or list sessions when given
                        no name

options:
  -h, --help            show this help message and exit
```

Four things were proved by that one command and none of them by the build. The
wheel installed. The entry point generated a real executable named `agentpath`
on the `PATH` of that environment. That executable found `agentpath.cli`,
imported it, and called `main`. And every import that `cli.py` performs at module
level resolved from what was inside the wheel plus the one declared dependency,
because there was nothing else in that environment for them to resolve from.

Go one step further and run the thing for real against your model, or against
the project's mock server. `--help` proves the package is importable. It does
not prove the package works.

The order is the entire point. Publishing is one way. A version number on the
package index can never be reused, even if you delete the file, which is a
deliberate rule that protects everybody who already depends on it. So a broken
`1.0.0` is not something you fix, it is something you replace with `1.0.1` while
the broken one stays visible forever. Ten minutes in a fresh virtual environment
buys you the ability to never do that.

### Publishing needs an account and a token

The upload itself is the short part.

```bash
python -m twine upload dist/*
```

Three things have to be true first.

You need an account on the package index, and you should have one on TestPyPI as
well, which is a separate service with separate accounts that exists precisely so
that your first ever upload can be a mistake. Upload there, install from there
into a fresh environment, and then do the real one.

You need an API token rather than a password. Generate it in your account
settings, scope it to the single project if the project already exists, and use
`__token__` as the username with the token as the password. The reason to prefer
a token is that it can be revoked on its own without changing your password, and
a project scoped token that leaks cannot touch anything else you own. Put it in
`~/.pypirc` with restrictive permissions, or in an environment variable, or in
your continuous integration secret store. Do not put it in the repository. A
token committed once is a token that must be revoked, because deleting the commit
does not delete it from anybody's clone.

And you need two factor authentication on the account, which the index now
requires for anyone who publishes.

### The name has to be free, and you should find that out early

The name in `[project]` must be unique across the entire index, and there are
several hundred thousand names already taken. Checking it is one request.

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/agentpath/json
```

```text
404
```

A `404` means no project by that name exists, so the name is free. A `200` means
it is taken. Do this before anything else, and be aware that names are also
normalised, so `agent_path`, `agent-path` and `Agent.Path` all collide with each
other.

This project checked. The line is still in the design document, written before a
single file existed.

```text
- ชื่อโปรเจกต์ agentpath (ตรวจแล้ว PyPI ว่าง, GitHub แทบไม่มีคู่แข่ง)
```

Which says the project name is `agentpath`, checked, PyPI is free, and there is
almost no competition on GitHub. It cost about thirty seconds and it was worth
doing then rather than later, because look at how far the name had already
travelled by the end of part 3.

### The check above is necessary and it is not sufficient

That request returned `404` for `agentpath` and the upload was still refused.
Here is the exact reply.

```text
This project name is too similar to an existing project
```

The index does not only reject a name that is taken. It rejects a name close
enough to an existing one that somebody typing from memory could land on the
wrong package, which is a real defence against a real attack. A project called
`agent_path` already existed. Normalised it is `agent-path`, which is not equal
to `agentpath`, so the request said free, and the similarity check said no.

The paragraph above about normalisation was right about which names collide and
wrong about the question it answers. Equality tells you whether the name is
taken. It tells you nothing about whether the name is allowed. There is no
public request that answers the second question, so the honest advice is to
upload to TestPyPI early, because the refusal arrives there for free and it
arrives on the day you pick the name rather than the day you ship.

The thing that made this survivable is that the name on the index and the name
you import do not have to match. This package is published as `agentpath-kit`
and installs a package called `agentpath`, which is the same arrangement that
has you install `scikit-learn` and import `sklearn`, or install `pillow` and
import `PIL`.

```toml
[project]
name = "agentpath-kit"
```

That one line was the entire fix. The import path, the console script, the three
environment variables, the repository, and every code block in twenty three
chapters all kept the name they had. Had the two names been required to match,
the rewrite described in the paragraph above is exactly what this would have
cost. It is the import path in every one of these
files. It is the console script. It is the three environment variables that every
lesson and the framework read. It is the repository name, the directory name in
every command in every chapter, and the first word of the tagline. Discovering a
collision after part 3 would not be a rename. It would be a rewrite of twenty
three chapters of prose, every code block in them, and every environment variable
name, and it would break every reader who had already set them up.

One last note, and it is not a formality. If you followed this course and built
your own copy, do not publish it as `agentpath`. Pick your own name, check it
with the request above, and put it in your `pyproject.toml` before you build.

## 6. Things worth adding next, with the honest cost of each

The course is frozen at twenty four chapters. That is a rule in the design
document rather than a shortage of ideas, and it exists because the project's
third principle says every feature must be able to answer what it teaches, and
one that cannot answer is refused. Ideas that arrived after the freeze live in
`docs/v2-ideas.md`, and being in that file means not dead rather than accepted.

Two things were added after the freeze and it is worth saying why neither
broke the rule. A foundations track of seven short chapters sits before lesson
01, in `foundations/`, for the reader who does not yet know what a token is. A
training track of five sits after lesson 23, in `training/`, for the reader who
wants to fine tune and serve a model of their own. The rule exists to stop good
ideas piling into the course until it never finishes. Neither track takes
anything from the twenty four, neither teaches the harness, and both are frozen
at their own count by the same rule, so the argument the rule makes still
holds.

Here are the five in that file. Each one is genuinely worth building. Each one
costs something, and the cost is the part that usually goes unsaid.

### MCP over HTTP

Lesson 19 built a client that speaks stdio only. The client starts a server as a
subprocess and talks JSON-RPC over its pipes, so every server you can use is a
program on your own machine that you launched yourself.

It buys servers you did not start and do not host. A team can run one
server for its internal systems and every agent in the company connects to the
same URL. It also removes the requirement that the server be installable on your
machine at all, which matters the moment a server needs credentials or a database
connection you do not have locally.

The cost is that everything that was free about a subprocess stops being free.
A pipe to a process you started needs no authentication, because the operating
system already decided you may run it. An HTTP endpoint needs authentication,
which means tokens, which means token storage and rotation. A subprocess dies
when you do, so there is no session lifetime to manage. A remote server does
not, so the transport has to handle reconnection and streamed server events.
And the trust story changes shape entirely. A local server runs as you, with
your files. A remote server is somebody else's code holding your requests, and
every tool description it sends you goes straight into your model's context,
which is a prompt injection surface owned by a third party.

### Async

The entire project is synchronous on purpose. `fanout.py` says why in its
opening paragraph.

```text
Threads rather than async, for the same reason the rest of the project is
synchronous. An agent run spends nearly all of its life waiting on a socket,
which is the case threads handle well, and async would put a second mental
model in front of a reader who came here to learn about agents.
```

It buys thousands of concurrent agent runs in one process instead of
dozens. If you are building a service where many users share one machine, this is
not a preference, it is the only design that works, because a thread costs
megabytes of stack and an awaiting coroutine costs kilobytes.

The cost is that it is contagious. `async def` at the bottom means `await` all
the way up, so the provider, the loop, every tool, the MCP client and the CLI
all change. You cannot half do it, and a synchronous call left in the middle
blocks the entire event loop and produces a performance bug that looks like a
network problem. The note in the ideas file adds the condition that matters for
this project. If it is ever done, it has to be justified by what it teaches, not
by how fast it is, because the reader came to learn how agents work and the event
loop is a second subject.

### A real vector database

Lesson 16 deliberately taught the decision rather than the technology. Four
questions in order. Is the data small enough to just put in the context. Is it
structured with a known query, in which case use SQL. Is it text an agent can
walk itself, in which case use the grep from lesson 09. Only if all three answer
no does vector search earn its place, and the chapter then built it as an
ordinary tool to show it is not a special system.

It buys scale and quality that a hand written embedder in a hundred lines
cannot reach. Real embeddings, an approximate nearest neighbour index that
stays fast at millions of documents, metadata filtering, incremental updates
without a full rebuild, and persistence across processes.

The cost is a service to run and back up, or a hosted one to pay for. An
embedding model, which means either another API bill on every document and every
query or a local model and the memory it needs. An index that goes stale, which
is the failure nobody plans for, because a stale index does not error, it just
confidently returns the old version of the file. And for the use most readers
have in mind, which is code, lesson 09's argument still stands, because
identifiers are exact and grep does not hallucinate a match.

### Observability and tracing

Right now you have two instruments. `Usage` tells you what a whole run cost, and
the session file tells you what happened in order. Both are excellent and both
are per run, local, and after the fact.

It buys the ability to answer questions about runs in aggregate, which
is a different kind of question from the ones a session file answers. Which tool
fails most often. Which step is slow, and whether it is the model or the shell.
What the ninety fifth percentile latency is. Whether the change you deployed on
Tuesday made things worse. With spans you get a nested timeline of one run
instead of a flat list, and the nesting is what makes a subagent's work legible
inside its parent's.

The cost is a collector to run and storage to pay for, both of which are
operational work that has nothing to do with agents. Instrumentation code
threaded through the loop, the provider and the tools, which is exactly the kind
of thing that turns into a branch in the loop if the seam is designed badly.
Section 3 applies directly here, because tracing is a subsystem by the test given
there, and the right shape for it is a callback rather than an import at the
centre. And the sharpest cost is privacy. A trace that captures prompts and tool
results is a copy of every file your agent read, sitting in somebody else's
system, and that decision has to be made deliberately rather than discovered.

### Running the agent in a sandbox

This is the one with the largest gap between what the harness promises and what
it enforces. `tools.py` confines file paths to the workspace and `run_shell` runs
with `cwd` set to it. That is a real gate, and it is a gate inside your own
process. `run_shell` will happily run a command that reads a file outside the
workspace, or opens a network connection, or installs a package, because
`subprocess.Popen` inherits everything your process can do.

It buys the ability to give an agent a task and go and do something else.
Everything the permission system is for becomes structural rather than a
question you have to keep answering correctly at the fortieth prompt, and
lesson 12's point about prompt injection changes character entirely, because a
successful injection then reaches a container rather than your laptop.

The cost is that the agent stops sharing your world, and that is the whole
difficulty rather than a detail. Files have to be mounted in and results copied
out. Your tools, credentials and language versions are not in there unless you
put them there, so the container image becomes something you maintain. Startup
time goes from nothing to seconds, which is fine for one long task and painful
for an interactive session. And the sandbox has to actually be one, because
network isolation, filesystem isolation and resource limits are three separate
settings, and a container with the default network is not isolated from anything
that matters.

## 7. What this course did not cover, and why

Four subjects that people expect in something called a course on AI agents and
that are not here. None of them was left out because it is unimportant. They were
left out because a harness is a specific thing and these are not it, and a course
that covers everything adjacent to its subject covers its subject badly.

Fine tuning takes a base model and continues training on your own examples so
it behaves differently by default. It is a real technique with real uses,
mostly narrowing a model to a specific format or domain. It is absent because it
changes what is behind the endpoint, and everything in this course is in front of
it. Every design decision here holds no matter which model answers, which is what
the provider abstraction in lesson 06 was for. Also, and more practically, it is
the wrong first tool. Almost every problem that people reach for fine tuning to
solve turns out to be a prompt problem, a tool description problem, or a context
problem, and lesson 22 exists so you can tell which one you have before spending
money finding out.

Training is building a model. This is a different field with different
prerequisites, different mathematics and different hardware, and it shares
almost no engineering with the subject of this course. The design document says
in its opening section that there is no maths here, and that is a promise about
who the course is for rather than a statement about what is worth knowing.

Prompt optimisation at scale is automated search over prompt variants, where a
program generates candidates, scores them against a dataset, and keeps the
winners. Lesson 22 built the foundation this needs, which is the eval suite,
because a search with no scoring function is not a search. What is missing is the
search on top. It is out of scope because it is a research subject with a moving
frontier, and because it needs a dataset of tasks large enough for the scores to
mean something. Write the eval suite first. If you build one and find yourself
editing the prompt and rerunning it by hand for the twentieth time, you have
earned the right to automate that loop, and you will know exactly what you want
from it.

Running agents as a hosted service means multi tenancy, queues, per user
isolation, autoscaling, billing, an authenticated API in front of it, and the
whole operational surface underneath. This is genuinely the next thing many
readers will need. It is also a distributed systems subject rather than an agent
subject. The agent shaped part of it is one paragraph long, which is that a
hosted agent needs the async model from section 6 and the sandbox from section 6,
and everything else about it is what you already know about running any service.
A course that added it would spend four chapters teaching web operations under an
agent shaped title.

There is a rule sitting under all four, and it is the third principle from the
design document. Every feature must be able to say what it teaches, and one that
cannot is refused. That rule is what kept this project to twenty four chapters and 2374 lines. It is a good rule to steal.

## 8. How to keep learning from here

Three things, in order. They are concrete on purpose, because the general advice
to keep building is worth nothing.

### Read the source of a harness you actually use

Pick the agent tool you already use every day and read its source, or its
protocol if the source is closed. Not a tutorial about it. The code.

You are now in the unusual position of being able to do that profitably, which
you were not twenty three chapters ago. You know what to look for, because you
know what the parts are called and what the hard decisions were. Find the loop.
Find where permissions live and whether they decide or execute. Find whether the
session is written as it happens or buffered. Find what it does when the context
window fills. Find whether its retries wrap the network call or something wider.

Every one of those is a question you have already answered once, so the
interesting part is where their answer is different from yours. Sometimes it is
because they were wrong. More often it is because they had a constraint you did
not, and finding out what that constraint was is the fastest way to learn
something you could not have derived on your own.

Start with the tool schemas, because they are the easiest thing to extract and
the most revealing. Every harness sends its tool descriptions to the model on
every request, so they are visible from the outside, and reading somebody's tool
descriptions is reading their entire theory of how the model should behave.

### Write an eval suite for a task you care about

Lesson 22 gave you the machinery. Use it on something real, and start smaller
than feels serious. Ten tasks from your own work, each with a mechanical check
that returns true or false.

Then use it to answer one question you currently have an opinion about. Does the
cheaper model actually do this job. Does that sentence you added to the system
prompt help. Does raising the budget change anything.

The habit this builds is worth more than any individual answer, and it transfers
to everything else you will build with a model in it. `evals.py` puts it plainly
in its own docstring.

```text
Everything before this chapter was built on the assumption that you can tell
a good change from a bad one by looking at it. You cannot. A wording change
in a system prompt can fix one task and quietly break three others, and the
only way to know is to run a set of tasks before and after.
```

Expect the first result to be uncomfortable. The most common outcome of a first
eval suite is discovering that a change you were sure about does nothing, and
that is the suite working.

### Build one tool for something you do by hand every week

Not a project. One tool. A function with a JSON schema and a dispatch entry, in
the shape you have written eight times already.

Pick it by the boring criterion rather than the interesting one. Something you
genuinely do every week, that you are tired of, that is mostly reading and
transforming rather than deciding. Querying your own database. Pulling the
current state of your tickets. Checking which of your services are on old
versions. The dull ones are the right ones, because you will notice immediately
whether the agent version is actually better, and there is no better teacher than
using your own tool on a Tuesday afternoon when you are busy.

Three things will happen, and all three are the point.

You will find that writing the tool is easy and writing the description is hard,
which is lesson 10 arriving as experience rather than as a claim. You will find
that the first version returns too much, and that trimming what a tool returns is
most of the work, which is lesson 15. And you will find out whether the seam holds
in a codebase you did not design as a teaching example, which is section 3
getting its first honest test.

If it turns out somebody already published an MCP server for that system, connect
it with lesson 19 instead and write nothing. Knowing which of the two situations
you are in is itself a thing you can now do.

## 9. A closing note

Twenty four chapters ago you sent one HTTP request with a list of messages in it.

You can now build the thing that stands around a model and makes it useful. A
loop that calls tools until the work is done. A gate that decides what may run. A
record on disk you can read afterwards. Trimming that does not corrupt that
record. A count of what it cost. Retries that do not repeat the things that must
not be repeated. An interrupt that stops the work. A protocol for tools you did
not write. Agents that start agents. Several running at once. And a way to
measure whether any change you make is an improvement.

None of that came from the model. Every part of it is ordinary engineering, and
the loop at the middle of it is fifty lines that have not changed shape since
lesson 04. The model was always the part somebody else built.

The interesting part was never the model. It was everything you had to put around
it.
