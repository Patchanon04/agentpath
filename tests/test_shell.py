import sys

from agentpath.tools.base import ToolRegistry
from agentpath.tools.shell import always_allow, never_allow, shell_tools
from agentpath.types import ToolCall


def run(root, command, confirm=always_allow, timeout=60):
    registry = ToolRegistry(shell_tools(root, confirm=confirm, timeout=timeout))
    return registry.run(ToolCall(id="1", name="run_shell", arguments={"command": command})).content


def test_command_output_comes_back(tmp_path):
    assert "hello" in run(tmp_path, f'"{sys.executable}" -c "print(\'hello\')"')


def test_exit_code_is_reported(tmp_path):
    result = run(tmp_path, f'"{sys.executable}" -c "import sys; sys.exit(3)"')
    assert "exit code 3" in result


def test_stderr_is_included(tmp_path):
    result = run(tmp_path, f'"{sys.executable}" -c "import sys; sys.stderr.write(\'bad\')"')
    assert "bad" in result


def test_a_refused_command_does_not_run(tmp_path):
    marker = (tmp_path / "created.txt").as_posix()
    command = f"\"{sys.executable}\" -c \"open(r'{marker}', 'w').write('x')\""
    result = run(tmp_path, command, confirm=never_allow)
    assert "refused" in result
    assert not (tmp_path / "created.txt").exists()


def test_the_command_runs_inside_the_workspace(tmp_path):
    (tmp_path / "marker.txt").write_text("here", encoding="utf-8")
    listing = run(tmp_path, f'"{sys.executable}" -c "import os; print(os.listdir(\'.\'))"')
    assert "marker.txt" in listing


def test_timeout_is_reported_not_raised(tmp_path):
    command = f'"{sys.executable}" -c "import time; time.sleep(5)"'
    assert "timed out" in run(tmp_path, command, timeout=1)


def test_long_output_is_truncated(tmp_path):
    assert "truncated" in run(tmp_path, f"\"{sys.executable}\" -c \"print('x' * 9000)\"")


def test_a_cancelled_run_does_not_start_the_command(tmp_path):
    """An interrupt has to stop real work, not only the display."""
    from agentpath.cancel import Cancellation

    cancellation = Cancellation()
    cancellation.cancel()
    marker = (tmp_path / "started.txt").as_posix()
    command = f"\"{sys.executable}\" -c \"open(r'{marker}', 'w').write('x')\""
    tools = shell_tools(tmp_path, confirm=always_allow, cancellation=cancellation)
    call = ToolCall(id="1", name="run_shell", arguments={"command": command})
    result = ToolRegistry(tools).run(call).content
    assert "Cancelled" in result
    assert not (tmp_path / "started.txt").exists()


def test_a_timeout_really_kills_the_command(tmp_path):
    """The message was always right. The killing was not.

    With shell=True the thing started is a shell and the slow command is its
    child, so killing only the shell left the child running and holding the
    pipes, and the call waited for the whole run anyway.
    """
    import time

    marker = (tmp_path / "finished.txt").as_posix()
    command = (
        f'"{sys.executable}" -c "import time; time.sleep(5); '
        f"open(r'{marker}','w').write('x')" + '"'
    )
    started = time.monotonic()
    result = run(tmp_path, command, timeout=1)
    elapsed = time.monotonic() - started

    assert "timed out" in result
    assert elapsed < 3.0, f"the call waited {elapsed:.1f}s for a 1 second timeout"
    time.sleep(6)
    assert not (tmp_path / "finished.txt").exists(), "the command survived its own timeout"
