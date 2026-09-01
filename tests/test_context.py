from agentpath.context import estimate_tokens, fit_to_budget, split_into_blocks
from agentpath.types import Message, ToolCall

CALL = ToolCall(id="c1", name="add", arguments={"a": 1})


def conversation():
    return [
        Message(role="system", content="be terse"),
        Message(role="user", content="first question"),
        Message(role="assistant", content="", tool_calls=[CALL]),
        Message(role="tool", content="result", tool_call_id="c1"),
        Message(role="assistant", content="first answer"),
        Message(role="user", content="second question"),
        Message(role="assistant", content="second answer"),
    ]


def test_blocks_start_at_user_messages():
    blocks = split_into_blocks(conversation()[1:])
    assert len(blocks) == 2
    assert blocks[0][0].content == "first question"
    assert blocks[1][0].content == "second question"


def test_a_tool_call_and_its_result_stay_in_the_same_block():
    blocks = split_into_blocks(conversation()[1:])
    assert [m.role for m in blocks[0]] == ["user", "assistant", "tool", "assistant"]


def test_the_system_message_is_never_dropped():
    assert fit_to_budget(conversation(), budget=1)[0].role == "system"


def test_the_most_recent_exchange_is_kept():
    assert fit_to_budget(conversation(), budget=20)[-1].content == "second answer"


def test_no_orphan_tool_result_survives_trimming():
    """This is the bug the whole module exists to prevent.

    A tool result whose matching tool call has been trimmed away makes the
    API reject the next request outright with a 400, so trimming has to
    treat the pair as one thing. Sweeping every budget catches an off by one
    that a single chosen number would miss.
    """
    for budget in range(1, 60):
        kept = fit_to_budget(conversation(), budget=budget)
        call_ids = {call.id for message in kept for call in message.tool_calls}
        result_ids = {m.tool_call_id for m in kept if m.role == "tool"}
        assert result_ids <= call_ids, f"orphaned tool result at budget {budget}"


def test_a_conversation_always_keeps_something_to_answer():
    for budget in range(1, 60):
        kept = fit_to_budget(conversation(), budget=budget)
        assert any(m.role == "user" for m in kept), f"nothing to answer at budget {budget}"


def test_everything_fits_when_the_budget_is_large():
    assert fit_to_budget(conversation(), budget=10000) == conversation()


def test_estimate_grows_with_length():
    long_message = [Message(role="user", content="x" * 400)]
    short_message = [Message(role="user", content="x" * 40)]
    assert estimate_tokens(long_message) > estimate_tokens(short_message)
