# ภาคฝึกที่ 2 LoRA บนตารางที่นับได้

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทที่สองของภาค 4 ของหนังสือ ที่
[book/18-lora.md](../../book/18-lora.md) ตัวบทเอาตารางจากบทพื้นฐานที่ 4 มา fine-tune
สองวิธีบนข้อความใหม่ แล้วให้เห็นว่า LoRA ให้อะไรและไม่ให้อะไร ไฟล์นี้คือฉบับสั้นสำหรับ
รันโค้ด

ไฟล์ numpy ไม่ต้องใช้ GPU `train_lora.py` ต้องใช้

## มีอะไรอยู่ในนี้

`grid.py` คือ model ของบทพื้นฐานที่ 4 ที่ยกเข้ามาในภาค 4 เพื่อให้ทุกการทดลองที่นี่ฝึกของชิ้นเดียวกัน
มี corpus สองชุด ข้อความฐานกับข้อความใหม่ และฟังก์ชันฝึกจากภาคพื้นฐาน มันอยู่ในอีกสอง
โฟลเดอร์ถัดไปโดยไม่เปลี่ยน

`lora.py` fine-tune ตารางนั้นบนข้อความใหม่ `full_finetune` ขยับทุกตัวเลข `lora_finetune`
ตรึงตารางไว้แล้วเรียนรู้คู่ตารางบางๆ ที่ผลคูณคือการเปลี่ยนแปลง และ `merge` บวกผลคูณเข้าไป
ให้ adapter หายเข้าไปในตารางธรรมดา `parameters` นับ

```python
def lora_finetune(weights, xs, ys, rank=2, steps=300, learning_rate=2.0, seed=0):
    """Keep the grid frozen. Learn a thin pair whose product is the change."""
    rng = np.random.default_rng(seed)
    size = weights.shape[0]
    down = rng.normal(0, 0.01, size=(size, rank))
    up = np.zeros((rank, size))
    for _ in range(steps):
        full_change = gradient(weights + down @ up, xs, ys)
        down_change = full_change @ up.T
        up_change = down.T @ full_change
        down -= learning_rate * down_change
        up -= learning_rate * up_change
    return down, up
```

`train_lora.py` คือแนวคิดเดียวกันบน model แบบเปิด โดย peft เพิ่มคู่ตารางบางๆ ข้างทุก
ตาราง attention และ feed-forward และ trl รัน loop บนไฟล์แชทที่โฟลเดอร์ก่อนหน้าเขียน ไม่ได้รันใน CI

`check.py` ยืนยันข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python lora.py
```

```text
41 words, a grid of 1681 numbers

                    loss on old text   on new text   numbers trained
frozen model                   0.787         3.505                 0
full finetune                  1.924         0.725              1681
lora rank 2                    2.466         0.942               164
lora, old text too             0.922         1.363               164

the change lora made has 2 independent directions in a 41 by
41 grid, and after merging the model is a plain grid again
```

```bash
python check.py
```

```text
OK lora learns the new text nearly as well as nudging every number does
OK and it trains under a tenth of the numbers to do it
OK the change has two independent directions, and merging gives a plain grid back
OK up starts at zero, so before training the adapter changes nothing at all
OK forgetting is real, both methods forget, and mixing the old text back in is the cure
```

บน GPU

```bash
pip install "agentpath-kit[training]"
python train_lora.py clean.jsonl --output adapter --merge
```

## สิ่งที่ควรสังเกต

อ่านตารางทีละคอลัมน์ คอลัมน์ข้อความใหม่คือสิ่งที่ fine-tuning มีไว้ทำ และ LoRA ตามหลัง
full fine-tuning ราวหนึ่งในห้าของหน่วย loss ตรงนั้น โดยฝึก 164 ตัวเลขแทนที่จะเป็น 1681 อัตราส่วนนั้นคือ
เหตุผลทั้งหมดที่วิธีนี้มีอยู่ บน model จริงคู่ตารางบางๆ คือเศษเสี้ยวของเปอร์เซ็นต์ของ
weight และหน่วยความจำที่ full fine-tuning ต้องใช้สำหรับ gradient กับสถานะของ optimizer
ซึ่งคือหลายเท่าของ weight ก็หดตามไปด้วย

ทีนี้อ่านคอลัมน์ข้อความเก่า ทั้งสองวิธีแย่ลงบนสิ่งที่ model รู้อยู่แล้ว และ LoRA แย่ลง
มากกว่า การลืมไม่ใช่สิ่งที่ LoRA แก้ และแถวสุดท้ายคือสิ่งที่แก้ ฝึกบนข้อความเก่าด้วย แล้ว
model รักษา 0.922 บนของเก่าไว้ได้ขณะที่ยังเรียนของใหม่ ยาแก้การลืมคือข้อมูล ไม่ใช่วิธี

`up` เริ่มที่ศูนย์ นั่นไม่ใช่รายละเอียด มันแปลว่า adapter มองไม่เห็นก่อนฝึก ก้าวที่ศูนย์
จึงคือ model ที่ตรึงไว้เป๊ะๆ และ LoRA ทุก implementation ทำแบบนี้ด้วยเหตุผลนั้น `check.py`
พิสูจน์ด้วยการฝึกศูนย์ก้าว
