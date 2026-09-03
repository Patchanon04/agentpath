// Print book.html to PDF. Chrome's own --print-to-pdf fires as soon as the
// page loads, which is long before paged.js has finished laying the book out,
// so this drives the same Chrome and waits for the page to say it is done.

const path = require("path");
const puppeteer = require("puppeteer-core");

const HERE = path.join(__dirname, "build");
const CHROME =
  process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "shell",
    args: ["--disable-gpu", "--font-render-hinting=none"],
  });
  const page = await browser.newPage();
  page.on("console", (m) => {
    const text = m.text();
    if (!text.startsWith("Loaded")) console.log("  page:", text.slice(0, 160));
  });
  page.on("pageerror", (e) => console.log("  error:", String(e).slice(0, 200)));

  const started = Date.now();
  await page.goto("file://" + path.join(HERE, "book.html").replace(/\\/g, "/"), {
    waitUntil: "networkidle0",
    timeout: 300000,
  });
  console.log(`  loaded in ${((Date.now() - started) / 1000).toFixed(1)}s, paginating`);

  await page.waitForFunction("window.__ready === true", { timeout: 900000, polling: 1000 });
  const pages = await page.$$eval(".pagedjs_page", (n) => n.length);
  console.log(`  paginated ${pages} pages in ${((Date.now() - started) / 1000).toFixed(1)}s`);

  await page.pdf({
    path: path.join(HERE, "agentpath-book.pdf"),
    preferCSSPageSize: true,
    printBackground: true,
    timeout: 600000,
  });
  await browser.close();
  console.log("  wrote agentpath-book.pdf");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
