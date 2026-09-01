"""Check that lesson 03 works."""
import sys

import tools
from llm import complete

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    text, calls = complete([{"role": "user", "content": PROMPT}], tools.SCHEMAS)
    if not calls:
        print(f"FAIL the model answered in words instead of calling a tool. Text was {text!r}")
        print("If you are using a local model, see the troubleshooting section of the README.")
        sys.exit(1)
    call = calls[0]
    if call["name"] != "add" or call["arguments"] != {"a": 2, "b": 3}:
        print(f"FAIL unexpected call {call}")
        sys.exit(1)
    result = tools.run(call["name"], call["arguments"])
    if result != "5":
        print(f"FAIL running the tool gave {result!r}")
        sys.exit(1)
    print("OK the model asked for add(2, 3) and the tool returned 5")


if __name__ == "__main__":
    main()
