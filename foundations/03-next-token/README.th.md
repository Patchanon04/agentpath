# บทพื้นฐานที่ 3 model ทำนายคำถัดไป

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทพื้นฐานบทที่สามของหนังสือ ที่
[book/00c-next-token.md](../../book/00c-next-token.md) ตัวบทบอกว่า language model
ทำอะไรกันแน่ ในประโยคเดียว แล้วสร้างมันขึ้นมาในห้าสิบบรรทัดด้วยการนับ ไฟล์นี้คือ
ฉบับสั้นสำหรับรันโค้ด

ไม่มี model ให้เรียก ไม่มี API key Python ล้วน

## มีอะไรอยู่ในนี้

`ngram.py` คือตัว model `train` นับว่าอะไรตามหลังแต่ละชุดคำ `probabilities` แปลง
จำนวนนับเป็นการแจกแจง `next_word` สุ่มจากมันโดยมี temperature และ `generate`
ทำนาย ต่อท้าย แล้วทำซ้ำ loop ใน `generate` คือบรรพบุรุษของ agent loop ที่คอร์สนี้สร้าง

```python
def generate(model, start, n=2, length=12, temperature=1.0, rng=random):
    """Predict, append, repeat. This loop is the ancestor of the agent loop."""
    out = list(start)
    for _ in range(length):
        word = next_word(model, out[-(n - 1) :], temperature, rng)
        if word is None:
            break
        out.append(word)
    return " ".join(out)
```

มันทำงานกับคำแทน token ของบทก่อน เพียงเพราะคำอ่านง่ายกว่าบนหน้ากระดาษ

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python ngram.py
```

```text
after 'the' the model has seen {'agent': 8, 'file': 2, 'tool': 2, 'result': 2, 'loop': 1, ...}

temperature 0
   the agent reads the agent reads the agent reads the agent reads the
temperature 1.0
   the agent reads the agent decides again . the agent reads the agent
temperature 2.0
   the tool and the agent decides again . the agent decides what to

with two words of context, after 'the agent' it has seen {'reads': 4, 'decides': 3, 'runs': 1}
   the agent reads the result and the agent reads the file and the agent
```

```bash
python check.py
```

```text
OK the model is a table of counts and the counts become probabilities
OK at temperature zero the same context always gives the same word
OK the randomness is the sampling and nothing else
OK the model knows nothing it did not count
OK more context means fewer choices, and the context is the model's only memory
OK top k cuts the tail off, so a word outside the k most likely can never be drawn
```

## สิ่งที่ควรสังเกต

ที่ temperature ศูนย์ model พูดซ้ำตัวเองไม่รู้จบ เพราะหลัง `the` คำที่น่าจะเป็นที่สุดคือ
`agent` หลัง `agent` คือ `reads` และหลัง `reads` คือ `the` นั่นคือ model ที่ติดอยู่ใน
loop และคุณจะเจอรูปร่างเดียวกันนี้ในบทที่ 2 ของหนังสือในชื่อ doom loop ที่สร้างจาก
model ที่ใหญ่กว่านี้พันล้านเท่า

ความจำทั้งหมดของ model คือ context ที่คุณยื่นให้ ด้วย context หนึ่งคำ มันรู้สิบอย่าง
ที่ตามหลัง `the` ได้ ด้วยสองคำ มันรู้สามอย่างที่ตามหลัง `the agent` ได้ ไม่มีอะไรอื่น
ถูกจำระหว่างการทำนายแต่ละครั้ง ซึ่งคือข้อเท็จจริงที่หนังสือทั้งเล่มตั้งอยู่บนนั้น
