[Read in English](README.md)

# บทที่ 18. หมุดหมาย. The harness

ไม่มีอะไรในบทนี้ที่เป็นของใหม่

ลองอ่านประโยคนั้นซ้ำช้า ๆ อีกครั้ง เพราะมันไม่ใช่คำขอโทษ มันคือการวัดผลที่บทนี้มีอยู่เพื่อทำ
บทที่ 12 ถึง 17 สร้างระบบ permission ไฟล์ session ตัวตัด context ตัวนับ token เครื่องมือ
retrieval ตัวช่วย retry และ cancellation token แต่ละอย่างมาถึงอย่างโดดเดี่ยว อยู่ในโฟลเดอร์
ของตัวเอง พิสูจน์ด้วย `check.py` ของตัวเอง โดยไม่มี subsystem อื่นอยู่ในห้องเลย บทนี้เอา
ทั้งหมดนั้นมาใส่ไว้ใน process เดียวกันพร้อมกัน ให้ command line กับ process นั้น ชี้มันไปที่
ไดเรกทอรีจริงที่มี bug จริงอยู่ข้างใน แล้วตรวจดิสก์หลังจากนั้น

ไม่มีกลไกใหม่แม้แต่บรรทัดเดียวที่ถูกคิดขึ้นมาเพื่อให้สิ่งนั้นทำงานได้ ถ้ามันจำเป็นต้องถูกคิดขึ้นมา
แปลว่ารอยต่อของภาค 3 ถูกตัดไว้ผิดที่ และนั่นคือสิ่งที่บทหมุดหมายมีไว้เพื่อค้นหาพอดี

บทหมุดหมายมีงานสามอย่าง ซึ่งต่างจากงานของบทปกติทั้งหมด การประกอบ ซึ่งคือการแสดงว่าชิ้นส่วน
เข้ากันได้ การสะท้อนกลับ ซึ่งคือการมองย้อนไปที่รอยต่อแล้วถามว่ามันถูกตัดในที่ที่ควรจะตัดหรือไม่
และการสรุปอย่างซื่อสัตย์ว่าสิ่งนี้ยังทำอะไรไม่ได้บ้าง เพราะหมุดหมายที่มีแต่การเฉลิมฉลองคือโฆษณา
มากกว่าจะเป็นบทเรียน

นี่คือสิ่งที่อยู่ในโฟลเดอร์นี้และที่มาของแต่ละไฟล์

```text
lessons/18-the-harness/
  main.py         new. argument parsing, wiring, and the interrupt handler
  check.py        new. the milestone check for part 3
  agent.py        identical to lesson 17
  prompt.py       identical to lesson 10
  permissions.py  identical to lesson 12
  session.py      identical to lesson 13
  context.py      identical to lesson 14
  providers.py    identical to lesson 15
  usage.py        identical to lesson 15
  retrieval.py    identical to lesson 16
  tools.py        identical to lesson 16
  retry.py        identical to lesson 17
  cancel.py       identical to lesson 17
  README.md       this file
```

สิบเอ็ดไฟล์จากสิบสามไฟล์ Python เหมือนเดิมทุกไบต์กับที่เคยอยู่ในบทก่อนหน้า นั่นไม่ใช่คำกล่าวอ้าง
มันตรวจสอบได้ และมันถูกตรวจสอบมาแล้ว

```bash
cd lessons
for f in agent.py permissions.py session.py context.py usage.py retry.py; do
  diff -qs 17-errors-and-retries/$f 18-the-harness/$f
done
```

```text
Files 17-errors-and-retries/agent.py and 18-the-harness/agent.py are identical
Files 17-errors-and-retries/permissions.py and 18-the-harness/permissions.py are identical
Files 17-errors-and-retries/session.py and 18-the-harness/session.py are identical
Files 17-errors-and-retries/context.py and 18-the-harness/context.py are identical
Files 17-errors-and-retries/usage.py and 18-the-harness/usage.py are identical
Files 17-errors-and-retries/retry.py and 18-the-harness/retry.py are identical
```

ไฟล์ใหม่สองไฟล์คือ `main.py` ซึ่งไม่มี logic ของ agent อยู่เลยแม้แต่น้อย และ `check.py`
ซึ่งก็ไม่มี logic ของ agent เช่นกัน

## 1. harness คืออะไร ในเมื่อคุณสร้างมันมาแล้ว

ทุกคอร์สที่ใช้คำนี้ให้นิยามมันแบบนามธรรม และนิยามแบบนามธรรมนั้นไร้ประโยชน์เพราะมันเข้ากับ
ทุกอย่าง ดังนั้นจงนิยามมันเทียบกับสิ่งที่นั่งอยู่ในโฟลเดอร์นี้แทน

ตอนจบภาค 2 คุณมี agent ตัวหนึ่ง `run` ใน `agent.py` บวกกับ tool เจ็ดตัว บวกกับ system
prompt มันถูกชี้ไปที่โฟลเดอร์หนึ่ง หาให้เจอว่าโค้ดอยู่ตรงไหน อ่านมัน แก้หนึ่งบรรทัด และรันคำสั่ง
เพื่อตรวจสอบการแก้ไขได้ นั่นคือความสามารถจริง และมันไม่ใช่ของเล่น

สิ่งที่มันทำไม่ได้คือการถูกใช้เป็นครั้งที่สอง

ปิด process แล้วทุกอย่างที่มันเรียนรู้มาก็หายไป อนุมัติคำสั่งหนึ่งไปแล้วมันก็ถามคำถามเดิมอีกในครั้ง
ต่อไป ทำงานนานพอ บทสนทนาก็ไม่พอดีกับ window อีกต่อไป และการรันก็จบลงด้วย HTTP error
กลางงาน ไม่มีอะไรที่ไหนบอกคุณว่าทั้งหมดนั้นมีต้นทุนเท่าไร เน็ตสะดุดห้าวินาทีก็ได้ traceback
พร้อมกับเสียงานยี่สิบนาที กดปุ่ม interrupt แล้วคุณก็ได้ stack trace ออกมาจากกลาง stream

ห้าประโยคนั้นคือนิยาม **harness คือทุกสิ่งที่ยืนอยู่รอบ ๆ agent เพื่อให้ agent ถูกรันได้มากกว่า
หนึ่งครั้ง บนงานที่สำคัญจริง โดยคนที่ไม่ใช่คนที่เขียนมันขึ้นมา**

ทีนี้มาเรียกชื่อชิ้นส่วนของสิ่งที่คุณสร้าง เพราะนั่นคือนิยามที่ถูกทำให้เป็นรูปธรรม

| ชิ้นส่วน | ไฟล์ | บทที่ | มันทำให้อะไรเป็นไปได้ |
| --- | --- | --- | --- |
| `Permissions` | `permissions.py` | 12 | ประตูที่คุณยังอ่านอยู่ตอนคำถามที่สี่สิบ |
| `Session` | `session.py` | 13 | การจากไปแล้วกลับมา และการอ่านว่าเกิดอะไรขึ้น |
| `fit_to_budget` | `context.py` | 14 | งานยาว ๆ ที่ไม่ตายตรงขอบ window |
| `Usage` | `usage.py` | 15 | การรู้ว่าการรันหนึ่งครั้งมีต้นทุนเท่าไร แทนที่จะเดา |
| `search_notes` | `retrieval.py` | 16 | retrieval ในฐานะ tool ธรรมดา ไม่ใช่ระบบพิเศษ |
| `with_retries` | `retry.py` | 17 | บ่ายวันที่เน็ตแย่ ที่ไม่ทำให้เสียงาน |
| `Cancellation` | `cancel.py` | 17 | การ interrupt ที่หยุดงานจริง ไม่ใช่หยุดแค่หน้าจอ |

อ่านคอลัมน์ที่สี่ ไม่มีสักรายการเดียวที่เป็นสิ่งใหม่ที่ agent ทำได้ ไม่มีสักอันที่เป็น tool ใหม่
ทุกอันล้วนว่าด้วยสิ่งที่เกิดขึ้นเมื่อ agent รันอีกครั้ง หรือรันนาน หรือรันแล้วพัง หรือรันขณะที่มีคนดูอยู่

นั่นคือความแตกต่างที่คำนี้แบกไว้ ภาค 2 ทำให้ agent **มีความสามารถ** มากขึ้น
ภาค 3 ทำให้มัน **ใช้งานจริงได้** ทั้งสองเป็นคนละแกน และการเพิ่มในแกนหนึ่งไม่ได้เพิ่มในอีกแกน

### สองสิ่งที่ไม่ใช่ harness

ควรพูดให้ชัด เพราะทั้งสองอย่างมักถูกเรียกว่าเป็น harness

**system prompt ที่ดีกว่าไม่ใช่ harness** บทที่ 10 เขียน system prompt ที่ดีไว้อันหนึ่ง แล้ว
บทที่ 12 ก็สาธิตว่าคุณไม่สามารถสั่งการเพื่อออกจาก prompt injection ได้ เพราะคำสั่งของคุณกับ
ข้อความของผู้โจมตีเป็นของชนิดเดียวกันในลิสต์เดียวกัน ที่แข่งกันแย่งความสนใจอันเดียวกัน
กลไกควบคุมที่อาศัยอยู่ภายในบทสนทนาย่อมถูกโต้แย้งได้โดยอะไรก็ตามในบทสนทนานั้น ทุกชิ้นส่วนใน
ตารางข้างบนอาศัยอยู่นอกบทสนทนา

**tool ที่มากขึ้นก็ไม่ใช่ harness เช่นกัน** อันนี้เป็นความเข้าใจผิดที่เกิดง่ายกว่า เพราะมันให้ความ
รู้สึกเหมือนความคืบหน้า บทที่ 16 คือหลักฐาน มันเพิ่มเครื่องมือ retrieval ทั้งชุด พร้อม vector
index ครบ และหัวข้อที่ 3 แสดงให้เห็นว่าสิ่งนั้นทำอะไรกับ loop ซึ่งคำตอบคือไม่ทำอะไรเลย

## 2. แต่ละชิ้นส่วนอาศัยอยู่ที่ไหน และทำไมมันถึงสำคัญ

ดูว่าความรับผิดชอบตั้งอยู่ตรงไหน ทีละอย่าง แต่ละข้อคือประโยคหนึ่งประโยคเกี่ยวกับขอบเขต และ
ทุกขอบเขตคือการตัดสินใจที่อาจจะไปทางตรงกันข้ามก็ได้

### permission ตัดสิน และไม่รัน

`permissions.py` มี method เดียวที่สำคัญ และมันคืนค่า boolean

```python
    def check(self, name, arguments):
        """Say whether this call may run, asking a person only when needed."""
        if name in SAFE_TOOLS:
            return True
        if self.auto_approve:
            return True
        if signature(name, arguments) in self.remembered:
            return True
        if self.ask is None:
            return False
        answer = self.ask(name, arguments)
        if answer == ALLOW_ALWAYS:
            self.remembered.add(signature(name, arguments))
            return True
        return answer == ALLOW_ONCE
```

ไม่มี `tools.run` ในไฟล์นั้น ไม่มี `subprocess` ไม่มี `open` `Permissions` ไม่เคยรันอะไรเลย
ตลอดชีวิตของมันและก็ทำไม่ได้ด้วย และเหตุผลเดียวที่มันรู้จักชื่อ tool เลยก็เพื่อจะได้ค้นหาชื่อนั้น
ใน set

การออกแบบทางเลือกคือแบบที่เห็นได้ชัด ที่ object ของ permission ห่อการเรียก tool ไว้แล้วรันมัน
ถ้าอนุญาต มันดูเรียบร้อยกว่าตอนแรกเพราะผู้เรียกจะเหลือหนึ่งบรรทัดแทนที่จะเป็นสองบรรทัด
สิ่งที่คุณต้องจ่ายคือ permission กลายเป็นสิ่งที่ทดสอบไม่ได้โดยไม่มี side effect เพราะคุณไม่
สามารถถามมันว่ามันจะตัดสินอย่างไรโดยที่มันไม่ลงมือทำจริง ดูสิ่งที่คุณสมบัตินี้ให้กับ `check.py`
ในหัวข้อที่ 6 ซึ่งสร้าง `Permissions` ที่ปฏิเสธทุกอย่างแล้วส่งมันเข้าไปในการรันจริงตรง ๆ

สังเกตด้วยว่า `confirm` หายไปไหน บทที่ 08 วางคำถามนั้นไว้ข้างใน `run_shell` บทที่ 12
เอามันออกมา และคอมเมนต์ที่ทิ้งไว้ใน `tools.py` บอกเหตุผล

```python
def run_shell(command):
    # The confirmation that used to live here moved to permissions.py in
    # lesson 12. Asking in both places would ask the same question twice,
    # and a tool that asks its own questions cannot be reused by anything
    # that is not a terminal.
```

อนุประโยคสุดท้ายนั่นคือทั้งหมดของข้อโต้แย้ง tool ที่เรียก `input` มี terminal ฝังอยู่ในตัวมัน
เมื่อบทที่ 20 รัน tool ข้างใน subagent โดยไม่มีใครนั่งอยู่หน้าคีย์บอร์ด tool ที่ถามคำถามของ
ตัวเองจะค้างไปตลอดกาล

### session บันทึก และไม่ตัดสิน

`Session.append` เขียนหนึ่งบรรทัดแล้วไม่คืนค่าอะไร

```python
    def append(self, message):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")
```

มันไม่เคยตรวจดูข้อความเลย มันไม่สนใจ role มันไม่ข้ามผลลัพธ์ของ tool เพื่อประหยัดพื้นที่ มันไม่
สรุปย่อ และมันไม่ตัดสินว่าบทสนทนาไหนควรค่าแก่การเก็บ มันรับ dictionary มาแล้วเอาไปวางบนดิสก์

loop เข้าถึงมันผ่าน callback ที่ไม่รู้อะไรเกี่ยวกับไฟล์เลย

```python
    def remember(message):
        messages.append(message)
        if on_message:
            on_message(message)
```

`on_message` เป็นฟังก์ชันที่รับหนึ่ง argument ใน `main.py` มันบังเอิญเป็น `session.append`
ใน `check.py` บางครั้งมันเป็น `denied.append` สำหรับ session object ตัวที่สอง มันจะเป็น
ฟังก์ชันที่ส่งข้อมูลไปยัง socket หรือเพิ่มลงลิสต์ในการทดสอบก็ได้ และ loop ก็จะไม่มีทางรู้

เหตุผลที่เรื่องนี้สำคัญกว่าที่ตาเห็นคือการ debug ไฟล์ session จะมีประโยชน์ต่อการตอบคำถามว่า
ทำไม agent ถึงทำสิ่งนั้นก็ต่อเมื่อมันบันทึกสิ่งที่เกิดขึ้นจริง ไม่ใช่ฉบับที่ถูกตัดต่อแล้ว วินาทีที่ตัว
บันทึกเริ่มตัดสินใจ มันก็เริ่มมีความเห็นว่าอะไรควรค่าแก่การบันทึก และบรรทัดที่คุณต้องการก็คือ
บรรทัดที่มันตัดทิ้งไป

### การจัดการ context ย่อสิ่งที่ถูกส่งออกไป โดยไม่แตะสิ่งที่ถูกจดจำ

นี่คือขอบเขตที่คมที่สุดในโปรแกรม และมันมีห้าบรรทัด

```python
    def to_send():
        """What travels is not what is remembered.

        The full conversation stays in messages because the session file and
        anyone debugging later need all of it. Only the copy handed to the
        provider is trimmed.
        """
        return messages if budget is None else fit_to_budget(messages, budget)
```

`fit_to_budget` คืนลิสต์ใหม่ `messages` ไม่เคยถูกแก้ไข ดังนั้นไฟล์ session จึงได้ทุกข้อความ
ตลอดไป และ provider ได้เท่าที่พอดี

ทำกลับด้านแล้วคุณจะได้ bug ที่วินิจฉัยไม่ได้เลยในภายหลัง ตัด `messages` ตัวมันเองแล้วไฟล์
session จะบรรจุบทสนทนาที่ไม่เคยเกิดขึ้น พร้อมกับรูตรงกลางที่ตัวตัดเอาบล็อกออกไป จากนั้น
สามวันต่อมา คุณเปิดไฟล์นั้นเพื่อหาว่าทำไม agent ถึงทำอะไรบ้า ๆ ในเทิร์นที่เก้า แล้วหลักฐานที่คุณ
ต้องการก็ถูกลบไปแล้วโดยสิ่งที่ทำให้มันมีพฤติกรรมบ้า ๆ นั้น หลักฐานชิ้นเดียวที่จะอธิบายความล้มเหลว
ได้ ถูกแก้ไขโดยความล้มเหลวนั้นเอง

การแยกสองอย่างนี้ออกจากกันยังทำให้ `fit_to_budget` เป็น pure function ซึ่งเป็นเหตุผลว่า
ทำไมบทที่ 14 ถึงทดสอบมันได้ด้วยการยื่นลิสต์ให้แล้วดูลิสต์ที่คืนกลับมา โดยไม่มี agent และไม่มี
model อยู่ที่ไหนเลย

### retry ห่อการเรียก network เท่านั้น และไม่ห่ออย่างอื่น

`retry.py` คือฟังก์ชันที่รับ callable

```python
def with_retries(call, attempts=4, sleep=time.sleep):
```

มันไม่รู้จัก tool มันไม่รู้จัก loop สัญญาทั้งหมดของมันคือคุณยื่นสิ่งที่ทำซ้ำได้อย่างปลอดภัยให้ แล้ว
มันจะทำซ้ำให้ docstring ของ module พูดชัดเจนว่าทำไมข้อจำกัดนั้นถึงมีอยู่

```text
Not everything may be retried. Asking the model again is safe because it
changes nothing outside the conversation. Running a tool that sent an email
is not, which is why nothing in this module wraps a tool call.
```

จงซื่อสัตย์กับสถานะของการต่อสายไฟ เพราะมันสำคัญ ไม่มีอะไรในโฟลเดอร์นี้เรียก `with_retries`
เลย บทที่ 17 บอกไว้ว่ามันควรไปอยู่ตรงไหนและทำไม และที่ตรงนั้นคือข้างใน provider

```python
from retry import with_retries

# in OpenAICompatProvider
def stream(self, messages, tools=None, on_text=None):
    return with_retries(lambda: self._stream_once(messages, tools, on_text))
```

provider เป็น object เดียวในโปรแกรมนี้ที่รู้ว่ามันกำลังพูด HTTP อยู่ มันคือที่ที่ `httpx` ถูก
import และเป็นที่ที่ `raise_for_status` ถูกเรียก ดังนั้นมันจึงเป็นที่เดียวที่
`httpx.HTTPStatusError` เป็นชนิดข้อมูลที่มีความหมายพอจะดักจับ ถ้าเอา retry ไปวางใน loop
แทน `agent.py` ก็ต้อง import `httpx` เพื่อจะรู้ว่าความล้มเหลวแบบไหนควรทำซ้ำ และการที่ loop
ยังคงไม่รู้เรื่องสายส่งคือคุณสมบัติที่บทที่ 06 ซื้อมาและบทที่ 11 วัดผลไว้ แบบฝึกหัดข้อสามในหัวข้อ
ที่ 8 ต่อสายไฟมันจริง ๆ

### cancellation บอกให้หยุด และคนอื่นเป็นฝ่ายถามมัน

```python
class Cancellation:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()
```

สาม method รอบ ๆ `threading.Event` มันไม่เริ่มอะไรและไม่หยุดอะไรด้วยกำลัง มันคือธงที่หลาย
thread อ่านได้อย่างปลอดภัย และการหยุดเป็นหน้าที่ของคนที่อ่านมัน

loop อ่านมันในสองที่

```python
    def stop_requested():
        return cancellation is not None and cancellation.cancelled
```

หัวข้อที่ 4 ครอบคลุมว่าสิ่งนั้นทำอะไรได้และทำอะไรไม่ได้เมื่อคุณกดปุ่มจริง ๆ เพราะมันน้อยกว่าที่
docstring บอกเป็นนัย และคุณควรรู้ให้ชัดว่าช่องโหว่อยู่ตรงไหน

### usage นับสิ่งที่ provider บอกมา และไม่ประมาณอะไรเลย

`Usage.add` รับ dictionary ที่ provider รายงานมาแล้วบวกรวมกัน มันไม่ tokenise อะไรทั้งนั้น
`context.py` มีตัวประมาณชื่อ `estimate_tokens` และตัวเลขสองชุดนั้นถูกตั้งใจไม่ให้ปนกันเด็ดขาด
เพราะตัวประมาณมีไว้เพื่อตัดสินว่าจะเริ่มตัดเมื่อไร ส่วนตัวเลขที่ถูกรายงานมีไว้เพื่อบอกคุณว่าเกิด
อะไรขึ้นจริง

### ทำไมนี่ไม่ใช่แค่ความเป็นระเบียบ

นี่คือผลตอบแทน และมันเป็นการวัดผลมากกว่าจะเป็นความชอบทางสุนทรียะ

ระหว่างบทที่ 06 ถึงบทที่ 11 คุณเพิ่ม tool เจ็ดตัว ระหว่างบทที่ 12 ถึงบทที่ 17 คุณเพิ่ม
subsystem ห้าตัวและเครื่องมือ retrieval หนึ่งตัว ทุกอย่างเข้ามาในรูปของไฟล์ใหม่หนึ่งไฟล์ บวกกับ
parameter ใหม่บน `run` อย่างมากหนึ่งตัว ไม่มีสักอันที่ต้องเขียนวิธีทำงานของ loop ใหม่

ทีนี้ลองนึกภาพเวอร์ชันที่รอยต่ออยู่ที่อื่น เพราะมันง่ายมากที่จะไปจบตรงนั้น และมันมักเริ่มต้นอย่าง
สมเหตุสมผลเสมอ tool ของ shell ต้องถามก่อนที่มันจะรัน และ loop เป็นเจ้าของ terminal ดังนั้น
การถามจึงไปอยู่ใน loop ตอนนี้ loop มีสาขาหนึ่งที่เอ่ยชื่อ tool ตัวหนึ่ง จากนั้น session ก็ต้องถูก
เขียน และ loop คือที่ที่ข้อความปรากฏ ดังนั้นการจัดการไฟล์จึงไปอยู่ใน loop จากนั้นก็การตัด
เพราะ loop คือที่ที่ request ถูกสร้าง จากนั้นก็ usage จากนั้นก็ retry ดังนั้น loop จึง import
`httpx` จากนั้นก็ cancellation

หกบทต่อมา loop ยาวสี่ร้อยบรรทัด ทุก subsystem มีสาขาอยู่ในนั้น และไฟล์เดียวที่ทุกฟีเจอร์ต้อง
วิ่งผ่านก็คือไฟล์ที่ไม่มีใครกล้าแก้ การเพิ่ม subsystem ตัวที่เจ็ดตอนนี้หมายถึงการแก้โค้ดที่อันตราย
ที่สุดในโปรแกรม และทุกการแก้ก็เสี่ยงต่อหกตัวที่ทำงานได้อยู่แล้ว

การออกแบบทั้งสองแบบรัน agent ตัวเดียวกันในวันที่คุณทำมันเสร็จ มันแยกทางกันในวันที่สามสิบ
และหัวข้อถัดไปวัดว่าแยกกันไปไกลแค่ไหน

## 3. เปรียบเทียบ loop กับบทที่ 04

บทที่ 11 ทำการเปรียบเทียบนี้ตอนจบภาค 2 และคำตอบคือ loop แทบไม่เปลี่ยนเลย การเปรียบเทียบ
แบบเดียวกันตอนนี้จะไม่ซื่อสัตย์ถ้ามันอ้างผลลัพธ์เดิม เพราะภาค 3 เปลี่ยน loop จริง ดังนั้นจงพูดให้
แม่นยำว่าเปลี่ยนอย่างไร และอะไรเป็นสาเหตุ

นี่คือบทที่ 04 agent ตัวแรกที่คุณเคยมี ก่อนจะมี tool จริง ก่อนจะมี streaming ก่อนจะมี provider

```python
def run(user_input, max_turns=10):
    """Run the agent until it produces a final answer. Returns the answer."""
    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_turns):
        text, calls = complete(messages, tools.SCHEMAS)

        if not calls:
            return text

        messages.append({...assistant message with tool_calls...})

        for call in calls:
            print(f"[calling {call['name']} with {call['arguments']}]")
            result = tools.run(call["name"], call["arguments"])
            print(f"[{call['name']} returned {result}]")
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": result}
            )

    raise RuntimeError(f"agent stopped after max turns ({max_turns})")
```

ห้าสิบสี่บรรทัดรวม docstring นี่คือ signature ที่มันมีในวันนี้

```python
def run(
    provider,
    user_input,
    system=None,
    permissions=None,
    on_message=None,
    history=None,
    budget=None,
    cancellation=None,
    usage=None,
    max_turns=10,
):
```

หนึ่งร้อยสี่สิบบรรทัด นั่นไม่ใช่การเปลี่ยนแปลงเล็ก ๆ และการแกล้งทำเป็นว่ามันเล็กคือบทเรียนที่ผิด

### ทุกความแตกต่าง และบทเรียนที่เป็นสาเหตุ

รายการครบถ้วน ถ้ามันไม่ครบ ข้อโต้แย้งตอนท้ายก็จะไม่มีค่าอะไรเลย

| ความแตกต่าง | บทที่ |
| --- | --- |
| `complete(...)` กลายเป็น `provider.stream(...)` | 05 ให้ streaming กับมัน 06 ให้ argument ที่เป็น provider |
| callback `on_text` ที่พิมพ์ออกมาขณะข้อความทยอยมาถึง | 05 |
| `tools.SCHEMAS` ถูกแกะออกด้วย `[t["function"] for t in ...]` | 06 ที่ provider เป็นคนห่อ |
| สาขา `call["error"]` สำหรับ argument ที่ parse ไม่ได้ | 05 |
| parameter `system=None` และข้อความที่มันเติมไว้ข้างหน้า | 10 |
| การคืน `(text, messages)` แทน `text` | 10 เพื่อให้ผู้เรียกตรวจดูบทสนทนาได้ |
| parameter `permissions` และสาขา `permissions.check` | 12 |
| parameter `on_message` และตัวช่วย `remember` | 13 |
| parameter `history` และ `messages = list(history or [])` | 13 |
| `if system and not messages` เพื่อไม่ให้การรันที่ resume ได้ system message สองอัน | 13 |
| parameter `budget` และตัวช่วย `to_send` | 14 |
| `provider.stream` คืนค่าสามตัว และ `usage.add(reported)` | 15 |
| การตรวจจับการทำซ้ำด้วย `signature`, `recent`, `warned` และ `REPEAT_LIMIT` | 15 |
| parameter `cancellation` และการตรวจ `stop_requested` สองจุด | 17 |

สิบสี่ความแตกต่าง ทีนี้จัดเรียงมันตามสาเหตุแทนที่จะตามหมายเลขบรรทัด

สองอันมาจาก streaming สองอันจากการทำ abstraction ของ provider สองอันจาก system prompt
หนึ่งอันจาก permission สามอันจาก session หนึ่งอันจากการจัดการ context สองอันจากการบริหาร
token หนึ่งอันจาก error และการ interrupt

ศูนย์อันมาจากการเพิ่ม tool

นั่นคือประโยคที่การเปรียบเทียบทั้งหมดนี้มีอยู่เพื่อผลิตออกมา สิบสี่การเปลี่ยนแปลงต่อฟังก์ชันที่
สำคัญที่สุดในโปรแกรม ตลอดสิบสี่บท และไม่มีสักอันเลยที่เกิดจากการสอนให้ agent ทำอะไรใหม่

### หลักฐาน ที่วัดผลแทนที่จะกล่าวอ้าง

คุณไม่ต้องเชื่อตารางนั้นด้วยศรัทธา จง hash ไฟล์ในทุกบท

```bash
cd lessons
for d in 06-provider-abstraction 07-file-tools 08-shell-tool 09-search-tools \
         10-anatomy-of-a-prompt 11-mini-coding-agent 12-permissions 13-sessions \
         14-context-management 15-token-economy 16-retrieval \
         17-errors-and-retries 18-the-harness; do
  printf "%-28s %s  %s lines\n" "$d" "$(md5sum $d/agent.py | cut -c1-32)" \
         "$(wc -l < $d/agent.py)"
done
```

```text
06-provider-abstraction      b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
07-file-tools                b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
08-shell-tool                b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
09-search-tools              b50c7e42ba1eac5d93fb4f678b0b0f05  48 lines
10-anatomy-of-a-prompt       02cf3a892d2e8c2e885b0c1af078b6c9  52 lines
11-mini-coding-agent         02cf3a892d2e8c2e885b0c1af078b6c9  52 lines
12-permissions               a01da24bdf59c0d570e8e24179b10c54  60 lines
13-sessions                  f12dce1e312f8d0c91814d07d3813fb4  80 lines
14-context-management        3b5ff3dc951bedc2578f8c81ab330d7d  91 lines
15-token-economy             7751a3e429e71a0f305ccfeb0ddc6519  130 lines
16-retrieval                 7751a3e429e71a0f305ccfeb0ddc6519  130 lines
17-errors-and-retries        3fb92af29d8aa02403e0e76984b74aa4  140 lines
18-the-harness               3fb92af29d8aa02403e0e76984b74aa4  140 lines
```

อ่านตารางนั้นสองรอบ เพราะมันบอกสองเรื่องที่ต่างกัน

**บทที่ 07, 08 และ 09 เป็นไบต์เดียวกับบทที่ 06** tool ไฟล์สี่ตัว shell ที่มี timeout glob และ
grep การจำกัดเส้นทาง การปฏิเสธไฟล์ลับ การตัดผลลัพธ์ให้สั้น การปฏิเสธการแก้ไขที่กำกวม และ
timeout ของ subprocess แล้ว loop ก็ไม่เปลี่ยนเลยสักครั้ง

**บทที่ 16 เป็นไบต์เดียวกับบทที่ 15** นั่นคืออันที่ควรนั่งอยู่กับมันสักพัก เพราะ retrieval คือฟีเจอร์
ที่มีแนวโน้มมากที่สุดที่จะถูกสร้างเป็นระบบพิเศษที่มี hook ของตัวเองอยู่กลางทุกสิ่ง บทที่ 16 สร้าง
vector index ตัว embedder และตัวให้คะแนน แล้วส่งมอบมันในรูปของ `search_notes` ใน
`tools.py` ซึ่งแปลว่า loop ไม่มีอะไรจะพูดเกี่ยวกับมันเลย

**ทุกบทที่เปลี่ยน loop คือบทที่เพิ่ม subsystem** permission ในบทที่ 12 session ในบทที่ 13
การตัดในบทที่ 14 การนับและตัวกันลูปวนซ้ำในบทที่ 15 cancellation ในบทที่ 17 ห้า subsystem
ห้าการเปลี่ยนแปลงใน `agent.py`

รูปแบบมันตรงเป๊ะ tool ไม่เคยแตะ loop subsystem แตะเสมอ

### รูปทรงเดิม แค่ parameter มากขึ้น

ประเด็นสุดท้ายที่ซื่อสัตย์ จำนวนบรรทัดโตขึ้นสามเท่า แต่ถ้าเอาสองฟังก์ชันมาวางเทียบกัน
โครงกระดูกของมันเหมือนกันเป๊ะ

```python
    for _ in range(max_turns):        # same loop, same bound
        ...                           # ask the model
        if not calls:                 # same early return
            return ...
        remember({...assistant...})   # same append
        for call in calls:            # same inner loop
            result = ...              # decide, then run
            remember({...tool...})    # same append
    raise RuntimeError(...)           # same bottom
```

ทุกอันในสิบสี่ความแตกต่างเป็นได้แค่ parameter หรือสาขาข้างในโครงกระดูกนั้น ไม่มีอันไหนเปลี่ยน
วิธีที่หนึ่งเทิร์นทำงาน ถาม รัน ป้อนกลับ ถามอีกครั้ง หยุดเมื่อมันตอบด้วยคำพูด คือสี่ขั้นตอนเดียวกับ
ที่มันเป็นในบทที่ 04 และนั่นคือเหตุผลที่ loop สามารถได้รับ permission session การตัด การนับ
และ cancellation ทีละอย่างโดยไม่มีอันไหนไปรบกวนกันเลย

การเติบโตนั้นเป็นเรื่องจริง แต่รูปทรงไม่ขยับ

## 4. เดินผ่าน main.py

ทีนี้มาถึงไฟล์ใหม่ มันยาวราวแปดสิบบรรทัดและไม่มี logic ของ agent อยู่เลย การตัดสินใจห้าอย่าง
ของมันมีค่ามากกว่าจำนวนบรรทัดที่มันกิน

### การ parse argument

```python
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("task", nargs="?", help="What you want the agent to do")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--session", default=None)
    parser.add_argument("--resume", default=None, help="Name of a session to carry on from")
    parser.add_argument("--budget", type=int, default=100000)
    parser.add_argument("--yes", action="store_true", help="Approve everything without asking")
    arguments = parser.parse_args()
```

```bash
python main.py --help
```

```text
usage: harness [-h] [--workspace WORKSPACE] [--session SESSION]
               [--resume RESUME] [--budget BUDGET] [--yes]
               [task]

positional arguments:
  task                  What you want the agent to do

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
  --session SESSION
  --resume RESUME       Name of a session to carry on from
  --budget BUDGET
  --yes                 Approve everything without asking
```

`argparse` อยู่ใน standard library ด้วยเหตุผลเดียวกับที่ `fnmatch` และ `re` เป็นคำตอบที่ถูกต้อง
ในบทที่ 09 คอร์สที่บังคับให้คุณติดตั้ง framework สำหรับ CLI ก่อนถึงบทหมุดหมาย คือคอร์สที่ใช้
dependency ไปกับสิ่งที่ standard library ทำได้ดีพออยู่แล้ว และทุก dependency คืออีกจุดหนึ่งที่
ผู้อ่านจะติดอยู่กับสิ่งที่ไม่ใช่หัวข้อของบท

`task` เป็นแบบ positional และไม่บังคับ ใส่มันเข้าไปแล้ว agent จะเริ่มทันที ซึ่งคือสิ่งที่คุณต้องการ
เวลาเขียนสคริปต์ ไม่ใส่แล้วคุณจะถูกถาม ซึ่งคือสิ่งที่คุณต้องการเวลาที่ยังตัดสินใจไม่ได้ การทำให้มัน
เป็น flag จะใส่พิธีกรรมเพิ่มอีกสี่ตัวอักษรลงบนสิ่งที่คุณพิมพ์บ่อยที่สุด

`--budget` รับจำนวนเต็มและมีค่าเริ่มต้นเป็นหนึ่งแสน สังเกตให้ดีว่ามันวัดด้วยหน่วยอะไร เพราะมันไม่ใช่
หน่วยเดียวกับตัวเลขที่พิมพ์ออกมาตอนจบการรัน มันถูกป้อนให้ `fit_to_budget` ซึ่งนับด้วย
`estimate_tokens` ซึ่งเป็นการประมาณจากจำนวนตัวอักษร ส่วนบรรทัด usage ตอนท้ายรายงานสิ่งที่
provider นับมา บทที่ 15 ใช้ทั้งหัวข้อไปกับเหตุผลว่าทำไมตัวเลขสองตัวนั้นต้องไม่ถูกสับสนกันเด็ดขาด
และนี่คือจุดที่ความสับสนจะเกิดขึ้น ดังนั้นค่าประมาณจึงถูกใช้เพื่อตัดสินว่าจะตัดเมื่อไรเท่านั้น และไม่
เคยถูกใช้ตัดสินว่าอะไรมีต้นทุนเท่าไร

`--yes` มีอยู่เพื่อให้เครื่องจักรรันสิ่งนี้ได้ มีประตูที่สองสำหรับสิ่งเดียวกัน และทั้งสองประตูถูกให้เกียรติ

```python
    permissions = Permissions(
        ask=ask_in_terminal,
        auto_approve=arguments.yes or os.environ.get("AGENTPATH_AUTO_APPROVE") == "1",
    )
```

environment variable ตัวนั้นอยู่ในโปรเจกต์มาตั้งแต่บทที่ 08 และเป็นตัวที่ `ci/run_lessons.py`
ตั้งค่า ส่วน flag มีไว้ให้คุณตอนอยู่หน้าคีย์บอร์ด ทั้งสองมีความหมายเดียวกัน มันจึงตั้งค่า field
เดียวกัน แทนที่จะมีสวิตช์สองตัวที่พฤติกรรมต่างกันอย่างแนบเนียน

### สองบรรทัดที่ลำดับของมันเป็นตัวรับน้ำหนัก

นี่คือส่วนที่กัดคนที่ชอบจัดระเบียบ

```python
    workspace = Path(arguments.workspace).resolve()
    os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

    from agent import run
    from cancel import Cancellation
    from permissions import Permissions, ask_in_terminal
    from prompt import build_system_prompt
    from providers import OpenAICompatProvider
    from session import Session
    from usage import Usage
```

การ import อยู่ที่ก้นฟังก์ชันแทนที่จะอยู่บนหัวไฟล์ อย่างจงใจ ดูสิ่งที่ `tools.py` ทำตอน Python
โหลดมัน

```python
WORKSPACE = Path(os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()
```

บรรทัดนั้นรันครั้งเดียว ตอน import และไม่รันอีกเลย `from agent import run` จะ import
`agent` ซึ่ง import `tools` ซึ่งรันบรรทัดนั้น พอ `run` มีตัวตนเป็นชื่อใน `main.py` แล้ว
workspace ก็ถูกตรึงไว้ตลอดชีวิตของ process

ตั้ง environment variable หลังการ import แล้วมันจะไม่ทำอะไรเลย โปรแกรมจะไม่พัง มันจะไม่เตือน
คุณ มันจะ resolve ทุกเส้นทางเทียบกับไดเรกทอรีที่คุณบังเอิญยืนอยู่ ดังนั้น
`--workspace ../other-project` จะอ่าน เขียน และแก้ไขไฟล์ในต้นไม้ที่ผิด ขณะที่พิมพ์ไดเรกทอรี
ที่ถูกไว้บนหัวจอ กฎการจำกัดขอบเขตที่ประกาศแต่ไม่ถูกบังคับใช้ แย่กว่าการไม่มีกฎเลย เพราะคุณจะ
ผ่อนคลายกับมัน

`resolve()` ก่อนเก็บ เพราะมีสามสิ่งแยกกันที่อยู่ปลายน้ำต้องการเส้นทางแบบสัมบูรณ์
`resolve_inside` เปรียบเทียบตัวเลือกกับ `WORKSPACE` ด้วย `is_relative_to` ซึ่งไร้ความหมาย
เมื่อ `WORKSPACE` เป็น `.` `run_shell` ส่ง `cwd=WORKSPACE` ให้ `subprocess.run` และ
`build_system_prompt` ใส่ไดเรกทอรีลงใน system prompt ในฐานะข้อเท็จจริงเกี่ยวกับโลก และ
model ที่ถูกบอกว่ามันทำงานอยู่ใน `.` ก็เท่ากับไม่ถูกบอกอะไรเลย

`check.py` ทำสิ่งเดียวกันด้วยเหตุผลเดียวกัน และทำเครื่องหมายไว้

```python
os.environ["AGENTPATH_HOME"] = str(home)
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

from agent import run  # noqa: E402
```

`# noqa: E402` คือวิธีที่ซื่อสัตย์ในการแหกกฎสไตล์ E402 คือ linter ที่บ่นว่ามี import ไม่ได้อยู่
บนหัวไฟล์ มันพูดถูกที่ว่านี่เป็นเรื่องผิดปกติ และเรากำลังบอกมันว่าเรารู้ อย่างตั้งใจ ตรงนี้

### ชื่อ session ถูกเลือกอย่างไร

หนึ่งบรรทัด สามกรณี

```python
    session = Session(arguments.resume or arguments.session or new_session_name())
    history = session.load() if arguments.resume else []
```

`--resume` ชนะขาด และมันชนะด้วยการให้ชื่อเดียวกัน ซึ่งเป็นสิ่งที่ทำให้การรันที่ resume เขียน
ต่อท้ายไฟล์ที่มันเพิ่งอ่านแทนที่จะเริ่มไฟล์ใหม่ คุณสมบัตินั้นคุ้มค่าแก่การหยุดคิด การ resume ไม่ใช่
การคัดลอก ไฟล์ session คือบันทึกต่อเนื่องอันเดียวของงานทั้งชิ้น ไม่ว่าคุณจะเดินจากมันไปกี่ครั้ง

`--session` มาเป็นอันดับถัดไป สำหรับเวลาที่คุณอยากได้ชื่อที่คุณเลือกเอง การตั้งชื่อ session ว่า
`refactor-auth` คือความต่างระหว่างการหามันเจอในอีกหนึ่งเดือนกับการหาไม่เจอ

และเมื่อไม่ได้ให้ทั้งสองอย่าง ก็ใช้ timestamp

```python
def new_session_name():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
```

สามคุณสมบัติ แต่ละอันคือเหตุผลว่าทำไมมันไม่เป็นอย่างอื่น มันไม่ชนกันในทางปฏิบัติ ซึ่งถ้าใช้ตัวนับ
ก็ต้องอ่านไดเรกทอรีก่อนถึงจะทำได้ มันเรียงตามเวลาได้ในฐานะสตริง ดังนั้น `ls` ในโฟลเดอร์
sessions จึงเรียงถูกอยู่แล้วโดยไม่ต้องทำอะไร และมันเป็น UTC เพราะชื่อที่ขยับเมื่อคุณข้ามเขตเวลา
หรือเมื่อ daylight saving สิ้นสุด จะผลิต session สองอันที่เรียงลำดับผิดเทียบกัน และโฟลเดอร์
sessions คือที่เดียวที่การเรียงลำดับนั้นปรากฏ

ทางเลือกที่เห็นได้ชัดคือ UUID UUID นั้นไม่ซ้ำและจำไม่ได้เลยสักนิด ส่วนไฟล์ session คือสิ่งที่คุณเปิด
ในโปรแกรมแก้ไขข้อความเมื่อคุณอยากรู้ว่าทำไม agent ถึงทำอะไรบางอย่าง `20260901-142233`
บอกคุณว่าคุณรันมันเมื่อไร `f47ac10b-58cc-4372-a567-0e02b2c3d479` ไม่บอกอะไรคุณเลย

### resume โหลดประวัติและส่งมันเข้าไปอย่างไร

สองบรรทัดใน `main.py` บวกกับหนึ่งบรรทัดใน `agent.py` ที่ทำให้มันถูกต้อง

```python
    history = session.load() if arguments.resume else []
```

`Session.load` อ่านไฟล์ JSONL แล้วคืนลิสต์ของ dictionary สิ่งเหล่านั้นเข้าไปใน `run` ตรง ๆ

```python
        run(
            provider,
            task,
            system=build_system_prompt(workspace),
            ...
            history=history,
```

ทีนี้สังเกตสิ่งที่ดูเหมือน bug แต่ไม่ใช่ `main.py` ส่ง system prompt เสมอ แม้ตอน resume แม้ว่า
ประวัติที่โหลดมาจะขึ้นต้นด้วย system prompt อยู่แล้ว loop จัดการเรื่องนี้

```python
    messages = list(history or [])
    ...
    if system and not messages:
        remember({"role": "system", "content": system})
```

`and not messages` คือกลไกป้องกันทั้งหมด ในการรันใหม่ `messages` ว่างเปล่าและ system
prompt ถูกเติมไว้ข้างหน้า ในการรันที่ resume `messages` ถือบทสนทนาทั้งหมดไว้แล้ว system
prompt จึงถูกข้าม และอันที่ถูกบันทึกไว้บนหัวไฟล์ถูกใช้แทน

ทางเลือกทั้งสองแบบแย่กว่า และควรรู้ว่าทำไม การเติม system prompt ใหม่เข้าไปอยู่ดีจะให้บทสนทนา
ที่มี system message สองอัน และ provider แต่ละเจ้าปฏิบัติกับสิ่งนั้นต่างกัน ซึ่งแปลว่าเป็น bug ที่
โผล่บน model หนึ่งแต่ไม่โผล่บนอีก model หนึ่ง ส่วนการแทนที่อันเก่าคือการเปลี่ยนคำสั่งกลางงาน
อย่างเงียบ ๆ ดังนั้น session ที่ resume หลังจากคุณแก้ `prompt.py` จะมีพฤติกรรมต่างจากอันที่
คุณบันทึกไว้ โดยไม่มีอะไรในไฟล์บันทึกไว้เลยว่ากฎถูกเปลี่ยนใต้ตีนมัน

`list(history or [])` คือสำเนา ไม่ใช่ตัวลิสต์เอง ดังนั้นลิสต์ของผู้เรียกจึงไม่ถูกแก้ไขโดยการรัน
`check.py` พึ่งพาสิ่งนั้นในข้ออ้างที่สี่ของมัน ตรงที่มันเทียบความยาวก่อนกับความยาวหลัง

### ตัวจัดการ interrupt ถูกติดตั้งอย่างไร

```python
    def handle_interrupt(signum, frame):
        if cancellation.cancelled:
            raise KeyboardInterrupt
        print("\nStopping after the current step. Press Ctrl+C again to force it.")
        cancellation.cancel()

    try:
        signal.signal(signal.SIGINT, handle_interrupt)
    except ValueError:
        pass
```

กดสองครั้ง พฤติกรรมสองแบบ และนั่นคือการออกแบบทั้งหมด

การกดครั้งแรกตั้งธงและบอกคุณว่ามันทำอะไรไป loop สังเกตเห็นที่จุดตรวจถัดไปแล้วโยน
`KeyboardInterrupt` ออกมาจากจุดที่บทสนทนาอยู่ในสภาพที่สอดคล้องกัน ดังนั้น `main` จึงดักจับ
มัน พิมพ์ `stopped` และยังไปถึงสองบรรทัดที่รายงานเส้นทางของ session และ usage ได้ คุณ
interrupt agent และคุณเก็บงานไว้ได้

การกดครั้งที่สองโยนออกมาทันที จากข้างในตัวจัดการ signal ณ ที่ใดก็ตามที่โปรแกรมบังเอิญอยู่
นั่นคือความรุนแรงโดยเจตนา มันมีอยู่เพราะการหยุดแบบสุภาพจะมีผลได้ก็ต่อเมื่อถึงจุดตรวจ และถ้า
โปรแกรมติดหนึบอยู่ที่ไหนสักแห่งที่ไม่มีจุดตรวจอยู่ข้างหน้า การหยุดแบบสุภาพก็ไม่มีวันมาถึง
ปุ่มหยุดที่ตัวมันเองค้างได้ ไม่ใช่ปุ่มหยุด

`try` ที่ล้อมรอบ `signal.signal` ไม่ใช่เสียงรบกวนเพื่อป้องกันตัว `signal.signal` โยน
`ValueError` เมื่อมันไม่ได้ถูกเรียกจาก thread หลักของ interpreter หลัก และฟังก์ชัน `main` อัน
นี้เอง import ได้และเรียกได้จากตัวรัน test หรือจากโปรแกรมอื่น ถ้าไม่มีตัวป้องกัน `main()` จะพัง
บนบรรทัดที่ไม่เกี่ยวอะไรกับงานเลย ในสภาพแวดล้อมที่ไม่มีใครจะกด Ctrl+C อยู่แล้ว

ทีนี้มาถึงส่วนที่ซื่อสัตย์ เพราะ docstring ใน `cancel.py` สัญญาไว้มากกว่าที่โปรแกรมนี้ส่งมอบ

```text
The same token is checked by the agent loop between turns and by the shell
tool before it starts a process
```

grep หา cancellation token ใน `tools.py` แล้วคุณจะไม่เจอ `run_shell` ไม่ปรึกษามัน loop
ตรวจสองที่ ก่อนแต่ละเทิร์นและก่อนแต่ละการเรียก

```python
    for _ in range(max_turns):
        if stop_requested():
            raise KeyboardInterrupt("cancelled")
        ...
        for call in calls:
            if stop_requested():
                raise KeyboardInterrupt("cancelled")
```

ดังนั้นกด Ctrl+C หนึ่งครั้งขณะที่ `run_shell` ที่กินเวลาหกสิบวินาทีกำลังทำงานอยู่ subprocess
ก็จะทำงานจนจบ การหยุดจะมีผลหลังจากนั้น ก่อนการเรียกครั้งถัดไป มันคือช่องโหว่จริง มันคือช่องโหว่
ที่ `cancel.py` ถูกเขียนขึ้นมาเพื่อเตือนพอดี และสิ่งที่ซื่อสัตย์คือการเรียกชื่อมันตรงนี้ แทนที่จะปล่อยให้
docstring บอกเป็นนัยว่ามันถูกปิดแล้ว แบบฝึกหัดข้อสี่ในหัวข้อที่ 8 ปิดมัน

### สี่บรรทัดสุดท้าย

```python
    print(f"\nsession {session.name} saved to {session.path}")
    print(f"usage {usage.summary()}")
    return 0
```

สิ่งเหล่านี้พิมพ์หลัง `try` ที่ดักจับ `KeyboardInterrupt` ซึ่งคือประเด็นของการที่มันอยู่ตรงนั้น
การรันที่ถูก interrupt ก็ยังบอกคุณว่าบทบันทึกของมันอยู่ที่ไหนและมันใช้ไปเท่าไร harness ที่พิมพ์
ใบเสร็จเฉพาะตอนสำเร็จ คือ harness ที่ซ่อนตัวเลขไว้ตอนที่การรันไปผิดทางพอดี ซึ่งเป็นตอนที่คุณ
ต้องการมันที่สุด

`raise SystemExit(main())` ที่ก้นไฟล์ทำให้ `main` คืนค่า exit code แทนที่จะเรียก `sys.exit`
จากข้างในตัวมัน ซึ่งทำให้ `main` ยังเป็นฟังก์ชันธรรมดาที่โปรแกรมอื่นเรียกได้โดยไม่ทำให้
interpreter ตาย

## 5. รันมันกับงานจริง

อ่านมาพอแล้ว สร้างอะไรที่พังแล้วชี้ harness ไปที่มัน

สร้างโฟลเดอร์นอก repository นี้ที่มีไฟล์สองไฟล์อยู่ข้างใน

```bash
mkdir -p ~/code/salestool
cd ~/code/salestool
```

`stats.py` ที่มี bug อยู่ข้างในซึ่งคุณไม่ควรแก้

```python
"""Small helpers for summarising a list of numbers."""


def total(numbers):
    return sum(numbers)


def average(numbers):
    if not numbers:
        return 0
    return total(numbers) / (len(numbers) + 1)


def largest(numbers):
    return max(numbers)
```

`report.py` ซึ่งใช้มัน

```python
from stats import average, largest, total

SALES = [120, 80, 100]

print("total", total(SALES))
print("average", average(SALES))
print("largest", largest(SALES))
```

รันมันแล้วดูอาการ

```bash
python report.py
```

```text
total 300
average 75.0
largest 120
```

สองในสามตัวเลขถูกต้อง สามร้อยหารด้วยสามค่าควรได้ค่าเฉลี่ยเป็นหนึ่งร้อย ไม่ใช่เจ็ดสิบห้า bug คือ
`len(numbers) + 1` ซึ่งเป็นความคลาดเคลื่อนหนึ่งหน่วยที่ผลิตตัวเลขที่ดูสมเหตุสมผลแทนที่จะพัง
ซึ่งเป็นชนิดที่รอดจากการ review โค้ดมาได้

ตั้งค่าสภาพแวดล้อมของคุณ นี่คือตัวแปรสามตัวเดียวกันจากบทที่ 00

```bash
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen3
export AGENTPATH_API_KEY=

cd /path/to/agentpath/lessons/18-the-harness
python main.py "The average is wrong in this project. Find it, fix it, and prove the fix." \
  --workspace ~/code/salestool --session salestool-1
```

บน Windows PowerShell การ export คือ `$env:AGENTPATH_BASE_URL = "..."` และการขึ้น
บรรทัดใหม่ใช้ backtick แทน backslash

### บทบันทึกการทำงาน

```text
Working in /home/you/code/salestool

[calling grep_files with {'pattern': 'def average', 'glob': '*.py'}]
[grep_files returned stats.py:8: def average(numbers):]

[calling read_file with {'path': 'stats.py'}]
[read_file returned """Small helpers for summarising a list of numbers."""


def total(numbers):
    return sum(numbers)


def average(numbers):
    if not numbers:
        return 0
    return total(numbers) / (len(numbers) + 1)


def largest(numbers):
    return max(numbers)
]

The agent wants to run edit_file
  path = 'stats.py'
  old = 'return total(numbers) / (len(numbers) + 1)'
  new = 'return total(numbers) / len(numbers)'
Allow? [y]es once, [a]lways for this exact call, [N]o y

[calling edit_file with {'path': 'stats.py', 'old': 'return total(numbers) / (len(numbers) + 1)', 'new': 'return total(numbers) / len(numbers)'}]
[edit_file returned Edited stats.py]

The agent wants to run run_shell
  command = 'python report.py'
Allow? [y]es once, [a]lways for this exact call, [N]o y

[calling run_shell with {'command': 'python report.py'}]
[run_shell returned total 300
average 100.0
largest 120
]
The tool returned total 300
average 100.0
largest 120
.

session salestool-1 saved to /home/you/.agentpath/sessions/salestool-1.jsonl
usage 5 calls, 1629 prompt tokens, 87 completion tokens
```

อ่านมันในฐานะห้าบทเรียนที่ทยอยมาถึงตามลำดับ

**`grep_files` คือบทที่ 09** คุณไม่ได้ระบุชื่อไฟล์ คุณบอกว่าค่าเฉลี่ยผิด แล้วมันก็ค้นหา
`def average` โดยจำกัดไว้ที่ `*.py` และได้ผลลัพธ์หนึ่งรายการพร้อมเส้นทางและหมายเลขบรรทัด

**`read_file` คือบทที่ 07** มันเอาเส้นทางจากผลลัพธ์ก่อนหน้าแล้วยื่นให้ tool ตัวถัดไปโดยไม่มี
การแปลงใด ๆ ซึ่งคือคุณสมบัติที่บทที่ 09 โต้แย้งไว้ตอนอธิบายว่าทำไมการค้นหาถึงคืนเส้นทางแทนที่
จะคืนบทสรุป

**คำถามขอสิทธิ์สองครั้งคือบทที่ 12 และมันคือความต่างที่มองเห็นได้จากภาค 2** สังเกตว่าการเรียก
ไหนถูกกั้นประตูและอันไหนไม่ถูกกั้น `grep_files` และ `read_file` ผ่านไปโดยไม่ถูกถามเพราะมัน
อยู่ใน `SAFE_TOOLS` และทำลายอะไรไม่ได้ ส่วน `edit_file` และ `run_shell` ทั้งคู่หยุดและรอ
ในภาค 2 มีแค่ `run_shell` ที่ถูกกั้น และคำสั่งที่ถูกฉีดเข้ามาซึ่งบอกให้เขียนไฟล์แทนที่จะรันคำสั่ง
ก็ไม่เจอประตูอะไรเลย

สังเกตด้วยว่าคำถามนั้นพิมพ์อะไรออกมา ไม่ใช่สตริงคำสั่งที่ถูกจัดรูปแล้ว แต่เป็น dictionary ของ
argument หนึ่งคีย์ต่อหนึ่งบรรทัด `ask_in_terminal` ไม่รู้ว่า `edit_file` คืออะไร มันจึงจัดรูปแบบ
พิเศษให้ไม่ได้ และการพิมพ์ทุก argument คือสิ่งเดียวที่มันทำได้ซึ่งรับประกันว่าครบถ้วน ประตูที่สรุป
ย่อสิ่งที่มันกำลังจะอนุญาต คือประตูที่อาจตกส่วนที่สำคัญไป

ตัวเลือก `[a]lways` คือคำตอบต่อปัญหาความล้าจากบทที่ 12 ตอบ `a` ให้ `python report.py`
หนึ่งครั้ง แล้วครั้งที่สามและสี่ที่มันรัน มันจะไม่ถาม สิ่งที่ถูกจดจำคือ signature เต็มรวมถึง argument
ดังนั้นการอนุญาต `python report.py` ตลอดไปจึงไม่อนุญาต `rm -rf .` แม้แต่ครั้งเดียว

**`run_shell` คือบทที่ 08 และมันคือประเด็นของบทบันทึกนี้** agent ไม่ได้ประกาศว่าแก้แล้ว
มันรันโปรแกรม `average 100.0` คือหลักฐาน และมันถูกผลิตขึ้นด้วยการรันโค้ด ไม่ใช่ด้วยการกล่าวอ้าง

**สองบรรทัดสุดท้ายคือบทที่ 13 และ 15** เส้นทางไฟล์ที่คุณเปิดได้ และตัวเลขที่คุณเอาไปเทียบกับ
การรันครั้งถัดไปได้ ทั้งสองอย่างไม่มีอยู่ตอนจบภาค 2

บันทึกที่ซื่อสัตย์สามข้อ บทบันทึกนี้ถูกเก็บมาจากการรัน `main.py` จริงกับ mock server ของ
โปรเจกต์ แทนที่จะเป็น model ที่ต้องจ่ายเงิน โดยเส้นทาง home directory และ workspace ถูกย่อ
ให้อ่านง่าย ทุกอย่างที่ harness พิมพ์ออกมาคือสิ่งที่ออกมาจริงเป๊ะ ๆ และผลที่มองเห็นได้อย่างเดียว
จาก mock คือ id ของการเรียก tool ในไฟล์ session ข้างล่างอ่านว่า `call_mock_1` และ
`call_mock_2` ตรงที่ provider จริงจะใส่ id ของตัวเอง

ประโยคของ model เองระหว่างการเรียก tool ไม่ถูกแสดง เพราะมันต่างกันไปในแต่ละการรันและแต่ละ
model model ขนาดเล็กที่รันในเครื่องมักไม่พูดอะไรเลยระหว่างการเรียก ส่วนตัวใหญ่กว่าจะบรรยาย
และความแปรผันนั้นเป็นเรื่องปกติ และลำดับที่แน่นอนก็ต่างกันได้ model ที่อ่านก่อนจะ grep หรือรัน
โปรแกรมก่อนเพื่อดูความล้มเหลวด้วยตาตัวเอง ก็ไม่ได้ทำอะไรผิด ไม่มีบทบันทึกที่ถูกต้องเพียงหนึ่งเดียว
ซึ่งเป็นเหตุผลที่หัวข้อถัดไปพิสูจน์ผลลัพธ์แทนที่จะพิสูจน์เส้นทาง

บันทึกเรื่องสภาพแวดล้อมหนึ่งข้อที่ไม่ใช่การสมมติ เพราะมันเกิดขึ้นจริงระหว่างที่เขียนบทนี้ ถ้า
`python` ไม่อยู่บน `PATH` ข้างใน shell ที่ `subprocess.run` ใช้ การเรียกครั้งที่สี่นั้นจะกลับมา
แบบนี้

```text
[run_shell returned 'python' is not recognized as an internal or external command,
operable program or batch file.

[exit code 1]]
```

ซึ่งคือ `run_shell` ทำสิ่งที่ถูกต้องเป๊ะ ๆ มันจับ stderr และ exit code แล้วยื่นทั้งสองอย่างให้
model ในฐานะผลลัพธ์ของ tool แทนที่จะโยน exception ดังนั้น agent จึงได้อ่านความล้มเหลวและ
ลอง `py report.py` หรือเส้นทางเต็มของ interpreter นี่คือการออกแบบของบทที่ 08 ที่ปรากฏออกมา
ในรูปของบ่ายที่ดีแทนที่จะเป็น traceback

### หลังจากนั้นบนดิสก์มีอะไร

ไฟล์นั้น ถูกเปลี่ยนไปหนึ่งตัวอักษรกับวงเล็บหนึ่งคู่

```python
def average(numbers):
    if not numbers:
        return 0
    return total(numbers) / len(numbers)
```

docstring ยังอยู่ครบและ `total` กับ `largest` ไม่ถูกแตะ ซึ่งคือ `edit_file` จากบทที่ 07 ทำงาน
ที่มันมีอยู่เพื่อทำ ถ้า agent ใช้ `write_file` มันจะต้องผลิตทั้ง module ขึ้นมาใหม่จากความจำ และ
model ที่ผลิตโค้ดที่มันไม่จำเป็นต้องเปลี่ยนซ้ำ คือ model ที่จะทำหล่นไปหนึ่งบรรทัดอย่างเงียบ ๆ

และ session ซึ่งคือสิ่งที่ภาค 3 เพิ่มเข้ามา

```bash
wc -l ~/.agentpath/sessions/salestool-1.jsonl
cut -c1-72 ~/.agentpath/sessions/salestool-1.jsonl | head -6
```

```text
11 salestool-1.jsonl
{"role": "system", "content": "You are a careful software assistant work
{"role": "user", "content": "The average is wrong in this project. Find
{"role": "assistant", "content": "", "tool_calls": [{"id": "call_mock_1"
{"role": "tool", "tool_call_id": "call_mock_1", "content": "stats.py:8:
{"role": "assistant", "content": "", "tool_calls": [{"id": "call_mock_2"
{"role": "tool", "tool_call_id": "call_mock_2", "content": "\"\"\"Small
```

หนึ่ง JSON object ต่อหนึ่งบรรทัด ตามลำดับที่สิ่งต่าง ๆ เกิดขึ้น เขียนตอนที่มันเกิดขึ้นแทนที่จะเขียน
ตอนจบ ไม่มีภาษาสำหรับ query และไม่มีตัวแสดงผล ทุกคำถามที่คุณจะมีเกี่ยวกับการรันครั้งนั้นถูกตอบ
ด้วยการเปิดไฟล์ข้อความหนึ่งไฟล์

### การทำงานต่อจากมัน

ทีนี้มาถึงสิ่งที่เป็นไปไม่ได้ตอนจบภาค 2 ปิด terminal กลับมาพรุ่งนี้ แล้วถามคำถามต่อเนื่อง

```bash
python main.py "What did you change, and why?" \
  --workspace ~/code/salestool --resume salestool-1
```

```text
Working in /home/you/code/salestool
Resumed salestool-1 with 11 messages

...the model's answer...

session salestool-1 saved to /home/you/.agentpath/sessions/salestool-1.jsonl
usage 1 calls, 384 prompt tokens, 6 completion tokens
```

`Resumed salestool-1 with 11 messages` คือ `Session.load` ยื่น dictionary สิบเอ็ดอันให้
`run` ซึ่งคัดลอกมันลงใน `messages` แล้วข้ามการเติม system prompt อันที่สอง model ตอบ
คำถามได้เพราะการแก้ไขที่มันทำเมื่อวานนั่งอยู่ใน context ของมันในฐานะการเรียก tool และผลลัพธ์
ของ tool เหมือนกับตอนที่มันทำเป๊ะ ๆ

ตรวจไฟล์อีกครั้งแล้วมันยาวขึ้น

```bash
wc -l ~/.agentpath/sessions/salestool-1.jsonl
```

```text
13 salestool-1.jsonl
```

สิบเอ็ดจากเมื่อวาน อีกสองจากวันนี้ หนึ่ง session หนึ่งไฟล์ สองครั้งที่นั่งลงทำ

## 6. การตรวจสอบหมุดหมายพิสูจน์อะไร

`check.py` ทุกอันที่ผ่านมาทดสอบชิ้นส่วนเดียว ของบทที่ 12 สร้าง object `Permissions` แล้วถาม
คำถามมัน ของบทที่ 13 เขียน session แล้วอ่านกลับมา ของบทที่ 14 ยื่นลิสต์ให้ `fit_to_budget`
แล้วดูลิสต์ที่ออกมา ของบทที่ 17 เรียก `with_retries` กับ mock server ที่คืน 429 แต่ละอันตั้งใจ
กันทุกอย่างที่เหลือออกไปนอกห้อง ซึ่งเป็นสิ่งที่ทำให้ unit test อ่านออกได้ตอนมันล้มเหลว

อันนี้ต่างออกไป และความต่างนั้นคือประเด็นทั้งหมดของหมุดหมาย subsystem ที่แต่ละตัวทำงานได้
ตามลำพัง ยังล้มเหลวร่วมกันได้ session อาจถูกต้องแต่ loop เรียกมันผิดจังหวะ permission อาจ
ตัดสินถูกแต่ loop เพิกเฉยต่อคำตอบ การตัดอาจถูกต้องแต่ไปแก้ลิสต์ที่ session กำลังเขียนจากมัน

ไม่มีอันไหนในนั้นที่หาเจอได้ด้วยการทดสอบชิ้นส่วนแยกกัน เพราะไม่มีอันไหนเป็นข้อบกพร่องของชิ้นส่วน
มันเป็นข้อบกพร่องของการต่อสายไฟ และสิ่งเดียวที่ทดสอบการต่อสายไฟได้คือการรันทุกอย่างพร้อมกัน

ดังนั้น `check.py` ตรงนี้จึงทำงานจริงหนึ่งงาน ในไดเรกทอรีจริง กับ bug จริง object permission
จริง session จริงบนดิสก์ budget จริง การนับ usage จริง provider จริงผ่าน socket จริง แล้วมัน
ก็ตรวจ filesystem หลังจากนั้น สิ่งเดียวที่ไม่จริงคือ model

### ชุดข้อมูลตั้งต้น

```python
home = Path(tempfile.mkdtemp(prefix="agentpath-lesson18-home-"))
workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson18-ws-"))
os.environ["AGENTPATH_HOME"] = str(home)
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)
```

ไดเรกทอรีชั่วคราวสองอันแทนที่จะเป็นอันเดียว และมันแยกกันโดยเจตนา
`AGENTPATH_WORKSPACE` คือที่ที่ agent แตะไฟล์ได้
`AGENTPATH_HOME` คือที่ที่ session ถูกเขียน และ `session.py` อ่านมันใน
`default_directory` ชี้การตรวจสอบไปที่ home จริงของคุณแล้วมันจะทิ้งขยะไว้ใน
`~/.agentpath/sessions` เป็นไฟล์ชื่อ `milestone.jsonl` ที่โตขึ้นทุกครั้งที่คุณรัน และที่แย่กว่านั้น
ข้ออ้างที่สามข้างล่างจะเริ่มล้มเหลว เพราะ session มีข้อความอยู่ในนั้นแล้วก่อนที่การรันจะเริ่ม

```python
BUGGY = 'def add(a, b):\n    """Return the sum."""\n    return a - b\n'
```

`a - b` ตรงที่ตั้งใจให้เป็น `a + b` bug ที่คนมองเห็นทันทีและ model ก็มองเห็นทันที ดังนั้นการ
ตรวจสอบนี้จึงไม่ใช่การทดสอบว่า model ฉลาดแค่ไหนอย่างลับ ๆ

### การบังคับทิศทาง model โดยไม่มี model

```python
TASK = (
    "Fix the bug in calc.py. "
    '[[tool:grep_files:{"pattern": "def add", "glob": "*.py"}]]'
    '[[tool:read_file:{"path": "calc.py"}]]'
    '[[tool:edit_file:{"path": "calc.py", "old": "return a - b", "new": "return a + b"}]]'
)
```

คำสั่ง `[[tool:name:{...}]]` ถูกอ่านโดย mock server ใน
`src/agentpath/testing/mock_server.py` ซึ่งคุณเจอมันในบทที่ 06 มันนับว่ามีผลลัพธ์ของ tool
กลับมากี่อันแล้วตอบด้วยคำสั่งถัดไป ดังนั้นสามคำสั่งจึงผลิตการเรียก tool สามครั้งตามลำดับ แล้วตาม
ด้วยคำตอบที่เป็นข้อความในตอนท้าย

เรื่องนี้สมควรได้รับการแก้ต่าง เพราะมันดูเหมือนการเขียนสคริปต์คำตอบไว้ล่วงหน้า

สิ่งที่ถูกเขียนสคริปต์ไว้มีแค่ว่า tool ไหนถูกเรียกด้วย argument อะไร นั่นคือส่วนที่ model จริงเป็น
คนตัดสิน และเป็นส่วนที่ไม่มีความแน่นอน จึงเอามาตั้งเป็นข้อยืนยันไม่ได้ ทุกอย่างที่อยู่ปลายน้ำเป็นของ
จริง provider ทำการ serialise schema และ stream การตอบกลับ HTTP จริงผ่าน socket จริง
loop สะสมชิ้นส่วน argument ที่ถูก stream มา สร้าง assistant message ปรึกษา `Permissions`
และส่งงานผ่าน `tools.run` `edit_file` เปิดไฟล์แล้วเขียนลงดิสก์ `Session` เขียนทุกข้อความลง
ไฟล์จริงขณะที่มันดำเนินไป ถ้าอะไรในนั้นพัง การตรวจสอบก็ล้มเหลว ด้วยเหตุผลเดียวกับที่มันจะล้ม
เหลวเมื่อเจอ model ที่ต้องจ่ายเงิน

สิ่งที่คุณยอมเสียคือความมั่นใจว่า model จะเลือกการเรียกสามครั้งนั้น สิ่งที่คุณได้มาคือการตรวจสอบที่
รันได้ทุกครั้งที่ push ไม่มีค่าใช้จ่าย ไม่ต้องใช้ API key เสร็จในเวลาต่ำกว่าหนึ่งวินาทีมาก และให้
คำตอบเดิมทุกครั้ง

### ข้ออ้างทั้งห้า

รันมันกับ mock server แบบเดียวกับที่ CI ทำ

```bash
python ci/run_lessons.py
```

```text
[calling grep_files with {'pattern': 'def add', 'glob': '*.py'}]
[grep_files returned calc.py:1: def add(a, b):]

[calling read_file with {'path': 'calc.py'}]
[read_file returned def add(a, b):
    """Return the sum."""
    return a - b
]

[calling edit_file with {'path': 'calc.py', 'old': 'return a - b', 'new': 'return a + b'}]
[edit_file returned Edited calc.py]
The tool returned Edited calc.py.
OK the agent fixed a real bug in a real file
OK the session was written as it happened, 9 messages
OK the run counted what it cost, 4 calls, 875 prompt tokens, 40 completion tokens
Hello from the mock server.
OK the session was resumed and carried on from, now 11 messages

[edit_file was refused]
The tool returned The user refused this call. Do not try it again, do something else..
OK a refused tool call really did not touch the file
```

ห้าบรรทัด `OK` ดูทีละอัน เพราะแต่ละอันครอบคลุม subsystem ที่ต่างกัน และอันสุดท้ายครอบคลุม
สิ่งที่อันอื่นทำไม่ได้เลย

**หนึ่ง agent แก้ bug จริงในไฟล์จริง**

```python
    if "return a + b" not in (workspace / "calc.py").read_text(encoding="utf-8"):
        fail("the bug was not fixed on disk")
```

ไฟล์ถูกเปิดใหม่และอ่านหลังจาก `run` คืนค่า ไม่มีการปรึกษาคำบอกเล่าของ agent เกี่ยวกับเหตุการณ์
เลย นี่คือข้ออ้างที่ครอบคลุมท่อทั้งเส้น ตั้งแต่การ serialise schema ผ่านการประกอบ argument ที่
ถูก stream มา ไปจนถึงการเขียน และทุกขั้นตอนของมันเคยพังมาแล้วระหว่างการพัฒนา

**สอง session ถูกเขียนตอนที่มันเกิดขึ้น**

```python
    saved = session.load()
    if [m["role"] for m in saved[:3]] != ["system", "user", "assistant"]:
        fail(f"the session was not written as the run happened. Got {...}")
```

สังเกตว่ามันยืนยันอะไร ไม่ใช่ว่าไฟล์มีอยู่ และไม่ใช่ว่ามันมีเก้าบรรทัด แต่คือ role สามอันแรกเป็น
`system`, `user`, `assistant` ตามลำดับนั้น

ข้อยืนยันเฉพาะเจาะจงอันนั้นคือสิ่งที่จับความล้มเหลวแบบแนบเนียนได้ harness ที่พัก message ไว้
แล้วเขียนตอนจบจะผ่านการทดสอบที่นับแค่จำนวนบรรทัด แล้วก็จะเสียทุกอย่างตอนมันพัง มันยังมีแนวโน้ม
สูงมากที่จะเขียนมันในลำดับที่ต่างออกไป เพราะวิธีธรรมชาติในการเขียนตอนจบคือการเดินไปตาม
โครงสร้างอะไรก็ตามที่คุณสะสมไว้ การตรวจลำดับพิสูจน์ว่า callback ทำงานข้างใน loop ทีละข้อความ
ตามลำดับ

เก้าข้อความ ซึ่งคือ system หนึ่ง user หนึ่ง แล้วสามคู่ของ assistant message ที่มีการเรียก tool
ตามด้วยผลลัพธ์ของ tool บวกกับคำตอบสุดท้าย

**สาม การรันนับว่ามันมีต้นทุนเท่าไร**

```python
    if usage.calls < 2 or usage.prompt_tokens <= 0:
        fail(f"usage was not counted. Got {usage.summary()}")
```

สองเงื่อนไข และอันที่สองคืออันที่น่าสนใจ `usage.calls` เพียงอย่างเดียวจะผ่านถ้า `Usage.add`
ถูกเรียกทุกเทิร์นด้วย dictionary ว่าง ซึ่งคือสิ่งที่เกิดขึ้นพอดีเมื่อ provider หยุดรายงาน usage หรือ
เมื่อ `stream_options` ที่ร้องขอมันถูกทำหล่นจาก payload ความล้มเหลวนั้นเงียบ เพราะตัวนับที่นับ
ศูนย์ดูเหมือนกันเป๊ะกับการรันที่ราคาถูก การกำหนดว่า `prompt_tokens > 0` พิสูจน์ว่าตัวเลขกลับมา
จากสายส่งจริง

สี่การเรียก เพราะการรันทำการเรียก tool สามครั้งแล้วตอบ

**สี่ session ถูก resume และทำงานต่อจากมัน**

```python
    carried_on = Session("milestone").load()
    _, messages = run(
        provider(),
        "Say thank you.",
        permissions=Permissions(auto_approve=True),
        history=carried_on,
        on_message=session.append,
        usage=usage,
    )
    if len(messages) <= len(carried_on):
        fail("resuming did not carry the old conversation forward")
```

ดูบรรทัดแรก มันสร้าง object `Session` **อันใหม่** ด้วยชื่อเดียวกันแล้วโหลดจากดิสก์ แทนที่จะ
ใช้ข้อความที่ `run` ครั้งก่อนคืนมาในหน่วยความจำซ้ำ นั่นคือความต่างระหว่างการทดสอบ resume กับ
การทดสอบตัวแปร สิ่งเดียวที่เชื่อมสองการรันเข้าด้วยกันคือไฟล์ ซึ่งเป็นข้ออ้างที่กำลังถูกทำอยู่พอดี

เก้าข้อความกลายเป็นสิบเอ็ด user หนึ่งกับ assistant หนึ่ง

สังเกตด้วยว่าอะไรที่จงใจไม่ถูกส่ง ไม่มี `system` ประวัติที่โหลดมาถือ system prompt ไว้แล้วในฐานะ
ข้อความแรกของมัน และ `if system and not messages` ใน loop คือสิ่งที่ทำให้นั่นปลอดภัย
หัวข้อที่ 4 ครอบคลุมเหตุผลไว้แล้ว

**ห้า การเรียก tool ที่ถูกปฏิเสธไม่ได้แตะไฟล์จริง ๆ**

นี่คืออันที่ต้องอ่านให้ละเอียด และมันอยู่ท้ายสุดเพราะมันสำคัญที่สุด

```python
    denied = Session("denied")
    (workspace / "other.py").write_text("x = 1\n", encoding="utf-8")
    run(
        provider(),
        'Change it. [[tool:edit_file:{"path": "other.py", "old": "x = 1", "new": "x = 2"}]]',
        permissions=Permissions(ask=lambda name, arguments: DENY),
        on_message=denied.append,
    )
    if (workspace / "other.py").read_text(encoding="utf-8") != "x = 1\n":
        fail("a refused edit changed the file anyway, which is the bug this check exists for")
```

ไฟล์ถูกเขียนด้วยเนื้อหาที่รู้แน่ `Permissions` ถูกสร้างขึ้นโดยที่ฟังก์ชัน `ask` ของมันปฏิเสธทุกอย่าง
ซึ่งเป็นไปได้ก็เพราะ `check` คืนค่า boolean แทนที่จะรันการเรียกนั้นเอง model ขอแก้ไฟล์ จากนั้น
ไฟล์ก็ถูกอ่านกลับมาแล้วเทียบกับไบต์เดิม

ทีนี้มาดูเวอร์ชันอ่อนแอของการทดสอบนี้ ซึ่งเขียนง่ายและดูโอเค

```python
if "refused" not in result:
    fail("the call was not refused")
```

นั่นยืนยันว่ามีสตริงหนึ่งปรากฏในข้อความ การที่สตริงหนึ่งปรากฏในข้อความคือสิ่งที่ทำให้เกิดขึ้นได้
ถูกที่สุดในโปรแกรมทั้งหมดนี้ มันไม่ต้องการประตูใดทำงาน มันไม่ต้องการให้ไฟล์ไหนไม่ถูกแก้ มันไม่
ต้องการอะไรเลยนอกจากคำสั่ง `print` ในสาขาที่ถูก และสาขาที่พิมพ์การปฏิเสธแล้วไหลต่อไปรัน tool
อยู่ดี ก็จะผ่านมันไปได้

นั่นไม่ใช่รูปทรงของ bug ที่สมมติขึ้น มันเป็นหนึ่งในข้อบกพร่องจริงที่พบบ่อยที่สุดในโค้ด permission
และมันปรากฏในลักษณะเฉพาะ มีคนไป refactor สายของ `if` และ `elif` ใน loop หรือเพิ่มสาขาใหม่
เหนือการตรวจ permission แล้วสาขาการปฏิเสธก็เลิกเป็นสิ่งที่แยกขาดจากสาขาการรัน หน้าจอยังบอก
ว่าปฏิเสธ ไฟล์ก็เปลี่ยนอยู่ดี ทุกบรรทัดใน log ดูถูกต้อง

ดังนั้นข้ออ้างนี้จึงยืนยันบนไบต์ `x = 1\n` เป๊ะ ๆ เทียบกับสิ่งที่อยู่บนดิสก์หลังการรันจริงเต็มรูปแบบ
ที่มี loop จริงและ `tools.run` จริงอยู่ในโปรแกรม เพื่อให้สิ่งนั้นผ่าน การปฏิเสธจะต้องเป็นเหตุผลที่
การเรียกไม่เกิดขึ้น ไม่ใช่ข้อความที่ถูกพิมพ์ควบคู่ไปกับการที่มันเกิดขึ้น

นิสัยนี้ใช้ได้กว้างไกลกว่าการตรวจสอบนี้มาก เมื่อคุณทดสอบอะไรก็ตามที่มี language model อยู่ข้างใน
จงหา side effect แล้วยืนยันบนสิ่งนั้น ข้อยืนยันบนถ้อยความคือข้อยืนยันบนส่วนเดียวของระบบที่ผิดได้
อย่างน่าเชื่อถือ และการปฏิเสธที่ถูกแค่พิมพ์ออกมาคือการปฏิเสธที่ไม่ได้เกิดขึ้น

### รันมันด้วยตัวเอง

จากข้างในโฟลเดอร์ของบท โดยตั้งค่า endpoint ไว้แล้ว

```bash
cd lessons/18-the-harness
python check.py
```

หรือทุกบทพร้อมกันกับ mock server ที่มีมาให้ ซึ่งเป็นสิ่งที่ CI รัน

```bash
python ci/run_lessons.py
```

ถ้า `OK` อันแรกล้มเหลวและไฟล์ยังบอกว่า `return a - b` แปลว่าการแก้ไขไปไม่ถึงดิสก์ และที่ที่
ต้องไปดูคือ `AGENTPATH_WORKSPACE` ถูกตั้งค่าก่อนการ import หรือไม่ ถ้าอันที่สองล้มเหลว
แปลว่า callback ของ session ไม่ได้ทำงานข้างใน loop ถ้าอันที่สามรายงาน prompt token เป็น
ศูนย์ แปลว่า usage ไม่ได้กลับมาจาก provider ถ้าอันที่สี่ล้มเหลว แปลว่า `history` ไม่ได้ถูกคัดลอก
ลงใน `messages` และถ้าอันที่ห้าล้มเหลว จงหยุดแล้วอ่านโครงสร้างของสาขาใน `agent.py` เพราะ
มีบางอย่างกำลังรันการเรียกที่ผู้ใช้ปฏิเสธไปแล้ว

## 7. ขีดจำกัดที่ซื่อสัตย์ และภาค 4 ทำอะไรกับแต่ละข้อ

คุณมี harness แล้ว มีสามอย่างที่มันทำไม่ได้ แต่ละอย่างคือหนึ่งบทของภาค 4 สิ่งเหล่านี้ไม่ใช่ความ
หลงลืม มันคือหลักสูตร

### มันใช้ได้แค่ tool ที่คุณเขียนเอง

ลองนับดู `read_file`, `write_file`, `edit_file`, `list_files`, `run_shell`,
`glob_files`, `grep_files`, `search_notes` แปดตัว ทั้งหมดอยู่ใน `tools.py` และทั้งหมด
คุณเขียนเอง

นั่นฟังดูเยอะจนกระทั่งคุณอยากได้ตัวที่เก้า ลองขอให้ agent ตัวนี้ดูแถวหนึ่งในฐานข้อมูลของคุณ หรือ
เปิดหน้าเว็บใน browser หรืออ่าน ticket หรือโพสต์ลงแชท แล้วคำตอบคือคุณต้องไปเขียน tool เอง
จากนั้นคุณก็เขียนอีกตัว แล้วอีกตัว และแต่ละตัวต้องมี schema รายการ dispatch การจัดการ error
และ `check.py` ในระหว่างนั้น คนอื่นก็เขียน tool ที่ดีเยี่ยมสำหรับฐานข้อมูลนั้นไว้แล้ว และไม่มีทาง
เลยที่จะใช้ของเขาได้ เพราะ tool ในโปรแกรมนี้คือฟังก์ชัน Python ใน module ที่ต้องถูก import
เข้ามาใน process นี้

รอยต่อที่ทำให้ภาค 2 ทำงานได้ คือรอยต่อเดียวกันที่ปิดตัวลงตรงนี้
`tools.run(name, arguments)` ค้นหาชื่อใน dictionary ของฟังก์ชัน Python ดังนั้นอะไรก็ตามที่
ไม่ใช่ฟังก์ชัน Python ใน dictionary นั้นก็ไม่มีอยู่จริงในสายตาของ agent โลกใบนี้เต็มไปด้วย
ความสามารถที่การออกแบบนี้เอื้อมไม่ถึง

**บทที่ 19 MCP client** protocol ที่ tool อาศัยอยู่ใน process แยกและถูกอธิบายผ่าน pipe
ดังนั้น tool จึงกลายเป็นสิ่งที่คุณเชื่อมต่อไป แทนที่จะเป็นสิ่งที่คุณเขียน คุณเขียน client เองแบบ
synchronous ใช้ stdio อย่างเดียว เพราะประเด็นคือการเข้าใจ protocol มากกว่าการ import SDK
ของคนอื่น และมันมาพร้อมต้นทุนที่ไม่ชัดเจนจนกว่าคุณจะมี server สี่ตัวเชื่อมต่ออยู่พร้อมกัน ซึ่งก็คือ
schema ของ tool ถูกส่งไปในทุก request เดียว เชื่อมต่อ server มากพอแล้วครึ่งหนึ่งของ context
ของคุณก็หายไปก่อนงานจะเริ่ม และ model ก็เลือก tool ผิดบ่อยขึ้นด้วย เพราะ tool สี่สิบตัวที่มีคำ
อธิบายทับซ้อนกันคือทางเลือกที่ยากกว่าแปดตัว

### มันทำทุกอย่างด้วยตัวเอง ในบทสนทนาเดียว

ทุกข้อความไปอยู่ในลิสต์เดียว system prompt งานของคุณ ทุกไฟล์ที่มันอ่าน ทุกผลลัพธ์ของ tool
ทุกทางตัน

บทที่ 14 ทำให้เรื่องนี้พอเอาตัวรอดได้ ไม่ใช่แก้ได้ ดูสิ่งที่ `fit_to_budget` ทำจริงเมื่อ budget
ถูกใช้จนเต็ม มันทิ้งบล็อกที่เก่าที่สุด ซึ่งก็คือบล็อกที่บรรจุงานตั้งต้นของคุณ ไฟล์แรกที่มันอ่าน และ
เหตุผลที่มันเลือกวิธีที่มันกำลังทำไปแล้วสามในสี่ส่วน

ดังนั้นในงานที่ใหญ่จริง รูปทรงของความล้มเหลวไม่ใช่การพัง มันแย่กว่านั้น agent ค่อย ๆ โง่ลงเรื่อย ๆ
ขณะที่การรันดำเนินไป ลืมส่วนที่เก่าที่สุดและรับน้ำหนักมากที่สุดของการให้เหตุผลของตัวมันเอง และไม่มี
error ที่ไหนเลย เพราะการตัดทำงานตามที่ออกแบบไว้เป๊ะ ๆ มันแค่โยนคำสั่งทิ้งไปอย่างเงียบ ๆ

การตัดแก้เรื่องนี้ไม่ได้ และ window ที่ใหญ่ขึ้นก็แก้ไม่ได้ เพราะทั้งสองอย่างเป็นคำตอบของคำถามที่ผิด
ปัญหาที่แท้จริงคือบทสนทนาเดียวถูกขอให้แบกงานที่ไม่พอดีกับบทสนทนาเดียว

**บทที่ 20 subagent** agent ที่เริ่ม agent อีกตัวได้ด้วย context สดของตัวเอง ยื่นงานแคบ ๆ ชิ้น
เดียวให้มัน แล้วรับคำตอบกลับมาแทนที่จะเป็นบทบันทึกทั้งเส้น บทสนทนาของพ่อแม่โตขึ้นด้วยผลลัพธ์
สั้น ๆ อันเดียว แทนที่จะโตด้วยการเรียก tool สี่สิบครั้ง บทนั้นยังมีรูปแบบความล้มเหลวที่แถมมาด้วย
ซึ่งก็คือพ่อแม่และลูกตอนนี้เห็นโลกคนละเวอร์ชัน ลูกแก้ไฟล์ไปแล้ว พ่อแม่ยังให้เหตุผลจากสิ่งที่มันอ่าน
ไว้ก่อนหน้า และการแยก context ของลูกออกมา ซึ่งคือสิ่งที่ทำให้มันคมชัด ก็คือสิ่งที่ทำให้เรื่องนี้แย่ลง
พอดี

**บทที่ 21 รูปแบบการทำงานแบบ multi agent** orchestrator กับ worker ที่ทำงานขนานกันบน
thread และ queue ซึ่งเป็นที่ที่คุณจะได้รู้ว่าส่วนไหนของ harness ของคุณแอบสมมติว่ามี agent เดียว
ไฟล์ session เป็นตัวอย่างหนึ่ง `session.py` บอกใน docstring ของตัวเองว่ามันรองรับผู้เขียนคน
เดียว และ worker สองตัวที่เขียนต่อท้ายไฟล์เดียวกันจะสลับบรรทัดกันแล้วทำให้มันเสียหาย

### คุณบอกไม่ได้ว่าการเปลี่ยนแปลงทำให้มันดีขึ้นหรือแย่ลง

นี่คือขีดจำกัดที่ควรรบกวนใจคุณมากที่สุด และมันมองไม่เห็นเพราะไม่มีอะไรเกี่ยวกับมันที่ผลิต error

เปิด `prompt.py` แล้วเปลี่ยน `BEHAVIOUR` เพิ่มประโยคที่บอก agent ให้รัน test เสมอก่อนจะ
บอกว่าเสร็จแล้ว ทีนี้ตอบคำถามหนึ่งข้อ นั่นช่วยหรือเปล่า

คุณตอบไม่ได้ คุณรันมันกับงานหนึ่งแล้วนั่งดูได้ แต่ model ไม่มีความแน่นอน ดังนั้นการรันที่คุณเพิ่ง
ดูไปจะดำเนินไปต่างออกไปในครั้งที่สองโดยไม่ต้องเปลี่ยนอะไรเลย คุณรันสองครั้งแล้วชอบครั้งที่สอง
มากกว่าได้ ซึ่งคือการวัดสัญญาณรบกวน สิ่งที่คุณมีจริง ๆ คือความรู้สึก และเป็นความรู้สึกที่ก่อตัวจาก
การรันสองครั้งบนงานหนึ่งงาน บน model หนึ่งตัว ด้วยการเรียบเรียงคำแบบเดียว

นั่นไม่ใช่ช่องว่างเล็ก ๆ มันแปลว่าทุกการปรับปรุงที่คุณทำกับข้อความที่สำคัญที่สุดในโปรแกรมนั้น
พิสูจน์ผิดไม่ได้ มันแปลว่าคุณบอกไม่ได้ว่า model ที่ถูกกว่าจะทำงานนี้ได้ดีพอกันหรือไม่ ดังนั้นคุณก็
ต้องจ่ายค่าตัวแพงไปทุกที่ด้วยความเชื่อโชคลาง หรือไม่ก็เปลี่ยนไปใช้ตัวถูกแล้วมารู้เอาจากผู้ใช้ และมัน
แปลว่าเมื่อ agent เริ่มมีพฤติกรรมแย่ลงหลังจากการเปลี่ยนแปลงเล็ก ๆ สามสัปดาห์ คุณก็ไม่มีทาง
หาว่าการเปลี่ยนแปลงไหนเป็นตัวการ

**บทที่ 22 eval และการเลือก model** ตัวรันงานที่รันชุดงานตายตัวแล้วตรวจผลลัพธ์ และ LLM ใน
ฐานะผู้ตัดสินสำหรับผลลัพธ์ที่ตรวจด้วยเครื่องไม่ได้ mock server ทำให้กลไกทั้งหมดนี้ทดสอบได้ฟรี
และเหตุผลที่การเลือก model อยู่ในบทนั้นแทนที่จะเป็นบทของตัวเอง ก็เพราะคำถามสองข้อนั้นคือ
คำถามเดียวกัน การบอกว่า model หนึ่งดีกว่าอีกตัวโดยไม่มีชุดทดสอบคือการเดา และเมื่อคุณมีชุด
ทดสอบแล้ว การเลือก model ก็กลายเป็นการทดลองที่คุณรัน แทนที่จะเป็นความเห็นที่คุณถือไว้ มันยัง
ครอบคลุมการแบ่งชั้นด้วย เพราะการสรุปย่อไฟล์หรือการจำแนกประเภทของ error ไม่ต้องใช้ model
ที่แพงที่สุดของคุณ

## 8. แบบฝึกหัด

สิ่งเหล่านี้คุ้มค่าแก่การทำ แต่ละข้อเล็กพอที่จะทำเสร็จในเย็นเดียว และแต่ละข้อทำให้คุณได้แตะรอยต่อ
จากทิศทางที่บทเรียนไม่ได้แตะ

### หนึ่ง โหมด permission แบบอ่านอย่างเดียว

เพิ่มโหมดที่อนุญาตทุกการอ่านและปฏิเสธทุกอย่างที่เหลือ โดยไม่มีการถามคำถามในทั้งสองทิศทาง

การใช้งานที่ชัดเจนคือการรัน agent บน repository ที่คุณไม่ไว้ใจ หรือให้มันอธิบาย codebase ให้
คุณฟังโดยรับประกันว่ามันเปลี่ยนอะไรไม่ได้ระหว่างที่ทำ มันยังเป็นโหมดที่คุณอยากใช้ในครั้งแรกสุดที่
คุณชี้ของสิ่งนี้ไปที่อะไรที่คุณห่วง

ร่างคร่าว ๆ ให้ `Permissions` มี `mode` แล้วทำให้ `check` เคารพมัน

```python
class Permissions:
    def __init__(self, ask=None, auto_approve=False, mode="normal"):
        self.mode = mode
        ...

    def check(self, name, arguments):
        if name in SAFE_TOOLS:
            return True
        if self.mode == "read_only":
            return False
        ...
```

จากนั้นก็ flag ใน `main.py` และมันควรเป็นตัวเลือกแบบปิด เพื่อให้การพิมพ์ผิดถูกจับโดย argparse
แทนที่จะได้โหมดที่ผิดอย่างเงียบ ๆ

```python
    parser.add_argument("--mode", choices=["normal", "read-only"], default="normal")
```

สี่เรื่องที่ต้องคิดขณะที่ทำ และมันคือแบบฝึกหัดจริง ๆ

**การตรวจสอบไปอยู่ตรงไหนในลำดับ** วาง `read_only` ไว้เหนือการตรวจ `SAFE_TOOLS` แล้วการ
อ่านจะเลิกทำงาน ดังนั้น agent จะทำอะไรไม่ได้เลย วางมันไว้ใต้ `auto_approve` แล้ว
`--yes --mode read-only` จะอนุญาตการเขียนอย่างเงียบ ๆ ซึ่งเป็นการผสมที่แย่ที่สุดที่เป็นไปได้
เพราะคนที่พิมพ์ทั้งสอง flag เชื่อว่าอันที่เข้มงวดกว่าเป็นฝ่ายชนะ จงตัดสินว่า flag ไหนชนะแล้วเขียน
คอมเมนต์บอกไว้

**model ถูกบอกอะไร** loop ส่งประโยคที่บอกว่าผู้ใช้ปฏิเสธกลับไปอยู่แล้ว ประโยคนั้นผิดในกรณีนี้
เพราะไม่มีผู้ใช้คนไหนปฏิเสธอะไร และ model จะพยายามลองรูปแบบต่าง ๆ ต่อไปโดยหวังคำตอบที่
ต่างออกไป การปฏิเสธที่บอกเหตุผลคือการปฏิเสธที่ model วางแผนรับมือได้ และมันน่าจะควรบอกว่า
session นี้เป็นแบบอ่านอย่างเดียว และการเขียนไม่มีให้ใช้เลย

**model ควรรู้ก่อนที่มันจะลองหรือไม่** อีกวิธีหนึ่งคือไม่ส่ง schema ของ tool ที่เขียนไปเลยในโหมด
อ่านอย่างเดียว เพื่อให้ model ไม่มีวันเห็นว่า `edit_file` มีอยู่ นั่นคือการตัดสินใจออกแบบจริงที่มี
การแลกได้แลกเสียจริง มันสะอาดกว่าและประหยัด token ซึ่งเป็นข้อโต้แย้งของบทที่ 15 มันยังแปลว่า
model บอกคุณไม่ได้ว่ามันจะเปลี่ยนอะไร ซึ่งบ่อยครั้งคือสิ่งที่คุณต้องการจากการรันแบบอ่านอย่างเดียว

**คุณจะพิสูจน์มันอย่างไร** เขียนการตรวจสอบก่อนเขียนโค้ด มันควรหน้าตาเหมือนข้ออ้างที่ห้าใน
หัวข้อที่ 6 เขียนไฟล์ รัน agent ด้วยงานที่พยายามเปลี่ยนมัน แล้วเทียบไบต์หลังจากนั้น อย่ายืนยันบน
ข้อความใด ๆ

### สอง ทำให้ session บันทึกว่าแต่ละเทิร์นใช้เวลาเท่าไร

ตอนนี้ session บอกคุณว่าเกิดอะไรขึ้น แต่ไม่บอกอะไรเลยเกี่ยวกับเวลา เพิ่มการจับเวลา เพื่อให้คุณ
เปิดไฟล์ session แล้วเห็นว่าการรันใช้เวลาเก้าสิบวินาที และแปดสิบวินาทีในนั้นเป็นการเรียก
`run_shell` ครั้งเดียว

เวอร์ชันตรงไปตรงมาคือหนึ่งบรรทัดใน `Session.append`

```python
    def append(self, message):
        message = dict(message, at=time.time())
        ...
```

ทำแบบนั้นก่อน แล้วค่อยสังเกตปัญหาสี่ข้อ ซึ่งคือแบบฝึกหัด

**มันเปลี่ยนข้อความ** ปัจจุบัน `append` เขียนสิ่งที่มันได้รับมา ตอนนี้มันเพิ่ม field เข้าไป ดังนั้น
ไฟล์จึงไม่ตรงกับสิ่งที่ถูกส่งไปหา provider อีกต่อไป โหลด session นั้นกลับมาด้วย `--resume`
แล้วคุณกำลังส่งข้อความที่มีคีย์ `at` ซึ่ง provider ไม่ได้ขอ provider บางเจ้าเพิกเฉยต่อ field ที่
ไม่รู้จัก และบางเจ้าปฏิเสธ request ดังนั้นนี่คือ bug ที่โผล่บน model หนึ่งแต่ไม่โผล่บนอีก model
หนึ่ง จงตัดสินว่า `load` จะตัดมันออก หรือ timestamp จะไปอาศัยอยู่ที่อื่นนอกข้อความ

**timestamp ไม่ใช่ระยะเวลา** สิ่งที่คุณอยากรู้คือขั้นตอนหนึ่งใช้เวลานานแค่ไหน และนั่นคือการลบกัน
ระหว่าง timestamp สองอัน สองอันไหนกันแน่ ช่องว่างระหว่าง assistant message กับผลลัพธ์ของ
tool ก่อนหน้ามันคือเวลาคิดกับเวลา network ช่องว่างระหว่างการเรียก tool กับผลลัพธ์ของมันคือ
เวลาของ tool นั่นคือตัวเลขต่างกันที่มีสาเหตุต่างกัน และการรวมมันเข้าด้วยกันไม่บอกอะไรคุณเลยว่า
ควรแก้อันไหน

**นาฬิกาไหน** ใช้ `time.time()` แล้วคุณจะได้ตัวเลขนาฬิกาผนังที่อ่านเป็นวันที่ได้ ซึ่งเคลื่อนคลาด
และกระโดดถอยหลังได้เมื่อนาฬิการะบบถูกปรับ บางครั้งผลิตระยะเวลาติดลบ ใช้ `time.monotonic()`
แล้วระยะเวลาของคุณจะถูกต้องเสมอ แต่ตัวเลขนั้นไร้ความหมายเมื่ออยู่ลำพัง คำตอบน่าจะเป็นทั้งสอง
อย่าง และการรู้ว่าทำไมคือประเด็น

**ขอบเขตอยู่ตรงไหน** ปัจจุบัน `Session` ไม่รู้อะไรเกี่ยวกับเทิร์นเลย มันรับข้อความ ถ้าคุณอยากได้
การจับเวลาต่อเทิร์น ก็ต้องเลือกว่า session จะเริ่มอนุมานขอบเขตของเทิร์นจาก role ซึ่งทำให้มันมี
ความเห็นและทำลายกฎจากหัวข้อที่ 2 ที่ว่าตัวบันทึกไม่ตัดสิน หรือไม่ก็ loop เป็นคนบอกมัน ซึ่งแปลว่า
ต้องมี parameter ใหม่และสัญญาที่กว้างขึ้น ทั้งสองอย่างมีเหตุผลรองรับได้ เลือกมาหนึ่งอย่างและ
บอกให้ได้ว่าทำไม

เมื่อมันทำงานได้ ให้รัน agent กับอะไรจริง ๆ แล้วดูไฟล์ ตัวเลขที่ทำให้คุณประหลาดใจคือสิ่งที่ควร
เอาไปปรับให้ดีขึ้น และมันแทบจะแน่นอนว่าไม่ใช่สิ่งที่คุณจะเดา

### สาม ทำให้ตัวช่วย retry บอกว่ามันกำลังทำอะไร

ปัจจุบัน `with_retries` รออย่างเงียบสนิท การรันที่เจอ 429 สามครั้งพร้อม exponential backoff
จะนั่งอยู่ตรงนั้นราวสิบสี่วินาทีกับหน้าจอว่างเปล่า และคนที่นั่งดูก็แยกไม่ออกระหว่างการ retry กับ
การค้าง ดังนั้นเขาก็กด Ctrl+C และตอนนี้คุณก็เสียการรันที่กำลังจะสำเร็จไปแล้ว

ให้ callback กับมัน ในแบบเดียวกันเป๊ะกับที่ส่วนอื่นของโปรแกรมนี้ให้ callback กับสิ่งต่าง ๆ

```python
def with_retries(call, attempts=4, sleep=time.sleep, on_retry=None):
    ...
            if on_retry:
                on_retry(attempt, attempts, wait, error)
            sleep(wait)
```

เหตุผลที่มันเป็น callback แทนที่จะเป็น `print` คือประเด็นทั้งหมดของแบบฝึกหัดนี้ และมันคือเหตุผล
เดียวกับที่ `on_message` เป็น callback module ที่พิมพ์มี terminal ฝังอยู่ในตัวมัน อันนี้กำลังจะ
ถูกเรียกจาก CI จาก test และในบทที่ 21 จาก worker thread สี่ตัวพร้อมกัน ซึ่ง module สี่ตัวที่
พิมพ์ลง stream เดียวกันทั้งหมดจะผลิตความมั่วที่สลับกันไปมา

จากนั้นก็ต่อสายไฟมันให้ถูกต้อง ซึ่งคือครึ่งหลัง

```python
from retry import with_retries

def stream(self, messages, tools=None, on_text=None):
    return with_retries(lambda: self._stream_once(messages, tools, on_text))
```

เปลี่ยนชื่อ method เดิมเป็น `_stream_once` แล้วคุณจะเจอความยุ่งยากที่บทที่ 17 เตือนไว้ทันที
stream ที่ถูก retry เริ่มใหม่จากต้น ดังนั้นข้อความใดก็ตามที่พิมพ์ไปแล้วผ่าน `on_text` จะพิมพ์อีก
ครั้ง และผู้ใช้ก็เห็นคำตอบครึ่งเดียวสองรอบ มีวิธีแก้ที่ซื่อสัตย์อยู่สองแบบ พักข้อมูลไว้ในผู้เรียกแล้ว
พิมพ์เมื่อ stream เสร็จเท่านั้น ซึ่งทำให้คุณเสียความรู้สึกแบบ streaming ที่บทที่ 05 สร้างไว้ หรือ
retry เฉพาะก่อนที่ไบต์แรกจะมาถึง ซึ่งรักษาความรู้สึกนั้นไว้แต่ยอมแพ้ต่อการกู้คืนจากความล้มเหลว
กลาง stream เลือกมาหนึ่งอย่าง แล้วจดไว้ว่าคุณยอมเสียอะไร

พิสูจน์มันกับ mock server ซึ่งสั่งให้ล้มเหลวตามต้องการได้ด้วย header `X-Mock-Fail` ที่การ
ตรวจสอบของบทที่ 17 ใช้ จงยืนยันว่า `on_retry` ทำงานตามจำนวนครั้งที่คุณคาดไว้ และว่าค่าหน่วง
ที่มันรายงานเพิ่มขึ้น ส่ง `sleep` ปลอมที่เพิ่มค่าลงลิสต์เข้าไป แบบเดียวกับที่บทที่ 17 ทำ เพื่อให้การ
ตรวจสอบของคุณเสร็จทันทีแทนที่จะรอจริงสิบสี่วินาที

### สี่ ถ้าคุณอยากได้ข้อที่ยากขึ้น

ปิดช่องโหว่ของ cancellation จากหัวข้อที่ 4 ทำให้ `run_shell` ปรึกษา cancellation token
เพื่อให้ Ctrl+C ระหว่างคำสั่งที่กินเวลาหกสิบวินาทีฆ่า subprocess จริง ๆ แทนที่จะรอมัน

อันนี้ยากกว่าที่เห็น และนั่นคือเหตุผลที่มันอยู่ตรงนี้ `subprocess.run` บล็อกจนกว่า process จะจบ
ดังนั้นจึงไม่มีที่ให้ตรวจธง คุณจะต้องใช้ `subprocess.Popen` ลูปที่ poll พร้อม timeout ขณะที่
ตรวจ token และ `terminate` ตามด้วย `kill` เมื่อคำขออย่างสุภาพถูกเพิกเฉย จากนั้นคุณต้องเอา
token เข้าไปใน `tools.py` โดยไม่ให้ทุก tool มี parameter ใหม่ ซึ่งเป็นคำถามเรื่องรอยต่อ
มากกว่าคำถามเรื่อง thread และมันคือหัวข้อจริงของแบบฝึกหัดนี้

## 9. นี่คือจุดจบของภาค 3

สามภาคเสร็จแล้ว ดูว่าแต่ละภาคมีไว้เพื่ออะไรจริง ๆ

**ภาค 1 บทที่ 00 ถึง 06 คือรากฐาน** มันเริ่มด้วย HTTP request หนึ่งครั้งไปหา model และจบด้วย
agent loop ที่ทำ streaming เรียก tool และคุยกับรูปแบบสายส่งสองแบบผ่าน interface เดียว
สิ่งสำคัญที่มันสอนคือ language model คือข้อความเข้าและข้อความออก ทุกอย่างที่เหลือคือธรรมเนียม
ที่ถูกสร้างทับบนนั้น และบทสนทนาถูกส่งซ้ำทั้งชุดในทุก request เดียว แทบทุกต้นทุนและขีดจำกัดใน
ส่วนที่เหลือของคอร์สสืบเนื่องมาจากข้อเท็จจริงสุดท้ายนั้น

**ภาค 2 บทที่ 07 ถึง 11 คือ tool จริง** ไฟล์ที่มีประตูเดียวสำหรับทุกเส้นทาง shell ที่มีคนยืนอยู่
ข้างหน้า glob และ grep พร้อมข้อโต้แย้งว่าทำไมนั่นคือคำตอบที่ถูกต้องสำหรับโค้ด แทนที่จะเป็นของ
ชั่วคราวรอของหรูกว่า system prompt ที่บอก model ทั้งว่าจะประพฤติตัวอย่างไรและมันอยู่ที่ไหน
มันจบด้วย agent ที่ถูกชี้ไปที่โฟลเดอร์ที่มันไม่เคยเห็นแล้วแก้ bug ในนั้นได้ สิ่งที่มันสอน มากกว่า
tool ตัวใดตัวหนึ่ง คือรอยต่อระหว่าง loop กับ tool คือสิ่งที่ทำให้คุณเพิ่ม tool ตัวที่แปดได้ง่ายพอ ๆ
กับตัวแรก

**ภาค 3 บทที่ 12 ถึง 18 คือ harness** permission ที่จำสิ่งที่คุณตัดสินใจได้ เพื่อให้ประตูยังทำงาน
อยู่ตอนคำถามที่สี่สิบ session ในรูป JSONL ธรรมดา ซึ่งกลายเป็นเครื่องมือ debug ที่ดีที่สุดใน
โปรเจกต์ การจัดการ context รวมถึงกับดักที่การตัดระหว่างการเรียก tool กับผลลัพธ์ของมันทำให้
request ถัดไปถูกปฏิเสธทันที การบริหาร token ที่เงินไปอยู่ตรงไหนจริง ๆ และทำไมอะไรก็ตามที่
เปลี่ยนแปลงจึงต้องไปอยู่ท้ายสุด retrieval และคำถามสี่ข้อที่คุณถามก่อนจะเอื้อมไปหยิบมัน error
retry ความเป็น idempotent และการ interrupt ที่หยุดงานแทนที่จะหยุดหน้าจอ และบทนี้ ที่ทุกอย่าง
รันพร้อมกันกับไดเรกทอรีจริงแล้วดิสก์ถูกตรวจหลังจากนั้น

ภาค 3 ไม่ได้ทำให้ agent ของคุณมีความสามารถมากขึ้น มันทำให้มันใช้งานจริงได้ สองอย่างนั้นต่างกัน
และนี่คือภาคที่ทำให้ความต่างนั้นมองเห็นได้

**ภาค 4 บทที่ 19 ถึง 23 ว่าด้วยขีดจำกัดของ agent ตัวเดียวกับ tool ที่คุณเขียนเอง** ทุกขีดจำกัด
ในหัวข้อที่ 7 มีรูปทรงเดียวกัน agent อยู่ตัวเดียว มันใช้ได้แค่สิ่งที่อยู่ใน `tools.py` มันทำงานใน
บทสนทนาเดียว และคุณไม่มีเครื่องมือวัดที่จะบอกได้ว่าการเปลี่ยนแปลงใด ๆ ที่คุณทำเป็นการปรับปรุง
หรือไม่

บทที่ 19 เชื่อมมันเข้ากับ tool ที่มันไม่ได้เขียนเอง ผ่าน MCP ด้วย client ที่คุณสร้างเอง บทที่ 20 ให้
มันเริ่ม agent ตัวอื่นได้ เพื่อให้งานใหญ่เลิกเป็นบทสนทนาเดียว บทที่ 21 รันหลายตัวพร้อมกันและทำ
ให้คุณได้รู้ว่าส่วนไหนของ harness ของคุณแอบสมมติว่าจะมีแค่ตัวเดียวตลอดไป บทที่ 22 ให้เครื่องมือ
วัดกับคุณ ซึ่งคือตัวรันงานกับผู้ตัดสิน และเปลี่ยนการเลือก model จากความเห็นให้เป็นการทดลอง
บทที่ 23 บรรจุทุกอย่างเพื่อให้คนอื่นติดตั้งมันได้

ก่อนไปต่อ ให้ทำสองอย่าง

รัน `python ci/run_lessons.py` จากรากของ repository แล้วดูทุกการตรวจสอบผ่าน รวมถึงอันนี้ด้วย

จากนั้นรัน `main.py` กับอะไรของคุณเองที่พังจริง ๆ ด้วยชื่อ session จริง แล้วปล่อยให้มันทำงานนาน
กว่าที่รู้สึกสบายใจ หลังจากนั้นเปิดไฟล์ session แล้วอ่านมันทั้งไฟล์ ไฟล์นั้นคือสิ่งที่มีประโยชน์ที่สุดที่
ภาค 3 ผลิตออกมา และจังหวะแรกในนั้นที่ agent ทำอะไรที่คุณไม่ได้คาดคิด คือการเตรียมตัวที่ดีที่สุด
เท่าที่เป็นไปได้สำหรับภาค 4

ไปต่อที่บทที่ 19
