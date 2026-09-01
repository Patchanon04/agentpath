"""Tests for the parts of the agent loop that part 3 adds."""
import pytest

from agentpath.agent import Agent
from agentpath.cancel import Cancellation
from agentpath.permissions import DENY, Permissions
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.tools.base import Tool, ToolRegistry
from agentpath.types import Message, ToolCall, ToolResult, TurnDone

RAN = []

ADD = Tool(
    name="add",
    description="Add two numbers",
    parameters={
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
    fn=lambda a, b: RAN.append((a, b)) or a + b,
    safe=False,
)

PROMPT = 'Add them. [[tool:add:{"a": 2, "b": 3}]]'


def build(mock_url, **kwargs):
    provider = OpenAICompatProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")
    return Agent(provider=provider, tools=ToolRegistry([ADD]), **kwargs)


def test_a_denied_call_does_not_run_and_the_model_is_told(mock_url):
    RAN.clear()
    agent = build(mock_url, permissions=Permissions(ask=lambda tool, call: DENY))
    events = list(agent.run(PROMPT))
    results = [e for e in events if isinstance(e, ToolResult)]
    assert RAN == [], "a denied tool must not run"
    assert "refused" in results[0].content


def test_every_message_is_reported_so_a_session_can_be_saved(mock_url):
    seen = []
    agent = build(mock_url, on_message=seen.append, permissions=Permissions(auto_approve=True))
    list(agent.run(PROMPT))
    assert [m.role for m in seen] == ["user", "assistant", "tool", "assistant"]
    assert seen == agent.messages


def test_usage_reported_by_the_provider_is_accumulated(mock_url):
    agent = build(mock_url, permissions=Permissions(auto_approve=True))
    list(agent.run(PROMPT))
    assert agent.usage.calls == 2
    assert agent.usage.prompt_tokens > 0


def test_the_conversation_costs_more_every_turn(mock_url):
    """This is the fact the token economy chapter is built on."""
    agent = build(mock_url, permissions=Permissions(auto_approve=True))
    list(agent.run(PROMPT))
    prompts = [call["prompt_tokens"] for call in agent.usage.per_call]
    assert prompts[1] > prompts[0]


def test_a_budget_shrinks_what_is_sent_but_not_what_is_remembered(mock_url):
    agent = build(mock_url, budget=10, permissions=Permissions(auto_approve=True))
    list(agent.run(PROMPT))
    list(agent.run("and again"))
    assert len(agent.messages) > len(agent._to_send())


def test_cancelling_stops_the_loop():
    cancellation = Cancellation()
    cancellation.cancel()

    class Never:
        def stream(self, messages, tools=None):
            raise AssertionError("the provider must not be called after cancelling")
            yield

    agent = Agent(provider=Never(), cancellation=cancellation)
    with pytest.raises(KeyboardInterrupt):
        list(agent.run("hello"))


def test_repeating_the_same_failing_call_is_stopped_and_explained():
    """A turn limit counts but does not notice that nothing is changing."""

    class AlwaysTheSameCall:
        def stream(self, messages, tools=None):
            yield TurnDone(
                message=Message(
                    role="assistant",
                    tool_calls=[ToolCall(id="c", name="add", arguments={"a": 1, "b": 1})],
                )
            )

    agent = Agent(
        provider=AlwaysTheSameCall(),
        tools=ToolRegistry([ADD]),
        permissions=Permissions(auto_approve=True),
        max_turns=6,
    )
    results = [e for e in agent.run("go") if isinstance(e, ToolResult)]
    assert any("going in circles" in r.content or "Stop repeating" in r.content for r in results)
