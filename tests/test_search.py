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
