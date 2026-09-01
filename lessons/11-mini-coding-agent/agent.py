"""The same loop again, now starting the conversation with a system prompt."""
import json

import tools


def run(provider, user_input, system=None, max_turns=10):
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
            else:
                print(f"\n[calling {call['name']} with {call['arguments']}]")
                result = tools.run(call["name"], call["arguments"])
                print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
