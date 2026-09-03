# ภาคฝึกที่ 3 quantization พร้อมวัดความผิดที่จ่าย

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทที่สามของภาค 4 ของหนังสือ ที่
[book/19-quantization.md](../../book/19-quantization.md) ตัวบทเก็บตารางของบทที่ 4 ด้วย
แปดบิตแล้วสี่บิต และวัดว่าการปัดเศษมีราคาเท่าไหร่ เพื่อให้การแลกระหว่างหน่วยความจำกับ
คุณภาพเป็นตัวเลข ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไฟล์ numpy ไม่ต้องใช้ GPU `load_4bit.py` ต้องใช้ และต้องเป็น Linux

## มีอะไรอยู่ในนี้

`grid.py` ไม่เปลี่ยนจากโฟลเดอร์ก่อน

`quantize.py` ปัดเศษ `quantize` แปลงแต่ละแถวเป็นจำนวนเต็มความกว้างที่กำหนดโดยมีตัวคูณ
หนึ่งตัวต่อแถว `dequantize` แปลงกลับ และ `bytes_for` บอกว่าตารางใช้ที่เท่าไหร่
`quantize_grouped` กับ `dequantize_grouped` ทำแบบสี่บิตที่มีตัวคูณต่อกลุ่มเล็กๆ ซึ่งคือ
สิ่งที่ตระกูล GGUF และ GPTQ ทำ

```python
def quantize(grid, bits=8):
    """Round each row to integers of the given width, with one scale per row."""
    levels = 2 ** (bits - 1) - 1
    scale = np.abs(grid).max(axis=1, keepdims=True) / levels
    scale[scale == 0] = 1.0
    integers = np.round(grid / scale).astype(np.int64)
    return integers, scale
```

`load_4bit.py` โหลด model แบบเปิดโดยทุกตารางอยู่ที่สี่บิตแล้วรายงานหน่วยความจำ และด้วย
`--train` มันเพิ่ม LoRA adapter ซ้อนข้างบน ซึ่งคือ QLoRA ไม่ได้รันใน CI

`check.py` ยึดข้ออ้างที่บทพูดไว้

## รันมัน

```bash
python quantize.py
```

```text
a grid of 1156 numbers, loss 0.7868 at 64 bits each

bits   bytes   loss     what changed
  64    9248   0.7868   nothing, this is the model
   8    1292   0.7868   one scale per row
   4     714   0.7930   one scale per row
   4     850   0.7898   one scale per group of 17

the largest single error at 4 bits with a scale per row is 0.460
the largest number in the grid is 8.938
```

```bash
python check.py
```

```text
OK at eight bits every number is an integer from minus 127 to 127, one scale per row
OK eight bits costs almost nothing, the loss moves in the third decimal place
OK four bits costs more, and the cost is a number you can read next to the bytes saved
OK a scale per small group keeps more detail at four bits than a scale per row
OK the largest single error is a small fraction of the largest number in the grid
```

บน GPU

```bash
pip install "agentpath-kit[training]" bitsandbytes
python load_4bit.py --model Qwen/Qwen2.5-7B-Instruct
python load_4bit.py --model Qwen/Qwen2.5-7B-Instruct --train clean.jsonl
```

## สิ่งที่ควรสังเกต

แปดบิตฟรี byte ลดลงเจ็ดเท่าและ loss ไม่ขยับในทศนิยมตำแหน่งที่สี่ นั่นคือเหตุผลที่ทุกการ
ให้บริการเริ่มที่ตรงนั้น และเหตุผลที่ int8 เป็นค่าเริ่มต้นในเลขคณิตของสองบทถัดไป

สี่บิตไม่ฟรี และตารางแสดงการแลกทั้งสองทาง ตัวคูณหนึ่งตัวต่อแถวลด byte ลงอีกครึ่งและมี
ราคา loss หกในพัน ตัวคูณต่อกลุ่มสิบเจ็ดมีราคาสามในพัน แลกกับ byte ของตัวคูณอีกร้อยสามสิบหก
บนตารางนี้ทั้งคู่ใช้ได้ บน model จริงสี่บิตที่มีตัวคูณต่อแถวมักใช้ไม่ได้ และรูปแบบแบบกลุ่ม
มีอยู่เพราะตารางนี้เป๊ะๆ

สองบรรทัดสุดท้ายคือกลไก ตัวเลขที่ใหญ่ที่สุดในแถวกำหนดตัวคูณ และตัวเลขอื่นทุกตัวในแถวถูก
ปัดไปที่ตารางซึ่งมีช่วงห่างเท่ากับตัวเลขนั้นหารเจ็ด แถวที่มี weight ใหญ่หนึ่งตัวและเล็กหลาย
ตัวจะเสียตัวเล็กๆ ไป และการแบ่งกลุ่มคือทางแก้
