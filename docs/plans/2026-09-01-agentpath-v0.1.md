# agentpath v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ส่งมอบ agentpath v0.1 ซึ่งประกอบด้วยบทเรียน 00 ถึง 06 (ภาค 1 Foundations) พร้อม package `agentpath` ที่ติดตั้งใช้งานได้จริงและ CI ที่ตรวจทุกบทโดยไม่ยิง API จริง

**Architecture:** โค้ดสองชุดที่แยกกันโดยตั้งใจ ชุดแรกคือ `lessons/NN-name/*.py` ไฟล์แบนๆ ที่ผู้เรียนพิมพ์ตามทีละบท ชุดที่สองคือ `src/agentpath/` package ตัวจริงที่มีสถานะเท่ากับจุดจบบทที่ 06 ทั้งสองชุดอ่าน config จาก environment variable เดียวกัน ทำให้ CI ชี้ทั้งคู่ไปที่ mock LLM server ตัวเดียวกันได้ mock server เป็นหัวใจของงานนี้และต้องสร้างก่อนของอย่างอื่น

**Tech Stack:** Python 3.10 ขึ้นไป, httpx (dependency เดียว), stdlib http.server สำหรับ mock, pytest, ruff, uv, GitHub Actions

**Spec:** `docs/specs/2026-09-01-agentpath-design.md`

---

## File Structure

ไฟล์ที่จะถูกสร้างใน v0.1 และหน้าที่ของแต่ละไฟล์

**Package**

| ไฟล์ | หน้าที่ |
|------|---------|
| `src/agentpath/types.py` | dataclass กลาง Message, ToolCall และ event ทั้งสี่ชนิด ไม่มี logic |
| `src/agentpath/providers/base.py` | interface `Provider` ที่มีเมธอดเดียวคือ `stream` |
| `src/agentpath/providers/openai_compat.py` | คุยกับ OpenAI, Ollama, Groq, OpenRouter |
| `src/agentpath/providers/anthropic.py` | คุยกับ Anthropic Messages API |
| `src/agentpath/tools/base.py` | dataclass `Tool` และ `ToolRegistry` ที่แปลง schema และรัน tool |
| `src/agentpath/agent.py` | agent loop ที่ yield event ออกอย่างเดียว |
| `src/agentpath/cli.py` | `agentpath chat` ด้วย argparse |
| `src/agentpath/testing/mock_server.py` | fake LLM ที่ตอบแบบ deterministic ทั้ง OpenAI และ Anthropic dialect |

**Lessons** ทุกบทมี `README.md` และ `check.py` เสมอ บทที่มีโค้ดมีไฟล์เพิ่มตามตาราง

| บท | ไฟล์โค้ด |
|----|----------|
| `lessons/00-setup/` | ไม่มีโค้ดสอน มีแค่ check.py ตรวจ environment |
| `lessons/01-first-llm-call/` | `llm.py` |
| `lessons/02-conversation-loop/` | `llm.py`, `chat.py` |
| `lessons/03-tool-calling/` | `llm.py`, `tools.py` |
| `lessons/04-agent-loop/` | `llm.py`, `tools.py`, `agent.py` |
| `lessons/05-streaming/` | `llm.py`, `tools.py`, `agent.py` |
| `lessons/06-provider-abstraction/` | `providers.py`, `tools.py`, `agent.py` |

**Infrastructure**

| ไฟล์ | หน้าที่ |
|------|---------|
| `ci/run_lessons.py` | เปิด mock server แล้วรัน check.py ของทุกบท |
| `ci/prose_lint.py` | fail ถ้าเจอ em-dash หรือ emoji ในไฟล์ md |
| `.github/workflows/ci.yml` | สี่งาน ruff, lessons, pytest, prose lint บน Ubuntu และ Windows |

## Key Design Decisions ที่ทุก task ต้องยึด

1. **mock server มีที่อยู่เดียวคือ `src/agentpath/testing/mock_server.py`** ส่วน `ci/run_lessons.py` เป็นแค่ตัวเรียก ไม่ก็อปโค้ด mock ซ้ำ CI จึงต้อง `pip install -e .` ก่อนรัน lesson checks
2. **โค้ดบทเรียนไม่ import `agentpath`** เด็ดขาด เพราะจะชนกับ package ที่ติดตั้งไว้ ทุกบท import ไฟล์ข้างๆ ตรงๆ เช่น `from llm import ask`
3. **การควบคุม mock ทำผ่าน directive ในข้อความผู้ใช้** รูปแบบ `[[tool:NAME:JSON]]` เมื่อ mock เห็น pattern นี้จะตอบเป็น tool call ของ NAME พร้อม argument ตาม JSON ที่ให้มา ผลคือ check.py ตัวเดียวกันทำงานได้ทั้งกับ mock (อ่าน directive) และกับ model จริง (อ่านประโยคภาษาคนที่อยู่ข้างหน้า directive แล้วเรียก tool เดียวกัน)
4. **provider yield แค่ TextDelta ระหว่างทางและ TurnDone ตอนจบ** ส่วน ToolCallRequest กับ ToolResult เป็นหน้าที่ของ agent loop เท่านั้น ห้ามให้ provider รู้จักการรัน tool
5. **env var สามตัวเท่านั้น** `AGENTPATH_BASE_URL`, `AGENTPATH_API_KEY`, `AGENTPATH_MODEL` ห้าม hardcode
6. **ไฟล์ md ทุกไฟล์ห้ามมี em-dash และ emoji** รวมถึงไฟล์ plan นี้เอง เพราะ prose lint สแกน `**/*.md` ทั้ง repo

---

## Task 1: Repo scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `src/agentpath/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: เขียน pyproject.toml**

```toml
[project]
name = "agentpath"
version = "0.1.0"
description = "Learn how AI agents actually work by building a real one, from a single LLM call to a full agent harness."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
dependencies = ["httpx>=0.27"]

[project.scripts]
agentpath = "agentpath.cli:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agentpath"]

[tool.ruff]
line-length = 100
exclude = ["lessons"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

หมายเหตุ `exclude = ["lessons"]` ตั้งไว้ก่อนเพราะ Task 22 จะเพิ่มการ lint บทเรียนด้วยกฎที่ผ่อนกว่า

- [ ] **Step 2: เขียน .gitignore**

```
__pycache__/
*.py[cod]
.venv/
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
.env
```

- [ ] **Step 3: เขียน LICENSE**

ใช้ MIT License ฉบับมาตรฐาน ปี 2026 ชื่อผู้ถือสิทธิ์คือเจ้าของ repo

- [ ] **Step 4: สร้างไฟล์ package ว่าง**

```python
# src/agentpath/__init__.py
__version__ = "0.1.0"
```

```python
# tests/__init__.py
```

- [ ] **Step 5: ติดตั้งและยืนยัน**

```bash
uv venv && uv pip install -e ".[dev]"
```

Expected: ติดตั้งสำเร็จ และ `python -c "import agentpath; print(agentpath.__version__)"` พิมพ์ `0.1.0`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore LICENSE src tests
git commit -m "chore: scaffold package with uv, ruff, pytest"
```

---

## Task 2: Prose lint

สร้างก่อนเขียนเอกสารใดๆ เพื่อให้กฎห้าม em-dash บังคับใช้ตั้งแต่ commit แรกของเนื้อหา

**Files:**
- Create: `ci/prose_lint.py`
- Create: `tests/test_prose_lint.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_prose_lint.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))

from prose_lint import find_violations


def test_flags_em_dash(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("a \u2014 b", encoding="utf-8")
    violations = find_violations([target])
    assert len(violations) == 1
    assert violations[0][1] == 1


def test_flags_emoji(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("all good \U0001F600", encoding="utf-8")
    assert len(find_violations([target])) == 1


def test_clean_file_passes(tmp_path):
    target = tmp_path / "doc.md"
    target.write_text("plain prose, nothing fancy", encoding="utf-8")
    assert find_violations([target]) == []
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_prose_lint.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'prose_lint'`

- [ ] **Step 3: เขียน ci/prose_lint.py**

```python
"""Fail the build when learner facing prose contains banned characters.

The project style rules ban the em dash and emoji in every markdown file.
People forget rules like this, so a machine enforces it.
"""
import re
import sys
from pathlib import Path

EM_DASH = "\u2014"
EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002600-\U000027BF"
    "\U0000FE0F"
    "]"
)


def find_violations(paths):
    """Return a list of (path, line_number, reason) for every banned character."""
    violations = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if EM_DASH in line:
                violations.append((path, number, "em dash"))
            if EMOJI.search(line):
                violations.append((path, number, "emoji"))
    return violations


def main():
    root = Path(__file__).resolve().parents[1]
    files = [p for p in root.rglob("*.md") if ".venv" not in p.parts]
    violations = find_violations(files)
    for path, number, reason in violations:
        print(f"{path.relative_to(root)}:{number} contains {reason}")
    if violations:
        print(f"\n{len(violations)} prose violations found")
        return 1
    print(f"prose lint clean across {len(files)} markdown files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `pytest tests/test_prose_lint.py -v`
Expected: PASS ทั้งสามเคส

- [ ] **Step 5: รันกับ repo จริง**

Run: `python ci/prose_lint.py`
Expected: exit code 0 และพิมพ์ว่าสะอาด ถ้าแดงแปลว่าไฟล์ md ที่มีอยู่ยังมี em-dash ให้แก้ก่อนไปต่อ

- [ ] **Step 6: Commit**

```bash
git add ci/prose_lint.py tests/test_prose_lint.py
git commit -m "feat: add prose lint that bans em dash and emoji in markdown"
```

---

## Task 3: Mock server, OpenAI dialect แบบไม่ stream

**Files:**
- Create: `src/agentpath/testing/__init__.py`
- Create: `src/agentpath/testing/mock_server.py`
- Create: `tests/test_mock_server.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_mock_server.py
import httpx
import pytest

from agentpath.testing.mock_server import serve


@pytest.fixture
def mock():
    base_url, shutdown = serve()
    yield base_url
    shutdown()


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
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_mock_server.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'agentpath.testing'`

- [ ] **Step 3: เขียน mock server ส่วนแรก**

```python
# src/agentpath/testing/__init__.py
from agentpath.testing.mock_server import serve

__all__ = ["serve"]
```

```python
# src/agentpath/testing/mock_server.py
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

    if role in ("tool", "user") and role == "tool":
        return f"The tool returned {last.get('content', '')}.", []

    if role == "user" and isinstance(last.get("content"), list):
        for block in last["content"]:
            if block.get("type") == "tool_result":
                return f"The tool returned {block.get('content', '')}.", []

    text = last.get("content", "")
    if isinstance(text, list):
        text = " ".join(b.get("text", "") for b in text)
    match = DIRECTIVE.search(text or "")
    if match:
        name, raw_arguments = match.group(1), match.group(2)
        return "", [{"id": CALL_ID, "name": name, "arguments": json.loads(raw_arguments)}]
    return GREETING, []


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

    def do_POST(self):
        payload = self._read_json()
        text, tool_calls = decide(payload.get("messages", []))
        if self.path.rstrip("/").endswith("/chat/completions"):
            self._send_json(openai_body(text, tool_calls))
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
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `pytest tests/test_mock_server.py -v`
Expected: PASS ทั้งสองเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/testing tests/test_mock_server.py
git commit -m "feat: add mock LLM server with OpenAI non streaming responses"
```

---

## Task 4: Mock server, OpenAI streaming

**Files:**
- Modify: `src/agentpath/testing/mock_server.py`
- Modify: `tests/test_mock_server.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

เพิ่มท้ายไฟล์ `tests/test_mock_server.py`

```python
def read_sse(response):
    """Return the list of json payloads from an SSE response body."""
    events = []
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        data = line[len("data: ") :]
        if data == "[DONE]":
            break
        events.append(__import__("json").loads(data))
    return events


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
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_mock_server.py::test_openai_streams_text_in_several_chunks -v`
Expected: FAIL เพราะ content-type เป็น application/json ไม่ใช่ text/event-stream

- [ ] **Step 3: เพิ่ม streaming ลง mock server**

เพิ่มฟังก์ชันนี้ก่อน class `MockHandler`

```python
def chunk_text(text, size=6):
    """Split text into small pieces so a client must accumulate them."""
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


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
```

เพิ่มเมธอดนี้ใน `MockHandler`

```python
    def _send_sse(self, events):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for event in events:
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
```

แก้ `do_POST` ให้แยกทางตาม `stream`

```python
    def do_POST(self):
        payload = self._read_json()
        text, tool_calls = decide(payload.get("messages", []))
        streaming = bool(payload.get("stream"))
        if self.path.rstrip("/").endswith("/chat/completions"):
            if streaming:
                self._send_sse(openai_stream_events(text, tool_calls))
            else:
                self._send_json(openai_body(text, tool_calls))
            return
        self._send_json({"error": f"unknown path {self.path}"}, status=404)
```

- [ ] **Step 4: รัน test ทั้งไฟล์ให้ผ่าน**

Run: `pytest tests/test_mock_server.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/testing/mock_server.py tests/test_mock_server.py
git commit -m "feat: stream OpenAI style SSE responses from the mock server"
```

---

## Task 5: Mock server, tool call directive

ยืนยันว่า directive ทำงานทั้งแบบ stream และไม่ stream และ argument ถูกหั่นเป็นเศษ JSON จริง ซึ่งเป็นสิ่งที่บทที่ 05 ต้องสอน

**Files:**
- Modify: `tests/test_mock_server.py`

- [ ] **Step 1: เขียน test**

เพิ่มท้ายไฟล์

```python
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
    assert __import__("json").loads(call["function"]["arguments"]) == {"a": 2, "b": 3}


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
    assert __import__("json").loads("".join(fragments)) == {"a": 2, "b": 3}
```

- [ ] **Step 2: รัน test**

Run: `pytest tests/test_mock_server.py -v`
Expected: PASS ทุกเคส เพราะ Task 3 และ 4 ทำ logic ไว้ครบแล้ว ถ้าแดงแปลว่า `decide` หรือ `openai_stream_events` ยังผิด ให้แก้ที่นั่น

- [ ] **Step 3: Commit**

```bash
git add tests/test_mock_server.py
git commit -m "test: cover tool call directive in both response modes"
```

---

## Task 6: Mock server, Anthropic dialect

ถ้าไม่มีส่วนนี้ check ของบทที่ 06 จะพิสูจน์ไม่ได้ว่า abstraction ทำงานจริง เพราะจะทดสอบได้แค่ provider เดียว

**Files:**
- Modify: `src/agentpath/testing/mock_server.py`
- Modify: `tests/test_mock_server.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

เพิ่มท้ายไฟล์ test

```python
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
    text = "".join(
        p["delta"]["text"] for p in payloads if p["type"] == "content_block_delta"
    )
    assert text == "Hello from the mock server."
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_mock_server.py -k anthropic -v`
Expected: FAIL ทั้งสามเคส เพราะ path `/v1/messages` ยังตอบ 404

- [ ] **Step 3: เพิ่ม Anthropic dialect**

เพิ่มสองฟังก์ชันนี้ต่อจาก `openai_stream_events`

```python
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
```

แก้ `do_POST` ให้รู้จัก path ที่สอง

```python
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
```

- [ ] **Step 4: รัน test ทั้งไฟล์**

Run: `pytest tests/test_mock_server.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/testing/mock_server.py tests/test_mock_server.py
git commit -m "feat: answer the Anthropic messages dialect from the mock server"
```

---

## Task 7: Spike, ยืนยันพฤติกรรมของ endpoint จริง

เสปคระบุว่าเรื่องนี้ต้องทำเป็นงานแรกๆ เพราะถ้า Ollama stream พร้อม tools ไม่ได้ ต้องมี fallback และบทที่ 05 ต้องเขียนต่างออกไป งานนี้ไม่มี test เพราะเป็นการสำรวจ ผลลัพธ์คือเอกสาร

**Files:**
- Create: `docs/provider-notes.md`

- [ ] **Step 1: เตรียม environment**

```bash
ollama pull qwen3
ollama serve
```

- [ ] **Step 2: ทดสอบ streaming พร้อม tools ด้วยมือ**

```bash
curl -s http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen3","stream":true,"messages":[{"role":"user","content":"What is 2 plus 3?"}],"tools":[{"type":"function","function":{"name":"add","description":"Add two numbers","parameters":{"type":"object","properties":{"a":{"type":"number"},"b":{"type":"number"}},"required":["a","b"]}}}]}'
```

Expected: ได้ SSE ที่มี `tool_calls` อยู่ใน delta บันทึกว่า argument มาเป็นก้อนเดียวหรือหลายก้อน

- [ ] **Step 3: ทดสอบซ้ำแบบไม่ stream**

รันคำสั่งเดิมโดยเปลี่ยน `"stream":true` เป็น `"stream":false` บันทึกความต่างของโครงสร้าง

- [ ] **Step 4: บันทึกผลลง docs/provider-notes.md**

เขียนหัวข้อเหล่านี้ ห้ามใช้ em-dash และ emoji

```markdown
# Provider notes

บันทึกพฤติกรรมจริงของแต่ละ endpoint ที่โครงการรองรับ ใช้ตัดสินใจเรื่อง fallback

## Ollama

- เวอร์ชันที่ทดสอบ
- streaming พร้อม tools ทำงานหรือไม่
- argument ของ tool call มาเป็นก้อนเดียวหรือหลายก้อน
- model ที่ยืนยันแล้วว่าเรียก tool ได้

## Groq และ OpenRouter

- ข้อสังเกตที่ต่างจาก OpenAI

## บทสรุปสำหรับบทที่ 05

- ถ้า streaming พร้อม tools ใช้ไม่ได้กับ endpoint ใด ให้ระบุว่า fallback คืออะไร
```

- [ ] **Step 5: Commit**

```bash
git add docs/provider-notes.md
git commit -m "docs: record real provider streaming and tool behaviour"
```

---

## Task 8: types.py

**Files:**
- Create: `src/agentpath/types.py`
- Create: `tests/test_types.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_types.py
from agentpath.types import Message, TextDelta, ToolCall, ToolResult, TurnDone


def test_message_defaults_are_independent():
    first = Message(role="user", content="hi")
    second = Message(role="user", content="hi")
    first.tool_calls.append(ToolCall(id="1", name="add", arguments={}))
    assert second.tool_calls == []


def test_events_carry_their_payload():
    assert TextDelta(text="ab").text == "ab"
    assert TurnDone(message=Message(role="assistant")).message.role == "assistant"
    assert ToolResult(tool_call_id="1", name="add", content="5").content == "5"
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_types.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'agentpath.types'`

- [ ] **Step 3: เขียน types.py**

```python
"""The small set of data shapes that every other module speaks.

There is no behaviour here on purpose. Keeping the shapes free of logic is
what lets the provider, the tool registry and the agent loop stay unaware of
each other.
"""
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A request from the model to run one tool."""

    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    """One entry in the conversation.

    role is one of system, user, assistant, tool. tool_call_id is filled in
    only when role is tool, so the provider can match a result back to the
    call that produced it.
    """

    role: str
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""


@dataclass
class TextDelta:
    """A piece of assistant text as it arrives."""

    text: str


@dataclass
class ToolCallRequest:
    """The agent is about to run this tool call."""

    tool_call: ToolCall


@dataclass
class ToolResult:
    """The outcome of running one tool call."""

    tool_call_id: str
    name: str
    content: str


@dataclass
class TurnDone:
    """The assistant finished a message."""

    message: Message
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `pytest tests/test_types.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/types.py tests/test_types.py
git commit -m "feat: add core message and event types"
```

---

## Task 9: Provider interface และ OpenAI compatible provider

**Files:**
- Create: `src/agentpath/providers/__init__.py`
- Create: `src/agentpath/providers/base.py`
- Create: `src/agentpath/providers/openai_compat.py`
- Create: `tests/conftest.py`
- Create: `tests/test_openai_compat.py`

- [ ] **Step 1: เขียน fixture ที่ทุก test ใช้ร่วมกัน**

```python
# tests/conftest.py
import pytest

from agentpath.testing.mock_server import serve


@pytest.fixture
def mock_url():
    base_url, shutdown = serve()
    yield base_url
    shutdown()
```

- [ ] **Step 2: เขียน test ที่ต้องแดง**

```python
# tests/test_openai_compat.py
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.types import Message, TextDelta, TurnDone


def build(mock_url):
    return OpenAICompatProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")


def test_streams_text_then_finishes(mock_url):
    events = list(build(mock_url).stream([Message(role="user", content="hi")]))
    deltas = [e for e in events if isinstance(e, TextDelta)]
    assert len(deltas) > 1
    assert isinstance(events[-1], TurnDone)
    assert events[-1].message.content == "Hello from the mock server."
    assert events[-1].message.tool_calls == []


def test_accumulates_streamed_tool_arguments(mock_url):
    tools = [
        {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        }
    ]
    prompt = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'
    events = list(build(mock_url).stream([Message(role="user", content=prompt)], tools))
    call = events[-1].message.tool_calls[0]
    assert call.name == "add"
    assert call.arguments == {"a": 2, "b": 3}


def test_sends_tool_results_back_in_wire_format(mock_url):
    history = [
        Message(role="user", content="hi"),
        Message(role="tool", content="5", tool_call_id="call_mock_1"),
    ]
    events = list(build(mock_url).stream(history))
    assert "5" in events[-1].message.content
```

- [ ] **Step 3: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_openai_compat.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'agentpath.providers'`

- [ ] **Step 4: เขียน providers/base.py**

```python
# src/agentpath/providers/__init__.py
from agentpath.providers.base import Provider

__all__ = ["Provider"]
```

```python
# src/agentpath/providers/base.py
"""The one interface every provider implements.

A provider turns a conversation into a stream of events. It yields TextDelta
while the assistant is speaking and exactly one TurnDone at the end that
carries the finished message, including any tool calls the model asked for.

A provider never runs a tool. Running tools belongs to the agent loop, and
keeping that line clean is what lets both providers share one loop.
"""
from collections.abc import Iterator

from agentpath.types import Message


class Provider:
    def stream(self, messages: list[Message], tools: list[dict] | None = None) -> Iterator:
        raise NotImplementedError
```

- [ ] **Step 5: เขียน providers/openai_compat.py**

```python
"""Talk to any server that speaks the OpenAI chat completions format.

That covers OpenAI itself, Ollama, Groq and OpenRouter. They differ only in
base url and model name, which is why this one class serves all of them.
"""
import json
import os
from collections.abc import Iterator

import httpx

from agentpath.providers.base import Provider
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
    def __init__(self, base_url=None, api_key=None, model=None, client=None, timeout=120):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]
        self.client = client or httpx.Client(timeout=timeout)

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
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": tool} for tool in tools]

        text_parts: list[str] = []
        partial: dict[int, dict] = {}

        with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                delta = json.loads(data)["choices"][0].get("delta", {})
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

        calls = [
            ToolCall(
                id=slot["id"],
                name=slot["name"],
                arguments=json.loads(slot["arguments"] or "{}"),
            )
            for _, slot in sorted(partial.items())
        ]
        yield TurnDone(
            message=Message(role="assistant", content="".join(text_parts), tool_calls=calls)
        )
```

- [ ] **Step 6: รัน test ให้ผ่าน**

Run: `pytest tests/test_openai_compat.py -v`
Expected: PASS ทั้งสามเคส

- [ ] **Step 7: Commit**

```bash
git add src/agentpath/providers tests/conftest.py tests/test_openai_compat.py
git commit -m "feat: add streaming OpenAI compatible provider"
```

---

## Task 10: Anthropic provider

**Files:**
- Create: `src/agentpath/providers/anthropic.py`
- Create: `tests/test_anthropic.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_anthropic.py
from agentpath.providers.anthropic import AnthropicProvider
from agentpath.types import Message, TextDelta, TurnDone


def build(mock_url):
    return AnthropicProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")


def test_streams_text_then_finishes(mock_url):
    events = list(build(mock_url).stream([Message(role="user", content="hi")]))
    assert [e for e in events if isinstance(e, TextDelta)]
    assert isinstance(events[-1], TurnDone)
    assert events[-1].message.content == "Hello from the mock server."


def test_accumulates_streamed_tool_input(mock_url):
    tools = [
        {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        }
    ]
    prompt = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'
    events = list(build(mock_url).stream([Message(role="user", content=prompt)], tools))
    call = events[-1].message.tool_calls[0]
    assert call.name == "add"
    assert call.arguments == {"a": 2, "b": 3}


def test_tool_results_become_user_content_blocks(mock_url):
    from agentpath.providers.anthropic import to_wire

    wire = to_wire(
        [
            Message(role="user", content="hi"),
            Message(role="tool", content="5", tool_call_id="call_mock_1"),
        ]
    )
    assert wire[-1]["role"] == "user"
    assert wire[-1]["content"][0]["type"] == "tool_result"
    assert wire[-1]["content"][0]["tool_use_id"] == "call_mock_1"
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_anthropic.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'agentpath.providers.anthropic'`

- [ ] **Step 3: เขียน providers/anthropic.py**

```python
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

from agentpath.providers.base import Provider
from agentpath.types import Message, TextDelta, ToolCall, TurnDone

API_VERSION = "2023-06-01"


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
    def __init__(self, base_url=None, api_key=None, model=None, client=None, timeout=120):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]
        self.client = client or httpx.Client(timeout=timeout)

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

        with self.client.stream(
            "POST",
            f"{self.base_url}/messages",
            json=payload,
            headers=self._headers(),
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                event = json.loads(data)
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

        calls = [
            ToolCall(id=slot["id"], name=slot["name"], arguments=json.loads(slot["json"] or "{}"))
            for _, slot in sorted(blocks.items())
        ]
        yield TurnDone(
            message=Message(role="assistant", content="".join(text_parts), tool_calls=calls)
        )
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `pytest tests/test_anthropic.py -v`
Expected: PASS ทั้งสามเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/providers/anthropic.py tests/test_anthropic.py
git commit -m "feat: add Anthropic messages provider behind the same interface"
```

---

## Task 11: Tool registry

**Files:**
- Create: `src/agentpath/tools/__init__.py`
- Create: `src/agentpath/tools/base.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_tools.py
import pytest

from agentpath.tools.base import Tool, ToolRegistry
from agentpath.types import ToolCall

ADD = Tool(
    name="add",
    description="Add two numbers",
    parameters={
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
    fn=lambda a, b: a + b,
)


def test_schemas_expose_name_description_parameters():
    schemas = ToolRegistry([ADD]).schemas()
    assert schemas == [
        {"name": "add", "description": "Add two numbers", "parameters": ADD.parameters}
    ]


def test_run_returns_string_content():
    result = ToolRegistry([ADD]).run(ToolCall(id="1", name="add", arguments={"a": 2, "b": 3}))
    assert result.content == "5"
    assert result.tool_call_id == "1"


def test_unknown_tool_becomes_an_error_result_not_a_crash():
    result = ToolRegistry([ADD]).run(ToolCall(id="1", name="nope", arguments={}))
    assert "unknown tool" in result.content


def test_bad_arguments_become_an_error_result_not_a_crash():
    result = ToolRegistry([ADD]).run(ToolCall(id="1", name="add", arguments={"a": 2}))
    assert result.content.startswith("Error")


def test_empty_registry_reports_no_schemas():
    assert ToolRegistry().schemas() == []


@pytest.mark.parametrize("arguments", [{"a": 1, "b": 2}, {"b": 2, "a": 1}])
def test_argument_order_does_not_matter(arguments):
    assert ToolRegistry([ADD]).run(ToolCall(id="1", name="add", arguments=arguments)).content == "3"
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'agentpath.tools'`

- [ ] **Step 3: เขียน tools/base.py**

```python
# src/agentpath/tools/__init__.py
from agentpath.tools.base import Tool, ToolRegistry

__all__ = ["Tool", "ToolRegistry"]
```

```python
# src/agentpath/tools/base.py
"""Tools are plain functions plus a hand written JSON schema.

The schema is written by hand rather than generated from type hints. Reading
the schema is how a learner understands what the model actually receives, and
hiding it behind a decorator would remove the most instructive part.
"""
from collections.abc import Callable
from dataclasses import dataclass

from agentpath.types import ToolCall, ToolResult


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., object]


class ToolRegistry:
    def __init__(self, tools=()):
        self._tools = {tool.name: tool for tool in tools}

    def schemas(self) -> list[dict]:
        return [
            {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
            for tool in self._tools.values()
        ]

    def run(self, call: ToolCall) -> ToolResult:
        """Run one tool call and always come back with a result.

        Arguments come from the model, so they are untrusted input. A bad call
        must turn into text the model can read and correct, never an exception
        that kills the agent loop.
        """
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: unknown tool {call.name}",
            )
        try:
            return ToolResult(
                tool_call_id=call.id, name=call.name, content=str(tool.fn(**call.arguments))
            )
        except Exception as error:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: {type(error).__name__}: {error}",
            )
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `pytest tests/test_tools.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/tools tests/test_tools.py
git commit -m "feat: add tool registry that turns failures into readable results"
```

---

## Task 12: Agent loop

**Files:**
- Create: `src/agentpath/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_agent.py
import pytest

from agentpath.agent import Agent
from agentpath.providers.openai_compat import OpenAICompatProvider
from agentpath.tools.base import Tool, ToolRegistry
from agentpath.types import TextDelta, ToolCallRequest, ToolResult, TurnDone

ADD = Tool(
    name="add",
    description="Add two numbers",
    parameters={
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
    fn=lambda a, b: a + b,
)


def build(mock_url, tools=()):
    provider = OpenAICompatProvider(base_url=f"{mock_url}/v1", api_key="unused", model="mock")
    return Agent(provider=provider, tools=ToolRegistry(tools))


def test_plain_answer_ends_after_one_turn(mock_url):
    events = list(build(mock_url).run("hi"))
    assert isinstance(events[-1], TurnDone)
    assert [e for e in events if isinstance(e, TextDelta)]
    assert not [e for e in events if isinstance(e, ToolCallRequest)]


def test_tool_call_is_executed_and_fed_back(mock_url):
    agent = build(mock_url, [ADD])
    events = list(agent.run('What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'))
    requests = [e for e in events if isinstance(e, ToolCallRequest)]
    results = [e for e in events if isinstance(e, ToolResult)]
    assert requests[0].tool_call.name == "add"
    assert results[0].content == "5"
    assert "5" in events[-1].message.content


def test_conversation_history_grows_with_the_tool_exchange(mock_url):
    agent = build(mock_url, [ADD])
    list(agent.run('[[tool:add:{"a": 2, "b": 3}]]'))
    roles = [m.role for m in agent.messages]
    assert roles == ["user", "assistant", "tool", "assistant"]


def test_runaway_loop_stops_at_max_turns(mock_url):
    agent = build(mock_url, [ADD])
    agent.max_turns = 2
    with pytest.raises(RuntimeError, match="max turns"):
        list(agent.run('[[tool:add:{"a": 2, "b": 3}]] keep going'))
```

หมายเหตุสำหรับเคสสุดท้าย mock จะตอบ tool call ทุกครั้งที่ข้อความล่าสุดยังมี directive แต่หลังรัน tool ข้อความล่าสุดจะกลายเป็น tool result ทำให้ mock ตอบเป็นข้อความธรรมดาและ loop จบ ดังนั้นเคสนี้ต้องบังคับด้วย provider ปลอมแทน ให้เขียนแบบนี้

```python
def test_runaway_loop_stops_at_max_turns():
    from agentpath.types import Message, ToolCall

    class AlwaysCallsATool:
        def stream(self, messages, tools=None):
            yield TurnDone(
                message=Message(
                    role="assistant",
                    tool_calls=[ToolCall(id="1", name="add", arguments={"a": 1, "b": 1})],
                )
            )

    agent = Agent(provider=AlwaysCallsATool(), tools=ToolRegistry([ADD]), max_turns=3)
    with pytest.raises(RuntimeError, match="max turns"):
        list(agent.run("go"))
```

ให้ใช้เวอร์ชันหลังนี้แทนเวอร์ชันแรกของเคสนั้น

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'agentpath.agent'`

- [ ] **Step 3: เขียน agent.py**

```python
"""The agent loop.

The loop only yields events. It never prints and never asks the user
anything. That is what lets the same loop serve a terminal chat, a subagent
and an eval run without changing a line inside it.
"""
from collections.abc import Iterator

from agentpath.tools.base import ToolRegistry
from agentpath.types import Message, ToolCallRequest, TurnDone


class Agent:
    def __init__(self, provider, tools=None, system=None, max_turns=10):
        self.provider = provider
        self.tools = tools if tools is not None else ToolRegistry()
        self.messages: list[Message] = []
        if system:
            self.messages.append(Message(role="system", content=system))
        self.max_turns = max_turns

    def run(self, user_input: str) -> Iterator:
        self.messages.append(Message(role="user", content=user_input))
        for _ in range(self.max_turns):
            assistant = None
            for event in self.provider.stream(self.messages, self.tools.schemas() or None):
                if isinstance(event, TurnDone):
                    assistant = event.message
                else:
                    yield event
            self.messages.append(assistant)

            if not assistant.tool_calls:
                yield TurnDone(message=assistant)
                return

            for call in assistant.tool_calls:
                yield ToolCallRequest(tool_call=call)
                result = self.tools.run(call)
                yield result
                self.messages.append(
                    Message(role="tool", content=result.content, tool_call_id=call.id)
                )
        raise RuntimeError(f"agent stopped after max turns ({self.max_turns})")
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `pytest tests/test_agent.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: รัน test ทั้งหมด**

Run: `pytest -v`
Expected: PASS ทั้ง suite

- [ ] **Step 6: Commit**

```bash
git add src/agentpath/agent.py tests/test_agent.py
git commit -m "feat: add event driven agent loop"
```

---

## Task 13: CLI

**Files:**
- Create: `src/agentpath/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_cli.py
import pytest

from agentpath.cli import build_provider, main


def test_builds_openai_provider_by_default(monkeypatch):
    monkeypatch.setenv("AGENTPATH_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    monkeypatch.setenv("AGENTPATH_API_KEY", "")
    provider = build_provider("openai")
    assert provider.__class__.__name__ == "OpenAICompatProvider"


def test_builds_anthropic_provider_on_request(monkeypatch):
    monkeypatch.setenv("AGENTPATH_BASE_URL", "https://api.anthropic.com/v1")
    monkeypatch.setenv("AGENTPATH_MODEL", "mock")
    monkeypatch.setenv("AGENTPATH_API_KEY", "x")
    provider = build_provider("anthropic")
    assert provider.__class__.__name__ == "AnthropicProvider"


def test_missing_configuration_gives_a_readable_message(monkeypatch, capsys):
    monkeypatch.delenv("AGENTPATH_BASE_URL", raising=False)
    monkeypatch.delenv("AGENTPATH_MODEL", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        main(["chat"])
    assert exit_info.value.code == 2
    assert "AGENTPATH_BASE_URL" in capsys.readouterr().err
```

- [ ] **Step 2: รัน test ให้เห็นว่าแดง**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL ด้วย `ModuleNotFoundError: No module named 'agentpath.cli'`

- [ ] **Step 3: เขียน cli.py**

```python
"""The agentpath command.

v0.1 has one subcommand, chat. Sessions and one shot runs arrive in part 3
of the course, so they are deliberately absent here.
"""
import argparse
import os
import sys

from agentpath.agent import Agent
from agentpath.types import TextDelta, ToolCallRequest, ToolResult, TurnDone

REQUIRED = ["AGENTPATH_BASE_URL", "AGENTPATH_MODEL"]


def build_provider(kind: str):
    if kind == "anthropic":
        from agentpath.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    from agentpath.providers.openai_compat import OpenAICompatProvider

    return OpenAICompatProvider()


def check_environment():
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        print(
            "Missing configuration. Set these environment variables and try again.\n  "
            + "\n  ".join(missing),
            file=sys.stderr,
        )
        raise SystemExit(2)


def chat(provider_kind: str):
    check_environment()
    agent = Agent(provider=build_provider(provider_kind))
    print("Type a message. Press Ctrl+C to leave.")
    while True:
        try:
            user_input = input("\nyou> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user_input.strip():
            continue
        for event in agent.run(user_input):
            if isinstance(event, TextDelta):
                print(event.text, end="", flush=True)
            elif isinstance(event, ToolCallRequest):
                print(f"\n[calling {event.tool_call.name} with {event.tool_call.arguments}]")
            elif isinstance(event, ToolResult):
                print(f"[{event.name} returned {event.content}]")
            elif isinstance(event, TurnDone):
                print()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentpath")
    subcommands = parser.add_subparsers(dest="command", required=True)
    chat_parser = subcommands.add_parser("chat", help="Talk to an agent in the terminal")
    chat_parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    arguments = parser.parse_args(argv)
    if arguments.command == "chat":
        return chat(arguments.provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `pytest tests/test_cli.py -v`
Expected: PASS ทั้งสามเคส

- [ ] **Step 5: ลองใช้จริงกับ mock**

```bash
python -m agentpath.testing.mock_server --port 8765
```

เปิดอีกหน้าต่างแล้วรัน

```bash
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock AGENTPATH_API_KEY= agentpath chat
```

Expected: พิมพ์ hi แล้วได้ `Hello from the mock server.` ทีละชิ้น

- [ ] **Step 6: Commit**

```bash
git add src/agentpath/cli.py tests/test_cli.py
git commit -m "feat: add agentpath chat command"
```

---

## Task 14: Lesson 00, setup

**Files:**
- Create: `lessons/00-setup/README.md`
- Create: `lessons/00-setup/check.py`

- [ ] **Step 1: เขียน check.py**

```python
"""Prove your machine is ready for the rest of the course.

This script does not test your model. It tests that Python is new enough and
that the endpoint you configured answers when we knock on it.
"""
import os
import sys

MINIMUM_PYTHON = (3, 10)


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


def main():
    if sys.version_info < MINIMUM_PYTHON:
        fail(f"Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer is required")
    print(f"OK Python {sys.version_info.major}.{sys.version_info.minor}")

    try:
        import httpx
    except ImportError:
        fail("httpx is not installed. Run uv pip install httpx")
    print("OK httpx is installed")

    base_url = os.environ.get("AGENTPATH_BASE_URL")
    model = os.environ.get("AGENTPATH_MODEL")
    if not base_url:
        fail("AGENTPATH_BASE_URL is not set")
    if not model:
        fail("AGENTPATH_MODEL is not set")
    print(f"OK AGENTPATH_BASE_URL is {base_url}")
    print(f"OK AGENTPATH_MODEL is {model}")

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say ready."}],
            },
            headers=headers,
            timeout=60,
        )
    except httpx.HTTPError as error:
        fail(f"could not reach {base_url}. {error}")
    if response.status_code != 200:
        fail(f"{base_url} answered {response.status_code}. {response.text[:200]}")
    print("OK the endpoint answered")
    print("\nYou are ready for lesson 01.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: ยืนยันกับ mock**

```bash
python -m agentpath.testing.mock_server --port 8765
```

อีกหน้าต่าง

```bash
cd lessons/00-setup
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

Expected: OK ทุกบรรทัด และจบด้วย `You are ready for lesson 01.`

- [ ] **Step 3: เขียน README.md**

เขียนตามกฎภาษาในเสปค ห้าม em-dash ห้าม colon ห้าม emoji และทุกหัวข้อต้องตอบว่ามันคืออะไร ทำทำไม เพราะอะไรถึงเลือกวิธีนี้ หัวข้อที่ต้องมี

1. What you will have at the end of this lesson
2. What an AI agent actually is, in two paragraphs and no jargon
3. Installing Python with uv, and why uv rather than pip or conda
4. Choosing where your model will run. อธิบายสามทาง Ollama บนเครื่องตัวเอง, free tier cloud อย่าง Groq หรือ OpenRouter, และ paid API พร้อมข้อดีข้อเสียของแต่ละทางแบบตรงไปตรงมา
5. Models that can actually call tools. ระบุ qwen3 และ llama3.1 ขนาด 8b ขึ้นไป และอธิบายว่าทำไม model เล็กกว่านั้นจะทำให้บทที่ 03 ล้มเหลว
6. The three environment variables. อธิบายว่าทำไมโครงการนี้ไม่ยอมให้ hardcode URL หรือกุญแจ พร้อมวิธีตั้งค่าทั้ง PowerShell, cmd, bash และ zsh
7. Running check.py and reading what it tells you
8. Troubleshooting. อย่างน้อยต้องมีเคส connection refused, 401, 404, และ model not found

- [ ] **Step 4: รัน prose lint**

Run: `python ci/prose_lint.py`
Expected: exit 0

- [ ] **Step 5: Commit**

```bash
git add lessons/00-setup
git commit -m "docs: add lesson 00 setup"
```

---

## Task 15: Lesson 01, first LLM call

**Files:**
- Create: `lessons/01-first-llm-call/llm.py`
- Create: `lessons/01-first-llm-call/check.py`
- Create: `lessons/01-first-llm-call/README.md`

- [ ] **Step 1: เขียน llm.py**

```python
"""One function that sends text to a model and returns the text it sends back.

Everything else in this course is built on top of this. There is no library
between you and the API here on purpose. You should be able to see that a
language model is an HTTP endpoint that takes a list of messages and returns
one more message.
"""
import os

import httpx


def ask(prompt):
    """Send one message and return the assistant reply as a string."""
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    return body["choices"][0]["message"]["content"]


if __name__ == "__main__":
    print(ask("Say hello in one short sentence."))
```

- [ ] **Step 2: เขียน check.py**

```python
"""Check that lesson 01 works."""
import sys

from llm import ask


def main():
    reply = ask("Say hello.")
    if not isinstance(reply, str) or not reply.strip():
        print(f"FAIL ask returned {reply!r}")
        sys.exit(1)
    print(f"OK the model replied with {reply.strip()[:60]}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: ยืนยันกับ mock**

```bash
cd lessons/01-first-llm-call
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

Expected: `OK the model replied with Hello from the mock server.`

- [ ] **Step 4: เขียน README.md**

หัวข้อที่ต้องมี

1. The problem. เราไม่มีทางคุยกับ model เลย ต้องเริ่มจากศูนย์
2. What an HTTP request to a language model looks like. โชว์ JSON ของ request และ response แบบเต็ม พร้อมอธิบายทุก field ว่าคืออะไร ทำไมต้องมี
3. Why we use httpx directly instead of an official SDK. เชื่อมกับหลักการไม่มีเวทมนตร์
4. Why the code reads three environment variables instead of holding a url
5. Writing llm.py line by line
6. Running it and reading the reply
7. What raise_for_status does and why the first version of this function would be dangerous without it
8. What you cannot do yet. model ยังจำอะไรไม่ได้เลย ซึ่งเป็นปัญหาของบทถัดไป

- [ ] **Step 5: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add lessons/01-first-llm-call
git commit -m "docs: add lesson 01 first LLM call"
```

---

## Task 16: Lesson 02, conversation loop

**Files:**
- Create: `lessons/02-conversation-loop/llm.py`
- Create: `lessons/02-conversation-loop/chat.py`
- Create: `lessons/02-conversation-loop/check.py`
- Create: `lessons/02-conversation-loop/README.md`

- [ ] **Step 1: เขียน llm.py**

```python
"""The same call as lesson 01, but taking a whole conversation.

A model has no memory. The only reason it appears to remember anything is
that we send the entire conversation again on every single call.
"""
import os

import httpx


def complete(messages):
    """Send a list of messages and return the assistant reply as a string."""
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.post(
        f"{base_url}/chat/completions",
        json={"model": model, "messages": messages},
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
```

- [ ] **Step 2: เขียน chat.py**

```python
"""A terminal chat that keeps the conversation in a plain list."""
from llm import complete


def main():
    messages = []
    print("Type a message. Press Ctrl+C to leave.")
    while True:
        try:
            user_input = input("\nyou> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not user_input.strip():
            continue
        messages.append({"role": "user", "content": user_input})
        reply = complete(messages)
        messages.append({"role": "assistant", "content": reply})
        print(f"\nbot> {reply}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: เขียน check.py**

```python
"""Check that lesson 02 works."""
import sys

from llm import complete


def main():
    messages = [{"role": "user", "content": "Hello."}]
    first = complete(messages)
    if not first.strip():
        print("FAIL the first reply was empty")
        sys.exit(1)

    messages.append({"role": "assistant", "content": first})
    messages.append({"role": "tool", "tool_call_id": "call_mock_1", "content": "42"})
    second = complete(messages)
    if "42" not in second:
        print(f"FAIL history was not sent back. Reply was {second!r}")
        sys.exit(1)
    print("OK the whole conversation travels on every call")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: ยืนยันกับ mock**

```bash
cd lessons/02-conversation-loop
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

Expected: `OK the whole conversation travels on every call`

- [ ] **Step 5: เขียน README.md**

หัวข้อที่ต้องมี

1. The problem left over from lesson 01. model ตอบคำถามต่อเนื่องไม่ได้
2. Why a model has no memory at all, and what that means for cost and speed
3. The message list and its four roles system, user, assistant, tool
4. Writing complete and chat line by line
5. Running the chat and watching the list grow
6. Why this breaks eventually. บทสนทนายาวขึ้นเรื่อยๆ ซึ่งเป็นปัญหาที่ภาค 3 จะแก้
7. What you cannot do yet. model บอกได้แต่คำ ทำอะไรไม่ได้เลย ซึ่งเป็นปัญหาของบทถัดไป

- [ ] **Step 6: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add lessons/02-conversation-loop
git commit -m "docs: add lesson 02 conversation loop"
```

---

## Task 17: Lesson 03, tool calling

**Files:**
- Create: `lessons/03-tool-calling/tools.py`
- Create: `lessons/03-tool-calling/llm.py`
- Create: `lessons/03-tool-calling/check.py`
- Create: `lessons/03-tool-calling/README.md`

- [ ] **Step 1: เขียน tools.py**

```python
"""Toy tools with hand written schemas.

The tools are deliberately boring. A calculator and a dice roll have results
you can predict, so when something goes wrong you know the problem is in the
plumbing and not in the tool.

The schema below is JSON Schema. It is the only thing the model ever sees
about your function, so every word in the description is doing work.
"""
import random

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers together and return the sum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "Roll a dice with the given number of sides.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {"type": "integer", "description": "How many sides the dice has"}
                },
                "required": ["sides"],
            },
        },
    },
]


def add(a, b):
    return a + b


def roll_dice(sides):
    return random.randint(1, sides)


FUNCTIONS = {"add": add, "roll_dice": roll_dice}


def run(name, arguments):
    """Run one tool by name and return its result as a string."""
    function = FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**arguments))
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"
```

- [ ] **Step 2: เขียน llm.py**

```python
"""Send tools along with the conversation and read what the model asks for."""
import json
import os

import httpx


def complete(messages, tools=None):
    """Return (text, tool_calls).

    tool_calls is a list of dicts with the keys id, name and arguments.
    When the model answers in words the list is empty.
    """
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools

    response = httpx.post(
        f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120
    )
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]

    calls = []
    for raw in message.get("tool_calls") or []:
        calls.append(
            {
                "id": raw["id"],
                "name": raw["function"]["name"],
                "arguments": json.loads(raw["function"]["arguments"] or "{}"),
            }
        )
    return message.get("content") or "", calls
```

- [ ] **Step 3: เขียน check.py**

```python
"""Check that lesson 03 works."""
import sys

import tools
from llm import complete

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    text, calls = complete([{"role": "user", "content": PROMPT}], tools.SCHEMAS)
    if not calls:
        print(f"FAIL the model answered in words instead of calling a tool. Text was {text!r}")
        print("If you are using a local model, see the troubleshooting section of the README.")
        sys.exit(1)
    call = calls[0]
    if call["name"] != "add" or call["arguments"] != {"a": 2, "b": 3}:
        print(f"FAIL unexpected call {call}")
        sys.exit(1)
    result = tools.run(call["name"], call["arguments"])
    if result != "5":
        print(f"FAIL running the tool gave {result!r}")
        sys.exit(1)
    print("OK the model asked for add(2, 3) and the tool returned 5")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: ยืนยันกับ mock**

```bash
cd lessons/03-tool-calling
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

Expected: `OK the model asked for add(2, 3) and the tool returned 5`

- [ ] **Step 5: เขียน README.md**

หัวข้อที่ต้องมี

1. The problem left over from lesson 02. model พูดได้อย่างเดียว
2. What tool calling really is. เน้นว่า model ไม่ได้รันอะไรเลย มันแค่ขอ และเราเป็นคนรัน จุดนี้คือความเข้าใจผิดที่พบบ่อยที่สุด
3. Reading a JSON Schema field by field
4. Why the description matters more than the code
5. Writing tools.py and llm.py line by line
6. Running check.py and reading the tool call
7. The directive in the prompt. อธิบายว่า `[[tool:add:{"a": 2, "b": 3}]]` มีไว้ให้ mock server อ่านตอน CI ส่วน model จริงจะอ่านประโยคภาษาคนที่อยู่ข้างหน้า ทั้งสองทางจึงลงเอยที่ tool call เดียวกัน
8. Troubleshooting when the model refuses to call a tool. อธิบายว่าเป็นเรื่องปกติของ model เล็ก ไม่ใช่ความผิดของผู้เรียน พร้อมทางแก้สามทาง เปลี่ยน model, ทำ description ให้ชัดขึ้น, หรือย้ายไป free tier cloud
9. What you cannot do yet. เรายังต้องเรียก tool ด้วยมือ และผลลัพธ์ยังไม่ได้กลับเข้าไปหา model

- [ ] **Step 6: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add lessons/03-tool-calling
git commit -m "docs: add lesson 03 tool calling"
```

---

## Task 18: Lesson 04, agent loop

**Files:**
- Create: `lessons/04-agent-loop/tools.py`
- Create: `lessons/04-agent-loop/llm.py`
- Create: `lessons/04-agent-loop/agent.py`
- Create: `lessons/04-agent-loop/check.py`
- Create: `lessons/04-agent-loop/README.md`

- [ ] **Step 1: คัดลอกไฟล์จากบทที่ 03**

```bash
cp lessons/03-tool-calling/tools.py lessons/04-agent-loop/tools.py
cp lessons/03-tool-calling/llm.py lessons/04-agent-loop/llm.py
```

การคัดลอกคือเจตนาของรูปแบบ snapshot ต่อบท ผู้เรียนเปิดโฟลเดอร์เดียวแล้วรันได้เลย

- [ ] **Step 2: เขียน agent.py**

```python
"""The agent loop.

This is the whole idea of an agent in one function. Ask the model. If it
asked for tools, run them, put the results back into the conversation, and
ask again. Stop when it answers in words instead of asking for a tool.

max_turns exists because a model can get stuck asking for the same tool
forever. Without a limit that is an infinite loop that spends real money.
"""
import tools
from llm import complete


def run(user_input, max_turns=10):
    """Run the agent until it produces a final answer. Returns the answer."""
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete(messages, tools.SCHEMAS)

        if not calls:
            return text

        messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": __import__("json").dumps(call["arguments"]),
                        },
                    }
                    for call in calls
                ],
            }
        )

        for call in calls:
            print(f"[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": result}
            )

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")


if __name__ == "__main__":
    print(run("What is 2 plus 3?"))
```

หมายเหตุ ให้เปลี่ยน `__import__("json").dumps` เป็น `json.dumps` โดยเพิ่ม `import json` ไว้บนสุดของไฟล์ การเขียนแบบ `__import__` ในแผนนี้มีไว้กันสับสนเท่านั้น โค้ดจริงต้อง import ตามปกติ

- [ ] **Step 3: เขียน check.py**

```python
"""Check that lesson 04 works."""
import sys

from agent import run

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    answer = run(PROMPT)
    if "5" not in answer:
        print(f"FAIL the final answer did not mention the tool result. Got {answer!r}")
        sys.exit(1)
    print(f"OK the agent ran the tool and answered with {answer.strip()[:60]}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: ยืนยันกับ mock**

```bash
cd lessons/04-agent-loop
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

Expected: บรรทัด calling และ returned แล้วตามด้วย OK

- [ ] **Step 5: เขียน README.md**

หัวข้อที่ต้องมี

1. The problem left over from lesson 03. เราเรียก tool เองและผลไม่ได้กลับเข้าบทสนทนา
2. What makes this a loop rather than a function call
3. The four steps of the loop, written out in plain language before any code
4. Why the assistant message with tool_calls must go back into the history. อธิบายว่าถ้าข้ามขั้นนี้ API จะปฏิเสธ tool result ที่ไม่มีการเรียกนำหน้า
5. Why max_turns is not optional. อธิบายเรื่อง loop ไม่รู้จบและค่าใช้จ่ายจริง
6. Writing agent.py line by line
7. Running it and reading the trace
8. What you cannot do yet. ต้องรอจนจบถึงจะเห็นอะไร ซึ่งเป็นปัญหาของบทถัดไป

- [ ] **Step 6: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add lessons/04-agent-loop
git commit -m "docs: add lesson 04 agent loop"
```

---

## Task 19: Lesson 05, streaming

บทที่ยากที่สุดของภาค 1 ต้องอ่าน `docs/provider-notes.md` จาก Task 7 ก่อนเขียน ถ้าผลการสำรวจบอกว่า endpoint ที่แนะนำ stream พร้อม tools ไม่ได้ ให้เพิ่มหัวข้อ fallback ใน README และให้ `complete_stream` รับพารามิเตอร์ปิด streaming เมื่อมี tools

**Files:**
- Create: `lessons/05-streaming/tools.py`
- Create: `lessons/05-streaming/llm.py`
- Create: `lessons/05-streaming/agent.py`
- Create: `lessons/05-streaming/check.py`
- Create: `lessons/05-streaming/README.md`

- [ ] **Step 1: คัดลอก tools.py**

```bash
cp lessons/04-agent-loop/tools.py lessons/05-streaming/tools.py
```

- [ ] **Step 2: เขียน llm.py แบบ streaming**

```python
"""Read the answer as it is produced instead of waiting for all of it.

Streaming changes the shape of the code, not just the feel of it. Text now
arrives in pieces, and so do the arguments of a tool call. Those arguments
arrive as fragments of JSON that are not valid JSON until the last fragment
lands, which is why we collect them in a buffer and only parse at the end.
"""
import json
import os

import httpx


def complete_stream(messages, tools=None, on_text=None):
    """Stream one reply. Returns (text, tool_calls).

    on_text is called with every piece of text as it arrives.
    """
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools

    text_parts = []
    partial = {}

    with httpx.Client(timeout=120) as client:
        with client.stream(
            "POST", f"{base_url}/chat/completions", json=payload, headers=headers
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                delta = json.loads(data)["choices"][0].get("delta", {})

                if delta.get("content"):
                    text_parts.append(delta["content"])
                    if on_text:
                        on_text(delta["content"])

                for chunk in delta.get("tool_calls", []):
                    index = chunk.get("index", 0)
                    slot = partial.setdefault(index, {"id": "", "name": "", "arguments": ""})
                    if chunk.get("id"):
                        slot["id"] = chunk["id"]
                    function = chunk.get("function", {})
                    if function.get("name"):
                        slot["name"] = function["name"]
                    if function.get("arguments"):
                        slot["arguments"] += function["arguments"]

    calls = [
        {
            "id": slot["id"],
            "name": slot["name"],
            "arguments": json.loads(slot["arguments"] or "{}"),
        }
        for _, slot in sorted(partial.items())
    ]
    return "".join(text_parts), calls
```

- [ ] **Step 3: เขียน agent.py ที่ใช้ streaming**

```python
"""The same loop as lesson 04, now printing text the moment it arrives."""
import json

import tools
from llm import complete_stream


def run(user_input, max_turns=10):
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete_stream(
            messages, tools.SCHEMAS, on_text=lambda piece: print(piece, end="", flush=True)
        )

        if not calls:
            print()
            return text

        messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"]),
                        },
                    }
                    for call in calls
                ],
            }
        )

        for call in calls:
            print(f"\n[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")


if __name__ == "__main__":
    run("What is 2 plus 3?")
```

- [ ] **Step 4: เขียน check.py**

```python
"""Check that lesson 05 works."""
import sys

import tools
from agent import run
from llm import complete_stream

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    pieces = []
    text, calls = complete_stream(
        [{"role": "user", "content": "Say hello."}], None, on_text=pieces.append
    )
    if len(pieces) < 2:
        print(f"FAIL the reply did not arrive in pieces. Got {len(pieces)} piece(s)")
        sys.exit(1)
    if "".join(pieces) != text:
        print("FAIL the streamed pieces do not add up to the final text")
        sys.exit(1)
    print(f"OK text arrived in {len(pieces)} pieces")

    _, calls = complete_stream([{"role": "user", "content": PROMPT}], tools.SCHEMAS)
    if not calls or calls[0]["arguments"] != {"a": 2, "b": 3}:
        print(f"FAIL streamed tool arguments were not reassembled. Got {calls}")
        sys.exit(1)
    print("OK streamed tool arguments were reassembled into valid JSON")

    answer = run(PROMPT)
    if "5" not in answer:
        print(f"FAIL the agent answer did not mention the tool result. Got {answer!r}")
        sys.exit(1)
    print("OK the streaming agent completed the tool round trip")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: ยืนยันกับ mock**

```bash
cd lessons/05-streaming
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

Expected: OK สามบรรทัด

- [ ] **Step 6: เขียน README.md**

หัวข้อที่ต้องมี

1. The problem left over from lesson 04. ต้องรอเงียบๆ จนกว่าคำตอบจะเสร็จ
2. What server sent events are, and how to read one by eye
3. Part one, streaming text. โค้ดส่วนแรก รันแล้วเห็นตัวอักษรไหล
4. Part two, streaming tool calls. อธิบายว่าทำไม arguments ถึงมาเป็นเศษ JSON และทำไมต้องสะสมก่อน parse ให้โชว์ตัวอย่างเศษจริงที่ mock ส่งมา
5. Why the buffer is keyed by index. อธิบายกรณี model ขอหลาย tool พร้อมกัน
6. Why we rebuilt the loop now instead of later. เชื่อมกับเหตุผลว่าถ้าปล่อยไว้จะต้องรื้อของที่ใหญ่กว่านี้
7. Troubleshooting. ถ้า endpoint ของคุณ stream พร้อม tools ไม่ได้ ให้ทำอะไร อ้างอิงผลจาก docs/provider-notes.md
8. What you cannot do yet. โค้ดนี้ผูกกับรูปแบบของ OpenAI อย่างเดียว ซึ่งเป็นปัญหาของบทถัดไป

- [ ] **Step 7: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add lessons/05-streaming
git commit -m "docs: add lesson 05 streaming"
```

---

## Task 20: Lesson 06, provider abstraction

**Files:**
- Create: `lessons/06-provider-abstraction/tools.py`
- Create: `lessons/06-provider-abstraction/providers.py`
- Create: `lessons/06-provider-abstraction/agent.py`
- Create: `lessons/06-provider-abstraction/check.py`
- Create: `lessons/06-provider-abstraction/README.md`

- [ ] **Step 1: คัดลอก tools.py**

```bash
cp lessons/05-streaming/tools.py lessons/06-provider-abstraction/tools.py
```

- [ ] **Step 2: เขียน providers.py**

ไฟล์นี้คือฉบับย่อของ `src/agentpath/providers/` ที่รวมไว้ในไฟล์เดียวเพื่อให้ผู้เรียนอ่านจบในครั้งเดียว โค้ดต้องเป็นเวอร์ชันเดียวกับ Task 9 และ Task 10 ในเชิงพฤติกรรม แต่ใช้ dict ธรรมดาแทน dataclass เพื่อไม่ให้ต้องแนะนำ types ใหม่ในบทนี้

```python
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


class OpenAICompatProvider:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]

    def stream(self, messages, tools=None, on_text=None):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        text_parts = []
        partial = {}
        with httpx.Client(timeout=120) as client:
            with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        break
                    delta = json.loads(data)["choices"][0].get("delta", {})
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

        calls = [
            {
                "id": s["id"],
                "name": s["name"],
                "arguments": json.loads(s["arguments"] or "{}"),
            }
            for _, s in sorted(partial.items())
        ]
        return "".join(text_parts), calls


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
            with client.stream(
                "POST", f"{self.base_url}/messages", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
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

        calls = [
            {"id": s["id"], "name": s["name"], "arguments": json.loads(s["json"] or "{}")}
            for _, s in sorted(blocks.items())
        ]
        return "".join(text_parts), calls
```

- [ ] **Step 3: เขียน agent.py ที่รับ provider เข้ามา**

```python
"""The same loop again, now taking whichever provider it is handed."""
import json

import tools


def run(provider, user_input, max_turns=10):
    messages = [{"role": "user", "content": user_input}]
    schemas = [t["function"] for t in tools.SCHEMAS]

    for _ in range(max_turns):
        text, calls = provider.stream(
            messages, schemas, on_text=lambda piece: print(piece, end="", flush=True)
        )

        if not calls:
            print()
            return text

        messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"]),
                        },
                    }
                    for call in calls
                ],
            }
        )

        for call in calls:
            print(f"\n[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
```

- [ ] **Step 4: เขียน check.py ที่พิสูจน์ว่า loop เดียวใช้ได้สอง provider**

```python
"""Check that lesson 06 works.

The point of this lesson is that one agent loop serves two different APIs.
So this check runs the same prompt through both providers and expects the
same outcome.
"""
import os
import sys

from agent import run
from providers import AnthropicProvider, OpenAICompatProvider

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    base_url = os.environ["AGENTPATH_BASE_URL"]
    model = os.environ["AGENTPATH_MODEL"]
    api_key = os.environ.get("AGENTPATH_API_KEY", "")

    for name, provider in [
        ("openai", OpenAICompatProvider(base_url, api_key, model)),
        ("anthropic", AnthropicProvider(base_url, api_key, model)),
    ]:
        answer = run(provider, PROMPT)
        if "5" not in answer:
            print(f"FAIL the {name} provider did not complete the tool round trip. Got {answer!r}")
            sys.exit(1)
        print(f"OK the same loop worked with the {name} provider")


if __name__ == "__main__":
    main()
```

หมายเหตุ check นี้รันผ่านเมื่อชี้ไปที่ mock server เพราะ mock พูดได้ทั้งสอง dialect ถ้าผู้เรียนชี้ไปที่ endpoint จริงตัวใดตัวหนึ่ง อีกฝั่งจะล้มเหลว ซึ่ง README ต้องอธิบายเรื่องนี้ให้ชัด และบอกวิธีรันทีละ provider ด้วยการตั้ง env ให้ตรงกับบริการที่มี

- [ ] **Step 5: ยืนยันกับ mock**

```bash
cd lessons/06-provider-abstraction
AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py
```

Expected: OK สองบรรทัด

- [ ] **Step 6: เขียน README.md**

หัวข้อที่ต้องมี

1. The problem left over from lesson 05. โค้ดผูกกับรูปแบบเดียว เปลี่ยนเจ้าไม่ได้
2. The three real differences between the two APIs, with the actual JSON of both side by side
3. What an interface is, explained without the word polymorphism
4. Why the interface is streaming first. อธิบายว่าถ้าออกแบบเป็นแบบไม่ stream ก่อนจะต้องรื้อทั้งสองคลาสทีหลัง
5. Writing providers.py class by class
6. Changing the agent loop to take a provider instead of importing one
7. Running check.py against the mock server, and how to run it against a real service
8. This is the end of part one. สรุปว่าตอนนี้ผู้เรียนมี agent ที่ stream ได้ เรียก tool ได้ และเปลี่ยนผู้ให้บริการได้ พร้อมชี้ว่าภาค 2 จะให้ agent แตะไฟล์จริง

- [ ] **Step 7: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add lessons/06-provider-abstraction
git commit -m "docs: add lesson 06 provider abstraction"
```

---

## Task 21: Lesson runner

**Files:**
- Create: `ci/run_lessons.py`

- [ ] **Step 1: เขียน runner**

```python
"""Run every lesson check against the mock server.

This is the same script a learner can run to prove the whole course still
works on their machine, and the one CI runs on every push. Having one script
for both means CI cannot drift away from what learners experience.
"""
import os
import subprocess
import sys
from pathlib import Path

from agentpath.testing.mock_server import serve

ROOT = Path(__file__).resolve().parents[1]


def main():
    base_url, shutdown = serve()
    environment = dict(os.environ)
    environment["AGENTPATH_BASE_URL"] = f"{base_url}/v1"
    environment["AGENTPATH_MODEL"] = "mock"
    environment["AGENTPATH_API_KEY"] = "mock-key"
    environment["AGENTPATH_AUTO_APPROVE"] = "1"

    failures = []
    lessons = sorted(p for p in (ROOT / "lessons").iterdir() if (p / "check.py").exists())
    for lesson in lessons:
        print(f"\n=== {lesson.name} ===", flush=True)
        completed = subprocess.run(
            [sys.executable, "check.py"], cwd=lesson, env=environment, timeout=120
        )
        if completed.returncode != 0:
            failures.append(lesson.name)

    shutdown()

    print("\n" + "=" * 40)
    if failures:
        print(f"FAILED {len(failures)} of {len(lessons)} lessons")
        for name in failures:
            print(f"  {name}")
        return 1
    print(f"All {len(lessons)} lesson checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`AGENTPATH_AUTO_APPROVE` ตั้งไว้ล่วงหน้าแม้ v0.1 ยังไม่มีบทที่ใช้ เพื่อให้ภาค 2 เพิ่มบทที่ 08 ได้โดยไม่ต้องแก้ runner

- [ ] **Step 2: รันทั้งชุด**

Run: `python ci/run_lessons.py`
Expected: `All 7 lesson checks passed`

- [ ] **Step 3: Commit**

```bash
git add ci/run_lessons.py
git commit -m "feat: add script that runs every lesson check against the mock"
```

---

## Task 22: GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: เขียน workflow**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .
      - run: ruff check --select E9,F63,F7,F82 lessons

  prose:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python ci/prose_lint.py

  tests:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.10", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest -v

  lessons:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: python ci/run_lessons.py
```

งาน lint รัน ruff เต็มรูปแบบกับโค้ดโปรเจกต์ และรันเฉพาะกฎ error ร้ายแรงกับโฟลเดอร์ lessons เพราะโค้ดบทเรียนจงใจซ้ำและจงใจเรียบง่ายกว่ามาตรฐานของ package

- [ ] **Step 2: ตรวจ workflow ในเครื่องก่อน push**

Run ทีละคำสั่งให้ผ่านทั้งหมด

```bash
ruff check .
python ci/prose_lint.py
pytest -v
python ci/run_lessons.py
```

Expected: ผ่านทั้งสี่

- [ ] **Step 3: Commit และ push แล้วดูผลบน GitHub**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run lint, prose lint, tests and lesson checks"
git push
```

Expected: ทั้งสี่งานเขียว ถ้า Windows แดงให้ดูเรื่อง path separator และ encoding ของ subprocess ก่อนเป็นอันดับแรก

---

## Task 23: Root README

**Files:**
- Create: `README.md`

- [ ] **Step 1: เขียน README.md**

หัวข้อที่ต้องมี ห้าม em-dash ห้าม emoji

1. ชื่อโปรเจกต์และ tagline `Learn how AI agents actually work by building a real one, from a single LLM call to a full agent harness.`
2. Who this is for. เขียนให้ชัดว่าไม่ต้องรู้เรื่อง AI มาก่อน ขอแค่เคยเขียนโปรแกรมมาบ้าง
3. Why this exists. tutorial ส่วนใหญ่หยุดที่ agent loop แต่ของจริงที่คนใช้คือ harness
4. What you will build. ตารางภาคทั้งสี่ พร้อมสถานะว่าภาค 1 พร้อมแล้วและภาคที่เหลืออยู่ระหว่างทำ
5. Quickstart. สี่คำสั่ง ติดตั้ง uv, clone, ตั้ง env, รัน lesson 00
6. The lesson index. ลิงก์ไปทุกบทของภาค 1 พร้อมประโยคเดียวว่าบทนั้นให้อะไร
7. Using the finished framework. ตัวอย่าง `pip install agentpath` และ `agentpath chat`
8. How this repository is laid out. อธิบาย lessons, src, ci
9. Running the checks yourself. `python ci/run_lessons.py`
10. Contributing และ License

- [ ] **Step 2: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add README.md
git commit -m "docs: add project README"
```

---

## Task 24: Thai translations

**Files:**
- Create: `lessons/00-setup/README.th.md` ถึง `lessons/06-provider-abstraction/README.th.md`
- Create: `README.th.md`

- [ ] **Step 1: แปลทีละไฟล์**

แปลจากฉบับอังกฤษที่ commit แล้ว ไม่ใช่แปลจากความจำ กฎการแปล

- คงศัพท์เทคนิคเป็นอังกฤษ เช่น tool call, streaming, provider, agent loop เพราะผู้เรียนต้องอ่านเอกสารอังกฤษต่อได้
- แปลคำอธิบายและเหตุผลทั้งหมดเป็นไทย
- comment ในโค้ดคงเป็นอังกฤษ เพื่อให้โค้ดในบททั้งสองภาษาเป็นไฟล์เดียวกัน
- ห้าม em-dash ห้าม colon ห้าม emoji เหมือนฉบับอังกฤษ

- [ ] **Step 2: ใส่ลิงก์สลับภาษาไว้บนสุดของทุกไฟล์**

ฉบับอังกฤษใส่บรรทัด `[อ่านภาษาไทย](README.th.md)` และฉบับไทยใส่ `[Read in English](README.md)`

- [ ] **Step 3: prose lint แล้ว commit**

```bash
python ci/prose_lint.py
git add README.th.md lessons/*/README.th.md
git commit -m "docs: add Thai translations for part one"
```

---

## Task 25: Release v0.1

ขั้นตอนนี้ต้องใช้ credential ของเจ้าของโปรเจกต์ ผู้ใช้เป็นคนรันเอง ไม่ใช่ agent

- [ ] **Step 1: ตรวจครั้งสุดท้าย**

```bash
ruff check . && python ci/prose_lint.py && pytest -q && python ci/run_lessons.py
```

Expected: ผ่านทั้งสี่

- [ ] **Step 2: build**

```bash
uv build
```

Expected: ได้ไฟล์ใน `dist/` ทั้ง wheel และ sdist

- [ ] **Step 3: ทดสอบติดตั้งจาก wheel ใน environment สะอาด**

```bash
uv venv /tmp/agentpath-check && /tmp/agentpath-check/bin/pip install dist/agentpath-0.1.0-py3-none-any.whl && /tmp/agentpath-check/bin/agentpath --help
```

Expected: help ของ CLI แสดงผล และไม่มี dependency อื่นถูกดึงมานอกจาก httpx

- [ ] **Step 4: upload ขึ้น PyPI**

เจ้าของโปรเจกต์รันด้วย token ของตัวเอง

```bash
uv publish
```

Expected: ชื่อ agentpath ถูกจองเรียบร้อย

- [ ] **Step 5: tag และ release**

```bash
git tag -a v0.1.0 -m "Part one, foundations"
git push origin v0.1.0
```

จากนั้นสร้าง GitHub release จาก tag นี้ เขียน changelog ที่บอกว่าภาค 1 มีบทอะไรบ้าง และภาค 2 กำลังจะมาอะไร

---

## Self-Review

**Spec coverage** ตรวจแล้วทุกหัวข้อของเสปคภาค 1 มี task รองรับ บทที่ 00 ถึง 06 อยู่ใน Task 14 ถึง 20 สัญญา env var อยู่ใน Task 9, 13, 14 เป็นต้นไป mock server สามความสามารถของภาค 1 อยู่ใน Task 3, 4, 5, 6 การจำลอง failure ของภาค 3 จงใจไม่ทำใน v0.1 ตามหลักการ ship ทีละภาค prose lint อยู่ใน Task 2 CI สี่งานอยู่ใน Task 22 การแปลไทยอยู่ใน Task 24 การ publish จองชื่ออยู่ใน Task 25

**สิ่งที่ไม่อยู่ใน v0.1 โดยตั้งใจ** file tools, shell tool, permission system, session, context management, MCP, subagent, eval ทั้งหมดเป็นของภาค 2 ถึง 4 ตามแผน ship

**Type consistency** ชื่อที่ใช้ข้าม task ตรงกันแล้ว `Provider.stream(messages, tools)` ใน Task 9 และ 10 ตรงกัน `ToolRegistry.schemas()` และ `ToolRegistry.run(call)` ใน Task 11 ถูกเรียกด้วยชื่อเดิมใน Task 12 `ToolResult` มี field `tool_call_id`, `name`, `content` เหมือนกันทุกที่ ฝั่งบทเรียนใช้ dict ธรรมดาและใช้คีย์ `id`, `name`, `arguments` เหมือนกันทุกบท

**ข้อควรระวังตอน execute** สองข้อ ข้อแรก Task 18 มีโค้ดที่เขียน `__import__("json").dumps` ไว้เพื่ออธิบาย ต้องเปลี่ยนเป็น `import json` ปกติตามที่หมายเหตุระบุ ข้อสอง Task 12 มี test สองเวอร์ชันสำหรับเคส max turns ให้ใช้เวอร์ชันหลังที่ใช้ provider ปลอมเท่านั้น
