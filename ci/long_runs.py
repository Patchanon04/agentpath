"""Report long stretches of Thai with no space in them.

This book has no commas and no full stops in Thai prose. A space is the only
thing marking where one thought ends and the next begins, so a run of sixty or
eighty characters without one is usually two sentences that have grown
together, and it reads as a wall.

The run is measured on the rendered paragraph, not on the source line, because
a line break between two Thai characters renders as nothing. A boundary that
sits exactly on such a break disappears when the book is built, which is one
of the two ways these runs appear. The other is prose that was simply written
without the space.

Run it from the repo root. Pass a threshold to change the default of 70.
"""

import re
import sys
from pathlib import Path

THAI = "฀-๿"
DEFAULT = 70


def join_wrapped(lines):
    """The same join the book build uses. Thai to Thai closes up."""
    out = lines[0]
    for line in lines[1:]:
        both_thai = re.search(f"[{THAI}]$", out) and re.match(f"[{THAI}]", line)
        out += line if both_thai else " " + line
    return out


def paragraphs(path):
    """Every prose paragraph as (first source line number, rendered text)."""
    found, para, start, fence = [], [], 0, False
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if line.startswith("```"):
            fence = not fence
            line = ""
        if fence or line.startswith(("#", "|")):
            line = ""
        if line.strip():
            if not para:
                start = number
            para.append(line.strip())
        elif para:
            found.append((start, join_wrapped(para)))
            para = []
    if para:
        found.append((start, join_wrapped(para)))
    return found


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    runs = []
    for path in sorted(Path("book").glob("*.md")):
        if path.name in ("README.md", "STYLE.md"):
            continue
        for start, text in paragraphs(path):
            for match in re.finditer(f"[{THAI}]{{{limit},}}", text):
                runs.append((len(match.group()), path.name, start, match.group()))

    runs.sort(reverse=True)
    print(f"{len(runs)} runs of {limit} Thai characters or more with no space")
    for length, name, start, text in runs:
        print(f"  {name}:{start} ({length})")
        print(f"      {text}")
    return 1 if runs else 0


if __name__ == "__main__":
    sys.exit(main())
