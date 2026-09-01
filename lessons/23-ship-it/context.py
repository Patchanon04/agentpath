"""Keeping the conversation small enough to send.

Every message is resent on every request, so a long conversation eventually
does not fit and the request is rejected. Something has to be dropped.

The dangerous way to drop things is to slice the list of messages by token
count until it fits. That produces a conversation where a tool result sits
with no tool call in front of it, and the API rejects the whole request with
a 400 rather than ignoring the stray message. The trap is that the error
arrives on the next request rather than on the one you trimmed, so it looks
unrelated to what you just did.

The fix is to never look at a single message. Work in blocks that start at a
user message and run up to just before the next one. A block always holds a
tool call together with its result, so dropping a whole block can never
strand anything.
"""
CHARACTERS_PER_TOKEN = 4
PER_MESSAGE_OVERHEAD = 4


def estimate_tokens(messages):
    """A rough count, deliberately not exact.

    Every provider counts differently and none of them count the way a
    character estimate does. Use this to decide when to start trimming, then
    use the number the provider reports afterwards to know what actually
    happened. Trusting a local estimate to be exact is how people end up
    trimming to ninety percent of a window and still getting rejected.
    """
    total = 0
    for message in messages:
        total += len(message.get("content") or "") // CHARACTERS_PER_TOKEN
        for call in message.get("tool_calls") or []:
            total += len(str(call)) // CHARACTERS_PER_TOKEN
        total += PER_MESSAGE_OVERHEAD
    return total


def split_into_blocks(messages):
    """Group messages into exchanges that each begin with a user message.

    Everything the assistant said and every tool it ran belongs to the
    question that prompted it, so the question and its consequences travel
    together or not at all.
    """
    blocks = []
    for message in messages:
        if message["role"] == "user" or not blocks:
            blocks.append([message])
        else:
            blocks[-1].append(message)
    return blocks


def fit_to_budget(messages, budget: int):
    """Return the newest messages that fit, dropping whole exchanges.

    System messages are always kept because they are the instructions, and an
    agent that forgets its instructions half way through a task is worse than
    one that forgets the beginning of the conversation.

    The newest block is kept even when it alone is over budget. Sending
    something too large and getting a clear error back is better than sending
    a conversation with nothing in it, which fails in a way that looks like
    the model has gone mad.
    """
    system = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]
    blocks = split_into_blocks(rest)

    kept = []
    used = estimate_tokens(system)
    for block in reversed(blocks):
        cost = estimate_tokens(block)
        if kept and used + cost > budget:
            break
        kept.insert(0, block)
        used += cost
    return system + [message for block in kept for message in block]
