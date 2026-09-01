"""Check that the mini coding agent works from end to end.

This is the milestone check for part 2, so it does the whole job rather than
testing pieces. It creates a real project directory with a real bug, asks
the agent to fix it, and then reads the file back off disk to prove the
change happened. Nothing is mocked except the model itself.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson11-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)
os.environ["AGENTPATH_AUTO_APPROVE"] = "1"

from agent import run  # noqa: E402
from prompt import build_system_prompt  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402

BUGGY = '''def add(a, b):
    """Return the sum of two numbers."""
    return a - b


def multiply(a, b):
    return a * b
'''

PYTHON = Path(sys.executable).as_posix()

TASK = (
    "The add function in calc.py has a bug. Find it and fix it, then prove it works. "
    '[[tool:grep_files:{"pattern": "def add", "glob": "*.py"}]]'
    '[[tool:read_file:{"path": "calc.py"}]]'
    '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]'
    '[[tool:run_shell:{"command": "\\"' + PYTHON + '\\" -c \\"import calc; print(calc.add(2, 3))\\""}]]'
)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    (workspace / "calc.py").write_text(BUGGY, encoding="utf-8")

    provider = OpenAICompatProvider(
        os.environ["AGENTPATH_BASE_URL"],
        os.environ.get("AGENTPATH_API_KEY", ""),
        os.environ["AGENTPATH_MODEL"],
    )
    answer, messages = run(provider, TASK, system=build_system_prompt(workspace))

    fixed = (workspace / "calc.py").read_text(encoding="utf-8")
    if "return a + b" not in fixed:
        fail(f"the bug was not fixed on disk. The file still says\n{fixed}")
    if "return a * b" not in fixed:
        fail("the agent damaged the rest of the file while fixing the bug")
    print("\nOK the agent found the bug, fixed it, and left the rest of the file alone")

    shell_results = [m["content"] for m in messages if m.get("role") == "tool"]
    if not any(result.strip() == "5" for result in shell_results):
        fail(f"running the fixed code did not print 5. Tool results were {shell_results!r}")
    print("OK running the fixed code printed 5, so the fix really works")


if __name__ == "__main__":
    main()
