"""The harness.

This is the end of part 3. Nothing here is new. It is the agent loop from
lesson 04 with every part of the harness attached around it, and a command
line so you can actually use it.

Look at where each piece lives. Permissions decide, they do not run
anything. The session records, it does not decide anything. Context
management shrinks what is sent without touching what is remembered. Retry
wraps the network call and nothing else. The loop in agent.py still knows
nothing about terminals, files, clocks or keyboards.

That separation is not tidiness for its own sake. It is what let part 2 add
seven tools and part 3 add five subsystems without the loop changing shape.
"""
import argparse
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path


def new_session_name():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def main():
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("task", nargs="?", help="What you want the agent to do")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--session", default=None)
    parser.add_argument("--resume", default=None, help="Name of a session to carry on from")
    parser.add_argument("--budget", type=int, default=100000)
    parser.add_argument("--yes", action="store_true", help="Approve everything without asking")
    arguments = parser.parse_args()

    workspace = Path(arguments.workspace).resolve()
    os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

    from agent import run
    from cancel import Cancellation
    from permissions import Permissions, ask_in_terminal
    from prompt import build_system_prompt
    from providers import OpenAICompatProvider
    from session import Session
    from usage import Usage

    base_url = os.environ.get("AGENTPATH_BASE_URL")
    model = os.environ.get("AGENTPATH_MODEL")
    if not base_url or not model:
        print("Set AGENTPATH_BASE_URL and AGENTPATH_MODEL first.", file=sys.stderr)
        return 2

    session = Session(arguments.resume or arguments.session or new_session_name())
    history = session.load() if arguments.resume else []
    provider = OpenAICompatProvider(base_url, os.environ.get("AGENTPATH_API_KEY", ""), model)
    permissions = Permissions(
        ask=ask_in_terminal,
        auto_approve=arguments.yes or os.environ.get("AGENTPATH_AUTO_APPROVE") == "1",
    )
    cancellation = Cancellation()
    usage = Usage()

    def handle_interrupt(signum, frame):
        if cancellation.cancelled:
            raise KeyboardInterrupt
        print("\nStopping after the current step. Press Ctrl+C again to force it.")
        cancellation.cancel()

    try:
        signal.signal(signal.SIGINT, handle_interrupt)
    except ValueError:
        pass

    print(f"Working in {workspace}")
    if history:
        print(f"Resumed {session.name} with {len(history)} messages")

    task = arguments.task
    if not task:
        try:
            task = input("What should I do? ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

    try:
        run(
            provider,
            task,
            system=build_system_prompt(workspace),
            permissions=permissions,
            on_message=session.append,
            history=history,
            budget=arguments.budget,
            cancellation=cancellation,
            usage=usage,
        )
    except KeyboardInterrupt:
        print("\nstopped")

    print(f"\nsession {session.name} saved to {session.path}")
    print(f"usage {usage.summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
