"""The same call as lesson 01, but taking a whole conversation.

A model has no memory. The only reason it appears to remember anything is
that we send the entire conversation again on every single call.
"""
import os

import httpx


def complete(messages):
    """Send a list of messages and return the assistant reply as a string."""
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": model, "messages": messages},
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
