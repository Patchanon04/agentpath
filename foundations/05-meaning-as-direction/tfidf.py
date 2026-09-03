"""A document as a vector, and why the common words have to be weighed down.

vectors.py gave a word a vector from its neighbours. This file gives a whole
document a vector from the words in it, which is the oldest way to search
and is still under most search engines. Bag of words counts. TF-IDF
corrects the counts for words that appear everywhere, which is the fix the
chapter promised for the word the, and the idea lesson 16 uses under the
name rarity.

The documents are already split into words with spaces, because Thai has
no spaces of its own and word segmentation is a problem of its own that
this file does not solve.
"""
import math
from collections import Counter

DOCUMENTS = {
    "one": "สุนัข แมว วิ่ง เล่น",
    "two": "แมว นอน หลับ",
    "three": "สุนัข เล่น วิ่ง กบ กระโดด",
}


def bag_of_words(text):
    """A document as counts, with the order thrown away.

    The name is honest. Tip the words into a bag and shake it. แมวกินปลา
    and ปลากินแมว are the same bag, which is the limit of this idea and
    the reason attention exists.
    """
    return Counter(text.split())


def feature_vocabulary(documents):
    """Every distinct word across the documents, in a fixed order.

    A word that occurs is a token. A distinct word is a type. The types
    become the features, one column each, and every document vector has
    exactly this many columns whether or not it uses them.
    """
    types = set()
    for text in documents.values():
        types |= set(text.split())
    return sorted(types)


def count_vector(text, features):
    """One document as a row of counts over the feature vocabulary."""
    bag = bag_of_words(text)
    return [bag.get(feature, 0) for feature in features]


def sparsity(vector):
    """The share of positions that are zero.

    With a real vocabulary of tens of thousands and a document that uses
    a few hundred, nearly every position is zero. Storing only the ones
    that are not is what makes lexical search cheap at scale.
    """
    return sum(1 for value in vector if value == 0) / len(vector)


def term_frequency(term, text):
    """How much of this document is this word."""
    words = text.split()
    return words.count(term) / len(words)


def inverse_document_frequency(term, documents):
    """How rare the word is across all the documents, as a log.

    A word in every document scores log of one, which is zero. It tells
    you nothing about which document you want. A word in one document out
    of three scores log of three. The log keeps the range sane.
    """
    containing = sum(1 for text in documents.values() if term in text.split())
    return math.log(len(documents) / containing) if containing else 0.0


def tfidf(term, text, documents):
    """Frequent in this document, rare across the rest, is what scores high."""
    return term_frequency(term, text) * inverse_document_frequency(term, documents)


def search(term, documents):
    """Rank every document for one word, best first."""
    scored = [(name, tfidf(term, text, documents)) for name, text in documents.items()]
    return sorted(scored, key=lambda pair: -pair[1])


if __name__ == "__main__":
    features = feature_vocabulary(DOCUMENTS)
    print("feature vocabulary", features)
    for name, text in DOCUMENTS.items():
        vector = count_vector(text, features)
        print(f"  {name:6s} {vector}  sparsity {sparsity(vector):.2f}")
    print()
    print("searching for แมว")
    for name, score in search("แมว", DOCUMENTS):
        tf = term_frequency("แมว", DOCUMENTS[name])
        print(f"  {name:6s} tf {tf:.4f}  score {score:.4f}")
    for word, where in [("แมว", "two documents of three"), ("กบ", "one document of three")]:
        print(f"idf of {word} {inverse_document_frequency(word, DOCUMENTS):.4f}, in {where}")
