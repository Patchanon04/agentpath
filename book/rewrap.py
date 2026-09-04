"""Re-wrap only the paragraphs an edit left with an over-long line.

The book renders a line break between two Thai characters as nothing and every
other break as a space, which is what build_book.join_wrapped does. Checked
against the text itself, 418 of these breaks have a run that appears joined
elsewhere in the book and only 17 have one that appears spaced, so the rule
matches how the source was written.

That rule decides where a break may go. A break at a real space is safe only
when one side is not Thai, otherwise the space would disappear on render. A
break inside a Thai run costs nothing, so those are the break points to use,
as long as the break does not land in front of a mark that cannot start a
word or behind a vowel that cannot end one.

wrap_paragraph asserts the rendered paragraph is unchanged, so a wrap that
would alter a single character fails rather than ships.

Run it from the repo root. Name the files to limit it to those, which matters
when more than one person is editing the book at once.
"""

import re
import sys
from pathlib import Path

THAI = "฀-๿"
NEVER_STARTS = "ะ-ฺๅ-๎"
NEVER_ENDS = "เ-ไ"
WIDTH = 80
TOO_LONG = 92

thai = re.compile(f"[{THAI}]").match


def render(lines):
    out = lines[0]
    for line in lines[1:]:
        joined = thai(out[-1:]) and thai(line[:1])
        out += line if joined else " " + line
    return out


def breakable(text, i):
    """Whether a line may end just before index i."""
    if i <= 0 or i >= len(text):
        return False
    before, after = text[i - 1], text[i]
    if after == " ":
        return False
    if before == " ":
        # The space becomes the break, so it must render back as a space.
        return not (thai(text[i - 2 : i - 1]) and thai(after))
    if not (thai(before) and thai(after)):
        return False
    return not re.match(f"[{NEVER_STARTS}]", after) and not re.match(f"[{NEVER_ENDS}]", before)


def wrap_paragraph(lines):
    text = render(lines)
    out, start = [], 0
    while len(text) - start > WIDTH:
        window = range(start + WIDTH, start + 20, -1)
        # A break at a space is always preferable. Splitting a Thai run is
        # correct for the book but reads as a broken word in the source and
        # anywhere else that joins soft breaks with a space.
        cut = next((i for i in window if text[i - 1] == " " and breakable(text, i)), None)
        if cut is None:
            cut = next((i for i in window if breakable(text, i)), None)
        if cut is None:
            break
        out.append(text[start:cut].rstrip())
        start = cut
    out.append(text[start:])
    assert render(out) == text, "wrapping changed the text"
    return out


def main():
    """Re-wrap the files named on the command line, or the whole book."""
    named = [Path(a) for a in sys.argv[1:]]
    total = 0
    for path in named or sorted(Path("book").glob("*.md")):
        lines = path.read_text(encoding="utf-8").split("\n")
        out, i, fence, touched = [], 0, False, 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("```"):
                fence = not fence
                out.append(line)
                i += 1
                continue
            if fence or not line.strip() or line.startswith(("#", "|", ">")):
                out.append(line)
                i += 1
                continue
            para = []
            listish = re.match(r"([-*] |\d+\. |\s)", line)
            stops = ("```", "#", "|")
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(stops):
                if para and re.match(r"([-*] |\d+\. )", lines[i]):
                    break
                para.append(lines[i])
                i += 1
            if listish or not any(len(x) > TOO_LONG for x in para):
                out.extend(para)
                continue
            out.extend(wrap_paragraph(para))
            touched += 1
        if touched:
            path.write_text("\n".join(out), encoding="utf-8", newline="\n")
            print(f"  {path.name:34} {touched}")
            total += touched
    print(f"{total} paragraphs re-wrapped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
