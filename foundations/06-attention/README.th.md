# บทพื้นฐานที่ 6 attention

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทพื้นฐานบทที่หกของหนังสือ ที่
[book/00f-attention.md](../../book/00f-attention.md) ตัวบทอธิบายกลไกที่เปลี่ยนทุกอย่าง
ในปี 2017 และเหตุผลที่มันทำให้ context ยาวมีราคาอย่างที่เป็น ไฟล์นี้คือฉบับสั้นสำหรับ
รันโค้ด

ไม่มี model ให้เรียก ไม่มี API key ใช้ numpy

## มีอะไรอยู่ในนี้

`attention.py` มี attention หนึ่งหัวในสิบกว่าบรรทัด `attention` แปลงแต่ละ token เป็น
query key และ value ให้คะแนนทุก query กับทุก key แล้วผสม value ตามคะแนนนั้น
`causal_mask` ซ่อนอนาคต `score_count` คือเลขคณิตเบื้องหลังต้นทุนกำลังสอง และ
`hand_built_grids` ตั้งน้ำหนักด้วยมือให้ `sat` มองไปที่ `cat` ซึ่งคือสิ่งที่ model จริง
จะเรียนรู้เอง

```python
def attention(x, w_query, w_key, w_value, mask=None):
    """One head of attention over a sequence of token vectors."""
    queries = x @ w_query
    keys = x @ w_key
    values = x @ w_value
    scores = queries @ keys.T / np.sqrt(keys.shape[1])
    if mask is not None:
        scores = scores + mask
    weights = softmax(scores)
    return weights @ values, weights
```

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python attention.py
```

```text
who looks at whom, rows are the token looking, columns the token looked at
             the     cat     sat    down
     the    1.00    0.00    0.00    0.00
     cat    0.38    0.62    0.00    0.00
     sat    0.05    0.91    0.05    0.00
    down    0.22    0.22    0.22    0.35

scores needed for a sequence of
        4 tokens                16
    1,000 tokens         1,000,000
  100,000 tokens    10,000,000,000
```

```bash
python check.py
```

```text
OK each token spreads exactly one unit of attention over the sequence
OK with the grids set to say so, sat looks at cat and mostly nothing else
OK the mask hides the future completely and the rows still sum to one
OK the first token has nothing before it and attends to itself
OK doubling the context quadruples the work, which is why long context costs what it does
```

## สิ่งที่ควรสังเกต

อ่านแถวของ `sat` มันวาง 0.91 ของความสนใจไว้ที่ `cat` เพราะตาราง query ถูกสร้างให้
ชี้ไปตรงนั้น ใน model จริงไม่มีใครสร้างตารางนั้น มันถูกเรียนรู้ด้วยวิธีของบทที่ 4 และสิ่ง
ที่มันเรียนคือ token ไหนควรมองที่ token ไหน กริยาเรียนรู้ที่จะมองประธานของมัน เพราะ
การทำแบบนั้นทำให้ token ถัดไปทายง่ายขึ้น

มุมขวาบนของตารางเป็นศูนย์ทั้งหมด นั่นคือ mask model ที่ทายคำถัดไปต้องไม่ได้รับ
อนุญาตให้เห็นมัน ทุก token จึงมองได้เฉพาะสิ่งที่มาก่อน

และตารางสุดท้ายคือเหตุผลทั้งหมดที่ context window ถูกคิดราคาแบบที่เป็น ทุก token ให้
คะแนนกับทุก token หนึ่งแสน token คือหมื่นล้านคะแนน ต่อหนึ่งชั้น ต่อหนึ่งหัว และ model
ที่คุณเรียกมีทั้งสองอย่างนั้นอย่างละหลายสิบ
