"""Prove the numbers in the chapter are the numbers on this machine."""
import sys

from text import code_points, combining_marks, cost, utf8_bytes


def fail(message):
    print(f"FAIL {message}")
    sys.exit(1)


hello = cost("hello")
thai = cost("สวัสดี")
if hello["bytes"] != 5:
    fail(f"hello should be five bytes, got {hello['bytes']}")
if thai["characters"] != 6 or thai["bytes"] != 18:
    fail(f"สวัสดี should be six characters and eighteen bytes, got {thai}")
print("OK hello costs one byte per character and สวัสดี costs three")

if code_points("ก")[0] != 0x0E01:
    fail("ก is not at U+0E01, which would mean this is not Unicode")
if utf8_bytes("ก") != [0xE0, 0xB8, 0x81]:
    fail("ก did not encode to the three UTF-8 bytes the chapter shows")
print("OK the code point and the bytes match the chapter")

marks = combining_marks("สวัสดี")
if len(marks) != 2:
    fail(f"expected two combining marks in สวัสดี, found {marks}")
print("OK two of the six characters are marks stacked on a consonant")

# The encoding is spelled out on purpose. It is the default, and the linter
# knows that, but the name of the encoding is the subject of the chapter.
if "สวัสดี".encode("utf-8").decode("utf-8") != "สวัสดี":  # noqa: UP012
    fail("encode then decode did not round trip")
print("OK bytes turn back into the same text")
