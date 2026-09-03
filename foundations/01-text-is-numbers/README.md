# Foundations 1. Text is numbers

This folder is the code behind the first foundations chapter of the book,
which explains why a computer never sees letters and what it sees instead.
The chapter is in Thai at [book/00a-text-is-numbers.md](../../book/00a-text-is-numbers.md).
This file is the short version for running the code.

Nothing here talks to a model. There is no API key to set. It is plain
Python and it runs anywhere Python runs.

## What is here

`text.py` holds four small functions. `code_points` gives the Unicode number
of each character, `utf8_bytes` gives the bytes that actually get stored or
sent, `cost` counts both and divides, and `combining_marks` picks out the
characters that are marks stacked on a letter rather than letters themselves.

```python
def cost(text):
    """Characters, bytes, and how many bytes each character cost on average."""
    characters = len(text)
    byte_count = len(text.encode("utf-8"))
    return {
        "characters": characters,
        "bytes": byte_count,
        "bytes_per_character": byte_count / characters if characters else 0.0,
    }
```

`check.py` asserts the numbers the chapter quotes, so that if they are ever
wrong on your machine you find out here rather than by trusting the page.

## Run it

```bash
python text.py
```

That prints every character of `hello` and of `สวัสดี` with its code point
and its bytes. Then run the check.

```bash
python check.py
```

```text
OK hello costs one byte per character and สวัสดี costs three
OK the code point and the bytes match the chapter
OK two of the six characters are marks stacked on a consonant
OK bytes turn back into the same text
```

## What to notice

`สวัสดี` is six characters and eighteen bytes. `hello` is five and five. Same
number of things you would say, three times the storage, and this is before
a model has touched anything. The next foundations chapter shows the same
gap opening again at the token level, which is the one that costs money.
