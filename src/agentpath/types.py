"""The small set of data shapes that every other module speaks.

There is no behaviour here on purpose. Keeping the shapes free of logic is
what lets the provider, the tool registry and the agent loop stay unaware of
each other.
"""
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A request from the model to run one tool.

    arguments_error is set when the model produced text that was not valid
    JSON, which happens when it runs out of output budget in the middle of a
    tool call. Carrying the problem instead of hiding it is what lets the
    tool registry hand the model a readable error it can correct.
    """

    id: str
    name: str
    arguments: dict
    arguments_error: str = ""


@dataclass
class Message:
    """One entry in the conversation.

    role is one of system, user, assistant, tool. tool_call_id is filled in
    only when role is tool, so the provider can match a result back to the
    call that produced it.
    """

    role: str
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""


@dataclass
class TextDelta:
    """A piece of assistant text as it arrives."""

    text: str


@dataclass
class ToolCallRequest:
    """The agent is about to run this tool call."""

    tool_call: ToolCall


@dataclass
class ToolResult:
    """The outcome of running one tool call."""

    tool_call_id: str
    name: str
    content: str


@dataclass
class TurnDone:
    """The assistant finished a message.

    usage is what the provider reported this request actually cost. It is a
    plain dict rather than a typed object because every provider names the
    fields slightly differently and pretending otherwise would hide that.
    """

    message: Message
    usage: dict = field(default_factory=dict)
