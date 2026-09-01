# agentpath v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development.

**Goal:** ส่งมอบภาค 4 Advanced ซึ่งคือบทเรียน 19 ถึง 23 และปิดหลักสูตรทั้ง 24 บท ให้ harness ต่อกับโลกภายนอกผ่าน MCP แบ่งงานให้ subagent ทำขนานกันได้ และวัดผลตัวเองได้

**Architecture:** ยังไม่แตะ agent loop เหมือนเดิม MCP เข้ามาเป็น tool ที่ค้นพบตอน runtime subagent เข้ามาเป็น tool ที่ข้างในมี agent อีกตัว eval เป็นตัวเรียก loop จากข้างนอก ทั้งสามอย่างพิสูจน์ว่า design จากภาค 1 ยังยืนอยู่หลังผ่านมาสามภาค

**Spec:** `docs/specs/2026-09-01-agentpath-design.md` ภาค 4 และหัวข้อย่อยบังคับของบท 19 20 21

---

## Key Design Decisions

1. **เขียน MCP client เองแบบ sync ไม่ใช้ SDK** ส่วนที่ใช้จริงมีแค่ initialize, notifications/initialized, tools/list และ tools/call ซึ่งเป็น JSON-RPC บรรทัดต่อบรรทัดผ่าน stdio รวมประมาณร้อยบรรทัด การใช้ SDK จะซ่อนสิ่งที่บทนี้ต้องการสอนพอดี และจะลาก dependency เข้ามาขัดกฎ httpx ตัวเดียว v1 รองรับ stdio เท่านั้น ไม่รองรับ HTTP transport

2. **ทดสอบ MCP ด้วย MCP server ปลอมของเราเอง** เขียน `testing/mock_mcp_server.py` เป็น server stdio จิ๋วที่มี tool สองตัว เหตุผลเดียวกับ mock LLM server คือ CI ต้องรันได้ฟรีและได้ผลเดิมทุกครั้ง โดยไม่ต้องติดตั้งอะไรจากภายนอก

3. **Subagent คือ tool ที่ข้างในมี agent** ไม่ใช่กลไกพิเศษ ตัวแม่เห็นมันเป็น tool ตัวหนึ่งเหมือน read_file นี่คือเหตุผลที่ loop ไม่ต้องแก้อะไรเลย

4. **Subagent มี context ของตัวเอง และนั่นคือทั้งข้อดีและกับดัก** ข้อดีคือประวัติยาวๆ ของลูกไม่ไหลเข้า context ของแม่ กับดักคือแม่กับลูกมองเห็น state คนละเวอร์ชัน ลูกแก้ไฟล์ไปแล้วแต่แม่ยังตัดสินใจจากของเก่า ต้องสอนเรื่องนี้ตรงๆ

5. **งานขนานใช้ thread กับ queue** สอดคล้องกับการตัดสินใจ sync ทั้งระบบจากภาค 1 ลูกแต่ละตัว push event ลง `queue.Queue` แล้วแม่ drain ออกมาแสดง จุดที่ยากคือ streaming กับ concurrency ชนกัน ต้องสอนไม่ใช่ซ่อน

6. **Eval รันบน mock server ได้** task runner รับรายการงาน แต่ละงานมี prompt กับฟังก์ชันตรวจ ส่วน LLM-as-judge เป็นตัวเลือกเพิ่ม เหตุผลที่ต้องรันบน mock ได้คือ CI ต้องพิสูจน์ว่า eval ทำงาน โดยไม่ต้องจ่ายเงิน

7. **การเลือก model อยู่ในบท eval** เพราะการบอกว่า model ไหนดีกว่าโดยไม่มีชุดทดสอบคือการเดา สองเรื่องนี้แยกกันไม่ได้

---

## Task 1: MCP client

**Files:** Create `src/agentpath/mcp.py`, `src/agentpath/testing/mock_mcp_server.py`, `tests/test_mcp.py`

- [ ] **Step 1: เขียน mock MCP server**

server stdio จิ๋วที่อ่าน JSON-RPC ทีละบรรทัดจาก stdin และตอบทาง stdout ต้องรองรับ
`initialize`, `notifications/initialized`, `tools/list` และ `tools/call` มี tool สองตัว
คือ `echo` ที่คืนข้อความเดิม และ `slow_add` ที่บวกเลขแล้วคืนผลลัพธ์ ต้องมี tool ที่ทำให้
เกิด error ด้วยเพื่อทดสอบว่า error ของ MCP กลายเป็นข้อความที่ model อ่านได้

- [ ] **Step 2: เขียน test ที่ต้องแดง**

```python
# tests/test_mcp.py
import sys

import pytest

from agentpath.mcp import MCPClient, mcp_tools
from agentpath.tools.base import ToolRegistry
from agentpath.types import ToolCall

SERVER = [sys.executable, "-m", "agentpath.testing.mock_mcp_server"]


@pytest.fixture
def client():
    with MCPClient(SERVER) as connected:
        yield connected


def test_connecting_reports_the_server_name(client):
    assert client.server_name


def test_tools_are_discovered_at_runtime(client):
    names = {tool["name"] for tool in client.list_tools()}
    assert {"echo", "add"} <= names


def test_a_tool_can_be_called(client):
    assert "hello" in client.call_tool("echo", {"text": "hello"})


def test_a_server_error_becomes_readable_text_not_a_crash(client):
    assert "Error" in client.call_tool("explode", {})


def test_the_connection_is_reused_rather_than_reopened(client):
    """One process for the whole session, not one per call.

    Reconnecting per call would restart the server every time, which is slow
    and loses any state the server holds.
    """
    first = client.process.pid
    client.call_tool("echo", {"text": "one"})
    client.call_tool("echo", {"text": "two"})
    assert client.process.pid == first


def test_mcp_tools_become_ordinary_tools():
    with MCPClient(SERVER) as client:
        registry = ToolRegistry(mcp_tools(client))
        result = registry.run(ToolCall("1", "echo", {"text": "through the registry"}))
        assert "through the registry" in result.content


def test_names_can_be_prefixed_to_avoid_collisions():
    """Two servers can both offer a tool called search."""
    with MCPClient(SERVER) as client:
        names = {tool.name for tool in mcp_tools(client, prefix="demo")}
        assert "demo.echo" in names
```

- [ ] **Step 3: เขียน mcp.py**

โครงสร้างที่ต้องมี

```python
class MCPClient:
    def __init__(self, command, timeout=30): ...
    def __enter__(self): self.connect(); return self
    def __exit__(self, *args): self.close()
    def connect(self): ...      # spawn, initialize, send initialized
    def _request(self, method, params=None): ...   # write one line, read until id matches
    def _notify(self, method, params=None): ...
    def list_tools(self): ...
    def call_tool(self, name, arguments): ...  # returns text, never raises for a tool error
    def close(self): ...


def mcp_tools(client, prefix=None) -> list[Tool]: ...
```

ประเด็นที่ต้องระวังและต้องเขียน comment อธิบาย

- ต้องส่ง `notifications/initialized` หลัง initialize ไม่งั้น server หลายตัวจะไม่ยอมทำงานต่อ
- ต้องอ่านจนกว่าจะเจอ response ที่ `id` ตรงกัน เพราะ server ส่ง notification แทรกมาได้
- `tools/call` ที่ล้มเหลวคืน `isError` กับ content ไม่ใช่ throw ต้องแปลงเป็นข้อความ
- ต้องปิด process ตอนจบ ไม่งั้นจะมี process ค้าง
- MCP tool ทุกตัวถือว่าไม่ปลอดภัยเสมอ `safe=False` เพราะเราไม่รู้ว่า server ทำอะไร

- [ ] **Step 4: รัน test ให้ผ่าน**

- [ ] **Step 5: Commit**

---

## Task 2: Schema budget

**Files:** Modify `src/agentpath/tools/base.py`, `tests/test_tools.py`

หัวข้อย่อยบังคับของบท 19 คือการต่อ MCP หลายตัวทำให้ schema กินครึ่ง context
ก่อนเริ่มงาน ต้องมีเครื่องมือให้ผู้เรียนเห็นตัวเลขจริง

- [ ] เพิ่มเมธอด `ToolRegistry.schema_size()` ที่คืนจำนวนตัวอักษรของ schema ทั้งหมด
      ที่จะถูกส่งไปทุกคำขอ
- [ ] test ต้องพิสูจน์ว่าตัวเลขโตขึ้นเมื่อเพิ่ม tool และ registry ว่างได้ศูนย์
- [ ] เพิ่มการพิมพ์ตัวเลขนี้ตอนเริ่ม CLI เมื่อเปิด `--verbose` เพื่อให้คนเห็นต้นทุนคงที่ของตัวเอง

---

## Task 3: Subagents

**Files:** Create `src/agentpath/subagent.py`, `tests/test_subagent.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

ต้องครอบห้าอย่าง
1. subagent เป็น tool ธรรมดาในสายตาแม่
2. subagent ทำงานแล้วคืนคำตอบสุดท้ายเป็นข้อความ
3. context ของลูกแยกจากแม่ ประวัติของลูกไม่โผล่ใน `agent.messages` ของแม่
4. ลูกใช้ tool ได้จริงและผลกระทบตกถึงดิสก์
5. ลูกที่พังไม่ทำให้แม่ตาย แต่คืน error ที่แม่อ่านได้

- [ ] **Step 2: เขียน subagent.py**

```python
def subagent_tool(build_agent, name="run_subagent", description=None, safe=False) -> Tool:
    """Turn a whole agent into one tool the parent can call.

    build_agent is a function that returns a fresh Agent. It is a function
    rather than an Agent so that every call starts clean. A subagent that
    kept its history between calls would slowly become the thing it was
    created to avoid.
    """
```

ข้างในสร้าง agent ใหม่ รัน แล้วคืนข้อความสุดท้าย ต้องจับ exception ทุกชนิดแล้วคืน
เป็นข้อความ เพราะลูกที่ระเบิดไม่ควรฆ่าแม่

- [ ] **Step 3: หัวข้อบังคับ state ที่ไม่ตรงกัน** เขียน test ที่แสดงให้เห็นว่าแม่ที่อ่านไฟล์
      ไว้ก่อน แล้วให้ลูกไปแก้ไฟล์นั้น จะยังถือเนื้อหาเก่าอยู่ใน context test นี้ไม่ได้ยืนยัน
      ว่าโค้ดถูก แต่ยืนยันว่ากับดักมีจริง ซึ่งเป็นสิ่งที่บทเรียนต้องสอน

- [ ] **Step 4: รัน test ให้ผ่านและ commit**

---

## Task 4: Parallel workers

**Files:** Create `src/agentpath/fanout.py`, `tests/test_fanout.py`

- [ ] **Step 1: ข้อกำหนด**

```python
def run_in_parallel(jobs, workers=4):
    """Run several agent runs at once and merge their events into one stream.

    jobs is a list of (label, callable) where the callable returns an event
    iterator. Yields (label, event) pairs as they arrive from any worker.

    Threads rather than async because the whole project is sync, and because
    an agent run spends nearly all of its time waiting on a socket, which is
    exactly the case threads handle well.
    """
```

ใช้ `queue.Queue` ตัวเดียวเป็นจุดรวม worker แต่ละตัว push `(label, event)` และ push
sentinel ตอนจบ ตัวหลัก drain จนครบทุก sentinel

- [ ] **Step 2: test ต้องครอบ**

1. งานทุกชิ้นเสร็จและ event ครบ
2. event ของแต่ละงานมาตามลำดับของงานนั้น แม้จะสลับกับงานอื่น
3. งานที่ throw ไม่ทำให้ทั้งชุดตาย และรายงานเป็น error ของงานนั้น
4. งานสิบชิ้นกับ worker สองตัวยังเสร็จครบ

- [ ] **Step 3: Commit**

---

## Task 5: Evals

**Files:** Create `src/agentpath/evals/__init__.py`, `src/agentpath/evals/runner.py`, `tests/test_evals.py`

- [ ] **Step 1: ข้อกำหนด**

```python
@dataclass
class Task:
    name: str
    prompt: str
    check: object          # callable(answer, workspace) -> (bool, str)


@dataclass
class Result:
    task: str
    passed: bool
    detail: str
    usage: dict


def run_evals(tasks, build_agent, workers=1) -> list[Result]: ...


def judge(provider, question, answer, criteria) -> tuple[bool, str]:
    """Ask a model whether an answer meets a written standard.

    Used only when the thing being judged cannot be checked mechanically.
    A check that can be a function should be a function, because a function
    is free, instant and does not have opinions.
    """
```

- [ ] **Step 2: test ต้องครอบ** งานที่ผ่านและงานที่ตกถูกรายงานถูก, การตรวจที่ throw
      กลายเป็นตกไม่ใช่ crash, usage ถูกเก็บต่อ task, และ judge ที่ตอบ yes กับ no ถูกแปลถูก

- [ ] **Step 3: เพิ่มคำสั่ง `agentpath eval`** ที่รับไฟล์ Python ที่ประกาศ `TASKS` แล้วรัน
      พิมพ์ตารางผลและ exit code ที่ไม่ใช่ศูนย์เมื่อมีงานตก เพื่อให้ใช้ใน CI ได้

- [ ] **Step 4: Commit**

---

## Task 6 ถึง 10: บทเรียน 19 ถึง 23

| บท | โฟลเดอร์ | check ต้องพิสูจน์อะไร |
|----|----------|------------------------|
| 19 MCP client | `lessons/19-mcp-client/` | ต่อ server ได้, ค้น tool ได้ตอน runtime, เรียกได้, error กลายเป็นข้อความ, และ schema ของ MCP กินที่เท่าไรเป็นตัวเลขจริง |
| 20 subagents | `lessons/20-subagents/` | subagent เป็น tool ธรรมดา, ทำงานได้จริงถึงดิสก์, context แยกจากแม่จริง, ลูกพังแล้วแม่รอด |
| 21 multi-agent | `lessons/21-multi-agent/` | งานหลายชิ้นรันขนานแล้วเสร็จครบ, event ของแต่ละงานเรียงถูกภายในงานตัวเอง, งานที่พังไม่ล้มทั้งชุด |
| 22 evals | `lessons/22-evals/` | ชุดงานรันแล้วรายงานผ่านและตกถูกต้อง, judge ทำงาน, และ exit code บอกผลได้ |
| 23 ship it | `lessons/23-ship-it/` | ไม่มีโค้ดใหม่ check ตรวจว่า package ที่ผู้เรียนสร้างติดตั้งและ import ได้ |

**หัวข้อบังคับของ README**

- บท 19 ต้องมีเรื่อง schema bloat พร้อมตัวเลขจริง และเรื่อง MCP tool ต้องถือว่าไม่ปลอดภัยเสมอ
  เพราะเราไม่ได้เขียนมันเอง เชื่อมกับ permission system ของบท 12
- บท 20 ต้องมีเรื่องแม่กับลูกเห็น state คนละเวอร์ชัน และต้องพูดตรงๆ ว่าการแยก context
  ซึ่งเป็นข้อดีหลักของ subagent คือสิ่งที่ทำให้ปัญหานี้หนักขึ้น
- บท 21 ต้องมีเรื่อง streaming ชนกับ concurrency คือ event จากหลาย worker มาปนกัน
  และเรื่อง tool สองตัวแตะไฟล์เดียวกันพร้อมกันแล้วทับกัน
- บท 22 ต้องมีเรื่องการเลือก model ด้วยการวัด และการแบ่ง tier ตามงาน
- บท 23 เป็นบทปิดหลักสูตร ต้องสรุปทั้งสี่ภาคและชี้ทางต่อ

## Task 11: Thai translations

## Task 12: Release v1.0

- [ ] อัปเดต README ทั้งสองภาษา ภาค 4 เป็น Available now และเพิ่มบท 19 ถึง 23
- [ ] version 1.0.0
- [ ] รันครบสี่อย่าง build ทดสอบติดตั้ง แล้ว tag `v1.0.0`
- [ ] เขียน `CHANGELOG.md` ที่สรุปทั้งสี่ release

---

## Self-Review

**Spec coverage** บท 19 ถึง 23 ครบ หัวข้อย่อยบังคับของบท 19 อยู่ใน Task 2 และ 6
ของบท 20 และ 21 อยู่ใน Task 3 และ 4

**สิ่งที่ยังไม่ทำและประกาศไว้** MCP HTTP transport, async, vector database เต็มรูปแบบ
ทั้งหมดอยู่ใน `docs/v2-ideas.md` แล้ว

**ความเสี่ยงที่รู้ตัว** สองข้อ ข้อแรก MCP client คุยกับ subprocess ผ่าน pipe ซึ่งบน Windows
มีเรื่อง buffering และ newline ที่ต่างจาก Unix ต้องทดสอบบนทั้งสองระบบตั้งแต่ต้น ข้อสอง
การรัน agent ขนานกันใน test อาจ flaky ถ้าพึ่งลำดับเวลา ดังนั้น test ต้องยืนยันความครบถ้วน
และลำดับภายในงานเดียวกัน ไม่ใช่ลำดับข้ามงาน
