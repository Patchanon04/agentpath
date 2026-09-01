"""Check that lesson 06 works.

The point of this lesson is that one agent loop serves two different APIs.
So this check runs the same prompt through both providers and expects the
same outcome.
"""
import os
import sys

from agent import run
from providers import AnthropicProvider, OpenAICompatProvider

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    base_url = os.environ["AGENTPATH_BASE_URL"]
    model = os.environ["AGENTPATH_MODEL"]
    api_key = os.environ.get("AGENTPATH_API_KEY", "")

    for name, provider in [
        ("openai", OpenAICompatProvider(base_url, api_key, model)),
        ("anthropic", AnthropicProvider(base_url, api_key, model)),
    ]:
        answer = run(provider, PROMPT)
        if "5" not in answer:
            print(f"FAIL the {name} provider did not complete the tool round trip. Got {answer!r}")
            sys.exit(1)
        print(f"OK the same loop worked with the {name} provider")


if __name__ == "__main__":
    main()
