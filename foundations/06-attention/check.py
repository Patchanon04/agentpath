"""Prove the chapter's claims about attention on this machine."""
import sys

import numpy as np
from attention import (
    TOKENS,
    attend_with_cache,
    attention,
    block,
    causal_mask,
    feed_forward,
    finish_head,
    hand_built_grids,
    key_rows_computed,
    layer_norm,
    position_vectors,
    score_count,
)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


x = np.eye(len(TOKENS))
w_query, w_key, w_value = hand_built_grids()

_, weights = attention(x, w_query, w_key, w_value)
if not np.allclose(weights.sum(axis=1), 1.0):
    fail("every token's weights should sum to one")
print("OK each token spreads exactly one unit of attention over the sequence")

sat = TOKENS.index("sat")
cat = TOKENS.index("cat")
if weights[sat].argmax() != cat or weights[sat, cat] < 0.8:
    fail(f"sat should look mostly at cat, its row is {weights[sat].round(2)}")
print("OK with the grids set to say so, sat looks at cat and mostly nothing else")

_, masked = attention(x, w_query, w_key, w_value, causal_mask(len(TOKENS)))
future = np.triu(np.ones_like(masked), k=1).astype(bool)
if not np.all(masked[future] == 0):
    fail("a masked token should get exactly zero weight, not a small one")
if not np.allclose(masked.sum(axis=1), 1.0):
    fail("masking should leave every row still summing to one")
print("OK the mask hides the future completely and the rows still sum to one")

if masked[0].argmax() != 0 or masked[0, 0] != 1.0:
    fail("the first token can only look at itself")
print("OK the first token has nothing before it and attends to itself")

if score_count(2_000) != 4 * score_count(1_000):
    fail("doubling the length should quadruple the scores")
print("OK doubling the context quadruples the work, which is why long context costs what it does")

mixed, _ = attention(x, w_query, w_key, w_value, causal_mask(len(TOKENS)))
untouched = finish_head(x, mixed, np.zeros((len(TOKENS), len(TOKENS))))
if not np.allclose(untouched, x):
    fail("a head that has learned nothing should pass its input through unchanged")
adjusted = finish_head(x, mixed, np.eye(len(TOKENS)))
if np.allclose(adjusted, x) or np.allclose(adjusted, mixed):
    fail("a head that has learned something should adjust the input, not replace it")
print("OK a head adjusts a token rather than replacing it, and the adjustment is added on")

size = len(TOKENS)
backwards = [3, 2, 1, 0]
plain, _ = attention(x, w_query, w_key, w_value)
shuffled, _ = attention(x[backwards], w_query, w_key, w_value)
if not np.allclose(shuffled, plain[backwards]):
    fail("without positions, reversing the tokens should only reverse the output rows")
print("OK without positions attention cannot tell the order, reversing tokens reverses the rows")

positions = position_vectors(size, size)
placed, _ = attention(x + positions, w_query, w_key, w_value)
placed_backwards, _ = attention(x[backwards] + positions, w_query, w_key, w_value)
if np.allclose(placed_backwards, placed[backwards]):
    fail("with positions added, the same tokens in another order should give a different output")
print("OK with position vectors added the same tokens in another order give a different output")

normed = layer_norm(np.array([[1.0, 2.0, 3.0, 10.0], [-5.0, 0.0, 0.0, 5.0]]))
centred = np.allclose(normed.mean(axis=1), 0, atol=1e-6)
if not centred or not np.allclose(normed.std(axis=1), 1, atol=1e-3):
    fail(f"layer norm should give every row mean zero and spread one, got {normed}")
print("OK layer norm gives every token mean zero and spread one, whatever it started as")

rng = np.random.default_rng(0)
w_in, w_ff = rng.normal(size=(size, 3 * size)), rng.normal(size=(3 * size, size))
before = feed_forward(x, w_in, w_ff)
poked = x.copy()
poked[2] += 1.0
after = feed_forward(poked, w_in, w_ff)
changed = [i for i in range(size) if not np.allclose(before[i], after[i])]
if changed != [2]:
    fail(f"changing one token should change only its own feed forward row, changed {changed}")
print("OK the feed forward layer works on each token alone, one token changed is one row changed")

heads = [hand_built_grids(), (np.eye(size), np.eye(size), np.eye(size))]
w_out = rng.normal(size=(2 * size, size))
out = block(x, heads, w_out, w_in, w_ff)
if out.shape != x.shape:
    fail(f"a block should return the shape it was given, got {out.shape}")
if not out.shape == block(out, heads, w_out, w_in, w_ff).shape:
    fail("a block's output should be a valid input to the next block")
print("OK a block returns tokens the same shape it was given, which is what lets blocks stack")

full, full_weights = attention(x, w_query, w_key, w_value, causal_mask(size))
cache = {"keys": [], "values": []}
one_at_a_time = np.array([attend_with_cache(row, w_query, w_key, w_value, cache)[0] for row in x])
if not np.allclose(one_at_a_time, full):
    fail("feeding tokens one at a time through the cache should give the masked attention exactly")
print("OK feeding tokens through the cache one at a time gives exactly what masked attention gives")

with_cache, without = key_rows_computed(1_000, cached=True), key_rows_computed(1_000, cached=False)
if with_cache != 1_000 or without != 500_500:
    fail(f"expected 1000 key rows with the cache and 500500 without, got {with_cache} {without}")
print("OK with the cache a thousand tokens cost a thousand key rows instead of half a million")
