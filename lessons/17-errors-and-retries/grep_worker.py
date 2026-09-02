"""The part of grep_files that runs in its own process.

It lives in a separate file so it can be killed. A regular expression that
takes exponential time cannot be interrupted from inside the process running
it, so the only way to put a limit on a search is to run it somewhere that
can be shut down from outside.
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

MAX_RESULTS = 200
MAX_LINE = 2000
SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache"}
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "credentials"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def looks_like_a_secret(name):
    lowered = name.lower()
    if lowered in SECRET_NAMES or lowered.startswith(".env."):
        return True
    return Path(lowered).suffix in SECRET_SUFFIXES


def allowed(root, relative):
    """The same rule as resolve_inside, repeated here because this process
    does not import tools.py. A link inside the workspace must not be a way
    out of it, and the name of a link never tells you where it points."""
    candidate = (root / relative).resolve()
    if candidate != root and not candidate.is_relative_to(root):
        return False
    return not looks_like_a_secret(candidate.name)


def path_matches(relative, name, pattern):
    if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern):
        return True
    return pattern.startswith("**/") and fnmatch.fnmatch(relative, pattern[3:])


def scan(root, pattern, glob):
    expression = re.compile(pattern)
    root = Path(root).resolve()
    hits = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
        if not allowed(root, relative):
            continue
        as_posix = relative.as_posix()
        if not path_matches(as_posix, path.name, glob):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if expression.search(line[:MAX_LINE]):
                hits.append(f"{as_posix}:{number}: {line.strip()[:200]}")
                if len(hits) >= MAX_RESULTS:
                    return hits
    return hits


if __name__ == "__main__":
    question = json.loads(sys.stdin.read())
    print(json.dumps(scan(question["root"], question["pattern"], question["glob"])))
