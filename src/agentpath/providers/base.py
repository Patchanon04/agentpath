"""The one interface every provider implements.

A provider turns a conversation into a stream of events. It yields TextDelta
while the assistant is speaking and exactly one TurnDone at the end that
carries the finished message, including any tool calls the model asked for.

A provider never runs a tool. Running tools belongs to the agent loop, and
keeping that line clean is what lets both providers share one loop.
"""
import json
from collections.abc import Iterator

from agentpath.types import Message


class Provider:
    def stream(self, messages: list[Message], tools: list[dict] | None = None) -> Iterator:
        raise NotImplementedError


def parse_arguments(raw: str) -> tuple[dict, str]:
    """Turn streamed argument text into a dict, or report why it could not.

    Returns (arguments, error). A model that hits its output limit part way
    through a tool call sends back JSON that stops mid string. Quietly
    turning that into an empty dict is the worst possible answer, because the
    tool then runs with no arguments and the model never learns it made a
    mistake, so it repeats the same broken call every time the conversation
    is replayed.
    """
    try:
        return json.loads(raw or "{}"), ""
    except json.JSONDecodeError as error:
        return {}, f"arguments were not valid JSON ({error}). Raw text was {raw!r}"
