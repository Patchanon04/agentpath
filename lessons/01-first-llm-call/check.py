"""Check that lesson 01 works."""
import sys

from llm import ask


def main():
    reply = ask("Say hello.")
    if not isinstance(reply, str) or not reply.strip():
        print(f"FAIL ask returned {reply!r}")
        sys.exit(1)
    print(f"OK the model replied with {reply.strip()[:60]}")


if __name__ == "__main__":
    main()
