"""Tools are plain functions plus a hand written JSON schema.

The schema is written by hand rather than generated from type hints. Reading
the schema is how a learner understands what the model actually receives, and
hiding it behind a decorator would remove the most instructive part.
"""
from collections.abc import Callable
from dataclasses import dataclass

from agentpath.types import ToolCall, ToolResult


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., object]


class ToolRegistry:
    def __init__(self, tools=()):
        self._tools = {tool.name: tool for tool in tools}

    def schemas(self) -> list[dict]:
        return [
            {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
            for tool in self._tools.values()
        ]

    def run(self, call: ToolCall) -> ToolResult:
        """Run one tool call and always come back with a result.

        Arguments come from the model, so they are untrusted input. A bad call
        must turn into text the model can read and correct, never an exception
        that kills the agent loop.
        """
        if call.arguments_error:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: {call.arguments_error}. Send the tool call again.",
            )
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: unknown tool {call.name}",
            )
        try:
            return ToolResult(
                tool_call_id=call.id, name=call.name, content=str(tool.fn(**call.arguments))
            )
        except Exception as error:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: {type(error).__name__}: {error}",
            )
