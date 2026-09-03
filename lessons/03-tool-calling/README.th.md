[Read in English](README.md)

# บทที่ 03 Tool calling

นี่คือบทที่สำคัญที่สุดในภาคหนึ่ง ทุกอย่างก่อนหน้านี้เป็นเพียงงานเดินท่อ
เพื่อสร้างโปรแกรมแชท ส่วนทุกอย่างหลังจากนี้ล้วนต่อยอดจากแนวคิดเดียว
ในบทนี้

เมื่อจบบทนี้ คุณจะได้ส่งคำอธิบายของฟังก์ชันไปให้ model ได้เห็น model
ขอเรียกฟังก์ชันนั้นโดยระบุชื่อพร้อม arguments ที่ตัวมันเลือกเอง และได้รัน
ฟังก์ชันนั้นด้วยตัวคุณเองใน Python ประโยคสุดท้ายนั้นคือทั้งหมดของบทนี้
และคำว่า "ด้วยตัวคุณเอง" คือส่วนที่แทบทุกคนเข้าใจผิดในครั้งแรก

ไฟล์ในโฟลเดอร์นี้

```text
lessons/03-tool-calling/
  tools.py    two toy tools and the schemas that describe them
  llm.py      the API call, now sending tools and reading tool calls back
  check.py    a script that proves the whole thing works
  README.md   this file
```

## 1. ปัญหาที่ค้างมาจากบทที่ 02

ในบทที่ 02 คุณสร้าง chat loop ขึ้นมา คุณเก็บ list ของ messages ไว้ใน Python
คุณ append เทิร์นของผู้ใช้เข้าไป คุณส่งทั้ง list ไปให้ model แล้ว append
คำตอบกลับเข้าไป มันดูเหมือน model จำบทสนทนาได้ แต่มันจำไม่ได้
ภาพลวงตานั้นเกิดจากการที่คุณส่ง history ทั้งหมดใหม่ทุกครั้งที่เรียก

โปรแกรมนั้นมีเพดานที่ชัดเจน และเป็นเพดานที่ชนได้ง่ายมาก ลองถามแบบนี้ดู

```text
you> What is 48213 times 9917?
bot> 478,127,... (a confident number that is often wrong)
```

หรือลองถามสิ่งที่มันไม่มีทางรู้

```text
you> How many .py files are in this folder?
bot> I do not have access to your file system, so I cannot tell you.
```

คำตอบทั้งสองเผยให้เห็นข้อจำกัดเดียวกัน language model ผลิตข้อความ
นั่นคือ output ทั้งหมดของมัน มันอ่านไฟล์ไม่ได้ เปิด socket ไม่ได้
คำนวณการคูณด้วยเครื่องคิดเลขไม่ได้ และเช็ควันที่วันนี้ก็ไม่ได้
เวลาที่มันดูเหมือนทำเลขได้ จริง ๆ แล้วมันกำลังทำนายตัวอักษรที่มักจะตามหลัง
เครื่องหมายคูณ ซึ่งใช้ได้กับตัวเลขเล็ก ๆ และล้มเหลวเงียบ ๆ กับตัวเลขใหญ่

model จึงเป็นเครื่องผลิตข้อความที่เก่งมาก แต่ถูกขังอยู่ในกล่องที่ไม่มีมือ
โปรแกรมแชทอยู่กับสภาพนี้ได้ แต่ agent อยู่ไม่ได้ agent คือโปรแกรมที่ลงมือ
ทำสิ่งต่าง ๆ ในโลกจริง และการลงมือทำต้องมีมือ

ไอเดียที่ผุดขึ้นมาทันทีคือให้ model เข้าถึงคอมพิวเตอร์ของคุณ ไอเดียนั้นทั้งเป็นไปไม่ได้
และไม่ควรทำ เป็นไปไม่ได้เพราะ model รันอยู่บนฮาร์ดแวร์ของคนอื่นหลัง HTTP endpoint
(URL ที่เรายิง request ไปหา) และไม่มีเส้นทางมาถึงดิสก์ของคุณ
ไม่ควรทำเพราะคุณกำลังจะยกสิทธิ์ รันอะไรก็ได้ให้ระบบที่ทำงานด้วยการเดา
สิ่งที่เราทำแทนคือหัวข้อของส่วนถัดไป

## 2. Tool calling คืออะไรกันแน่

นี่คือความเข้าใจผิดที่พบบ่อยที่สุดเกี่ยวกับ agent เขียนไว้ตรง ๆ
เพื่อไม่ให้คุณหลงเชื่อ

> model ไม่ได้รันโค้ดของคุณ ไม่เคยรัน และจะไม่มีวันรัน model
> ปล่อยข้อความที่มีโครงสร้างออกมาชิ้นหนึ่ง ซึ่งระบุชื่อฟังก์ชันและใส่
> arguments มาให้ โปรแกรม Python ของคุณเป็นคนอ่านข้อความนั้นแล้วตัดสินใจ
> ว่าจะทำอะไรกับมัน

อ่านสองรอบ คนที่ใช้ agent framework มาหลายเดือนก็ยังเชื่อว่า
"model เรียก tool" เพราะ framework ซ่อนขั้นตอนตรงกลางได้เนียนจนดูเหมือนเวทมนตร์
ไม่มีเวทมนตร์ มีแค่ก้อน JSON กับคำสั่ง `if` ที่คุณเขียนเอง

### กลไก ทีละขั้น

1. คุณเขียนฟังก์ชัน Python ธรรมดา ไม่มีอะไรพิเศษเลย
2. คุณเขียนคำอธิบายของฟังก์ชันนั้นในรูปแบบที่เรียกว่า JSON Schema
   คำอธิบายบอกว่าฟังก์ชันชื่ออะไร ทำอะไร และรับ arguments อะไรบ้าง
3. คุณส่งคำอธิบายนั้นไปพร้อมกับบทสนทนาใน HTTP request เดียวกัน
   มันเดินทางไปในฟิลด์ `tools` ที่อยู่ข้าง ๆ `messages`
4. model อ่านบทสนทนาและคำอธิบายเหล่านั้น ถ้ามันตัดสินใจว่าสิ่งที่ผู้ใช้ขอ
   จะได้ประโยชน์จากฟังก์ชันเหล่านั้น มันจะไม่ตอบเป็นคำพูด
   แต่จะผลิต message ที่มีโครงสร้างออกมา ซึ่งมีความหมายประมาณว่า
   "ผมอยากให้รัน `add` โดยให้ `a` เท่ากับ 2 และ `b` เท่ากับ 3"
5. message ที่มีโครงสร้างนั้นกลับมาหาคุณผ่าน HTTP มันคือข้อมูล มันเฉื่อยชา
   ยังไม่มีอะไรเกิดขึ้นเลย
6. โปรแกรมของคุณดูที่ชื่อ เอาไปค้นใน dictionary ของฟังก์ชันที่คุณควบคุมอยู่
   แล้วเรียกมัน หรือจะปฏิเสธก็ได้ หรือจะถามผู้ใช้ก่อนก็ได้ หรือจะบันทึกไว้
   แล้วไม่ทำอะไรเลยก็ได้

ขั้นที่ 6 เป็นของคุณ มันเป็นขั้นเดียวที่แตะโลกจริง และมันอยู่ในโค้ดที่คุณเขียนเอง
และอ่านได้ทั้งหมด

### ทำไมต้องออกแบบแบบนี้ ไม่ใช่แบบอื่น

คุณอาจนึกถึงการออกแบบแบบอื่นได้ model ที่คืน source code ของ Python ให้คุณเอาไป
`exec` model ที่เปิด network connection ของตัวเอง model ที่มี shell
ทั้งหมดนั้นมีอยู่จริงในฐานะการทดลอง และทั้งหมดแย่กว่าด้วยเหตุผลเดียวกัน

ลองเทียบสองรูปแบบนี้

```text
Shape A, the one nobody should build
  model  ->  "import os; os.system('rm -rf /')"  ->  exec()
  Your program cannot inspect intent before it runs. Parsing arbitrary code
  to decide if it is safe is an unsolved problem.

Shape B, tool calling, the one everybody actually builds
  model  ->  {"name": "add", "arguments": {"a": 2, "b": 3}}  ->  your dispatcher
  Your program sees a name from a list you defined and arguments you can
  validate before anything executes.
```

Shape B ให้คลังคำศัพท์ที่ตายตัวกับคุณ model ขอได้เฉพาะฟังก์ชันที่คุณเลือก
ประกาศไว้เท่านั้น ถ้ามันคิดชื่อขึ้นมาเองที่คุณไม่เคยลงทะเบียนไว้ dispatcher
(โค้ดที่รับชื่อ tool แล้วเรียกฟังก์ชันจริงให้) ของคุณจะคืน error string
ออกมาและโลกก็ไม่เปลี่ยนแปลง คุณจะเห็นตัวป้องกันนั้นตรง ๆ ใน `tools.py` ด้านล่าง

### นี่คือเหตุผลที่ agent ถูกทำให้ปลอดภัยได้

เพราะคุณเป็นเจ้าของขั้นที่ 6 คุณจึงเป็นเจ้าของผลลัพธ์ทุกอย่าง ช่องว่างระหว่าง
"model ขอมา" กับ "โค้ดได้รัน" คือที่ที่ความปลอดภัยทั้งหมดในการออกแบบ agent
อาศัยอยู่ ในช่องว่างนั้นคุณทำอะไรต่อไปนี้ก็ได้

- พิมพ์คำขอออกมาแล้วรอให้ผู้ใช้พิมพ์ yes
- ตรวจว่า path ของไฟล์ยังอยู่ในโฟลเดอร์ของโปรเจกต์
- ปฏิเสธคำสั่ง shell ใดก็ตามที่มีการลบอยู่ในนั้น
- จำกัดจำนวนครั้งที่ tool ถูกรันในหนึ่งเทิร์น
- บันทึกทุกการเรียกไว้เพื่อให้คนตรวจสอบย้อนหลังได้ว่าเกิดอะไรขึ้น

ไม่มีอะไรในนี้ทำได้เลยถ้า model รันสิ่งต่าง ๆ เอง แต่ทั้งหมดกลายเป็นเรื่องง่าย
ทันทีที่การรันคือการเรียกฟังก์ชันในโปรแกรมของคุณเอง ภาคสอง ของคอร์สนี้จะเพิ่ม
ตัวอ่านไฟล์จริงและตัวรัน shell จริง และเพิ่ม prompt ขอคำยืนยันไว้ในช่องว่างนี้
พอดี เรื่องความปลอดภัยไม่ใช่ฟีเจอร์ที่มาแปะทีหลัง มันเป็นผลพวงของรูปแบบ
ที่คุณกำลังเรียนอยู่ตอนนี้

อีกเรื่องที่ควรสังเกตก่อนเราไปดูโค้ด การที่ model เลือกปล่อย tool call ออกมา
ก็ยังเป็นแค่การทำนาย มันไม่ใช่การตัดสินใจในความหมายที่คนตัดสินใจ มันคือ model
ผลิต output ที่เข้ากับบทสนทนาบวกกับคำอธิบาย tool ที่มันถูกให้ดูมากที่สุด
นั่นคือเหตุผลที่ถ้อยคำในคำอธิบายเหล่านั้นสำคัญมหาศาล ซึ่งเป็นเนื้อหาของส่วนที่ 5

## 3. อ่าน JSON Schema ทีละฟิลด์

JSON Schema คือมาตรฐานในการอธิบายรูปร่างของค่า JSON ฝั่ง provider หยิบมันมาใช้
เพื่อให้รูปแบบเดียวอธิบาย arguments ของฟังก์ชันได้ทุกภาษา คุณไม่ต้องเรียน
JSON Schema ทั้งหมด คุณต้องรู้ประมาณห้า keyword และบทนี้ใช้อยู่สี่ตัว

นี่คือ schema ของ `add` ตรงตามที่ปรากฏใน `tools.py`

```python
{
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two numbers together and return the sum.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "The first number"},
                "b": {"type": "number", "description": "The second number"},
            },
            "required": ["a", "b"],
        },
    },
}
```

ทีนี้มาดูสิ่งเดียวกันทีละฟิลด์

ฟิลด์ `type` ชั้นนอกมีค่าเป็น string ตรงตัวว่า `function` ทุกวันนี้
นั่นเป็นค่าเดียวที่ API แบบ OpenAI compatible ยอมรับตรงนี้ มันมีอยู่เพราะฟิลด์นี้
เป็นตัวแยกประเภท เป็นแท็กที่บอก parser ในอนาคตว่ารูปแบบอะไรตามมา provider
เพิ่ม tool ชนิดใหม่ ๆ เข้ามาเรื่อย ๆ รูปแบบนี้จึงเผื่อที่ไว้ ให้มองว่ามันเป็น
boilerplate ที่คุณต้องเขียนเสมอ

`function.name` คือ identifier ที่ model จะส่งกลับมาเมื่อมันต้องการ tool นี้
มันต้องตรงกับ key ที่คุณใช้ค้นหาฟังก์ชัน Python ตัวจริง ใช้เฉพาะตัวอักษร ตัวเลข
และ underscore string นี้ยังถูก model อ่านเป็นคำใบ้ด้วย แปลว่า `add` ดีกว่า `f1`
และ `read_file` ดีกว่า `rf`

`function.description` คือภาษาอังกฤษง่าย ๆ หนึ่งหรือสองประโยคที่อธิบายว่า
tool ทำอะไร ส่วนที่ 5 พูดถึงฟิลด์นี้ทั้งส่วน เพราะมันทำงานหนักกว่าส่วนอื่น
ใด ๆ ของ schema

`function.parameters` คือ object แบบ JSON Schema ที่อธิบาย arguments
มันเป็น schema ในตัวเอง จึงมี `type` ของตัวเองอยู่ข้างใน

`parameters.type` สำหรับ tool จะเป็น string ว่า `object` เสมอ arguments
เดินทางมาเป็น JSON object ที่มี key ระบุชื่อ เพราะ keyword arguments ของ Python
กับ key ของ JSON object เข้ากันได้พอดี ไม่มีรูปแบบ positional argument

`parameters.properties` คือ dictionary ที่แต่ละ key คือชื่อ argument และแต่ละ
ค่าคือ schema เล็ก ๆ ของ argument นั้น ชื่อในนี้จะกลายเป็น keyword arguments
ที่ส่งเข้าฟังก์ชัน Python ของคุณ แปลว่า `a` และ `b` ใน schema ต้องตรงกับ
`def add(a, b)` ในโค้ด ถ้ามันเพี้ยนไปคนละทาง คุณจะได้ `TypeError` ตอนเรียก
ซึ่ง `tools.run` จะดักไว้แล้วแปลงเป็น error string

`type` ที่อยู่ในแต่ละ property คือที่ที่คุณบอกว่าอนุญาตค่าชนิดไหน
ตัวที่มีประโยชน์อยู่ด้านล่าง

| JSON Schema type | ค่าที่คุณได้รับใน Python | ใช้กับอะไร |
| --- | --- | --- |
| `"number"` | `float` หรือ `int` | ค่าตัวเลขใด ๆ รวมทั้งทศนิยม |
| `"integer"` | `int` | จำนวนนับ index จำนวนหน้าของลูกเต๋า |
| `"string"` | `str` | ข้อความ path identifier |
| `"boolean"` | `bool` | แฟล็ก |
| `"array"` | `list` | list ของค่าต่าง ๆ ต้องมี schema `items` ด้วย |
| `"object"` | `dict` | โครงสร้างซ้อนกัน ต้องมี `properties` ของตัวเอง |

สังเกตว่า `add` ใช้ `number` ขณะที่ `roll_dice` ใช้ `integer` นั่นไม่ใช่การประดับ
ลูกเต๋าที่มี 6.5 หน้าไม่มีความหมาย และ `random.randint` จะ raise ถ้าได้ค่า float
การเลือก `integer` ทำให้ข้อจำกัดนั้นกลายเป็นส่วนหนึ่งของสัญญาที่ model อ่าน
ซึ่งแปลว่า model มีโอกาสส่งทศนิยมมาตั้งแต่แรกน้อยลงมาก

`description` ที่อยู่ในแต่ละ property อธิบาย argument ตัวนั้น
model อ่านมันตอนตัดสินใจว่าจะใส่ค่าอะไรลงไป "The first number" นั้นบางไปหน่อย
แต่พอใช้ได้กับของเล่น สำหรับ tool จริง คุณจะเขียนประมาณว่า "Absolute path to
the file to read, relative paths are rejected."

`parameters.required` คือ list ของชื่อ argument ที่ต้องมี property ใดที่ไม่ได้
อยู่ในนี้ถือว่าเป็นตัวเลือก และ model อาจไม่ส่งมาก็ได้ ฟังก์ชัน Python ของคุณ
จึงต้องมีค่า default ให้มัน ไม่อย่างนั้นคุณจะได้ `TypeError` นิสัยที่ดีคือ
รักษาให้ `required` กับ signature ของฟังก์ชันสอดคล้องกัน โดยอ่านทั้งสองเทียบกัน
ทุกครั้งที่คุณแก้ฝั่งใดฝั่งหนึ่ง

### JSON ตัวจริงที่วิ่งไปตามสาย

เมื่อ `check.py` รัน `llm.py` จะประกอบ body ของ HTTP request นี้ขึ้นมาแล้ว post
ไปที่ path `/chat/completions` ของ endpoint คุณ นี่คือของจริง มี tool ทั้งสองตัว
ครบและไม่ได้ตัดอะไรออก

```json
{
  "model": "mock",
  "messages": [
    {
      "role": "user",
      "content": "What is 2 plus 3? [[tool:add:{\"a\": 2, \"b\": 3}]]"
    }
  ],
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
    },
    {
      "type": "function",
      "function": {
        "name": "roll_dice",
        "description": "Roll a dice with the given number of sides.",
        "parameters": {
          "type": "object",
          "properties": {
            "sides": {
              "type": "integer",
              "description": "How many sides the dice has"
            }
          },
          "required": ["sides"]
        }
      }
    }
  ]
}
```

มีสองอย่างที่ควรจ้องดูให้ดี อย่างแรก `tools` อยู่ข้าง ๆ `messages` ที่ระดับบนสุด
ไม่ได้อยู่ข้างใน message อย่างที่สอง schema ถูกส่งไปใหม่ทุก request ไม่มีขั้นตอน
ลงทะเบียน ไม่มี session ไม่มีหน่วยความจำฝั่งเซิร์ฟเวอร์ที่จำ tool ของคุณ
เหมือนกับ history ของบทสนทนาในบทที่ 02 list ของ tool เดินทางไปแบบเต็ม ๆ ทุกครั้ง
ถ้าคุณหยุดส่งมันไป model ก็จะหยุดรู้ว่ามี tool เหล่านั้นอยู่

## 4. กลไกเดียวกันนี้ให้ structured output กับคุณ

มีฟีเจอร์ที่สองที่คุณจะได้เจอในไม่ช้า ในบทเรียนอื่น ภายใต้ชื่ออื่น provider
เรียกมันว่า structured output หรือ JSON mode หรือ response format มันมีหน้า
เอกสารของตัวเอง มี helper ของตัวเองในทุก framework และมีบทของตัวเองในคอร์ส
ส่วนใหญ่ วางอยู่ห่างไกลจากบทที่ว่าด้วย tool คนจึงเรียนมันในฐานะของคนละเรื่อง
สองฟีเจอร์ สองชื่อ สอง mental model ความรู้สึกนั้นผิด และมันแพง เพราะมันทำให้
คุณเรียนแนวคิดเดียวกันสองรอบ และแบกโค้ดสองชุดไว้เพื่อเรื่องเดียว

structured output กับ tool calling คือกลไกเดียวกัน คุณสร้างมันไปเรียบร้อยแล้ว
สิ่งที่ตามมาคือเครื่องจักรจากส่วนที่ 2 และ schema จากส่วนที่ 3 โดยลบออกไป
หนึ่งขั้นพอดี

### structured output หมายถึงอะไร

โดยปกติ model ตอบเป็นร้อยแก้ว และร้อยแก้วแทบไม่มีประโยชน์กับส่วนที่เหลือของ
โปรแกรมคุณ ลองให้ model คัดแยก support ticket แล้วมันจะพูดประมาณว่า
"This customer sounds quite frustrated about a late delivery." คุณเก็บสิ่งนั้น
ลงคอลัมน์ในฐานข้อมูลไม่ได้ แตกกิ่งด้วย `if` ไม่ได้ และนับไม่ได้ว่าสัปดาห์นี้
มี ticket เชิงลบกี่ใบ การ parse มันด้วย regular expression ใช้ได้จนกว่า model
จะเปลี่ยนสำนวน ซึ่งมันจะเปลี่ยนแน่นอน

สิ่งที่คุณต้องการแทนคือคำตอบที่มีรูปร่างเป็นข้อมูล JSON object ที่มีฟิลด์ตามที่
คุณกำหนด ในชนิดที่คุณกำหนด เหมือนกันทุกครั้ง นั่นคือทั้งหมดของคำว่า structured
output คุณไม่ได้ขอให้ model ฉลาดขึ้น คุณขอให้มันกรอกฟอร์มแทนการเขียนเรียงความ

### tool call เป็น structured output อยู่แล้ว

อ่าน tool call จากส่วนที่ 2 อีกครั้งด้วยสายตาใหม่

```json
{"name": "add", "arguments": {"a": 2, "b": 3}}
```

model ผลิตชื่อกับ arguments object ที่สอดคล้องกับ JSON Schema ที่คุณเขียน
การผลิต object นั้นคือส่วนร่วมทั้งหมดของ model การรันฟังก์ชัน Python ที่คู่กัน
หลังจากนั้นเป็นการตัดสินใจอีกอันหนึ่ง เกิดขึ้นในขั้นที่ 6 โดยโค้ดที่คุณเป็นเจ้าของ

จงตัดสินใจต่างออกไปในขั้นที่ 6 อย่ารันอะไรเลย อ่าน `call["arguments"]`
แล้วถือว่า dictionary นั้นคือคำตอบ นั่นคือ structured output ของคุณ โดยไม่มี
API ใหม่ ไม่มีฟิลด์ใหม่ใน request body และไม่มี library ใหม่ tool นั้นไม่เคย
เป็น tool จริง ๆ มันคือฟอร์ม และ model เป็นคนกรอกมัน

### ตัวอย่างที่ทำจริง sentiment ในฐานะฟอร์ม

สมมติว่าคุณอยากได้ค่า sentiment ของข้อความชิ้นหนึ่งในรูปข้อมูล เพื่อเก็บไว้และ
นับทีหลัง ให้นิยาม tool ที่คุณไม่มีเจตนาจะรันเลย

```python
RECORD_SENTIMENT = {
    "type": "function",
    "function": {
        "name": "record_sentiment",
        "description": (
            "Record the sentiment of the message you were shown. "
            "Call this exactly once for every message, and never answer in words."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"],
                    "description": "The overall sentiment of the message",
                },
                "confidence": {
                    "type": "number",
                    "description": "How certain you are, from 0.0 for a guess to 1.0 for certain",
                },
                "reason": {
                    "type": "string",
                    "description": "One sentence explaining the label, at most fifteen words",
                },
            },
            "required": ["label", "confidence", "reason"],
        },
    },
}
```

มีสามอย่างใน schema นั้นที่ควรกล่าวถึง

`enum` คือ JSON Schema keyword ตัวที่ห้าที่ส่วนที่ 3 สัญญาไว้ และตรงนี้คือที่ที่
มันพิสูจน์คุณค่าของตัวเอง มันระบุรายการค่าที่ฟิลด์นี้ได้รับอนุญาตให้เป็นเท่านั้น
ถ้าไม่มีมัน label ที่เป็น `string` เปล่า ๆ จะเชื้อเชิญ `Positive` `very negative`
`NEGATIVE` และ `mixed` เข้ามา แล้วคุณจะใช้ชีวิตที่เหลือไปกับการ normalise string
เมื่อมีมัน สัญญาที่ model อ่านบอกว่ามีค่าอยู่สามค่า และไม่มีค่าอื่นอยู่เลย
ทำไมต้องใส่ข้อจำกัดไว้ใน schema แทนที่จะใส่เป็นประโยคใน prompt เพราะ schema คือส่วนที่
provider ตรวจสอบ และเป็นส่วนที่ constrained decoder (ตัวที่คุม model ให้เขียน output
ตรงรูปแบบ) บังคับได้ ส่วนประโยคใน prompt เป็นแค่คำขอสุภาพ

`confidence` เป็น `number` ไม่ใช่ `string` สิ่งที่มาถึงจึงเป็น float ที่คุณเทียบ
กับ threshold ได้ทันที ไม่ใช่ข้อความที่ต้องแปลงก่อน ส่วน `reason` ระบุขีดจำกัด
ความยาวไว้ในคำอธิบายของตัวเอง เพราะคำว่า "short" ลอย ๆ ไม่มีความหมายทั้งกับ model
และกับเพื่อนร่วมงาน

คำอธิบายของ tool สั่ง model ให้เรียกมันทุกครั้งและไม่ให้ตอบเป็นคำพูดเลย
นั่นแข็งกร้าวกว่าที่ส่วนที่ 5 จะแนะนำตามปกติ และมันตั้งใจ ใน tool calling ทั่วไป
คุณอยากให้ model เลือกระหว่างร้อยแก้วกับการเรียก tool แต่ใน structured output
คุณไม่อยากให้มีทางเลือกเลย คุณอยากได้ฟอร์ม ทุกครั้ง

ทีนี้เรียก model ด้วย tool ตัวเดียวนั้นแล้วดึง arguments ออกมา

```python
from llm import complete

MESSAGE = "The parcel arrived two weeks late and nobody replied to my emails."

text, calls = complete([{"role": "user", "content": MESSAGE}], [RECORD_SENTIMENT])
sentiment = calls[0]["arguments"]
print(sentiment)
```

สิ่งที่กลับมาคือ dictionary ธรรมดาของ Python ที่ถูก parse ไปแล้วโดยบรรทัด
`json.loads` ใน `llm.py`

```python
{"label": "negative", "confidence": 0.95, "reason": "Parcel was very late and support emails went unanswered."}
```

สังเกตสิ่งที่ไม่มี ไม่มีฟังก์ชัน `record_sentiment` อยู่ที่ไหนเลยในโค้ดของคุณ
`tools.FUNCTIONS` ไม่มี entry สำหรับชื่อนั้น และ `tools.run` ไม่เคยถูกเรียก
ไม่มีอะไรถูกรัน สิ่งเดียวที่คุณต้องการมาตลอดคือ dictionary ของ arguments
และตอนนี้คุณถือมันอยู่ในมือแล้ว

รายละเอียดเชิงปฏิบัติอีกหนึ่งข้อ `calls` กลับมาว่างได้ เพราะ model ที่อ่อนกว่า
อาจตอบเป็นคำพูดอยู่ดี ให้เช็ค list ก่อน index มัน แบบเดียวกับที่ `check.py` ทำ
และมองว่า list ว่างคือการสกัดข้อมูลที่ต้องลองใหม่ ไม่ใช่การ crash

### ทำไมเรื่องนี้ถึงควรรู้

นี่ไม่ใช่กลเล่นสนุก มันตัดงานออกไปทั้งหมวด

การสกัดข้อมูล การจัดหมวดหมู่ และการกรอกฟอร์ม คืองานส่วนใหญ่ที่ model ถูกใช้จริง
ใน production ดึงเลขที่ใบแจ้งหนี้ วันที่ และยอดรวมออกจากอีเมลฉบับนี้ ตัดสินว่า
ticket ใบนี้เป็น billing เป็น bug หรือเป็น spam เปลี่ยนย่อหน้าที่ผู้ใช้พิมพ์มา
เรื่อยเปื่อยให้เป็นหกฟิลด์ของฟอร์มจอง ทุกอันในนั้นคือ schema หนึ่งชุด การเรียก
หนึ่งครั้ง และการอ่าน arguments คุณไม่ต้องมีกลไกที่สอง library ที่สอง หรือ
mental model ที่สองสำหรับอันไหนเลย และคุณไม่ต้องเรียนรูปแบบความล้มเหลวใหม่
เมื่อมีอันใดอันหนึ่งทำตัวแปลก

มันยังแปลว่าทุกอย่างที่ส่วนที่ 5 กำลังจะพูดถูกยกมาใช้ตรงนี้ได้โดยไม่ต้องแก้
คำอธิบายยังคงเป็นสิ่งเดียวที่ model เห็น คำอธิบายของฟิลด์ที่คลุมเครือให้ผล
การสกัดที่คลุมเครือ แบบเดียวกับที่คำอธิบาย tool ที่คลุมเครือทำให้ tool ไม่เคย
ถูกเรียก ถ้า classifier ของคุณเลือก `neutral` อยู่เรื่อย ให้เขียนคำอธิบายของ
enum ใหม่ก่อนจะไปแตะอย่างอื่น ด้วยเหตุผลเดียวกันและด้วยโอกาสสำเร็จเท่ากัน

และความรู้เรื่องงานเดินท่อก็ถ่ายทอดมาได้เช่นกัน output ยังมาถึงในรูป JSON string
ที่อยู่ในฟิลด์ `arguments` มันจึงยังต้องใช้ `json.loads` และ model ที่อ่อนกว่า
ก็ยังผลิต JSON ที่ผิดรูปตรงนั้นได้ ด้วยเหตุผลเรื่องการสร้างทีละ token ที่ส่วนที่ 7
อธิบายไว้

### โหมดเฉพาะทาง และเมื่อไรที่มันดีกว่า

การพูดถึงทางเลือกอีกทางอย่างเป็นธรรมสำคัญตรงนี้ เพราะ tool ที่ไม่ถูกรันไม่ใช่
เส้นทางที่ถูกต้องเสมอไป

provider รายใหญ่ทุกเจ้ามีโหมดที่สร้างมาเพื่อเรื่องนี้โดยเฉพาะจริง ๆ ชื่อเรียก
ต่างกันไป `response_format` ที่พก JSON Schema มาด้วย JSON mode structured outputs
แต่แนวคิดเป็นแนวคิดเดียว คุณใส่ schema ไว้ในฟิลด์ของตัวเองใน request แทนที่จะ
ใส่ไว้ใน list `tools` และคำตอบกลับมาเป็น JSON ใน `content` แทนที่จะอยู่ใน
`tool_calls`

เหตุผลที่ควรเลือกมันเมื่อคุณเลือกได้ ไม่ใช่เรื่องความเรียบร้อย แต่เป็นเพราะ
implementation ที่ดีจะบังคับ model ระหว่างการสร้างข้อความ ในทุก token ตัว decoder
เลือกได้เฉพาะ token ที่ทำให้ output ยังถูกต้องตาม schema ของคุณ key ที่คุณไม่เคย
นิยามจึงถูกปล่อยออกมาไม่ได้ และ `label` ที่อยู่นอก enum ก็ผลิตไม่ได้ tool calling
เป็นการขออย่างสุภาพแล้วค่อยตรวจทีหลัง ส่วน constrained decoder ทำให้คำตอบที่ผิด
ไปไม่ถึงตั้งแต่แรก ใน production ความต่างนั้นปรากฏออกมาเป็นจำนวนครั้งที่ต้อง
ลองใหม่ที่น้อยลง

เหตุผลที่ควรรู้เส้นทาง tool calling ไว้อยู่ดีคือความครอบคลุม มันทำงานได้บนทุก
endpoint ที่รองรับ tool รวมถึง model เล็ก ๆ บนเครื่องและ gateway รุ่นเก่าที่โหมด
เฉพาะทางนั้นไม่มี ถูกเมิน หรือถูกรับไว้แล้วเงียบ ๆ ไม่บังคับใช้จริง มันไม่ต้องการ
อะไรเกินจากที่คุณเขียนไปแล้วในบทนี้ และมันเป็นทางเดียวในสองทางที่ยังปล่อยให้
model เลือกระหว่างการตอบเป็นร้อยแก้วกับการคืนข้อมูล ซึ่งเป็นสิ่งที่คุณต้องการ
ทันทีที่การเรียกครั้งเดียวต้องรับใช้ทั้งบทสนทนาและการสกัดข้อมูล

ค่าเริ่มต้นที่สมเหตุสมผล ใช้โหมดเฉพาะทางเมื่อ provider ของคุณรองรับมันอย่างถูกต้อง
และคุณต้องการข้อมูลกลับมาเสมอ หันไปใช้ tool ที่คุณไม่รันเมื่อคุณไม่มีโหมดนั้น
เมื่อคุณกำลังย้ายไปมาระหว่าง provider หรือเมื่อ request เดียวกันต้องรับใช้ทั้งสอง
วัตถุประสงค์

## 5. ทำไมคำอธิบายจึงสำคัญกว่าตัวโค้ด

ฟังก์ชัน Python ของคุณอาจเป็นงานประณีตยาวพันบรรทัด model ไม่เคยเห็นตัวอักษร
สักตัวเดียวของมัน model เห็นชื่อ คำอธิบาย ชื่อของ arguments ชนิดของ arguments
และคำอธิบายของ arguments เท่านั้น นั่นคืออินเทอร์เฟซทั้งหมด

เรื่องนี้กลับหัวสัญชาตญาณปกติ ในการเขียนโปรแกรมทั่วไป implementation คือความจริง
และ docstring เป็นแค่มารยาท แต่ใน tool calling คำอธิบายคือความจริง เพราะมันเป็น
input เดียวของการตัดสินใจว่าจะเรียกฟังก์ชันของคุณหรือไม่ตั้งแต่แรก

คำอธิบายที่อ่อนแอทำให้เกิดความล้มเหลวหนึ่งในสองแบบ ไม่ model ก็ไม่เคยเรียก tool
เลยเพราะบอกไม่ได้ว่า tool เกี่ยวข้อง หรือไม่ก็เรียก tool ผิด ๆ เพราะมันเดาเอาว่า
arguments หมายถึงอะไร ทั้งสองแบบดูเหมือน model โง่ แต่ทั้งสองแบบมักเป็นเพราะ
schema คลุมเครือ

### ตัวอย่างที่แย่

```json
{
  "type": "function",
  "function": {
    "name": "get_data",
    "description": "Gets data.",
    "parameters": {
      "type": "object",
      "properties": {
        "q": {"type": "string"},
        "n": {"type": "integer"}
      },
      "required": ["q"]
    }
  }
}
```

ทุกอย่างในนี้ถูกต้องตามหลักเทคนิคและไร้ประโยชน์ในทางปฏิบัติ ข้อมูลอะไร จากที่ไหน
`q` คืออะไร query quantity หรือ quarter `n` คืออะไร และจะเกิดอะไรขึ้นเมื่อไม่ใส่มา
model ที่เห็น schema นี้ไม่มีอะไรให้ใช้ตัดสินใจว่าควรเลือกมันแทนการตอบเป็นคำพูด
และถ้ามันเลือกจริง arguments ก็เหมือนโยนหัวก้อย จากนั้นคุณจะเสียเวลาทั้งบ่าย
ไปกับการโทษ model

### ตัวอย่างที่ดี

```json
{
  "type": "function",
  "function": {
    "name": "search_orders",
    "description": "Search this shop's order database by customer email address. Returns the matching orders as JSON, newest first, including order id, status and total. Use this whenever the user asks about the status or history of an order. Returns an empty list when the email is not found.",
    "parameters": {
      "type": "object",
      "properties": {
        "email": {
          "type": "string",
          "description": "The customer's full email address, for example ada@example.com. Partial addresses are not matched."
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of orders to return. Defaults to 10 when omitted. Maximum accepted value is 100."
        }
      },
      "required": ["email"]
    }
  }
}
```

ลองเทียบว่าอันที่สองบอกอะไรกับ model ที่อันแรกไม่ได้บอก

- มันค้นอะไร เพื่อให้ model รู้ว่า tool นี้เกี่ยวข้องเมื่อไร
- อะไรจะกลับมาและเรียงลำดับอย่างไร เพื่อให้ model รู้ว่าต้องทำอะไรต่อ
- ควรหยิบมันมาใช้เมื่อไร ระบุเป็นคำสั่ง ซึ่งทำได้และได้ผล
- เกิดอะไรขึ้นในกรณีที่ไม่พบอะไรเลย เพื่อให้ model ไม่มองผลลัพธ์ว่างเปล่า
  ว่าเป็นความล้มเหลวแล้วลองใหม่ไม่รู้จบ
- รูปแบบที่แน่นอนของ argument พร้อมตัวอย่าง
- ค่า default และขอบบนของ argument ที่เป็นตัวเลือก

กฎที่มีประโยชน์ระหว่างที่คุณกำลังเรียนรู้ เขียนคำอธิบายเหมือนเขียนให้เพื่อนร่วมงาน
ใหม่ที่เก่ง แต่มองไม่เห็นอะไรเลยนอกจากย่อหน้านั้น เข้าถึง codebase ไม่ได้ และ
จะถูกตำหนิถ้าใช้ฟังก์ชันผิด ถ้าย่อหน้าของคุณปล่อยให้เพื่อนร่วมงานคนนั้นต้องเดา
model ก็จะต้องเดาเช่นกัน

กฎข้อที่สอง เมื่อ model ทำตัวแย่กับ tool ให้แก้คำอธิบายก่อนจะไปแตะอย่างอื่น
มันเป็นการทดลองที่ถูกที่สุดที่คุณมี และมันแก้ปัญหาได้บ่อยกว่าการเปลี่ยนอย่างอื่น

## 6. ทำไม tool ในบทนี้ถึงเป็นของเล่น

tool สองตัวในบทนี้คือเครื่องคิดเลขกับการทอยลูกเต๋า นั่นเป็นความตั้งใจ และเหตุผล
เขียนไว้ใน docstring ด้านบนของ `tools.py`

```python
def add(a, b):
    return a + b


def roll_dice(sides):
    return random.randint(1, sides)
```

สองบวกสามได้ห้า มันได้ห้าบนเครื่องคุณ บนตัวรัน continuous integration บน Windows บน
Linux ทั้งวันนี้และปีหน้า ลูกเต๋าหกหน้าคืนค่าตั้งแต่หนึ่งถึงหกเสมอ ไม่มี network ไม่มี
file system ไม่มี permission ไม่มี rate limit ไม่มี API key
ไม่มีค่าใช้จ่าย และไม่มีทางที่ตัว tool เองจะเป็นบั๊ก

เรื่องนี้สำคัญกว่าที่ฟังดู คุณกำลังจะเชื่อมต่อ HTTP request หนึ่งตัว JSON Schema
หนึ่งชุด ตัว parse response หนึ่งตัว string ที่ต้อง parse ให้เป็น dictionary
และ dispatcher หนึ่งตัวเข้าด้วยกัน นั่นคือห้าจุดที่พลาดได้ ถ้า tool เป็น
`fetch_weather` คุณจะต้องรับมือกับการเรียก network เพิ่ม กับ API key กับ rate limit
และกับรูปแบบ response ที่คุณไม่เคยเห็น เวลาการตรวจล้มเหลว คุณจะไม่รู้เลยว่า
เก้าอย่างนั้นพังตรงไหน

ถ้าใช้ `add` แล้วผลลัพธ์ไม่ใช่ `5` ปัญหาอยู่ที่งานเดินท่อ นั่นเป็นขอบเขตการค้นหา
ที่เล็กกว่ามาก การเรียนรู้ที่จะแยกตัวแปรออกมาแบบนี้เป็นทักษะทั่วไป และคุ้มค่าที่จะ
ฝึกอย่างตั้งใจตรงนี้ ที่ซึ่งไม่มีอะไรต้องเสีย

และพูดตรง ๆ tool ที่น่าเบื่อช่วยให้ส่วนที่น่าสนใจยังมองเห็นได้ ส่วนที่น่าสนใจ
ไม่ใช่การบวก แต่คือการที่ language model มองประโยคหนึ่งแล้วผลิตคำขอที่มีโครงสร้าง
ซึ่งระบุชื่อฟังก์ชันที่มันไม่เคยเห็นมาก่อนหน้า HTTP call นี้เลย

tool ของจริงจะมาถึงในภาคสอง ที่นั่นคุณจะสร้างตัวอ่านไฟล์ ตัวเขียนไฟล์ และตัวรัน
shell และคุณจะเพิ่มด่านขอคำยืนยันที่เปลี่ยนความสามารถอันตรายให้เป็นความสามารถ
ที่มีคนกำกับ งานเดินท่อที่คุณกำลังสร้างวันนี้ไม่เปลี่ยนเลยเมื่อ tool กลายเป็นของจริง
มีแค่ tool เท่านั้นที่เปลี่ยน

## 7. เขียน tools.py และ llm.py ทีละบรรทัด

### tools.py

เปิดไฟล์แล้วอ่านจากบนลงล่าง มันมีสามส่วน และการเรียงลำดับนั้นตั้งใจ schema
มาก่อนเพราะมันคืออินเทอร์เฟซ ฟังก์ชันมาที่สองเพราะเป็น implementation และ
dispatcher มาท้ายสุดเพราะมันเชื่อมสองอย่างเข้าด้วยกัน docstring ด้านบนถูกย่อไว้ตรงนี้
ตัวไฟล์จริงมีเต็มเก้าบรรทัด

```python
"""Toy tools with hand written schemas."""
import random

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers together and return the sum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "Roll a dice with the given number of sides.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {"type": "integer", "description": "How many sides the dice has"}
                },
                "required": ["sides"],
            },
        },
    },
]
```

`SCHEMAS` เป็น list ธรรมดาของ Python ที่บรรจุ dictionary ธรรมดาของ Python ไม่มี
library ไม่มี decorator และไม่มีคลาส registry มันถูกเขียนด้วยมือโดยตั้งใจ
เพราะจุดประสงค์ของคอร์สนี้คือให้คุณเห็นทุกไบต์ที่วิ่งไปตามสาย framework
สร้าง list นี้จาก type hints ซึ่งสะดวกดี เมื่อคุณรู้อยู่แล้วว่าสิ่งที่ถูกสร้าง
ขึ้นมาคืออะไร

```python
def add(a, b):
    return a + b


def roll_dice(sides):
    return random.randint(1, sides)


FUNCTIONS = {"add": add, "roll_dice": roll_dice}
```

ฟังก์ชันธรรมดาสองตัวและ dictionary ที่ map ชื่อใน schema เข้ากับฟังก์ชันเหล่านั้น
dictionary นี้คือ allow list มันคือเหตุผลที่ model ขอสิ่งที่คุณไม่ได้เลือกเปิดเผย
ไม่ได้ ชื่อที่ไม่ได้เป็น key ในนี้ก็แค่หาไม่เจอ

```python
def run(name, arguments):
    """Run one tool by name and return its result as a string."""
    function = FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**arguments))
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"
```

ฟังก์ชันจิ๋วนี้คือขั้นตอนการรัน คือขั้นที่ 6 ทั้งหมดจากส่วนที่ 2 มีสามรายละเอียด
ที่ควรใส่ใจ

การค้นด้วย `FUNCTIONS.get(name)` พร้อมการเช็ค `None` อย่างชัดเจนคือตัวป้องกันที่กัน
ชื่อ tool ที่ model หลอนขึ้นมา model คิดชื่อฟังก์ชันที่ฟังดูสมเหตุสมผลขึ้นมาเอง
เป็นครั้งคราวจริง ๆ เมื่อเกิดขึ้นคุณคืน string ออกมา ไม่ใช่ exception และโปรแกรม
ก็เดินหน้าต่อ

การกระจายด้วย `**arguments` เปลี่ยน dictionary `{"a": 2, "b": 3}` ให้เป็นการเรียก
`add(a=2, b=3)` นี่แหละคือเหตุผลที่ชื่อ property ใน schema ต้องตรงกับชื่อ
พารามิเตอร์ใน Python

การใช้ `except Exception` แบบกว้าง ๆ เป็นเรื่องผิดปกติใน Python ระดับ production
แต่ถูกต้องตรงนี้ tool จะต้องพังบ้างในบางครั้ง ไฟล์จะไม่มีอยู่ ตัวเลขจะเกินช่วง
network จะล่ม ถ้าความล้มเหลวเหล่านั้น raise ออกมา agent ของคุณจะตายกลางเทิร์น
ถ้ามันกลับมาเป็น string loop ที่คุณจะสร้างในบทที่ 04 จะส่งข้อความ error นั้นกลับ
ไปให้ model ได้ ซึ่งมันจะลองทำอย่างอื่นต่อ agent ที่อ่าน error ของตัวเองได้นั้น
มีความสามารถมากกว่า agent ที่ crash อยู่มาก และบรรทัดเดียวนี้คือสิ่งที่ทำให้
เป็นไปได้

สังเกตด้วยว่าทุกอย่างถูกแปลงด้วย `str()` ผลลัพธ์ของ tool เดินทางกลับไปหา model
ในรูปข้อความ เพราะ messages คือข้อความ การคืน `int` ตรงนี้จะแปลว่าต้องแปลง
มันทีหลังอยู่ดี

### llm.py

นี่คือ `complete` ของบทที่ 02 ที่มีการเปลี่ยนแปลงสองจุด อ่านทั้งไฟล์ก่อน

```python
"""Send tools along with the conversation and read what the model asks for."""
import json
import os

import httpx


def complete(messages, tools=None):
    """Return (text, tool_calls).

    tool_calls is a list of dicts with the keys id, name and arguments.
    When the model answers in words the list is empty.
    """
    base_url = os.environ["AGENTPATH_BASE_URL"].rstrip("/")
    api_key = os.environ.get("AGENTPATH_API_KEY", "")
    model = os.environ["AGENTPATH_MODEL"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools

    response = httpx.post(
        f"{base_url}/chat/completions", json=payload, headers=headers, timeout=120
    )
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]

    calls = []
    for raw in message.get("tool_calls") or []:
        calls.append(
            {
                "id": raw["id"],
                "name": raw["function"]["name"],
                "arguments": json.loads(raw["function"]["arguments"] or "{}"),
            }
        )
    return message.get("content") or "", calls
```

การเปลี่ยนแปลงที่หนึ่งคือ signature และค่าที่คืนกลับ ในบทที่ 02 `complete`
คืน string ตอนนี้มันคืน tuple ของ text กับ list ของ tool calls เพราะตอนนี้
มีคำตอบสองชนิดและผู้เรียกต้องแยกออกจากกันได้ เมื่อ model ตอบเป็นคำพูด list
จะว่าง เมื่อ model ขอ tool ปกติ text จะว่างและ list จะมีสมาชิกหนึ่งตัวขึ้นไป
การที่ทั้งสองอย่างไม่ว่างพร้อมกันนั้นถูกต้องตามกติกาและเกิดขึ้นจริงกับบาง model
นั่นคือเหตุผลที่เราคืนทั้งสองอย่างแทนที่จะคืนอย่างใดอย่างหนึ่ง

การเปลี่ยนแปลงที่สองอยู่ที่ payload ตัว key `tools` จะถูกเพิ่มก็ต่อเมื่อมีการส่ง tools
เข้ามา การส่ง `"tools": []` หรือ `"tools": null` ทำให้ provider บางเจ้าไม่พอใจ
ตัวป้องกัน `if tools` จึงทำให้ request สะอาด และยังให้ฟังก์ชันนี้ใช้กับแชทธรรมดาได้

environment variables (ตัวแปรสภาพแวดล้อม คือค่าที่ตั้งไว้ใน shell) ตัว bearer header
และการเรียก `raise_for_status` ยังเหมือนเดิมจากบทที่ 02 ถ้า `raise_for_status`
เป็นของใหม่สำหรับคุณ มันเปลี่ยน response 4xx หรือ 5xx ใด ๆ ให้เป็น exception
แทนที่จะปล่อยให้ JSON parse error มาทำให้คุณงงในอีกสามบรรทัดถัดไป

### JSON string ที่ทำให้ทุกคนประหลาดใจ

นี่คือส่วนของบทเรียนที่ทำให้ผู้อ่านแทบทุกคนสะดุดในการลองครั้งแรก มันจึงได้หัวข้อ
เป็นของตัวเอง

ดูให้ดีที่ response ที่ model ส่งกลับมา

```json
{
  "id": "call_mock_1",
  "type": "function",
  "function": {
    "name": "add",
    "arguments": "{\"a\": 2, \"b\": 3}"
  }
}
```

ค่าของ `arguments` ไม่ใช่ object มันคือ **string ที่บรรจุ JSON เอาไว้**
backslash พวกนั้นมีอยู่จริง ถ้าคุณเขียนแบบนี้

```python
arguments = raw["function"]["arguments"]
result = tools.run(raw["function"]["name"], arguments)
```

คุณจะส่ง string ไปในที่ที่ต้องการ dictionary และ `**arguments` จะ raise
อะไรประมาณ `TypeError: argument after ** must be a mapping, not str`
คนจ้องเรื่องนี้อยู่นาน เพราะการที่ response JSON มาถึงเป็น dictionary
ที่ถูก parse แล้วในทุกฟิลด์อื่น ทำให้ฟิลด์นี้ดูเป็นไปไม่ได้

วิธีแก้คือการเรียกครั้งเดียว

```python
"arguments": json.loads(raw["function"]["arguments"] or "{}"),
```

`json.loads` แปลง string ให้เป็น dictionary ของ Python จริง ๆ ส่วน `or "{}"`
รับมือกรณีที่ tool ไม่รับ arguments เลยและ provider ส่ง string ว่างมา
ซึ่ง `json.loads` จะไม่ยอมรับ

แล้วทำไมฟิลด์นี้ถึงเป็น string ตั้งแต่แรก เพราะ arguments ถูกสร้างโดย model
ทีละ token เหมือนกับที่มันสร้างข้อความร้อยแก้ว provider stream ตัวอักษรเหล่านั้น
ออกมาตามที่ผลิตได้ และไม่อยากรับปากว่ามันจะ parse ผ่าน การส่งข้อความดิบให้คุณ
แล้วให้คุณตัดสินใจเองนั้นซื่อตรงกว่าการซ่อมแซม JSON ที่พังแบบเงียบ ๆ ผลที่ตามมา
คือ `json.loads` อาจโยน exception ได้เมื่อ model ที่อ่อนกว่าผลิต arguments
ที่ผิดรูป ในบทนี้เราปล่อยให้ exception นั้นโผล่ขึ้นมาเพื่อให้คุณได้เห็น ใน agent
จริงคุณจะดักมันไว้แล้วป้อน parse error กลับไปให้ model เป็นผลลัพธ์ของ tool
ซึ่งมักจะกระตุ้นให้เกิดการลองครั้งที่สองที่ถูกต้อง

ฟิลด์สุดท้ายที่ควรเอ่ยถึง tool call ทุกตัวมี `id` ติดมาด้วย ในที่นี้คือ
`call_mock_1` เราเก็บมันไว้แม้ยังไม่มีอะไรใช้มัน ในบทที่ 04 คุณจะส่งผลลัพธ์
กลับไป และ message ผลลัพธ์นั้นต้องพก `tool_call_id` ที่ตรงกันไปด้วย เพื่อให้
model จับคู่คำตอบกับคำถามที่มันถามได้ การเก็บ id ไว้ตอนนี้ช่วยให้ไม่ต้องเขียน
parser ใหม่ทีหลัง

## 8. รัน check.py และอ่าน tool call

`check.py` สั้นมาก มันส่ง prompt หนึ่งอันพร้อมแนบ schema ไปด้วย ยืนกรานว่าต้อง
ได้ tool call กลับมา ตรวจสอบชื่อ tool และ arguments รัน tool แล้วตรวจผลลัพธ์

```python
"""Check that lesson 03 works."""
import sys

import tools
from llm import complete

PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'


def main():
    text, calls = complete([{"role": "user", "content": PROMPT}], tools.SCHEMAS)
    if not calls:
        print(f"FAIL the model answered in words instead of calling a tool. Text was {text!r}")
        print("If you are using a local model, see the troubleshooting section of the README.")
        sys.exit(1)
    call = calls[0]
    if call["name"] != "add" or call["arguments"] != {"a": 2, "b": 3}:
        print(f"FAIL unexpected call {call}")
        sys.exit(1)
    result = tools.run(call["name"], call["arguments"])
    if result != "5":
        print(f"FAIL running the tool gave {result!r}")
        sys.exit(1)
    print("OK the model asked for add(2, 3) and the tool returned 5")


if __name__ == "__main__":
    main()
```

ตั้งค่า environment ของคุณแล้วรันจากในโฟลเดอร์ของบทเรียน

```bash
cd lessons/03-tool-calling
export AGENTPATH_BASE_URL=http://localhost:11434/v1
export AGENTPATH_MODEL=qwen2.5:7b
export AGENTPATH_API_KEY=
python check.py
```

บน Windows PowerShell สิ่งเดียวกันหน้าตาแบบนี้

```powershell
cd lessons\03-tool-calling
$env:AGENTPATH_BASE_URL = "http://localhost:11434/v1"
$env:AGENTPATH_MODEL = "qwen2.5:7b"
python check.py
```

การรันที่ผ่านจะพิมพ์ออกมาบรรทัดเดียว

```text
OK the model asked for add(2, 3) and the tool returned 5
```

มันจืดชืดโดยตั้งใจ นี่คือสิ่งที่เดินทางไปมาจริง ๆ body ของ response
จาก endpoint หน้าตาแบบนี้

```json
{
  "id": "mock-1",
  "object": "chat.completion",
  "model": "mock",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_mock_1",
            "type": "function",
            "function": {
              "name": "add",
              "arguments": "{\"a\": 2, \"b\": 3}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

มีสามอย่างที่ควรอ่านตรงนี้

`content` เป็น `null` model ไม่ได้ตอบเป็นคำพูด parser ของเราเปลี่ยนมันเป็น
string ว่างด้วย `message.get("content") or ""` ซึ่งเป็นเหตุผลที่ `complete`
คืนค่า text ได้แม้ในเทิร์นที่เป็น tool call ล้วน ๆ

`finish_reason` เป็น `tool_calls` แทนที่จะเป็น `stop` แบบปกติ นี่คือ provider
บอกคุณว่าทำไมการสร้างข้อความจึงจบลง client บางตัวแตกกิ่งตามฟิลด์นี้แทนที่จะเช็ค
ว่า list ว่างหรือไม่ การเช็ค list ทนทานกว่า เพราะ provider ไม่ได้ตั้งค่าเหตุผลนี้
เหมือนกันทุกเจ้า

`tool_calls` เป็น list model อาจขอ tool หลายตัวในหนึ่งเทิร์นได้ และบทที่ 04
จะวนลูปผ่านทุกตัว ตรงนี้ `check.py` หยิบ `calls[0]` เพราะ prompt ถูกออกแบบมา
ให้ได้ผลลัพธ์เพียงหนึ่งตัวพอดี

หลังจาก parse แล้ว `complete` คืนคู่นี้กลับไปให้ `check.py`

```python
(
    "",
    [
        {
            "id": "call_mock_1",
            "name": "add",
            "arguments": {"a": 2, "b": 3},
        }
    ],
)
```

ตอนนี้ `arguments` เป็น dictionary จริง ๆ แล้ว และ `tools.run("add", {"a": 2, "b": 3})`
จะกระจายมันเป็น `add(a=2, b=3)` ซึ่งคืนค่า `5` แล้ว `str()` เปลี่ยนเป็น `"5"`

ถ้าคุณอยากดูทั้งคอร์สรันกับเซิร์ฟเวอร์ทดสอบแบบ deterministic แทนที่จะเป็น model
จริง ให้รันคำสั่งนี้จากรากของ repository

```bash
python ci/run_lessons.py
```

มันจะเริ่ม endpoint ปลอมบนเครื่อง ชี้ environment variables ไปที่มัน แล้วรัน
การตรวจของทุกบทตามลำดับ มันคือสคริปต์เดียวกับที่ continuous integration ใช้
ซึ่งพาเรามาถึงข้อความหน้าตาประหลาดใน prompt

## 9. ว่าด้วย directive ใน prompt

คุณต้องสังเกตเห็นส่วนต่อท้ายแปลก ๆ ใน `check.py` แน่นอน

```python
PROMPT = 'What is 2 plus 3? [[tool:add:{"a": 2, "b": 3}]]'
```

เครื่องหมายในวงเล็บนั้นคือ directive สำหรับเซิร์ฟเวอร์ทดสอบปลอมของโปรเจกต์นี้
ไวยากรณ์ของมันเรียบง่าย ชื่อ tool ตามด้วย arguments ที่แน่นอนในรูป JSON
ห่อด้วยวงเล็บเหลี่ยมคู่

```text
[[tool:NAME:{"argument": value}]]
```

เซิร์ฟเวอร์ปลอมอยู่ใน repository และพูดภาษา HTTP แบบเดียวกับ provider จริง
เมื่อมันเห็น directive ใน message สุดท้ายของผู้ใช้ มันจะตอบกลับด้วย tool call
สำหรับชื่อนั้นและ arguments เหล่านั้น เมื่อไม่มี directive มันจะตอบเป็นข้อความ
ธรรมดา เมื่อ message สุดท้ายเป็นผลลัพธ์ของ tool มันจะตอบเป็นข้อความที่ทวน
ผลลัพธ์นั้น

เหตุผลที่สิ่งนี้มีอยู่คือเรื่องเงินและความน่าเชื่อถือ คอร์สที่การทดสอบต้องใช้
API key แบบเสียเงินนั้น คนแปลกหน้าที่เพิ่ง clone repository มาก็รันไม่ได้
และรันทุกครั้งที่ push ใน continuous integration ไม่ได้โดยไม่มีใครสักคนถูกตัดบัตร
แย่กว่านั้น model จริงไม่ deterministic ชุดทดสอบที่สร้างบนมันจึงล้มเหลวแบบสุ่ม
และสอนให้คนมองข้าม build สีแดง เซิร์ฟเวอร์ปลอมให้การรันทดสอบที่ไม่มีค่าใช้จ่าย
ไม่ต้องใช้ key ทำงานแบบออฟไลน์ได้ และให้คำตอบเดิมทุกครั้ง

ส่วนสำคัญคือ directive นั้นไม่ได้เปลี่ยนบทเรียน ชี้ `check.py` ตัวเดิมไปที่ model
จริง แล้วเครื่องหมายนั้นก็เป็นแค่วรรคตอนแปลก ๆ ท้ายประโยค model อ่านคำถาม
ภาษาอังกฤษง่าย ๆ ที่วางอยู่ตรงหน้า เห็น tool ชื่อ `add` ใน list ของ schema
แล้วขอ `add` โดยให้ `a` เท่ากับ 2 และ `b` เท่ากับ 3 ทั้งสองเส้นทางมาถึง tool call
เดียวกัน การตรวจแบบเดียวกันจึงยืนยันได้ทั้งสองทาง

```text
real model    "What is 2 plus 3?"  ->  reasons about it  ->  add(2, 3)
fake server   "[[tool:add:{...}]]" ->  matches directive ->  add(2, 3)
```

เทคนิคนี้คุ้มค่าที่จะขโมยไปใช้ในโปรเจกต์ของคุณเอง เมื่อคุณสร้างอะไรบางอย่างบน
language model ตัว model คือส่วนที่ทดสอบได้ยากที่สุดในระบบของคุณ และยังเป็นส่วน
ที่ทุกคนโทษเวลาการทดสอบล้มเหลว วางของปลอมเล็ก ๆ ที่ deterministic ไว้หลัง
อินเทอร์เฟซ HTTP เดียวกัน บังคับทิศทางมันด้วย directive ที่ชัดเจน แล้วชี้ชุดทดสอบ
ของคุณไปที่มัน จากนั้นคุณจะได้ทดสอบโค้ดของตัวเอง ซึ่งเป็นส่วนที่คุณแก้ได้จริง
และชุดทดสอบของคุณจะรันเสร็จในไม่กี่มิลลิวินาทีโดยไม่เสียเงิน เก็บชุดทดสอบอีกชุด
ที่แยกออกมาและเล็กกว่ามากไว้ยิงไปที่ model จริง แล้วรันชุดนั้นเมื่อจำเป็น
แทนที่จะรันทุก commit

## 10. การแก้ปัญหาเมื่อ model ไม่ยอมเรียก tool

ไม่ช้าก็เร็ว `check.py` จะพิมพ์ข้อความนี้ออกมา

```text
FAIL the model answered in words instead of calling a tool. Text was 'The answer is 5.'
If you are using a local model, see the troubleshooting section of the README.
```

หายใจลึก ๆ นี่เป็นเรื่องปกติ โดยเฉพาะกับ model เล็ก ๆ ที่รันบนเครื่องตัวเอง
และมันไม่ใช่ความผิดพลาดในโค้ดของคุณ tool calling เป็นพฤติกรรมที่ต้องเรียนรู้
model ต้องถูกเทรนมาให้ปล่อย call ที่มีโครงสร้างเหล่านี้ และต้องเก่งพอที่จะรู้ว่า
เมื่อไรควรใช้ model จำนวนมากในระดับ 3 พันล้านพารามิเตอร์จะตอบว่า "5"
เป็นคำพูดอย่างสบายใจ ทั้งที่มี tool วางอยู่ตรงนั้นใน request บางตัวจะปล่อย
tool call ออกมาเป็นข้อความตรง ๆ ใน `content` แทนที่จะอยู่ในฟิลด์ `tool_calls`
ซึ่งเป็นความล้มเหลวแบบเดียวกันในเสื้อผ้าคนละชุด

ก่อนอื่น ยืนยันว่าความล้มเหลวเป็นอย่างที่คุณคิด ถ้าข้อความที่พิมพ์ออกมามีอะไร
ที่ดูเหมือน JSON แสดงว่า model พยายามแล้วแต่ใส่ผิดที่ ถ้าข้อความที่พิมพ์ออกมา
เป็นประโยคปกติ แสดงว่า model ไม่ได้พยายามเลย ไม่ว่าทางไหน นี่คือวิธีแก้สามข้อ
เรียงตามลำดับที่ควรลอง

วิธีที่หนึ่งคือใช้ model ที่ใหญ่กว่า นี่คือการเปลี่ยนแปลงที่น่าเชื่อถือที่สุด
และบ่อยครั้งเป็นสิ่งเดียวที่ต้องทำ ความสามารถด้าน tool calling เพิ่มขึ้นอย่างชัดเจน
ตามขนาดของ model และตามความใหม่ของช่วงเวลาที่เทรน ถ้าคุณรัน model ขนาด 1 พันล้าน
หรือ 3 พันล้านพารามิเตอร์บนเครื่อง ให้ย้ายไปใช้ตัวในช่วง 7 พันล้านถึง 14 พันล้าน
ที่ระบุการรองรับ tool ไว้ใน model card ของมัน มองหาวลีอย่าง function calling
หรือ tool use ในคำอธิบายก่อนที่คุณจะดาวน์โหลดหลายกิกะไบต์ เปลี่ยน environment
variable หนึ่งตัวแล้วรันใหม่

```bash
export AGENTPATH_MODEL=qwen2.5:14b
python check.py
```

วิธีที่สองคือทำให้คำอธิบายชัดเจนและเจาะจงขึ้น ส่วนที่ 5 บอกว่าคำอธิบายคือ
สิ่งเดียวที่ model เห็น และตรงนี้คือจุดที่มันเลิกเป็นทฤษฎี model ที่ก้ำกึ่ง
ต้องการแรงผลักที่หนักแน่นกว่า แก้ `tools.py` แล้วลองคำอธิบายที่บอกออกมาตรง ๆ
ว่าควรใช้ tool เมื่อไร

```python
"description": (
    "Add two numbers and return their exact sum. "
    "Always use this tool for any addition instead of computing the answer yourself, "
    "because it is exact and your mental arithmetic is not."
),
```

นั่นแข็งกร้าวกว่าที่สไตล์การเขียนที่ดีจะยอมให้ตามปกติ และมันได้ผล
รันการตรวจใหม่หลังแก้ไข ถ้าตอนนี้มันผ่าน คุณได้เรียนรู้บางอย่างที่ติดตัว
เกี่ยวกับว่าพฤติกรรมของ agent นั้นเป็น prompt engineering ที่ซ่อนอยู่ใน schema
มากแค่ไหน

วิธีที่สามคือย้ายไปใช้ model แบบ hosted บน free tier มี provider หลายเจ้าเสนอ
endpoint แบบ OpenAI compatible พร้อม free tier ที่เหลือเฟือสำหรับคอร์สนี้
เพราะทุกบทส่ง request เล็ก ๆ แค่ไม่กี่อัน พอ `llm.py` อ่าน endpoint
ของมันจาก environment variable การสลับจึงเสียแค่สองบรรทัดและไม่ต้องแก้โค้ดเลย

```bash
export AGENTPATH_BASE_URL=https://your-provider.example/v1
export AGENTPATH_API_KEY=your-key-here
export AGENTPATH_MODEL=the-model-name
python check.py
```

อย่า commit key นั้นเด็ดขาด เก็บมันไว้ใน shell profile ของคุณหรือในไฟล์บนเครื่อง
ที่ถูกระบุไว้ใน `.gitignore`

ถ้าทั้งสามวิธีล้มเหลว ให้ถอยกลับไปใช้เซิร์ฟเวอร์แบบ deterministic ด้วย
`python ci/run_lessons.py` จากรากของ repository นั่นจะพิสูจน์ว่างานเดินท่อของคุณ
ถูกต้องและแยกปัญหาไปที่ความสามารถของ model ซึ่งเป็นการแยกแบบที่ส่วนที่ 6
พยายามบอกไว้พอดี

มีปัญหาเล็ก ๆ อีกสองอย่างที่ควรรู้

ถ้าคุณเห็น `TypeError: argument after ** must be a mapping, not str` แสดงว่าคุณ
ทำการเรียก `json.loads` ตกไป กลับไปดูส่วนที่ 7

ถ้าคุณเห็น `KeyError: 'AGENTPATH_BASE_URL'` แสดงว่า environment variable ยังไม่ได้
ถูกตั้งใน shell นี้ การตั้งมันในเทอร์มินัลหนึ่งไม่ได้ทำให้มันถูกตั้งในอีกเทอร์มินัล

## 11. สิ่งที่คุณยังทำไม่ได้

รัน `check.py` อีกครั้งแล้วอ่าน output ด้วยสายตาที่วิพากษ์

```text
OK the model asked for add(2, 3) and the tool returned 5
```

tool คืนค่า 5 คืนให้ใคร คืนให้ `check.py` เลข `5` นั่งอยู่ในตัวแปร Python
ในสคริปต์ที่กำลังจะจบการทำงาน model ไม่รู้เลยว่าคำตอบคืออะไร มันถามคำถามไป
แล้วไม่เคยได้ยินอะไรกลับมา

คุณเห็นช่องว่างนั้นได้ในโค้ด `check.py` เรียก `tools.run` แล้วก็ print
ไม่มีการเรียก `complete` ครั้งที่สอง บทสนทนาหยุดกลางคันระหว่างการแลกเปลี่ยน

นั่นแปลว่าทั้งหมดนี้ยังเป็นไปไม่ได้

- ตอบผู้ใช้เป็นประโยค เพราะมีแต่ model ที่เขียนประโยคได้ และมันไม่รู้ผลลัพธ์
- ร้อยเรียง tool ต่อกัน เพราะการตัดสินใจว่าจะทำอะไรต่อต้องรู้ว่าเกิดอะไรขึ้น
  ครั้งก่อน
- กู้คืนจาก error ของ tool เพราะ model ไม่เคยเห็น error string ที่ `tools.run`
  อุตส่าห์สร้างขึ้นมาอย่างพิถีพิถัน

ทุกอย่างที่ขาดหายไปคือสิ่งเดียวกันที่ขาดหายไป ผลลัพธ์ไม่เคยกลับเข้าไปในบทสนทนา

การแก้ปัญหานี้ต้องใช้สองชิ้นส่วน message role ตัวใหม่ชื่อ `tool` ที่พกผลลัพธ์
และ `tool_call_id` ที่มันตอบอยู่ กับ loop ที่เรียก model ไปเรื่อย ๆ จนกว่ามัน
จะหยุดขอ tool และตอบเป็นคำพูดแทน

สองชิ้นส่วนนั้นคือ agent นั่นคือบทที่ 04
