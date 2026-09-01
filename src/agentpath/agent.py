"""The agent loop.

The loop only yields events. It never prints and never asks the user
anything. That is what lets the same loop serve a terminal chat, a subagent
and an eval run without changing a line inside it.

Part 3 adds four things around the loop rather than inside it. Permissions
decide whether a tool may run. A callback records every message so a session
can be saved. A budget decides how much of the conversation is sent. A
cancellation token lets an interrupt stop real work. Each of those is
injected, so the loop still knows nothing about terminals, files or clocks.
"""
from collections.abc import Iterator

from agentpath.cancel import NEVER
from agentpath.context import fit_to_budget
from agentpath.permissions import Permissions, signature
from agentpath.tools.base import ToolRegistry
from agentpath.types import Message, ToolCallRequest, ToolResult, TurnDone
from agentpath.usage import Usage

REPEAT_LIMIT = 3


class Agent:
    def __init__(
        self,
        provider,
        tools=None,
        system=None,
        max_turns=10,
        permissions=None,
        on_message=None,
        budget=None,
        cancellation=None,
    ):
        self.provider = provider
        self.tools = tools if tools is not None else ToolRegistry()
        self.messages: list[Message] = []
        self.max_turns = max_turns
        if permissions is None:
            permissions = Permissions(auto_approve=True)
        self.permissions = permissions
        self.on_message = on_message
        self.budget = budget
        self.cancellation = cancellation or NEVER
        self.usage = Usage()
        if system:
            self._remember(Message(role="system", content=system))

    def _remember(self, message: Message) -> None:
        """Add to history and tell whoever is listening.

        The loop keeps the whole history even when only part of it is sent,
        because the full record is what a session file and a debugging
        session need. What shrinks is what travels, not what is remembered.
        """
        self.messages.append(message)
        if self.on_message:
            self.on_message(message)

    def _to_send(self) -> list[Message]:
        if self.budget is None:
            return self.messages
        return fit_to_budget(self.messages, self.budget)

    def run(self, user_input: str) -> Iterator:
        self._remember(Message(role="user", content=user_input))
        recent: list[str] = []
        self._warned: set[str] = set()
        self._stuck_on = None
        self._results: list[tuple[str, str]] = []

        for _ in range(self.max_turns):
            self.cancellation.raise_if_cancelled()
            assistant = None
            for event in self.provider.stream(self._to_send(), self.tools.schemas() or None):
                if isinstance(event, TurnDone):
                    assistant = event.message
                    self.usage.add(getattr(event, "usage", None) or {})
                else:
                    yield event
            self._remember(assistant)

            if not assistant.tool_calls:
                yield TurnDone(message=assistant)
                return

            # Every tool call in the message above needs a result, even the
            # ones we are about to abandon. An assistant message carrying
            # three tool calls followed by two results is rejected outright
            # by the API on the next request, and that request is the one
            # after the interruption, so the error looks unrelated to it.
            # This is the same pairing rule the context chapter is about.
            answered = 0
            stop_after_this_turn = False
            for call in assistant.tool_calls:
                if self.cancellation.cancelled:
                    break
                yield ToolCallRequest(tool_call=call)
                result = self._run_one(call, recent)
                yield result
                self._remember(
                    Message(role="tool", content=result.content, tool_call_id=call.id)
                )
                answered += 1
                if self._stuck_on and signature(call) == self._stuck_on:
                    stop_after_this_turn = True
                    break

            for call in assistant.tool_calls[answered:]:
                self._remember(
                    Message(
                        role="tool",
                        content="Not run. The run was stopped before this call.",
                        tool_call_id=call.id,
                    )
                )

            if stop_after_this_turn:
                giving_up = Message(
                    role="assistant",
                    content=(
                        "Stopping. A tool was called with the same arguments repeatedly, "
                        "it was warned once, and it repeated anyway. Nothing is changing, "
                        "so continuing would only cost money."
                    ),
                )
                self._remember(giving_up)
                yield TurnDone(message=giving_up)
                return
            self.cancellation.raise_if_cancelled()
        raise RuntimeError(f"agent stopped after max turns ({self.max_turns})")

    def _run_one(self, call, recent: list[str]) -> ToolResult:
        """Run one call, after checking permission and watching for a loop.

        The repeat check exists because a turn limit counts but does not
        think. A model can spend every turn it has retrying the same failing
        call with a comma moved, so we tell it plainly when it is going in
        circles rather than waiting for the budget to run out.

        The model gets exactly one warning. A warning it ignores is not a
        misunderstanding to clear up, it is a loop, and the caller is paying
        for every further turn.
        """
        current = signature(call)
        recent.append(current)

        # Two different ways of going in circles, and a turn cap sees
        # neither. The first is the same call over and over. The second is
        # the same tool with the arguments nudged, which produces a
        # different signature every time and so slips past any check that
        # only compares calls. What gives it away is the result. If a tool
        # keeps handing back exactly the same thing, nothing is changing,
        # whatever the arguments say.
        repeating = recent[-REPEAT_LIMIT:].count(current) >= REPEAT_LIMIT
        stalled = (
            len(self._results) >= REPEAT_LIMIT
            and len(set(self._results[-REPEAT_LIMIT:])) == 1
            and self._results[-1][0] == call.name
        )
        if repeating or stalled:
            marker = current if repeating else f"no progress from {call.name}"
            if marker in self._warned:
                self._stuck_on = current
            self._warned.add(marker)
            reason = (
                f"has been called with these exact arguments {REPEAT_LIMIT} times in a row"
                if repeating
                else f"has returned the same thing {REPEAT_LIMIT} times in a row"
            )
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=(
                    f"Error: {call.name} {reason} and nothing has changed. You are "
                    "going in circles. Stop repeating it and try a different approach."
                ),
            )

        tool = self.tools.get(call.name)
        if not self.permissions.check(tool, call):
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content="The user refused this call. Do not try it again, do something else.",
            )
        result = self.tools.run(call)
        self._results.append((call.name, result.content))
        return result
