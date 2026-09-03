"""Prove the chapter's arithmetic about serving on this machine."""
import sys

from serving import (
    BYTES_PER_PARAMETER,
    GIGABYTE,
    concurrent_requests,
    decode_tokens_per_second,
    fits,
    kv_bytes_per_token,
    weight_bytes,
)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


gigabytes = weight_bytes("7B", "fp16") / GIGABYTE
if abs(gigabytes - 14.2) > 0.2:
    fail(f"7.6 billion numbers at two bytes should be about 14 GB, not {gigabytes:.0f}")
if weight_bytes("7B", "int4") != weight_bytes("7B", "fp16") / 4:
    fail("four bits should be a quarter of sixteen")
print("OK 7B weights are fourteen gigabytes at sixteen bits and a quarter of that at four bits")

if fits("72B", "fp16", "H100 80GB"):
    fail("a 72B model at sixteen bits is 135 GB and should not fit an 80 GB card")
if not fits("72B", "int4", "H100 80GB"):
    fail("the same model at four bits is 34 GB and should fit")
print("OK a 72B model does not fit one 80 GB card at sixteen bits and does at four")

per_token = kv_bytes_per_token("7B")
expected = 2 * 28 * 4 * 128 * 2
if per_token != expected:
    fail(f"cache per token should be two per layer times heads times head size, got {per_token}")
print("OK the cache costs 56 KB per token of context for the 7B model, from its shape alone")

at_8k = concurrent_requests("7B", "fp16", "RTX 4090", 8192)
at_32k = concurrent_requests("7B", "fp16", "RTX 4090", 32768)
if not at_8k > 0 or at_32k >= at_8k:
    fail(f"longer conversations should mean fewer of them at once, got {at_8k} and {at_32k}")
if concurrent_requests("72B", "fp16", "RTX 4090", 8192) != 0:
    fail("a model that does not fit serves nobody")
print("OK fewer conversations fit as they get longer, and none at all if the weights do not fit")

slow = decode_tokens_per_second("7B", "fp16", "RTX 4090")
fast = decode_tokens_per_second("7B", "int4", "RTX 4090")
if abs(fast / slow - 4) > 1e-6:
    fail("a quarter of the bytes should mean four times the tokens per second")
if not decode_tokens_per_second("7B", "fp16", "H100 80GB") > slow:
    fail("more bandwidth should mean more tokens per second")
widths = [decode_tokens_per_second("7B", w, "RTX 4090") for w in BYTES_PER_PARAMETER]
if widths != sorted(widths):
    fail("narrower should always be faster")
print("OK decode speed is bandwidth over bytes, so a quarter of the bytes is four times the tokens")
