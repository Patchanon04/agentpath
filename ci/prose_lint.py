"""Fail the build when learner facing prose contains banned characters.

The project style rules ban the em dash, emoji and the colon in ordinary
sentences. People forget rules like this, so a machine enforces them.

The colon needs more care than the other two, because a colon is ordinary
inside code, inside a URL and inside a time. Fenced blocks and inline code
are stripped before the line is judged, and lines that are clearly a table
or a link are left alone.
"""
import re
import sys
from pathlib import Path

EM_DASH = "—"
EMOJI = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U0001f1e6-\U0001f1ff"
    "\U00002600-\U000027bf"
    "\U0000fe0f"
    "]"
)

# Inline code is exempt, so it is removed before a line is judged.
INLINE_CODE = re.compile(r"`[^`]*`")

# A colon that follows an ordinary word and is followed by a space or the
# end of the line. This deliberately misses a colon inside a URL, a time,
# a Windows path and a markdown table divider, all of which are fine.
COLON_IN_PROSE = re.compile(r"[A-Za-z฀-๿,\)][ ]?:(\s|$)")


def strip_code(line):
    """Remove inline code spans so their colons do not count as prose."""
    return INLINE_CODE.sub("", line)


def find_violations(paths, check_colons=True):
    """Return a list of (path, line_number, reason) for every banned thing."""
    violations = []
    for path in paths:
        in_code = False
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if EM_DASH in line:
                violations.append((path, number, "em dash"))
            if EMOJI.search(line):
                violations.append((path, number, "emoji"))
            if in_code or not check_colons:
                continue
            prose = strip_code(line)
            if COLON_IN_PROSE.search(prose):
                violations.append((path, number, "colon in prose"))
    return violations


def is_learner_facing(path, root):
    """Say whether a learner ever reads this file.

    The colon rule exists so that the prose a learner reads is consistent.
    The design document and the implementation plans are working notes for
    whoever maintains the course, written in a different language and never
    linked from a chapter, so the rule does not reach them. The ban on the
    em dash and on emoji still applies everywhere, because those two are
    about the project having one voice.
    """
    parts = path.relative_to(root).parts
    return not (parts[:2] == ("docs", "plans") or parts[:2] == ("docs", "specs"))


def main():
    root = Path(__file__).resolve().parents[1]
    files = [p for p in root.rglob("*.md") if ".venv" not in p.parts]
    violations = []
    for path in files:
        violations.extend(
            find_violations([path], check_colons=is_learner_facing(path, root))
        )
    for path, number, reason in violations:
        print(f"{path.relative_to(root)}:{number} contains {reason}")
    if violations:
        print(f"\n{len(violations)} prose violations found")
        return 1
    checked = sum(1 for p in files if is_learner_facing(p, root))
    print(f"prose lint clean across {len(files)} markdown files")
    print(f"{checked} of them were checked for colons as well")
    return 0


if __name__ == "__main__":
    sys.exit(main())
