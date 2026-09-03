"""Prove the chapter's claims about preference tuning on this machine."""
import sys

import numpy as np
from dpo import PREFERENCES, dpo_loss, drift, log_probability, train_dpo
from grid import BASE_CORPUS, gradient, pairs, pretrain, vocabulary


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


words, index = vocabulary(BASE_CORPUS, " ".join(w for p in PREFERENCES for w in p))
reference = pretrain(index)
tuned, history = train_dpo(reference, PREFERENCES, index)

if abs(history[0] - np.log(2)) > 1e-9:
    fail(f"the policy starts at the reference, so the loss should be log 2, got {history[0]:.4f}")
print("OK at the start the loss is log two, because the policy and the reference agree exactly")

if not history[-1] < history[0] / 5:
    fail(f"the dpo loss should fall a long way, went from {history[0]:.3f} to {history[-1]:.3f}")
print("OK the loss falls, with no reward model and no reinforcement learning anywhere")

for context, chosen, rejected in PREFERENCES:
    before = log_probability(reference, context, chosen, index) - log_probability(
        reference, context, rejected, index
    )
    after = log_probability(tuned, context, chosen, index) - log_probability(
        tuned, context, rejected, index
    )
    if not after > before:
        fail(f"after '{context}' the model should prefer {chosen} over {rejected} more than it did")
print("OK every chosen word gains on its rejected word, relative to where the reference was")

naive = reference.copy()
xs, ys = pairs("the agent asks . the tool returns . the model asks .", index)
for _ in range(60):
    naive -= 2.0 * gradient(naive, xs, ys)
if not drift(tuned, reference, index) < drift(naive, reference, index):
    fail("dpo should move the whole model less than plain finetuning on the chosen words")
print("OK the reference term keeps the model near where it started, plain finetuning drifts more")

if dpo_loss(reference, reference, PREFERENCES, index, beta=5.0) != dpo_loss(
    reference, reference, PREFERENCES, index, beta=0.1
):
    fail("with the policy at the reference, beta should not matter yet")
print("OK beta only matters once the policy has moved, it is the leash and not the direction")
