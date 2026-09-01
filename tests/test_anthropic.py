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
