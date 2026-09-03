# Foundations 5. Meaning as direction

This folder is the code behind the fifth foundations chapter of the book,
at [book/00e-meaning-as-direction.md](../../book/00e-meaning-as-direction.md).
The chapter explains why a word becomes a list of numbers, what it means
for two words to be close, and how a whole document becomes a vector you
can search. This file is the short version for running the code.

No model to call, no API key. `vectors.py` uses numpy, `tfidf.py` does not.

## What is here

`vectors.py` builds the oldest kind of word embedding there is.
`cooccurrence` counts, for every word, which words appeared near it, and
that row of counts is the word's vector. `cosine` compares two vectors by
direction alone, `euclidean` by straight line distance, and `nearest` ranks
every other word by cosine.

```python
def cosine(a, b):
    """How much two vectors point the same way, ignoring how long they are."""
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
```

`tfidf.py` does the same thing for whole documents, the way search engines
did it before embeddings and mostly still do. `bag_of_words` counts the
words in a document and throws the order away. `feature_vocabulary` and
`count_vector` turn that into a row over a fixed vocabulary, and `sparsity`
says how much of the row is zero. `term_frequency`, `inverse_document_frequency`
and `tfidf` weigh a word by how much of the document it is and how rare it is
everywhere else, and `search` ranks the documents for one word.

```python
def tfidf(term, text, documents):
    """Frequent in this document, rare across the rest, is what scores high."""
    return term_frequency(term, text) * inverse_document_frequency(term, documents)
```

`check.py` pins the claims the chapter makes about both files.

## Run it

```bash
python vectors.py
```

```text
nearest to 'cat'
  dog      0.979
  bone     0.928
  fish     0.928
nearest to 'agent'
  model    0.998
  file     0.952
  result   0.952

cat appears 5 times, dog 3
cosine(cat, dog) 0.979   euclidean(cat, dog) 5.74
cosine(cat, file) 0.854   euclidean(cat, file) 7.28
```

```bash
python tfidf.py
```

```text
feature vocabulary ['กบ', 'กระโดด', 'นอน', 'วิ่ง', 'สุนัข', 'หลับ', 'เล่น', 'แมว']
  one    [0, 0, 0, 1, 1, 0, 1, 1]  sparsity 0.50
  two    [0, 0, 1, 0, 0, 1, 0, 1]  sparsity 0.62
  three  [1, 1, 0, 1, 1, 0, 1, 0]  sparsity 0.38

searching for แมว
  two    tf 0.3333  score 0.1352
  one    tf 0.2500  score 0.1014
  three  tf 0.0000  score 0.0000
idf of แมว 0.4055, in two documents of three
idf of กบ 1.0986, in one document of three
```

```bash
python check.py
```

```text
OK words used the same way point the same way, and nobody defined either
OK the two groups in the text are two groups in the space
OK cosine is one for the same direction
OK cosine ignores how common a word is and euclidean does not
OK cat is more common than dog and is still its nearest neighbour
OK a bag of words cannot tell who ate whom
OK the numbers match the worked example, and the shortest document wins
OK a word in every document scores zero, because it points at nothing
```

## What to notice

Nobody defined `cat`. The nearest word to it is `dog` because the two keep
the same company, and that is the whole idea. Meaning, for a machine, is
the company a word keeps, written as a direction.

`cat` and `file` still score 0.854 with nothing in common, because both
live next to `the`, and `the` lives next to everything. `tfidf.py` is the
fix. A word that appears in every document gets an inverse document
frequency of zero and drops out of every score. That is the idea lesson 16
uses under the name rarity when `search_notes` ranks paragraphs.

The count vectors are mostly zeros, and in a real vocabulary of tens of
thousands of words they are almost entirely zeros. That is what sparse
means, and storing only the positions that are not zero is what makes
searching a million documents by word affordable.
