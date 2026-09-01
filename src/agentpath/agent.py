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
from agentpath.permissions import Permissions, loose_signature
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
            # The fill in below runs in a finally, not after the loop. An
            # interrupt arriving while a tool is running raises straight
            # through, and a plain loop would leave the calls behind it
            # with no result at all. That poisons the next request and,
            # because every message is written to the session as it
            # happens, poisons the saved session for good.
            try:
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
                    if self._stuck_on and loose_signature(call) == self._stuck_on:
                        stop_after_this_turn = True
                        break
            finally:
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
        current = loose_signature(call)
        recent.append(current)

        # The fingerprint here is deliberately blind to whitespace and
        # letter case, because a model that retries with a space added has
        # not changed anything and should not get a fresh fingerprint for
        # it. That is the whole of the check.
        #
        # An earlier version also cried loop when a tool returned the same
        # text three times running, on the theory that identical results
        # mean no progress. That is not true and it stopped real work. A
        # tool that legitimately prints nothing, such as a shell command
        # that succeeds quietly, returns the same text for every different
        # thing it does. Deciding a run has stalled from the shape of the
        # output alone is not something a cheap check can do correctly,
        # and a wrong stop costs more than a late one.
        if recent[-REPEAT_LIMIT:].count(current) >= REPEAT_LIMIT:
            if current in self._warned:
                self._stuck_on = current
            self._warned.add(current)
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=(
                    f"Error: {call.name} has been called with the same arguments "
                    f"{REPEAT_LIMIT} times in a row and nothing has changed. You are "
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
        return self.tools.run(call)
