"""The one interface every provider implements.

A provider turns a conversation into a stream of events. It yields TextDelta
while the assistant is speaking and exactly one TurnDone at the end that
carries the finished message, including any tool calls the model asked for.

A provider never runs a tool. Running tools belongs to the agent loop, and
keeping that line clean is what lets both providers share one loop.
"""
import json
from collections.abc import Iterator

from agentpath.retry import with_retries
from agentpath.types import Message


class Provider:
    def stream(self, messages: list[Message], tools: list[dict] | None = None) -> Iterator:
        raise NotImplementedError


def open_stream(client, url, payload, headers, attempts=4):
    """Open a streaming request, retrying the failures worth retrying.

    Only the opening is retried. Once the first bytes have arrived the caller
    has already seen part of an answer, and replaying the request would
    produce a second answer spliced onto the first. A partly consumed stream
    is not a thing you can retry, so the honest boundary is here.

    The error body is read before raising so the message is useful. Without
    that a failure reports only a status code, which sends people looking in
    the wrong place.
    """

    def once():
        request = client.build_request("POST", url, json=payload, headers=headers)
        response = client.send(request, stream=True)
        if response.status_code >= 400:
            response.read()
            response.close()
            response.raise_for_status()
        return response

    return with_retries(once, attempts=attempts)


def ensure_ids(calls):
    """Give every tool call an id, and make sure no two share one.

    Some servers leave the id off. Every API rejects a tool result whose id
    matches nothing, and two calls sharing an id makes it impossible to say
    which result belongs to which call, so a missing one has to be invented
    rather than passed along.
    """
    seen = set()
    counter = 0
    for call in calls:
        if not call.id or call.id in seen:
            # The replacement has to be checked too. Handing out call_2
            # to fill a gap when another call already answers to call_2
            # produces exactly the collision this function exists to
            # prevent, and servers really do use that shape of id.
            counter += 1
            while f"call_{counter}" in seen:
                counter += 1
            call.id = f"call_{counter}"
        seen.add(call.id)
    return calls


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
