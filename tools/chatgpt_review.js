#!/usr/bin/env node
/* ChatGPT review через Playwright CDP: настоящий Chrome запускается нами (не automation-флаг),
   playwright подключается к нему по remote-debugging-port — ChatGPT не видит автоматизацию.
   Использование:
     node tools/chatgpt_review.js ask "промпт"          # отправить и получить ответ
     node tools/chatgpt_review.js ask-file prompt.txt  # из файла
     node tools/chatgpt_review.js status
   Переменные: CHATGPT_PROFILE (по умолчанию ~/.cache/bukifon-chatgpt), PORT (9333). */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");
const PW = process.env.PW || path.join(os.homedir(), ".openclaw/workspace/node_modules/playwright");
const { chromium } = require(PW);

const PORT = Number(process.env.CHATGPT_DEBUG_PORT || 9333);
const PROFILE = process.env.CHATGPT_PROFILE || path.join(os.homedir(), ".cache", "bukifon-chatgpt");
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
async function getJson(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      let d = ""; res.on("data", c => d += c); res.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve(null); } });
    });
    req.on("error", () => resolve(null)); req.setTimeout(1500, () => { req.destroy(); resolve(null); });
  });
}
async function ensureChrome() {
  let v = await getJson(`http://127.0.0.1:${PORT}/json/version`);
  if (v && v.webSocketDebuggerUrl) return v;
  fs.mkdirSync(PROFILE, { recursive: true });
  const child = spawn(CHROME, [
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    "--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process", "--start-maximized", "about:blank",
  ], { detached: true, stdio: "ignore" });
  child.unref();
  for (let i = 0; i < 40; i++) { await sleep(500); v = await getJson(`http://127.0.0.1:${PORT}/json/version`); if (v) return v; }
  throw new Error("Chrome не запустился на порту " + PORT);
}
async function connect() {
  await ensureChrome();
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
  const ctx = browser.contexts()[0];
  if (!ctx) throw new Error("нет контекста");
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    if (!window.chrome) window.chrome = { runtime: {} };
  });
  let page = ctx.pages().find(p => p.url().includes("chatgpt.com")) || ctx.pages()[0];
  if (!page) page = await ctx.newPage();
  return { browser, ctx, page };
}
async function openChatGpt(page) {
  if (!page.url().includes("chatgpt.com")) {
    await page.goto("https://chatgpt.com/", { waitUntil: "domcontentloaded", timeout: 60000 });
  }
  await page.waitForTimeout(2500);
  return page;
}
function composer(page) {
  return page.locator('div[contenteditable="true"]#prompt-textarea, div.ProseMirror[contenteditable="true"], textarea[name="prompt-textarea"]').first();
}
async function ask(prompt, opts = {}) {
  const { browser, page } = await connect();
  await openChatGpt(page);
  const c = composer(page);
  await c.waitFor({ state: "visible", timeout: 30000 });
  await c.click();
  await page.keyboard.press("Control+A").catch(() => {});
  await page.keyboard.press("Backspace").catch(() => {});
  await page.keyboard.type(prompt, { delay: 2 });
  await page.waitForTimeout(300);
  const send = page.locator('button[data-testid="send-button"], button[aria-label*="Send" i], button[aria-label*="Отправ" i]').first();
  if (await send.isVisible().catch(() => false)) await send.click(); else await page.keyboard.press("Enter");

  const start = Date.now();
  let last = "";
  while (Date.now() - start < (opts.timeoutMs || 180000)) {
    await sleep(2000);
    const texts = await page.evaluate(() => Array.from(document.querySelectorAll('[data-message-author-role="assistant"]')).map(e => e.innerText.trim()).filter(Boolean));
    const cur = texts[texts.length - 1] || "";
    const busy = await page.locator('button[aria-label*="Stop" i], button:has-text("Stop")').count().catch(() => 0);
    if (cur && cur !== last) { last = cur; }
    else if (cur && cur === last && !busy && cur.length > 20) break;
  }
  await browser.close();
  if (!last) throw new Error("ответ не получен (возможно, скрыта панель ввода/логин)");
  return last;
}
(async () => {
  const cmd = process.argv[2];
  try {
    if (cmd === "status") {
      const { page, browser } = await connect();
      await openChatGpt(page);
      const has = await composer(page).isVisible().catch(() => false);
      console.log(JSON.stringify({ url: page.url(), title: await page.title(), composerVisible: has, profile: PROFILE }, null, 2));
      await browser.close();
    } else if (cmd === "ask" || cmd === "ask-file") {
      const prompt = cmd === "ask" ? process.argv.slice(3).join(" ") : fs.readFileSync(process.argv[3], "utf8");
      if (!prompt) throw new Error("пустой промпт");
      const answer = await ask(prompt);
      console.log(answer);
    } else {
      console.log("usage: node tools/chatgpt_review.js status|ask \"prompt\"|ask-file file");
    }
  } catch (e) { console.error("ERROR:", e.message); process.exit(1); }
})();
