"""Fail the build when learner facing prose contains banned characters.

The project style rules ban the em dash and emoji in every markdown file.
People forget rules like this, so a machine enforces it.
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


def find_violations(paths):
    """Return a list of (path, line_number, reason) for every banned character."""
    violations = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if EM_DASH in line:
                violations.append((path, number, "em dash"))
            if EMOJI.search(line):
                violations.append((path, number, "emoji"))
    return violations


def main():
    root = Path(__file__).resolve().parents[1]
    files = [p for p in root.rglob("*.md") if ".venv" not in p.parts]
    violations = find_violations(files)
    for path, number, reason in violations:
        print(f"{path.relative_to(root)}:{number} contains {reason}")
    if violations:
        print(f"\n{len(violations)} prose violations found")
        return 1
    print(f"prose lint clean across {len(files)} markdown files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
