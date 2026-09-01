"""Two providers, one interface.

The OpenAI format and the Anthropic format disagree in three places. The
system prompt is a message in one and a top level field in the other. Tool
schemas use the key parameters in one and input_schema in the other. Tool
results come back as a message with the tool role in one and as content
blocks inside a user message in the other.

Wrapping both behind one stream method is what lets the agent loop below
stay completely unaware of which service it is talking to.
"""
import json
import os

import httpx

from retry import with_retries


def parse_arguments(raw):
    """Return (arguments, error). See lesson 05 for why we do not hide this."""
    try:
        return json.loads(raw or "{}"), ""
    except json.JSONDecodeError as problem:
        return {}, f"arguments were not valid JSON ({problem})"


def open_stream(client, url, payload, headers, attempts=4):
    """Open a streaming request, retrying the failures worth retrying."""

    def once():
        request = client.build_request("POST", url, json=payload, headers=headers)
        response = client.send(request, stream=True)
        if response.status_code >= 400:
            response.read()
            response.close()
            response.raise_for_status()
        return response

    return with_retries(once, attempts=attempts)


class OpenAICompatProvider:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]

    def stream(self, messages, tools=None, on_text=None):
        usage = {}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        text_parts = []
        partial = {}
        with httpx.Client(timeout=120) as client:
            # Only opening the request is retried. Once bytes have arrived the
            # caller has already seen part of an answer, and replaying would
            # splice a second answer onto the first.
            response = open_stream(
                client, f"{self.base_url}/chat/completions", payload, headers
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
                        if on_text:
                            on_text(delta["content"])
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
        for _, s in sorted(partial.items()):
            arguments, error = parse_arguments(s["arguments"])
            calls.append({"id": s["id"], "name": s["name"], "arguments": arguments, "error": error})
        return "".join(text_parts), calls, usage


class AnthropicProvider:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]

    def _to_wire(self, messages):
        wire = []
        for message in messages:
            if message["role"] == "system":
                continue
            if message["role"] == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": message["tool_call_id"],
                    "content": message["content"],
                }
                if wire and wire[-1]["role"] == "user" and isinstance(wire[-1]["content"], list):
                    wire[-1]["content"].append(block)
                else:
                    wire.append({"role": "user", "content": [block]})
                continue
            if message["role"] == "assistant" and message.get("tool_calls"):
                blocks = []
                if message.get("content"):
                    blocks.append({"type": "text", "text": message["content"]})
                for call in message["tool_calls"]:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call["id"],
                            "name": call["function"]["name"],
                            "input": json.loads(call["function"]["arguments"] or "{}"),
                        }
                    )
                wire.append({"role": "assistant", "content": blocks})
                continue
            wire.append({"role": message["role"], "content": message["content"]})
        return wire

    def stream(self, messages, tools=None, on_text=None):
        usage = {}
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "stream": True,
            "messages": self._to_wire(messages),
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]

        text_parts = []
        blocks = {}
        with httpx.Client(timeout=120) as client:
            response = open_stream(client, f"{self.base_url}/messages", payload, headers)
            try:
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    if event.get("usage"):
                        usage = event["usage"]
                    if event.get("type") == "content_block_start":
                        block = event["content_block"]
                        if block.get("type") == "tool_use":
                            blocks[event["index"]] = {
                                "id": block["id"],
                                "name": block["name"],
                                "json": "",
                            }
                    elif event.get("type") == "content_block_delta":
                        delta = event["delta"]
                        if delta.get("type") == "text_delta":
                            text_parts.append(delta["text"])
                            if on_text:
                                on_text(delta["text"])
                        elif delta.get("type") == "input_json_delta":
                            blocks[event["index"]]["json"] += delta["partial_json"]
            finally:
                response.close()

        calls = []
        for _, s in sorted(blocks.items()):
            arguments, error = parse_arguments(s["json"])
            calls.append({"id": s["id"], "name": s["name"], "arguments": arguments, "error": error})
        return "".join(text_parts), calls, usage
