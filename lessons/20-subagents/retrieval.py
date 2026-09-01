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
refunds will not find a document that only says money back, and a question
about dispatch will not find a document that says dispatched. That is
exactly the gap embeddings fill, and it is the honest reason to reach for
them. It is not a reason to reach for them first.
"""
import math
import os
import re
from pathlib import Path

# Imported inside the functions rather than at the top of the file. tools.py
# imports this module to register the tool, so importing it back here at
# import time would be a circle and neither module could be loaded first.
MAX_OUTPUT = 4000

WORD = re.compile(r"[A-Za-z0-9_]+")
TOP_RESULTS = 5
DEFAULT_PATTERN = "*.md"


def words(text):
    return WORD.findall(text.lower())


def _from_tools():
    """Borrow the workspace rules without importing at module level."""
    import tools

    return tools.SKIP_DIRECTORIES, tools.looks_like_a_secret, tools.truncate


def passages_in(path):
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


def build_index(root, pattern=DEFAULT_PATTERN):
    """Read the documents once and remember their words."""
    skip, is_secret, _ = _from_tools()
    index = []
    for path in sorted(root.rglob(pattern)):
        if any(part in skip for part in path.relative_to(root).parts):
            continue
        if is_secret(path.name):
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


def score(question_words, entry, rarity):
    return sum(rarity.get(word, 0.0) for word in question_words & entry["words"])


def search_notes(question, limit=TOP_RESULTS, root=None, pattern=DEFAULT_PATTERN):
    root = Path(root or os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()
    index = build_index(root, pattern)
    if not index:
        return f"there are no {pattern} documents to search"

    appearances = {}
    for entry in index:
        for word in entry["words"]:
            appearances[word] = appearances.get(word, 0) + 1
    rarity = {word: math.log(len(index) / count) for word, count in appearances.items()}

    question_words = set(words(question))
    ranked = sorted(index, key=lambda entry: score(question_words, entry, rarity), reverse=True)
    best = [entry for entry in ranked if score(question_words, entry, rarity) > 0]
    if not best:
        return f"nothing in the documents mentions any of the words in {question!r}"

    _, _, truncate = _from_tools()
    parts = [f"{entry['source']}\n{entry['text']}" for entry in best[: int(limit)]]
    return truncate("\n\n".join(parts))


SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_notes",
        "description": (
            "Search the project documents for passages related to a question, and "
            "return them with the file and line they came from. Use this for prose. "
            "For code, grep_files is usually better because names are exact."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "What you want to know"},
                "limit": {"type": "integer", "description": "How many passages to return"},
            },
            "required": ["question"],
        },
    },
}
