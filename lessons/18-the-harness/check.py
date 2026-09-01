"""Check that the harness works from end to end.

This is the milestone for part 3, so it exercises every subsystem in one
run rather than testing them apart. A real task is done in a real directory
with permissions on, the session is written as it happens, the usage is
counted, and then the session is loaded again and carried on with, which is
the thing an agent could not do at the end of part 2.
"""
import os
import sys
import tempfile
from pathlib import Path

home = Path(tempfile.mkdtemp(prefix="agentpath-lesson18-home-"))
workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson18-ws-"))
os.environ["AGENTPATH_HOME"] = str(home)
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from agent import run  # noqa: E402
from permissions import DENY, Permissions  # noqa: E402
from prompt import build_system_prompt  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402
from session import Session  # noqa: E402
from usage import Usage  # noqa: E402

BUGGY = 'def add(a, b):\n    """Return the sum."""\n    return a - b\n'

TASK = (
    "Fix the bug in calc.py. "
    '[[tool:grep_files:{"pattern": "def add", "glob": "*.py"}]]'
    '[[tool:read_file:{"path": "calc.py"}]]'
    '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]'
)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def provider():
    return OpenAICompatProvider(
        os.environ["AGENTPATH_BASE_URL"],
        os.environ.get("AGENTPATH_API_KEY", ""),
        os.environ["AGENTPATH_MODEL"],
    )


def main():
    (workspace / "calc.py").write_text(BUGGY, encoding="utf-8")
    session = Session("milestone")
    usage = Usage()

    run(
        provider(),
        TASK,
        system=build_system_prompt(workspace),
        permissions=Permissions(auto_approve=True),
        on_message=session.append,
        budget=100000,
        usage=usage,
    )

    if "return a + b" not in (workspace / "calc.py").read_text(encoding="utf-8"):
        fail("the bug was not fixed on disk")
    print("OK the agent fixed a real bug in a real file")

    saved = session.load()
    if [m["role"] for m in saved[:3]] != ["system", "user", "assistant"]:
        fail(f"the session was not written as the run happened. Got {[m['role'] for m in saved]}")
    print(f"OK the session was written as it happened, {len(saved)} messages")

    if usage.calls < 2 or usage.prompt_tokens <= 0:
        fail(f"usage was not counted. Got {usage.summary()}")
    print(f"OK the run counted what it cost, {usage.summary()}")

    carried_on = Session("milestone").load()
    _, messages = run(
        provider(),
        "Say thank you.",
        permissions=Permissions(auto_approve=True),
        history=carried_on,
        on_message=session.append,
        usage=usage,
    )
    if len(messages) <= len(carried_on):
        fail("resuming did not carry the old conversation forward")
    print(f"OK the session was resumed and carried on from, now {len(messages)} messages")

    denied = Session("denied")
    (workspace / "other.py").write_text("x = 1\n", encoding="utf-8")
    run(
        provider(),
        'Change it. [[tool:edit_file:{"path": "other.py", "old": "x = 1", "new": "x = 2"}]]',
        permissions=Permissions(ask=lambda name, arguments: DENY),
        on_message=denied.append,
    )
    if (workspace / "other.py").read_text(encoding="utf-8") != "x = 1\n":
        fail("a refused edit changed the file anyway, which is the bug this check exists for")
    print("OK a refused tool call really did not touch the file")


if __name__ == "__main__":
    main()
