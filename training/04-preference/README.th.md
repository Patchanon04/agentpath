# ภาคฝึกที่ 4 ปรับตามความชอบ โดยไม่มี reward model

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทที่สี่ของภาค 4 ของหนังสือ ที่
[book/20-preference.md](../../book/20-preference.md) ตัวบทเอาการฝึกรอบที่สามจากบท
พื้นฐานที่ 7 คือการปรับตามความชอบ มารันบนตารางของบทพื้นฐานที่ 4 ด้วย DPO โดยความชอบหนึ่งข้อคือ
คู่ของคำถัดไป ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไฟล์ numpy ไม่ต้องใช้ GPU `train_dpo.py` ต้องใช้

## มีอะไรอยู่ในนี้

`grid.py` ตารางของบทพื้นฐานที่ 4 ไม่เปลี่ยนจากโฟลเดอร์ก่อน

`dpo.py` มี loss กับ gradient ของมัน `dpo_loss` บอกว่า model ห่างจากการชอบ chosen มากกว่า
rejected แค่ไหน เทียบกับ reference ที่ตรึงไว้ `dpo_gradient` คือ loss นั้นที่หาอนุพันธ์ด้วย
chain rule `train_dpo` ก้าวลงเขาบนมัน และ `drift` วัดว่า model ทั้งตัวขยับไปไกลแค่ไหน ซึ่ง
คือสิ่งที่พจน์ reference มีไว้จำกัด

```python
def dpo_loss(weights, reference, preferences, index, beta=1.0):
    """How far the policy is from preferring chosen over rejected, relative to the reference."""
    total = 0.0
    for context, chosen, rejected in preferences:
        policy_margin = log_probability(weights, context, chosen, index) - log_probability(
            weights, context, rejected, index
        )
        reference_margin = log_probability(reference, context, chosen, index) - log_probability(
            reference, context, rejected, index
        )
        total += -np.log(sigmoid(beta * (policy_margin - reference_margin)))
    return total / len(preferences)
```

`train_dpo.py` คือ loss เดียวกันบน model แบบเปิด โดย trl ถือ reference กับ loop และไฟล์
ของคู่ความชอบเป็นข้อมูล ไม่ได้รันใน CI

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python dpo.py
```

```text
dpo loss at the start 0.693, after training 0.013

after 'the agent'   reference   tuned
  asks              0.000    0.003
  runs              0.121    0.015
  reads             0.496    0.554
  decides           0.371    0.415

mean change in every probability of the model 0.0015
the same with plain finetuning on the chosen words only 0.0043
```

```bash
python check.py
```

```text
OK at the start the loss is log two, because the policy and the reference agree exactly
OK the loss falls, with no reward model and no reinforcement learning anywhere
OK every chosen word gains on its rejected word, relative to where the reference was
OK the reference term keeps the model near where it started, plain finetuning drifts more
OK beta only matters once the policy has moved, it is the leash and not the direction
```

บน GPU

```bash
pip install "agentpath-kit[training]"
python train_dpo.py pairs.jsonl --model adapter-merged --output dpo-adapter
```

## สิ่งที่ควรสังเกต

loss เริ่มที่ 0.693 ซึ่งคือ log สอง และนั่นไม่ใช่เรื่องบังเอิญ ที่ก้าวศูนย์ policy คือ
reference ส่วนต่างหักล้างกัน sigmoid อยู่ที่ครึ่ง และลบ log ครึ่งคือ log สอง DPO ทุกการรัน
เริ่มตรงนั้น และการรันที่ไม่เริ่มตรงนั้นมีบั๊กใน reference

อ่านแถว `runs` คำที่ถูกปฏิเสธตกจาก 0.121 เหลือ 0.015 ขณะที่คำที่ถูกเลือกแทบไม่ขึ้น เพราะ
model ฐานไม่เคยเห็น `asks` ตามหลัง `agent` และการขยับหกสิบก้าวพาคำหนึ่งจากศูนย์ไปได้แค่
นั้น การปรับตามความชอบดัน rejected ลงได้ง่ายกว่าดึง chosen ขึ้นมาก และบน model จริงนั่นคือ
ที่ที่ผลของมันแสดงออกมากที่สุด ในสิ่งที่ model เลิกพูด

สองบรรทัดสุดท้ายคือพจน์ reference ทำงานของมัน DPO ขยับความน่าจะเป็นของ model โดยเฉลี่ย
0.0015 fine-tuning ธรรมดาบนคำที่ถูกเลือกอย่างเดียว ก้าวเท่ากันอัตราเท่ากัน ขยับสามเท่าของ
นั้น reference คือสายจูง beta คือความยาวของมัน และมันคือความต่างทั้งหมดระหว่าง model ที่
เรียนรู้ความชอบ กับ model ที่ลืมทุกอย่างอื่นเพื่อสนองมัน
