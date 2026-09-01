"""Send tools along with the conversation and read what the model asks for."""
import json
import os

import httpx


def complete(messages, tools=None):
    """Return (text, tool_calls).

    tool_calls is a list of dicts with the keys id, name and arguments.
    When the model answers in words the list is empty.
    """
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools

    response = httpx.post(
        f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120
    )
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]

    calls = []
    for raw in message.get("tool_calls") or []:
        calls.append(
            {
                "id": raw["id"],
                "name": raw["function"]["name"],
                "arguments": json.loads(raw["function"]["arguments"] or "{}"),
            }
        )
    return message.get("content") or "", calls
