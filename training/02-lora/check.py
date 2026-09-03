"""Prove the chapter's claims about LoRA on this machine."""
import sys

import numpy as np
from grid import BASE_CORPUS, NEW_CORPUS, loss, pairs, pretrain, vocabulary
from lora import full_finetune, lora_finetune, merge, parameters


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


words, index = vocabulary(BASE_CORPUS, NEW_CORPUS)
base = pretrain(index)
old_xs, old_ys = pairs(BASE_CORPUS, index)
new_xs, new_ys = pairs(NEW_CORPUS, index)

full = full_finetune(base, new_xs, new_ys)
down, up = lora_finetune(base, new_xs, new_ys, rank=2)
adapted = merge(base, down, up)

if not loss(adapted, new_xs, new_ys) < loss(base, new_xs, new_ys) / 2:
    fail("lora should learn the new text, at least halving the frozen model's loss on it")
if not loss(adapted, new_xs, new_ys) < loss(full, new_xs, new_ys) + 0.4:
    fail(
        f"lora should get close to full finetuning on the new text, got "
        f"{loss(adapted, new_xs, new_ys):.3f} against {loss(full, new_xs, new_ys):.3f}"
    )
print("OK lora learns the new text nearly as well as nudging every number does")

if not parameters(down, up) < parameters(base) / 10:
    fail(f"lora should train under a tenth of the numbers, trained {parameters(down, up)}")
print("OK and it trains under a tenth of the numbers to do it")

if np.linalg.matrix_rank(down @ up) != 2:
    fail("the change should have exactly rank independent directions")
if adapted.shape != base.shape:
    fail("merging should give back a grid the same shape as the frozen one")
print("OK the change has two independent directions, and merging gives a plain grid back")

untouched_down, untouched_up = lora_finetune(base, new_xs, new_ys, rank=2, steps=0)
if not np.allclose(merge(base, untouched_down, untouched_up), base):
    fail("with up at zero the adapter should be invisible, so step zero is the frozen model")
print("OK up starts at zero, so before training the adapter changes nothing at all")

if not loss(full, old_xs, old_ys) > loss(base, old_xs, old_ys) + 0.5:
    fail("training on the new text alone should make the model worse on the old")
mixed_xs, mixed_ys = pairs(BASE_CORPUS + NEW_CORPUS, index)
mixed_down, mixed_up = lora_finetune(base, mixed_xs, mixed_ys, rank=2)
rehearsed = merge(base, mixed_down, mixed_up)
if not loss(rehearsed, old_xs, old_ys) < loss(adapted, old_xs, old_ys) - 0.5:
    fail("training on both texts should keep most of what the model knew")
print("OK forgetting is real, both methods forget, and mixing the old text back in is the cure")
