# Foundations 5. Meaning as direction

This folder is the code behind the fifth foundations chapter of the book,
at [book/00e-meaning-as-direction.md](../../book/00e-meaning-as-direction.md).
The chapter explains why a word becomes a list of numbers and what it means
for two words to be close. This file is the short version for running the
code.

No model to call, no API key. Uses numpy.

## What is here

`vectors.py` builds the oldest kind of embedding there is. `cooccurrence`
counts, for every word, which words appeared near it, and that row of
counts is the word's vector. `cosine` compares two vectors by direction
alone, `euclidean` by straight line distance, and `nearest` ranks every
other word by cosine.

```python
def cosine(a, b):
    """How much two vectors point the same way, ignoring how long they are."""
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
```

The corpus is built so that `cat` and `dog` do the same things and `agent`
and `model` do the same things, and nothing in the code is told that.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python vectors.py
```

```text
nearest to 'cat'
  dog      0.979
  bone     0.928
  fish     0.928
nearest to 'agent'
  model    0.998
  file     0.952
  result   0.952

cat appears 5 times, dog 3
cosine(cat, dog) 0.979   euclidean(cat, dog) 5.74
cosine(cat, file) 0.854   euclidean(cat, file) 7.28
```

```bash
python check.py
```

```text
OK words used the same way point the same way, and nobody defined either
OK the two groups in the text are two groups in the space
OK cosine is one for the same direction
OK cosine ignores how common a word is and euclidean does not
OK cat is more common than dog and is still its nearest neighbour
```

## What to notice

Nobody defined `cat`. The nearest word to it is `dog` because the two keep
the same company, and that is the whole idea. Meaning, for a machine, is
the company a word keeps, written as a direction.

`cat` appears five times and `dog` three, so the `cat` vector is longer.
Cosine does not care, and that is why it is the comparison everyone uses.
Euclidean distance would call a common word far from a rare one that
means the same thing.

`cat` and `file` still score 0.854, which is high for two words with
nothing in common. Both live next to `the`, and `the` lives next to
everything. Real embeddings weight down the words that appear everywhere
for exactly this reason. The chapter says how.
