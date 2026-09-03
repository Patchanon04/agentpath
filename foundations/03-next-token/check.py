"""Prove the chapter's claims about next word prediction on this machine."""
import random
import sys

from ngram import CORPUS, generate, next_word, next_word_top_k, probabilities, train


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


bigram = train(CORPUS, n=2)
after_the = bigram[("the",)]
if sum(after_the.values()) != CORPUS.split().count("the"):
    fail("the counts after 'the' do not add up to the number of times 'the' appears")
if abs(sum(probabilities(after_the).values()) - 1.0) > 1e-9:
    fail("probabilities after 'the' do not sum to one")
print("OK the model is a table of counts and the counts become probabilities")

greedy = {next_word(bigram, ["the"], temperature=0) for _ in range(20)}
if greedy != {max(after_the, key=after_the.get)}:
    fail(f"temperature zero should always pick the most likely word, got {greedy}")
print("OK at temperature zero the same context always gives the same word")

first = generate(bigram, ["the"], rng=random.Random(7))
second = generate(bigram, ["the"], rng=random.Random(7))
if first != second:
    fail("the same seed gave different text, so sampling is not the only randomness")
print("OK the randomness is the sampling and nothing else")

if next_word(bigram, ["banana"]) is not None:
    fail("a word the model never saw should have no prediction")
print("OK the model knows nothing it did not count")

trigram = train(CORPUS, n=3)
choices_bigram = sum(len(counts) for counts in bigram.values()) / len(bigram)
choices_trigram = sum(len(counts) for counts in trigram.values()) / len(trigram)
if choices_trigram >= choices_bigram:
    fail(
        "more context should leave fewer choices, "
        f"got {choices_bigram:.2f} then {choices_trigram:.2f}"
    )
print("OK more context means fewer choices, and the context is the model's only memory")

top_two = {max(after_the, key=after_the.get)}
ranked = sorted(after_the, key=after_the.get, reverse=True)
allowed = set(ranked[:2])
drawn = {next_word_top_k(bigram, ["the"], k=2, rng=random.Random(seed)) for seed in range(200)}
if not drawn <= allowed or not top_two <= drawn:
    fail(f"top k of two should only ever draw from {allowed}, drew {drawn}")
print("OK top k cuts the tail off, so a word outside the k most likely can never be drawn")
