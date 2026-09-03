"""Report technical terms that are explained two different ways.

The book and the lessons each explain a term in Thai the first time it turns
up. A reader who meets `context window` in the book and again in a lesson
should meet the same sentence, not two attempts at it. Nothing else checks
this, and the wording drifts every time someone edits one side.

Run it from the repo root. It prints the terms that disagree and exits
non-zero, so it can be wired into CI later if that is wanted.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# An English term, then a parenthesis that opens with Thai.
GLOSS = re.compile(r"([A-Za-z][A-Za-z0-9 ._\-]{1,28}?)\s*\(([฀-๿][^)]{3,150})\)")

# Terms whose parenthesis is an aside rather than a definition.
SKIP = {"e.g", "i.e"}

# Terms that really do carry two senses in this course. Each entry says why,
# because the whole point of the check is that a second wording is normally a
# mistake.
TWO_SENSES = {
    "corpus": "the text a model trains on, and the documents a search runs over",
    "vector": "a row of numbers in the foundations, and an embedding in retrieval",
}


def glosses(path):
    """Every gloss in one file, outside fenced code."""
    found = []
    fence = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        for match in GLOSS.finditer(line):
            term = match.group(1).strip().lower()
            if term and term not in SKIP:
                found.append((term, " ".join(match.group(2).split())))
    return found


def main():
    root = Path(".")
    sources = sorted(root.glob("book/*.md")) + sorted(root.glob("lessons/*/README.th.md"))
    wordings = defaultdict(set)
    where = defaultdict(set)
    for path in sources:
        for term, text in glosses(path):
            wordings[term].add(text)
            where[term].add(path.as_posix())

    split = {t: v for t, v in wordings.items() if len(v) > 1 and t not in TWO_SENSES}
    print(f"{len(wordings)} terms glossed across {len(sources)} files")
    for term, why in TWO_SENSES.items():
        if len(wordings.get(term, ())) > 1:
            print(f"  {term} is allowed two wordings, {why}")
    if not split:
        print("every other term is explained one way")
        return 0

    print(f"{len(split)} explained more than one way\n")
    for term in sorted(split, key=lambda t: -len(split[t])):
        print(f"  {term}")
        for text in sorted(split[term]):
            print(f"      {text}")
        print(f"      in {len(where[term])} files")
    return 1


if __name__ == "__main__":
    sys.exit(main())
