"""Check that lesson 13 works.

Five things must be true. A conversation written out and read back is the
same conversation, including tool calls. The file really is one JSON object
per line, which is what makes it readable. Everything written before a crash
survives it. Text in any language stays readable rather than being escaped
away. And a resumed conversation is one the model can carry on with.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

home = Path(tempfile.mkdtemp(prefix="agentpath-lesson13-"))
workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson13-ws-"))
os.environ["AGENTPATH_HOME"] = str(home)
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from agent import run  # noqa: E402
from providers import OpenAICompatProvider  # noqa: E402
from session import Session  # noqa: E402


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    session = Session("demo")
    written = [
        {"role": "user", "content": "what is 2 plus 3"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "add", "arguments": "{}"}}
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "5"},
    ]
    for message in written:
        session.append(message)

    if Session("demo").load() != written:
        fail("the conversation did not survive a round trip")
    print("OK a conversation survives being written and read back")

    lines = session.path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 3 or any(not json.loads(line) for line in lines):
        fail("the file is not one readable JSON object per line")
    print("OK the file is one JSON object per line and you can read it")

    session.append({"role": "user", "content": "สวัสดี"})
    if "สวัสดี" not in session.path.read_text(encoding="utf-8"):
        fail("non English text was escaped away, which makes the file unreadable")
    print("OK text in any language stays readable in the file")

    provider = OpenAICompatProvider(
        os.environ["AGENTPATH_BASE_URL"],
        os.environ.get("AGENTPATH_API_KEY", ""),
        os.environ["AGENTPATH_MODEL"],
    )
    live = Session("live")
    _, messages = run(provider, "Say hello.", on_message=live.append)
    if live.load() != messages:
        fail("the session on disk does not match the conversation in memory")
    print(f"OK a real run was saved as it happened, {len(messages)} messages")

    resumed = Session("live").load()
    if [m["role"] for m in resumed] != ["user", "assistant"]:
        fail(f"the resumed conversation is wrong. Got {resumed!r}")
    print("OK the saved conversation can be loaded again to carry on from")


if __name__ == "__main__":
    main()
