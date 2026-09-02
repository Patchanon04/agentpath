from agentpath.providers.base import parse_arguments
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.types import Message, TextDelta, ToolCall, TurnDone

TOOLS = [
    {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    }
]


def build(mock_url):
    return OpenAICompatProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")


def test_streams_text_then_finishes(mock_url):
    events = list(build(mock_url).stream([Message(role="user", content="hi")]))
    deltas = [e for e in events if isinstance(e, TextDelta)]
    assert len(deltas) > 1
    assert isinstance(events[-1], TurnDone)
    assert events[-1].message.content == "Hello from the mock server."
    assert events[-1].message.tool_calls == []


def test_accumulates_streamed_tool_arguments(mock_url):
    prompt = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'
    events = list(build(mock_url).stream([Message(role="user", content=prompt)], TOOLS))
    call = events[-1].message.tool_calls[0]
    assert call.name == "add"
    assert call.arguments == {"a": 2, "b": 3}
    assert call.arguments_error == ""


def test_truncated_tool_arguments_do_not_crash_the_provider():
    arguments, error = parse_arguments('{"a": 2, "b')
    assert arguments == {}
    assert "not valid JSON" in error

    arguments, error = parse_arguments("")
    assert arguments == {}
    assert error == ""


def test_sends_tool_results_back_in_wire_format(mock_url):
    history = [
        Message(role="user", content="hi"),
        Message(role="tool", content="5", tool_call_id="call_mock_1"),
    ]
    events = list(build(mock_url).stream(history))
    assert "5" in events[-1].message.content

ESCAPED_X = '\\"x\\":'
ESCAPED_Y = '\\"y\\":'
SEPARATOR = "\n\n"

def test_a_missing_index_starts_a_new_call_rather_than_merging():
    """Some servers leave index off tool call deltas.

    Defaulting every fragment to slot zero merged the calls, which destroyed
    one and lost the other entirely. The model was handed a JSON error for a
    call it never made, and never learned the first one had been dropped.
    """
    import httpx

    from agentpath.types import TurnDone

    events = [
        '{"choices":[{"delta":{"tool_calls":[{"id":"call_1",'
        '"function":{"name":"a","arguments":""}}]}}]}',
        '{"choices":[{"delta":{"tool_calls":[{"function":{"arguments":"{QX 1}"}}]}}]}',
        '{"choices":[{"delta":{"tool_calls":[{"id":"call_2",'
        '"function":{"name":"b","arguments":""}}]}}]}',
        '{"choices":[{"delta":{"tool_calls":[{"function":{"arguments":"{QY 2}"}}]}}]}',
        '{"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        "[DONE]",
    ]
    events = [event.replace("QX", ESCAPED_X).replace("QY", ESCAPED_Y) for event in events]
    body = "".join("data: " + event + SEPARATOR for event in events).encode()
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=body, headers={"content-type": "text/event-stream"}
            )
        )
    )
    provider = OpenAICompatProvider("http://x/v1", "k", "m", client=client)
    done = [
        event
        for event in provider.stream([Message(role="user", content="hi")])
        if isinstance(event, TurnDone)
    ][0]
    assert [(c.name, c.arguments) for c in done.message.tool_calls] == [
        ("a", {"x": 1}),
        ("b", {"y": 2}),
    ]


def test_missing_tool_call_ids_are_filled_in_and_made_unique():
    """A server that leaves the id off gives every call the same empty one.

    Every API rejects a tool result whose id matches nothing, and two calls
    sharing an id makes it impossible to say which result belongs to which.
    """
    from agentpath.providers.base import ensure_ids

    calls = [
        ToolCall(id="", name="a", arguments={}),
        ToolCall(id="", name="b", arguments={}),
        ToolCall(id="keep", name="c", arguments={}),
    ]
    identifiers = [call.id for call in ensure_ids(calls)]
    assert len(set(identifiers)) == 3
    assert "" not in identifiers
    assert "keep" in identifiers


def test_a_replacement_id_never_collides_with_one_already_taken():
    """The collision the function exists to prevent, produced by the function.

    The check ran against the original id and the replacement was assigned
    without being checked, so filling a gap with call_2 while another call
    already answered to call_2 produced two calls sharing an id.
    """
    from agentpath.providers.base import ensure_ids

    calls = [
        ToolCall(id="call_2", name="a", arguments={}),
        ToolCall(id="", name="b", arguments={}),
        ToolCall(id="", name="c", arguments={}),
    ]
    identifiers = [call.id for call in ensure_ids(calls)]
    assert len(set(identifiers)) == 3, identifiers
