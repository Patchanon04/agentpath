"""Talk to the Anthropic messages API.

This provider exists to prove the interface is real. Anthropic differs from
the OpenAI format in three ways that matter. The system prompt is a top level
field instead of a message. Tool schemas use input_schema instead of
parameters. Tool results travel back as content blocks inside a user message
instead of a message with the tool role.
"""
import json
import os
from collections.abc import Iterator

import httpx

from agentpath.providers.base import Provider, open_stream, parse_arguments
from agentpath.types import Message, TextDelta, ToolCall, TurnDone

API_VERSION = "2023-06-01"


def normalise_usage(reported: dict) -> dict:
    """Rename Anthropic's usage fields to the ones the rest of the code uses.

    Anthropic says input_tokens and output_tokens where the OpenAI format
    says prompt_tokens and completion_tokens. Without this the counter reads
    zero against a real Anthropic endpoint and nothing errors, which is the
    worst kind of bug because the number it shows looks like an answer.
    """
    if not reported:
        return {}
    prompt = reported.get("prompt_tokens", reported.get("input_tokens", 0))
    completion = reported.get("completion_tokens", reported.get("output_tokens", 0))
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }


def to_wire(messages: list[Message]) -> list[dict]:
    """Convert the conversation into Anthropic content blocks.

    System messages are dropped here because they travel as a separate field.
    """
    wire: list[dict] = []
    for message in messages:
        if message.role == "system":
            continue
        if message.role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": message.tool_call_id,
                "content": message.content,
            }
            if wire and wire[-1]["role"] == "user" and isinstance(wire[-1]["content"], list):
                wire[-1]["content"].append(block)
            else:
                wire.append({"role": "user", "content": [block]})
            continue
        if message.role == "assistant" and message.tool_calls:
            blocks = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            blocks.extend(
                {
                    "type": "tool_use",
                    "id": call.id,
                    "name": call.name,
                    "input": call.arguments,
                }
                for call in message.tool_calls
            )
            wire.append({"role": "assistant", "content": blocks})
            continue
        wire.append({"role": message.role, "content": message.content})
    return wire


class AnthropicProvider(Provider):
    def __init__(
        self, base_url=None, api_key=None, model=None, client=None, timeout=120, attempts=4
    ):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]
        self.client = client or httpx.Client(timeout=timeout)
        self.attempts = attempts

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
        }

    def stream(self, messages: list[Message], tools: list[dict] | None = None) -> Iterator:
        system = "\n".join(m.content for m in messages if m.role == "system")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "stream": True,
            "messages": to_wire(messages),
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["parameters"],
                }
                for tool in tools
            ]

        text_parts: list[str] = []
        blocks: dict[int, dict] = {}
        usage: dict = {}

        response = open_stream(
            self.client,
            f"{self.base_url}/messages",
            payload,
            self._headers(),
            attempts=self.attempts,
        )
        try:
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                event = json.loads(data)
                # Usage arrives in two places and neither one is complete.
                # The input count rides inside message_start, nested under
                # message, and only the output count appears later at the
                # top level. Reading one and overwriting with the other is
                # how the prompt count silently reads zero.
                if event.get("type") == "message_start":
                    usage.update(normalise_usage((event.get("message") or {}).get("usage")))
                if event.get("usage"):
                    usage.update(
                        {
                            key: value
                            for key, value in normalise_usage(event["usage"]).items()
                            if value
                        }
                    )
                kind = event.get("type")
                if kind == "content_block_start":
                    block = event["content_block"]
                    if block.get("type") == "tool_use":
                        blocks[event["index"]] = {
                            "id": block["id"],
                            "name": block["name"],
                            "json": "",
                        }
                elif kind == "content_block_delta":
                    delta = event["delta"]
                    if delta.get("type") == "text_delta":
                        text_parts.append(delta["text"])
                        yield TextDelta(text=delta["text"])
                    elif delta.get("type") == "input_json_delta":
                        blocks[event["index"]]["json"] += delta["partial_json"]
            # The two halves were merged field by field, so the total that
            # came with the second half was computed from that half alone.
            if usage:
                usage["total_tokens"] = (
                    usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                )
        finally:
            response.close()

        calls = []
        for _, slot in sorted(blocks.items()):
            arguments, error = parse_arguments(slot["json"])
            calls.append(
                ToolCall(
                    id=slot["id"], name=slot["name"], arguments=arguments, arguments_error=error
                )
            )
        yield TurnDone(
            message=Message(role="assistant", content="".join(text_parts), tool_calls=calls),
            usage=usage,
        )
