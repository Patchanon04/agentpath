from agentpath.agent import Agent
from agentpath.evals import Result, Task, judge, run_evals
from agentpath.evals.runner import report
from agentpath.permissions import Permissions
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.tools.base import ToolRegistry
from agentpath.tools.files import file_tools


def build_provider(mock_url):
    return OpenAICompatProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")


def builder(mock_url, workspace=None):
    def build(task):
        tools = ToolRegistry(file_tools(workspace)) if workspace else ToolRegistry()
        return Agent(
            provider=build_provider(mock_url),
            tools=tools,
            permissions=Permissions(auto_approve=True),
        )

    return build


def test_a_passing_task_is_reported_as_passing(mock_url):
    tasks = [Task("greets", "Say hello.", lambda answer, workspace: ("Hello" in answer, "found"))]
    results = run_evals(tasks, builder(mock_url))
    assert results[0].passed is True
    assert results[0].task == "greets"


def test_a_failing_task_is_reported_as_failing(mock_url):
    tasks = [Task("impossible", "Say hello.", lambda answer, workspace: (False, "never passes"))]
    results = run_evals(tasks, builder(mock_url))
    assert results[0].passed is False
    assert results[0].detail == "never passes"


def test_a_check_that_throws_is_a_failure_not_a_crashed_run(mock_url):
    def broken(answer, workspace):
        raise ValueError("the check is wrong")

    results = run_evals([Task("broken", "Say hello.", broken)], builder(mock_url))
    assert results[0].passed is False
    assert "the check itself failed" in results[0].detail


def test_usage_is_recorded_for_every_task(mock_url):
    tasks = [Task("greets", "Say hello.", lambda answer, workspace: (True, "ok"))]
    results = run_evals(tasks, builder(mock_url))
    assert results[0].usage["calls"] >= 1
    assert results[0].usage["prompt_tokens"] > 0


def test_a_task_can_check_the_world_rather_than_the_words(mock_url, tmp_path):
    """The strongest checks look at what changed, not at what was said."""
    prompt = 'Write it. [[tool:write_file:{"path": "proof.txt", "content": "done"}]]'

    def file_exists(answer, workspace):
        target = workspace / "proof.txt"
        return target.exists(), f"proof.txt {'exists' if target.exists() else 'is missing'}"

    tasks = [Task("writes a file", prompt, file_exists, workspace=tmp_path)]
    results = run_evals(tasks, builder(mock_url, tmp_path))
    assert results[0].passed is True


def test_results_come_back_in_the_order_the_tasks_were_given(mock_url):
    tasks = [
        Task(f"task-{index}", "Say hello.", lambda answer, workspace: (True, "ok"))
        for index in range(5)
    ]
    results = run_evals(tasks, builder(mock_url), workers=3)
    assert [result.task for result in results] == [f"task-{index}" for index in range(5)]


def test_running_in_parallel_gives_the_same_verdicts(mock_url):
    tasks = [
        Task("a", "Say hello.", lambda answer, workspace: (True, "ok")),
        Task("b", "Say hello.", lambda answer, workspace: (False, "no")),
    ]
    serial = run_evals(tasks, builder(mock_url), workers=1)
    parallel = run_evals(tasks, builder(mock_url), workers=2)
    assert [r.passed for r in serial] == [r.passed for r in parallel]


def test_the_judge_reads_a_pass(mock_url, monkeypatch):
    from agentpath.types import Message, TurnDone

    class Grader:
        def __init__(self, verdict):
            self.verdict = verdict

        def stream(self, messages, tools=None):
            yield TurnDone(message=Message(role="assistant", content=self.verdict))

    passed, text = judge(Grader("PASS the answer is correct"), "q", "a", "must be correct")
    assert passed is True
    assert "correct" in text

    failed, _ = judge(Grader("FAIL it is wrong"), "q", "a", "must be correct")
    assert failed is False


def test_an_unreadable_verdict_counts_as_a_failure():
    """A grader that cannot be read must never quietly become a green tick."""
    from agentpath.types import Message, TurnDone

    class Rambling:
        def stream(self, messages, tools=None):
            yield TurnDone(message=Message(role="assistant", content="Well, it depends really"))

    passed, _ = judge(Rambling(), "q", "a", "must be correct")
    assert passed is False


def test_the_report_is_readable():
    results = [Result("a", True, "fine"), Result("b", False, "broken")]
    text = report(results)
    assert "pass  a" in text
    assert "FAIL  b" in text
    assert "1 of 2 tasks passed" in text


def test_two_tasks_with_the_same_name_do_not_merge(mock_url):
    """Keying results by name turned one task's verdict into the other's."""
    tasks = [
        Task("same", "Say hello.", lambda answer, workspace: (True, "first")),
        Task("same", "Say hello.", lambda answer, workspace: (False, "second")),
    ]
    serial = [(r.passed, r.detail) for r in run_evals(tasks, builder(mock_url), workers=1)]
    parallel = [(r.passed, r.detail) for r in run_evals(tasks, builder(mock_url), workers=2)]
    assert serial == [(True, "first"), (False, "second")]
    assert parallel == serial

def test_a_task_whose_agent_cannot_be_built_is_one_failure(mock_url):
    """Building the agent sat outside the try, so one bad task lost the report."""

    def build(task):
        if task.name == "broken":
            raise RuntimeError("could not connect to the server")
        return builder(mock_url)(task)

    results = run_evals(
        [
            Task("fine", "Say hello.", lambda answer, workspace: (True, "ok")),
            Task("broken", "Say hello.", lambda answer, workspace: (True, "ok")),
        ],
        build,
    )
    assert [r.passed for r in results] == [True, False]
    assert "could not connect" in results[1].detail
