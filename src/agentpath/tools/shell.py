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
            command,
            shell=True,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_new_process_group(),
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            # shell=True means the thing we started is a shell, and the slow
            # command is its child. Killing only the shell leaves the child
            # running and still holding the pipes, so a call that was meant
            # to give up after the timeout waits for the whole run anyway.
            # The tree has to go, not just the root of it.
            _kill_tree(process)
            try:
                stdout, stderr = process.communicate(timeout=5)
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
