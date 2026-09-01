"""The agentpath command.

v0.1 has one subcommand, chat. Sessions and one shot runs arrive in part 3
of the course, so they are deliberately absent here.
"""
import argparse
import os
import sys
from pathlib import Path

from agentpath.agent import Agent
from agentpath.prompt import build_system_prompt
from agentpath.tools.base import ToolRegistry
from agentpath.tools.files import file_tools
from agentpath.tools.search import search_tools
from agentpath.tools.shell import shell_tools
from agentpath.types import TextDelta, ToolCallRequest, ToolResult, TurnDone

REQUIRED = ["AGENTPATH_BASE_URL", "AGENTPATH_MODEL"]


def build_tools(root):
    """Every tool the chat command gives the agent."""
    return ToolRegistry(file_tools(root) + shell_tools(root) + search_tools(root))


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


def chat(provider_kind: str, workspace="."):
    check_environment()
    root = Path(workspace).resolve()
    agent = Agent(
        provider=build_provider(provider_kind),
        tools=build_tools(root),
        system=build_system_prompt(root),
    )
    print(f"Working in {root}")
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
    chat_parser.add_argument(
        "--workspace",
        default=".",
        help="Directory the agent is allowed to work in. Defaults to the current directory.",
    )
    arguments = parser.parse_args(argv)
    if arguments.command == "chat":
        return chat(arguments.provider, arguments.workspace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
