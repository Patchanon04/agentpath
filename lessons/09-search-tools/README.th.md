[Read in English](README.md)

# บทที่ 09 เครื่องมือค้นหา

บทนี้สั้นที่สุดในภาคสอง และเป็นบทที่ส่งผลมากที่สุดบทหนึ่ง คุณกำลังจะเพิ่ม tool
สองตัว การเดินไฟล์ที่ใช้ร่วมกันหนึ่งชุด และไฟล์ที่สองเล็ก ๆ อีกหนึ่งไฟล์ที่รันใน
process ของตัวเอง แล้ว agent จะเลิกเป็นสิ่งที่คุณต้องชี้ไปที่ไฟล์ให้ และกลายเป็น
สิ่งที่หาทางเดินใน code base ได้ด้วยตัวเอง

คุณจะใช้เวลาอีกส่วนยาวไปกับสิ่งที่คุณจะไม่สร้าง และส่วนนั้นสำคัญพอ ๆ กับโค้ด
เกือบทุกคนที่มาถึงจุดนี้ในคอร์สคาดว่าคำถัดไปคือ embeddings แต่มันไม่ใช่ และเหตุผล
ก็คุ้มที่จะเข้าใจให้ถ่องแท้ แทนที่จะเชื่อไปตามที่บอก

ไฟล์ในโฟลเดอร์นี้

```text
lessons/09-search-tools/
  tools.py       lesson 08's tools, plus glob_files and grep_files at the bottom
  grep_worker.py the half of grep_files that runs in a separate process
  providers.py   unchanged from lesson 06
  agent.py       unchanged from lesson 06
  check.py       proves the two new tools work and that .venv is skipped
  README.md      this file
```

`tools.py` เปลี่ยน และ `grep_worker.py` เป็นไฟล์ใหม่ ส่วน `agent.py` และ
`providers.py` เหมือนเดิมทุกไบต์กับเมื่อสามบทก่อน เรื่องนี้น่าสังเกตในตัวมันเอง
loop เรียนรู้ความสามารถใหม่ได้โดยไม่ต้องแก้แม้แต่บรรทัดเดียว เพราะ tool คือ
schema บวกกับ function ใน dictionary เท่านั้น และไม่มีส่วนอื่นของโปรแกรมที่ต้อง
รู้เรื่องนี้

`grep_worker.py` คือไฟล์ที่น่าแปลกใจในรายการนั้น และหัวข้อ 5 คือที่ที่มันถูก
อธิบายอย่างละเอียด ฉบับย่อคือ regular expression ที่ model เขียนอาจรันนานกว่าอายุ
ของจักรวาล ไม่มีอะไรใน process ที่กำลังรันมันทำให้มันหยุดได้ และสิ่งเดียวที่คุณ
ฆ่าได้อย่างแน่นอนคืออีก process หนึ่ง การแมตช์จึงเกิดขึ้นใน process นั้น

## 1. ปัญหาที่ค้างมาจากบทที่ 08

บทที่ 07 ให้ agent มีสี่วิธีในการแตะไฟล์ และบทที่ 08 ให้ shell กับมัน นี่คือ
รายการทั้งหมดของสิ่งที่มันทำได้ตอนนี้

| Tool | สิ่งที่มันต้องการจากคุณ |
| --- | --- |
| `read_file` | path ที่ถูกต้องแม่นยำ |
| `write_file` | path ที่ถูกต้องแม่นยำ |
| `edit_file` | path ที่ถูกต้องแม่นยำ บวกข้อความที่จะแทนที่แบบตรงเป๊ะ |
| `list_files` | directory ที่ถูกต้องแม่นยำ |
| `run_shell` | คำสั่ง และการอนุมัติจากคุณ |

อ่านคอลัมน์ขวามือดู สี่ในห้า tool ต้องการให้คุณรู้อยู่แล้วว่าสิ่งนั้นอยู่ที่ไหน
agent ตอบคำถามว่า "function ที่ parse tool arguments อยู่ตรงไหน" ไม่ได้ ถ้าคุณ
ไม่ตอบให้มันก่อน

ลองดูว่าจะเกิดอะไรขึ้นจริงถ้าคุณถามไปเลย agent มี `list_files` มันจึงไต่ไปได้
repository นี้มี 42 directory และไฟล์ Python 251 ไฟล์ เมื่อไม่นับ virtual
environment กับ git store ดังนั้น agent เรียก `list_files` ที่ root เห็น `src/`
เรียกอีกครั้ง เห็น `src/agentpath/` เรียกอีกครั้ง แล้วไล่ลงไปเรื่อย ๆ นั่นคือ
การวิ่งไปกลับหา model 42 รอบก่อนที่มันจะได้อ่านโค้ดแม้แต่บรรทัดเดียว และทุกรอบคือ
HTTP request เต็มรูปแบบที่แบกบทสนทนาทั้งหมดที่ผ่านมาไปด้วย

จากนั้นมันเริ่มเดาว่าจะเปิดไฟล์ไหน `read_file` คืนค่าได้สูงสุด 4000 ตัวอักษร ซึ่ง
คือ `MAX_OUTPUT` ที่คุณเขียนไว้ในบทที่ 07 ไฟล์ 251 ไฟล์นั้นมี source รวมกัน
987,154 ตัวอักษร ซึ่งประมาณ 247,000 token ถ้า agent อ่านทั้งหมดเพื่อหา function
เดียว มันได้เท token 247,000 ตัวลงในบทสนทนาไปแล้ว และเพราะบทสนทนาถูกส่งซ้ำ
ทั้งก้อนในทุก request ถัดไป มันจึงจ่ายค่า token พวกนั้นซ้ำในทุกเทิร์นไปตลอด
เซสชัน บทที่ 02 สอนคุณว่า model ไม่มีความจำ และ history คือความจำ นี่คือใบเรียก
เก็บเงินของเรื่องนั้นที่มาถึงแล้ว

และนั่นคือกรณีที่ดี ตอนที่ agent ใจเย็น กรณีที่เกิดขึ้นจริงคือหลังจากอ่านสี่ห้า
ครั้งมันหมดงบหรือหมดความอดทน เดา แล้วแก้ผิดไฟล์

ในทางปฏิบัติคุณจึงไม่ปล่อยให้มันไต่ คุณทำแบบนี้แทน

```text
You: the tool argument parsing is in src/agentpath/providers/base.py,
     around line 47, add a check for a null argument object
```

ดูให้ดีว่าเกิดอะไรขึ้นตรงนั้น คุณเปิด editor คุณค้นหา คุณเจอไฟล์ คุณเจอบรรทัด
แล้วคุณพิมพ์มันลงในกล่องแชทเพื่อให้ language model พิมพ์งานให้ คุณเป็นคนหา และ
มันเป็นคนพิมพ์ นั่นคือสลับกันพอดี การหาคือส่วนที่เครื่องจักรเก่งและคุณช้า การ
พิมพ์คือส่วนที่คุณทำได้สบายอยู่แล้ว

tool สองตัวถัดจากนี้มีจุดประสงค์เดียว คือพลิกมันกลับให้ถูกทาง

## 2. สองวิธีที่มนุษย์ใช้หาของใน code base

หยุดคิดสักครู่ว่าคุณทำอะไรจริง ๆ เวลาเปิด repository ที่ไม่คุ้นเคยแล้วต้องหาอะไร
สักอย่าง ไม่ใช่สิ่งที่คุณคิดว่าควรทำ แต่คือสิ่งที่มือคุณทำ

มีสองท่า และมีแค่สองท่า

**คุณหาไฟล์จากชื่อของมัน** คุณรู้ว่ามันชื่อประมาณ `settings` หรือรู้ว่ามันเป็น
test หรือรู้ว่ามันลงท้ายด้วย `.tsx` ใน editor นี่คือ fuzzy file finder กล่องที่
เด้งขึ้นมาตอนคุณกด control p บน command line มันคือ `find` หรือ `ls` คุณกำลังค้น
บนชื่อไฟล์ ไม่ใช่เนื้อหาไฟล์

**คุณหาข้อความข้างในไฟล์** คุณรู้สตริงที่ปรากฏในโค้ด ชื่อ function ข้อความ error
ที่ผู้ใช้แจ้งมา key ของ configuration หรือตัวเลขประหลาดสักตัว คุณไม่รู้ว่ามันอยู่
ในไฟล์ไหน และตอนนี้คุณยังไม่สนใจ ใน editor นี่คือการค้นข้ามไฟล์ บน command line
มันคือ `grep`

นั่นคือชุดเครื่องมือทั้งหมด ลองดูวิศวกรระดับซีเนียร์ที่ลงไปใน codebase ที่ไม่เคย
เห็นมาก่อน เขาจะใช้สองท่านี้สลับกัน แล้วค่อย ๆ แคบเข้าไปเรื่อย ๆ grep หาข้อความ
error ได้มาสามไฟล์ glob หา test ที่อยู่ใกล้ไฟล์หนึ่งในนั้น อ่าน test grep หา
helper ที่ test นั้น import อ่านมัน จบ

ทีนี้มาถึงข้อเสนอของบทนี้ ซึ่งหนักแน่นกว่าที่เห็น

tool สองตัวเดียวกันนี้คือทั้งหมดที่ coding agent ต้องการ ไม่ใช่ชุดย่อ ๆ ไว้เริ่ม
ต้น ไม่ใช่ของขัดตาทัพจนกว่าคุณจะสร้างของจริง แต่คือคำตอบที่ถูกต้อง

เหตุผลคือ agent ทำงานในสื่อเดียวกับคุณ โค้ดถูกเขียนโดยคนที่ตั้งชื่อสิ่งต่าง ๆ
อย่างตั้งใจ เพื่อให้คนอื่นหามันเจอ function ที่ชื่อ `parse_arguments` ถูกตั้งชื่อ
แบบนั้นอย่างจงใจ ข้อความ error เป็นสตริงที่ไม่ซ้ำใครอย่างจงใจ ไฟล์ test ถูกตั้ง
ชื่อตามสิ่งที่มันทดสอบอย่างจงใจ code base ไม่ใช่กองข้อความไร้รูปร่างที่ต้องค้นหา
ด้วยความหมาย มันคือโครงสร้างที่ถูก index ด้วยมือไปแล้ว โดยนักพัฒนาทุกคนที่เลือก
ชื่อ และ index นั้นก็คือชื่อเหล่านั้นเอง

มีเหตุผลที่สอง และมันเกี่ยวกับ loop มากกว่าตัว tool agent ของคุณไม่ได้มีโอกาส
แค่ครั้งเดียว มันค้นหา อ่านผลลัพธ์ แล้วค้นหาอีกครั้งด้วยสิ่งที่เพิ่งเรียนรู้
บทที่ 04 สร้าง loop แบบนั้นพอดี และบทที่ 08 พิสูจน์ว่ามันรอดจาก shell จริงได้
tool หยาบ ๆ สองตัวที่อยู่ใน loop ซึ่งปรับแก้ตัวเองได้ มีค่ามากกว่า tool ฉลาด ๆ
ตัวเดียวที่มีสิทธิ์ลองแค่ครั้งเดียว และเนื้อหาที่เหลือของบทนี้จะวนกลับมาที่ข้อ
เท็จจริงนี้ตลอด

ดังนั้นเมื่อดีไซน์ตรงนี้ดูเรียบง่ายเกินไป นั่นไม่ใช่การประนีประนอมเพื่อทำ
tutorial การให้ tool สองตัวเดียวกับที่นักพัฒนาใช้แก่ agent คือคำตอบที่ถูกต้อง
และหัวข้อ 3 จะอธิบายว่าทำไมทางเลือกที่ดูน่าประทับใจกว่ามักเป็นทางเลือกที่ผิด

## 3. ตรงนี้คือจุดที่คนคาดว่าจะเจอ vector database และเหตุผลที่เราไม่สร้างมัน

ถ้าคุณเคยอ่านอะไรเกี่ยวกับการสร้างของด้วย language model ในไม่กี่ปีมานี้ คุณคง
เคยเจอวลี retrieval augmented generation ซึ่งมักย่อว่า RAG มันน่าจะเป็นสิ่งที่
คุณคาดว่าบทนี้จะพูดถึง งั้นเรามาให้ความสำคัญกับมัน อธิบายมันอย่างถูกต้อง แล้ว
พูดตรง ๆ ว่ามันเหมาะกับที่ไหน

### retrieval augmented generation หมายถึงอะไรจริง ๆ

ไอเดียนี้เริ่มจากข้อจำกัดที่มีจริง model เห็นได้แค่สิ่งที่อยู่ในบทสนทนา และบท
สนทนามีขีดจำกัดด้านขนาด ถ้าคุณมีเอกสารหมื่นหน้า คุณแปะมันเข้าไปไม่ได้ คุณจึงหา
เอกสารไม่กี่หน้าที่เกี่ยวข้องกับคำถาม แล้วแปะเฉพาะหน้าเหล่านั้น retrieval แล้ว
augmentation ของ prompt แล้วจึง generation จึงเป็นที่มาของชื่อ

ส่วนที่น่าสนใจคือคุณตัดสินอย่างไรว่าอะไรเกี่ยวข้อง คำตอบมาตรฐานมีสามขั้น

**Chunking** คุณตัดทุกเอกสารเป็นชิ้นเล็กพอที่จะใส่ใน prompt ได้ อาจจะราวห้าร้อย
คำต่อชิ้น มักมีส่วนซ้อนทับเล็กน้อยระหว่างชิ้นที่ติดกัน เพื่อไม่ให้ประโยคที่คร่อม
เส้นแบ่งหายไป

**Embedding** คุณส่งแต่ละ chunk ไปยัง model ที่มีหน้าที่ไม่ใช่เขียนข้อความ แต่
แปลงข้อความเป็นรายการตัวเลข โดยทั่วไปหลายร้อยตัวหรือสองสามพันตัว รายการนั้นเรียก
ว่า vector หรือ embedding คุณสมบัติที่มีประโยชน์คือข้อความที่มีความหมายใกล้เคียง
กันจะได้ vector ที่อยู่ใกล้กันในสเปซนั้น แม้จะไม่มีคำร่วมกันเลยก็ตาม "The cat
sat on the mat" กับ "a feline was resting on the rug" จะไปตกอยู่ใกล้กัน คุณเก็บ
vector ทั้งหมดไว้ใน database ที่ถูกสร้างมาเพื่อตอบคำถามเดียวอย่างรวดเร็ว นั่นคือ
"vector ที่เก็บไว้ตัวไหนใกล้ตัวนี้ที่สุด"

**เวลาที่มี query** เมื่อคำถามมาถึง คุณ embed คำถามด้วยวิธีเดียวกัน ถาม database
เอา chunk ที่ใกล้ที่สุดสิบชิ้น แล้วแปะสิบ chunk นั้นลงใน prompt

มันเป็นเทคนิคที่ดีจริง มันแก้ปัญหาที่มีอยู่จริง เหตุผลที่มันโด่งดังคือมันได้ผล

### ทำไมมันไม่เข้ากับโค้ด

ทีนี้ลองเอาทั้งสามขั้นนั้นไปใช้กับไฟล์ Python แล้วดูว่าอะไรพัง

**Chunking ทำลายโครงสร้างที่ทำให้โค้ดมีความหมาย** หน้าต่างขนาดห้าร้อยคำที่เลื่อน
ผ่าน source code ไม่เคารพอะไรเลย มันตัด function ครึ่งหนึ่ง มันแยก decorator ออก
จาก function ที่มัน decorate แยก `try` ออกจาก `except` แยก class ออกจาก method
ที่ให้ความหมายกับมัน แย่กว่านั้นคือมันปอก context ที่บอกคุณว่ากำลังดูอะไรอยู่
chunk ที่มี method ชื่อ `run` อาจไม่มีชื่อ class ไม่มี imports ไม่มี path ของไฟล์
และเมื่อขาดสิ่งเหล่านั้น chunk แทบไร้ความหมาย ร้อยแก้วเสื่อมคุณภาพอย่างนุ่มนวล
เมื่อคุณตัดผิดที่ แต่โค้ดไม่เป็นแบบนั้น body ของ function ที่ไม่มี signature
ไม่ใช่เวอร์ชันที่แย่ลงนิดหน่อยของ function นั้น มันคือเศษชิ้นส่วนที่จะเป็นของ
อะไรก็ได้

**ชื่อ function เป็น search key ที่ยอดเยี่ยมอยู่แล้ว** นี่คือประเด็นที่ทำงานหนัก
ที่สุด เหตุผลทั้งหมดที่ embedding น่าประทับใจคือมันหาข้อความที่มีความหมายเดียวกัน
แต่ใช้คำต่างกันได้ นั่นคือพลังพิเศษเมื่อคลังข้อมูลของคุณเป็นร้อยแก้วที่เขียนโดย
คนหลายคนซึ่งเลือกใช้คำต่างกันสำหรับไอเดียเดียวกัน แต่มันแทบไร้ค่าเมื่อสิ่งที่คุณ
กำลังหามีการสะกดแบบเดียวเป๊ะ ที่ปรากฏเหมือนกันทุกที่ที่ถูกใช้ ถ้าคุณอยากได้
นิยามของ `parse_arguments` การ grep หา `parse_arguments` ก็เจอมัน เจอทุกจุดที่
เรียกใช้ และไม่เจออย่างอื่นเลย ไม่มีปัญหาเรื่องคำพ้องความหมายให้แก้ เพราะภาษา
โปรแกรมไม่มีคำพ้องความหมาย ชื่อหนึ่งไม่ตรงก็เป็นคนละชื่อ และ compiler บังคับ
เรื่องนี้เข้มงวดกว่าที่ embedding model ใด ๆ จะประมาณได้

**index เก่าทันทีที่ไฟล์เปลี่ยน** ข้อนี้ร้ายแรงในแบบที่คนมักประเมินต่ำเกินไป
จุดประสงค์ทั้งหมดของ agent คือแก้โค้ด วินาทีที่มันเขียนไฟล์ ทุก chunk จากไฟล์นั้น
ก็ผิดทันที และ vector ทุกตัวที่สร้างจาก chunk เหล่านั้นก็ผิดด้วย ตอนนี้คุณต้อง
rebuild ถ้า rebuild ทั้ง index repository ขนาดกลางจะกินเวลาคุณหลายนาที บวกกับ
กอง embedding API call ในทุกครั้งที่แก้ไข ถ้า rebuild แบบ incremental คุณต้องตาม
ให้ทันว่า chunk ไหนมาจากไฟล์เวอร์ชันไหน ซึ่งคือปัญหา cache invalidation และนั่นก็คือ
สิ่งที่ทุกคนยกมาอ้างว่าเป็นหนึ่งในสองปัญหายากของวิทยาการคอมพิวเตอร์ เทียบกับ
`grep` ที่ไม่มี index เก่าไม่ได้ และเห็นไฟล์ที่ agent เพิ่งเขียนเมื่อหนึ่ง
มิลลิวินาทีก่อน เพราะมันอ่านจากไฟล์จริง

**การค้นด้วยความคล้ายครั้งเดียวปรับแก้ไม่ได้ แต่ agent ทำได้** vector query คือ
การยิงครั้งเดียว คุณ embed คำถาม คุณได้ chunk ที่ใกล้ที่สุดสิบชิ้น และนั่นคือคำ
ตอบที่คุณต้องใช้ ไม่มีความพยายามครั้งที่สองที่ได้ข้อมูลจากครั้งแรก เพราะไม่มี
อะไรในผลลัพธ์ที่บอกคุณว่าจะถามให้ดีขึ้นได้อย่างไร

loop ของ agent ตรงข้ามกับสิ่งนั้น ลองดูลำดับจริง

```text
grep_files("MCPError")                        -> 30 hits in 6 files
grep_files("class MCPError", "src/**/*.py")   -> 1 hit, src/agentpath/mcp.py:27
read_file("src/agentpath/mcp.py")
glob_files("test_mcp*.py")                    -> tests/test_mcp.py, the test that covers it
read_file the test
```

แต่ละขั้นถูกเลือกเพราะสิ่งที่ขั้นก่อนหน้าคืนกลับมา นั่นคือกลยุทธ์การค้นหา ไม่ใช่
การเปิดตาราง และมันเป็นไปได้เพราะ tool ถูกพอที่จะเรียกสี่ครั้ง และแม่นพอที่ผล
ลัพธ์ของอันหนึ่งบอกคุณว่าต้องถามอะไรต่อ chunk สิบชิ้นที่เกี่ยวข้องกันอย่างหลวม ๆ
ทำแบบนั้นไม่ได้ ไม่ว่า embedding model จะดีแค่ไหน

รวมสี่ข้อนี้เข้าด้วยกัน แล้วข้อสรุปก็ไม่สูสีเลย สำหรับโค้ด การค้นหาแบบธรรมดา
เร็วกว่า ถูกกว่า ทันสมัยเสมอ ไม่ต้องมี infrastructure และประกอบเข้ากับ loop ได้

### เครื่องมือที่คนใช้จริงทำงานแบบนี้

นี่ไม่ใช่จุดยืนแบบขวางโลกที่ตั้งขึ้นเพื่อคอร์ส มันคือสิ่งที่ coding agent ระดับ
จริงจังทำกัน ลองดูรายการ tool ที่พวกมันเปิดเผยออกมา แล้วคุณจะเจอตัวจับคู่ชื่อไฟล์
กับตัวค้นเนื้อหา มักมีตัวเลือกให้จำกัดการค้นด้วย glob และคืนชื่อไฟล์กับหมายเลข
บรรทัด บางตัวเรียกออกไปหา `ripgrep` แทนที่จะเดินต้นไม้ด้วยภาษาของตัวเอง นั่นคือ
การตัดสินใจเรื่องประสิทธิภาพ และหัวข้อ 8 พูดถึงมัน แต่รูปทรงของ tool คือรูปทรง
เดียวกับที่คุณกำลังจะเขียน

ถ้าคุณเคยใช้ agent พวกนั้นและเฝ้าดู tool call ไหลผ่านหน้าจอ คุณเห็นเรื่องนี้มา
แล้ว มัน grep มันอ่านไฟล์รอบ ๆ จุดที่เจอ มัน grep อีกครั้งด้วย pattern ที่แคบลง
ไม่มี vector database ใน trace นั้น เพราะไม่จำเป็นต้องมี

### จุดที่ vector search ชนะจริง ๆ

ทีนี้มาถึงส่วนที่แฟร์ เพราะข้อโต้แย้งข้างบนเป็นเรื่องของโค้ด และมันไม่ได้ขยาย
ผลไปทั่วแบบที่คนทั้งสองฝ่ายในการถกเถียงนี้มักอ้าง

vector search ชนะอย่างชัดเจนและชนะขาด เมื่อมีสามสิ่งเป็นจริงพร้อมกัน

**คลังข้อมูลใหญ่และเป็นร้อยแก้วที่ไม่มีโครงสร้าง** ตั๋ว support งานวิจัย เอกสาร
นโยบาย หน้า wiki ภายใน บทถอดเสียง อีเมลหลายปี ข้อความที่ไม่มีวินัยการตั้งชื่อ
เขียนโดยคนหลายคนตลอดช่วงเวลายาวนาน

**คำถามเป็นเรื่องความหมายมากกว่าตัวคำ** "นโยบายการคืนเงินสำหรับแพ็กเกจรายปีของ
เราคืออะไร" ต้องจับคู่กับเอกสารที่เขียนว่า "yearly subscriptions may be
reimbursed within thirty days" และไม่เคยใช้คำว่า refund หรือคำว่า policy เลย
การค้นด้วย keyword ล้มเหลวโดยสิ้นเชิงกับเรื่องนี้ นี่คือปัญหาคำพ้องความหมาย และ
embedding แก้มันได้จริง

**คลังข้อมูลเปลี่ยนช้า** knowledge base ที่ rebuild ทุกคืนก็เพียงพอ ความเก่าของ
ข้อมูลทำให้คุณเสียหนึ่งวัน ไม่ใช่หนึ่งมิลลิวินาที และไม่มีใครมาแก้คลังข้อมูล
ระหว่างที่ query กำลังทำงาน

สถานการณ์เหล่านั้นมีจริงและพบบ่อย ถ้างานของ agent คือการตอบคำถามบนตั๋ว support
หมื่นใบ ก็สร้าง vector index เถอะ อย่าให้บทนี้พูดจนคุณเลิกทำ ความผิดพลาดไม่ใช่
การใช้ embedding ความผิดพลาดคือการคว้ามันมาใช้เป็นค่าเริ่มต้นเพราะมันฟังดูซับซ้อน
โดยไม่ตรวจสอบว่าคลังข้อมูลของคุณมีคุณสมบัติสามข้อที่ทำให้มันคุ้มหรือไม่

ยังมีทางสายกลางที่ควรรู้ว่ามีอยู่ ระบบจริงมักผสมการค้นด้วย keyword กับ vector
search เอารายการผลลัพธ์ทั้งสองมารวมกัน นั่นเรียกว่า hybrid retrieval และมันชนะ
วิธีใดวิธีหนึ่งเพียงลำพังอยู่บ่อยครั้ง

บทที่ 16 ในภาคสาม พูดถึงการตัดสินใจเรื่องนี้อย่างถูกต้องล้วน ๆ มันพาไล่ดูคุณสมบัติ
ของคลังข้อมูล โมเดลต้นทุน คำถามเรื่องความเก่าของข้อมูล และสร้าง vector index เล็ก
ๆ เพื่อให้คุณวัดความต่างได้ด้วยตัวเองแทนที่จะเถียงกัน บทนี้ไม่ใช่ข้อโต้แย้งที่
ต่อต้าน retrieval มันคือข้อโต้แย้งให้ตรวจสอบก่อน และสำหรับโค้ด ผลการตรวจสอบออกมา
เข้าข้าง tool สองตัวที่คุณรู้จักอยู่แล้ว

## 4. เขียน glob_files

เปิด `tools.py` แล้วเลื่อนไปล่างสุด ทุกอย่างเหนือเครื่องหมายของบทที่ 09 ไม่ถูกแตะต้อง

```python
# Lesson 09 adds the search tools. Everything above is unchanged from lesson 08.

import json
import subprocess
import sys
import fnmatch  # noqa: E402
import re  # noqa: E402

MAX_RESULTS = 200
```

ห้าโมดูลจาก standard library และเพดานใหม่หนึ่งค่า หัวข้อ 7 พูดถึงเพดานนั้น
`fnmatch` กับ `re` ทำหน้าที่จับคู่ ส่วน `json` `subprocess` และ `sys` อยู่ตรงนี้
เพราะครึ่งหนึ่งของ `grep_files` รันอยู่ที่อื่น ซึ่งคือหัวข้อ 5

### การเดินต้นไม้

tool ทั้งสองตัวต้องการสิ่งเดียวกันก่อน นั่นคือวิธีเยี่ยมชมทุกไฟล์ที่ควรค่าแก่การ
เยี่ยมชม สิ่งนั้นได้ function ของตัวเอง

```python
def _walk():
    """Yield every file in the workspace that a search is allowed to look at.

    Two exclusions happen here. Directories such as .venv are skipped because
    searching them buries the real answer in thousands of irrelevant hits.
    Credential files are skipped because otherwise search would be a way
    around the refusal in read_file, and a rule that one tool honours and
    another ignores is not a rule at all.
    """
    for path in WORKSPACE.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(WORKSPACE)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
        try:
            # The same gate every file tool uses, rather than a check on the
            # name. rglob follows symlinks and Windows junctions, so a link
            # planted inside the workspace would otherwise let search read
            # anything on the machine while read_file correctly refused.
            # Looking at the name of the link never sees the name of what it
            # points at.
            resolve_inside(str(relative))
        except WorkspaceError:
            continue
        yield path
```

`WORKSPACE` `SKIP_DIRECTORIES` และ `resolve_inside` มาจากบทที่ 07 ทั้งหมด
และถูกนำมาใช้ซ้ำโดยไม่เปลี่ยน `rglob("*")` เดินทั้งต้นไม้แบบ recursive
และให้ทั้งไฟล์และ directory ออกมา จึงเป็นเหตุผลที่มีการเช็ค `is_file()` อยู่ตรงนั้น
ขีดล่างนำหน้าชื่อคือธรรมเนียมของ Python ที่แปลว่า "อันนี้ใช้ภายใน ไม่ใช่หนึ่งใน tool"

การตรวจสอบสองอันในนั้นเป็นการปฏิเสธ ไม่ใช่ท่อส่งของ และแต่ละอันได้หัวข้อของตัวเอง
การเช็ค `SKIP_DIRECTORIES` คือหัวข้อ 6 และมันเป็นเรื่องต้นทุน ส่วนการเรียก
`resolve_inside` คือหัวข้อ 5 และมันเป็นเรื่อง key ที่คุณเอาออกจากบทสนทนาไม่ได้
อีกเลย และเรื่องลิงก์ที่พาออกไปนอก workspace ทั้งดุ้น

มันเป็น generator ซึ่งสำคัญกว่าที่เห็น `yield` แปลว่าไฟล์ทยอยออกมาทีละไฟล์ตามที่
การเดินคืบหน้าไป แทนที่จะถูกเก็บรวมเป็น list ก่อน บนต้นไม้ขนาดใหญ่นั่นคือความ
ต่างระหว่างการถือ path เดียวไว้ในหน่วยความจำกับการถือแสน path และมันยังเป็นสิ่งที่
ทำให้ worker ของ grep หยุดเดินก่อนกำหนดได้ในหัวข้อ 7

หัวข้อ 6 พูดถึงบรรทัด `SKIP_DIRECTORIES`

### fnmatch

ทีนี้มาถึงตัว tool เอง

```python
def glob_files(pattern):
    matches = []
    for path in _walk():
        relative = path.relative_to(WORKSPACE).as_posix()
        if path_matches(relative, path.name, pattern):
            matches.append(relative)
    if not matches:
        return f"no files match {pattern}"
    return truncate("\n".join(sorted(matches)[:MAX_RESULTS]))
```

`fnmatch` คือโมดูลใน standard library ที่ตอบคำถามเดียว ชื่อนี้ตรงกับ pattern แบบ
shell นี้หรือไม่ มันรู้อยู่สี่อย่างและไม่รู้อย่างอื่นเลย

| Pattern | ความหมาย |
| --- | --- |
| `*` | ตัวอักษรกี่ตัวก็ได้ติดกัน รวมถึงศูนย์ตัว |
| `?` | ตัวอักษรหนึ่งตัวพอดี |
| `[abc]` | ตัวอักษรหนึ่งตัวจากเซตนี้ |
| `[!abc]` | ตัวอักษรหนึ่งตัวที่ไม่อยู่ในเซตนี้ |

นั่นคือทั้งภาษา มันคือ syntax ของ wildcard เดียวกับที่ shell ของคุณใช้เวลาคุณ
พิมพ์ `ls *.py` ซึ่งเป็นเหตุผลตรง ๆ ว่าทำไมมันจึงเป็นตัวเลือกที่ถูกต้องตรงนี้
model ได้อ่าน shell มามาก และอ่านเอกสารมามาก มันจึงรู้วิธีเขียน `*.py` และ
`test_*.py` อยู่แล้วโดยไม่ต้องสอน การเลือก syntax ที่ model พูดได้อยู่แล้วเป็น
ข้อพิจารณาด้านการออกแบบที่มีน้ำหนักจริง และจะกลับมาอีกในบทที่ 10

`as_posix()` อยู่ตรงนั้นเพื่อ Windows บน Windows คลาส `Path` แสดงตัวคั่นเป็น
backslash ดังนั้น relative path จะออกมาเป็น `src\main.py` และ model ที่อ่าน glob
pattern มาเป็นล้านครั้งจะส่ง `src/*.py` ด้วย forward slash แล้วไม่มีวันจับคู่ได้
`as_posix()` บังคับให้เป็น forward slash ดังนั้น pattern เดียวกันจึงทำงานเหมือน
กันบนทุกระบบปฏิบัติการ นี่คือบรรทัดเล็ก ๆ ที่ป้องกันบั๊กซึ่งวินิจฉัยแล้วน่า
หงุดหงิดมาก เพราะ tool ทำงานได้สมบูรณ์แบบสำหรับคนที่เขียนมัน แต่คืนค่าว่างเปล่า
เงียบ ๆ ให้กับผู้อ่านอีกครึ่งหนึ่งของคุณ

### ทำไมเราจับคู่สามครั้ง

นี่คือโค้ดที่สมควรได้รับความสนใจมากที่สุด และมันไม่ได้อยู่ใน `glob_files` เลย
มันเป็น helper ที่มีชื่อของตัวเอง เพราะ `grep_files` ต้องตัดสินใจเรื่องเดียวกัน
เป๊ะ ๆ และกฎที่ถูกเขียนไว้สองที่คือกฎที่วันหนึ่งจะขัดกันเอง

```python
def path_matches(relative, name, pattern):
    """Decide whether one file matches a glob the way a person would expect.

    Three attempts are made because fnmatch is stricter than people are. The
    pattern is tried against the path inside the workspace, then against the
    bare file name so that main.py works from anywhere, and then with a
    leading star star slash removed so that a pattern like **/*.py also
    finds files sitting at the top level. Without that third attempt the
    most common pattern a model writes silently misses every file that is
    not inside a subdirectory.
    """
    if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern):
        return True
    return pattern.startswith("**/") and fnmatch.fnmatch(relative, pattern[3:])
```

ทุกไฟล์ถูกทดสอบได้ถึงสามครั้ง ครั้งหนึ่งกับ relative path เต็ม ๆ เช่น
`src/agentpath/tools/search.py` ครั้งหนึ่งกับชื่อเปล่า ๆ ซึ่งก็คือ `search.py`
และอีกครั้งกับ path เดิม โดยตัด `**/` ที่นำหน้า pattern ออก ตรงอันไหนก็นับทั้งนั้น

เหตุผลคือ `fnmatch` มีคุณสมบัติหนึ่งที่ทำให้คนแปลกใจ `*` ของมันจับคู่กับตัวอักษร
อะไรก็ได้ รวมถึงตัวคั่น path ด้วย มันไม่ใช่การ glob ที่รู้เรื่อง directory แบบที่
git หรือ shell ของคุณทำ ลองรันดูเองแล้วพฤติกรรมจะชัดเจน

```python
>>> import fnmatch
>>> fnmatch.fnmatch("src/main.py", "*.py")
True
>>> fnmatch.fnmatch("agent.py", "**/*.py")
False
>>> fnmatch.fnmatch("tests/test_x.py", "test_*.py")
False
>>> fnmatch.fnmatch("test_x.py", "test_*.py")
True
```

อ่านผลลัพธ์สี่อันนั้นตามลำดับ เพราะแต่ละอันอธิบายส่วนหนึ่งของการออกแบบ

อันแรกบอกว่า `*.py` ค้นทั้งต้นไม้อยู่แล้วเมื่อจับคู่กับ relative path เพราะ `*`
กลืน slash ได้สบาย ดังนั้นการจับคู่กับ path เพียงอย่างเดียวก็รองรับกรณี recursive

อันที่สองบอกว่า `**/*.py` ล้มเหลวกับไฟล์ที่วางอยู่บนสุดของ workspace pattern นั้น
ต้องการ `/` จริง ๆ อยู่ที่ไหนสักแห่ง และไฟล์ที่ root ไม่มีเลย model เขียน
`**/*.py` ตลอดเวลาเพราะนั่นคือสิ่งที่ git และเครื่องมือสมัยใหม่ส่วนใหญ่ใช้แทนคำ
ว่า "ทุกที่" กรณีนี้จึงต้องทำงานได้ ค่า false อันเดียวนั้นคือเหตุผลทั้งหมดที่การ
จับคู่ครั้งที่สามมีอยู่ ตัด `**/` ที่นำหน้าออกแล้ว pattern จะกลายเป็น `*.py`
ซึ่งจับคู่กับ `agent.py` ที่ root ได้ และเพราะ `*` กลืน slash มันจึงยังจับคู่กับ
ทุกอย่างที่อยู่ต่ำลงไปได้ด้วย tool จึงทำในสิ่งที่ model ตั้งใจ ไม่ใช่สิ่งที่มัน
พิมพ์มาตรง ๆ

อันที่สามกับอันที่สี่คือคู่ที่ทำให้เห็นประเด็นเรื่องชื่อ `test_*.py` เป็นสิ่งที่ขอ
กันอย่างเป็นธรรมชาติมาก และมันล้มเหลวเมื่อเทียบกับ path เต็ม `tests/test_x.py`
เพราะ path ไม่ได้ขึ้นต้นด้วย `test_` แต่เมื่อจับคู่กับชื่อเปล่า `test_x.py` มัน
สำเร็จทันที

ดังนั้นการจับคู่กับ path รองรับ pattern ที่บรรยายตำแหน่ง การจับคู่กับชื่อรองรับ
pattern ที่บรรยายตัวไฟล์เอง และการจับคู่กับ pattern ที่ถูกตัดหัวรองรับคำว่า
"ทุกที่" ในการสะกดแบบที่ model หยิบมาใช้บ่อยที่สุด ตัดอันใดอันหนึ่งในสามออก แล้ว
คำขอที่สมเหตุสมผลทั้งหมวดจะคืนค่าว่างเปล่าอย่างเงียบ ๆ และการคืนค่าว่างเปล่าอย่าง
เงียบ ๆ คือความล้มเหลวที่แย่ที่สุดตรงนี้ เพราะ model จะสรุปว่าไฟล์นั้นไม่มีอยู่
แล้วลงมือทำตามข้อสรุปนั้น

คุณอาจแปลง pattern ให้เป็น glob แบบ recursive จริง ๆ แทน หรือใช้ `rglob` ของ
`pathlib` เองซึ่งเข้าใจ `**` เหตุผลที่เราไม่ทำคือทั้งสองแนวทางทำให้ syntax หนึ่ง
แบบทำงานได้สมบูรณ์แบบ แต่ syntax ข้างเคียงทุกแบบล้มเหลว การลองสามครั้งซึ่งราคาถูก
ทำให้ tool ผ่อนปรนกับทุก pattern ที่ model น่าจะผลิตออกมา และความผ่อนปรนมีค่ามาก
กว่าความถูกหลักการ ใน tool ที่ผู้เรียกใช้อ่าน source ไม่ได้

สังเกตด้วยว่าความผ่อนปรนนี้ถูกจ่ายที่ไหน คุณอาจเลือกสอน syntax ที่ถูกต้องให้ model
แทน ด้วยการเขียนกฎลงในคำบรรยายของ tool แต่คำบรรยาย tool ถูกส่งทุก request ไปตลอด
เซสชัน และเสีย token ทุกครั้ง ส่วนการยอมรับ pattern ที่คนเขียนกันจริงเสียโค้ดสาม
บรรทัดครั้งเดียว

นี่คือ output จริง ที่รันกับ directory `src` ของโปรเจกต์นี้

```text
--- glob_files("**/*.py")
agentpath/__init__.py
agentpath/agent.py
agentpath/cli.py
agentpath/prompt.py
agentpath/providers/__init__.py
agentpath/providers/anthropic.py
agentpath/providers/base.py
agentpath/providers/openai_compat.py
agentpath/testing/__init__.py
agentpath/testing/mock_server.py
agentpath/tools/__init__.py
agentpath/tools/base.py
agentpath/tools/files.py
agentpath/tools/search.py
agentpath/tools/shell.py
agentpath/tools/workspace.py
agentpath/types.py

--- glob_files("mock_server.py")
agentpath/testing/mock_server.py
```

ทั้งสองการเรียกคืน path ที่สัมพันธ์กับ workspace ซึ่งเป็นรูปแบบที่ `read_file`
ต้องการพอดี agent หยิบบรรทัดไหนก็ได้จาก output นั้นแล้วส่งต่อให้ tool ตัวถัดไปได้
เลยโดยไม่ต้องแก้ นั่นไม่ใช่เรื่องบังเอิญ มันคือเหตุผลหลักที่รูปแบบ output เป็น
แบบนี้

มีการตัดสินใจเล็ก ๆ อีกสองอย่างในสองบรรทัดสุดท้าย

`sorted` ทำให้ output เป็นแบบกำหนดได้แน่นอน ลำดับการเดินไฟล์ระบบไม่มีการรับประกัน
และต่างกันไปตามระบบปฏิบัติการ และ agent ที่ได้ลำดับต่างกันทุกครั้งที่รันจะ debug
ยากขึ้นและ cache ยากขึ้น

`f"no files match {pattern}"` เป็นประโยค ไม่ใช่สตริงว่าง ผลลัพธ์ว่างเปล่าที่ส่ง
กลับไปหา model คลุมเครือ เพราะ model บอกไม่ได้ว่า tool หาไม่เจอหรือ tool พัง
ประโยคที่ทวน pattern กลับไปบอกมันทั้งสองอย่างว่าการค้นหาได้รันจริง และรันหาอะไร
ซึ่งเพียงพอให้มันลอง pattern อื่น นี่คือหลักการจากบทที่ 07 ที่ว่า error คือ
ข้อความ นำมาใช้กับสิ่งที่ไม่ใช่ error

## 5. เขียน grep_files

tool ตัวที่สองค้นหาข้างในไฟล์ แทนที่จะค้นบนชื่อ และมันยังเป็น tool เดียวในคอร์ส
นี้ที่ส่ง input ที่ไม่น่าเชื่อถือให้เครื่องยนต์ซึ่งทำงานนานเท่าไหร่ก็ได้ มันจึงยาว
กว่าที่คุณคาดไว้

```python
def grep_files(pattern, glob="*"):
    try:
        re.compile(pattern)
    except re.error as error:
        return f"Error: {pattern} is not a valid regular expression ({error})"
    if NESTED_QUANTIFIER.search(pattern):
        return (
            f"Error: {pattern} has one repeat wrapped in another, which can take "
            "effectively forever to match. Write it without the nested repeat."
        )

    # The search runs in a separate process. Two earlier attempts at this did
    # not work and both are worth knowing about. Checking a deadline between
    # lines never gets a turn, because one line is enough to go exponential
    # and nothing interrupts a regular expression that is already running.
    # Moving it to a thread does not help either, because matching does not
    # release the global interpreter lock, so the thread waiting on the
    # deadline cannot run until the matching it waits on has finished.
    #
    # A separate process can simply be killed, which is the only thing that
    # actually works. The cost is about a tenth of a second of start up.
    request = json.dumps({"root": str(WORKSPACE), "pattern": pattern, "glob": glob})
    try:
        # -I matters more than it looks. Without it, the directory the child
        # starts in goes first on the import path, and that directory is the
        # workspace. A file the agent wrote there called json.py would be
        # imported and run before the search began, with no permission check,
        # because searching is a safe tool. -I removes it and ignores the
        # environment variables that could put it back.
        worker = Path(__file__).with_name("grep_worker.py")
        completed = subprocess.run(
            [sys.executable, "-I", str(worker)],
            input=request,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=SEARCH_SECONDS,
            cwd=str(worker.parent),
        )
    except OSError as error:
        return f"Error: the search could not be started. {error}"
    except subprocess.TimeoutExpired:
        return (
            f"Error: searching for {pattern} took longer than {SEARCH_SECONDS} "
            "seconds and was given up on. Try a simpler pattern, or narrow the "
            "search with the glob argument."
        )
    if completed.returncode != 0:
        return f"Error: the search failed. {completed.stderr.strip()[:200]}"
    hits = json.loads(completed.stdout or "[]")
    if not hits:
        return f"no matches for {pattern}"
    return truncate("\n".join(hits))
```

สังเกตสิ่งที่ไม่ได้อยู่ใน function นั้น ไม่มีลูปที่วนไฟล์ และไม่มีการเรียก
`search` บนบรรทัดใดเลย `grep_files` ไม่ได้แมตช์อะไรทั้งสิ้น มันตรวจ pattern
เริ่ม process Python ตัวที่สอง รอคำตอบเป็น JSON ห้าวินาที แล้วจัดรูปแบบสิ่งที่
กลับมา ส่วนการแมตช์จริงอยู่ใน `grep_worker.py`

รูปทรงนั้นคือหัวข้อทั้งหมดของส่วนนี้ และวิธีอ่านที่ง่ายที่สุดคือมองเป็นเกราะสาม
ชั้นที่วางซ้อนกันอยู่หน้าอันตรายเดียวกัน ตามด้วย worker แล้วจึงเป็นการจัดรูปแบบ
ผลลัพธ์ธรรมดาที่ `glob_files` สอนคุณไปแล้ว

### ชั้นที่หนึ่ง ขั้นตอน compile และทำไม pattern ที่ผิดจึงเป็นข้อความ

```python
    try:
        re.compile(pattern)
    except re.error as error:
        return f"Error: {pattern} is not a valid regular expression ({error})"
```

อ็อบเจกต์ที่ compile แล้วถูกทิ้งไปเฉย ๆ ซึ่งดูเหมือนความผิดพลาดแต่ไม่ใช่ การเรียก
นี้คือการทดสอบความถูกต้อง ไม่ใช่การเตรียมของ เพราะการแมตช์เกิดขึ้นในอีก process
หนึ่ง และ process นั้น compile pattern ใหม่เองอยู่แล้ว ของที่ compile ตรงนี้จึง
ส่งต่อไปให้มันไม่ได้อยู่ดี

สิ่งที่ได้มาคือความสามารถในการปฏิเสธ pattern ที่พังตั้งแต่ใน process แม่ ก่อนที่
process ลูกจะถูกสร้าง ก่อนที่ไฟล์จะถูกเปิด และก่อนที่ห้าวินาทีในชีวิตของใครจะถูก
ใช้ไป regular expression คือโปรแกรมเล็ก ๆ และ model เป็นคนเขียนมัน model เขียน
regular expression พังเป็นประจำ มักเป็นเพราะลืม escape วงเล็บเหลี่ยม
หรือวงเล็บกลมที่ตั้งใจให้เป็นตัวอักษรตรง ๆ การค้นหาการเรียก function ด้วยการพิมพ์
`def (` เป็นความผิดพลาดที่เป็นธรรมชาติมาก และมันไม่ใช่ expression ที่ถูกต้อง

ทีนี้ลองพิจารณาสองสิ่งที่อาจเกิดขึ้นต่อไป

ถ้า exception หลุดออกไป `tools.run` จะจับมันด้วยตัวจัดการแบบกว้างที่คุณเขียนไว้ใน
บทที่ 07 แล้วเปลี่ยนมันเป็นแบบนี้

```text
Error: error: missing ), unterminated subpattern at position 4
```

ในทางเทคนิคนั่นคือข้อความ ไม่ใช่การพัง ซึ่งดีกว่าไม่มีอะไรเลยอยู่แล้ว แต่มันไม่
บอกชื่อ tool ไม่ทวน pattern และใช้คำว่า `error` สองครั้งกับสองความหมาย model ต้อง
เดาเองว่ามันทำอะไรผิด

ถ้าเราจับมันตรงนี้ model จะได้แบบนี้

```text
Error: def ( is not a valid regular expression (missing ), unterminated subpattern at position 4)
```

ประโยคนั้นมี pattern ที่มันส่งมา มีข้อเท็จจริงว่าปัญหาคือ pattern ไม่ใช่ระบบไฟล์
และมีตำแหน่งของความผิดพลาดอย่างแม่นยำ model อ่านมัน escape วงเล็บ แล้วเรียกใหม่
ความล้มเหลวนี้ราคาแค่หนึ่งเทิร์น แทนที่จะจบงานไปเลย

นี่คือหลักการทั่วไปจากบทที่ 05 ที่โผล่มาเป็นที่ที่สาม tool คุยกับ model และ model
ทำได้แค่ตามที่ข้อความบอก exception คือข้อความถึงนักพัฒนาที่กำลังอ่าน stack trace
สตริงที่คืนกลับคือข้อความถึงผู้เรียก และตรงนี้ผู้เรียกคือ model ที่สามารถแก้ความ
ผิดพลาดของตัวเองได้สบาย ถ้าคุณบอกมันว่าความผิดพลาดคืออะไร

### ชั้นที่สอง เกราะที่อ่าน pattern ก่อนจะรันมัน

pattern หนึ่งอาจถูกต้องสมบูรณ์แบบและยังเป็นหายนะได้ `re.compile` รับ `(a+)+$` ไป
โดยไม่บ่นสักคำ และการเอามันไปแมตช์กับตัวอักษร a สามสิบตัวใช้เวลานานกว่าที่คุณจะรอ
ไหว สิ่งนี้เรียกว่า catastrophic backtracking และสาเหตุคือตัวทำซ้ำที่ถูกห่ออยู่ใน
ตัวทำซ้ำอีกชั้น ซึ่งทำให้เครื่องยนต์มีวิธีแบ่ง input ระหว่างสองตัวนั้นมากแบบชี้
กำลัง มีค่าคงที่อีกสามตัวอยู่เหนือ `_walk` เพื่อเรื่องนี้

```python
# Two quantifiers stacked on one group, as in (a+)+ or (a*)*, is the shape
# that makes a regular expression take exponential time. A model writing one
# by accident would otherwise wedge the whole process, and no cancellation
# token can help because the matching never returns to check one.
NESTED_QUANTIFIER = re.compile(r"\([^()]*[+*][^()]*\)\s*[+*{]")

# A line longer than this is truncated before matching. Catastrophic
# backtracking grows with the length of the input, so bounding the input is
# the one guard that works whatever the pattern turns out to be.
MAX_LINE = 2000

SEARCH_SECONDS = 5
```

ตัวแรกคือ regular expression ที่เอาไว้อ่าน regular expression มันมองหากลุ่มที่มี
`+` หรือ `*` อยู่ข้างใน แล้วตามด้วย `+` หรือ `*` หรือ `{` อีกตัว นั่นคือรูปทรง
ระเบิดแบบคลาสสิก และเมื่อเจอ tool จะปฏิเสธก่อนที่อะไรจะได้รัน

```python
    if NESTED_QUANTIFIER.search(pattern):
        return (
            f"Error: {pattern} has one repeat wrapped in another, which can take "
            "effectively forever to match. Write it without the nested repeat."
        )
```

ทำไมต้องตรวจ pattern ทั้งที่มี timeout อยู่ข้างล่างแล้ว มีสองเหตุผล การปฏิเสธเกิด
ขึ้นทันที ส่วน timeout เสียเวลาจริงห้าวินาทีในลูปที่ผู้ใช้นั่งมองอยู่ และการปฏิเสธ
เป็นประโยคที่ model ทำตามได้ ขณะที่ timeout บอกมันได้แค่ว่ามีอะไรบางอย่างช้า
`Write it without the nested repeat` คือคำสั่งซ่อม ส่วน `it took too long` คือ
การยักไหล่

ทำไมไม่พึ่งเกราะนี้อย่างเดียวแล้วตัดงาน process ทิ้งไป เพราะเกราะนี้ครบไม่ได้ และ
เรื่องนี้ต้องพูดตรง ๆ มันรู้จักรูปทรงเดียวที่เรารู้จัก regular expression ที่ช้า
เป็นตระกูลที่ใหญ่กว่าที่ใครจะเขียนรายการไว้ได้ และ pattern ที่ปลอดภัยกับ input
หนึ่งอาจระเบิดกับอีก input หนึ่ง รายการของรูปทรงที่ไม่ดีคือตัวกรอง ไม่ใช่ข้อพิสูจน์

นั่นคือหน้าที่ของ `MAX_LINE` และมันคือเกราะที่ไม่ต้องพึ่งการจดจำรูปทรงใด ๆ
backtracking บานปลายตามความยาวของข้อความที่ถูกแมตช์ การจำกัดข้อความนั้นจึงจำกัด
ความเสียหายได้ ไม่ว่า pattern จะกลายเป็นอะไรก็ตาม สองพันตัวอักษรยาวพอที่บรรทัด
โค้ดจริงจะไม่ถูกตัดจนเสียจุดที่ตรงกัน และสั้นพอที่แม้แต่ pattern ที่แย่ก็ทำงานจบ
มันถูกใช้ใน worker บนตัวบรรทัด ณ ขณะที่แมตช์

`SEARCH_SECONDS` คือทางสุดท้ายที่รออยู่หลังทั้งสองอัน และมันคือหัวข้อของส่วนถัดไป

### ชั้นที่สาม ทำไมเส้นตายต้องเป็นอีก process

นี่คือส่วนที่ควรอ่านช้า ๆ เพราะสองแบบที่ทุกคนคิดออกก่อนนั้นผิดทั้งคู่ และการอธิบาย
ได้ว่าทำไมมันผิด มีค่ามากกว่าตัวโค้ดเสียอีก

ไอเดียแรกคือเช็คนาฬิกาคั่นระหว่างบรรทัด อ่านเส้นตาย แมตช์หนึ่งบรรทัด ดูนาฬิกา
เลิกถ้าหมดงบ มันไม่ทำงาน เพราะบรรทัดเดียวก็พอที่จะระเบิดแบบชี้กำลังแล้ว การเช็ค
นั้นอยู่หลังการเรียกที่ไม่มีวันคืนค่ากลับมา โค้ดที่ไม่เคยได้คิวไม่ใช่เส้นตาย
มันคือคอมเมนต์

ไอเดียที่สองคือย้ายการแมตช์ไปไว้ใน thread แล้วให้อีก thread จับเวลา อันนี้ล้มเหลว
ด้วยเหตุผลที่เฉพาะกับ Python การแมตช์ไม่ปล่อย global interpreter lock ซึ่งคือ
กุญแจที่ยอมให้ thread เดียวรัน Python ได้ในหนึ่งขณะ thread ที่เฝ้านาฬิกาจึงไม่ได้
คิวจนกว่าการแมตช์ที่มันรออยู่จะจบไปแล้ว ซึ่งถึงตอนนั้นก็ไม่เหลืออะไรให้ขัดจังหวะ
thread ให้คุณรอสิ่งต่าง ๆ ได้ แต่มันไม่ได้ให้คุณแย่งหน่วยประมวลผลคืนจากโค้ด C
ที่ไม่มีความตั้งใจจะคืนมันเลย

และไม่มีรูปแบบที่สามที่ฉลาดกว่านั้น คุณยกเลิก regular expression ที่กำลังรันจาก
ข้างใน process ที่รันมันไม่ได้ เพราะการยกเลิกใน Python เป็นแบบร่วมมือ และโค้ดนี้
ไม่เคยร่วมมือ

สิ่งที่เหลืออยู่คือระบบปฏิบัติการ process แยกถูกฆ่าได้จากข้างนอก โดยไม่มีเงื่อนไข
และไม่ต้องขอความยินยอมจากมัน นั่นคือกลไกเดียวในรายการที่ไม่ต้องการให้โค้ดที่กำลัง
วิ่งหนีอาสาสมัครหยุดเอง

```python
        completed = subprocess.run(
            [sys.executable, "-I", str(worker)],
            input=request,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=SEARCH_SECONDS,
            cwd=str(worker.parent),
        )
```

`sys.executable` คือ interpreter ตัวเดียวกับที่กำลังรันอยู่ process ลูกจึงเป็น
Python ตัวที่ถูกและ virtual environment ที่ถูกอย่างแน่นอน ส่วน `input` กับ
`capture_output` แปลว่าสอง process คุยกันผ่าน pipe โดยส่งคำขอเป็น JSON หนึ่ง
อ็อบเจกต์เข้าไป และรับรายการ hit เป็น JSON หนึ่งอาร์เรย์ออกมา `timeout` คือส่วนที่
สำคัญ และเมื่อมันหมดเวลา `subprocess.run` จะฆ่า process ลูกแล้วโยน exception

```python
    except subprocess.TimeoutExpired:
        return (
            f"Error: searching for {pattern} took longer than {SEARCH_SECONDS} "
            "seconds and was given up on. Try a simpler pattern, or narrow the "
            "search with the glob argument."
        )
```

สังเกตว่านี่คือประโยคที่คืนกลับ ไม่ใช่ exception และมันบอก model สองอย่างที่ทำต่อ
ได้จริง นั่นคือกฎเดียวกับขั้นตอน compile ที่ถูกใช้กับความล้มเหลวซึ่ง model ไม่รู้
ด้วยซ้ำว่าเป็นไปได้

ราคาถูกเขียนไว้ในโค้ดเป็นคอมเมนต์ ซึ่งเป็นที่ที่ราคาควรอยู่ การเริ่ม process
Python เสียเวลาราวหนึ่งในสิบวินาที และการค้นหาทุกครั้งจ่ายค่านั้น รวมถึงครั้งที่
จะเสร็จภายในหนึ่งมิลลิวินาทีด้วย นั่นคือต้นทุนจริงและมันคุ้ม เพราะทางเลือกอีกทาง
คือ agent ที่ถูก pattern โชคร้ายอันเดียวทำให้หยุดนิ่งไปเลย

### ทำไม process ลูกจึงรันด้วย `-I` และในโฟลเดอร์ที่เราเลือก

มีอาร์กิวเมนต์สองตัวในการเรียกนั้นที่ไม่เกี่ยวกับประสิทธิภาพ และอ่านผ่านได้ง่าย

```python
        worker = Path(__file__).with_name("grep_worker.py")
```

worker ถูกหาจากตำแหน่งข้าง ๆ `tools.py` ไม่ใช่จากตำแหน่งที่โปรแกรมถูกสั่งให้เริ่ม
นั่นคือสิ่งที่ทำให้ tool ทำงานได้ไม่ว่า agent จะถูกเปิดจาก directory ไหน

ตัวที่น่าสนใจคือ `-I` ซึ่งคือโหมด isolated ใช้คู่กับ `cwd` และการจะเห็นว่าทำไมมัน
สำคัญ ให้นึกถึงสิ่งที่เกิดขึ้นตามปกติเวลา Python เริ่มรันสคริปต์ directory ที่
สคริปต์อยู่จะไปอยู่หน้าสุดของ import path และในบางวิธีการเรียก directory ที่
process เริ่มต้นก็ไปอยู่ตรงนั้นด้วย ของที่อยู่หน้าสุดชนะ ดังนั้น `import json`
ครั้งแรกใน process ลูกจะ import ไฟล์ `json.py` ตัวแรกที่ interpreter หาเจอ และถ้า
ไฟล์ชื่อนั้นวางอยู่ในโฟลเดอร์ที่ process เริ่มต้น ไฟล์นั้นจะถูก import และโค้ด
ระดับบนสุดของมันจะรัน

ทีนี้เอาเรื่องนั้นไปวางข้าง ๆ สิ่งที่ agent ตัวนี้ทำเป็นอาชีพ มันเขียนไฟล์ลงใน
workspace มันเขียนเพราะ model สั่ง และ model ถูกชักจูงได้ด้วยข้อความที่มันอ่านมา
จากไฟล์ ถ้า process ลูกเริ่มต้นใน workspace ไฟล์ชื่อ `json.py` ที่ agent เขียนไว้
จะถูก import และถูกรันทันทีที่การค้นหาเริ่มขึ้น ไม่ใช่ถูกแมตช์ ไม่ใช่ถูกอ่านเป็น
ข้อมูล แต่ถูกรันในฐานะ Python ในตัว interpreter ของคุณ ด้วยสิทธิ์ของคุณ

ส่วนที่แย่ที่สุดคือเรื่องการขออนุมัติ บทที่ 08 วางคนไว้หน้า `run_shell` เพราะการ
รันคำสั่งอันตรายอย่างเห็นได้ชัด แต่ไม่มีใครวางคำถามยืนยันไว้หน้าการค้นหา เพราะการ
ค้นหาคือ tool ที่ปลอดภัยซึ่งแค่อ่านและคืนข้อความ เส้นทางนี้จึงรันโค้ดโดยไม่มีการ
ถามใด ๆ เลย บนความไว้ใจใน tool ที่ผู้ใช้ตัดสินอย่างถูกต้องแล้วว่าไม่มีพิษภัย

`-I` เอา directory ของสคริปต์และ directory ปัจจุบันออกจาก import path และไม่สนใจ
ตัวแปรสภาพแวดล้อมอย่าง `PYTHONPATH` ที่จะเอามันกลับมาได้ ส่วน
`cwd=str(worker.parent)` ทำให้ process ลูกเริ่มต้นในโฟลเดอร์ของบทเรียน ไม่ใช่ใน
workspace ดังนั้นแม้จะพลาดเรื่อง path ก็ยังไปตกอยู่ในที่ที่ agent เขียนไม่ได้
สองอย่างรวมกันแปลว่า process ลูก import ได้แค่ standard library กับไฟล์เดียวที่
เราชี้ให้มัน

### grep_worker.py และทำไมกฎจึงถูก import แทนที่จะถูกคัดลอก

อีกครึ่งหนึ่งของ tool คือไฟล์ของมันเอง

```python
"""The part of grep_files that runs in its own process.

It lives in a separate file so it can be killed. A regular expression that
takes exponential time cannot be interrupted from inside the process running
it, so the only way to put a limit on a search is to run it somewhere that
can be shut down from outside.

The rules about which files may be searched are imported from tools.py
rather than copied here. An earlier version of this file had its own copy of
the secret names and the skip list, which is exactly what lesson 09 tells
you not to do. Two copies agree until the day somebody edits one.
"""
import json
import sys
from pathlib import Path

# Isolated mode removes every directory from the import path, including the
# one this file lives in, so the lesson folder has to be put back by hand.
# Only this folder, and never the folder the agent is working in, which is
# the whole point of starting isolated in the first place.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tools  # noqa: E402
```

ทำไมต้องเป็นไฟล์แยก แทนที่จะเป็น function เป็น flag หรือเป็น thread เพราะหน่วยที่
ระบบปฏิบัติการฆ่าได้คือ process และหน่วยที่ process ถูกเริ่มจากได้คือไฟล์ ทุกอย่าง
ที่เล็กกว่าไฟล์ใช้ interpreter ร่วมกับโค้ดที่พยายามจะหยุดมัน และหัวข้อ 5 ผ่านเรื่อง
ที่ว่านั่นล้มเหลวอย่างไรมาแล้ว เส้นแบ่งที่เป็นไฟล์ไม่ใช่ทางเลือกด้านสไตล์ มันคือ
สิ่งที่เล็กที่สุดที่มีสวิตช์ปิด

ทำไมมันจึงเอาโฟลเดอร์ของบทเรียนใส่กลับเข้า `sys.path` ด้วยมือ เพราะ `-I` เอาทุก
directory ออกไปหมด รวมถึงอันที่ worker เองอาศัยอยู่ การ import `tools` จึงจะพัง
การ insert เพิ่มกลับเข้ามาแค่ directory เดียว คืออันที่คำนวณจากตำแหน่งของ worker
เอง มันไม่เคยเพิ่ม workspace เข้าไป โหมด isolated ถูกรักษาไว้แล้วเปิดประตูที่รู้จัก
หนึ่งบาน แทนที่จะทิ้งโหมด isolated ไปทั้งอัน

และอันที่สำคัญที่สุด ทำไมจึง import กฎมาจาก `tools.py` แทนที่จะเขียนมันตรงนี้
worker ต้องใช้ `_walk` `path_matches` `MAX_LINE` และ `MAX_RESULTS` ทุกอันในนั้นคือ
กฎว่าการค้นหาเห็นอะไรได้บ้าง และคืนกลับมาได้มากแค่ไหน การคัดลอกมันมาไว้ในไฟล์นี้
จะสร้างการประกาศกฎเดิมเป็นครั้งที่สอง และการประกาศครั้งที่สองคือสิ่งที่เคลื่อนออก
จากกันได้ docstring พูดตรง ๆ ว่าเรื่องนี้เคยเกิดขึ้นมาแล้วครั้งหนึ่ง กับรายชื่อ
ไฟล์ลับและรายการ directory ที่ต้องข้าม ซึ่งเคยอยู่สองที่

ลองคิดว่าการเคลื่อนออกจากกันแปลว่าอะไรตรงนี้ มีคนเพิ่ม `.pgpass` เข้าไปใน
`SECRET_NAMES` ใน `tools.py` สำเนาใน worker ไม่ถูกแตะ และตอนนี้ `read_file`
ปฏิเสธไฟล์นั้น ขณะที่ `grep_files` พิมพ์มันออกมา ไม่มีอะไรพัง ไม่มี test ไหนล้ม
เว้นแต่จะมีคนคิดเขียน test อันนั้นไว้พอดี กฎยังอยู่ในโค้ด เป็นลายลักษณ์อักษร
และมันไม่ถูกบังคับใช้อีกต่อไป

นี่คือข้อโต้แย้งเดียวกับที่หัวข้อ 5 พูดเรื่องการเดินต้นไม้ และเป็นข้อเดียวกับที่
บทที่ 07 พูดเรื่อง `resolve_inside` ซึ่งมาถึงเป็นครั้งที่สามในสามบท กฎที่ถูกบังคับ
ใช้ที่เดียวคือกฎ ส่วนกฎที่ถูกเขียนไว้สองที่คือความบังเอิญที่รอวันหมดอายุ

### ตัวกรอง glob

```python
        relative = path.relative_to(root).as_posix()
        if not tools.path_matches(relative, path.name, glob):
            continue
```

พารามิเตอร์ตัวที่สองที่ไม่บังคับ ทำให้การค้นแคบลงเหลือเฉพาะไฟล์ที่ตรง และมันเรียก
helper ตัวเดียวกันคือ `path_matches` ที่ `glob_files` ใช้ ซึ่งเป็นเหตุผลว่าทำไม
อาร์กิวเมนต์ `glob` จึงทำตัวเหมือนอาร์กิวเมนต์ `pattern` เป๊ะ ๆ ค่าเริ่มต้นคือ
`"*"` ซึ่งจับคู่กับทุกอย่าง พารามิเตอร์นี้จึงไม่บังคับจริง ๆ และ schema ระบุแค่
`pattern` ว่าจำเป็น

สิ่งนี้มีอยู่เพราะ agent มักรู้บางอย่างเกี่ยวกับตำแหน่งที่ควรมองแม้จะไม่รู้ว่า
ไฟล์ไหน การค้นหาคำว่า `test` ทั่วทุกไฟล์ใน repository แทบไร้ประโยชน์ การค้นหามัน
ใน `*.py` เป็นคำถามคนละแบบที่มีคำตอบที่ใช้ได้ การให้ทางแก่ model ในการบอกสิ่งที่
มันรู้อยู่แล้ว ช่วยให้รายการผลลัพธ์สั้น และรายการผลลัพธ์ที่สั้นคือเศรษฐศาสตร์
ทั้งหมดของบทนี้

### การข้ามไฟล์ที่ไม่ใช่ข้อความ

```python
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
```

repository จริงมีไฟล์ PNG ไบนารีที่ compile แล้ว ไฟล์ database และ font
`read_text` กับไฟล์เหล่านั้นจะโยน `UnicodeDecodeError` และไฟล์ที่ถูกลบไประหว่าง
การเดินกับการอ่าน หรือไฟล์ที่ process ไม่มีสิทธิ์เปิด จะโยน `OSError` ทั้งสองอย่าง
ไม่คุ้มที่จะรายงาน ไฟล์นั้นถูกข้ามไปเฉย ๆ แล้วการเดินก็ดำเนินต่อ ส่วนนี้รันอยู่ใน
worker ไฟล์ที่ process ลูกเปิดไม่ได้จึงเสียแค่การวนหนึ่งรอบ และไม่เคยกลายเป็น
error ที่ส่งกลับไปถึง process แม่

สังเกตความต่างที่จงใจกับบทที่ 07 ที่ `read_file` ส่ง `errors="replace"` เพื่อให้
ไฟล์ข้อความที่เสียบางส่วนยังกลับมาพร้อมตัวอักษรแทนที่ แทนที่จะล้มเหลว นั่นถูก
ต้องเมื่อมนุษย์ขอไฟล์นั้นเจาะจง เพราะได้อะไรมาบ้างดีกว่าไม่ได้อะไรเลย แต่มันผิด
ตรงนี้ เพราะไฟล์ไบนารีจะผลิตตัวอักษรแทนที่ออกมาเป็นพัน ๆ ตัวอย่างสบายใจ และ
pattern อย่าง `.` จะจับคู่กับทุกบรรทัดของไฟล์ JPEG การเรียก library เดียวกัน แต่
ตัดสินใจตรงข้าม เพราะเจตนาของผู้เรียกต่างกัน

### ชื่อไฟล์และหมายเลขบรรทัด

นี่คือส่วนที่ทำให้ tool มีประโยชน์ ไม่ใช่แค่ถูกต้อง และมันคือลูปชั้นในสุดของ
worker

```python
        for number, line in enumerate(text.splitlines(), start=1):
            if expression.search(line[: tools.MAX_LINE]):
                hits.append(f"{relative}:{number}: {line.strip()[:200]}")
                if len(hits) >= tools.MAX_RESULTS:
                    return hits
```

`line[: tools.MAX_LINE]` คือเกราะจากชั้นที่สองที่มาถึงจุดที่มันทำงานจริง ข้อความ
ที่ถูกส่งให้เครื่องยนต์ไม่เคยยาวเกินสองพันตัวอักษร ไม่ว่าไฟล์จะมีอะไรอยู่ และไม่
ว่า pattern จะกลายเป็นอะไร

`enumerate(..., start=1)` นับจากหนึ่ง เพราะนั่นคือวิธีที่ editor และ compiler และ
เครื่องมืออื่นทุกตัวนับบรรทัด การนับจากศูนย์ตรงนี้จะสอดคล้องกับ Python ในทาง
เทคนิค และผิดสำหรับผู้บริโภค output ทุกราย

รูปแบบคือ path หมายเลขบรรทัด และบรรทัดที่ตรง ซึ่งจงใจให้เป็นรูปทรงเดียวกับที่
`grep -n` ผลิตออกมาตลอดหลายสิบปี หน้าตาเป็นแบบนี้

```text
agentpath/providers/base.py:21: def parse_arguments(raw: str) -> tuple[dict, str]:
agentpath/providers/openai_compat.py:16: def to_wire(message: Message) -> dict:
agentpath/testing/mock_server.py:47: def decide(messages):
agentpath/tools/search.py:18: def _walk(root: Path):
agentpath/tools/workspace.py:27: def resolve_inside(root, path) -> Path:
```

ทีนี้ลองถามว่าทำไมต้องมีหมายเลขบรรทัดอยู่ในนั้นด้วย ในเมื่อ model กระโดดไปยัง
บรรทัดใดบรรทัดหนึ่งด้วย tool ที่มีไม่ได้ `read_file` รับ path แล้วคืน 4000 ตัวอักษร
แรก ไม่มี `read_lines`

คำตอบคือหมายเลขบรรทัดไม่ได้มีไว้ให้ tool มันมีไว้ให้ model ใช้ให้เหตุผลว่าจะไล่ตาม
จุดไหน และจะเจออะไรเมื่อไปถึงที่นั่น จุดที่ตรงกันที่บรรทัด 21 ของไฟล์อยู่ใกล้ด้าน
บน ดังนั้นการอ่านไฟล์จะไปถึงมัน จุดที่ตรงกันที่บรรทัด 900 บอก model ว่าไฟล์นี้
ใหญ่ ว่า `read_file` ธรรมดาจะตัดจบก่อนถึงส่วนที่น่าสนใจเสียนาน และว่ามันควรทำให้
แคบลงด้วย grep อีกครั้ง หรืออ่านไฟล์ผ่าน shell แทน ตัวเลขนี้คือข้อมูลเกี่ยวกับ
รูปทรงของ code base และ model ใช้มันวางแผน

ชื่อไฟล์ทำสิ่งที่สำคัญยิ่งกว่า นั่นคือการเปลี่ยนผลการค้นหาให้เป็น input ของการ
เรียก tool ครั้งถัดไป `agentpath/tools/search.py` คือสิ่งที่ `read_file` ต้องการ
พอดี output ของ tool ตัวหนึ่งคืออาร์กิวเมนต์ของตัวถัดไป โดยไม่ต้องแปลงอะไรคั่น
กลาง ออกแบบ tool ทุกตัวแบบนั้น แล้ว agent จะร้อยมันต่อกันได้โดยไม่ต้องประดิษฐ์
อะไรขึ้นมา ถ้าคืนสรุปสวย ๆ ที่ไม่มี path อยู่ในนั้น สายโซ่จะขาดตั้งแต่ข้อแรก

`line.strip()` เอา indentation ออก ซึ่งในโค้ดที่ซ้อนลึกอาจเป็นตัวอักษรที่เสียเปล่า
ยี่สิบตัวในทุกจุดที่ตรงกัน ส่วน `[:200]` จำกัดสิ่งที่หนึ่ง hit ใส่ลงใน output
เพราะไฟล์ JavaScript ที่ถูก minify คือหนึ่งบรรทัดที่ยาวเก้าหมื่นตัวอักษร และถ้า
ไม่มีเพดานนี้ จุดที่ตรงกันเพียงจุดเดียวจะเติมเต็มผลลัพธ์ของ tool ทั้งหมด สังเกต
ว่านี่เป็นคนละเพดานกับ `MAX_LINE` ในบรรทัดข้างบน และทั้งสองไม่ได้ซ้ำซ้อนกัน
`MAX_LINE` จำกัดสิ่งที่เครื่องยนต์ถูกขอให้แมตช์ ซึ่งเป็นเรื่องเวลา ส่วน `[:200]`
จำกัดสิ่งที่คืนกลับมา ซึ่งเป็นเรื่อง context window นั่นคือเพดานที่สองกับที่สาม
จากสี่เพดานในบทนี้ และหัวข้อ 7 จะรวมทั้งสี่เข้าด้วยกัน

### สิ่งเดียวที่ tool ค้นหาไม่ได้สืบทอดมาฟรี ๆ

มีการตรวจสอบหนึ่งอันใน `_walk` ที่ไม่เกี่ยวอะไรกับการค้นหาเลย และมันคือบรรทัดที่
สำคัญที่สุดในบทนี้

ในบทที่ 07 คุณสร้าง `resolve_inside` และส่วนหนึ่งของหน้าที่มันคือปฏิเสธการอ่าน
ไฟล์ credential เพื่อให้ key ไม่มีวันเข้าสู่บทสนทนา แต่ tool ค้นหาไม่ได้อ่านไฟล์
ผ่าน `resolve_inside` มันเดินต้นไม้เองและเรียก `read_text` ตรง ๆ ถ้าเขียนแบบตรงไป
ตรงมา มันจะไม่สืบทอดอะไรจากการปฏิเสธนั้นเลย และคุณจะได้แบบนี้

```text
read_file(".env")   -> Error: this tool refuses to touch .env because credential
                       files must not enter the conversation or be changed by
                       an agent
grep_files("KEY")   -> .env:1: OPENAI_API_KEY=sk-secret-value
```

ประตูหน้าล็อกอยู่ แต่หน้าต่างเปิด นั่นไม่ใช่บั๊กที่แนบเนียน มันคือการตรวจสอบที่
หายไป และมันคือช่องโหว่แบบที่เกิดขึ้นพอดีเมื่อกฎความปลอดภัยอยู่ใน function เดียว
แทนที่จะอยู่ในการเดินต้นไม้ที่ tool ทุกตัวใช้ร่วมกัน

การซ่อมที่ชัดเจนคือเทียบชื่อในการเดินต้นไม้ ด้วย helper ชื่อ `looks_like_a_secret`
ที่บทที่ 07 ให้คุณไว้แล้ว การซ่อมแบบนั้นคือสิ่งที่บทเรียนนี้ปล่อยออกมาเป็นครั้งแรก
และมันไม่พอ การกรองด้วยชื่อปิดกรณี `.env` ได้ แต่เปิดกรณีที่ใหญ่กว่าทิ้งไว้เต็ม
บาน `_walk` จึงส่งทุกไฟล์ที่เข้าข่ายผ่านประตูเดิมแทน

```python
        try:
            # The same gate every file tool uses, rather than a check on the
            # name. rglob follows symlinks and Windows junctions, so a link
            # planted inside the workspace would otherwise let search read
            # anything on the machine while read_file correctly refused.
            # Looking at the name of the link never sees the name of what it
            # points at.
            resolve_inside(str(relative))
        except WorkspaceError:
            continue
```

นี่คือเหตุผลที่ชื่อไม่พอ และกลไกของมันควรพูดให้แม่นยำ `rglob` เดินตาม symbolic
link และบน Windows มันเดินตาม junction ด้วย symbolic link คือไฟล์ที่เนื้อในของมัน
คือ path ไปยังที่อื่น และระบบปฏิบัติการจะสลับไปใช้ปลายทางให้เงียบ ๆ เมื่อมีอะไรมา
เปิดมัน ลิงก์ที่วางอยู่ใน workspace จึงถูกการเดินต้นไม้เยี่ยมชมเหมือนไฟล์อื่นทุก
ประการ และ `read_text` บนมันจะอ่านสิ่งที่มันชี้ไป ซึ่งอยู่ที่ไหนก็ได้บนเครื่องที่
ผู้ใช้อ่านได้

ทีนี้ดูว่าการเช็คชื่อเห็นอะไรในสถานการณ์นั้น มันเห็นชื่อของลิงก์ และชื่อของลิงก์
คือชื่อที่คนวางลิงก์เป็นคนตั้ง มันไม่มีความสัมพันธ์ใด ๆ กับชื่อของปลายทางเลย ลิงก์
ชื่อ `notes.txt` ชี้ไปที่ `/home/you/.ssh/id_rsa` ได้ ลิงก์ชื่อ `docs` ชี้ไปที่
root ของไดรฟ์ได้ `looks_like_a_secret("notes.txt")` คืน `False` อย่างถูกต้อง และ
ความลับก็ถูกอ่านอยู่ดี การเช็คนั้นไม่ได้ตัดสินชื่อผิด มันแค่มองผิดวัตถุ

`resolve_inside` ถูกหลอกไม่ได้ เพราะการ resolve path คือปฏิบัติการที่เดินตามลิงก์
และให้ตำแหน่งจริงออกมาพอดี เมื่อมันได้ตำแหน่งจริงแล้ว การปฏิเสธสองข้อที่มันมีอยู่
เดิมก็ทำงานเอง ลิงก์ที่ชี้ออกไปนอก workspace ตกการทดสอบเรื่องขอบเขต และลิงก์ที่ชี้
ไปยังไฟล์ credential ใน workspace ตกการทดสอบชื่อบนชื่อจริงของปลายทาง ไม่มีกฎข้อ
ไหนต้องถูกเขียนใหม่เลย การเดินต้นไม้แค่เลิกประดิษฐ์คำถามเวอร์ชันของตัวเอง แล้วไป
ถาม function ที่รู้คำตอบอยู่แล้ว

นั่นคือรูปทรงที่การแก้บั๊กแบบนี้ควรมี สี่บรรทัด ไม่มีกฎใหม่ และบรรทัดใหม่คือการ
เรียกประตูเดิม ถ้าคุณพบว่าตัวเองกำลังเขียนกฎความปลอดภัยข้อเดิมเป็นครั้งที่สองด้วย
ถ้อยคำที่ต่างออกไป แปลว่าคุณกำลังรักษาที่อาการ

ลองกับไฟล์จริงใน `lessons/09-search-tools/tools.py` ดู วาง `.env` ไว้ใน
workspace ชั่วคราวแล้วประตูทั้งสองบานก็ปิดสนิท

```text
read_file(".env")   -> Error: this tool refuses to touch .env because credential
                       files must not enter the conversation or be changed by
                       an agent
grep_files("KEY")   -> no matches for KEY
glob_files("**/*")  -> the other files, and no .env in the list
```

สังเกตว่า `glob_files` ก็ถูกครอบคลุมด้วย ทั้งที่มันไม่เคยอ่านไฟล์แม้แต่ไบต์เดียว
นั่นคือประเด็นของการวางการตรวจสอบไว้ในการเดินต้นไม้แทนที่จะวางไว้ใน tool แต่ละตัว
ชื่อไฟล์เพียงอย่างเดียวก็เป็นการรั่วไหลได้ `secrets.prod.env` ที่โผล่อยู่ในรายการ
บอกผู้โจมตีที่อ่านบทสนทนาอยู่ได้ทันทีว่าควรขออะไรต่อ

บทเรียนทั่วไปมีค่ามากกว่าสี่บรรทัดนั้น **กฎที่บังคับใช้ที่จุดเข้าจุดเดียวเท่ากับ
ไม่ได้บังคับใช้** มันต้องอยู่ในที่ที่ทุกเส้นทางผ่าน และ tool ใหม่ทุกตัวที่แตะ
ทรัพยากรเดียวกันต้องถูกพาไปหามัน ไม่ใช่ได้ตัวกรองของตัวเอง `resolve_inside` คือ
ที่นั้น tool ไฟล์เรียกมันตรง ๆ `_walk` เรียกมันแทน tool ค้นหาทั้งสองตัว และ
`grep_worker.py` import `_walk` มาใช้แทนที่จะเขียนซ้ำสักส่วนเดียว หนึ่งกฎ หนึ่ง
function สามผู้เรียก ภาคสามจะสร้าง tool ใหม่รอบแนวคิดนี้พอดี

## 6. ทำไมเราจึงข้าม directory อย่าง .git และ .venv

บรรทัดนี้ปรากฏขึ้นในหัวข้อ 4 โดยไม่มีคำอธิบาย

```python
        relative = path.relative_to(WORKSPACE)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
```

`SKIP_DIRECTORIES` คือเซตที่คุณนิยามไว้ในบทที่ 07 สำหรับ `list_files` นำมาใช้ซ้ำ
ตรงนี้โดยไม่เปลี่ยน

```python
SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache"}
```

`.parts` แยก path ออกเป็นส่วนประกอบ ดังนั้นบรรทัดนี้จึงข้ามไฟล์ถ้ามี directory
ใดก็ตามที่อยู่เหนือมันอยู่ในเซตนี้ การเช็คทุกส่วนประกอบแทนที่จะเช็คแค่ parent
ที่อยู่ติดกัน คือสิ่งที่ทำให้มันได้ผลในระดับลึก เพราะไฟล์ที่ฝังอยู่ที่
`.venv/Lib/site-packages/httpx/_client.py` มี `.venv` อยู่เหนือขึ้นไปหกชั้น

`relative_to` ในบรรทัดก่อนหน้ากำลังทำงานเงียบ ๆ อยู่ ถ้าคุณขอส่วนประกอบของ path
แบบสัมบูรณ์ คุณก็กำลังทดสอบทุก directory ที่อยู่เหนือ workspace ขึ้นไปด้วย
ซึ่งเป็น directory ที่ผู้ใช้เลือกเอง และ agent ไม่มีสิทธิ์ไปมีความเห็นกับมัน
วางโปรเจกต์ของคุณไว้ในโฟลเดอร์ที่บังเอิญชื่อ `node_modules` แล้วทุกไฟล์จะถูกข้าม
tool ทั้งสองตัวจะคืนค่าว่างตลอดกาล และจะไม่มี error message ใดบอกคุณว่าทำไม
การเทียบกับ path แบบสัมพัทธ์คือการเรียกเพิ่มหนึ่งครั้ง และมันจำกัดกฎนี้ให้อยู่
แค่ในต้นไม้ที่ agent ได้รับอนุญาตให้เห็นจริง ๆ

ทีนี้มาดูตัวเลข เพราะข้อโต้แย้งนี้น่าเชื่อกว่ามากเมื่อมีตัวเลขจริง แทนที่จะใช้
วลีว่า "ด้วยเหตุผลด้านประสิทธิภาพ"

repository นี้เล็ก มี HTTP library หนึ่งตัวกับ test runner เป็น dependency นี่คือ
สิ่งที่อยู่บนดิสก์จริง ๆ

```text
project Python files, ignoring .venv and .git      251
files inside .venv                                 999
Python files inside .venv                          599
files inside .git                                  558
size of .venv                                       41M
```

ดังนั้นการเดินที่ไม่ข้ามอะไรเลยจะเยี่ยมชม 1808 ไฟล์ แทนที่จะเป็น 251 ไฟล์ งานมาก
กว่าเจ็ดเท่าเพื่อหาคำตอบเดิม บนโปรเจกต์ที่มี dependency สองตัว แอปพลิเคชันเว็บ
ที่มี dependency tree จริง หรืออะไรก็ตามที่ใช้ Node แล้วมี directory
`node_modules` จะมีไฟล์เป็นหมื่น ๆ ไฟล์และหลายร้อยเมกะไบต์ สามหมื่นไฟล์เป็นเรื่อง
ธรรมดามาก นั่นคือเวลาที่เสียไปเปล่า

context ที่เสียไปเปล่าแย่กว่ามาก และมันคือเหตุผลที่เรื่องนี้สำคัญกับ agent มากกว่า
ที่จะสำคัญกับคุณตอนนั่งอยู่หน้า terminal ลองค้นคำว่า `def` ในไฟล์ Python ของ
repository นี้แล้วนับจำนวนที่เจอ

```text
matches in the project                            1279
matches inside .venv                              5935
characters of output from the .venv matches     563745
```

สัญญาณรบกวนมากกว่าสัญญาณจริงเกือบห้าเท่า และคิดเป็นราว 140,000 token นั่นใหญ่กว่า
context window ทั้งอันของ model หลายตัว มันไม่ใช่แค่ไม่ช่วยอะไร แต่มันจะล้มเหลว
ไปเลย

แต่สมมติว่าคุณมี context window ที่ใหญ่มากและมันใส่ได้พอดี ทีนี้เอาผลลัพธ์นั้นใส่
ลงในบทสนทนา แล้วนึกถึงสิ่งที่บทที่ 02 สอนคุณ บทสนทนาถูกส่งซ้ำทั้งก้อนในทุก
request token 140,000 ตัวของโครงสร้างภายใน `httpx` ตอนนี้ติดอยู่กับทุกข้อความไป
ตลอดเซสชัน คุณจ่ายค่ามันทุกเทิร์น model อ่านมันทุกเทิร์น และทุกเทิร์นมันแย่งความ
สนใจของ model ไปจากสี่บรรทัดที่สำคัญจริง

ประเด็นสุดท้ายนั้นคือสิ่งที่คนมองข้าม ต้นทุนไม่ได้มีแค่เงินกับ latency model ที่
ได้ผลลัพธ์ที่ไม่เกี่ยวข้องยี่สิบอันกับที่เกี่ยวข้องหนึ่งอัน หยิบอันที่เกี่ยวข้อง
ได้แย่กว่า model ที่ได้ผลลัพธ์สามอันอย่างวัดผลได้ การเติม context ด้วยสัญญาณ
รบกวนทำให้ agent โง่ลง ไม่ใช่แค่ช้าลง

ยังมีข้อควรระวังที่ควรพูดตรง ๆ เหลืออยู่หนึ่งข้อ และมันชี้ไปอีกทาง เซตนี้ถูก
เขียนตายตัวไว้ ดังนั้นโปรเจกต์ที่เก็บของหนักไว้ในที่ที่คอร์สนี้ไม่เคยได้ยินชื่อ
อย่าง `vendor` หรือ `target` หรือ `.next` หรือ `dist` จะไม่ได้รับการปกป้องนี้เลย
กฎนี้ไม่เรียนรู้ และมันไม่อ่าน `.gitignore` ของคุณ มันคือแบบฝึกหัดข้อที่สอง
ท้ายบทนี้

## 7. ทำไมเราจึงจำกัดจำนวนผลลัพธ์

`MAX_RESULTS = 200` และมันถูกใช้ใน tool ทั้งสองตัว ใน `glob_files` มันคือการเฉือน
ที่ทำหลังการเรียงลำดับ

```python
    return truncate("\n".join(sorted(matches)[:MAX_RESULTS]))
```

ส่วนใน worker มันคือการทดสอบในลูปชั้นในสุด และค่าคงที่ถูกเข้าถึงผ่าน import แทน
ที่จะถูกประกาศซ้ำ

```python
                if len(hits) >= tools.MAX_RESULTS:
                    return hits
```

เหตุผลเหมือนกับหัวข้อ 6 จึงเขียนสั้นได้ การค้นหาที่ตรงกันหนึ่งหมื่นบรรทัดไม่ได้
ตอบคำถาม มันแค่ย้ายปัญหา ไม่มีใคร ไม่ว่า model หรือมนุษย์ ใช้ผลลัพธ์หนึ่งหมื่น
รายการได้ และทุกรายการเหล่านั้นเข้าไปอยู่ในบทสนทนาและอยู่ตรงนั้นต่อไป โดยถูกจ่าย
ค่าในทุกเทิร์นถัดไป

เลข 200 ไม่ใช่ของศักดิ์สิทธิ์ และไม่มีการพิสูจน์เชิงหลักการว่ามาจากไหน มันถูก
เลือกเพื่อให้การค้นแบบกว้างยังคืนของมาพอที่จะมีประโยชน์จริง ขณะที่ output ในกรณี
แย่ที่สุดยังอยู่ที่หลักพันต้น ๆ ของตัวอักษร ปรับมันตาม repository ของคุณเองและ
model ของคุณเอง สิ่งที่สำคัญคือต้องมีขอบเขตอยู่

### เรื่องนี้เชื่อมกับการตัดข้อความของบทที่ 07 อย่างไร

ตอนนี้คุณมีสี่ขีดจำกัดแยกกันซ้อนกันอยู่ บวกกับเส้นตายอีกหนึ่งอันที่รออยู่หลังทุก
ตัว และมันคุ้มที่จะมองพวกมันเป็นระบบเดียว มากกว่าเป็นตัวเลขห้าตัวที่ไม่เกี่ยวกัน

| ขีดจำกัด | มาจากไหน | มันจำกัดอะไร |
| --- | --- | --- |
| `MAX_LINE = 2000` | บทที่ 09 | ส่วนของบรรทัดที่ถูกเอาไปแมตช์ |
| `[:200]` บนหนึ่งบรรทัด | บทที่ 09 | หนึ่งบรรทัดผลลัพธ์ |
| `MAX_RESULTS = 200` | บทที่ 09 | จำนวนบรรทัดผลลัพธ์ |
| `MAX_OUTPUT = 4000` | บทที่ 07 | สตริงทั้งก้อนที่คืนกลับ |
| `SEARCH_SECONDS = 5` | บทที่ 09 | เวลาที่การค้นหาทั้งครั้งใช้ได้ |

พวกมันประกอบกัน และแต่ละตัวจับกรณีที่ตัวอื่นจับไม่ได้ ผลลัพธ์สองร้อยรายการ
รายการละสองร้อยตัวอักษรจะเป็น 40,000 ตัวอักษร ดังนั้น `truncate` จากบทที่ 07 จึง
ยังทำงานและยังต่อท้ายโน้ต `[truncated, N more characters]` ของมัน ในขณะเดียวกัน
บรรทัดเดียวที่ตรงกันจาก bundle ที่ถูก minify จะทะลุ `MAX_OUTPUT` ได้ด้วยตัวเอง
ซึ่งเป็นสิ่งที่เพดานต่อบรรทัดป้องกันไว้ และการค้นหาที่คืนผลลัพธ์สั้น ๆ ห้าหมื่น
รายการจะผ่านเพดานต่อบรรทัดและผ่าน `truncate` แต่เสียการเดินต้นไม้ไปทั้งหมด ซึ่ง
เป็นสิ่งที่ `MAX_RESULTS` ป้องกันไว้

อันแรกกับอันสุดท้ายในห้าตัวนั้นเป็นขีดจำกัดคนละชนิดกับสามตัวตรงกลาง และความต่าง
นี้ควรถูกเรียกชื่อ `[:200]` `MAX_RESULTS` และ `MAX_OUTPUT` จำกัดปริมาณข้อความที่
คืนกลับมา พวกมันจึงปกป้อง context window ส่วน `MAX_LINE` กับ `SEARCH_SECONDS`
จำกัดปริมาณงานที่เกิดขึ้น พวกมันจึงปกป้อง process tool ที่ส่ง input ซึ่ง model
เขียนให้เครื่องยนต์ ต้องมีทั้งสองชนิด เพราะการค้นหาที่ไม่คืนอะไรเลยหลังจากเผา
เครื่องไปหนึ่งชั่วโมง อยู่ในกรอบของเพดาน output ทุกอันครบถ้วน และยังทำลายเซสชัน
ทิ้งอยู่ดี

กฎที่อยู่ใต้ทั้งหมดคือกฎจากบทที่ 07 และมันคือนิสัยที่สำคัญที่สุดข้อเดียวใน
การออกแบบ tool ผลลัพธ์ของ tool ทุกอันเป็นสิ่งถาวร มันเข้าไปอยู่ในบทสนทนา มันถูก
ส่งอีกครั้งในทุก request ถัดไป และไม่มีทางเอาคืนได้ ดังนั้น tool ทุกตัวจึงต้องมี
ขอบเขตของสิ่งที่มันคืนได้ และขอบเขตของสิ่งที่มันใช้ไปได้ และขอบเขตทั้งสองต้องอยู่
ใน tool ไม่ใช่อยู่ในความหวังว่าผู้เรียกจะมีสติ

### ทำไม tool ทั้งสองจึงจำกัดต่างกัน

ลองดูอีกครั้งแล้วสังเกตว่า tool สองตัวนี้ไม่ได้หยุดแบบเดียวกัน

`glob_files` เดินทั้งต้นไม้ เก็บทุกจุดที่ตรงกัน เรียงลำดับ แล้วค่อยหยิบ 200 อันแรก
ส่วน worker ที่อยู่หลัง `grep_files` หยุดเดินทันทีที่มี 200 hit

ความต่างนั้นจงใจ และมันเป็นเรื่องต้นทุน `glob_files` อ่านแค่รายการใน directory
ซึ่งถูก และมันต้องการ output ที่เรียงแล้ว นั่นแปลว่ามันต้องมีชื่อครบทั้งหมดก่อน
จึงจะตัดสินได้ว่า 200 อันไหนมาก่อน การหยุดก่อนกำหนดจะให้ 200 อันแรกตามลำดับของ
ระบบไฟล์ ซึ่งไม่มีความหมาย

worker เปิดและอ่านเนื้อหาของทุกไฟล์ที่เข้าข่าย ซึ่งแพงกว่ามหาศาล เมื่อมันมี 200
hit แล้ว การอ่านไฟล์ต่อไปคือความสูญเปล่าล้วน ๆ มันจึงหยุด ผลที่ตามมาคือผลลัพธ์
ของ grep เรียงตามลำดับการเดินแทนที่จะเรียงลำดับ และ grep ที่ถูกจำกัด
จะแสดงจุดที่ตรงกันจากตำแหน่งที่การเดินบังเอิญไปถึง นั่นคือการแลกจริง ที่ทำอย่างรู้
ตัว การอ่านข้อมูลร้อยเมกะไบต์เพื่อผลิต output ที่คุณกำลังจะทิ้ง แย่กว่าลำดับที่
ไม่มีความหมาย

วิธีที่มันหยุดควรค่าแก่การอธิบายสักประโยค เพราะการสะกดแบบที่ชัดเจนที่สุดจะเป็นบั๊ก
ตรงนี้มีสองลูป อันหนึ่งวนไฟล์และอีกอันวนบรรทัดในไฟล์ปัจจุบัน และ `break` ในลูปชั้น
ในจบแค่ไฟล์ปัจจุบัน การเดินจะเดินหน้าเปิดทุกไฟล์ที่เหลือใน repository ต่อไปแล้ว
ไม่เพิ่มอะไรเลย ซึ่งคือครึ่งที่แพงของงาน โดยไม่ได้ประโยชน์ใด ๆ ส่วน `return hits`
ออกจากทั้งสองลูปและออกจาก function พร้อมกัน ซึ่งเป็นสิ่งที่สถานการณ์นี้ต้องการ
จริง ๆ การใช้ `break` ซ้อนกันสองตัวก็ได้ผลเหมือนกัน และการ `return` พูดเรื่อง
เดียวกันในบรรทัดเดียว โดยไม่ทิ้งให้คนอ่านต้องไปตรวจว่าตัวที่สองอยู่ครบไหม

## 8. ทำไมเราไม่เรียก ripgrep ไปเลย

ข้อโต้แย้งที่เห็นได้ชัดต่อทุกอย่างข้างบน `ripgrep` ซึ่งเป็นเครื่องมือ command
line ชื่อ `rg` ทำทั้งหมดนี้ได้อยู่แล้ว มันเขียนด้วย Rust มันเร็วมาก มันเคารพ
`.gitignore` โดยอัตโนมัติ มันตรวจไฟล์ไบนารีได้อย่างถูกต้อง เครื่องยนต์ regular
expression ของมันไม่มี catastrophic backtracking ให้ต้องกันตั้งแต่แรก และมันผ่าน
การจัดการกรณีขอบมาหลายปีซึ่งโค้ดไม่กี่สิบบรรทัดนี้ไม่มี และคุณก็มี `run_shell`
จากบทที่ 08 อยู่แล้ว แล้วทำไมไม่ทำ `grep_files` เป็น wrapper สองบรรทัดเสียเลย

```python
def grep_files(pattern, glob="*"):
    return run_shell(f"rg -n --glob '{glob}' '{pattern}'")
```

เพราะมันจะไม่รันบนเครื่องของคุณ และนี่คือคอร์สเรียน

`ripgrep` ไม่ใช่ส่วนหนึ่งของระบบปฏิบัติการใด มันไม่อยู่ใน Python standard library
มันไม่ได้ถูกติดตั้งด้วย `pip install` ผู้อ่านบนแล็ปท็อป Windows เครื่องใหม่ หรือ
เครื่ององค์กรที่ถูกล็อก หรือคอนเทนเนอร์ Linux แบบ minimal ไม่มีมัน และข้อความที่
พวกเขาจะได้รับคือแบบนี้

```text
'rg' is not recognized as an internal or external command,
operable program or batch file.
```

ตอนนี้ผู้อ่านคนนั้นไม่ได้เรียนเรื่องเครื่องมือค้นหาแล้ว พวกเขากำลังเรียนเรื่อง
package manager และเรื่องซอฟต์แวร์ชิ้นหนึ่งที่ไม่เกี่ยวอะไรกับหัวข้อของบทนี้เลย
บางคนจะติดตั้งมันแล้วไปต่อ บางคนจะชนกำแพงเรื่องสิทธิ์แล้วหยุด คอร์สที่ล้มเหลวที่
บทที่ 09 สำหรับผู้อ่านที่ติดตั้งไบนารีตามใจไม่ได้ ก็คือคอร์สที่ทำให้ผู้อ่านเหล่า
นั้นล้มเหลว และล้มเหลวเพราะ dependency ที่ไม่จำเป็นด้วยซ้ำ

มีเหตุผลที่สองและมันเกี่ยวกับสิ่งที่คุณได้เรียนรู้ ถ้า `grep_files` เป็น wrapper
การตัดสินใจที่น่าสนใจทั้งหมดก็อยู่ในไบนารีของคนอื่น คุณจะไม่ได้คิดเรื่องการจับคู่
ทั้ง path และชื่อ เรื่อง pattern ที่ผิดกลายเป็นข้อความ เรื่องว่าควรข้าม directory
ไหน เรื่องว่าเพดานควรอยู่ตรงไหน เรื่องหมายเลขบรรทัดที่มีไว้วางแผนไม่ใช่ไว้กระโดด
หรือเรื่องว่าทำไมเส้นตายจึงต้องใช้ process ไม่ใช่ thread สิ่งเหล่านั้นคือไอเดียที่
ถ่ายโอนไปใช้ที่อื่นได้ในบทนี้ และการเขียนการเดินต้นไม้เองคือสิ่งที่บังคับให้คุณได้
พบกับพวกมัน

standard library เพียงพอจริง ๆ ตรงนี้ `fnmatch` `re` `pathlib` `json` และ
`subprocess` ทั้งหมดมีอยู่ในทุกการติดตั้ง Python มานานก่อนที่คุณจะเริ่มอ่านสิ่งนี้
และผลลัพธ์คือ tool ที่ทำงานเหมือนกันเป๊ะบน Windows macOS และ Linux โดยไม่ต้อง
ติดตั้งอะไรเลย

ทีนี้มาถึงครึ่งที่แฟร์

**การใช้ `ripgrep` ในโปรเจกต์ของคุณเองเป็นทางเลือกที่สมเหตุสมผล** เมื่อคุณคุม
สภาพแวดล้อมได้ เมื่อมี Dockerfile หรือมีขั้นตอนติดตั้งที่จดไว้ หรือแค่บนแล็ปท็อป
ของคุณเอง การคำนวณเปลี่ยนไปโดยสิ้นเชิง `rg` เร็วกว่าราวหนึ่งถึงสองอันดับของขนาด
บน repository ขนาดใหญ่ การอ่าน `.gitignore` เป็นพฤติกรรมที่ถูกต้องพอดี และเป็นกฎ
ที่ดีกว่าเซตของชื่อ directory ที่ hardcode ไว้มาก การตรวจไบนารีของมันถูกต้อง ขณะที่
การเช็ค `UnicodeDecodeError` เป็นเพียงการประมาณแบบหยาบ บน monorepo ความต่างไม่ใช่
ของฟุ่มเฟือย มันคือความต่างระหว่าง tool ที่ agent เรียกได้อย่างอิสระ กับ tool ที่
มันต้องคิดสองรอบก่อนเรียก

วิธีแบบมืออาชีพที่จะได้ทั้งสองอย่างคือเช็คครั้งเดียวตอนเริ่มต้นแล้วมีทางถอย

```python
import shutil

HAVE_RIPGREP = shutil.which("rg") is not None
```

ถ้ามี `rg` ก็เรียกออกไปที่ shell ถ้าไม่มีก็ใช้การเดินต้นไม้ที่คุณเพิ่งเขียน schema
ของ tool ไม่เปลี่ยน model ไม่มีวันรู้ว่าอันไหนทำงาน และ agent ทำงานได้ทุกที่ ขณะที่
เร็วในที่ที่มันเร็วได้ นั่นคือแบบฝึกหัดข้อที่สาม และเป็นสิ่งที่มีประโยชน์จริงเมื่อ
ได้สร้างไว้สักครั้ง

หลักการทั่วไปคุ้มที่จะเก็บไว้ dependency ซื้อความเร็วและการครอบคลุมกรณีขอบให้คุณ
และมันทำให้คุณเสียผู้อ่านหรือผู้ใช้กลุ่มหนึ่งที่ติดตั้งมันไม่ได้ สำหรับ repository
เพื่อการสอน ต้นทุนชนะ สำหรับ tool ที่คุณ deploy ลงในสภาพแวดล้อมที่คุณคุมได้
ประโยชน์ชนะ ไม่มีคำตอบสากล มีแต่นิสัยของการสังเกตว่าคุณกำลังแลกอะไรอยู่

## 9. รัน check.py

`check.py` สร้าง workspace ปลอมขนาดเล็กใน directory ชั่วคราว แล้ว assert สี่อย่าง
เกี่ยวกับมัน

```python
workspace = Path(tempfile.mkdtemp(prefix="agentpath-lesson09-"))
os.environ["AGENTPATH_WORKSPACE"] = str(workspace)

import tools  # noqa: E402
```

ตัวแปรสภาพแวดล้อมถูกตั้งค่าก่อนที่ `tools` จะถูก import และลำดับนั้นไม่ใช่เรื่อง
สไตล์ ย้อนกลับไปดูบทที่ 07 แล้วคุณจะเห็นว่า `WORKSPACE` ถูกอ่านตอนที่โมดูลถูก
import ครั้งเดียว

```python
WORKSPACE = Path(os.environ.get("AGENTPATH_WORKSPACE", ".")).resolve()
```

ถ้า import มาก่อน `WORKSPACE` จะถูกตรึงไว้ที่ directory ปัจจุบันแล้ว และทุก
assertion ในไฟล์นี้จะค้นผิดต้นไม้ คอมเมนต์ `# noqa: E402` บอก linter ว่า import
นี้จงใจไม่อยู่บนสุดของไฟล์ ซึ่งเป็นวิธีที่ซื่อตรงในการแหกกฎสไตล์

จากนั้นคือ fixture

```python
    (workspace / "src").mkdir()
    (workspace / "src" / "main.py").write_text("def start():\n    return 1\n", encoding="utf-8")
    (workspace / "notes.md").write_text("start here\n", encoding="utf-8")
    (workspace / ".venv").mkdir()
    (workspace / ".venv" / "junk.py").write_text("def start():\n", encoding="utf-8")
```

ไฟล์สี่ไฟล์ที่เลือกมาเพื่อให้ทุก assertion มีความหมาย `src/main.py` อยู่ซ้อนใน
directory ดังนั้น pattern ที่มีส่วนประกอบเป็น directory จึงมีอะไรให้หา `notes.md`
เป็นนามสกุลอื่น ดังนั้นตัวกรอง glob จึงมีอะไรให้คัดออก และ `.venv/junk.py` จงใจมี
ข้อความเดียวกับ `src/main.py` ดังนั้นการเดินที่ล้มเหลวในการข้าม virtual
environment จะให้คำตอบที่ผิดอย่างเห็นได้ชัด แทนที่จะถูกโดยบังเอิญ

assertion ทั้งสี่

```python
    found = tools.run("glob_files", {"pattern": "**/*.py"})
    if "src/main.py" not in found:
        fail(f"glob_files did not find the source file. Got {found!r}")
    print("OK glob_files found the source file")

    if "junk.py" in found:
        fail("glob_files searched inside .venv, which it must skip")
    print("OK glob_files skipped the virtual environment")

    hits = tools.run("grep_files", {"pattern": "def start"})
    if "main.py" not in hits or ":1:" not in hits:
        fail(f"grep_files did not report the file and line number. Got {hits!r}")
    print("OK grep_files reported the file name and line number")

    limited = tools.run("grep_files", {"pattern": "start", "glob": "*.md"})
    if "notes.md" not in limited or "main.py" in limited:
        fail(f"the glob filter did not narrow the search. Got {limited!r}")
    print("OK the glob filter narrowed the search")
```

สังเกตว่าทุกอย่างผ่าน `tools.run` แทนที่จะเรียก function ตรง ๆ นั่นคือเส้นทางการ
ส่งต่อเดียวกับที่ loop ของ agent ใช้ การเช็คนี้จึงทดสอบการค้นหาชื่อ การแกะ
อาร์กิวเมนต์ และการจัดการ error ไปพร้อมกับตัวการค้นหาเอง

assertion ข้อที่สามตรวจหา `:1:` ไม่ใช่แค่ชื่อไฟล์ เพราะ tool ที่คืนแค่
`src/main.py` จะดูเหมือนทำงานได้ ทั้งที่โยนทิ้งสิ่งที่หัวข้อ 5 บอกว่าจำเป็นไปแล้ว

รันมันจากในโฟลเดอร์ของบทนี้ หรือรันทุกบทพร้อมกันจาก root ของ repository

```bash
cd lessons/09-search-tools
python check.py
```

```bash
python ci/run_lessons.py
```

การรันที่ผ่านจะมีหน้าตาแบบนี้

```text
OK glob_files found the source file
OK glob_files skipped the virtual environment
OK grep_files reported the file name and line number
OK the glob filter narrowed the search
```

สี่บรรทัด ไม่ต้องใช้เครือข่าย ไม่ต้องใช้ API key และใช้เวลาไม่ถึงหนึ่งวินาทีบน
แล็ปท็อป และเวลาส่วนใหญ่นั้นไม่ใช่การค้นหา การเรียก `grep_files` สองครั้งเริ่ม
process Python ครั้งละหนึ่งตัว นั่นคือหนึ่งในสิบวินาทีต่อการค้นหาจากหัวข้อ 5 ที่
โผล่มาบนนาฬิกาจับเวลา แทนที่จะอยู่แค่ในคอมเมนต์

สังเกตความต่างจาก check ของบทที่ 06 ซึ่งต้องมี fake server รันอยู่เพราะมันทดสอบ
provider ไม่มีอะไรในบทนี้ที่คุยกับ model เพราะ tool ค้นหาคือ function Python
ธรรมดา และข้อเท็จจริงที่ว่าสุดท้ายจะมี model มาเรียกมันนั้นไม่เกี่ยวกับว่ามันทำงาน
ได้หรือไม่ การทดสอบ tool แยกจาก loop คือประโยชน์เงียบ ๆ อย่างหนึ่งของรูปทรงที่
คอร์สนี้สร้างมาตลอด

ถ้าบรรทัดที่สองล้มเหลว แสดงว่า `_walk` ของคุณไม่ได้เช็ค `relative.parts` ถ้าบรรทัดที่
สามล้มเหลวและพิมพ์ผลลัพธ์ที่มี `src/main.py` แต่ไม่มี `:1:` แสดงว่า format string
ของคุณทำหมายเลขบรรทัดหาย ถ้าบรรทัดที่สี่ล้มเหลวและมี `main.py` อยู่ด้วย แสดงว่า
ตัวกรอง glob ไม่ได้ถูกนำมาใช้ และถ้าบรรทัดที่สามกับที่สี่ล้มเหลวทั้งคู่ด้วย
`Error: the search failed` ข้อความที่ตามหลังมันคือ standard error ของ worker เอง
ซึ่งเกือบทุกครั้งแปลว่า `grep_worker.py` ไม่ได้วางอยู่ข้าง ๆ `tools.py` หรือ
import มันไม่ได้

## 10. สิ่งที่คุณยังทำไม่ได้

มาสรุปกัน ตอนนี้ agent มี tool เจ็ดตัว

```text
read_file    write_file    edit_file    list_files
run_shell    glob_files    grep_files
```

นั่นคือชุดเต็มที่ coding agent ต้องการเพื่อเปลี่ยนโค้ดจริง ๆ มันหาไฟล์จากชื่อได้
หาข้อความในไฟล์ได้ อ่านสิ่งที่หาเจอได้ เปลี่ยนมันอย่างแม่นยำได้ สร้างไฟล์ใหม่ได้
แสดงรายการใน directory ได้ และรันคำสั่งด้วยการอนุมัติของคุณได้ ความสามารถทุกอย่าง
ในภาคสองมีครบแล้ว

และถ้าคุณต่อมันเข้าด้วยกันตอนนี้แล้วขอให้มันแก้บั๊ก มันคงจะงงงวย

นี่คือเหตุผล เริ่มบทสนทนาแล้วความรู้ทั้งหมดของ agent เกี่ยวกับโลกคือประโยคที่คุณ
พิมพ์ มันไม่รู้ว่ามันอยู่ใน directory ไหน มันไม่รู้ว่าโปรเจกต์เขียนด้วยภาษาอะไร
หรือมี test ไหม หรือรัน test อย่างไร มันไม่รู้ว่า `grep_files` ราคาถูกและมันควรค้น
ก่อนอ่าน หรือว่า `read_file` ตัดจบที่ 4000 ตัวอักษรและไฟล์ใหญ่ต้องใช้วิธีที่แคบ
กว่า มันไม่รู้ว่าเมื่อการแก้ไขล้มเหลวเพราะข้อความไม่ซ้ำใคร วิธีแก้คือใส่บรรทัด
รอบข้างเพิ่มเข้าไป ไม่ใช่ยอมแพ้ มันไม่รู้ว่ามันควรตรวจสอบการเปลี่ยนแปลง แทนที่จะ
ประกาศความสำเร็จ

ไม่มีอะไรในนั้นอยู่ใน tool schema และมันอยู่ตรงนั้นไม่ได้ schema บรรยาย function
หนึ่งตัว ยังไม่มีอะไรจนถึงตอนนี้ที่บรรยายสถานการณ์ ขั้นตอนการทำงาน หรือมาตรฐาน

คุณสร้างมือให้มันแล้ว แต่ยังไม่มีใครบอก agent ว่ามันอยู่ที่ไหนหรือควรประพฤติตัว
อย่างไร

นั่นคือบทที่ 10 ว่าด้วยกายวิภาคของ prompt มันครอบคลุมว่าอะไรควรอยู่ใน system
prompt อะไรควรอยู่ใน user message และอะไรควรอยู่ในคำบรรยาย tool ซึ่งเป็นความแตก
ต่างที่มีจริงและมีผลจริง ไม่ใช่สามชื่อของกล่องใบเดียวกัน มันคืองานที่น้อยที่สุดใน
ภาคสอง และเป็นการก้าวกระโดดครั้งเดียวที่ใหญ่ที่สุดในความสามารถที่ agent แสดงออก
เพราะมันคือความต่างระหว่าง model ที่ถือ tool เจ็ดตัว กับ model ที่รู้ว่ากำลังทำ
อะไรอยู่กับมัน

จากนั้นบทที่ 11 จะประกอบทุกอย่างเข้าเป็น coding agent ขนาดเล็กที่เปลี่ยนโค้ดใน
โฟลเดอร์ได้จริง แล้วภาคสองก็จบ

### แบบฝึกหัดก่อนไปต่อ

**ข้อหนึ่ง** ทำให้การตัดจบจากหัวข้อ 7 มองเห็นได้ ตอนนี้ tool ทั้งสองตัวหยุดที่
`MAX_RESULTS` แล้วไม่พูดอะไรเลย ดังนั้นการค้นหาที่เจอสี่พันแมตช์กับการค้นหาที่เจอ
สองร้อยแมตช์พอดี ให้ output ที่ model แยกไม่ออก มันอ่านสองร้อยบรรทัด สรุปว่ามัน
เห็นครบแล้ว แล้วก็แคบลงไปผิดทาง เปลี่ยน tool ทั้งสองให้ต่อท้ายบรรทัดอย่างเช่น
`[stopped at 200 results, narrow the pattern or the glob]` ซึ่งแปลว่า worker
ต้องนับต่อไปเกินเพดานแทนที่จะ return ทันที และต้องส่งข้อเท็จจริงนั้นกลับไปหา
process แม่ใน JSON ด้วย จากนั้นเขียน check ที่สร้างสามร้อยบรรทัดที่แมตช์และ
assert ว่าหมายเหตุนั้นอยู่ตรงนั้น ข้อนี้มีค่าที่สุดใน
สามข้อ เพราะมันเป็นข้อบกพร่องจริง และอาการของมันคือคำตอบที่ผิดอย่างมั่นใจ ไม่ใช่
error

**ข้อสอง** ทำให้ `SKIP_DIRECTORIES` เลิกเป็นการเดา หัวข้อ 6 ยอมรับไปแล้วว่าเซตนี้
ถูกเขียนตายตัว ดังนั้น `vendor` `target` `.next` และ `dist` จึงถูกเดินเต็ม ๆ บน
โปรเจกต์ที่มีมัน อ่าน `.gitignore` ของ workspace ตอน import แล้วเพิ่มชื่อ
directory ทุกอันที่มันระบุลงในเซต โดยถอยกลับไปใช้ค่าคงที่ปัจจุบันเมื่อไม่มีไฟล์นั้น
ส่วนที่น่าสนใจคือการตัดสินใจว่าคุณยอมรับที่จะรองรับรูปแบบ `.gitignore` ได้มากแค่
ไหน เพราะสเปกเต็มมีทั้งการปฏิเสธ การยึดตำแหน่ง และไฟล์แยกต่อ directory และการ
หยุดแต่เนิ่น ๆ อย่างตั้งใจคือการตัดสินใจทางวิศวกรรมจริง ไม่ใช่ความขี้เกียจ

**ข้อสาม** สร้างทางถอยไปหา `ripgrep` จากหัวข้อ 8 ตรวจหา `rg` ด้วย `shutil.which`
ตอน import เรียกออกไปที่ shell เมื่อมันมีอยู่ และใช้การเดินต้นไม้ที่มีอยู่เมื่อ
มันไม่มี ส่วนที่น่าสนใจคือการทำให้ทั้งสองเส้นทางผลิตรูปแบบ output ที่เหมือนกันเป๊ะ
เพราะ model ต้องแยกไม่ออกว่าอันไหนทำงาน จากนั้นจับเวลาทั้งสองบน repository ขนาด
ใหญ่ แล้วดูด้วยตาตัวเองว่า Rust นั้นมีค่าแค่ไหน
