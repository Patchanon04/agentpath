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


def test_stopping_mid_turn_leaves_no_tool_call_without_a_result():
    """The pairing rule from lesson 14, enforced where it can be broken.

    An assistant message with three tool calls followed by two results is
    rejected outright on the next request, and that request is the one after
    the interruption, so the error looks like it came from nowhere.
    """
    calls = [ToolCall(id=str(index), name="add", arguments={"a": index}) for index in range(3)]

    class ThreeAtOnce:
        def stream(self, messages, tools=None):
            yield TurnDone(message=Message(role="assistant", tool_calls=list(calls)))

    cancellation = Cancellation()
    slow = Tool(
        name="add",
        description="d",
        parameters={"type": "object", "properties": {}},
        fn=lambda a=0: cancellation.cancel() or "done",
        safe=True,
    )
    agent = Agent(
        provider=ThreeAtOnce(),
        tools=ToolRegistry([slow]),
        permissions=Permissions(auto_approve=True),
        cancellation=cancellation,
        max_turns=2,
    )
    with pytest.raises(KeyboardInterrupt):
        list(agent.run("go"))

    requested = {call.id for message in agent.messages for call in message.tool_calls}
    answered = {m.tool_call_id for m in agent.messages if m.role == "tool"}
    assert requested == answered, f"orphaned tool calls {requested - answered}"


def test_giving_up_on_a_loop_also_leaves_no_orphan():
    calls = [ToolCall(id=str(index), name="add", arguments={"a": 1}) for index in range(3)]

    class SameCallForever:
        def stream(self, messages, tools=None):
            yield TurnDone(message=Message(role="assistant", tool_calls=list(calls)))

    agent = Agent(
        provider=SameCallForever(),
        tools=ToolRegistry([ADD]),
        permissions=Permissions(auto_approve=True),
        max_turns=6,
    )
    events = list(agent.run("go"))
    assert "Stopping" in events[-1].message.content
    requested = {call.id for message in agent.messages for call in message.tool_calls}
    answered = {m.tool_call_id for m in agent.messages if m.role == "tool"}
    assert requested == answered, f"orphaned tool calls {requested - answered}"


def test_a_model_nudging_the_whitespace_is_still_caught():
    """The case a strict fingerprint misses.

    A model that retries with a space added or a word capitalised has not
    changed anything, but a fingerprint taken from the exact arguments
    says it has, so a strict check never fires.
    """
    wiggles = iter(["a.txt", "a.txt ", " a.txt", "A.TXT", "a.txt  ", "a.txt"])

    class NudgesTheWhitespace:
        def stream(self, messages, tools=None):
            yield TurnDone(
                message=Message(
                    role="assistant",
                    tool_calls=[
                        ToolCall(id="c", name="peek", arguments={"path": next(wiggles)})
                    ],
                )
            )

    peek = Tool(
        name="peek",
        description="d",
        parameters={"type": "object", "properties": {}},
        fn=lambda path=None: "Error: no such file",
        safe=True,
    )
    agent = Agent(
        provider=NudgesTheWhitespace(),
        tools=ToolRegistry([peek]),
        permissions=Permissions(auto_approve=True),
        max_turns=6,
    )
    events = list(agent.run("go"))
    results = [e for e in events if isinstance(e, ToolResult)]
    assert any("going in circles" in r.content for r in results)
    assert "Stopping" in events[-1].message.content


def test_a_tool_that_legitimately_returns_the_same_thing_is_left_alone():
    """The false positive that an earlier version of this check produced.

    A shell command that succeeds quietly returns the same empty output
    for every different thing it does. Reading no progress from that
    stopped real work half way through, and a wrong stop costs more than
    a late one.
    """
    names = iter(["a", "b", "c", "d", "e"])
    made = []

    class DifferentWorkEachTime:
        def stream(self, messages, tools=None):
            try:
                name = next(names)
            except StopIteration:
                yield TurnDone(message=Message(role="assistant", content="all done"))
                return
            yield TurnDone(
                message=Message(
                    role="assistant",
                    tool_calls=[ToolCall(id="c", name="make", arguments={"name": name})],
                )
            )

    make = Tool(
        name="make",
        description="d",
        parameters={"type": "object", "properties": {}},
        fn=lambda name: made.append(name) or "[no output]",
        safe=True,
    )
    agent = Agent(
        provider=DifferentWorkEachTime(),
        tools=ToolRegistry([make]),
        permissions=Permissions(auto_approve=True),
        max_turns=8,
    )
    list(agent.run("make them all"))
    assert made == ["a", "b", "c", "d", "e"], f"the run was stopped early, only made {made}"


def test_an_interrupt_inside_a_tool_still_answers_the_calls_behind_it():
    """The path that actually happens, and the one a plain loop misses.

    A second interrupt is documented as forcing the stop, and it arrives
    while a tool is running. Filling the gaps after the loop never runs,
    so the calls behind it are left unanswered and written to the session
    that way, which poisons every later resume of it.
    """
    calls = [ToolCall(id=str(i), name="boom", arguments={"n": i}) for i in range(3)]

    class ThreeAtOnce:
        def stream(self, messages, tools=None):
            yield TurnDone(message=Message(role="assistant", tool_calls=list(calls)))

    def explode(n=0):
        if n == 1:
            raise KeyboardInterrupt("the person pressed it again")
        return "fine"

    boom = Tool(
        name="boom",
        description="d",
        parameters={"type": "object", "properties": {}},
        fn=explode,
        safe=True,
    )
    saved = []
    agent = Agent(
        provider=ThreeAtOnce(),
        tools=ToolRegistry([boom]),
        permissions=Permissions(auto_approve=True),
        on_message=saved.append,
        max_turns=2,
    )
    with pytest.raises(KeyboardInterrupt):
        list(agent.run("go"))

    requested = {c.id for m in saved for c in m.tool_calls}
    answered = {m.tool_call_id for m in saved if m.role == "tool"}
    assert requested == answered, f"orphaned in the session {sorted(requested - answered)}"
