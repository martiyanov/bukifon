#!/usr/bin/env node
/* Smoke-тест микрофона в демо: fake-устройство Chrome, MIC → REC MIC → PAD. */
"use strict";
const path = require("path"), os = require("os"), { spawn } = require("child_process");
const { chromium } = require(path.join(os.homedir(), ".openclaw/workspace/node_modules/playwright"));
const PORT = 8791;
const server = spawn("python3", ["-m", "http.server", String(PORT), "-d", path.join(__dirname, "..", "docs")], { stdio: "ignore" });
(async () => {
  await new Promise(r => setTimeout(r, 800));
  const b = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
    args: ["--no-sandbox", "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream", "--autoplay-policy=no-user-gesture-required"] });
  const p = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = []; p.on("pageerror", e => errs.push(e.message));
  await p.goto(`http://127.0.0.1:${PORT}/demo/index.html`, { waitUntil: "load" });
  await p.waitForTimeout(600);
  await p.locator("#btnMic").click(); await p.waitForTimeout(900);
  const micOn = await p.evaluate(() => state.mic.on);
  await p.locator("#btnRecMic").click(); await p.waitForTimeout(2200); await p.locator("#btnRecMic").click(); await p.waitForTimeout(600);
  const pads = await p.evaluate(() => state.pads.map(x => ({ name: x.name, dur: x.buffer ? +x.buffer.duration.toFixed(2) : 0 })));
  await b.close(); server.kill();
  const ok = micOn && pads.length >= 1 && pads[0].dur > 0.3 && errs.length === 0;
  console.log(JSON.stringify({ micOn, pads, pageErrors: errs }, null, 1));
  console.log("MIC-DEMO:", ok ? "OK" : "FAIL");
  process.exit(ok ? 0 : 1);
})();
