# บทพื้นฐานที่ 1 ข้อความคือตัวเลข

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทพื้นฐานบทแรกของหนังสือ ซึ่งอธิบายว่าทำไมคอมพิวเตอร์
ไม่เคยเห็นตัวอักษร และมันเห็นอะไรแทน ตัวบทอยู่ที่ [book/00a-text-is-numbers.md](../../book/00a-text-is-numbers.md)
ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไม่มีอะไรในนี้คุยกับ model ไม่ต้องตั้ง API key เป็น Python ล้วนและรันได้ทุกที่ที่มี Python

## มีอะไรอยู่ในนี้

`text.py` มีฟังก์ชันเล็กๆ สี่ตัว `code_points` ให้เลข Unicode ของแต่ละตัวอักษร
`utf8_bytes` ให้ byte ที่ถูกเก็บหรือส่งจริง `cost` นับทั้งสองอย่างแล้วหาร และ
`combining_marks` แยกตัวอักษรที่เป็นเครื่องหมายซ้อนบนตัวอักษรอื่นออกมาจากตัวอักษรจริง

```python
def cost(text):
    """Characters, bytes, and how many bytes each character cost on average."""
    characters = len(text)
    byte_count = len(text.encode("utf-8"))
    return {
        "characters": characters,
        "bytes": byte_count,
        "bytes_per_character": byte_count / characters if characters else 0.0,
    }
```

`check.py` ยืนยันตัวเลขที่บทยกมา ถ้าวันไหนมันผิดบนเครื่องคุณ คุณจะรู้จากตรงนี้
ไม่ใช่จากการเชื่อหน้ากระดาษ

## รันมัน

```bash
python text.py
```

มันพิมพ์ทุกตัวอักษรของ `hello` และ `สวัสดี` พร้อม code point และ byte ของแต่ละตัว
แล้วรันตัวตรวจ

```bash
python check.py
```

```text
OK hello costs one byte per character and สวัสดี costs three
OK the code point and the bytes match the chapter
OK two of the six characters are marks stacked on a consonant
OK bytes turn back into the same text
```

## สิ่งที่ควรสังเกต

`สวัสดี` คือหกตัวอักษรและสิบแปด byte `hello` คือห้าและห้า จำนวนสิ่งที่พูดออกมาเท่ากัน
แต่ที่เก็บต่างกันสามเท่า และนี่คือก่อนที่ model จะแตะอะไรเลย บทพื้นฐานถัดไปจะให้เห็น
ช่องว่างเดิมเปิดออกอีกครั้งที่ระดับ token ซึ่งเป็นระดับที่คิดเงิน
