# Training 2. LoRA, on a grid you can count

This folder is the code behind the second chapter of part 4 of the book,
at [book/18-lora.md](../../book/18-lora.md). The chapter takes the grid
from foundations chapter 4, fine tunes it two ways on new text, and shows
what LoRA buys and what it does not. This file is the short version for
running the code.

The numpy files need no GPU. `train_lora.py` needs one.

## What is here

`grid.py` is the foundations chapter 4 model, carried into part 4 so every demo here
trains the same thing. Two corpora, the base text and the new text, and
the training functions from foundations. It is also in the next two
folders unchanged.

`lora.py` fine tunes that grid on the new text. `full_finetune` nudges
every number. `lora_finetune` keeps the grid frozen and learns a thin
pair whose product is the change, and `merge` adds the product on so
that the adapter disappears into a plain grid. `parameters` counts.

```python
def lora_finetune(weights, xs, ys, rank=2, steps=300, learning_rate=2.0, seed=0):
    """Keep the grid frozen. Learn a thin pair whose product is the change."""
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
```

`train_lora.py` is the same idea on an open model, with peft adding the
thin pairs beside every attention and feed forward grid and trl running
the loop, on the chat file the previous folder wrote. It is not run in CI.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python lora.py
```

```text
41 words, a grid of 1681 numbers

                    loss on old text   on new text   numbers trained
frozen model                   0.787         3.505                 0
full finetune                  1.924         0.725              1681
lora rank 2                    2.466         0.942               164
lora, old text too             0.922         1.363               164

the change lora made has 2 independent directions in a 41 by
41 grid, and after merging the model is a plain grid again
```

```bash
python check.py
```

```text
OK lora learns the new text nearly as well as nudging every number does
OK and it trains under a tenth of the numbers to do it
OK the change has two independent directions, and merging gives a plain grid back
OK up starts at zero, so before training the adapter changes nothing at all
OK forgetting is real, both methods forget, and mixing the old text back in is the cure
```

On a GPU.

```bash
pip install "agentpath-kit[training]"
python train_lora.py clean.jsonl --output adapter --merge
```

## What to notice

Read the table by columns. The new text column is what fine tuning is
for, and LoRA lands about a fifth of a loss unit behind full fine tuning
there while training 164 numbers instead of 1681. That ratio is the whole reason the
method exists. On a real model the thin pairs are a fraction of a percent
of the weights, and the memory that full fine tuning needs for gradients
and optimiser state, several times the weights themselves, shrinks with them.

Now read the old text column. Both methods got worse on what the model
already knew, and LoRA got worse by more. Forgetting is not something
LoRA fixes, and the last row is what does. Train on the old text too, and
the model keeps 0.922 on the old while still learning the new. The cure
for forgetting is data, not the method.

`up` starts at zero. That is not a detail. It means the adapter is
invisible before training, so step zero is exactly the frozen model, and
every LoRA implementation does it for that reason. `check.py` proves it
by training for zero steps.
