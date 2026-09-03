"""Prove the chapter's claims about next word prediction on this machine."""
import random
import sys

from ngram import (
    CORPUS,
    beam_search,
    generate,
    log_probability,
    next_word,
    next_word_top_k,
    next_word_top_p,
    nucleus,
    probabilities,
    train,
)


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

flat = len(nucleus(bigram[("the",)], p=0.8))
sure = len(nucleus(trigram[("the", "agent")], p=0.8))
if not sure < flat:
    fail(f"top p should keep fewer words where the model is surer, kept {sure} and {flat}")
if next_word_top_p(bigram, ["the"], p=0.01) != max(after_the, key=after_the.get):
    fail("a tiny p should keep only the single most likely word")
drawn = {next_word_top_p(bigram, ["the"], p=0.8, rng=random.Random(seed)) for seed in range(200)}
if not drawn <= {word for word, _ in nucleus(after_the, p=0.8)}:
    fail(f"top p drew a word outside the nucleus {drawn}")
print("OK top p keeps fewer words where the model is sure and more where it is not")

greedy = generate(bigram, ["the"], n=2, temperature=0).split()
beam = beam_search(bigram, ["the"], n=2, beams=3).split()
if not log_probability(bigram, beam) >= log_probability(bigram, greedy):
    fail("beam search should find a sequence at least as probable as greedy")
phrases = [tuple(beam[i : i + 5]) for i in range(len(beam) - 4)]
if len(set(phrases)) == len(phrases):
    fail(f"the most probable sequence should repeat a whole phrase, got {beam}")
print("OK beam search finds a more probable sentence than greedy, and it repeats a whole phrase")
