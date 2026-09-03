"""Prove the chapter's claims about the data on this machine."""
import json
import sys

from dataset import (
    EVAL_PROMPTS,
    EXAMPLES,
    clean,
    decontaminate,
    exact_dedupe,
    jaccard,
    quality_filter,
    shingles,
    to_chat_jsonl,
)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


kept, report = clean(EXAMPLES)
dropped = dict(report)

if dropped["exact duplicates"] != 1 or len(exact_dedupe(EXAMPLES)) != len(EXAMPLES) - 1:
    fail(f"two examples are the same after normalising, one should go, dropped {dropped}")
print("OK an exact duplicate is dropped after normalising, so a full stop does not hide it")

original = shingles("Rename the variable x to total in math.py")
polite = shingles("Please rename the variable x to total in math.py")
if jaccard(original, polite) < 0.8:
    fail(f"the polite copy should share most word runs, got {jaccard(original, polite):.2f}")
if dropped["near duplicates"] != 1:
    fail(f"the polite copy should have gone as a near duplicate, dropped {dropped}")
print("OK a near duplicate that exact matching misses is caught by comparing word runs")

if dropped["evaluation questions"] != 1:
    fail(f"one example is an eval question and should have gone, dropped {dropped}")
if any(example["prompt"] in EVAL_PROMPTS for example in kept):
    fail("an evaluation question survived into the training set")
if len(decontaminate(EXAMPLES, set())) != len(EXAMPLES):
    fail("with no eval set nothing should be dropped")
print("OK an example that is an evaluation question is removed, so the score cannot lie")

if dropped["answers too short"] != 1 or any(len(e["answer"].split()) < 4 for e in kept):
    fail(f"the one word answer should have gone, dropped {dropped}")
if len(quality_filter(EXAMPLES, minimum_answer_words=0)) != len(EXAMPLES):
    fail("a filter with no minimum should keep everything")
print("OK the answer too short to teach anything is dropped, and the filter says how many")

lines = to_chat_jsonl(kept).splitlines()
if len(lines) != len(kept):
    fail("one example should be one line")
first = json.loads(lines[0])
roles = [message["role"] for message in first["messages"]]
if roles != ["system", "user", "assistant"]:
    fail(f"each line should be system then user then assistant, got {roles}")
print("OK what a trainer reads is the same messages list the course sends over HTTP, one per line")

if len(kept) != 3:
    fail(f"seven examples should come out as three, got {len(kept)}")
print("OK seven examples in, three out, and the report says where every one of the four went")
