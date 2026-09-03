"""Prove the chapter's claims about vectors on this machine."""
import sys

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
