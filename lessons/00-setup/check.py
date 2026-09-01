"""Prove your machine is ready for the rest of the course.

This script does not test your model. It tests that Python is new enough and
that the endpoint you configured answers when we knock on it.
"""
import os
import sys

MINIMUM_PYTHON = (3, 10)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    if sys.version_info < MINIMUM_PYTHON:
        fail(f"Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer is required")
    print(f"OK Python {sys.version_info.major}.{sys.version_info.minor}")

    try:
        import httpx
    except ImportError:
        fail("httpx is not installed. Run uv pip install httpx")
    print("OK httpx is installed")

    base_url = os.environ.get("AGENTPATH_BASE_URL")
    model = os.environ.get("AGENTPATH_MODEL")
    if not base_url:
        fail("AGENTPATH_BASE_URL is not set")
    if not model:
        fail("AGENTPATH_MODEL is not set")
    print(f"OK AGENTPATH_BASE_URL is {base_url}")
    print(f"OK AGENTPATH_MODEL is {model}")

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say ready."}],
            },
            headers=headers,
            timeout=60,
        )
    except httpx.HTTPError as error:
        fail(f"could not reach {base_url}. {error}")
    if response.status_code != 200:
        fail(f"{base_url} answered {response.status_code}. {response.text[:200]}")
    print("OK the endpoint answered")
    print("\nYou are ready for lesson 01.")


if __name__ == "__main__":
    main()
