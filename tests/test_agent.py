import pytest

from agentpath.agent import Agent
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.tools.base import Tool, ToolRegistry
from agentpath.types import Message, TextDelta, ToolCall, ToolCallRequest, ToolResult, TurnDone

ADD = Tool(
    name="add",
    description="Add two numbers",
    parameters={
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
    fn=lambda a, b: a + b,
)


def build(mock_url, tools=()):
    provider = OpenAICompatProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")
    return Agent(provider=provider, tools=ToolRegistry(tools))


def test_plain_answer_ends_after_one_turn(mock_url):
    events = list(build(mock_url).run("hi"))
    assert isinstance(events[-1], TurnDone)
    assert [e for e in events if isinstance(e, TextDelta)]
    assert not [e for e in events if isinstance(e, ToolCallRequest)]


def test_tool_call_is_executed_and_fed_back(mock_url):
    agent = build(mock_url, [ADD])
    events = list(agent.run('What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'))
    requests = [e for e in events if isinstance(e, ToolCallRequest)]
    results = [e for e in events if isinstance(e, ToolResult)]
    assert requests[0].tool_call.name == "add"
    assert results[0].content == "5"
    assert "5" in events[-1].message.content


def test_conversation_history_grows_with_the_tool_exchange(mock_url):
    agent = build(mock_url, [ADD])
    list(agent.run('[[tool:add:{"a": 2, "b": 3}]]'))
    roles = [m.role for m in agent.messages]
    assert roles == ["user", "assistant", "tool", "assistant"]


def test_runaway_loop_stops_at_max_turns():
    class AlwaysCallsATool:
        def stream(self, messages, tools=None):
            yield TurnDone(
                message=Message(
                    role="assistant",
                    tool_calls=[ToolCall(id="1", name="add", arguments={"a": 1, "b": 1})],
                )
            )

    agent = Agent(provider=AlwaysCallsATool(), tools=ToolRegistry([ADD]), max_turns=3)
    with pytest.raises(RuntimeError, match="max turns"):
        list(agent.run("go"))


def test_system_prompt_becomes_the_first_message():
    class Silent:
        def stream(self, messages, tools=None):
            yield TurnDone(message=Message(role="assistant", content="done"))

    agent = Agent(provider=Silent(), system="be terse")
    list(agent.run("hi"))
    assert agent.messages[0].role == "system"
    assert agent.messages[0].content == "be terse"
