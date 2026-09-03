"""Build the Thai book in book/ as one print ready HTML, then a PDF.

The markdown here is a small, regular subset, so this converts it directly
rather than pulling in a dependency. Headings one to three, fenced code with a
language, pipe tables, bullet and numbered lists, links, bold and inline code.

Line breaks inside a paragraph are the one hard part. Thai has no spaces
between words, so a wrapped line can break in the middle of a word. Joining
those with a space, which is what CommonMark says, puts a visible gap inside
the word. Joining Thai to Thai with nothing keeps the word whole and lets the
browser rebreak the line with its own Thai dictionary. The cost is that a
space used as a phrase separator is lost when the wrap landed on it, and the
two cases cannot be told apart from the text alone.
"""

import html
import re
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
OUT = SRC / "build"
REPO = "https://github.com/Patchanon04/agentpath"
THAI = "\u0e00-\u0e7f"
FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Sarabun:ital,wght@0,400;0,600;0,700;1,400"
    "&family=JetBrains+Mono:wght@400;700&display=block"
)

PARTS = [
    ("ภาค 0", "พื้นฐานจากศูนย์", "เริ่มจากตัวอักษร จบที่ chatbot โดยไม่ต้องมี model", [
        "00a-text-is-numbers", "00b-tokens", "00c-next-token", "00d-learning",
        "00e-meaning-as-direction", "00f-attention", "00g-from-model-to-chatbot"]),
    ("ภาค 1", "ทฤษฎี", "เจ็ดบทที่อยู่เบื้องหลังบทเรียนทั้งหมด", [
        "01-what-a-model-is", "02-the-loop", "03-tools", "04-context",
        "05-trust", "06-failure", "07-measurement"]),
    ("ภาค 2", "คิดโปรเจกต์จริง", "เอาไอเดียมาคิดว่าจะสร้างอะไร", [
        "08-how-to-think", "09-case-line-health", "10-more-cases", "11-what-goes-wrong"]),
    ("ภาค 3", "ลงมือทำ", "อ่านโค้ดฉบับสมบูรณ์ทีละชิ้น", [
        "12-providers", "13-tools-that-touch-the-world", "14-mcp",
        "15-subagents", "16-shipping"]),
    ("ภาค 4", "ฝึก model ของตัวเอง", "fine-tune และให้บริการ model ของคุณเอง", [
        "17-dataset", "18-lora", "19-quantization", "20-preference", "21-serving"]),
]


def slug(text):
    keep = re.sub(r"[^\w\u0e00-\u0e7f]+", "-", text.strip().lower())
    return keep.strip("-") or "x"


def link_target(href):
    """Rewrite a link from the markdown to something a standalone book can use."""
    if href.startswith(("http://", "https://", "#")):
        return href
    if href.endswith(".md"):
        return "#ch-" + href[:-3]
    path = href[3:] if href.startswith("../") else href
    kind = "tree" if path.endswith("/") else "blob"
    return f"{REPO}/{kind}/main/{path.rstrip('/')}"


def inline(text):
    """Inline markup, with code spans held aside so nothing rewrites them."""
    spans = []

    def stash(match):
        spans.append(html.escape(match.group(1)))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(link_target(m.group(2)), quote=True)}">{m.group(1)}</a>',
        text,
    )
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", text)


def join_wrapped(lines):
    """Undo the hard wrap. See the module docstring for the Thai rule."""
    out = lines[0]
    for line in lines[1:]:
        thai_thai = re.search(f"[{THAI}]$", out) and re.match(f"[{THAI}]", line)
        out += line if thai_thai else " " + line
    return out


def convert(text, chapter_id):
    """Markdown to HTML for the subset this book uses.

    Every top level block carries a data-b stamp. Pagination can clip a block
    instead of moving it to the next page, and it does so silently, so
    comparing the stamps that reached a page against the stamps that went in
    is the only way to know the whole book is there.
    """
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            lang = line[3:].strip()
            body, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(body)
            if lang == "mermaid":
                drawing = html.escape(code)
                out.append(
                    f'<figure class="diagram"><pre class="mermaid">{drawing}</pre></figure>'
                )
            else:
                cls = f' class="language-{lang}"' if lang else ""
                out.append(f"<pre><code{cls}>{html.escape(code)}</code></pre>")
            continue

        if match := re.match(r"(#{1,3}) (.+)", line):
            level, title = len(match.group(1)), match.group(2).strip()
            if level == 1:
                # The chapter number rides above the title as a kicker, the
                # way a book sets it, rather than running into the title.
                named = re.match(r"((?:บทพื้นฐานที่|บทที่) \d+)\s+(.+)", title)
                if named:
                    out.append(
                        f'<header class="opener" id="ch-{chapter_id}">'
                        f'<p class="chapter-number">{inline(named.group(1))}</p>'
                        f"<h1>{inline(named.group(2))}</h1></header>"
                    )
                else:
                    out.append(f'<h1 id="ch-{chapter_id}">{inline(title)}</h1>')
            else:
                out.append(f'<h{level} id="{chapter_id}-{slug(title)}">{inline(title)}</h{level}>')
            i += 1
            continue

        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            body = rows[2:] if len(rows) > 1 and set("".join(rows[1])) <= set("-: ") else rows[1:]
            head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            cells = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body
            )
            out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{cells}</tbody></table>")
            continue

        if re.match(r"([-*] |\d+\. )", line):
            tag = "ul" if line[0] in "-*" else "ol"
            items, current = [], []
            while i < len(lines):
                if match := re.match(r"(?:[-*] |\d+\. )(.*)", lines[i]):
                    if current:
                        items.append(current)
                    current = [match.group(1)]
                elif lines[i].startswith("  ") and current:
                    current.append(lines[i].strip())
                elif (
                    not lines[i].strip()
                    and current
                    and i + 1 < len(lines)
                    and re.match(r"(?:[-*] |\d+\. |  )", lines[i + 1])
                ):
                    pass
                else:
                    break
                i += 1
            if current:
                items.append(current)
            body = "".join(f"<li>{inline(join_wrapped(item))}</li>" for item in items)
            out.append(f"<{tag}>{body}</{tag}>")
            continue

        if not line.strip():
            i += 1
            continue

        para = []
        block = r"(```|#{1,3} |\||[-*] |\d+\. )"
        while i < len(lines) and lines[i].strip() and not re.match(block, lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(join_wrapped(para))}</p>")

    stamped = [b.replace(">", f' data-b="{chapter_id}:{n}">', 1) for n, b in enumerate(out)]
    return "\n".join(stamped)


def chapter_title(text):
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "?"


def build_html():
    parts_html, toc_rows = [], []
    for number, name, blurb, stems in PARTS:
        toc_rows.append(f'<li class="toc-part"><span>{number}</span> {name}</li>')
        chapters = []
        for stem in stems:
            source = (SRC / f"{stem}.md").read_text(encoding="utf-8")
            title = chapter_title(source)
            toc_rows.append(
                f'<li class="toc-chapter"><a href="#ch-{stem}" data-chapter="{stem}">'
                f'<span class="toc-title">{html.escape(title)}</span>'
                f'<span class="toc-dots"></span>'
                f'<span class="toc-page"></span></a></li>'
            )
            chapters.append(f'<section class="chapter">{convert(source, stem)}</section>')
        parts_html.append(
            f'<section class="part-title"><p class="part-number">{number}</p>'
            f'<h1 class="part-name">{html.escape(name)}</h1>'
            f'<p class="part-blurb">{html.escape(blurb)}</p></section>' + "".join(chapters)
        )

    css = (SRC / "book.css").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>agentpath</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<style>{css}</style>
<script>window.PagedConfig = {{auto: false}};</script>
<script src="https://cdn.jsdelivr.net/npm/pagedjs@0.4.3/dist/paged.polyfill.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
</head>
<body>

<section class="cover">
  <p class="cover-kicker">เรียนรู้ว่า AI agent ทำงานยังไงจริงๆ ด้วยการสร้างมันขึ้นมาเอง</p>
  <h1 class="cover-title">agentpath</h1>
  <p class="cover-sub">จากการเรียก LLM ครั้งเดียว ไปจนถึง harness ที่ใช้งานได้จริง</p>
  <p class="cover-foot">หนังสือประกอบหลักสูตร 24 บทเรียน</p>
</section>

<section class="colophon">
  <p>หนังสือเล่มนี้อธิบายทฤษฎีที่อยู่เบื้องหลังบทเรียนทั้ง 24 บท และวิธีคิดเวลาจะเอาไปทำโปรเจกต์จริง
  บทเรียนสอนให้คุณสร้าง เล่มนี้อธิบายว่าทำไมมันถึงเป็นแบบนั้น</p>
  <p>ศัพท์เทคนิคคงไว้เป็นภาษาอังกฤษ และใส่ความหมายไทยในวงเล็บครั้งแรกที่พบในแต่ละบท
  เหตุผลคือคุณต้องอ่านเอกสารภาษาอังกฤษต่อได้ การแปลศัพท์เป็นไทยทำให้ค้นหาต่อไม่เจอ</p>
  <p>โค้ดทุกบรรทัดในเล่มนี้อยู่ใน repository เดียวกับหนังสือ และรันได้จริง</p>
  <dl>
    <dt>ที่มา</dt><dd>{REPO}</dd>
    <dt>package</dt><dd>agentpath-kit บน PyPI</dd>
    <dt>สัญญาอนุญาต</dt><dd>MIT</dd>
  </dl>
</section>

<section class="toc">
  <h1>สารบัญ</h1>
  <ul>{"".join(toc_rows)}</ul>
</section>

{"".join(parts_html)}

<script>
(async function () {{
  // Wait for the real faces before anything measures a line. Paginating with
  // the fallback metrics and letting the webfont swap in afterwards is what
  // puts four chapter openers on one page.
  try {{ await document.fonts.ready; }} catch (e) {{ console.log("fonts skipped", e); }}
  try {{
    mermaid.initialize({{startOnLoad: false, theme: "base",
      themeVariables: {{
        fontFamily: "Sarabun, sans-serif", fontSize: "13px",
        primaryColor: "#f5f6f8", primaryBorderColor: "#1f3a5f",
        primaryTextColor: "#16181d", lineColor: "#5d6470",
        secondaryColor: "#eef1f5", tertiaryColor: "#ffffff"
      }}}});
    await mermaid.run({{querySelector: ".mermaid"}});
  }} catch (e) {{ console.log("mermaid skipped", e); }}
  try {{
    document.querySelectorAll("pre code").forEach(function (b) {{ hljs.highlightElement(b); }});
  }} catch (e) {{ console.log("highlight skipped", e); }}
  await window.PagedPolyfill.preview();

  // Fill the contents page numbers here rather than with target-counter.
  // Paged.js leaves the unpaginated source in the document, so every chapter
  // id exists twice and the counter resolves against the copy that never
  // landed on a page. Reading the laid out pages directly cannot go wrong.
  var sheets = Array.prototype.slice.call(document.querySelectorAll(".pagedjs_page"));
  function pageOf(id) {{
    var found = document.querySelectorAll('[id="' + id + '"]');
    for (var i = 0; i < found.length; i++) {{
      var sheet = found[i].closest(".pagedjs_page");
      if (sheet) {{
        return sheet.getAttribute("data-page-number") || String(sheets.indexOf(sheet) + 1);
      }}
    }}
    return "";
  }}
  document.querySelectorAll(".pagedjs_page .toc-chapter a").forEach(function (row) {{
    var slot = row.querySelector(".toc-page");
    if (slot) {{ slot.textContent = pageOf("ch-" + row.dataset.chapter); }}
  }});

  // A page that opens something carries no running head, which is what a
  // printed book does. Named pages would say this in CSS, but paged.js drops
  // whole chapters when consecutive blocks share one, so it is said here.
  sheets.forEach(function (sheet) {{
    var opens = sheet.querySelector("h1[id^='ch-'], .part-title, .toc, .colophon");
    var blank = sheet.classList.contains("pagedjs_blank_page");
    if (opens || blank) {{
      var head = sheet.querySelector(".pagedjs_margin-top");
      if (head) {{ head.style.visibility = "hidden"; }}
    }}
    if (blank) {{
      var foot = sheet.querySelector(".pagedjs_margin-bottom");
      if (foot) {{ foot.style.visibility = "hidden"; }}
    }}
  }});

  window.__ready = true;
}})();
</script>
</body>
</html>
"""


def main():
    OUT.mkdir(exist_ok=True)
    out_html = OUT / "book.html"
    out_html.write_text(build_html(), encoding="utf-8")
    print(f"wrote {out_html} ({out_html.stat().st_size // 1024} KB)")

    result = subprocess.run(["node", str(SRC / "render.js")], cwd=SRC, text=True, timeout=1800)
    pdf = OUT / "agentpath-book.pdf"
    if result.returncode or not pdf.exists():
        return 1
    print(f"wrote {pdf} ({pdf.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
