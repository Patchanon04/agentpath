"""Prove the chapter's claims about learning on this machine."""
import sys
from collections import Counter

import numpy as np
from learn import CORPUS, gradient, loss, pairs, predict, softmax, train


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


row = softmax(np.array([1.0, 2.0, 3.0]))
if abs(row.sum() - 1.0) > 1e-9 or not (row[0] < row[1] < row[2]):
    fail(f"softmax should give a distribution that keeps the order, got {row}")
print("OK softmax turns any row of numbers into probabilities that sum to one")

weights, index, history = train(CORPUS)
if not history[-1] < history[0] / 2:
    fail(f"loss should at least halve, went from {history[0]:.3f} to {history[-1]:.3f}")
if any(later > earlier + 1e-6 for earlier, later in zip(history, history[1:], strict=False)):
    fail("loss went up during training, so a step went uphill")
print("OK every step goes downhill and the loss more than halves")

words_after_the = Counter()
tokens = CORPUS.split()
for current, following in zip(tokens, tokens[1:], strict=False):
    if current == "the":
        words_after_the[following] += 1
counted = {w: n / sum(words_after_the.values()) for w, n in words_after_the.items()}
learned = predict(weights, index, "the")
top_counted = max(counted, key=counted.get)
top_learned = next(iter(learned))
if top_learned != top_counted:
    fail(f"counting says {top_counted} follows 'the', learning says {top_learned}")
if abs(learned[top_counted] - counted[top_counted]) > 0.05:
    fail(
        f"learned {learned[top_counted]:.3f} for {top_counted}, "
        f"counting gave {counted[top_counted]:.3f}"
    )
print("OK the grid learned what the count table knew, without a count table")

if "and" in counted:
    fail("the test assumes 'and' never follows 'the' in the corpus")
if not learned["and"] > 0:
    fail(
        "the grid gave zero to a word it never saw follow 'the', "
        "which counting does and learning must not"
    )
print("OK a word never seen in that position still gets a small chance rather than none")

xs, ys = pairs(CORPUS, index)
before = loss(weights, xs, ys)
after = loss(weights - 1.0 * gradient(weights, xs, ys), xs, ys)
if not after < before:
    fail("stepping against the gradient did not lower the loss")
print("OK the gradient points uphill, so stepping against it goes down")
