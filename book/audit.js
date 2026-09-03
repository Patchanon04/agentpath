// Compare the stamped blocks that reached a laid out page against the ones
// that went in. A block that is clipped rather than carried over shows up as
// missing here, which nothing else in the build catches.

const path = require("path");
const puppeteer = require("puppeteer-core");

const HERE = path.join(__dirname, "build");
const CHROME =
  process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "shell",
    args: ["--disable-gpu"],
  });
  const page = await browser.newPage();
  await page.goto("file://" + path.join(HERE, "book.html").replace(/\\/g, "/"), {
    waitUntil: "networkidle0",
    timeout: 300000,
  });
  await page.waitForFunction("window.__ready === true", { timeout: 900000, polling: 1000 });

  const out = await page.evaluate(() => {
    const onPage = new Set();
    document.querySelectorAll(".pagedjs_page [data-b]").forEach((el) => {
      const box = el.closest(".pagedjs_page_content");
      if (!box) return;
      const rect = el.getBoundingClientRect();
      const limit = box.getBoundingClientRect();
      // Count a block only when it sits inside the box completely. A block that
      if (rect.bottom <= limit.bottom + 4 && rect.top >= limit.top - 4) onPage.add(el.dataset.b);
    });
    return { pages: document.querySelectorAll(".pagedjs_page").length, shown: [...onPage] };
  });

  const fs = require("fs");
  const html = fs.readFileSync(path.join(HERE, "book.html"), "utf8");
  const all = new Set([...html.matchAll(/data-b="([^"]+)"/g)].map((m) => m[1]));
  const shown = new Set(out.shown);
  const missing = [...all].filter((b) => !shown.has(b));

  const byChapter = {};
  for (const b of missing) {
    const chapter = b.split(":")[0];
    byChapter[chapter] = (byChapter[chapter] || 0) + 1;
  }
  console.log(`pages ${out.pages} | blocks in ${all.size} | blocks on a page ${shown.size} | missing ${missing.length}`);
  for (const [chapter, count] of Object.entries(byChapter)) console.log(`  ${chapter.padEnd(30)} ${count} missing`);
  if (!missing.length) console.log("  every block reached a page");
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
