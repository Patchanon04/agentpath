import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))

from prose_lint import find_violations


def test_flags_em_dash(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("a — b", encoding="utf-8")
    violations = find_violations([target])
    assert len(violations) == 1
    assert violations[0][1] == 1


def test_flags_emoji(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("all good \U0001F600", encoding="utf-8")
    assert len(find_violations([target])) == 1


def test_clean_file_passes(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("plain prose, nothing fancy", encoding="utf-8")
    assert find_violations([target]) == []


def test_flags_a_colon_in_prose(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("Troubleshooting: when it refuses\n", encoding="utf-8")
    violations = find_violations([target])
    assert any(reason == "colon in prose" for _, _, reason in violations)


def test_a_colon_inside_inline_code_is_fine(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("Set the header `Content-Type: application/json` first\n", encoding="utf-8")
    assert find_violations([target]) == []


def test_a_colon_inside_a_fenced_block_is_fine(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text('```python\nd = {"a": 1}\n```\n', encoding="utf-8")
    assert find_violations([target]) == []


def test_a_url_is_not_a_colon_violation(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("Read more at https://example.com/page for the details\n", encoding="utf-8")
    assert find_violations([target]) == []


def test_colon_checking_can_be_turned_off(tmp_path):
    """The design document and the plans are working notes, not chapters."""
    target = tmp_path / "doc.md"
    target.write_text("Note: this is an internal working document\n", encoding="utf-8")
    assert find_violations([target], check_colons=False) == []
