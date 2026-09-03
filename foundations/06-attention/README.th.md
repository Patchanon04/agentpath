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

ส่วนที่เหลือของไฟล์คือส่วนประกอบที่ model จริงห่อรอบหัวนั้น แต่ละชิ้นเล็กพอจะอ่านได้
`position_vectors` ใส่ลำดับกลับเข้าไป เพราะ attention เองแยก token แรกจาก token สุดท้าย
ไม่ออก `multi_head` รันหลายหัวเคียงข้างกันเพื่อให้หนึ่งชั้นถือรูปแบบว่าใครมองใครได้หลาย
แบบ `layer_norm` รักษาตัวเลขให้อยู่ในช่วง และ `feed_forward` คือครึ่งของ block ที่แต่ละ
token คิดคนเดียว ส่วน `block` ประกอบสองครึ่งเข้าด้วยกันด้วย residual จาก `finish_head`
`attend_with_cache` คือการสร้างทีละ token โดยเก็บ key กับ value ของ token ก่อนหน้าไว้
แทนที่จะคำนวณใหม่ ซึ่งคือ KV cache และ `key_rows_computed` คือเลขคณิตที่บอกว่าทำไม
มันถึงมีอยู่

```python
def block(x, heads, w_out, w_in, w_ff):
    """One transformer block. A real model is this, dozens of times, in a stack."""
    x = x + multi_head(layer_norm(x), heads, w_out)
    x = x + feed_forward(layer_norm(x), w_in, w_ff)
    return x
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

without positions, reversing the tokens reverses the output rows and nothing else
  same rows in the other order: True
with positions added, the same tokens in the other order give a different output
  same rows in the other order: False

key and value rows computed to generate, one token at a time
        4 tokens                10 without the cache          4 with it
    1,000 tokens           500,500 without the cache      1,000 with it
  100,000 tokens     5,000,050,000 without the cache    100,000 with it
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
OK a head adjusts a token rather than replacing it, and the adjustment is added on
OK without positions attention cannot tell the order, reversing tokens reverses the rows
OK with position vectors added the same tokens in another order give a different output
OK layer norm gives every token mean zero and spread one, whatever it started as
OK the feed forward layer works on each token alone, one token changed is one row changed
OK a block returns tokens the same shape it was given, which is what lets blocks stack
OK feeding tokens through the cache one at a time gives exactly what masked attention gives
OK with the cache a thousand tokens cost a thousand key rows instead of half a million
```

## สิ่งที่ควรสังเกต

อ่านแถวของ `sat` มันวาง 0.91 ของความสนใจไว้ที่ `cat` เพราะตาราง query ถูกสร้างให้
ชี้ไปตรงนั้น ใน model จริงไม่มีใครสร้างตารางนั้น มันถูกเรียนรู้ด้วยวิธีของบทที่ 4 และสิ่ง
ที่มันเรียนคือ token ไหนควรมองที่ token ไหน กริยาเรียนรู้ที่จะมองประธานของมัน เพราะ
การทำแบบนั้นทำให้ token ถัดไปทายง่ายขึ้น

มุมขวาบนของตารางเป็นศูนย์ทั้งหมด นั่นคือ mask model ที่ทายคำถัดไปต้องไม่ได้รับ
อนุญาตให้เห็นมัน ทุก token จึงมองได้เฉพาะสิ่งที่มาก่อน

ตารางที่สามคือเหตุผลทั้งหมดที่ context window ถูกคิดราคาแบบที่เป็น ทุก token ให้
คะแนนกับทุก token หนึ่งแสน token คือหมื่นล้านคะแนน ต่อหนึ่งชั้น ต่อหนึ่งหัว และ model
ที่คุณเรียกมีทั้งสองอย่างนั้นอย่างละหลายสิบ

ถัดมาคือสองบรรทัดที่บอกว่า True กับ False กลับลำดับสี่ token โดยไม่เปลี่ยนอย่างอื่น
แถวของ output กลับลำดับตามและไม่มีอะไรอื่นขยับ attention ไม่รู้เลยว่า token ไหนมาก่อน
เพราะ query คูณ key ไม่มีอะไรที่รู้เรื่องลำดับ บวก vector ตำแหน่งเข้าไป สี่ token เดิม
กลับหลังให้คำตอบต่างออกไป model ทุกตัวที่คุณเรียกทำอย่างใดอย่างหนึ่งในนี้ บวก vector
ตำแหน่งหรือหมุนตามตำแหน่ง และถ้าไม่ทำ `the cat sat down` กับ `down sat cat the` จะ
เป็นประโยคเดียวกัน

ตารางสุดท้ายคือเหตุผลที่หน่วยความจำของ model ที่ให้บริการโตตามความยาวของบทสนทนา
และเหตุผลที่ prompt ที่ server ถืออยู่แล้วถูกกว่า การสร้างทีละ token โดยไม่มี cache
คำนวณ key กับ value ของ token ก่อนหน้าทุกตัวใหม่ทุกก้าว และผลรวมนั้นคือห้าแสนแถว
สำหรับพัน token มี cache แล้วแต่ละตัวคำนวณครั้งเดียว `check.py` ยืนยันว่าการป้อน token
ผ่าน cache ทีละตัวให้แถวเดียวกันเป๊ะกับ masked attention ที่ทำทั้งหมดในครั้งเดียว ซึ่ง
คือประเด็นทั้งหมด คำตอบเดิม และงานลดลงราวครึ่งหนึ่งของความยาวลำดับเท่า ที่พัน token
คือห้าร้อยเท่า
