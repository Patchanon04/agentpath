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
