"""Deciding what the agent is allowed to do, and remembering the answer.

Lesson 08 asked a yes or no question before every command. That is correct
and it is also unusable, because being asked to approve the same harmless
command forty times trains you to stop reading the question. A permission
system is what you get when you keep the gate and remove the fatigue.

The rule for what counts as risky lives on the Tool rather than here. The
person who writes a tool knows whether it can destroy something, and a
default of not safe means that forgetting to think about it leads to a
question rather than to silence.
"""
import json
from dataclasses import dataclass, field

from agentpath.tools.base import Tool
from agentpath.types import ToolCall

ALLOW_ONCE = "allow_once"
ALLOW_ALWAYS = "allow_always"
DENY = "deny"


def signature(call: ToolCall) -> str:
    """A stable string identifying this exact call, used for remembering.

    The arguments are part of the signature on purpose. Approving
    git status must not also approve rm -rf, and a rule keyed on the tool
    name alone would do exactly that.
    """
    return f"{call.name}({json.dumps(call.arguments, sort_keys=True)})"


def loose_signature(call: ToolCall) -> str:
    """The same idea, but blind to whitespace and letter case.

    This one is for spotting a model going in circles, not for deciding what
    is allowed. A model that retries with a trailing space added, or with a
    word capitalised, has not changed anything and should not get a fresh
    fingerprint for it. Permission decisions keep using the exact signature,
    because there the difference between two nearly identical commands can
    be the whole point.
    """
    # Trailing and leading space only. An earlier version also folded case
    # and collapsed interior spaces, which made three genuinely different
    # searches look identical. A model widening a case sensitive pattern from
    # Error to ERROR to error is doing the right thing, and it was being told
    # it was going in circles and then stopped.
    flattened = {key: str(value).strip() for key, value in call.arguments.items()}
    return f"{call.name}({json.dumps(flattened, sort_keys=True)})"


@dataclass
class Permissions:
    ask: object = None
    auto_approve: bool = False
    remembered: set = field(default_factory=set)

    def check(self, tool: Tool, call: ToolCall) -> bool:
        """Say whether this call may run, asking a person only when needed."""
        if tool is not None and tool.safe:
            return True
        if self.auto_approve:
            return True
        if signature(call) in self.remembered:
            return True
        if self.ask is None:
            return False
        answer = self.ask(tool, call)
        if answer == ALLOW_ALWAYS:
            self.remembered.add(signature(call))
            return True
        return answer == ALLOW_ONCE


def ask_in_terminal(tool: Tool, call: ToolCall) -> str:
    """Ask the person at the keyboard, offering the three real answers.

    Yes and no are not enough. Without an always option the person is asked
    the same question repeatedly and starts approving without reading, which
    is worse than having no gate at all.
    """
    print(f"\nThe agent wants to run {call.name}")
    for key, value in call.arguments.items():
        print(f"  {key} = {value!r}")
    try:
        answer = input("Allow? [y]es once, [a]lways for this exact call, [N]o ")
    except (EOFError, KeyboardInterrupt):
        print()
        return DENY
    answer = answer.strip().lower()
    if answer in ("a", "always"):
        return ALLOW_ALWAYS
    if answer in ("y", "yes"):
        return ALLOW_ONCE
    return DENY
