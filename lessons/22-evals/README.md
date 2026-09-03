[อ่านภาษาไทย](README.th.md)

# Lesson 22. Evals and choosing a model

This chapter builds the instrument that every chapter before it has been
missing, and it builds it out of a dataclass with four fields, one optional, a runner with
two branches, and a grader that reads one word.

That is not modesty. The reason evaluation gets skipped is that people imagine
it as a platform, so they postpone it until there is time to build a platform,
and there never is. The whole of `evals.py` is two hundred and five lines
including the docstrings. There was always time.

Here is what is in this folder and where each file came from.

```text
lessons/22-evals/
    evals.py            new. Task, Result, run_one, run_evals, judge, compare, report
  check.py            new. seven claims about the measuring instrument
  grep_worker.py      identical to lesson 21

  fanout.py           identical to lesson 21
  agent.py            identical to lesson 21
  tools.py            identical to lesson 21
  session.py          identical to lesson 21
  permissions.py      identical to lesson 21
  providers.py        identical to lesson 21
  prompt.py           identical to lesson 21
  context.py          identical to lesson 21
  usage.py            identical to lesson 21
  retrieval.py        identical to lesson 21
  retry.py            identical to lesson 21
  cancel.py           identical to lesson 21
  subagent.py         identical to lesson 21
  main.py             identical to lesson 21
  mcp.py              identical to lesson 21
  mock_mcp_server.py  identical to lesson 21
  README.md           this file
```

Seventeen of the nineteen Python files are byte for byte what they were last
chapter, which is checkable rather than claimed.

```bash
cd lessons
for f in agent.py fanout.py tools.py providers.py usage.py permissions.py; do
  diff -s 21-multi-agent/$f 22-evals/$f
done
```

```text
Files 21-multi-agent/agent.py and 22-evals/agent.py are identical
Files 21-multi-agent/fanout.py and 22-evals/fanout.py are identical
Files 21-multi-agent/tools.py and 22-evals/tools.py are identical
Files 21-multi-agent/providers.py and 22-evals/providers.py are identical
Files 21-multi-agent/usage.py and 22-evals/usage.py are identical
Files 21-multi-agent/permissions.py and 22-evals/permissions.py are identical
```

`agent.py` did not change, and this time that fact is doing real work. An eval
harness that required the agent to be modified in order to be measured would be
measuring a different agent from the one you ship. The whole design pressure in
this chapter is to keep the thing being measured untouched by the measurement.

`subagent.py` is in this folder even though nothing in this chapter starts a
child, and so are `mcp.py`, `main.py`, and `mock_mcp_server.py`. That is the
rule every folder from lesson 19 onward follows. Each one carries everything the
course has built so far, so a chapter can be opened on its own and run without
first copying files in from a neighbour.

A full folder is not a claim that the chapter uses all of it, and pretending
otherwise is how a course starts lying about what it depends on. So here is the
sentence the folder listing cannot say for itself. What this chapter actually
depends on is `evals.py`, which imports `run_in_parallel` from `fanout.py` and
nothing else, and the agent stack that `check.py` drives through `agent.py`,
`tools.py`, `providers.py`, `permissions.py`, and `usage.py`. The rest is
carried, not used. If you do want subagents in your own eval runs, `subagent.py`
is right there and unchanged from lesson 21.

## 1. The problem left over from lesson 21

You have been changing the agent for eleven chapters and you do not know
whether it is better.

Be specific about what has changed, because the vagueness is the problem. The
system prompt in `prompt.py` has been rewritten several times since lesson 10.
Lesson 12 put a permission gate in front of the tools. Lesson 14 started
throwing away old messages when the conversation grew. Lesson 16 added a
retrieval tool and put its schema in every single request. Lesson 19 connected
tools you did not write, and warned in its own text that more tools makes the
model choose worse. Lesson 20 replaced a parent reading tool results with a
parent reading a summary written by a child. Lesson 21 ran four of those
children at once against one shared workspace.

Every one of those is a trade. Every one of them was argued for in prose, by
me, in a chapter, and not one of them was measured.

Now suppose you make the twelfth change. You reword one sentence in the system
prompt so the agent stops running `pytest` before it has read the failing test.
You try it on the task that annoyed you, it behaves, and you keep the change.

What you have just learned is that the new prompt handles that one task on that
one run. What you wanted to learn is whether the agent is better. Those are
different claims and only one of them is supported.

This gap is not a small one, and it is worth naming exactly what it does to
you. Without measurement, every improvement is a belief. Beliefs do not
compose. Ten beliefs about ten changes do not add up to knowledge about the
system, they add up to a system that nobody can reason about, because the only
evidence for any part of it is that somebody once watched it work.

The failure mode this produces is specific, and it is worse than a bug. You do
not notice a regression. You accumulate several, each individually defensible,
each shipped by somebody who tried it and was satisfied, and three weeks later
the agent is worse than it was in lesson 18 and there is no way to find out
which change did it. Reverting is no help, because you would have to revert
eleven things to find the one.

What you need is an instrument, and an instrument has a very low bar. It has to
produce a number, the same way, from the same inputs, before and after. That is
all. This chapter builds one.

## 2. Why looking at it does not work

The obvious objection to all of this is that you can see whether the agent
works. You are sitting right there. It either fixed the bug or it did not.

That is true for the run you watched. It is the generalisation that fails, and
it fails for two separate reasons that compound.

**A change is not local, but your attention is.** A system prompt is one block
of text at the front of every request, and the model attends to all of it on
every turn. There is no such thing as editing the part of the prompt that
affects only the task you are looking at. Add the sentence that stops premature
test runs and you have also, invisibly, made the model slightly more reluctant
to run any command, which is fine for the task you tested and quietly wrong for
the task where the right first move is to run the build and read the error.

So the change fixed one task and broke three, and you tested one. You did not
test the one that broke because you did not think of it, and you did not think
of it because the connection between a sentence about tests and a regression in
build handling is not visible from the sentence. This is not carelessness. It
is the normal condition of editing a prompt.

**A single run is close to no evidence.** This one is harder to accept because
it contradicts the mental model most of us bring from ordinary programming. A
function with the same inputs gives the same output, so running it once tells
you what it does. An agent does not work like that.

The request carries a sampling temperature. The same conversation produces
different text on different calls, and different text means a different tool
call, which means a different tool result, which means the second turn starts
from a different place. Divergence compounds across turns, and an agent run is
many turns. Lesson 21 made this worse on purpose, since four agents writing to
one workspace produce a final state that depends on thread scheduling, and
thread scheduling is not something you control.

Put the two together and here is the honest description of what you learn from
watching one run succeed. You learn that success is possible. You do not learn
that it is likely, and likely is the thing you actually care about, because you
are going to run this agent a hundred more times.

The fix for both is the same and it is not clever. Fix a set of tasks. Run all
of them. Count. Do it again after the change and compare the counts. Everything
in `evals.py` exists to make that cheap enough that you actually do it.

## 3. What a task is

Here is the whole definition.

```python
@dataclass
class Task:
    """One thing the agent should be able to do.

    check receives the final answer and the workspace, and returns a pair of
    a boolean and a sentence explaining the verdict. The sentence is not
    decoration. A failing eval you cannot read is a failing eval you will
    ignore.
    """

    name: str
    prompt: str
    check: object
    workspace: object = None
```

Four fields, one of them optional. Take them one at a time, because each is a
decision.

**`name` exists so the report can be read and diffed.** It is the identity of
the task across runs, which is what lets you say that `fixes-the-off-by-one`
passed yesterday and fails today. If tasks were identified by their position in
a list, inserting a task at the top would rename all of them and yesterday's
report would stop being comparable with today's.

**`prompt` is the exact string a person would have typed.** Not a description of
the task, and not a structured object describing what the agent should do. The
instrument has to exercise the same entry point that real use exercises, or you
are measuring something adjacent to the product. This is why the prompt lives
in the task rather than being assembled by the runner from parts.

**`check` is a function, not a string or a pattern.** It receives the final
answer and the workspace and returns a pair. Making it a function is what makes
section 4 possible at all. A declarative check format, however rich, can only
express the comparisons its designer thought of, and the most valuable check in
your suite is usually the one that opens a file, imports a module, or runs a
subprocess. A Python function can do all three today with no new syntax.

**`workspace` is optional because most tasks do not need one.** A question that
is answered in prose has nothing on disk to inspect. A task that edits code
needs a directory that is its own, and section 10 shows how the command line
gives each task the directory named here, falling back to the one shared root
when the task did not name one.

Now the part people delete when they write their own version, which is the
sentence.

A check returns `(passed, detail)` where `detail` is a plain English sentence.
It would be less code to return only the boolean. Every real eval suite that
does this converges on the same end state, so it is worth walking through.

You run the suite in CI. It reports that four of twenty tasks failed and names
them. You open the log and it says `FAIL fixes-the-off-by-one` and nothing
else. To find out what happened you now have to reproduce locally, which needs
a model call, a workspace, an API key and about four minutes, and you have to
do it four times, once per failure. So you do not do it. You look at the diff,
decide the failures are probably flaky, and merge.

That is the actual cost of the missing sentence. Not confusion, but a red
result that nobody investigates, which is exactly as useful as no result and
more expensive to produce. The docstring says it in one line. A failing eval
you cannot read is a failing eval you will ignore.

The sentence is required on the passing path too, and that is deliberate rather
than an oversight. A check that passes for the wrong reason is the most
dangerous object in a test suite, and reading `pass  world check  notes.txt on
disk says done` in the report is the only cheap moment where you might notice
that it is passing because the file was left behind by the previous run.

## 4. Checks that look at the world beat checks that look at the words

This is the most important section in the chapter. If you take one thing from
it, take this, because it is the difference between an eval suite that catches
regressions and one that produces a green tick while the agent quietly does
nothing.

**A check that reads the answer text is checking what the model said. A check
that reads the workspace is checking what the model did.** Those are different
things, and only one of them is what you are paying for.

Consider the obvious check for a task that asks the agent to fix a bug.

```python
def by_words(answer, workspace):
    return "done" in answer.lower(), "the answer contains the word done"
```

This is nearly worthless, and the reason is not that it is imprecise. It is
that a model which did nothing at all will happily say done. Saying done is the
cheapest possible action available to a language model. It requires no tool
call, no file read, no reasoning about the code, and it is what a model
produces when it has lost track of the task and is trying to close the
conversation politely. Your check rewards exactly the behaviour you least want.

It gets worse, because the check is adversarially weak in a way that has
nothing to do with adversaries. You will, over the next few weeks, tune your
system prompt against this suite. Every tuning pass is a small optimisation
against whatever the check measures. If the check measures the presence of a
word, you are running a slow gradient descent towards a model that says that
word, and it will get there. This is not hypothetical mischief. It is what
optimising against a proxy always does.

Now the other kind.

```python
def by_the_world(answer, workspace):
    note = Path(workspace) / "notes.txt"
    if not note.is_file():
        return False, "notes.txt was never created"
    return "done" in note.read_text(encoding="utf-8"), "notes.txt on disk says done"
```

There is no sentence the model can produce that makes this pass. It either
called `write_file` and the bytes are on the disk, or it did not. The check
cannot be talked into passing, because it is not reading anything the model
wrote in prose. That property has a name worth remembering. The check is
grounded, meaning its verdict is a fact about the world rather than a fact
about the transcript.

Here are both checks, in one suite, on one run, against the built in mock
server. The full tasks file is short and appears in section 10. The word check
there looks for the greeting the mock server actually produces rather than for
the word done, because the mock never claims anything, and the point being
demonstrated is that a check reading the answer text passes on a run where
nothing happened.

```text
pass  word check  the answer sounds like it worked
FAIL  world check  notes.txt was never created

1 of 2 tasks passed
```

Read that carefully. The agent produced an answer and wrote nothing. The word
check passed. The world check failed and said, in the report, exactly what it
looked for and did not find. If your suite had contained only the first kind of
check, this run is a green build.

The reverse case is just as instructive. Same two checks, same file, one line
changed so that the agent really does write to the disk.

```text
FAIL  word check  the answer sounds like it worked
pass  world check  notes.txt on disk says done

1 of 2 tasks passed
```

The work was done correctly and the word check failed, because the model
finished with a sentence that did not happen to contain the word it was looking
for. That is a false alarm, and false alarms are how a suite dies. Three of
those and the team stops reading the report.

So the word check is wrong in both directions. It passes when nothing happened
and fails when everything happened. It is not a weak version of the world
check, it is a measurement of an unrelated quantity.

### What grounded checks look like in practice

The pattern generalises past reading a file. Ranked roughly by how hard they
are to fake.

```python
# Strongest. Run the project's own tests in the workspace.
def tests_pass(answer, workspace):
    done = subprocess.run(["pytest", "-q"], cwd=workspace, capture_output=True, text=True)
    return done.returncode == 0, f"pytest exited {done.returncode}"

# Strong. Import the changed module and call the function.
def the_function_is_right(answer, workspace):
    sys.path.insert(0, str(workspace))
    from billing import total
    return total([1, 2, 3]) == 6, f"total returned {total([1, 2, 3])}"

# Fine. The file on disk contains the fix and not the bug.
def the_edit_landed(answer, workspace):
    text = (Path(workspace) / "billing.py").read_text(encoding="utf-8")
    return "range(len(items))" not in text, "the old loop is gone"

# Weak, and only for tasks whose entire output is prose.
def the_answer_names_the_file(answer, workspace):
    return "billing.py" in answer, "named the file"
```

The first one is the reason the `workspace` field exists. A task whose check
runs the project's own test suite in a directory the agent just edited is very
close to the thing you actually want to know, and it needs no eval framework
features at all beyond being handed a path.

### The honest exception

Some tasks have no world to check. If the task is to explain why a design
choice was made, the entire deliverable is prose, and there is no file to open
afterwards. For those, reading the answer is not a weak substitute for
something better, it is the only thing there is.

That is what section 5 is for, and note the ordering carefully. You reach for a
judge when the world offers nothing to check, not when checking the world would
be inconvenient.

## 5. Mechanical checks and judges

The module docstring states the split in four sentences and it is worth reading
before the code.

```text
Two kinds of check exist here and the split matters. A mechanical check is a
function that looks at the world and returns true or false. It is free,
instant, and it has no opinions. A judge asks a model whether an answer is
acceptable, which costs money, takes time, and can be wrong. Use a judge only
for the things a function genuinely cannot decide, such as whether an
explanation is clear.
```

Set the two side by side, because the asymmetry is larger than people expect.

| | mechanical check | judge |
| --- | --- | --- |
| cost per run | nothing | one model call, per task, every run |
| time per run | microseconds | seconds, and it is a network call that can fail |
| determinism | same input, same verdict, always | same input, sometimes a different verdict |
| what it can decide | anything expressible as code | anything expressible in English |
| what it costs you when wrong | a bug in your suite, findable | a wrong number that looks like a measurement |

A judge is a language model grading a language model, which means the grader
has every failure mode the thing being graded has. It can be verbose, it can be
talked round by a confident wrong answer, and it is sensitive to how the
criteria are worded. It is genuinely useful, and it is the more expensive and
less trustworthy instrument on every axis except expressiveness.

Which leads to the rule, and it is a rule rather than a preference.

**Anything checkable by a function should be a function.** If you find yourself
writing criteria that say the answer must mention the file `billing.py`, stop
and write `"billing.py" in answer`. If the criteria say the code must compile,
run the compiler. Every criterion you can move from the judge into a function
makes the suite cheaper, faster, and repeatable, and removes one place where a
model's mood becomes your metric.

Here is the judge, whole.

```python
JUDGE_PROMPT = """You are grading one answer against a standard.

The standard
{criteria}

The question
{question}

The answer
{answer}

Reply with the single word PASS or the single word FAIL, then one short
sentence saying why."""


def judge(provider, question, answer, criteria):
    request = JUDGE_PROMPT.format(criteria=criteria, question=question, answer=answer)
    verdict, _, _ = provider.stream([{"role": "user", "content": request}])
    verdict = (verdict or "").strip()
    first = verdict.split()[0].upper().strip(".,") if verdict.split() else ""
    return first == "PASS", verdict
```

Four things in that function are decisions rather than details.

**The provider is a parameter.** The grader is not the agent's provider by
default and does not have to be the agent's model. It can be, and the laziest
setup uses one model for both, but passing it in is what lets you grade with a
different model from the one being tested. That matters more than it sounds,
because a model asked to grade its own output is being asked whether it did a
good job, and it is not a neutral party in that question.

**There are no tools and no history.** The judge gets one message and answers
once. It is not an agent, it cannot go and look at the workspace, and giving it
that ability would make grading as slow and as variable as the thing being
graded.

**The criteria are a string you write per task.** They belong to the task,
because a standard that fits every task is too vague to grade against. Good
criteria read like a rubric line, for example that the explanation must name
the specific function responsible and must not recommend a rewrite.

**The verdict comes back with the reason attached.** `judge` returns the full
text as the second element, and that is what ends up in the `detail` field of
the `Result`. This is section 3's rule applied to the judge. A failing judged
task tells you the grader's stated reason in the report, which is the only way
you will ever notice that the grader is failing tasks for a reason you did not
intend.

Using it inside a task looks like this.

```python
def explanation_is_clear(answer, workspace):
    return judge(
        grading_provider,
        question="Why does the retry helper not wrap tool calls?",
        answer=answer,
        criteria=(
            "The answer must say that retrying a tool call can repeat a side "
            "effect, and must not claim that retries are unsafe in general."
        ),
    )
```

That is the whole integration. `judge` already returns `(passed, sentence)`,
which is exactly the shape a `check` must return, so a judged task is an
ordinary task and `run_one` never learns that a model was involved in grading
it. That is the same seam as everywhere else in this project. The runner
consults, and implements nothing.

### What a judge gets wrong, and the swap that catches one of them

A judge is wrong in three known ways, and two of them are cheap to defend
against.

A judge prefers longer answers. Shown a complete answer and a complete answer
with three more paragraphs, it leans toward the second, whether or not the
paragraphs help. A judge prefers its own family. A model grading answers from
the same model, or one trained the same way, scores them higher than an
outside grader would, which is the reason the provider is a parameter. And a
judge has a position bias. Shown two answers and asked which is better, it
favours one position more often than that position deserves, usually the first,
by an amount and in a direction that depend on the model and the wording.

The first two are reduced by how you use it, not removed. Criteria that name
what a good answer contains help, and so does comparing answers of similar
length, and grading with a model that did not produce the answers. The third
one is handled by code.

```python
def compare(provider, question, first, second, criteria):
    """Ask a model which of two answers is better, twice, with the order swapped."""

    def ask(left, right):
        request = COMPARE_PROMPT.format(
            criteria=criteria, question=question, first=left, second=right
        )
        verdict, _, _ = provider.stream([{"role": "user", "content": request}])
        verdict = (verdict or "").strip()
        return verdict.split()[0].upper().strip(".,") if verdict.split() else ""

    forwards = ask(first, second)
    backwards = ask(second, first)
    if forwards not in ("A", "B") or backwards not in ("A", "B"):
        # Section 6's rule again. A verdict that is neither letter is not a
        # tie, it is a grader you cannot read, and it must not look like one.
        return "unreadable"
    if forwards == "A" and backwards == "B":
        return "first"
    if forwards == "B" and backwards == "A":
        return "second"
    return "tie"
```

Ask twice, with the answers in the other order the second time. A preference
that survives the swap is a preference about the answers. One that flips with
the order was a preference about the position, and the honest verdict is a
tie. A verdict that is neither letter is not a tie, it is a grader you cannot
read, and it comes back as its own value, which is section 6's rule applied
twice. This costs two calls instead of one, which is the usual price of not
being fooled, and `check.py` proves it with two fake graders, one that only
ever reads position and one that reads the answers, crudely, by length, which
is enough to show a preference that survives the swap. The swap turns the
first into a tie and leaves the second alone.

Pairwise comparison is also the form that model selection in section 9
quietly wants. Grading two models against a standard gives two pass rates.
Comparing their answers to the same question, with the swap, gives a
preference, and preferences are what people actually have about models.

## 6. Why an unreadable verdict counts as a failure

Look again at the two lines that read the verdict.

```python
    first = verdict.split()[0].upper().strip(".,") if verdict.split() else ""
    return first == "PASS", verdict
```

The verdict is taken from the first word. Not searched for anywhere in the
reply, not extracted with a regular expression, not parsed out of JSON. The
first word, uppercased, with a trailing full stop or comma removed.

**Why the first word and not a search.** Because a search is ambiguous in
exactly the cases that matter. Ask a model to grade something and it will
sometimes write that the answer would fail a stricter standard but should pass
here. Search that sentence for the word `FAIL` and you find it. Search for
`PASS` and you find that too. The first word is unambiguous by construction,
and the prompt asks for it explicitly, so the parsing rule and the instruction
agree. When the two disagree you get a grader whose behaviour depends on the
grammar of a sentence, which is not a grader.

**Why anything that is not clearly a pass is a failure.** This is the important
half and it is a safety property rather than a parsing convenience. Suppose the
model replies with `Well, it depends`, which is a real thing graders do when
the criteria are badly written. There are three possible policies.

Treat it as a pass, and a grader that has become confused now produces green
ticks. Your suite reports twenty of twenty on a day when the grader stopped
working, and you ship on the strength of it.

Raise an exception, and one confused grader takes down a suite of forty tasks
that was thirty minutes into a run.

Treat it as a failure, and you get a red line in the report with the grader's
own words in the detail column, in a run that completed. You look at the
report, you see `FAIL  explains-clearly  Well, it depends`, and the thing you
fix is the criteria, which is the thing that was actually broken.

The third is the only one where the system tells you the truth. The docstring
puts it plainly, that a grader that sometimes cannot be read is worse than no
grader, because it looks like a measurement.

The empty case is handled by the same rule. If the model returns nothing at
all, `verdict.split()` is empty, `first` is the empty string, the comparison
with `PASS` is false, and the task fails with an empty detail. No exception, no
index error, no silent pass.

`check.py` pins all three behaviours with a fake provider, which is worth
seeing because it needs no network.

```python
    class Grader:
        def __init__(self, verdict):
            self.verdict = verdict

        def stream(self, messages, tools=None, on_text=None):
            return self.verdict, [], {}

    if judge(Grader("PASS it is correct"), "q", "a", "must be correct")[0] is not True:
        fail("the judge did not read a pass")
    if judge(Grader("FAIL it is wrong"), "q", "a", "must be correct")[0] is not False:
        fail("the judge did not read a fail")
    if judge(Grader("Well, it depends"), "q", "a", "must be correct")[0] is not False:
        fail("an unreadable verdict became a pass, which must never happen")
```

Eleven lines and no model. The reason this works is the provider interface from
lesson 06. `judge` calls `provider.stream` and unpacks three values, so
anything with a `stream` method of the right shape is a provider as far as it
is concerned. A three line class is a perfectly good grader when what you are
testing is the parsing.

## 7. Failures that must not stop the run

Two `try` blocks in `run_one` carry the entire error policy of this chapter.

```python
    usage = None
    try:
        answer, usage = run_agent(task)
    except Exception as error:
        return Result(
            task=task.name,
            passed=False,
            detail=f"the run failed, {type(error).__name__}: {error}",
        )

    try:
        passed, detail = task.check(answer, task.workspace)
    except Exception as error:
        # A check that throws is a failing task, not a crashed eval run. The
        # whole point is to get a report at the end rather than an exception
        # half way through.
        passed, detail = False, f"the check itself failed, {type(error).__name__}: {error}"
```

The first block catches the agent blowing up. Network died, budget exhausted,
tool raised, model returned nonsense that the loop could not handle. The task
fails and the exception type and message go into the detail, and the run
continues.

The second block catches your check blowing up, which is the one people forget
and the one that hurts. Checks are code you wrote at speed while thinking about
something else. They open files that might not exist, index into lists that
might be empty, and import modules the agent was supposed to create. A check
raising `FileNotFoundError` is not an unusual event, it is Tuesday.

The principle behind both is one sentence. **A report you never receive is
worse than a red line.**

Work through what the alternative costs, because it is not obvious until you
have lived it. You have a forty task suite. Each task is a real agent run,
call it forty seconds, so the suite takes about half an hour on one worker.
Task eleven's check raises `KeyError` because the agent renamed a dictionary
key. Without the second `try`, the exception propagates out of `run_one`, out
of `run_evals`, out of your script. You get a traceback and no report. You have
now spent seven minutes and learned one thing, that one check has a bug, and
you know nothing whatsoever about tasks twelve through forty. Fix the check,
run again, and if task nineteen also has a bug you get to do it a third time.

With the `try`, you get all forty verdicts, one of which says
`FAIL  eleven  the check itself failed, KeyError: 'total'`. You fix that check,
and you also already know which of the other thirty nine regressed. One run
instead of three, and the failure is described in the place you were already
looking.

Two details in that code are deliberate and easy to get wrong.

**The failure is described, not summarised.** The detail includes
`type(error).__name__` and the message. `FileNotFoundError` and
`AssertionError` mean completely different things about who is at fault, and a
detail that says only that the check failed sends you back to reproducing
locally, which is the loop section 3 was trying to break.

**A failed run reports no cost.** On the first path, `usage` is still `None`
when the exception is caught, so the `Result` carries an empty usage dictionary.
That is honest in the sense that the runner never received a usage object, and
misleading in the sense that a run which died on turn nine did in fact cost
money. Section 9 depends on those cost numbers, so know that failures
understate the true spend. The packaged version of this runner in
`src/agentpath/evals/runner.py` closes the gap by reading `agent.usage` on the
failure path, because there the runner builds the agent and can still reach it.

## 8. Order and parallelism together

`run_evals` has two branches. The first is the whole function for anyone who has
not hit the wait yet.

```python
    tasks = list(tasks)
    if workers <= 1:
        return [run_one(task, run_agent) for task in tasks]
```

The second exists because a suite is a set of independent agent runs, which is
precisely the shape lesson 21 built `run_in_parallel` for, and forty times forty
seconds is twenty seven minutes of a machine sitting idle on a socket.

```python
    def make(task):
        def produce():
            yield run_one(task, run_agent)

        return produce

        # Jobs are labelled by position rather than by name. Two tasks are allowed
    # to share a name, and keying on the name would quietly merge them, turning
    # one task's verdict into the other's and changing the exit code with it.
    labelled = [(str(index), make(task)) for index, task in enumerate(tasks)]
    collected = {}
    for label, event in run_in_parallel(labelled, workers):
        if isinstance(event, Result):
            collected[label] = event
    return [
        collected.get(str(index), Result(task.name, False, "the task produced no result"))
        for index, task in enumerate(tasks)
    ]
```

Note first how little there is. `run_in_parallel` wants a list of
`(label, callable)` where the callable returns an iterator, and `run_one`
returns a single `Result`, so `produce` is a generator that yields exactly once.
An eval task is a one event job. No new concurrency machinery was written for
this chapter, which is the return on having cut the seam in lesson 21 at
callables rather than at agents.

Now the part that matters, which is the last three lines.

Results arrive in completion order. Task seven finishes first because its
prompt was short, then task two, then task nine. `collected` is keyed by
position, and then the return statement walks `tasks`, the list you wrote, and
pulls each result out by index. The output order is the order you wrote, always,
whatever the threads did.

**Why bother.** Because the entire purpose of this chapter is comparison, and
two reports you cannot lay side by side are not a measurement. Run the suite
before the change and after it, and if the rows are in completion order the two
reports have different row orders for reasons that have nothing to do with the
change, since completion order depends on how long each model call happened to
take. `diff` on those two files is noise. `diff` on two reports in written order
shows you exactly the lines that changed verdict, which is the one thing you
wanted to see.

There is a second reason and it is human. A suite has a shape you remember. The
easy tasks at the top, the three hard ones at the bottom. Reading a report where
that shape is preserved lets you notice at a glance that the failures are all in
the hard block, or worse, that one of the easy ones went red.

**Why `collected.get` with a fallback.** Because a task that produced no
`Result` must still occupy its row. The `isinstance(event, Result)` filter drops
anything that is not a result, which in practice means a `FanoutError` from
lesson 21 arriving because `run_one` itself failed rather than the agent inside
it. Without the fallback, `collected[task.name]` raises `KeyError` on a suite
that is otherwise complete, and section 7's rule dies at the last line of the
function. With it, the row reads `FAIL  nine  the task produced no result`, and
the report survives.

### Two honest limits

**Task names may repeat without harm.** `collected` is keyed by position, so
two tasks called `edits-the-file` each keep their own verdict and the report
shows both rows. An earlier version keyed by name, and the second result
quietly overwrote the first. Keep names distinct anyway, for the reader of the
report, and because section 3's argument about comparing reports across edits
rests on the name meaning one thing.

**Parallel eval runs are subject to lesson 21's warning about shared state.** If
two tasks name the same `workspace` and both edit it, running them on separate
workers means each is looking at a directory the other is changing. The runner
does not copy workspaces and does not know it should. Give each task its own
directory, or run those tasks with `workers=1`.

## 9. Choosing a model, which is the same problem

Everything above is usually filed under testing, and model choice is usually
filed under strategy, and that split is why people spend weeks arguing about
models with no data. They are the same problem. Both are the question of
whether one configuration of the system does better work than another, and a
model is just one more thing in the configuration, next to the system prompt
and the tool list and the fan out width.

So state the position plainly. **Saying one model is better than another,
without a task list, is a guess.** It may be an informed guess, from somebody
who has used both a great deal, and it is still a guess about your workload,
which is not the workload they used. Public benchmark scores are a guess with
better production values. They measure competition mathematics and multiple
choice trivia. Your agent reads a stack trace, greps a repository, and edits
one line without breaking the file, and the correlation between those is real
but nothing like tight enough to pick on.

You already have the apparatus. Look at what `run_one` takes.

```python
def run_one(task: Task, run_agent) -> Result:
    """Run one task and turn whatever happened into a verdict.

    run_agent is a function taking a task and returning (answer, usage).
    Passing a function rather than an agent means the eval harness does not
    need to know how an agent is built, which is what lets you point the
    same task list at two different models.
    """
```

The second argument is a function, not an agent. That was chosen for this
section. If `run_evals` took an agent object, the model would be baked into the
thing you handed it, and comparing two models would mean building two harnesses
and hoping they were otherwise identical. Because it takes a builder, the model
is the only variable you change.

```python
def with_model(model):
    def run_agent(task):
        usage = Usage()
        provider = OpenAICompatProvider(BASE_URL, API_KEY, model)
        answer, _ = run(provider, task.prompt, permissions=Permissions(auto_approve=True), usage=usage)
        return answer, usage

    return run_agent


small = run_evals(TASKS, with_model("the-small-one"))
large = run_evals(TASKS, with_model("the-large-one"))
```

Same `TASKS`, same checks, same order out. Everything except the model string
is held fixed, which is what makes this an experiment rather than two
anecdotes.

### The three columns

Compare on three numbers and refuse to compare on fewer.

**How many tasks passed.** Straight from the report. This is the only column
that is about quality, and on its own it will talk you into the most expensive
model available for jobs that did not need it.

**What it cost.** `Result.usage` carries `prompt_tokens`, `completion_tokens`
and `calls` per task, summed from what the provider actually reported rather
than estimated locally. `Usage.cost` turns tokens into money and takes the
prices as arguments, for the reason its own docstring gives, that a stale price
table is worse than no price table since it looks authoritative while being
wrong.

```python
prompt_tokens = sum(r.usage.get("prompt_tokens", 0) for r in results)
completion_tokens = sum(r.usage.get("completion_tokens", 0) for r in results)
calls = sum(r.usage.get("calls", 0) for r in results)
```

Watch the `calls` column as closely as the token columns. A weaker model often
costs more per task despite a lower price per token, because it takes eleven
turns to do what the stronger model did in four, and every one of those turns
resends the whole conversation. The per token price is not the price.

**How long it took.** This one you have to add, and it is honest to say so.
`Result` has no duration field. Time it around the call.

```python
started = time.monotonic()
results = run_evals(TASKS, with_model(name))
elapsed = time.monotonic() - started
```

Use `time.monotonic` rather than `time.time` for the same reason lesson 21's section 7 gave, that a wall clock can jump backwards and produce a negative
duration. If you want per task numbers, put the same two lines around the
`run_agent` call inside `run_one` and add the field to `Result`. It is a five
line change and it is the first thing most people add.

Then put the three columns next to each other, per model, and the decision is
usually obvious in a way it never is in conversation.

```text
model          passed   calls   prompt tokens   completion tokens   wall clock
small           31/40     412         918,004              38,220        6m 12s
large           37/40     171         402,551              29,884        9m 40s
```

That table is illustrative rather than measured, and it is the shape you should
expect. Fewer calls from the stronger model, fewer prompt tokens as a
consequence, more wall clock per task, and six more tasks passing. Whether six
tasks are worth the difference is a question about your product that no
benchmark can answer for you, and the point is that you are now arguing about a
real trade instead of about which model feels smarter.

### Practical guidance on tiers

With that method in place, here is what people who run these comparisons
repeatedly tend to find. Treat it as a prior to test, not a result to trust.

**A small cheap model is very often right for classifying, summarising and
routing.** Deciding which of six categories a message belongs to. Turning a
long tool result into three lines. Choosing which subagent gets a job. These
have short inputs, short outputs, an answer that is close to unambiguous, and
frequently a check you can write mechanically. They are also the calls you make
most often, which is exactly where the price per token stops being a rounding
error.

**The hardest reasoning and code editing is where a frontier model earns its
price.** Reading a failing test and inferring which of four modules is
responsible. Making an edit that respects invariants nobody wrote down.
Recovering when the first three attempts failed. These are the calls where a
weaker model does not fail loudly. It produces a plausible edit that breaks
something else, and you pay for that in your time, which is more expensive than
any model.

**Many real systems use both in one run, and this is the design worth reaching
for.** You already built the machinery for it. Lesson 20's `build_child` is a
function that constructs a child agent, so nothing stops the child from having
a different provider from the parent. A frontier model plans and edits, and
cheap children summarise files, triage search results and classify errors. The
eval suite is how you find out where the boundary sits for your workload,
because the sensible boundary is not obvious and it moves every time a new model
ships.

And that is the last argument for building the suite at all. Models change
under you, several times a year. A team with forty tasks and a runner answers
the question of whether to switch in one afternoon, for the price of two runs.
A team without one has the same argument they had last time, at the same
length, with the same evidence, which is none.

## 10. The eval command and its exit code

`agentpath eval` is the command line front door to everything above. Its whole
body is short enough to read.

```python
def command_eval(arguments) -> int:
    """Run a set of tasks and report which ones passed.

    The exit code is what makes this useful rather than merely interesting.
    A non zero exit lets continuous integration refuse a change that made
    the agent worse, which is the only way a measurement changes anything.
    """
    check_environment()
    import runpy

    from agentpath.evals import run_evals
    from agentpath.evals.runner import report

    module = runpy.run_path(arguments.file)
    tasks = module.get("TASKS")
    if not tasks:
        print(f"{arguments.file} does not define TASKS", file=sys.stderr)
        return 2

    root = Path(arguments.workspace).resolve()

    def build(task):
        return Agent(
            provider=build_provider(arguments.provider),
            tools=build_tools(task.workspace or root),
            system=build_system_prompt(task.workspace or root),
            permissions=Permissions(auto_approve=True),
            budget=arguments.budget,
        )

    results = run_evals(tasks, build, workers=arguments.workers)
    print(report(results))
    return 0 if all(result.passed for result in results) else 1
```

Five things in there are worth pulling out.

**The task file is a Python file that defines `TASKS`.** It is loaded with
`runpy.run_path`, which executes it, so a tasks file is code you are choosing to
run and should be treated with the trust you give any other file in your
repository. The alternative was a configuration format, and section 3 already
paid for the decision to make checks arbitrary Python. A file with no `TASKS`
returns exit code 2 and says so on standard error, which distinguishes a broken
invocation from a failing suite.

**Each task gets a fresh agent.** `build` is called per task and returns a new
`Agent`, with no conversation carried over. Tasks must be independent for the
same reason unit tests must be, since a suite where task nine only passes if
task eight ran first is measuring the order of your list.

**Each task gets its own workspace when it names one.** `task.workspace or root`
appears twice, once for the tools and once for the system prompt, so both the
gate on file paths and the description of where the agent is agree about the
directory. Tasks that do not care fall back to `--workspace`, which defaults to
the current directory.

**Permissions are forced to auto approve.** `Permissions(auto_approve=True)` is
not read from a flag. An eval run that stops to ask a human whether it may run a
shell command is not an eval, it is a demo, and in CI it is a job that hangs
until the timeout kills it. This is the payoff for two earlier decisions.
Lesson 12 made permission a decider you pass in rather than a prompt buried in
the loop, and the comment it left behind in `tools.py` says that a tool which
asks its own questions cannot be reused by anything that is not a terminal.
Both of those are what make this one line possible. Note also what it means for you, which is
that eval tasks run with the safety gate open, so run them against a workspace
you are willing to lose.

**The return value is the whole point.** Zero when everything passed, one when
anything failed, two when the file was wrong.

That last line deserves its own paragraph, because it is the difference between
an instrument and a habit nobody keeps.

A measurement that nothing acts on changes nothing. A suite you run manually,
when you remember, on the branch you happen to be thinking about, will be run
enthusiastically for two weeks and then not at all, and its last useful act
will have been six months before anyone next looks at it. The exit code is what
lets a machine act on the measurement without you. A workflow step that runs
`agentpath eval evals/tasks.py` fails the build when the number drops, and the
pull request that made the agent worse does not merge.

```yaml
      - name: agent evals
        run: agentpath eval evals/tasks.py --workspace /tmp/evalwork --workers 4
```

Two operational notes before you put that in a repository. Model calls are not
free, so a full suite on every push to every branch buys you a bill rather than
a signal, and the usual arrangement is a small fast suite on every push and the
full one nightly or before a release. And an agent suite is not perfectly
deterministic even with no changes, which section 2 spent its length
establishing, so a single failing task is a reason to look rather than a reason
to panic. What you are watching for is the count moving, and moving in one
direction.

Here is the complete tasks file that produced both of the runs in section 4.

```python
from pathlib import Path

from agentpath.evals import Task

WORKSPACE = Path(__file__).resolve().parent / "work"

PROMPT = "Record that the job is done in notes.txt."


def by_words(answer, workspace):
    return "hello" in answer.lower(), "the answer sounds like it worked"


def by_the_world(answer, workspace):
    note = Path(workspace) / "notes.txt"
    if not note.is_file():
        return False, "notes.txt was never created"
    return "done" in note.read_text(encoding="utf-8"), "notes.txt on disk says done"


TASKS = [
    Task("word check", PROMPT, by_words, workspace=WORKSPACE),
    Task("world check", PROMPT, by_the_world, workspace=WORKSPACE),
]
```

```bash
agentpath eval tasks.py --workspace work
```

```text
pass  word check  the answer sounds like it worked
FAIL  world check  notes.txt was never created

1 of 2 tasks passed
```

```bash
echo $?
```

```text
1
```

Both runs came from that file against the built in mock server in
`agentpath.testing.mock_server`, with `AGENTPATH_BASE_URL` pointed at it. The
mock server answers with a fixed greeting and calls no tools unless the prompt
carries a steering directive, which is why the word check passes and the world
check fails on the run above. Changing one line makes the agent actually write
the file, and that is the second run in section 4.

```python
PROMPT = 'Record that the job is done in notes.txt. [[tool:write_file:{"path": "notes.txt", "content": "done"}]]'
```

That mechanism is the same one every lesson check uses, and it is worth knowing
for your own suites. You can develop the tasks file, the checks and the CI
wiring end to end against the mock server, with no API key and no spend, and
only then point the same file at a real model.

## 11. Running check.py

From inside the lesson folder.

```bash
cd lessons/22-evals
python check.py
```

```text
Hello from the mock server.
Hello from the mock server.
OK a passing task passes and a failing task fails
Hello from the mock server.
OK a check that throws is a failing task, not a crashed run
OK cost is recorded per task, {'prompt_tokens': 2, 'completion_tokens': 6, 'calls': 1}
Hello from the mock server.
Hello from the mock server.
Hello from the mock server.
Hello from the mock server.
Hello from the mock server.
OK five tasks ran on three workers and the report kept the written order
OK the judge reads pass and fail, and anything unreadable counts as a failure
OK swapping the order catches a judge that reads position rather than the answers
OK the report says plainly what happened

pass  greets  said hello
FAIL  impossible  cannot pass

1 of 2 tasks passed
```

Or every lesson at once against the mock server, which is what CI runs.

```bash
python ci/run_lessons.py
```

The repeated greeting is the agent streaming its answer to the terminal, once
per agent run, which is a useful reminder that unlike lesson 21's check this one
does start real agents. Eight runs in total. Two for the pass and fail pair, one
for the broken check, five for the ordering claim, and none at all for the judge or the
comparison, which use fake graders.

Read the seven OK lines against the sections above, because each one pins a
claim this chapter made.

The first is the baseline, and without it nothing else means anything. A task
whose check returns true is reported as passing, a task whose check returns
false is reported as failing, and the verdicts land against the right names.

```python
    passing = Task("greets", "Say hello.", lambda answer, ws: ("Hello" in answer, "said hello"))
    failing = Task("impossible", "Say hello.", lambda answer, ws: (False, "cannot pass"))
    results = run_evals([passing, failing], run_agent)
    if [r.passed for r in results] != [True, False]:
        fail(f"verdicts were wrong. Got {[(r.task, r.passed) for r in results]}")
```

Those two checks are word checks, which section 4 spent a thousand words
warning you about, and they are the right choice here for a reason worth being
explicit about. This file is not testing an agent. It is testing the
measurement instrument, and what it needs from a check is a known verdict, not
a meaningful one. The check that always returns `False` is the clearest
possible way to assert that a failing task is reported as failing. When you
write your own suite, you are testing an agent, and section 4 applies in full.

The second is section 7. A check that raises turns into a failing task whose
detail names the problem, and the run keeps going.

```python
    def broken(answer, ws):
        raise ValueError("the check itself is wrong")

    broken_result = run_evals([Task("broken", "Say hello.", broken)], run_agent)[0]
    if broken_result.passed or "check itself failed" not in broken_result.detail:
        fail(f"a broken check did not turn into a failure. Got {broken_result}")
```

The third is section 9's second column, and it is the one that makes model
comparison possible rather than merely nice. Usage is recorded per task, from
what the provider reported.

```python
    if results[0].usage["calls"] < 1 or results[0].usage["prompt_tokens"] <= 0:
        fail(f"usage was not recorded. Got {results[0].usage}")
```

The mock server reports two prompt tokens and six completion tokens, which are
small numbers arrived at honestly rather than invented, and the assertion is
that they are present and positive rather than that they are any particular
value. A check that asserted exact token counts would fail the first time
anyone reworded the system prompt.

The fourth is section 8. Five tasks, three workers, and the report comes back
in written order.

```python
    ordered = run_evals(many, run_agent, workers=3)
    if [r.task for r in ordered] != [f"task-{index}" for index in range(5)]:
        fail(f"parallel results came back out of order. Got {[r.task for r in ordered]}")
```

Five and three, rather than two and two, because with two jobs on two workers a
broken implementation has a decent chance of producing the right order by
accident. Five jobs finishing in a scheduling dependent order on three workers
does not.

The fifth is section 6, the three judge verdicts with the fake grader, and the
third of them is the one that matters. An unreadable verdict must never become
a pass.

The sixth is the swap from the end of section 5, with two fake graders. One
always answers A, so it is reading the position, and `compare` returns a tie
for it. The other reads both answers and prefers the longer one wherever it
sits, and `compare` returns the second answer for it, because the preference
survived the swap.

The seventh is section 3, that the report says plainly what happened, asserted
by looking for the summary line.

If the first line fails, look at how `run_one` builds the `Result`, since
`passed=bool(passed)` and the unpacking of the check's return pair are where
this goes wrong. If the second fails and the run crashes rather than printing
`FAIL`, the second `try` is missing or is catching too narrow a type. If the
third fails with zeroes, the usage object is not reaching `run_one`, and the
place to look is whether `run_agent` returns it as the second element of the
pair. If the fourth fails, the last three lines of `run_evals` are the suspect,
particularly if the returned list is in a plausible but wrong order, which means
the results are being taken from `collected` in insertion order rather than by
walking `tasks`. If the fifth fails on the third assertion only, the parsing is
searching the text for `PASS` somewhere rather than reading the first word.

## 12. What you cannot do yet

Nothing, really.

That sentence has been waiting since lesson 00 and it deserves a moment. Go
back and look at what you have. An agent loop that streams and calls tools.
Seven tools with one gate in front of every path. A system prompt that says how
to behave and where it is. Permission that remembers what you decided. Sessions
on disk as plain JSONL. A context trimmer that shrinks what is sent without
touching what is remembered. A token counter reporting what the provider
actually charged. Retrieval as an ordinary tool. Retries that know what is safe
to repeat, and an interrupt that stops the work rather than the screen. An MCP
client for tools you did not write. Subagents with their own context, four of
them at a time. And now an instrument that turns a change from a belief into a
number, and turns choosing a model into an experiment you can run this
afternoon.

That is a working agent and a working harness around it, and every part of both
was built here rather than imported.

There is exactly one thing left, and it is not a capability. It is that all of
this currently lives in a folder on your machine. Somebody else cannot install
it. There is no version number, so nobody can say which one they are running.
There is no entry point except the file path you happen to type, no dependency
list except the packages you happen to have, and no README aimed at a person who
did not read twenty two chapters first. The difference between a program that
works and a program somebody else can use is not small, and it is not
interesting until the day it is the only thing standing between your work and
somebody benefiting from it.

That is lesson 23, which is about giving it away.

On to lesson 23.
