import pytest

from agentpath.tools.base import ToolRegistry
from agentpath.tools.files import file_tools
from agentpath.types import ToolCall


@pytest.fixture
def registry(tmp_path):
    (tmp_path / "a.py").write_text("print('one')\nprint('two')\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("x = 1\n", encoding="utf-8")
    return ToolRegistry(file_tools(tmp_path)), tmp_path


def call(registry, name, **arguments):
    return registry.run(ToolCall(id="1", name=name, arguments=arguments)).content


def test_read_file_returns_content(registry):
    reg, _ = registry
    assert "print('one')" in call(reg, "read_file", path="a.py")


def test_read_file_outside_workspace_is_an_error_not_a_crash(registry):
    reg, _ = registry
    assert "outside the workspace" in call(reg, "read_file", path="../x.txt")


def test_read_file_refuses_env(registry):
    reg, root = registry
    (root / ".env").write_text("KEY=supersecret\n", encoding="utf-8")
    result = call(reg, "read_file", path=".env")
    assert "refuses to touch" in result
    assert "supersecret" not in result


def test_write_file_creates_and_reports(registry):
    reg, root = registry
    result = call(reg, "write_file", path="new.txt", content="hello")
    assert (root / "new.txt").read_text(encoding="utf-8") == "hello"
    assert "new.txt" in result


def test_write_file_creates_missing_directories(registry):
    reg, root = registry
    call(reg, "write_file", path="deep/nested/x.txt", content="hi")
    assert (root / "deep" / "nested" / "x.txt").exists()


def test_list_files_shows_the_tree(registry):
    reg, _ = registry
    result = call(reg, "list_files", path=".")
    assert "a.py" in result
    assert "sub" in result


def test_edit_file_replaces_exactly_once(registry):
    reg, root = registry
    result = call(reg, "edit_file", path="a.py", old="print('one')", new="print('ONE')")
    assert "print('ONE')" in (root / "a.py").read_text(encoding="utf-8")
    assert "Edited" in result


def test_edit_file_refuses_when_the_text_is_missing(registry):
    reg, _ = registry
    assert "was not found" in call(reg, "edit_file", path="a.py", old="nope", new="x")


def test_edit_file_refuses_when_the_text_is_ambiguous(registry):
    reg, root = registry
    (root / "c.py").write_text("v = 1\nv = 1\n", encoding="utf-8")
    result = call(reg, "edit_file", path="c.py", old="v = 1", new="v = 2")
    assert "appears 2 times" in result
    assert (root / "c.py").read_text(encoding="utf-8") == "v = 1\nv = 1\n"


def test_long_output_is_truncated(registry):
    reg, root = registry
    (root / "big.txt").write_text("x" * 9000, encoding="utf-8")
    result = call(reg, "read_file", path="big.txt")
    assert len(result) < 5000
    assert "truncated" in result
