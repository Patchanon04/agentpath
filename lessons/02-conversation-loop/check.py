"""Check that lesson 02 works."""
import sys

from llm import complete


def main():
    messages = [{"role": "user", "content": "Hello."}]
    first = complete(messages)
    if not first.strip():
        print("FAIL the first reply was empty")
        sys.exit(1)

    messages.append({"role": "assistant", "content": first})
    messages.append({"role": "tool", "tool_call_id": "call_mock_1", "content": "42"})
    second = complete(messages)
    if "42" not in second:
        print(f"FAIL history was not sent back. Reply was {second!r}")
        sys.exit(1)
    print("OK the whole conversation travels on every call")


if __name__ == "__main__":
    main()
