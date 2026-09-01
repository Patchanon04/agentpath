"""A small coding agent you can actually use.

Nothing in this file is new. It is the loop from lesson 04, the streaming
from lesson 05, the provider interface from lesson 06, the tools from
lessons 07 to 09 and the system prompt from lesson 10, wired together and
given a command line.

The thing worth noticing is what is not here. The agent loop has not changed
since lesson 04 apart from taking a provider and a system prompt. Every
capability added in part 2 arrived as a tool. That is the payoff of putting
the loop and the tools on opposite sides of a clean line.
"""
import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="mini-coding-agent")
    parser.add_argument("task", nargs="?", help="What you want the agent to do")
    parser.add_argument(
        "--workspace", default=".", help="Directory the agent is allowed to work in"
    )
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    arguments = parser.parse_args()

    workspace = Path(arguments.workspace).resolve()
    os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

    from agent import run
    from prompt import build_system_prompt
    from providers import AnthropicProvider, OpenAICompatProvider

    base_url = os.environ.get("AGENTPATH_BASE_URL")
    model = os.environ.get("AGENTPATH_MODEL")
    if not base_url or not model:
        print(
            "Set AGENTPATH_BASE_URL and AGENTPATH_MODEL before running this.",
            file=sys.stderr,
        )
        return 2

    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    build = AnthropicProvider if arguments.provider == "anthropic" else OpenAICompatProvider
    provider = build(base_url, api_key, model)
    system = build_system_prompt(workspace)

    print(f"Working in {workspace}")
    task = arguments.task
    if not task:
        try:
            task = input("What should I do? ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

    run(provider, task, system=system)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
