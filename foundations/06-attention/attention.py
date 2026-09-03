"""Attention, on four tokens, with every number visible.

The 2017 paper that changed everything is called Attention Is All You
Need. The mechanism it names fits in a dozen lines. Every token asks a
question, every token offers an answer, the questions are matched against
the offers, and each token becomes a mix of the answers it matched best,
weighted by how well. That is attention. Everything else in a transformer
is plumbing around it, and the second half of this file is that plumbing,
each piece small enough to read.
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


def finish_head(x, mixed, w_out):
    """What happens to a head's output before the next layer sees it.

    The head returns values mixed by attention, and they live in the value
    space. w_out projects them back into the token's own space, and then
    the token the head started from is added back. That addition is the
    residual connection. Every layer adjusts a token rather than replacing
    it, which is what lets a stack of dozens of layers be trained at all,
    because a layer that has learned nothing yet passes its input through
    unchanged instead of destroying it.
    """
    return x + mixed @ w_out


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


def position_vectors(length, size):
    """One vector per position, so a token carries where it is as well as what it is.

    Attention on its own cannot tell the first token from the last. The
    scores are every query against every key, and nothing in that
    arithmetic knows the order, so shuffling the tokens shuffles the
    output rows and changes nothing else. Order has to be put in. Each
    token's vector becomes what it is plus where it is, and this is the
    where, the sine and cosine table from the 2017 paper. Later models
    learn the table instead, or rotate the queries and keys by an angle
    that grows with position, which is what RoPE is. The point is the
    same in every version. Attention does not carry order, so the input
    has to.
    """
    positions = np.arange(length)[:, None]
    dims = np.arange(size)[None, :]
    angles = positions / (10_000 ** (2 * (dims // 2) / size))
    return np.where(dims % 2 == 0, np.sin(angles), np.cos(angles))


def multi_head(x, heads, w_out):
    """Several heads on the same tokens, each with its own grids, joined side by side.

    One head has one set of grids and so learns one pattern of who looks
    at whom. A verb looking at its subject is one pattern. A closing
    bracket looking at its opening one is another. Running several heads
    at once and joining their outputs lets one layer hold several
    patterns, and w_out mixes them back into the token's own space. That
    is all multi head means.
    """
    mixed = [attention(x, w_query, w_key, w_value)[0] for w_query, w_key, w_value in heads]
    return np.concatenate(mixed, axis=1) @ w_out


def layer_norm(x, epsilon=1e-5):
    """Rescale each token's vector to mean zero and spread one, so no token shouts.

    Dozens of layers each adding onto the token would let the numbers
    drift as large as they like, and softmax on huge scores turns into a
    hard pick of one token. Normalising each row before it enters a layer
    keeps everything in the range the arithmetic was designed for.
    """
    mean = x.mean(axis=-1, keepdims=True)
    spread = x.std(axis=-1, keepdims=True)
    return (x - mean) / (spread + epsilon)


def feed_forward(x, w_in, w_out):
    """The half of a block where each token thinks alone.

    Attention is where tokens talk to each other. This is where each
    token, by itself, is pushed through a wider grid, has its negatives
    cut to zero, and is pulled back to its own size. No token sees any
    other here, so changing one token changes one row of the output.
    About two thirds of a real model's parameters live in these two
    grids, and this is where the facts a model knows are mostly stored.
    """
    return np.maximum(0, x @ w_in) @ w_out


def block(x, heads, w_out, w_in, w_ff):
    """One transformer block. A real model is this, dozens of times, in a stack.

    Talk, then think. Attention lets every token gather from the others,
    then the feed forward layer lets every token work on what it
    gathered, alone. Each half is added onto the token rather than
    replacing it, which is the residual from finish_head, and each half
    normalises its input first. The output is the same shape as the
    input. That is what lets blocks stack, and the next block starts from
    tokens that already carry what this one gathered.
    """
    x = x + multi_head(layer_norm(x), heads, w_out)
    x = x + feed_forward(layer_norm(x), w_in, w_ff)
    return x


def attend_with_cache(token_row, w_query, w_key, w_value, cache):
    """One new token attends over everything before it, reusing what was computed.

    Generation is one token at a time, and an earlier token's key and
    value are the same on every step, because they depend only on that
    token. Recomputing them for the whole sequence on every step is
    where most of the work would go. So they are kept. The new token
    computes its own query, key and value, appends its key and value to
    the cache, and scores its query against every key in it. That is the
    KV cache. It is why the memory a served model uses grows with the
    length of the conversation, and why a prompt the server already
    holds is billed cheaper than a new one.
    """
    cache["keys"].append(token_row @ w_key)
    cache["values"].append(token_row @ w_value)
    keys = np.array(cache["keys"])
    values = np.array(cache["values"])
    scores = (token_row @ w_query) @ keys.T / np.sqrt(keys.shape[1])
    weights = softmax(scores)
    return weights @ values, weights


def key_rows_computed(length, cached):
    """Key and value rows computed while generating a sequence one token at a time.

    Without the cache, step t recomputes keys and values for all t
    tokens, so the total is one plus two plus three and so on. With it,
    each token's key and value are computed once.
    """
    return length if cached else length * (length + 1) // 2


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
    print()
    backwards = [3, 2, 1, 0]
    plain, _ = attention(x, w_query, w_key, w_value)
    shuffled, _ = attention(x[backwards], w_query, w_key, w_value)
    print("without positions, reversing the tokens reverses the output rows and nothing else")
    print("  same rows in the other order:", np.allclose(shuffled, plain[backwards]))
    positions = position_vectors(len(TOKENS), len(TOKENS))
    placed, _ = attention(x + positions, w_query, w_key, w_value)
    placed_backwards, _ = attention(x[backwards] + positions, w_query, w_key, w_value)
    print("with positions added, the same tokens in the other order give a different output")
    print("  same rows in the other order:", np.allclose(placed_backwards, placed[backwards]))
    print()
    print("key and value rows computed to generate, one token at a time")
    for length in [4, 1_000, 100_000]:
        without, with_cache = key_rows_computed(length, False), key_rows_computed(length, True)
        print(f"  {length:>7,} tokens  {without:>16,} without the cache  {with_cache:>9,} with it")
