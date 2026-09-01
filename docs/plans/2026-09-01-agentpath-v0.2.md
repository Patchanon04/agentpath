# agentpath v0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** ส่งมอบภาค 2 Real Tools ซึ่งคือบทเรียน 07 ถึง 11 พร้อม tool ที่แตะไฟล์จริงและรันคำสั่งจริง จบด้วย mini coding agent ที่แก้ไฟล์ได้จริง

**Architecture:** ต่อยอดจาก v0.1 โดยไม่แตะ agent loop เลย ทุกอย่างที่เพิ่มเป็น tool ใหม่ใน `src/agentpath/tools/` ซึ่งเป็นการพิสูจน์ว่า design ของภาค 1 ถูก ความปลอดภัยเข้ามาที่ชั้น tool ไม่ใช่ชั้น loop

**Spec:** `docs/specs/2026-09-01-agentpath-design.md` หัวข้อ 5 ภาค 2 และหัวข้อย่อยบังคับของบท 07 08 12

---

## Key Design Decisions

1. **Workspace root ส่งผ่าน factory function ไม่ใช่ global** `file_tools(root)` คืน list ของ Tool ที่ผูกกับ root นั้น เหตุผลคือไม่มี global state ทดสอบง่าย และสอน dependency injection ต่อเนื่องจาก permission callback ของ v0.1

2. **Path safety ทำที่จุดเดียว** ฟังก์ชัน `resolve_inside(root, path)` ตัวเดียวที่ทุก file tool เรียก ทำ resolve แล้วเช็ค `is_relative_to` การมีจุดเดียวคือสิ่งที่ทำให้ตรวจสอบความปลอดภัยได้จริง ถ้ากระจายอยู่หลายที่จะมีที่ใดที่หนึ่งลืม

3. **Secret deny list อยู่ในชั้นเดียวกับ path safety** ปฏิเสธ .env, ไฟล์ที่ลงท้ายด้วย .pem หรือ .key, id_rsa, .npmrc, .aws เหตุผลตามเสปคคือ agent อ่าน .env แล้วกุญแจไหลเข้า context และถูกส่งไปให้ผู้ให้บริการทุกรอบถัดไป การปฏิเสธต้องอยู่ที่ชั้น tool เพราะ model ขอมาแล้วสายเกินไป

4. **edit_file ใช้ string replace ที่ต้องตรงแบบไม่กำกวม** ถ้าหาไม่เจอคืน error ถ้าเจอมากกว่าหนึ่งที่ก็คืน error ขอให้ส่ง context มามากขึ้น นี่คือวิธีที่ harness จริงใช้ และเป็นบทเรียนว่าทำไมการแทนที่แบบกำกวมคือหายนะ

5. **Shell tool มีการยืนยันตั้งแต่บรรทัดแรก** ผ่าน callback `confirm` ที่ฉีดเข้ามา ค่า default อ่าน `AGENTPATH_AUTO_APPROVE` ถ้าเป็น 1 ให้ผ่านเลย ไม่งั้นถาม `input` การมีสวิตช์นี้ตั้งแต่ต้นคือสิ่งที่ทำให้ CI รันได้และเป็นเมล็ดพันธุ์ของ permission system ภาค 3

6. **ตัด output ของ tool ทุกตัวที่ 4000 ตัวอักษร** เหตุผลคือผลลัพธ์ shell ที่ยาวมากจะกิน context จนหมด เป็นการปูทางบท 15 token economy และเป็นพฤติกรรมที่ถูกต้องอยู่แล้ว

7. **Search เขียนเองด้วย stdlib** ไม่พึ่ง ripgrep เพราะ dependency หลักต้องเหลือ httpx ตัวเดียว ใช้ `Path.rglob` กับ `re` และข้ามโฟลเดอร์อย่าง .git และ .venv กับไฟล์ binary

8. **Mock server ต้องรองรับ tool call หลายขั้นตอน** บท 11 ต้องอ่านไฟล์แล้วแก้ไฟล์ ซึ่งเป็นสองขั้น directive เดิมให้ได้ครั้งเดียว ทางแก้คืออนุญาตให้มี directive หลายอันในข้อความเดียว แล้ว mock นับจำนวน tool result ที่มีอยู่ใน history เพื่อเลือกว่าจะตอบ directive ตัวที่เท่าไร เมื่อหมดแล้วตอบเป็นข้อความ วิธีนี้เข้ากันได้กับของเดิมทั้งหมด

---

## Task 1: Mock server รองรับ tool call หลายขั้น

**Files:** Modify `src/agentpath/testing/mock_server.py`, `tests/test_mock_server.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

เพิ่มท้าย `tests/test_mock_server.py`

```python
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
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_mock_server.py -k multiple_directives -v`
Expected: FAIL เพราะตอนนี้เมื่อข้อความล่าสุดเป็น tool result mock จะตอบข้อความธรรมดาเสมอ

- [ ] **Step 3: แก้ decide ให้เดินตามลำดับ**

แทนที่ฟังก์ชัน `decide` ทั้งฟังก์ชันด้วยเวอร์ชันนี้

```python
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
```

- [ ] **Step 4: รัน test ทั้งไฟล์**

Run: `python -m pytest tests/test_mock_server.py -v`
Expected: PASS ทุกเคสรวมของเดิม

- [ ] **Step 5: รัน lesson check ของภาค 1 ให้แน่ใจว่าไม่พัง**

Run: `python ci/run_lessons.py`
Expected: All 7 lesson checks passed

- [ ] **Step 6: Commit**

```bash
git add src/agentpath/testing/mock_server.py tests/test_mock_server.py
git commit -m "feat: let the mock server answer chained tool calls"
```

---

## Task 2: Path safety และ secret deny list

**Files:** Create `src/agentpath/tools/workspace.py`, `tests/test_workspace.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_workspace.py
import pytest

from agentpath.tools.workspace import WorkspaceError, resolve_inside


def test_normal_path_resolves(tmp_path):
    target = resolve_inside(tmp_path, "notes.txt")
    assert target == (tmp_path / "notes.txt").resolve()


def test_subdirectory_is_allowed(tmp_path):
    (tmp_path / "src").mkdir()
    assert resolve_inside(tmp_path, "src/main.py").name == "main.py"


def test_parent_escape_is_refused(tmp_path):
    with pytest.raises(WorkspaceError, match="outside the workspace"):
        resolve_inside(tmp_path, "../secrets.txt")


def test_absolute_path_outside_is_refused(tmp_path):
    with pytest.raises(WorkspaceError, match="outside the workspace"):
        resolve_inside(tmp_path, "/etc/passwd")


@pytest.mark.parametrize(
    "name", [".env", ".env.local", "id_rsa", "server.pem", "secret.key", ".npmrc"]
)
def test_secret_files_are_refused(tmp_path, name):
    with pytest.raises(WorkspaceError, match="refuses to read"):
        resolve_inside(tmp_path, name)


def test_a_file_merely_containing_env_is_fine(tmp_path):
    assert resolve_inside(tmp_path, "environment.md").name == "environment.md"
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_workspace.py -v`
Expected: FAIL ด้วย ModuleNotFoundError

- [ ] **Step 3: เขียน workspace.py**

```python
"""One place that decides which paths a tool is allowed to touch.

Every file tool goes through resolve_inside. Having exactly one gate is what
makes the rule reviewable. A rule spread across four tools is a rule that one
of them will forget.
"""
from pathlib import Path

SECRET_NAMES = {".env", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "credentials"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SECRET_PREFIXES = (".env.",)


class WorkspaceError(Exception):
    """Raised when a tool asks for a path it is not allowed to have."""


def looks_like_a_secret(name: str) -> bool:
    lowered = name.lower()
    if lowered in SECRET_NAMES:
        return True
    if lowered.startswith(SECRET_PREFIXES):
        return True
    return Path(lowered).suffix in SECRET_SUFFIXES


def resolve_inside(root, path) -> Path:
    """Turn a path from the model into a real path inside root, or refuse.

    Two separate refusals happen here. The first stops the agent reaching
    outside its workspace at all, which covers both ../ escapes and absolute
    paths. The second stops it reading credential files that happen to live
    inside the workspace, because anything a tool reads is sent to the model
    provider on every later request and stays in the conversation.
    """
    root = Path(root).resolve()
    candidate = (root / Path(path)).resolve()
    if candidate != root and not candidate.is_relative_to(root):
        raise WorkspaceError(f"{path} is outside the workspace")
    if looks_like_a_secret(candidate.name):
        raise WorkspaceError(
            f"this tool refuses to read {candidate.name} because credential files "
            "must not enter the conversation"
        )
    return candidate
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `python -m pytest tests/test_workspace.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/tools/workspace.py tests/test_workspace.py
git commit -m "feat: add one gate for workspace paths and secret files"
```

---

## Task 3: File tools

**Files:** Create `src/agentpath/tools/files.py`, `tests/test_files.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_files.py
import pytest

from agentpath.tools.files import file_tools
from agentpath.tools.base import ToolRegistry
from agentpath.types import ToolCall


@pytest.fixture
def registry(tmp_path):
    (tmp_path / "a.py").write_text("print('one')\nprint('two')\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("x = 1\n", encoding="utf-8")
    return ToolRegistry(file_tools(tmp_path)), tmp_path


def call(registry, name, **arguments):
    return registry.run(ToolCall(id="1", name=name, arguments=arguments)).content


def test_read_file_returns_content(registry):
    reg, _ = registry
    assert "print('one')" in call(reg, "read_file", path="a.py")


def test_read_file_outside_workspace_is_an_error_not_a_crash(registry):
    reg, _ = registry
    assert "outside the workspace" in call(reg, "read_file", path="../x.txt")


def test_read_file_refuses_env(registry):
    reg, root = registry
    (root / ".env").write_text("KEY=secret\n", encoding="utf-8")
    result = call(reg, "read_file", path=".env")
    assert "refuses to read" in result
    assert "secret" not in result


def test_write_file_creates_and_reports(registry):
    reg, root = registry
    result = call(reg, "write_file", path="new.txt", content="hello")
    assert (root / "new.txt").read_text(encoding="utf-8") == "hello"
    assert "new.txt" in result


def test_write_file_creates_missing_directories(registry):
    reg, root = registry
    call(reg, "write_file", path="deep/nested/x.txt", content="hi")
    assert (root / "deep" / "nested" / "x.txt").exists()


def test_list_files_shows_the_tree(registry):
    reg, _ = registry
    result = call(reg, "list_files", path=".")
    assert "a.py" in result
    assert "sub" in result


def test_edit_file_replaces_exactly_once(registry):
    reg, root = registry
    result = call(reg, "edit_file", path="a.py", old="print('one')", new="print('ONE')")
    assert "print('ONE')" in (root / "a.py").read_text(encoding="utf-8")
    assert "Edited" in result


def test_edit_file_refuses_when_the_text_is_missing(registry):
    reg, _ = registry
    assert "was not found" in call(reg, "edit_file", path="a.py", old="nope", new="x")


def test_edit_file_refuses_when_the_text_is_ambiguous(registry):
    reg, root = registry
    (root / "c.py").write_text("v = 1\nv = 1\n", encoding="utf-8")
    result = call(reg, "edit_file", path="c.py", old="v = 1", new="v = 2")
    assert "appears 2 times" in result
    assert (root / "c.py").read_text(encoding="utf-8") == "v = 1\nv = 1\n"


def test_long_output_is_truncated(registry):
    reg, root = registry
    (root / "big.txt").write_text("x" * 9000, encoding="utf-8")
    result = call(reg, "read_file", path="big.txt")
    assert len(result) < 5000
    assert "truncated" in result
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_files.py -v`
Expected: FAIL ด้วย ModuleNotFoundError

- [ ] **Step 3: เขียน files.py**

```python
"""Tools that let the agent read and change files.

Each tool is a plain function plus a hand written schema, exactly like the
toy tools in lesson 03. The only new idea is that every path goes through
resolve_inside first, so the rules about what may be touched live in one
place instead of being repeated four times.
"""
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.workspace import resolve_inside

MAX_OUTPUT = 4000
SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache"}


def truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    """Keep tool output small enough that it does not eat the context window.

    A single command can produce megabytes. Everything a tool returns is sent
    back to the model on this request and every later one, so an untruncated
    result is paid for many times over.
    """
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated, {len(text) - limit} more characters]"


def file_tools(root) -> list[Tool]:
    """Build the file tools bound to one workspace directory."""
    root = Path(root).resolve()

    def read_file(path):
        target = resolve_inside(root, path)
        if not target.is_file():
            return f"Error: {path} does not exist"
        return truncate(target.read_text(encoding="utf-8", errors="replace"))

    def write_file(path, content):
        target = resolve_inside(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to {path}"

    def edit_file(path, old, new):
        target = resolve_inside(root, path)
        if not target.is_file():
            return f"Error: {path} does not exist"
        text = target.read_text(encoding="utf-8")
        found = text.count(old)
        if found == 0:
            return (
                f"Error: the text to replace was not found in {path}. "
                "Read the file again and copy the exact text including whitespace."
            )
        if found > 1:
            return (
                f"Error: the text to replace appears {found} times in {path}. "
                "Include more surrounding lines so the match is unique."
            )
        target.write_text(text.replace(old, new), encoding="utf-8")
        return f"Edited {path}"

    def list_files(path="."):
        target = resolve_inside(root, path)
        if not target.is_dir():
            return f"Error: {path} is not a directory"
        names = []
        for entry in sorted(target.iterdir()):
            if entry.name in SKIP_DIRECTORIES:
                continue
            names.append(entry.name + "/" if entry.is_dir() else entry.name)
        return truncate("\n".join(names) or "(empty directory)")

    return [
        Tool(
            name="read_file",
            description="Read a text file and return its contents.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"}
                },
                "required": ["path"],
            },
            fn=read_file,
        ),
        Tool(
            name="write_file",
            description=(
                "Write a whole file, creating it if needed. Use edit_file instead when "
                "you only want to change part of an existing file."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "content": {"type": "string", "description": "The complete new contents"},
                },
                "required": ["path", "content"],
            },
            fn=write_file,
        ),
        Tool(
            name="edit_file",
            description=(
                "Replace one exact piece of text in a file. The old text must appear "
                "exactly once, so include enough surrounding lines to make it unique."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "old": {"type": "string", "description": "The exact text to replace"},
                    "new": {"type": "string", "description": "The text to put in its place"},
                },
                "required": ["path", "old", "new"],
            },
            fn=edit_file,
        ),
        Tool(
            name="list_files",
            description="List the files and directories in one directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory relative to the workspace"}
                },
                "required": [],
            },
            fn=list_files,
        ),
    ]
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `python -m pytest tests/test_files.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/tools/files.py tests/test_files.py
git commit -m "feat: add file tools with a unique match editor"
```

---

## Task 4: Shell tool

**Files:** Create `src/agentpath/tools/shell.py`, `tests/test_shell.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_shell.py
import sys

from agentpath.tools.base import ToolRegistry
from agentpath.tools.shell import always_allow, never_allow, shell_tools
from agentpath.types import ToolCall


def run(root, command, confirm=always_allow):
    registry = ToolRegistry(shell_tools(root, confirm=confirm))
    return registry.run(ToolCall(id="1", name="run_shell", arguments={"command": command})).content


def test_command_output_comes_back(tmp_path):
    assert "hello" in run(tmp_path, f'{sys.executable} -c "print(\'hello\')"')


def test_exit_code_is_reported(tmp_path):
    result = run(tmp_path, f"{sys.executable} -c \"import sys; sys.exit(3)\"")
    assert "exit code 3" in result


def test_stderr_is_included(tmp_path):
    result = run(tmp_path, f"{sys.executable} -c \"import sys; sys.stderr.write('bad')\"")
    assert "bad" in result


def test_a_refused_command_does_not_run(tmp_path):
    marker = tmp_path / "created.txt"
    command = f"{sys.executable} -c \"open(r'{marker}', 'w').write('x')\""
    result = run(tmp_path, command, confirm=never_allow)
    assert "refused" in result
    assert not marker.exists()


def test_the_command_runs_inside_the_workspace(tmp_path):
    (tmp_path / "marker.txt").write_text("here", encoding="utf-8")
    listing = run(tmp_path, f"{sys.executable} -c \"import os; print(os.listdir('.'))\"")
    assert "marker.txt" in listing


def test_timeout_is_reported_not_raised(tmp_path):
    command = f"{sys.executable} -c \"import time; time.sleep(5)\""
    registry = ToolRegistry(shell_tools(tmp_path, confirm=always_allow, timeout=1))
    result = registry.run(
        ToolCall(id="1", name="run_shell", arguments={"command": command})
    ).content
    assert "timed out" in result


def test_long_output_is_truncated(tmp_path):
    command = f"{sys.executable} -c \"print('x' * 9000)\""
    assert "truncated" in run(tmp_path, command)
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_shell.py -v`
Expected: FAIL ด้วย ModuleNotFoundError

- [ ] **Step 3: เขียน shell.py**

```python
"""A tool that runs shell commands, with a question asked first.

The question is the whole point. A model can be talked into running
something destructive by text it read from a file, so the last gate before
anything runs is a human. In part 3 this grows into a real permission
system. Here it is deliberately one function, so you can see that the idea
is small even though it matters a lot.
"""
import os
import subprocess
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import truncate

DEFAULT_TIMEOUT = 60


def always_allow(command: str) -> bool:
    return True


def never_allow(command: str) -> bool:
    return False


def ask_the_user(command: str) -> bool:
    """Ask before running, unless the environment says not to.

    AGENTPATH_AUTO_APPROVE exists because automated runs have nobody at the
    keyboard. Without it every test and every continuous integration job
    would hang forever waiting for an answer that never comes.
    """
    if os.environ.get("AGENTPATH_AUTO_APPROVE") == "1":
        return True
    print(f"\nThe agent wants to run this command.\n\n    {command}\n")
    try:
        return input("Run it? [y/N] ").strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def shell_tools(root, confirm=ask_the_user, timeout=DEFAULT_TIMEOUT) -> list[Tool]:
    root = Path(root).resolve()

    def run_shell(command):
        if not confirm(command):
            return "The user refused to run this command. Do not try to run it again."
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=root,
                capture_output=True,
                timeout=timeout,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return f"Error: the command timed out after {timeout} seconds"
        parts = []
        if completed.stdout:
            parts.append(completed.stdout)
        if completed.stderr:
            parts.append(completed.stderr)
        if completed.returncode != 0:
            parts.append(f"[exit code {completed.returncode}]")
        return truncate("\n".join(parts) or "[no output]")

    return [
        Tool(
            name="run_shell",
            description=(
                "Run a shell command in the workspace directory and return its output. "
                "The user is asked to approve the command before it runs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line to run"}
                },
                "required": ["command"],
            },
            fn=run_shell,
        )
    ]
```

หมายเหตุเรื่อง Windows ที่ต้องอธิบายใน README ของบท 08 `shell=True` ใช้ cmd.exe บน Windows และ /bin/sh บน Unix ดังนั้นคำสั่งเดียวกันอาจใช้ไม่ได้ทั้งสองที่ ส่วน `encoding="utf-8"` กับ `errors="replace"` มีไว้เพราะ output บน Windows มักไม่ใช่ utf-8 และจะทำให้ตายด้วย UnicodeDecodeError ถ้าไม่ระบุ

- [ ] **Step 4: รันให้ผ่าน**

Run: `python -m pytest tests/test_shell.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/tools/shell.py tests/test_shell.py
git commit -m "feat: add shell tool that asks before it runs anything"
```

---

## Task 5: Search tools

**Files:** Create `src/agentpath/tools/search.py`, `tests/test_search.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

```python
# tests/test_search.py
import pytest

from agentpath.tools.base import ToolRegistry
from agentpath.tools.search import search_tools
from agentpath.types import ToolCall


@pytest.fixture
def registry(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    (tmp_path / "src" / "util.py").write_text("def helper():\n    return 2\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("start here\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "junk.py").write_text("def start():\n", encoding="utf-8")
    return ToolRegistry(search_tools(tmp_path))


def call(registry, name, **arguments):
    return registry.run(ToolCall(id="1", name=name, arguments=arguments)).content


def test_glob_finds_python_files(registry):
    result = call(registry, "glob_files", pattern="**/*.py")
    assert "src/main.py" in result.replace("\\", "/")
    assert "src/util.py" in result.replace("\\", "/")


def test_glob_skips_virtual_environments(registry):
    assert "junk.py" not in call(registry, "glob_files", pattern="**/*.py")


def test_grep_reports_file_and_line(registry):
    result = call(registry, "grep_files", pattern="def start")
    assert "main.py" in result
    assert "1" in result


def test_grep_can_be_limited_by_glob(registry):
    result = call(registry, "grep_files", pattern="start", glob="*.md")
    assert "notes.md" in result
    assert "main.py" not in result


def test_grep_reports_no_matches_clearly(registry):
    assert "no matches" in call(registry, "grep_files", pattern="zzzz").lower()


def test_a_bad_regular_expression_is_an_error_not_a_crash(registry):
    assert "not a valid" in call(registry, "grep_files", pattern="[unclosed")
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_search.py -v`
Expected: FAIL ด้วย ModuleNotFoundError

- [ ] **Step 3: เขียน search.py**

```python
"""Tools that let the agent find things instead of being told where they are.

This is the part people are surprised by. A coding agent does not need a
vector database to work on a code base. It needs the same two tools a human
uses, which are a way to find files by name and a way to find text inside
them. Lesson 16 in part 3 explains when that stops being enough.
"""
import fnmatch
import re
from pathlib import Path

from agentpath.tools.base import Tool
from agentpath.tools.files import SKIP_DIRECTORIES, truncate

MAX_RESULTS = 200


def _walk(root: Path):
    """Yield every file under root, skipping directories nobody wants searched."""
    for path in root.rglob("*"):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if path.is_file():
            yield path


def search_tools(root) -> list[Tool]:
    root = Path(root).resolve()

    def glob_files(pattern):
        matches = []
        for path in _walk(root):
            relative = path.relative_to(root).as_posix()
            if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern):
                matches.append(relative)
        if not matches:
            return f"no files match {pattern}"
        return truncate("\n".join(sorted(matches)[:MAX_RESULTS]))

    def grep_files(pattern, glob="*"):
        try:
            expression = re.compile(pattern)
        except re.error as error:
            return f"Error: {pattern} is not a valid regular expression ({error})"
        hits = []
        for path in _walk(root):
            relative = path.relative_to(root).as_posix()
            if not (fnmatch.fnmatch(relative, glob) or fnmatch.fnmatch(path.name, glob)):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if expression.search(line):
                    hits.append(f"{relative}:{number}: {line.strip()[:200]}")
                    if len(hits) >= MAX_RESULTS:
                        break
            if len(hits) >= MAX_RESULTS:
                break
        if not hits:
            return f"no matches for {pattern}"
        return truncate("\n".join(hits))

    return [
        Tool(
            name="glob_files",
            description=(
                "Find files by name pattern, for example **/*.py or test_*.py. "
                "Use this when you know roughly what a file is called."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "A glob pattern"}
                },
                "required": ["pattern"],
            },
            fn=glob_files,
        ),
        Tool(
            name="grep_files",
            description=(
                "Search the text inside files using a regular expression and return "
                "matching lines with their file name and line number."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "A regular expression"},
                    "glob": {
                        "type": "string",
                        "description": "Only search files matching this glob, for example *.py",
                    },
                },
                "required": ["pattern"],
            },
            fn=grep_files,
        ),
    ]
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `python -m pytest tests/test_search.py -v`
Expected: PASS ทุกเคส

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/tools/search.py tests/test_search.py
git commit -m "feat: add glob and grep search tools"
```

---

## Task 6: System prompt

**Files:** Create `src/agentpath/prompt.py`, `tests/test_prompt.py`

- [ ] **Step 1: เขียน test**

```python
# tests/test_prompt.py
from agentpath.prompt import build_system_prompt


def test_prompt_names_the_workspace(tmp_path):
    prompt = build_system_prompt(tmp_path)
    assert str(tmp_path) in prompt


def test_prompt_states_the_platform(tmp_path):
    assert "Platform" in build_system_prompt(tmp_path)


def test_extra_instructions_are_appended(tmp_path):
    prompt = build_system_prompt(tmp_path, extra="Always write tests first.")
    assert prompt.rstrip().endswith("Always write tests first.")
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_prompt.py -v`
Expected: FAIL ด้วย ModuleNotFoundError

- [ ] **Step 3: เขียน prompt.py**

```python
"""The system prompt.

A system prompt does two different jobs and it helps to keep them apart in
your head. The first job is telling the model who it is and how to behave.
The second is telling it facts about the world it cannot see, such as which
directory it is working in and what operating system it is on. Without the
second job the model guesses, and it guesses wrong in ways that waste turns.
"""
import platform
import sys
from pathlib import Path

BEHAVIOUR = """You are a careful software assistant working inside one directory.

Work in small steps. Look before you change anything. When you need to know
what a file contains, read it rather than guessing. When you change a file,
change the smallest amount of text that does the job.

Prefer edit_file over write_file for existing files, because write_file
replaces the whole file and loses anything you did not include.

When you are done, say what you changed in one or two sentences."""


def build_system_prompt(root, extra: str = "") -> str:
    """Assemble the system prompt for a run inside root."""
    facts = [
        f"Workspace directory {Path(root).resolve()}",
        f"Platform {platform.system()}",
        f"Python {sys.version_info.major}.{sys.version_info.minor}",
    ]
    prompt = BEHAVIOUR + "\n\nFacts about this environment\n" + "\n".join(facts)
    if extra:
        prompt += "\n\n" + extra
    return prompt
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `python -m pytest tests/test_prompt.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agentpath/prompt.py tests/test_prompt.py
git commit -m "feat: add a system prompt that states the environment"
```

---

## Task 7: ต่อ tool เข้า CLI

**Files:** Modify `src/agentpath/cli.py`, `tests/test_cli.py`

- [ ] **Step 1: เขียน test ที่ต้องแดง**

เพิ่มท้าย `tests/test_cli.py`

```python
def test_default_tool_set_covers_files_shell_and_search(tmp_path):
    from agentpath.cli import build_tools

    names = {schema["name"] for schema in build_tools(tmp_path).schemas()}
    assert names == {
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "run_shell",
        "glob_files",
        "grep_files",
    }
```

- [ ] **Step 2: รันให้เห็นว่าแดง**

Run: `python -m pytest tests/test_cli.py -k default_tool_set -v`
Expected: FAIL ด้วย ImportError

- [ ] **Step 3: แก้ cli.py**

เพิ่ม import และฟังก์ชันนี้

```python
from agentpath.prompt import build_system_prompt
from agentpath.tools.base import ToolRegistry
from agentpath.tools.files import file_tools
from agentpath.tools.search import search_tools
from agentpath.tools.shell import shell_tools


def build_tools(root):
    """Every tool the chat command gives the agent."""
    return ToolRegistry(file_tools(root) + shell_tools(root) + search_tools(root))
```

แก้ `chat` ให้รับ workspace และส่ง tool กับ system prompt เข้า Agent

```python
def chat(provider_kind: str, workspace):
    check_environment()
    root = Path(workspace).resolve()
    agent = Agent(
        provider=build_provider(provider_kind),
        tools=build_tools(root),
        system=build_system_prompt(root),
    )
    print(f"Working in {root}")
    print("Type a message. Press Ctrl+C to leave.")
    ...
```

แก้ `main` ให้มี argument ใหม่

```python
    chat_parser.add_argument(
        "--workspace",
        default=".",
        help="Directory the agent is allowed to work in. Defaults to the current directory.",
    )
    ...
    if arguments.command == "chat":
        return chat(arguments.provider, arguments.workspace)
```

อย่าลืม `from pathlib import Path` ที่หัวไฟล์

- [ ] **Step 4: รัน test ทั้งหมดให้ผ่าน**

Run: `python -m pytest -q`
Expected: PASS ทั้ง suite

- [ ] **Step 5: ลองใช้จริง**

เปิด mock server แล้วรัน

```bash
agentpath chat --workspace .
```

Expected: บรรทัด Working in แสดง path ที่ถูกต้อง

- [ ] **Step 6: Commit**

```bash
git add src/agentpath/cli.py tests/test_cli.py
git commit -m "feat: give the chat command real tools and a system prompt"
```

---

## Task 8 ถึง 12: บทเรียน 07 ถึง 11

ทุกบทใช้รูปแบบเดียวกับภาค 1 คือไฟล์แบนๆ ในโฟลเดอร์บท ไม่ import package
โค้ดคัดลอกต่อกันมาจากบทก่อนหน้า และมี check.py ที่รันกับ mock server ได้

### Task 8: Lesson 07 file tools

**Files:** `lessons/07-file-tools/` มี `providers.py`, `tools.py`, `agent.py`, `check.py`, `README.md`

- [ ] **Step 1: คัดลอกฐานจากบท 06**

```bash
mkdir -p lessons/07-file-tools
cp lessons/06-provider-abstraction/providers.py lessons/07-file-tools/providers.py
cp lessons/06-provider-abstraction/agent.py lessons/07-file-tools/agent.py
```

- [ ] **Step 2: เขียน tools.py ใหม่ทั้งไฟล์**

เนื้อหาคือ path safety, secret deny list, truncate, และ tool สี่ตัว read_file write_file
edit_file list_files เขียนเป็นสไตล์เดียวกับ `src/agentpath/tools/files.py` แต่ใช้ dict
schema แบบ OpenAI เหมือน `lessons/03-tool-calling/tools.py` และมี `WORKSPACE` เป็นตัวแปร
ระดับโมดูลที่ check.py ตั้งค่าได้ เหตุผลที่ไม่ใช้ factory function ในบทเรียนคือผู้เรียน
ยังไม่ต้องเจอ closure ในบทนี้

- [ ] **Step 3: เขียน check.py**

check ต้องพิสูจน์สี่อย่าง อ่านไฟล์ได้, แก้ไฟล์แล้วไฟล์บนดิสก์เปลี่ยนจริง, path ที่ออก
นอก workspace ถูกปฏิเสธ, และ .env ถูกปฏิเสธโดยเนื้อหาไม่หลุดออกมา ใช้ `tempfile`
สร้าง workspace ชั่วคราว

- [ ] **Step 4: ยืนยัน**

Run: `cd lessons/07-file-tools && AGENTPATH_BASE_URL=http://127.0.0.1:8765/v1 AGENTPATH_MODEL=mock python check.py`
Expected: OK ทุกบรรทัด

- [ ] **Step 5: เขียน README.md** ตามหัวข้อในส่วน Lesson content ด้านล่าง

- [ ] **Step 6: Commit**

### Task 9: Lesson 08 shell tool

**Files:** `lessons/08-shell-tool/` คัดลอกจากบท 07 แล้วเพิ่ม `run_shell` เข้า tools.py

- [ ] ต้องมีการยืนยันตั้งแต่บรรทัดแรก และข้ามได้ด้วย `AGENTPATH_AUTO_APPROVE=1`
- [ ] check.py พิสูจน์สามอย่าง คำสั่งรันได้และได้ output กลับมา, คำสั่งที่ถูกปฏิเสธไม่ถูกรันจริง โดยตรวจว่าไฟล์ที่คำสั่งจะสร้างไม่มีอยู่, และ timeout รายงานเป็นข้อความไม่ใช่ exception
- [ ] README ต้องมีหัวข้อ Windows ที่อธิบาย cmd.exe กับ /bin/sh, path separator, และ encoding ของ output

### Task 10: Lesson 09 search tools

**Files:** `lessons/09-search-tools/` เพิ่ม `glob_files` และ `grep_files`

- [ ] check.py พิสูจน์ว่า glob หาไฟล์เจอ, grep รายงานชื่อไฟล์กับเลขบรรทัด, และ .venv ถูกข้าม
- [ ] README ต้องอธิบายว่าทำไม coding agent ใช้ grep แทน vector search และชี้ไปบท 16

### Task 11: Lesson 10 anatomy of a prompt

**Files:** `lessons/10-anatomy-of-a-prompt/` เพิ่ม `prompt.py` และแก้ agent.py ให้รับ system prompt

- [ ] check.py พิสูจน์ว่า system prompt เป็น message แรกและมี path ของ workspace อยู่จริง
- [ ] README ต้องครอบคลุมสามที่ที่ข้อความไปถึง model คือ system prompt, user message, และ description ของ tool พร้อมย้ำว่า description ของ tool คือ prompt engineering ที่คนมองข้ามที่สุด

### Task 12: Lesson 11 milestone mini coding agent

**Files:** `lessons/11-mini-coding-agent/` ประกอบทุกอย่างเข้าด้วยกันเป็น CLI ชื่อ `main.py`

- [ ] มี tool ครบเจ็ดตัวจากบท 07 ถึง 09 บวก system prompt จากบท 10
- [ ] check.py ต้องเป็นการพิสูจน์แบบ end to end จริง สร้างโฟลเดอร์ชั่วคราวที่มีไฟล์ Python ที่มี bug ใส่ prompt ที่มี directive สองขั้นคือ read_file แล้ว edit_file แล้วยืนยันว่าไฟล์บนดิสก์เปลี่ยนจริง นี่คือจุดที่ Task 1 ของแผนนี้จำเป็น
- [ ] README เป็นบท milestone สรุปว่าผู้เรียนมีอะไรแล้ว และชี้ว่าอะไรยังขาด ซึ่งคือ permission ที่จำได้ว่าเคยอนุญาตอะไร, session ที่กลับมาทำต่อได้, และการจัดการ context ที่ยาวเกิน ทั้งหมดคือภาค 3

---

## Lesson content requirements

ทุก README ต้องตามกฎภาษาในเสปคคือ ห้าม em-dash ห้าม emoji ห้าม colon ในร้อยแก้ว
และต้องตอบครบสามคำถามคือมันคืออะไร ทำทำไม ทำไมต้องวิธีนี้ หัวข้อบังคับของแต่ละบท

**บท 07** ปัญหาที่ค้างจากบท 06 คือ agent ยังแตะโลกจริงไม่ได้ / path safety และทำไม
ต้องมีประตูเดียว / ทำไม edit_file ต้องบังคับให้ข้อความตรงแบบไม่กำกวม พร้อมตัวอย่าง
ความหายนะเมื่อแทนที่โดนหลายที่ / ทำไม write_file อันตรายกว่า edit_file / secret deny list
และเหตุผลว่าอะไรที่ tool อ่านจะถูกส่งไปให้ผู้ให้บริการทุกรอบถัดไปและอยู่ในบทสนทนาตลอด
/ การตัด output และทำไมมันสำคัญกับ token

**บท 08** ปัญหาที่ค้าง / subprocess และ shell=True / ทำไมต้องถามก่อนรัน โดยเชื่อมกับ
prompt injection ว่าไฟล์ที่ agent อ่านมาอาจมีข้อความสั่งให้ทำอย่างอื่น / AGENTPATH_AUTO_APPROVE
มีไว้ทำไมและทำไมมันไม่ใช่ช่องโหว่ / timeout / ความต่างของ Windows

**บท 09** ปัญหาที่ค้าง / glob กับ grep คืออะไร / ทำไม coding agent จริงใช้วิธีนี้แทน
vector search และชี้ไปบท 16 / ทำไมต้องข้าม .git และ .venv / ทำไมต้องจำกัดจำนวนผลลัพธ์

**บท 10** สามที่ที่ข้อความไปถึง model / อะไรควรอยู่ที่ไหน / description ของ tool คือ prompt
engineering / ทำไมต้องบอก model ว่าอยู่ directory ไหนและ OS อะไร / ทำไม system prompt
ที่ยาวเกินไปทำร้ายมากกว่าช่วย

**บท 11** เป็นบท milestone ประกอบของ ไม่มีแนวคิดใหม่ ให้เน้นการเดินดูโค้ดทั้งหมดที่
ผู้เรียนเขียนมาแล้วและชี้ให้เห็นว่า agent loop ไม่เคยเปลี่ยนเลยตั้งแต่บท 04 ซึ่งคือหลักฐาน
ว่า design ถูก

---

## Task 13: Thai translations

- [ ] แปลบท 07 ถึง 11 เป็น `README.th.md` และใส่ลิงก์สลับภาษาทั้งสองทาง
- [ ] กฎเดียวกับภาค 1 คือศัพท์เทคนิคคงภาษาอังกฤษ โค้ดไม่แปล

## Task 14: Release v0.2

- [ ] อัปเดต `README.md` และ `README.th.md` ตารางภาค 2 เป็น Available now และเพิ่มรายการบท 07 ถึง 11
- [ ] เปลี่ยน version ใน `pyproject.toml` เป็น 0.2.0 และใน `src/agentpath/__init__.py`
- [ ] รันครบสี่อย่าง `ruff check .` และ `python ci/prose_lint.py` และ `pytest -q` และ `python ci/run_lessons.py`
- [ ] `uv build` แล้วทดสอบติดตั้งใน environment สะอาด
- [ ] tag `v0.2.0`

---

## Self-Review

**Spec coverage** บท 07 ถึง 11 ครบตามเสปค หัวข้อย่อยบังคับของบท 07 เรื่อง .env อยู่ใน
Task 2 และ 3 หัวข้อ Windows ของบท 08 อยู่ใน Task 4 และ 9 หัวข้อ description ของ tool
คือ prompt engineering อยู่ใน Task 11

**สิ่งที่ไม่อยู่ใน v0.2 โดยตั้งใจ** permission ที่จำการอนุญาตได้, session, context management,
token economy, retrieval ทั้งหมดเป็นภาค 3 การยืนยันในบท 08 เป็นแค่คำถามใช่หรือไม่
ไม่มีการจำ

**Type consistency** `truncate` และ `SKIP_DIRECTORIES` นิยามใน `files.py` แล้วถูก import
ไปใช้ใน `shell.py` และ `search.py` ชื่อ tool ทั้งเจ็ดตัวตรงกันระหว่าง Task 3 4 5 และ 7

**ความเสี่ยงที่รู้ตัว** test ของ shell tool เรียก `sys.executable` เพื่อให้ทำงานได้ทั้ง
Windows และ Unix โดยไม่ต้องพึ่งคำสั่งของระบบปฏิบัติการ ถ้า CI บน Windows ยังพัง
ให้ดูเรื่อง quoting ของ path ที่มีช่องว่างเป็นอันดับแรก
