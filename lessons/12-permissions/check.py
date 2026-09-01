"""Check that lesson 12 works.

Five things must be true. Safe tools never ask. Risky tools do ask. A refusal
means the tool really did not run, not that a message was printed. Answering
always means the same call is not asked about twice. And that memory does not
leak to a different call, which is the difference between a permission system
and a switch that turns safety off.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson12-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from permissions import ALLOW_ALWAYS, ALLOW_ONCE, DENY, Permissions  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    asked = []

    def record(name, arguments):
        asked.append((name, arguments))
        return DENY

    permissions = Permissions(ask=record)
    if not permissions.check("read_file", {"path": "a.py"}):
        fail("a safe tool was refused")
    if asked:
        fail("a safe tool caused a question")
    print("OK reading never asks")

    if permissions.check("run_shell", {"command": "rm -rf /"}):
        fail("a dangerous command was allowed when the answer was no")
    if len(asked) != 1:
        fail(f"expected exactly one question, saw {len(asked)}")
    print("OK a dangerous command asks, and no means no")

    marker = workspace / "should-not-exist.txt"
    command = f"\"{sys.executable}\" -c \"open(r'{marker.as_posix()}', 'w').write('x')\""
    import tools

    if permissions.check("run_shell", {"command": command}):
        tools.run("run_shell", {"command": command})
    if marker.exists():
        fail("a refused command still ran, which is the bug this check exists to catch")
    print("OK a refused command really did not run")

    always = Permissions(ask=lambda name, arguments: ALLOW_ALWAYS)
    call = {"command": "git status"}
    always.check("run_shell", call)

    # From here on every question is answered with no. Anything that still
    # gets through must have got through by being remembered.
    asked_again = []

    def refuse_everything(name, arguments):
        asked_again.append((name, arguments))
        return DENY

    always.ask = refuse_everything
    if not always.check("run_shell", call):
        fail("a call approved with always was refused the second time")
    if asked_again:
        fail("an approved call was asked about a second time")
    print("OK answering always is remembered")

    if always.check("run_shell", {"command": "rm -rf /"}):
        fail("approving one command approved a completely different one")
    if not asked_again:
        fail("a different command should have caused a fresh question")
    print("OK the memory does not leak to a different command")


if __name__ == "__main__":
    main()
