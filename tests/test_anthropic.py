from agentpath.providers.anthropic import AnthropicProvider, to_wire
from agentpath.types import Message, TextDelta, TurnDone

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
    return AnthropicProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")


def test_streams_text_then_finishes(mock_url):
    events = list(build(mock_url).stream([Message(role="user", content="hi")]))
    assert [e for e in events if isinstance(e, TextDelta)]
    assert isinstance(events[-1], TurnDone)
    assert events[-1].message.content == "Hello from the mock server."


def test_accumulates_streamed_tool_input(mock_url):
    prompt = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'
    events = list(build(mock_url).stream([Message(role="user", content=prompt)], TOOLS))
    call = events[-1].message.tool_calls[0]
    assert call.name == "add"
    assert call.arguments == {"a": 2, "b": 3}


def test_tool_results_become_user_content_blocks():
    wire = to_wire(
        [
            Message(role="user", content="hi"),
            Message(role="tool", content="5", tool_call_id="call_mock_1"),
        ]
    )
    assert wire[-1]["role"] == "user"
    assert wire[-1]["content"][0]["type"] == "tool_result"
    assert wire[-1]["content"][0]["tool_use_id"] == "call_mock_1"


def test_system_messages_are_dropped_from_the_message_list():
    wire = to_wire(
        [Message(role="system", content="be terse"), Message(role="user", content="hi")]
    )
    assert [m["role"] for m in wire] == ["user"]

SEPARATOR = "\n\n"

def test_usage_is_read_from_both_halves_of_the_stream():
    """Anthropic reports the two numbers in two places and neither is whole.

    The input count rides inside message_start, nested under message. Only
    the output count appears later at the top level. Reading one and letting
    the other overwrite it is how the prompt count silently reads zero, which
    is the exact failure normalise_usage exists to prevent.
    """
    import httpx

    from agentpath.providers.anthropic import AnthropicProvider
    from agentpath.types import TurnDone

    events = [
        '{"type":"message_start","message":{"id":"m","role":"assistant","content":[],'
        '"usage":{"input_tokens":2513,"output_tokens":1}}}',
        '{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
        '{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"hi"}}',
        '{"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":42}}',
        '{"type":"message_stop"}',
    ]
    body = "".join("data: " + event + SEPARATOR for event in events).encode()
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=body, headers={"content-type": "text/event-stream"}
            )
        )
    )
    provider = AnthropicProvider("http://x/v1", "k", "m", client=client)
    done = [
        event
        for event in provider.stream([Message(role="user", content="hi")])
        if isinstance(event, TurnDone)
    ][0]
    assert done.usage["prompt_tokens"] == 2513
    assert done.usage["completion_tokens"] == 42
    assert done.usage["total_tokens"] == 2555
