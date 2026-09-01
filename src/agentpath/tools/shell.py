"""A tool that runs shell commands, with a question asked first.

The question is the whole point. A model can be talked into running
something destructive by text it read from a file, so the last gate before
anything runs is a human. In part 3 this grows into a real permission
system. Here it is deliberately one function, so you can see that the idea
is small even though it matters a lot.
"""
import os
import subprocess
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import truncate

DEFAULT_TIMEOUT = 60


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


def shell_tools(root, confirm=ask_the_user, timeout=DEFAULT_TIMEOUT) -> list[Tool]:
    root = Path(root).resolve()

    def run_shell(command):
        if not confirm(command):
            return "The user refused to run this command. Do not try to run it again."
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=root,
                capture_output=True,
                timeout=timeout,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return f"Error: the command timed out after {timeout} seconds"
        parts = []
        if completed.stdout:
            parts.append(completed.stdout)
        if completed.stderr:
            parts.append(completed.stderr)
        if completed.returncode != 0:
            parts.append(f"[exit code {completed.returncode}]")
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
