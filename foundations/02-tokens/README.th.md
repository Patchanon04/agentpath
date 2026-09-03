# บทพื้นฐานที่ 2 token คืออะไร

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทพื้นฐานบทที่สองของหนังสือ ที่
[book/00b-tokens.md](../../book/00b-tokens.md) ตัวบทอธิบายว่า token คืออะไร และทำไม
ประโยคเดียวกันในภาษาไทยถึงกินมากกว่า ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไม่มี model ไม่มี API key Python ล้วน

## มีอะไรอยู่ในนี้

`bpe.py` คือ tokenizer แบบ byte pair encoding ที่เขียนขึ้นจากศูนย์ เป็นอัลกอริทึม
เดียวกับที่อยู่เบื้องหลัง model ทุกตัวในปัจจุบัน `train` เรียนรู้การรวมคู่จากข้อความ
`encode` แปลงข้อความเป็น id `decode` แปลงกลับ และ `pieces` แสดงแต่ละ id เป็น
ข้อความที่มันแทน หัวใจของมันคือ loop เดียวที่แทนที่คู่หนึ่งด้วย id ใหม่

```python
def merge(ids, pair, new_id):
    """Replace every occurrence of pair in ids with new_id."""
    out = []
    i = 0
    while i < len(ids):
        if i + 1 < len(ids) and (ids[i], ids[i + 1]) == pair:
            out.append(new_id)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out
```

ไฟล์นี้มี corpus เล็กๆ สองชุด อังกฤษหนึ่ง ไทยหนึ่ง เพราะการทดลองคือฝึกจากชุดหนึ่ง
แล้วเอาไป encode อีกชุด

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python bpe.py
```

```text
== trained on English only, 44 merges ==
  'the agent reads the file'  24 bytes  7 tokens
    ['t', 'he ', 'agent reads', ' the ', 'f', 'i', 'le']
  'agent อ่านไฟล์'  30 bytes  25 tokens
    ['agent ', '<e0>', '<b8>', '<ad>', '<e0>', '<b9>', '<88>', ...]

== trained on both, 44 merges ==
  'the agent reads the file'  24 bytes  9 tokens
  'agent อ่านไฟล์'  30 bytes  9 tokens
    ['a', 'gent ', 'อ่า', '<e0 b8 99 e0 b9>', '<84 e0 b8>', '<9f>', 'ล', '<e0 b9>', '<8c>']
```

```bash
python check.py
```

```text
OK a vocabulary of 300 is 256 bytes plus 44 learned merges
OK before any merge, a token is a byte
OK encode then decode gives the text back
OK the same Thai sentence costs over twice as much under a tokenizer that never saw Thai
OK a token is a run of bytes and can split a character
```

## สิ่งที่ควรสังเกต

tokenizer ที่ไม่เคยเห็นภาษาไทยจ่าย token ให้เกือบทุก byte ของมัน ยี่สิบห้า token
สำหรับประโยคที่ภาษาอังกฤษจ่ายเจ็ด พอให้มันเห็นภาษาไทยบ้าง ประโยคเดียวกันลดเหลือเก้า
ราคาของภาษาไม่ใช่คุณสมบัติของภาษา มันคือคุณสมบัติของสิ่งที่ tokenizer ถูกฝึกมา และ
tokenizer เบื้องหลัง model ที่คุณจะเรียก ถูกฝึกจากภาษาอังกฤษเป็นส่วนใหญ่

ชิ้นในวงเล็บแหลมคือ token ที่จบกลางตัวอักษรไทย token คือแถวของ byte และไม่มีอะไร
ในอัลกอริทึมรู้ว่าตัวอักษรจบตรงไหน
