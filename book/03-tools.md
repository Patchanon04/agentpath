# บทที่ 3 tool คือสัญญา ไม่ใช่ฟังก์ชัน

model ไม่เคยเรียกอะไรเลย มันขอ แล้วเราเป็นคนรัน

ประโยคที่คนส่วนใหญ่ใช้คือ tool (ฟังก์ชันที่ model ขอให้เรารันได้) เป็น
ฟังก์ชันที่ AI เรียกได้ และประโยคนั้นผิดตรงคำเดียวที่สำคัญที่สุด ความต่างระหว่างขอกับ
เรียกฟังดูเหมือนการเล่นคำ แต่มันคือช่องว่างเดียวที่ทุกกลไกความปลอดภัยในหนังสือเล่มนี้
ยืนอยู่ และเป็นฐานของทั้งบทที่ 5 เรื่องความไว้ใจ

บทนี้เดินจากช่องว่างนั้นไปถึงสัญญาห้าข้อที่ tool ทุกตัวต้องรักษา ระหว่างทางคือสองเรื่อง
ที่คนมองข้ามมากที่สุด คือ description ของ tool เป็น prompt ที่สำคัญกว่า system prompt
และข้อความ error ที่ส่งกลับไปหา model ก็เป็น prompt ชิ้นหนึ่งเหมือนกัน

ถ้าคุณเคยเขียน tool มาก่อน หัวข้อที่ 2 เรื่อง structured output (บังคับให้ model ตอบเป็น
JSON ตามรูปที่เรากำหนด) ข้ามได้ มันเชื่อมสองเรื่องที่คุณรู้อยู่แล้วเข้าด้วยกัน ไม่ใช่ของ
ใหม่ที่หัวข้อหลังจากนั้นต้องใช้

## 1. tool คืออะไรจริงๆ

tool หนึ่งตัวประกอบด้วยสามอย่าง ชื่อ คำอธิบาย และ JSON Schema (บอกรูปร่างของข้อมูลด้วย
JSON) ที่บอกว่ารับ argument อะไรบ้าง สามอย่างนี้คือสิ่งที่ model ได้เห็น ส่วนอย่างที่สี่
คือฟังก์ชัน Python ซึ่ง model ไม่เคยเห็นและไม่เคยแตะ

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

กลไกทั้งหมดมีแค่นี้ เราส่งรายการ schema ไปพร้อมบทสนทนา model อ่านแล้วตัดสินใจว่า
ต้องการ tool ตัวไหน มันตอบกลับมาเป็นข้อความที่มี `tool_calls` ซึ่งข้างในคือชื่อ tool
และ argument ที่มันแต่งขึ้นเป็นข้อความ JSON เราแยก JSON นั้นออกมา ตัดสินใจว่า
จะรันหรือไม่ ถ้ารันก็เรียกฟังก์ชันของเราเอง แล้วส่งผลลัพธ์กลับเข้าบทสนทนา
บทพื้นฐานที่ 7 แสดงว่าคำขอนั้นคือข้อความธรรมดาที่ model เขียนต่อจาก template เหมือนคำตอบ
อื่นทุกประการ

ทำไมไม่ให้ model รันเอง เพราะถ้ามันรันเองได้ คุณไม่มีจุดใดเลยที่จะยับยั้ง ทุกกลไกความ
ปลอดภัยในหลักสูตรนี้ ตั้งแต่การกักพาธ การปฏิเสธไฟล์ความลับ ไปจนถึงระบบ permission
ทั้งระบบ อาศัยข้อเท็จจริงข้อเดียวว่ามีช่องว่างระหว่างคำขอกับการรัน และช่องว่างนั้นเป็น
ของเรา

ทางเลือกที่มีคนทำจริงคือให้ model เขียนโค้ดแล้วเรา `exec` โค้ดนั้น ซึ่งรวมหลายขั้นตอน
ไว้ในการเรียกครั้งเดียวและได้ความยืดหยุ่นสูง แต่มันทำลายช่องว่างที่ว่า เพราะคุณจะไม่รู้
ล่วงหน้าว่าโค้ดก้อนนั้นจะทำอะไรจนกว่ามันจะทำไปแล้ว การอนุญาตเป็นรายคำสั่งจึงเป็นไป
ไม่ได้ ในระบบแบบนั้นสิ่งเดียวที่ทำได้คือขังทั้งก้อนไว้ใน sandbox ซึ่งเป็นคนละปัญหาและ
แพงกว่ามากครับ

## 2. tool calling คือกลไกเดียวกับ structured output

คนมักคิดว่า tool calling กับ structured output เป็นคนละเรื่อง อย่างที่สองคืออย่างแรกที่ไม่ได้รัน
อะไร

ถ้าคุณอยากได้ผลวิเคราะห์อารมณ์เป็น JSON ที่มีฟิลด์แน่นอน คุณนิยาม tool ชื่อ
`record_sentiment` ที่รับ `label` กับ `confidence` แล้วบอก model ให้ใช้ tool นั้น สิ่ง
ที่ได้กลับมาคือ JSON ที่ตรงตาม schema แล้วคุณก็หยิบมันไปใช้โดยไม่ต้องรันฟังก์ชันอะไร
เลย

เรื่องนี้แปลว่าคุณไม่ต้องเรียนสองเรื่อง กลไกการบังคับรูปร่างคำตอบกับกลไกการเรียก
tool คือกลไกเดียวกัน ที่ผู้ให้บริการสร้างขึ้นมาเพื่อให้ output ของ model มีรูปร่างที่
โปรแกรมอ่านได้ ส่วนจะเอาไปรันอะไรต่อหรือไม่ เป็นเรื่องของเราฝ่ายเดียว

## 3. description คือ prompt engineering ที่คนมองข้ามที่สุด

คนใช้เวลาหลายชั่วโมงขัด system prompt แล้วเขียน description ของ tool ว่า `"Read a
file"` ทั้งที่ description ถูกส่งไปพร้อมทุกคำขอเหมือนกัน และเป็นข้อมูลเดียวที่ model มี
ในการตัดสินใจว่าจะเลือก tool ตัวไหน

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

สองประโยคนี้ทำงานสามอย่างพร้อมกัน อธิบายว่า tool ทำอะไร บอกว่าเมื่อไหร่ควรใช้อีกตัว
แทน และบอกล่วงหน้าถึงเงื่อนไขที่ทำให้มันพัง คือข้อความเดิมต้องไม่ซ้ำ

ต้องละเอียดขนาดนี้เพราะทางเลือกคือ model เดา และเมื่อมันเดาผิด คุณจ่ายหนึ่งรอบเต็ม
ไปกับการเรียกที่ล้มเหลว บวกอีกหนึ่งรอบให้มันแก้ตัว ประโยคเดียวใน description ราคาไม่
กี่สิบ token แต่มันตัดสองรอบนั้นออกไป

ต้องบอกด้วยว่าเมื่อไหร่ไม่ควรใช้ เพราะเมื่อ tool สองตัวทำงานคล้ายกัน model จะเลือกตัวที่
ง่ายกว่าเสมอ การเขียนไฟล์ทั้งไฟล์ง่ายกว่าการหาข้อความที่ต้องแทนที่ ถ้าไม่มีประโยคที่ผลัก
ไปหา `edit_file` model จะใช้ `write_file` กับทุกอย่าง แล้วเนื้อหาส่วนที่มันไม่ได้ใส่กลับมา
จะหายไปทั้งหมด

และไม่ควร generate description อัตโนมัติจาก type hint เพราะสิ่งที่ model ต้องรู้ไม่ได้
อยู่ในลายเซ็นของฟังก์ชัน type hint บอกได้ว่า `old` เป็น `str` แต่บอกไม่ได้ว่ามันต้อง
ปรากฏในไฟล์เพียงครั้งเดียว หลักสูตรนี้จึงเขียน schema ด้วยมือทั้งหมด

```python
"""Tools are plain functions plus a hand written JSON schema.

The schema is written by hand rather than generated from type hints. Reading
the schema is how a learner understands what the model actually receives, and
hiding it behind a decorator would remove the most instructive part.
"""
```

### description ทุกตัวมีราคาที่จ่ายทุกคำขอ

schema ของ tool ทุกตัวเดินทางไปกับทุกคำขอ ก่อนที่ model จะอ่านงานจริงสักตัวอักษร นี่คือ
ต้นทุนคงที่ของการมี tool

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

ผลเสียมีสองชั้น ชั้นแรกคือเปลือง ชั้นที่สองที่หนักกว่าคือ model เลือก tool ผิดบ่อยขึ้น
เมื่อมีตัวเลือกเยอะเกินไป การต่อ MCP server หลายตัวพร้อมกันจึงทำให้ agent แย่ลงได้
ไม่ใช่แค่แพงขึ้น

ข้อสรุปเชิงปฏิบัติคือ description ต้องละเอียดพอที่จะเลือกถูก แต่จำนวน tool ต้องน้อยพอ
ที่จะมีอะไรให้เลือก และสอง tool ที่ทำงานทับกันเกือบหมดควรรวมเป็นตัวเดียวครับ

## 4. system prompt กับ description แบ่งงานกันยังไง

หัวข้อที่แล้วบอกว่า description คือ prompt engineering คำถามที่ตามมาทันทีคือแล้วอะไร
ควรไปอยู่ที่ไหน เพราะสามที่นี้ถูกส่งไปพร้อมกันทุกคำขอ และมันทำงานคนละอย่าง

โปรเจกต์นี้ตอบคำถามนั้นไว้ในไฟล์เดียว คือ `src/agentpath/prompt.py` ซึ่งยาวสามสิบห้า
บรรทัด และแบ่ง system prompt ออกเป็นสองงานตั้งแต่ย่อหน้าแรก

```python
"""The system prompt.

A system prompt does two different jobs and it helps to keep them apart in
your head. The first job is telling the model who it is and how to behave.
The second is telling it facts about the world it cannot see, such as which
directory it is working in and what operating system it is on. Without the
second job the model guesses, and it guesses wrong in ways that waste turns.
"""
```

งานที่หนึ่งคือพฤติกรรม และมันเป็นค่าคงที่ ข้อความเดียวกันทุกครั้ง ทุกผู้ใช้ ทุกงาน

```python
BEHAVIOUR = """You are a careful software assistant working inside one directory.

Work in small steps. Look before you change anything. When you need to know
what a file contains, read it rather than guessing. When you change a file,
change the smallest amount of text that does the job.

Prefer edit_file over write_file for existing files, because write_file
replaces the whole file and loses anything you did not include.

When you are done, say what you changed in one or two sentences."""
```

งานที่สองคือข้อเท็จจริงที่ model มองไม่เห็น และมันถูกประกอบตอนรัน

```python
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

สามบรรทัดนั้นดูน้อยจนน่าขำ แต่ลองเอาออกดู model ที่ไม่รู้ว่ากำลังยืนอยู่โฟลเดอร์ไหนจะ
เดาพาธ model ที่ไม่รู้ว่าอยู่บน Windows จะเขียนคำสั่งฝั่ง Unix แล้วรอบนั้นก็เสียไปทั้ง
รอบ ข้อเท็จจริงที่ราคาสามสิบ token ตัดการเดาที่ราคาหนึ่งรอบเต็มออกไป

เส้นแบ่งที่ใช้ตัดสินว่าอะไรอยู่ที่ไหนมาจากคำถามเดียว คือสิ่งนี้เปลี่ยนตามอะไร

| ที่อยู่ | ใส่อะไร | เพราะมันเปลี่ยนตาม |
| --- | --- | --- |
| `BEHAVIOUR` ใน system prompt | นิสัย มาตรฐานงาน สิ่งที่ห้ามทำ | ไม่เปลี่ยนเลย |
| ส่วน facts ของ system prompt | โฟลเดอร์ ระบบปฏิบัติการ รุ่นภาษา | เปลี่ยนตามการรัน |
| `description` ของ tool | tool ตัวนี้ทำอะไร เมื่อไหร่ควรใช้ตัวอื่น เงื่อนไขที่ทำให้พัง | เปลี่ยนตาม tool |
| user message | งานที่ต้องทำครั้งนี้ | เปลี่ยนทุกข้อความ |

จากตารางตามมาสามกฎ

อย่าเขียนวิธีใช้ tool ไว้ใน system prompt อย่างเดียว ประโยคว่า เวลาจะแก้ไฟล์ให้ใช้
edit_file ไม่ใช่ write_file อยู่ใน `BEHAVIOUR` ข้างบนก็จริง แต่มันอยู่ใน `description`
ของ `write_file` ด้วย และตัวหลังคือตัวที่นับ เพราะมันเดินทางไปพร้อมกับ tool
ตัวนั้นเสมอ รวมถึงตอนที่ tool ถูกยืมไปใช้ที่อื่น และตอนที่คุณลืมว่าเคยเขียนกฎนั้นไว้
system prompt ที่สะสมวิธีใช้ tool ทีละข้อ คือ system prompt ที่จะขัดกับ `description`
ในวันที่มีคนแก้ที่เดียว

อย่าเอางานของครั้งนี้ไปไว้ใน system prompt มันน่าดึงดูดมาก เพราะรู้สึกว่าคำสั่งใน
system prompt มีน้ำหนักกว่า แต่จากบทที่ 4 ของนิ่งต้องอยู่หน้าเพื่อให้ cache ทำงาน
system prompt ที่เปลี่ยนทุกคำขอคือ cache ที่ไม่เคยทำงาน และอาการของมันคือไม่มี error
อะไรเลย มีแต่บิลที่แพงกว่าที่ควร

ส่วนที่เปลี่ยนได้มีช่องของมันอยู่แล้ว คือ argument ชื่อ `extra` ซึ่งต่อท้ายเสมอ ไม่ใช่
แทรกกลาง บทเรียนที่ 10 ใช้ช่องนี้ใส่ตัวอย่างต่อท้าย ส่วน subagent ในบทที่ 15 ส่งงาน
เป็น user message ตัวแรกของลูก ทั้งสองทาง `BEHAVIOUR` ยังเป็น prefix ชุดเดิมทุกตัวอักษร

ทดสอบข้อเดียวที่ใช้ได้จริงคือ ถ้าคุณลบ tool ตัวหนึ่งทิ้ง มีประโยคไหนใน system prompt
ที่กลายเป็นเรื่องโกหกไหม ถ้ามี ประโยคนั้นควรอยู่ใน `description` ของ tool ตัวนั้น
ตั้งแต่แรกครับ

## 5. error ของ tool ต้องเป็นข้อความ ไม่ใช่ exception

นี่คือหัวข้อที่แยกโค้ดสาธิตออกจาก harness ที่ใช้งานได้จริง

argument ทุกตัวที่ tool ได้รับ มาจาก model

แปลว่ามันคือ input ที่ไม่น่าเชื่อถือ เหมือน input จากผู้ใช้ทางอินเทอร์เน็ตทุกประการ
การเรียกที่ผิดจึงต้องกลายเป็นข้อความที่ model อ่านแล้วแก้ทางได้ ไม่ใช่ exception ที่ฆ่า
loop

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

จับทุก exception เพราะ agent ที่ตายเพราะ model พิมพ์ชื่อ argument ผิดคือ agent ที่ใช้
งานไม่ได้ ในขณะที่ model แก้เรื่องแบบนี้เองได้ถ้ามันรู้ว่าเกิดอะไรขึ้น การส่ง error กลับ
ไปเป็นข้อความคือการให้โอกาสมันแก้

ยกเว้น `KeyboardInterrupt` เพราะการที่คนกดหยุดไม่ใช่ความล้มเหลวของ tool ถ้าเรา
แปลงมันเป็นข้อความ error ที่อ่านได้ agent จะอ่านแล้วลองใหม่ ซึ่งคือการกลืนสิ่งที่คน
เพิ่งสั่งไปเมื่อวินาทีก่อน บทที่ 6 อธิบายเต็ม

### error ที่ดีบอกวิธีแก้ ไม่ใช่แค่บอกว่าพัง

ความต่างระหว่าง error ที่ช่วยกับ error ที่ไม่ช่วย อยู่ที่ว่ามันทิ้ง model ไว้ในตำแหน่งที่ทำ
อะไรต่อได้หรือไม่

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

ข้อความสองอันข้างบนบอกสามอย่าง เกิดอะไรขึ้น เกิดที่ไฟล์ไหน และขั้นตอนถัดไปคืออะไร
model ที่ได้รับข้อความแรกจะไปอ่านไฟล์ใหม่ model ที่ได้รับข้อความที่สองจะขยายบริบทของ
ข้อความที่จะแทนที่ ทั้งสองกรณีแก้จบในรอบเดียว

ตัวอย่างที่ชัดอีกอันอยู่ใน `search.py` ตอนที่ model เขียน regular expression (รูปแบบสำหรั
บค้นหาข้อความ) ที่อันตราย

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

อันที่สองบอกทางออกสองทางที่ต่างกันจริง คือทำ pattern ให้ง่ายลง หรือจำกัดขอบเขตด้วย
argument ที่มีอยู่แล้ว การเอ่ยชื่อ argument ตรงๆ สำคัญ เพราะมันเชื่อม error กับ schema
ที่ model มีอยู่ในมือ

ข้อความ error ที่ส่งกลับไปหา model คือ prompt ชิ้นหนึ่ง หน้าที่ของมันคือทำให้ model
อยู่ในตำแหน่งที่ทำถูกได้ในความพยายามครั้งถัดไป error ที่รายงานความล้มเหลวอย่างเดียว
ทำงานไปได้แค่ครึ่งเดียวครับ

## 6. ค่าเริ่มต้นของ safe คือ False โดยตั้งใจ

`Tool` มีฟิลด์ `safe` ที่บอกว่ารันได้เลยโดยไม่ต้องถามคนหรือไม่ ค่าเริ่มต้นคือ `False`

เพราะการลืมไม่ควรนำไปสู่ความเงียบ ถ้าค่าเริ่มต้นเป็น `True` คนที่เขียน tool ใหม่แล้วลืม
คิดเรื่องความปลอดภัย จะได้ tool ที่รันได้ทันทีโดยไม่มีอะไรเตือน ถ้าค่าเริ่มต้นเป็น
`False` การลืมนำไปสู่คำถามบนหน้าจอ ซึ่งเป็นความผิดพลาดที่มองเห็นและแก้ได้

กฎนี้อยู่บน `Tool` ไม่ใช่ในระบบ permission เพราะคนที่เขียน tool คือคนที่รู้ว่ามันทำลาย
อะไรได้บ้าง การเก็บรายชื่อ tool อันตรายไว้ในไฟล์อื่นแปลว่ามีสองที่ที่ต้องแก้ตอนเพิ่ม tool
และที่ที่คนลืมแก้คือที่ที่สองครับ

## 7. สรุปสัญญาที่ tool ต้องรักษา

- รับ argument ของตัวเองอย่างเดียว ไม่ต้องรู้ว่ามีบทสนทนาอยู่
- คืน string เสมอ ไม่โยน exception ออกไปหา loop
- description บอกว่าทำอะไร เมื่อไหร่ควรใช้ตัวอื่น และอะไรทำให้พัง
- ข้อความ error บอกขั้นตอนถัดไป ไม่ใช่บอกแค่ว่าล้มเหลว
- `safe` ต้องถูกตั้งอย่างจงใจ ไม่ใช่ถูกละไว้

สัญญาห้าข้อนี้คือสิ่งที่ทำให้บทที่ 2 เป็นจริง tool ตัวใหม่ที่รักษาสัญญาครบ ไม่มีเหตุผล
ใดที่จะต้องแตะ loop อีกสองเรื่องของบทนี้ไม่ใช่สัญญาแต่เป็นมุมมอง หัวข้อที่ 2 ว่า
structured output คือกลไกเดียวกัน และหัวข้อที่ 4 ว่าอะไรอยู่ใน system prompt อะไรอยู่
ใน description

## บทเรียนที่ลงมือทำเรื่องนี้

| บทเรียน | สิ่งที่ได้ลงมือทำ |
| --- | --- |
| 03 tool calling | เขียน JSON Schema ด้วยมือ เห็น JSON ที่เดินทางไปจริง และเห็นว่า structured output คือกลไกเดียวกัน |
| 07 file tools | เขียน tool ที่ error message ตัวมันเองสอน model ให้แก้ถูกในรอบเดียว |
| 09 search tools | จัดการ regular expression ที่ model เขียนผิด และเปลี่ยนความพังเป็นคำแนะนำ |
| 10 anatomy of a prompt | แยกว่าอะไรอยู่ใน system prompt อะไรอยู่ใน description และทำไม description คือ prompt |
| 19 MCP client | เห็นว่า tool ที่ตัวจริงอยู่อีก process หนึ่ง ก็ยังเป็น tool ตัวหนึ่งเหมือนเดิม |
