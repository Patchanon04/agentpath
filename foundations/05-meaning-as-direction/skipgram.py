"""Embeddings that are learned rather than counted.

vectors.py counted neighbours and got a row of twenty five numbers per
word, one per word in the vocabulary. A real embedding is a few hundred
numbers wide no matter how big the vocabulary is, and nobody counts it.
It is learned, by the method of chapter 4, from a task chosen so that
the vectors come out meaning something. The task here is the one
word2vec used in 2013, guess the neighbours from the word. A word whose
vector predicts its neighbours well is a word whose vector says what
company it keeps, which is the same idea as counting, in fewer numbers.
"""
import numpy as np
from vectors import CORPUS, cosine, vocabulary


def softmax(logits):
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def training_pairs(text, index, window=2):
    """Every word paired with every neighbour inside the window, as two arrays.

    This is the whole dataset. No labels, no annotation, just the text
    and a window. The word is the input and the neighbour is the answer
    the model has to guess, so any text at all is training data, which
    is why the vectors in real models were trained on the whole web.
    """
    tokens = text.split()
    centres, contexts = [], []
    for position, word in enumerate(tokens):
        for offset in range(-window, window + 1):
            neighbour = position + offset
            if offset == 0 or neighbour < 0 or neighbour >= len(tokens):
                continue
            centres.append(index[word])
            contexts.append(index[tokens[neighbour]])
    return np.array(centres), np.array(contexts)


def train(text, size=8, steps=400, learning_rate=0.5, seed=0):
    """Learn a vector per word by guessing neighbours. Chapter 4 again, with two grids.

    The first grid is the embedding, one row of `size` numbers per word.
    The second turns a row back into a guess over the vocabulary. The
    loss and the gradient are exactly the ones in chapter 4. The only
    new step is that the gradient flows through the second grid into the
    first, which is the smallest possible example of backpropagation.
    """
    words, index = vocabulary(text)
    centres, contexts = training_pairs(text, index)
    rng = np.random.default_rng(seed)
    embedding = rng.normal(0, 0.1, size=(len(words), size))
    readout = rng.normal(0, 0.1, size=(size, len(words)))
    history = []
    for _ in range(steps):
        hidden = embedding[centres]
        guess = softmax(hidden @ readout)
        history.append(-np.log(guess[np.arange(len(contexts)), contexts]).mean())
        guess[np.arange(len(contexts)), contexts] -= 1
        guess /= len(contexts)
        readout_change = hidden.T @ guess
        hidden_change = guess @ readout.T
        readout -= learning_rate * readout_change
        np.add.at(embedding, centres, -learning_rate * hidden_change)
    return embedding, index, history


def nearest(word, embedding, index, count=3):
    """The words whose learned vectors point most nearly the same way."""
    words = sorted(index, key=index.get)
    me = embedding[index[word]]
    scored = [(other, cosine(me, embedding[index[other]])) for other in words if other != word]
    return sorted(scored, key=lambda pair: -pair[1])[:count]


if __name__ == "__main__":
    embedding, index, history = train(CORPUS)
    words = len(index)
    print(f"{words} words, each a vector of {embedding.shape[1]} numbers, not {words}")
    print(f"loss at the start {history[0]:.3f}, after training {history[-1]:.3f}")
    print()
    for word in ["cat", "agent"]:
        print(f"nearest to {word!r} by the learned vectors")
        for other, score in nearest(word, embedding, index):
            print(f"  {other:8s} {score:.3f}")
    cat, dog, file = (embedding[index[w]] for w in ["cat", "dog", "file"])
    print()
    print(f"cosine(cat, dog) {cosine(cat, dog):.3f}   cosine(cat, file) {cosine(cat, file):.3f}")
