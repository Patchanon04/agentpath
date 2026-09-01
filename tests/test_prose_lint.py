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
