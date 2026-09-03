# บทพื้นฐานที่ 5 ความหมายเป็นทิศทาง

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทพื้นฐานบทที่ห้าของหนังสือ ที่
[book/00e-meaning-as-direction.md](../../book/00e-meaning-as-direction.md)
ตัวบทอธิบายว่าทำไมคำถึงกลายเป็นชุดตัวเลข และการที่สองคำอยู่ใกล้กันแปลว่าอะไร
ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไม่มี model ให้เรียก ไม่มี API key ใช้ numpy

## มีอะไรอยู่ในนี้

`vectors.py` สร้าง embedding แบบเก่าแก่ที่สุดที่มี `cooccurrence` นับว่าคำแต่ละคำ
มีคำไหนปรากฏใกล้ๆ บ้าง และแถวของจำนวนนับนั้นคือ vector ของคำ `cosine` เทียบสอง
vector ด้วยทิศทางอย่างเดียว `euclidean` เทียบด้วยระยะทางเส้นตรง และ `nearest`
จัดอันดับทุกคำอื่นด้วย cosine

```python
def cosine(a, b):
    """How much two vectors point the same way, ignoring how long they are."""
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
```

corpus ถูกสร้างให้ `cat` กับ `dog` ทำสิ่งเดียวกัน และ `agent` กับ `model` ทำสิ่ง
เดียวกัน โดยไม่มีบรรทัดไหนในโค้ดถูกบอกเรื่องนี้

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python vectors.py
```

```text
nearest to 'cat'
  dog      0.979
  bone     0.928
  fish     0.928
nearest to 'agent'
  model    0.998
  file     0.952
  result   0.952

cat appears 5 times, dog 3
cosine(cat, dog) 0.979   euclidean(cat, dog) 5.74
cosine(cat, file) 0.854   euclidean(cat, file) 7.28
```

```bash
python check.py
```

```text
OK words used the same way point the same way, and nobody defined either
OK the two groups in the text are two groups in the space
OK cosine is one for the same direction
OK cosine ignores how common a word is and euclidean does not
OK cat is more common than dog and is still its nearest neighbour
```

## สิ่งที่ควรสังเกต

ไม่มีใครนิยาม `cat` คำที่ใกล้มันที่สุดคือ `dog` เพราะทั้งสองคบเพื่อนกลุ่มเดียวกัน และ
นั่นคือแนวคิดทั้งหมด ความหมายสำหรับเครื่องคือเพื่อนที่คำนั้นคบ เขียนเป็นทิศทาง

`cat` ปรากฏห้าครั้ง `dog` สามครั้ง vector ของ `cat` จึงยาวกว่า cosine ไม่สน และนั่นคือ
เหตุผลที่มันเป็นการเทียบที่ทุกคนใช้ ระยะทางแบบ euclidean จะบอกว่าคำที่พบบ่อยอยู่ไกล
จากคำหายากที่ความหมายเดียวกัน

`cat` กับ `file` ยังได้ 0.854 ซึ่งสูงสำหรับสองคำที่ไม่มีอะไรร่วมกัน ทั้งคู่อยู่ข้าง `the`
และ `the` อยู่ข้างทุกอย่าง embedding จริงถ่วงน้ำหนักคำที่ปรากฏทุกที่ลงด้วยเหตุผลนี้
พอดี ตัวบทบอกว่าทำยังไง
