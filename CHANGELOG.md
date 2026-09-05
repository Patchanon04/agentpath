# Changelog

## Unreleased

A foundations track, for the reader who does not yet know what a token
is. Seven folders in foundations/ and seven chapters as part 0 of the
book. Text to bytes and why Thai costs three, a byte pair tokenizer from
nothing and the two corpus experiment that shows the price of a language
is a property of what the tokenizer saw, a language model that counts and
loops at temperature zero, the same model that learns by gradient descent
in eighty lines, word vectors and why cosine ignores length, one head of
attention on four tokens with the quadratic cost as a table, and the chat
template built by hand with a prompt injection at the marker level. Every
folder runs without an API key and has a check.py that pins the numbers
its chapter quotes. numpy is an optional group, used here and later by the training demos.

The book has a rhythm. The first draft opened three hundred and sixty
eight paragraphs with a bold label and all sixteen chapters with the same
sentence, and read like a reference card. STYLE.md gains a section of
rhythm rules that can be checked by reading. All sixteen chapters are
rewritten to them, each opening on the problem it is about rather than on
a list of what the reader will have, and every foundations chapter is
written to them from the start. Every code block in the book is byte for
byte what it was, and the drift tests say so. Chapter 16 also catches up
with the package as shipped, showing the pyproject.toml that is on PyPI
and the sdist pattern that has to start with a slash.

The course was read against eight books on language models and AI
engineering, and the gaps were filled. In the foundations track, top p
and beam search with the run that shows why chat models sample instead
of searching, perplexity as the loss a person can read, embeddings that
are learned rather than counted, position vectors and the experiment
that shows attention is order blind without them, the rest of the
transformer block, the KV cache with the check that it gives exactly
what masked attention gives, the four tokenizer families, hallucination
as the same mechanism that makes a model answer at all, scaling laws,
when to fine tune, and the encoder decoder split. In the lessons, few
shot examples with a helper in lesson 10, reranking and recall at k in
lesson 16, and a pairwise judge that asks twice with the order swapped
in lesson 22, each pinned by check.py. In the book, output guardrails
in chapter 5 and the forty year old agent frame in chapter 8.

Part 4 of the book, fine tuning and serving a model of your own, with a
training/ track of five folders. Three of the five, LoRA, quantization and
DPO, have a numpy demo on the grid the foundations trained, checked in CI,
and a real script with transformers, peft and trl that needs a GPU and is
not. The dataset and serving folders are plain Python at both layers.
Dataset engineering with exact
and near deduplication, decontamination and a report per step. LoRA on
a grid you can count, with the run that shows forgetting is real and
rehearsal is the cure. Quantization at eight and four bits with the loss
measured next to the bytes, and QLoRA. DPO with the loss that starts at
log two, and the drift that shows the reference is the leash. And the
arithmetic of serving, weights, cache, concurrency and the bandwidth
bound on decode, ending in the vLLM command that points the whole
course at the model you trained. A training extra in pyproject lists
the real dependencies.

A second review pass over every chapter, checking prose against code.
It found the places where the book had drifted from what the code does.
Chapter 16 quoted a pyproject without the training group, chapter 13
quoted the search subprocess before it learned -I and cwd, chapter 6
said a stop request halts a running stream when the token is only read
at three gates, chapter 5 said auto approve is never the default when a
bare Agent approves everything, chapter 4 said Usage keeps the cache
numbers when the Anthropic provider drops them, and the MCP client
docstring said only a broken server raises when nothing raises. Every
reference to a lesson now says lesson, not chapter, and every reference
to the foundations uses one form. About a hundred smaller fixes in
wording, glosses at first use, and paragraph rhythm, in Thai and
English. The MCP client now reports the real package version.

A third pass, in three parts. The top level documents are audited
against the repository, so the README now describes a book of twenty
eight chapters in five parts, the Thai README gains that section, the
install line for running every check includes the numpy extra that the
foundations and training checks need, and the freeze rule names both
tracks in lesson 23 and the design document. The verbal tics that
flattened the voice of chapters 1 to 16, นั่นคือ, ทั้งหมด, เป๊ะ and the
frame ไม่ใช่ X มันคือ Y, are thinned to the places where they earn it.
And the second pass is re-read for what it broke, which was a claim in
chapter 6 that subagent and eval call tools outside the loop, and seven
places in the foundations that sent readers to book chapter 16 when they
meant lesson 16.

A fourth pass over the twenty four lesson READMEs in both languages,
checked against the code in each folder. The numbers had drifted most.
The agent.py hashes in lesson 18, the line counts and file listings from
lesson 11 onward, which had never listed grep_worker.py, the pyproject and
wheel metadata in lesson 23, still shown at 1.0.0 without the extras and
classifiers, and lesson 15's truncation arithmetic, which described a
tools.py half the size of the real one. The loop's repeat detection is
now described as loose_signature everywhere, rather than the exact
signature it stopped using in lesson 15. Lesson 22 no longer says task
names must be unique when the code keys results by position. Every
mention of subprocess.run in lessons 17 to 23 names Popen and communicate,
which is what run_shell has used since lesson 08. Lesson 06 quotes the
current mock server. Lesson 10 quotes its full check. In Thai, the term
model replaces โมเดล in the eight files that had switched, lesson 06 loses
the English lesson NN references and its English title, part numbers use
ภาค throughout, and the commas, chained ซึ่ง and doubled ทำให้ the style
guide bans are gone from the lesson prose.

The PyPI page now carries classifiers, and chapter 16 of the book, which
quotes pyproject whole, shows them.

Two small changes reach the package. The MCP client tells the server the
real package version rather than a fixed 1.0.0, and a comment in the agent
loop and a docstring in the MCP client now say what the code does. Nothing
else in this section touches src/agentpath, and no release has been cut, so
the wheel on PyPI is still 1.0.6.

The book is a book. book/build_book.py turns the twenty eight chapters into
one 354 page volume, 170 by 240 mm, with a cover, a contents page whose
numbers are the pages the chapters landed on, running heads, page numbers,
part openers on a right hand page, and the figures drawn rather than quoted.
The markdown here is a small regular subset so it is converted directly
rather than by taking a dependency, and paged.js in headless Chrome does the
pagination. Two things about that library drop content with no error at all,
a named page shared by consecutive blocks and a break inside a code block,
so every block goes in stamped and book/audit.js checks that each stamp came
out inside a page box. It reports 2050 of 2050.

The layout was set from how books are set rather than from taste. Paragraphs
are separated by space and never indented, because using both is a belt and
braces pair and because Thai has no capital letters to mark a sentence start.
The measure is about 66 characters, inside the 45 to 75 that reads well. The
leading is 1.75 rather than the 1.2 to 1.45 Latin text is set at, because
Thai stacks vowels above and tone marks above those.

The explanations were rewritten. The style guide's own worked example of a
gloss was a word for word rendering of the English term, and every chapter
had copied the shape, so the guide now shows what a gloss should be and adds
three rules. A gloss says what the thing does rather than translating its
name, it is one short clause, and prose does not sit in the register of an
official document. Against those, 175 of the book's 190 glosses and about
ninety across the lessons were rewritten. gradient descent was การเดินลงตาม
เกรเดียนต์ and now says it moves the numbers against the gradient one step at
a time. Two were wrong rather than stiff, a token defined in terms of words
in the chapter that disproves exactly that, and the mark ◌ั called สระอั in
five places when its name is ไม้หันอากาศ.

Then the concrete work. There were 21 uses of เช่น in 3931 lines of prose and
twelve chapters had none, so the book asserted a great deal a newcomer could
not picture. 121 examples were added to the book and about a hundred to the
lessons, each a short situation with real numbers rather than the word for
example bolted to a claim, and the figure count went from six to twenty in
the book and from zero to twenty four in the lessons.

Thai prose here carries no commas and no full stops, so a space is the only
mark saying a thought has ended, and 130 stretches had run past seventy
characters without one. 142 spaces went back in and nothing else changed,
which a check confirms by removing every space from before and after and
comparing.

Last, the whole book was read start to finish for the first time, because
each pass had worked on a range and none had listened to whether it is one
voice. That found cross references that collided, บทที่ 4 meaning the
learning chapter in one sentence and the context window chapter in the next,
four references pointing at the wrong chapter outright, and openings that had
settled into a formula.

Three checks are new and all three now run in CI. ci/gloss_consistency.py
reports a term explained two different ways, which nothing caught before and
which drifted every time one side was edited. ci/long_runs.py reports Thai
that has run on without the space that ends a thought. book/rewrap.py rewraps
a paragraph an edit left too long, knowing where a Thai line may break and
asserting the rendered paragraph is unchanged.

Part 4's real scripts had never been run, only the numpy demos beside them.
train_lora.py and train_dpo.py now take --cpu, since both set bf16
unconditionally, which is a GPU number format, and a reader without a card
was stopped before the run began. Run that way on the half billion parameter
model, LoRA trains and writes an adapter, and it works with transformers
5.16, trl 1.12 and peft 0.20, all far newer than the floors in pyproject. One
claim did not survive the measurement. The adapter is 8.8 million numbers and
35 megabytes at rank sixteen, not the few megabytes the docstring promised.
launch.py prints the numbers chapter 21 quotes. train_dpo.py runs too, one
step in fifty nine minutes on the CPU, and it reported a loss of 0.6914,
which is the 0.693 chapter 20 opens with, measured on a real model instead
of on the three pair demo. load_4bit.py is still unverified, because four
bit through bitsandbytes needs an NVIDIA card.

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
