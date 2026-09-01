"""The same loop, now asking permission before it runs anything risky."""
import json

import tools
from permissions import Permissions


def run(provider, user_input, system=None, permissions=None, max_turns=10):
    permissions = permissions or Permissions(auto_approve=True)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_input})
    schemas = [t["function"] for t in tools.SCHEMAS]

    for _ in range(max_turns):
        text, calls = provider.stream(
            messages, schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )

        if not calls:
            print()
            messages.append({"role": "assistant", "content": text})
            return text, messages

        messages.append(
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
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
