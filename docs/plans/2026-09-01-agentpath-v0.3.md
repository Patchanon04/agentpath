# agentpath v0.3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development.

**Goal:** ส่งมอบภาค 3 The Harness ซึ่งคือบทเรียน 12 ถึง 18 ทำให้ agent กลายเป็นเครื่องมือที่ไว้ใจได้ จำการอนุญาตได้ กลับมาทำงานต่อได้ อยู่รอดเมื่อบทสนทนายาวเกิน และไม่ตายเมื่อ API ล่ม

**Architecture:** agent loop ยังไม่เปลี่ยนโครง สิ่งที่เพิ่มคือชั้นรอบๆ loop ทั้งหมด permission เป็น callback ที่ฉีดเข้ามาตามที่ v0.1 ออกแบบไว้ session เป็นไฟล์ JSONL context management เป็นฟังก์ชันบริสุทธิ์ที่ทำงานกับ list ของ message และ retry เป็น decorator รอบการเรียก provider

**Spec:** `docs/specs/2026-09-01-agentpath-design.md` ภาค 3 และหัวข้อย่อยบังคับของบท 12 13 14 15 17

**หมายเหตุเรื่องความละเอียดของแผนนี้** แผนนี้ให้โค้ดเต็มเฉพาะส่วนที่ตัดสินใจยากหรือพลาดง่าย ส่วนที่เป็นรูปแบบซ้ำกับภาค 1 และ 2 เช่นการคัดลอกโฟลเดอร์บทเรียนและโครง check.py จะระบุเป็นข้อกำหนดแทนโค้ดเต็ม เพราะรูปแบบนั้นตั้งมั่นแล้วใน repo และการทำซ้ำในเอกสารไม่ได้ลดความเสี่ยงลง

---

## Key Design Decisions

1. **Permission เป็นวัตถุที่จำได้ ไม่ใช่ฟังก์ชันที่ถามทุกครั้ง** ชั้น `Permissions` เก็บกฎสามอย่าง tool ที่ปลอดภัยเสมอ, กฎที่ผู้ใช้เคยตอบว่าอนุญาตตลอดในเซสชันนี้, และ callback สำหรับถาม สิ่งที่เปลี่ยนจากภาค 2 คือคำตอบ allow always ถูกจำ ไม่ใช่ถามซ้ำทุกครั้ง

2. **การจำแนกว่า tool ไหนอันตรายอยู่ที่ Tool ไม่ใช่ที่ Permissions** เพิ่ม field `safe: bool` ลง dataclass `Tool` เหตุผลคือคนเขียน tool คือคนที่รู้ว่ามันอันตรายไหม ไม่ใช่คนตั้งค่า permission และการแยกไปอยู่คนละที่จะทำให้เพิ่ม tool ใหม่แล้วลืมตั้งค่า ซึ่ง default ต้องเป็นไม่ปลอดภัยเสมอ

3. **Session เป็น JSONL แบบเพิ่มอย่างเดียว** หนึ่งบรรทัดหนึ่ง message เขียนทันทีที่เกิด ไม่รอจบ เหตุผลคือถ้าโปรแกรมตายกลางคันสิ่งที่ทำไปแล้วยังอยู่ และไฟล์เปิดอ่านด้วยตาเปล่าได้ ซึ่งทำให้มันเป็นเครื่องมือ debug อันดับหนึ่ง ประกาศตรงๆ ว่า v1 รองรับผู้เขียนคนเดียว

4. **Context management ต้องมองคู่ tool call กับ tool result เป็นก้อนเดียว** นี่คือกับดักใหญ่ที่สุดของภาค 3 ถ้าตัด history ตรงกลางระหว่าง assistant ที่มี tool_calls กับ tool result ของมัน API จะปฏิเสธด้วย 400 ทันที การตัดจึงทำเป็นบล็อกที่เริ่มต้นด้วย user message และจบก่อน user message ถัดไป

5. **การนับ token ใช้ตัวเลขจริงจาก provider เป็นหลัก** ไม่ใช้ตัวนับข้ามเจ้า provider ส่งจำนวน token ที่ใช้จริงกลับมาในทุก response เราเก็บค่านั้น ส่วนการประมาณก่อนส่งใช้กฎหยาบๆ ที่ประกาศตรงๆ ว่าเป็นการประมาณ

6. **Retry รู้จัก Retry-After และมี jitter** และ retry เฉพาะสิ่งที่ปลอดภัยจะทำซ้ำ การเรียก provider ปลอดภัย ส่วน tool ที่มี side effect ไม่ retry อัตโนมัติ

7. **การขัดจังหวะเป็นวัตถุที่ส่งต่อลงไปทุกชั้น** `Cancellation` ตัวเดียวที่ loop เช็คระหว่าง turn และ shell tool เช็คก่อนรัน เพื่อให้การกด Ctrl+C หยุดของจริงไม่ใช่แค่หน้าจอ

8. **Mock server ต้องจำลอง failure ได้** ผ่าน header `X-Mock-Fail` และต้องส่ง `usage` กลับมาทุกครั้ง ไม่งั้นบท 15 และ 17 ไม่มีอะไรให้ตรวจ

---

## Task 1: Mock server จำลอง failure และรายงาน usage

**Files:** Modify `src/agentpath/testing/mock_server.py`, `tests/test_mock_server.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
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
    first = httpx.post(f"{mock}/v1/chat/completions", json=body, headers=headers)
    second = httpx.post(f"{mock}/v1/chat/completions", json=body, headers=headers)
    third = httpx.post(f"{mock}/v1/chat/completions", json=body, headers=headers)
    assert (first.status_code, second.status_code, third.status_code) == (500, 500, 200)


def test_responses_report_token_usage(mock):
    response = httpx.post(
        f"{mock}/v1/chat/completions",
        json={"model": "mock", "messages": [{"role": "user", "content": "hi"}]},
    )
    usage = response.json()["usage"]
    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_mock_server.py -k "failure or usage" -v`

- [ ] **Step 3: เพิ่มลง mock_server.py**

เพิ่มตัวนับระดับโมดูลและฟังก์ชันช่วย

```python
FAIL_COUNTS: dict[str, int] = {}


def estimate_tokens(text: str) -> int:
    """A deliberately crude token estimate, about four characters per token.

    This is not accurate and the chapter on token economy says so plainly.
    It exists so the mock can report a number that moves in the right
    direction when the conversation grows.
    """
    return max(1, len(text) // 4)


def usage_for(messages, text, tool_calls) -> dict:
    prompt = sum(estimate_tokens(_text_of(m)) for m in messages)
    completion = estimate_tokens(text) + sum(
        estimate_tokens(json.dumps(call["arguments"])) for call in tool_calls
    )
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }
```

เพิ่มการตรวจ header ที่หัวของ `do_POST` ก่อนอย่างอื่น

```python
    def _maybe_fail(self):
        """Return True when this request should fail, per the caller's headers.

        Tests drive this rather than the server choosing to fail on its own,
        because a test that fails at random is not a test.
        """
        status = self.headers.get("X-Mock-Fail")
        if not status:
            return False
        times = self.headers.get("X-Mock-Fail-Times")
        if times is not None:
            key = f"{status}:{times}"
            FAIL_COUNTS[key] = FAIL_COUNTS.get(key, 0) + 1
            if FAIL_COUNTS[key] > int(times):
                return False
        code = int(status)
        headers = {"Retry-After": "2"} if code == 429 else {}
        self._send_json({"error": {"type": "mock_failure", "code": code}}, status=code,
                        extra_headers=headers)
        return True
```

แก้ `_send_json` ให้รับ `extra_headers` และแก้ `openai_body` กับ `anthropic_body` ให้ใส่ `usage`
แล้วเรียก `_maybe_fail` เป็นบรรทัดแรกของ `do_POST`

- [ ] **Step 4: รัน test ทั้งชุดและ lesson check เดิม**

Run: `python -m pytest -q` แล้ว `python ci/run_lessons.py`
Expected: ผ่านทั้งหมด ภาค 1 และ 2 ต้องไม่พัง

- [ ] **Step 5: Commit**

---

## Task 2: Permission system

**Files:** Create `src/agentpath/permissions.py`, `tests/test_permissions.py`
Modify `src/agentpath/tools/base.py` เพิ่ม field `safe`, และ tool ทุกตัวให้ประกาศค่า

- [ ] **Step 1: เพิ่ม safe ลง Tool**

```python
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., object]
    safe: bool = False
```

`safe` ต้องเป็น False โดย default เพราะการลืมตั้งค่าต้องนำไปสู่การถาม ไม่ใช่การอนุญาต
จากนั้นตั้ง `safe=True` ให้ `read_file`, `list_files`, `glob_files`, `grep_files`
และปล่อย `write_file`, `edit_file`, `run_shell` เป็น False

- [ ] **Step 2: เขียน test ที่ต้องแดง**

```python
# tests/test_permissions.py
from agentpath.permissions import ALLOW_ALWAYS, ALLOW_ONCE, DENY, Permissions
from agentpath.tools.base import Tool
from agentpath.types import ToolCall

SAFE = Tool("read_file", "d", {}, lambda: None, safe=True)
RISKY = Tool("run_shell", "d", {}, lambda: None, safe=False)


def test_safe_tools_never_ask():
    asked = []
    permissions = Permissions(ask=lambda tool, call: asked.append(call) or DENY)
    assert permissions.check(SAFE, ToolCall("1", "read_file", {})) is True
    assert asked == []


def test_risky_tools_ask():
    permissions = Permissions(ask=lambda tool, call: ALLOW_ONCE)
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "ls"})) is True


def test_deny_stops_the_call():
    permissions = Permissions(ask=lambda tool, call: DENY)
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "ls"})) is False


def test_allow_once_does_not_persist():
    answers = iter([ALLOW_ONCE, DENY])
    permissions = Permissions(ask=lambda tool, call: next(answers))
    call = ToolCall("1", "run_shell", {"command": "ls"})
    assert permissions.check(RISKY, call) is True
    assert permissions.check(RISKY, call) is False


def test_allow_always_is_remembered_for_the_same_command():
    asked = []

    def ask(tool, call):
        asked.append(call)
        return ALLOW_ALWAYS

    permissions = Permissions(ask=ask)
    call = ToolCall("1", "run_shell", {"command": "git status"})
    assert permissions.check(RISKY, call) is True
    assert permissions.check(RISKY, call) is True
    assert len(asked) == 1


def test_allow_always_does_not_leak_to_a_different_command():
    answers = iter([ALLOW_ALWAYS, DENY])
    permissions = Permissions(ask=lambda tool, call: next(answers))
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "git status"})) is True
    assert permissions.check(RISKY, ToolCall("2", "run_shell", {"command": "rm -rf /"})) is False


def test_auto_approve_mode_never_asks():
    permissions = Permissions(ask=lambda tool, call: DENY, auto_approve=True)
    assert permissions.check(RISKY, ToolCall("1", "run_shell", {"command": "ls"})) is True
```

- [ ] **Step 3: เขียน permissions.py**

```python
"""Deciding what the agent is allowed to do, and remembering the answer.

Lesson 08 asked a yes or no question before every command. That is correct
and it is also unusable, because being asked to approve the same harmless
command forty times trains you to stop reading the question. A permission
system is what you get when you keep the gate and remove the fatigue.

The rule for what counts as risky lives on the Tool rather than here. The
person who writes a tool knows whether it can destroy something, and a
default of not safe means that forgetting to think about it leads to a
question rather than to silence.
"""
import json
from dataclasses import dataclass, field

from agentpath.tools.base import Tool
from agentpath.types import ToolCall

ALLOW_ONCE = "allow_once"
ALLOW_ALWAYS = "allow_always"
DENY = "deny"


def signature(call: ToolCall) -> str:
    """A stable string identifying this exact call, used for remembering.

    The arguments are part of the signature on purpose. Approving
    git status must not also approve rm -rf, and a rule keyed on the tool
    name alone would do exactly that.
    """
    return f"{call.name}({json.dumps(call.arguments, sort_keys=True)})"


@dataclass
class Permissions:
    ask: object = None
    auto_approve: bool = False
    remembered: set = field(default_factory=set)

    def check(self, tool: Tool, call: ToolCall) -> bool:
        if tool.safe:
            return True
        if self.auto_approve:
            return True
        if signature(call) in self.remembered:
            return True
        if self.ask is None:
            return False
        answer = self.ask(tool, call)
        if answer == ALLOW_ALWAYS:
            self.remembered.add(signature(call))
            return True
        return answer == ALLOW_ONCE
```

- [ ] **Step 4: ต่อเข้า Agent**

`Agent.__init__` รับ `permissions=None` และ loop เรียก `self.permissions.check(tool, call)`
ก่อนรัน ถ้าไม่ผ่านให้ใส่ ToolResult ที่บอกว่าผู้ใช้ปฏิเสธ ไม่ใช่ข้ามเงียบๆ เพราะ model
ต้องรู้ว่าเกิดอะไรขึ้นจึงจะเปลี่ยนแผนได้ ต้องเพิ่มเมธอด `ToolRegistry.get(name)` ด้วย

- [ ] **Step 5: รัน test ให้ผ่านและ commit**

---

## Task 3: Sessions

**Files:** Create `src/agentpath/session.py`, `tests/test_session.py`

- [ ] **Step 1: เขียน test**

ต้องครอบสี่อย่าง เขียนแล้วอ่านกลับได้เหมือนเดิมรวม tool_calls, ไฟล์เป็น JSONL ที่แต่ละ
บรรทัดคือ JSON ที่ parse ได้, การเขียนเป็นแบบเพิ่มทีละบรรทัดจึงรอดเมื่อโปรแกรมตายกลางคัน,
และ list สามารถบอกรายการ session ที่มีอยู่ได้

- [ ] **Step 2: เขียน session.py**

```python
"""Saving a conversation so you can come back to it.

The format is one JSON object per line, which is called JSONL. Two things
make it the right choice here. Each message is written the moment it
happens rather than at the end, so a crash loses nothing that already
finished. And you can open the file and read it, which matters more than it
sounds, because the session file is the first place to look when you want
to know why the agent did something.

This version supports one writer. Two processes appending to the same
session will interleave and corrupt it. Real harnesses take a lock. That is
left out here because the locking is not the lesson.
"""
import json
import os
from dataclasses import asdict
from pathlib import Path

from agentpath.types import Message, ToolCall


def default_directory() -> Path:
    return Path(os.environ.get("AGENTPATH_HOME", Path.home() / ".agentpath")) / "sessions"


def to_json(message: Message) -> str:
    return json.dumps(asdict(message))


def from_json(line: str) -> Message:
    raw = json.loads(line)
    raw["tool_calls"] = [ToolCall(**call) for call in raw.get("tool_calls", [])]
    return Message(**raw)


class Session:
    def __init__(self, name, directory=None):
        self.name = name
        self.path = Path(directory or default_directory()) / f"{name}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, message: Message) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(to_json(message) + "\n")

    def load(self) -> list[Message]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [from_json(line) for line in lines if line.strip()]

    @staticmethod
    def list_all(directory=None) -> list[str]:
        folder = Path(directory or default_directory())
        if not folder.is_dir():
            return []
        return sorted(p.stem for p in folder.glob("*.jsonl"))
```

- [ ] **Step 3: ต่อเข้า Agent** ผ่าน `on_message` callback ที่ Agent เรียกทุกครั้งที่ต่อ message
เข้า history เหตุผลที่ใช้ callback แทนการให้ Agent รู้จัก Session คือ loop ต้องไม่ผูกกับ
ที่เก็บข้อมูล ซึ่งเป็นหลักการเดียวกับ permission

- [ ] **Step 4: รัน test ให้ผ่านและ commit**

---

## Task 4: Context management

**Files:** Create `src/agentpath/context.py`, `tests/test_context.py`

นี่คือ task ที่สำคัญที่สุดของภาค 3

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_context.py
from agentpath.context import estimate_tokens, fit_to_budget, split_into_blocks
from agentpath.types import Message, ToolCall

CALL = ToolCall(id="c1", name="add", arguments={"a": 1})


def conversation():
    return [
        Message(role="system", content="be terse"),
        Message(role="user", content="first question"),
        Message(role="assistant", content="", tool_calls=[CALL]),
        Message(role="tool", content="result", tool_call_id="c1"),
        Message(role="assistant", content="first answer"),
        Message(role="user", content="second question"),
        Message(role="assistant", content="second answer"),
    ]


def test_blocks_start_at_user_messages():
    blocks = split_into_blocks(conversation()[1:])
    assert len(blocks) == 2
    assert blocks[0][0].content == "first question"
    assert blocks[1][0].content == "second question"


def test_a_tool_call_and_its_result_stay_in_the_same_block():
    blocks = split_into_blocks(conversation()[1:])
    roles = [m.role for m in blocks[0]]
    assert roles == ["user", "assistant", "tool", "assistant"]


def test_the_system_message_is_never_dropped():
    kept = fit_to_budget(conversation(), budget=1)
    assert kept[0].role == "system"


def test_the_most_recent_exchange_is_kept():
    kept = fit_to_budget(conversation(), budget=20)
    assert kept[-1].content == "second answer"


def test_no_orphan_tool_result_survives_trimming():
    """This is the bug the whole module exists to prevent.

    A tool result whose matching tool call has been trimmed away makes the
    API reject the next request outright with a 400, so trimming has to
    treat the pair as one thing.
    """
    for budget in range(1, 60):
        kept = fit_to_budget(conversation(), budget=budget)
        call_ids = {c.id for m in kept for c in m.tool_calls}
        result_ids = {m.tool_call_id for m in kept if m.role == "tool"}
        assert result_ids <= call_ids, f"orphaned tool result at budget {budget}"


def test_everything_fits_when_the_budget_is_large():
    assert fit_to_budget(conversation(), budget=10000) == conversation()


def test_estimate_is_rough_but_grows_with_length():
    assert estimate_tokens([Message(role="user", content="x" * 400)]) > estimate_tokens(
        [Message(role="user", content="x" * 40)]
    )
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

- [ ] **Step 3: เขียน context.py**

```python
"""Keeping the conversation small enough to send.

Every message is resent on every request, so a long conversation eventually
does not fit and the request is rejected. Something has to be dropped.

The dangerous way to drop things is to slice the list of messages by token
count until it fits. That produces a conversation where a tool result sits
with no tool call in front of it, and the API rejects the whole request
with a 400 rather than ignoring the stray message. The trap is that the
error arrives on the next request rather than on the one you trimmed, so
it looks unrelated to what you just did.

The fix is to never look at a single message. Work in blocks that start at
a user message and run up to just before the next one. A block always holds
a tool call together with its result, so dropping a whole block can never
strand anything.
"""
from agentpath.types import Message

CHARACTERS_PER_TOKEN = 4


def estimate_tokens(messages: list[Message]) -> int:
    """A rough count, deliberately not exact.

    Every provider counts differently and none of them count the way a
    character estimate does. Use this to decide when to start trimming, and
    use the number the provider reports afterwards to know what actually
    happened. Trusting a local estimate to be exact is how people end up
    trimming to ninety percent of a window and still getting rejected.
    """
    total = 0
    for message in messages:
        total += len(message.content) // CHARACTERS_PER_TOKEN
        for call in message.tool_calls:
            total += len(str(call.arguments)) // CHARACTERS_PER_TOKEN
        total += 4
    return total


def split_into_blocks(messages: list[Message]) -> list[list[Message]]:
    """Group messages into exchanges that begin with a user message."""
    blocks: list[list[Message]] = []
    for message in messages:
        if message.role == "user" or not blocks:
            blocks.append([message])
        else:
            blocks[-1].append(message)
    return blocks


def fit_to_budget(messages: list[Message], budget: int) -> list[Message]:
    """Return the newest messages that fit, dropping whole exchanges.

    System messages are always kept because they are the instructions, and
    an agent that forgets its instructions half way through a task is worse
    than one that forgets the beginning of the conversation.
    """
    system = [m for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]
    blocks = split_into_blocks(rest)

    kept: list[list[Message]] = []
    used = estimate_tokens(system)
    for block in reversed(blocks):
        cost = estimate_tokens(block)
        if kept and used + cost > budget:
            break
        kept.insert(0, block)
        used += cost
    return system + [message for block in kept for message in block]
```

- [ ] **Step 4: ต่อเข้า Agent** ให้ Agent รับ `budget=None` และเรียก `fit_to_budget` ก่อนส่ง
ทุกครั้ง โดยไม่แก้ `self.messages` เอง เหตุผลคือ history เต็มยังมีค่าสำหรับ session และ
การ debug สิ่งที่หดคือสิ่งที่ส่ง ไม่ใช่สิ่งที่จำ

- [ ] **Step 5: รัน test ให้ผ่านและ commit**

---

## Task 5: Token accounting

**Files:** Create `src/agentpath/usage.py`, `tests/test_usage.py`
Modify providers ให้อ่าน usage จาก response แล้วส่งออกมาใน `TurnDone`

- [ ] **Step 1: เพิ่ม field ลง TurnDone**

```python
@dataclass
class TurnDone:
    message: Message
    usage: dict = field(default_factory=dict)
```

- [ ] **Step 2: ให้ provider อ่าน usage** OpenAI ส่ง `usage` มาใน chunk สุดท้ายเมื่อขอ
`stream_options` หรือใน body เมื่อไม่ stream ส่วน mock ของเราส่งมาเสมอ ให้ provider
เก็บ field `usage` ถ้ามีและใส่ลง TurnDone

- [ ] **Step 3: เขียน usage.py**

```python
"""Keeping track of what a run costs.

The numbers here come from the provider rather than from a local estimate,
because a local estimate is wrong by enough to matter. tiktoken does not
count Claude tokens and the reverse is also true, so a harness that speaks
to more than one service and uses one counter for both is making decisions
on the wrong number.
"""
from dataclasses import dataclass, field


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0
    per_call: list = field(default_factory=list)

    def add(self, reported: dict) -> None:
        if not reported:
            return
        self.calls += 1
        self.prompt_tokens += reported.get("prompt_tokens", 0)
        self.completion_tokens += reported.get("completion_tokens", 0)
        self.per_call.append(reported)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def cost(self, prompt_price_per_million=0.0, completion_price_per_million=0.0) -> float:
        return (
            self.prompt_tokens * prompt_price_per_million
            + self.completion_tokens * completion_price_per_million
        ) / 1_000_000

    def summary(self) -> str:
        return (
            f"{self.calls} calls, {self.prompt_tokens} prompt tokens, "
            f"{self.completion_tokens} completion tokens"
        )
```

- [ ] **Step 4: test ต้องพิสูจน์ว่า prompt token โตขึ้นทุกรอบในบทสนทนาที่มี tool call**
ซึ่งเป็นหลักฐานของประโยคที่บทนี้สอนว่าบทสนทนาเดิมแพงขึ้นเรื่อยๆ

- [ ] **Step 5: Commit**

---

## Task 6: Retrieval

**Files:** Create `src/agentpath/tools/retrieval.py`, `tests/test_retrieval.py`

- [ ] **Step 1: ข้อกำหนด** สร้าง tool ชื่อ `search_notes` ที่ทำ retrieval แบบง่ายที่สุดที่
ยังทำงานจริง คือหั่นไฟล์ text เป็นย่อหน้า ให้คะแนนด้วยจำนวนคำที่ตรงกันถ่วงด้วยความหายาก
ของคำ แล้วคืน top N พร้อมชื่อไฟล์ ห้ามใช้ embedding และห้ามเพิ่ม dependency
เหตุผลคือบทนี้สอนกลไกและการตัดสินใจ ไม่ได้สอนวิธีใช้ vector database

- [ ] **Step 2: test ต้องพิสูจน์สามอย่าง** คำถามที่ใช้คำตรงกับเอกสารได้เอกสารนั้นเป็นอันดับหนึ่ง,
คำที่โผล่ในทุกเอกสารต้องไม่ทำให้คะแนนเพี้ยน, และผลลัพธ์บอกที่มาเสมอเพื่อให้ agent
ไปอ่านต่อได้

- [ ] **Step 3: Commit**

---

## Task 7: Errors, retries and cancellation

**Files:** Create `src/agentpath/retry.py`, `tests/test_retry.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

ต้องครอบห้าอย่าง
1. สำเร็จตั้งแต่ครั้งแรกไม่ retry
2. 500 แล้วสำเร็จ ทำให้ผลลัพธ์ออกมาถูกต้อง
3. 429 ที่มี Retry-After ทำให้รอตามที่ header บอก ไม่ใช่ตามสูตรของเราเอง
4. 400 ไม่ retry เพราะการส่งคำขอที่ผิดซ้ำก็ผิดเหมือนเดิม
5. delay มี jitter คือค่าไม่เท่ากันเป๊ะทุกครั้ง

- [ ] **Step 2: เขียน retry.py**

```python
"""Retrying the things that are safe to retry.

Three ideas matter here and each one is a mistake people make.

The provider knows better than we do. When a response carries Retry-After
we wait exactly that long. Our own doubling formula is the fallback for
when the server said nothing, not an opinion that overrides it.

Jitter is not decoration. Without it every client that failed at the same
moment retries at the same moment, which turns one bad second into a
sustained outage.

Not everything may be retried. Asking the model again is safe. Running a
tool that sent an email is not, which is why nothing here wraps a tool.
"""
import random
import time

import httpx

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


def delay_for(attempt: int, response=None, base=1.0, cap=30.0) -> float:
    """How long to wait before attempt number attempt, counting from one."""
    if response is not None:
        header = response.headers.get("Retry-After")
        if header:
            try:
                return float(header)
            except ValueError:
                pass
    exponential = min(cap, base * (2 ** (attempt - 1)))
    return exponential * (0.5 + random.random() / 2)


def with_retries(call, attempts=4, sleep=time.sleep):
    """Run call, retrying only failures that retrying can fix."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except httpx.HTTPStatusError as error:
            if error.response.status_code not in RETRYABLE_STATUS:
                raise
            last_error = error
            if attempt == attempts:
                break
            sleep(delay_for(attempt, error.response))
        except httpx.TransportError as error:
            last_error = error
            if attempt == attempts:
                break
            sleep(delay_for(attempt))
    raise last_error
```

- [ ] **Step 3: Cancellation** เพิ่มคลาสเล็กๆ ลง `src/agentpath/cancel.py`

```python
"""One object that says stop, shared by everything that can be stopped.

An interrupt that only updates the screen is the bug this prevents. The
same token is checked by the agent loop between turns and by the shell tool
before it starts a process, so pressing Ctrl+C stops the actual work rather
than only the display.
"""
import threading


class Cancellation:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise KeyboardInterrupt("cancelled")
```

- [ ] **Step 4: Doom loop detection** เพิ่มลง Agent การนับ signature ของ tool call ที่ซ้ำ
ถ้า signature เดียวกันเกิดเกินสามครั้งติดกันให้ใส่ ToolResult ที่บอก model ตรงๆ ว่ากำลังวน
และให้เปลี่ยนวิธี เหตุผลคือ max_turns นับจำนวนแต่ไม่ได้ดูว่ามีความคืบหน้าไหม

- [ ] **Step 5: รัน test ให้ผ่านและ commit**

---

## Task 8: CLI ฉบับ harness

**Files:** Modify `src/agentpath/cli.py`

- [ ] เพิ่มคำสั่ง `run` สำหรับงานครั้งเดียวแล้วจบ และ `resume` สำหรับกลับมาทำต่อ
- [ ] `chat` ได้ permission จริงที่ถามแบบมีสามตัวเลือกคือ y, a สำหรับอนุญาตตลอด, และ n
- [ ] ทุกคำสั่งบันทึก session อัตโนมัติและพิมพ์ชื่อ session ตอนจบ
- [ ] ทุกคำสั่งพิมพ์สรุป usage ตอนจบ
- [ ] Ctrl+C ยกเลิกงานปัจจุบันโดยไม่ทิ้ง session
- [ ] test ครอบว่าคำสั่งทั้งสามมีอยู่และ argument ถูกส่งต่อถูกที่

---

## Task 9 ถึง 15: บทเรียน 12 ถึง 18

ทุกบทใช้รูปแบบเดิมคือไฟล์แบนๆ คัดลอกต่อกันมา และ check.py ที่รันกับ mock server ได้

| บท | โฟลเดอร์ | check ต้องพิสูจน์อะไร |
|----|----------|------------------------|
| 12 permission system | `lessons/12-permissions/` | tool ที่ปลอดภัยไม่ถาม, tool อันตรายถาม, deny ทำให้ไม่รันจริง, allow always ถามครั้งเดียวแล้วจำ, และคำสั่งอื่นยังถามอยู่ |
| 13 sessions | `lessons/13-sessions/` | เขียนแล้วอ่านกลับได้ครบรวม tool call, ไฟล์เป็น JSONL ที่อ่านด้วยตาได้, และ resume แล้ว model เห็นบทสนทนาเดิม |
| 14 context management | `lessons/14-context-management/` | ต้องมี test ที่ไล่ budget ทุกค่าแล้วยืนยันว่าไม่มี tool result กำพร้าเหลืออยู่ นี่คือหัวใจของบท |
| 15 token economy | `lessons/15-token-economy/` | prompt token โตขึ้นทุกรอบจริง, และการเรียงของนิ่งไว้หน้าทำให้ prefix เหมือนเดิมข้ามคำขอ |
| 16 retrieval | `lessons/16-retrieval/` | คำถามได้เอกสารที่ถูกเป็นอันดับหนึ่ง, และ grep ตอบคำถามแบบคำตรงได้ดีกว่าเพื่อแสดงว่าเมื่อไหร่ไม่ต้องใช้ retrieval |
| 17 errors and retries | `lessons/17-errors-and-retries/` | 500 แล้วสำเร็จ, 429 รอตาม Retry-After, 400 ไม่ retry, และ doom loop ถูกจับได้ |
| 18 milestone the harness | `lessons/18-the-harness/` | รันงานจริงจนจบ แล้ว resume session นั้นได้และเห็นประวัติเดิม พร้อมสรุป usage |

**หัวข้อบังคับของ README แต่ละบท** ตามเสปคหัวข้อย่อยบังคับ โดยเฉพาะ

- บท 12 ต้องมี prompt injection ที่มาทางผลลัพธ์ของ tool ไม่ใช่แค่ทาง shell และเรื่อง
  id ของ tool call ตอน stream อาจไม่ตรงกับตอนจบ
- บท 13 ต้องมีว่าไฟล์ session คือเครื่องมือ debug อันดับหนึ่ง และข้อจำกัดผู้เขียนคนเดียว
- บท 14 ต้องมีกับดัก tool result กำพร้าเป็นหัวข้อหลักของบท
- บท 15 ต้องมีกฎการเรียงสำหรับ prompt caching และเรื่องตัวนับ token ข้ามเจ้าที่ใช้ไม่ได้
- บท 17 ต้องมีการขัดจังหวะที่หยุดของจริงทุกชั้น, idempotency ของ tool ที่มี side effect,
  และการเคารพ Retry-After ก่อนสูตรของเราเอง

## Task 16: Thai translations

## Task 17: Release v0.3

- [ ] อัปเดต README ทั้งสองภาษา ตารางภาค 3 เป็น Available now และเพิ่มบท 12 ถึง 18
- [ ] version 0.3.0
- [ ] รันครบสี่อย่างแล้ว build แล้ว tag `v0.3.0`

---

## Self-Review

**Spec coverage** บท 12 ถึง 18 ครบ หัวข้อย่อยบังคับทั้งห้ากลุ่มมีที่อยู่ชัดเจน

**สิ่งที่ไม่อยู่ใน v0.3 โดยตั้งใจ** MCP, subagent, multi agent, eval ทั้งหมดเป็นภาค 4

**ความเสี่ยงที่รู้ตัว** สองข้อ ข้อแรก การเพิ่ม field `usage` ลง `TurnDone` แตะโค้ดที่บท 04
ถึง 11 พึ่งพาอยู่ ต้องรัน lesson check ทั้งหมดหลังแก้เพื่อยืนยันว่าไม่พัง ข้อสอง การเพิ่ม
field `safe` ลง `Tool` มี default ที่ปลอดภัยจึงไม่ทำให้โค้ดเดิมพัง แต่ต้องตรวจว่า tool
ที่ควรปลอดภัยถูกตั้งค่าจริง ไม่งั้นผู้เรียนจะโดนถามทุกครั้งที่อ่านไฟล์
