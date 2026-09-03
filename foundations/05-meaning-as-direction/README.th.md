# บทพื้นฐานที่ 5 ความหมายเป็นทิศทาง

โฟลเดอร์นี้คือโค้ดที่อยู่เบื้องหลังบทพื้นฐานบทที่ห้าของหนังสือ ที่
[book/00e-meaning-as-direction.md](../../book/00e-meaning-as-direction.md)
ตัวบทอธิบายว่าทำไมคำถึงกลายเป็นชุดตัวเลข การที่สองคำอยู่ใกล้กันแปลว่าอะไร และเอกสาร
ทั้งฉบับกลายเป็น vector ที่ค้นหาได้ยังไง ไฟล์นี้คือฉบับสั้นสำหรับรันโค้ด

ไม่มี model ให้เรียก ไม่มี API key `vectors.py` กับ `skipgram.py` ใช้ numpy `tfidf.py`
ไม่ใช้

## มีอะไรอยู่ในนี้

`vectors.py` สร้าง embedding ของคำแบบเก่าแก่ที่สุดที่มี `cooccurrence` นับว่าคำแต่ละคำ
มีคำไหนปรากฏใกล้ๆ บ้าง และแถวของจำนวนนับนั้นคือ vector ของคำ `cosine` เทียบสอง
vector ด้วยทิศทางอย่างเดียว `euclidean` เทียบด้วยระยะทางเส้นตรง และ `nearest`
จัดอันดับทุกคำอื่นด้วย cosine

```python
def cosine(a, b):
    """How much two vectors point the same way, ignoring how long they are."""
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
```

`tfidf.py` ทำอย่างเดียวกันกับเอกสารทั้งฉบับ แบบที่ search engine ทำก่อนจะมี embedding
และส่วนใหญ่ยังทำอยู่ `bag_of_words` นับคำในเอกสารแล้วทิ้งลำดับ `feature_vocabulary`
กับ `count_vector` แปลงมันเป็นแถวบน vocabulary ที่ตายตัว และ `sparsity` บอกว่าแถวนั้น
เป็นศูนย์แค่ไหน `term_frequency` `inverse_document_frequency` และ `tfidf` ถ่วงน้ำหนัก
คำด้วยว่ามันเป็นสัดส่วนเท่าไหร่ของเอกสาร และหายากแค่ไหนในที่อื่น ส่วน `search` จัดอันดับ
เอกสารสำหรับคำหนึ่งคำ

```python
def tfidf(term, text, documents):
    """Frequent in this document, rare across the rest, is what scores high."""
    return term_frequency(term, text) * inverse_document_frequency(term, documents)
```

`skipgram.py` คือก้าวจากการนับไปสู่การเรียนรู้ `training_pairs` แปลงข้อความเป็นทุกคำ
จับคู่กับทุกเพื่อนบ้าน `train` เรียนรู้ vector แปดตัวเลขต่อคำด้วยการทายเพื่อนบ้านพวก
นั้น ซึ่งคือวิธีของบทที่ 4 บวกตารางที่สอง และ `nearest` จัดอันดับด้วย vector ที่เรียนรู้
มา นี่คือแนวคิด word2vec ปี 2013 บน corpus ที่เล็กพอจะดูได้

```python
def train(text, size=8, steps=400, learning_rate=0.5, seed=0):
    """Learn a vector per word by guessing neighbours. Chapter 4 again, with two grids."""
    words, index = vocabulary(text)
    centres, contexts = training_pairs(text, index)
    rng = np.random.default_rng(seed)
    embedding = rng.normal(0, 0.1, size=(len(words), size))
    readout = rng.normal(0, 0.1, size=(size, len(words)))
    history = []
    for _ in range(steps):
        hidden = embedding[centres]
        guess = softmax(hidden @ readout)
        history.append(-np.log(guess[np.arange(len(contexts)), contexts]).mean())
        guess[np.arange(len(contexts)), contexts] -= 1
        guess /= len(contexts)
        readout_change = hidden.T @ guess
        hidden_change = guess @ readout.T
        readout -= learning_rate * readout_change
        np.add.at(embedding, centres, -learning_rate * hidden_change)
    return embedding, index, history
```

`check.py` ยึดข้ออ้างที่บทพูดไว้เกี่ยวกับทั้งสามไฟล์

## รันมัน

```bash
python vectors.py
```

```text
nearest to 'cat'
  dog      0.979
  bone     0.928
  fish     0.928
nearest to 'agent'
  model    0.998
  file     0.952
  result   0.952

cat appears 5 times, dog 3
cosine(cat, dog) 0.979   euclidean(cat, dog) 5.74
cosine(cat, file) 0.854   euclidean(cat, file) 7.28
```

```bash
python tfidf.py
```

```text
feature vocabulary ['กบ', 'กระโดด', 'นอน', 'วิ่ง', 'สุนัข', 'หลับ', 'เล่น', 'แมว']
  one    [0, 0, 0, 1, 1, 0, 1, 1]  sparsity 0.50
  two    [0, 0, 1, 0, 0, 1, 0, 1]  sparsity 0.62
  three  [1, 1, 0, 1, 1, 0, 1, 0]  sparsity 0.38

searching for แมว
  two    tf 0.3333  score 0.1352
  one    tf 0.2500  score 0.1014
  three  tf 0.0000  score 0.0000
idf of แมว 0.4055, in two documents of three
idf of กบ 1.0986, in one document of three
```

```bash
python skipgram.py
```

```text
25 words, each a vector of 8 numbers, not 25
loss at the start 3.217, after training 2.173

nearest to 'cat' by the learned vectors
  dog      0.945
  sofa     0.825
  bone     0.789
nearest to 'agent' by the learned vectors
  tool     0.978
  model    0.933
  answer   0.913

cosine(cat, dog) 0.945   cosine(cat, file) 0.545
```

```bash
python check.py
```

```text
OK words used the same way point the same way, and nobody defined either
OK the two groups in the text are two groups in the space
OK cosine is one for the same direction
OK cosine ignores how common a word is and euclidean does not
OK cat is more common than dog and is still its nearest neighbour
OK a bag of words cannot tell who ate whom
OK the numbers match the worked example, and the shortest document wins
OK a word in every document scores zero, because it points at nothing
OK the learned vectors are eight numbers wide and the counted ones are twenty five
OK guessing neighbours finds the groups that counting found, in a third of the numbers
OK the word next to everything pulls the learned vectors together less than the counted
```

## สิ่งที่ควรสังเกต

ไม่มีใครนิยาม `cat` คำที่ใกล้มันที่สุดคือ `dog` เพราะทั้งสองคบเพื่อนกลุ่มเดียวกัน และ
นั่นคือแนวคิดทั้งหมด ความหมายสำหรับเครื่องคือเพื่อนที่คำนั้นคบ เขียนเป็นทิศทาง

`cat` กับ `file` ยังได้ 0.854 ทั้งที่ไม่มีอะไรร่วมกัน เพราะทั้งคู่อยู่ข้าง `the` และ `the`
อยู่ข้างทุกอย่าง `tfidf.py` คือวิธีแก้ คำที่ปรากฏในทุกเอกสารได้ inverse document
frequency เป็นศูนย์และหลุดออกจากทุกคะแนน นั่นคือแนวคิดที่บทเรียนที่ 16 ใช้ในชื่อ rarity
ตอน `search_notes` จัดอันดับย่อหน้า

count vector ส่วนใหญ่เป็นศูนย์ และใน vocabulary จริงที่มีคำหลายหมื่นคำ มันเกือบเป็นศูนย์
ทั้งหมด นั่นคือความหมายของคำว่า sparse และการเก็บเฉพาะตำแหน่งที่ไม่ใช่ศูนย์คือสิ่งที่ทำให้
การค้นเอกสารล้านฉบับด้วยคำมีราคาที่จ่ายไหว

`skipgram.py` ได้กลุ่มเดียวกันจากแปดตัวเลขต่อคำแทนที่จะเป็นยี่สิบห้า และมันไม่เคยนับ
เพื่อนบ้านเลย มันทาย ถูกบอกว่าผิดแค่ไหน แล้วขยับ vector ซึ่งคือบทที่ 4 โดยมี embedding
เป็นสิ่งที่ถูกเรียนรู้ มีสองอย่างให้ดูใน output vector เป็นแบบ dense ทุกตัวเลขถูกใช้ ซึ่ง
คือสิ่งที่ทำให้ embedding model จริงบรรยายคำได้ในไม่กี่ร้อยตัวเลขทั้งที่ vocabulary มีเป็น
แสน และ `cat` กับ `file` ตกจาก 0.854 เหลือ 0.545 เพราะ vector ที่ต้องทายเพื่อนบ้านของ
ตัวเอง ใช้ตัวเองไปกับ `the` ซึ่งทายอะไรไม่ได้ ได้ไม่มาก embedding model ที่อยู่หลัง
บทเรียนที่ 16 คือแนวคิดนี้ ฝึกบนเว็บ โดยใช้ทั้งประโยคแทนคำ
