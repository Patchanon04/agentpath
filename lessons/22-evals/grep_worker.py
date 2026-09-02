"""The part of grep_files that runs in its own process.

It lives in a separate file so it can be killed. A regular expression that
takes exponential time cannot be interrupted from inside the process running
it, so the only way to put a limit on a search is to run it somewhere that
can be shut down from outside.

The rules about which files may be searched are imported from tools.py
rather than copied here. An earlier version of this file had its own copy of
the secret names and the skip list, which is exactly what lesson 09 tells
you not to do. Two copies agree until the day somebody edits one.
"""
import json
import sys
from pathlib import Path

# Isolated mode removes every directory from the import path, including the
# one this file lives in, so the lesson folder has to be put back by hand.
# Only this folder, and never the folder the agent is working in, which is
# the whole point of starting isolated in the first place.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tools  # noqa: E402


def scan(root, pattern, glob):
    """Search every file the workspace rules allow."""
    import re

    expression = re.compile(pattern)
    root = Path(root).resolve()
    hits = []
    for path in tools._walk():
        relative = path.relative_to(root).as_posix()
        if not tools.path_matches(relative, path.name, glob):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if expression.search(line[: tools.MAX_LINE]):
                hits.append(f"{relative}:{number}: {line.strip()[:200]}")
                if len(hits) >= tools.MAX_RESULTS:
                    return hits
    return hits


if __name__ == "__main__":
    question = json.loads(sys.stdin.read())
    print(json.dumps(scan(question["root"], question["pattern"], question["glob"])))
