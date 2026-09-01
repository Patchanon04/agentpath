"""Check that lesson 23 works.

This chapter adds no new ideas, so the check asks a different question. Is
what you built actually shippable. That means four things. Every module the
course wrote imports cleanly on its own. The agent still does a real job end
to end. The pieces from all four parts are present. And nothing in the
project reaches for a dependency the reader was never told to install.
"""
import importlib
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson23-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)
os.environ["AGENTPATH_HOME"] = str(workspace / "home")

MODULES = [
    "providers",
    "tools",
    "agent",
    "prompt",
    "permissions",
    "session",
    "context",
    "usage",
    "retry",
    "cancel",
    "retrieval",
    "fanout",
    "subagent",
    "evals",
    "mcp",
]

ALLOWED_OUTSIDE_THE_STANDARD_LIBRARY = {"httpx"}


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    for name in MODULES:
        try:
            importlib.import_module(name)
        except Exception as error:
            fail(f"{name}.py does not import on its own, {type(error).__name__}: {error}")
    print(f"OK all {len(MODULES)} modules import cleanly")

    import tools
    from agent import run
    from permissions import Permissions
    from providers import OpenAICompatProvider
    from session import Session
    from usage import Usage

    (workspace / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    session = Session("shipping")
    usage = Usage()
    run(
        OpenAICompatProvider(
            os.environ["AGENTPATH_BASE_URL"],
            os.environ.get("AGENTPATH_API_KEY", ""),
            os.environ["AGENTPATH_MODEL"],
        ),
        'Fix it. [[tool:read_file:{"path": "calc.py"}]]'
        '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]',
        permissions=Permissions(auto_approve=True),
        on_message=session.append,
        usage=usage,
    )
    if "return a + b" not in (workspace / "calc.py").read_text(encoding="utf-8"):
        fail("the finished agent could not do the job it could do in lesson 11")
    print("OK the finished agent still fixes a real bug in a real file")

    if not session.load() or usage.calls < 1:
        fail("the harness pieces from part 3 are not working")
    print(f"OK the session and the usage counter are working, {usage.summary()}")

    expected_tools = {
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "run_shell",
        "glob_files",
        "grep_files",
        "search_notes",
    }
    have = {schema["function"]["name"] for schema in tools.SCHEMAS}
    if not expected_tools <= have:
        fail(f"tools are missing. Expected {expected_tools}, have {have}")
    print(f"OK all {len(expected_tools)} tools from parts 2 and 3 are present")

    imported = set()
    for path in Path(__file__).parent.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imported.add(stripped.split()[1].split(".")[0])
    third_party = {
        name
        for name in imported
        if name not in sys.stdlib_module_names
        and name not in {m for m in MODULES}
        and name not in {"__future__"}
    }
    if not third_party <= ALLOWED_OUTSIDE_THE_STANDARD_LIBRARY:
        fail(f"something reaches for an unexpected dependency, {third_party}")
    print(f"OK the only dependency outside the standard library is {third_party or 'none'}")


if __name__ == "__main__":
    main()
