# Foundations 4. What learning is

This folder is the code behind the fourth foundations chapter of the book,
at [book/00d-learning.md](../../book/00d-learning.md). The chapter takes
the count table of the previous chapter and replaces it with a grid of
numbers that starts random and learns. This file is the short version for
running the code.

No model to call, no API key. This is the one folder in the course that
uses numpy, so install it first.

```bash
pip install numpy
```

## What is here

`learn.py` holds the whole of training in five functions. `softmax` turns a
row of numbers into probabilities. `loss` says how wrong the grid is as one
number. `gradient` says which way to nudge every number in the grid.
`train` starts random and steps downhill three hundred times. `predict`
reads the trained grid back out.

```python
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
```

`check.py` pins the claims the chapter makes.

## Run it

```bash
python learn.py
```

```text
loss at the start 3.526, after training 0.787

after 'the', most likely first
  agent          0.363
  model          0.135
  file           0.090
  result         0.090
  tool           0.090
  ...and 'and', which never followed 'the' in the text, gets 0.0004
```

```bash
python check.py
```

```text
OK softmax turns any row of numbers into probabilities that sum to one
OK every step goes downhill and the loss more than halves
OK the grid learned what the count table knew, without a count table
OK a word never seen in that position still gets a small chance rather than none
OK the gradient points uphill, so stepping against it goes down
OK one hot times the grid is a row lookup, and the row is the embedding
```

## What to notice

The previous chapter counted and found that `agent` follows `the` thirty six
percent of the time. This chapter never counts. It starts from random
numbers, and after three hundred nudges it believes thirty six percent.
Nobody told it the answer. The loss told it which direction was less wrong,
three hundred times.

The word `and` never follows `the` in the text. Counting gives it nothing.
The grid gives it four in ten thousand, which is small and is not zero, and
that gap is the difference between a table and a model. A table knows only
what it saw. A model has an opinion about everything, held with more or
less confidence.
