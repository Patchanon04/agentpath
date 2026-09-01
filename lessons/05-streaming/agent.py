"""The same loop as lesson 04, now printing text the moment it arrives."""
import json

import tools
from llm import complete_stream


def run(user_input, max_turns=10):
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete_stream(
            messages, tools.SCHEMAS, on_text=lambda piece: print(piece, end="", flush=True)
        )

        if not calls:
            print()
            return text

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


if __name__ == "__main__":
    run("What is 2 plus 3?")
