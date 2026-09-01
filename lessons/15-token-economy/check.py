"""Check that lesson 15 works.

Two facts have to be demonstrated rather than asserted, because they are the
facts the whole chapter is built on. A conversation gets more expensive on
every single turn even when you say nothing new. And putting the things that
never change at the front is what lets a provider reuse work between calls,
which only happens if the beginning of the request is byte for byte the same.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson15-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import httpx  # noqa: E402
from usage import Usage  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def send(messages):
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": os.environ["AGENTPATH_MODEL"], "messages": messages},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main():
    usage = Usage()
    conversation = [{"role": "user", "content": "Say hello."}]
    prompts = []

    for turn in range(4):
        body = send(conversation)
        usage.add(body["usage"])
        prompts.append(body["usage"]["prompt_tokens"])
        conversation.append({"role": "assistant", "content": body["choices"][0]["message"]["content"] or ""})
        conversation.append({"role": "user", "content": f"And again, turn {turn}."})

    if prompts != sorted(prompts) or prompts[0] == prompts[-1]:
        fail(f"the prompt cost did not grow every turn. Saw {prompts}")
    print(f"OK the same conversation cost more every turn, {prompts}")

    if usage.calls != 4:
        fail(f"expected four calls, counted {usage.calls}")
    print(f"OK usage adds up across calls, {usage.summary()}")

    price = usage.cost(prompt_price_per_million=3.0, completion_price_per_million=15.0)
    if price <= 0:
        fail("turning tokens into money produced nothing")
    print(f"OK tokens can be turned into money, about {price:.6f} at example prices")

    stable = [{"role": "system", "content": "long instructions " * 20}]
    first = stable + [{"role": "user", "content": "one"}]
    second = stable + [{"role": "user", "content": "two"}]
    shared = 0
    for left, right in zip(first, second):
        if left != right:
            break
        shared += 1
    if shared != 1:
        fail("the unchanging prefix was not shared between two requests")
    print("OK putting the unchanging part first leaves a prefix a provider can reuse")

    moved_first = [{"role": "user", "content": "one"}] + stable
    moved_second = [{"role": "user", "content": "two"}] + stable
    if moved_first[0] == moved_second[0]:
        fail("this check is wrong, the first messages should differ")
    print("OK putting the changing part first destroys that prefix, which is the mistake to avoid")


if __name__ == "__main__":
    main()
