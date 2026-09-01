"""Check that lesson 14 works.

The important test here is the last one, and it is the reason this whole
module exists. A tool result whose matching tool call has been trimmed away
makes the API reject the next request with a 400. Sweeping every budget from
one upwards is what catches the off by one that a single chosen number
would sail straight past.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson14-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from context import estimate_tokens, fit_to_budget, split_into_blocks  # noqa: E402

CONVERSATION = [
    {"role": "system", "content": "be terse"},
    {"role": "user", "content": "first question"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "add", "arguments": "{}"}}
        ],
    },
    {"role": "tool", "tool_call_id": "c1", "content": "result"},
    {"role": "assistant", "content": "first answer"},
    {"role": "user", "content": "second question"},
    {"role": "assistant", "content": "second answer"},
]


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def call_ids(messages):
    found = set()
    for message in messages:
        for call in message.get("tool_calls") or []:
            found.add(call["id"])
    return found


def result_ids(messages):
    return {m["tool_call_id"] for m in messages if m["role"] == "tool"}


def main():
    blocks = split_into_blocks(CONVERSATION[1:])
    if len(blocks) != 2:
        fail(f"expected two exchanges, got {len(blocks)}")
    if [m["role"] for m in blocks[0]] != ["user", "assistant", "tool", "assistant"]:
        fail("a tool call and its result did not stay in the same block")
    print("OK a tool call and its result stay together in one block")

    if fit_to_budget(CONVERSATION, budget=1)[0]["role"] != "system":
        fail("the system message was dropped, so the agent forgot its instructions")
    print("OK the system message is never dropped")

    if fit_to_budget(CONVERSATION, budget=20)[-1]["content"] != "second answer":
        fail("the newest exchange was dropped instead of the oldest")
    print("OK the newest exchange is the one that is kept")

    for budget in range(1, 60):
        kept = fit_to_budget(CONVERSATION, budget=budget)
        if not result_ids(kept) <= call_ids(kept):
            fail(f"a tool result was left with no tool call at budget {budget}")
        if not any(m["role"] == "user" for m in kept):
            fail(f"nothing was left to answer at budget {budget}")
    print("OK no budget produces an orphaned tool result, which is the bug this prevents")

    if fit_to_budget(CONVERSATION, budget=100000) != CONVERSATION:
        fail("a large budget changed the conversation")
    print(f"OK a full conversation of about {estimate_tokens(CONVERSATION)} tokens is left alone")


if __name__ == "__main__":
    main()
