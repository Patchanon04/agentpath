"""Check that lesson 04 works."""
import sys

from agent import run

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    answer = run(PROMPT)
    if "5" not in answer:
        print(f"FAIL the final answer did not mention the tool result. Got {answer!r}")
        sys.exit(1)
    print(f"OK the agent ran the tool and answered with {answer.strip()[:60]}")


if __name__ == "__main__":
    main()
