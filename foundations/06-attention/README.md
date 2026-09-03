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

The rest of the file is the plumbing a real model wraps around that head,
each piece small enough to read. `position_vectors` puts order back in,
because attention on its own cannot tell the first token from the last.
`multi_head` runs several heads side by side so one layer can hold several
patterns of who looks at whom. `layer_norm` keeps the numbers in range and
`feed_forward` is the half of a block where each token thinks alone, and
`block` puts the two halves together with the residual from `finish_head`.
`attend_with_cache` is generation one token at a time with the keys and
values of earlier tokens kept rather than recomputed, which is the KV
cache, and `key_rows_computed` is the arithmetic that says why it exists.

```python
def block(x, heads, w_out, w_in, w_ff):
    """One transformer block. A real model is this, dozens of times, in a stack."""
    x = x + multi_head(layer_norm(x), heads, w_out)
    x = x + feed_forward(layer_norm(x), w_in, w_ff)
    return x
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

without positions, reversing the tokens reverses the output rows and nothing else
  same rows in the other order: True
with positions added, the same tokens in the other order give a different output
  same rows in the other order: False

key and value rows computed to generate, one token at a time
        4 tokens                10 without the cache          4 with it
    1,000 tokens           500,500 without the cache      1,000 with it
  100,000 tokens     5,000,050,000 without the cache    100,000 with it
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
OK a head adjusts a token rather than replacing it, and the adjustment is added on
OK without positions attention cannot tell the order, reversing tokens reverses the rows
OK with position vectors added the same tokens in another order give a different output
OK layer norm gives every token mean zero and spread one, whatever it started as
OK the feed forward layer works on each token alone, one token changed is one row changed
OK a block returns tokens the same shape it was given, which is what lets blocks stack
OK feeding tokens through the cache one at a time gives exactly what masked attention gives
OK with the cache a thousand tokens cost a thousand key rows instead of half a million
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

The third table is the whole reason context windows are priced the way
they are. Every token scores against every token. A hundred thousand
tokens is ten billion scores, per layer, per head, and the models you call
have dozens of each.

Then two lines that say True and False. Reverse the four tokens and, with
nothing else changed, the output rows reverse and nothing else moves.
Attention has no idea which token came first, because nothing in query
times key knows about order. Add the position vectors and the same four
tokens backwards give a different answer. Every model you call does one
of these, adds a position vector or rotates by position, and without it
`the cat sat down` and `down sat cat the` would be the same sentence.

The last table is why a served model's memory grows with the length of
the conversation and why a prompt the server already holds is cheaper.
Generating one token at a time, without a cache, recomputes every earlier
token's key and value on every step, and that sum is half a million rows
for a thousand tokens. With the cache each is computed once. `check.py`
confirms that feeding the tokens through the cache one at a time gives
exactly the rows the masked attention gives all at once, which is the
whole point. Same answer, a thousand times less work.
