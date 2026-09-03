"""Prove the chapter's claims about tokens on this machine."""
import sys

from bpe import ENGLISH, THAI, decode, encode, pieces, train


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


english_only = train(ENGLISH, 300)
both = train(ENGLISH + THAI, 300)
if len(english_only) != 44 or len(both) != 44:
    fail(f"expected 44 merges each, got {len(english_only)} and {len(both)}")
print("OK a vocabulary of 300 is 256 bytes plus 44 learned merges")

if encode("hello", {}) != list(b"hello"):
    fail("with no merges, the ids should be exactly the bytes")
print("OK before any merge, a token is a byte")

for sentence in ["the agent reads the file", "agent อ่านไฟล์", "สวัสดี"]:
    if decode(encode(sentence, both), both) != sentence:
        fail(f"round trip changed {sentence!r}")
print("OK encode then decode gives the text back")

english = encode("the agent reads the file", english_only)
if len(english) >= 24:
    fail(f"English did not compress, {len(english)} tokens for 24 bytes")
thai_naive = encode("agent อ่านไฟล์", english_only)
thai_learned = encode("agent อ่านไฟล์", both)
if len(thai_naive) < 2 * len(thai_learned):
    fail(
        "expected Thai to cost far more under the English tokenizer, "
        f"got {len(thai_naive)} against {len(thai_learned)}"
    )
print("OK the same Thai sentence costs over twice as much under a tokenizer that never saw Thai")

if not any(piece.startswith("<") for piece in pieces(thai_learned, both)):
    fail("expected at least one token that ends in the middle of a character")
print("OK a token is a run of bytes and can split a character")
