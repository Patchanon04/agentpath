"""Learning, from nothing, on the problem the previous chapter counted.

The count table cannot scale. This file replaces it with a grid of numbers
that starts random and is nudged, a few hundred times, toward giving the
same answers the table gave. That nudging is training. It is the whole of
what the word learn means for a model, and it fits in eighty lines.

numpy is used here and nowhere else in the course, because the nudging is
arithmetic on a grid and the grid is what numpy is for. Every operation
below is a loop you could write by hand. It would just be slow to read.
"""
import numpy as np

CORPUS = """
the agent reads the file and the agent decides what to do . the agent runs
the tool and the tool returns a result . the agent reads the result and
the agent decides again . the loop ends when the model stops asking for a
tool . the model never remembers the last turn . the model reads the whole
conversation every turn . the conversation grows and the cost grows with it .
the agent reads the file . the agent reads the result . the agent decides .
"""


def vocabulary(text):
    """Every distinct word, and a number for each, because a grid needs indices."""
    words = sorted(set(text.split()))
    return words, {word: i for i, word in enumerate(words)}


def pairs(text, index):
    """Each word and the word that followed it, as two arrays of indices."""
    ids = [index[word] for word in text.split()]
    return np.array(ids[:-1]), np.array(ids[1:])


def softmax(logits):
    """Turn any row of numbers into probabilities that sum to one.

    Subtracting the largest value first changes nothing mathematically and
    stops the exponentials overflowing, which they otherwise do the moment
    a logit passes about seven hundred.
    """
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def loss(weights, xs, ys):
    """How wrong the grid is, as one number. Lower is better.

    For every pair, look up the probability the grid gave to the word that
    actually came next, take the log, and average the negatives. A perfect
    model gives probability one to every right answer and scores zero.
    """
    probabilities = softmax(weights[xs])
    return -np.log(probabilities[np.arange(len(ys)), ys]).mean()


def gradient(weights, xs, ys):
    """Which direction to nudge every number in the grid, and how hard.

    This is the line that makes learning possible. For a softmax followed
    by that loss, the gradient is the probabilities the grid gave, minus
    one at the position of the right answer. Where the grid was too
    confident in a wrong word the number is positive and will be pushed
    down. Where it doubted the right word the number is negative and will
    be pushed up.
    """
    probabilities = softmax(weights[xs])
    probabilities[np.arange(len(ys)), ys] -= 1
    change = np.zeros_like(weights)
    np.add.at(change, xs, probabilities / len(ys))
    return change


def train(text, steps=300, learning_rate=10.0, seed=0):
    """Start random, and step downhill on the loss until the steps run out."""
    words, index = vocabulary(text)
    xs, ys = pairs(text, index)
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, 0.01, size=(len(words), len(words)))
    history = []
    for _ in range(steps):
        history.append(loss(weights, xs, ys))
        weights -= learning_rate * gradient(weights, xs, ys)
    return weights, index, history


def predict(weights, index, word):
    """What the trained grid believes follows a word, most likely first."""
    words = sorted(index, key=index.get)
    row = softmax(weights[index[word]])
    ranked = sorted(zip(words, row, strict=True), key=lambda pair: -pair[1])
    return {candidate: float(p) for candidate, p in ranked}


if __name__ == "__main__":
    weights, index, history = train(CORPUS)
    print(f"loss at the start {history[0]:.3f}, after training {history[-1]:.3f}")
    print()
    beliefs = predict(weights, index, "the")
    print("after 'the', most likely first")
    for word, p in list(beliefs.items())[:5]:
        print(f"  {word:14s} {p:.3f}")
    print(f"  ...and 'and', which never followed 'the' in the text, gets {beliefs['and']:.4f}")
