from agentpath.providers.base import parse_arguments
from agentpath.providers.openai_compat import OpenAICompatProvider
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
