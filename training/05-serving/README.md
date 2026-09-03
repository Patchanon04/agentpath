# Training 5. Serving is arithmetic

This folder is the code behind the last chapter of part 4 of the book,
at [book/21-serving.md](../../book/21-serving.md). The chapter says that
most of what a served model does, how much memory it needs, how many
people it can serve at once, and how fast it generates, can be predicted
by multiplication before touching a GPU. This file is the short version
for running the code.

Nothing here needs a GPU. Nothing here is measured, either. It is all
multiplication, and the point is how far multiplication gets you.

## What is here

`serving.py` holds the shapes of three open models and three cards, and
the four functions that turn them into answers. `weight_bytes` is the
weights at a width. `kv_bytes_per_token` is the cache from foundations
chapter 6 per token of context. `concurrent_requests` is how many
conversations fit beside the weights. `decode_tokens_per_second` is the
ceiling on generation speed for one request, from bandwidth alone.

```python
def decode_tokens_per_second(model, width, card):
    """The ceiling on generation speed for one request, from bandwidth alone."""
    return CARDS[card]["bandwidth"] / weight_bytes(model, width)
```

`launch.py` applies the arithmetic to a model and a card you name, and
prints the vLLM command that would serve it as the same OpenAI shaped
endpoint the whole course calls, so that one environment variable points
the course at your own model. It runs anywhere and starts nothing.

`check.py` pins the claims the chapter makes.

## Run it

```bash
python serving.py
```

```text
weights alone, in gigabytes
model    fp16    int8    int4
0.5B      0.9     0.5     0.2
7B       14.2     7.1     3.5
70B     130.4    65.2    32.6

the 7B model at fp16 on each card
card        fits   8k conversations at once   tokens per second, one request
RTX 4090    True                         22                             66
A100 80GB   True                        150                            134
H100 80GB   True                        150                            220

the same model on the same card, narrower
  fp16    22 conversations      66 tokens per second
  int8    38 conversations     133 tokens per second
  int4    46 conversations     265 tokens per second

the 7B model's cache costs 56 KB per token of context, per conversation
```

```bash
python check.py
```

```text
OK 7B weights are fourteen gigabytes at sixteen bits and a quarter of that at four bits
OK a 70B model does not fit one 80 GB card at sixteen bits and does at four
OK the cache costs 56 KB per token of context for the 7B model, from its shape alone
OK fewer conversations fit as they get longer, and none at all if the weights do not fit
OK decode speed is bandwidth over bytes, so a quarter of the bytes is four times the tokens
```

```bash
python launch.py --model 7B --card "RTX 4090" --width int4 --context 8192
```

```text
7B at int4 is 3.5 GB of weights
beside the weights, about 46 conversations of 8192 tokens fit
one request decodes at most 265 tokens per second, bandwidth bound

vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --max-model-len 8192 --port 8000 --quantization awq

then, on the machine running the course
  export AGENTPATH_BASE_URL=http://localhost:8000/v1
  export AGENTPATH_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
```

## What to notice

Sixty six tokens per second. That number came from dividing the card's
bandwidth by the size of the weights and nothing else, and it is close to
what the card actually does, because generating one token means reading
every weight once and the chip's arithmetic is nowhere near the limit.
That single fact explains three things people pay for. Quantizing to
four bits makes one request four times faster. Serving many requests at
once is nearly free, the weights are read once per step either way, which
is why the int4 row fits forty six conversations and why providers batch.
And output tokens cost more than input tokens, because input is read in
one pass and output is this loop, one token at a time.

The cache is the other number. Fifty six kilobytes per token does not
sound like much until it is multiplied by eight thousand tokens and
twenty two conversations, at which point it is most of the card. That is
why the concurrent column falls as conversations get longer, why serving
providers charge for long context, and why foundations chapter 6 built
the cache by hand.

`launch.py` ends with the environment variable. The whole course was
written against an endpoint shape rather than a provider, lesson 06's
argument, and this is where it pays. Point `AGENTPATH_BASE_URL` at the
served model and every lesson from 01 onward runs against the model you
trained in the last four chapters.
