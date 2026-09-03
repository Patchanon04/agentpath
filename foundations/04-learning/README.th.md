# บทพื้นฐานที่ 4 การเรียนรู้คืออะไร

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทพื้นฐานบทที่สี่ของหนังสือ ที่
[book/00d-learning.md](../../book/00d-learning.md) ตัวบทเอาตารางนับของบทก่อน
มาแทนที่ด้วยตารางตัวเลขที่เริ่มจากค่าสุ่มแล้วเรียนรู้ ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไม่มี model ให้เรียก ไม่มี API key นี่คือโฟลเดอร์เดียวในคอร์สที่ใช้ numpy ติดตั้งก่อน

```bash
pip install numpy
```

## มีอะไรอยู่ในนี้

`learn.py` มีการฝึกทั้งหมดในห้าฟังก์ชัน `softmax` แปลงแถวตัวเลขเป็นความน่าจะเป็น
`loss` บอกว่าตารางผิดแค่ไหนเป็นตัวเลขเดียว `gradient` บอกว่าต้องขยับตัวเลขแต่ละตัว
ไปทางไหน `train` เริ่มจากค่าสุ่มแล้วก้าวลงเขาสามร้อยครั้ง และ `predict` อ่านตารางที่
ฝึกแล้วออกมา

```python
def train(text, steps=300, learning_rate=10.0, seed=0):
    """Start random, and step downhill on the loss until the steps run out."""
    words, index = vocabulary(text)
    xs, ys = pairs(text, index)
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, 0.01, size=(len(words), len(words)))
    history = []
    for _ in range(steps):
        history.append(loss(weights, xs, ys))
        weights -= learning_rate * gradient(weights, xs, ys)
    return weights, index, history
```

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python learn.py
```

```text
loss at the start 3.526, after training 0.787

after 'the', most likely first
  agent          0.363
  model          0.135
  file           0.090
  result         0.090
  tool           0.090
  ...and 'and', which never followed 'the' in the text, gets 0.0004
```

```bash
python check.py
```

```text
OK softmax turns any row of numbers into probabilities that sum to one
OK every step goes downhill and the loss more than halves
OK the grid learned what the count table knew, without a count table
OK a word never seen in that position still gets a small chance rather than none
OK the gradient points uphill, so stepping against it goes down
OK one hot times the grid is a row lookup, and the row is the embedding
```

## สิ่งที่ควรสังเกต

บทก่อนนับแล้วพบว่า `agent` ตามหลัง `the` สามสิบหกเปอร์เซ็นต์ของเวลา บทนี้ไม่เคยนับ
มันเริ่มจากตัวเลขสุ่ม และหลังจากขยับสามร้อยครั้ง มันเชื่อว่าสามสิบหกเปอร์เซ็นต์ ไม่มี
ใครบอกคำตอบมัน loss บอกมันว่าทางไหนผิดน้อยลง สามร้อยครั้ง

คำว่า `and` ไม่เคยตามหลัง `the` ในข้อความ การนับให้มันศูนย์ ตารางให้มันสี่ในหมื่น
ซึ่งน้อยแต่ไม่ใช่ศูนย์ และช่องว่างนั้นคือความต่างระหว่างตารางกับ model ตารางรู้แค่
สิ่งที่มันเห็น model มีความเห็นต่อทุกอย่าง ด้วยความมั่นใจมากบ้างน้อยบ้าง
