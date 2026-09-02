"""Every tool has to prove the same things, and a new tool has to prove them too.

Three reviews found the same shape of bug three times. A rule was enforced
where somebody remembered to enforce it, a new entry point appeared later,
and nothing noticed that the rule now had a hole in it. read_file refused a
path outside the workspace while grep_files walked straight past it. The
whole registry honoured the credential list while a subprocess did not.

The fix for that is not another test of read_file. It is a test that asks
every tool in the registry the same questions, so that adding a tool without
answering them fails the build. The parametrise below reads the registry
rather than a list written by hand, which is the part that makes it hold.
"""
import json
import os
import subprocess
import sys

import pytest

from agentpath.cli import build_tools
from agentpath.types import ToolCall

SECRET = "SUPERSECRETVALUE"
OUTSIDE = "OUTSIDEVALUE"

# Arguments that name a path, per tool. A tool that takes a path and is not
# listed here will fail test_every_path_taking_tool_is_listed, which is the
# point. Somebody adding a tool has to decide what its escape attempt looks
# like rather than quietly inheriting no coverage.
ESCAPE_ATTEMPTS = {
    "read_file": {"path": "../outside/secret.txt"},
    "write_file": {"path": "../outside/planted.txt", "content": "x"},
    "edit_file": {"path": "../outside/secret.txt", "old": "a", "new": "b"},
    "list_files": {"path": ".."},
}

# Tools that take no path and so cannot be asked to escape by naming one.
# run_shell is here for an uncomfortable reason that the note below explains.
NO_PATH_ARGUMENT = {"glob_files", "grep_files", "search_notes", "run_shell"}


@pytest.fixture
def workspace(tmp_path):
    """A workspace with a secret inside it and a secret next to it."""
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(f"value={OUTSIDE}\n", encoding="utf-8")
    (root / ".env").write_text(f"API_KEY={SECRET}\n", encoding="utf-8")
    (root / "ok.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    (root / "notes.md").write_text("# Notes\n\nnothing sensitive\n", encoding="utf-8")
    return root


def tool_names():
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        return sorted(schema["name"] for schema in build_tools(directory).schemas())


def run_tool(registry, name, arguments):
    return registry.run(ToolCall(id="1", name=name, arguments=arguments)).content


def test_every_path_taking_tool_is_listed():
    """A new tool must be classified before it can be shipped.

    This is the test that makes the rest of the file keep working. Without
    it, a tool added next year takes a path, gets no escape attempt written
    for it, and passes this suite by not being in it.
    """
    known = set(ESCAPE_ATTEMPTS) | NO_PATH_ARGUMENT
    unclassified = set(tool_names()) - known
    assert not unclassified, (
        f"these tools are new and nobody has said whether they take a path {unclassified}. "
        "Add them to ESCAPE_ATTEMPTS with an escape attempt, or to NO_PATH_ARGUMENT."
    )


@pytest.mark.parametrize("name", sorted(ESCAPE_ATTEMPTS))
def test_a_named_path_cannot_leave_the_workspace(workspace, name):
    result = run_tool(build_tools(workspace), name, ESCAPE_ATTEMPTS[name])
    assert OUTSIDE not in result, f"{name} read a file outside the workspace"
    assert "outside the workspace" in result, f"{name} did not refuse, it said {result[:120]!r}"
    assert not (workspace.parent / "outside" / "planted.txt").exists()


@pytest.mark.parametrize("name", tool_names())
def test_no_tool_hands_back_the_contents_of_a_credential_file(workspace, name):
    """Asked in the way each tool is actually used, not with a crafted path.

    grep_files never takes a path, so the only way it leaks .env is by
    searching it, which is exactly how it leaked before.
    """
    probes = {
        "read_file": {"path": ".env"},
        "write_file": {"path": "harmless.txt", "content": "x"},
        "edit_file": {"path": ".env", "old": "API_KEY", "new": "NOPE"},
        "list_files": {"path": "."},
        "glob_files": {"pattern": "**/*"},
        "grep_files": {"pattern": "API_KEY"},
        "search_notes": {"question": "API_KEY"},
        "run_shell": {"command": f'"{sys.executable}" -c "print(1)"'},
    }
    result = run_tool(build_tools(workspace), name, probes[name])
    assert SECRET not in result, f"{name} handed back the contents of .env"


@pytest.mark.parametrize("name", ["glob_files", "grep_files", "search_notes"])
def test_a_link_is_not_a_way_out(workspace, name):
    """rglob follows links, and the name of a link says nothing about its target.

    This is the bug that shipped. It cannot be caught by testing read_file,
    because read_file was never the tool that had it.
    """
    outside = workspace.parent / "outside"
    (outside / "readable.md").write_text(f"# Outside\n\nvalue is {OUTSIDE}\n", encoding="utf-8")
    link = workspace / "vendor"
    if sys.platform == "win32":
        subprocess.run(f'mklink /J "{link}" "{outside}"', shell=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    if not link.exists():
        pytest.skip("this system does not allow creating a link")

    probes = {
        "glob_files": {"pattern": "**/*"},
        "grep_files": {"pattern": "value"},
        "search_notes": {"question": "value outside"},
    }
    result = run_tool(build_tools(workspace), name, probes[name])
    assert OUTSIDE not in result, f"{name} read through a link and out of the workspace"
    assert "secret.txt" not in result


@pytest.mark.parametrize("name", ["read_file", "list_files", "glob_files", "grep_files"])
def test_a_safe_tool_still_does_its_job(workspace, name):
    """The other half of every fix above, and the half that gets forgotten.

    Two fixes in this project stopped legitimate work while closing a hole.
    A refusal that refuses everything passes a security test and is useless.
    """
    probes = {
        "read_file": ({"path": "ok.py"}, "def start"),
        "list_files": ({"path": "."}, "ok.py"),
        "glob_files": ({"pattern": "**/*.py"}, "ok.py"),
        "grep_files": ({"pattern": "def start"}, "ok.py:1:"),
    }
    arguments, expected = probes[name]
    result = run_tool(build_tools(workspace), name, arguments)
    assert expected in result, f"{name} refused ordinary work, it said {result[:120]!r}"


def test_no_tool_runs_code_it_found_in_the_workspace(workspace, monkeypatch):
    """A subprocess started in the workspace imports the workspace.

    Running a module with -m puts the starting directory first on the import
    path. A file the agent wrote called json.py or types.py was then imported
    and executed before any work began, and searching is a safe tool so
    nothing asked permission. The tell is that the tool still returns the
    right answer, so nothing looks wrong.
    """
    monkeypatch.chdir(workspace)
    proof = workspace / "EXECUTED.txt"
    for shadowed in ["json", "types", "fnmatch", "re", "pathlib"]:
        (workspace / f"{shadowed}.py").write_text(
            f'open(r"{proof}", "w").write("workspace code ran via {shadowed}")\n',
            encoding="utf-8",
        )

    registry = build_tools(workspace)
    for name, arguments in [
        ("grep_files", {"pattern": "def start"}),
        ("glob_files", {"pattern": "**/*.py"}),
        ("search_notes", {"question": "notes"}),
        ("run_shell", {"command": f'"{sys.executable}" -c "print(1)"'}),
    ]:
        run_tool(registry, name, arguments)
        assert not proof.exists(), f"{name} executed a file out of the workspace"


def test_the_shell_tool_is_not_confined_and_the_suite_says_so(workspace):
    """A failing promise recorded as a passing test, on purpose.

    run_shell takes a command line rather than a path, so the workspace gate
    has nothing to hold on to and cwd is a starting point rather than a
    fence. The book and lesson 13 both say this in words. This test pins the
    behaviour so that the day somebody confines the shell, this fails and
    the two documents get updated with it.
    """
    outside = (workspace.parent / "outside" / "secret.txt").resolve()
    reader = f'"{sys.executable}" -c "print(open(r\'{outside}\').read())"'
    result = run_tool(build_tools(workspace), "run_shell", {"command": reader})
    assert OUTSIDE in result, (
        "run_shell is confined now, which is good news and means the honest limit "
        "written in book/13-tools-that-touch-the-world.md section 1.1 and in "
        "lessons/13 is out of date. Update both, then delete this test."
    )


def test_a_tool_that_is_not_read_only_is_not_marked_safe(workspace):
    """safe means the permission gate is skipped, so it has to stay narrow."""
    registry = build_tools(workspace)
    changes_things = {"write_file", "edit_file", "run_shell"}
    for name in changes_things:
        assert not registry.get(name).safe, f"{name} changes things and must not be safe"


def test_tools_discovered_at_run_time_are_never_safe():
    """We did not write them and the description is whatever its author claimed."""
    from agentpath.mcp import MCPClient, mcp_tools

    server = [sys.executable, "-m", "agentpath.testing.mock_mcp_server"]
    with MCPClient(server) as client:
        discovered = mcp_tools(client, prefix="probe")
    assert discovered
    assert all(not tool.safe for tool in discovered)


def test_the_environment_the_child_sees_does_not_leak_the_workspace(workspace, monkeypatch):
    """A child that inherits PYTHONPATH pointing at the workspace is the same hole."""
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("PYTHONPATH", str(workspace))
    proof = workspace / "VIA_PYTHONPATH.txt"
    (workspace / "fnmatch.py").write_text(
        f'open(r"{proof}", "w").write("ran")\n', encoding="utf-8"
    )
    registry = build_tools(workspace)
    run_tool(registry, "grep_files", {"pattern": "def start"})
    assert not proof.exists(), "the child honoured PYTHONPATH pointing at the workspace"


def test_the_search_child_cannot_be_told_to_search_somewhere_else(workspace):
    """The request crosses a process boundary as JSON, so it is worth pinning.

    Nothing stops the parent asking the child for a different root today,
    because the parent is the one that decides. This test records that the
    child is only ever asked for the workspace it was built with.
    """
    import agentpath.tools.search as module

    seen = {}
    original = module.subprocess.run

    def capture(command, **kwargs):
        seen["request"] = json.loads(kwargs["input"])
        seen["cwd"] = kwargs.get("cwd")
        seen["isolated"] = "-I" in command
        return original(command, **kwargs)

    module.subprocess.run = capture
    try:
        run_tool(build_tools(workspace), "grep_files", {"pattern": "def"})
    finally:
        module.subprocess.run = original

    assert seen["request"]["root"] == str(workspace.resolve())
    assert seen["isolated"], "the child is not started isolated"
    assert os.path.realpath(seen["cwd"]) != os.path.realpath(workspace)
