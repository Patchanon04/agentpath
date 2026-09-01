"""Run the command line as a real process, the way a person runs it.

Every other test in this suite imports a piece and calls it. That is useful,
and it is also how four bugs shipped. A run started with --yes refused every
command it had just approved. One interrupt disabled the shell for the rest
of a session. Running out of turns printed a traceback. Resuming added a
second system prompt every time. All four lived in the wiring between the
pieces, which is exactly the part a unit test does not touch.

So these tests start the command as a subprocess, point it at a fake model
server, and then look at what is on disk and what was printed. Nothing is
mocked except the model itself.
"""
import json
import os
import subprocess
import sys

import pytest

from agentpath.testing.mock_server import serve

PYTHON = sys.executable


@pytest.fixture(scope="module")
def server():
    base_url, shutdown = serve()
    yield base_url
    shutdown()


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    return root


def run_cli(server, workspace, home, *arguments, stdin="", timeout=90):
    """Run agentpath as a separate process and return the finished result."""
    environment = dict(os.environ)
    environment.update(
        {
            "AGENTPATH_BASE_URL": f"{server}/v1",
            "AGENTPATH_MODEL": "mock",
            "AGENTPATH_API_KEY": "",
            "AGENTPATH_HOME": str(home),
        }
    )
    environment.pop("AGENTPATH_AUTO_APPROVE", None)
    return subprocess.run(
        [PYTHON, "-m", "agentpath.cli", *arguments],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=environment,
        cwd=str(workspace),
    )


def shell_task(marker):
    """A directive asking the agent to run a command that creates a file.

    The arguments are built with json.dumps rather than by hand. A Windows
    interpreter path is full of backslashes, and every one of them has to
    be escaped to survive the trip through JSON. Writing that out by hand
    produces a directive the server cannot parse, and the test then passes
    for the wrong reason because the file was never created either way.
    """
    inner = "open(r'" + marker + "','w').write('x')"
    arguments = {"command": f'"{PYTHON}" -c "{inner}"'}
    return "Run it. [[tool:run_shell:" + json.dumps(arguments) + "]]"


FIX_THE_BUG = (
    "Fix it. "
    '[[tool:read_file:{"path": "calc.py"}]]'
    '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]'
)


def test_run_does_the_job_and_says_where_it_went(server, workspace, tmp_path):
    result = run_cli(server, workspace, tmp_path / "home", "run", FIX_THE_BUG, "--yes")

    assert result.returncode == 0, result.stderr
    assert "return a + b" in (workspace / "calc.py").read_text(encoding="utf-8")
    assert "session " in result.stdout
    assert "usage " in result.stdout
    assert "Traceback" not in result.stderr


def test_the_session_file_holds_the_whole_conversation(server, workspace, tmp_path):
    home = tmp_path / "home"
    run_cli(server, workspace, home, "run", FIX_THE_BUG, "--session", "demo", "--yes")

    path = home / "sessions" / "demo.jsonl"
    assert path.exists()
    messages = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert messages[0]["role"] == "system"
    assert "tool" in [m["role"] for m in messages]

    requested = {c["id"] for m in messages for c in m.get("tool_calls") or []}
    answered = {m["tool_call_id"] for m in messages if m["role"] == "tool"}
    assert requested == answered, "a real run left a tool call with no result"


def test_yes_really_approves_a_shell_command(server, workspace, tmp_path):
    """The bug this catches shipped. --yes approved, then the tool refused."""
    marker = (workspace / "made-by-shell.txt").as_posix()
    result = run_cli(server, workspace, tmp_path / "home", "run", shell_task(marker), "--yes")

    assert result.returncode == 0, result.stderr
    assert (workspace / "made-by-shell.txt").exists(), result.stdout
    assert "refused" not in result.stdout


def test_with_nobody_watching_and_no_yes_the_command_is_refused(server, workspace, tmp_path):
    """Silence must not mean yes. There is no keyboard attached here."""
    marker = (workspace / "should-not-exist.txt").as_posix()
    result = run_cli(server, workspace, tmp_path / "home", "run", shell_task(marker))

    assert result.returncode == 0, result.stderr
    assert not (workspace / "should-not-exist.txt").exists()


def test_chat_reads_from_the_keyboard_and_saves_on_the_way_out(server, workspace, tmp_path):
    home = tmp_path / "home"
    result = run_cli(
        server, workspace, home, "chat", "--session", "talk", "--yes", stdin="hello\n"
    )

    assert result.returncode == 0, result.stderr
    assert "Type a message" in result.stdout
    assert "Hello from the mock server." in result.stdout
    assert "hello" in (home / "sessions" / "talk.jsonl").read_text(encoding="utf-8")


def test_resume_carries_the_conversation_and_adds_no_second_prompt(server, workspace, tmp_path):
    home = tmp_path / "home"
    run_cli(server, workspace, home, "run", "First question.", "--session", "keep", "--yes")
    before = (home / "sessions" / "keep.jsonl").read_text(encoding="utf-8").splitlines()

    result = run_cli(
        server, workspace, home, "resume", "Second question.", "--session", "keep", "--yes"
    )
    after = (home / "sessions" / "keep.jsonl").read_text(encoding="utf-8").splitlines()

    assert result.returncode == 0, result.stderr
    assert f"Resumed keep with {len(before)} messages" in result.stdout
    assert len(after) > len(before)
    systems = sum(1 for line in after if json.loads(line)["role"] == "system")
    assert systems == 1, "resuming added another system prompt"


def test_resume_with_no_name_lists_what_is_there(server, workspace, tmp_path):
    home = tmp_path / "home"
    run_cli(server, workspace, home, "run", "hello", "--session", "alpha", "--yes")
    result = run_cli(server, workspace, home, "resume")

    assert result.returncode == 0
    assert "alpha" in result.stdout


def test_running_out_of_turns_is_an_outcome_not_a_traceback(server, workspace, tmp_path):
    """A stuck run still has to report the session name and what it cost."""
    task = "Go. " + '[[tool:read_file:{"path": "calc.py"}]]' * 12
    result = run_cli(server, workspace, tmp_path / "home", "run", task, "--yes")

    assert "Traceback" not in result.stderr, result.stderr
    assert "session " in result.stdout
    assert "usage " in result.stdout


def test_missing_configuration_exits_two_and_says_what_is_missing(workspace):
    environment = dict(os.environ)
    for name in ["AGENTPATH_BASE_URL", "AGENTPATH_MODEL"]:
        environment.pop(name, None)
    result = subprocess.run(
        [PYTHON, "-m", "agentpath.cli", "run", "hello"],
        capture_output=True,
        text=True,
        timeout=60,
        env=environment,
        cwd=str(workspace),
    )
    assert result.returncode == 2
    assert "AGENTPATH_BASE_URL" in result.stderr


def test_the_workspace_flag_confines_the_agent(server, workspace, tmp_path):
    """The gate has to hold when the path arrives through argparse."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("LEAKEDVALUE\n", encoding="utf-8")

    task = 'Read it. [[tool:read_file:{"path": "../outside/secret.txt"}]]'
    result = run_cli(
        server, workspace, tmp_path / "home", "run", task, "--workspace", str(workspace), "--yes"
    )

    assert "LEAKEDVALUE" not in result.stdout
    assert "outside the workspace" in result.stdout


def test_verbose_reports_what_the_tools_cost_before_anything_runs(server, workspace, tmp_path):
    result = run_cli(server, workspace, tmp_path / "home", "run", "hello", "--yes", "--verbose")
    assert "tool schemas cost" in result.stdout


def test_an_mcp_server_can_be_connected_from_the_command_line(server, workspace, tmp_path):
    task = 'Echo. [[tool:agentpath-mock.echo:{"text": "across a pipe"}]]'
    result = run_cli(
        server,
        workspace,
        tmp_path / "home",
        "run",
        task,
        "--yes",
        "--mcp",
        f'"{PYTHON}" -m agentpath.testing.mock_mcp_server',
    )

    assert result.returncode == 0, result.stderr
    assert "across a pipe" in result.stdout


def test_eval_passes_and_fails_with_the_right_exit_code(server, workspace, tmp_path):
    tasks = workspace / "tasks.py"
    tasks.write_text(
        "from agentpath.evals import Task\n"
        "TASKS = [\n"
        "    Task('greets', 'Say hello.', lambda answer, ws: ('Hello' in answer, 'said it')),\n"
        "]\n",
        encoding="utf-8",
    )
    passing = run_cli(server, workspace, tmp_path / "home", "eval", str(tasks))
    assert passing.returncode == 0, passing.stdout
    assert "1 of 1 tasks passed" in passing.stdout

    tasks.write_text(
        "from agentpath.evals import Task\n"
        "TASKS = [Task('never', 'Say hello.', lambda answer, ws: (False, 'no'))]\n",
        encoding="utf-8",
    )
    failing = run_cli(server, workspace, tmp_path / "home", "eval", str(tasks))
    assert failing.returncode == 1
    assert "0 of 1 tasks passed" in failing.stdout


def test_several_tool_calls_in_one_message_all_get_answered(server, workspace, tmp_path):
    """A real model asks for several independent calls at once.

    Until the mock could do this, the loop over assistant.tool_calls was
    never exercised with more than one item end to end, so every path that
    only appears when a turn is abandoned part way through was unreachable.
    """
    home = tmp_path / "home"
    task = "Look at it. " + '[[tools:read_file:{"path": "calc.py"}]]' * 3
    result = run_cli(server, workspace, home, "run", task, "--session", "many", "--yes")

    assert result.returncode == 0, result.stderr
    messages = [
        json.loads(line)
        for line in (home / "sessions" / "many.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    requested = {c["id"] for m in messages for c in m.get("tool_calls") or []}
    answered = {m["tool_call_id"] for m in messages if m["role"] == "tool"}
    assert len(requested) == 3
    assert requested == answered


def test_a_turn_abandoned_part_way_still_answers_every_call(server, workspace, tmp_path):
    """The orphan bug, reached the way it happens in life.

    Five identical calls in one message trip the loop detector part way
    through, so the run stops with calls still unanswered. An assistant
    message carrying five tool calls followed by three results is rejected
    outright on the next request.
    """
    home = tmp_path / "home"
    task = "Go. " + '[[tools:read_file:{"path": "calc.py"}]]' * 5
    result = run_cli(server, workspace, home, "run", task, "--session", "stopped", "--yes")

    assert "Traceback" not in result.stderr, result.stderr
    messages = [
        json.loads(line)
        for line in (home / "sessions" / "stopped.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    requested = {c["id"] for m in messages for c in m.get("tool_calls") or []}
    answered = {m["tool_call_id"] for m in messages if m["role"] == "tool"}
    assert len(requested) == 5
    assert requested == answered, f"orphaned tool calls {sorted(requested - answered)}"


def test_a_run_that_never_finishes_reports_instead_of_crashing(server, workspace, tmp_path):
    """Reaching the turn limit is an outcome, and the person still wants the receipt.

    Each read has to return something different, otherwise the no progress
    check stops the run first and the turn limit is never reached. That is
    the newer guard doing its job, but it is not the path under test here.
    """
    home = tmp_path / 'home'
    for index in range(14):
        (workspace / f'note{index}.txt').write_text(
            f'this is note number {index}', encoding='utf-8'
        )
    task = 'Read them all. ' + ''.join(
        "[[tool:read_file:" + json.dumps({"path": f"note{index}.txt"}) + "]]"
        for index in range(14)
    )
    result = run_cli(server, workspace, home, 'run', task, '--session', 'endless', '--yes')

    assert 'Traceback' not in result.stderr, result.stderr
    assert 'max turns' in result.stdout, result.stdout
    assert 'session endless saved' in result.stdout
    assert 'usage ' in result.stdout
