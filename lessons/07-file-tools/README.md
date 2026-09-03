[อ่านภาษาไทย](README.th.md)

# Lesson 07. File tools

This is the first chapter of part two, and it is the chapter where the agent
stops being a demonstration and starts being something you would actually run
on a folder you care about.

By the end you will have four tools that touch real files on your disk, one
gate that every path they receive has to pass through, and a check that proves
the agent can read a file, change a file, and be refused twice when it asks for
something it should not have.

Files in this folder.

```text
lessons/07-file-tools/
  tools.py       four real file tools, one path gate, one deny list
  providers.py   unchanged from lesson 06, byte for byte
  agent.py       unchanged from lesson 06, byte for byte
  check.py       proves it reads, edits, and refuses twice
  README.md      this file
```

Two of those four files say **unchanged**, and that is not a footnote. It is
the headline.

## 1. Welcome to part two

Part one built a loop. Six lessons, about three hundred lines, and at the end of
it you had a program that could hold a conversation, describe your Python
functions to a model, read back a structured request for one of them, run it,
feed the result back in, and do all of that against two completely different
provider APIs without knowing which one it was talking to.

And it could not do anything.

That is the honest summary of part one. The tools were `add` and a dice roll.
The worst outcome of a bug was a wrong number on your terminal. The agent could
talk, and talking is all it could do.

From this chapter on, it touches your filesystem. It reads files you did not
show it. It writes files. It edits files in place. That is the moment the whole
exercise becomes useful, because an agent that can read your code and change
your code is the thing everybody actually wants. It is also the exact moment it
becomes dangerous, because every one of those verbs works just as well on a
file you did not mean and a directory you did not mention.

So part two is two things happening at the same time. New abilities, and the
first real safety machinery in this course. They arrive together in this
chapter and they will keep arriving together, because a file tool without a
gate on it is not a simpler version of a file tool. It is a different and worse
thing.

### The loop does not change, and that is the point

Here is the claim that makes the rest of part two easy, and you can verify it
with one command before you read another word.

```bash
cd lessons
diff 06-provider-abstraction/agent.py 07-file-tools/agent.py
```

```text
Files are identical
```

Run the same command for `providers.py` and you get the same answer. The agent
loop and the provider layer are unchanged between a lesson where the agent
could add two numbers and a lesson where it can rewrite your source code.

That is worth sitting with, because it is not an accident and it is not luck.
It is the payoff of everything part one spent its time on.

Think about what the loop actually knows how to do. It knows how to send
messages. It knows how to receive a request that has a name, an id, and a
dictionary of arguments. It knows how to look that name up in a dictionary, call
whatever it finds, turn the answer into a string, and append that string to the
conversation with the matching id. That is the entire contract, and nothing in
it mentions arithmetic, or files, or shells, or networks.

Because the contract is that narrow, every new ability in this whole part is a
tool and nothing but a tool. Reading files is a tool. Editing files is a tool.
Running a shell command in lesson 08 is a tool. Searching a codebase in lesson
09 is a tool. Not one of them requires a line of change in `agent.py`.

```text
lesson 03    tools.py  ->  add, roll_dice                  toy
lesson 07    tools.py  ->  read_file, write_file,          real
                           edit_file, list_files
lesson 08    tools.py  ->  + run_shell                     real and loud
lesson 09    tools.py  ->  + glob_files, grep_files        real and fast

agent.py     unchanged through all four
providers.py unchanged through all four
```

This is what people mean when they say a design has good seams. You cut the
system in the right place once, and then the expensive part of the work
happens on one side of the cut while the other side sits still. If you had
built the loop with file handling woven into it, every one of the next four
lessons would be surgery on code that already works, and every one of them
would carry a chance of breaking something that used to be fine.

You did not, so they will not. From here, new capability means one new function
and one new schema in `tools.py`.

### What actually changes in this lesson

Exactly one file. `tools.py` is rewritten from the toy version you have been
carrying since lesson 03, and two ideas arrive with it that were not needed
before.

The first is that every path the model sends must pass through one gate, called
`resolve_inside`, so that the rules about what may be touched live in a single
function rather than being restated in four places.

The second is that everything a tool returns is not a print statement. It is
data that goes into the conversation and gets sent to the model provider on this
request and on every request after it. That single fact is why the tools
truncate their output and why they refuse to touch credential files, and both of
those decisions are covered in full below.

## 2. The problem left over from lesson 06

Open `lessons/06-provider-abstraction/tools.py` and read the whole thing. It is
short, and its shortness is the problem.

```python
def add(a, b):
    return a + b


def roll_dice(sides):
    return random.randint(1, sides)
```

Look at what these functions have in common. Every argument is a number. Every
return value is a number. There is no input a model could send that would do
anything worse than produce a wrong answer. If the model asks for
`add(a=99999999, b=99999999)` you get a large integer. If it asks for
`roll_dice(sides=0)` you get a `ValueError` that `tools.run` catches and hands
back as a string.

Because of that, `tools.run` in lesson 06 is a completely trusting function.

```python
def run(name, arguments):
    function = FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**arguments))
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"
```

It looks the name up, it splats the arguments in, and it catches whatever comes
out. There is no validation anywhere, and there did not need to be, because the
worst case was arithmetic.

Now imagine adding the obvious first file tool to that file, in the obvious
first way somebody writes it.

```python
def read_file(path):
    return Path(path).read_text()
```

Three lines, it works, and it is a catastrophe. That function will read
`/etc/passwd`. It will read `~/.ssh/id_rsa`. It will read the `.env` file in
the project directory with your provider key in it. It will read a file three
directories above wherever you started the agent. It will read a two hundred
megabyte log file and hand the whole thing back into a conversation that gets
resent on every subsequent turn.

None of that requires a malicious model. Every one of those outcomes is what a
helpful model does when it is trying to answer your question and it guesses
wrong about where something lives.

Here is the situation stated plainly. Lesson 06 left you with a `tools.py`
whose functions could not do damage, and therefore with no habits, no gate, and
no vocabulary for the case where they can. This lesson is where that changes,
and the useful part is not that we add safety checks. It is *where* we add
them, because the wrong place is the obvious place.

```text
lesson 06
  tools.run  ->  add(a, b)        arguments are numbers, nothing to check

lesson 07
  tools.run  ->  read_file(path)  ->  resolve_inside(path)  ->  refuse or proceed
             ->  write_file(...)  ->  resolve_inside(path)  ->  refuse or proceed
             ->  edit_file(...)   ->  resolve_inside(path)  ->  refuse or proceed
             ->  list_files(...)  ->  resolve_inside(path)  ->  refuse or proceed
```

## 3. One gate for every path

Here is the gate, complete apart from its docstring. In tools.py the function
runs to twenty lines with the docstring counted, and it is the most important
code in the chapter.

```python
WORKSPACE = Path(os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()


class WorkspaceError(Exception):
    """Raised when a tool asks for a path it is not allowed to have."""


def resolve_inside(path):
    candidate = (WORKSPACE / Path(path)).resolve()
    if candidate != WORKSPACE and not candidate.is_relative_to(WORKSPACE):
        raise WorkspaceError(f"{path} is outside the workspace")
    if looks_like_a_secret(candidate.name):
        raise WorkspaceError(
            f"this tool refuses to touch {candidate.name} because credential files "
            "must not enter the conversation or be changed by an agent"
        )
    return candidate
```

### What it is

`resolve_inside` is a translator with a veto. It takes a string that a language
model produced, which is to say a string with no guarantees attached to it at
all, and it either returns a real `Path` object that the tool is allowed to
operate on, or it raises `WorkspaceError` and the tool never runs.

There are exactly two ways out of that function. A safe path, or an exception.
There is no third branch where a slightly questionable path gets through with a
warning printed somewhere.

`WORKSPACE` is the root of everything the agent is permitted to touch. It comes
from the `AGENTPATH_WORKSPACE` environment variable, defaulting to `.`, and it
is resolved to an absolute path once when the module is imported. That last
detail matters more than it looks and gets its own subsection in section 9.

### Why we are doing it

Because the model decides the path and you decide what is allowed, and those
are two different jobs that must not be done by the same participant.

The model is not adversarial in the normal case. It is helpful, and it is
guessing. You ask it to fix a failing import and it reasons that the config
probably lives one level up, so it asks for `../config.py`. You ask it to
summarise your project and it reasons that the deployment settings are
interesting, so it asks for `.env`. Nothing about either request is hostile.
Both of them are wrong, and only your code is in a position to say so.

There is also the case where the model is not the one doing the asking. Once an
agent reads files, text written by other people flows into the conversation and
the model treats it as input. A README in a dependency can contain a sentence
addressed to the agent. That is prompt injection, it arrives through tool
results rather than through you, and part three deals with it properly. What
matters here is that a gate written in Python is not persuadable by a sentence
in a file, whereas a rule written in a prompt is exactly the sort of thing a
sentence in a file gets to argue with.

### Why one function and not four

This is the design decision the section is named after, so here it is at full
length.

The alternative is obvious and it is what most people write first. Put the
check in each tool, where the path is used.

```python
def read_file(path):
    target = (WORKSPACE / path).resolve()
    if not target.is_relative_to(WORKSPACE):
        return "Error: outside the workspace"
    ...


def write_file(path, content):
    target = (WORKSPACE / path).resolve()
    if not target.is_relative_to(WORKSPACE):
        return "Error: outside the workspace"
    ...


def edit_file(path, old, new):
    target = (WORKSPACE / path).resolve()
    # ... and so on, four times
```

Every copy is correct. The code works. And it is still the wrong answer, for
two reasons that are worth separating.

A rule spread across four places is a rule one of them will forget. Not
today. Today you have four functions and you wrote all four in the same hour
with the same idea in your head. The forgetting happens in six weeks when you
add `append_file`, or `copy_file`, or `delete_file`, and you write it by
copying the shape of `read_file` and adjusting. Or it happens when somebody
improves the check, correctly, in three of the four functions, because they
found three with a search and there was a fourth that spelled it slightly
differently. Or it happens when a tool grows a second path argument, like a
rename with a source and a destination, and only the first one gets checked.

The failure mode of duplicated security is never that all the copies are wrong.
It is that one of them is, and the other three keep working perfectly and make
the whole thing look fine.

A security rule you cannot review in one sitting is not a security rule.
This is the sharper half of the argument. Ask what it takes to answer the
question "can this agent read files outside its workspace?" With one gate, you
read twenty lines and you are done, and you can be confident because you can
also check that no tool builds a path any other way. With four copies, you have
to read four functions, confirm all four checks are the same check, confirm
none of them has an early return before the check, and confirm nobody added a
fifth tool since you last looked. The first review is a task. The second is a
standing obligation, and standing obligations are not met.

Notice that this argument has nothing to do with typing less. It would still be
the right call if `resolve_inside` were forty lines and the duplication were
four. The value is not that the code appears once. It is that the *decision*
appears once, in a place with a name, so that reasoning about it is a bounded
piece of work.

You can see the consequence in how small each tool became.

```python
def read_file(path):
    target = resolve_inside(path)
    if not target.is_file():
        return f"Error: {path} does not exist"
    return truncate(target.read_text(encoding="utf-8", errors="replace"))
```

There is no security in `read_file`. It is four lines about reading a file, and
the only trace of the gate is that its first line calls it. That is what a
tool should look like once the rule lives somewhere else. If you ever want to
know whether a new tool is safe, the question is not "did you write the
checks?" It is the much easier "does it call `resolve_inside`?"

### Why an exception rather than a returned error

Look again at the two exits. On refusal, `resolve_inside` raises. It does not
return `None` and it does not return an error string.

That is deliberate, and it is the one place in this file where raising beats
returning.

If the gate returned a sentinel, every caller would have to check for it, and a
caller who forgot would carry on with `None` or with an unvalidated path. The
mistake would be silent, which is precisely the failure we spent the last
subsection eliminating. An exception cannot be forgotten. A tool that ignores
the result of `resolve_inside` does not exist, because there is no result to
ignore when the path is refused. Control simply leaves.

The exception is caught in exactly one place, at the edge, in `tools.run`.

```python
def run(name, arguments):
    function = FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**arguments))
    except WorkspaceError as error:
        return f"Error: {error}"
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"
```

Compare that with lesson 06's version and you will find one new clause. The
`except WorkspaceError` arm is above the general one so that a refusal comes
back as a clean sentence rather than as `WorkspaceError: ...` with the class
name attached. The model reads that sentence, and a sentence that reads like an
explanation gets a better response than a sentence that reads like a crash.

This is the same principle as the parse error in lesson 05. A refusal is not a
disaster to be escalated. It is information the model needs, delivered in the
one channel the model can hear, which is the tool result. The agent asks for
`../../etc/passwd`, gets told it is outside the workspace, and tries something
sensible instead. Nothing crashed, nothing leaked, and the loop kept going.

## 4. What resolve_inside actually stops

Two categories of path get refused by the first check, and they are worth
seeing separately because people usually only think of the first one.

### The parent directory escape

The model asks for a path with `..` in it and walks up out of the workspace.

```python
tools.run("read_file", {"path": "../../secrets.txt"})
```

```text
'Error: ../../secrets.txt is outside the workspace'
```

The mechanics are simple once you write them out. `WORKSPACE / Path(path)`
joins the requested path onto the workspace root, giving something like
`/tmp/agentpath-lesson07-abc/../../secrets.txt`. Then `.resolve()` flattens it,
because that is what `resolve` does with `..` components, and you are left with
`/secrets.txt`. That final path is compared with the workspace, is not inside
it, and the call is refused.

### The absolute path

The model does not bother with `..` and simply names the file it wants.

```python
tools.run("read_file", {"path": "/etc/passwd"})
tools.run("read_file", {"path": "C:/Windows/win.ini"})
```

```text
'Error: /etc/passwd is outside the workspace'
'Error: C:/Windows/win.ini is outside the workspace'
```

Both refused, by the same line, with no special case for either.

The reason one check covers both is a property of `pathlib` that is worth
knowing on its own. When you join a path onto another path with `/` and the
right hand side is absolute, the left hand side is discarded entirely.

```python
>>> from pathlib import Path
>>> Path("/home/me/work") / "notes.txt"
PosixPath('/home/me/work/notes.txt')
>>> Path("/home/me/work") / "/etc/passwd"
PosixPath('/etc/passwd')
```

That behaviour surprises people the first time, and it is occasionally the
cause of a bug. Here it works for us. An absolute path from the model
annihilates the workspace prefix, produces an absolute path pointing somewhere
else, and fails the same containment test that catches `..`. The gate does not
need to know which trick was attempted. It only needs to know where the path
ended up.

### Why resolving first is the thing that makes this work

Now the part that matters more than either example.

The order of operations in that function is not decoration. `resolve_inside`
resolves the path *first* and compares *second*. The temptation, and the thing
you will find in a great deal of real code, is to compare the text of the path
before resolving it. That is easy to write, easy to read, and easy to fool.

Here is the bad version, which is what people reach for.

```python
# do not do this
def resolve_inside_wrong(path):
    if ".." in path or path.startswith("/"):
        raise WorkspaceError("nope")
    return WORKSPACE / path
```

Count the ways past it.

Backslashes are one way. On Windows the model may well send `..\..\etc\hosts`. The
substring `..` is present in that one, so this particular check happens to
catch it, but any check written in terms of `/` separators will not. Path
separators are a platform detail and a string check has to get every platform
right by hand.

A leading component that is not `..` is another. The string
`notes/../../../etc/passwd` does not start with a slash and looks like it
begins with a harmless directory. It escapes three levels. Any check that only
inspects the beginning of the string misses it.

Drive letters and UNC paths get through too. `C:/Windows/win.ini` does not
start with `/` and contains no `..`, so the check above lets it straight
through. So does `\\server\share\file`.

Symbolic links are the one thing string checks cannot fix at all, even in
principle. Suppose the workspace contains a symlink named `data` that points
at `/etc`. The path `data/passwd` contains no `..`, no drive letter, no leading
slash, and no suspicious characters of any kind. It is a completely ordinary
relative path and it reads `/etc/passwd`. No amount of inspecting the text can
detect that, because the information is not in the text. It is on the
filesystem. `.resolve()` follows symlinks, so the resolved path is
`/etc/passwd`, and the containment check refuses it.

And one more, which is the classic bug in this family and the reason the code
uses `is_relative_to` rather than a string comparison even after resolving.

The last one is a prefix that is not a parent. Suppose you resolved properly
but then compared with `str(candidate).startswith(str(WORKSPACE))`. With a
workspace of `/home/me/work`, the path `/home/me/workspace_evil/notes.txt`
passes that test, because the workspace string really is a prefix of it. It is
not inside the workspace. It is a sibling directory whose name happens to start
the same way. `is_relative_to` compares path components rather than characters,
so `work` and `workspace_evil` are simply different components and the test
fails correctly.

Put those together and the rule is short. Turn the request into a real,
absolute, symlink free path first, then ask one question about where that path
actually is. Never try to decide the question from the request itself, because
the request is text and text has an unlimited number of ways to describe the
same destination.

There is one small piece of the condition left to explain.

```python
    if candidate != WORKSPACE and not candidate.is_relative_to(WORKSPACE):
```

`Path.is_relative_to` already returns `True` when the two paths are equal, so
the first half of that condition is not strictly necessary. It is there to make
the intent explicit, because `list_files(".")` resolves to exactly the workspace
root and a reader should not have to go and check the standard library's
behaviour on the equality case to be sure the common call works. This is a
place where a redundant clause buys clarity in code that people will read
carefully and rarely, which is a good trade in a security function and a bad
one almost everywhere else.

Note also that `is_relative_to` needs Python 3.9 or newer. On an older
interpreter you would write the same test with `os.path.commonpath`, and you
would be more likely to get it subtly wrong, which is a decent argument for the
version requirement in this course.

## 5. The credential deny list

The second refusal in `resolve_inside` has nothing to do with where a file is.
It is about what a file is, and it applies to files that are perfectly, legally,
unambiguously inside the workspace.

```python
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "credentials"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def looks_like_a_secret(name):
    lowered = name.lower()
    if lowered in SECRET_NAMES or lowered.startswith(".env."):
        return True
    return Path(lowered).suffix in SECRET_SUFFIXES
```

```python
tools.run("read_file", {"path": ".env"})
tools.run("read_file", {"path": "deploy.pem"})
```

```text
'Error: this tool refuses to touch .env because credential files must not enter the conversation or be changed by an agent'
'Error: this tool refuses to touch deploy.pem because credential files must not enter the conversation or be changed by an agent'
```

### The specific failure this prevents

Walk through it one step at a time, because the shape of this failure is
unusual and the unusual part is what makes it serious.

You start an agent in your project directory and ask it something ordinary.
"Why is this deploy script failing?" The agent lists the directory, sees a
`.env` file, and reasons entirely correctly that a deploy script probably reads
its configuration from there. So it calls `read_file` with `.env`.

Nothing has gone wrong yet in any sense the model would recognise. It is being
helpful. Reading the config file is the right instinct.

The tool returns the contents. Those contents become the `content` of a message
with the role `tool`, and that message is appended to `messages` in `agent.py`.
Your API key, in plain text, is now item four in a Python list.

Here is where it stops being a normal mistake. Look at what the loop does next.

```python
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
```

and then, at the top of the next iteration,

```python
        text, calls = provider.stream(messages, schemas, ...)
```

The entire `messages` list is sent. Not the new part. All of it, every turn.
That is how the conversation works and lesson 02 explained why. The consequence
is that your key does not get sent once. It gets sent on this request, and on
the next request, and on every request for the rest of the session. A twenty
turn conversation transmits it twenty times.

It also gets written to whatever you write conversations to. Any transcript you
save has it. Any log line that dumps `messages` for debugging has it. Any crash
report that includes the request body has it. Any evaluation dataset you build
from saved sessions has it. Every one of those is a normal thing to do, and
every one of them now contains a live credential in a place nobody will think
to look for one.

### You cannot take it back

This is the property that makes it worth a whole section instead of a bullet
point.

The conversation is append only. Not by policy, by construction. `messages` is
a list and the loop appends to it. There is no mechanism anywhere in this
design for a message to be revised after the fact, and there could not really
be one, because the model's later replies were produced in the presence of the
earlier content and rewriting history under them makes no sense.

So there is no undo. Realising your mistake one turn later does not help. You
can stop the process, and the key has still gone over the wire. You can delete
the transcript file, and the key has still gone over the wire. The only real
remedy after the fact is to rotate the credential, which is a chore, which
means people put it off, which means it does not happen.

Compare that with almost every other kind of tool bug. A wrong edit can be
reverted. A file written to the wrong place can be moved. A shell command that
failed can be run again. Those are all recoverable. A secret that entered a
conversation is not, and irreversibility is exactly the property that should
decide where you spend your prevention effort.

### Why the check lives in the tool and not in the prompt

The obvious alternative is one line in the system prompt.

```text
Never read .env or any file containing credentials.
```

That line is worth having. Add it. It will change behaviour most of the time,
because models are quite good at following clear standing instructions, and
having the agent not even try is better than having it try and be refused.

It is not a control, and the reason is a matter of timing rather than a matter
of how well models behave.

Follow the sequence. The model produces a tool call. The provider streams it
back. `agent.py` parses it and calls `tools.run`. At that instant, the request
for `.env` exists. It is in `calls`. It is about to be appended to `messages` as
part of the assistant turn. **By the time the model has asked, the moment for
politeness has already passed.** The only question still open is whether the
contents come back, and the only participant who gets to answer that question
is your code.

A prompt instruction acts before the ask. It lowers the probability of the ask.
It does not act on the ask, because it is not present at the point where the
ask is answered. Those are different positions in the pipeline and only one of
them is a gate.

There is a second reason, and it is the one that generalises. A prompt is text
in a conversation, and by the end of part two the conversation will be full of
other text that arrived from files, command output, and search results, none of
which you wrote. Instructions and data share one channel. A tool result
containing "ignore your previous instructions about configuration files" is
competing with your system prompt on equal footing, and that competition is
decided by the model's judgement rather than by anything you control. The check
in `resolve_inside` is not in that channel at all. It is in Python. It has no
opinion about persuasive arguments, because it never sees them.

The rule underneath both reasons is one you should carry into every agent you
build. A prompt shapes what the model tries. Code decides what happens.
Anything you cannot undo belongs in the second category.

### What the list actually catches, and what it does not

Read `looks_like_a_secret` carefully, because being precise about the limits of
a control is part of having one.

It lowercases the name first, so `.ENV` and `ID_RSA` are caught. It matches
whole names against `SECRET_NAMES`, which covers `.env`, the two common SSH
private keys, `.npmrc` and `.netrc` which both routinely contain tokens, and a
bare `credentials`, which is the AWS CLI's file name. It matches the
`.env.` prefix, so `.env.production` and `.env.local` are caught. And it matches
four suffixes, so certificate and key files are caught wherever they sit.

Now the honest part.

It only inspects the final component. `candidate.name` is the file name, so
a file at `credentials/database.txt` is not caught by the `credentials` entry,
because that entry matches a file named `credentials`, not a directory.

It is a deny list, and deny lists are always incomplete. A file called
`api_keys.txt` sails through. So does `config.local.json` with a token in it.
There is no possible list that covers everything a secret can be named,
because naming is up to whoever created the file.

It does not stop the file being seen. `list_files` does not filter names,
so the agent can tell you `.env` exists. Here is that, exactly as it happens.

```text
'.env\ncalc.py\nnotes.txt'
```

Which raises the fair question of why bother with something this leaky.

Because of what it is aimed at. This control is not aimed at an attacker who is
trying to get your key out, and it would be poor at that job. It is aimed at a
helpful model making the single most common and most expensive mistake
available to it, which is opening the file that is literally named after the
environment configuration. That one specific case covers most of the real
incidents, it costs six lines, and it fails closed on the names that matter
most.

Knowing that a control is partial is not a reason to skip it. It is a reason to
know which threat you have addressed. The complete answer, which is a permission
system that asks you before anything sensitive happens rather than guessing from
file names, is part three.

One more detail worth noticing. The deny list lives in `resolve_inside`, which
means it applies to `write_file` too, not only to reading. The agent cannot
overwrite your `.env` either. That came free from putting the rule in the gate
rather than in `read_file`, and it is a small concrete example of the argument
from section 3. Rules in one place get applied everywhere by default. Rules in
four places get applied in the four places somebody thought of.

## 6. Why edit_file refuses an ambiguous match

This is the most interesting design decision in the chapter, and it is the one
that separates a file tool that works in a demo from one that works on a real
codebase.

```python
def edit_file(path, old, new):
    target = resolve_inside(path)
    if not target.is_file():
        return f"Error: {path} does not exist"
    text = target.read_text(encoding="utf-8")
    found = text.count(old)
    if found == 0:
        return (
            f"Error: the text to replace was not found in {path}. "
            "Read the file again and copy the exact text including whitespace."
        )
    if found > 1:
        return (
            f"Error: the text to replace appears {found} times in {path}. "
            "Include more surrounding lines so the match is unique."
        )
    target.write_text(text.replace(old, new), encoding="utf-8")
    return f"Edited {path}"
```

### What it is

`edit_file` replaces one exact run of text with another, and it does the
replacement only when the old text occurs exactly once in the file. Zero
matches is an error. Two or more matches is an error. One match is an edit.

Note that it counts before it writes. `found = text.count(old)` runs against the
file contents, both refusals happen, and only then does `text.replace` execute.
There is no partial state. Either the file is written once, correctly, or it is
not touched at all.

### Why we are doing it

Because the natural implementation is a silent corruption machine, and it
corrupts in a way that is almost perfectly designed to escape notice.

Here is the natural implementation.

```python
def edit_file(path, old, new):
    target = resolve_inside(path)
    text = target.read_text()
    target.write_text(text.replace(old, new))
    return f"Edited {path}"
```

`str.replace` replaces every occurrence. That is what it has always done and it
is the right behaviour for `str.replace`. It is a disaster as a tool for a
model, because the model has no idea how many occurrences there are.

Think about what the model is actually working with. It read the file some
turns ago. It is now producing an `old` string from memory, character by
character, aiming to identify one specific place. It is not running a count. It
is not looking at the file. It picked a snippet that felt distinctive to it,
which is not at all the same thing as a snippet that appears once.

Now suppose the file is this.

```python
def parse(line):
    total = 0
    ...

def summarise(rows):
    total = 0
    ...

def report(rows):
    total = 0
    ...
```

The model wants to change the initial value in `summarise` only, so it sends
`old="total = 0"`. With the naive implementation, all three change. The tool
returns `Edited notes.py`, which is true. The model reads that, concludes the
task went as planned, and moves on. You read it too, and it looks like a normal
successful step in a trace full of normal successful steps.

Two of those three edits are wrong and nobody in the system knows. The model
does not know, because the only feedback it got was the word `Edited`. You do
not know, because you were watching the trace and the trace said it worked.
The program does not know, because both of the other functions still parse
perfectly and still run. They just compute the wrong thing now.

That is the specific failure and it is worth naming precisely. It is not a
crash. It is not an error the loop can feed back. It is a change to code you
did not ask to change, reported as a success, discovered later by whoever is
unlucky, at a distance from the cause that makes the connection hard to see.

Here is the refusal instead, exactly as the tool produces it.

```text
'Error: the text to replace appears 3 times in notes.py. Include more surrounding lines so the match is unique.'
```

And the other refusal, for the case where the model's remembered snippet does
not match the file at all, usually because of whitespace.

```text
'Error: the text to replace was not found in notes.py. Read the file again and copy the exact text including whitespace.'
```

### Why this way and not the alternatives

Several other designs are available, and each of them is worse for a reason
worth understanding.

The first alternative replaces the first occurrence only. Use
`text.replace(old, new, 1)` and move on. This is worse than replacing all of
them, which is a strange thing to say until you see why. Replacing everything
at least produces a visible mess. A first occurrence rule silently edits
whichever place happens to come earliest in the file, which is a position the
model was not reasoning about at all. You get an edit in the wrong function,
reported as success, with no signal anywhere. It turns an ambiguity into a coin
flip and hides the coin.

The second takes a line number as well. Have the model send `line=42` and edit
there. Now the tool is exact, and the model is required to track line numbers
across a conversation while the file changes underneath it. Every previous edit
shifts the numbers below it. Models are poor at this arithmetic, and worse, the
resulting error mode is an off by one that lands in the wrong place and
succeeds. Matching on text has the enormous advantage that the model's
identifier for a location is checkable against the file. A line number is not.

The third asks the user which occurrence. Prompt a human every time a match is
ambiguous. This is not wrong, and lesson 08 introduces confirmation for shell
commands where it is exactly right. It is the wrong tool for this problem
because ambiguity here is not a question about intent. It is a question about
specificity, and the model can fix it alone by sending more context. Interrupting
a person to answer something the model can resolve by trying again is a bad
trade, and an agent that asks constantly gets approved reflexively, which
destroys the value of asking at all.

The fourth lets the model send a diff or patch. That is what some real tools do
and it is a legitimate design. It costs you a patch parser, an offset resolver,
and a fuzz matching policy, and it gives models a format they produce less
reliably than plain text. It is a reasonable trade at scale and a bad one for a
tool you want to fit in twenty lines and understand completely.

### An error the model can read beats an edit it cannot see

That subheading is the whole principle, and it is worth stating as a general
rule because it applies far beyond this function.

You are designing for a participant that cannot observe consequences. The model
does not see your filesystem. It does not see the diff. It has no way to notice
that a file changed in three places when it wanted one. Its entire perception of
what happened is the string your tool returned.

That has a direct consequence for how you write tools. Anything the tool does
not say did not happen, as far as the model is concerned. So the tool must never
do something the model would object to and then report success, because a false
success is not recoverable inside the loop. There is no later step where the
model finds out.

A refusal, on the other hand, is completely recoverable, and cheap. Look at what
the loop does with it. The error string goes back as a tool result, the model
reads a sentence telling it exactly what was wrong and exactly how to fix it,
and it sends a new call with three more lines of surrounding context. That is
one extra turn. One extra turn costs a few seconds and a few thousand tokens.
A silent corruption costs an afternoon, and it costs it to somebody who does not
yet know it happened.

Read the two error messages again with that in mind. Neither of them just
reports a failure. Both of them contain the instruction for what to do next.
`Include more surrounding lines so the match is unique` tells the model the
remedy. `Read the file again and copy the exact text including whitespace`
tells the model the likely cause and the remedy together, because the usual
reason for a zero match is that the model reconstructed indentation from memory
and got it slightly wrong. The count is in the message too, since knowing it was
three rather than two tells the model how much more context it needs.

Writing error messages this way is not politeness. It is the interface. The
error string is a prompt, produced by your code, arriving at the moment the
model needs it most, and it deserves the same care as anything in your system
prompt. Lesson 10 makes that argument in full.

### This is what real harnesses do

This is not a teaching simplification that gets replaced by something more
sophisticated later. The unique match rule is what the real tools do.

Claude Code's edit tool requires the old string to be unique in the file and
returns an error asking for more context when it is not. Aider matches exact
blocks and refuses when the block does not resolve to one place. Cursor's apply
model is built around unambiguous anchors. The rule is not universal in its
details, but the principle that an edit must identify exactly one location or
fail is close to it.

They converged on this for the same reason you just read. The alternative
failure is silent, and silent failures in a system that edits your code are not
acceptable at any frequency.

## 7. Why write_file is more dangerous than edit_file

Here are the two tools side by side.

```python
def write_file(path, content):
    target = resolve_inside(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {path}"
```

`write_file` has no equivalent of the count check, and it cannot have one.
`edit_file` can verify a claim about the file before acting, because the model
told it what it expected to find. `write_file` receives no claim at all. It
receives new contents, and new contents are consistent with every possible
current state of the file, so there is nothing to check.

That difference has a sharp practical edge. If the model has a file's contents
slightly wrong in its memory, and it rewrites the whole file from that memory,
everything it misremembered is now the truth on disk. A function it forgot is
gone. A comment it did not think mattered is gone. An import it did not notice
is gone. The tool reports `Wrote 2431 characters to app.py` and every one of
those losses is invisible in that sentence.

`edit_file` cannot do that. Its blast radius is bounded by construction. It
changes one run of text that it proved was present, and every other byte in the
file is carried across untouched because it was never in play.

There is a second cost that is easier to measure. Rewriting a whole file means
the model has to generate the whole file. For a three hundred line source file
that is several thousand output tokens, spent to change one of them. It is
slow, it is expensive, and every token generated is another chance to introduce
a difference nobody asked for. That is the same argument lesson 06 made when it
promised part two would have an edit tool rather than only a write tool, and
here is the promise being kept.

So `write_file` exists because you genuinely need it. Creating a new file
requires it. Replacing a file whose contents are irrelevant requires it. It is
the right tool sometimes and the wrong tool most of the time, and the model has
to be told which is which.

### The description is the only instruction the model gets

Look at what `write_file` actually says about itself in the schema.

```python
        "function": {
            "name": "write_file",
            "description": (
                "Write a whole file, creating it if needed. Use edit_file instead when "
                "you only want to change part of an existing file."
            ),
```

That second sentence is not documentation. It is the mechanism.

Think about what the model has to work with when it decides between two tools.
It has the tool names, the descriptions, and the parameter descriptions. That
is the entire specification. It cannot read `tools.py`. It cannot see that
`edit_file` counts occurrences first. It cannot see that `write_file` truncates
whatever was there. It has never met your codebase, it has no memory of your
previous sessions, and it will not learn from a mistake it made yesterday.

Everything you know about which tool is appropriate and why has to survive the
trip into those few sentences, or it does not reach the model at all.

Now read the other three descriptions with that lens.

```python
            "description": "Read a text file and return its contents.",
```

Short, because there is nothing to disambiguate. There is one way to read a file
and no competing tool.

```python
            "description": (
                "Replace one exact piece of text in a file. The old text must appear "
                "exactly once, so include enough surrounding lines to make it unique."
            ),
```

Two sentences, and the second one is doing real work. It states the constraint
and the remedy in advance, so that the model has a chance to get it right on the
first attempt instead of learning the rule by being refused. Note the phrasing.
It does not say "an error occurs if the text is not unique." It says what to do.
Descriptions written as instructions outperform descriptions written as
specifications, because the model is deciding what to send, not writing a
compliance report.

```python
                    "path": {"type": "string", "description": "Path relative to the workspace"}
```

Three of the four tools repeat that same parameter description, and it is worth
noticing what it is for. It is the workspace rule, restated where the model will
be looking at the moment it constructs a path. The gate in `resolve_inside` is
what makes the rule true. This line is what makes the rule known. You want both,
because a refusal the model could have avoided is a wasted turn even though it
was handled correctly.

The general point is one that catches almost everybody the first time. When a
tool of yours misbehaves in an agent, your instinct will be to look at the
Python. Very often the Python is fine and the description is what is wrong,
because the description is the part the model actually reads. Treat those few
sentences as the user interface of your tool, and write them for a reader who is
capable, motivated, and has no other source of information. Lesson 10 is
entirely about this.

## 8. Truncating output

```python
MAX_OUTPUT = 4000


def truncate(text, limit=MAX_OUTPUT):
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated, {len(text) - limit} more characters]"
```

```python
tools.truncate("x" * 10, limit=4)
```

```text
'xxxx\n\n[truncated, 6 more characters]'
```

Both `read_file` and `list_files` pass their results through it. `edit_file` and
`write_file` do not need it, because they return one short sentence.

### Why a tool result is not a print statement

This is the mental model to fix now, because everything else in this section
follows from it and because it is the thing beginners get wrong.

When you `print` in a normal program, the string goes to your terminal and then
it is over. It cost nothing, it is gone, and printing more of it costs
proportionally more of nothing.

A tool result is not that. It is appended to `messages`, and `messages` is
resent in full on every subsequent call. So a tool result is not a thing you
emit. It is a thing you *install* into the conversation, and it stays installed
until the session ends.

Count what that means for a single large result. Suppose the agent reads a
120000 character log file, which is about 30000 tokens, and the session runs
another fifteen turns after that. Those 30000 tokens are sent on the turn they
arrived and on all fifteen turns after it. You paid for that file sixteen times.
It is also occupying 30000 tokens of a context window that has a fixed size, so
it is crowding out the file you actually need to read on turn twelve, and when
the window fills the earliest and most important part of the conversation is
what has to go.

There is a third cost that is harder to see and often the worst one. A model's
attention is finite in practice even when the context window is not. Burying
one relevant function inside a hundred thousand characters of log makes the
answer worse, not just more expensive. Less input can genuinely produce better
output, which is a counterintuitive claim until you have watched it happen.

So the limit is not stinginess. Four thousand characters is roughly a thousand
tokens, which is a large source file and a very large directory listing. It is
plenty for the job and small enough that a wrong guess about which file to read
costs a rounding error rather than a chunk of the session.

### Why the truncation announces itself

The important part of that function is the suffix.

```text
[truncated, 6 more characters]
```

Silently cutting text would be a bug of exactly the kind section 6 spent its
time on. The model would receive what looks like a complete file, reason about
it as complete, and conclude that a function it needed does not exist. The
tool would have lied by omission and nothing downstream could detect it.

The marker converts that into information. The model now knows the content is
partial, knows roughly by how much, and can respond sensibly by reading a
narrower target or by using the search tools that arrive in lesson 09. It is the
same principle as the edit refusals. Tell the model the truth about what
happened, in the only channel it can hear.

### The related decision in list_files

```python
SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache"}
```

```python
def list_files(path="."):
    target = resolve_inside(path)
    if not target.is_dir():
        return f"Error: {path} is not a directory"
    names = []
    for entry in sorted(target.iterdir()):
        if entry.name in SKIP_DIRECTORIES:
            continue
        names.append(entry.name + "/" if entry.is_dir() else entry.name)
    return truncate("\n".join(names) or "(empty directory)")
```

This is the same economy applied at a different point. Those five directory
names are skipped because they are enormous, uninteresting, and machine
generated. A `node_modules` in a modest project contains tens of thousands of
entries. A `.git` directory contains object files that are not text. Listing
either one would blow through the truncation limit and fill the model's context
with nothing it can use.

Notice the two small touches at the end. Directories get a trailing `/`, which
costs one character each and saves the model from calling `read_file` on a
directory to find out what it is. And an empty directory returns
`(empty directory)` rather than an empty string, because an empty tool result
is ambiguous. It could mean the directory is empty, or that the tool failed
quietly. Saying so removes the ambiguity for one word.

### The forward reference

Everything in this section is a first pass at a subject that gets a chapter of
its own. Part three has a lesson on the token economy, where you will measure
where a session's tokens actually go, learn why a long conversation gets slower
and more expensive per turn even when nothing else changes, and build the
machinery for handling it properly, including summarising older turns and
dropping tool results that are no longer relevant.

The habit to form now, ahead of that chapter, is to ask one question every time
you write a tool. How large can this return value get, and who pays for it, and
how many times? Tools written without asking that question are the single most
common reason an agent that worked beautifully on a small example becomes
unusable on a real one.

## 9. Running check.py and reading the output

`check.py` proves four claims, one per `OK` line. It is worth reading in full
because the first ten lines contain a trap that will catch you when you write
your own tests against this module.

```python
"""Check that lesson 07 works.

This check proves four things. The agent can read a real file. It can edit a
real file and the change lands on disk. It cannot escape the workspace. It
cannot read a credential file, and the secret inside never appears in the
result.

The workspace is set before tools is imported, because tools reads
AGENTPATH_WORKSPACE once when the module loads.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson07-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402
from agent import run  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402
```

### The import order trap

Those imports are below the environment variable assignment on purpose, and the
`# noqa: E402` comments exist to tell the linter that the author knows the rule
being broken and is breaking it deliberately.

The reason is one line in `tools.py`.

```python
WORKSPACE = Path(os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()
```

That is module level code. It runs exactly once, the first time `tools` is
imported, and never again. Set `AGENTPATH_WORKSPACE` after that import and
nothing happens, because `WORKSPACE` was already computed and stored.

If the imports were in the usual place at the top, the workspace would be the
current directory, and the test that tries to read `.env` would be reaching for
a file in your actual project. The check would either fail confusingly or, much
worse, pass while testing something other than what it claims.

Reading configuration once at import is a real trade. It makes the value
constant and cheap and impossible to change mid run, which is a good property
for a security boundary, since a workspace that can be reassigned at runtime is
a workspace an injected instruction might one day talk the harness into
reassigning. The cost is this awkwardness in tests. The exercises at the end
suggest turning it into a function argument so you can see the other side of
the trade for yourself.

### The prompt, and why it is written that way

```python
READ_AND_EDIT = (
    "Fix the bug in calc.py. "
    '[[tool:read_file:{"path": "calc.py"}]]'
    '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]'
)
```

Those `[[tool:...]]` markers are the instruction format this course's fake
server understands, the same one you have used since lesson 03. The mock server
scans the prompt for them and emits exactly those tool calls, so the check
exercises the real loop, the real provider, the real streaming parser, and the
real tools, with only the model's choice replaced by a script.

This is what makes the check deterministic. A real model asked to fix a bug in
`calc.py` would probably do the same thing, and probably is not good enough for
something CI runs on every push.

### Running it

From inside the lesson folder, with the environment variables pointing at a
provider.

```bash
cd lessons/07-file-tools
python check.py
```

```powershell
cd lessons\07-file-tools
python check.py
```

Or run the whole course at once from the repository root, which starts the fake
server for you and sets the variables.

```bash
python ci/run_lessons.py
```

A passing run looks exactly like this.

```text
OK read_file returned the real file

[calling read_file with {'path': 'calc.py'}]
[read_file returned def add(a, b):
    return a - b
]

[calling edit_file with {'path': 'calc.py', 'old': 'return a - b', 'new': 'return a + b'}]
[edit_file returned Edited calc.py]
The tool returned Edited calc.py.
OK the agent edited a real file on disk
OK a path outside the workspace was refused
OK reading .env was refused and the secret did not leak
```

Four `OK` lines, which is the whole claim of the lesson.

### Reading it line by line

The first `OK` comes before any model is involved at all.

```python
    if "return a - b" not in tools.read_file("calc.py"):
        fail("read_file did not return the file contents")
```

`read_file` is called directly, in process, and the assertion is that the real
bytes from a real file on disk came back. This is deliberately the least
interesting test in the file and it belongs first, because if it fails then
every later failure is a consequence and you would waste time debugging the
wrong layer.

The tool trace in the middle is `agent.py` printing, and it is unchanged
code from lesson 06 producing it. Read the shape of it. There is a blank line,
then `[calling read_file with ...]`, then the result, then the same pair for
`edit_file`, then a sentence of model text. That is two full turns of the agent
loop. Tool call, result appended, model called again, second tool call, result
appended, model called again, model answers in words, loop returns.

The blank lines at the top of each pair come from the `\n` at the front of the
`[calling ...]` message, which normally separates streamed text from the tool
trace. On a turn where the model went straight to a tool call there was no text
before it, so the newline lands on an empty line. Lesson 06 explained the same
artefact.

Notice that `[read_file returned ...]` prints the file contents across two
lines and closes the bracket on a line of its own. That is the actual file, with
its trailing newline intact, being echoed into the trace. It is a small
reminder that tool results are arbitrary text rather than tidy one line values,
which is exactly why section 8 exists.

`The tool returned Edited calc.py.` is the fake server's final sentence. Its
`decide` function turns any tool result into that sentence, which is how the
loop reaches a turn with no tool calls and exits.

The second `OK` is the one that matters most, and note what it checks.

```python
    run(provider, READ_AND_EDIT)
    if "return a + b" not in (workspace / "calc.py").read_text(encoding="utf-8"):
        fail("the agent did not edit the file on disk")
```

It does not inspect what `run` returned. It reads the file off the disk. That is
the correct assertion for a lesson about side effects, because the tool
reporting `Edited calc.py` is a claim and the file contents are the fact.
Testing the claim would pass even if `edit_file` returned its success message
without writing anything.

The third `OK` goes around the model entirely.

```python
    escape = tools.run("read_file", {"path": "../../secrets.txt"})
    if "outside the workspace" not in escape:
        fail(f"an escape attempt was not refused. Got {escape!r}")
```

`tools.run` is called directly with a path no model produced. That is right,
because the property under test is a property of the gate, and involving the
model would make the test depend on the model choosing to try the bad path. You
test a control by attacking it yourself.

The fourth `OK` has two conditions and both are load bearing.

```python
    secret = tools.run("read_file", {"path": ".env"})
    if "refuses to touch" not in secret or "supersecretvalue" in secret:
        fail(f"the credential file was not protected. Got {secret!r}")
```

The first condition checks that the refusal happened. The second checks that the
secret is not in the returned string. The second is not redundant, and the
reason is a real category of bug. Imagine a future version of this tool that
reads the file first and then decides whether to allow it, and includes the
contents in the error message for debugging. That version would refuse, so the
first condition passes, and it would leak, which is the entire thing the control
exists to prevent. The check asserts on the outcome you care about rather than
only on the mechanism you happened to build.

### If it fails

`FAIL read_file did not return the file contents` means the file was not
written where `tools` is looking, which almost always means `AGENTPATH_WORKSPACE`
was set after `tools` was imported. Check the import order.

`FAIL the agent did not edit the file on disk` with a clean tool trace above it
means `edit_file` returned an error rather than editing. Read the trace and look
at what `[edit_file returned ...]` actually says. The two likely messages are
the zero match one and the multiple match one, and both name the cause.

`KeyError: 'AGENTPATH_BASE_URL'` means the provider variables are not set in
this shell. Run `ci/run_lessons.py` from the repository root instead, or set
them yourself as lesson 06 showed.

## 10. What you cannot do yet

Stop and look at what the agent gained in one file.

It can list a directory and see what is there. It can read any text file inside
its workspace. It can create a file, including the directories on the way to
it. It can change one exact piece of text in an existing file, and it will be
told clearly when its target was ambiguous or absent. It cannot leave the
workspace, in either direction, by any path expression. It cannot put your
credentials into the conversation. Nothing it returns can flood the context
window without saying so.

And it still cannot find out whether any of that worked.

That is the gap, and it is a big one. The agent in this chapter edited
`calc.py` and changed `return a - b` into `return a + b`. Was that right? The
agent has no idea. It cannot run the file. It cannot run the tests. It cannot
run `python -c` to check that `add(2, 3)` is now `5`. It made a change, it was
told the change landed on disk, and that is the end of its knowledge.

Think about what that costs. Every agent in this chapter is working open loop.
It reasons, it acts, and it never observes the result of acting. Every
correction has to come from you, reading the diff yourself and typing another
instruction. The agent cannot notice a typo it introduced, cannot discover that
its fix broke a different test, and cannot try a second approach when the first
one did not work, because it has no way to learn that the first one did not
work.

The thing that closes that loop is a tool that runs commands, and it is lesson
08. Once the agent can run the test suite, read the failure output, edit again,
and run it again, it becomes something qualitatively different from what you
have now. That is the entire difference between an assistant that suggests
changes and an agent that gets to a working result.

It is also the most dangerous tool in the course by a wide margin, which is why
the confirmation prompt is in it on the first day it exists rather than added
afterwards. `resolve_inside` bounds where the file tools can reach. There is no
equivalent boundary that a shell command respects, because a shell command can
do anything the user running it can do, including undoing every constraint in
this chapter. That is the subject of lesson 08 and the reason it takes safety
even more seriously than this one did.

### Exercises before you move on

Four, in increasing order of difficulty.

First, try to get out. Start a Python session, set `AGENTPATH_WORKSPACE` to a
temporary directory, import `tools`, and spend ten minutes calling
`tools.run("read_file", {"path": ...})` with the nastiest paths you can invent.
Backslashes, mixed separators, a very long chain of `..`, a UNC path, a path
with a null byte in it, a trailing dot on Windows. Write down anything that
behaves in a way you did not expect. Then create a symlink inside the workspace
pointing outside it and confirm the refusal, since that is the case that
resolving first exists to catch.

Second, break `edit_file` on purpose. Change it to a plain
`text.replace(old, new)` with no counting, then run it against a file with three
identical lines and watch it report `Edited` while corrupting two places you did
not mean. Now imagine that inside a fifty step agent run. This takes two
minutes and it is the fastest way to make section 6 permanent.

Third, make the workspace an argument instead of a module level constant.
Give the tools a small class that holds a root and has `read_file`,
`write_file`, `edit_file` and `list_files` as methods, and build `FUNCTIONS`
from an instance of it. `check.py` no longer needs its import ordering trick.
Then decide for yourself which version you prefer, and be able to say why. There
is a real argument on both sides and the exercise is having it.

Fourth, add a fifth tool, `append_file`, that adds text to the end of a file.
Write it, then look at what you wrote. Did you call `resolve_inside`? Did you
truncate anything it returns? Did you write a description that tells the model
when to use it rather than `write_file`? Now go back to section 3 and reread the
argument about a rule spread across four places, with your own new function in
front of you as evidence.

On to lesson 08, where the agent gets to run things.
