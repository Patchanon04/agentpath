# บทที่ 14 MCP คือการยืม tool ที่คนอื่นเขียน

จบบทนี้คุณจะมี client (ไคลเอนต์ คือฝั่งที่เป็นคนเรียก) ที่ต่อกับ server
ตัวไหนก็ได้ในโลกที่พูดโปรโตคอลนี้ แล้วเอา tool (เครื่องมือ คือฟังก์ชันที่
model ขอให้เรารันได้) ของเขามาใส่ agent (เอเจนต์ คือโปรแกรมที่ให้ model
ตัดสินใจแล้วรัน tool ให้) ของคุณโดยไม่ต้องแก้ agent loop สักบรรทัด และคุณ
จะรู้ราคาที่ต้องจ่ายเป็นตัวเลข ไม่ใช่เป็นความรู้สึก

## 1. MCP คืออะไร ในย่อหน้าเดียว

MCP (Model Context Protocol คือโปรโตคอลสำหรับให้ agent ใช้ tool ที่คนอื่น
เขียน) คือข้อตกลงว่าโปรแกรมสองตัวจะคุยกันยังไงเรื่อง tool ฝั่งที่ให้บริการ
เรียกว่า server และมันรันเป็นคนละ process (โพรเซส คือโปรแกรมที่กำลังทำงาน
อยู่หนึ่งตัว) กับ agent ของคุณ server บอกได้ว่าตัวเองทำอะไรได้บ้าง และ
ทำให้เมื่อถูกขอ นั่นคือทั้งหมด ที่มันสำคัญเพราะมันเปลี่ยน server ทุกตัวใน
โลกให้กลายเป็น tool ที่ agent ของคุณเรียกได้ โดยที่คุณไม่ต้องเขียนสักตัว

โปรเจกต์นี้เขียน client เองแทนที่จะใช้ library ที่มีคนทำไว้ ด้วยเหตุผล
เดียวกับที่บทที่ 1 ยิง HTTP เอง คือส่วนของโปรโตคอลที่ agent ต้องใช้จริงมี
สามอย่าง คือ `initialize` `tools/list` และ `tools/call` ซึ่งเป็น JSON-RPC
(เจสันอาร์พีซี คือรูปแบบการเรียกฟังก์ชันข้ามโปรแกรมด้วย JSON) บนท่อ และ
มันยาวไม่ถึงสองร้อยบรรทัด

และข้อจำกัดสองข้อถูกเขียนไว้แทนที่จะถูกซ่อน

```text
Two limits are stated rather than hidden. This client speaks the stdio
transport only, so a server reachable over HTTP will not work. And every
tool it discovers is marked as not safe, because we did not write those
tools and cannot know what they do.
```

ข้อแรกคือขอบเขตของงาน ข้อสองคือเรื่องความปลอดภัยที่หัวข้อที่ 5 จะขยาย

## 2. handshake ที่มีสามจังหวะ และจังหวะที่สามคือจังหวะที่คนลืม

การเชื่อมต่อไม่ได้เริ่มด้วยการถามว่ามี tool อะไรบ้าง มันเริ่มด้วยการทักทาย
ที่มีสามจังหวะ และทั้งสามต้องครบ

จังหวะแรกคือส่ง `initialize` พร้อมบอกว่าเราพูดโปรโตคอลรุ่นไหนและเราเป็นใคร
จังหวะที่สองคืออ่านคำตอบ ซึ่งมีชื่อและความสามารถของ server อยู่ในนั้น
จังหวะที่สามคือส่ง `notifications/initialized` ซึ่งเป็นข้อความที่ไม่มี id
และไม่ต้องการคำตอบ มันแค่บอกว่าฝั่งเราพร้อมแล้ว

จังหวะที่สามคือจังหวะที่ทุกคนลืม และผลของการลืมคืออาการที่หลอกที่สุด

```python
    def connect(self):
        """Start the server and complete the handshake.

        The handshake has two steps that both matter. We ask to initialize
        and read the answer, then we send an initialized notification with
        no id. Many servers refuse to do anything until that second message
        arrives, and forgetting it produces a server that simply never
        answers, which looks like a hang rather than a mistake.
        """
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
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
        return self
```

**ทำไมการลืมถึงดูเหมือนโปรแกรมค้าง** เพราะ server ที่ยังไม่ได้รับข้อความนั้น
ไม่ได้ตอบว่าผิด มันไม่ตอบเลย คำขอ `tools/list` ที่ตามมาจึงนั่งรออยู่จนหมด
เวลา คนที่เจออาการนี้จะไปไล่ดูเรื่อง buffer ไล่ดูว่าท่อตันไหม ไล่ดูว่า
process ตายหรือเปล่า โดยไม่มีอะไรชี้ไปที่ข้อความสามคำที่ไม่ได้ส่ง

**ทำไมข้อความนั้นถึงไม่มี id** เพราะใน JSON-RPC ข้อความที่ไม่มี id คือ
notification (การแจ้ง คือข้อความที่ไม่ต้องการคำตอบ) การใส่ id ให้มันแปลว่า
เรากำลังรอคำตอบที่จะไม่มีวันมา ซึ่งเป็นวิธีทำให้ค้างอีกวิธีหนึ่ง

```python
    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})
```

**ทำไม `stderr` ถูกโยนทิ้ง** เพราะ server จำนวนมากพิมพ์ log ลง stderr และ
ถ้าไม่มีใครอ่าน ท่อจะเต็มแล้ว server จะค้าง การทิ้งไปที่ `DEVNULL` คือ
ทางที่ง่ายที่สุดที่ไม่พัง ราคาคือคุณมองไม่เห็น log ของ server ตอน debug
ซึ่งเป็นการแลกที่ควรรู้ตัวว่ากำลังแลกครับ

## 3. อ่านจนกว่า id จะตรง ไม่ใช่อ่านบรรทัดถัดไป

จุดที่โค้ด client ที่เขียนเร็วๆ มักผิดคือการสมมติว่าบรรทัดถัดไปที่กลับมา
คือคำตอบของคำถามที่เพิ่งถาม

มันไม่จริง server ส่ง notification และ log ออกมาเมื่อไหร่ก็ได้ตามใจ บรรทัด
ถัดไปจึงอาจเป็นอะไรก็ได้ วิธีที่ถูกคือวนอ่านไปเรื่อยๆ แล้วทิ้งทุกอย่างที่
`id` ไม่ตรงกับที่เราส่งไป

```python
    def _request(self, method, params=None):
        """Send one request and read until the answer to it arrives.

        Reading until the id matches is not defensive programming. A server
        is allowed to send notifications and log messages at any moment, so
        the next line back is often not the answer to the question just
        asked. Taking the first line and hoping works until it does not.
        """
        with self._lock:
            self._next_id += 1
            identifier = self._next_id
            self._send(
                {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params or {}}
            )
            deadline = time.monotonic() + self.timeout
            while True:
                if time.monotonic() > deadline:
                    # A server that stops answering must not take the agent
                    # with it. Reading with no deadline meant one wedged
                    # server hung the whole run, and the interrupt key could
                    # not help because the read never came back to check it.
                    raise MCPError(
                        f"the server did not answer {method} within "
                        f"{self.timeout} seconds"
                    )
                line = _readline_with_deadline(self.process.stdout, deadline)
                if line is None:
                    continue
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
                if "error" in message:
                    raise MCPError(message["error"].get("message", "unknown server error"))
                return message.get("result") or {}
```

ใน loop นี้มีการแยกกรณีสี่แบบที่หน้าตาคล้ายกันแต่คนละเรื่อง และมันคุ้มที่จะ
แยกให้ออก บรรทัดที่เป็น `None` แปลว่ายังไม่มีอะไรมา ให้ไปดูนาฬิกาแล้ววนต่อ
บรรทัดว่างเปล่าจริงแปลว่าท่อถูกปิด ซึ่งคือ server ตาย ต้องโยน error
บรรทัดที่แกะ JSON ไม่ออกคือขยะที่ server พิมพ์ออกมา ให้ข้าม ส่วนบรรทัดที่
id ไม่ตรงคือข้อความของคนอื่น ให้ข้ามเหมือนกัน

**ทำไมต้องมี `_lock`** เพราะสองสายการทำงานที่ยิงคำขอพร้อมกันบนท่อเดียวจะ
สลับกันอ่านคำตอบของกันและกัน กุญแจตัวนี้ทำให้หนึ่งคำถามหนึ่งคำตอบเสร็จเป็น
คู่ก่อนที่คู่ถัดไปจะเริ่ม

**ทำไมการอ่านต้องมีเส้นตาย** เพราะการอ่านจากท่อไม่มี timeout ในตัวที่ทำงาน
เหมือนกันทั้งสองระบบปฏิบัติการ ตอนที่ยังไม่มีเส้นตาย server ตัวเดียวที่ค้าง
ทำให้ทั้งการรันค้างตาม และปุ่มหยุดช่วยอะไรไม่ได้เพราะการอ่านไม่เคยกลับมา
เช็คธง วิธีของโปรเจกต์นี้คือให้การอ่านหนึ่งบรรทัดไปเกิดใน thread สั้นๆ
แล้วให้คนเรียกรอโดยดูนาฬิกาแทน

```python
def _readline_with_deadline(stream, deadline):
    """Read one line, giving up when the deadline passes.

    A pipe read has no timeout of its own on either operating system that
    works the same way, so the read happens on a short lived thread and
    the caller waits with a deadline instead. Returning None means
    nothing arrived yet and the caller should look at the clock again.
    """
    box = []
    reader = threading.Thread(target=lambda: box.append(stream.readline()), daemon=True)
    reader.start()
    reader.join(max(0.05, min(1.0, deadline - time.monotonic())))
    return box[0] if box else None
```

## 4. tool ที่พังคนละเรื่องกับ server ที่พัง

`call_tool` แยกความล้มเหลวสองชนิดออกจากกัน และเส้นนี้เป็นเส้นเดียวกับที่
บทที่ 6 ลากไว้

tool ที่ทำงานแล้วไม่สำเร็จ ไม่ใช่ exception มันคือข้อมูลที่ model ควรอ่าน
แล้วตัดสินใจต่อ ส่วน server ที่พัง คือปัญหาของโปรแกรมเรา ไม่ใช่ของ model

```python
    def call_tool(self, name, arguments):
        """Run one tool and return its output as text.

        A tool that fails is not an exception here. The server reports it
        with isError and the failure is something the model should read and
        respond to, exactly like the tool errors from lesson 07. Only a
        broken server raises.
        """
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

สังเกตว่าถึง server จะพัง ฟังก์ชันนี้ก็ยังคืนสตริงกลับไปให้ model อ่าน
ไม่ได้โยน exception ขึ้นไป เพราะการที่ server ตัวหนึ่งตายไม่ควรทำให้งาน
ทั้งงานตายตาม model ที่อ่านว่า server ล่มสามารถเลือกทางอื่นได้

## 5. tool ที่ค้นพบตอนรัน ต้องถือว่าไม่ปลอดภัยเสมอ

`Tool` ในโปรเจกต์นี้มี field ชื่อ `safe` ที่บอกว่ารันได้เลยโดยไม่ต้องถามคน
หรือไม่ สำหรับ tool ที่เราเขียนเอง เราตอบคำถามนั้นได้ เพราะเราอ่านโค้ดของมัน

สำหรับ tool ของ MCP เราตอบไม่ได้ และคำตอบจึงถูกฝังไว้ตายตัว

```python
        tools.append(
            Tool(
                name=exposed,
                description=described.get("description", ""),
                parameters=described.get("inputSchema")
                or {"type": "object", "properties": {}},
                fn=make(name),
                # Never safe. We did not write this tool and the description
                # is whatever its author decided to claim.
                safe=False,
            )
        )
```

**ทำไมถึงไม่ยอมเชื่อคำอธิบายของ server** เพราะคำอธิบายคือข้อความที่คนเขียน
server เป็นคนพิมพ์ มันไม่ใช่หลักฐาน tool ที่บอกว่าตัวเองอ่านไฟล์อย่างเดียว
อาจลบไฟล์ก็ได้ และไม่มีอะไรในโปรโตคอลที่ตรวจสอบเรื่องนี้ให้ นี่คือกฎจาก
บทที่ 5 ที่ว่าทุกอย่างที่เข้ามาคือข้อมูลที่ไม่น่าเชื่อถือ ขยายมาถึงคำอธิบาย
ของ tool ด้วย

**และมีอันตรายอีกชั้นที่ลึกกว่านั้น** คือผลลัพธ์ที่ server คืนกลับมาจะกลาย
เป็นข้อความในบทสนทนาของ agent คุณ ซึ่งแปลว่าคนที่เขียน server เขียนข้อความ
ลงในบทสนทนาของคุณได้โดยตรง ข้อความนั้นสั่งงาน model ได้เหมือนที่ข้อความ
จากผู้ใช้สั่งได้ นี่คือเหตุผลที่ประตูอนุญาตต้องอยู่ระหว่างคำขอกับการรัน
ไม่ใช่อยู่ที่ตัว tool

ปัญหาที่เล็กกว่าแต่เจอบ่อยกว่าคือชื่อชนกัน server สองตัวมีสิทธิ์เรียก tool
ของตัวเองว่า `search` เท่ากัน และ registry เก็บด้วย dict ที่ key คือชื่อ

```text
    prefix exists because two servers can both offer a tool called search.
    Without it the second one silently replaces the first in the registry.
```

ทางแก้คือเติมชื่อ server ไว้ข้างหน้า ซึ่ง CLI ทำให้ตอนต่อ

```python
    prefix = client.server_name or f"mcp{index}"
    for tool in mcp_tools(client, prefix=prefix):
        registry.add(tool)
```

จุดที่ควรจำคือคำว่า silently ในคอมเมนต์ การที่ tool ตัวหนึ่งหายไปจาก
registry ไม่มี error ให้เห็น model จะเรียก `search` แล้วได้ของอีกเจ้าหนึ่ง
ที่หน้าตาคล้ายกันแต่ทำคนละอย่าง

## 6. ราคาที่ไม่มีใครบอก คือ schema ที่กินงบก่อนเริ่มงาน

หัวข้อนี้คือตัวเลข ไม่ใช่ความเห็น

จากบทที่ 1 เรารู้ว่าทุกคำขอส่งบทสนทนาทั้งก้อนไปใหม่ สิ่งที่คนมักลืมคือ
รายการ tool ก็ถูกส่งไปใหม่ทุกครั้งเหมือนกัน มันไม่ได้ส่งครั้งเดียวตอนเริ่ม
และ server ไม่ได้จำมันไว้ให้ แปลว่า schema (สคีมา คือคำอธิบายรูปร่างของ
ข้อมูลในรูป JSON) ของ tool ทุกตัวคือค่าใช้จ่ายคงที่ที่จ่ายทุกรอบ ก่อนที่
model จะได้อ่านคำสั่งของคุณสักคำ

`ToolRegistry` มีเมธอดที่วัดตัวเลขนี้ให้ดูตรงๆ

```python
    def schema_size(self) -> int:
        """How many characters of tool description travel on every request.

        This is the fixed cost of having tools at all. It is paid on the
        first request and on every request after it, before the model has
        read a word of the actual task. Connect a handful of MCP servers and
        this number can eat a large share of the context window on its own,
        which is why it is worth being able to see it.
        """
        schemas = self.schemas()
        if not schemas:
            return 0
        return len(json.dumps(schemas))
```

และ CLI พิมพ์มันออกมาเมื่อสั่งให้พูดเยอะ

```python
    if getattr(arguments, "verbose", False):
        print(f"tool schemas cost {tools.schema_size()} characters on every request")
```

ตัวเลขจริงจากบทเรียน 19 วัดก่อนและหลังต่อ server ทดสอบตัวเล็กที่สุดเท่าที่
จะเขียนได้ คือมี tool สามตัว คำอธิบายตัวละหนึ่งประโยค และ schema ที่ใหญ่
ที่สุดมีสอง property

```text
OK the schemas grew from 3101 to 3826 characters, 725 more on every request from one small server
```

สามพันหนึ่งร้อยตัวอักษรคือ tool แปดตัวที่เราเขียนเองทั้งหมด เจ็ดร้อยยี่สิบห้า
คือสิ่งที่ server จิ๋วตัวเดียวเพิ่มเข้ามา ตกประมาณสองร้อยสี่สิบสองตัวอักษร
ต่อ tool หนึ่งตัว จาก server ที่เล็กที่สุดที่เป็นไปได้

ทีนี้ลองคูณด้วยของจริง server จริงมีคำอธิบายที่ยาวกว่านั้นมาก เพราะมันต้อง
บอกให้ model แยกออกจาก tool อีกสิบเอ็ดตัวที่คล้ายกัน และ schema ของมันมี
สิบถึงสิบห้า property ที่แต่ละตัวมีคำอธิบายของตัวเอง สมมติต่อ server สิบตัว
ตัวละแปด tool ซึ่งไม่ใช่ตัวเลขสุดโต่งเลย

| ขนาดต่อ tool | 80 tool คิดเป็น | ประมาณเป็น token |
| --- | --- | --- |
| 242 ตัวอักษร แบบ server ของเล่น | 19,360 ตัวอักษร | ราว 4,800 |
| 800 ตัวอักษร แบบ server จริง | 64,000 ตัวอักษร | ราว 16,000 |
| 1,500 ตัวอักษร แบบ server ใหญ่ | 120,000 ตัวอักษร | ราว 30,000 |

ช่อง token ใช้ค่า `CHARACTERS_PER_TOKEN` เท่ากับสี่ จาก `context.py` ซึ่ง
เป็นตัวประมาณหยาบตัวเดียวกับที่บทที่ 4 ใช้ตัดสินใจว่าจะตัดหรือยัง

เอาแถวกลางไปเทียบกับงบเริ่มต้นของ CLI ซึ่งคือหนึ่งแสน จะได้ว่าหกสิบสี่พัน
ตัวอักษร คือประมาณหนึ่งหมื่นหกพัน token หายไปตั้งแต่ก่อน system prompt
ก่อนงานของคุณ และก่อนที่ agent จะอ่านไฟล์แรก แล้วมันหายอีกรอบในคำขอถัดไป
และรอบถัดไป การรันยี่สิบรอบจ่ายค่านี้ยี่สิบครั้ง

**และผลที่ตามมาแย่กว่าตัวเลข** เพราะเมื่องบเต็ม สิ่งที่ `fit_to_budget`
ตัดทิ้งคือ block เก่าที่สุด ซึ่งคือคำสั่งเดิมของคุณ ส่วน schema ไม่ได้อยู่
ในรายการที่ตัดได้ ผลสุทธิคือรายการ tool ที่อ้วนไปดัน task ของคุณออกจาก
หน้าต่าง คุณจ่าย token เพื่อทำให้ agent ลืมว่ากำลังทำอะไรอยู่

**ราคาที่ไม่ได้เป็น token** ยังมีอีกข้อ และมันอยู่ต่อไปแม้ context window
จะใหญ่ขึ้นจนไม่มีใครนับตัวอักษรแล้ว คือ model ที่ต้องเลือกจาก tool หกสิบตัว
ที่ชื่อคล้ายกัน จะเลือกผิดบ่อยขึ้น server สามเจ้ามี tool ที่ทำเรื่องค้นหา
เหมือนกัน คำอธิบายก็พูดคล้ายกัน model ต้องเลือกจากคำอธิบายอย่างเดียวโดย
ไม่มีสิทธิ์ลองก่อน มันเลือกตัวที่ดูสมเหตุสมผลแต่ผิด ได้ผลลัพธ์ที่ไม่มี
ประโยชน์แต่ก็ไม่ใช่ error แล้วคิดต่อจากนั้น ความล้มเหลวแบบนี้ไม่มี
exception ไม่มี log และไม่มีอาการ มันดูเหมือน agent วันนี้โง่ลงเฉยๆ

วินัยที่ตามมาจึงง่ายแต่ไม่มีใครชอบ คือต่อเฉพาะ server ที่งานนี้ต้องใช้

## 7. ปิดของที่เปิดไว้

เรื่องสุดท้ายสั้นแต่ลืมกันบ่อย server คือ process แยก มันไม่ตายเองเมื่อ
คำสั่งของเราจบ

```python
def close_mcp_servers() -> None:
    """Shut down every MCP server this run started.

    They are separate processes. A server that does not happen to exit
    when its input closes will otherwise outlive the command that started
    it, and a person who runs the agent forty times has forty of them.
    """
    while OPEN_MCP_CLIENTS:
        try:
            OPEN_MCP_CLIENTS.pop().close()
        except Exception:
            pass
```

ประโยคสุดท้ายของ docstring คือสิ่งที่ทำให้เรื่องนี้ไม่ใช่เรื่องเล็ก คนที่
รัน agent สี่สิบครั้งจะมี process ค้างอยู่สี่สิบตัว และเขาจะไม่รู้ตัวจนกว่า
เครื่องจะช้าลงโดยไม่มีเหตุผล นี่คือกฎเดิมจากบทที่ 6 ในรูปแบบใหม่ คือทุก
อย่างที่คุณเปิด ต้องมีโค้ดที่ปิดมัน และโค้ดนั้นต้องทำงานแม้ตอนที่มีอะไรพัง

## บทเรียนที่ลงมือทำเรื่องนี้

| บทเรียน | สิ่งที่ได้ลงมือทำ |
| --- | --- |
| 19 mcp client | เขียน client ด้วยมือ ต่อกับ server ทดสอบในโปรเจกต์ และวัด schema ที่โตขึ้นด้วยตัวเลขจริง |
| 12 permissions | เห็นว่าทำไม tool ที่มาจากที่อื่นต้องผ่านประตูอนุญาตตัวเดียวกับ tool ของเรา |
| 15 token economy | เห็นว่าค่าใช้จ่ายคงที่ต่อรอบมีผลต่อบิลมากแค่ไหนเมื่อคูณด้วยจำนวนรอบ |
| 03 tool calling | เข้าใจว่า schema คือสิ่งที่ model อ่าน ก่อนจะมาเจอว่ามันคือของที่ต้องจ่ายทุกรอบ |
