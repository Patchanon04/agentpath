"""The agent loop, with every part of the harness attached around it.

Compare this with lesson 04. The middle of the function is the same four
steps it always was. Ask the model. Run what it asked for. Put the results
back. Ask again.

Everything part 3 added is passed in rather than built in. Permissions
decide. A callback records. A budget shrinks what is sent. A cancellation
token can stop the work. A usage object counts. The loop consults each of
them and implements none of them, which is why it did not have to change
shape to gain any of them.
"""
import json

import tools
from context import fit_to_budget
from permissions import Permissions, signature

REPEAT_LIMIT = 3


def run(
    provider,
    user_input,
    system=None,
    permissions=None,
    on_message=None,
    history=None,
    budget=None,
    usage=None,
    max_turns=10,
):
    permissions = permissions or Permissions(auto_approve=True)
    messages = list(history or [])

    def remember(message):
        messages.append(message)
        if on_message:
            on_message(message)

    def to_send():
        """What travels is not what is remembered.

        The full conversation stays in messages because the session file and
        anyone debugging later need all of it. Only the copy handed to the
        provider is trimmed.
        """
        return messages if budget is None else fit_to_budget(messages, budget)

    if system and not messages:
        remember({"role": "system", "content": system})
    remember({"role": "user", "content": user_input})
    schemas = [t["function"] for t in tools.SCHEMAS]

    recent = []
    warned = set()

    for _ in range(max_turns):
        text, calls, reported = provider.stream(
            to_send(), schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )
        if usage is not None:
            usage.add(reported)

        if not calls:
            print()
            remember({"role": "assistant", "content": text})
            return text, messages

        remember(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"]),
                        },
                    }
                    for call in calls
                ],
            }
        )

        for call in calls:
            current = signature(call["name"], call["arguments"])
            recent.append(current)
            going_in_circles = recent[-REPEAT_LIMIT:].count(current) >= REPEAT_LIMIT

            if call["error"]:
                result = f"Error: {call['error']}. Send the tool call again."
                print(f"\n[{call['name']} was not run because {call['error']}]")
            elif going_in_circles:
                # A turn limit counts but does not notice that nothing is
                # changing. Saying so plainly gives the model a chance to
                # change course instead of spending the whole budget.
                result = (
                    f"Error: {call['name']} has been called with these exact arguments "
                    f"{REPEAT_LIMIT} times in a row and nothing has changed. You are going "
                    "in circles. Stop repeating it and try a different approach."
                )
                print(f"\n[{call['name']} is going in circles]")
            elif not permissions.check(call["name"], call["arguments"]):
                result = "The user refused this call. Do not try it again, do something else."
                print(f"\n[{call['name']} was refused]")
            else:
                print(f"\n[calling {call['name']} with {call['arguments']}]")
                result = tools.run(call["name"], call["arguments"])
                print(f"[{call['name']} returned {result}]")

            remember({"role": "tool", "tool_call_id": call["id"], "content": result})

            if going_in_circles and current in warned:
                giving_up = {
                    "role": "assistant",
                    "content": (
                        f"Stopping. {call['name']} was warned about repeating itself and "
                        "repeated anyway. Continuing would only cost money."
                    ),
                }
                remember(giving_up)
                print(f"\n{giving_up['content']}")
                return giving_up["content"], messages
            if going_in_circles:
                warned.add(current)

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
