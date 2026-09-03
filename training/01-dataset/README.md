# Training 1. The data is the fine tune

This folder is the code behind the first chapter of part 4 of the book,
at [book/17-dataset.md](../../book/17-dataset.md). The chapter says that a
fine tuning run is a few lines of training code and a long list of
decisions about the data, and that the decisions are where runs go
wrong. This file is the short version for running the code.

No model to call, no API key, no GPU, plain Python.

## What is here

`dataset.py` is the decisions, as functions, on seven chat examples that
have the problems real datasets have. `normalise` makes cosmetic
differences invisible. `exact_dedupe` drops copies, `near_dedupe` drops
near copies by comparing runs of words, `decontaminate` drops anything
that is an evaluation question, and `quality_filter` drops answers too
short to teach anything. `to_chat_jsonl` writes what survives in the
shape the trainers of the next chapters read, and `clean` runs the whole
pipeline with a count at every step.

```python
def near_dedupe(examples, threshold=0.8):
    """Drop an example whose prompt shares most of its word runs with one already kept."""
    kept = []
    for example in examples:
        mine = shingles(example["prompt"])
        if all(jaccard(mine, shingles(other["prompt"])) < threshold for other in kept):
            kept.append(example)
    return kept
```

`build_dataset.py` is the same pipeline over a real JSONL file, with an
evaluation file to keep out and an output the next chapter trains on. It
runs anywhere, because this is the part of fine tuning that needs no GPU.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python dataset.py
```

```text
started with 7 examples
  dropped 1 for exact duplicates
  dropped 1 for near duplicates
  dropped 1 for evaluation questions
  dropped 1 for answers too short
kept 3

the first line of the file a trainer would read
{"messages": [{"role": "system", "content": "You are a careful software assistant."}, {"role": "user", "content": "Rename the variable x to total in math.py"}, {"role": "assistant", "content": "Edited math.py, x is now total in both places it appeared."}]}
```

```bash
python check.py
```

```text
OK an exact duplicate is dropped after normalising, so a full stop does not hide it
OK a near duplicate that exact matching misses is caught by comparing word runs
OK an example that is an evaluation question is removed, so the score cannot lie
OK the answer too short to teach anything is dropped, and the filter says how many
OK what a trainer reads is the same messages list the course sends over HTTP, one per line
OK seven examples in, three out, and the report says where every one of the four went
```

On a real file.

```bash
python build_dataset.py raw.jsonl clean.jsonl --eval eval.jsonl
```

## What to notice

Seven in, three out, and every one of the four that left is named. A
pipeline that drops half the data silently is a pipeline nobody notices
until the model is worse, and the report is the whole defence.

The near duplicate is the one people miss. `Please rename the variable x`
and `Rename the variable x` are not the same string, and exact matching
keeps both. They share six of seven runs of three words, and that is
enough. The real pipelines do this with MinHash so that a million examples
can be compared, and the idea is the same, compare word runs rather than
whole strings.

The last line of the run is the messages list from lesson 01, on disk.
The trainer applies the model's chat template to it, foundations chapter
7 at full size, so the text the model learns from is the exact string it
will see when the course calls it.
