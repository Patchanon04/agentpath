# Foundations 2. What a token is

This folder is the code behind the second foundations chapter of the book,
at [book/00b-tokens.md](../../book/00b-tokens.md). The chapter explains
what a token is and why the same sentence in Thai costs more of them. This
file is the short version for running the code.

No model, no API key, plain Python.

## What is here

`bpe.py` is a byte pair encoding tokenizer written from nothing, the same
algorithm behind every current model. `train` learns merges from a text,
`encode` turns text into ids, `decode` turns them back, and `pieces` shows
each id as the text it stands for. The heart of it is one loop that
replaces a pair with a new id.

```python
def merge(ids, pair, new_id):
    """Replace every occurrence of pair in ids with new_id."""
    out = []
    i = 0
    while i < len(ids):
        if i + 1 < len(ids) and (ids[i], ids[i + 1]) == pair:
            out.append(new_id)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out
```

The file also carries two small corpora, one English and one Thai, because
the experiment is to train on one and encode the other.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python bpe.py
```

```text
== trained on English only, 44 merges ==
  'the agent reads the file'  24 bytes  7 tokens
    ['t', 'he ', 'agent reads', ' the ', 'f', 'i', 'le']
  'agent อ่านไฟล์'  30 bytes  25 tokens
    ['agent ', '<e0>', '<b8>', '<ad>', '<e0>', '<b9>', '<88>', ...]

== trained on both, 44 merges ==
  'the agent reads the file'  24 bytes  9 tokens
  'agent อ่านไฟล์'  30 bytes  9 tokens
    ['a', 'gent ', 'อ่า', '<e0 b8 99 e0 b9>', '<84 e0 b8>', '<9f>', 'ล', '<e0 b9>', '<8c>']
```

```bash
python check.py
```

```text
OK a vocabulary of 300 is 256 bytes plus 44 learned merges
OK before any merge, a token is a byte
OK encode then decode gives the text back
OK the same Thai sentence costs over twice as much under a tokenizer that never saw Thai
OK a token is a run of bytes and can split a character
```

## What to notice

The tokenizer that never saw Thai spends a token on nearly every byte of
it, twenty five tokens for a sentence that costs seven in English. Show it
some Thai and the same sentence drops to nine. The price of a language is
not a property of the language. It is a property of what the tokenizer was
trained on, and the tokenizers behind the models you will call were trained
mostly on English.

The pieces in angle brackets are tokens that end in the middle of a Thai
character. A token is a run of bytes, and nothing in the algorithm knows
where a character ends.
