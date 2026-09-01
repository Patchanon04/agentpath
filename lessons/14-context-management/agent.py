"""The same loop, now asking permission before it runs anything risky."""
import json

import tools
from context import fit_to_budget
from permissions import Permissions


def run(
    provider,
    user_input,
    system=None,
    permissions=None,
    on_message=None,
    history=None,
    budget=None,
    max_turns=10,
):
    permissions = permissions or Permissions(auto_approve=True)
    messages = list(history or [])

    def remember(message):
        """Add to the conversation and tell whoever is listening.

        The callback is how a session gets written without the loop knowing
        that files exist. It is the same trick as permissions, which the
        loop also does not implement, only consult.
        """
        messages.append(message)
        if on_message:
            on_message(message)

    if system and not messages:
        remember({"role": "system", "content": system})
    remember({"role": "user", "content": user_input})
    def to_send():
        """What travels is not what is remembered.

        The whole conversation stays in messages because the session file
        and anyone debugging later need all of it. Only the copy handed to
        the provider is trimmed.
        """
        return messages if budget is None else fit_to_budget(messages, budget)

    schemas = [t["function"] for t in tools.SCHEMAS]

    for _ in range(max_turns):
        text, calls = provider.stream(
            to_send(), schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )

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
            if call["error"]:
                result = f"Error: {call['error']}. Send the tool call again."
                print(f"\n[{call['name']} was not run because {call['error']}]")
            elif not permissions.check(call["name"], call["arguments"]):
                # The model is told it was refused rather than the call being
                # skipped in silence. A model that does not know what happened
                # cannot choose a different approach, so it just tries again.
                result = "The user refused this call. Do not try it again, do something else."
                print(f"\n[{call['name']} was refused]")
            else:
                print(f"\n[calling {call['name']} with {call['arguments']}]")
                result = tools.run(call["name"], call["arguments"])
                print(f"[{call['name']} returned {result}]")
            remember({"role": "tool", "tool_call_id": call["id"], "content": result})

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
