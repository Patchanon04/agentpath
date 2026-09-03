"""What the computer has when you type a word.

Every later chapter rests on this one. A model never sees letters. It sees
numbers, and the path from a letter to a number has steps worth watching
once with your own eyes, because they are where Thai starts costing more
than English long before a model is involved.
"""
import unicodedata


def code_points(text):
    """The number Unicode gives each character.

    Before anything is stored or sent, every character has an integer, and
    it is the same integer on every machine in the world. That agreement
    is the whole point of Unicode.
    """
    return [ord(character) for character in text]


def utf8_bytes(text):
    """The bytes that actually travel over the wire or sit on disk.

    UTF-8 spends one byte on the characters that fit the old ASCII table
    and more on everything else. Latin letters cost one. Thai characters
    cost three. That is not a judgement on the language, it is the order
    the table was filled in.
    """
    return list(text.encode("utf-8"))


def describe(text):
    """One row per character, with its name, its code point and its bytes."""
    rows = []
    for character in text:
        rows.append(
            {
                "char": character,
                "name": unicodedata.name(character, "UNKNOWN"),
                "code_point": ord(character),
                "bytes": list(character.encode("utf-8")),
            }
        )
    return rows


def cost(text):
    """Characters, bytes, and how many bytes each character cost on average."""
    characters = len(text)
    byte_count = len(text.encode("utf-8"))
    return {
        "characters": characters,
        "bytes": byte_count,
        "bytes_per_character": byte_count / characters if characters else 0.0,
    }


def combining_marks(text):
    """The characters that are not letters but marks stacked on a letter.

    Thai vowels above and below the line and the tone marks are separate
    characters that sit on the consonant before them. They take up bytes
    and, later, tokens, without taking up a column on the screen. A model
    that counts characters and a person who counts what they can see are
    counting different things.
    """
    return [c for c in text if unicodedata.category(c).startswith("M")]


if __name__ == "__main__":
    for sample in ["hello", "สวัสดี"]:
        print(f"{sample!r}")
        for row in describe(sample):
            print(f"  {row['char']!r:6} {row['code_point']:>6}  {row['bytes']}")
        print(f"  {cost(sample)}")
        print()
