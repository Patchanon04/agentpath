"""Tools that let the agent find things instead of being told where they are.

This is the part people are surprised by. A coding agent does not need a
vector database to work on a code base. It needs the same two tools a human
uses, which are a way to find files by name and a way to find text inside
them. Lesson 16 in part 3 explains when that stops being enough.
"""
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import SKIP_DIRECTORIES, truncate
from agentpath.tools.workspace import WorkspaceError, resolve_inside

MAX_RESULTS = 200
SEARCH_SECONDS = 5

# A line longer than this is truncated before matching. Catastrophic
# backtracking grows with the length of the input, so bounding the input is
# the one guard that works whatever the pattern turns out to be.
MAX_LINE = 2000

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
            re.compile(pattern)
        except re.error as error:
            return f"Error: {pattern} is not a valid regular expression ({error})"
        if NESTED_QUANTIFIER.search(pattern):
            return (
                f"Error: {pattern} has one repeat wrapped in another, which can take "
                "effectively forever to match. Write it without the nested repeat."
            )

        # The search runs in a separate process. Two earlier attempts at
        # this did not work and both are worth knowing about. Checking a
        # deadline between lines never gets a turn, because one line is
        # enough to go exponential and nothing interrupts a regular
        # expression that is already running. Moving it to a thread does
        # not help either, because matching does not release the global
        # interpreter lock, so the thread waiting on the deadline cannot
        # run until the matching it is waiting on has finished.
        #
        # A separate process can simply be killed, which is the only thing
        # that actually works. The cost is about a tenth of a second of
        # start up on every search.
        request = json.dumps({"root": str(root), "pattern": pattern, "glob": glob})
        try:
            # Isolated on purpose, and this is the important part rather
            # than a detail. Running a module with -m puts the current
            # directory first on the import path, and the current
            # directory is the workspace. A file the agent wrote there
            # called json.py or types.py would then be imported and run by
            # this child before the search starts, with no permission
            # check anywhere, because searching is a safe tool. -I removes
            # that directory from the path and ignores the environment
            # variables that could put it back.
            completed = subprocess.run(
                [sys.executable, "-I", "-m", "agentpath.tools.search"],
                input=request,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=SEARCH_SECONDS,
                cwd=str(Path(__file__).resolve().parent),
            )
        except OSError as error:
            # The child could not be started at all, which is a different
            # thing from the search failing. Saying so, and naming the tool,
            # is what lets the model try something else instead of repeating
            # a search that can never run.
            return f"Error: the search could not be started. {error}"
        except subprocess.TimeoutExpired:
            return (
                f"Error: searching for {pattern} took longer than {SEARCH_SECONDS} "
                "seconds and was given up on. Try a simpler pattern, or narrow the "
                "search with the glob argument."
            )
        if completed.returncode != 0:
            return f"Error: the search failed. {completed.stderr.strip()[:200]}"
        hits = json.loads(completed.stdout or "[]")
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


def scan(root, pattern, glob):
    """Do the searching. Runs in its own process so it can be killed."""
    expression = re.compile(pattern)
    root = Path(root)
    hits = []
    for path in _walk(root):
        relative = path.relative_to(root).as_posix()
        if not path_matches(relative, path.name, glob):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if expression.search(line[:MAX_LINE]):
                hits.append(f"{relative}:{number}: {line.strip()[:200]}")
                if len(hits) >= MAX_RESULTS:
                    return hits
    return hits


if __name__ == "__main__":
    question = json.loads(sys.stdin.read())
    print(json.dumps(scan(question["root"], question["pattern"], question["glob"])))
