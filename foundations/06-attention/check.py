"""Prove the chapter's claims about attention on this machine."""
import sys

import numpy as np
from attention import TOKENS, attention, causal_mask, finish_head, hand_built_grids, score_count


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
