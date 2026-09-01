"""Read the answer as it is produced instead of waiting for all of it.

Streaming changes the shape of the code, not just the feel of it. Text now
arrives in pieces, and so do the arguments of a tool call. Those arguments
arrive as fragments of JSON that are not valid JSON until the last fragment
lands, which is why we collect them in a buffer and only parse at the end.
"""
import json
import os

import httpx


def complete_stream(messages, tools=None, on_text=None):
    """Stream one reply. Returns (text, tool_calls).

    on_text is called with every piece of text as it arrives.
    """
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools

    text_parts = []
    partial = {}

    with httpx.Client(timeout=120) as client:
        with client.stream(
            "POST", f"{base_url}/chat/completions", json=payload, headers=headers
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                delta = json.loads(data)["choices"][0].get("delta", {})

                if delta.get("content"):
                    text_parts.append(delta["content"])
                    if on_text:
                        on_text(delta["content"])

                for chunk in delta.get("tool_calls", []):
                    index = chunk.get("index", 0)
                    slot = partial.setdefault(index, {"id": "", "name": "", "arguments": ""})
                    if chunk.get("id"):
                        slot["id"] = chunk["id"]
                    function = chunk.get("function", {})
                    if function.get("name"):
                        slot["name"] = function["name"]
                    if function.get("arguments"):
                        slot["arguments"] += function["arguments"]

    calls = []
    for _, slot in sorted(partial.items()):
        try:
            arguments = json.loads(slot["arguments"] or "{}")
            error = ""
        except json.JSONDecodeError as problem:
            arguments = {}
            error = f"arguments were not valid JSON ({problem})"
        calls.append(
            {
                "id": slot["id"],
                "name": slot["name"],
                "arguments": arguments,
                "error": error,
            }
        )
    return "".join(text_parts), calls
