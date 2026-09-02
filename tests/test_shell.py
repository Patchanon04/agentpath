import sys

import pytest

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
        f'"{sys.executable}" -c "import time; time.sleep(8); '
        f"open(r'{marker}','w').write('x')" + '"'
    )
    started = time.monotonic()
    result = run(tmp_path, command, timeout=1)
    elapsed = time.monotonic() - started

    assert "timed out" in result
    # Killing the tree measures at three and a bit seconds on Windows,
    # because taskkill is itself a process that has to start. The budget
    # used to be three, which passed by luck and failed on a loaded
    # machine. Six sits above the real cost and below the eight the call
    # would take if the kill did not work at all.
    assert elapsed < 6.0, f"the call waited {elapsed:.1f}s for a 1 second timeout"
    time.sleep(9)
    assert not (tmp_path / "finished.txt").exists(), "the command survived its own timeout"


def test_output_that_is_utf_8_is_read_as_utf_8(tmp_path):
    """The child writes bytes directly rather than printing.

    print goes through the encoding of the child's own stdout, which on a
    Windows machine with no console is often not utf-8 at all. The child
    then dies encoding its own message and the test measures that instead
    of measuring what we decode. Writing bytes takes the child's opinion
    out of the question.
    """
    thai = "สวัสดี"
    command = (
        f'"{sys.executable}" -c "import sys; '
        "sys.stdout.buffer.write(bytes([224,184,170,224,184,167,224,184,177,"
        "224,184,170,224,184,148,224,184,181]))\""
    )
    assert thai in run(tmp_path, command)


@pytest.mark.skipif(sys.platform != "win32", reason="only Windows has an OEM codepage")
def test_output_in_the_old_windows_codepage_is_still_read(tmp_path):
    """Two encodings turn up on the same Windows machine and both must work.

    A modern tool writes utf-8. Most of the programs that ship with the
    system write the old console codepage. Decoding the second as the
    first turns every accented character into a replacement mark, and
    errors equals replace means nothing complains about it.

    Only Windows has that second encoding, so this is the one assertion
    in the file that is about one operating system rather than about the
    behaviour we want everywhere.
    """
    command = (
        f'"{sys.executable}" -c "import sys; '
        "sys.stdout.buffer.write(bytes([99,97,102,130,32,114,130,115,117,109,130]))\""
    )
    assert "café résumé" in run(tmp_path, command)


def test_the_agent_can_see_a_file_name_it_cannot_spell(tmp_path):
    """Listing a directory used to lose every non Latin name to question marks.

    The console codepage cannot write those characters at all, so the shell
    destroyed them before we saw the bytes. Decoding cannot recover what was
    never encoded, which is why the shell is asked to speak utf-8 first.
    """
    (tmp_path / "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35.txt").write_text("hi", encoding="utf-8")
    (tmp_path / "plain.txt").write_text("hi", encoding="utf-8")

    listing = run(tmp_path, "dir /b" if sys.platform == "win32" else "ls -1")
    assert "plain.txt" in listing
    assert "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35.txt" in listing, listing
