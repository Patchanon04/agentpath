"""Quantization on the chapter 4 grid, with the error you pay measured.

A model's parameters are stored as numbers, and how many bytes each
number takes decides how much memory the model needs and how fast it
can be read, which chapter 5 of this part shows is what decides how
fast it generates. Training uses sixteen or thirty two bits per number.
Quantization stores each number in eight or four bits instead, with a
scale per row or per group so that the small integers cover the range
the real numbers had. The model gets two to eight times smaller. The
price is a rounding error in every parameter, and this file measures
what that error does to the loss, so the trade is a number rather than
a feeling.
"""
import numpy as np
from grid import BASE_CORPUS, loss, pairs, pretrain, vocabulary


def quantize(grid, bits=8):
    """Round each row to integers of the given width, with one scale per row.

    absmax quantization. The largest magnitude in the row becomes the
    largest integer the width allows, and every other number is scaled
    by the same factor and rounded. One scale per row rather than per
    grid, because a row with small numbers next to a row with large ones
    would otherwise lose all its detail to the large one's scale.
    """
    levels = 2 ** (bits - 1) - 1
    scale = np.abs(grid).max(axis=1, keepdims=True) / levels
    scale[scale == 0] = 1.0
    integers = np.round(grid / scale).astype(np.int64)
    return integers, scale


def dequantize(integers, scale):
    """Back to real numbers, which is what happens on the way into every matrix multiply."""
    return integers * scale


def bytes_for(grid, bits):
    """Storage for the grid at this width, plus one four byte scale per row."""
    return int(grid.size * bits / 8 + grid.shape[0] * 4)


def quantize_grouped(grid, bits=4, group=17):
    """Four bit with a scale per small group, which is what the GGUF and GPTQ families do.

    At four bits there are only fifteen levels, and one scale per row
    wastes most of them on the few large numbers. A scale per group of
    thirty two or so numbers keeps the detail, at the cost of more scales
    to store. This is the knob the file formats differ on. Seventeen here
    because the grid is thirty four wide and the groups have to divide it.
    """
    flat = grid.reshape(-1, group)
    integers, scale = quantize(flat, bits)
    return integers.reshape(grid.shape), scale


def dequantize_grouped(integers, scale, group=17):
    flat = integers.reshape(-1, group)
    return dequantize(flat, scale).reshape(integers.shape)


if __name__ == "__main__":
    words, index = vocabulary(BASE_CORPUS)
    base = pretrain(index)
    xs, ys = pairs(BASE_CORPUS, index)
    print(f"a grid of {base.size} numbers, loss {loss(base, xs, ys):.4f} at 64 bits each")
    print()
    print("bits   bytes   loss     what changed")
    print(f"  64  {base.nbytes:6d}   {loss(base, xs, ys):.4f}   nothing, this is the model")
    for bits in [8, 4]:
        integers, scale = quantize(base, bits)
        back = dequantize(integers, scale)
        size = bytes_for(base, bits)
        print(f"  {bits:2d}  {size:6d}   {loss(back, xs, ys):.4f}   one scale per row")
    integers, scale = quantize_grouped(base, 4, group=17)
    back = dequantize_grouped(integers, scale, group=17)
    grouped_bytes = int(base.size * 4 / 8 + scale.size * 4)
    print(f"   4  {grouped_bytes:6d}   {loss(back, xs, ys):.4f}   one scale per group of 17")
    print()
    worst = np.abs(base - dequantize(*quantize(base, 4))).max()
    print(f"the largest single error at 4 bits with a scale per row is {worst:.3f}")
    print(f"the largest number in the grid is {np.abs(base).max():.3f}")
