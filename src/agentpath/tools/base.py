"""Tools are plain functions plus a hand written JSON schema.

The schema is written by hand rather than generated from type hints. Reading
the schema is how a learner understands what the model actually receives, and
hiding it behind a decorator would remove the most instructive part.
"""
import json
from collections.abc import Callable
from dataclasses import dataclass

from agentpath.types import ToolCall, ToolResult


@dataclass
class Tool:
    """One tool the model can ask for.

    safe says whether this tool can be run without asking a person first.
    It defaults to False because forgetting to think about a new tool must
    lead to a question rather than to silence, and because the person who
    writes a tool is the one who knows whether it can destroy something.
    """

    name: str
    description: str
    parameters: dict
    fn: Callable[..., object]
    safe: bool = False


class ToolRegistry:
    def __init__(self, tools=()):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name):
        return self._tools.get(name)

    def add(self, tool):
        """Put one more tool in. Used when tools are discovered at run time."""
        self._tools[tool.name] = tool

    def schema_size(self) -> int:
        """How many characters of tool description travel on every request.

        This is the fixed cost of having tools at all. It is paid on the
        first request and on every request after it, before the model has
        read a word of the actual task. Connect a handful of MCP servers and
        this number can eat a large share of the context window on its own,
        which is why it is worth being able to see it.
        """
        schemas = self.schemas()
        if not schemas:
            return 0
        return len(json.dumps(schemas))

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
        except KeyboardInterrupt:
            # An interrupt is not a tool failure. Turning it into a readable
            # result would swallow the thing the person just asked for.
            raise
        except Exception as error:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: {type(error).__name__}: {error}",
            )
