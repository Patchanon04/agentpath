"""Talk to any server that speaks the OpenAI chat completions format.

That covers OpenAI itself, Ollama, Groq and OpenRouter. They differ only in
base url and model name, which is why this one class serves all of them.
"""
import json
import os
from collections.abc import Iterator

import httpx

from agentpath.providers.base import Provider, open_stream, parse_arguments
from agentpath.types import Message, TextDelta, ToolCall, TurnDone


def to_wire(message: Message) -> dict:
    """Convert one Message into the shape the API expects."""
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content,
        }
    wire = {"role": message.role, "content": message.content}
    if message.tool_calls:
        wire["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    return wire


class OpenAICompatProvider(Provider):
    def __init__(
        self, base_url=None, api_key=None, model=None, client=None, timeout=120, attempts=4
    ):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]
        self.client = client or httpx.Client(timeout=timeout)
        self.attempts = attempts

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def stream(self, messages: list[Message], tools: list[dict] | None = None) -> Iterator:
        payload = {
            "model": self.model,
            "messages": [to_wire(m) for m in messages],
            "stream": True,
            # OpenAI only reports what a streamed request cost when asked.
            # Servers that do not know this option ignore it, so asking is
            # free and not asking means flying blind on the real endpoint.
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": tool} for tool in tools]

        text_parts: list[str] = []
        partial: dict[int, dict] = {}
        usage: dict = {}

        response = open_stream(
            self.client,
            f"{self.base_url}/chat/completions",
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
                chunk = json.loads(data)
                if chunk.get("usage"):
                    usage = chunk["usage"]
                if not chunk.get("choices"):
                    continue
                delta = chunk["choices"][0].get("delta", {})
                if delta.get("content"):
                    text_parts.append(delta["content"])
                    yield TextDelta(text=delta["content"])
                for chunk in delta.get("tool_calls", []):
                    slot = partial.setdefault(
                        chunk.get("index", 0), {"id": "", "name": "", "arguments": ""}
                    )
                    if chunk.get("id"):
                        slot["id"] = chunk["id"]
                    function = chunk.get("function", {})
                    if function.get("name"):
                        slot["name"] = function["name"]
                    if function.get("arguments"):
                        slot["arguments"] += function["arguments"]
        finally:
            response.close()

        calls = []
        for _, slot in sorted(partial.items()):
            arguments, error = parse_arguments(slot["arguments"])
            calls.append(
                ToolCall(
                    id=slot["id"],
                    name=slot["name"],
                    arguments=arguments,
                    arguments_error=error,
                )
            )
        yield TurnDone(
            message=Message(role="assistant", content="".join(text_parts), tool_calls=calls),
            usage=usage,
        )
