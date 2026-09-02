# Changelog

## 1.0.6

The package has a front door. An import of agentpath gave you a version
number and nothing else, so somebody who installed it and wanted an agent
had to guess that Agent lives in agentpath.agent and that ToolRegistry is
two levels down. What is exported is the list the project's own command
line imports, on the argument that a name the CLI never needs has not yet
earned a place at the front. The deeper paths still work and still say
more about where a thing lives.

A py.typed marker ships with the package. The type hints were always
written and, without that file, PEP 561 says every type checker on every
machine that installs this is required to ignore them.

Both READMEs show how to drive the agent from Python rather than only from
the command line, and a test runs that example in a fresh process against
the mock server. It is extracted from the README rather than copied, so
there is one version of it. Deleting the example fails the test rather
than quietly retiring it.

## 1.0.5

Published as agentpath-kit rather than agentpath. The index refused the bare
name as too similar to agent_path, an abandoned template placeholder, which
a request for the exact name cannot detect because the exact name is free.
The package it installs is still called agentpath, so the import, the
command and the three environment variables are unchanged, the same way
scikit-learn installs sklearn.

The source distribution carried the whole repository, three hundred and
fifty files, because hatchling reads include patterns the way git reads
gitignore and a bare README.md matched all twenty six of them. Anchored with
a leading slash it is thirty six files.

Chapter 23 and book chapter 16 both taught that a 404 on the name means the
name is free. It does not, and this project is the counter example, so both
now say so and show the two name arrangement that made the refusal survivable.


The loop fingerprint no longer folds letter case or interior spaces. It made
three genuinely different case sensitive searches look identical, so a model
widening a pattern from Error to error was told it was going in circles and
stopped. Only leading and trailing space is ignored now. The 1.0.3 note
below describes the fingerprint as blind to case, which was true when it was
written and is not anymore.

The credential gate's refusal now says the file will not be touched rather
than read, because the same gate refuses writes and the old wording told
somebody who tried to overwrite .env that reading was the problem.

Chapter 16 showed build_index and search_notes calling names that
retrieval.py does not define, so a reader typing them out got a NameError.
The chapter now shows the code that is in the folder and explains the
_from_tools helper it had been assuming.

Three new test files hold the classes of bug that reviews kept finding by
hand. Every tool in the registry is asked the same security questions, a new
tool cannot ship unclassified, every lesson copy is run in its own process
and asked what the library gets asked, and a function a chapter shows whole
has to appear in the shape the folder has.

## 1.0.4

Command output on Windows was decoded as utf-8 whatever the command actually
wrote. Two encodings turn up on the same machine, because a modern tool
writes utf-8 while most of the programs that ship with the system write the
old console codepage, and decoding the second as the first turned every
accented or non Latin character into a replacement mark without a word of
complaint. Output is now decoded by trying utf-8 first, which fails loudly on
the wrong input, then the codepages the machine actually uses.

A second and separate problem sat behind it. Listing a directory holding a
Thai file name printed question marks, which is not a decoding failure at
all. The shell cannot write those characters in the old codepage, so they
were destroyed before we saw the bytes, and decoding cannot recover what was
never encoded. The console is now put into utf-8 once before any shell is
started.

Putting chcp at the front of the command, which is the obvious fix, does not
work reliably and is worth knowing about. A shell builtin such as dir reads
the codepage when the shell starts, which is before the chcp on the same
command line runs, so the first command of a session still lost the name and
every command after it was fine.

Both fixes also reached the sixteen lesson copies of the shell tool, which
had none of this and none of the timeout fix either, so the course was
teaching two bugs.

## 1.0.3

Eleven bugs from a second review, and one of them was introduced by the
first. The no progress check added in 1.0.1 decided a run had stalled when a
tool returned the same text three times, which a command that succeeds
quietly does for every different thing it does, so it stopped real work.
Reading progress from the shape of the output is not something a cheap check
can do correctly and it has been removed. The case it was written for, a
model retrying with the arguments nudged, is handled soundly now with a
fingerprint blind to whitespace and letter case.

Also. Abandoned tool calls are filled in even when an interrupt lands inside
a tool, which is the one path where it matters. The search deadline runs in a
separate process, because neither a check between lines nor a thread can stop
a regular expression that is already running. The MCP client honours its
timeout and its servers are closed when a run ends. Anthropic usage is read
from both places it appears rather than one. A tool call delta with no index
starts a new call instead of merging. Reusing a session name no longer adds a
second system prompt. An eval task whose agent fails to build is one failure
rather than a lost report. Retrieval survives an unreadable path.

## 1.0.2

Sixteen tests that run the command line as a real process, which is the gap
that let every bug in 1.0.1 through. Each one was verified by putting the
bug it guards back and watching it fail, and two of them did not fail on the
first attempt, which is the reason this release also changes the fake model
server. It can now answer with several tool calls in one message, the way a
real model does, so the paths that only appear when a turn is abandoned part
way through can be reached at all.

## 1.0.1

Everything found by a full review of the finished course. Nothing here was
caught by the test suite, which is the part worth noticing.

Security. The search and retrieval tools walked the workspace themselves
instead of going through the one gate every file tool uses. Because rglob
follows symlinks and Windows junctions, a link planted inside the workspace
let them read anything on the machine while read_file correctly refused.

Correctness. A run started with --yes refused every shell command it had
already approved, because the shell tool asked a second question of its own.
The shell timeout reported a timeout and killed nothing, so the call waited
for the whole command anyway. Stopping mid turn left tool calls with no
matching result, which makes the next request fail. One interrupt disabled
the shell for the rest of a chat session. Running out of turns printed a
traceback. Resuming added a second system prompt every time. Parallel evals
merged tasks that share a name. A model supplied regular expression could
wedge the process forever. And the loop detector missed a model retrying
with its arguments nudged, which is the case it was written for.

Content. Roughly forty factual errors across the chapters, including two
chapters telling readers to look for code that had already been removed and
two telling them to add code that was already there. The two mandatory
topics the specification asked for and the chapters had missed are now
written. The prose lint enforces all three content rules rather than two.

## 1.0.0

Part 4, Advanced. The course is complete at 24 chapters.

- An MCP client written by hand, speaking the stdio transport, so tools other
  people wrote become tools this agent can use
- A tiny MCP server for testing, so the client can be proved to work with
  nothing installed from outside this repository
- Subagents, which are ordinary tools whose implementation runs another agent
- Parallel work through threads and one queue, with each event labelled by the
  job it came from
- An eval runner with mechanical checks and an optional judge, plus the
  agentpath eval command whose exit code lets continuous integration refuse a
  change that made the agent worse
- Lessons 19 to 23 in English and Thai

## 0.3.0

Part 3, The Harness.

- A permission system that remembers an answer instead of asking again
- Sessions saved as JSONL, written as the run happens rather than at the end
- Context management that treats a tool call and its result as one unit, so
  trimming can never leave a result with no call in front of it
- Token accounting taken from what the provider reports rather than guessed
- Retrieval, and a chapter about when not to use it
- Retries that respect Retry-After and carry jitter, plus cancellation that
  stops real work rather than only the display
- Lessons 12 to 18 in English and Thai

## 0.2.0

Part 2, Real Tools.

- File tools with one gate deciding which paths may be touched, and an editor
  that refuses an ambiguous match
- A shell tool that asks before it runs anything
- Search by file name and by content, and the argument for why that beats a
  vector database for code
- A system prompt that states the facts the model cannot see
- Lessons 07 to 11 in English and Thai

## 0.1.0

Part 1, Foundations.

- One HTTP request to a model, with nothing hiding the wire
- Conversation history, tool calling, and the agent loop
- Streaming, including reassembling tool arguments that arrive in fragments
- One agent loop that works with two different provider dialects
- Lessons 00 to 06 in English and Thai
