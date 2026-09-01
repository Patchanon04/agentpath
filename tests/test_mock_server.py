import json

import httpx
import pytest

from agentpath.testing.mock_server import serve


@pytest.fixture
def mock():
    base_url, shutdown = serve()
    yield base_url
    shutdown()


def read_sse(response):
    """Return the list of json payloads from an SSE response body."""
    events = []
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        data = line[len("data: ") :]
        if data == "[DONE]":
            break
        events.append(json.loads(data))
    return events


def test_openai_plain_text(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={"model": "mock", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"]
    assert body["choices"][0]["message"].get("tool_calls") in (None, [])


def test_openai_echoes_tool_result(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "", "tool_calls": []},
                {"role": "tool", "tool_call_id": "call_1", "content": "5"},
            ],
        },
    )
    assert "5" in response.json()["choices"][0]["message"]["content"]


def test_openai_streams_text_in_several_chunks(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={"model": "mock", "messages": [{"role": "user", "content": "hi"}], "stream": True},
    )
    assert response.headers["content-type"].startswith("text/event-stream")
    events = read_sse(response)
    pieces = [e["choices"][0]["delta"].get("content", "") for e in events]
    assert len(events) > 1
    assert "".join(pieces) == "Hello from the mock server."


def test_directive_produces_tool_call(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [
                {"role": "user", "content": 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'}
            ],
        },
    )
    call = response.json()["choices"][0]["message"]["tool_calls"][0]
    assert call["function"]["name"] == "add"
    assert json.loads(call["function"]["arguments"]) == {"a": 2, "b": 3}


def test_streamed_tool_arguments_arrive_in_pieces(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={
            "model": "mock",
            "messages": [{"role": "user", "content": '[[tool:add:{"a": 2, "b": 3}]]'}],
            "stream": True,
        },
    )
    events = read_sse(response)
    fragments = [
        chunk["function"]["arguments"]
        for event in events
        for chunk in event["choices"][0]["delta"].get("tool_calls", [])
        if "arguments" in chunk.get("function", {})
    ]
    assert len(fragments) > 2, "arguments must be split so clients have to accumulate"
    assert json.loads("".join(fragments)) == {"a": 2, "b": 3}


def test_anthropic_plain_text(mock):
    response = httpx.post(
        f"{mock}/v1/messages",
        json={"model": "mock", "max_tokens": 100, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["content"][0]["type"] == "text"
    assert body["content"][0]["text"] == "Hello from the mock server."


def test_anthropic_tool_use(mock):
    response = httpx.post(
        f"{mock}/v1/messages",
        json={
            "model": "mock",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": '[[tool:add:{"a": 2, "b": 3}]]'}],
        },
    )
    block = response.json()["content"][0]
    assert block["type"] == "tool_use"
    assert block["name"] == "add"
    assert block["input"] == {"a": 2, "b": 3}


def test_anthropic_streams_text(mock):
    response = httpx.post(
        f"{mock}/v1/messages",
        json={
            "model": "mock",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    payloads = read_sse(response)
    kinds = [p["type"] for p in payloads]
    assert "content_block_delta" in kinds
    text = "".join(p["delta"]["text"] for p in payloads if p["type"] == "content_block_delta")
    assert text == "Hello from the mock server."


def test_anthropic_tool_result_block_is_echoed(mock):
    response = httpx.post(
        f"{mock}/v1/messages",
        json={
            "model": "mock",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "hi"},
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "call_mock_1", "content": "5"}
                    ],
                },
            ],
        },
    )
    assert "5" in response.json()["content"][0]["text"]


def test_multiple_directives_are_answered_one_at_a_time(mock):
    prompt = (
        'Fix it. [[tool:read_file:{"path": "a.py"}]]'
        '[[tool:edit_file:{"path": "a.py", "old": "x", "new": "y"}]]'
    )
    first = httpx.post(
        f"{mock}/v1/chat/completions",
        json={"model": "mock", "messages": [{"role": "user", "content": prompt}]},
    ).json()
    assert first["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "read_file"

    history = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "tool", "tool_call_id": "call_mock_1", "content": "x"},
    ]
    second = httpx.post(
        f"{mock}/v1/chat/completions", json={"model": "mock", "messages": history}
    ).json()
    assert second["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "edit_file"

    history += [
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "tool", "tool_call_id": "call_mock_2", "content": "done"},
    ]
    third = httpx.post(
        f"{mock}/v1/chat/completions", json={"model": "mock", "messages": history}
    ).json()
    assert not third["choices"][0]["message"].get("tool_calls")


def test_failure_can_be_requested_by_header(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={"model": "mock", "messages": [{"role": "user", "content": "hi"}]},
        headers={"X-Mock-Fail": "429"},
    )
    assert response.status_code == 429
    assert response.headers.get("retry-after") == "2"


def test_failure_can_be_made_to_stop_after_a_number_of_calls(mock):
    headers = {"X-Mock-Fail": "500", "X-Mock-Fail-Times": "2"}
    body = {"model": "mock", "messages": [{"role": "user", "content": "hi"}]}
    codes = [
        httpx.post(f"{mock}/v1/chat/completions", json=body, headers=headers).status_code
        for _ in range(3)
    ]
    assert codes == [500, 500, 200]


def test_responses_report_token_usage(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={"model": "mock", "messages": [{"role": "user", "content": "hi"}]},
    )
    usage = response.json()["usage"]
    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0


def test_streamed_responses_report_usage_on_the_last_chunk(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={"model": "mock", "messages": [{"role": "user", "content": "hi"}], "stream": True},
    )
    events = read_sse(response)
    assert events[-1]["usage"]["prompt_tokens"] > 0
