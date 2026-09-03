"""Prove the chapter's claims about quantization on this machine."""
import sys

import numpy as np
from grid import BASE_CORPUS, loss, pairs, pretrain, vocabulary
from quantize import bytes_for, dequantize, dequantize_grouped, quantize, quantize_grouped


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


words, index = vocabulary(BASE_CORPUS)
base = pretrain(index)
xs, ys = pairs(BASE_CORPUS, index)
before = loss(base, xs, ys)

integers, scale = quantize(base, 8)
if integers.min() < -127 or integers.max() > 127:
    fail("eight bit integers should stay inside minus 127 to 127")
if not bytes_for(base, 8) < base.nbytes / 6:
    fail("eight bits should be a small fraction of sixty four")
print("OK at eight bits every number is an integer from minus 127 to 127, one scale per row")

eight = loss(dequantize(integers, scale), xs, ys)
if abs(eight - before) > 0.01:
    fail(f"eight bits should cost almost nothing, loss went from {before:.4f} to {eight:.4f}")
print("OK eight bits costs almost nothing, the loss moves in the third decimal place")

four_integers, four_scale = quantize(base, 4)
four = loss(dequantize(four_integers, four_scale), xs, ys)
if not four > eight:
    fail("four bits should cost more than eight")
if four - before > 0.1:
    fail(f"four bits should still be usable on this grid, loss went to {four:.4f}")
print("OK four bits costs more, and the cost is a number you can read next to the bytes saved")

grouped_integers, grouped_scale = quantize_grouped(base, 4, group=17)
grouped = loss(dequantize_grouped(grouped_integers, grouped_scale, group=17), xs, ys)
if not grouped <= four:
    fail(f"a scale per group should lose less than per row, got {grouped:.4f} vs {four:.4f}")
print("OK a scale per small group keeps more detail at four bits than a scale per row")

worst = np.abs(base - dequantize(four_integers, four_scale)).max()
if not worst < np.abs(base).max() / 10:
    fail("the largest rounding error should be small next to the largest number in the grid")
print("OK the largest single error is a small fraction of the largest number in the grid")
