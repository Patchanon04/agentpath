"""Measuring whether the agent actually works.

Everything before this chapter was built on the assumption that you can tell
a good change from a bad one by looking at it. You cannot. A wording change
in a system prompt can fix one task and quietly break three others, and the
only way to know is to run a set of tasks before and after.

Two kinds of check exist here and the split matters. A mechanical check is a
function that looks at the world and returns true or false. It is free,
instant, and it has no opinions. A judge asks a model whether an answer is
acceptable, which costs money, takes time, and can be wrong. Use a judge only
for the things a function genuinely cannot decide, such as whether an
explanation is clear.
"""
from dataclasses import dataclass, field

from agentpath.fanout import run_in_parallel
from agentpath.types import TurnDone


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


@dataclass
class Result:
    task: str
    passed: bool
    detail: str
    usage: dict = field(default_factory=dict)
    answer: str = ""


def run_one(task: Task, build_agent) -> Result:
    """Run one task and turn whatever happened into a verdict.

    Building the agent is inside the try because it can fail on its own,
    for a bad workspace or a server that will not start, and one task
    that cannot even begin must not take the whole report with it.
    """
    agent = None
    answer = ""
    try:
        agent = build_agent(task)
        for event in agent.run(task.prompt):
            if isinstance(event, TurnDone):
                answer = event.message.content
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

    usage = getattr(agent, "usage", None)
    return Result(
        task=task.name,
        passed=bool(passed),
        detail=str(detail),
        usage={
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "calls": getattr(usage, "calls", 0),
        },
        answer=answer,
    )


def run_evals(tasks, build_agent, workers=1) -> list[Result]:
    """Run every task and return one result per task, in the order given."""
    tasks = list(tasks)
    if workers <= 1:
        return [run_one(task, build_agent) for task in tasks]

    def make(task):
        def produce():
            yield run_one(task, build_agent)

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
    """Ask a model whether an answer meets a written standard.

    The verdict is read from the first word rather than parsed out of a
    sentence, because a grader that sometimes cannot be read is worse than
    no grader. Anything that is not clearly a pass counts as a failure, so
    an unreadable verdict never silently becomes a green tick.
    """
    from agentpath.types import Message

    request = JUDGE_PROMPT.format(criteria=criteria, question=question, answer=answer)
    verdict = ""
    for event in provider.stream([Message(role="user", content=request)]):
        if isinstance(event, TurnDone):
            verdict = event.message.content.strip()
    first = verdict.split()[0].upper().strip(".,") if verdict.split() else ""
    return first == "PASS", verdict


def report(results) -> str:
    """A plain table, because a report nobody reads changes nothing."""
    lines = []
    for result in results:
        mark = "pass" if result.passed else "FAIL"
        lines.append(f"{mark}  {result.task}  {result.detail}")
    passed = sum(1 for result in results if result.passed)
    lines.append(f"\n{passed} of {len(results)} tasks passed")
    return "\n".join(lines)
