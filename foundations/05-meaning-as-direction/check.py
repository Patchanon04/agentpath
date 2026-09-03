"""Prove the chapter's claims about vectors on this machine."""
import sys

import skipgram
from tfidf import DOCUMENTS, bag_of_words, inverse_document_frequency, search, term_frequency
from vectors import CORPUS, cooccurrence, cosine, euclidean, nearest


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


grid, index = cooccurrence(CORPUS)
cat, dog, agent, model, file = (grid[index[w]] for w in ["cat", "dog", "agent", "model", "file"])

if nearest("cat", grid, index)[0][0] != "dog":
    fail(f"the nearest word to cat should be dog, got {nearest('cat', grid, index)}")
if nearest("agent", grid, index)[0][0] != "model":
    fail(f"the nearest word to agent should be model, got {nearest('agent', grid, index)}")
print("OK words used the same way point the same way, and nobody defined either")

if not cosine(cat, dog) > cosine(cat, file):
    fail("cat should be closer to dog than to file")
if not cosine(agent, model) > cosine(agent, dog):
    fail("agent should be closer to model than to dog")
print("OK the two groups in the text are two groups in the space")

if abs(cosine(cat, cat) - 1.0) > 1e-9:
    fail("a vector should have cosine one with itself")
print("OK cosine is one for the same direction")

if abs(cosine(cat, dog) - cosine(3 * cat, dog)) > 1e-9:
    fail("scaling a vector should not change its cosine with anything")
if abs(euclidean(cat, dog) - euclidean(3 * cat, dog)) < 1e-9:
    fail("scaling a vector should change its euclidean distance")
print("OK cosine ignores how common a word is and euclidean does not")

if grid[index["cat"]].sum() <= grid[index["dog"]].sum():
    fail("the test assumes cat appears more often than dog in the text")
print("OK cat is more common than dog and is still its nearest neighbour")

if bag_of_words("แมว กิน ปลา") != bag_of_words("ปลา กิน แมว"):
    fail("two sentences with the same words should be the same bag")
print("OK a bag of words cannot tell who ate whom")

ranked = search("แมว", DOCUMENTS)
if ranked[0][0] != "two" or abs(ranked[0][1] - 0.1352) > 0.0005:
    fail(f"expected document two to win with 0.1352, got {ranked[0]}")
if abs(term_frequency("แมว", DOCUMENTS["one"]) - 0.25) > 1e-9:
    fail("แมว is one word of four in document one")
if abs(inverse_document_frequency("แมว", DOCUMENTS) - 0.4055) > 0.0005:
    fail("idf of a word in two documents of three should be log of three halves")
print("OK the numbers match the worked example, and the shortest document wins")

everywhere = {name: text + " และ" for name, text in DOCUMENTS.items()}
if inverse_document_frequency("และ", everywhere) != 0.0:
    fail("a word in every document should have idf zero")
if any(score != 0.0 for _, score in search("และ", everywhere)):
    fail("a word in every document should score zero for every document")
print("OK a word in every document scores zero, because it points at nothing")

embedding, learned_index, history = skipgram.train(CORPUS)
if embedding.shape != (len(index), 8) or grid.shape != (len(index), len(index)):
    fail(f"learned vectors should be 8 wide and counted ones {len(index)}, got {embedding.shape}")
if not history[-1] < history[0]:
    fail("guessing neighbours should get better with training")
print("OK the learned vectors are eight numbers wide and the counted ones are twenty five")

learned_cat_near = skipgram.nearest("cat", embedding, learned_index)
learned_agent_near = skipgram.nearest("agent", embedding, learned_index, count=2)
if learned_cat_near[0][0] != "dog":
    fail(f"learned cat should still be nearest dog, got {learned_cat_near}")
if "model" not in [w for w, _ in learned_agent_near]:
    fail(f"learned agent should have model among its two nearest, got {learned_agent_near}")
print("OK guessing neighbours finds the groups that counting found, in a third of the numbers")

learned_cat, learned_file = embedding[learned_index["cat"]], embedding[learned_index["file"]]
if not cosine(learned_cat, learned_file) < cosine(cat, file):
    fail("learned vectors should be less pulled together by 'the' than counted ones")
print("OK the word next to everything pulls the learned vectors together less than the counted")
