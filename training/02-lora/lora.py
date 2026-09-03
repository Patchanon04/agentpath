"""LoRA on the grid from foundations chapter 4, so the trick is visible.

Fine tuning a model means nudging its parameters on new text, chapter 4
again. Full fine tuning nudges all of them, which for a real model means
a copy of every weight in memory plus its gradient plus the optimiser
state, three times the model, on hardware that can hold it. LoRA is the
observation that the nudge is usually simple. Instead of changing the
whole grid, learn a thin pair of grids whose product is the change, keep
the original frozen, and add the product on at inference. The pair is a
small fraction of the parameters and it trains on a fraction of the
memory. This file does it to a forty one by forty one grid, where you
can count.
"""
import numpy as np
from grid import BASE_CORPUS, NEW_CORPUS, gradient, loss, pairs, pretrain, vocabulary


def full_finetune(weights, xs, ys, steps=100, learning_rate=10.0):
    """Nudge every number in the grid on the new text. Every parameter moves."""
    tuned = weights.copy()
    for _ in range(steps):
        tuned -= learning_rate * gradient(tuned, xs, ys)
    return tuned


def lora_finetune(weights, xs, ys, rank=2, steps=300, learning_rate=2.0, seed=0):
    """Keep the grid frozen. Learn a thin pair whose product is the change.

    down is size by rank, up is rank by size. Their product is a full
    sized grid that has only rank independent directions in it, which is
    what low rank means. The gradient of the loss with respect to the
    full grid is the one chapter 4 derived. The chain rule turns it into
    gradients for the two thin grids, and those are the only numbers
    that move. up starts at zero so that the first step is the frozen
    model exactly, which is the convention every LoRA implementation
    uses for the same reason.
    """
    rng = np.random.default_rng(seed)
    size = weights.shape[0]
    down = rng.normal(0, 0.01, size=(size, rank))
    up = np.zeros((rank, size))
    for _ in range(steps):
        full_change = gradient(weights + down @ up, xs, ys)
        down_change = full_change @ up.T
        up_change = down.T @ full_change
        down -= learning_rate * down_change
        up -= learning_rate * up_change
    return down, up


def merge(weights, down, up):
    """Add the product on. After this there is no adapter, only a grid, at no extra cost."""
    return weights + down @ up


def parameters(*grids):
    return sum(int(grid.size) for grid in grids)


if __name__ == "__main__":
    words, index = vocabulary(BASE_CORPUS, NEW_CORPUS)
    base = pretrain(index)
    old_xs, old_ys = pairs(BASE_CORPUS, index)
    new_xs, new_ys = pairs(NEW_CORPUS, index)
    full = full_finetune(base, new_xs, new_ys)
    down, up = lora_finetune(base, new_xs, new_ys, rank=2)
    adapted = merge(base, down, up)
    mixed_xs, mixed_ys = pairs(BASE_CORPUS + NEW_CORPUS, index)
    mixed_down, mixed_up = lora_finetune(base, mixed_xs, mixed_ys, rank=2)
    rehearsed = merge(base, mixed_down, mixed_up)
    print(f"{len(words)} words, a grid of {parameters(base)} numbers")
    print()
    print("                    loss on old text   on new text   numbers trained")
    rows = [
        ("frozen model", base, 0),
        ("full finetune", full, parameters(full)),
        ("lora rank 2", adapted, parameters(down, up)),
        ("lora, old text too", rehearsed, parameters(mixed_down, mixed_up)),
    ]
    for name, model, trained in rows:
        old, new = loss(model, old_xs, old_ys), loss(model, new_xs, new_ys)
        print(f"{name:18s}  {old:16.3f}   {new:11.3f}   {trained:15d}")
    print()
    directions = np.linalg.matrix_rank(down @ up)
    print(f"the change lora made has {directions} independent directions in a {base.shape[0]} by")
    print(f"{base.shape[1]} grid, and after merging the model is a plain grid again")
