# ภาคฝึกที่ 1 ข้อมูลคือตัว fine-tune

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทแรกของภาค 4 ของหนังสือ ที่
[book/17-dataset.md](../../book/17-dataset.md) ตัวบทบอกว่าการ fine-tune หนึ่งรอบคือ
โค้ดฝึกไม่กี่บรรทัดกับรายการยาวของการตัดสินใจเรื่องข้อมูล และการตัดสินใจคือจุดที่การรัน
พังกัน ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไม่มี model ให้เรียก ไม่มี API key ไม่มี GPU Python ล้วน

## มีอะไรอยู่ในนี้

`dataset.py` คือการตัดสินใจพวกนั้นในรูปฟังก์ชัน บนตัวอย่างแชทเจ็ดตัวอย่างที่มีปัญหาแบบ
เดียวกับ dataset จริง `normalise` ทำให้ความต่างเชิงผิวมองไม่เห็น `exact_dedupe` ตัด
สำเนา `near_dedupe` ตัดสำเนาที่เกือบเหมือนด้วยการเทียบชุดคำที่เรียงติดกัน `decontaminate`
ตัดทุกอย่างที่เป็นคำถามในชุดวัดผล และ `quality_filter` ตัดคำตอบที่สั้นเกินกว่าจะสอนอะไรได้
`to_chat_jsonl` เขียนสิ่งที่รอดออกมาในรูปที่ trainer ของบทถัดไปอ่าน และ `clean` รันทั้ง
สายพร้อมนับทุกขั้น

```python
def near_dedupe(examples, threshold=0.8):
    """Drop an example whose prompt shares most of its word runs with one already kept."""
    kept = []
    for example in examples:
        mine = shingles(example["prompt"])
        if all(jaccard(mine, shingles(other["prompt"])) < threshold for other in kept):
            kept.append(example)
    return kept
```

`build_dataset.py` คือสายเดียวกันบนไฟล์ JSONL จริง มีไฟล์วัดผลให้กันออก และ output ที่
บทถัดไปเอาไปฝึก มันรันได้ทุกที่ เพราะนี่คือส่วนของ fine-tuning ที่ไม่ต้องใช้ GPU

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python dataset.py
```

```text
started with 7 examples
  dropped 1 for exact duplicates
  dropped 1 for near duplicates
  dropped 1 for evaluation questions
  dropped 1 for answers too short
kept 3

the first line of the file a trainer would read
{"messages": [{"role": "system", "content": "You are a careful software assistant."}, {"role": "user", "content": "Rename the variable x to total in math.py"}, {"role": "assistant", "content": "Edited math.py, x is now total in both places it appeared."}]}
```

```bash
python check.py
```

```text
OK an exact duplicate is dropped after normalising, so a full stop does not hide it
OK a near duplicate that exact matching misses is caught by comparing word runs
OK an example that is an evaluation question is removed, so the score cannot lie
OK the answer too short to teach anything is dropped, and the filter says how many
OK what a trainer reads is the same messages list the course sends over HTTP, one per line
OK seven examples in, three out, and the report says where every one of the four went
```

บนไฟล์จริง

```bash
python build_dataset.py raw.jsonl clean.jsonl --eval eval.jsonl
```

## สิ่งที่ควรสังเกต

เจ็ดเข้า สามออก และสี่ตัวที่หายไปทุกตัวถูกบอกชื่อ สายที่ตัดข้อมูลครึ่งหนึ่งทิ้งเงียบๆ คือ
สายที่ไม่มีใครสังเกตจนกว่า model จะแย่ลง และรายงานคือการป้องกันทั้งหมด

สำเนาที่เกือบเหมือนคือตัวที่คนพลาด `Please rename the variable x` กับ `Rename the
variable x` ไม่ใช่ string เดียวกัน และการเทียบตรงตัวเก็บไว้ทั้งคู่ มันมีชุดสามคำที่เรียง
ติดกันร่วมกันหกจากเจ็ดชุด และแค่นั้นพอ สายจริงทำเรื่องนี้ด้วย MinHash เพื่อให้เทียบล้าน
ตัวอย่างได้ และแนวคิดเหมือนกัน เทียบชุดคำ ไม่ใช่ทั้ง string

บรรทัดสุดท้ายของการรันคือรายการ messages จากบทเรียนที่ 01 บนดิสก์ trainer ใส่ chat
template ของ model ให้มัน คือบทพื้นฐานที่ 7 ในขนาดจริง ข้อความที่ model เรียนจากจึงเป็น
string เดียวกันเป๊ะกับที่มันจะเห็นตอนคอร์สเรียกมัน
