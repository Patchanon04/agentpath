"""The agentpath command.

v0.1 has one subcommand, chat. Sessions and one shot runs arrive in part 3
of the course, so they are deliberately absent here.
"""
import argparse
import os
import sys

from agentpath.agent import Agent
from agentpath.types import TextDelta, ToolCallRequest, ToolResult, TurnDone

REQUIRED = ["AGENTPATH_BASE_URL", "AGENTPATH_MODEL"]


def build_provider(kind: str):
    if kind == "anthropic":
        from agentpath.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    from agentpath.providers.openai_compat import OpenAICompatProvider

    return OpenAICompatProvider()


def check_environment():
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        print(
            "Missing configuration. Set these environment variables and try again.\n  "
            + "\n  ".join(missing),
            file=sys.stderr,
        )
        raise SystemExit(2)


def chat(provider_kind: str):
    check_environment()
    agent = Agent(provider=build_provider(provider_kind))
    print("Type a message. Press Ctrl+C to leave.")
    while True:
        try:
            user_input = input("\nyou> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user_input.strip():
            continue
        for event in agent.run(user_input):
            if isinstance(event, TextDelta):
                print(event.text, end="", flush=True)
            elif isinstance(event, ToolCallRequest):
                print(f"\n[calling {event.tool_call.name} with {event.tool_call.arguments}]")
            elif isinstance(event, ToolResult):
                print(f"[{event.name} returned {event.content}]")
            elif isinstance(event, TurnDone):
                print()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentpath")
    subcommands = parser.add_subparsers(dest="command", required=True)
    chat_parser = subcommands.add_parser("chat", help="Talk to an agent in the terminal")
    chat_parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    arguments = parser.parse_args(argv)
    if arguments.command == "chat":
        return chat(arguments.provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
