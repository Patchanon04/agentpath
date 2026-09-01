[อ่านภาษาไทย](README.th.md)

# Lesson 10. Anatomy of a prompt

This is the last lesson before the milestone, and it is the one with the worst
ratio of effort to effect in the whole course. You are going to write a file
with two names in it and add three lines to the agent loop. Perhaps twenty
lines of Python in total. The agent will not gain a single new capability.

And it will get dramatically better at using the seven capabilities it already
has.

That sounds like magic, and this chapter exists to make sure it does not stay
magic. Everything here has a mechanism, and the mechanism is the same one from
lesson 02. The model sees the conversation and nothing else. Every fact it
uses, every rule it follows, every preference it honours, is either in that
conversation or is not available to it. Prompting is not a way of persuading a
model. It is the act of deciding what is in the conversation.

Files in this folder.

```text
lessons/10-anatomy-of-a-prompt/
  prompt.py      new, builds the system prompt
  agent.py       lesson 09's loop, plus a system message at the front
  tools.py       unchanged from lesson 09, byte for byte
  providers.py   unchanged from lesson 06
  check.py       proves the system prompt exists and arrives first
  README.md      this file
```

Notice `tools.py` on that list. It did not change, and section 6 is largely
about a part of it you have been writing since lesson 07 without being told
what it was.

## 1. The problem left over from lesson 09

At the end of lesson 09 the agent had seven tools.

```text
read_file    write_file    edit_file    list_files
run_shell    glob_files    grep_files
```

That is a complete set. Anything a developer does to a code base can be
expressed as some sequence of those seven. Nothing is missing.

Now start a real conversation and look at what the model actually knows. In
lesson 09 the entire conversation on the first request was one message.

```python
messages = [{"role": "user", "content": user_input}]
```

One sentence, typed by you. That is the whole world. The model does not know
which directory it is standing in. It does not know whether it is on Windows or
Linux. It does not know that `read_file` stops at 4000 characters. It does not
know that searching is cheap and reading everything is expensive. It does not
know that when you say "the config" you mean a file in this repository rather
than a file in its training data.

So it guesses. Not because it is careless, but because a guess is the only
thing available. And a wrong guess does not fail quietly. It costs a whole
turn, which is one full HTTP request carrying the entire conversation, plus the
tokens of the failed attempt, which then stay in the conversation forever.

Here is what that looks like in practice. Three traces, all of them ordinary.

### Guess one, the invented path

You type this.

```text
You: add a docstring to the start function
```

The model has to call a tool. It has no idea where anything is, and it has read
a great deal of Python in its training data, so it produces the most statistically
ordinary path it can imagine.

```text
[calling read_file with {'path': '/home/user/project/src/main.py'}]
[read_file returned Error: /home/user/project/src/main.py is outside the workspace]
```

That is a turn spent. Nothing was learned about your project. The model tries
again with a shorter guess.

```text
[calling read_file with {'path': 'src/main.py'}]
[read_file returned Error: src/main.py does not exist]
```

Two turns spent. On the third it finally calls `list_files`, which is what it
should have done first, and which it would have done first if anybody had told
it that it was standing in an unfamiliar directory rather than in the imagined
average of every Python project ever written.

### Guess two, the Unix command on Windows

You are on Windows. You ask the agent to check the test suite.

```text
[calling run_shell with {'command': 'ls -la && cat pytest.ini'}]
```

The user is now looking at a confirmation prompt for a command that cannot
work. If they approve it, this comes back.

```text
'ls' is not recognized as an internal or external command,
operable program or batch file.
[exit code 1]
```

A turn spent, and worse, a turn that spent a human's attention. Lesson 08 made
the user the last gate before anything runs. Every command the model proposes
that was never going to work is a withdrawal from that person's patience, and
patience is the resource that makes the confirmation gate viable at all. A user
who has clicked no four times starts clicking yes without reading.

The model did not have a preference for Unix. It had no information, and in the
absence of information it produced the most common shape in its training data,
which is a Linux shell because that is what most of the world's shell scripts
are written in.

### Guess three, the wrong tool for the job

This one is the most expensive, and it is silent.

```text
You: change the timeout in config.py from 30 to 60
```

```text
[calling read_file with {'path': 'config.py'}]
[read_file returned TIMEOUT = 30
RETRIES = 3
LOG_LEVEL = "info"
...]
[calling write_file with {'path': 'config.py', 'content': 'TIMEOUT = 60\nRETRIES = 3\n...'}]
[write_file returned Wrote 61 characters to config.py]
```

It worked. That is the problem. Nothing errored, nothing was refused, and the
agent reported success. But `write_file` replaces the entire file with whatever
the model typed out, and the model was reconstructing 61 characters from a read
that may have been truncated at 4000. Any comment it did not bother to repeat,
any line below the truncation point, any blank line it normalised, is gone. The
diff you review is not a one line change, it is a whole file rewrite that
happens to look similar.

`edit_file` exists precisely for this. It replaces one exact piece of text and
touches nothing else. The model had it available and chose the other one,
because nothing in the conversation said which to prefer.

### What all three have in common

None of these is a missing capability. In all three cases the right tool was
sitting in the schema list. What was missing was information.

| The guess | What would have prevented it |
| --- | --- |
| invented absolute path | a sentence stating the workspace directory |
| `ls -la` on Windows | a sentence stating the platform |
| `write_file` over `edit_file` | a sentence stating the preference |

Three sentences. That is the entire content of this lesson, and the rest of the
chapter is about where each sentence goes and why the placement matters more
than the wording.

## 2. The three places your words reach the model

Here is the framing idea of this chapter, and it is worth stating plainly
before any code appears.

There are exactly three channels through which your words reach the model.

**The system prompt.** A message at the front of the conversation, sent before
anything the user said. It is where you put standing instructions and standing
facts. It is written once by you, the developer, and it is present on every
request for the life of the session.

**The user message.** The task. Written by whoever is using your agent, fresh
each turn, and different every time.

**The description of each tool.** A string attached to every function in your
schema list. It is sent on every request alongside the messages, and it is the
only thing the model will ever know about what your function does.

Most people who talk about prompt engineering know about the first two. They
argue about the wording of system prompts, they collect templates, they debate
whether to say "you are an expert" at the top. Almost nobody thinks about the
third one at all, and the third one is where a great deal of the leverage
actually is.

Look at what the provider sends on a single request and the reason becomes
obvious. Here is the shape of the payload from `providers.py`, with the parts
that come from you marked.

```json
{
  "model": "...",
  "stream": true,
  "messages": [
    {"role": "system",    "content": "<- channel one, written by you"},
    {"role": "user",      "content": "<- channel two, written by your user"},
    {"role": "assistant", "content": "..."},
    {"role": "tool",      "content": "..."}
  ],
  "tools": [
    {"name": "read_file", "description": "<- channel three, written by you",
     "parameters": {"...": "..."}}
  ]
}
```

Three of those four marked spots are yours. The `tools` array is not
configuration that sits quietly on the side. It is text, it is in the prompt,
and the model reads it exactly the way it reads the system message. There is no
architectural difference between a sentence in the system prompt and a sentence
in a tool description. They arrive in the same request, they are processed by
the same model, and they compete for the same attention.

The difference is where they sit relative to the decision being made, and
section 6 argues that this difference favours the tool description more often
than people expect.

A fourth channel exists and is worth naming so you do not confuse it with these
three. Tool results, from lesson 07 onwards, are also text you control, and you
have already been engineering them. When `edit_file` returns "Include more
surrounding lines so the match is unique", that is a sentence you wrote,
addressed to a model, intended to change its next action. It is the same
activity under a different name. The only reason it is not counted here is that
it is reactive, sent after something happened, while these three are all present
before the model does anything.

## 3. What belongs in the system prompt

Open `prompt.py`. It is thirty five lines and it does two different jobs that
are easy to confuse.

**Job one is behaviour.** How to work. What to prefer. What to do when things
go wrong. This part is written by you once and never changes between runs.

**Job two is facts.** Things that are true about this particular run, which the
model has no way of discovering without spending a turn on it. Where it is
standing. What operating system it is on. What version of Python is available.
This part is computed fresh every time the program starts.

Keeping them apart matters because they have different lifetimes and different
authors. Behaviour is a design decision you make while writing the agent. Facts
are measurements taken at startup. Mixing them into one hand written string
means somebody eventually hardcodes a directory into it and the agent quietly
lies to the model on every other machine.

### The behaviour block

Here is the real text, exactly as it appears in the file.

```python
BEHAVIOUR = """You are a careful software assistant working inside one directory.

Work in small steps. Look before you change anything. When you need to know
what a file contains, read it rather than guessing. When you change a file,
change the smallest amount of text that does the job.

Prefer edit_file over write_file for existing files, because write_file
replaces the whole file and loses anything you did not include.

When you are done, say what you changed in one or two sentences."""
```

Four paragraphs. Take them one at a time, because each one is doing a specific
job and none of them is filler.

**"You are a careful software assistant working inside one directory."**

This is the only sentence in the prompt that resembles the "you are an expert
X" opening that everybody writes, and it is here for a narrower reason than
those usually are. The two load bearing words are `careful` and `one
directory`.

`careful` sets a disposition that the following paragraphs then make concrete.
On its own it would be close to worthless, because a vague instruction to be
careful does not tell a model what to do differently. It earns its place by
being the heading that the specific rules below hang from.

`one directory` is the important half. It tells the model that its world is
bounded, which prepares it for the refusals it is going to get from
`resolve_inside` when it reaches outside. A model that has been told it works
inside one directory reads "outside the workspace" as a rule it understood in
advance rather than as a surprise it has to reason about.

**"Work in small steps. Look before you change anything. When you need to know
what a file contains, read it rather than guessing. When you change a file,
change the smallest amount of text that does the job."**

This is the working method, and every sentence in it maps onto a specific
failure you saw in section 1.

"Look before you change anything" is the fix for guess one. It pushes the model
toward `list_files` and `glob_files` and `grep_files` before it starts opening
files by name. Those tools are cheap. Guessing a path is not, because a wrong
guess costs a full round trip.

"Read it rather than guessing" is aimed at the specific failure where a model
writes an edit based on what it assumes the file contains. Models are extremely
good at producing plausible file contents, which is exactly the danger.
`edit_file` will refuse an edit whose old text does not appear, so the guess
does not corrupt anything, but it does burn a turn and it does put a wrong
version of the file into the conversation where it stays.

"Change the smallest amount of text that does the job" is about the diff a
human will read afterwards. An agent that rewrites a file to change one line
produces a change nobody can review, and an unreviewable change is one you
either accept blindly or throw away. Both are bad outcomes.

**"Prefer edit_file over write_file for existing files, because write_file
replaces the whole file and loses anything you did not include."**

This is the fix for guess three, and it is the one line in the block most worth
studying, because of the word `because`.

The instruction would still parse without the clause after it. "Prefer
edit_file over write_file for existing files" is a complete rule. Giving the
reason does two additional things.

It generalises. A model that knows why the rule exists can apply it to cases
the rule never mentioned. Told only the rule, the model has nothing to reason
with when it meets a situation the rule does not cover, such as a file it just
created three turns ago. Told the reason, it can work out that the risk is
losing content it did not include, and act accordingly.

It survives conflict. Later in a long conversation the model will meet a
situation that pulls the other way, such as a user explicitly asking for a file
to be regenerated from scratch. A bare rule and an explicit request are two
instructions in tension with nothing to break the tie. A rule with a reason
attached lets the model see that the reason does not apply here, because there
is nothing to lose, and follow the user.

Note also that this sentence names your tools by their exact names. `edit_file`
and `write_file` are the strings in the schema. Not "the edit tool", not
"editing". The model matches what it reads in the prompt against what it sees
in the tool list, and exact names make that match trivial instead of inferential.

**"When you are done, say what you changed in one or two sentences."**

An output format rule, and the smallest one that works. Without it, models end
a session in one of two unhelpful ways. Either they stop after the last tool
call with no text at all, which leaves the user staring at a trace and
wondering whether it finished, or they produce six paragraphs restating
everything they did, which the user will not read.

The cap of one or two sentences is doing real work. "Summarise your changes" on
its own reliably produces an essay. A number is an instruction a model can
actually comply with.

### The facts block

Now the second job, and it is code rather than prose because the values are not
known until the program runs.

```python
def build_system_prompt(root, extra=""):
    """Assemble the system prompt for a run inside root."""
    facts = [
        f"Workspace directory {Path(root).resolve()}",
        f"Platform {platform.system()}",
        f"Python {sys.version_info.major}.{sys.version_info.minor}",
    ]
    prompt = BEHAVIOUR + "\n\nFacts about this environment\n" + "\n".join(facts)
    if extra:
        prompt += "\n\n" + extra
    return prompt
```

Three facts, one function call each, all from the standard library.

`Path(root).resolve()` produces an absolute path with any symlinks and `..`
segments already collapsed. Resolving matters because `.` is not a fact. If the
prompt said the workspace was `.`, the model would learn nothing it did not
already assume, and the string would mean a different directory depending on
where the process was launched from. The resolved path is the same path that
`resolve_inside` in `tools.py` compares against, so the model is being told the
truth as the tools understand it rather than an approximation of it.

`platform.system()` returns one word. `Windows`, `Linux`, or `Darwin`. Section
4 is entirely about why that one word pays for itself.

`sys.version_info` gives the running interpreter's version. This one is
narrower than the other two but it prevents a recognisable class of waste. A
model that does not know the version will either avoid recent syntax
defensively, producing older and clunkier code than necessary, or use something
from a version you do not have and discover it when the test run fails. Neither
costs as much as a wrong path, but both are free to prevent.

The header line `Facts about this environment` is not decoration. It marks a
boundary between two kinds of content that the model should treat differently.
Above the line are instructions, things to do. Below it are observations,
things that are true. Labelling that boundary makes it much less likely that a
fact gets read as a suggestion.

`extra` is the extension point. It appends caller supplied text to the end,
which is where per project instructions belong. If you have used a coding agent
that reads a file of project specific rules from the repository root, this
parameter is where such a file would be dropped in. Lesson 11 uses it.

Here is the whole thing assembled, printed from a real run on the machine this
chapter was written on.

```text
You are a careful software assistant working inside one directory.

Work in small steps. Look before you change anything. When you need to know
what a file contains, read it rather than guessing. When you change a file,
change the smallest amount of text that does the job.

Prefer edit_file over write_file for existing files, because write_file
replaces the whole file and loses anything you did not include.

When you are done, say what you changed in one or two sentences.

Facts about this environment
Workspace directory C:\Users\usEr\Desktop\agentpath\lessons\10-anatomy-of-a-prompt
Platform Windows
Python 3.11
```

618 characters. Roughly 150 tokens. Hold that number, because section 7 is
about why it should stay small.

## 4. Why the model needs to be told where it is and what platform it is on

This section exists because the facts block looks like the least interesting
part of the file and is in fact the part that changes behaviour the most per
character spent.

Start with the general principle. A language model has no senses. It cannot run
`pwd`. It cannot look at your task bar. It has no ambient awareness of anything
whatsoever. Its knowledge of the present moment is exactly the text in the
conversation, and if a fact is not in that text then from the model's point of
view the fact does not exist.

But it still has to produce an answer, and this is the part people
underestimate. A model asked for a file path does not return "I do not know". It
returns the most probable path. That probability was learned from an enormous
amount of public code, which means the model's default guess is not random. It
is a confident, specific, well formed guess drawn from the average of everything
it has read.

That average is a Linux machine, in a directory called something like
`/home/user/project` or `/app`, running a shell where `ls` and `grep` and `cat`
exist. The guess is not stupid. It is correct for most of the code the model
was trained on. It is simply not correct for your machine, and the model has no
way to find out.

### The cost of the platform guess

Put a number on it. If your agent is on Windows and the system prompt says
nothing, then every shell command the model proposes is a coin flip weighted
toward Unix. Here are the pairs that come up constantly.

| What the model writes | What Windows needs |
| --- | --- |
| `ls -la` | `dir` or `Get-ChildItem` |
| `cat file.txt` | `type file.txt` or `Get-Content` |
| `rm -rf build` | `Remove-Item -Recurse build` |
| `export VAR=1` | `$env:VAR = "1"` |
| `grep -r x .` | `Select-String -Path *.* -Pattern x` |
| `./venv/bin/python` | `venv\Scripts\python.exe` |

Each wrong guess is a confirmation prompt shown to a human, a refusal or a
failed command, an error message added permanently to the conversation, and
another full round trip. Three of those in a session and you have spent more
tokens on shell dialect than on the actual task.

With one word in the prompt, the model gets it right the first time. `Platform
Windows` costs two tokens. The failures it prevents cost hundreds each, plus
something more valuable than tokens, which is the user's willingness to keep
reading confirmation prompts carefully.

### The cost of the directory guess

The workspace path does something slightly different, and it is worth
separating.

The obvious benefit is that the model stops inventing absolute paths, which
`resolve_inside` refuses anyway, so those attempts are pure waste.

The subtler benefit is that the absolute path tells the model what kind of place
it is in. Look at the difference between these two facts.

```text
Workspace directory C:\Users\usEr\Desktop\agentpath\lessons\10-anatomy-of-a-prompt
```

```text
Workspace directory /srv/deploy/customer-data-import
```

The first says this is a lesson folder inside a course repository on somebody's
desktop, which is a place where experimenting is fine. The second says
production. A model that can see either string reasons differently about how
much to verify before acting, and it did not need to be told any of that
explicitly. The path carried it.

There is a third benefit that only shows up in error messages. When
`resolve_inside` refuses a path, the model has to work out what a legal path
looks like. If the workspace is in the prompt, that reasoning is immediate. If
it is not, the model is guessing again, and a second guess after a refusal is
often worse than the first because the model starts trying elaborate escapes.

### Facts, not instructions

One last point about the shape of this block, because it is a habit worth
forming.

Notice that none of the three facts is phrased as an instruction. It does not
say "always use Windows commands" or "never use absolute paths". It states what
is true and lets the model draw the conclusion.

This is deliberate and it scales better. There are dozens of consequences of
being on Windows, and you cannot enumerate them. Path separators, line endings,
the absence of `chmod`, the different Python launcher, case insensitive file
names, `%APPDATA%` instead of `$HOME`. Write them all as rules and you have
thirty rules that compete with each other, which section 7 says is the way to
make a prompt worse. State the one fact and the model already knows the
consequences, because that particular knowledge is genuinely in its training
data. What it lacked was not knowledge of Windows. It was knowing that Windows
was the case here.

State facts the model cannot know. Let it apply the knowledge it already has.

## 5. What belongs in the user message

This section is short, because the user message is the one channel where the
right answer is to do less.

The user message is the task. That is all.

```python
messages.append({"role": "user", "content": user_input})
```

Whatever the person typed goes in unmodified. No prefix, no template, no
appended reminder about being careful, no restating of the rules.

Three reasons, in increasing order of importance.

**It is already covered.** Anything you would prepend to every user message
belongs in the system prompt, where it is written once and stated once. Adding
it here means the same instruction appears twice in the conversation, and when
the same instruction appears twice a model must decide whether the second one
is emphasis or a correction of the first. Neither reading helps.

**It grows.** A reminder appended to every user message is sent again for every
message in the history. Ten turns into a session that reminder is in the
conversation ten times. It is being paid for ten times and it is diluting the
conversation ten times.

**It hides the task.** This is the real one. The model's job on each turn is to
work out what the user wants. Padding the message with boilerplate buries the
one sentence that actually matters, and models, like people, weight the
beginning and end of a message more heavily than the middle. Wrapping the task
in a preamble and a postscript puts the important part in the least attended
position.

There is one case where extra content in the user turn is right, and it is
worth naming so you recognise it as different. Context the user is deliberately
attaching to this specific task, such as the text of an error they hit or the
contents of a file they pasted, belongs in the user message, because it is part
of the task and it is not true of the next task. That is not a template. That
is the user speaking.

## 6. Tool descriptions are prompt engineering, and this is the part people miss

Now the long section, and the reason it is long is that this is the channel
nobody counts.

Open `tools.py`. It has not changed since lesson 09. Look at what is sitting in
the schema for `read_file`.

```python
"description": "Read a text file and return its contents.",
```

Here is the claim of this section. That sentence is a prompt. Not something
like a prompt, not metadata about a prompt. It is text that you wrote, that is
sent to the model inside the same HTTP request as your system message, that the
model reads before deciding what to do, and that influences its behaviour by
exactly the same mechanism as any other text in the request. You have been
writing prompts since lesson 07 and this chapter is where you find out.

### The description is all the model will ever know

Take this seriously, because it is more absolute than it sounds.

The model cannot see your Python. It does not know that `read_file` calls
`resolve_inside`. It does not know that the return value is truncated at 4000
characters. It cannot inspect the function, cannot read your docstring, cannot
run it to find out what it does. It has the name, the description, and the
parameter schema. That is the complete interface.

Every property of your function that the model needs in order to use it well
must be in that string, or the model does not have it.

This inverts how you normally write a docstring. A docstring is written for
somebody who can also read the code underneath it, so it can be terse and leave
things implied. A tool description is written for a caller who will never see
the code, will never see it again after this call, and cannot ask a follow up
question. Nothing may be implied. If a constraint is not written down it does
not exist as far as the caller is concerned.

### It is read on every single request

Here is the second property, and it is the one that makes descriptions
unusually powerful.

The tool list is sent on every request in the conversation. Not once at the
start. Every time. Turn one, turn five, turn twenty.

Compare that to a system prompt, which is also present every time but is
positioned at the very front of a conversation that keeps growing. By turn
fifteen your system prompt is buried under fifteen turns of file contents,
search results and shell output. It is still there and the model still attends
to it, but it is competing with a great deal of more recent material.

The tool description is not in that stream. It sits in the `tools` array
alongside the function the model is about to call, which means it is adjacent to
the decision rather than fifteen turns upstream of it.

That adjacency is why the practical rule below holds so consistently.

**If you want to change how a tool is used, change its description before you
add a paragraph to the system prompt.**

The description is read at the moment of choosing, it applies to exactly the
decision you care about, and it does not compete with anything except the other
six descriptions. A system prompt rule about a specific tool is a general
instruction that has to be recalled at the right moment. A description is
information delivered at the point of use.

Now look at what the tool descriptions in this project actually do with that
position.

### Worked example one, write_file steering toward edit_file

```python
"description": (
    "Write a whole file, creating it if needed. Use edit_file instead when "
    "you only want to change part of an existing file."
),
```

Read the second sentence again. It is a description of `write_file` that spends
half its length telling the model to call a different tool.

That looks wrong the first time you see it. A function's documentation should
describe the function. But remember who the reader is and when they are
reading. The model reads this while deciding what to call. The moment just
before it calls `write_file` on a file that already exists is precisely the
moment the warning is useful. Putting it anywhere else means it arrives too
early or too late.

It also works. This is the same rule that is already in the system prompt, in
the `Prefer edit_file over write_file` paragraph, and having it in both places
is not an accident. It is one rule stated where it is remembered and again where
it is needed. If you can only have one, the description is the one that lands,
because it is attached to the decision instead of being a policy the model has
to recall.

Notice the precision of the condition. It says `part of an existing file`, not
"prefer edit_file". Both halves of that phrase matter. `existing` excludes the
case where the file does not exist yet, where `write_file` is correct and
`edit_file` will fail. `part of` excludes the case where the whole file really
is being replaced. A blanket instruction would push the model toward `edit_file`
in situations where `edit_file` cannot work, and then it fails, retries, and you
have made things worse with an instruction that was too strong.

Compare it to the descriptions people usually write.

```python
"description": "Writes a file."
```

Everything the model needs is missing. It does not know a sibling tool exists,
does not know that the write is destructive, does not know when the sibling is
the better choice. The function behaves identically. The agent behaves much
worse, and it behaves worse in the silent way from section 1 where nothing
errors and the file quietly loses content.

### Worked example two, edit_file explaining how to succeed

This is the best description in the file and the pattern is worth taking away
whole.

```python
"description": (
    "Replace one exact piece of text in a file. The old text must appear "
    "exactly once, so include enough surrounding lines to make it unique."
),
```

Three things are packed into two sentences.

**What it does.** Replace one exact piece of text.

**The constraint.** The old text must appear exactly once.

**How to satisfy the constraint.** Include enough surrounding lines to make it
unique.

The third is the part that most tool descriptions leave out, and leaving it out
is the difference between a model that succeeds on the first call and a model
that succeeds on the second.

Trace both versions. Suppose the model wants to change a `return None` inside a
function, and the file contains four of them.

Without the third sentence, the model sends the smallest edit it can, because
small edits are what it was told to prefer.

```text
[calling edit_file with {'path': 'app.py', 'old': '    return None', 'new': '    return []'}]
[edit_file returned Error: the text to replace appears 4 times in app.py.
 Include more surrounding lines so the match is unique.]
```

One turn spent. The error message you wrote back in lesson 07 rescues the
situation, the model reads it, adds context, and the second call works. The
system recovers, which is exactly what that error message was designed for.

With the third sentence in the description, the model knows the uniqueness rule
before it composes the call, and it sends this instead.

```text
[calling edit_file with {'path': 'app.py', 'old': 'def parse(raw):\n    if not raw:\n        return None', 'new': 'def parse(raw):\n    if not raw:\n        return []'}]
[edit_file returned Edited app.py]
```

No wasted turn. Same function, same code, same error handling still there for
the cases where it is genuinely needed. The only difference is that the
requirement was stated in advance rather than only on violation.

Say the general form out loud, because it applies to every tool you will ever
write.

**A good error message tells the model what went wrong. A good description
stops it from going wrong.**

You want both. Errors are the safety net and you built a good one in lesson 07.
The description is the part that means the net is rarely needed. A system that
only has the error message works, and pays a turn every time. A system that only
has the description works until something unexpected happens and then has no
recovery. Having both is why the agent feels smooth rather than merely
functional.

### Worked example three, teaching syntax by example

```python
"description": (
    "Find files by name pattern, for example **/*.py or test_*.py. "
    "Use this when you know roughly what a file is called."
),
```

Two techniques here that are worth separating.

The first is `for example **/*.py or test_*.py`. Those five words do more than a
paragraph explaining `fnmatch` syntax would. Two concrete examples establish the
dialect immediately, and they were chosen carefully. `**/*.py` is the recursive
form, and `test_*.py` is the bare name form, which are exactly the two cases
section 4 of lesson 09 had to write extra matching code to support. The examples
in the description and the double match in the implementation are the same
design decision seen from two sides.

The second is `Use this when you know roughly what a file is called`. That
sentence is not about `glob_files` at all. It is about choosing between
`glob_files` and `grep_files`, which is the actual decision the model faces when
it reads the tool list. Compare with the neighbouring description.

```python
"description": (
    "Search the text inside files using a regular expression and return "
    "matching lines with their file name and line number."
),
```

One tool says it searches names and tells you when to use it. The other says it
searches contents and tells you what it gives back. Between them the model can
pick correctly without trying one and falling back, and trying one and falling
back is a turn.

Also notice that `grep_files` advertises its return format. Saying that it
returns the file name and the line number tells the model in advance that the
output can be fed to `read_file`, which is the whole chaining argument from
lesson 09 delivered as a single clause.

### Worked example four, describing a side effect

```python
"description": (
    "Run a shell command in the workspace directory and return its output. "
    "The user is asked to approve the command before it runs."
),
```

The second sentence describes something that happens outside the model's world.
A human being is going to look at the command and decide.

Why tell the model at all, given that it cannot influence the outcome.

Because it changes what the model does before and after. Before, it knows the
command will be read by a person, which discourages long chained one liners in
favour of a command somebody can evaluate at a glance. After, when the refusal
message comes back, it can interpret it correctly as a human decision rather
than as a broken tool, and not retry the same thing with slightly different
quoting.

It also tells the model that the tool has a cost that is not measured in tokens.
Every call to `run_shell` interrupts a person. That is worth knowing when
choosing between `run_shell` and `grep_files` for the same question.

Note what the description does not say. It does not say that the command runs
with `shell=True`, or that there is a 60 second timeout, or that output is
truncated at 4000 characters. Those are implementation details the model cannot
act on, and section 7's argument about competing instructions applies inside a
description too. The timeout is arguably borderline and you could make a case
for including it. The rest are noise.

### The whole set, and what it costs

Here is every description in the project, measured.

| Tool | Description length | Full schema in JSON |
| --- | --- | --- |
| `read_file` | 41 | 230 |
| `write_file` | 119 | 395 |
| `edit_file` | 136 | 484 |
| `list_files` | 48 | 237 |
| `run_shell` | 126 | 314 |
| `glob_files` | 115 | 295 |
| `grep_files` | 119 | 388 |
| total | 704 | 2343 |

704 characters of description. About 180 tokens, sent on every request,
alongside a system prompt of about 150. The parameter schemas roughly triple
that, because JSON is verbose, and there is nothing to be done about the JSON.

The descriptions themselves are the part you control, and this table is the
argument for keeping the boring ones boring. `read_file` gets 41 characters
because there is nothing interesting to say about reading a file. `edit_file`
gets 136 because there is a constraint the model must know in advance. Length
follows from how much the caller actually needs, not from a desire to be
thorough.

### How to work on descriptions

A short practical method, because this is a thing you will do repeatedly for
the rest of your time building agents.

**Watch the traces.** Every wrong tool call, every malformed argument, every
retry is a defect in a description. Do not fix it by adding a system prompt
rule. Read the description the model was working from and ask what a person
would have got wrong given only those words.

**Change one description at a time.** They are short enough that the effect of a
single change is visible, and changing two at once means you learn nothing about
either.

**Write the constraint before the model violates it.** This is the `edit_file`
lesson generalised. If your function will reject certain inputs, the rule
belongs in the description as well as in the error message.

**Name the sibling tool when there is one.** Whenever two tools overlap, each
description should say when the other one is right. This is the `write_file`
lesson, and it is the single highest value edit you can make to a tool list.

**Delete anything the model cannot act on.** Implementation details cost tokens
on every request forever and change nothing about the call.

## 7. Why a longer system prompt is not a better one

There is an obvious next move after this chapter, and it is the wrong one.
Having seen that a few sentences improved the agent, the natural conclusion is
that a few more sentences will improve it further. People end up with system
prompts of two thousand words, and their agents are not two thousand words
better.

Three reasons, and they are independent, which means they stack.

### Every token is resent on every request, forever

This is the lesson 02 mechanism arriving with a bill attached.

The system prompt is not sent once at the start of a session. It is part of the
conversation, and the whole conversation goes out with every request. A twenty
turn session sends the system prompt twenty times.

The prompt in this lesson is about 150 tokens. A thoughtfully bloated one is
easily 1500. Put that against a session and the difference is real.

| | 150 token prompt | 1500 token prompt |
| --- | --- | --- |
| one request | 150 | 1500 |
| twenty turn session | 3,000 | 30,000 |
| a hundred sessions | 300,000 | 3,000,000 |

Those are input tokens you pay for, on every request, for as long as the agent
exists. And input tokens are not the only cost. They are latency, because the
model must process them before producing the first output token, and they are
context window, because everything the prompt occupies is space the actual task
cannot use.

The point is not that 1350 extra tokens will bankrupt you. It is that a
sentence in the system prompt is a permanent recurring cost, and it should
therefore have to justify itself the way a recurring cost does. Ask of every
line whether it will change what the model does. If it will not, it is a
subscription to nothing.

### Instructions compete with each other

This is the reason that matters more, and it is not about money.

A model does not hold a list of rules and check them off. It attends to the
whole conversation at once, and attention is finite and divided. Every
additional instruction takes some share of the attention that the other
instructions were getting.

The practical consequence is uncomfortable and worth stating bluntly. A model
given five rules follows them more reliably than a model given twenty. Not
because twenty is too many to store, but because the twentieth rule dilutes the
first one. Adding a rule you care about a little makes the rule you care about a
lot slightly weaker.

It gets worse when rules interact, which they do more often than people expect
when writing them one at a time. Consider a prompt containing all of these.

```text
Always read a file before editing it.
Minimise the number of tool calls you make.
Never make an edit you have not verified.
Be efficient and avoid unnecessary work.
```

Rules one and three demand more tool calls. Rules two and four demand fewer.
Every one of them sounds sensible in isolation and together they describe a
contradiction. The model will resolve it somehow, differently on different
turns, and the behaviour you observe will look like randomness. It is not
randomness. It is you having asked for two incompatible things and left the
model to choose.

The behaviour block in `prompt.py` is four short paragraphs and they were
checked against each other. "Work in small steps" and "change the smallest
amount of text" point the same way. "Look before you change anything" and "read
rather than guessing" point the same way. Nothing in it argues with anything
else in it. That property is much easier to maintain at four paragraphs than at
forty, which is a good reason to stay at four.

### A rule in code beats a rule in a prompt, every time

The third reason is the most important and it is the one that changes how you
build things.

A prompt is a request. Even a well written instruction followed by a good model
is a strong tendency, not a guarantee. There is always some input, some
conversation, some unusual phrasing, where the model does something else.

Code is not a request. Code is what happens.

You already have the clearest possible demonstration of this, and it is lesson
08. Consider the two ways you could have built the shell tool.

The prompt way.

```text
Never run a destructive command. Always ask the user before running anything
that deletes files or modifies the system.
```

The code way, which is what you actually wrote.

```python
def run_shell(command):
    if not confirm(command):
        return "The user refused to run this command. Do not try to run it again."
```

These are not two styles of the same solution. They are different in kind.

The prompt version depends on the model correctly classifying every command as
destructive or not, in every phrasing, under every kind of pressure, including
when a file it just read contains text designed to talk it out of the rule.
Lesson 08 called that prompt injection, and the whole argument there was that
you cannot defend against it with an instruction, because the attack and the
defence are the same kind of thing and the attacker gets to write theirs
second.

The code version does not care what the model concluded. `confirm` runs before
`subprocess.run`, on every call, with no path around it. A model that has been
completely persuaded that deleting the repository is a great idea still stops at
that line, because the line is not addressed to the model.

The same pattern is everywhere in what you have built, and it is worth
collecting.

| The rule | Where it lives | Where it does not live |
| --- | --- | --- |
| do not touch files outside the workspace | `resolve_inside` | a prompt asking politely |
| never read credential files | `looks_like_a_secret` | a prompt listing bad filenames |
| tool output cannot flood the context | `truncate` and `MAX_RESULTS` | a prompt asking for brevity |
| a human approves shell commands | `confirm` | a prompt about being careful |
| an edit must be unambiguous | the count check in `edit_file` | a prompt about being precise |

Every one of those could have been written as a sentence. None of them was, and
that is why they hold.

So the test to apply, whenever you are about to add a line to a system prompt,
is this. Could this be a check in the code instead. If it could, put it in the
code, and use the prompt only to tell the model that the check exists so it does
not waste turns discovering the boundary by hitting it.

That last clause is the honest complement to the whole argument. Prompts and
code are not competitors. Code enforces, prompts inform. `resolve_inside`
enforces the workspace boundary, and `Workspace directory ...` in the prompt
tells the model where the boundary is so it never has to be enforced. The
enforcement is what makes the agent safe. The information is what makes it
efficient. You want both, doing their own jobs.

## 8. Writing prompt.py and changing the agent loop

Now the code, which after all that argument is short.

### prompt.py

The whole file, top to bottom.

```python
import platform
import sys
from pathlib import Path

BEHAVIOUR = """You are a careful software assistant working inside one directory.

Work in small steps. Look before you change anything. When you need to know
what a file contains, read it rather than guessing. When you change a file,
change the smallest amount of text that does the job.

Prefer edit_file over write_file for existing files, because write_file
replaces the whole file and loses anything you did not include.

When you are done, say what you changed in one or two sentences."""


def build_system_prompt(root, extra=""):
    """Assemble the system prompt for a run inside root."""
    facts = [
        f"Workspace directory {Path(root).resolve()}",
        f"Platform {platform.system()}",
        f"Python {sys.version_info.major}.{sys.version_info.minor}",
    ]
    prompt = BEHAVIOUR + "\n\nFacts about this environment\n" + "\n".join(facts)
    if extra:
        prompt += "\n\n" + extra
    return prompt
```

Three small decisions in there deserve a sentence each.

The prompt is built by a **function**, not stored as a constant. A constant
cannot contain `platform.system()`, and the moment you want a fact in the prompt
you need code to produce it. Building it in a function also means the prompt is
computed when a run starts rather than when the module is imported, which is the
difference between the prompt describing the current run and describing whatever
was true the first time Python touched the file.

`root` is a **parameter** rather than being read from `os.environ` inside the
function. The tools module does read the environment, at import time, and that
is right for the tools because the workspace is a property of the process. Here
a parameter is better because it makes the function testable without touching
global state, which is exactly what `check.py` relies on.

The prompt lives in **its own file**. It is not a string inside `agent.py`. The
loop should not have an opinion about what the agent is for, and putting the
personality in a separate module keeps that boundary clean. In lesson 11 you
will have one loop and a prompt you edit constantly, and you do not want to open
the loop to change a sentence.

### The change to agent.py

Three lines, at the top of `run`.

```python
def run(provider, user_input, system=None, max_turns=10):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_input})
```

That replaces the single line from lesson 09.

```python
    messages = [{"role": "user", "content": user_input}]
```

`system=None` with a default means every existing caller keeps working. Lessons
06 through 09 call `run(provider, prompt)` with two arguments and are unaffected.
Making the parameter optional rather than required is what lets a change like
this land without touching anything upstream.

The `if system` guard covers both `None` and the empty string, so an empty
prompt does not produce an empty system message. An empty system message is not
an error, but it is a message that costs a little and says nothing, and models
occasionally treat an unexpected empty message as meaningful.

There is a second, smaller change further down. The function now returns both
the text and the message list.

```python
        if not calls:
            print()
            return text, messages
```

Lesson 09 returned only `text`. Returning the conversation as well lets the
caller inspect what was actually sent, which is precisely what `check.py` does
when it asserts that the first message is the system message. It is also useful
in lesson 11, where the loop is called repeatedly and the conversation has to
survive between calls.

### Why the system message goes first

Not "near the front". First. Index zero, before anything the user said.

Three reasons, and they are unrelated to each other, which is a good sign that
the ordering is not arbitrary.

**The API defines it that way.** For OpenAI compatible endpoints the system
prompt is a message with `role` set to `system`, and it is expected at the start
of the array. Providers are trained and tuned on conversations shaped that way.
Putting a system message in the middle of a conversation is not an error you
will see reported, it is just a request the model has seen far less often, and
less familiar shapes get less reliable behaviour.

**Instructions must precede the thing they govern.** This is the one that
matters for behaviour. The rule about preferring `edit_file` needs to be in
context before the model reads a request that might tempt it toward
`write_file`. A model reads the conversation as a whole, but ordering still
carries meaning, and an instruction that appears after the task reads like an
afterthought or a correction rather than a standing rule.

**It is stable, and stable content goes at the front.** The system prompt is
identical on every request in a session. Everything after it changes. Providers
that offer prompt caching key on a shared prefix, so an unchanging block at
position zero is exactly the shape that can be cached, and cached input is
substantially cheaper and faster. Put the system prompt after the first user
message and the prefix differs on every session, and there is nothing to cache.

There is a fourth point that is really about `providers.py`, and it is why this
design survives contact with a second API. The Anthropic API does not take the
system prompt as a message at all. It takes it as a top level field. Look at
what `AnthropicProvider` does with the list it is handed.

```python
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        ...
        if system:
            payload["system"] = system
```

And in `_to_wire`, which builds the messages array for that API.

```python
            if message["role"] == "system":
                continue
```

The system message is lifted out of the list and moved to its own field, and
skipped when the messages are converted. This is lesson 06's argument arriving
again. The agent loop holds one internal format and each provider translates it
to the wire format its API wants. The loop does not know that two APIs disagree
about where a system prompt lives, and it should not have to.

## 9. Running check.py

`check.py` asserts three things, and each one is a different kind of claim.

```python
def main():
    system = build_system_prompt(workspace)
    if str(workspace.resolve()) not in system:
        fail("the system prompt does not tell the model where it is working")
    print("OK the system prompt states the workspace directory")

    if "Platform" not in system:
        fail("the system prompt does not tell the model which platform it is on")
    print("OK the system prompt states the platform")

    provider = OpenAICompatProvider(...)
    _, messages = run(provider, "Say hello.", system=system)
    if messages[0]["role"] != "system":
        fail(f"the first message was {messages[0]['role']!r} rather than the system prompt")
    print("OK the system prompt is the first message in the conversation")
```

The first two are pure string checks on the output of `build_system_prompt`,
and they need no model at all. The workspace check compares against the resolved
temporary directory the check made for itself, so it is verifying that the real
path arrives rather than that some path shaped text is present.

The third one is different, and it is the only reason this check needs a
provider. It calls `run` and then looks at the conversation that came back. That
is the only way to prove the ordering claim from section 8, because the ordering
is a property of the list the loop built, not of the prompt string.

Notice that it checks `messages[0]`, not "a system message exists somewhere".
The claim being tested is specifically that it is first, and a weaker assertion
would pass on a loop that appended the system message at the end.

This check talks to a model, unlike lesson 09's, so it needs the mock server.
The simplest way is the runner from the repository root, which starts the fake
server, sets the three environment variables, and runs every lesson in turn.

```bash
python ci/run_lessons.py
```

```powershell
python ci\run_lessons.py
```

To run this lesson on its own, point the environment variables at a running
model endpoint first, exactly as in lesson 06.

```bash
cd lessons/10-anatomy-of-a-prompt
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen2.5:14b
export AGENTPATH_API_KEY=
python check.py
```

```powershell
cd lessons\10-anatomy-of-a-prompt
$env:AGENTPATH_BASE_URL = "http://localhost:11434/v1"
$env:AGENTPATH_MODEL = "qwen2.5:14b"
$env:AGENTPATH_API_KEY = ""
python check.py
```

A passing run against the mock server looks like this.

```text
OK the system prompt states the workspace directory
OK the system prompt states the platform
Hello from the mock server.
OK the system prompt is the first message in the conversation
```

Three OK lines, which are the three claims.

```text
OK the system prompt states the workspace directory
OK the system prompt states the platform
OK the system prompt is the first message in the conversation
```

The `Hello from the mock server.` in the middle is not part of the check. It is
the model's streamed reply printing as it arrives, from the `on_text` callback
you wrote in lesson 05, and it appears third because the first two assertions
run before the request is made. Against a real model that line will say
something else, and the check will still pass, because none of the three
assertions is about what the model said.

If the first line fails, `build_system_prompt` is not resolving `root`, or it
is dropping the facts block. If the third fails and reports that the first
message was `'user'`, the `if system` block in `agent.py` is missing or is
running after the user message is appended.

One detail at the top of the file that is easy to skim past.

```python
workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson10-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from agent import run  # noqa: E402
```

Same ordering trap as lesson 09. `agent` imports `tools`, and `tools` reads
`AGENTPATH_WORKSPACE` at import time and never again. Set it after the import
and the tools are pinned to the wrong directory. The `# noqa: E402` marks the
deliberate style violation rather than hiding it.

## 10. What you cannot do yet

Stop and look at what exists.

```text
lessons/06-provider-abstraction/   two providers behind one interface
lessons/07-file-tools/             read, write, edit, list, with a safe path gate
lessons/08-shell-tool/             run a command, with a human in the way
lessons/09-search-tools/           find files by name, find text inside them
lessons/10-anatomy-of-a-prompt/    a system prompt, and words in three channels
```

Every part of a coding agent is now present. A loop that keeps going until the
model stops asking for tools. Streaming so you can watch it work. Two providers
so you are not locked to one company. Seven tools that are a complete set for
changing code. A workspace boundary, a credential refusal, output caps, and a
human gate on the shell. And now a prompt that tells the model where it is and
how to behave.

And you cannot use any of it.

There is no program. There are five folders, each with its own copy of
`tools.py` at a different stage of completion, each with a `check.py` that
proves one chapter's claims and then exits. Nothing takes a task from you.
Nothing runs more than one request without a check file driving it. If you
wanted to point this at a real folder and ask it to fix a bug this afternoon,
you would have to write the wiring yourself, and you would immediately hit
questions no lesson has answered.

Where does the workspace come from when a person runs it, rather than a test.
How does a second message get added to a conversation that already exists, so
you can say "no, the other file" without starting over. What happens when the
model wants to keep going past the turn limit. What does the user actually see
while it works, given that tool traces printed raw are unreadable after about
three calls. What does a person type to start it at all.

None of those are hard. All of them are unbuilt.

That is lesson 11, the milestone that closes part two. It takes the best version
of each file you have written, puts them in one package with a command line
entry point, and turns twelve hundred lines of teaching code into a small coding
agent you can run against a real directory. No new concepts. Assembly, a
readable interface, and a program that starts when you type its name.

### Exercises before you move on

**One.** Delete the facts block. Run the agent against a real directory with
only `BEHAVIOUR` in the system prompt and give it a task that requires finding a
file. Count the turns. Put the facts back and count again. This is the whole
argument of section 4 measured on your own machine, and the number is usually
larger than people expect.

**Two.** Break the `write_file` description down to just `Write a whole file.`
and ask the agent to change one line in an existing file. Watch which tool it
picks. Restore the sentence about `edit_file` and ask again. Then do the same
experiment with the sentence removed from the description but added to the
system prompt instead, and compare. The point of the third run is to find out
for yourself whether section 6's claim about adjacency holds for your model.

**Three.** Add a fourth fact to `build_system_prompt` that lists the top level
entries of the workspace, using the `list_files` function you already have. Then
argue with yourself about whether it belongs there. It saves a turn on the first
request, and it costs tokens on every request for the rest of the session, and
it goes stale the moment the agent creates a file. There is a defensible answer
in both directions, and working out which one applies to your situation is the
skill this chapter is really teaching.
