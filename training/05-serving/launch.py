"""Check the arithmetic before renting the card, then print the command that serves the model.

serving.py is the multiplication. This is the multiplication applied to
a model and a card you name, followed by the vLLM command that would
serve it as an OpenAI compatible endpoint, which is the same endpoint
shape lesson 01 of the course called and the mock server imitates. The
whole course then runs against your own model by changing one
environment variable, AGENTPATH_BASE_URL.

This file runs anywhere and starts nothing. It prints. Copy the command
to a machine with the card and vLLM installed.

    python launch.py --model 7B --card "RTX 4090" --width int4 --context 8192
"""
import argparse

from serving import (
    CARDS,
    GIGABYTE,
    MODELS,
    concurrent_requests,
    decode_tokens_per_second,
    fits,
    weight_bytes,
)

# The names vLLM and the hub use for the shapes in serving.py, and the
# flag that asks vLLM for each width. Four bit here is AWQ, one of the
# grouped formats from chapter 3.
CHECKPOINTS = {
    "0.5B": {"fp16": "Qwen/Qwen2.5-0.5B-Instruct", "int4": "Qwen/Qwen2.5-0.5B-Instruct-AWQ"},
    "7B": {"fp16": "Qwen/Qwen2.5-7B-Instruct", "int4": "Qwen/Qwen2.5-7B-Instruct-AWQ"},
    "72B": {"fp16": "Qwen/Qwen2.5-72B-Instruct", "int4": "Qwen/Qwen2.5-72B-Instruct-AWQ"},
}


def command(model, width, context):
    """The vLLM invocation for this model at this width with this context limit."""
    checkpoint = CHECKPOINTS[model].get(width, CHECKPOINTS[model]["fp16"])
    parts = ["vllm", "serve", checkpoint, "--max-model-len", str(context), "--port", "8000"]
    if width == "int4":
        parts += ["--quantization", "awq"]
    if width == "int8":
        parts += ["--quantization", "fp8"]
    return " ".join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=sorted(MODELS), default="7B")
    parser.add_argument("--card", choices=sorted(CARDS), default="RTX 4090")
    parser.add_argument("--width", choices=["fp16", "int8", "int4"], default="fp16")
    parser.add_argument("--context", type=int, default=8192)
    arguments = parser.parse_args(argv)

    size = weight_bytes(arguments.model, arguments.width) / GIGABYTE
    print(f"{arguments.model} at {arguments.width} is {size:.1f} GB of weights")
    if not fits(arguments.model, arguments.width, arguments.card):
        card_size = CARDS[arguments.card]["memory"] / GIGABYTE
        print(f"it does not fit the {card_size:.0f} GB of the {arguments.card}")
        print("narrower, or a bigger card")
        return 1
    many = concurrent_requests(arguments.model, arguments.width, arguments.card, arguments.context)
    speed = decode_tokens_per_second(arguments.model, arguments.width, arguments.card)
    print(f"beside the weights, about {many} conversations of {arguments.context} tokens fit")
    print(f"one request decodes at most {speed:.0f} tokens per second, bandwidth bound")
    print()
    print(command(arguments.model, arguments.width, arguments.context))
    print()
    print("then, on the machine running the course")
    print("  export AGENTPATH_BASE_URL=http://localhost:8000/v1")
    print(f"  export AGENTPATH_MODEL={CHECKPOINTS[arguments.model].get(arguments.width)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
