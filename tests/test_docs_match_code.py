"""A chapter that quotes code must quote the code that is in the folder.

Twice now a fix landed in a lesson's code and the chapter beside it kept
teaching the version that was removed. Both times it was a security fix, so
a reader following the prose typed out the vulnerable version while the
surrounding text told them it was safe. Both times a person found it by
reading, because nothing checked.

The rule this file enforces is narrow on purpose. A function shown whole in
a chapter has to appear somewhere in that chapter in the shape the folder
has. Not similar to, not a fair summary of, present in. A block that is
deliberately partial says so with an ellipsis, and one that is deliberately
wrong says so in the words around it and is recorded here by name rather
than waved through by a loose comparison.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LESSONS = ROOT / "lessons"
# The foundations track is the from zero material. It has no tools.py and
# no API, so the parity tests do not apply, but a chapter there quotes code
# from its own folder exactly as a lesson does and drifts the same way.
FOUNDATIONS = ROOT / "foundations"
# The training track is part 4, fine tuning and serving. Its numpy demos
# are checked like the foundations, and its real scripts need a GPU and
# are quoted by the chapters like any other file.
TRAINING = ROOT / "training"
TRACKS = [track for track in (FOUNDATIONS, LESSONS, TRAINING) if track.exists()]

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
    "20-subagents": [
        ("# the version that is wrong", "a counter example the prose argues against"),
    ],
}


def python_files(folder):
    return {path.name: path.read_text(encoding="utf-8") for path in folder.glob("*.py")}


# Docstrings are stripped before comparing. DOTALL rather than an escaped
# newline keeps the pattern readable.
TRIPLE = re.compile('"""' + ".*?" + '"""', re.DOTALL)


def normalise(text):
    """Compare bodies, not prose.

    Chapters shorten a docstring when they show a whole function, which is a
    deliberate convention rather than drift. What must not differ is the
    code, and both drift bugs this file exists for were changed bodies.
    """
    stripped = TRIPLE.sub("", text)
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
    found = []
    for track in TRACKS:
        found += sorted(track.glob("*/README.md"))
    return found


def chapter_id(path):
    return f"{path.parent.parent.name}/{path.parent.name}"


DEFINITION = re.compile(r"^(?:def|class) (\w+)", re.MULTILINE)


def definitions(body):
    """Every top level def or class in a block, as (name, source).

    Splitting the block up is what makes this test worth running. Chapters
    show whole files, and a whole file block holds several definitions, so a
    rule that only looked at blocks containing exactly one definition
    skipped sixty six blocks and compared nine percent of the code in the
    course. A security helper lives in a file alongside other functions,
    which is exactly the shape that was being skipped.
    """
    lines = body.splitlines()
    found = []
    start = None
    name = None
    for index, line in enumerate(lines):
        heading = DEFINITION.match(line)
        if heading:
            if start is not None:
                found.append((name, "\n".join(lines[start:index])))
            start, name = index, heading.group(1)
        elif start is not None and line and not line[0].isspace():
            found.append((name, "\n".join(lines[start:index])))
            start = name = None
    if start is not None:
        found.append((name, "\n".join(lines[start:])))
    return found


@pytest.mark.parametrize("chapter", chapters(), ids=chapter_id)
def test_a_whole_definition_quoted_from_the_folder_matches_the_folder(chapter):
    """Every function shown whole has to be shown in its current shape somewhere.

    A chapter quotes an old shape on purpose. It says here is what we had,
    and here is what it becomes, and the old one is the point of the
    paragraph. So the rule cannot be that every quotation matches the folder.

    The rule is that at least one quotation of a given name matches. A
    chapter that only ever shows a shape the folder no longer has is a
    chapter teaching code that does not exist, and that is what both drift
    bugs looked like. A before and after pair still passes because the after
    is there.
    """
    lesson = chapter.parent
    sources = python_files(lesson)
    bodies = {filename: normalise(text) for filename, text in sources.items()}
    defined = {}
    for filename, text in sources.items():
        for name in DEFINITION.findall(text):
            defined.setdefault(name, []).append(filename)

    current = {}
    for block in BLOCK.findall(chapter.read_text(encoding="utf-8")):
        if is_illustration(lesson.name, block) or is_partial(block):
            continue
        for name, quoted in definitions(normalise(block)):
            # A lone signature line is a fragment, not a whole quotation.
            if name not in defined or len(quoted.splitlines()) < 2:
                continue
            matched = any(quoted in bodies[f] for f in defined[name])
            current[name] = current.get(name, False) or matched

    stale = sorted(name for name, matched in current.items() if not matched)
    assert not stale, (
        f"{lesson.name} shows these whole and never in the shape the folder has. "
        "Either the code moved on and the chapter did not, which is how a chapter "
        f"ends up teaching a bug that was already fixed, or the quote drifted. {stale}"
    )


def test_the_comparison_is_not_quietly_checking_nothing():
    """A drift test that skips everything passes and proves nothing.

    Every exclusion in the test above is a place drift could hide, and the
    exclusions grew without anybody noticing until somebody counted them.
    This records the coverage as a number, so a change that halves it fails
    here rather than passing in silence.
    """
    compared = 0
    for chapter in chapters():
        sources = python_files(chapter.parent)
        defined = set()
        for text in sources.values():
            defined |= set(DEFINITION.findall(text))
        seen = set()
        for block in BLOCK.findall(chapter.read_text(encoding="utf-8")):
            if is_illustration(chapter.parent.name, block) or is_partial(block):
                continue
            for name, quoted in definitions(normalise(block)):
                if name in defined and len(quoted.splitlines()) >= 2:
                    seen.add(name)
        compared += len(seen)
    assert compared >= 70, (
        f"only {compared} definitions are being compared against the folders. "
        "Something narrowed the comparison, and a drift test that compares "
        "nothing still passes."
    )


BOOK = ROOT / "book"

# The book quotes code from the whole project, so its blocks are compared
# against the package and every lesson folder at once. Deliberate
# simplifications are named here with their reason, same as above.
BOOK_ILLUSTRATIONS = {
    "02-the-loop.md": [
        ("def run(self, user_input", "the loop with its protections cut away, as the prose says"),
    ],
}


def book_chapters():
    return sorted(BOOK.glob("[0-9]*.md"))


@pytest.fixture(scope="module")
def everything_normalised():
    """Every Python file the book could be quoting, normalised once."""
    sources = []
    patterns = ["src/agentpath/**/*.py", "lessons/*/*.py", "foundations/*/*.py", "training/*/*.py"]
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if "__pycache__" not in str(path):
                sources.append(normalise(path.read_text(encoding="utf-8")))
    return sources


@pytest.mark.parametrize("chapter", book_chapters(), ids=lambda p: p.name)
def test_a_definition_the_book_shows_whole_exists_somewhere(chapter, everything_normalised):
    """The book is where this class of bug did the most damage.

    The chapters sit beside the code they quote and still drifted twice.
    The book sits beside nothing, quotes code from the whole project, and
    had no check at all, which is how it kept teaching a fingerprint that
    folds letter case for two weeks after that folding was removed as a
    bug. Every definition the book shows whole has to exist somewhere in
    the project in that shape.
    """
    defined = set()
    for source in everything_normalised:
        defined |= set(DEFINITION.findall(source))

    current = {}
    for block in BLOCK.findall(chapter.read_text(encoding="utf-8")):
        if is_partial(block):
            continue
        if any(marker in block for marker, _ in BOOK_ILLUSTRATIONS.get(chapter.name, [])):
            continue
        for name, quoted in definitions(normalise(block)):
            if name not in defined or len(quoted.splitlines()) < 2:
                continue
            matched = any(quoted in source for source in everything_normalised)
            current[name] = current.get(name, False) or matched

    stale = sorted(name for name, matched in current.items() if not matched)
    assert not stale, (
        f"book/{chapter.name} shows these whole and no file in the project has "
        f"that shape. The code moved on and the book did not. {stale}"
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
    # Within its own track. The first foundations folder has nothing before
    # it, and the first lesson does not inherit from the last foundation.
    folders = sorted(p for p in lesson.parent.iterdir() if p.is_dir())
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
