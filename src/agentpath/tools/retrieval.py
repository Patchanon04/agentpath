"""Retrieval, built the small way, so you can see what it actually is.

Retrieval means finding the parts of a body of text that are most likely to
answer a question. People often assume that requires embeddings and a vector
database. It does not. It requires a way to score a piece of text against a
question, and the scoring below is about twenty lines.

The scoring is term overlap weighted by how rare each word is. A word that
appears in every document tells you nothing about which document you want,
so it counts for almost nothing. A word that appears in one document is a
strong signal, so it counts for a lot. That single idea is most of what
classical search engines do, and it is enough to be genuinely useful.

What this cannot do is match meaning when the words differ. A question about
refunds will not find a document that only says money back. That is exactly
the gap embeddings fill, and it is the honest reason to reach for them. It
is not a reason to reach for them first.
"""
import math
import re
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import SKIP_DIRECTORIES, truncate
from agentpath.tools.workspace import WorkspaceError, resolve_inside

WORD = re.compile(r"[A-Za-z0-9_]+")
TOP_RESULTS = 5


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def passages_in(path: Path) -> list[tuple[int, str]]:
    """Split a file into paragraphs, keeping the line each one starts on.

    Paragraphs are used rather than fixed size chunks because a paragraph is
    a unit somebody wrote on purpose. Cutting every four hundred characters
    splits sentences in half and produces passages that read as nonsense.
    """
    passages = []
    line_number = 1
    for block in path.read_text(encoding="utf-8", errors="replace").split("\n\n"):
        if block.strip():
            passages.append((line_number, block.strip()))
        line_number += block.count("\n") + 2
    return passages


def build_index(root: Path, pattern="*.md") -> list[dict]:
    """Read the documents once and remember their words."""
    index = []
    for path in sorted(root.rglob(pattern)):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
        try:
            # The same gate every other tool uses. See _walk in search.py for
            # why filtering on the name alone is not enough.
            resolve_inside(root, relative)
        except WorkspaceError:
            continue
        for line_number, text in passages_in(path):
            index.append(
                {
                    "source": f"{path.relative_to(root).as_posix()}:{line_number}",
                    "text": text,
                    "words": set(words(text)),
                }
            )
    return index


def score(question_words: set, entry: dict, rarity: dict) -> float:
    return sum(rarity.get(word, 0.0) for word in question_words & entry["words"])


def retrieval_tools(root, pattern="*.md") -> list[Tool]:
    root = Path(root).resolve()

    def search_notes(question, limit=TOP_RESULTS):
        index = build_index(root, pattern)
        if not index:
            return f"there are no {pattern} documents to search"

        appearances: dict[str, int] = {}
        for entry in index:
            for word in entry["words"]:
                appearances[word] = appearances.get(word, 0) + 1
        rarity = {
            word: math.log(len(index) / count) for word, count in appearances.items()
        }

        question_words = set(words(question))
        ranked = sorted(
            index, key=lambda entry: score(question_words, entry, rarity), reverse=True
        )
        best = [entry for entry in ranked if score(question_words, entry, rarity) > 0]
        if not best:
            return f"nothing in the documents mentions any of the words in {question!r}"

        parts = []
        for entry in best[: int(limit)]:
            parts.append(f"{entry['source']}\n{entry['text']}")
        return truncate("\n\n".join(parts))

    return [
        Tool(
            name="search_notes",
            description=(
                "Search the project documents for passages related to a question, and "
                "return them with the file and line they came from. Use this for prose. "
                "For code, grep_files is usually better because names are exact."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "What you want to know"},
                    "limit": {"type": "integer", "description": "How many passages to return"},
                },
                "required": ["question"],
            },
            fn=search_notes,
            safe=True,
        )
    ]
