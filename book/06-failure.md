# บทที่ 6 ระบบที่อยู่รอดคือระบบที่ยอมรับว่าจะพัง

agent เรียกใช้บริการที่อยู่อีกฝั่งของอินเทอร์เน็ต รัน subprocess (โปรเซสลูก
คือโปรแกรมที่โปรแกรมของเราสั่งให้เริ่มทำงาน) บนเครื่องที่คุณควบคุมไม่ได้
และทำงานนานพอที่คนจะเปลี่ยนใจกลางคัน ทั้งสามอย่างล้มเหลวได้ และจะล้มเหลวจริง

คำถามจึงไม่ใช่ว่าจะป้องกันความล้มเหลวยังไง แต่คือเมื่อมันเกิดขึ้น ระบบจะทำอะไร

จบบทนี้คุณจะมี `with_retries` ที่รู้ว่าสถานะไหนลองใหม่แล้วช่วย และสถานะไหน
ลองใหม่แล้วแค่ช้าลง ที่เคารพสิ่งที่ server บอกก่อนสูตรของตัวเองเสมอ และคุณจะมี
token ตัวเดียวที่ทำให้การกดหยุดหนึ่งครั้ง หยุดทั้ง stream ทั้ง subprocess
และทั้ง loop พร้อมกัน พร้อมกับเส้นสองเส้นที่บอกว่าตรงไหน retry ไม่ได้เลย
และไฟล์ session แบบ JSONL ที่รอดจากการถูกฆ่ากลางทาง

หัวข้อที่ 6 เป็นหัวข้อที่หนักที่สุด เพราะมันขอให้คุณถือสามเรื่องไว้ในหัว
พร้อมกัน คือ retry ที่อยากลองใหม่ timeout ที่อยากเลิกรอ และการกดหยุดที่มา
จากคน บทนี้จึงแยกทั้งสามออกจากกันก่อน หัวข้อที่ 1 ถึง 4 ว่าด้วย retry
อย่างเดียว หัวข้อที่ 5 ว่าด้วยเส้นที่ retry ข้ามไม่ได้ แล้วหัวข้อที่ 6
ค่อยเอาทั้งสามมาชนกัน

ถ้าอ่านรอบแรกแล้วหัวข้อที่ 3 เรื่อง jitter ดูเป็นรายละเอียดปลีกย่อยเกินไป
คุณข้ามมันได้ ไม่มีหัวข้อไหนหลังจากนั้นที่ต้องใช้มัน

## 1. retry เฉพาะสิ่งที่ retry แล้วช่วย

retry (การลองใหม่ คือการยิงคำขอเดิมซ้ำหลังจากล้มเหลว) ที่ใส่ผิดที่คือการทำ
ปัญหาให้ช้าลง ไม่ใช่ทำให้หายไป

```python
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
```

**เส้นแบ่งคืออะไร** ความล้มเหลวแบ่งเป็นสองพวก พวกที่บอกว่าคำขอของคุณผิด
กับพวกที่บอกว่าตอนนี้เรารับไม่ไหว พวกแรก retry ไม่ช่วย พวกหลัง retry ช่วย

400 หมายความว่าคำขอนั้นเองผิด การส่งคำขอที่ผิดอันเดิมไปใหม่ได้คำตอบผิดอันเดิม
กลับมา แค่ช้าลง 401 แปลว่ากุญแจไม่ถูกต้อง ซึ่งจะไม่ถูกต้องเหมือนเดิมในอีก
สองวินาที 404 แปลว่าไม่มีสิ่งนั้น

429 แปลว่าเร็วเกินไป ซึ่งจะไม่จริงอีกต่อไปเมื่อเวลาผ่านไป 500 กับ 503
แปลว่าฝั่งนั้นมีปัญหาชั่วคราว 408 แปลว่าหมดเวลา ทั้งหมดนี้คือสถานะที่รอแล้ว
ต่างออกไปได้

**ทำไม retry 400 ถึงแย่กว่าไม่ retry เลย** เพราะมันซ่อนบั๊ก คำขอที่ผิดรูป
จากการตัด context ผิดวิธีตามบทที่ 4 จะกลายเป็นความช้าที่อธิบายไม่ได้แทนที่
จะเป็น error ที่ชี้ตำแหน่งชัดเจน คุณจะเสียเวลาสี่เท่าเพื่อไปถึงข้อความ error
เดิม และจะสงสัยว่าเครือข่ายมีปัญหา ทั้งที่ปัญหาอยู่ในโค้ดของคุณเอง

**ทำไม transport error ถึงนับเป็นพวกที่ retry ได้** เพราะการเชื่อมต่อที่ขาด
ก่อนอะไรจะไปถึง แปลว่า server ยังไม่เคยเห็นคำขอนั้น การส่งใหม่จึงไม่ใช่การ
ทำซ้ำ มันคือความพยายามครั้งแรกที่สำเร็จ

## 2. เชื่อ server ก่อนสูตรของเรา

```python
def delay_for(attempt: int, response=None, base=1.0, cap=30.0) -> float:
    """How long to wait before the given attempt, counting from one.

    A Retry-After header wins outright. It is the server telling us when it
    will be ready, and guessing earlier than that just wastes a request and
    makes the overload worse.
    """
    if response is not None:
        header = response.headers.get("Retry-After")
        if header:
            try:
                return float(header)
            except ValueError:
                pass
    exponential = min(cap, base * (2 ** (attempt - 1)))
    return exponential * (0.5 + random.random() / 2)
```

**Retry-After คืออะไร** header ที่ผู้ให้บริการส่งกลับมาพร้อมกับ 429 หรือ 503
บอกว่าให้รอกี่วินาทีก่อนลองใหม่

**ทำไมมันต้องชนะสูตรของเรา** เพราะ server รู้สิ่งที่เราไม่รู้ มันรู้ว่างบ
ของเราจะรีเซ็ตเมื่อไหร่ มันรู้ว่าคิวยาวแค่ไหน สูตรคูณสองของเราเป็นการเดา
ที่ตั้งอยู่บนความไม่รู้ทั้งหมด ถ้าเราเดาสั้นกว่าที่มันบอก เราจะเสียคำขอไป
เปล่าๆ หนึ่งครั้ง และเพิ่มภาระให้ระบบที่กำลังมีปัญหาอยู่แล้ว สูตรของเรามีไว้
เป็นทางสำรองเมื่อ server ไม่ได้บอกอะไร ไม่ใช่ความเห็นที่ไปหักล้างสิ่งที่มันบอก

**ทำไมต้องมี try รอบ float** เพราะสเปกของ HTTP อนุญาตให้ `Retry-After`
เป็นวันที่แบบ HTTP ได้ด้วย ไม่ใช่แค่ตัวเลขวินาที ถ้าเราแปลงไม่ได้ เราตกลงไป
ใช้สูตรแทน ซึ่งถูกกว่าการปล่อยให้ทั้ง retry พังเพราะ header ที่อ่านไม่ออก

## 3. jitter ไม่ใช่ของประดับ

`(0.5 + random.random() / 2)` คือ jitter (การกระจายเวลาแบบสุ่ม คือการบวก
ความสุ่มเข้าไปในเวลารอ) มันทำให้เวลารอจริงอยู่ระหว่างครึ่งหนึ่งถึงเต็มของ
ค่าที่สูตรคำนวณได้

**ปัญหาที่มันป้องกัน อธิบายเป็นขั้นตอน** สมมติมี client หนึ่งพันตัวคุยกับ
บริการเดียวกัน บริการนั้นล่มไปหนึ่งวินาที client ทั้งพันตัวได้ 503 พร้อมกัน
ทุกตัวคำนวณเวลารอด้วยสูตรเดียวกันได้เลขเดียวกัน คือหนึ่งวินาที หนึ่งวินาที
ต่อมา client ทั้งพันตัวยิงพร้อมกัน บริการที่เพิ่งจะฟื้นโดนกระแทกด้วย
คำขอพันคำขอในเสี้ยววินาที แล้วล่มอีกรอบ ทุกตัวได้ 503 อีกครั้ง คำนวณได้
สองวินาทีเท่ากันหมด แล้ววนแบบนี้ไป

ผลคือความล้มเหลวหนึ่งวินาทีกลายเป็นการล่มที่ยืดยาว โดยที่ตัว client เองคือ
คนซ้ำเติม

jitter ทำให้ client พันตัวรอไม่เท่ากัน คำขอที่กลับมาจึงกระจายตัวแทนที่จะ
กระจุก บริการฟื้นได้จริง

**ทำไมไม่ใช้ค่าสุ่มเต็มช่วงตั้งแต่ศูนย์** ทำได้ และบางระบบทำ แต่การรอ
ใกล้ศูนย์แปลว่าบางตัวยิงกลับมาแทบจะทันที ซึ่งเสียประโยชน์ของ backoff
(การถอยห่าง คือการยืดเวลารอออกไปเรื่อยๆ เมื่อล้มเหลวซ้ำ) ไป การใช้ช่วง
ครึ่งหนึ่งถึงเต็ม รักษาการถอยห่างไว้ พร้อมกับกระจายเวลาพอที่จะไม่กระจุก

## 4. สิ่งที่ retry ไม่ได้ และเหตุผลว่าทำไม

ความคิดเห็นบนสุดของ `retry.py` ประกาศขอบเขตของทั้งไฟล์

```python
"""Retrying the things that are safe to retry.
...
Not everything may be retried. Asking the model again is safe because it
changes nothing outside the conversation. Running a tool that sent an email
is not, which is why nothing in this module wraps a tool call.
"""
```

**เส้นแบ่งคือ idempotency** (ความไม่เปลี่ยนแปลงเมื่อทำซ้ำ คือคุณสมบัติที่การ
ทำสองครั้งให้ผลเท่ากับทำครั้งเดียว)

การถาม model ซ้ำไม่เปลี่ยนอะไรนอกบทสนทนา ถ้าคำขอแรกไม่ถึง เราแค่ถามใหม่
ถ้ามันถึงแล้วแต่คำตอบหายกลางทาง คุณเสียเงินหนึ่งครั้ง ซึ่งเป็นราคาที่ยอมรับได้

การรัน tool ที่มี side effect (ผลข้างเคียง คือการเปลี่ยนแปลงที่เกิดขึ้น
นอกโปรแกรม) ไม่ใช่แบบนั้น retry คำสั่งที่ส่งอีเมลแปลว่าอีเมลสองฉบับ
retry คำสั่งที่ตัดเงินแปลว่าตัดสองครั้ง และเรื่องที่ทำให้มันร้าย คือกรณีที่
ต้องการ retry มากที่สุด คือกรณีที่คุณไม่รู้ว่าเกิดอะไรขึ้น เช่นการเชื่อมต่อ
ขาดหลังส่งคำขอไปแล้วแต่ก่อนได้คำตอบ ในกรณีนั้นการกระทำอาจสำเร็จไปแล้ว
และคุณไม่มีทางรู้

**ทางแก้ที่ถูกคือ idempotency key** (กุญแจกันทำซ้ำ คือรหัสที่ผู้เรียกสร้างขึ้น
เพื่อให้ผู้รับรู้ว่าคำขอสองครั้งคือคำขอเดียวกัน) ผู้เรียกสร้างรหัสไม่ซ้ำหนึ่งตัว
ต่อหนึ่งเจตนา แล้วส่งไปกับทุกความพยายาม ฝั่งรับเก็บรหัสที่เคยทำแล้วไว้
คำขอที่สองที่ถือรหัสเดิมได้ผลลัพธ์ของครั้งแรกกลับไป โดยไม่ทำงานซ้ำ

สังเกตว่านี่ไม่ใช่สิ่งที่ฝั่ง client ทำเองได้ตามลำพัง มันคือสัญญาระหว่างสองฝั่ง
ซึ่งเป็นเหตุผลว่าทำไมการ retry tool ที่ไม่ได้ออกแบบมารองรับ จึงไม่มีทางทำ
ให้ปลอดภัยด้วยโค้ดฝั่งคุณอย่างเดียว

**ผลเชิงออกแบบ** `with_retries` ห่อเฉพาะการเรียก provider เท่านั้น
และไม่มีที่ไหนใน codebase ที่ห่อ `tools.run` เลยครับ

## 5. stream ที่เริ่มไหลแล้ว retry ไม่ได้

มีอีกเส้นที่ละเอียดกว่านั้นและคนพลาดบ่อย

```python
def open_stream(client, url, payload, headers, attempts=4):
    """Open a streaming request, retrying the failures worth retrying.

    Only the opening is retried. Once the first bytes have arrived the caller
    has already seen part of an answer, and replaying the request would
    produce a second answer spliced onto the first. A partly consumed stream
    is not a thing you can retry, so the honest boundary is here.

    The error body is read before raising so the message is useful. Without
    that a failure reports only a status code, which sends people looking in
    the wrong place.
    """
```

**ทำไมเส้นอยู่ตรงนี้** เพราะเมื่อ byte แรกมาถึงแล้ว ผู้ใช้เห็นข้อความบางส่วน
บนหน้าจอไปแล้ว ถ้าเราเปิดคำขอใหม่ คำตอบที่สองจะถูกต่อท้ายคำตอบแรกที่ค้างอยู่
ได้ข้อความที่ไม่มีใครเคยเขียน การยอมรับตรงๆ ว่า stream ที่เริ่มบริโภคแล้ว
retry ไม่ได้ ดีกว่าการเขียนโค้ดที่ดูเหมือนกู้คืนได้ แต่ให้ผลลัพธ์ที่ผิด

**ทำไมต้องอ่าน body ของ error ก่อนโยน** เพราะ error ที่รายงานแค่ตัวเลขสถานะ
ส่งคนไปหาผิดที่ ข้อความที่ผู้ให้บริการเขียนมามักบอกเลยว่าอะไรผิด เช่น
tool result ที่ไม่มีคู่ ซึ่งคือกับดักของบทที่ 4 การทิ้งข้อความนั้นไปทำให้
บั๊กที่แก้ได้ในห้านาทีกลายเป็นการค้นหาทั้งบ่าย

## 6. การขัดจังหวะต้องหยุดของจริงทุกชั้น

นี่คือหัวข้อที่ harness ที่คนใช้กันอยู่จริงเคยพลาด และมันพลาดในแบบเดียวกัน
ทุกครั้ง คือหน้าจอบอกว่าหยุดแล้ว แต่ tool ยังทำงานต่อจนจบ

```python
"""One object that says stop, shared by everything that can be stopped.

An interrupt that only updates the screen is the bug this exists to prevent.
Harnesses people use every day have shipped versions where pressing the
interrupt key printed a cancellation message while the tool it was supposed
to stop kept running to completion.

The same token is checked by the agent loop between turns and by the shell
tool before it starts a process, so one press stops the actual work rather
than only the display.
"""
```

**ทำไมต้องเป็น object ตัวเดียวที่ทุกคนถือร่วมกัน** เพราะการหยุดต้องเกิดขึ้น
หลายที่พร้อมกัน ต้องปิด stream ที่ค้างอยู่ ต้องฆ่า subprocess ที่ spawn ไว้
ต้องปลดการรอคำตอบ permission และต้องหยุด loop ไม่ให้เริ่มรอบใหม่ ถ้าแต่ละที่
มีสัญญาณของตัวเอง จะมีที่ใดที่หนึ่งที่ไม่ได้รับข่าว และนั่นคือที่ที่บั๊กอยู่

`run_shell` ตรวจ token ก่อนเริ่ม process ด้วยเหตุผลที่ระบุไว้ตรงๆ

```python
        # Checked here rather than only in the loop because a command started
        # after the person pressed the interrupt key is exactly the failure
        # a cancellation token exists to prevent.
        if cancellation is not None and cancellation.cancelled:
            return "Cancelled before the command started."
```

**ทำไมตรวจใน loop อย่างเดียวไม่พอ** เพราะ loop ตรวจระหว่างรอบ ถ้าคนกดหยุด
ตอนที่ loop กำลังไล่รัน tool ตัวที่สองจากสามตัว การตรวจครั้งถัดไปของ loop
จะเกิดขึ้นหลังจากทั้งสามตัวรันจบแล้ว การตรวจที่ประตูของ tool เองคือสิ่งที่
ทำให้ตัวที่สามไม่ได้เริ่ม

**ทำไม reset ต้องล้างค่าในตัวเดิม แทนที่จะสร้าง object ใหม่**

```python
    def reset(self) -> None:
        """Clear the flag without replacing the object.

        Tools hold a reference to this token. Handing them a new object
        would leave them watching one that nothing ever cancels, so the
        interrupt would appear to work and then quietly stop working.
        """
```

นี่คือบั๊กที่โหดที่สุดในหมวดนี้ เพราะการกดหยุดครั้งแรกจะทำงาน แล้วครั้งต่อๆ
ไปจะไม่ทำงาน โดยไม่มี error ให้เห็นเลย คนจะสรุปว่าตัวเองกดไม่ทัน

### การฆ่า process ต้องฆ่าทั้งต้น

```python
        except subprocess.TimeoutExpired:
            # shell=True means the thing we started is a shell, and the slow
            # command is its child. Killing only the shell leaves the child
            # running and still holding the pipes, so a call that was meant
            # to give up after the timeout waits for the whole run anyway.
            # The tree has to go, not just the root of it.
            _kill_tree(process)
```

**บทเรียนทั่วไปที่ได้จากตรงนี้** การหยุดต้องหยุดสิ่งที่ทำงานอยู่จริง ไม่ใช่
สิ่งที่คุณคิดว่าคุณเริ่มไว้ ระหว่างสองอย่างนั้นมักมีชั้นที่คุณลืมนับ

## 7. ความล้มเหลวที่ไม่ควรถูกกลืน

จากบทที่ 3 เรารู้ว่า tool ต้องเปลี่ยน exception เป็นข้อความให้ model อ่าน
แต่มีข้อยกเว้นหนึ่งข้อ

```python
        except KeyboardInterrupt:
            # An interrupt is not a tool failure. Turning it into a readable
            # result would swallow the thing the person just asked for.
            raise
```

**ทำไมต้องยกเว้น** เพราะถ้าเราแปลง `KeyboardInterrupt` เป็น `ToolResult`
ที่เขียนว่ามีความผิดพลาด model จะอ่านแล้วตัดสินใจลองใหม่ ผลคือคนกดหยุด
แล้ว agent ทำงานต่อ ซึ่งคือบั๊กเดียวกับหัวข้อที่ 6 แค่มาจากคนละทาง

**หลักที่ใช้ได้ทั่วไป** `except Exception` ที่กว้างมีที่ทางของมัน แต่มันต้อง
มาพร้อมกับรายการสั้นๆ ของสิ่งที่ต้องปล่อยผ่าน สัญญาณหยุดที่มาจากคน
เป็นข้อแรกในรายการนั้นเสมอครับ

## 8. บทสนทนาที่รอดจาก crash คือบทสนทนาที่ถูกเขียนไว้แล้ว

หัวข้อที่ผ่านมาทั้งหมดว่าด้วยการล้มเหลวที่โปรแกรมยังอยู่ หัวข้อนี้ว่าด้วย
กรณีที่โปรแกรมไม่อยู่แล้ว ไฟดับ เครื่องรีสตาร์ท หรือ orchestrator ฆ่า
process ทิ้ง ในกรณีนั้น `finally` ไม่ทำงาน `except` ไม่ทำงาน และสิ่งเดียว
ที่เหลืออยู่คือสิ่งที่อยู่บนดิสก์ไปแล้ว

`src/agentpath/session.py` ยาวแปดสิบเอ็ดบรรทัด และเลือกไว้สามอย่าง

```python
"""Saving a conversation so you can come back to it.

The format is one JSON object per line, which is called JSONL. Two things
make it the right choice here. Each message is written the moment it
happens rather than at the end, so a crash loses nothing that already
finished. And you can open the file and read it, which matters more than it
sounds, because the session file is the first place to look when you want
to know why the agent did something.

This version supports one writer. Two processes appending to the same
session will interleave their lines and corrupt it. Real harnesses take a
lock before writing and release it after. That is left out here because the
locking is not the lesson, but the limit is real and you should know it.
"""
```

**ทำไม JSONL ไม่ใช่ JSON ก้อนเดียว** เพราะ JSON ก้อนเดียวต้องปิดวงเล็บถึงจะ
อ่านได้ ไฟล์ที่เขียนค้างไว้ครึ่งทางจึงเป็นไฟล์เสียทั้งไฟล์ ส่วน JSONL คือ
หนึ่งบรรทัดหนึ่งข้อความ บรรทัดสุดท้ายที่เขียนไม่จบเป็นบรรทัดเดียวที่เสีย
และทุกบรรทัดก่อนหน้ายังอ่านได้ตามปกติ นี่คือความต่างระหว่างการเสียบทสนทนา
ทั้งบท กับการเสียข้อความสุดท้ายหนึ่งข้อความ

**ทำไมเขียนทีละบรรทัดตอนเกิด ไม่ใช่เขียนตอนจบ** ด้วยเหตุผลเดียวกับที่บทนี้
ทั้งบทตั้งอยู่บน คือของที่ทำเสร็จไปแล้วต้องไม่หายไปกับสิ่งที่ยังไม่เสร็จ

```python
    def append(self, message: Message) -> None:
        """Write one message immediately.

        Appending as we go rather than saving at the end is what makes a
        crash survivable. Everything that already happened is on disk.
        """
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(to_json(message) + "\n")
```

ราคาของทางเลือกนี้คือการเปิดปิดไฟล์ทุกข้อความ ซึ่งช้ากว่าการเขียนทีเดียว
อย่างเห็นได้ชัดในทางทฤษฎี และวัดไม่ออกในทางปฏิบัติ เพราะจังหวะของ agent
ถูกกำหนดโดยการรอ model ไม่ใช่โดยดิสก์

**และ safe_name มีไว้เพราะชื่อ session มาจากผู้ใช้** ชื่อไฟล์ที่รับมาจาก
argument ของบรรทัดคำสั่ง คือข้อมูลที่ไม่น่าเชื่อถือชนิดเดียวกับที่บทที่ 5
พูดถึง ชื่อว่า `../../notes` จะเขียนไฟล์นอกโฟลเดอร์ sessions ได้ทันที

```python
def safe_name(name):
    """Turn a session name into something that cannot leave the folder.

    The name reaches us from a command line argument, so a name of
    ../../notes would have written outside the sessions directory. Keeping
    only the last part and refusing the two dot names is enough, and it
    keeps the file name readable, which matters because reading these
    files by eye is what they are for.
    """
```

**สังเกตว่ามันไม่ได้ใช้ `resolve_inside`** เพราะสิ่งที่เข้ามาไม่ใช่พาธ
มันคือชื่อ วิธีที่ถูกจึงไม่ใช่การตรวจว่าพาธที่ประกอบแล้วอยู่ในโฟลเดอร์ไหม
แต่คือการทิ้งทุกอย่างที่ไม่ใช่ชื่อ เก็บเฉพาะส่วนหลังตัวคั่นตัวสุดท้าย
แล้วแทนอักขระที่ไม่ใช่ตัวอักษรตัวเลขด้วยขีด สิ่งที่เหลือจึงเป็นชื่อไฟล์
โดยโครงสร้าง ไม่ใช่โดยการผ่านการตรวจ

**ข้อจำกัดที่เขียนไว้แทนที่จะซ่อน** คือหนึ่งไฟล์รับผู้เขียนได้คนเดียว
สอง process ที่ append ไฟล์เดียวกันจะได้บรรทัดที่สลับกัน harness จริง
ใช้ lock ตรงนี้ โปรเจกต์นี้ไม่ทำเพราะ lock ไม่ใช่บทเรียน แต่การรู้ว่า
ขอบอยู่ตรงไหน คือสิ่งที่ทำให้คุณไม่เอาโค้ดนี้ไปวางในที่ที่มันพังครับ

## 9. สรุป

- แบ่งความล้มเหลวเป็นพวกที่คำขอผิด กับพวกที่รับไม่ไหว retry เฉพาะพวกหลัง

- Retry-After จาก server ชนะสูตรของเราเสมอ สูตรมีไว้ใช้ตอนที่มันเงียบ

- jitter ป้องกันไม่ให้ client กลายเป็นสาเหตุของการล่มที่ยืดยาว

- อะไรที่มี side effect retry ไม่ได้โดยลำพัง ต้องมี idempotency key
  ซึ่งเป็นสัญญาสองฝ่าย

- stream ที่เริ่มไหลแล้ว retry ไม่ได้ เส้นที่ซื่อสัตย์อยู่ที่การเปิดคำขอ

- การหยุดต้องหยุดของจริงทุกชั้นด้วย token ตัวเดียวที่ทุกคนถือร่วมกัน

- สิ่งที่รอด crash คือสิ่งที่อยู่บนดิสก์แล้ว JSONL ที่เขียนทีละบรรทัดตอนเกิด
  จึงเสียได้อย่างมากหนึ่งบรรทัด ไม่ใช่ทั้งไฟล์

## บทเรียนที่ลงมือทำเรื่องนี้

| บทเรียน | สิ่งที่ได้ลงมือทำ |
| --- | --- |
| 08 shell tool | ใส่ timeout ให้ subprocess และเห็นว่าทำไมการฆ่าแค่ shell ไม่พอ |
| 17 errors and retries | เขียน `with_retries` เอง แยกสถานะที่ retry ได้ เคารพ Retry-After ใส่ jitter และสร้าง token ที่หยุดของจริงทุกชั้น ผ่าน mock server ที่จำลอง rate limit และ 500 ได้ |
| 18 the harness | ต่อ cancellation เข้ากับ CLI จริง แล้วกดหยุดดูว่าอะไรหยุดจริงบ้าง |
| 13 sessions | เขียน session เป็น JSONL ทีละบรรทัด แล้วฆ่า process กลางทางเพื่อดูว่าอะไรรอด |
| 21 multi-agent | เห็นว่า agent หลายตัวที่รันพร้อมกันทำให้การหยุดยากขึ้นอย่างไร |
