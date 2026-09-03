"""The same pipeline on a real file, which is the version you would actually run.

dataset.py works on a list in memory so every step can be read. This
runs the same functions over a JSONL file of prompt and answer pairs,
writes the cleaned chat file the trainers in the next chapters read,
and prints the report. Nothing here needs a GPU or a model. It is the
part of fine tuning that decides whether the GPU time is wasted.

    python build_dataset.py raw.jsonl clean.jsonl --eval eval.jsonl
"""
import argparse
import json
from pathlib import Path

from dataset import clean, to_chat_jsonl


def read_jsonl(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("raw", help="JSONL with a prompt and an answer per line")
    parser.add_argument("out", help="where to write the cleaned chat JSONL")
    parser.add_argument("--eval", help="JSONL of evaluation prompts to keep out of training")
    parser.add_argument("--system", default="You are a careful software assistant.")
    arguments = parser.parse_args(argv)

    examples = read_jsonl(arguments.raw)
    eval_prompts = set()
    if arguments.eval:
        eval_prompts = {row["prompt"] for row in read_jsonl(arguments.eval)}
    kept, report = clean(examples, eval_prompts)
    Path(arguments.out).write_text(to_chat_jsonl(kept, arguments.system), encoding="utf-8")

    print(f"read {len(examples)} examples from {arguments.raw}")
    for name, dropped in report:
        print(f"  dropped {dropped} for {name}")
    print(f"wrote {len(kept)} to {arguments.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
