"""Check that lesson 10 works.

Two things must be true. The system prompt is the first message in the
conversation, before anything the user said. It contains the facts the model
cannot work out for itself, which here means the workspace directory.
"""
import os
import sys
import tempfile
from pathlib import Path

workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson10-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from agent import run  # noqa: E402
from prompt import build_system_prompt, examples_block  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    system = build_system_prompt(workspace)
    if str(workspace.resolve()) not in system:
        fail("the system prompt does not tell the model where it is working")
    print("OK the system prompt states the workspace directory")

    if "Platform" not in system:
        fail("the system prompt does not tell the model which platform it is on")
    print("OK the system prompt states the platform")

    pairs = [("rename x to total", "Edited math.py"), ("add a test", "Edited test_math.py")]
    shown = examples_block(pairs)
    with_examples = build_system_prompt(workspace, extra=shown)
    if not with_examples.endswith(shown):
        fail("the examples did not reach the end of the system prompt")
    if shown.index("rename x") > shown.index("add a test"):
        fail("the examples changed order, and the order is part of the pattern")
    if shown.index("rename x") > shown.index("Edited math.py"):
        fail("an answer came before its question")
    print("OK examples ride in the prompt in the order given, each answer after its question")

    provider = OpenAICompatProvider(
        os.environ["AGENTPATH_BASE_URL"],
        os.environ.get("AGENTPATH_API_KEY", ""),
        os.environ["AGENTPATH_MODEL"],
    )
    _, messages = run(provider, "Say hello.", system=system)
    if messages[0]["role"] != "system":
        fail(f"the first message was {messages[0]['role']!r} rather than the system prompt")
    print("OK the system prompt is the first message in the conversation")


if __name__ == "__main__":
    main()
