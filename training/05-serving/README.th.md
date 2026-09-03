# ภาคฝึกที่ 5 การให้บริการคือเลขคณิต

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทสุดท้ายของภาค 4 ของหนังสือ ที่
[book/21-serving.md](../../book/21-serving.md) ตัวบทบอกว่าสิ่งที่ model ที่ให้บริการทำ
ส่วนใหญ่ ใช้หน่วยความจำเท่าไหร่ รับคนพร้อมกันได้กี่คน และสร้างข้อความเร็วแค่ไหน ทำนายได้
ด้วยการคูณก่อนจะแตะ GPU ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไม่มีอะไรที่นี่ต้องใช้ GPU และไม่มีอะไรที่นี่ถูกวัดด้วย มันคือการคูณทั้งหมด และประเด็นคือ
การคูณพาไปได้ไกลแค่ไหน

## มีอะไรอยู่ในนี้

`serving.py` เก็บรูปร่างของ model แบบเปิดสามตัวกับการ์ดสามใบ และสี่ฟังก์ชันที่แปลงมันเป็น
คำตอบ `weight_bytes` คือ weight ที่ความกว้างหนึ่ง `kv_bytes_per_token` คือ cache จากบท
พื้นฐานที่ 6 ต่อ token ของ context `concurrent_requests` คือจำนวนบทสนทนาที่พอดีข้าง
weight `decode_tokens_per_second` คือเพดานความเร็วในการสร้างสำหรับหนึ่งคำขอ จาก
bandwidth อย่างเดียว

```python
def decode_tokens_per_second(model, width, card):
    """The ceiling on generation speed for one request, from bandwidth alone."""
    return CARDS[card]["bandwidth"] / weight_bytes(model, width)
```

`launch.py` เอาเลขคณิตไปใช้กับ model และการ์ดที่คุณระบุ แล้วพิมพ์คำสั่ง vLLM ที่จะให้บริการ
มันเป็น endpoint รูป OpenAI แบบเดียวกับที่ทั้งคอร์สเรียก เพื่อให้ตัวแปรสภาพแวดล้อมตัวเดียว
ชี้คอร์สไปที่ model ของคุณเอง มันรันได้ทุกที่และไม่เริ่มอะไรเลย

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python serving.py
```

```text
weights alone, in gigabytes
model    fp16    int8    int4
0.5B      0.9     0.5     0.2
7B       14.2     7.1     3.5
72B     135.4    67.7    33.9

the 7B model at fp16 on each card
card        fits   8k conversations at once   tokens per second, one request
RTX 4090    True                         22                             66
A100 80GB   True                        150                            134
H100 80GB   True                        150                            220

the same model on the same card, narrower
  fp16    22 conversations      66 tokens per second
  int8    38 conversations     133 tokens per second
  int4    46 conversations     265 tokens per second

the 7B model's cache costs 56 KB per token of context, per conversation
```

```bash
python check.py
```

```text
OK 7B weights are fourteen gigabytes at sixteen bits and a quarter of that at four bits
OK a 72B model does not fit one 80 GB card at sixteen bits and does at four
OK the cache costs 56 KB per token of context for the 7B model, from its shape alone
OK fewer conversations fit as they get longer, and none at all if the weights do not fit
OK decode speed is bandwidth over bytes, so a quarter of the bytes is four times the tokens
```

```bash
python launch.py --model 7B --card "RTX 4090" --width int4 --context 8192
```

```text
7B at int4 is 3.5 GB of weights
beside the weights, about 46 conversations of 8192 tokens fit
one request decodes at most 265 tokens per second, bandwidth bound

vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --max-model-len 8192 --port 8000 --quantization awq

then, on the machine running the course
  export AGENTPATH_BASE_URL=http://localhost:8000/v1
  export AGENTPATH_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
```

## สิ่งที่ควรสังเกต

หกสิบหก token ต่อวินาที ตัวเลขนั้นมาจากการเอา bandwidth ของการ์ดหารด้วยขนาดของ weight
และไม่มีอย่างอื่น และมันใกล้กับสิ่งที่การ์ดทำได้จริง เพราะการสร้างหนึ่ง token คือการอ่านทุก
weight หนึ่งรอบ และเลขคณิตของชิปยังห่างจากขีดจำกัดมาก ข้อเท็จจริงข้อเดียวนี้อธิบายสาม
อย่างที่คนจ่ายเงิน การ quantize เป็นสี่บิตยกเพดานของหนึ่งคำขอขึ้นสี่เท่า การให้บริการหลาย
คำขอพร้อมกันเกือบฟรี เพราะ weight ถูกอ่านหนึ่งรอบต่อก้าวอยู่ดี ซึ่งเป็นเหตุผลที่ผู้ให้บริการทำ
batch ส่วนจำนวนที่รับได้คืออีกตัวเลข คือหน่วยความจำ และนั่นคือเหตุผลที่แถว int4 ไปถึงสี่สิบหก
และ token ขาออกแพงกว่าขาเข้า เพราะขาเข้า
อ่านรอบเดียว ส่วนขาออกคือ loop นี้ ทีละ token

cache คืออีกตัวเลข ห้าสิบหกกิโลไบต์ต่อ token ฟังดูไม่มากจนกระทั่งคูณด้วยแปดพัน token และ
ยี่สิบสองบทสนทนา ตอนนั้นมันคือการ์ดเกือบทั้งใบ นั่นคือเหตุผลที่คอลัมน์พร้อมกันลดลงเมื่อ
บทสนทนายาวขึ้น เหตุผลที่ผู้ให้บริการคิดเงินกับ context ยาว และเหตุผลที่บทพื้นฐานที่ 6 สร้าง
cache ด้วยมือ

`launch.py` จบด้วยตัวแปรสภาพแวดล้อม ทั้งคอร์สถูกเขียนกับรูปร่างของ endpoint ไม่ใช่ผู้ให้
บริการ ซึ่งคือข้อโต้แย้งของบทเรียนที่ 06 และตรงนี้คือที่ที่มันคุ้ม ชี้ `AGENTPATH_BASE_URL`
ไปที่ model ที่ให้บริการอยู่ แล้วทุกบทเรียนตั้งแต่ 01 เป็นต้นไปรันกับ model ที่คุณฝึกเองในสี่
บทที่ผ่านมา
