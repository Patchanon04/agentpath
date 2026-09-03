# Training 3. Quantization, with the error measured

This folder is the code behind the third chapter of part 4 of the book,
at [book/19-quantization.md](../../book/19-quantization.md). The chapter
stores the chapter 4 grid in eight bits and then four, and measures what
the rounding costs, so that the trade between memory and quality is a
number. This file is the short version for running the code.

The numpy files need no GPU. `load_4bit.py` needs one, and Linux.

## What is here

`grid.py` is unchanged from the previous folder.

`quantize.py` rounds. `quantize` turns each row into integers of a given
width with one scale per row, `dequantize` turns them back, and
`bytes_for` says what the grid then takes. `quantize_grouped` and
`dequantize_grouped` do the four bit version with a scale per small
group, which is what the GGUF and GPTQ families do.

```python
def quantize(grid, bits=8):
    """Round each row to integers of the given width, with one scale per row."""
    levels = 2 ** (bits - 1) - 1
    scale = np.abs(grid).max(axis=1, keepdims=True) / levels
    scale[scale == 0] = 1.0
    integers = np.round(grid / scale).astype(np.int64)
    return integers, scale
```

`load_4bit.py` loads an open model with every grid at four bits and
reports the memory, and with `--train` adds LoRA adapters on top, which
is QLoRA. It is not run in CI.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python quantize.py
```

```text
a grid of 1156 numbers, loss 0.7868 at 64 bits each

bits   bytes   loss     what changed
  64    9248   0.7868   nothing, this is the model
   8    1292   0.7868   one scale per row
   4     714   0.7930   one scale per row
   4     850   0.7898   one scale per group of 17

the largest single error at 4 bits with a scale per row is 0.460
the largest number in the grid is 8.938
```

```bash
python check.py
```

```text
OK at eight bits every number is an integer from minus 127 to 127, one scale per row
OK eight bits costs almost nothing, the loss moves in the third decimal place
OK four bits costs more, and the cost is a number you can read next to the bytes saved
OK a scale per small group keeps more detail at four bits than a scale per row
OK the largest single error is a small fraction of the largest number in the grid
```

On a GPU.

```bash
pip install "agentpath-kit[training]" bitsandbytes
python load_4bit.py --model Qwen/Qwen2.5-7B-Instruct
python load_4bit.py --model Qwen/Qwen2.5-7B-Instruct --train clean.jsonl
```

## What to notice

Eight bits is free. The bytes fall by seven times and the loss does not
move in the fourth decimal place. That is why every serving setup starts
there and why int8 is the default in the next two chapters' arithmetic.

Four bits is not free, and the table shows the trade in both directions.
One scale per row halves the bytes again and costs six thousandths of
loss. One scale per group of seventeen costs three thousandths for a
hundred and thirty six more bytes of scales. On this grid both are fine.
On a real model four bits with one scale per row is usually not, and the
grouped formats exist because of exactly that table.

The last two lines are the mechanism. The largest number in a row sets
the scale, and every other number in the row is rounded to a grid whose
step is that number divided by seven. A row with one large weight and
many small ones loses the small ones, and grouping is the fix.
