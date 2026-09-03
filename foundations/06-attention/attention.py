"""Attention, on four tokens, with every number visible.

The 2017 paper that changed everything is called Attention Is All You
Need. The mechanism it names fits in a dozen lines. Every token asks a
question, every token offers an answer, the questions are matched against
the offers, and each token becomes a mix of the answers it matched best,
weighted by how well. That is attention. Everything else in a transformer
is plumbing around it, and the plumbing is what this file leaves out.
"""
import numpy as np

TOKENS = ["the", "cat", "sat", "down"]


def softmax(scores):
    """Each row of scores into weights that sum to one."""
    shifted = scores - scores.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def attention(x, w_query, w_key, w_value, mask=None):
    """One head of attention over a sequence of token vectors.

    x has one row per token. The three grids turn each row into a query,
    a key and a value. The query is what the token is looking for. The key
    is what the token offers to be found by. The value is what it hands
    over when chosen. Scores are every query against every key. Weights
    are the scores through softmax, so each row sums to one. The output for
    a token is all the values, mixed by that token's row of weights.
    """
    queries = x @ w_query
    keys = x @ w_key
    values = x @ w_value
    scores = queries @ keys.T / np.sqrt(keys.shape[1])
    if mask is not None:
        scores = scores + mask
    weights = softmax(scores)
    return weights @ values, weights


def causal_mask(length):
    """Hide the future. Position i may look at positions up to i and no further.

    A model that predicts the next token must not see it. Minus infinity
    becomes zero after softmax, so a masked position gets no weight at all
    rather than a small one.
    """
    return np.triu(np.full((length, length), -np.inf), k=1)


def score_count(length):
    """How many query against key comparisons a sequence of this length needs.

    Every token scores against every token. That is the square, and it is
    the reason a long context costs what it costs. Double the length,
    four times the work.
    """
    return length * length


def hand_built_grids():
    """Grids set by hand so that sat looks at cat, to show what learning would find.

    Tokens are one hot, so the identity grid means a token's key and value
    are just itself. The query grid is identity except that the query for
    sat is pointed hard at the key for cat. In a real model these grids
    are learned by the method of chapter 4, and what they learn is which
    tokens should look at which.
    """
    size = len(TOKENS)
    w_key = np.eye(size)
    w_value = np.eye(size)
    w_query = np.eye(size)
    w_query[TOKENS.index("sat")] = 0
    w_query[TOKENS.index("sat"), TOKENS.index("cat")] = 6.0
    return w_query, w_key, w_value


if __name__ == "__main__":
    x = np.eye(len(TOKENS))
    w_query, w_key, w_value = hand_built_grids()
    output, weights = attention(x, w_query, w_key, w_value, causal_mask(len(TOKENS)))
    print("who looks at whom, rows are the token looking, columns the token looked at")
    print("        " + "".join(f"{t:>8s}" for t in TOKENS))
    for token, row in zip(TOKENS, weights, strict=True):
        print(f"{token:>8s}" + "".join(f"{w:8.2f}" for w in row))
    print()
    print("scores needed for a sequence of")
    for length in [4, 1_000, 100_000]:
        print(f"  {length:>7,} tokens  {score_count(length):>16,}")
