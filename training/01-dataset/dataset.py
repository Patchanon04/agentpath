"""Dataset engineering, which is most of fine tuning and gets the least attention.

Every fine tuning run is a small number of lines of training code and a
large number of decisions about the data. Which examples to keep, which
are duplicates, which leaked in from the test set, and what shape each
one takes. The functions here are those decisions written down, on a
list of chat examples small enough to read, and every one of them is
what the real pipelines do at scale with the same logic.
"""
import hashlib
import json

# A dataset of chat examples, the shape every instruction tuning run wants.
# It has the problems real datasets have. An exact duplicate, a near
# duplicate, an answer that is far too short, and one that is a copy of an
# evaluation question, which would make the eval score a lie.
EXAMPLES = [
    {
        "prompt": "Rename the variable x to total in math.py",
        "answer": "Edited math.py, x is now total in both places it appeared.",
    },
    {
        "prompt": "Rename the variable x to total in math.py",
        "answer": "Edited math.py, x is now total in both places it appeared.",
    },
    {
        "prompt": "Please rename the variable x to total in math.py",
        "answer": "Done, x is now total in both places it appeared in math.py.",
    },
    {"prompt": "Add a test for the add function", "answer": "ok"},
    {
        "prompt": "Why does the retry helper not wrap tool calls?",
        "answer": (
            "Because a tool call can have a side effect, and retrying it repeats the "
            "side effect. Retrying the model call is safe because it has none."
        ),
    },
    {
        "prompt": "List the files in the workspace",
        "answer": "Ran list_files. The workspace holds math.py, test_math.py and README.md.",
    },
    {
        "prompt": "Delete everything and start again",
        "answer": (
            "I will not do that. Deleting the workspace is not something I run without "
            "you confirming each file, and there is no way to confirm all of them at once."
        ),
    },
]

EVAL_PROMPTS = {"Why does the retry helper not wrap tool calls?"}


def normalise(text):
    """Lower case, one space between words, no trailing punctuation.

    Two examples that differ only in a full stop or a capital are the same
    example, and a model shown both learns that the example is twice as
    important as it is. Normalising before comparing is what makes the
    next two functions see through cosmetic differences.
    """
    return " ".join(text.lower().split()).rstrip(".!?")


def fingerprint(example):
    """A short hash of the normalised prompt and answer together."""
    joined = normalise(example["prompt"]) + "\n" + normalise(example["answer"])
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def exact_dedupe(examples):
    """Keep the first of every group of examples that are the same after normalising."""
    seen = set()
    kept = []
    for example in examples:
        key = fingerprint(example)
        if key not in seen:
            seen.add(key)
            kept.append(example)
    return kept


def shingles(text, size=3):
    """Every run of `size` consecutive words, which is what near duplicate detection compares."""
    words = normalise(text).split()
    return {" ".join(words[i : i + size]) for i in range(max(1, len(words) - size + 1))}


def jaccard(a, b):
    """How much two sets overlap, from zero to one."""
    return len(a & b) / len(a | b) if a | b else 0.0


def near_dedupe(examples, threshold=0.8):
    """Drop an example whose prompt shares most of its word runs with one already kept.

    Exact matching misses the near copies, and real datasets scraped from
    the same sources are full of them. The comparison here is every pair,
    which is fine for a hundred examples and hopeless for a million. The
    real pipelines hash the shingles into short signatures so that near
    duplicates land in the same bucket, which is called MinHash, and the
    idea is the same. Compare word runs, not whole strings.
    """
    kept = []
    for example in examples:
        mine = shingles(example["prompt"])
        if all(jaccard(mine, shingles(other["prompt"])) < threshold for other in kept):
            kept.append(example)
    return kept


def decontaminate(examples, eval_prompts):
    """Drop every example whose prompt is an evaluation question.

    A model that has seen the test in training scores well on the test
    and learned nothing, and the score is then a lie you will make
    decisions on. This is the check that stops it, and it has to run
    against the eval set you actually use, not one you intend to write.
    """
    banned = {normalise(prompt) for prompt in eval_prompts}
    return [example for example in examples if normalise(example["prompt"]) not in banned]


def quality_filter(examples, minimum_answer_words=4):
    """Drop answers too short to have taught anything.

    Real filters are longer lists. Answers in the wrong language, answers
    that are only a link, answers a classifier scores as low quality. The
    shape is the same, a function that returns true or false per example
    and a count of what it dropped, because a filter that silently removes
    half the data is a filter nobody will notice until the model is worse.
    """
    return [
        example for example in examples if len(example["answer"].split()) >= minimum_answer_words
    ]


def to_chat_jsonl(examples, system="You are a careful software assistant."):
    """One JSON object per line in the messages shape the trainers read.

    This is the same list of role and content the whole course sends over
    HTTP, written to disk. The trainer applies the model's chat template
    from foundations chapter 7 to each line, so the text the model learns
    from is the exact string it will see at inference.
    """
    lines = []
    for example in examples:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": example["prompt"]},
            {"role": "assistant", "content": example["answer"]},
        ]
        lines.append(json.dumps({"messages": messages}, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def clean(examples, eval_prompts=EVAL_PROMPTS):
    """The whole pipeline, in the order that matters, with a count at each step."""
    steps = [
        ("exact duplicates", exact_dedupe),
        ("near duplicates", near_dedupe),
        ("evaluation questions", lambda rows: decontaminate(rows, eval_prompts)),
        ("answers too short", quality_filter),
    ]
    report = []
    current = list(examples)
    for name, step in steps:
        before = len(current)
        current = step(current)
        report.append((name, before - len(current)))
    return current, report


if __name__ == "__main__":
    kept, report = clean(EXAMPLES)
    print(f"started with {len(EXAMPLES)} examples")
    for name, dropped in report:
        print(f"  dropped {dropped} for {name}")
    print(f"kept {len(kept)}")
    print()
    print("the first line of the file a trainer would read")
    print(to_chat_jsonl(kept).splitlines()[0])
