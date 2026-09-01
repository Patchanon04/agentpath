"""Check that lesson 05 works."""
import sys

import tools
from agent import run
from llm import complete_stream

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    pieces = []
    text, _ = complete_stream(
        [{"role": "user", "content": "Say hello."}], None, on_text=pieces.append
    )
    if len(pieces) < 2:
        print(f"FAIL the reply did not arrive in pieces. Got {len(pieces)} piece(s)")
        sys.exit(1)
    if "".join(pieces) != text:
        print("FAIL the streamed pieces do not add up to the final text")
        sys.exit(1)
    print(f"OK text arrived in {len(pieces)} pieces")

    _, calls = complete_stream([{"role": "user", "content": PROMPT}], tools.SCHEMAS)
    if not calls or calls[0]["arguments"] != {"a": 2, "b": 3}:
        print(f"FAIL streamed tool arguments were not reassembled. Got {calls}")
        sys.exit(1)
    print("OK streamed tool arguments were reassembled into valid JSON")

    answer = run(PROMPT)
    if "5" not in answer:
        print(f"FAIL the agent answer did not mention the tool result. Got {answer!r}")
        sys.exit(1)
    print("OK the streaming agent completed the tool round trip")


if __name__ == "__main__":
    main()
