"""A tokenizer built from nothing, so the word token stops being magic.

The algorithm every current model uses is byte pair encoding. Start with
bytes. Find the pair of adjacent units that occurs most often. Give that
pair a new number and replace every occurrence of it. Repeat. That is the
whole thing. GPT, Llama and Claude differ from this file in scale and in
details that do not change what it is.
"""
from collections import Counter

# Two small corpora, because the point of the chapter is what a tokenizer
# learns depends entirely on what it was shown. Train on one, encode the
# other, and watch the price.
ENGLISH = """
The agent reads the file, decides what to do, and does it. Then it reads
the result and decides again. The loop ends when the model stops asking
for tools. Every request carries the whole conversation, so the cost of a
long conversation grows with its length twice over. The agent reads, the
agent decides, the agent acts, and then the agent reads the result.
"""

THAI = """
agent อ่านไฟล์ ตัดสินใจว่าจะทำอะไร แล้วทำ จากนั้นอ่านผลลัพธ์แล้วตัดสินใจอีกครั้ง
loop จบเมื่อ model เลิกขอ tool ทุก request แบกบทสนทนาทั้งหมดไปด้วย
ต้นทุนของบทสนทนายาวจึงโตตามความยาวสองเท่าตัว agent อ่าน agent ตัดสินใจ
agent ทำ แล้ว agent อ่านผลลัพธ์อีกครั้ง
"""


def pair_counts(ids):
    """How often each adjacent pair occurs in a list of ids."""
    return Counter(zip(ids, ids[1:], strict=False))


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


def train(text, vocabulary_size):
    """Learn merges from text until the vocabulary is the size asked for.

    The first 256 ids are the bytes themselves, so every possible input
    already has a representation before a single merge is learned. Each
    merge adds one id. A vocabulary of 300 means at most 44 merges.
    """
    ids = list(text.encode("utf-8"))
    merges = {}
    for new_id in range(256, vocabulary_size):
        counts = pair_counts(ids)
        if not counts:
            break
        pair = max(counts, key=counts.get)
        if counts[pair] < 2:
            break
        ids = merge(ids, pair, new_id)
        merges[pair] = new_id
    return merges


def encode(text, merges):
    """Text to ids, applying the merges in the order they were learned."""
    ids = list(text.encode("utf-8"))
    for pair, new_id in merges.items():
        ids = merge(ids, pair, new_id)
    return ids


def vocabulary(merges):
    """Every id and the bytes it stands for, the 256 raw bytes included."""
    table = {i: bytes([i]) for i in range(256)}
    for (left, right), new_id in merges.items():
        table[new_id] = table[left] + table[right]
    return table


def decode(ids, merges):
    """Ids back to text. A merged id unfolds to the bytes it stands for."""
    table = vocabulary(merges)
    return b"".join(table[i] for i in ids).decode("utf-8", errors="replace")


def pieces(ids, merges):
    """Each id as readable text, or as its bytes when it is not whole text.

    A token is a run of bytes, not a run of characters, and nothing stops a
    merge from ending in the middle of a three byte Thai character. Such a
    token cannot be shown as text on its own, so it is shown as bytes, the
    way tokenizer viewers do.
    """
    table = vocabulary(merges)
    shown = []
    for i in ids:
        try:
            shown.append(table[i].decode("utf-8"))
        except UnicodeDecodeError:
            shown.append("<" + " ".join(f"{b:02x}" for b in table[i]) + ">")
    return shown


def report(sentence, merges):
    """Bytes in, tokens out, and the tokens themselves."""
    ids = encode(sentence, merges)
    return {
        "bytes": len(sentence.encode("utf-8")),
        "tokens": len(ids),
        "pieces": pieces(ids, merges),
    }


if __name__ == "__main__":
    english_only = train(ENGLISH, 300)
    both = train(ENGLISH + THAI, 300)
    for name, merges in [("trained on English only", english_only), ("trained on both", both)]:
        print(f"== {name}, {len(merges)} merges ==")
        for sentence in ["the agent reads the file", "agent อ่านไฟล์"]:
            result = report(sentence, merges)
            print(f"  {sentence!r}  {result['bytes']} bytes  {result['tokens']} tokens")
            print(f"    {result['pieces']}")
        print()
