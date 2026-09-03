"""The chapter 4 model, carried into part 4 so every demo here trains the same thing.

A grid of numbers, one row per word, one column per word that could
follow, and the three functions from foundations chapter 4 that train
it. Nothing in this file is new. It is here so that LoRA, quantization
and preference tuning can each be shown on a model small enough to
count, and the same model each time.
"""
import numpy as np

# The text the base model was trained on, from chapter 4, and the new
# text a fine tune wants it to learn without forgetting the first.
BASE_CORPUS = """
the agent reads the file and the agent decides what to do . the agent runs
the tool and the tool returns a result . the agent reads the result and
the agent decides again . the loop ends when the model stops asking for a
tool . the model never remembers the last turn . the model reads the whole
conversation every turn . the conversation grows and the cost grows with it .
the agent reads the file . the agent reads the result . the agent decides .
"""

NEW_CORPUS = """
the agent asks the user before it runs the tool . the user says no and the
agent stops . the user says yes and the agent runs the tool . the agent asks
the user again . the user decides . the agent never runs the tool without
the user . the agent asks . the user says yes .
"""


def vocabulary(*texts):
    words = sorted({word for text in texts for word in text.split()})
    return words, {word: i for i, word in enumerate(words)}


def pairs(text, index):
    ids = [index[word] for word in text.split()]
    return np.array(ids[:-1]), np.array(ids[1:])


def softmax(logits):
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def loss(weights, xs, ys):
    probabilities = softmax(weights[xs])
    return float(-np.log(probabilities[np.arange(len(ys)), ys]).mean())


def gradient(weights, xs, ys):
    probabilities = softmax(weights[xs])
    probabilities[np.arange(len(ys)), ys] -= 1
    change = np.zeros_like(weights)
    np.add.at(change, xs, probabilities / len(ys))
    return change


def pretrain(index, steps=300, learning_rate=10.0, seed=0):
    """Chapter 4's training on the base corpus, giving the model every demo starts from."""
    xs, ys = pairs(BASE_CORPUS, index)
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, 0.01, size=(len(index), len(index)))
    for _ in range(steps):
        weights -= learning_rate * gradient(weights, xs, ys)
    return weights
