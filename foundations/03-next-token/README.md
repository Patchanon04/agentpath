# Foundations 3. A model predicts the next word

This folder is the code behind the third foundations chapter of the book,
at [book/00c-next-token.md](../../book/00c-next-token.md). The chapter
says what a language model actually does, in one sentence, and then builds
one in fifty lines by counting. This file is the short version for running
the code.

No model to call, no API key, plain Python.

## What is here

`ngram.py` holds the model. `train` counts what follows each run of words,
`probabilities` turns counts into a distribution, `next_word` draws from it
with a temperature, and `generate` predicts, appends and repeats. The loop
in `generate` is the ancestor of the agent loop the course builds.

```python
def generate(model, start, n=2, length=12, temperature=1.0, rng=random):
    """Predict, append, repeat. This loop is the ancestor of the agent loop."""
    out = list(start)
    for _ in range(length):
        word = next_word(model, out[-(n - 1) :], temperature, rng)
        if word is None:
            break
        out.append(word)
    return " ".join(out)
```

It works on words rather than the tokens of the previous chapter, only
because words are easier to read on the page.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python ngram.py
```

```text
after 'the' the model has seen {'agent': 8, 'file': 2, 'tool': 2, 'result': 2, 'loop': 1, ...}

temperature 0
   the agent reads the agent reads the agent reads the agent reads the
temperature 1.0
   the agent reads the agent decides again . the agent reads the agent
temperature 2.0
   the tool and the agent decides again . the agent decides what to

with two words of context, after 'the agent' it has seen {'reads': 4, 'decides': 3, 'runs': 1}
   the agent reads the result and the agent reads the file and the agent
```

```bash
python check.py
```

```text
OK the model is a table of counts and the counts become probabilities
OK at temperature zero the same context always gives the same word
OK the randomness is the sampling and nothing else
OK the model knows nothing it did not count
OK more context means fewer choices, and the context is the model's only memory
OK top k cuts the tail off, so a word outside the k most likely can never be drawn
```

## What to notice

At temperature zero the model repeats itself forever, because after `the`
the most likely word is `agent` and after `agent` it is `reads` and after
`reads` it is `the`. That is a model stuck in a loop, and you will meet the
same shape in chapter 2 of the book as the doom loop, built from a model a
billion times larger.

The model's entire memory is the context you hand it. With one word of
context it knows ten things that can follow `the`. With two words it knows
three things that can follow `the agent`. Nothing else is remembered
between predictions, which is the fact the whole book rests on.
