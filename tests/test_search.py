import pytest

from agentpath.tools.base import ToolRegistry
from agentpath.tools.search import search_tools
from agentpath.types import ToolCall


@pytest.fixture
def registry(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    (tmp_path / "src" / "util.py").write_text("def helper():\n    return 2\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("start here\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "junk.py").write_text("def start():\n", encoding="utf-8")
    return ToolRegistry(search_tools(tmp_path))


def call(registry, name, **arguments):
    return registry.run(ToolCall(id="1", name=name, arguments=arguments)).content


def test_glob_finds_python_files(registry):
    result = call(registry, "glob_files", pattern="**/*.py")
    assert "src/main.py" in result
    assert "src/util.py" in result


def test_glob_skips_virtual_environments(registry):
    assert "junk.py" not in call(registry, "glob_files", pattern="**/*.py")


def test_grep_reports_file_and_line(registry):
    result = call(registry, "grep_files", pattern="def start")
    assert "main.py" in result
    assert ":1:" in result


def test_grep_can_be_limited_by_glob(registry):
    result = call(registry, "grep_files", pattern="start", glob="*.md")
    assert "notes.md" in result
    assert "main.py" not in result


def test_grep_reports_no_matches_clearly(registry):
    assert "no matches" in call(registry, "grep_files", pattern="zzzz").lower()


def test_a_bad_regular_expression_is_an_error_not_a_crash(registry):
    assert "not a valid" in call(registry, "grep_files", pattern="[unclosed")


def test_search_cannot_be_used_to_read_credential_files(tmp_path):
    """grep must honour the same refusal read_file does.

    Without this, search is a way around the credential deny list, and a
    rule one tool honours while another ignores it is not a rule.
    """
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-supersecret\n", encoding="utf-8")
    registry = ToolRegistry(search_tools(tmp_path))
    assert "sk-supersecret" not in call(registry, "grep_files", pattern="KEY")
    assert ".env" not in call(registry, "glob_files", pattern="*")


def test_a_workspace_living_inside_a_skipped_directory_still_works(tmp_path):
    """The skip list must apply to the path inside the workspace only.

    A project that happens to live under a folder called node_modules would
    otherwise have every one of its files skipped.
    """
    workspace = tmp_path / "node_modules" / "myproject"
    workspace.mkdir(parents=True)
    (workspace / "main.py").write_text("def start():\n    pass\n", encoding="utf-8")
    registry = ToolRegistry(search_tools(workspace))
    assert "main.py" in call(registry, "glob_files", pattern="**/*.py")


def test_a_link_cannot_be_used_to_read_outside_the_workspace(tmp_path):
    """rglob follows symlinks and Windows junctions.

    A link planted inside the workspace, which the shell tool can create,
    would otherwise let search read anything on the machine while read_file
    correctly refused. Filtering on the name of the link never sees the name
    of the target, so the check has to resolve the path.
    """
    import subprocess
    import sys

    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secrets.txt").write_text("value=LEAKEDVALUE\n", encoding="utf-8")
    (root / "ok.txt").write_text("nothing here\n", encoding="utf-8")

    link = root / "vendor"
    if sys.platform == "win32":
        subprocess.run(f'mklink /J "{link}" "{outside}"', shell=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    if not link.exists():
        pytest.skip("this system does not allow creating a link")

    registry = ToolRegistry(search_tools(root))
    assert "LEAKEDVALUE" not in call(registry, "grep_files", pattern="value")
    assert "secrets.txt" not in call(registry, "glob_files", pattern="**/*")


def test_a_pattern_that_could_run_forever_is_refused(tmp_path):
    """A model can write (a+)+ by accident and wedge the whole process.

    No cancellation token helps, because the matching never returns to check
    one. The only place to stop it is before it starts.
    """
    (tmp_path / "small.txt").write_text("a" * 39 + "!\n", encoding="utf-8")
    registry = ToolRegistry(search_tools(tmp_path))
    import time as _time

    started = _time.monotonic()
    result = call(registry, "grep_files", pattern="(a+)+$")
    assert _time.monotonic() - started < 1.0
    assert "nested repeat" in result or "one repeat wrapped in another" in result


def test_ordinary_patterns_with_one_quantifier_still_work(tmp_path):
    (tmp_path / "a.py").write_text("def start():\n    pass\n", encoding="utf-8")
    registry = ToolRegistry(search_tools(tmp_path))
    assert "a.py:1:" in call(registry, "grep_files", pattern="def +start")

NEWLINE = "\n"

def test_a_catastrophic_pattern_gives_up_instead_of_hanging(tmp_path):
    """The pattern gate cannot catch every shape, so there is a hard deadline.

    Two earlier attempts at that deadline did not work and both are worth
    knowing. Checking between lines never gets a turn, because one line is
    enough to go exponential. Moving the match to a thread does not help
    either, because matching does not release the interpreter lock, so the
    waiter cannot run. Only a separate process can be given up on.
    """
    import time as _time

    (tmp_path / "one.txt").write_text(("a" * 40 + "!" + NEWLINE) * 20, encoding="utf-8")
    registry = ToolRegistry(search_tools(tmp_path))

    started = _time.monotonic()
    result = call(registry, "grep_files", pattern="(a|a)+$")
    elapsed = _time.monotonic() - started

    assert elapsed < 20, f"the search ran for {elapsed:.1f} seconds"
    assert "given up on" in result or "nested repeat" in result


def test_a_search_that_cannot_start_says_so(tmp_path, monkeypatch):
    """A child that will not start is not the same as a search that failed."""
    import agentpath.tools.search as module

    monkeypatch.setattr(module.sys, "executable", str(tmp_path / "no-such-python.exe"))
    registry = ToolRegistry(search_tools(tmp_path))
    result = call(registry, "grep_files", pattern="anything")
    assert "could not be started" in result


def test_a_workspace_file_cannot_be_imported_by_the_search(tmp_path, monkeypatch):
    """The child used to start with the workspace first on the import path.

    A file the agent had written there called json.py or types.py was
    imported and run before any searching began, and searching is a safe
    tool so nothing asked permission first.
    """
    monkeypatch.chdir(tmp_path)
    proof = tmp_path / "EXECUTED.txt"
    (tmp_path / "fnmatch.py").write_text(
        f'open(r"{proof}", "w").write("workspace code ran")\n', encoding="utf-8"
    )
    (tmp_path / "app.py").write_text("needle\n", encoding="utf-8")

    registry = ToolRegistry(search_tools(tmp_path))
    assert "app.py:1: needle" in call(registry, "grep_files", pattern="needle")
    assert not proof.exists(), "the search executed a file out of the workspace"
