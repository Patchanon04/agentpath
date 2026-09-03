"""A language model in fifty lines, so the phrase stops being magic.

A language model does one thing. Given what came before, it gives every
possible next token a probability. The chat, the apparent memory and the
personality are all built on top of that one thing, and this file has the
whole of it in a form you can read in one sitting.

It works on words rather than the tokens of the previous chapter, only
because words are easier to read on the page. Swap in token ids and not
one line of the model changes.
"""
import random
from collections import Counter, defaultdict

CORPUS = """
the agent reads the file and the agent decides what to do . the agent runs
the tool and the tool returns a result . the agent reads the result and
the agent decides again . the loop ends when the model stops asking for a
tool . the model never remembers the last turn . the model reads the whole
conversation every turn . the conversation grows and the cost grows with it .
the agent reads the file . the agent reads the result . the agent decides .
"""


def words(text):
    """The units this model counts. A real model would use tokens here."""
    return text.split()


def train(text, n=2):
    """Count what follows each run of n minus one words.

    That is the entire training. There is no cleverness, only a table of
    what came after what, and n is the only choice being made. With n=2
    the table remembers one word of context. With n=3 it remembers two.
    """
    following = defaultdict(Counter)
    tokens = words(text)
    for i in range(len(tokens) - n + 1):
        context = tuple(tokens[i : i + n - 1])
        following[context][tokens[i + n - 1]] += 1
    return following


def probabilities(counts):
    """Turn counts into a distribution that sums to one."""
    total = sum(counts.values())
    return {word: count / total for word, count in counts.items()}


def next_word(model, context, temperature=1.0, rng=random):
    """Choose the next word given the context, or None if it is unknown.

    Temperature reshapes the counts before the draw. At zero the most
    likely word always wins. At one the counts are used as they are. Above
    one the gap between likely and unlikely shrinks and the model takes
    more chances. This is the same knob the API calls temperature.
    """
    counts = model.get(tuple(context))
    if not counts:
        return None
    if temperature == 0:
        return max(counts, key=counts.get)
    weights = [count ** (1 / temperature) for count in counts.values()]
    return rng.choices(list(counts), weights=weights, k=1)[0]


def next_word_top_k(model, context, k=2, rng=random):
    """Draw only from the k most likely words. This is the knob called top k.

    Temperature reshapes the whole distribution. Top k cuts it off, so the
    long tail of unlikely words can never be drawn no matter how the dice
    fall. Top p is the same idea with a different cut, keep the most likely
    words until their probabilities add up to p. APIs offer all three and
    they are all ways of deciding how much of the distribution to trust.
    """
    counts = model.get(tuple(context))
    if not counts:
        return None
    kept = sorted(counts.items(), key=lambda pair: -pair[1])[:k]
    return rng.choices([word for word, _ in kept], weights=[n for _, n in kept], k=1)[0]


def generate(model, start, n=2, length=12, temperature=1.0, rng=random):
    """Predict, append, repeat. This loop is the ancestor of the agent loop."""
    out = list(start)
    for _ in range(length):
        word = next_word(model, out[-(n - 1) :], temperature, rng)
        if word is None:
            break
        out.append(word)
    return " ".join(out)


if __name__ == "__main__":
    bigram = train(CORPUS, n=2)
    print("after 'the' the model has seen", dict(bigram[("the",)]))
    print("as probabilities", probabilities(bigram[("the",)]))
    print()
    for temperature in [0, 1.0, 2.0]:
        rng = random.Random(7)
        print(f"temperature {temperature}")
        print("  ", generate(bigram, ["the"], n=2, temperature=temperature, rng=rng))
    print()
    trigram = train(CORPUS, n=3)
    seen = dict(trigram[("the", "agent")])
    print("with two words of context, after 'the agent' it has seen", seen)
    print("  ", generate(trigram, ["the", "agent"], n=3, temperature=1.0, rng=random.Random(7)))
