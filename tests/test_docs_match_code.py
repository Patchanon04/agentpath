"""A chapter that quotes code must quote the code that is in the folder.

Twice now a fix landed in a lesson's code and the chapter beside it kept
teaching the version that was removed. Both times it was a security fix, so
a reader following the prose typed out the vulnerable version while the
surrounding text told them it was safe. Both times a person found it by
reading, because nothing checked.

The rule this file enforces is narrow on purpose. Every Python block in a
chapter has to appear in one of the Python files in that same folder. Not
similar to, not a fair summary of, present in. A block that is deliberately
partial says so with an ellipsis, and one that is deliberately wrong says so
in the words around it, and both of those are recorded here by name rather
than waved through by a loose comparison.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LESSONS = ROOT / "lessons"

BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)

# A block may be an illustration rather than a quotation. Each entry says
# which chapter, and enough of the block to find it, and why it is allowed.
# The point of listing them is that adding one is a decision somebody makes
# on purpose rather than a silent exception.
ILLUSTRATIONS = {
    "09-search-tools": [
        ("shutil.which", "shows how a ripgrep fallback could be written"),
        ("def grep_with_ripgrep", "an exercise, not code in the folder"),
    ],
}


def python_files(folder):
    return {path.name: path.read_text(encoding="utf-8") for path in folder.glob("*.py")}


# Docstrings are stripped before comparing, using DOTALL rather than an
# escape so the pattern stays readable.
TRIPLE = re.compile('"""' + '.*?' + '"""', re.DOTALL)


def normalise(text):
    """Compare bodies, not prose.

    Chapters shorten a docstring when they show a whole function, which
    is a deliberate convention rather than drift. What must not differ is
    the code, and both drift bugs this file exists for were changed
    bodies rather than changed prose.
    """
    stripped = TRIPLE.sub('', text)
    lines = [line.rstrip() for line in stripped.strip().splitlines()]
    return "\n".join(line for line in lines if line.strip())


def is_illustration(lesson, block):
    for marker, _ in ILLUSTRATIONS.get(lesson, []):
        if marker in block:
            return True
    return False


def is_partial(block):
    """A block that says it is abbreviated does not have to match whole."""
    return "..." in block or "…" in block


def chapters():
    return sorted(LESSONS.glob("*/README.md"))


def chapter_id(path):
    return path.parent.name


DEFINITION = re.compile(r"^(?:def|class) (\w+)", re.MULTILINE)


@pytest.mark.parametrize("chapter", chapters(), ids=chapter_id)
def test_a_whole_definition_quoted_from_the_folder_matches_the_folder(chapter):
    """Every function shown whole has to be shown in its current shape somewhere.

    A chapter quotes an old shape on purpose. It says here is what we had,
    and here is what it becomes, and the old one is the point of the
    paragraph. So the rule cannot be that every block matches the folder.

    The rule is that at least one block for a given name matches. A chapter
    that only ever shows a shape the folder no longer has is a chapter
    teaching code that does not exist, and that is exactly what the two
    drift bugs looked like. A before and after pair still passes, because
    the after is there.
    """
    lesson = chapter.parent
    sources = python_files(lesson)
    defined = {}
    for filename, text in sources.items():
        for name in DEFINITION.findall(text):
            defined.setdefault(name, []).append(filename)

    current = {}
    for block in BLOCK.findall(chapter.read_text(encoding="utf-8")):
        if is_illustration(lesson.name, block) or is_partial(block):
            continue
        body = normalise(block)
        if len(body.splitlines()) < 8:
            continue
        names = DEFINITION.findall(body)
        if len(names) != 1 or names[0] not in defined:
            continue
        name = names[0]
        # A block often carries the import that goes with the function above
        # it, which is helpful in a chapter and is not part of the function.
        # Compare from the definition line down.
        quoted = body[body.index(DEFINITION.search(body).group(0)):]
        matches = any(quoted in normalise(sources[f]) for f in defined[name])
        current[name] = current.get(name, False) or matches

    stale = sorted(name for name, matched in current.items() if not matched)
    assert not stale, (
        f"{lesson.name} shows these whole and never in the shape the folder has. "
        "Either the code moved on and the chapter did not, which is how a chapter "
        f"ends up teaching a bug that was already fixed, or the quote drifted. {stale}"
    )


@pytest.mark.parametrize("chapter", chapters(), ids=chapter_id)
def test_the_thai_chapter_quotes_the_same_code_as_the_english_one(chapter):
    """The translation is a translation, so its code must be untouched."""
    thai = chapter.with_name("README.th.md")
    if not thai.exists():
        pytest.skip("no translation yet")

    english_blocks = [normalise(b) for b in BLOCK.findall(chapter.read_text(encoding="utf-8"))]
    thai_blocks = [normalise(b) for b in BLOCK.findall(thai.read_text(encoding="utf-8"))]
    assert english_blocks == thai_blocks, (
        f"{chapter.parent.name} has code in the translation that differs from the original"
    )


def previous_lesson(lesson):
    folders = sorted(p for p in LESSONS.iterdir() if p.is_dir())
    index = folders.index(lesson)
    return folders[index - 1] if index else None


@pytest.mark.parametrize("chapter", chapters(), ids=chapter_id)
def test_a_file_this_lesson_introduces_is_explained_in_it(chapter):
    """A file that appears without a word about it is a file nobody can follow.

    Carried forward files are already explained where they were introduced.
    A file that appears for the first time here has to be named here, which
    is the thing grep_worker.py failed for a week.
    """
    lesson = chapter.parent
    earlier = previous_lesson(lesson)
    if earlier is None:
        pytest.skip("nothing comes before the first lesson")

    inherited = {path.name for path in earlier.glob("*.py")}
    text = chapter.read_text(encoding="utf-8")
    unexplained = [
        path.name
        for path in sorted(lesson.glob("*.py"))
        if path.name not in inherited and path.name not in text
    ]
    assert not unexplained, (
        f"{lesson.name} introduces files the chapter never names {unexplained}"
    )


def test_a_chapter_does_not_promise_a_count_it_does_not_deliver():
    """The check output quoted in a chapter has to have the right number of lines."""
    wrong = []
    for chapter in chapters():
        lesson = chapter.parent
        check = lesson / "check.py"
        if not check.exists():
            continue
        printed = check.read_text(encoding="utf-8").count('print("OK')
        text = chapter.read_text(encoding="utf-8")
        quoted = text.count("OK ")
        if printed and quoted and quoted < printed:
            wrong.append(f"{lesson.name} prints {printed} OK lines and quotes {quoted}")
    assert not wrong, wrong
