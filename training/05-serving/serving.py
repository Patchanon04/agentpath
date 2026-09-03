"""The arithmetic of serving a model, which is what the bill and the latency are made of.

Nothing here is measured. It is all multiplication, and the point is
that the multiplication is enough to predict most of what a served model
does before touching a GPU. How much memory the weights take. How much
the KV cache from foundations chapter 6 takes per token of context, and
why that is what limits how many people a card can serve at once. And
why generating tokens is limited by how fast memory can be read rather
than how fast the chip can multiply, which is the single fact behind
batching, quantization, and the price gap between input and output
tokens.
"""

GIGABYTE = 1024**3

# Shapes of a few open models, from their configs. Layers, hidden size,
# attention heads, and the number of key value heads, which is smaller
# than the number of query heads in every recent model precisely to
# shrink the cache this file computes.
MODELS = {
    "0.5B": {"parameters": 0.5e9, "layers": 24, "hidden": 896, "kv_heads": 2, "head_size": 64},
    "7B": {"parameters": 7.6e9, "layers": 28, "hidden": 3584, "kv_heads": 4, "head_size": 128},
    "72B": {"parameters": 72.7e9, "layers": 80, "hidden": 8192, "kv_heads": 8, "head_size": 128},
}

# Bytes per parameter at each width. Sixteen bit is what training leaves
# behind. Eight and four are chapter 3 of this part.
BYTES_PER_PARAMETER = {"fp16": 2, "int8": 1, "int4": 0.5}

# Memory bandwidth of a few cards in bytes per second, the number that
# decides decode speed. Compute is listed too, to show how far it is
# from being the limit.
CARDS = {
    "RTX 4090": {"memory": 24 * GIGABYTE, "bandwidth": 1008e9},
    "A100 80GB": {"memory": 80 * GIGABYTE, "bandwidth": 2039e9},
    "H100 80GB": {"memory": 80 * GIGABYTE, "bandwidth": 3350e9},
}


def weight_bytes(model, width):
    """What the parameters take on the card, before a single token arrives."""
    return MODELS[model]["parameters"] * BYTES_PER_PARAMETER[width]


def kv_bytes_per_token(model, width="fp16"):
    """The cache from foundations chapter 6, per token, for every layer.

    A key and a value per layer, each kv_heads times head_size numbers.
    This is what grows with the conversation, and it is per request, so
    a card serving many people at once holds one of these for each of
    them and the context length they are at.
    """
    shape = MODELS[model]
    numbers = 2 * shape["layers"] * shape["kv_heads"] * shape["head_size"]
    return numbers * BYTES_PER_PARAMETER[width]


def concurrent_requests(model, width, card, context):
    """How many conversations of this length fit beside the weights."""
    free = CARDS[card]["memory"] - weight_bytes(model, width)
    if free <= 0:
        return 0
    return int(free // (kv_bytes_per_token(model) * context))


def decode_tokens_per_second(model, width, card):
    """The ceiling on generation speed for one request, from bandwidth alone.

    Generating one token reads every weight once. So the fastest a card
    can produce tokens for a single request is its bandwidth divided by
    the size of the weights, and nothing about the chip's arithmetic
    speed enters into it. That is why halving the bytes per parameter
    nearly doubles tokens per second, and why serving many requests at
    once is almost free, the weights are read once per step either way.
    """
    return CARDS[card]["bandwidth"] / weight_bytes(model, width)


def fits(model, width, card):
    return weight_bytes(model, width) < CARDS[card]["memory"]


if __name__ == "__main__":
    print("weights alone, in gigabytes")
    print("model    fp16    int8    int4")
    for model in MODELS:
        sizes = [weight_bytes(model, width) / GIGABYTE for width in BYTES_PER_PARAMETER]
        print(f"{model:5s}  {sizes[0]:6.1f}  {sizes[1]:6.1f}  {sizes[2]:6.1f}")
    print()
    print("the 7B model at fp16 on each card")
    print("card        fits   8k conversations at once   tokens per second, one request")
    for card in CARDS:
        can = fits("7B", "fp16", card)
        many = concurrent_requests("7B", "fp16", card, 8192)
        speed = decode_tokens_per_second("7B", "fp16", card) if can else 0
        print(f"{card:10s}  {str(can):5s}  {many:24d}   {speed:28.0f}")
    print()
    print("the same model on the same card, narrower")
    for width in BYTES_PER_PARAMETER:
        many = concurrent_requests("7B", width, "RTX 4090", 8192)
        speed = decode_tokens_per_second("7B", width, "RTX 4090")
        print(f"  {width:5s}  {many:3d} conversations   {speed:5.0f} tokens per second")
    print()
    per_token = kv_bytes_per_token("7B") / 1024
    print(f"the 7B model's cache costs {per_token:.0f} KB per token of context, per conversation")
