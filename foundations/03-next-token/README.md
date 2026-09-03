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

The rest of the file is the other ways of choosing a word, because every
API exposes them and they are all one question, how much of the
distribution to trust. `next_word_top_k` keeps a fixed number of words.
`nucleus` and `next_word_top_p` keep as many words as it takes to cover a
share of the probability, so the cut moves with the model's confidence.
`log_probability` scores a whole sequence, and `beam_search` uses it to
keep the few most probable sequences alive at every step instead of
committing to one word.

```python
def nucleus(counts, p=0.9):
    """The most likely words, taken in order until their probabilities reach p."""
    ranked = sorted(probabilities(counts).items(), key=lambda pair: -pair[1])
    kept, total = [], 0.0
    for word, probability in ranked:
        kept.append((word, probability))
        total += probability
        if total >= p:
            break
    return kept
```

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

top p of 0.8 after 'the' keeps 6 words ['agent', 'model', 'file', 'tool', 'result', 'loop']
top p of 0.8 after 'the agent' keeps 2 words ['reads', 'decides']

greedy    -6.819  the agent reads the agent reads the agent reads the agent reads the
beam      -6.182  the agent decides what to do . the agent decides what to do
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
OK top p keeps fewer words where the model is sure and more where it is not
OK beam search finds a more probable sentence than greedy, and it repeats a whole phrase
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

Top p with the same setting keeps six words after `the` and two after
`the agent`. Nobody changed the knob. The model was surer in the second
place, so the same share of probability took fewer words to cover, and
that is why top p is the default most APIs ship with. Top k would have
kept the same number in both.

The last two lines are why chat models sample instead of searching. Beam
search found a sentence with a higher probability than greedy decoding,
and the sentence it found says the same six words twice. The most
probable text in a language is repetitive text. A model that always
picked the most probable continuation would be right more often and
worth reading less often, which is the trade every chat product has made.
