# Changelog

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
