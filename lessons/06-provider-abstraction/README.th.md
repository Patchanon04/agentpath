[Read in English](README.md)

# Lesson 06. Provider abstraction

นี่คือบทสุดท้ายของภาคหนึ่ง และเป็นบทแรกที่คุณจะเปลี่ยนรูปร่างของโค้ดที่ทำงานได้อยู่แล้ว
โดยไม่เพิ่มฟีเจอร์ใหม่ที่ผู้ใช้มองเห็นแม้แต่อย่างเดียว

เมื่อจบบทนี้ คุณจะมี agent loop เดียวที่คุยกับ HTTP API สองตัวที่ต่างกันโดยสิ้นเชิงได้
และคุณจะได้รัน prompt เดียวกันผ่านทั้งสองตัวแล้วได้คำตอบเหมือนกัน
โดยที่ไม่มีอะไรใน loop รู้เลยว่าใช้ตัวไหน

ไฟล์ในโฟลเดอร์นี้

```text
lessons/06-provider-abstraction/
  tools.py       unchanged from lesson 03, the toy tools and their schemas
  providers.py   two classes that speak two dialects behind one method
  agent.py       the lesson 05 loop, now handed a provider instead of importing one
  check.py       runs the same prompt through both providers
  README.md      this file
```

## 1. ปัญหาที่ค้างมาจาก lesson 05

ดูส่วนบนของ `lessons/05-streaming/agent.py`

```python
import tools
from llm import complete_stream


def run(user_input, max_turns=10):
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete_stream(
            messages, tools.SCHEMAS, on_text=lambda piece: print(piece, end="", flush=True)
        )
```

บรรทัด `from llm import complete_stream` คือปัญหาทั้งหมดในแปดคำ
loop ไม่ได้ขอวิธีคุยกับ model แต่ยื่นมือไปคว้าวิธีเฉพาะวิธีหนึ่งมาเลย เรียกด้วยชื่อ ตอน import
สำหรับไฟล์นี้ โลกนี้มี `complete_stream` อยู่แค่ตัวเดียวเท่านั้น

ทีนี้เปิด `lessons/05-streaming/llm.py` แล้วสังเกตว่ามีส่วนไหนบ้างที่ไม่ได้ทั่วไปเลย

```python
    payload = {"model": model, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools

    with httpx.Client(timeout=120) as client:
        with client.stream(
            "POST", f"{base_url}/chat/completions", json=payload, headers=headers
        ) as response:
            ...
                delta = json.loads(data)["choices"][0].get("delta", {})
```

มีข้อสมมติสี่ข้อฝังอยู่ในโค้ดชุดนั้น และทุกข้อผิดสำหรับ provider จริงบางตัวที่คุณอาจอยากใช้ในวันพรุ่งนี้

- path คือ `/chat/completions`
- คำตอบเป็น JSON object ที่มี list ชื่อ `choices`
- สมาชิกตัวแรกของ list นั้นมี object ชื่อ `delta`
- ชิ้นส่วนของ tool call อยู่ใน `delta.tool_calls` โดยมี `index` ประจำแต่ละ call

ไม่มีข้อไหนเป็นมาตรฐาน มันคือรูปแบบ request ของบริษัทหนึ่ง แล้วอีกหลายบริษัทลอกตามไป
เพราะการทำให้เข้ากันได้ถูกกว่าการทำให้ต่าง Ollama, OpenRouter, Groq, Together, vLLM
และ local server อีกมากมายพูดภาษานี้ ซึ่งเป็นเหตุผลที่ภาคหนึ่งของคอร์สนี้เลือกใช้มัน
คุณเปลี่ยน environment variable ตัวเดียวก็ยิงไปที่ตัวไหนก็ได้

แต่ไม่ใช่ทุก provider ที่ลอกตาม API ของ Anthropic เอง ตัวที่ให้บริการ Claude
มีรูปร่าง request ต่างกัน รูปร่าง response ต่างกัน และรูปแบบ streaming ต่างกัน
มันไม่ได้แย่กว่าและไม่ได้ดีกว่า มันแค่ต่าง และความต่างนั้นตกอยู่ตรงจุดที่ `llm.py` hard code ไว้พอดี

สรุปสถานการณ์จริงของคุณตอนจบ lesson 05 คุณมี streaming agent ที่ทำงานได้และเรียก tool วนเป็น loop
ถ้ามีคนขอให้คุณรันมันกับ Claude แทน คุณเปลี่ยนแค่ base URL ไม่ได้
คุณต้องเปิด `llm.py` แล้วเขียนตัวสร้าง payload, URL และตัว parse stream ใหม่
และถ้าคุณอยากรองรับทั้งสองแบบ คุณต้องใส่ `if` ในทุกจุดเหล่านั้น
ซึ่งเป็นจุดเริ่มของความยุ่งเหยิงที่โตขึ้นทุกครั้งที่มี provider ตัวที่ห้าโผล่มา

จุดประสงค์ของบทนี้คือย้ายความต่างนั้นออกจาก loop ไปไว้ในที่ที่สลับสับเปลี่ยนได้
และทำตอนที่ codebase ยังเล็กพอจนการผ่าตัดใช้เวลาแค่ยี่สิบนาที

```text
lesson 05
  agent.py  ->  llm.complete_stream  ->  one HTTP dialect, welded in

lesson 06
  agent.py  ->  provider.stream      ->  OpenAICompatProvider  ->  dialect A
                                     ->  AnthropicProvider     ->  dialect B
```

## 2. ความต่างจริงระหว่าง API สองตัว

ก่อนออกแบบอะไร ลองดูก่อนว่าอะไรต่างกันจริง เรื่องนี้สำคัญ
เพราะพอได้ยินคำว่า abstraction คนมักอยากประดิษฐ์ framework ขนาดใหญ่
เพื่อรองรับความต่างที่ยังไม่เคยเห็น วิธีที่ซื่อตรงกว่าคือดู API จริงสองตัว
ไล่รายการว่าอะไรขัดกันจริง แล้วซ่อนเฉพาะส่วนนั้น

มีความต่างสามข้อในรูปร่างของ request และของบทสนทนา บวกอีกหนึ่งข้อในรูปแบบ streaming
เท่านั้นเอง ที่เหลือทั้งหมด ทั้งชื่อ model, list ของ messages, แนวคิดของ tool call ที่มี id นั้นเหมือนกัน

### ความต่างที่หนึ่ง ตำแหน่งของ system prompt

system prompt คือคำสั่งประจำที่คุณให้ model ก่อนบทสนทนาจะเริ่ม
ทำนองว่า "You are a careful assistant that always shows its working."
ภาคหนึ่งยังไม่ได้ใช้มันเลย และ lesson 10 ในภาคสองว่าด้วยการเขียนมันโดยเฉพาะ
สิ่งที่สำคัญตรงนี้คือมันไปอยู่ตรงไหนบนสาย

ในรูปแบบ OpenAI compatible มันคือ message ธรรมดาตัวหนึ่ง มี role เป็น `system`
วางอยู่หน้าสุดของ list `messages`

```json
{
  "model": "mock",
  "stream": true,
  "messages": [
    {"role": "system", "content": "You are a careful assistant."},
    {"role": "user", "content": "What is 2 plus 3?"}
  ]
}
```

ในรูปแบบ Anthropic ไม่มี role ชื่อ `system` เลย system prompt เป็น field ระดับบนสุดที่อยู่ข้าง ๆ `messages`
และการใส่ message ที่มี role เป็น `system` ลงใน list ถือเป็น error

```json
{
  "model": "mock",
  "max_tokens": 4096,
  "stream": true,
  "system": "You are a careful assistant.",
  "messages": [
    {"role": "user", "content": "What is 2 plus 3?"}
  ]
}
```

สังเกตอีกเรื่องเล็ก ๆ ในบล็อกนั้น `max_tokens` เป็น field บังคับของ Anthropic API
แต่เป็น optional ในฝั่ง OpenAI compatible นั่นคือเหตุผลที่ `providers.py`
hard code ค่า `4096` ไว้ใน class หนึ่ง และไม่พูดถึง field นี้เลยในอีก class หนึ่ง

### ความต่างที่สอง key ที่เก็บ schema ของ argument

คุณรู้จักรูปแบบ tool schema มาตั้งแต่ lesson 03 แล้ว ทั้งสอง API ใช้ JSON Schema สำหรับ argument
สิ่งที่ต่างกันคือ key ที่แขวนมันไว้ และความลึกของการซ้อนโครงสร้าง

ฝั่ง OpenAI compatible tool ถูกห่อไว้ใน object ที่มีตัวแยกประเภทชื่อ `type`
และ schema อยู่ใต้ `function.parameters`

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "add",
        "description": "Add two numbers together and return the sum.",
        "parameters": {
          "type": "object",
          "properties": {
            "a": {"type": "number", "description": "The first number"},
            "b": {"type": "number", "description": "The second number"}
          },
          "required": ["a", "b"]
        }
      }
    }
  ]
}
```

ฝั่ง Anthropic tool เป็นโครงสร้างแบน และ schema อยู่ใต้ `input_schema`

```json
{
  "tools": [
    {
      "name": "add",
      "description": "Add two numbers together and return the sum.",
      "input_schema": {
        "type": "object",
        "properties": {
          "a": {"type": "number", "description": "The first number"},
          "b": {"type": "number", "description": "The second number"}
        },
        "required": ["a", "b"]
      }
    }
  ]
}
```

จ้อง object ของ schema ทั้งสองตัวให้ดี มันเหมือนกันทุกไบต์
ความต่างอยู่ที่ซองห่อล้วน ๆ ซึ่งเป็นสัญญาณที่ดีว่าคุณต้องการแค่ชั้นแปลเล็ก ๆ ชั้นเดียว
ไม่ใช่การเขียน `tools.py` ใหม่

### ความต่างที่สาม เส้นทางที่ผลลัพธ์ของ tool เดินทางกลับ

ข้อนี้ใหญ่ที่สุดในสามข้อ และเป็นข้อที่ก่อ bug จริง

ใน lesson 04 คุณได้เรียนว่าผลลัพธ์ของ tool ถูกส่งกลับไปหา model เป็น message ใหม่ที่มี role เป็น `tool`
พร้อม `tool_call_id` ของ call ที่มันตอบ ต่อไปนี้คือการแลกเปลี่ยนสาม message ครบชุดในรูปแบบนั้น
ตรงตามที่ `agent.py` สร้างไว้ในหน่วยความจำ

```json
[
  {"role": "user", "content": "What is 2 plus 3?"},
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_mock_1",
        "type": "function",
        "function": {"name": "add", "arguments": "{\"a\": 2, \"b\": 3}"}
      }
    ]
  },
  {"role": "tool", "tool_call_id": "call_mock_1", "content": "5"}
]
```

รูปแบบของ Anthropic ไม่มี role ชื่อ `tool` เลย มีแค่สอง role คือ `user` และ `assistant`
`content` ของ message เป็นได้ทั้ง string ธรรมดาหรือ list ของ block ที่มี type
และทั้งการร้องขอ tool กับคำตอบของมันต่างก็เป็น block
คำร้องขอคือ `tool_use` block ที่อยู่ใน assistant message
ส่วนคำตอบคือ `tool_result` block ที่อยู่ใน message ของ **user**
เพราะในมุมของ model ผลลัพธ์คือสิ่งที่โลกภายนอกบอกมัน

```json
[
  {"role": "user", "content": "What is 2 plus 3?"},
  {
    "role": "assistant",
    "content": [
      {"type": "tool_use", "id": "call_mock_1", "name": "add", "input": {"a": 2, "b": 3}}
    ]
  },
  {
    "role": "user",
    "content": [
      {"type": "tool_result", "tool_use_id": "call_mock_1", "content": "5"}
    ]
  }
]
```

มีสามอย่างเปลี่ยนพร้อมกัน ค่อย ๆ อ่านทีละอย่าง

role ของ message ที่เป็นผลลัพธ์เปลี่ยนจาก `tool` เป็น `user`
field ของ id เปลี่ยนชื่อจาก `tool_call_id` เป็น `tool_use_id`
และ argument เปลี่ยนจาก JSON string ที่อยู่ใต้ `function.arguments`
มาเป็น object ที่ parse แล้วจริง ๆ อยู่ใต้ `input`
ข้อสุดท้ายควรมองซ้ำอีกรอบ เพราะ lesson 03 ใช้ทั้งหัวข้ออธิบายว่า `arguments`
มาถึงในรูป string ที่บรรจุ JSON ไว้ แต่ในรูปแบบ message ของ Anthropic
tool call ของ assistant เองจะถูกส่งกลับไปหา server เป็น object ที่ parse แล้ว
ดังนั้นชั้นแปลต้องเรียก `json.loads` ตอนขาออก คุณจะเห็นบรรทัดนั้นในหัวข้อ 6

### ความต่างที่สี่ รูปแบบ streaming

lesson 05 สอนว่าคำตอบแบบ stream มาถึงเป็นชุดของบรรทัด `data: `
บน HTTP response ยาว ๆ เส้นเดียว และคุณต้องต่อชิ้นส่วนกลับเข้าด้วยกันเอง
ทั้งสอง API ทำแบบนั้น แต่ขัดกันสิ้นเชิงเรื่องสิ่งที่อยู่ในแต่ละบรรทัด

ทุกบล็อก JSON ข้างล่างนี้คัดลอกมาจาก fake server ของโปรเจกต์นี้ที่
`src/agentpath/testing/mock_server.py` ซึ่งผลิตทั้งสอง dialect
เพื่อให้ check ของบทเรียนรันแบบ offline ได้ มันคือรูปร่าง event จริง ไม่ใช่ภาพร่าง

stream ฝั่ง OpenAI compatible เป็นชุดของ object ที่แทบเหมือนกันหมด
แต่ละตัวมี list ชื่อ `choices` และส่วนที่น่าสนใจคือ `delta` ที่บอกว่าให้ต่ออะไรเพิ่ม
ข้อความมาแบบนี้

```json
{"choices": [{"index": 0, "delta": {"content": "Hello "}}]}
{"choices": [{"index": 0, "delta": {"content": "from t"}}]}
{"choices": [{"index": 0, "delta": {"content": "he moc"}}]}
```

tool call มาในรูปร่างเดียวกัน แต่ delta พา `tool_calls` มาแทน `content`
ชิ้นแรกประกาศ id กับชื่อ และทุกชิ้นหลังจากนั้นพาส่วนหนึ่งของ string argument มา

```json
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "call_mock_1", "type": "function", "function": {"name": "add", "arguments": ""}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"a\":"}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": " 2, \""}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "b\": 3"}}]}}]}
{"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]}}]}
{"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
```

ทุกอย่างไร้ type ในความหมายที่ว่าคุณต้องเดาความหมายของ chunk ด้วยการงมหา key
มี `content` ไหม มี `tool_calls` ไหม นั่นคือเหตุผลที่ตัว parse ของ lesson 05
เป็นกอง `if` ที่ซ้อนอยู่บนการเรียก `.get(...)`

stream ฝั่ง Anthropic เป็นการออกแบบตรงข้าม ทุกบรรทัดเป็น event ที่มี type ชัดเจนผ่าน field `type`
และ event เหล่านั้นบรรยาย state machine เล็ก ๆ เหนือ content block ที่มีหมายเลขกำกับ
message เริ่ม block เปิดและปิดตาม index แล้ว message ก็จบ

นี่คือคำตอบแบบข้อความ ครบชุด

```json
{"type": "message_start", "message": {"id": "mock-1", "role": "assistant", "content": []}}
{"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello "}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "from t"}}
{"type": "content_block_stop", "index": 0}
{"type": "message_delta", "delta": {"stop_reason": "end_turn"}}
{"type": "message_stop"}
```

และนี่คือ tool call ครบชุด สังเกตว่าชิ้นส่วนของ argument มี delta type ของตัวเอง คือ
`input_json_delta` และ field ของชิ้นส่วนชื่อ `partial_json`

```json
{"type": "message_start", "message": {"id": "mock-1", "role": "assistant", "content": []}}
{"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "call_mock_1", "name": "add", "input": {}}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{\"a\":"}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": " 2, \""}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "b\": 3"}}
{"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "}"}}
{"type": "content_block_stop", "index": 0}
{"type": "message_delta", "delta": {"stop_reason": "tool_use"}}
{"type": "message_stop"}
```

ข้อสังเกตสองข้อที่จะช่วยประหยัดเวลาคุณในภายหลัง

ข้อแรก สังเกต `"input": {}` ใน event `content_block_start`
server ส่ง object ว่างมาตรงนั้น แล้วค่อย stream argument จริงมาเป็นชิ้นส่วนข้อความ
ถ้าคุณอ่าน event เริ่มต้นแล้วเชื่อ field `input` ของมัน คุณจะได้ dictionary ว่าง
และได้ tool call ที่ไม่ทำอะไรเลย ซึ่งเป็น bug ที่ตามหาแล้วปวดหัวมาก
argument จะมีตัวตนก็ต่อเมื่อคุณต่อชิ้นส่วน `partial_json` ครบทุกชิ้นแล้วเท่านั้น

ข้อสอง ทั้งสอง dialect stream argument ของ tool มาเป็นชิ้นส่วนข้อความที่ยังไม่ใช่ JSON
ที่ถูกต้องจนกว่าชิ้นสุดท้ายจะมาถึง นั่นไม่ใช่ความบังเอิญของรูปแบบ
แต่เป็นผลจากวิธีที่ model สร้างข้อความ ตัวอักษรออกมาทีละตัว
และ provider ก็ส่งต่อทันทีที่มันปรากฏ lesson 05 สอนคุณไปแล้วว่าให้ buffer ไว้แล้ว parse ครั้งเดียวตอนจบ
และบทเรียนนั้นย้ายมาใช้กับ dialect ใหม่ได้โดยไม่ต้องแก้อะไร

นี่คือการเปรียบเทียบทั้งหมดในตารางเดียว เผื่อคุณอยากมีอะไรให้ชี้

| ประเด็น | OpenAI compatible | Anthropic |
| --- | --- | --- |
| Path | `/chat/completions` | `/messages` |
| Auth header | `Authorization` พร้อมค่าแบบ bearer | `x-api-key` บวก `anthropic-version` |
| System prompt | message ที่มี role `system` | field `system` ระดับบนสุด |
| Max tokens | ไม่บังคับ | บังคับ ในชื่อ `max_tokens` |
| key ของ tool schema | `function.parameters` | `input_schema` |
| model ขอเรียก tool | `tool_calls` บน assistant message | `tool_use` block |
| argument ของ tool บนสาย | JSON string | object ที่ parse แล้ว อยู่ใต้ `input` |
| คุณส่งผลลัพธ์กลับ | message ที่มี role `tool` | `tool_result` block ใน user message |
| ข้อความแบบ streaming | `choices[0].delta.content` | `content_block_delta` แบบ `text_delta` |
| argument ของ tool แบบ streaming | `choices[0].delta.tool_calls[].function.arguments` | `content_block_delta` แบบ `input_json_delta` |

## 3. thinking block และ field ที่คุณห้ามทิ้ง

หัวข้อ 2 นับความต่างสามข้อในรูปร่างของบทสนทนา และอีกหนึ่งข้อในรูปร่างของ stream
การนับนั้นซื่อตรงสำหรับโค้ดในบทเรียนนี้ และฝั่งบทสนทนาจะได้ข้อที่สี่เพิ่มมาทันที
ที่คุณขอให้ model คิดก่อนตอบ

ข้อนี้ได้หัวข้อของตัวเองเพราะมันไม่ประพฤติตัวเหมือนข้ออื่น
ความต่างสามข้อในหัวข้อ 2 ประกาศตัวเองตั้งแต่ครั้งแรกที่คุณรันโค้ด
key ผิดก็ได้ 400 ทันที คุณแก้แล้วเดินต่อ
ส่วนข้อนี้มองไม่เห็นเลยตราบใดที่คุณยังไม่ใช้ฟีเจอร์นั้น
แล้วในวันแรกที่มีคนเปิดมันขึ้นมา request ที่หน้าตาเหมือนกับที่ทำงานได้มาหลายเดือน
กลับถูกปฏิเสธทั้งก้อน และต้นเหตุคือ field ที่สัญชาตญาณทุกอย่างของคุณบอกว่าทิ้งได้อย่างปลอดภัย

### thinking block คืออะไร

model ปัจจุบันหลายตัวถูกสั่งให้แสดงการคิดก่อนตอบได้ คุณเปิดมันด้วย field ใน request
ซึ่งใน dialect ของ Anthropic ชื่อ `thinking` และพา effort level
หรือ budget เป็นจำนวน token มาด้วย จากนั้น model จะใช้ output ส่วนหนึ่ง
ไปกับการผลิตการให้เหตุผลที่นำไปสู่คำตอบ แทนที่จะเป็นตัวคำตอบเอง

สิ่งที่สำคัญตรงนี้ไม่ใช่เนื้อหาของการให้เหตุผลนั้น แต่คือมันไปตกอยู่ตรงไหน
การคิดไม่ได้มาถึงในรูปที่พับซ่อนอยู่ในข้อความของ assistant
แต่มาถึงเป็น content block ชนิดของมันเอง เป็นพี่น้องกับ text block
และกับ `tool_use` block ที่คุณเจอในหัวข้อ 2 โดยอยู่ใน assistant message เดียวกัน

นี่คือ assistant message ตามจริงจากเทิร์นที่ model คิดแล้วเรียก tool

```json
{
  "role": "assistant",
  "content": [
    {
      "type": "thinking",
      "thinking": "The user is asking for 2 plus 3. I have an add tool and arithmetic is exactly what it is for, so I should call it rather than answer from memory.",
      "signature": "ErUBCkYIBBgCIkBub3RfYV9yZWFsX3NpZ25hdHVyZV9leGFtcGxlEgxzaWduYXR1cmUtdjEaDGV4YW1wbGUtb25seQ"
    },
    {
      "type": "tool_use",
      "id": "call_mock_1",
      "name": "add",
      "input": {"a": 2, "b": 3}
    }
  ]
}
```

อ่านรูปร่างมากกว่าอ่านถ้อยคำ block นี้มี `type` เป็น `thinking`
มีการคิดที่อ่านได้อยู่ใต้ key ชื่อเดียวกัน และมี key ที่สาม คือ `signature`
ซึ่งเก็บ string ทึบที่ model ไม่ได้เขียนและคุณตีความไม่ได้
มันอยู่ใน list เดียวกับ `tool_use` block ในระดับเดียวกัน ตามลำดับที่ model ผลิตออกมา

dialect แบบ OpenAI compatible ไม่มี block ที่เทียบเท่านี้เลย
server บางตัวที่พูด dialect นี้แปะข้อความการให้เหตุผลไว้ใน delta ใต้ field ที่ตัวเองคิดชื่อขึ้นมา
ไม่มีสองตัวไหนตั้งชื่อตรงกัน และไม่มีตัวไหนพาอะไรที่เหมือน signature มาด้วย
ความว่างเปล่านั้นเองคือความต่าง dialect หนึ่งให้ที่ทางระดับชั้นหนึ่งกับการให้เหตุผลใน message
พร้อมกฎที่ผูกติดมาด้วย ส่วนอีก dialect ยังไม่ได้ทำให้มันเป็นมาตรฐานเลย

### กฎ

ทุก request ของทั้งสอง API พาบทสนทนาทั้งหมดไปด้วย server ไม่เก็บอะไรไว้ระหว่างเทิร์น
ซึ่งเป็นข้อเท็จจริงเดียวกับที่ lesson 02 ใช้สร้าง list ของประวัติ
ดังนั้นเมื่อ model ผลิต thinking block ในเทิร์นหนึ่งและคุณอยากได้เทิร์นที่สอง
block นั้นต้องเดินทางกลับไปหา server ในประวัติที่คุณส่งไป

กฎคือมันต้องกลับไปเหมือนตอนที่มันมาถึงทุกประการ

ไม่สรุปย่อเหลือประโยคแรกเพราะมันยาว ไม่ตัดทิ้งเพราะรูปแบบประวัติภายในของคุณไม่มีที่ให้มันอยู่
ไม่ serialise ใหม่ให้เป็นทรงของคุณเองด้วยการเปลี่ยนชื่อ key สลับลำดับ หรือจัด whitespace ใหม่
block ที่คุณได้รับคือ block ที่คุณส่ง ทีละ field ในตำแหน่งเดิมของ message เดิม
และเรียงลำดับเดิมเทียบกับ thinking block อื่นในเทิร์นนั้น

นั่นเข้มกว่าที่ API ส่วนใหญ่เป็น และควรรู้ว่าทำไมมันเข้มขนาดนั้น ไม่ใช่แค่รู้ว่ามันเข้ม
thinking block ไม่ใช่ข้อความสนทนาธรรมดาที่ model แค่อ่านซ้ำ
มันคือบันทึกของการคำนวณที่ server ทำไป และ server ต้องบอกได้ว่า
บันทึกที่ถูกยื่นกลับมาคือบันทึกที่มันผลิตเอง ข้อความธรรมดา server อ่านแล้วเชื่อได้
แต่ของชิ้นนี้มันตรวจสอบ

### field ชื่อ signature

ซึ่งพาเรามาถึง field ที่ก่อ bug

`signature` คือค่าสำหรับตรวจสอบตัวนั้น คุณอ่านมันไม่ได้ สร้างมันเองไม่ได้
และไม่มีอะไรในโค้ดของคุณที่จะมีเหตุผลให้ต้องแหย่เข้าไปดูข้างในมัน
พูดอีกอย่างคือมันเป็น field ชนิดที่คนเขียนโค้ดอย่างรอบคอบจะตัดสินว่าเป็นเศษขยะของ provider
แล้วทิ้งมันตอนแปลงเข้าสู่รูปแบบภายในของตัวเอง
มันคือ field ที่ถูกทิ้งบ่อยที่สุดในเรื่องทั้งหมดนี้ และคนที่ทิ้งมันคือคนที่เรียบร้อย ไม่ใช่คนที่สะเพร่า

นี่คือสิ่งที่ทำให้มันแพง ถ้า thinking block กลับไปโดยไม่มี signature
หรือมี signature ที่ไม่ตรงกับเนื้อการคิดที่อยู่ข้าง ๆ แล้วมี tool call อยู่ในเทิร์นเดียวกันนั้นด้วย
API จะไม่เมิน field ที่หายไปแล้วทำงานต่อ แต่จะปฏิเสธ request ทั้งก้อน
คุณจะได้ 400 บนบทสนทนาที่เทิร์นก่อนหน้ายังทำงานได้ดี ชี้ไปที่ message ที่คุณไม่คิดว่าตัวเองไปแตะ
จากโค้ดที่ถูกต้องมาตั้งแต่วันที่คุณเขียนมัน

นั่นคือเหตุผลที่ควรรู้เรื่องนี้ก่อนจะเจอมัน ทุกอย่างที่เหลือในบทนี้คุณค้นพบใหม่ได้ในสิบนาที
จากข้อความ error กับ schema แต่ข้อนี้ปรากฏตัวในรูปของ request ที่เคยทำงานได้แล้วอยู่ ๆ ก็ไม่ได้
บน field ที่คุณจงใจเอาออกด้วยเหตุผลที่ดี และความเชื่อมโยงระหว่างต้นเหตุกับอาการ
ไม่ใช่สิ่งที่ stack trace จะยื่นให้คุณ

### block แบบ redacted

มีอีกชนิดหนึ่งของเรื่องเดียวกัน บางครั้งการคิดไม่ได้ถูกส่งกลับมาในรูปที่อ่านได้เลย
สิ่งที่มาถึงคือ `redacted_thinking` block ที่พา field ทึบชื่อ `data` มาเพียงตัวเดียว
และไม่มีข้อความที่คุณอ่านได้

```json
{
  "role": "assistant",
  "content": [
    {
      "type": "redacted_thinking",
      "data": "EroBCkYIBBgCKkBub3RfYV9yZWFsX3JlZGFjdGVkX3BheWxvYWQSDHJlZGFjdGVkLXYxGgxleGFtcGxlLW9ubHk"
    },
    {
      "type": "tool_use",
      "id": "call_mock_1",
      "name": "add",
      "input": {"a": 2, "b": 3}
    }
  ]
}
```

ตรงนี้ยั่วใจกว่าเดิม เพราะ block ที่คุณอ่านไม่ได้ยิ่งดูเหมือนของที่ทิ้งได้อย่างปลอดภัย
กฎไม่เปลี่ยน มันกลับไปโดยไม่ถูกแตะ อยู่ในตำแหน่งเดิม เหมือนตอนที่มันมาถึงทุกประการ
agent ของคุณไม่จำเป็นต้องเข้าใจ block เพื่อจะพามันไปได้
และการพาสิ่งที่ตัวเองไม่เข้าใจไปด้วยคือส่วนใหญ่ของการเป็น client ที่ประพฤติตัวดี

### ผลกระทบต่อ cache ที่คิดเงินแทนที่จะ error

ครึ่งหลังของเรื่องนี้ไม่ผลิต error ออกมาเลย ซึ่งเป็นสิ่งที่ทำให้มันแย่กว่า

provider จะ cache ส่วนหน้าของบทสนทนาไว้ ถ้า token หลายพันตัวแรกของ request นี้
เหมือนกับ token หลายพันตัวแรกของ request ที่แล้วทุกไบต์
server จะเอางานที่ทำไปแล้วมาใช้ซ้ำและคิดเงินส่วนนั้นถูกลงมาก
agent loop เป็นกรณีที่เกือบสมบูรณ์แบบสำหรับเรื่องนี้ เพราะทุกเทิร์นส่ง system prompt เดิม
tool schema เดิม และประวัติเดิมที่ต่อท้ายเพิ่มมานิดเดียวไปใหม่

จุดที่ต้องระวังคือการเทียบต้องตรงเป๊ะ และต้องเริ่มจากต้น
เปลี่ยนอะไรก็ตามใกล้ ๆ ส่วนหน้าของ request แล้วทุกอย่างหลังจุดที่เปลี่ยนจะพลาด cache ทั้งหมด

การเปิด thinking การปิดมัน การขยับ effort level หรือการเพิ่ม budget
ล้วนเปลี่ยนรูปร่างของสิ่งที่ถูกส่งไป ตั้งแต่ request นั้นเป็นต้นไป
ส่วนหน้าจะเลิกตรงกับสิ่งที่ cache ไว้ และทุก request หลังจากนั้นใน session เดียวกัน
จะจ่ายเต็มราคาสำหรับ token ที่เทิร์นก่อนหน้าเกือบฟรี ไม่มีอะไรล้มเหลว ไม่มี warning ถูกบันทึก
ที่เดียวที่มันโผล่มาคือใบเรียกเก็บเงิน และตอนนั้นก็ไม่มีใครจำได้แล้วว่าบ่ายวันไหน
ที่มีคนขยับ budget จากเลขหนึ่งไปอีกเลขหนึ่ง

กฎที่ใช้จริงจึงคือเลือกค่า thinking ตอน session เริ่ม แล้วอย่าไปแตะมันตลอดอายุของ session นั้น
ถ้าคุณต้องการค่าอื่น นั่นคือ session อื่น lesson 15 คือที่ที่เรื่องนี้ถูกวัดอย่างจริงจัง
ด้วยตัวเลขจริงที่ดึงออกมาจาก field usage และรายการเต็มของสิ่งที่ทำลาย cache ส่วนหน้าแบบเงียบ ๆ
ตอนนี้เอากฎกับเหตุผลของมันไปก่อน

### provider ของเราทำอะไรจริง ๆ และไม่ทำอะไร

ทีนี้ถึงส่วนที่ต้องพูดตรง ๆ

กลับไปดู loop สำหรับ parse ใน `AnthropicProvider.stream` อีกครั้ง
มันจัดการ content block แค่สองชนิด `content_block_start` ที่ type เป็น `tool_use`
เปิดช่องเก็บหนึ่งช่อง และ `content_block_delta` ที่พา `text_delta` หรือ `input_json_delta`
มาป้อนข้อความที่มองเห็นได้หรือชิ้นส่วนของ argument ที่เหลือทั้งหมดตกผ่านไปและถูกเมิน
ซึ่งหัวข้อ 6 จะชมว่าเป็นเหตุผลที่ตัว parse นี้อยู่รอดเมื่อ provider เพิ่ม event ชนิดใหม่

thinking block คือหนึ่งในสิ่งที่ตกผ่านไป มันไม่ถูกเก็บ ไม่ถูกคืนกลับมา
และ `stream` ก็ไม่มีที่ในค่าคืนของมันให้ใส่ เพราะข้อตกลงในหัวข้อ 4
สัญญาไว้แค่ข้อความกับ call เท่านั้น จากนั้น `_to_wire` ก็ประกอบเทิร์นของ assistant ขึ้นใหม่
จาก string ของข้อความกับ list ของ tool call ดังนั้นต่อให้ thinking block รอดจากตัว parse มาได้
ก็ยังไม่มีทางที่มันจะกลับขึ้นไปบนสายได้อยู่ดี

นั่นคือข้อจำกัดจริง และบทนี้จะไม่แกล้งทำเป็นอย่างอื่น
มันยอมรับได้ตรงนี้ด้วยเหตุผลเดียวที่เฉพาะเจาะจง ไม่มีอะไรในคอร์สนี้ที่เปิด extended thinking เลย
`providers.py` ไม่เคยส่ง field `thinking` ดังนั้นจึงไม่มี model ตัวไหนผลิต thinking block
จึงไม่มี block ไหนถูกทิ้ง โค้ดนี้ถูกต้องสำหรับ request ที่มันสร้างขึ้นจริง

มันจะกลายเป็น bug ในวันแรกที่มีคนเปลี่ยนเรื่องนั้น เพิ่ม field `thinking` เข้าไปใน payload
กับ model จริง ปล่อยให้มันเรียก tool แล้วเทิร์นที่สองจะล้มเหลว ด้วยเหตุผลที่อธิบายไว้ข้างบนพอดี

การเรียกมันด้วยชื่อของมันดีกว่าการกลบไว้ การแก้ครึ่งเดียว
ที่ตัว parse เก็บ thinking block มาแล้ว loop ยังไม่มีที่ให้เก็บ จะแย่กว่าการไม่ทำอะไรเลย
เพราะมันจะดูเหมือนถูกจัดการแล้ว ส่วนการแก้จริงก็ไม่ใช่การปะที่ `_to_wire` เช่นกัน
มันต้องการให้รูปแบบบทสนทนาภายในมีที่สำหรับเก็บ block ทึบของ provider ไว้ทั้งดุ้น
แล้วส่งคืนไปโดยไม่แตะ ซึ่งก็คือรูปแบบภายในที่เป็นกลางที่แบบฝึกหัดข้อสามท้ายบทนี้ขอให้คุณสร้างพอดี
ถ้าคุณทำแบบฝึกหัดข้อนั้น นี่คือข้อกำหนดที่ทำให้มันคุ้มที่จะทำให้ถูกต้องจริง ๆ

### ทำไมเรื่องนี้ถึงอยู่ในบทนี้

เพราะมันคือความต่างจริงข้อที่สี่ระหว่างสอง dialect และเป็นชนิดที่บทนี้มีอยู่เพื่อแยกมันออกมาพอดี
dialect หนึ่งมี content block ที่มีกฎการจัดการเข้มงวดและมี field สำหรับตรวจสอบติดมาด้วย
อีก dialect ไม่มีอะไรที่เป็นมาตรฐานตรงนั้นเลย ความต่างนั้นต้องไปอยู่ที่ไหนสักแห่ง
และที่เดียวที่สมเหตุสมผลคือข้างใน class ของ provider

และเพราะมันสอนสิ่งที่ความต่างอีกสามข้อสอนไม่ได้ `input_schema` ที่หายไป
บอกคุณว่าอะไรผิดตั้งแต่ครั้งแรกที่รันโค้ด ส่วน signature ที่ถูกทิ้งไม่บอกอะไรคุณเลย
จนกว่าฟีเจอร์ที่คุณไม่ได้ใช้จะถูกเปิดขึ้นในอีกหลายเดือนถัดมา
และ thinking budget ที่ถูกเปลี่ยนก็ไม่บอกอะไรคุณเลยตลอดกาล
นั่นคือความต่างชนิดที่ตัดสินว่า abstraction จะรอดจากการปะทะกับสินค้าจริงหรือไม่
และวิธีที่ซื่อตรงในการจัดการกับข้อที่คุณยังไม่ได้ทำ คือเขียนมันไว้ในที่ที่คนอ่านคนต่อไปจะเจอ

## 4. interface คืออะไร

ตอนนี้คุณมีรายการความต่าง และมี loop ที่ต้องไม่สนใจความต่างเหล่านั้นเลย
เครื่องมือสำหรับงานนี้คือ interface

interface คือข้อตกลงเรื่องรูปร่างของการเรียก มันบอกว่า function ชื่ออะไร
รับ argument อะไรเข้าไป และคืนอะไรออกมา มันไม่บอกอะไรเลยเกี่ยวกับวิธีทำงาน
โค้ดที่เขียนตามข้อตกลงนี้จะถูกยื่นอะไรก็ได้ที่ทำตามข้อตกลง แล้วมันจะทำงานได้
เพราะมันพึ่งพาแค่ส่วนที่ถูกสัญญาไว้เท่านั้น

คุณใช้แนวคิดนี้มาหลายปีแล้วโดยไม่ได้เรียกชื่อมัน เวลาคุณเขียน `open(path)`
แล้วเรียก `handle.read()` คุณไม่รู้ว่าไบต์นั้นมาจากจานหมุน SSD network share หรือ RAM disk
`read` คือข้อตกลง มีใครสักคนทำตามมัน โค้ดของคุณเขียนตามข้อตกลง
และอยู่รอดผ่านทุกการเปลี่ยนแปลงที่อยู่ข้างใต้

ใน Python ข้อตกลงมักไม่ได้ถูกเขียนเป็นคำประกาศแยกต่างหากด้วยซ้ำ
ถ้า object มี method ชื่อถูกต้องและรับ argument ถูกต้อง มันก็ผ่านแล้ว
เท่านี้ก็พอสำหรับ `agent.py`

นี่คือข้อตกลงของเรา อธิบายในประโยคเดียว provider คือ object ใดก็ได้ที่มี method
ชื่อ `stream` ซึ่งรับ list ของ messages, list ของ tool schema แบบไม่บังคับ
และ callback `on_text` แบบไม่บังคับ แล้วคืน tuple ของข้อความฉบับเต็มกับ list ของ tool call

เขียนเป็น signature

```python
def stream(self, messages, tools=None, on_text=None):
    """Returns (text, calls).

    text  is the complete assistant text for this turn, "" if there was none
    calls is a list of dicts with the keys id, name, arguments, error
    """
```

key ทั้งสี่ใน call ควรตรึงให้ชัด เพราะมันคืออีกครึ่งหนึ่งของข้อตกลง
`id` คือตัวระบุที่ model ให้มากับ call ซึ่งคุณต้องส่งกลับไปพร้อมผลลัพธ์
`name` คือชื่อ tool `arguments` คือ dictionary ของ Python จริง ๆ ที่ parse เรียบร้อยแล้ว
`error` เป็น string ว่างเมื่อทุกอย่างเรียบร้อย และเป็นเหตุผลที่มนุษย์อ่านรู้เรื่อง
เมื่อชิ้นส่วน argument ต่อกันแล้วไม่เป็น JSON ที่ถูกต้อง key ตัวสุดท้ายมาจาก lesson 05
ที่คุณได้เรียนว่าการป้อน parse error กลับไปให้ model ดีกว่าการ crash มาก

สังเกตสิ่งที่ข้อตกลงไม่ได้พูดถึง ไม่มี URL ไม่มี header ไม่มี `choices`
ไม่มี `content_block_delta` ไม่มี `input_schema` คำเหล่านั้นปรากฏเฉพาะภายใน
class สองตัวใน `providers.py` และไม่ปรากฏที่อื่นในบทเรียนนี้เลย
นั่นคือบททดสอบของ interface ที่ดี ถ้าคำจากเอกสารของ provider ตัวใดโผล่มาใน agent loop ของคุณ
แปลว่า abstraction นั้นรั่ว

### ทำไมต้องเป็นข้อตกลง ไม่ใช่ทางเลือกอื่น

คุณแก้ปัญหาเดียวกันนี้ได้อีกสามวิธี ควรดูว่าทำไมมันแย่กว่า
เพราะคุณจะเจอทั้งสามแบบใน codebase จริง

**flag ภายใน function เดียว** เพิ่ม argument `provider="openai"` ให้ `complete_stream`
แล้วแยกสาขาตามค่านั้น วิธีนี้ใช้ได้กับ provider สองตัวพอดี และใช้ได้แค่บ่ายเดียว
จากนั้น function จะมีสี่สาขาในตัวสร้าง payload สามสาขาในส่วน URL
และ loop สำหรับ parse อีกสองชุดเต็ม ๆ ทั้งหมดอยู่ในไฟล์เดียว แชร์ตัวแปร local ร่วมกัน
การเพิ่ม provider ตัวที่สามหมายถึงการแก้โค้ดที่อีกสองตัวพึ่งพาอยู่
ความผิดพลาดในตัวใหม่จึงพังตัวเก่าได้
นั่นคือความล้มเหลวเฉพาะตัวที่ function ร่วมที่มี flag สร้างขึ้นเสมอ

**แปลทุกอย่างให้เป็นรูปแบบเดียวที่ขอบ** เก็บ HTTP client ตัวเดียวไว้
แล้วเขียน function ที่แปลง request และ response วิธีนี้ใกล้เคียงคำตอบที่ถูก
และจริง ๆ แล้วหัวข้อ 6 ก็ทำการแปลงแบบนี้พอดี ความต่างอยู่ที่ตัวแปลงอยู่ตรงไหน
function ลอย ๆ ต้องถูกเลือกโดยผู้เรียก ซึ่งเท่ากับย้าย branch กลับไปไว้ที่ผู้เรียก
การผูกตัวแปลงแต่ละตัวเข้ากับ class ที่ต้องใช้มันทำให้การเลือกเกิดขึ้นครั้งเดียว ตอนสร้าง object

**สืบทอดจาก base class ที่มีโค้ดร่วม** เขียน `BaseProvider` ที่จัดการ HTTP
แล้วให้แต่ละ provider override เฉพาะส่วนที่ต่าง วิธีนี้ยั่วใจ
และเป็นเส้นทางที่ทำให้โค้ดจำนวนมากอ่านไม่รู้เรื่อง method `stream` สองตัวที่นี่
แทบไม่มีอะไรร่วมกันในเชิงโครงสร้างเลย มันต่างกันที่ payload, URL, header และ loop สำหรับ parse ทั้งชุด
สิ่งที่เหลือให้แชร์คือบรรทัด `with httpx.Client(...)` เท่านั้น
การยกโค้ดหนึ่งบรรทัดขึ้นไปไว้ใน class แม่ แลกกับการบังคับให้คนอ่านกระโดดไปมาระหว่างสองไฟล์
เป็นการแลกที่ไม่คุ้ม class ทั้งสองใน `providers.py` จึงเขียนแบบแบน อ่านจากบนลงล่าง
และซ้ำกันนิดหน่อยโดยตั้งใจ เพื่อให้แต่ละตัวอ่านจบได้ด้วยตัวเอง

การตัดสินใจข้อสุดท้ายควรระบุเป็นกฎ เพราะมันสวนกับสัญชาตญาณที่คนส่วนใหญ่ถูกสอนมา
การเขียนซ้ำนั้นถูก โค้ดร่วมที่ผิดนั้นแพง สองร้อยบรรทัดที่คุณอ่านรวดเดียวจบ
ดีกว่าหนึ่งร้อยบรรทัดที่คุณต้องประกอบในหัว

## 5. ทำไม interface จึงเอา streaming มาก่อน

method เดียวในข้อตกลงชื่อ `stream` ไม่ใช่ `complete` และไม่มี method แบบไม่ stream เลย
นั่นเป็นการเลือกโดยตั้งใจ และเป็นเหตุผลที่บทนี้มาหลัง lesson 05 แทนที่จะมาก่อน

ลองจินตนาการว่าเราทำสลับกัน lesson 05 สอน streaming ก็ลองนึกภาพคอร์สรุ่นที่
abstraction มาที่ lesson 05 และ streaming มาที่ lesson 06
ข้อตกลงคงถูกออกแบบตามสิ่งที่มีอยู่ในตอนนั้น ซึ่งก็คือ function ของ lesson 04

```python
def complete(self, messages, tools=None):
    """Returns (text, calls) once the whole reply has arrived."""
```

ข้อตกลงนั้นดูสมเหตุสมผลมาก และมันคือกับดัก
การที่ข้อความมาถึงเป็นชิ้น ๆ ไม่ใช่รายละเอียดที่คุณเติมเข้าไปใต้คำสัญญาแบบนั้นได้
เพราะคำสัญญานั้นไม่มีที่ให้ชิ้นส่วนไปอยู่ มันมีค่าคืนค่าเดียวและเกิดขึ้นครั้งเดียวตอนจบ
การจะเพิ่ม streaming คุณต้องเปลี่ยนตัวข้อตกลงเอง
และการเปลี่ยนข้อตกลงหมายถึงการเปลี่ยนทุก implementation และทุกผู้เรียก

ลองนับจำนวนการแก้ในแต่ละลำดับ

```text
abstraction first, streaming second
  change the agreement            1 edit
  rewrite OpenAICompatProvider    1 edit
  rewrite AnthropicProvider       1 edit
  update agent.py                 1 edit
  update check.py                 1 edit
                                  5 edits, two of them full parser rewrites

streaming first, abstraction second   (this course)
  rewrite llm.py as a stream      1 edit   (lesson 05, one parser)
  split it into two classes       1 edit   (lesson 06)
  update agent.py                 1 edit
                                  the second parser is written once, correctly
```

กฎทั่วไปเบื้องหลังเรื่องนี้ควรพกติดตัวไว้ เวลาคุณออกแบบ interface
ให้ใส่ความสามารถที่ยากที่สุดที่คุณรู้ว่าจะต้องใช้ลงไปในข้อตกลงตั้งแต่ต้น
แม้วันนี้จะมี implementation แค่ตัวเดียวที่รองรับมันก็ตาม
ความสามารถที่เปลี่ยนรูปร่างของ control flow คือความสามารถที่ย้อนใส่ทีหลังไม่ได้
streaming เป็นตัวอย่างคลาสสิก เพราะมันเปลี่ยนค่าคืนค่าเดียวให้กลายเป็นลำดับของ event ตามเวลา
asynchrony เป็นอีกตัวอย่าง cancellation เป็นตัวที่สาม

มีเหตุผลที่สองว่าทำไม streaming มาก่อนจึงถูกต้อง และมันเกี่ยวกับว่าอะไรใส่ในอะไรได้
การเรียกแบบ streaming แกล้งทำตัวเป็นการเรียกแบบ batch ได้ง่ายมาก
คุณแค่เมิน callback แล้วอ่านค่าที่คืนมา ซึ่งเป็นสิ่งที่ `check.py` ทำพอดีเมื่อมันไม่สนใจ output แบบสด
แต่การเรียกแบบ batch แกล้งทำตัวเป็น streaming ไม่ได้
เพราะข้อมูลว่าแต่ละชิ้นมาถึงเมื่อไรถูกทิ้งไปแล้ว

นั่นคือเหตุผลที่ค่าคืนยังคงเป็นข้อความฉบับเต็ม ข้อตกลงให้คุณทั้งสองอย่าง
callback มีไว้สำหรับผู้เรียกที่อยากได้ชิ้นส่วนทันทีที่มันมาถึง
และค่าคืนมีไว้สำหรับผู้เรียกที่อยากได้แค่คำตอบ ไม่มีผู้เรียกฝ่ายไหนต้องจ่ายให้ความต้องการของอีกฝ่าย

มันยังหมายความว่า provider ในอนาคตที่ไม่มี endpoint แบบ streaming ก็ยังเข้ากับข้อตกลงได้
method `stream` ของมันเรียก endpoint ธรรมดา รับคำตอบทั้งก้อน เรียก `on_text` ครั้งเดียวด้วยข้อความทั้งหมด แล้วคืนค่า
output ดูไม่น่าตื่นเต้นเท่า แต่ interface ไม่ต้องเปลี่ยน
นั่นคือสัญญาณว่าข้อตกลงถูกลากเส้นไว้ถูกที่

## 6. เขียน providers.py ทีละ class

เปิด `providers.py` มันมี helper ร่วมหนึ่งตัวและ class สองตัว เรียงตามลำดับนั้น

### helper ที่ใช้ร่วมกัน

```python
def parse_arguments(raw):
    """Return (arguments, error). See lesson 05 for why we do not hide this."""
    try:
        return json.loads(raw or "{}"), ""
    except json.JSONDecodeError as problem:
        return {}, f"arguments were not valid JSON ({problem})"
```

โค้ดนี้ยกมาตรง ๆ จาก loop สำหรับ parse ของ lesson 05 แล้วตั้งชื่อให้
ด้วยเหตุผลง่าย ๆ ว่า class ทั้งสองต้องการพฤติกรรมเดียวกันเป๊ะ ในจังหวะเดียวกันเป๊ะ
ทั้งคู่สะสมข้อความ argument ทีละชิ้น และทั้งคู่ต้องแปลง string ที่สะสมไว้เป็น dictionary ตอนจบ

`or "{}"` รองรับ tool ที่ไม่รับ argument เลย ซึ่ง provider อาจส่ง string ว่างมา
แล้ว `json.loads` จะปฏิเสธ การคืน error เป็นค่าแทนที่จะ raise คือการรักษาการตัดสินใจจาก lesson 05 ไว้
model ที่สร้าง JSON พังสามารถถูกบอกให้รู้และขอให้ลองใหม่ได้ และ `agent.py` ก็ทำแบบนั้นพอดี
แต่ model ที่สร้าง JSON พังแล้วทำให้ process ของคุณ crash นั้นทำแบบนั้นไม่ได้

function เดียวนี้คือโค้ดชิ้นเดียวที่ class ทั้งสองใช้ร่วมกัน นั่นคือความจริงที่ตรงไปตรงมา
และเป็นเหตุผลที่ไม่มี base class

### OpenAICompatProvider

```python
class OpenAICompatProvider:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url or os.environ["AGENTPATH_BASE_URL"]).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AGENTPATH_API_KEY", "")
        self.model = model or os.environ["AGENTPATH_MODEL"]
```

constructor คือที่ที่การตั้งค่าทั้งหมดมาอยู่แล้วตอนนี้ ใน lesson 05
environment variable ทั้งสามตัวถูกอ่านอยู่ใน `complete_stream`
ซึ่งแปลว่ามันถูกอ่านใหม่ทุก request และ override ไม่ได้ถ้าไม่เปลี่ยน environment ของ process
ตอนนี้มันถูกอ่านครั้งเดียว และทั้งสามค่าส่งเข้ามาตรง ๆ ได้
นั่นคือสิ่งที่ทำให้ `check.py` สร้าง provider สองตัวด้วยการตั้งค่าที่ต่างกันใน process เดียวได้
และเป็นสิ่งที่จะทำให้ภาคสามรัน model ราคาถูกสำหรับงานย่อยแบบสรุปความ
ควบคู่ไปกับ model ที่เก่งกว่าสำหรับ loop หลักได้

อ่านบรรทัด `api_key` ให้ดี เพราะรูปแบบมันต่างจากอีกสองบรรทัด
มันคือ `api_key if api_key is not None else ...` ไม่ใช่ `api_key or ...`
ความต่างจะโผล่มาตอนคุณส่ง string ว่างเข้าไป ถ้าใช้ `or` string ว่างเป็นค่า falsy
และจะตกไปใช้ environment variable แบบเงียบ ๆ ส่วนการเช็ก `is not None` แบบชัดเจน
ทำให้การส่ง string ว่างหมายความว่าคุณตั้งใจไม่ใช้ key
ซึ่งเป็นกรณีปกติสำหรับ Ollama server ที่รันในเครื่อง ความต่างเล็กน้อย แต่กัน bug จริงได้

`rstrip("/")` บน base URL ทำให้ slash ต่อท้ายใน environment variable
ไม่ทำให้เกิด slash ซ้อนสองอันใน path ของ request เรื่องแบบนี้แหละที่สร้าง 404 ชวนงง
และการนั่งจ้องหน้าจอครึ่งชั่วโมง

```python
    def stream(self, messages, tools=None, on_text=None):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
```

header `Authorization` จะถูกเพิ่มเมื่อมี key เท่านั้น
เพื่อให้ local server ที่ไม่ชอบ auth header แปลกปลอมยังทำงานได้ดี

บรรทัด `tools` คือการแปล schema สำหรับ dialect นี้ และมันยาวแค่บรรทัดเดียว
เพราะเราเลือกให้รูปแบบ tool ของ interface เป็น object ชั้นในของ function
คือส่วนที่มี `name`, `description` และ `parameters` provider ตัวนี้ห่อแต่ละตัว
ด้วยซอง `{"type": "function", ...}` จากหัวข้อ 2
ส่วน `agent.py` จะแกะ `tools.SCHEMAS` ลงมาถึง object ชั้นในนั้นก่อนเรียก ซึ่งคุณจะเห็นในหัวข้อ 7

```python
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
```

เนื้อในนี้คือตัว parse ของ lesson 05 ที่ย้ายเข้ามาอยู่ใน method โดยไม่แตะอะไรอย่างอื่นเลย
นั่นเป็นความตั้งใจ และคุณควรเทียบมันกับ `lessons/05-streaming/llm.py` ทีละบรรทัด
เพื่อให้ตัวเองมั่นใจ การ refactor เชื่อถือได้ง่ายขึ้นมาก
เมื่อส่วนหนึ่งของการเปลี่ยนแปลงพิสูจน์ได้ว่าเป็นศูนย์

แนวคิดเดียวที่ควรอ่านซ้ำคือ `partial` มันคือ dictionary ที่ใช้ index ของ call
ที่ provider ส่งมาเป็น key เพราะ model ขอ tool หลายตัวในเทิร์นเดียวได้
และชิ้นส่วนของมันปนกันมาใน stream index คือวิธีที่คุณรู้ว่าชิ้นส่วนหนึ่งเป็นของ
string argument ที่ยังไม่เสร็จตัวไหน

```python
        calls = []
        for _, s in sorted(partial.items()):
            arguments, error = parse_arguments(s["arguments"])
            calls.append({"id": s["id"], "name": s["name"], "arguments": arguments, "error": error})
        return "".join(text_parts), calls
```

`sorted` จัด call กลับมาเรียงตาม index เพราะลำดับการแทรกของ dictionary
เป็นไปตามว่าชิ้นแรกของ call ไหนมาถึงก่อน ซึ่งไม่รับประกันว่าจะเป็น call ที่ศูนย์
จากนั้น string ที่สะสมไว้ทุกตัวจะถูก parse ครั้งเดียว แล้วผลลัพธ์ก็เป็นรูปร่างตามที่ข้อตกลงสัญญาไว้

### AnthropicProvider ส่วน constructor และ payload

constructor เหมือนกับอีกตัวทุกประการ โดยตั้งใจ
เพื่อให้ class ทั้งสองสลับกันได้ ณ จุดที่สร้าง object

```python
    def stream(self, messages, tools=None, on_text=None):
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
```

ความต่างของ header สองข้อจากหัวข้อ 2 โผล่มาตรงนี้ key ไปอยู่ใน `x-api-key`
แทนที่จะเป็นค่า bearer ใน `Authorization` และมี header `anthropic-version` ที่บังคับ
string ของเวอร์ชันนั้นคือวันที่ และมันตรึง request ไว้กับพฤติกรรมเวอร์ชันหนึ่งของ API
เพื่อให้การเปลี่ยนแปลงฝั่ง server ไม่ไปเปลี่ยนสิ่งที่โค้ดของคุณได้รับแบบเงียบ ๆ
นี่เป็นการออกแบบที่ดี และ API อื่นควรลอกตาม

สังเกตด้วยว่าต่างจาก class อีกตัว ตัวนี้ส่ง header ไปเสมอแม้ key จะว่าง
ซึ่งไม่เป็นไร เพราะไม่มี local server จริงจังตัวไหนที่พูด dialect นี้แล้วจะมีปัญหา

```python
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "stream": True,
            "messages": self._to_wire(messages),
        }
        if system:
            payload["system"] = system
```

นี่คือการจัดการความต่างข้อที่หนึ่ง ทุก message ที่มี role เป็น `system` จะถูกดึงออกจาก list
ข้อความถูกเชื่อมด้วย newline เพื่อให้กรณีมีมากกว่าหนึ่งอันก็ยังทำงานได้
แล้วผลลัพธ์กลายเป็น field ระดับบนสุด field นี้จะถูกเพิ่มเมื่อมีอะไรจะใส่เท่านั้น
เพราะการส่ง `"system": ""` อย่างดีที่สุดก็เป็นแค่สัญญาณรบกวน

อีกครึ่งที่คู่กันอยู่ใน `_to_wire` ซึ่งตัด message เหล่านั้นออกจาก list เพื่อไม่ให้ส่งซ้ำสองรอบ

```python
        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]
```

และนั่นคือความต่างข้อที่สอง ในสี่บรรทัด object ของ schema ตัวเดียวกัน
ที่ provider อีกตัวส่งผ่านในชื่อ `parameters` ถูกส่งผ่านที่นี่ในชื่อ `input_schema`
`tools.py` ไม่เคยเปลี่ยน และ `agent.py` ก็ไม่เปลี่ยน
มีแค่ list comprehension นี้เท่านั้นที่รู้ว่ามีคำว่า `input_schema` อยู่ในโลก

### method _to_wire

นี่คือโค้ดที่น่าสนใจที่สุดในบทเรียนนี้ จึงได้พื้นที่อ่านของตัวเอง
หน้าที่ของมันคือรับบทสนทนาในรูปแบบที่ `agent.py` เก็บไว้ในหน่วยความจำ
ซึ่งเป็นรูปแบบทรง OpenAI แล้วผลิตออกมาเป็น wire format ของ Anthropic

```python
    def _to_wire(self, messages):
        wire = []
        for message in messages:
            if message["role"] == "system":
                continue
```

message ที่เป็น system ถูกดึงไปใส่ field ระดับบนสุดแล้ว จึงถูกทิ้งตรงนี้
ถ้าคุณลืมบรรทัดนี้ request จะล้มเหลวพร้อมคำบ่นเรื่อง role ที่ไม่รู้จัก
และข้อความ error จะไม่ชี้มาที่ function นี้อย่างชัดเจนเลย

```python
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
```

นี่คือความต่างข้อที่สาม และ `if` ตรงกลางคือส่วนที่ควรใส่ใจจริง ๆ

เริ่มจากส่วนที่ง่ายก่อน message ที่มี role เป็น `tool` กลายเป็น `tool_result` block
`tool_call_id` กลายเป็น `tool_use_id` และข้อความผลลัพธ์คงเดิม
block นี้ต้องถูกพาโดย message ที่มี role เป็น `user`
เพราะ role นั้นเป็น role เดียวที่รูปแบบ Anthropic มีไว้สำหรับ input ที่มาจากภายนอก model

ทีนี้ส่วนที่ยาก ทำไมผลลัพธ์ tool ตัวที่สองที่ติดกันจึงถูกต่อเข้าไปใน user message เดิม
แทนที่จะเพิ่มเป็น message ใหม่

เหตุผลคือ Anthropic API กำหนดให้ role ใน `messages` ต้องสลับกัน
user message แล้ว assistant message แล้ว user message ต่อกันไปเรื่อย ๆ
user message สองอันติดกันจะถูก server ปฏิเสธ

ดูสิ่งที่ `agent.py` ผลิตออกมาเวลา model ขอ tool สองตัวในเทิร์นเดียว
loop จะเพิ่ม assistant message หนึ่งอันที่มี call ทั้งสอง
แล้วเพิ่ม message ที่มี role เป็น `tool` หนึ่งอันต่อหนึ่ง call
เพราะรูปแบบ OpenAI compatible กำหนดไว้แบบนั้น

```python
[
  {"role": "user",      "content": "Roll two dice."},
  {"role": "assistant", "content": "", "tool_calls": [call_1, call_2]},
  {"role": "tool", "tool_call_id": "call_1", "content": "4"},
  {"role": "tool", "tool_call_id": "call_2", "content": "6"},
]
```

ถ้าแปล message `tool` แต่ละอันให้เป็น user message ของตัวเอง คุณจะได้แบบนี้ ซึ่ง server ปฏิเสธ

```json
[
  {"role": "user", "content": "Roll two dice."},
  {"role": "assistant", "content": [ ... two tool_use blocks ... ]},
  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": "4"}]},
  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_2", "content": "6"}]}
]
```

รวมมันเข้าด้วยกัน ซึ่งคือสิ่งที่โค้ดทำ แล้วคุณจะได้รูปร่างที่ถูกต้อง
assistant หนึ่งเทิร์นขอ tool สองตัว user หนึ่งเทิร์นตอบทั้งสองตัว

```json
[
  {"role": "user", "content": "Roll two dice."},
  {"role": "assistant", "content": [ ... two tool_use blocks ... ]},
  {
    "role": "user",
    "content": [
      {"type": "tool_result", "tool_use_id": "call_1", "content": "4"},
      {"type": "tool_result", "tool_use_id": "call_2", "content": "6"}
    ]
  }
]
```

นี่ไม่ใช่กฎมั่ว ๆ ที่คุณต้องท่องจำ มันตามมาจากการที่รูปแบบทั้งสองไม่ตรงกันเรื่องนิยามของ message
ในทรง OpenAI message คือเหตุการณ์หนึ่งเหตุการณ์ที่เกิดขึ้น ผลลัพธ์สองอันจึงเป็น message สองอัน
ในทรง Anthropic message คือหนึ่งเทิร์นของบทสนทนา และหนึ่งเทิร์นบรรจุหลายอย่างได้
การแปลระหว่างสองรูปแบบจึงต้องเปลี่ยนจำนวน message และการรวมคือจุดที่เรื่องนั้นเกิดขึ้น

เงื่อนไขที่คุมการรวมมีสามส่วน และทุกส่วนสำคัญ

`wire` ต้องไม่ว่าง ไม่อย่างนั้น `wire[-1]` จะ raise `IndexError` ตั้งแต่ message แรก
ผลลัพธ์ของ tool มาเป็นอันแรกไม่ได้อยู่แล้วโดยชอบธรรม
แต่ function แปลที่ crash เมื่อเจอ input ผิดรูป debug ยากกว่า function
ที่ผลิต request ซึ่ง server ปฏิเสธพร้อมข้อความชัดเจน

`wire[-1]["role"] == "user"` กันไม่ให้ผลลัพธ์ถูกต่อเข้าไปในเทิร์นของ assistant

`isinstance(wire[-1]["content"], list)` คือข้อที่แนบเนียนที่สุด
user message แรกในทุกบทสนทนาเป็น string ธรรมดา เพราะมันคือคำถามที่มนุษย์พิมพ์
การต่อ block เข้าไปใน string จะ raise `AttributeError`
และต่อให้ Python ยอม ผลลัพธ์ก็ไม่มีความหมายอยู่ดี การเช็กนี้แยกระหว่าง
"user message ก่อนหน้าเป็น list ของ block ที่ฉันสร้างเอง จึงต่อเพิ่มได้" กับ
"user message ก่อนหน้าเป็นข้อความธรรมดา จึงต้องเริ่มอันใหม่"

```python
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
```

นี่คืออีกครึ่งหนึ่งของความต่างข้อที่สาม คือคำร้องขอ tool ของ assistant เอง
text block ถูกเพิ่มก่อนและเพิ่มเฉพาะเมื่อมีข้อความ
เพราะบาง model พูดหนึ่งประโยคก่อนเรียก tool และบาง model ไม่พูดอะไรเลย
การส่ง `{"type": "text", "text": ""}` จะถูก API ปฏิเสธ ดังนั้น `if` ตัวนี้จึงรับน้ำหนักจริง
ไม่ใช่แค่ความเรียบร้อย

จากนั้นคือ `json.loads(call["function"]["arguments"] or "{}")` จำจากหัวข้อ 2 ได้ว่า
รูปแบบ OpenAI พา argument มาเป็น JSON string ส่วนรูปแบบ Anthropic
พามันมาเป็น object ที่ parse แล้ว `agent.py` เก็บมันไว้เป็น string ด้วย `json.dumps`
และตรงนี้มันถูก parse กลับ

การเดินทางไปกลับแบบนั้นสิ้นเปลืองจริง และควรพูดออกมาตรง ๆ แทนที่จะซ่อนไว้
มันมีอยู่เพราะคอร์สนี้เลือกเก็บบทสนทนาภายในของ agent ไว้ในทรง OpenAI
เนื่องจากนั่นคือทรงที่คุณอ่านมาตั้งแต่ lesson 02 และการเปลี่ยนมันตอนนี้จะบดบังบทเรียนจริง
harness ระดับ production จะนิยามรูปแบบภายในที่เป็นกลางของตัวเอง
ซึ่งไม่ใช่ของ provider ฝ่ายไหน แล้วแปลทั้งสองทางที่ขอบ
ถ้าคุณอยากรู้ว่ามันหน้าตาเป็นอย่างไร แบบฝึกหัดท้ายบทนี้คือให้ลองทำ

```python
            wire.append({"role": message["role"], "content": message["content"]})
        return wire
```

กรณีที่ตกมาถึงตัวสุดท้าย user message ธรรมดาหรือ assistant message
ที่เป็นข้อความธรรมดาจะผ่านไปโดยไม่เปลี่ยน เพราะรูปแบบทั้งสองเห็นตรงกันเรื่องทรงนั้น

### AnthropicProvider ส่วนตัว parse stream

```python
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
```

การจัดการชั้นขนส่งเหมือนกันทุกอย่าง HTTP response ที่อยู่ยาว บรรทัดขึ้นต้นด้วย `data: `
และข้ามทุกอย่างที่เหลือ มีแค่ path ที่เปลี่ยน จาก `/chat/completions` เป็น `/messages`

```python
                    if event.get("type") == "content_block_start":
                        block = event["content_block"]
                        if block.get("type") == "tool_use":
                            blocks[event["index"]] = {
                                "id": block["id"],
                                "name": block["name"],
                                "json": "",
                            }
```

`content_block_start` ของ tool จะเปิดช่องเก็บหนึ่งช่อง id กับชื่อรู้ได้ทันที
ส่วน field `json` เริ่มจากค่าว่างและจะถูกเติมด้วยชิ้นส่วนที่ตามมา
text block ไม่ถูกเก็บเลย เพราะเนื้อหาของมันไหลตรงเข้า `text_parts`
ดังนั้น `blocks` จึงบรรจุแต่ tool call และแปลงเป็น list `calls` ได้เลยโดยไม่ต้องกรอง

`event["index"]` ตรงนี้ทำหน้าที่เดียวกับ `chunk["index"]` ในอีก provider หนึ่ง
สอง dialect ปัญหาเดียวกัน วิธีแก้เดียวกัน

```python
                    elif event.get("type") == "content_block_delta":
                        delta = event["delta"]
                        if delta.get("type") == "text_delta":
                            text_parts.append(delta["text"])
                            if on_text:
                                on_text(delta["text"])
                        elif delta.get("type") == "input_json_delta":
                            blocks[event["index"]]["json"] += delta["partial_json"]
```

ชิ้นส่วนทั้งสองชนิดมาถึงในรูป `content_block_delta` และ `type` ชั้นในเป็นตัวบอกว่าเป็นชนิดไหน
`text_delta` คือคำตอบที่มองเห็นได้ และถูกส่งเข้า callback ทันทีที่มาถึง
ซึ่งเป็นสิ่งที่ทำให้ output ปรากฏแบบสด ส่วน `input_json_delta`
คือเสี้ยวหนึ่งของ string argument และถูกต่อเข้าช่องที่เปิดไว้ก่อนหน้า

event ทุกชนิดที่โค้ดไม่ได้จัดการจะถูกเมินไปเฉย ๆ `message_start`,
`content_block_stop`, `message_delta` และ `message_stop` ผ่านไปโดยไม่มี branch
นั่นเป็นความตั้งใจ เรารู้อยู่แล้วว่าคำตอบจบเมื่อ body ของ response จบ
การไปกิน end marker เหล่านั้นจึงเป็นการเพิ่มโค้ดที่ไม่พิสูจน์อะไร
การเมิน event ที่ไม่รู้จักยังเป็นวิธีที่ทำให้ตัว parse นี้อยู่รอด
เมื่อ provider เพิ่ม event ชนิดใหม่ในภายหลัง

```python
        calls = []
        for _, s in sorted(blocks.items()):
            arguments, error = parse_arguments(s["json"])
            calls.append({"id": s["id"], "name": s["name"], "arguments": arguments, "error": error})
        return "".join(text_parts), calls
```

ตอนจบเป็นแนวคิดเดียวกับอีก class หนึ่งแบบตัวต่อตัว เรียงตาม index
parse string ที่สะสมไว้แต่ละตัวครั้งเดียว แล้วสร้าง dictionary สี่ key ตามที่ข้อตกลงสัญญาไว้
สอง stream ที่ต่างกันมาก แต่รูปร่างเดียวกันที่หน้าประตู

## 7. เปลี่ยน agent loop

เปิด `agent.py` แล้วเทียบกับของ lesson 05 มีสองอย่างที่เปลี่ยน
และหนึ่งในนั้นคือ import ที่หายไป

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
```

**การเปลี่ยนที่หนึ่ง** `from llm import complete_stream` หายไป
และ `provider` กลายเป็นพารามิเตอร์ตัวแรกของ `run`
loop ไม่ได้เลือกอีกต่อไปว่าใครจะเป็นคนตอบ มันถูกบอก โดยใครก็ตามที่เรียกมัน

นั่นคือเทคนิคทั้งหมด และมันมีชื่อที่ฟังดูยิ่งใหญ่กว่าตัวแนวคิดมาก
มันเรียกว่า dependency injection และถ้าคุณเคยหลบคำนี้เพราะมันฟังดูเหมือนต้องมี
framework กับไฟล์ config นี่คือทั้งหมดของมันในประโยคเดียว
แทนที่ function จะยื่นมือออกไปสร้างหรือ import สิ่งที่มันต้องการ สิ่งที่มันต้องการถูกส่งเข้ามาเป็น argument

แค่นั้น `run(provider, ...)` คือ dependency injection
คุณเกือบแน่นอนว่าเคยเขียนมันมาแล้วเป็นร้อยครั้งโดยไม่ได้เรียกชื่อนี้
ทุก function ที่รับ file handle แทนที่จะเปิด path เองก็กำลังทำสิ่งเดียวกัน

**การเปลี่ยนที่สอง** `schemas = [t["function"] for t in tools.SCHEMAS]`
lesson 05 ส่ง `tools.SCHEMAS` ผ่านไปตรง ๆ พร้อมซองห่อทั้งชุด
เพราะ provider ตัวเดียวที่มีอยู่ตอนนั้นต้องการซองนั้น
ตอนนี้ซองห่อกลายเป็นความเห็นของ dialect หนึ่ง loop จึงแกะมันลงมาถึง object ชั้นในที่เป็นกลาง
ซึ่งมี `name`, `description` และ `parameters` แล้วให้แต่ละ provider ใส่ห่อของตัวเอง
class ฝั่ง OpenAI ใส่ซอง `{"type": "function", ...}` กลับเข้าไป
class ฝั่ง Anthropic เปลี่ยนชื่อ `parameters` เป็น `input_schema`

ส่วนที่เหลือในไฟล์ไม่ถูกแตะเลย งานจดบันทึกหลังการเรียก tool เหมือนกับ lesson 05 ทุกอย่าง

```python
        for call in calls:
            if call["error"]:
                result = f"Error: {call['error']}. Send the tool call again."
                print(f"\n[{call['name']} was not run because {call['error']}]")
            else:
                print(f"\n[calling {call['name']} with {call['arguments']}]")
                result = tools.run(call["name"], call["arguments"])
                print(f"[{call['name']} returned {result}]")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
```

loop ยังคงเขียน `{"role": "tool", "tool_call_id": ...}` แม้ตอนที่ provider เป็นตัวของ Anthropic
ซึ่งไม่มี role นั้นอยู่เลย นั่นไม่ใช่ความหลงลืม
loop เก็บบทสนทนาไว้ในรูปร่างภายในแบบเดียว และ provider แปลตอนขาออก
ซึ่งคือ `_to_wire` ทำงานของมัน ถ้า loop ต้องรู้ว่าจะบันทึกด้วยรูปร่างไหน
abstraction ก็จะพังในขั้นตอนสุดท้าย ซึ่งเป็นวิธีที่การ refactor แบบนี้พลาดกันบ่อย

ยังมีอีกหนึ่งความต่างที่พลาดง่าย `agent.py` ของ lesson 05 จบด้วยแบบนี้

```python
if __name__ == "__main__":
    run("What is 2 plus 3?")
```

ของ lesson 06 ไม่มีแบบนั้น และมีไม่ได้ เพราะ `run` เสก provider ขึ้นมาจากอากาศไม่ได้อีกแล้ว
ต้องมีใครสักคนข้างนอกเป็นคนตัดสิน นั่นไม่ใช่การสูญเสีย
มันคือจุดประสงค์ของการเปลี่ยนแปลงที่ถูกทำให้มองเห็นได้
การตัดสินใจว่าจะเรียกบริการไหนย้ายออกจาก loop ขึ้นไปอยู่ที่ผู้เรียก ซึ่งเป็นที่ของมัน

### สิ่งที่คุณได้จากเรื่องนี้

ผลตอบแทนไม่ใช่ความสามารถในการใช้ Claude นั่นเป็นผลพลอยได้ที่ดี
ผลตอบแทนคือตอนนี้ loop มีรอยต่อแล้ว

**ทดสอบได้โดยไม่ต้องมีเครือข่าย** test สามารถยื่น object เล็ก ๆ ที่มี method `stream`
ซึ่งคืนคำตอบสำเร็จรูปจาก list ให้ `run` แล้วตรวจว่า loop ต่อ message ถูกต้องไหม
มันหยุดเมื่อไม่มี call ไหม มันป้อน parse error กลับไปไหม และ `max_turns` ทำให้เกิด error ไหม
ทั้งหมดนี้เสร็จในหน่วยไมโครวินาที ไม่มี HTTP ไม่มี server และไม่ต้องสตาร์ต process ปลอม
fake server ของโปรเจกต์นี้ดีมาก แต่ก็ยังช้ากว่าและหนักกว่า stub object ห้าบรรทัด

```python
class ScriptedProvider:
    def __init__(self, turns):
        self.turns = list(turns)
        self.seen = []

    def stream(self, messages, tools=None, on_text=None):
        self.seen.append(list(messages))
        return self.turns.pop(0)
```

ยื่นตัวนั้นให้ `run` แล้วคุณ assert บทสนทนาที่ loop สร้างขึ้นได้แบบเป๊ะ ๆ
object นั้นเป็น provider ที่ถูกต้องตามมาตรฐานเดียวที่สำคัญ คือมันทำตามข้อตกลง

**นำกลับมาใช้ได้โดยไม่ต้องแก้** บทเรียนในอนาคตที่รัน model ราคาถูก
เพื่อสรุปบทสนทนายาว ๆ ก็เรียก `run` ตัวเดิมด้วย provider คนละตัว
test ที่ต้องการ output แน่นอนก็เรียกมันด้วย provider แบบสคริปต์
benchmark ที่รัน prompt เดียวกันกับสี่บริการก็เรียกมันสี่ครั้งใน loop
ไม่มีอันไหนต้องแก้ `agent.py`

**พัฒนา provider แยกกันได้** provider ใหม่คือ class ใหม่ใน `providers.py`
ไม่มีอะไรที่ทำงานอยู่แล้วถูกแตะ จึงไม่มีอะไรที่ทำงานอยู่แล้วพังได้
เทียบกับการเพิ่ม branch ที่สี่เข้าไปใน function ที่ใช้ร่วมกัน

## 8. รัน check.py

`check.py` คือโปรแกรมที่เล็กที่สุดที่แสดงข้ออ้างของบทเรียนนี้ได้

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
```

อ่าน loop ที่อยู่ล่างสุด มี `PROMPT` เดียว `run` เดียว และ provider สองตัว
ที่สร้างจาก environment variable สามตัวเดียวกัน การตรวจสอบเหมือนกันทั้งสองฝั่ง
เพราะข้ออ้างทั้งหมดคือผลลัพธ์ไม่ขึ้นกับ dialect
สังเกตด้วยว่า `check.py` ไม่ได้ส่ง `on_text` ของตัวเองเลย และมันไม่จำเป็นต้องส่ง
`agent.py` เป็นคนจัดหา callback สำหรับพิมพ์ และ `check.py` สนใจแค่ string ที่คืนมา

รันจากในโฟลเดอร์ของบทเรียน หรือรันทุกบทเรียนพร้อมกันจาก root ของ repository

```bash
cd lessons/06-provider-abstraction
python check.py
```

```bash
python ci/run_lessons.py
```

การรันที่ผ่านจะได้แบบนี้

```text

[calling add with {'a': 2, 'b': 3}]
[add returned 5]
The tool returned 5.
OK the same loop worked with the openai provider

[calling add with {'a': 2, 'b': 3}]
[add returned 5]
The tool returned 5.
OK the same loop worked with the anthropic provider
```

สองครึ่งเหมือนกันทุกอย่างยกเว้นคำสุดท้าย ซึ่งเป็นผลลัพธ์ที่คุณต้องการ
บรรทัดว่างบนสุดของแต่ละครึ่งมาจาก `\n` ที่อยู่หน้าข้อความ `[calling ...]`
ซึ่งปกติทำหน้าที่คั่นคำตอบที่ stream มากับร่องรอยของ tool
ในเทิร์นที่ model ตรงไปเรียก tool เลยจึงไม่มีข้อความอยู่ก่อนหน้า newline นั้นจึงตกลงบนบรรทัดว่าง

### ทำไมมันผ่านได้โดยไม่ต้องมีเครือข่าย

เหตุผลที่ทั้งสองครึ่งทำงานได้คือ fake server ของโปรเจกต์นี้ที่
`src/agentpath/testing/mock_server.py` พูดได้ทั้งสอง dialect
ตัวจัดการ request ของมันแยกสาขาตาม path

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
```

function `decide` ตัวเดียวคิดว่าจะตอบอะไร แล้วตัวจัดรูปแบบสองตัว
ก็เรนเดอร์คำตอบเดียวกันนั้นออกมาเป็นสอง dialect
นั่นคือภาพสะท้อนของสิ่งที่คุณเพิ่งสร้างใน `providers.py`
ซึ่งเป็นความสมมาตรที่น่าพอใจ และยังเป็นเหตุผลที่ check นี้เป็นการทดสอบจริง ไม่ใช่การพูดวนซ้ำ
ถ้าการแปลของคุณผิดในทิศทางใดทิศทางหนึ่ง ครึ่งหนึ่งจะล้มและอีกครึ่งจะผ่าน
และความต่างนั้นจะบอกคุณว่าต้องไปดูตรงไหน

`decide` ยังรองรับผลลัพธ์ tool ทั้งสองรูปร่างด้วย ซึ่งควรดูไว้
เพราะมันพิสูจน์ว่าตรรกะการรวมจากหัวข้อ 6 มาถึงอย่างถูกต้อง

```python
    if role == "tool":
        return f"The tool returned {content}.", []

    if isinstance(content, list):
        for block in content:
            if block.get("type") == "tool_result":
                return f"The tool returned {block.get('content', '')}.", []
```

สาขาแรกดักผลลัพธ์ที่เป็น message ทรง OpenAI สาขาที่สองดัก user message ทรง Anthropic
ที่มี `tool_result` block อยู่ข้างใน ทั้งสองผลิตประโยคเดียวกัน
ซึ่งเป็นเหตุผลที่ทั้งสองครึ่งของ check พิมพ์ `The tool returned 5.` และทั้งคู่มีเลข `5` อยู่

### รันกับบริการจริง

ทุกอย่างข้างบนรันแบบ offline ถ้าจะชี้ไปที่ของจริง ให้ตั้ง environment variable สามตัวแล้วรันไฟล์เดิม

สำหรับบริการแบบ OpenAI compatible รวมถึง Ollama ในเครื่อง base URL คือตัวที่ลงท้ายด้วย `/v1`
และ key ใส่เข้าไปเป็น bearer token

```bash
cd lessons/06-provider-abstraction
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen2.5:14b
export AGENTPATH_API_KEY=
python check.py
```

```powershell
cd lessons\06-provider-abstraction
$env:AGENTPATH_BASE_URL = "http://localhost:11434/v1"
$env:AGENTPATH_MODEL = "qwen2.5:14b"
$env:AGENTPATH_API_KEY = ""
python check.py
```

สำหรับ API ของ Anthropic เอง base URL และชื่อ model ต่างออกไป และต้องใช้ key จริง

```bash
cd lessons/06-provider-abstraction
export AGENTPATH_BASE_URL=https://api.anthropic.com/v1
export AGENTPATH_MODEL=claude-sonnet-4-5
export AGENTPATH_API_KEY=your-key-here
python check.py
```

```powershell
cd lessons\06-provider-abstraction
$env:AGENTPATH_BASE_URL = "https://api.anthropic.com/v1"
$env:AGENTPATH_MODEL = "claude-sonnet-4-5"
$env:AGENTPATH_API_KEY = "your-key-here"
python check.py
```

อย่า commit key นั้นเด็ดขาด เก็บมันไว้ใน shell profile ของคุณ
หรือในไฟล์ในเครื่องที่ระบุไว้ใน `.gitignore`

### คำเตือน อ่านตรงนี้ก่อนจะแจ้ง bug

เมื่อคุณชี้ไปที่บริการจริงหนึ่งตัว จะมีแค่ provider ที่ตรงกันเท่านั้นที่ทำงานได้
อีกตัวจะล้มเหลว และนั่นคือพฤติกรรมที่ถูกต้อง ไม่ใช่ข้อบกพร่องในโค้ดของคุณ

เหตุผลชัดเจนทันทีที่พูดออกมาดัง ๆ มี `AGENTPATH_BASE_URL` แค่ตัวเดียว
และมันระบุ endpoint ของบริษัทเดียว endpoint จริงพูดได้ dialect เดียว
fake server ผิดปกติตรงที่มันพูดได้สอง dialect ซึ่งเป็นความหรูหราที่มีแต่ test double เท่านั้นที่จ่ายไหว

ดังนั้นคาดหวังผลลัพธ์รูปแบบนี้เมื่อชี้ไปที่ endpoint แบบ OpenAI compatible ตัวจริง

```text
OK the same loop worked with the openai provider
Traceback (most recent call last):
  ...
httpx.HTTPStatusError: Client error '404 Not Found' for url '.../v1/messages'
```

และรูปแบบนี้เมื่อชี้ไปที่ Anthropic ตัวจริง

```text
Traceback (most recent call last):
  ...
httpx.HTTPStatusError: Client error '404 Not Found' for url '.../v1/chat/completions'
```

provider ตัวแรกผ่าน ตัวที่สองได้ 404 หรือ 401 จาก `raise_for_status` แล้วสคริปต์ก็หยุด
404 หมายความว่า path นั้นไม่มีอยู่บน host ตัวนั้น ซึ่งก็คือประเด็นพอดี
401 หมายความว่า auth header เป็นคนละชนิด ซึ่งเป็นประเด็นเดียวกันแต่สวมตัวเลขคนละตัว

ถ้าจะทดสอบ provider ตัวเดียวกับบริการจริงตัวเดียว ให้ comment อีกบรรทัดหนึ่งใน list ใน `check.py` ทิ้ง

```python
    for name, provider in [
        ("openai", OpenAICompatProvider(base_url, api_key, model)),
        # ("anthropic", AnthropicProvider(base_url, api_key, model)),
    ]:
```

ถ้าคุณอยากให้ทั้งสองตัวรันกับบริการจริงพร้อมกัน คุณต้องมี environment variable ชุดที่สอง
และ base URL ตัวที่สอง ซึ่งเป็นแบบฝึกหัดที่มีประโยชน์จริง
constructor รับทุกอย่างแบบระบุชัดอยู่แล้ว มันจึงเป็นการเปลี่ยนใน `check.py` เพียงไฟล์เดียว
ไม่มีอะไรใน `providers.py` หรือ `agent.py` ต้องขยับ
ซึ่งเป็นหลักฐานอีกชิ้นว่ารอยต่อถูกตัดไว้ถูกที่

มีความล้มเหลวอีกสองแบบที่ควรบอกไว้ล่วงหน้า

ถ้า model จริงตอบว่า `5` ด้วยคำพูดโดยไม่เรียก tool คุณจะได้บรรทัด `FAIL`
เรื่องการเดินทางไปกลับ และหัวข้อ 9 ของ lesson 03 คือที่ที่ควรไปดู
model เล็ก ๆ ในเครื่องมักทำแบบนี้ และมันเป็นปัญหาความสามารถของ model ไม่ใช่ปัญหาท่อ

ถ้าคุณเห็น `KeyError: 'AGENTPATH_BASE_URL'` แปลว่าตัวแปรยังไม่ถูกตั้งใน shell นี้
การตั้งค่าใน terminal หนึ่งไม่ได้ตั้งให้อีก terminal หนึ่ง

## 9. จบภาคหนึ่ง

หยุดสักครู่แล้วดูสิ่งที่คุณมี

หกบทเรียนที่แล้วคุณไม่มีอะไรเลย ตอนนี้คุณมีโปรแกรมที่ทำทุกอย่างต่อไปนี้
ในโค้ด Python ประมาณสามร้อยบรรทัดที่คุณอ่านจากบนลงล่างได้ และไม่มี framework อยู่ในนั้นเลย

- มันส่งบทสนทนาไปยัง language model ผ่าน HTTP แล้วอ่านคำตอบ
- มันเก็บประวัติ ทำให้ model ดูเหมือนจำได้ และคุณรู้แน่ชัดว่าภาพลวงนั้นเกิดขึ้นได้อย่างไรและมีต้นทุนเท่าไร
- มันอธิบาย function ของ Python ของคุณด้วย JSON Schema แล้วส่งไปด้วย
- มันอ่านคำร้องขอที่มีโครงสร้างสำหรับ function เหล่านั้นกลับมา แล้วรัน function เอง
  ในโค้ดที่คุณเขียนและตรวจดูได้
- มันส่งผลลัพธ์กลับเข้าบทสนทนาแล้ววน loop ทำให้ model ใช้สิ่งที่มันเรียนรู้
  ต่อ tool หนึ่งเข้ากับอีก tool หนึ่ง และกู้คืนจาก error ที่มันก่อขึ้นเองได้
- มันหยุดเมื่อ model ตอบเป็นคำพูด และมันปฏิเสธที่จะวนไม่รู้จบ
- มัน stream ทำให้ข้อความปรากฏขณะถูกผลิต และมันประกอบ argument ของ tool
  กลับจากชิ้นส่วน JSON ที่ยังไม่ถูกต้องจนกว่าชิ้นสุดท้ายจะมาถึง
- มันคุยกับ API ของ provider สองตัวที่ต่างกันสิ้นเชิงผ่าน interface เดียว และ loop แยกไม่ออกว่าเป็นตัวไหน

บรรทัดสุดท้ายนั่นแหละที่ทำให้ทุกอย่างที่เหลืออยู่ทน ภูมิทัศน์ของ provider จะเปลี่ยนไปเรื่อย ๆ
บริษัทใหม่จะเกิด รูปแบบจะเลื่อนไหล บริการที่คุณพึ่งพาจะขึ้นราคา
หรือล่มในเช้าวันที่คุณต้องเดโม agent loop ของคุณไม่สนใจ
เพราะสิ่งเดียวที่มันรู้วิธีทำคือเรียก `stream` แล้วอ่าน tuple

ที่สำคัญกว่านั้น ตอนนี้คุณรู้แล้วว่า agent จริง ๆ คืออะไร มันคือ loop หนึ่งอัน
list ของ messages หนึ่งอัน dictionary ของ function หนึ่งอัน และ `if` หนึ่งตัว
ไม่มีกลไกลับซ่อนอยู่ ครั้งต่อไปที่คุณอ่านเอกสารของ framework
คุณจะชี้ไปที่แต่ละแนวคิดของมันได้แล้วบอกว่ามันกำลังห่อสิ่งไหนในห้าอย่างนี้อยู่
นั่นคือความได้เปรียบถาวรเหนือคนที่เรียน framework ก่อน

### ภาคสองเพิ่มอะไร

ทุกอย่างที่ผ่านมาปลอดภัยโดยบังเอิญ tool ที่มีคือเครื่องคิดเลขกับการทอยลูกเต๋า
สิ่งเลวร้ายที่สุดที่ bug ทำได้คือคืนตัวเลขผิด

ภาคสองจะให้มือกับ agent คุณจะสร้าง tool ที่อ่าน เขียน list และแก้ไฟล์จริงบนดิสก์ของคุณ
รวมถึงการแก้ไขที่แทนที่ข้อความบางส่วนแทนที่จะเขียนทั้งไฟล์ใหม่
เพราะการบังคับให้ model พิมพ์ทั้งไฟล์ใหม่เพื่อเปลี่ยนบรรทัดเดียวนั้นช้า แพง และผิดพลาดง่าย
และ harness ที่จริงจังทุกตัวหลีกเลี่ยงมัน คุณจะสร้าง tool ที่รันคำสั่ง shell จริง
พร้อม timeout และเก็บ output คุณจะสร้าง tool สำหรับค้นหา
ทั้งตัวจับคู่ชื่อไฟล์และตัว grep เนื้อหา เพื่อให้ agent หาของใน codebase เองได้
แทนที่จะต้องถูกบอกว่าให้ดูตรงไหน จากนั้นเป็นบทที่ว่าด้วยอะไรควรอยู่ใน system prompt
อะไรควรอยู่ใน user message และอะไรควรอยู่ในคำอธิบาย tool
ซึ่งเป็นบทที่เปลี่ยน agent ที่ทำงานได้ให้กลายเป็น agent ที่มีประโยชน์
ภาคสองจบด้วยการประกอบทุกอย่างเข้าเป็น coding agent เล็ก ๆ ที่เปลี่ยนโค้ดในโฟลเดอร์ได้จริง

และนี่คือจุดที่คำถามเรื่องความปลอดภัยเริ่มขึ้น เพราะมันต้องเริ่ม

lesson 03 ให้สัญญาเรื่องนี้ไว้ และถึงเวลาทวงสัญญาแล้ว
ช่องว่างระหว่างการที่ model ร้องขอกับการที่โค้ดทำงานเป็นของคุณทั้งหมด
และจนถึงตอนนี้คุณยังไม่มีเหตุผลต้องใช้มัน
ตั้งแต่วินาทีที่ tool ลบไฟล์ได้หรือรันคำสั่งได้ ช่องว่างนั้นคือสิ่งเดียวที่กั้นระหว่าง
การเดาผิดอย่างมั่นใจกับบ่ายวันที่แย่ ดังนั้น shell tool ในภาคสองจึงมาพร้อม
prompt ยืนยันตั้งแต่วันแรกที่มันมีตัวตน ไม่ใช่ในฐานะการปรับปรุงภายหลัง
คุณจะได้พบทางออกฉุกเฉินที่ทำให้การตรวจอัตโนมัติเป็นไปได้ คือ
`AGENTPATH_AUTO_APPROVE` และคุณจะเห็นว่าสวิตช์ที่ปิดคำถามนั้น
เป็นการตัดสินใจเชิงออกแบบที่ควรคิดให้ดีในตัวมันเอง
สวิตช์นั้นจะเติบโตเป็นระบบ permission เต็มรูปแบบในภาคสาม

คุณจะได้พบภัยคุกคามที่ทำให้คนประหลาดใจด้วย เมื่อ agent อ่านไฟล์และ output ของคำสั่งได้แล้ว
ข้อความที่คนอื่นเขียนจะไหลเข้ามาในบทสนทนา และ model ปฏิบัติกับมันเหมือน input
ไฟล์ใน repository อาจมีประโยคที่จ่าหน้าถึง agent นั่นคือ prompt injection
และมันมาถึงผ่านผลลัพธ์ของ tool ไม่ใช่ผ่านผู้ใช้ ภาคสองแนะนำมัน และภาคสามจัดการมันอย่างจริงจัง

ไม่มีอะไรในนั้นที่ต้องเปลี่ยนสิ่งที่คุณสร้างไว้ตรงนี้ loop ยังอยู่
interface ของ provider ยังอยู่ มีแค่ tool เท่านั้นที่กลายเป็นของจริง

### แบบฝึกหัดก่อนไปต่อ

สามข้อ เรียงตามความยากเพิ่มขึ้น ทุกข้อเป็นทางเลือก
และทุกข้อสอนบางอย่างที่การอ่านอย่างเดียวสอนไม่ได้

**ข้อหนึ่ง** เขียน `ScriptedProvider` จากหัวข้อ 7 แล้วใช้มันทดสอบ `run` โดยไม่ใช้เครือข่ายเลย
ให้มันคืน tool call ในเทิร์นแรกและคืนข้อความในเทิร์นที่สอง
แล้ว assert list ของ message ที่ loop สร้างขึ้นแบบเป๊ะ ๆ
จากนั้นให้มันคืน call ที่ argument parse ไม่ผ่าน แล้วตรวจว่า loop ส่ง error กลับไปแทนที่จะ crash

**ข้อสอง** เพิ่ม class ของ provider ตัวที่สามสำหรับบริการที่คุณใช้จริง
หรือคิด dialect ขึ้นมาเองแล้วเพิ่ม branch ของมันเข้าไปใน fake server จับเวลาตัวเองด้วย
ถ้าใช้เวลาเกินครึ่งชั่วโมง แปลว่า interface มีรูรั่ว และการหารูนั้นคือแบบฝึกหัดตัวจริง

**ข้อสาม** เปลี่ยนรูปแบบบทสนทนาภายใน ตอนนี้ `agent.py` เก็บประวัติในทรง OpenAI
ซึ่งทำให้ `OpenAICompatProvider` แทบไม่ต้องทำอะไร และผลัก
งานทั้งหมดไปให้ `_to_wire` รวมถึงการเดินทางไปกลับด้วย `json.dumps` และ `json.loads`
บน argument ของ tool ให้นิยามรูปแบบที่เป็นกลางของคุณเอง
อะไรสักอย่างที่มี role มีข้อความ และมี list ของ tool call ที่ใช้ dictionary จริงเป็น argument
แล้วให้ provider ทั้งสองมี method `_to_wire` โค้ดจะยาวขึ้นเล็กน้อยและสมมาตรขึ้นมาก
และคุณจะเข้าใจว่าทำไม harness จริงจึงทำแบบนั้น

ไปต่อภาคสองกันเลย
