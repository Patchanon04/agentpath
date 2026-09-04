# บทที่ 6 ระบบที่อยู่รอดคือระบบที่ยอมรับว่าจะพัง

คุณกดหยุด หน้าจอบอกว่าหยุดแล้ว แต่คำสั่งที่มันควรจะหยุดยังรันต่อจนจบ นี่ไม่ใช่
เรื่องสมมติ harness ที่คนใช้กันทุกวันเคย ship เวอร์ชันที่ทำแบบนี้ออกมาจริง
และมันพลาดในแบบเดียวกันทุกครั้ง คือส่วนที่บอกว่าหยุดกับส่วนที่ทำงานอยู่ เป็น
คนละส่วนที่ไม่ได้คุยกัน

agent อยู่ในตำแหน่งที่พังได้สามทาง มันเรียกบริการที่อยู่อีกฝั่งของอินเทอร์เน็ต
มันรัน subprocess (โปรแกรมที่โปรแกรมเราสั่งให้เริ่มทำงาน) บน
เครื่องที่คุณควบคุมไม่ได้ และมันทำงานนานพอที่คนจะเปลี่ยนใจกลางคัน ทั้งสามทาง
จะพังจริง คำถามจึงไม่ใช่ว่าจะกันยังไง แต่คือพอมันพังแล้วระบบทำอะไร

บทนี้ตอบคำถามนั้นเป็นสี่ชิ้น retry (ยิงคำขอเดิมซ้ำหลังพลาด) ที่รู้ว่าลองใหม่ตอนไหนช่วยและ
ตอนไหนแค่ช้าลง เส้นสองเส้นที่ retry ข้ามไม่ได้ token ตัวเดียวที่ถูกอ่านสามจุด จึงทำให้การ
กดหยุดหนึ่งครั้งหยุดงานที่ยังไม่เริ่มได้ทุกชิ้น และไฟล์ session ที่รอดจากการถูกฆ่ากลางทา
ง ชิ้นที่หนักคือชิ้นที่สาม เพราะมันขอให้คุณถือสามเรื่องไว้ในหัวพร้อมกัน คือ retry ที่อยาก
ลองใหม่ timeout ที่อยากเลิกรอ และการกดหยุดที่มาจากคน หัวข้อที่ 1 ถึง 5 จึงแยกทั้งสามออกจา
กกันก่อน แล้วหัวข้อที่ 6 ค่อยว่าด้วยตัวที่สามซึ่งต้องเห็นอีกสองตัวอยู่ในสายตาตลอด

หัวข้อที่ 3 เรื่อง jitter (บวกเวลาสุ่มเข้าไปในเวลารอ) ข้ามได้ในรอบแรก
ไม่มีหัวข้อไหนหลังจากนั้นที่ต้องใช้มัน

## 1. retry เฉพาะสิ่งที่ retry แล้วช่วย

retry ที่ใส่ผิดที่ไม่ได้ทำให้
ปัญหาหายไป มันทำให้ปัญหาช้าลง

```python
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
```

ความล้มเหลวมีสองพวก พวกที่บอกว่าคำขอของคุณผิด กับพวกที่บอกว่าตอนนี้เรารับ
ไม่ไหว พวกแรก retry ไม่ช่วย พวกหลังช่วย เส้นแบ่งอยู่ตรงนั้น

400 แปลว่าคำขอนั้นเองผิด ส่งอันเดิมไปใหม่ได้คำตอบผิดอันเดิมกลับมา แค่ช้าลง
401 แปลว่ากุญแจไม่ถูก และมันจะไม่ถูกเหมือนเดิมในอีกสองวินาที 404 แปลว่าไม่มี
สิ่งนั้น รอไปก็ไม่มี

429 ต่างออกไป มันแปลว่าเร็วเกินไป และคำว่าเร็วเกินไปหยุดเป็นจริงเมื่อเวลาผ่าน
500 กับ 503 แปลว่าฝั่งนั้นมีปัญหาชั่วคราว 408 แปลว่าหมดเวลา
รหัสพวกนี้คือสถานะที่รอแล้วต่างออกไปได้ จึงคุ้มที่จะรอ

การ retry 400 แย่กว่าการไม่ retry เลย เพราะมันซ่อนบั๊ก คำขอที่ผิดรูปจากการ
ตัด context ผิดวิธีตามบทที่ 4 ควรจะโผล่มาเป็น error ที่ชี้ตำแหน่งชัดเจน
แต่ถ้ามี retry ห่ออยู่ มันจะกลายเป็นความช้าที่อธิบายไม่ได้แทน คุณเสียเวลาสี่
เท่าเพื่อไปถึงข้อความ error เดิม แล้วสงสัยว่าเครือข่ายมีปัญหา ทั้งที่ปัญหาอยู่
ในโค้ดของคุณเอง คำขอที่ตัด context ผิดตามบทที่ 4 ควรคืน 400 กลับมาในสองร้อย
มิลลิวินาที ถ้ามี retry สี่ครั้งห่ออยู่ มันคืน 400 อันเดียวกันในเจ็ดวินาที และเจ็ด
วินาทีนั้นทำให้ทุกคนเดาว่าเป็นเรื่องเครือข่าย

transport error นับเป็นพวกที่ retry ได้ ไม่ใช่เพราะคำขอไม่ถึง server เสมอไป
timeout ตอนอ่านก็อยู่ในตระกูลนี้ทั้งที่ server รับคำขอไปแล้ว แต่เพราะสิ่งที่ห่ออยู่คือ
การถาม model ซึ่งถามซ้ำได้เสมอ การส่งใหม่จึงเป็นแค่การถามคำถามเดิมอีกครั้ง ไม่มีผลข้างเคียง

## 2. เชื่อ server ก่อนสูตรของเรา

การยิงซ้ำหนึ่งชุดกางออกบนเส้นเวลาแบบนี้ เวลารอโตขึ้นทุกครั้งที่พลาด

```mermaid
flowchart LR
    A1["ครั้งที่ 1<br/>วินาทีที่ 0.0<br/>ได้ 429"] --> W1["รอ 0.7"]
    W1 --> A2["ครั้งที่ 2<br/>วินาทีที่ 0.7<br/>ได้ 503"]
    A2 --> W2["รอ 1.6"]
    W2 --> A3["ครั้งที่ 3<br/>วินาทีที่ 2.3<br/>ได้ 200"]
```

ตัวเลขที่รอมาจากฟังก์ชันเดียว และบรรทัดแรกของมันไม่ได้คำนวณอะไรเลย

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

`Retry-After` คือ header ที่ผู้ให้บริการส่งกลับมาพร้อม 429 หรือ 503 บอกว่า
ให้รอกี่วินาทีก่อนลองใหม่ ในฟังก์ชันข้างบน มันชนะสูตรของเราขาด และควรชนะ

server รู้สิ่งที่เราไม่รู้ มันรู้ว่างบของเราจะรีเซ็ตเมื่อไหร่ รู้ว่าคิวยาวแค่ไหน
สูตรคูณสองของเราไม่รู้อะไรเลย มันคือการเดา ถ้าเราเดาสั้นกว่าที่ server บอก
เราเสียคำขอไปเปล่าๆ หนึ่งครั้ง และไปเพิ่มภาระให้ระบบที่กำลังแย่อยู่แล้ว สูตรจึง
มีไว้เป็นทางสำรองตอนที่ server เงียบ ไม่ใช่ความเห็นที่ไปหักล้างสิ่งที่มันบอก

`try` รอบ `float` อยู่ตรงนั้นเพราะสเปกของ HTTP อนุญาตให้ `Retry-After` เป็น
วันที่แบบ HTTP ได้ด้วย ไม่ใช่แค่ตัวเลขวินาที ถ้าแปลงไม่ได้เราตกไปใช้สูตรแทน
ซึ่งถูกกว่าการปล่อยให้ทั้ง retry พังเพราะ header ที่อ่านไม่ออกหนึ่งตัว

## 3. jitter ไม่ใช่ของประดับ

`(0.5 + random.random() / 2)` คือ jitter มันทำให้เวลารอจริงอยู่ระหว่างครึ่งหนึ่งถึงเต็มของ
ค่าที่สูตรคำนวณได้ ดูเหมือนรายละเอียดปลีกย่อย จนกว่าจะเห็นว่ามันกันอะไร

สมมติมี client หนึ่งพันตัวคุยกับบริการเดียวกัน บริการนั้นล่มไปหนึ่งวินาที
client ทั้งพันได้ 503 พร้อมกัน ทุกตัวคำนวณเวลารอด้วยสูตรเดียวกัน ได้เลข
เดียวกัน คือหนึ่งวินาที หนึ่งวินาทีต่อมา client ทั้งพันยิงพร้อมกัน บริการที่
เพิ่งจะฟื้นโดนกระแทกด้วยพันคำขอในเสี้ยววินาที แล้วล่มอีกรอบ ทุกตัวได้ 503
อีก คำนวณได้สองวินาทีเท่ากันหมด แล้ววนแบบนี้ไป

ความล้มเหลวหนึ่งวินาทีกลายเป็นการล่มที่ยืดยาว และคนซ้ำเติมคือ client เอง

jitter ทำให้ client พันตัวรอไม่เท่ากัน คำขอที่กลับมาจึงกระจายตัวแทนที่จะกระจุก
บริการฟื้นได้จริง

ทำไมไม่สุ่มเต็มช่วงตั้งแต่ศูนย์ ทำได้ และบางระบบทำ แต่การรอใกล้ศูนย์แปลว่าบางตัวยิงกลับมา
แทบจะทันที ซึ่งทิ้งประโยชน์ของ backoff (ยืดเวลารอออกไปเรื่อยๆ เมื่อพลาดซ้ำ) ไปเปล่าๆ ช่วง
ครึ่งหนึ่งถึงเต็มรักษา backoff ไว้ พร้อมกับกระจายเวลาพอที่จะไม่กระจุก

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

เส้นแบ่งคือ idempotency (ทำซ้ำแล้วผลเท่าเดิม)

การถาม model ซ้ำไม่เปลี่ยนอะไรนอกบทสนทนา ถ้าคำขอแรกไม่ถึง เราแค่ถามใหม่ ถ้า
มันถึงแล้วแต่คำตอบหายกลางทาง คุณเสียเงินหนึ่งครั้ง เป็นราคาที่รับได้

การรัน tool ที่มี side effect (ทำแล้วมีอะไรในระบบเปลี่ยนไป) ไม่ใช่แบบนั้น retry คำสั่งที่
ส่งอีเมลแปลว่าอีเมลสองฉบับ retry คำสั่งที่ตัดเงินแปลว่าตัดสองครั้ง และเรื่องที่ทำให้มันร้
ายคือกรณีที่อยาก retry ที่สุดคือกรณีที่คุณไม่รู้ว่าเกิดอะไรขึ้น การเชื่อมต่อขาดหลังส่งคำข
อไปแล้วแต่ก่อนได้คำตอบ ตรงนั้นการกระทำอาจสำเร็จไปแล้ว และคุณไม่มีทางรู้

ทางแก้ที่ถูกคือ idempotency key (รหัสที่ผู้เรียกแนบไปให้ผู้รับรู้ว่าสองคำขอนี้คืออันเดียว
กัน) ผู้เรียกสร้างรหัสไม่ซ้ำหนึ่งตัวต่อหนึ่งเจตนา แล้วส่งไปกับทุกความพยายาม ฝั่งรับเก็บร
หัสที่เคยทำแล้วไว้คำขอที่สองที่ถือรหัสเดิมได้ผลลัพธ์ของครั้งแรกกลับไป โดยไม่ทำงานซ้ำ

ในทางปฏิบัติมันหน้าตาแบบนี้ agent สั่งเปิด ticket ผ่าน API ของระบบ helpdesk คำขอไปถึง
แล้วสายหลุดก่อนคำตอบจะกลับมา retry เปิด ticket ใบที่สองให้เรื่องเดียวกัน ถ้าทั้งสองครั้ง
ถือรหัสเดียวกัน ฝั่ง helpdesk คืนหมายเลขใบเดิมกลับมาแทนที่จะเปิดใบใหม่

สังเกตว่านี่ไม่ใช่สิ่งที่ฝั่ง client ทำเองได้ตามลำพัง มันคือสัญญาระหว่างสองฝั่ง
การ retry tool ที่ไม่ได้ออกแบบมารองรับ จึงไม่มีทางปลอดภัยด้วยโค้ดฝั่งคุณ
อย่างเดียว

ผลที่ตามมาในโค้ดคือ `with_retries` ห่อเฉพาะการเรียก provider เท่านั้น และ
ไม่มีที่ไหนใน codebase ที่ห่อ `tools.run` เลยครับ

## 5. stream ที่เริ่มไหลแล้ว retry ไม่ได้

มีอีกเส้นที่ละเอียดกว่านั้น และคนพลาดบ่อย

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

เมื่อ byte แรกมาถึง ผู้ใช้เห็นข้อความบางส่วนบนหน้าจอไปแล้ว ถ้าเราเปิดคำขอใหม่
คำตอบที่สองจะถูกต่อท้ายคำตอบแรกที่ค้างอยู่ ได้ข้อความที่ไม่มีใครเคยเขียน บนหน้าจอ
ผู้ใช้เห็นว่าไฟล์นี้มี 240 บรรทัด และบั๊กอยู่ที่ แล้วสายขาดตรงนั้น คำตอบใหม่เริ่มจาก
ต้นเรื่องอีกครั้ง สิ่งที่อ่านต่อกันคือประโยคค้างที่ตามด้วยประโยคเปิดของคำตอบคนละใบ
เส้นจึงอยู่ที่การเปิดคำขอ ก่อน byte แรก การยอมรับตรงๆ ว่า stream ที่เริ่ม
บริโภคแล้ว retry ไม่ได้ ดีกว่าโค้ดที่ดูเหมือนกู้คืนได้แต่ให้ผลลัพธ์ที่ผิด

ส่วน body ของ error ถูกอ่านก่อนโยน เพราะ error ที่รายงานแค่ตัวเลขสถานะส่งคน
ไปหาผิดที่ ข้อความที่ผู้ให้บริการเขียนมามักบอกเลยว่าอะไรผิด เช่น tool result
ที่ไม่มีคู่ ซึ่งคือกับดักของบทที่ 4 ทิ้งข้อความนั้นไป บั๊กที่แก้ได้ในห้านาที
กลายเป็นการค้นหาทั้งบ่าย

## 6. การขัดจังหวะต้องหยุดของจริงทุกชั้น

กลับมาที่ฉากเปิดบท หน้าจอบอกว่าหยุด แต่งานไม่หยุด

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

การหยุดต้องถูกเห็นหลายที่พร้อมกัน ก่อน loop เริ่มรอบใหม่ ก่อน tool แต่ละตัว
เริ่ม และก่อน shell จะ spawn process ส่วน stream หรือ process ที่กำลังวิ่งอยู่จะจบ
ของมันก่อน แล้วค่อยถูกหยุดที่ประตูถัดไป ถ้าแต่ละที่มีสัญญาณของตัวเอง
จะมีสักที่ที่ไม่ได้รับข่าว และนั่น
คือที่ที่บั๊กอยู่ object ตัวเดียวที่ทุกคนถือร่วมกัน คือวิธีเดียวที่ทุกที่ได้ข่าว
พร้อมกัน

`run_shell` ตรวจ token ก่อนเริ่ม process ด้วยเหตุผลที่ระบุไว้ตรงๆ

```python
        # Checked here rather than only in the loop because a command started
        # after the person pressed the interrupt key is exactly the failure
        # a cancellation token exists to prevent.
        if cancellation is not None and cancellation.cancelled:
            return "Cancelled before the command started."
```

ตรวจใน loop อย่างเดียวไม่พอ loop ตรวจก่อนเรียก tool แต่ละตัวก็จริง
แต่ระหว่างการตรวจนั้นกับ `Popen` ยังมีช่องว่าง และ token ถูกส่งให้ shell tool
ตอนสร้าง ไม่ได้ผ่าน loop ประตูของ shell จึงทำงานไม่ว่าใครเป็นคนเรียกมัน

มีบั๊กอีกตัวในหมวดนี้ที่โหดกว่า และมันซ่อนอยู่ในเมธอดที่ดูไม่มีพิษภัยที่สุด

```python
    def reset(self) -> None:
        """Clear the flag without replacing the object.

        Tools hold a reference to this token. Handing them a new object
        would leave them watching one that nothing ever cancels, so the
        interrupt would appear to work and then quietly stop working.
        """
```

`reset` ล้างค่าในตัวเดิมแทนที่จะสร้าง object ใหม่ เพราะ tool ทุกตัวถือ
reference ไปที่ตัวเดิม ถ้าเราสร้างตัวใหม่ tool จะเฝ้าตัวเก่าที่ไม่มีใครสั่ง
หยุดอีกแล้ว ผลคือการกดหยุดครั้งแรกทำงาน แล้วครั้งต่อๆ ไปไม่ทำงาน โดยไม่มี
error ให้เห็นเลย คนจะสรุปว่าตัวเองกดไม่ทัน

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

ภาพของมันคือ agent สั่ง `pytest` ผ่าน `run_shell` ที่ตั้ง timeout ไว้สามสิบวินาที
ชุดทดสอบนั้นใช้เวลาสี่นาที พอครบสามสิบวินาทีเราฆ่า shell แล้ว `pytest` ยังวิ่งต่อและ
ยังถือปลายท่ออยู่ การอ่านท่อจึงค้างรอจนกว่ามันจะจบเองอยู่ดี timeout ที่ตั้งไว้สามสิบ
วินาทีกลายเป็นสี่นาที

การหยุดต้องหยุดสิ่งที่ทำงานอยู่จริง ไม่ใช่สิ่งที่คุณคิดว่าคุณเริ่มไว้ ระหว่าง
สองอย่างนั้นมักมีชั้นที่คุณลืมนับ ที่นี่ชั้นนั้นคือ shell

## 7. ความล้มเหลวที่ไม่ควรถูกกลืน

จากบทที่ 3 เรารู้ว่า tool ต้องเปลี่ยน exception เป็นข้อความให้ model อ่าน
แต่มีข้อยกเว้นหนึ่งข้อ

```python
        except KeyboardInterrupt:
            # An interrupt is not a tool failure. Turning it into a readable
            # result would swallow the thing the person just asked for.
            raise
```

ถ้าเราแปลง `KeyboardInterrupt` เป็น `ToolResult` ที่เขียนว่ามีความผิดพลาด
model จะอ่านแล้วตัดสินใจลองใหม่ คนกดหยุด agent ทำงานต่อ บั๊กเดียวกับหัวข้อ
ที่ 6 แค่มาจากคนละทาง

`except Exception` ที่กว้างมีที่ทางของมัน Python แยกสัญญาณหยุดที่มาจากคนออกจาก
`Exception` ให้อยู่แล้ว บรรทัด `except KeyboardInterrupt: raise` ใน `base.py` จึง
เขียนไว้เพื่อให้คนที่วันหนึ่งขยาย `except` เป็น `BaseException` เห็นว่าห้ามครับ

## 8. บทสนทนาที่รอดจาก crash คือบทสนทนาที่ถูกเขียนไว้แล้ว

หัวข้อที่ผ่านมาทั้งหมดว่าด้วยความล้มเหลวที่โปรแกรมยังอยู่ หัวข้อนี้ว่าด้วย
กรณีที่โปรแกรมไม่อยู่แล้ว ไฟดับ เครื่องรีสตาร์ท orchestrator ฆ่า process ทิ้ง
ในกรณีนั้น `finally` ไม่ทำงาน `except` ไม่ทำงาน สิ่งเดียวที่เหลือคือสิ่งที่
อยู่บนดิสก์ไปแล้ว

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

อย่างแรกคือ JSONL แทน JSON ก้อนเดียว JSON ก้อนเดียวต้องปิดวงเล็บถึงจะอ่านได้
ไฟล์ที่เขียนค้างครึ่งทางจึงเสียทั้งไฟล์ JSONL คือหนึ่งบรรทัดหนึ่งข้อความ
บรรทัดสุดท้ายที่เขียนไม่จบเป็นบรรทัดเดียวที่เสีย ทุกบรรทัดก่อนหน้าอ่านได้
ตามปกติ นี่คือความต่างระหว่างเสียบทสนทนาทั้งบท กับเสียข้อความสุดท้ายหนึ่ง
ข้อความ ถ้าไฟดับตอนเขียนบรรทัดที่ 43 สิ่งที่เหลือบนดิสก์คือ 42 บรรทัดที่อ่านได้ครบ
กับบรรทัดสุดท้ายที่ขาด และงานสี่สิบสองรอบที่ทำไปแล้ว resume ต่อได้

อย่างที่สองคือเขียนทีละบรรทัดตอนเกิด ไม่ใช่ตอนจบ ด้วยเหตุผลเดียวกับที่บทนี้
ทั้งบทตั้งอยู่บน ของที่ทำเสร็จไปแล้วต้องไม่หายไปกับสิ่งที่ยังไม่เสร็จ

```python
    def append(self, message: Message) -> None:
        """Write one message immediately.

        Appending as we go rather than saving at the end is what makes a
        crash survivable. Everything that already happened is on disk.
        """
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(to_json(message) + "\n")
```

ราคาของทางเลือกนี้คือเปิดปิดไฟล์ทุกข้อความ ช้ากว่าเขียนทีเดียวอย่างเห็นได้
ชัดในทางทฤษฎี และวัดไม่ออกในทางปฏิบัติ เพราะจังหวะของ agent ถูกกำหนดโดยการ
รอ model ไม่ใช่โดยดิสก์

อย่างที่สามคือ `safe_name` และมันมีไว้เพราะชื่อ session มาจากผู้ใช้ ชื่อไฟล์
ที่รับมาจาก argument ของบรรทัดคำสั่งคือข้อมูลที่ไม่น่าเชื่อถือชนิดเดียวกับที่
บทที่ 5 พูดถึง ชื่อว่า `../../notes` จะเขียนไฟล์นอกโฟลเดอร์ sessions ได้ทันที

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

มันไม่ได้ใช้ `resolve_inside`
เพราะสิ่งที่เข้ามาคือชื่อ ไม่ใช่พาธการตรวจว่าพาธที่ประกอบแล้วอยู่ในโฟลเดอร์ไหมจึ
งไม่ตรงโจทย์วิธีที่ถูกคือทิ้งทุกอย่างที่ไม่ใช่ชื่อ เก็บเฉพาะส่วนหลังตัวคั่นตัวสุ
ดท้าย แล้วแทนอักขระที่ไม่ใช่ตัวอักษร ตัวเลข ขีด หรือจุดด้วยขีด แล้วตัดขีดกับจุด
ที่หัวท้ายทิ้ง ซึ่งขั้นหลังคือสิ่งที่กัน `..`
สิ่งที่เหลือเป็นชื่อไฟล์โดยโครงสร้าง ไม่ใช่โดยการผ่านการตรวจ

ข้อจำกัดหนึ่งข้อถูกเขียนไว้แทนที่จะซ่อน หนึ่งไฟล์รับผู้เขียนได้คนเดียว สอง
process ที่ append ไฟล์เดียวกันจะได้บรรทัดที่สลับกัน harness จริงใช้ lock
ตรงนี้ โปรเจกต์นี้ไม่ทำเพราะ lock ไม่ใช่บทเรียน แต่การรู้ว่าขอบอยู่ตรงไหน
คือสิ่งที่ทำให้คุณไม่เอาโค้ดนี้ไปวางในที่ที่มันพังครับ

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
| 13 sessions | เขียน session เป็น JSONL ทีละบรรทัด แล้วฆ่า process กลางทางเพื่อดูว่าอะไรรอด |
| 17 errors and retries | เขียน `with_retries` เอง แยกสถานะที่ retry ได้ เคารพ Retry-After ใส่ jitter และสร้าง token ที่หยุดของจริงทุกชั้น ผ่าน mock server ที่จำลอง rate limit และ 500 ได้ |
| 18 the harness | ต่อ cancellation เข้ากับ CLI จริง แล้วกดหยุดดูว่าอะไรหยุดจริงบ้าง |
| 21 multi-agent | เห็นว่า agent หลายตัวที่รันพร้อมกันทำให้การหยุดยากขึ้นอย่างไร |
