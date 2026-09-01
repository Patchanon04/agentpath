[Read in English](README.md)

# บทที่ 19 MCP client

## ยินดีต้อนรับสู่ part 4

Part 1 สร้าง agent ขึ้นมา Part 2 ให้ tool จริง ๆ กับมัน Part 3 ทำให้มันอยู่รอดได้
ซึ่งเป็นคนละแกนกันโดยสิ้นเชิง และบทที่ 18 ใช้ทั้งบทพิสูจน์ว่าความต่างระหว่าง
"ทำได้" กับ "ใช้งานจริงได้" นั้นมีอยู่จริงและวัดได้

Part 4 ว่าด้วยขีดจำกัดของ agent ตัวเดียว ที่อยู่ลำพัง ใช้ได้แค่ tool ที่คุณเขียนเอง
และไม่มีเครื่องมือวัดเลยว่าการเปลี่ยนแปลงที่คุณทำนั้นดีขึ้นจริงหรือไม่ ขีดจำกัดสามข้อ
และแต่ละข้อได้บทของตัวเอง

บทนี้เชื่อม agent เข้ากับ tool ที่คนอื่นเขียน บทที่ 20 ให้มันมอบงานให้ agent อีกตัว
ที่มี context สดของตัวเอง และบทที่ 21 รัน agent แบบนั้นหลายตัวพร้อมกัน บทที่ 22
จะให้เครื่องมือวัดกับคุณเสียที ทั้ง task runner และ judge เพื่อให้ประโยคว่า
"ผมว่า prompt ใหม่ดีกว่า" กลายเป็นการทดลองที่คุณรันได้ แทนที่จะเป็นแค่ความรู้สึก
บทที่ 23 จะแพ็กทั้งหมดนี้รวมกัน

ทีนี้มาถึงส่วนที่คุณควรคาดไว้อยู่แล้วมากกว่าจะแปลกใจ **agent loop ก็ไม่เปลี่ยนใน
part นี้เช่นกัน**

บทที่ 11 วัดเรื่องนี้ไว้ บทที่ 18 วัดซ้ำอีกครั้งด้วยตารางของ hash ไฟล์ และผลลัพธ์ก็
ชัดเจนแม่นยำ tool ไม่เคยแตะ loop ส่วน subsystem แตะเสมอ บทนี้เพิ่ม protocol
ทั้งตัว เพิ่ม process ที่สอง เพิ่ม handshake และเพิ่ม tool ประเภทที่ยังไม่มีอยู่เลย
ตอนโปรแกรมเริ่มต้น แต่ `agent.py` ยังเหมือนเดิมทุก byte กับบทที่ 17

```bash
cd lessons
for f in agent.py permissions.py session.py context.py providers.py usage.py \
         retry.py cancel.py prompt.py retrieval.py; do
  diff -qs 18-the-harness/$f 19-mcp-client/$f
done
```

```text
Files 18-the-harness/agent.py and 19-mcp-client/agent.py are identical
Files 18-the-harness/permissions.py and 19-mcp-client/permissions.py are identical
Files 18-the-harness/session.py and 19-mcp-client/session.py are identical
Files 18-the-harness/context.py and 19-mcp-client/context.py are identical
Files 18-the-harness/providers.py and 19-mcp-client/providers.py are identical
Files 18-the-harness/usage.py and 19-mcp-client/usage.py are identical
Files 18-the-harness/retry.py and 19-mcp-client/retry.py are identical
Files 18-the-harness/cancel.py and 19-mcp-client/cancel.py are identical
Files 18-the-harness/prompt.py and 19-mcp-client/prompt.py are identical
Files 18-the-harness/retrieval.py and 19-mcp-client/retrieval.py are identical
```

มาถึงตอนนี้ ผลลัพธ์แบบนี้ควรอ่านได้ว่าเป็นสิ่งที่คาดไว้อยู่แล้ว ไม่ใช่คำกล่าวอ้าง
ถ้าการเชื่อมต่อกับ tool server ภายนอกต้องแก้ loop ก็แปลว่ารอยต่อระหว่าง loop
กับ tool registry ถูกตัดผิดที่ และการถกเถียงเรื่องตำแหน่งของขอบเขตตลอดสิบแปดบท
ที่ผ่านมาก็ผิดหมด

นี่คือสิ่งที่อยู่ในโฟลเดอร์นี้

```text
lessons/19-mcp-client/
  mcp.py               new. the whole client, around 190 lines with docstrings
  mock_mcp_server.py   new. a tiny MCP server so the check needs nothing external
  check.py             new. five claims about the client
  tools.py             lesson 18, plus one 8 line function called register_mcp
  main.py              identical to lesson 18
  agent.py             identical to lesson 17
  permissions.py       identical to lesson 12
  session.py           identical to lesson 13
  context.py           identical to lesson 14
  providers.py         identical to lesson 17
  usage.py             identical to lesson 15
  retrieval.py         identical to lesson 16
  prompt.py            identical to lesson 10
  retry.py             identical to lesson 17
  cancel.py            identical to lesson 17
  README.md            this file
```

นอกเหนือจากไฟล์ใหม่สามไฟล์ `tools.py` เป็นไฟล์เดียวที่เปลี่ยนเลย
และการเปลี่ยนคือสิบเจ็ดบรรทัดท้ายไฟล์ ไฟล์อื่นทุกไฟล์ในโฟลเดอร์นี้ รวมถึง `main.py`
เป็นไบต์ต่อไบต์เหมือนที่บทที่ 18 ส่งมอบไว้

```bash
diff 18-the-harness/tools.py 19-mcp-client/tools.py
```

```python
# Lesson 19 lets tools arrive from another process at run time.


def register_mcp(schemas, functions):
    """Add tools discovered from an MCP server to the ones we wrote ourselves.

    Nothing else changes. The agent loop, the permission check and the
    registry all treat these exactly like read_file.
    """
    SCHEMAS.extend(schemas)
    FUNCTIONS.update(functions)


# Tools we did not write are never on the safe list, so every one of them
# goes through the permission gate from lesson 12.
```

สองคำสั่งกับสองคอมเมนต์ นั่นคือต้นทุนใน codebase นี้ ของการที่จะใช้ MCP server
ทุกตัวที่ใครก็ตามเคยเขียนขึ้นมาได้

## 1. ปัญหาที่ part 3 ทิ้งไว้

หัวข้อ 7 ของบทที่ 18 เอ่ยถึงขีดจำกัดนี้แล้วเดินจากไป ตอนนี้มันกลับมาอีกครั้ง
ในฐานะสิ่งที่บทนี้ต้องแก้

ลองนับ tool ที่ agent ของคุณมี `read_file`, `write_file`, `edit_file`,
`list_files`, `run_shell`, `glob_files`, `grep_files`, `search_notes` แปดตัว
ทุกตัวอยู่ใน `tools.py` และทุกตัวคุณเขียนเองด้วยมือ พร้อม schema พร้อมรายการ
dispatch พร้อมการจัดการ error พร้อมการตัดสินใจเรื่อง permission และพร้อม `check.py`

นั่นเป็นชุด tool ที่มีประโยชน์จริงสำหรับการแก้โค้ดในโฟลเดอร์หนึ่ง และมันก็เป็น
รายการทั้งหมดของสิ่งที่ agent ตัวนี้ทำได้ ตลอดไป เว้นแต่คุณจะเขียนเพิ่ม

ทีนี้ลองอยากได้ตัวที่เก้าดู ขอให้ agent ตัวนี้อ่านสักแถวจากฐานข้อมูล Postgres ของคุณ
ขอให้มันเปิดหน้าเว็บใน browser แล้วบอกว่ามีอะไรอยู่บนนั้น ขอให้มันค้นหา ticket
ที่คุณกำลังทำอยู่ หรือเช็กว่า deploy ออกไปหรือยัง หรือค้นเอกสารของทีมคุณ
หรือดูไฟล์ design คำตอบของทุกข้อคือคำตอบเดียวกัน ไปเขียน tool เอาเอง

แล้วก็เขียนอีกตัว แล้วก็อีกตัว แต่ละตัวคือ schema ที่คุณต้องทำให้ถูก รายการ dispatch
การตัดสินใจว่าความล้มเหลวจะคืนค่าอะไร การถกเถียงว่ามันควรอยู่ใน `SAFE_TOOLS`
หรือไม่ และ check ที่พิสูจน์ว่ามันทำงาน การทำแบบนั้นแปดครั้งกินเวลาเกือบทั้ง part 2

นี่คือส่วนที่ควรทำให้คุณหงุดหงิด มีคนเขียน tool สำหรับ Postgres ที่ดีไว้แล้ว
มีคนเขียน tool สำหรับ browser ที่ดีไว้แล้ว และ tool สำหรับ ticket ที่ดีไว้แล้ว
และมันดีกว่าที่คุณจะเขียนได้ในบ่ายเดียว เพราะมันถูกใช้โดยคนหลายพันคนจนมุมคม ๆ
ถูกลบไปหมดแล้ว และไม่มีทางเลยที่ agent ของคุณจะใช้ตัวไหนได้เลยสักตัว

เหตุผลอยู่ที่บรรทัดเดียว และเป็นบรรทัดที่คุณตั้งใจเขียน

```python
def run(name, arguments):
    function = FUNCTIONS.get(name)
```

`FUNCTIONS` คือ dictionary ของฟังก์ชัน Python ที่อยู่ใน process นี้ tool ในสายตา
ของโปรแกรมนี้คือ Python callable ที่ถูก import เข้ามาใน interpreter ตัวนี้
อะไรที่ไม่ใช่แบบนั้นก็ถือว่าไม่มีอยู่

รอยต่อที่ทำให้ part 2 ใช้ได้ ซึ่ง tool เป็นแค่ชื่อใน dictionary และ loop ไม่รู้อะไร
เกี่ยวกับมันเลย คือรอยต่อเดียวกันที่ปิดตัวลงตรงนี้ มันเป็นรอยต่อที่ดี เพียงแต่มัน
ถูกลากรอบ process ที่ผิดตัว

## 2. MCP คืออะไรกันแน่

ลอกแบรนด์ ลอกเอกสารข้อกำหนด และลอก ecosystem ออกไป Model Context Protocol
เหลือแค่ประโยคเดียว

**server คือโปรแกรมแยกต่างหากที่ประกาศว่าตัวเองทำอะไรได้ และลงมือทำเมื่อถูกขอ**

แค่นั้นเอง มีข้อความสามแบบที่คุณต้องสนใจ คุณขอให้ server ทำ `initialize`
ซึ่งคือ handshake ที่ทั้งสองฝั่งบอกว่าตัวเองคือใคร คุณขอ `tools/list` แล้วมันส่ง
รายการ tool กลับมาพร้อมชื่อ คำอธิบาย และ JSON Schema ของ argument คุณส่ง
`tools/call` พร้อมชื่อและ argument บางอย่าง แล้วมันก็ทำสิ่งนั้นและส่งผลลัพธ์กลับมา

สังเกตหน้าตาของรายการ tool ตอนที่มันมาถึง

```json
{
  "name": "add",
  "description": "Add two numbers and return the sum.",
  "inputSchema": {
    "type": "object",
    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
    "required": ["a", "b"]
  }
}
```

ทีนี้ดูสิ่งที่ model ต้องการ ซึ่งคุณสร้างด้วยมือมาตั้งแต่บทที่ 03

```json
{
  "type": "function",
  "function": {
    "name": "add",
    "description": "Add two numbers and return the sum.",
    "parameters": {"type": "object", "properties": {"...": "..."}}
  }
}
```

มันคือสามฟิลด์เดียวกันที่ใส่เสื้อผ้าคนละชุด ชื่อ คำอธิบาย JSON Schema
นั่นไม่ใช่เรื่องบังเอิญ และเป็นเหตุผลที่ทำให้บทนี้สั้น การแปลงจากสิ่งที่ server ประกาศ
ไปเป็นสิ่งที่ model อ่านคือการเปลี่ยนชื่อ key สองตัว ซึ่งเป็นเหตุผลที่ `mcp_schemas`
ยาวสามสิบบรรทัดและส่วนใหญ่เป็น docstring

### ทำไมเรื่องนี้ถึงสำคัญ และไม่ใช่เพราะมันเป็นมาตรฐาน

คำโฆษณามาตรฐานของ MCP คือมันเป็น open standard ที่มีคนใช้กว้างขวาง ซึ่งจริง
และไม่ใช่เหตุผลให้คุณต้องสนใจอะไรทั้งนั้น มาตรฐานคุ้มที่จะรับมาใช้เมื่อสิ่งที่มันมา
ทำให้เป็นมาตรฐานนั้นเคยเจ็บปวด และควรเมินเมื่อมันไม่เคยเจ็บ

เหตุผลที่ควรสนใจคือเหตุผลจากหัวข้อ 1 ทุกความสามารถในโลกที่มีคนอุตส่าห์แพ็ก
เป็น MCP server ตอนนี้กลายเป็นความสามารถที่ agent ของคุณมี และปริมาณโค้ด
ที่คุณต้องเขียนเพื่อให้ได้มาคือศูนย์ ไม่ใช่ "adapter เล็ก ๆ" แต่คือศูนย์ คุณรันคำสั่ง
หนึ่งคำสั่งแล้วอ่านรายการ

ลองนั่งคิดว่ามันเปลี่ยนงานของคุณอย่างไร ก่อนบทนี้ คำถามว่า "agent ทำ X ได้ไหม"
ถูกตอบด้วย "ฉันต้องใช้เวลานานแค่ไหนถึงจะเขียน X" หลังบทนี้ มันถูกตอบด้วย
"มีใครเขียน X ไว้หรือยัง" และคำถามที่สองมีอัตราการเจอที่ดีกว่ามาก

นั่นคือข้อโต้แย้งทั้งหมด มันคือกลไกกระจายความสามารถ และมันบังเอิญถูกกำหนดเป็น
protocol เพราะนั่นเป็นวิธีเดียวที่กลไกกระจายจะทำงานข้ามภาษาและข้ามบริษัทได้
ถ้าพรุ่งนี้มีของแบบเดียวกันมาในชื่ออื่นด้วย wire format อื่น เหตุผลที่จะใช้มันก็เหมือนกันเป๊ะ

### ข้อจำกัดสองข้อของสิ่งที่เราสร้างในบทนี้

บอกไว้ตรงหัวไฟล์ `mcp.py` แทนที่จะให้คุณไปค้นพบเองตอนเที่ยงคืน

client ตัวนี้พูดได้แค่ **stdio transport เท่านั้น** server เป็น subprocess และเรา
คุยกับมันผ่าน standard input และ output ของมัน MCP ยังนิยาม HTTP transport ไว้ด้วย
และ server ที่พูดได้แค่ HTTP จะใช้กับไฟล์นี้ไม่ได้เลย นั่นเป็นข้อจำกัดจริง และเป็น
ข้อจำกัดที่ถูกต้องสำหรับบทเรียน เพราะกรณี stdio คือกรณีที่ protocol มองเห็นได้ชัด
ส่วนกรณี HTTP เพิ่ม transport ที่คุณเข้าใจอยู่แล้วจากบทที่ 01 โดยไม่ได้เพิ่ม protocol อะไรเลย

และ **tool ทุกตัวที่มันค้นพบจะถูกทำเครื่องหมายว่าไม่ปลอดภัย** หัวข้อ 7 ทั้งหัวข้อ
ว่าด้วยเหตุผลนั้น

## 3. ทำไมเราถึงเขียน client เอง แทนที่จะติดตั้งของสำเร็จรูป

มี MCP SDK อย่างเป็นทางการอยู่ `pip install mcp` แล้วคุณก็จบใน 4 บรรทัด
เราไม่ใช้มัน ด้วยเหตุผลเดียวกับที่บทที่ 01 เขียน HTTP request ด้วยมือ แทนที่จะ
import ไลบรารีของ provider

ข้อโต้แย้งตอนนั้นคือ ไลบรารีที่ซ่อน request ไว้ก็ซ่อนความจริงที่ว่าบทสนทนาทั้งหมด
ถูกส่งใหม่ทุกครั้งที่เรียก และความจริงข้อนั้นกลายเป็นคำอธิบายของต้นทุนส่วนใหญ่
และขีดจำกัดส่วนใหญ่ในคอร์สที่เหลือ คุณคิดวิเคราะห์เกี่ยวกับสิ่งที่ไม่เคยเห็นไม่ได้

ที่นี่ก็เหมือนกัน และคมกว่าเดิม ส่วนของ MCP ที่ agent ต้องใช้จริง ๆ มีแค่สาม method
ดูขนาดของมัน

```bash
grep -c "" mcp.py
```

```text
188
```

หนึ่งร้อยแปดสิบแปดบรรทัด รวมทั้ง docstring ระดับ module สิบเจ็ดบรรทัดและ
คอมเมนต์ที่อธิบายเหตุผล โค้ดจริงคือ class เดียวที่มีหก method กับฟังก์ชันหนึ่งตัว
คุณอ่าน protocol ทั้งหมดได้ในสิบนาที และหลังจากนั้นคุณจะรู้แน่ชัดว่าจะเกิดอะไรขึ้น
เมื่อ server ค้าง รู้แน่ชัดว่า `isError` แปลว่าอะไร รู้แน่ชัดว่าทำไมชื่อ tool ต้องมี prefix
และรู้แน่ชัดว่า tool พวกนั้นทำให้คุณเสียอะไรบ้างในทุก request

ติดตั้ง SDK ก่อน แล้วทั้งสี่เรื่องนั้นจะอยู่หลัง abstraction พอ agent ของคุณเงียบไป
เฉย ๆ เพราะ server ไม่เคยได้รับ notification ชื่อ `initialized` คุณจะไม่มีแบบจำลอง
ของระบบเลยสักนิด และคุณจะต้องมานั่งอ่าน async internals ของคนอื่นภายใต้แรงกดดัน
ด้านเวลา ซึ่งเป็นจังหวะที่แย่ที่สุดในการเรียนรู้ protocol

ทีนี้มาพูดให้เป็นธรรมกับอีกฝั่ง เพราะข้อโต้แย้งนี้ไม่ได้ยืดไปไกลเท่าที่คนชอบดันมัน

**ใช้ SDK ในโปรเจกต์ของคุณเอง** เมื่ออ่านไฟล์นี้จบแล้ว คุณรู้ว่าไลบรารีทำอะไรอยู่
และเมื่อถึงจุดนั้นไลบรารีดีกว่าตัวนี้อย่างชัดเจน มันรองรับ transport แบบ HTTP และ SSE
มันรองรับ server ที่ส่ง notification ว่ารายการ tool ของตัวเองเปลี่ยนไป มันรองรับ
resources และ prompts และ sampling ซึ่งเป็นส่วนของ protocol ที่ client ตัวนี้
ไม่สนใจเลย เพราะ agent ไม่ต้องใช้มันเพื่อเรียก tool มันถูกทดสอบกับ server จริง
หลายร้อยตัวพร้อมนิสัยแปลก ๆ ของแต่ละตัว ส่วนไฟล์นี้ถูกทดสอบกับ server ตัวเดียว
ที่เราเขียนขึ้นให้ประพฤติดี

กฎเดียวกับบทที่ 01 เขียนเองครั้งหนึ่งเพื่อให้เข้าใจ แล้วหันไปใช้ไลบรารี และเป็นคน
ในทีมที่ debug มันได้เวลามันพัง

## 4. JSON-RPC บน pipe ทีละบรรทัด

ถึงเวลาดู byte จริง ๆ transport เป็นสิ่งที่ลึกลับน้อยที่สุดในบทนี้ และการได้เห็นมัน
ก็ลบความลึกลับส่วนใหญ่ของเรื่องที่เหลือออกไป

server คือโปรแกรม คุณสตาร์ตมันเป็น subprocess คุณเขียน JSON ลง standard input
ของมันหนึ่ง object ต่อหนึ่งบรรทัด และคุณอ่าน JSON จาก standard output ของมัน
หนึ่ง object ต่อหนึ่งบรรทัด นั่นคือ transport ทั้งหมด

```python
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
```

argument สี่ตัวในนั้นมีบทบาทสำคัญและควรเอ่ยชื่อ

`stderr=subprocess.DEVNULL` เพราะ stdout คือช่องทางของ protocol และห้ามมี
อย่างอื่นอยู่บนนั้น server พ่นเสียง debug ลง stderr ตลอดเวลา ถ้ารวมสองช่องเข้าด้วยกัน
บรรทัด log แรกที่ server เขียนจะกลายเป็นบรรทัดที่ทำให้ตัว parse JSON ของคุณสำลัก

`text=True` คู่กับ `encoding="utf-8"` เพราะไม่อย่างนั้นคุณจะอ่าน byte แล้วต้อง decode
เอง และเพราะ encoding ปริยายบน Windows ไม่ใช่ UTF-8 ดังนั้น server ที่คืน
ตัวอักษรที่ไม่ใช่ ASCII จะให้ mojibake หรือ exception บนแพลตฟอร์มหนึ่ง
แต่ทำงานได้ปกติบนอีกแพลตฟอร์ม

`bufsize=1` คือ line buffering ถ้าไม่มีมัน Python อาจกอด request ของคุณไว้ใน buffer
ระหว่างที่คุณรอคำตอบที่มาไม่ได้ เพราะจริง ๆ แล้วคุณยังไม่ได้ส่งอะไรออกไป
เรายังเรียก `flush()` อย่างชัดเจนหลังทุกครั้งที่เขียน ซึ่งเป็นเข็มขัดเสริมให้กับสายเอี๊ยมคู่นั้น

### ลองแลกเปลี่ยนข้อความจริงด้วยมือ

คุณไม่จำเป็นต้องมี client เพื่อดูเรื่องนี้ server คือโปรแกรมที่อ่านบรรทัด ก็แค่ pipe
บรรทัดเข้าไป

```bash
cd lessons/19-mcp-client
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"agentpath","version":"1.0.0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python mock_mcp_server.py
```

```text
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "agentpath-mock", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "echo", "description": "Return the text you were given, unchanged.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string", "description": "Anything at all"}}, "required": ["text"]}}, {"name": "add", "description": "Add two numbers and return the sum.", "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}, {"name": "explode", "description": "Always fail, so a client can be tested against a failing tool.", "inputSchema": {"type": "object", "properties": {}, "required": []}}]}}
```

สามบรรทัดเข้าไป สองบรรทัดกลับมา อ่านรูปทรงของมัน

### id, method, params, result

JSON-RPC มีสี่ฟิลด์ที่คุณต้องสนใจ และทั้งสี่ปรากฏอยู่ข้างบนแล้ว

**`method`** คือชื่อของสิ่งที่คุณกำลังขอ `initialize`, `tools/list`, `tools/call`
เครื่องหมายทับเป็นแค่ส่วนหนึ่งของชื่อ ไม่ใช่ path

**`params`** คือ argument ของ method นั้น เป็น object เสมอ สำหรับ `initialize`
มันบรรจุเวอร์ชันของ protocol ที่คุณพูด ความสามารถที่คุณมี และคุณเป็นใคร
สำหรับ `tools/list` มันว่างเปล่า สำหรับ `tools/call` มันคือชื่อ tool กับ argument
ของ tool เอง ซ้อนลงไปอีกหนึ่งชั้น

**`id`** คือวิธีที่คุณจับคู่คำตอบกับคำถาม คุณเป็นคนเลือกมัน server ส่งกลับมา
เหมือนเดิมไม่เปลี่ยน ของเราคือตัวนับ

```python
            self._next_id += 1
            identifier = self._next_id
```

**`result`** คือคำตอบ ซึ่งมีอยู่เมื่อการเรียกสำเร็จ เมื่อไม่สำเร็จจะมี object ชื่อ `error`
แทน พร้อม `code` และ `message` และจะไม่มีทั้ง `result` และ `error` ในข้อความเดียวกัน

```python
                if "error" in message:
                    raise MCPError(message["error"].get("message", "unknown server error"))
                return message.get("result") or {}
```

ความแตกต่างข้อนี้สำคัญกว่าที่ตาเห็น และหัวข้อ 6 ว่าด้วยเรื่องนี้ `error` ที่ระดับนี้
หมายถึง **server** ล้มเหลว เช่น method ไม่มีอยู่จริงหรือ request ผิดรูปแบบ
ส่วน tool ที่รันแล้วไม่พอใจ argument ของตัวเองเป็นคนละเรื่องกันโดยสิ้นเชิง
และมาถึงข้างใน `result`

ยังมีฟิลด์ `jsonrpc` ซึ่งเป็นสตริง `"2.0"` เสมอ และคุณจะไม่ต้องคิดถึงมันอีกเลย

### รูปแบบของข้อความมีสองแบบ

ดูบรรทัดที่สองที่เรา pipe เข้าไป

```json
{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
```

ไม่มี `id` นั่นคือความแตกต่างทั้งหมดระหว่าง request กับ notification ข้อความที่มี id
คาดหวังคำตอบ ข้อความที่ไม่มีไม่คาดหวัง และต้องไม่ได้รับคำตอบด้วย นั่นคือเหตุผล
ที่สามบรรทัดเข้าไปแล้วออกมาสองบรรทัด

server จัดการเรื่องนี้ด้วยสามบรรทัดกับหนึ่งคอมเมนต์

```python
    if identifier is None:
        # A notification such as notifications/initialized. Nothing to answer.
        return None
```

และ client มี method แยกต่างหากสำหรับส่งข้อความแบบนั้น เพื่อไม่ให้ผู้เรียกคนไหน
เผลอไปนั่งรอคำตอบของข้อความที่จะไม่มีวันได้คำตอบ

```python
    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})
```

### ทีนี้ทำแบบเดิมผ่าน client

```bash
python -c "
import sys
from mcp import MCPClient
with MCPClient([sys.executable, 'mock_mcp_server.py']) as client:
    print('server name:', client.server_name)
    for t in client.list_tools():
        print(' -', t['name'], '|', t['description'])
    print('echo  ->', repr(client.call_tool('echo', {'text': 'across a pipe'})))
    print('add   ->', repr(client.call_tool('add', {'a': 2, 'b': 3})))
"
```

```text
server name: agentpath-mock
 - echo | Return the text you were given, unchanged.
 - add | Add two numbers and return the sum.
 - explode | Always fail, so a client can be tested against a failing tool.
echo  -> 'across a pipe'
add   -> '5'
```

`with` สตาร์ต process และทำ handshake แล้วปิด pipe และเก็บกวาด process ตอนขาออก
`connect` และ `close` เป็น public ด้วย เพราะ `check.py` และ agent ที่อยู่ยาว
ต้องการถือ server เปิดค้างไว้ข้ามหลาย turn แทนที่จะเปิดแค่บล็อกเดียว

สังเกตว่า `list_tools` ทำอะไรกับรูปทรงของโปรแกรม มันคือการค้นพบ **ตอน run time**
ไม่มีอะไรใน repository นี้รู้ว่ามี tool ชื่อ `add` อยู่ จนกว่าการเรียกนั้นจะคืนค่ากลับมา
tool ทุกตัวก่อนหน้าบทนี้คือชื่อที่คนพิมพ์ลงไปใน `tools.py` แต่พวกนี้ไม่ใช่
และนั่นคือความใหม่ที่แท้จริงของบทนี้ มากกว่าตัว protocol เสียอีก

## 5. สองเรื่องที่จะเล่นงานคุณ

ทั้งสองเรื่องอยู่ในโค้ดพร้อมคอมเมนต์กำกับ และทั้งสองสร้างอาการที่ชี้ไปผิดที่

### หนึ่ง notification ชื่อ initialized ไม่ใช่ของที่ข้ามได้

handshake มีสองขั้น ไม่ใช่ขั้นเดียว คุณส่ง `initialize` แล้วอ่านคำตอบ จากนั้นคุณส่ง
notification ชื่อ `notifications/initialized` ที่ไม่มี id และไม่มีคำตอบ

```python
        answer = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "agentpath", "version": "1.0.0"},
            },
        )
        self.server_name = (answer.get("serverInfo") or {}).get("name", "unknown")
        self._notify("notifications/initialized")
```

ข้อความที่สองดูเหมือนพิธีกรรม แต่ไม่ใช่ มันคือ client ที่บอกว่าตัวเองได้อ่าน
ความสามารถของ server แล้วและพร้อมแล้ว และ **server หลายตัวปฏิเสธที่จะประมวลผล
อะไรทั้งสิ้นจนกว่ามันจะมาถึง**

นี่คือเหตุผลที่เรื่องนี้คุ้มค่ากับการมีหัวข้อของตัวเองแทนที่จะเป็นแค่บรรทัดเดียว
ข้ามมันไปแล้วความล้มเหลวจะไม่ใช่ error คุณส่ง `tools/list` server ปฏิเสธที่จะตอบ
เพราะคุณไม่เคยทำ handshake ให้จบ และ client ของคุณก็นั่งอยู่ใน
`stdout.readline()` รอบรรทัดที่จะไม่มีวันถูกเขียน ไม่มี exception ไม่มีข้อความ
ไม่มี exit code โปรแกรมแค่หยุดนิ่ง

อาการจึงเป็นการค้าง และการค้างพาคุณไปตามหา deadlock ปัญหา buffering
subprocess ที่สตาร์ตไม่สำเร็จ หรือ network ที่หยุดชะงัก คุณจะไปเช็ก `bufsize`
คุณจะไปเช็กว่า server crash หรือเปล่า คุณจะเติม print เข้าไป ทั้งหมดนั้นผิดที่
เพราะไม่มีอะไรพัง server กำลังรออย่างสุภาพเพื่อข้อความที่คุณตัดสินใจไม่ส่ง
และมันจะรอตลอดไปเพราะ protocol บอกให้มันทำแบบนั้น

ความผิดพลาดอีกสองแบบที่ทำให้ค้างเหมือนกันเป๊ะและควรรู้ไว้ตอนที่คุณอยู่ตรงนั้น
คำสั่ง server ที่ไม่มีอยู่จริงจะสตาร์ตได้ปกติในสายตาของ `Popen` แล้วตายไป
ดังนั้นอ่าน guard ใน `_send`

```python
        if self.process is None or self.process.poll() is not None:
            raise MCPError("the server is not running")
```

`poll()` คืน exit code ถ้า process จบไปแล้ว ดังนั้น server ที่ตายไปแล้วจะกลายเป็น
exception ในการเขียนครั้งถัดไป แทนที่จะกลายเป็นการรอเงียบ ๆ บน pipe ที่ปิดไปแล้ว
และ server ที่ปิด output ของตัวเองจะกลายเป็น exception แทนที่จะเป็นสตริงว่าง
ที่ถูกเอาไป parse เป็น JSON

```python
                if not line:
                    raise MCPError(f"the server closed while waiting for {method}")
```

พูดตรง ๆ เรื่องช่องโหว่หนึ่งข้อตอนที่เราอยู่ตรงนี้ `MCPClient.__init__` รับ argument
ชื่อ `timeout` และเก็บมันไว้ แต่ไม่มีอะไรในไฟล์อ่านค่านั้นเลย การอ่านที่บล็อกตลอดไป
ยังเป็นไปได้อยู่ จาก server ที่ยังมีชีวิต ไม่ได้ปิดอะไร และแค่ไม่มีวันตอบ การอุดช่องโหว่นั้น
หมายถึง reader thread พร้อม queue หรือการอ่านแบบ non blocking และมันเป็นกลไก
ที่มากกว่าที่บทนี้จะแบกไหวจริง ๆ argument ตัวนั้นถูกทิ้งไว้เพราะนั่นคือที่ของมัน
เมื่อคุณจะเพิ่มความสามารถนี้ และการบอกชื่อช่องโหว่ก็ดีกว่าปล่อยให้พารามิเตอร์
ทำให้เข้าใจว่าเรื่องนี้ถูกจัดการแล้ว

### สอง อ่านไปเรื่อย ๆ จนกว่า id จะตรง

วิธีเขียน request แบบที่นึกออกทันทีคือเขียนหนึ่งบรรทัดแล้วอ่านหนึ่งบรรทัด

```python
# what you would write first, and it is wrong
self._send(request)
return json.loads(self.process.stdout.readline())["result"]
```

มันใช้ได้ จนถึงจุดที่ใช้ไม่ได้ และวิธีที่มันพังนั้นน่ากลัว

server อาจส่งข้อความที่ไม่ใช่คำตอบของคำถามคุณเมื่อไรก็ได้ ข้อความ log
notification บอกความคืบหน้า notification บอกว่ารายการ tool ของมันเปลี่ยน
ไม่มีอันไหนพก id ของคุณมาด้วย เพราะไม่มีอันไหนเป็นคำตอบ ดังนั้นบรรทัดถัดไป
ที่ออกจาก pipe บ่อยครั้งไม่ใช่สิ่งที่คุณขอ

หยิบบรรทัดแรกมาแล้วคุณจะได้ `KeyError` ที่ `result` ถ้าโชคดี เพราะ notification
ไม่มีฟิลด์ `result` ถ้าโชคร้ายคุณจะได้ dictionary ว่าง ๆ แล้วเดินหน้าต่อกับ
ผลลัพธ์ tool ที่จริง ๆ แล้วเป็นบรรทัด log และคำตอบทุกอันหลังจากนั้นใน session
ก็เหลื่อมไปหนึ่งช่อง เพราะคำตอบที่คุณข้ามไปยังนั่งอยู่ใน pipe รอให้ถูกเข้าใจผิด
ว่าเป็นคำตอบของอันถัดไป

ดังนั้น loop จึงอ่านไปเรื่อย ๆ จนกว่า id จะตรง และทิ้งทุกอย่างที่เหลือ

```python
            while True:
                line = self.process.stdout.readline()
                if not line:
                    raise MCPError(f"the server closed while waiting for {method}")
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("id") != identifier:
                    continue
```

คำสั่ง `continue` สี่ตัว และแต่ละตัวคือสิ่งที่ server ทำจริง ๆ บรรทัดว่าง บรรทัดที่
ไม่ใช่ JSON ซึ่งคือหน้าตาของ server ที่พิมพ์ผิด stream notification ซึ่งไม่มี id เลย
ดังนั้น `message.get("id")` เป็น `None` และไม่มีวันเท่ากับ integer ของคุณ
และคำตอบของ request อื่น

ข้อสุดท้ายคือเหตุผลที่ทั้ง method นั่งอยู่ในล็อก

```python
        with self._lock:
```

สอง thread ที่ส่ง request ลง pipe เดียวกันพร้อมกันจะเขียนสลับกันไปมา
และแต่ละตัวก็จะแข่งกันอ่านคำตอบที่อาจเป็นของฝ่ายไหนก็ได้ ล็อกทำให้การส่ง
และการอ่านทั้งหมดเป็น operation เดียวแบบ atomic เรื่องนี้แลกมาด้วยความสามารถ
ในการทำงานพร้อมกัน เพราะการเรียก tool ที่ช้าจะบล็อก thread ที่สองซึ่งแค่อยาก
list tool เฉย ๆ และสำหรับ client ขนาดนี้นั่นคือการแลกที่ถูกต้อง บทที่ 21 คือที่ที่
คุณจะได้รู้ว่าส่วนไหนของโปรแกรมคุณแอบสมมติว่ามีแค่ thread เดียว และตัวนี้ไม่ได้สมมติ
อย่างจงใจ

## 6. tool ที่ล้มเหลวไม่ใช่ exception

บทที่ 07 ตั้งกฎที่ยืนหยัดมาตลอดตั้งแต่นั้น เมื่อ tool ล้มเหลว ความล้มเหลวไม่ใช่
exception แต่เป็นสตริงที่กลับเข้าไปในบทสนทนาในฐานะผลลัพธ์ของ tool
เพราะ model คือสิ่งที่ทำอะไรกับมันได้

```python
# lesson 07
except FileNotFoundError:
    return f"Error: {path} does not exist"
```

agent อ่านข้อความนั้น สังเกตว่า path ผิด เรียก `list_files` แล้วลองใหม่ ถ้า raise
แทน การรันก็จบลงด้วย traceback เพราะพิมพ์ผิดตัวเดียว

MCP มีแนวคิดเดียวกัน สะกดว่า `isError` คำตอบของ `tools/call` ทุกอันพก content
กับ flag มาด้วย

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"explode","arguments":{}}}' \
  | python mock_mcp_server.py
```

```text
{"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "5"}], "isError": false}}
{"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "this tool always fails on purpose"}], "isError": true}}
```

อ่านสองบรรทัดนั้นให้ดี เพราะสิ่งสำคัญคือสิ่งที่ทั้งสองมีเหมือนกัน **ทั้งคู่คือ `result`**
ไม่มีอันไหนเป็น `error` ของ JSON-RPC tool ระเบิดไปแล้วแต่ protocol ยังบอกว่า
การเรียกสำเร็จ เพราะในมุมมองของ protocol มันสำเร็จจริง ๆ คุณขอให้ server รัน tool
และมันก็รัน tool และความเห็นของ tool คือเรื่องนี้ไปได้ไม่สวย

นั่นคือความแตกต่างเดียวกับที่คอร์สนี้ย้ำมาตั้งแต่บทที่ 07 ถูกยกระดับขึ้นไปอยู่ใน
wire format ส่วน client ก็แค่ทำตาม

```python
        try:
            result = self._request("tools/call", {"name": name, "arguments": arguments})
        except MCPError as error:
            return f"Error: the MCP server failed, {error}"
        parts = [
            block.get("text", "")
            for block in result.get("content", [])
            if block.get("type") == "text"
        ]
        text = "\n".join(part for part in parts if part)
        if result.get("isError"):
            return f"Error: {text or 'the tool failed with no message'}"
        return text
```

สามเส้นทาง และแต่ละเส้นทางคืนสตริง

**server ที่พัง** ถูกจับแล้วแปลงเป็นข้อความ เพราะแม้แต่เรื่องนั้น model ก็ยังกู้ได้
มันลอง tool อื่นได้ หรือบอกคุณได้ว่าเกิดอะไรขึ้น แทนที่จะตายไปเฉย ๆ

**tool ที่ล้มเหลว** กลายเป็น `Error: ` บวกกับสิ่งที่ tool พูด prefix นี้สำคัญ
มันคือรูปแบบเดียวกับที่ tool ทุกตัวใน `tools.py` ใช้ ดังนั้น model ที่เรียนรู้ที่จะ
จำความล้มเหลวจาก `read_file` ได้ ก็จำอันนี้ได้โดยไม่ต้องบอกอะไรใหม่เลย

**tool ที่สำเร็จ** คืนข้อความของมัน สังเกตว่า `content` เป็นลิสต์ของบล็อก
และแต่ละบล็อกมี type เพราะ tool ของ MCP คืนรูปภาพและ resource ที่ฝังมาได้
นอกเหนือจากข้อความ เราเก็บบล็อกที่เป็นข้อความและทิ้งที่เหลือ ซึ่งเป็นการลดทอน
อย่างซื่อสัตย์ server ที่คืน screenshot มาจะไม่คืนอะไรที่มีประโยชน์ผ่าน client ตัวนี้
และการจัดการเรื่องนั้นให้ถูกต้องแปลว่า model ต้องรับรูปภาพได้ ซึ่งเป็นบทที่คอร์สนี้ไม่มี

ดูทั้งสามเส้นทาง บวกกับกรณีที่ server เองตัดสินว่า argument ผิด

```bash
python -c "
import sys
from mcp import MCPClient
with MCPClient([sys.executable, 'mock_mcp_server.py']) as client:
    print('add   ->', repr(client.call_tool('add', {'a': 2, 'b': 3})))
    print('add   ->', repr(client.call_tool('add', {'a': 2})))
    print('boom  ->', repr(client.call_tool('explode', {})))
"
```

```text
add   -> '5'
add   -> "Error: bad arguments, 'b'"
boom  -> 'Error: this tool always fails on purpose'
```

บรรทัดกลางคือบรรทัดที่ควรชื่นชม argument ที่จำเป็นขาดไป server สังเกตเห็น
และ model ได้รับแจ้งว่ามันลืม key ไหน มันจะใส่ `b` แล้วลองใหม่ ไม่มีอะไร crash
ไม่มีอะไรหาย และการรันก็ดำเนินต่อไป

## 7. tool ที่ค้นพบมาไม่เคยปลอดภัย

หัวข้อนี้ไม่ใช่ทางเลือกและไม่ใช่คำปฏิเสธความรับผิด มันคือเหตุผลที่ `register_mcp`
ยาวแปดบรรทัดแทนที่จะเป็นสองบรรทัด

หยุดคิดสักครู่ว่าคุณเพิ่งทำอะไรลงไป คุณสตาร์ตโปรแกรมที่คนอื่นเขียน บนเครื่องของคุณ
ด้วยบัญชีผู้ใช้ของคุณ แล้วถามมันว่าทำอะไรได้บ้าง มันตอบมาด้วยรายชื่อและคำอธิบาย
และคำอธิบายเหล่านั้นกำลังจะเข้าไปอยู่ใน context ของ model ที่จะตัดสินใจด้วยตัวเอง
ว่าจะรันอันไหนและด้วย argument อะไร

มีสามเรื่องที่จริงพร้อมกัน และแต่ละเรื่องเพียงลำพังก็เพียงพอแล้ว

**คุณไม่ได้เขียน tool พวกนี้** tool ทุกตัวใน part 2 มาพร้อมกับข้อถกเถียงว่ามันควร
ปฏิเสธอะไร `read_file` ปฏิเสธที่จะออกนอก workspace เพราะ `resolve_inside`
เทียบ path ที่ resolve แล้วกับ `WORKSPACE` `run_shell` มี timeout `edit_file`
ปฏิเสธการจับคู่ที่กำกวมแทนที่จะเดาว่าคุณหมายถึงตำแหน่งไหน คุณรู้ว่ากฎเหล่านั้นมีอยู่
เพราะคุณเขียนมันและถกเถียงเรื่องมันมาสี่บท คุณไม่รู้อะไรแบบนั้นเลยเกี่ยวกับ tool
ที่ค้นพบมา มันอาจจำกัดตัวเองอยู่ในไดเรกทอรีหนึ่ง หรืออาจไม่ ไม่มีฟิลด์ไหนใน protocol
ที่บอกคุณได้ และไม่มีฟิลด์ไหนบอกได้ เพราะฟิลด์คือคำกล่าวอ้าง

**คำอธิบายคืออะไรก็ตามที่ผู้เขียนตัดสินใจจะอ้าง** ข้อนี้คือข้อที่คมที่สุด คำอธิบาย tool
ไม่ใช่เอกสารที่มีอะไรตรวจสอบ มันคือสตริงใน JSON object ที่เขียนโดยผู้เขียน server
ซึ่งเข้าไปตรง ๆ ใน context ของ model ของคุณ และเป็นฐานทั้งหมดที่ model ใช้
ตัดสินใจเรียก tool tool ชื่อ `get_weather` ที่คำอธิบายบอกว่าคืนพยากรณ์อากาศ
จะทำอะไรก็ได้เมื่อคุณเรียกมัน และบทที่ 12 สอนคุณไปแล้วว่าจะเกิดอะไรขึ้นเมื่อ
ข้อความที่ไว้ใจไม่ได้ตกลงมาอยู่ใน context เดียวกับคำสั่งของคุณ เรื่องนี้แย่กว่า
prompt injection ในบทที่ 12 เพราะที่นั่นข้อความของผู้โจมตีมาในไฟล์ที่ agent อ่าน
ส่วนที่นี่มันมาในรายการ tool ก่อนงานจะเริ่มด้วยซ้ำ ในที่ที่ model ถือว่าเป็น
ความสามารถของตัวเอง

**server คือโปรแกรมที่รันอยู่บนเครื่องคุณ** ไม่ใช่ฟังก์ชันใน sandbox แต่เป็น
subprocess ที่สตาร์ตโดย `subprocess.Popen` ด้วยสิทธิ์ไฟล์ของคุณ การเข้าถึง
เครือข่ายของคุณ ตัวแปรสภาพแวดล้อมของคุณ และดังนั้นก็รวมถึง API key ของคุณ
การเพิ่ม MCP server ลงในคอนฟิกคือการรันโค้ดของคนอื่น มันสมควรได้รับความระแวง
เท่ากับ `curl | sh` และปกติมันได้น้อยกว่านั้นมาก เพราะมันมาผ่านตัวช่วยติดตั้ง
ที่หน้าตาเป็นมิตร

กฎจึงเด็ดขาดและไม่มีข้อยกเว้นให้เถียง

```python
# Tools we did not write are never on the safe list, so every one of them
# goes through the permission gate from lesson 12.
```

ดูวิธีบังคับใช้ เพราะมันบังคับใช้ด้วยการละเว้นมากกว่าด้วยการตรวจสอบ และการละเว้น
คือกลไกที่แข็งแรงกว่าในกรณีนี้

```python
SAFE_TOOLS = {"read_file", "list_files", "glob_files", "grep_files"}
```

สี่ชื่อ เขียนตายตัว และเป็นของเราทั้งหมด `register_mcp` เติมของลงใน `SCHEMAS`
และ `FUNCTIONS` และไม่แตะ `SAFE_TOOLS` เลย และไม่มีเส้นทางโค้ดไหนในโปรแกรม
ที่เติมของลงในนั้นได้ตอน run time ดังนั้น `Permissions.check` ก็จะไปถึงบรรทัดแรก
ไม่เจอชื่อ แล้วตกลงไปที่การถามคน

```python
    def check(self, name, arguments):
        if name in SAFE_TOOLS:
            return True
```

คอมเมนต์เหนือ set นั้นใน `permissions.py` คือหลักการออกแบบที่พูดออกมาตรง ๆ

```python
# A tool missing from this set is treated as dangerous, which is the safe
# direction to be wrong in.
```

allowlist ล้มแบบปิด blocklist ล้มแบบเปิด ถ้าประตูตรวจถูกเขียนเป็น "ปฏิเสธ tool
ที่อยู่ในรายชื่ออันตรายนี้" tool ของ MCP ทุกตัวก็จะผ่านฉลุยโดยปริยาย และการผิด
เพียงครั้งเดียวก็แปลว่าผิดในทิศทางที่ข้อมูลของใครบางคนหายไปแล้ว

ทีนี้มาถึงทางเลือกที่น่าดึงดูด เพราะคุณจะอยากได้มันภายในวันเดียวหลังใช้ของนี้
tool ของ MCP พก annotation มาได้ รวมถึงตัวหนึ่งชื่อ `readOnlyHint` การอ่านค่านั้น
แล้วเอา tool ที่อ่านอย่างเดียวไปใส่ในรายการปลอดภัยเป็นเรื่องง่าย และมันจะลดคำถาม
ไปได้เยอะ

อย่าทำ `readOnlyHint` คือคำกล่าวอ้างของผู้เขียนคนเดียวกับที่เขียน tool และคำอธิบาย
tool ที่ตั้งใจจะเป็นอันตรายก็ตั้งค่ามันเป็น true คำว่า hint ในชื่อนั้นทำงานจริง
และมันเป็น hint สำหรับ user interface ไม่ใช่เส้นแบ่งด้านความปลอดภัย tool
ตัวเดียวที่อยู่ในรายการปลอดภัยได้คือ tool ที่คุณอ่าน source ของมันได้ใน repository นี้

ผลในทางปฏิบัติคือ การเชื่อม server ที่ช่างพูดเข้ากับ agent ที่ใช้ `ask_in_terminal`
จะทำให้คุณถูกถามเยอะมาก และคุณจะอยากคว้า `--yes` ความตึงเครียดนั้นมีจริง
และบทนี้ไม่ได้แก้มัน คำตอบที่ซื่อสัตย์คือ `--yes` มีไว้สำหรับเครื่องที่รันงานที่คุณเข้าใจ
อยู่แล้ว และ MCP server ที่คุณตรวจสอบและไว้ใจแล้วมีความเสี่ยงต่างจากตัวที่คุณเพิ่ง
ติดตั้งเมื่อเช้านี้ และตัวเลือก `[a]lways` จำลายเซ็นเต็มรวมถึง argument ด้วย
ดังนั้นการอนุมัติการเรียกเฉพาะอย่างหนึ่งไปตลอดกาลไม่ได้เป็นการอนุมัติ tool นั้น
โดยรวม

## 8. schema พวกนั้นมีต้นทุนเท่าไร นับเป็นตัวอักษรจริง

นี่คืออีกหัวข้อที่จำเป็น และเป็นต้นทุนที่ไม่มีใครเอ่ยถึงตอนที่บอกให้คุณเชื่อม server
สิบสองตัว

schema ของ tool ทุกตัวถูกส่งไปใน **ทุก request** ไม่ใช่ครั้งเดียวตอนเริ่ม ไม่ได้ถูก
cache ไว้บน server ผลการค้นพบของบทที่ 01 ที่ว่าบทสนทนาทั้งหมดถูกส่งใหม่ทุกครั้ง
ใช้กับรายการ tool ด้วย และรายการ tool ถูกส่งไปก่อนที่ model จะอ่านงานของคุณ
แม้แต่คำเดียว

อย่าเชื่อข้อโต้แย้ง ให้ดูตัวเลข บรรทัดสุดท้ายของ `check.py` วัดมันด้วยการ serialise
`tools.SCHEMAS` ก่อนและหลังการเชื่อมต่อ

```python
def schema_size():
    import json

    return len(json.dumps(tools.SCHEMAS))
```

```text
OK the schemas grew from 3101 to 3826 characters, 725 more on every request from one small server
```

**3101 ตัวอักษร** คือ tool แปดตัวที่คุณเขียนเอง ทุกอย่างที่ part 2 และ part 3
สร้างขึ้นมา **725 ตัวอักษร** คือสิ่งที่ server ตัวเล็กจิ๋วที่ตั้งใจให้เล็กเพิ่มเข้ามา
สาม tool คำอธิบายตัวละหนึ่งประโยค และ input schema ที่ใหญ่ที่สุดมีสอง property

นั่นคือราว ๆ **242 ตัวอักษรต่อ tool** จาก server ที่เล็กที่สุดเท่าที่จะเขียนได้

### ทีนี้ลองคำนวณกับการตั้งค่าจริง

server จริงอ้วนกว่าของเรามาก และไม่ใช่เพราะผู้เขียนสะเพร่า คำอธิบาย tool ที่มี
ประโยชน์คือหนึ่งย่อหน้า เพราะ model ต้องเลือกระหว่าง tool ตัวนี้กับอีกสิบเอ็ดตัว
ที่คล้ายกัน และ input schema มีสิบหรือสิบห้า property พร้อมคำอธิบายในแต่ละตัว
เพราะนั่นคือวิธีที่ model รู้ว่าจะใส่อะไรลงไป ระหว่าง 600 ถึง 1500 ตัวอักษรต่อ tool
เป็นเรื่องธรรมดามาก

สมมติคุณเชื่อม server สิบตัว ซึ่งไม่ใช่ตัวเลขสุดโต่ง และสมมติแต่ละตัวเสนอ tool
แปดตัว ซึ่งถือว่าน้อย นั่นคือ 80 tool

| ขนาดต่อ tool เท่านี้ | tool 80 ตัวมีต้นทุน | token โดยประมาณ |
| --- | --- | --- |
| 242 ตัวอักษร server ของเล่นของเรา | 19,360 ตัวอักษร | ราว 4,800 |
| 800 ตัวอักษร server ตามความเป็นจริง | 64,000 ตัวอักษร | ราว 16,000 |
| 1,500 ตัวอักษร server ขนาดใหญ่ | 120,000 ตัวอักษร | ราว 30,000 |

คอลัมน์ token ใช้ `CHARACTERS_PER_TOKEN = 4` จาก `context.py` ซึ่งเป็นตัวประมาณ
หยาบ ๆ ตัวเดียวกับที่บทที่ 14 ใช้ตัดสินใจว่าจะตัดเมื่อไร

เอาแถวกลางมาเทียบกับงบประมาณปริยายใน `main.py` ของบทที่ 18 ซึ่งคือ 100,000
สิบหกเปอร์เซ็นต์ของ context window ทั้งหมดหายไปก่อน system prompt ก่อนงานของคุณ
ก่อนที่ agent จะได้อ่านไฟล์แม้แต่ไฟล์เดียว และมันหายไปอีกครั้งใน request ถัดไป
และอันถัดจากนั้น เพราะ schema ถูกส่งใหม่ทุกครั้ง การรันยี่สิบ turn จ่ายค่าผ่านทางนั้น
ยี่สิบครั้ง

แล้วนึกถึงสิ่งที่บทที่ 14 ทำเมื่อถึงงบประมาณ มันทิ้งบล็อกที่เก่าที่สุด ซึ่งก็คือคำสั่ง
ดั้งเดิมของคุณ schema ไม่ได้อยู่ในรายการนั้นและตัดทิ้งไม่ได้ ดังนั้นสิ่งที่เกิดขึ้นจริง
คือรายการ tool ที่อ้วนไปดันงานของคุณเองออกนอกหน้าต่าง คุณจ่าย token เพื่อทำให้
agent ลืมว่ามันทำงานนี้ไปทำไม

### ต้นทุนที่ไม่ใช่ token

นี่คือส่วนที่ทำให้คนแปลกใจ และมันจะยังอยู่แม้ว่า context window จะใหญ่พอจน
ไม่มีใครนับตัวอักษรอีกต่อไป

**model ที่ต้องเลือกระหว่าง tool หกสิบตัวที่ชื่อคล้ายกันจะเลือกผิดบ่อยขึ้น**

server สามตัวต่างเสนอบางอย่างที่ชื่อ search หรือ `find_files` หรือ `query`
และคำอธิบายของทั้งหมดก็พูดทำนองว่าใช้ค้นหาของ ตอนนี้ model ต้องเลือกจาก
คำอธิบายอย่างเดียว โดยไม่มีทางลองอันหนึ่งแล้วดูผล มันเลือกอันที่ดูสมเหตุสมผล
แต่ผิด ได้ผลลัพธ์ที่ไม่มีประโยชน์แต่ก็ไม่ใช่ error แล้วก็คิดต่อจากตรงนั้น ความล้มเหลว
แบบนั้นไม่มี exception ไม่มีบรรทัด log และไม่มีอาการที่ชัดเจน มันแค่ดูเหมือน agent
โง่ลงนิดหน่อยในวันนี้

คุณดูเรื่องนี้แย่ลงได้เรื่อย ๆ เมื่อคุณเชื่อม server เพิ่ม tool แปดตัวที่มีหน้าที่ต่างกันชัดเจน
เป็นทางเลือกที่ง่าย ยี่สิบตัวก็ยังโอเค เกินสี่สิบตัวและมีการทับซ้อน อัตราความผิดพลาด
จะไต่ขึ้น และเหตุผลไม่ใช่ว่า model อ่อนแอ แต่เป็นเพราะคำถามมันยากขึ้นจริง ๆ
คุณเองก็จะเลือกผิด ถ้าให้คำอธิบายบรรทัดเดียวหกสิบอันโดยไม่มีทางทดลอง

ดังนั้นวินัยที่ต้องมีจึงไม่เป็นที่นิยมและก็เรียบง่าย เชื่อม server ที่คุณต้องใช้กับงาน
ตรงหน้า ไม่ใช่ server ทุกตัวที่คุณเคยตั้งค่าไว้ server ที่เชื่อมไว้สิบตัวไม่ได้ทำให้
agent เก่งกว่าสามตัว บ่อยครั้งมันแย่กว่าและแพงกว่าด้วย

### สิ่งที่วงการมาลงตัวกันในปี 2026

คำตอบที่ ecosystem ขยับเข้าหาคือหยุดส่งทุกอย่าง

แทนที่จะใส่ schema เต็มทั้งแปดสิบตัวลงในทุก request คุณให้ดัชนีสั้น ๆ กับ model
หนึ่งบรรทัดต่อ tool ชื่อกับคำอธิบายไม่กี่คำ และ tool พิเศษอีกหนึ่งตัวที่ดึง schema เต็ม
ของ tool ที่ระบุชื่อมาเมื่อต้องการ model อ่านดัชนี ตัดสินใจว่าต้องใช้ตัวของ Postgres
ขอ schema นั้น แล้วก็ได้มา คุณเปลี่ยนภาษีคงที่ 64,000 ตัวอักษรในทุก request
ให้เป็นไม่กี่พันตัวอักษร บวกกับการวิ่งไปกลับอีกหนึ่งรอบเฉพาะใน request ที่ต้องใช้ tool จริง ๆ

ถ้าฟังดูคุ้น ๆ ก็ถูกแล้ว มันคือข้อโต้แย้งของบทที่ 16 เรื่อง retrieval เป๊ะ ๆ นำมาใช้
กับนิยามของ tool แทนที่จะเป็นเอกสาร อย่าใส่ทุกอย่างลงใน context ใส่ดัชนีลงไป
แล้วดึงมาเมื่อต้องการ

มันไม่ฟรี การวิ่งไปกลับเพิ่มมีต้นทุนด้าน latency และ model ที่อ่านสรุปบรรทัดเดียว
ผิดจะไม่มีวันขอ schema ที่จะแก้ความเข้าใจผิดนั้น ดังนั้นคุณแลกปัญหาเรื่อง token
กับปัญหาเรื่องการค้นพบที่แย่ลงนิดหน่อย แต่ที่ tool แปดสิบตัว การแลกนั้นคุ้มอย่างชัดเจน
และที่แปดตัวมันไม่คุ้มอย่างชัดเจน ซึ่งเป็นเหตุผลที่ client ตัวนี้ทำแบบง่าย และหัวข้อนี้
บอกคุณว่าเส้นแบ่งอยู่ตรงไหน

## 9. ชื่อชนกัน

อีกเรื่องหนึ่ง เล็กและร้ายกาจ

server สองตัวเสนอ tool ชื่อ `search` ได้ทั้งคู่ ไม่มีอะไรใน protocol ห้ามไว้
และห้ามไม่ได้ด้วย เพราะ server ไม่รู้จักกันและกัน

`FUNCTIONS` เป็น dictionary `SCHEMAS` เป็นลิสต์ ดูสิว่าเกิดอะไรขึ้นเมื่อคุณลงทะเบียน
server สองตัวโดยไม่ใส่ prefix

```bash
python -c "
import sys
from mcp import MCPClient, mcp_schemas
import tools
a = MCPClient([sys.executable, 'mock_mcp_server.py']).connect()
b = MCPClient([sys.executable, 'mock_mcp_server.py']).connect()
tools.register_mcp(*mcp_schemas(a))
tools.register_mcp(*mcp_schemas(b))
names = [s['function']['name'] for s in tools.SCHEMAS]
print('schema list length:', len(tools.SCHEMAS))
print('dispatch table length:', len(tools.FUNCTIONS))
print('echo appears', names.count('echo'), 'times in the schemas')
a.close(); b.close()
"
```

```text
schema list length: 14
dispatch table length: 11
echo appears 2 times in the schemas
```

สิบสี่ schema กับสิบเอ็ดฟังก์ชัน model ถูกแสดง `echo` สองครั้งและไปถึงได้แค่ตัวเดียว
คือตัวที่สอง เพราะ `FUNCTIONS.update` เขียนทับตัวแรกไปแล้ว ไม่มี error ถูกโยน
ไม่มีอะไรถูกบันทึก tool ของ server ตัวแรกยังเชื่อมอยู่ ยังทำงานอยู่ และเข้าถึงไม่ได้
โดยสิ้นเชิง

ทีนี้ลองนึกภาพว่า server สองตัวนั้นคือฐานข้อมูล staging กับฐานข้อมูล production
ที่เปิด `run_query` ทั้งคู่ model เรียก `run_query` ได้คำตอบ และทั้งคุณและมันก็ไม่มี
ทางรู้เลยว่าฐานข้อมูลไหนตอบ

ทางแก้คือ prefix และเป็นเหตุผลที่ `mcp_schemas` รับมันเข้ามา

```python
    for described in client.list_tools():
        name = described["name"]
        exposed = f"{prefix}.{name}" if prefix else name
```

ส่ง prefix เข้าไปจาก `check.py` แล้ว registry จะหน้าตาเป็นแบบนี้แทน

```bash
python -c "
import sys
from mcp import MCPClient, mcp_schemas
import tools
with MCPClient([sys.executable, 'mock_mcp_server.py']) as client:
    schemas, functions = mcp_schemas(client, prefix=client.server_name)
    tools.register_mcp(schemas, functions)
    print([s['function']['name'] for s in tools.SCHEMAS])
    print('via tools.run ->', repr(tools.run('agentpath-mock.add', {'a': 40, 'b': 2})))
"
```

```text
['read_file', 'write_file', 'edit_file', 'list_files', 'run_shell', 'glob_files',
 'grep_files', 'search_notes', 'agentpath-mock.echo', 'agentpath-mock.add',
 'agentpath-mock.explode']
via tools.run -> '42'
```

ตอนนี้ `agentpath-mock.echo` ชนกับของเราไม่ได้ และชนกับ server ตัวอื่นไม่ได้
prefix ยังทำอะไรที่มีประโยชน์กับ model ด้วย คือมันทำให้ทางเลือกที่กำกวมจากหัวข้อ 8
กำกวมน้อยลงนิดหนึ่ง `staging.run_query` กับ `production.run_query` เป็น tool
สองตัวที่ model แยกแยะได้ ส่วน tool สองตัวที่ชื่อ `run_query` เหมือนกันนั้นแยกไม่ได้

prefix เป็นตัวเลือกในลายเซ็นฟังก์ชัน เพราะ server ตัวเดียวที่ไม่มีโอกาสชนกันอ่านง่ายกว่า
เมื่อไม่มี prefix และเพราะการบังคับใช้จะทำให้พารามิเตอร์รู้สึกเหมือนพิธีกรรมแทนที่จะเป็น
การตัดสินใจ ใช้มันเมื่อไรก็ตามที่อาจมี server มากกว่าหนึ่งตัว ซึ่งในทางปฏิบัติคือเสมอ

มีรายละเอียดหนึ่งในฟังก์ชันนั้นที่ควรชี้ให้เห็น เพราะมันเป็นบั๊กประเภทที่ใช้เวลาหาเป็นชั่วโมง

```python
        def make(bound_name):
            def call(**arguments):
                return client.call_tool(bound_name, arguments)

            return call

        functions[exposed] = make(name)
```

ฟังก์ชันด้านในถูกสร้างโดยฟังก์ชันด้านนอกที่รับชื่อเป็น argument เวอร์ชันที่นึกออก
ทันทีคือนิยาม `call` ตรง ๆ ใน loop แล้ว closure จับ `name` ซึ่งใช้ไม่ได้
closure ของ Python จับตัวแปร ไม่ใช่ค่าของมัน ดังนั้นเมื่อถึงเวลาที่มีอะไรเรียก
ฟังก์ชันพวกนั้น loop จบไปแล้ว และทุกตัวจะเห็นชื่อสุดท้ายในลิสต์ tool ทั้งสามตัว
ของคุณจะไปเรียก `explode` กันหมด การส่งชื่อเข้าไปใน `make` ผูกมันไว้กับพารามิเตอร์
ใหม่ในแต่ละรอบ ซึ่งเป็นสิ่งที่ทำให้แต่ละ closure จำ tool ของตัวเองได้

## 10. การรัน check.py

```bash
cd lessons/19-mcp-client
python check.py
```

```text
OK connected and the server says it is agentpath-mock
OK 3 tools were discovered at run time, not written by us
OK agentpath-mock.echo ran in another process and the answer came back
OK a tool that fails on the server becomes text the model can read
OK the schemas grew from 3101 to 3826 characters, 725 more on every request from one small server
```

ห้าบรรทัด หนึ่งบรรทัดต่อหนึ่งหัวข้อของบทนี้ ไล่ดูตามลำดับ

**หนึ่ง handshake เสร็จสมบูรณ์** `client.server_name` คือ `agentpath-mock`
ซึ่งเป็นค่าที่มาจากบล็อก `serverInfo` ในคำตอบของ `initialize` ได้เท่านั้น
มันพิสูจน์ว่า request ไหลลง pipe คำตอบกลับมา และ id ตรงกัน ถ้า notification
ชื่อ `initialized` หายไป บรรทัดนี้ก็ยังจะผ่านเมื่อทดสอบกับ mock ที่ประพฤติดีของเรา
แต่จะค้างเมื่อทดสอบกับ server จริง ซึ่งเป็นเหตุผลว่าทำไมหัวข้อ 5 จึงมีอยู่ในฐานะ
ร้อยแก้วแทนที่จะเป็น check

**สอง tool ถูกค้นพบตอน run time** สามชื่อที่ไม่ปรากฏที่ไหนเลยใน repository นี้
นอกจาก `mock_mcp_server.py` และมาถึงในฐานะข้อมูลไม่ใช่โค้ด นั่นคือประโยค
ที่บทเรียนทั้งบทนี้พูดถึง

**สาม tool ที่ค้นพบมาถูกรันและคำตอบกลับมา** ดูให้ดีว่าคำกล่าวอ้างนี้ถูกทำอย่างไร

```python
        schemas, functions = mcp_schemas(client, prefix=client.server_name)
        tools.register_mcp(schemas, functions)

        name = f"{client.server_name}.echo"
        answer = tools.run(name, {"text": "across a pipe"})
```

มันเรียก **`tools.run`** ไม่ใช่ `client.call_tool` นั่นเป็นความจงใจและเป็นคำกล่าวอ้าง
ที่แข็งแรงที่สุดในไฟล์ มันพิสูจน์ว่าการลงทะเบียนใช้ได้ ว่าชื่อที่มี prefix อยู่ใน `FUNCTIONS`
ว่า closure ผูกชื่อ tool ถูกตัว และว่าเส้นทาง dispatch ปกติที่ agent loop ใช้
ไปถึงฟังก์ชันในอีก process ได้โดยไม่รู้ตัวว่ามันทำแบบนั้น การเรียก client ตรง ๆ
จะพิสูจน์แค่ว่า client ทำงานได้ และไม่พิสูจน์อะไรเลยเกี่ยวกับการผสานรวม

**สี่ tool ที่ล้มเหลวกลายเป็นข้อความที่อ่านได้** `explode` รัน server ตั้ง `isError`
และสิ่งที่กลับมาขึ้นต้นด้วย `Error` ไม่ใช่ exception ไม่ใช่ traceback แต่เป็นสตริง
ที่ model อ่านและตอบสนองได้ เหมือนบทที่ 07 เป๊ะ

**ห้า ต้นทุนคือตัวเลขที่คุณมองเห็นได้** หัวข้อ 8 ในหนึ่งบรรทัด และมันจะล้มเหลว
ถ้าการเชื่อม server ไม่ทำให้ขนาด schema เปลี่ยนเลย ซึ่งจะแปลว่า `register_mcp`
ไม่ได้ทำอะไรเลยแบบเงียบ ๆ

หรือรันทุกบทเรียนพร้อมกัน แบบที่ CI ทำ

```bash
python ci/run_lessons.py
```

ถ้าบรรทัดแรกล้มเหลวและการรันค้างแทนที่จะขึ้น error แปลว่า handshake ไม่เสร็จ
และที่ที่ควรไปดูคือ notification ชื่อ `initialized` ถ้ามันล้มเหลวโดย server ปิดตัว
แปลว่าคำสั่งผิดหรือ server crash ตอนเริ่ม และวิธีที่เร็วที่สุดในการดูสาเหตุคือเปลี่ยน
`stderr=subprocess.DEVNULL` เป็น `stderr=None` ชั่วคราว เพื่อให้ error output
ของ server เองมาถึง terminal ของคุณ ถ้าข้อสามล้มเหลวโดยบอกว่าไม่รู้จัก tool
แปลว่า prefix ใน `mcp_schemas` กับ prefix ในชื่อที่คุณเรียกไม่ตรงกันแล้ว

## 11. สิ่งที่คุณยังทำไม่ได้

ตอนนี้ agent ใช้ tool ที่คุณไม่ได้เขียนได้แล้ว และไม่มีขีดจำกัดว่าจะกี่ตัว นั่นคือ
การก้าวกระโดดด้านความสามารถของจริง และมันใช้แค่สิบเจ็ดบรรทัดใน `tools.py`

มันไม่ได้เปลี่ยนอะไรเลยเกี่ยวกับวิธีที่ agent ทำงาน

ทุกอย่างยังเกิดขึ้นในบทสนทนาเดียว ลิสต์ข้อความเดียว context window เดียว
model เดียว กระแสความคิดเดียว งานของคุณ system prompt ทุกไฟล์ที่มันอ่าน
ผลลัพธ์ของ tool ทุกอัน ทางตันทุกทาง ทั้งหมดอยู่ในลิสต์เดียวกัน และโตขึ้นเรื่อย ๆ

บทที่ 14 ทำให้เรื่องนี้พออยู่รอดได้ ไม่ใช่แก้ได้ และบทนี้ก็แอบทำให้มันแย่ลงในสองทาง
schema จากหัวข้อ 8 คือภาษีคงที่ในทุก request ที่การตัดทิ้งแตะไม่ได้ และ tool
จากหัวข้อ 7 คือแหล่งใหม่ของผลลัพธ์ tool ขนาดใหญ่ เพราะการ query ฐานข้อมูล
หรือการดึงหน้าเว็บคืนข้อความมามากกว่าที่ `read_file` คืนจากไฟล์ source มาก

ดูสิว่าเกิดอะไรขึ้นในงานที่ใหญ่จริง บทสนทนาเต็ม `fit_to_budget` ทิ้งบล็อกที่เก่าที่สุด
ซึ่งบรรจุคำสั่งดั้งเดิมของคุณและเหตุผลที่ agent เลือกวิธีที่มันทำมาแล้วสามในสี่ส่วน
ไม่มี error เพราะการตัดทิ้งทำงานตรงตามที่ออกแบบไว้เป๊ะ agent แค่ค่อย ๆ โง่ลง
เรื่อย ๆ ตามการรัน ลืมส่วนที่สำคัญที่สุดของการให้เหตุผลของตัวเอง และอาการเดียว
คืองานที่ออกมาแย่ลง

หน้าต่างที่ใหญ่ขึ้นไม่ได้แก้เรื่องนี้ และการตัดทิ้งที่ดีขึ้นก็ไม่แก้ เพราะทั้งสองเป็นคำตอบ
ของคำถามที่ผิด ปัญหาคือบทสนทนาเดียวกำลังถูกขอให้แบกงานที่ไม่พอดีกับบทสนทนาเดียว

**นั่นคือบทที่ 20** subagent agent ที่สตาร์ต agent อีกตัวที่มี context สดของตัวเองได้
ยื่นงานแคบ ๆ ชิ้นเดียวให้มัน แล้วรับคำตอบสั้น ๆ กลับมาแทนที่จะเป็นบทสนทนา
สี่สิบข้อความ บทสนทนาของ parent โตขึ้นหนึ่งย่อหน้า แทนที่จะโตขึ้นเท่ากับทุกอย่าง
ที่ child ต้องอ่านเพื่อเขียนย่อหน้านั้น บทนั้นยังมาพร้อมกับ failure mode ที่คุณได้ฟรี
ซึ่งก็คือ parent กับ child ตอนนี้เห็นโลกคนละเวอร์ชัน และ isolation ที่ทำให้ child
คมชัดก็คือสิ่งที่ทำให้เรื่องนั้นแย่ลงพอดี

ก่อนไปต่อ ลองเชื่อม MCP server ตัวจริงเข้ากับ client ตัวนี้ server สำหรับระบบไฟล์
หรืออะไรก็ได้ที่รันผ่าน stdio ก็ใช้ได้ แล้วทำสองอย่าง พิมพ์รายการ tool ออกมา
แล้วอ่านคำอธิบายราวกับว่าคุณคือ model ที่ต้องเลือกระหว่างมันกับ tool แปดตัวของคุณเอง
และรันการวัดขนาด schema ของ `check.py` กับมัน เพื่อให้ตัวเลขในหัวข้อ 8
เลิกเป็นข้อโต้แย้งในบทเรียน และกลายเป็นตัวเลขที่คุณเห็นบนเครื่องของคุณเอง

ไปต่อที่บทที่ 20
