# บทที่ 12 provider ที่ต่างกัน และ interface ที่ทำให้ไม่ต้องสน

จบบทนี้คุณจะมีโค้ดที่สลับจากผู้ให้บริการเจ้าหนึ่งไปอีกเจ้าหนึ่งได้ด้วยการ
เปลี่ยนค่าตัวแปรตัวเดียว โดยที่ agent loop (วงรอบของเอเจนต์ คือลูปที่ถาม
model แล้วรัน tool สลับกันไปจนได้คำตอบ) ไม่มีบรรทัดไหนขยับ และคุณจะมีตาราง
สี่บรรทัดที่ครอบคลุมความต่างทั้งหมดที่ต้องเขียนโค้ดรับมือ ไม่ใช่สี่สิบบรรทัด

ภาค 1 บอกไปแล้วว่า model (โมเดล คือตัวประมวลผลภาษาที่เราเรียกใช้ผ่านเครือข่าย)
คือ HTTP endpoint หนึ่งตัว บทนี้คือสิ่งที่เกิดขึ้นเมื่อคุณมี endpoint สองตัว
ที่ทำงานเหมือนกันแต่พูดคนละภาษา

## 1. ความต่างจริงมีสี่จุด และนับได้

คนที่ยังไม่เคยเขียน provider (คือคลาสของเราที่รู้วิธีคุยกับ API เจ้าหนึ่ง)
ด้วยมือ มักคิดว่าการรองรับสองเจ้าคือการเขียนโปรแกรมสองตัว ความจริงคือ
มันคือการแปลสี่จุด

ทั้งเล่มนี้ใช้สองคำแยกกัน `provider` คือคลาสในโค้ดของเรา ส่วนผู้ให้บริการ
คือบริษัทที่เป็นเจ้าของ API ปลายทาง หนึ่ง provider คุยกับหนึ่งผู้ให้บริการ
แต่มันคนละชั้นกัน และหัวข้อที่ 6 คือจุดที่ความต่างนั้นสำคัญที่สุด

ในโปรเจกต์นี้ไฟล์ทั้งสองอยู่ที่ `src/agentpath/providers/openai_compat.py`
ซึ่งยาว 143 บรรทัด กับ `src/agentpath/providers/anthropic.py` ซึ่งยาว
195 บรรทัด รวมคอมเมนต์และ docstring ทั้งคู่ และนี่คือสิ่งที่ต่างกันจริงๆ

| จุดที่ต่าง | OpenAI format | Anthropic format |
| --- | --- | --- |
| system prompt | message ที่มี role เป็น system | field ต่างหากชื่อ `system` |
| key ของ tool schema | `parameters` | `input_schema` |
| ผลลัพธ์ของ tool เดินทางกลับยังไง | message ที่มี role เป็น `tool` | content block ใน message ของ user |
| รูปแบบ stream | `choices[0].delta` | typed event เช่น `content_block_delta` |

สี่บรรทัดนี้คือทั้งหมด ทุกอย่างที่เหลือคือ URL กับชื่อ header ซึ่งไม่ใช่
ความต่างเชิงความคิด มันคือค่าคงที่

**ทำไมถึงคุ้มที่จะนับให้ได้** เพราะรายการที่นับได้แปลว่าคุณรู้ว่าเมื่อไหร่
คุณทำครบแล้ว ถ้าคุณคิดว่าความต่างมีไม่จำกัด คุณจะเขียน abstraction
(นามธรรม คือชั้นที่ซ่อนรายละเอียดของข้างใต้ไว้) ที่ใหญ่เกินความจำเป็น
เพื่อรับมือกับความต่างที่คุณจินตนาการขึ้นเอง

## 2. system prompt เป็นข้อความ หรือเป็นช่องแยก

ในรูปแบบ OpenAI คำสั่งของระบบคือ message ธรรมดาที่มี role เป็น system
มันนั่งอยู่หัว list เหมือนข้อความอื่นทุกประการ

ในรูปแบบ Anthropic มันไม่ใช่ message เลย มันเป็น field ที่อยู่ระดับเดียวกับ
`model` และ `max_tokens` ในตัว payload (สัมภาระ คือ JSON ก้อนที่ส่งไปกับ
คำขอ) ซึ่งแปลว่าตอนแปลง เราต้องดึงมันออกจาก list ก่อน แล้วค่อยส่งไปคนละที่

โค้ดที่ทำสองอย่างนั้นอยู่ต้นฟังก์ชัน `stream` ของ Anthropic บรรทัดแรกรวบ
ทุก system message เข้าด้วยกันด้วยการต่อบรรทัด แล้วใส่ลงไปใน payload
เฉพาะเมื่อมีของจริง

```python
        system = "\n".join(m.content for m in messages if m.role == "system")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "stream": True,
            "messages": to_wire(messages),
        }
        if system:
            payload["system"] = system
```

และอีกครึ่งหนึ่งของงานนี้อยู่ในฟังก์ชันแปลง ซึ่งต้องข้าม system message
ไม่ให้หลุดเข้าไปใน list ของ message อีกที ไม่อย่างนั้นคำสั่งจะถูกส่งไปสองรอบ

```python
        if message.role == "system":
            continue
```

**ทำไม Anthropic ถึงแยกออกมา** เพราะคำสั่งของระบบไม่ใช่สิ่งที่คนพูด และ
การให้มันมี role เดียวกับบทสนทนาทำให้เส้นแบ่งระหว่างคำสั่งของนักพัฒนา
กับข้อความของผู้ใช้จางลง ซึ่งเป็นเส้นที่บทที่ 5 บอกว่าห้ามให้จาง
การแยกเป็นคนละช่องคือการทำให้เส้นนั้นบังคับใช้ได้จากโครงสร้าง

**ทำไม `max_tokens` ถึงอยู่ในนั้นเสมอ** เพราะฝั่ง Anthropic บังคับ ไม่ใส่
แล้วได้ HTTP 400 (รหัสสี่ร้อย คือคำตอบที่บอกว่าคำขอผิดรูป) ทันที ส่วนฝั่ง
OpenAI ไม่บังคับ นี่คือความต่างที่ไม่ต้องคิดอะไรมาก แค่ใส่ค่าคงที่ไว้

## 3. tool schema ต่างกันที่ชื่อ key คำเดียว

รูปแบบ OpenAI ห่อ schema (สคีมา คือคำอธิบายรูปร่างของข้อมูลในรูป JSON)
ของ tool (เครื่องมือ คือฟังก์ชันที่ model ขอให้เรารันได้) ไว้ในกล่องอีกชั้น
ที่บอกว่านี่คือ function แล้วรายละเอียดของ argument อยู่ใต้ key ชื่อ
`parameters`

```python
        if tools:
            payload["tools"] = [{"type": "function", "function": tool} for tool in tools]
```

รูปแบบ Anthropic ไม่มีกล่องชั้นนอก และรายละเอียดของ argument อยู่ใต้ key
ชื่อ `input_schema` แทน ซึ่งแปลว่าต้องประกอบ dict ใหม่ทีละตัว

```python
        if tools:
            payload["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["parameters"],
                }
                for tool in tools
            ]
```

สังเกตว่าทั้งสองรับ input ก้อนเดียวกัน คือ list ของ dict ที่ `ToolRegistry`
คายออกมา ซึ่งมี `name` `description` และ `parameters` เสมอ รูปแบบกลางนั้น
ไม่ได้ตรงกับเจ้าไหนโดยบังเอิญ มันเป็นรูปแบบของเราเอง และการมีรูปแบบของ
ตัวเองคือสิ่งที่ทำให้การเพิ่มเจ้าที่สามไม่ต้องแก้ของเดิม

**ทำไมความต่างข้อนี้ถึงไม่อันตราย** เพราะมันประกาศตัวเองทันที ใส่ key ผิด
แล้วคุณได้ 400 ในการรันครั้งแรก แก้แล้วจบ ความต่างที่อันตรายคือความต่างที่
เงียบ ซึ่งจะพูดถึงในหัวข้อที่ 8 และ 9

## 4. ผลลัพธ์ของ tool กลับบ้านคนละทาง

นี่คือจุดที่ต่างกันจริงในเชิงรูปร่างของข้อมูล ไม่ใช่แค่ชื่อ key

ในรูปแบบ OpenAI ผลลัพธ์ของ tool คือ message หนึ่งอันที่มี role เป็น `tool`
มันเป็นสมาชิกของ list เท่าเทียมกับ message อื่น ฟังก์ชันแปลงจึงทำงานทีละ
message ได้ และนี่คือทั้งฟังก์ชัน

```python
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
```

รับหนึ่ง message คืนหนึ่ง dict ไม่ต้องรู้ว่ามีอะไรอยู่ก่อนหน้าหรือหลัง

ในรูปแบบ Anthropic ไม่มี role ชื่อ `tool` ผลลัพธ์คือ content block
(บล็อกเนื้อหา คือชิ้นส่วนหนึ่งชิ้นในข้อความที่มีหลายชิ้น) ชนิด `tool_result`
ที่ต้องไปนั่งอยู่ใน message ของ user และถ้า model ขอเรียก tool สามตัวใน
ข้อความเดียว ผลลัพธ์ทั้งสามต้องรวมอยู่ใน user message อันเดียวกัน ไม่ใช่
สาม message

ผลคือฟังก์ชันแปลงของ Anthropic ทำงานทีละ message ไม่ได้ มันต้องเห็นทั้ง list
และต้องจำได้ว่าเพิ่งเขียนอะไรลงไป

```python
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
```

เทียบสองฟังก์ชันแล้วจะเห็นความต่างที่สำคัญกว่าชื่อ key คือ signature ของ
ฟังก์ชัน อันแรกรับ `Message` อันเดียว อันหลังรับ `list[Message]` เพราะการ
รวม block เข้า message ก่อนหน้าเป็นสิ่งที่ทำไม่ได้ถ้ามองเห็นทีละอัน

**ทำไมต้องเช็คสามเงื่อนไขก่อนรวม** บรรทัดที่เช็คว่ามีของอยู่แล้ว และตัว
สุดท้ายเป็น user และ content ของมันเป็น list คือการกันสามกรณีคนละอย่าง
คือ list ว่าง กรณีที่ตัวก่อนหน้าเป็น assistant และกรณีที่ตัวก่อนหน้าเป็น
user ที่ถือข้อความธรรมดาซึ่ง content เป็นสตริงไม่ใช่ list การเผลอ append
ลงไปในสตริงจะพังทันที

**ทำไมยังส่ง argument เป็น object ตรงๆ ได้ในฝั่งหนึ่งแต่ต้อง `json.dumps`
ในอีกฝั่ง** เพราะ OpenAI นิยามให้ argument เดินทางเป็นสตริง JSON ส่วน
Anthropic นิยามให้เป็น object ที่แกะแล้ว นี่คืออีกความต่างที่เป็นค่าคงที่
ไม่ใช่ความคิด แต่มันคือความต่างที่ทำให้ code ที่คัดลอกข้ามฝั่งพังเงียบๆ
ถ้าไม่รู้

## 5. stream ที่ตัวหนึ่งส่ง delta อีกตัวส่ง event ที่มีชนิด

สามข้อข้างบนเป็นเรื่องรูปร่างของบทสนทนา ข้อนี้เป็นเรื่องรูปร่างของสาย

ฝั่ง OpenAI ส่ง chunk ที่หน้าตาเหมือนคำตอบเต็มที่ถูกหั่น ทุก chunk มี
`choices` และข้างในมี `delta` (เดลตา คือส่วนที่เพิ่มขึ้นมาจากครั้งก่อน)
ข้อความอยู่ที่ `delta.content` และชิ้นส่วนของ argument อยู่ที่
`delta.tool_calls` การอ่านจึงเป็นการเจาะลงไปตามพาธเดิมทุกครั้ง

```python
                delta = chunk["choices"][0].get("delta", {})
                if delta.get("content"):
                    text_parts.append(delta["content"])
                    yield TextDelta(text=delta["content"])
```

ฝั่ง Anthropic ส่ง event (เหตุการณ์ คือข้อความบอกว่าเกิดอะไรขึ้น ณ ขณะนั้น)
ที่มีชนิดกำกับ คุณจะได้ `message_start` ก่อน แล้ว `content_block_start`
ตอนเปิด block ใหม่ แล้ว `content_block_delta` เรื่อยๆ การอ่านจึงเป็นการ
แยกตามชนิดก่อน แล้วค่อยดูข้างใน

```python
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
```

**ข้อดีที่ซ่อนอยู่ในรูปแบบที่มีชนิด** คือ event ชนิดที่เราไม่รู้จักจะตกลง
พื้นเงียบๆ โดยไม่พัง ผู้ให้บริการเพิ่มชนิดใหม่พรุ่งนี้ parser ตัวนี้ยัง
ทำงานได้ ส่วนรูปแบบที่เจาะพาธตรงๆ จะพังทันทีถ้าโครงสร้างขยับ นี่คือเหตุผล
ที่โค้ดฝั่ง Anthropic ใช้ `elif` ต่อกันแทนที่จะยกเว้นสิ่งที่ไม่รู้จัก

**สิ่งที่เหมือนกันทั้งสองฝั่ง** คือ argument ของ tool มาเป็นชิ้นๆ ไม่ใช่
ก้อนเดียว ทั้งคู่จึงต้องมี dict ที่เอาไว้สะสมชิ้นส่วนตาม index แล้วค่อย
แปลงเป็น JSON ตอนจบ และทั้งคู่ใช้ `parse_arguments` ตัวเดียวกันจาก
`base.py` เพราะปัญหาที่ต้องแก้เป็นปัญหาเดียวกัน คือ model ที่หมดโควตา
output กลางคันจะส่ง JSON ที่ขาดครึ่ง

## 6. interface ที่มีเมธอดเดียว

ตอนนี้เรามีความต่างสี่จุดแล้ว คำถามคือจะเอาไปซ่อนไว้ที่ไหน คำตอบคือ
interface (อินเทอร์เฟซ คือข้อตกลงเรื่องรูปร่างของการเรียก) และในโปรเจกต์นี้
มันเล็กจนน่าตกใจ

```python
class Provider:
    def stream(self, messages: list[Message], tools: list[dict] | None = None) -> Iterator:
        raise NotImplementedError
```

หนึ่งเมธอด รับ list ของ message กับ list ของ schema คืน iterator ของ event
จบ

ข้อตกลงที่ไม่ได้เขียนเป็นโค้ดแต่สำคัญเท่ากันอยู่ใน docstring ของไฟล์

```python
"""The one interface every provider implements.

A provider turns a conversation into a stream of events. It yields TextDelta
while the assistant is speaking and exactly one TurnDone at the end that
carries the finished message, including any tool calls the model asked for.

A provider never runs a tool. Running tools belongs to the agent loop, and
keeping that line clean is what lets both providers share one loop.
"""
```

ประโยคสุดท้ายคือเส้นที่ทำให้เรื่องทั้งหมดนี้ทำงาน provider ไม่เคยรัน tool
มันแค่บอกว่า model ขออะไร ส่วนการตัดสินใจว่าจะรันไหม รันยังไง และเอาผล
ไปไว้ไหน เป็นงานของ loop ทั้งหมด

ผลของเส้นนั้นเห็นได้จากโค้ดใน `agent.py` ซึ่งคือทั้งหมดที่ loop รู้เกี่ยวกับ
provider

```python
            for event in self.provider.stream(self._to_send(), self.tools.schemas() or None):
                if isinstance(event, TurnDone):
                    assistant = event.message
                    self.usage.add(getattr(event, "usage", None) or {})
                else:
                    yield event
```

ไม่มีคำว่า OpenAI ไม่มีคำว่า Anthropic ไม่มี `if` ที่ถามว่ากำลังคุยกับใคร
และการเพิ่มเจ้าที่สามคือการเขียนคลาสใหม่หนึ่งคลาส ไม่ใช่การแก้ไฟล์นี้ครับ

## 7. ทำไม interface ต้องเป็น streaming ตั้งแต่วันแรก

คำถามที่ตามมาตามธรรมชาติคือทำไมไม่ทำ interface ให้ง่ายกว่านี้ คือรับ
บทสนทนาแล้วคืน message หนึ่งอัน แล้วค่อยเพิ่ม streaming ทีหลังเมื่อจำเป็น

**เพราะทิศทางของการแปลงมันเป็นทางเดียว** จาก stream ไปเป็นคำตอบก้อนเดียว
คือการวนเก็บจนหมด ซึ่งใครก็เขียนได้ในสามบรรทัด และในโปรเจกต์นี้มีคนเขียน
ไว้แล้วจริงๆ อยู่ใน `subagent.py`

```python
def run_to_completion(agent, task):
    """Run an agent and return the text it finished with."""
    answer = ""
    for event in agent.run(task):
        if isinstance(event, TurnDone):
            answer = event.message.content
    return answer
```

ส่วนทางกลับกันทำไม่ได้เลย ถ้า interface คืนคำตอบก้อนเดียว คนเรียกไม่มีทาง
รู้ว่าตัวอักษรตัวแรกมาถึงตอนไหน เพราะข้อมูลนั้นถูกทิ้งไปแล้วข้างใน

**ผลที่ตามมาถ้าเลือกผิด** คือวันที่คุณอยากได้ข้อความไหลบนหน้าจอ คุณต้อง
เปลี่ยน signature ของ `stream` ซึ่งแปลว่าต้องแก้ทุกที่ที่เรียกมัน ทุก test
ที่มี provider ปลอม และทุกคลาสที่ implement interface นั้นไว้ การเลือก
streaming ตั้งแต่แรกจึงไม่ใช่การเผื่ออนาคต มันคือการเลือกด้านที่แปลงเป็น
อีกด้านได้ฟรี

**ทำไม eval กับ subagent ไม่เดือดร้อน** เพราะทั้งคู่ไม่มีใครนั่งดูอยู่
พวกมันจึงเรียก `run_to_completion` แล้วทิ้ง event ระหว่างทาง การจ่ายค่า
ความสามารถที่ไม่ได้ใช้ในกรณีนี้เท่ากับศูนย์ เพราะ event ถูกสร้างแล้วก็
ถูกโยนทิ้งทันที ไม่มีการเก็บ ไม่มีการรอ

## 8. thinking block และ field ที่ห้ามทิ้ง

สามข้อแรกในหัวข้อที่ 1 ประกาศตัวเองด้วย 400 ในนาทีแรกที่รันโค้ด ข้อนี้ไม่
มันเงียบสนิทจนถึงวันที่มีคนเปิดฟีเจอร์หนึ่ง แล้วคำขอที่ทำงานมาหลายเดือน
ถูกปฏิเสธทั้งก้อน

model รุ่นใหม่หลายตัวสั่งให้คิดก่อนตอบได้ ผลของการคิดไม่ได้ปนอยู่ในข้อความ
มันมาเป็น block ของตัวเองชนิด `thinking` ที่นั่งอยู่ใน assistant message
เดียวกันกับ block ชนิดอื่น หน้าตาแบบนี้

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

ให้ดูรูปร่างไม่ต้องอ่านเนื้อความ block มี `type` มีเนื้อความที่อ่านได้
และมี key ที่สามชื่อ `signature` ซึ่งเป็นสตริงทึบที่เราอ่านไม่ออกและ
สร้างเองไม่ได้

**กฎมีข้อเดียว มันต้องกลับไปเหมือนตอนที่มันมา** ทุกคำขอส่งบทสนทนาทั้งก้อน
ใหม่ ตามที่บทที่ 1 บอกไว้ ดังนั้น block ที่ model สร้างในรอบนี้ต้องเดินทาง
กลับไปในรอบหน้า และต้องกลับไปแบบไม่ถูกย่อ ไม่ถูกตัด ไม่ถูกประกอบใหม่ด้วย
ลำดับ key ที่ต่างออกไป

**ทำไมถึงเข้มขนาดนั้น** เพราะ thinking block ไม่ใช่ข้อความในบทสนทนาที่
server อ่านซ้ำได้เฉยๆ มันคือบันทึกของการคำนวณที่ server ทำไว้ และ server
ต้องพิสูจน์ได้ว่าสิ่งที่ถูกส่งกลับมาคือสิ่งที่ตัวเองผลิต `signature` คือ
ค่าที่ใช้พิสูจน์

และนี่คือจุดที่บั๊กเกิด `signature` เป็น field ที่ไม่มีโค้ดของเราส่วนไหน
ต้องใช้ อ่านก็ไม่ออก คำนวณก็ไม่ได้ มันจึงเป็น field ที่คนเขียนโค้ดเรียบร้อย
ตัดทิ้งตอนแปลงเข้ารูปแบบภายในของตัวเอง คนที่ทำแบบนั้นไม่ได้สะเพร่า เขากำลัง
เก็บกวาด ผลคือวันที่มีคนเปิด thinking แล้ว model เรียก tool ในรอบเดียวกัน
คำขอรอบถัดไปโดนปฏิเสธ โดยที่โค้ดที่เป็นต้นเหตุถูกเขียนไว้ถูกต้องมาตั้งแต่วันแรก

มีอีกชนิดหนึ่งที่เป็นเรื่องเดียวกัน คือ `redacted_thinking` ซึ่งไม่มีเนื้อความ
ให้อ่านเลย มีแต่ field ทึบชื่อ `data` กฎเดียวกันใช้กับมันทั้งหมด

**แล้วโปรเจกต์นี้ทำอะไรกับเรื่องนี้** ตอบตรงๆ คือไม่ได้ทำ parser ในหัวข้อที่ 5
รู้จัก block สองชนิดเท่านั้น `thinking` จึงตกพื้นและหายไป และ `to_wire`
ประกอบ assistant message ขึ้นใหม่จากสตริงกับ list ของ tool call ดังนั้น
ต่อให้ parser เก็บไว้ ก็ไม่มีที่ให้มันกลับขึ้นสาย

มันถูกต้องสำหรับคำขอที่โค้ดนี้ยิงจริง เพราะไม่มีที่ไหนในหลักสูตรที่เปิด
thinking เลย ไม่มีการส่ง field นั้น จึงไม่มี block ให้ทำหาย แต่มันจะกลายเป็น
บั๊กในวันแรกที่มีคนเปลี่ยน และการเขียนไว้ตรงนี้ดีกว่าการแก้ครึ่งเดียว
เพราะ parser ที่เก็บ block ไว้โดยที่ loop ยังไม่มีที่เก็บ จะดูเหมือนจัดการ
แล้วทั้งที่ยังไม่ได้จัดการ

## 9. usage ที่มาสองที่ คนละครึ่ง

ปิดท้ายด้วยบั๊กจริงที่โปรเจกต์นี้เจอและแก้ไปแล้ว มันอยู่ในบันทึกรุ่น 1.0.3

usage (การใช้งาน คือตัวเลขที่ผู้ให้บริการรายงานว่าคำขอนี้ใช้ token ไปเท่าไหร่)
เป็นตัวเลขที่บทที่ 4 บอกว่าเป็นตัวเลขเดียวที่แม่นจริง ปัญหาคือฝั่ง Anthropic
ไม่ได้ส่งมาที่เดียว

จำนวน token ขาเข้ามาตั้งแต่ event แรกคือ `message_start` และมันซ่อนอยู่
ใต้ key ชื่อ `message` อีกชั้น ส่วนจำนวน token ขาออกมาทีหลังที่ระดับบนสุด
ของ event คนละอัน ใครที่เขียนโค้ดอ่านที่เดียวจะได้ครึ่งเดียว และใครที่
อ่านทั้งสองที่แต่เขียนทับกัน จะได้ครึ่งหลังทับครึ่งแรก

```python
                if event.get("type") == "message_start":
                    usage.update(normalise_usage((event.get("message") or {}).get("usage")))
                if event.get("usage"):
                    usage.update(
                        {
                            key: value
                            for key, value in normalise_usage(event["usage"]).items()
                            if value
                        }
                    )
```

`update` ตัวที่สองกรองค่าที่เป็นศูนย์ทิ้งก่อน นั่นคือหัวใจ event ที่แบก
เฉพาะ token ขาออกมาด้วยจะรายงาน token ขาเข้าเป็นศูนย์ ถ้าปล่อยให้ศูนย์นั้น
ทับของจริง ตัวเลขขาเข้าจะกลายเป็นศูนย์โดยไม่มี error ให้ใครเห็น

แล้วยังมีผลข้างเคียงอีกชั้น เมื่อรวมทีละ field แบบนี้ ยอดรวมที่ติดมากับ
ครึ่งหลังคือยอดที่คำนวณจากครึ่งหลังอย่างเดียว จึงต้องคำนวณใหม่ตอนจบ

```python
            if usage:
                usage["total_tokens"] = (
                    usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                )
```

ยังไม่จบ เพราะสองเจ้าเรียกชื่อ field ไม่เหมือนกันด้วย Anthropic พูดว่า
`input_tokens` กับ `output_tokens` ส่วนรูปแบบ OpenAI พูดว่า `prompt_tokens`
กับ `completion_tokens` การแปลงชื่อจึงต้องเกิดก่อนการรวม

```python
def normalise_usage(reported: dict) -> dict:
    """Rename Anthropic's usage fields to the ones the rest of the code uses.

    Anthropic says input_tokens and output_tokens where the OpenAI format
    says prompt_tokens and completion_tokens. Without this the counter reads
    zero against a real Anthropic endpoint and nothing errors, which is the
    worst kind of bug because the number it shows looks like an answer.
    """
```

ประโยคสุดท้ายของ docstring คือเหตุผลที่บั๊กนี้คุ้มค่าเล่า ตัวนับที่อ่านได้
ศูนย์ไม่ได้ดูเหมือนของเสีย มันดูเหมือนคำตอบ คุณจะเห็นเลขศูนย์แล้วคิดว่า
คำขอนั้นถูกเก็บด้วย cache หรือคิดว่ามันเล็กมาก และคุณจะตัดสินใจเรื่องงบ
บนตัวเลขที่ไม่จริง

**บทเรียนที่กว้างกว่าตัวบั๊ก** คือ field ที่ไม่มีใครใช้ตอน develop คือ field
ที่ถูกทำหายง่ายที่สุด และมันมีสองประเภทที่พูดถึงในบทนี้ อันหนึ่งพังดังคือ
`signature` อีกอันพังเงียบคือ `usage` ประเภทหลังคือประเภทที่ต้องมี test ยืนยัน
เพราะมันไม่มีทางประกาศตัวเองครับ

## บทเรียนที่ลงมือทำเรื่องนี้

| บทเรียน | สิ่งที่ได้ลงมือทำ |
| --- | --- |
| 01 first llm call | ยิง HTTP ไปหา model ด้วยมือ เห็นรูปร่างของ payload และคำตอบก่อนที่จะมีอะไรมาห่อ |
| 05 streaming | อ่าน chunk ทีละบรรทัด และประกอบ argument ของ tool ที่มาเป็นชิ้นกลับเป็นก้อนเดียว |
| 06 provider abstraction | เขียนคลาสที่สองให้ทำงานได้โดยไม่แตะ loop และอ่านเรื่อง thinking block กับ signature เต็มๆ |
| 15 token economy | วัด token จากตัวเลขที่ผู้ให้บริการรายงาน แทนการเดาด้วยตัวนับของตัวเอง |
