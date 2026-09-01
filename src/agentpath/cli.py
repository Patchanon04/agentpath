"""The agentpath command.

Three subcommands. chat is a conversation. run does one task and exits, which
is what you want in a script. resume picks up a saved session.

Everything the harness added in part 3 is wired in here rather than inside the
agent loop. This file is the only place that knows about terminals, keyboards
and the clock.
"""
import argparse
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from agentpath.agent import Agent
from agentpath.cancel import Cancellation
from agentpath.permissions import Permissions, ask_in_terminal
from agentpath.prompt import build_system_prompt
from agentpath.session import Session
from agentpath.tools.base import ToolRegistry
from agentpath.tools.files import file_tools
from agentpath.tools.retrieval import retrieval_tools
from agentpath.tools.search import search_tools
from agentpath.tools.shell import shell_tools
from agentpath.types import TextDelta, ToolCallRequest, ToolResult, TurnDone

REQUIRED = ["AGENTPATH_BASE_URL", "AGENTPATH_MODEL"]
DEFAULT_BUDGET = 100_000


def build_tools(root, cancellation=None):
    """Every tool the command line gives the agent."""
    return ToolRegistry(
        file_tools(root)
        + shell_tools(root, cancellation=cancellation)
        + search_tools(root)
        + retrieval_tools(root)
    )


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


def new_session_name() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def build_agent(arguments, session):
    """Assemble the agent with every part of the harness attached."""
    root = Path(arguments.workspace).resolve()
    permissions = Permissions(
        ask=ask_in_terminal,
        auto_approve=os.environ.get("AGENTPATH_AUTO_APPROVE") == "1" or arguments.yes,
    )
    cancellation = Cancellation()
    agent = Agent(
        provider=build_provider(arguments.provider),
        tools=build_tools(root, cancellation=cancellation),
        system=build_system_prompt(root),
        permissions=permissions,
        on_message=session.append,
        budget=arguments.budget,
        cancellation=cancellation,
    )
    return agent, root


def show(events) -> None:
    """Draw one run on the terminal. The loop itself prints nothing."""
    for event in events:
        if isinstance(event, TextDelta):
            print(event.text, end="", flush=True)
        elif isinstance(event, ToolCallRequest):
            print(f"\n[calling {event.tool_call.name} with {event.tool_call.arguments}]")
        elif isinstance(event, ToolResult):
            first_line = event.content.splitlines()[0] if event.content else ""
            print(f"[{event.name} returned {first_line[:120]}]")
        elif isinstance(event, TurnDone):
            print()


def install_interrupt_handler(agent):
    """Make Ctrl+C stop the work rather than only the display.

    The first press asks the agent to stop, which it notices between turns
    and before running a tool. A second press falls through to the normal
    Python behaviour, so a genuinely wedged process can still be killed.
    """

    def handle(signum, frame):
        if agent.cancellation.cancelled:
            raise KeyboardInterrupt
        print("\nStopping after the current step. Press Ctrl+C again to force it.")
        agent.cancellation.cancel()

    try:
        signal.signal(signal.SIGINT, handle)
    except ValueError:
        pass


def finish(agent, session) -> int:
    print(f"\nsession {session.name} saved to {session.path}")
    print(f"usage {agent.usage.summary()}")
    return 0


def command_chat(arguments) -> int:
    check_environment()
    session = Session(arguments.session or new_session_name())
    agent, root = build_agent(arguments, session)
    install_interrupt_handler(agent)
    print(f"Working in {root}")
    print("Type a message. Press Ctrl+C to leave.")
    while True:
        try:
            user_input = input("\nyou> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return finish(agent, session)
        if not user_input.strip():
            continue
        try:
            show(agent.run(user_input))
        except KeyboardInterrupt:
            print("\nstopped")
            agent.cancellation = Cancellation()
            install_interrupt_handler(agent)


def command_run(arguments) -> int:
    check_environment()
    session = Session(arguments.session or new_session_name())
    agent, root = build_agent(arguments, session)
    install_interrupt_handler(agent)
    print(f"Working in {root}")
    try:
        show(agent.run(arguments.task))
    except KeyboardInterrupt:
        print("\nstopped")
    return finish(agent, session)


def command_resume(arguments) -> int:
    check_environment()
    if not arguments.session:
        names = Session.list_all()
        if not names:
            print("There are no saved sessions yet.", file=sys.stderr)
            return 1
        print("\n".join(names))
        return 0
    session = Session(arguments.session)
    history = session.load()
    if not history:
        print(f"Session {arguments.session} is empty or does not exist.", file=sys.stderr)
        return 1
    agent, root = build_agent(arguments, session)
    agent.messages = history
    install_interrupt_handler(agent)
    print(f"Working in {root}")
    print(f"Resumed {arguments.session} with {len(history)} messages")
    if arguments.task:
        try:
            show(agent.run(arguments.task))
        except KeyboardInterrupt:
            print("\nstopped")
    return finish(agent, session)


def add_common_arguments(parser):
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Directory the agent is allowed to work in. Defaults to the current directory.",
    )
    parser.add_argument("--session", default=None, help="Name of the session file")
    parser.add_argument(
        "--budget",
        type=int,
        default=DEFAULT_BUDGET,
        help="Roughly how many tokens of conversation to send. Older exchanges are dropped.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Approve every tool call without asking. Know what you are doing.",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentpath")
    subcommands = parser.add_subparsers(dest="command", required=True)

    chat_parser = subcommands.add_parser("chat", help="Talk to an agent in the terminal")
    add_common_arguments(chat_parser)

    run_parser = subcommands.add_parser("run", help="Do one task and exit")
    run_parser.add_argument("task", help="What you want the agent to do")
    add_common_arguments(run_parser)

    resume_parser = subcommands.add_parser(
        "resume", help="Continue a saved session, or list sessions when given no name"
    )
    resume_parser.add_argument("task", nargs="?", default=None, help="Optional next task")
    add_common_arguments(resume_parser)

    arguments = parser.parse_args(argv)
    return {
        "chat": command_chat,
        "run": command_run,
        "resume": command_resume,
    }[arguments.command](arguments)


if __name__ == "__main__":
    raise SystemExit(main())
