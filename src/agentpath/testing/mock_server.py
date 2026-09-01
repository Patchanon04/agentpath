"""A deterministic fake LLM server.

Lesson checks and unit tests point AGENTPATH_BASE_URL at this server so the
whole project can be verified without spending money or needing an API key.

The server never guesses. A caller steers it by putting a directive in the
last user message. The directive looks like this.

    [[tool:add:{"a": 2, "b": 3}]]

When the directive is present the server answers with a tool call for that
tool and those arguments. When it is absent the server answers with plain
text. When the last message is a tool result the server answers with text
that repeats the result, so a caller can prove the result travelled back
into the conversation.
"""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

# Tool names may contain dots and dashes because MCP tools are prefixed
# with the name of the server they came from.
DIRECTIVE = re.compile(r"\[\[tool:([A-Za-z_][A-Za-z0-9_.-]*):(\{.*?\})\]\]", re.DOTALL)
GREETING = "Hello from the mock server."
CALL_ID = "call_mock_1"


def _text_of(message):
    """Return the readable text of a message in either dialect."""
    content = message.get("content", "")
    if isinstance(content, list):
        return " ".join(block.get("text", "") for block in content)
    return content or ""


def _tool_result_of(message):
    """Return the tool result content of a message, or None."""
    if message.get("role") == "tool":
        return message.get("content", "")
    content = message.get("content", "")
    if isinstance(content, list):
        for block in content:
            if block.get("type") == "tool_result":
                return block.get("content", "")
    return None


def decide(messages):
    """Return (text, tool_calls) for a list of wire format messages.

    A caller can chain several tool calls by putting several directives in
    the same message. We answer them one at a time, choosing which one by
    counting how many tool results have already come back.
    """
    directives = []
    for message in messages:
        directives.extend(DIRECTIVE.findall(_text_of(message)))

    completed = sum(1 for message in messages if _tool_result_of(message) is not None)

    if directives and completed < len(directives):
        name, raw_arguments = directives[completed]
        return "", [
            {
                "id": f"call_mock_{completed + 1}",
                "name": name,
                "arguments": json.loads(raw_arguments),
            }
        ]

    last_result = _tool_result_of(messages[-1]) if messages else None
    if last_result is not None:
        return f"The tool returned {last_result}.", []
    return GREETING, []


def chunk_text(text, size=6):
    """Split text into small pieces so a client must accumulate them."""
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


def estimate_tokens(text):
    """A deliberately crude token estimate, about four characters per token.

    This is not accurate and the chapter on token economy says so plainly.
    It exists so the mock can report a number that moves in the right
    direction when the conversation grows.
    """
    return max(1, len(text) // 4)


def usage_for(messages, text, tool_calls):
    prompt = sum(estimate_tokens(_text_of(message)) for message in messages)
    completion = estimate_tokens(text) + sum(
        estimate_tokens(json.dumps(call["arguments"])) for call in tool_calls
    )
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }


def openai_body(text, tool_calls, usage=None):
    message = {"role": "assistant", "content": text or None}
    if tool_calls:
        message["tool_calls"] = [
            {
                "id": call["id"],
                "type": "function",
                "function": {"name": call["name"], "arguments": json.dumps(call["arguments"])},
            }
            for call in tool_calls
        ]
    finish = "tool_calls" if tool_calls else "stop"
    return {
        "id": "mock-1",
        "object": "chat.completion",
        "model": "mock",
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": usage,
    }


def openai_stream_events(text, tool_calls, usage=None):
    """Yield the dict payloads of an OpenAI style SSE stream."""
    if text:
        for piece in chunk_text(text):
            yield {"choices": [{"index": 0, "delta": {"content": piece}}]}
    for index, call in enumerate(tool_calls):
        yield {
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": index,
                                "id": call["id"],
                                "type": "function",
                                "function": {"name": call["name"], "arguments": ""},
                            }
                        ]
                    },
                }
            ]
        }
        for piece in chunk_text(json.dumps(call["arguments"]), size=5):
            yield {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [{"index": index, "function": {"arguments": piece}}]
                        },
                    }
                ]
            }
    finish = "tool_calls" if tool_calls else "stop"
    yield {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}], "usage": usage}


def anthropic_body(text, tool_calls, usage=None):
    if tool_calls:
        blocks = [
            {"type": "tool_use", "id": call["id"], "name": call["name"], "input": call["arguments"]}
            for call in tool_calls
        ]
        stop_reason = "tool_use"
    else:
        blocks = [{"type": "text", "text": text}]
        stop_reason = "end_turn"
    return {
        "id": "mock-1",
        "type": "message",
        "role": "assistant",
        "model": "mock",
        "content": blocks,
        "stop_reason": stop_reason,
        "usage": usage,
    }


def anthropic_stream_events(text, tool_calls, usage=None):
    yield {"type": "message_start", "message": {"id": "mock-1", "role": "assistant", "content": []}}
    if tool_calls:
        for index, call in enumerate(tool_calls):
            yield {
                "type": "content_block_start",
                "index": index,
                "content_block": {
                    "type": "tool_use",
                    "id": call["id"],
                    "name": call["name"],
                    "input": {},
                },
            }
            for piece in chunk_text(json.dumps(call["arguments"]), size=5):
                yield {
                    "type": "content_block_delta",
                    "index": index,
                    "delta": {"type": "input_json_delta", "partial_json": piece},
                }
            yield {"type": "content_block_stop", "index": index}
        yield {"type": "message_delta", "delta": {"stop_reason": "tool_use"}}
    else:
        yield {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        }
        for piece in chunk_text(text):
            yield {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": piece},
            }
        yield {"type": "content_block_stop", "index": 0}
        yield {"type": "message_delta", "delta": {"stop_reason": "end_turn"}}
    yield {"type": "message_stop", "usage": usage}


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def _send_json(self, payload, status=200, extra_headers=None):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def _maybe_fail(self):
        """Return True when this request should fail, per the caller's headers.

        The caller drives this rather than the server failing on its own,
        because a test that fails at random is not a test.

        The counter lives on the server rather than in a module global so
        that each server starts fresh. A shared global would make one test
        depend on how many tests ran before it, which is the kind of bug
        that only appears when the whole suite runs.
        """
        status = self.headers.get("X-Mock-Fail")
        if not status:
            return False
        times = self.headers.get("X-Mock-Fail-Times")
        if times is not None:
            counts = getattr(self.server, "fail_counts", None)
            if counts is None:
                counts = self.server.fail_counts = {}
            key = f"{status}:{times}:{self.path}"
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > int(times):
                return False
        code = int(status)
        headers = {"Retry-After": "2"} if code == 429 else {}
        self._send_json(
            {"error": {"type": "mock_failure", "code": code}},
            status=code,
            extra_headers=headers,
        )
        return True

    def _send_sse(self, events):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for event in events:
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def do_POST(self):
        payload = self._read_json()
        if self._maybe_fail():
            return
        messages = payload.get("messages", [])
        text, tool_calls = decide(messages)
        usage = usage_for(messages, text, tool_calls)
        streaming = bool(payload.get("stream"))
        path = self.path.rstrip("/")
        if path.endswith("/chat/completions"):
            if streaming:
                self._send_sse(openai_stream_events(text, tool_calls, usage))
            else:
                self._send_json(openai_body(text, tool_calls, usage))
            return
        if path.endswith("/messages"):
            if streaming:
                self._send_sse(anthropic_stream_events(text, tool_calls, usage))
            else:
                self._send_json(anthropic_body(text, tool_calls, usage))
            return
        self._send_json({"error": f"unknown path {self.path}"}, status=404)

    def do_GET(self):
        self._send_json({"status": "ok"})


def serve(port=0):
    """Start the mock server on a background thread.

    Returns (base_url, shutdown). Call shutdown when the test is finished.
    """
    server = ThreadingHTTPServer(("127.0.0.1", port), MockHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{server.server_port}", server.shutdown


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="agentpath-mock")
    parser.add_argument("--port", type=int, default=8765)
    arguments = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), MockHandler)
    print(f"mock server listening on http://127.0.0.1:{server.server_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
