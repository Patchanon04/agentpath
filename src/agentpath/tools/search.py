"""Tools that let the agent find things instead of being told where they are.

This is the part people are surprised by. A coding agent does not need a
vector database to work on a code base. It needs the same two tools a human
uses, which are a way to find files by name and a way to find text inside
them. Lesson 16 in part 3 explains when that stops being enough.
"""
import fnmatch
import re
import time
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import SKIP_DIRECTORIES, truncate
from agentpath.tools.workspace import WorkspaceError, resolve_inside

MAX_RESULTS = 200
SEARCH_SECONDS = 10

# Two quantifiers stacked on one group, as in (a+)+ or (a*)*, is the shape
# that makes a regular expression take exponential time. A model writing one
# by accident would otherwise wedge the whole process, and no cancellation
# token can help because the matching never returns to check it.
NESTED_QUANTIFIER = re.compile(r"\([^()]*[+*][^()]*\)\s*[+*{]")


def _walk(root: Path):
    """Yield every file under root that a search is allowed to look at.

    Two exclusions happen here. Directories such as .venv are skipped because
    searching them buries the real answer in thousands of irrelevant hits.
    Credential files are skipped because otherwise search would be a way
    around the refusal in read_file, and a rule that one tool honours while
    another ignores it is not a rule at all.

    The skip list is checked against the path inside the workspace rather
    than the whole path, because a project that happens to live in a folder
    called node_modules should still be searchable.

    Every candidate goes through resolve_inside rather than being filtered
    here. That matters because rglob follows symlinks and Windows junctions,
    so a link planted inside the workspace would otherwise let search read
    files the workspace was drawn to exclude. Filtering on the name of the
    link never sees the name of the target.
    """
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
        try:
            resolve_inside(root, relative)
        except WorkspaceError:
            continue
        yield path


def path_matches(relative: str, name: str, pattern: str) -> bool:
    """Decide whether one file matches a glob the way a person would expect.

    Three attempts are made because fnmatch is stricter than people are. The
    pattern is tried against the path inside the workspace, then against the
    bare file name so that main.py works from anywhere, and then with a
    leading star star slash removed so that a pattern like **/*.py also
    finds files sitting at the top level. Without that third attempt the
    most common pattern a model writes silently misses every file that is
    not inside a subdirectory.
    """
    if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern):
        return True
    return pattern.startswith("**/") and fnmatch.fnmatch(relative, pattern[3:])


def search_tools(root) -> list[Tool]:
    root = Path(root).resolve()

    def glob_files(pattern):
        found = []
        for path in _walk(root):
            relative = path.relative_to(root).as_posix()
            if path_matches(relative, path.name, pattern):
                found.append(relative)
        if not found:
            return f"no files match {pattern}"
        return truncate("\n".join(sorted(found)[:MAX_RESULTS]))

    def grep_files(pattern, glob="*"):
        try:
            expression = re.compile(pattern)
        except re.error as error:
            return f"Error: {pattern} is not a valid regular expression ({error})"
        if NESTED_QUANTIFIER.search(pattern):
            return (
                f"Error: {pattern} has one repeat wrapped in another, which can take "
                "effectively forever to match. Write it without the nested repeat."
            )
        deadline = time.monotonic() + SEARCH_SECONDS
        hits = []
        for path in _walk(root):
            if time.monotonic() > deadline:
                hits.append(f"[search stopped after {SEARCH_SECONDS} seconds]")
                break
            relative = path.relative_to(root).as_posix()
            if not path_matches(relative, path.name, glob):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if expression.search(line):
                    hits.append(f"{relative}:{number}: {line.strip()[:200]}")
                    if len(hits) >= MAX_RESULTS:
                        break
            if len(hits) >= MAX_RESULTS:
                break
        if not hits:
            return f"no matches for {pattern}"
        return truncate("\n".join(hits))

    return [
        Tool(
            name="glob_files",
            description=(
                "Find files by name pattern, for example **/*.py or test_*.py. "
                "Use this when you know roughly what a file is called."
            ),
            parameters={
                "type": "object",
                "properties": {"pattern": {"type": "string", "description": "A glob pattern"}},
                "required": ["pattern"],
            },
            fn=glob_files,
            safe=True,
        ),
        Tool(
            name="grep_files",
            description=(
                "Search the text inside files using a regular expression and return "
                "matching lines with their file name and line number."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "A regular expression"},
                    "glob": {
                        "type": "string",
                        "description": "Only search files matching this glob, for example *.py",
                    },
                },
                "required": ["pattern"],
            },
            fn=grep_files,
            safe=True,
        ),
    ]
