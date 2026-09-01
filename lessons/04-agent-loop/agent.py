"""The agent loop.

This is the whole idea of an agent in one function. Ask the model. If it
asked for tools, run them, put the results back into the conversation, and
ask again. Stop when it answers in words instead of asking for a tool.

max_turns exists because a model can get stuck asking for the same tool
forever. Without a limit that is an infinite loop that spends real money.
"""
import json

import tools
from llm import complete


def run(user_input, max_turns=10):
    """Run the agent until it produces a final answer. Returns the answer."""
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete(messages, tools.SCHEMAS)

        if not calls:
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
            print(f"[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")


if __name__ == "__main__":
    print(run("What is 2 plus 3?"))
