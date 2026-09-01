from agentpath.permissions import ALLOW_ALWAYS, ALLOW_ONCE, DENY, Permissions
from agentpath.tools.base import Tool
from agentpath.types import ToolCall

SAFE = Tool("read_file", "d", {}, lambda: None, safe=True)
RISKY = Tool("run_shell", "d", {}, lambda: None, safe=False)


def test_safe_tools_never_ask():
    asked = []
    permissions = Permissions(ask=lambda tool, call: asked.append(call) or DENY)
    assert permissions.check(SAFE, ToolCall("1", "read_file", {})) is True
    assert asked == []


def test_a_tool_defaults_to_not_safe():
    assert Tool("mystery", "d", {}, lambda: None).safe is False


def test_risky_tools_ask():
    permissions = Permissions(ask=lambda tool, call: ALLOW_ONCE)
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "ls"})) is True


def test_deny_stops_the_call():
    permissions = Permissions(ask=lambda tool, call: DENY)
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "ls"})) is False


def test_allow_once_does_not_persist():
    answers = iter([ALLOW_ONCE, DENY])
    permissions = Permissions(ask=lambda tool, call: next(answers))
    call = ToolCall("1", "run_shell", {"command": "ls"})
    assert permissions.check(RISKY, call) is True
    assert permissions.check(RISKY, call) is False


def test_allow_always_is_remembered_for_the_same_command():
    asked = []

    def ask(tool, call):
        asked.append(call)
        return ALLOW_ALWAYS

    permissions = Permissions(ask=ask)
    call = ToolCall("1", "run_shell", {"command": "git status"})
    assert permissions.check(RISKY, call) is True
    assert permissions.check(RISKY, call) is True
    assert len(asked) == 1


def test_allow_always_does_not_leak_to_a_different_command():
    answers = iter([ALLOW_ALWAYS, DENY])
    permissions = Permissions(ask=lambda tool, call: next(answers))
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "git status"})) is True
    assert permissions.check(RISKY, ToolCall("2", "run_shell", {"command": "rm -rf /"})) is False


def test_auto_approve_mode_never_asks():
    permissions = Permissions(ask=lambda tool, call: DENY, auto_approve=True)
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "ls"})) is True


def test_with_no_way_to_ask_the_answer_is_no():
    """Silence must not mean yes.

    A harness running with no human attached and no explicit auto approve
    has nobody to consult, so the only safe reading is a refusal.
    """
    assert Permissions().check(RISKY, ToolCall("1", "run_shell", {"command": "ls"})) is False
