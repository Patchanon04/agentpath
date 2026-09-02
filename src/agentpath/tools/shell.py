"""A tool that runs shell commands, with a question asked first.

The question is the whole point. A model can be talked into running
something destructive by text it read from a file, so the last gate before
anything runs is a human. In part 3 this grows into a real permission
system. Here it is deliberately one function, so you can see that the idea
is small even though it matters a lot.
"""
import os
import signal
import subprocess
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import truncate

DEFAULT_TIMEOUT = 60


def _output_encodings():
    """The encodings to try on command output, in order.

    Assuming utf-8 is wrong on Windows. A command that writes utf-8, which
    most modern tools do, and a command that writes the old console
    codepage, which most of the ones that ship with the system do, both
    turn up on the same machine. Decoding the second as the first turns
    every accented or non Latin character into a replacement mark, and
    errors equals replace means it happens silently.

    utf-8 goes first because it fails loudly on the wrong input. A single
    byte encoding never fails, so trying one first would decode utf-8 text
    into nonsense without complaining.
    """
    encodings = ["utf-8"]
    if os.name == "nt":
        import ctypes

        for codepage in (
            ctypes.windll.kernel32.GetOEMCP(),
            ctypes.windll.kernel32.GetACP(),
        ):
            name = f"cp{codepage}"
            if name not in encodings:
                encodings.append(name)
    return encodings


def decode_output(raw):
    """Turn the bytes a command produced into text."""
    for encoding in _output_encodings():
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


_CONSOLE_READY = False


def _use_utf8_console():
    """Put this process's console into utf-8, once.

    The chcp inside the command is not enough on its own. A shell builtin
    such as dir reads the codepage when the shell starts, which happens
    before the chcp in the same command line runs, so the first command of a
    session still lost non ASCII names while every later one was fine. That
    is a maddening thing to debug and the fix is to set it here instead,
    before any shell exists.

    This does change the codepage of the terminal the person is sitting in.
    It is a display setting, it is what any modern tool wants anyway, and the
    alternative is output that is quietly wrong.
    """
    global _CONSOLE_READY
    if _CONSOLE_READY or os.name != "nt":
        return
    _CONSOLE_READY = True
    try:
        import atexit
        import ctypes

        previous = ctypes.windll.kernel32.GetConsoleOutputCP()
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        # Put it back on the way out. This is the terminal the person is
        # sitting in, and leaving it changed after the program has finished
        # is rude in a way that is hard to trace back to us. The input
        # codepage is left alone entirely, because nothing here needs it and
        # changing it is the half with the known trouble.
        atexit.register(ctypes.windll.kernel32.SetConsoleOutputCP, previous)
    except Exception:
        # No console attached, or not permitted. The chcp in the command is
        # the fallback and still helps every program the shell launches.
        pass


def as_utf8_console(command):
    """Ask the Windows shell to speak utf-8 before running the command.

    Without this the shell itself does the damage before we ever see the
    bytes. Listing a directory with a Thai name on a console set to the
    old codepage prints question marks, because that codepage has no way
    to write those characters at all. Decoding cannot recover what was
    never encoded.

    The prefix is a fixed string that the model cannot influence and that
    changes nothing except the encoding. It is worth knowing that it makes
    the command that runs differ by these few characters from the one the
    person approved, which is the only reason it is written out here
    rather than hidden.
    """
    if os.name != "nt":
        return command
    _use_utf8_console()
    # What this does not fix. The shell reads the command line before the
    # chcp takes effect, so non ASCII characters inside the command itself
    # are still flattened. Writing a Thai string with echo loses it. File
    # names, command output and everything the agent reads back are fine,
    # which covers the cases that actually come up, and write_file is the
    # right tool for putting text in a file anyway.
    return f"chcp 65001 >nul & {command}"


def _new_process_group():
    """Start the command in its own group so the whole tree can be killed.

    Without this there is nothing to aim at. On Unix the shell and its
    children share our group, so signalling the group would signal us too.
    On Windows a new process group is what lets taskkill find the
    descendants of the shell rather than only the shell.
    """
    if os.name == "posix":
        return {"start_new_session": True}
    return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}


def _kill_tree(process):
    """Kill the command and everything it started."""
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            killed = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                timeout=10,
            )
            # subprocess.run does not raise on a non zero exit, so without
            # this the fallback below could never run for the case it was
            # written for, which is taskkill failing.
            if killed.returncode != 0:
                raise OSError(f"taskkill exited {killed.returncode}")
    except Exception:
        # Last resort. Killing only the shell beats killing nothing.
        try:
            process.kill()
        except Exception:
            pass


def always_allow(command: str) -> bool:
    return True


def never_allow(command: str) -> bool:
    return False


def ask_the_user(command: str) -> bool:
    """Ask before running, unless the environment says not to.

    AGENTPATH_AUTO_APPROVE exists because automated runs have nobody at the
    keyboard. Without it every test and every continuous integration job
    would hang forever waiting for an answer that never comes.
    """
    if os.environ.get("AGENTPATH_AUTO_APPROVE") == "1":
        return True
    print(f"\nThe agent wants to run this command.\n\n    {command}\n")
    try:
        return input("Run it? [y/N] ").strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def shell_tools(
    root, confirm=ask_the_user, timeout=DEFAULT_TIMEOUT, cancellation=None
) -> list[Tool]:
    root = Path(root).resolve()

    def run_shell(command):
        # Checked here rather than only in the loop because a command started
        # after the person pressed the interrupt key is exactly the failure
        # a cancellation token exists to prevent.
        if cancellation is not None and cancellation.cancelled:
            return "Cancelled before the command started."
        if not confirm(command):
            return "The user refused to run this command. Do not try to run it again."
        process = subprocess.Popen(
            as_utf8_console(command),
            shell=True,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_new_process_group(),
        )
        try:
            raw_out, raw_err = process.communicate(timeout=timeout)
            stdout, stderr = decode_output(raw_out), decode_output(raw_err)
        except subprocess.TimeoutExpired:
            # shell=True means the thing we started is a shell, and the slow
            # command is its child. Killing only the shell leaves the child
            # running and still holding the pipes, so a call that was meant
            # to give up after the timeout waits for the whole run anyway.
            # The tree has to go, not just the root of it.
            _kill_tree(process)
            try:
                raw_out, raw_err = process.communicate(timeout=5)
                stdout, stderr = decode_output(raw_out), decode_output(raw_err)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", ""
            partial = truncate((stdout or "") + (stderr or ""), 500)
            note = f"Error: the command timed out after {timeout} seconds and was killed"
            return f"{note}\n{partial}" if partial.strip() else note

        parts = []
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(stderr)
        if process.returncode != 0:
            parts.append(f"[exit code {process.returncode}]")
        return truncate("\n".join(parts) or "[no output]")

    return [
        Tool(
            name="run_shell",
            description=(
                "Run a shell command in the workspace directory and return its output. "
                "The user is asked to approve the command before it runs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line to run"}
                },
                "required": ["command"],
            },
            fn=run_shell,
        )
    ]
