# บทที่ 3 tool คือสัญญา ไม่ใช่ฟังก์ชัน

คนส่วนใหญ่เข้าใจว่า tool (เครื่องมือ คือความสามารถหนึ่งอย่างที่ agent เรียกใช้ได้)
คือฟังก์ชันที่ AI เรียกได้ ประโยคนี้ผิดในจุดที่สำคัญที่สุด

model ไม่เคยเรียกอะไรเลย มันขอ แล้วเราเป็นคนรัน

ความต่างนี้ฟังดูเหมือนการเล่นคำ แต่มันคือสิ่งเดียวที่ทำให้ agent ปลอดภัยได้
และเป็นฐานของทั้งบทที่ 5 เรื่องความไว้ใจ

## 1. tool คืออะไรจริงๆ

tool หนึ่งตัวประกอบด้วยสามอย่าง ชื่อ คำอธิบาย และ JSON Schema (สคีมา JSON
คือคำอธิบายรูปร่างของข้อมูลในรูปแบบ JSON) ที่บอกว่ารับ argument อะไรบ้าง
สามอย่างนี้คือสิ่งที่ model ได้เห็น ส่วนอย่างที่สี่คือฟังก์ชัน Python
ซึ่ง model ไม่เคยเห็นและไม่เคยแตะ

```python
@dataclass
class Tool:
    """One tool the model can ask for.

    safe says whether this tool can be run without asking a person first.
    It defaults to False because forgetting to think about a new tool must
    lead to a question rather than to silence, and because the person who
    writes a tool is the one who knows whether it can destroy something.
    """

    name: str
    description: str
    parameters: dict
    fn: Callable[..., object]
    safe: bool = False
```

สิ่งที่เดินทางไปหา model คือสามฟิลด์แรกเท่านั้น

```python
    def schemas(self) -> list[dict]:
        return [
            {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
            for tool in self._tools.values()
        ]
```

`fn` ไม่อยู่ในนั้น และไม่มีวันอยู่

**กลไกโดยละเอียด** เราส่งรายการ schema ไปพร้อมบทสนทนา model อ่านแล้วตัดสินใจ
ว่าต้องการ tool ตัวไหน มันตอบกลับมาเป็นข้อความที่มี `tool_calls` ซึ่งข้างใน
คือชื่อ tool และ argument ที่มันแต่งขึ้นเป็นข้อความ JSON เราแยก JSON นั้น
ออกมา ตรวจสอบ ตัดสินใจว่าจะรันหรือไม่ ถ้ารันก็เรียกฟังก์ชันของเราเอง
แล้วส่งผลลัพธ์กลับเข้าบทสนทนา

**ทำไมออกแบบแบบนี้ ไม่ใช่ให้ model รันเอง** เพราะถ้า model รันเองได้
คุณไม่มีจุดใดเลยที่จะยับยั้ง ทุกกลไกความปลอดภัยในหลักสูตรนี้ ตั้งแต่การกัก
พาธ การปฏิเสธไฟล์ความลับ ไปจนถึงระบบ permission ทั้งระบบ อาศัยข้อเท็จจริง
ข้อเดียวว่ามีช่องว่างระหว่างคำขอกับการรัน และช่องว่างนั้นเป็นของเรา

**ทำไมไม่ใช่แบบอื่น** ทางเลือกที่มีคนทำจริงคือให้ model เขียนโค้ดแล้วเรา
`exec` โค้ดนั้น ซึ่งรวมหลายขั้นตอนไว้ในการเรียกครั้งเดียวและได้ความยืดหยุ่นสูง
แต่มันทำลายช่องว่างที่ว่า เพราะคุณจะไม่รู้ล่วงหน้าว่าโค้ดก้อนนั้นจะทำอะไร
จนกว่ามันจะทำไปแล้ว การอนุญาตเป็นรายคำสั่งจึงเป็นไปไม่ได้ ในระบบแบบนั้น
สิ่งเดียวที่ทำได้คือการขังทั้งก้อนไว้ใน sandbox ซึ่งเป็นคนละปัญหาและแพงกว่ามาก

## 2. tool calling คือกลไกเดียวกับ structured output

คนมักคิดว่า tool calling กับ structured output (ผลลัพธ์มีโครงสร้าง คือการ
บังคับให้ model ตอบเป็น JSON ตามรูปที่กำหนด) เป็นคนละเรื่อง จริงๆ แล้ว
อย่างที่สองคืออย่างแรกที่ไม่ได้รันอะไร

ถ้าคุณอยากได้ผลวิเคราะห์อารมณ์เป็น JSON ที่มีฟิลด์แน่นอน คุณนิยาม tool
ชื่อ `record_sentiment` ที่รับ `label` กับ `confidence` แล้วบอก model ให้
ใช้ tool นั้น สิ่งที่ได้กลับมาคือ JSON ที่ตรงตาม schema แล้วคุณก็หยิบมันไป
ใช้โดยไม่ต้องรันฟังก์ชันอะไรเลย

**ทำไมถึงสำคัญ** เพราะมันแปลว่าคุณไม่ต้องเรียนสองเรื่อง กลไกการบังคับรูปร่าง
คำตอบกับกลไกการเรียกเครื่องมือคือกลไกเดียวกัน ที่ผู้ให้บริการสร้างขึ้นมา
เพื่อให้ output ของ model มีรูปร่างที่โปรแกรมอ่านได้ ส่วนจะเอาไปรันอะไร
ต่อหรือไม่ เป็นเรื่องของเราฝ่ายเดียว

## 3. description คือ prompt engineering ที่คนมองข้ามที่สุด

คนใช้เวลาหลายชั่วโมงขัด system prompt แล้วเขียน description ของ tool ว่า
`"Read a file"` ทั้งที่ description ถูกส่งไปพร้อมทุกคำขอเหมือนกัน และเป็น
ข้อมูลเดียวที่ model มีในการตัดสินใจว่าจะเลือก tool ตัวไหน

เทียบสองแบบนี้

```python
        Tool(
            name="write_file",
            description=(
                "Write a whole file, creating it if needed. Use edit_file instead when "
                "you only want to change part of an existing file."
            ),
```

```python
        Tool(
            name="edit_file",
            description=(
                "Replace one exact piece of text in a file. The old text must appear "
                "exactly once, so include enough surrounding lines to make it unique."
            ),
```

สองประโยคนี้ทำงานสามอย่างพร้อมกัน อธิบายว่า tool ทำอะไร บอกว่าเมื่อไหร่ควร
ใช้อีกตัวแทน และบอกล่วงหน้าถึงเงื่อนไขที่ทำให้มันพัง คือข้อความเดิมต้องไม่ซ้ำ

**ทำไมต้องเขียนละเอียดขนาดนี้** เพราะทางเลือกคือ model เดา และเมื่อมันเดาผิด
คุณจ่ายหนึ่งรอบเต็มไปกับการเรียกที่ล้มเหลว บวกอีกหนึ่งรอบให้มันแก้ตัว
ประโยคเดียวใน description ราคาไม่กี่สิบ token แต่มันตัดสองรอบนั้นออกไป

**ทำไมต้องบอกด้วยว่าเมื่อไหร่ไม่ควรใช้** เพราะเมื่อ tool สองตัวทำงานคล้ายกัน
model จะเลือกตัวที่ง่ายกว่าเสมอ การเขียนไฟล์ทั้งไฟล์ง่ายกว่าการหาข้อความ
ที่ต้องแทนที่ ถ้าไม่มีประโยคที่ผลักไปหา `edit_file` model จะใช้ `write_file`
กับทุกอย่าง แล้วเนื้อหาส่วนที่มันไม่ได้ใส่กลับมาจะหายไปทั้งหมด

**ทำไม description ไม่ควรเขียนแบบ generate อัตโนมัติจาก type hint**
เพราะสิ่งที่ model ต้องรู้ไม่ได้อยู่ในลายเซ็นของฟังก์ชัน type hint บอกได้ว่า
`old` เป็น `str` แต่บอกไม่ได้ว่ามันต้องปรากฏในไฟล์เพียงครั้งเดียว หลักสูตรนี้
จึงเขียน schema ด้วยมือทั้งหมด

```python
"""Tools are plain functions plus a hand written JSON schema.

The schema is written by hand rather than generated from type hints. Reading
the schema is how a learner understands what the model actually receives, and
hiding it behind a decorator would remove the most instructive part.
"""
```

### description ทุกตัวมีราคาที่จ่ายทุกคำขอ

schema ของ tool ทุกตัวเดินทางไปกับทุกคำขอ ก่อนที่ model จะอ่านงานจริงสักตัวอักษร
นี่คือต้นทุนคงที่ของการมี tool

```python
    def schema_size(self) -> int:
        """How many characters of tool description travel on every request.

        This is the fixed cost of having tools at all. It is paid on the
        first request and on every request after it, before the model has
        read a word of the actual task. Connect a handful of MCP servers and
        this number can eat a large share of the context window on its own,
        which is why it is worth being able to see it.
        """
```

ผลเสียมีสองชั้น ชั้นแรกคือเปลือง ชั้นที่สองที่หนักกว่าคือ model เลือก tool
ผิดบ่อยขึ้นเมื่อมีตัวเลือกเยอะเกินไป การต่อ MCP server หลายตัวพร้อมกันจึงทำให้
agent แย่ลงได้ ไม่ใช่แค่แพงขึ้น

ข้อสรุปเชิงปฏิบัติคือ description ต้องละเอียดพอที่จะเลือกถูก แต่จำนวน tool
ต้องน้อยพอที่จะมีอะไรให้เลือก และสอง tool ที่ทำงานทับกันเกือบหมดควรรวมเป็นตัวเดียว

## 4. error ของ tool ต้องเป็นข้อความ ไม่ใช่ exception

นี่คือหัวข้อที่แยกโค้ดสาธิตออกจาก harness ที่ใช้งานได้จริง

argument ที่ tool ได้รับมาจาก model แปลว่ามันคือ input ที่ไม่น่าเชื่อถือ
เหมือน input จากผู้ใช้ทางอินเทอร์เน็ต การเรียกที่ผิดต้องกลายเป็นข้อความที่
model อ่านแล้วแก้ทางได้ ไม่ใช่ exception ที่ฆ่า loop

```python
    def run(self, call: ToolCall) -> ToolResult:
        """Run one tool call and always come back with a result.

        Arguments come from the model, so they are untrusted input. A bad call
        must turn into text the model can read and correct, never an exception
        that kills the agent loop.
        """
        if call.arguments_error:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: {call.arguments_error}. Send the tool call again.",
            )
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
        except KeyboardInterrupt:
            # An interrupt is not a tool failure. Turning it into a readable
            # result would swallow the thing the person just asked for.
            raise
        except Exception as error:
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=f"Error: {type(error).__name__}: {error}",
            )
```

**ทำไมต้องจับทุก exception** เพราะ agent ที่ตายเพราะ model พิมพ์ชื่อ argument
ผิดคือ agent ที่ใช้งานไม่ได้ ในขณะที่ model แก้เรื่องแบบนี้เองได้ถ้ามันรู้ว่า
เกิดอะไรขึ้น การส่ง error กลับไปเป็นข้อความคือการให้โอกาสมันแก้

**ทำไม KeyboardInterrupt ต้องถูกยกเว้น** เพราะการที่คนกดหยุดไม่ใช่ความล้มเหลว
ของ tool ถ้าเราแปลงมันเป็นข้อความ error ที่อ่านได้ agent จะอ่านแล้วลองใหม่
ซึ่งคือการกลืนสิ่งที่คนเพิ่งสั่งไปเมื่อวินาทีก่อน เรื่องนี้อธิบายเต็มในบทที่ 6

### error ที่ดีบอกวิธีแก้ ไม่ใช่แค่บอกว่าพัง

ความต่างระหว่าง error ที่ช่วยกับ error ที่ไม่ช่วย อยู่ที่ว่ามันทิ้ง model
ไว้ในตำแหน่งที่ทำอะไรต่อได้หรือไม่

```python
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
```

เทียบกับ `Error: edit failed` ซึ่งถูกในเชิงข้อเท็จจริงและไร้ประโยชน์โดยสมบูรณ์

ข้อความสองอันข้างบนบอกสามอย่าง เกิดอะไรขึ้น เกิดที่ไฟล์ไหน และขั้นตอนถัดไป
คืออะไร model ที่ได้รับข้อความแรกจะไปอ่านไฟล์ใหม่ model ที่ได้รับข้อความที่สอง
จะขยายบริบทของข้อความที่จะแทนที่ ทั้งสองกรณีแก้จบในรอบเดียว

ตัวอย่างที่ชัดอีกอันอยู่ใน `search.py` ตอนที่ model เขียน regular expression
(นิพจน์ปกติ คือรูปแบบสำหรับค้นหาข้อความ) ที่อันตราย

```python
        if NESTED_QUANTIFIER.search(pattern):
            return (
                f"Error: {pattern} has one repeat wrapped in another, which can take "
                "effectively forever to match. Write it without the nested repeat."
            )
```

```python
        except subprocess.TimeoutExpired:
            return (
                f"Error: searching for {pattern} took longer than {SEARCH_SECONDS} "
                "seconds and was given up on. Try a simpler pattern, or narrow the "
                "search with the glob argument."
            )
```

อันที่สองบอกทางออกสองทางที่ต่างกันจริง คือทำ pattern ให้ง่ายลง หรือจำกัด
ขอบเขตด้วย argument ที่มีอยู่แล้ว การเอ่ยชื่อ argument ตรงๆ สำคัญ เพราะมัน
เชื่อม error กับ schema ที่ model มีอยู่ในมือ

**หลักที่ใช้ได้ทั่วไป** ข้อความ error ที่ส่งกลับไปหา model คือ prompt ชิ้นหนึ่ง
หน้าที่ของมันคือทำให้ model อยู่ในตำแหน่งที่ทำถูกได้ในความพยายามครั้งถัดไป
error ที่รายงานความล้มเหลวอย่างเดียวทำงานไปได้แค่ครึ่งเดียว

## 5. ค่าเริ่มต้นของ safe คือ False และนั่นคือการตัดสินใจเชิงออกแบบ

`Tool` มีฟิลด์ `safe` ที่บอกว่ารันได้เลยโดยไม่ต้องถามคนหรือไม่ ค่าเริ่มต้นคือ
`False`

**ทำไม** เพราะการลืม ไม่ควรนำไปสู่ความเงียบ ถ้าค่าเริ่มต้นเป็น `True`
คนที่เขียน tool ใหม่แล้วลืมคิดเรื่องความปลอดภัย จะได้ tool ที่รันได้ทันที
โดยไม่มีอะไรเตือน ถ้าค่าเริ่มต้นเป็น `False` การลืมนำไปสู่คำถามบนหน้าจอ
ซึ่งเป็นความผิดพลาดที่มองเห็นและแก้ได้

**ทำไมกฎนี้อยู่บน Tool ไม่ใช่ในระบบ permission** เพราะคนที่เขียน tool คือคนที่
รู้ว่ามันทำลายอะไรได้บ้าง การเก็บรายชื่อ tool อันตรายไว้ในไฟล์อื่นแปลว่ามีสอง
ที่ที่ต้องแก้ตอนเพิ่ม tool และที่ที่คนลืมแก้คือที่ที่สอง

## 6. สรุปสัญญาที่ tool ต้องรักษา

- รับ argument ของตัวเองอย่างเดียว ไม่ต้องรู้ว่ามีบทสนทนาอยู่
- คืน string เสมอ ไม่โยน exception ออกไปหา loop
- description บอกว่าทำอะไร เมื่อไหร่ควรใช้ตัวอื่น และอะไรทำให้พัง
- ข้อความ error บอกขั้นตอนถัดไป ไม่ใช่บอกแค่ว่าล้มเหลว
- `safe` ต้องถูกตั้งอย่างจงใจ ไม่ใช่ถูกละไว้

สัญญาห้าข้อนี้คือสิ่งที่ทำให้บทที่ 2 เป็นจริง tool ตัวใหม่ที่รักษาสัญญาครบ
ไม่มีเหตุผลใดที่จะต้องแตะ loop

## บทเรียนที่ลงมือทำเรื่องนี้

| บทเรียน | สิ่งที่ได้ลงมือทำ |
| --- | --- |
| 03 tool calling | เขียน JSON Schema ด้วยมือ เห็น JSON ที่เดินทางไปจริง และเห็นว่า structured output คือกลไกเดียวกัน |
| 07 file tools | เขียน tool ที่ error message ตัวมันเองสอน model ให้แก้ถูกในรอบเดียว |
| 09 search tools | จัดการ regular expression ที่ model เขียนผิด และเปลี่ยนความพังเป็นคำแนะนำ |
| 10 anatomy of a prompt | แยกว่าอะไรอยู่ใน system prompt อะไรอยู่ใน description และทำไม description คือ prompt |
| 19 MCP client | เห็นว่า tool ที่ตัวจริงอยู่อีก process หนึ่ง ก็ยังเป็น tool ตัวหนึ่งเหมือนเดิม |
