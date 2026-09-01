"""Tools that let the agent find things instead of being told where they are.

This is the part people are surprised by. A coding agent does not need a
vector database to work on a code base. It needs the same two tools a human
uses, which are a way to find files by name and a way to find text inside
them. Lesson 16 in part 3 explains when that stops being enough.
"""
import fnmatch
import re
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import SKIP_DIRECTORIES, truncate

MAX_RESULTS = 200


def _walk(root: Path):
    """Yield every file under root, skipping directories nobody wants searched."""
    for path in root.rglob("*"):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if path.is_file():
            yield path


def search_tools(root) -> list[Tool]:
    root = Path(root).resolve()

    def glob_files(pattern):
        matches = []
        for path in _walk(root):
            relative = path.relative_to(root).as_posix()
            if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern):
                matches.append(relative)
        if not matches:
            return f"no files match {pattern}"
        return truncate("\n".join(sorted(matches)[:MAX_RESULTS]))

    def grep_files(pattern, glob="*"):
        try:
            expression = re.compile(pattern)
        except re.error as error:
            return f"Error: {pattern} is not a valid regular expression ({error})"
        hits = []
        for path in _walk(root):
            relative = path.relative_to(root).as_posix()
            if not (fnmatch.fnmatch(relative, glob) or fnmatch.fnmatch(path.name, glob)):
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
        ),
    ]
