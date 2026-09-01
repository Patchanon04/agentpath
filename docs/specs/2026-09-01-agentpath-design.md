# agentpath Design Document

วันที่ 2026-09-01 | สถานะ รอผู้ใช้อนุมัติ

## 1. โปรเจกต์คืออะไร

โปรเจกต์ open source สอนคนที่ไม่รู้อะไรเลยให้สร้าง AI agent และ harness ด้วยตัวเอง
รูปแบบคือ tutorial เป็นบทเรียนตามลำดับ และผลลัพธ์สุดท้ายของบทเรียนคือ framework
ตัวจริงชื่อ `agentpath` ที่ pip install ใช้งานได้

- ชื่อโปรเจกต์ `agentpath` (ตรวจแล้ว PyPI ว่าง, GitHub แทบไม่มีคู่แข่ง)

ทำไมต้องมีอันนี้ในเมื่อ tutorial สอน agent มีเป็นสิบ เพราะเกือบทั้งหมดหยุดที่ agent loop
แต่ของจริงที่คนใช้ (Claude Code, OpenHands) คือ harness ที่มี permission, session,
context management, MCP ซึ่งแทบไม่มีใครสอนสร้าง โปรเจกต์นี้พาไปถึงตรงนั้น
และมีฉบับภาษาไทยซึ่งแทบไม่มีในตลาด
- Tagline: "Learn how AI agents actually work by building a real one, from a single LLM call to a full agent harness."
- ภาษาโปรแกรม Python
- เนื้อหาอังกฤษเป็นหลัก แปลไทยตอน ship แต่ละภาค
- License MIT

## 2. หลักการที่คุมทุกการตัดสินใจ

1. **ความเข้าใจของผู้เรียนชนะทุกอย่าง** ชนะ performance ชนะความเท่ ชนะ best practice ระดับ production
2. **ไม่มีเวทมนตร์** ผู้เรียนต้องเห็นไส้ในทุกชั้น เขียน HTTP call เอง เขียน JSON schema เอง ไม่พึ่ง SDK ของ provider
3. **agentpath คือ reference implementation ที่คุณสร้างเองได้ ไม่ใช่คู่แข่ง LangGraph** ทุก feature ต้องตอบได้ว่าสอนอะไร ตอบไม่ได้เท่ากับปฏิเสธ นี่คือเกราะกัน scope creep ถาวรของโปรเจกต์
4. **ทุกบทจบด้วยของที่รันได้จริง** ไม่มีบทไหนจบครึ่งๆ กลางๆ
5. **โค้ดไม่มี check คือโค้ดยังไม่เสร็จ** ทุกบทมี `check.py` ให้ผู้เรียนรันยืนยันว่าของที่สร้างทำงาน และ CI รันไฟล์เดียวกันนี้

## 3. กฎการเขียนเนื้อหา

- อธิบายละเอียดสุดๆ ทุกหัวข้อต้องตอบครบสามคำถาม มันคืออะไร ทำทำไม เพราะอะไรถึงเลือกวิธีนี้ไม่ใช่วิธีอื่น ห้ามโยนโค้ดใส่ผู้อ่านโดยไม่อธิบายที่มา
- ห้ามใช้ em-dash ห้ามใช้ colon ห้ามใช้ emoji ในร้อยแก้วทุกอย่างที่ผู้เรียนอ่าน ครอบคลุม README บทเรียน docs และ comment ในโค้ด lesson ทั้ง EN และ TH ยกเว้น string ในโค้ดที่จำเป็นเชิง syntax
- เนื้อหาบทอยู่ใน README ของโฟลเดอร์บทนั้น อ่านบน GitHub ได้ทันที ไม่แยกไปเว็บอื่น

## 4. โครง repo

แนวทาง snapshot ต่อบท ทุกบทมีโค้ดสมบูรณ์ของตัวเอง รันได้ทันที ผู้เรียนเทียบ diff
ระหว่างบทได้ ยอมรับโค้ดซ้ำเพราะมันคือ feature ของสื่อการสอน

```
agentpath/
├── README.md               pitch + สารบัญบทเรียน + quickstart
├── lessons/
│   ├── 00-setup/
│   │   ├── README.md       เนื้อหาบท (EN)
│   │   ├── README.th.md    ฉบับไทย
│   │   ├── llm.py          โค้ด ณ จุดจบบทนี้ เป็นไฟล์แบนๆ ไม่ใช่ package
│   │   ├── agent.py
│   │   └── check.py        ผู้เรียนรันยืนยันว่าของที่สร้างทำงาน
│   └── ...
├── src/agentpath/          framework ตัวเต็ม (pip install agentpath)
├── tests/                  test ของ framework ตัวเต็ม
├── ci/                     mock server + script รันทุก lesson (อยู่นอก lesson folders)
├── docs/                   ภาพรวม, roadmap, contributing, specs (EN/TH)
└── pyproject.toml          uv + ruff
```

โค้ดในโฟลเดอร์บทเรียนเป็นไฟล์แบนๆ ไม่ทำเป็น package ชื่อ `agentpath` เพราะจะชนกับ
package ตัวจริงที่ผู้เรียนอาจ pip install ไว้แล้ว ผลของการชนคือ `import agentpath`
ได้โค้ดคนละตัวขึ้นกับว่ารันจากโฟลเดอร์ไหน โดยไม่มี error เตือน ซึ่งเป็นความผิดพลาด
เงียบๆ ที่มือใหม่แก้เองไม่ได้ ผู้เรียนจึง import ตรงๆ แบบ `from agent import Agent`

### สัญญาระดับโปรเจกต์ เรื่อง configuration

โค้ดทุกบทและ framework ตัวเต็มอ่านค่าเชื่อมต่อจาก environment variable สามตัวเท่านั้น

- `AGENTPATH_BASE_URL` ปลายทาง API
- `AGENTPATH_API_KEY` กุญแจ (ค่าว่างได้ถ้าใช้ Ollama)
- `AGENTPATH_MODEL` ชื่อ model

ห้าม hardcode URL หรือกุญแจในโค้ดบทเรียนเด็ดขาด เหตุผลมีสองชั้น ชั้นแรกคือ CI
ต้องชี้โค้ดทุกบทไปที่ mock server ได้โดยไม่แก้โค้ด ถ้าฝัง URL ไว้ระบบ CI ทั้งหมด
ที่ออกแบบไว้จะใช้ไม่ได้เลย ชั้นที่สองคือมันเป็นบทเรียนเรื่องการไม่ผูกความลับไว้กับโค้ด

การตัดสินใจที่ปฏิเสธไปแล้ว

- ไม่ใช้ git tags ต่อบท เพราะคนเริ่มต้นงง git checkout และแก้บทเก่าต้อง rewrite history
- ไม่แยก 2 repo เพราะ sync กันคือฝันร้าย
- ไม่สร้าง tooling sync โค้ดข้าม lesson folders ตอนนี้ แก้ bug ต้อง propagate มือ CI จับพัง พอเจ็บจริงค่อยสร้าง

## 5. หลักสูตร (24 บท 4 ภาค)

หนึ่งภาคเท่ากับหนึ่ง release มีคุณค่าจบในตัว ป้องกันโปรเจกต์ตายกลางทาง

### ภาค 1 Foundations (v0.1)

| บท | เนื้อหา |
|----|---------|
| 00 setup | ติดตั้ง Python/uv, หา API key, ลง Ollama, env var ครอบคลุม Windows/Mac/Linux ระบุ model ที่ tool calling ใช้ได้จริง (qwen3, llama3.1-8b ขึ้นไป) และ free tier cloud (Groq, OpenRouter) เป็นทางสายกลาง นี่คือด่านที่คนเลิกเยอะสุด ต้องเป็นบทเต็ม check.py ของบทนี้ตรวจ Python version และตรวจว่า endpoint ที่ระบุใน `AGENTPATH_BASE_URL` ตอบกลับได้ ไม่ผูกกับ Ollama โดยเฉพาะ เพื่อให้ CI ชี้ไป mock server แล้วผ่านเหมือนกัน |
| 01 first LLM call | ยิง OpenAI-compatible API ตรงๆ ด้วย httpx เห็น request/response ดิบ เข้าใจว่า LLM คือ text in, text out |
| 02 conversation loop | เก็บ history, chat CLI โต้ตอบได้ |
| 03 tool calling | เขียน JSON schema ด้วยมือ, LLM ขอเรียก tool, เรารันแล้วส่งผลกลับ ใช้ toy tools (เครื่องคิดเลข, ทอยลูกเต๋า, mock weather) เพราะผลลัพธ์คาดเดาได้ ผู้เรียนโฟกัสกลไก มีหัวข้อ "ถ้า model ไม่ยอมเรียก tool" เป็นบทเรียนไม่ใช่ bug |
| 04 agent loop | วน tool call จนงานเสร็จ agent ตัวจริงตัวแรก |
| 05 streaming | เปลี่ยน loop เป็น streaming ตอนโค้ดยังเล็ก การรื้อครั้งนี้คือบทเรียนว่าทำไม design ต้องเผื่อ streaming บทนี้ยากสุดของภาค 1 ต้องแบ่งสองขยัก stream ข้อความก่อน แล้วค่อย stream tool call (arguments มาเป็นเศษ JSON ต้องสะสมเอง) หมายเหตุ implementation ต้อง verify พฤติกรรม streaming + tools ของ Ollama เป็นงานแรกๆ ถ้าไม่สมบูรณ์ให้มี fallback ไม่ stream ตอนมี tools |
| 06 provider abstraction | อยากใช้ Claude แต่ schema ไม่เหมือน จึงต้อง abstract ออกแบบ interface โดยมี streaming อยู่ในนั้นตั้งแต่แรก รองรับ OpenAI-compat + native Anthropic |

เหตุผลที่ภาค 1 ใช้ OpenAI-compatible API เพราะ Ollama, OpenRouter, Groq, OpenAI
ใช้ format เดียวกัน เปลี่ยนแค่ base URL คนไม่มีบัตรเครดิตรัน Ollama ได้ตั้งแต่บรรทัดแรก

เหตุผลที่ streaming มาก่อน abstraction เพราะถ้า abstraction มาก่อนจะต้อง retrofit
streaming เข้าสอง provider เท่ากับรื้อสองรอบ

### ภาค 2 Real Tools (v0.2)

| บท | เนื้อหา |
|----|---------|
| 07 file tools | read, write, list, และ edit แบบ string replace พร้อม path safety เหตุผลที่ต้องมี edit เพราะให้ agent เขียนไฟล์ทั้งไฟล์เพื่อแก้บรรทัดเดียวคือหายนะ และ harness จริงทุกตัวใช้วิธีนี้ |
| 08 shell tool | subprocess, timeout, จับ output มีคำถามยืนยันก่อนรันตั้งแต่วันแรก บรรทัดเดียวปลอดภัยทันที และ foreshadow permission system ภาค 3 ฟังก์ชันยืนยันต้องข้ามได้ด้วย `AGENTPATH_AUTO_APPROVE=1` ตั้งแต่บทนี้ ไม่งั้น check.py ใน CI จะเจอ EOFError เพราะไม่มีใครพิมพ์ตอบ และตัวสวิตช์นี้คือเมล็ดพันธุ์ของ permission mode ในภาค 3 |
| 09 search tools | glob + grep ให้ agent หาโค้ดเจอ |
| 10 anatomy of a prompt | อะไรควรอยู่ใน system prompt อะไรควรอยู่ใน user message และอะไรควรอยู่ใน description ของ tool ประเด็นสำคัญคือ description ของ tool ก็คือ prompt engineering เหมือนกัน คนส่วนใหญ่มองข้าม รวมเรื่อง environment info ที่ agent ต้องรู้ เช่น cwd, OS, วันที่ |
| 11 milestone: mini coding agent | ประกอบทุกอย่าง agent ที่แก้โค้ดในโฟลเดอร์ได้จริง |

### ภาค 3 The Harness (v0.3)

| บท | เนื้อหา |
|----|---------|
| 12 permission system | ask/allow/deny ก่อนรัน tool อันตราย รวมหัวข้อ prompt injection พื้นฐาน ทำไมต้องถามก่อนรัน shell |
| 13 sessions | บันทึก/resume เป็น JSONL ธรรมดา |
| 14 context management | truncate/summarize เมื่อบทสนทนายาวเกินหน้าต่าง |
| 15 token economy | ทำไมบทสนทนาเดิมถึงแพงขึ้นเรื่อยๆ และลดยังไง เรียงตามผลกระทบจริง prompt caching และกฎว่าของนิ่งต้องอยู่หน้า ของเปลี่ยนต้องอยู่ท้าย ไม่งั้น cache พังทุกรอบ, การตัด output ของ tool ก่อนส่งกลับ, การอ่านไฟล์เฉพาะช่วงแทนทั้งไฟล์, การใช้ model ถูกกับงานย่อย, การไม่ส่ง tool schema ที่ไม่ได้ใช้ |
| 16 retrieval and when not to use it | บทที่สอนการตัดสินใจ ไม่ใช่บทสอนทำ vector database ลำดับคำถามสี่ข้อ ข้อมูลเล็กพอใส่ context ไหม, มีโครงสร้างและรู้ query ไหมให้ใช้ SQL, เป็น text ที่ agent เดินหาเองได้ไหมให้ใช้ grep ซึ่งคือบท 09 ที่สร้างไปแล้ว, ถ้าไม่เข้าสามข้อแรกจริงๆ ค่อยใช้ vector search อธิบายว่าทำไม coding agent ที่คนใช้จริงเกือบไม่ใช้ vector RAG และลงมือทำ retrieval เป็น tool ตัวหนึ่งเพื่อให้เห็นว่ามันไม่ใช่ระบบพิเศษอะไร |
| 17 errors & retries | API ล่ม, tool พัง, rate limit |
| 18 milestone: the harness | CLI จริงจัง `agentpath` (chat, run, resume) ประกอบทุกระบบ |

### ภาค 4 Advanced (v1.0)

| บท | เนื้อหา |
|----|---------|
| 19 MCP client | เขียน MCP client แบบ sync เอง (stdio เท่านั้น) |
| 20 subagents | agent spawn agent |
| 21 multi-agent | orchestrator, parallel workers ผ่าน thread + queue |
| 22 evals and choosing a model | task runner + LLM-as-judge, mock server ช่วยทดสอบฟรี และรวมเรื่องการเลือก model ไว้ที่นี่เพราะหลักคือเลือกด้วยการวัดไม่ใช่ด้วยความรู้สึก การบอกว่า model ไหนดีกว่าโดยไม่มีชุดทดสอบคือการเดา ครอบคลุมการแบ่ง tier ตามงาน งานถูกอย่างจัดหมวดหรือสรุปไม่ต้องใช้ตัวแพงสุด |
| 23 ship it | packaging, ต่อยอด, ทิศทางถัดไป |

โครงภาค 4 หลวมได้ ship ทีละภาคอยู่แล้ว ถึงตอนนั้นค่อยแตกบทถ้าแน่นไป

โครงสร้างทุกบท เริ่มด้วยปัญหาที่บทก่อนยังแก้ไม่ได้ แล้วสร้าง แล้วรันเห็นผล
แล้วจบด้วยโค้ดสมบูรณ์ + check.py ในโฟลเดอร์บทนั้น

## 6. สถาปัตยกรรม src/agentpath

หลักการ ทุกบทชี้ได้ว่าสร้างไฟล์ไหนใน framework ตัวเต็ม (ไฟล์โครงสร้างอย่าง types.py,
cli.py, mock_server.py โตข้ามหลายบท ไม่นับเป็น 1:1)

```
src/agentpath/
├── types.py            ข้อมูลกลาง (Message, ToolCall, ToolResult, Event) เป็น dataclasses
├── providers/
│   ├── base.py         Provider interface, streaming เป็น default
│   ├── openai_compat.py  OpenAI, Ollama, Groq, OpenRouter
│   └── anthropic.py
├── tools/
│   ├── base.py         นิยาม tool + registry, JSON schema เขียนมือ
│   ├── files.py        read, write, edit, list
│   ├── shell.py
│   └── search.py       glob, grep
├── agent.py            agent loop ตัวเดียวใช้ทุกที่
├── permissions.py      ask/allow/deny
├── session.py          JSONL ใน ~/.agentpath/sessions/
├── context.py          truncate/summarize (รับ provider เป็น argument)
├── mcp.py              MCP client sync, stdio เท่านั้น (~100 บรรทัด)
├── subagent.py         thread + queue.Queue รวม event stream
├── evals/              task runner + LLM judge
├── testing/
│   └── mock_server.py  mock LLM (stdlib http.server) สำหรับ CI และผู้เรียน
│                       เป็น component จริงที่โตตามหลักสูตร ดูรายละเอียดท้ายข้อนี้
└── cli.py              argparse (chat, run, resume)
```

### การตัดสินใจสถาปัตยกรรม

1. **sync ทั้ง codebase** streaming ใช้ generator ธรรมดา (httpx รองรับ) subagent
   ขนานใช้ thread เหตุผลคือ async คือกำแพงสูงมากสำหรับคนไม่รู้อะไรเลย
   ความเข้าใจง่ายชนะ performance บทท้ายมีหัวข้ออธิบายว่า harness จริงใช้ async
   เพราะอะไร ถ้าจะ scale ต้องแปลงตรงไหน

2. **Agent loop เป็น event stream ขาออกอย่างเดียว** yield event
   (text_delta, tool_call_request, tool_result, turn_done) แล้ว CLI วาดจอ
   ทำให้ streaming, subagent, eval ใช้ loop ตัวเดียวกันโดยไม่แก้ไส้ใน

3. **Permission เป็น callback ฉีดเข้า Agent** ตอนสร้าง CLI ฉีดฟังก์ชันถามผู้ใช้จริง
   eval ฉีด allow ทุกอย่าง test ฉีด deny ทุกอย่าง event ยังเป็นขาออกล้วน

4. **Dependency หลักตัวเดียวคือ httpx** ไม่ใช้ pydantic (ขัดธีมไม่มีเวทมนตร์
   ใช้ dataclasses จาก stdlib) ไม่ใช้ typer/click (argparse พอ) ไม่ใช้ mcp SDK
   (เขียน JSON-RPC stdio client เองร้อยบรรทัด ส่วนที่ใช้จริงมีแค่ initialize,
   tools/list, tools/call) ข้อจำกัดที่ประกาศตรงๆ คือ v1 ไม่รองรับ MCP แบบ
   HTTP transport

5. **State เป็นไฟล์ธรรมดา** JSONL เปิดอ่านด้วยตาเปล่าได้ เห็นว่าความจำของ agent
   คือ list ของ message

6. **ณ จุด ship แต่ละภาค src/agentpath เท่ากับสถานะจบบทล่าสุดของภาคนั้น**
   ไม่ใส่ของล้ำอนาคต

7. **mock_server.py เป็น component จริงที่โตตามหลักสูตร** ไม่ใช่ script แปะข้าง
   ความสามารถที่ต้องมีตามบทที่มาถึง
   - ภาค 1 ตอบ OpenAI-compat ทั้งแบบปกติและ SSE streaming รวม tool call
     และตอบ dialect ของ Anthropic ด้วย (ไม่งั้น check บท 06 ทดสอบ abstraction ไม่ได้จริง)
   - ภาค 3 สั่งจำลอง failure ได้ (rate limit, 500, timeout) ผ่าน request header
     ไม่งั้นบท 15 errors & retries ไม่มีอะไรตรวจ
   - ภาค 4 โผล่เป็นเนื้อหาในบท evals ให้ผู้เรียนทดสอบ agent โดยไม่เสียเงิน

## 7. CI

GitHub Actions สี่งาน รันบน matrix Ubuntu + Windows (กลุ่มเป้าหมายใช้ Windows เยอะ)

1. ruff ตรวจโค้ดทุกโฟลเดอร์
2. รัน check.py ของทุก lesson ต่อ mock server แบบ deterministic ไม่ยิง API จริง
   ไม่ต้องมี secret ไม่เสียเงิน fork/PR รันได้ CI ทำได้เพราะตั้ง `AGENTPATH_BASE_URL`
   ชี้ไป mock server และตั้ง `AGENTPATH_AUTO_APPROVE=1`
3. pytest ของ src/agentpath
4. prose lint หา em-dash และ emoji ในไฟล์ md ทุกไฟล์แล้ว fail ถ้าเจอ เพราะกฎแบบนี้
   คนลืมแน่นอน ต้องให้เครื่องบังคับ (เสปคฉบับแรกก็ละเมิดกฎตัวเองมาแล้ว)

โค้ด CI กับ mock server อยู่ที่ `ci/` ระดับ root โฟลเดอร์บทเรียนมีแต่ของที่ผู้เรียนพิมพ์เอง
(check.py อยู่ในโฟลเดอร์บทเพราะผู้เรียนเป็นคนรันเอง)

## 8. แผนการ ship

| Release | เนื้อหา |
|---------|---------|
| v0.1 | ภาค 1 + publish package ขึ้น PyPI ทันทีเพื่อจองชื่อ (เราเห็นแล้วว่า agentcraft โดนตัดหน้า) |
| v0.2 | ภาค 2 |
| v0.3 | ภาค 3 |
| v1.0 | ภาค 4 |

แต่ละภาคคือ GitHub release จริง มี tag, changelog v0.1 ต้องรีบปล่อยเพื่อทดสอบว่า
มีคนสนใจจริงก่อนลงแรงที่เหลือ

การแปล อังกฤษคือ source of truth เขียนก่อน แปลไทยเป็นงานปิดท้ายก่อน ship แต่ละภาค

## 9. สิ่งที่ตัดสินใจว่าไม่ทำ (บันทึกกันเถียงซ้ำ)

- ไม่ทำ TypeScript ควบ Python (งาน x2 ทุกบท)
- ไม่มีบทสอนสร้าง vector database หรือ RAG pipeline แบบเต็มรูปแบบ บทที่ 16 สอนการตัดสินใจว่าเมื่อไหร่ต้องใช้อะไร และลงมือทำ retrieval เป็น tool ตัวหนึ่งเท่านั้น เหตุผลคือหลักการข้อ 3 บทที่สอน vector database จะกลายเป็นการแข่งกับ tutorial RAG ที่มีเป็นร้อย และไม่ตอบว่าสอนอะไรที่ harness ต้องรู้
- ไม่แข่ง feature กับ production framework (หลักการข้อ 3)
- ไม่รองรับ MCP HTTP transport ใน v1
- ไม่ทำ async (จนกว่าจะมีเหตุผลเชิงการสอน)
- ไม่สร้าง tooling sync ข้าม lesson folders จนกว่าจะเจ็บจริง
- ไม่ทำเว็บไซต์แยก เนื้อหาอยู่บน GitHub ล้วน
