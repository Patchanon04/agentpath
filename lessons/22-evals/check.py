"""Check that lesson 22 works.

Six things must be true. A passing task is reported as passing and a
failing one as failing. A check that itself throws counts as a failure
rather than crashing the run, because a report you never get is worse than
a red line. Usage is recorded per task so you can compare cost as well as
correctness. Results come back in the order the tasks were written even when
they ran in parallel. A judge that cannot be read counts as a failure, so an
unreadable verdict never turns into a green tick. And the report says in one
line how many tasks passed, because a measurement nobody reads changes
nothing.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson22-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402
from agent import run  # noqa: E402
from evals import Task, judge, report, run_evals  # noqa: E402
from permissions import Permissions  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402
from usage import Usage  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def provider():
    return OpenAICompatProvider(
        os.environ["AGENTPATH_BASE_URL"],
        os.environ.get("AGENTPATH_API_KEY", ""),
        os.environ["AGENTPATH_MODEL"],
    )


def run_agent(task):
    usage = Usage()
    answer, _ = run(
        provider(),
        task.prompt,
        permissions=Permissions(auto_approve=True),
        usage=usage,
    )
    return answer, usage


def main():
    passing = Task("greets", "Say hello.", lambda answer, ws: ("Hello" in answer, "said hello"))
    failing = Task("impossible", "Say hello.", lambda answer, ws: (False, "cannot pass"))
    results = run_evals([passing, failing], run_agent)
    if [r.passed for r in results] != [True, False]:
        fail(f"verdicts were wrong. Got {[(r.task, r.passed) for r in results]}")
    print("OK a passing task passes and a failing task fails")

    def broken(answer, ws):
        raise ValueError("the check itself is wrong")

    broken_result = run_evals([Task("broken", "Say hello.", broken)], run_agent)[0]
    if broken_result.passed or "check itself failed" not in broken_result.detail:
        fail(f"a broken check did not turn into a failure. Got {broken_result}")
    print("OK a check that throws is a failing task, not a crashed run")

    if results[0].usage["calls"] < 1 or results[0].usage["prompt_tokens"] <= 0:
        fail(f"usage was not recorded. Got {results[0].usage}")
    print(f"OK cost is recorded per task, {results[0].usage}")

    many = [
        Task(f"task-{index}", "Say hello.", lambda answer, ws: (True, "ok"))
        for index in range(5)
    ]
    ordered = run_evals(many, run_agent, workers=3)
    if [r.task for r in ordered] != [f"task-{index}" for index in range(5)]:
        fail(f"parallel results came back out of order. Got {[r.task for r in ordered]}")
    print("OK five tasks ran on three workers and the report kept the written order")

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
    print("OK the judge reads pass and fail, and anything unreadable counts as a failure")

    text = report(results)
    if "1 of 2 tasks passed" not in text:
        fail(f"the report is not readable. Got\n{text}")
    print("OK the report says plainly what happened")
    print()
    print(text)


if __name__ == "__main__":
    main()
