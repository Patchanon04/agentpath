"""Meaning as direction.

A word becomes a list of numbers, and two words that are used the same way
end up pointing the same way. That is the idea under every embedding
model, every vector database, and the retrieval chapter of the book. The
version here is the oldest form of it, count the neighbours, and it is
enough to see why cosine similarity is the comparison everybody uses.
"""
import numpy as np

# Built so that some words share company. cat and dog do the same things,
# agent and model do the same things, and nothing else overlaps much.
CORPUS = """
the cat sat on the mat . the dog sat on the mat . the cat ate the fish .
the dog ate the bone . the cat sleeps all day . the dog sleeps all day .
the cat chased the bird . the cat sat on the sofa . the cat ate the fish .
the agent reads the file . the model reads the file . the agent runs the
tool . the model runs the tool . the agent writes the answer . the model
writes the answer . the agent reads the result . the agent runs the tool .
"""


def vocabulary(text):
    words = sorted(set(text.split()))
    return words, {word: i for i, word in enumerate(words)}


def cooccurrence(text, window=2):
    """A grid of counts. Row for a word, column for a neighbour it appeared near.

    That row is the word's vector. It says nothing about what the word
    means and everything about the company it keeps, and the claim of this
    chapter is that the second is enough.
    """
    words, index = vocabulary(text)
    tokens = text.split()
    grid = np.zeros((len(words), len(words)))
    for position, word in enumerate(tokens):
        for offset in range(-window, window + 1):
            neighbour = position + offset
            if offset == 0 or neighbour < 0 or neighbour >= len(tokens):
                continue
            grid[index[word], index[tokens[neighbour]]] += 1
    return grid, index


def cosine(a, b):
    """How much two vectors point the same way, ignoring how long they are.

    One means the same direction, zero means nothing in common. Length is
    divided out on purpose. A word that appears ten times has a vector ten
    times longer than a word that appears once, and that says how common
    the word is, not what it means.
    """
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def euclidean(a, b):
    """The straight line distance, which does care about length."""
    return float(np.linalg.norm(a - b))


def nearest(word, grid, index, count=3):
    """The words whose vectors point most nearly the same way as this one."""
    words = sorted(index, key=index.get)
    me = grid[index[word]]
    scored = [(other, cosine(me, grid[index[other]])) for other in words if other != word]
    return sorted(scored, key=lambda pair: -pair[1])[:count]


if __name__ == "__main__":
    grid, index = cooccurrence(CORPUS)
    for word in ["cat", "agent", "mat"]:
        print(f"nearest to {word!r}")
        for other, score in nearest(word, grid, index):
            print(f"  {other:8s} {score:.3f}")
    cat, dog, file = (grid[index[w]] for w in ["cat", "dog", "file"])
    print()
    times = {w: int(grid[index[w]].sum() / 4) for w in ["cat", "dog"]}
    print(f"cat appears {times['cat']} times, dog {times['dog']}")
    for other, vector in [("dog", dog), ("file", file)]:
        print(
            f"cosine(cat, {other}) {cosine(cat, vector):.3f}   "
            f"euclidean(cat, {other}) {euclidean(cat, vector):.2f}"
        )
