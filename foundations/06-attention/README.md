# Foundations 6. Attention

This folder is the code behind the sixth foundations chapter of the book,
at [book/00f-attention.md](../../book/00f-attention.md). The chapter
explains the mechanism that changed everything in 2017 and why it makes a
long context cost what it does. This file is the short version for running
the code.

No model to call, no API key. Uses numpy.

## What is here

`attention.py` holds one head of attention in a dozen lines. `attention`
turns each token into a query, a key and a value, scores every query
against every key, and mixes the values by those scores. `causal_mask`
hides the future. `score_count` is the arithmetic behind the quadratic
cost. `hand_built_grids` sets the weights by hand so that `sat` looks at
`cat`, which is what a real model would learn.

```python
def attention(x, w_query, w_key, w_value, mask=None):
    """One head of attention over a sequence of token vectors."""
    queries = x @ w_query
    keys = x @ w_key
    values = x @ w_value
    scores = queries @ keys.T / np.sqrt(keys.shape[1])
    if mask is not None:
        scores = scores + mask
    weights = softmax(scores)
    return weights @ values, weights
```

`check.py` pins the claims the chapter makes.

## Run it

```bash
python attention.py
```

```text
who looks at whom, rows are the token looking, columns the token looked at
             the     cat     sat    down
     the    1.00    0.00    0.00    0.00
     cat    0.38    0.62    0.00    0.00
     sat    0.05    0.91    0.05    0.00
    down    0.22    0.22    0.22    0.35

scores needed for a sequence of
        4 tokens                16
    1,000 tokens         1,000,000
  100,000 tokens    10,000,000,000
```

```bash
python check.py
```

```text
OK each token spreads exactly one unit of attention over the sequence
OK with the grids set to say so, sat looks at cat and mostly nothing else
OK the mask hides the future completely and the rows still sum to one
OK the first token has nothing before it and attends to itself
OK doubling the context quadruples the work, which is why long context costs what it does
```

## What to notice

Read the `sat` row. It puts 0.91 of its attention on `cat`, because the
query grid was built to point it there. In a real model nobody builds that
grid. It is learned by the method of chapter 4, and what it learns is
which tokens should look at which. The verb learns to look at its subject
because doing so makes the next token easier to predict.

The upper right of the table is all zeros. That is the mask. A model that
predicts the next token must not be allowed to see it, so every token may
look only at what came before.

And the last table is the whole reason context windows are priced the way
they are. Every token scores against every token. A hundred thousand
tokens is ten billion scores, per layer, per head, and the models you call
have dozens of each.
