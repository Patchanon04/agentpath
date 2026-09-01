"""Tools that touch real files.

Two new ideas arrive in this file. The first is that every path the model
sends us goes through one gate called resolve_inside, so the rules about
what may be touched live in one place instead of being repeated in four
functions. The second is that everything a tool returns is sent to the model
provider on this request and on every later request in the conversation,
which is why we truncate output and why we refuse to read credential files.
"""
import os
from pathlib import Path

MAX_OUTPUT = 4000
SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache"}
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "credentials"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}

WORKSPACE = Path(os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()


class WorkspaceError(Exception):
    """Raised when a tool asks for a path it is not allowed to have."""


def looks_like_a_secret(name):
    lowered = name.lower()
    if lowered in SECRET_NAMES or lowered.startswith(".env."):
        return True
    return Path(lowered).suffix in SECRET_SUFFIXES


def resolve_inside(path):
    """Turn a path from the model into a real path, or refuse it.

    Two separate refusals happen here. The first stops the agent from
    reaching outside its workspace at all, which covers both parent
    directory escapes such as ../../etc/passwd and absolute paths. The
    second stops it from reading credential files that happen to live inside
    the workspace, because once a key is in the conversation it is sent to
    the model provider on every later call and you cannot take it back.
    """
    candidate = (WORKSPACE / Path(path)).resolve()
    if candidate != WORKSPACE and not candidate.is_relative_to(WORKSPACE):
        raise WorkspaceError(f"{path} is outside the workspace")
    if looks_like_a_secret(candidate.name):
        raise WorkspaceError(
            f"this tool refuses to read {candidate.name} because credential files "
            "must not enter the conversation"
        )
    return candidate


def truncate(text, limit=MAX_OUTPUT):
    """Keep tool output small enough that it does not eat the context window."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated, {len(text) - limit} more characters]"


def read_file(path):
    target = resolve_inside(path)
    if not target.is_file():
        return f"Error: {path} does not exist"
    return truncate(target.read_text(encoding="utf-8", errors="replace"))


def write_file(path, content):
    target = resolve_inside(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {path}"


def edit_file(path, old, new):
    """Replace one exact piece of text, but only when the match is unique.

    A replace that hits three places when the model meant one is a silent
    corruption. Refusing an ambiguous edit and asking for more surrounding
    context turns that disaster into a message the model can act on.
    """
    target = resolve_inside(path)
    if not target.is_file():
        return f"Error: {path} does not exist"
    text = target.read_text(encoding="utf-8")
    found = text.count(old)
    if found == 0:
        return (
            f"Error: the text to replace was not found in {path}. "
            "Read the file again and copy the exact text including whitespace."
        )
    if found > 1:
        return (
            f"Error: the text to replace appears {found} times in {path}. "
            "Include more surrounding lines so the match is unique."
        )
    target.write_text(text.replace(old, new), encoding="utf-8")
    return f"Edited {path}"


def list_files(path="."):
    target = resolve_inside(path)
    if not target.is_dir():
        return f"Error: {path} is not a directory"
    names = []
    for entry in sorted(target.iterdir()):
        if entry.name in SKIP_DIRECTORIES:
            continue
        names.append(entry.name + "/" if entry.is_dir() else entry.name)
    return truncate("\n".join(names) or "(empty directory)")


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write a whole file, creating it if needed. Use edit_file instead when "
                "you only want to change part of an existing file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "content": {"type": "string", "description": "The complete new contents"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace one exact piece of text in a file. The old text must appear "
                "exactly once, so include enough surrounding lines to make it unique."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "old": {"type": "string", "description": "The exact text to replace"},
                    "new": {"type": "string", "description": "The text to put in its place"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the files and directories in one directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory relative to the workspace",
                    }
                },
                "required": [],
            },
        },
    },
]

FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
}


def run(name, arguments):
    """Run one tool by name and return its result as a string."""
    function = FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**arguments))
    except WorkspaceError as error:
        return f"Error: {error}"
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"


# Lesson 08 adds the shell tool. Everything above is unchanged from lesson 07.

import subprocess  # noqa: E402

SHELL_TIMEOUT = 60


CANCELLATION = None


def run_shell(command):
    # The confirmation that used to live here moved to permissions.py in
    # lesson 12. Asking in both places would ask the same question twice,
    # and a tool that asks its own questions cannot be reused by anything
    # that is not a terminal.
    #
    # The cancellation check is here as well as in the loop because a command
    # started after the person pressed the interrupt key is exactly the
    # failure a cancellation token exists to prevent.
    if CANCELLATION is not None and CANCELLATION.cancelled:
        return "Cancelled before the command started."
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            timeout=SHELL_TIMEOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"Error: the command timed out after {SHELL_TIMEOUT} seconds"
    parts = []
    if completed.stdout:
        parts.append(completed.stdout)
    if completed.stderr:
        parts.append(completed.stderr)
    if completed.returncode != 0:
        parts.append(f"[exit code {completed.returncode}]")
    return truncate("\n".join(parts) or "[no output]")


SCHEMAS.append(
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a shell command in the workspace directory and return its output. "
                "The user is asked to approve the command before it runs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line to run"}
                },
                "required": ["command"],
            },
        },
    }
)

FUNCTIONS["run_shell"] = run_shell


# Lesson 09 adds the search tools. Everything above is unchanged from lesson 08.

import fnmatch  # noqa: E402
import re  # noqa: E402

MAX_RESULTS = 200


def path_matches(relative, name, pattern):
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


def _walk():
    """Yield every file in the workspace that a search is allowed to look at.

    Two exclusions happen here. Directories such as .venv are skipped because
    searching them buries the real answer in thousands of irrelevant hits.
    Credential files are skipped because otherwise search would be a way
    around the refusal in read_file, and a rule that one tool honours and
    another ignores is not a rule at all.
    """
    for path in WORKSPACE.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(WORKSPACE)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
        if looks_like_a_secret(path.name):
            continue
        yield path


def glob_files(pattern):
    matches = []
    for path in _walk():
        relative = path.relative_to(WORKSPACE).as_posix()
        if path_matches(relative, path.name, pattern):
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
    for path in _walk():
        relative = path.relative_to(WORKSPACE).as_posix()
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


SCHEMAS.extend(
    [
        {
            "type": "function",
            "function": {
                "name": "glob_files",
                "description": (
                    "Find files by name pattern, for example **/*.py or test_*.py. "
                    "Use this when you know roughly what a file is called."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "A glob pattern"}
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_files",
                "description": (
                    "Search the text inside files using a regular expression and return "
                    "matching lines with their file name and line number."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "A regular expression"},
                        "glob": {
                            "type": "string",
                            "description": "Only search files matching this glob",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
    ]
)

FUNCTIONS["glob_files"] = glob_files
FUNCTIONS["grep_files"] = grep_files


# Lesson 16 adds retrieval. Everything above is unchanged from lesson 15.

from retrieval import SCHEMA as RETRIEVAL_SCHEMA  # noqa: E402
from retrieval import search_notes  # noqa: E402

SCHEMAS.append(RETRIEVAL_SCHEMA)
FUNCTIONS['search_notes'] = search_notes


# Lesson 19 lets tools arrive from another process at run time.


def register_mcp(schemas, functions):
    """Add tools discovered from an MCP server to the ones we wrote ourselves.

    Nothing else changes. The agent loop, the permission check and the
    registry all treat these exactly like read_file.
    """
    SCHEMAS.extend(schemas)
    FUNCTIONS.update(functions)


# Tools we did not write are never on the safe list, so every one of them
# goes through the permission gate from lesson 12.
