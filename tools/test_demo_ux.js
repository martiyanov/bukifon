#!/usr/bin/env node
/* Авто-прогон blind UX-теста в демо (?test=1): Playwright управляет браузером,
   проходит 8 задач и проверяет, что харнесс засчитывает их. */
"use strict";
const path = require("path"), os = require("os");
const { chromium } = require(path.join(os.homedir(), ".openclaw/workspace/node_modules/playwright"));
const url = "file://" + path.join(__dirname, "..", "docs", "demo", "index.html") + "?test=1";
(async () => {
  const b = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"] });
  const p = await b.newPage({ viewport: { width: 1500, height: 1100 } });
  const errors = [];
  p.on("pageerror", e => errors.push(e.message));
  await p.goto(url, { waitUntil: "load" });
  await p.waitForTimeout(800);
  const canvas = await p.locator("#screen").boundingBox();
  const W = 800, H = 480;
  const clickCanvas = async (x, y) => { await p.mouse.click(canvas.x + x * canvas.width / W, canvas.y + y * canvas.height / H); };
  // 1: звук — клавиша A
  await p.keyboard.press("KeyA"); await p.waitForTimeout(350);
  // 2: ENV — клик по чипу страницы
  await p.locator("#pagechips button", { hasText: "ENV" }).click(); await p.waitForTimeout(300);
  // 3: замьютить две партии — клик по именам партий на канвасе
  await clickCanvas(40, 96 + 14); await clickCanvas(40, 96 + 56 + 14); await p.waitForTimeout(300);
  // 4: GEN → EUCLID (второй энкодер)
  await p.locator("#pagechips button", { hasText: "GEN" }).click(); await p.waitForTimeout(300);
  console.log("after GEN:", await p.evaluate(()=>({page:state.page, idx:state.test.idx, flags: window.TEST})));
  const knobs = p.locator("#knobs .knob");
  const k1 = await knobs.nth(1).boundingBox();
  await p.mouse.move(k1.x + k1.width / 2, k1.y + k1.height / 2); await p.mouse.down();
  await p.mouse.move(k1.x + k1.width / 2, k1.y - 40, { steps: 8 }); await p.mouse.up(); await p.waitForTimeout(400);
  console.log("after knob1:", await p.evaluate(()=>({page:state.page, idx:state.test.idx, flags: window.TEST})));
  // 5: MUTATE → UNDO (третий энкодер + Ctrl+Z)
  const k2 = await knobs.nth(2).boundingBox();
  await p.mouse.move(k2.x + k2.width / 2, k2.y + k2.height / 2); await p.mouse.down();
  await p.mouse.move(k2.x + k2.width / 2, k2.y - 30, { steps: 6 }); await p.mouse.up(); await p.waitForTimeout(200);
  await p.keyboard.press("Control+z"); await p.waitForTimeout(300);
  // 6: REC → подождать → стоп
  await p.locator("#btnRec").click(); await p.waitForTimeout(1800); await p.locator("#btnRec").click(); await p.waitForTimeout(400);
  // 7: SCENE
  await p.locator('[data-fmode="SCENE"]').click(); await p.waitForTimeout(300);
  // 8: HOME
  await p.locator("#btnHome").click(); await p.waitForTimeout(500);
  const res = await p.evaluate(() => (window.state && window.state.test) ? { done: state.test.done, results: state.test.results } : null);
  await b.close();
  if (!res) { console.log("FAIL: state недоступен"); process.exit(1); }
  if (errors.length) { console.log("PAGE ERRORS:", errors.slice(0, 3)); }
  const ok = res.results.filter(x => x.ok).length;
  console.log(JSON.stringify(res.results, null, 1));
  console.log(`UX-TEST: ${ok}/${res.results.length} задач, done=${res.done}, pageErrors=${errors.length}`);
  process.exit(res.done && ok === 8 && errors.length === 0 ? 0 : 1);
})();
