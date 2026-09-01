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

DIRECTIVE = re.compile(r"\[\[tool:([A-Za-z_][A-Za-z0-9_]*):(\{.*?\})\]\]", re.DOTALL)
GREETING = "Hello from the mock server."
CALL_ID = "call_mock_1"


def decide(messages):
    """Return (text, tool_calls) for a list of wire format messages."""
    last = messages[-1] if messages else {}
    role = last.get("role", "")
    content = last.get("content", "")

    if role == "tool":
        return f"The tool returned {content}.", []

    if isinstance(content, list):
        for block in content:
            if block.get("type") == "tool_result":
                return f"The tool returned {block.get('content', '')}.", []
        content = " ".join(block.get("text", "") for block in content)

    match = DIRECTIVE.search(content or "")
    if match:
        name, raw_arguments = match.group(1), match.group(2)
        return "", [{"id": CALL_ID, "name": name, "arguments": json.loads(raw_arguments)}]
    return GREETING, []


def chunk_text(text, size=6):
    """Split text into small pieces so a client must accumulate them."""
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


def openai_body(text, tool_calls):
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
    }


def openai_stream_events(text, tool_calls):
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
    yield {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]}


def anthropic_body(text, tool_calls):
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
    }


def anthropic_stream_events(text, tool_calls):
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
    yield {"type": "message_stop"}


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def _send_json(self, payload, status=200):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

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
        text, tool_calls = decide(payload.get("messages", []))
        streaming = bool(payload.get("stream"))
        path = self.path.rstrip("/")
        if path.endswith("/chat/completions"):
            if streaming:
                self._send_sse(openai_stream_events(text, tool_calls))
            else:
                self._send_json(openai_body(text, tool_calls))
            return
        if path.endswith("/messages"):
            if streaming:
                self._send_sse(anthropic_stream_events(text, tool_calls))
            else:
                self._send_json(anthropic_body(text, tool_calls))
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
