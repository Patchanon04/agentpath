# บทที่ 14 MCP คือการยืม tool ที่คนอื่นเขียน

คุณส่ง `tools/list` ไปแล้วไม่มีอะไรกลับมา process (โปรแกรมที่กำลังทำงานอยู่หนึ่งตัว) ยังอ
ยู่ ท่อยังเปิด ไม่มี error สักบรรทัดคุณไล่ดู buffer ไล่ดูว่าท่อตันไหม ไล่ดูว่า server ตาย
หรือเปล่า สาเหตุคือข้อความสามคำที่คุณไม่ได้ส่ง และไม่มีอะไรในโลกชี้ไปที่มัน

บทนี้คือ client (ฝั่งที่เป็นคนเรียก) ที่ต่อกับ server ตัวไหนก็ได้ที่พูด
โปรโตคอลนี้ แล้วเอา tool (ฟังก์ชันที่ model ขอให้เรารันได้) ของเขามาใส่
agent (โปรแกรมที่ให้ model ตัดสินใจแล้วรัน tool ให้) ของคุณโดยไม่ต้องแก้
agent loop สักบรรทัด ข้อความสามคำนั้นอยู่ในหัวข้อที่ 2 และท้ายบทมีตัวเลขราคาของการต่อ
server หนึ่งตัว วัดจากโค้ดจริง ไม่ใช่จากความรู้สึก

## 1. MCP คืออะไร ในย่อหน้าเดียว

MCP (Model Context Protocol คือโปรโตคอลที่ให้ agent ใช้ tool ที่คนอื่นเขียนได้) คือข้อตกล
งว่าโปรแกรมสองตัวจะคุยกันยังไงเรื่อง tool ฝั่งที่ให้บริการเรียกว่า server และมันรันเป็นคน
ละ process กับ agent ของคุณ server บอกได้ว่าตัวเองทำอะไรได้บ้าง และทำสิ่งนั้นเมื่อถูกข
อ แค่นั้น ที่มันสำคัญเพราะมันเปลี่ยน server ทุกตัวในโลกให้กลายเป็น tool ที่ agent ของคุณ
เรียกได้ โดยที่คุณไม่ต้องเขียนสักตัว

โปรเจกต์นี้เขียน client เองแทนที่จะใช้ library ที่มีคนทำไว้ ด้วยเหตุผลเดียวกับที่บทที่ 1
ยิง HTTP เอง ส่วนของโปรโตคอลที่ agent ต้องใช้จริงมีสามอย่าง คือ `initialize`
`tools/list` และ `tools/call` ซึ่งเป็น JSON-RPC (เรียก function ข้าม process โดยส่งกันเป็น JSON) บ
นท่อ `src/agentpath/mcp.py` ทั้งไฟล์ยาว 217 บรรทัด รวมคอมเมนต์และ docstring

ข้อจำกัดสองข้อถูกเขียนไว้แทนที่จะถูกซ่อน

```text
Two limits are stated rather than hidden. This client speaks the stdio
transport only, so a server reachable over HTTP will not work. And every
tool it discovers is marked as not safe, because we did not write those
tools and cannot know what they do.
```

ข้อแรกคือขอบเขตของงาน ข้อสองคือเรื่องความปลอดภัยที่หัวข้อที่ 5 จะขยาย

## 2. handshake ที่มีสองจังหวะ และจังหวะที่สองคือจังหวะที่คนลืม

การเชื่อมต่อไม่ได้เริ่มด้วยการถามว่ามี tool อะไรบ้าง มันเริ่มด้วยการทักทายที่มีสองจังหวะ
และทั้งสองต้องครบ

จังหวะแรกคือส่ง `initialize` พร้อมบอกว่าเราพูดโปรโตคอลรุ่นไหนและเราเป็นใคร
แล้วอ่านคำตอบที่มีชื่อและความสามารถของ server อยู่ในนั้น จังหวะที่สองคือส่ง
`notifications/initialized` ซึ่งเป็นข้อความที่ไม่มี id และไม่ต้องการคำตอบ มันแค่บอกว่า
ฝั่งเราพร้อมแล้ว

จังหวะที่สองคือจังหวะที่ทุกคนลืม และผลของการลืมคืออาการที่เปิดบท

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

การลืมดูเหมือนโปรแกรมค้าง เพราะ server ที่ยังไม่ได้รับข้อความนั้นไม่ได้ตอบว่าผิด มันไม่
ตอบเลย คำขอ `tools/list` ที่ตามมาจึงนั่งรออยู่จนหมดเวลา ความผิดพลาดที่ประกาศตัวเองแก้ได้
ในนาทีเดียว ความผิดพลาดที่เงียบกินไปครึ่งวัน

ข้อความนั้นไม่มี id เพราะใน JSON-RPC ข้อความที่ไม่มี id คือ notification (ข้อความที่ไม่ต้
องการคำตอบ) การใส่ id ให้มันแปลว่าเรากำลังรอคำตอบที่จะไม่มีวันมา ซึ่งเป็นวิธีทำให้ค้างอีก
วิธีหนึ่ง

```python
    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})
```

`stderr` ถูกโยนทิ้งเพราะ server จำนวนมากพิมพ์ log ลง stderr และถ้าไม่มีใครอ่าน ท่อจะเต็ม
แล้ว server จะค้าง การทิ้งไปที่ `DEVNULL` คือทางที่ง่ายที่สุดที่ไม่พัง ราคาคือคุณมองไม่เห็น
log ของ server ตอน debug ซึ่งเป็นการแลกที่ควรรู้ตัวว่ากำลังแลกครับ

## 3. อ่านจนกว่า id จะตรง ไม่ใช่อ่านบรรทัดถัดไป

จุดที่โค้ด client ที่เขียนเร็วๆ มักผิดคือการสมมติว่าบรรทัดถัดไปที่กลับมาคือคำตอบของ
คำถามที่เพิ่งถาม

มันไม่จริง server ส่ง notification และ log ออกมาเมื่อไหร่ก็ได้ตามใจ บรรทัดถัดไปจึงอาจ
เป็นอะไรก็ได้ วิธีที่ถูกคือวนอ่านไปเรื่อยๆ แล้วทิ้งทุกอย่างที่ `id` ไม่ตรงกับที่เราส่งไป

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

ใน loop นี้มีการแยกกรณีสี่แบบที่หน้าตาคล้ายกันแต่คนละเรื่อง และมันคุ้มที่จะแยกให้ออก
บรรทัดที่เป็น `None` แปลว่ายังไม่มีอะไรมา ให้ไปดูนาฬิกาแล้ววนต่อ บรรทัดว่างเปล่าจริง
แปลว่าท่อถูกปิด ซึ่งคือ server ตาย ต้องโยน error บรรทัดที่แกะ JSON ไม่ออกคือขยะที่
server พิมพ์ออกมา ให้ข้าม ส่วนบรรทัดที่ id ไม่ตรงคือข้อความของคนอื่น ให้ข้ามเหมือนกัน

`_lock` อยู่ตรงนั้นเพราะสองสายการทำงานที่ยิงคำขอพร้อมกันบนท่อเดียวจะสลับกันอ่านคำตอบ
ของกันและกัน กุญแจตัวนี้ทำให้หนึ่งคำถามหนึ่งคำตอบเสร็จเป็นคู่ก่อนที่คู่ถัดไปจะเริ่ม

การอ่านต้องมีเส้นตายเพราะการอ่านจากท่อไม่มี timeout ในตัวที่ทำงานเหมือนกันทั้งสองระบบ
ปฏิบัติการ ตอนที่ยังไม่มีเส้นตาย server ตัวเดียวที่ค้างทำให้ทั้งการรันค้างตาม และปุ่มหยุด
ช่วยอะไรไม่ได้เพราะการอ่านไม่เคยกลับมาเช็คธง วิธีของโปรเจกต์นี้คือให้การอ่านหนึ่งบรรทัด
ไปเกิดใน thread สั้นๆ แล้วให้คนเรียกรอโดยดูนาฬิกาแทน

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

`call_tool` แยกความล้มเหลวสองชนิดออกจากกัน และเส้นนี้เป็นเส้นเดียวกับที่บทที่ 6 ลากไว้

tool ที่ทำงานแล้วไม่สำเร็จ ไม่ใช่ exception มันคือข้อมูลที่ model ควรอ่านแล้วตัดสินใจต่อ
ส่วน server ที่พัง คือปัญหาของโปรแกรมเรา ไม่ใช่ของ model แต่ก็ยังถูกส่งกลับให้ model
เป็นข้อความเหมือนกัน ด้วยเหตุผลคนละข้อ

```python
    def call_tool(self, name, arguments):
        """Run one tool and return its output as text.

        A tool that fails is not an exception here. The server reports it
        with isError and the failure is something the model should read and
        respond to, exactly like the tool errors from lesson 07. A broken
        server comes back as text too, so that one dead server does not end
        the whole turn.
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

ถึง server จะพัง ฟังก์ชันนี้ก็ยังคืนสตริงกลับไปให้ model อ่าน ไม่ได้โยน exception ขึ้นไป
เพราะการที่ server ตัวหนึ่งตายไม่ควรทำให้งานทั้งงานตายตาม model ที่อ่านว่า server ล่ม
สามารถเลือกทางอื่นได้

## 5. tool ที่ค้นพบตอนรัน ต้องถือว่าไม่ปลอดภัยเสมอ

`Tool` ในโปรเจกต์นี้มี field ชื่อ `safe` ที่บอกว่ารันได้เลยโดยไม่ต้องถามคนหรือไม่ สำหรับ
tool ที่เราเขียนเอง เราตอบคำถามนั้นได้ เพราะเราอ่านโค้ดของมัน

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

โค้ดไม่ยอมเชื่อคำอธิบายของ server เพราะคำอธิบายคือข้อความที่คนเขียน server เป็นคนพิมพ์
มันไม่ใช่หลักฐาน tool ที่บอกว่าตัวเองอ่านไฟล์อย่างเดียวอาจลบไฟล์ก็ได้ และไม่มีอะไรใน
โปรโตคอลที่ตรวจสอบเรื่องนี้ให้ นี่คือกฎจากบทที่ 5 ที่ว่าทุกอย่างที่เข้ามาคือข้อมูลที่ไม่น่า
เชื่อถือ ขยายมาถึงคำอธิบายของ tool ด้วย

มีอันตรายอีกชั้นที่ลึกกว่านั้น ผลลัพธ์ที่ server คืนกลับมาจะกลายเป็นข้อความในบทสนทนาของ
agent คุณ ซึ่งแปลว่าคนที่เขียน server เขียนข้อความลงในบทสนทนาของคุณได้โดยตรง ข้อความ
นั้นสั่งงาน model ได้เหมือนที่ข้อความจากผู้ใช้สั่งได้ นี่คือเหตุผลที่ประตูอนุญาตต้องอยู่
ระหว่างคำขอกับการรัน ไม่ใช่อยู่ที่ตัว tool

ปัญหาที่เล็กกว่าแต่เจอบ่อยกว่าคือชื่อชนกัน server สองตัวมีสิทธิ์เรียก tool ของตัวเองว่า
`search` เท่ากัน และ registry เก็บด้วย dict ที่ key คือชื่อ

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

คำที่ควรจำคือ silently ในคอมเมนต์ การที่ tool ตัวหนึ่งหายไปจาก registry ไม่มี error ให้
เห็น model จะเรียก `search` แล้วได้ของอีกเจ้าหนึ่งที่หน้าตาคล้ายกันแต่ทำคนละอย่าง

## 6. ราคาที่ไม่มีใครบอก คือ schema ที่กินงบก่อนเริ่มงาน

หัวข้อนี้คือตัวเลข ไม่ใช่ความเห็น

จากบทที่ 1 เรารู้ว่าทุกคำขอส่งบทสนทนาทั้งก้อนไปใหม่ สิ่งที่คนมักลืมคือรายการ tool ก็ถูก
ส่งไปใหม่ทุกครั้งเหมือนกัน มันไม่ได้ส่งครั้งเดียวตอนเริ่ม และ server ไม่ได้จำมันไว้ให้
แปลว่า schema (บอกรูปร่างของข้อมูลด้วย JSON) ของ tool ทุกตัวคือค่าใช้จ่าย
คงที่ที่จ่ายทุกรอบ ก่อนที่ model จะได้อ่านคำสั่งของคุณสักคำ

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

ตัวเลขแรกมาจาก `build_tools` ใน `src/agentpath/cli.py` ซึ่งคือ tool
แปดตัวที่เราเขียนเอง เรียก `schema_size()` แล้วได้ 2847 ตัวอักษร ราคานี้จ่ายก่อนต่อ server ตัวไหนเลย

ตัวเลขที่สองมาจากบทเรียนที่ 19 ซึ่ง `check.py` วัดก่อนและหลังต่อ server ทดสอบตัวเล็กที่สุด
เท่าที่จะเขียนได้ คือมี tool สามตัว คำอธิบายตัวละหนึ่งประโยค และ schema ที่ใหญ่ที่สุดมี
สอง property

```text
OK the schemas grew from 3101 to 3826 characters, 725 more on every request from one small server
```

เลขตั้งต้นสองอันไม่เท่ากัน ทั้งที่เป็น tool แปดตัวเดียวกัน เพราะบทเรียนที่ 19 เก็บ schema ใน
รูปแบบของ OpenAI คือห่อแต่ละตัวไว้ใน `{"type": "function", "function": {...}}` ส่วน
`ToolRegistry` ในโค้ดหลักเก็บ schema เปล่าๆ แล้วให้ provider เป็นคนห่อตอนส่ง ปลอกหุ้มนั้น
กินตัวละราวสามสิบตัวอักษร คูณแปดตัวได้ราวสองร้อยห้าสิบ ซึ่งใกล้กับ 254 ที่เป็นระยะห่าง
ระหว่าง 2847 กับ 3101
บทเรียนที่ควรจำไม่ใช่ตัวเลขไหนถูก แต่คือเวลาเทียบตัวเลขสองอัน ให้ดูก่อนว่ามันวัดของรูป
แบบเดียวกันหรือเปล่า

ส่วนเจ็ดร้อยยี่สิบห้าคือสิ่งที่ server จิ๋วตัวเดียวเพิ่มเข้ามา ตกประมาณสองร้อยสี่สิบสอง
ตัวอักษรต่อ tool หนึ่งตัว จาก server ที่เล็กที่สุดที่เป็นไปได้

ทีนี้ลองคูณด้วยของจริง server จริงมีคำอธิบายที่ยาวกว่านั้นมาก เพราะมันต้องบอกให้ model
แยกออกจาก tool อีกสิบเอ็ดตัวที่คล้ายกัน และ schema ของมันมีสิบถึงสิบห้า property ที่แต่
ละตัวมีคำอธิบายของตัวเอง สมมติต่อ server สิบตัว ตัวละแปด tool ซึ่งไม่ใช่ตัวเลขสุดโต่งเลย

| ขนาดต่อ tool | 80 tool คิดเป็น | ประมาณเป็น token |
| --- | --- | --- |
| 242 ตัวอักษร แบบ server ของเล่น | 19,360 ตัวอักษร | ราว 4,800 |
| 800 ตัวอักษร แบบ server จริง | 64,000 ตัวอักษร | ราว 16,000 |
| 1,500 ตัวอักษร แบบ server ใหญ่ | 120,000 ตัวอักษร | ราว 30,000 |

ช่อง token ใช้ค่า `CHARACTERS_PER_TOKEN` เท่ากับสี่ จาก `context.py` ซึ่งเป็นตัวประมาณ
หยาบตัวเดียวกับที่บทที่ 4 ใช้ตัดสินใจว่าจะตัดหรือยัง

เอาแถวกลางไปเทียบกับงบเริ่มต้นของ CLI ซึ่งคือหนึ่งแสน จะได้ว่าหกสิบสี่พันตัวอักษร คือ
ประมาณหนึ่งหมื่นหกพัน token หายไปตั้งแต่ก่อน system prompt ก่อนงานของคุณ และก่อนที่
agent จะอ่านไฟล์แรก แล้วมันหายอีกรอบในคำขอถัดไป และรอบถัดไป การรันยี่สิบรอบจ่ายค่านี้
ยี่สิบครั้ง

ผลที่ตามมาแย่กว่าตัวเลข เมื่องบเต็ม สิ่งที่ `fit_to_budget` ตัดทิ้งคือ block เก่าที่สุด ซึ่ง
คือคำสั่งเดิมของคุณ ส่วน schema ไม่ได้อยู่ในรายการที่ตัดได้ ผลสุทธิคือรายการ tool ที่อ้วน
ไปดัน task ของคุณออกจากหน้าต่าง **คุณจ่าย token เพื่อทำให้ agent ลืมว่ากำลังทำอะไรอยู่**

ราคาที่ไม่ได้เป็น token ยังมีอีกข้อ และมันอยู่ต่อไปแม้ context window จะใหญ่ขึ้นจนไม่มีใคร
นับตัวอักษรแล้ว model ที่ต้องเลือกจาก tool แปดสิบตัวที่ชื่อคล้ายกัน จะเลือกผิดบ่อยขึ้น
server สามเจ้ามี tool ที่ทำเรื่องค้นหาเหมือนกัน คำอธิบายก็พูดคล้ายกัน model ต้องเลือกจาก
คำอธิบายอย่างเดียวโดยไม่มีสิทธิ์ลองก่อน มันเลือกตัวที่ดูสมเหตุสมผลแต่ผิด ได้ผลลัพธ์ที่ไม่มี
ประโยชน์แต่ก็ไม่ใช่ error แล้วคิดต่อจากนั้น ความล้มเหลวแบบนี้ไม่มี exception ไม่มี log
และไม่มีอาการ มันดูเหมือน agent วันนี้โง่ลงเฉยๆ

วินัยที่ตามมาจึงง่ายแต่ไม่มีใครชอบ คือต่อเฉพาะ server ที่งานนี้ต้องใช้

## 7. ปิดของที่เปิดไว้

เรื่องสุดท้ายสั้นแต่ลืมกันบ่อย server คือ process แยก มันไม่ตายเองเมื่อคำสั่งของเราจบ

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

ประโยคสุดท้ายของ docstring คือสิ่งที่ทำให้เรื่องนี้ไม่ใช่เรื่องเล็ก คนที่รัน agent สี่สิบครั้ง
จะมี process ค้างอยู่สี่สิบตัว และเขาจะไม่รู้ตัวจนกว่าเครื่องจะช้าลงโดยไม่มีเหตุผล นี่คือ
กฎเดิมจากบทที่ 6 ในรูปแบบใหม่ ทุกอย่างที่คุณเปิด ต้องมีโค้ดที่ปิดมัน และโค้ดนั้นต้องทำงาน
แม้ตอนที่มีอะไรพังครับ

## บทเรียนที่ลงมือทำเรื่องนี้

| บทเรียน | สิ่งที่ได้ลงมือทำ |
| --- | --- |
| 19 mcp client | เขียน client ด้วยมือ ต่อกับ server ทดสอบในโปรเจกต์ และวัด schema ที่โตขึ้นด้วยตัวเลขจริง |
| 12 permissions | เห็นว่าทำไม tool ที่มาจากที่อื่นต้องผ่านประตูอนุญาตตัวเดียวกับ tool ของเรา |
| 15 token economy | เห็นว่าค่าใช้จ่ายคงที่ต่อรอบมีผลต่อบิลมากแค่ไหนเมื่อคูณด้วยจำนวนรอบ |
| 03 tool calling | เข้าใจว่า schema คือสิ่งที่ model อ่าน ก่อนจะมาเจอว่ามันคือของที่ต้องจ่ายทุกรอบ |
