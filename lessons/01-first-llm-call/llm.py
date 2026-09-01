"""One function that sends text to a model and returns the text it sends back.

Everything else in this course is built on top of this. There is no library
between you and the API here on purpose. You should be able to see that a
language model is an HTTP endpoint that takes a list of messages and returns
one more message.
"""
import os

import httpx


def ask(prompt):
    """Send one message and return the assistant reply as a string."""
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    return body["choices"][0]["message"]["content"]


if __name__ == "__main__":
    print(ask("Say hello in one short sentence."))
