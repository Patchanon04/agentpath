"""The agent loop.

The loop only yields events. It never prints and never asks the user
anything. That is what lets the same loop serve a terminal chat, a subagent
and an eval run without changing a line inside it.
"""
from collections.abc import Iterator

from agentpath.tools.base import ToolRegistry
from agentpath.types import Message, ToolCallRequest, TurnDone


class Agent:
    def __init__(self, provider, tools=None, system=None, max_turns=10):
        self.provider = provider
        self.tools = tools if tools is not None else ToolRegistry()
        self.messages: list[Message] = []
        if system:
            self.messages.append(Message(role="system", content=system))
        self.max_turns = max_turns

    def run(self, user_input: str) -> Iterator:
        self.messages.append(Message(role="user", content=user_input))
        for _ in range(self.max_turns):
            assistant = None
            for event in self.provider.stream(self.messages, self.tools.schemas() or None):
                if isinstance(event, TurnDone):
                    assistant = event.message
                else:
                    yield event
            self.messages.append(assistant)

            if not assistant.tool_calls:
                yield TurnDone(message=assistant)
                return

            for call in assistant.tool_calls:
                yield ToolCallRequest(tool_call=call)
                result = self.tools.run(call)
                yield result
                self.messages.append(
                    Message(role="tool", content=result.content, tool_call_id=call.id)
                )
        raise RuntimeError(f"agent stopped after max turns ({self.max_turns})")
