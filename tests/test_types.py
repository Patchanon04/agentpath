from agentpath.types import Message, TextDelta, ToolCall, ToolResult, TurnDone


def test_message_defaults_are_independent():
    first = Message(role="user", content="hi")
    second = Message(role="user", content="hi")
    first.tool_calls.append(ToolCall(id="1", name="add", arguments={}))
    assert second.tool_calls == []


def test_events_carry_their_payload():
    assert TextDelta(text="ab").text == "ab"
    assert TurnDone(message=Message(role="assistant")).message.role == "assistant"
    assert ToolResult(tool_call_id="1", name="add", content="5").content == "5"


def test_tool_call_defaults_to_no_argument_error():
    assert ToolCall(id="1", name="add", arguments={}).arguments_error == ""
