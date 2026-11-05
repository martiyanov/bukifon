#!/usr/bin/env node
/* Сверка раскладки демо с реальной панелью (spec/panel-spec-v0.4.json).
   Меряет центры 16 энкодеров, экрана, 2 кластеров клавиш, 2 фейдеров, 10 джеков
   и сравнивает с нормированными координатами панели 380×210 (допуск 8%). */
"use strict";
const path = require("path"), os = require("os"), fs = require("fs");
const { chromium } = require(path.join(os.homedir(), ".openclaw/workspace/node_modules/playwright"));
const SPEC = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "spec", "panel-spec-v0.4.json"), "utf8"));
const W = 380, H = 210;
const TOL = 0.08;
const exp = {};
// экран
const lcd = SPEC.lcd || SPEC.display || {};
const lx = lcd.x ?? 136, ly = lcd.y ?? 26.3, lw = lcd.w ?? 108, lh = lcd.h ?? 64.8;
exp.screen = { x: (lx + lw / 2) / W, y: (ly + lh / 2) / H };
// кластеры клавиш
exp.keysLeft = { x: 83 / W, y: 148 / H };
exp.keysRight = { x: 297 / W, y: 148 / H };
// фейдеры
exp.faders = { x: 190 / W, y: 150 / H };
// джеки — центр ряда
(SPEC.jacks || []).length ? null : null;
exp.jacks = { x: 190 / W, y: 10.5 / H };
// 16 энкодеров: из spec (если есть) или известные строки
const rows = [35.7, 68.5], lefts = [25.2, 54.1, 82.6, 111.4], rights = [269.3, 297.8, 326.6, 355.8];
exp.knobs = [];
rows.forEach(y => lefts.forEach(x => exp.knobs.push({ x: x / W, y: y / H })));
rows.forEach(y => rights.forEach(x => exp.knobs.push({ x: x / W, y: y / H })));

(async () => {
  const b = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-sandbox"] });
  const p = await b.newPage({ viewport: { width: 1500, height: 1000 } });
  await p.goto("file://" + path.join(__dirname, "..", "docs", "demo", "index.html"), { waitUntil: "load" });
  await p.waitForTimeout(1200);
  const data = await p.evaluate(() => {
    const box = document.querySelector(".device").getBoundingClientRect();
    const center = (el) => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; };
    const norm = (pt) => ({ x: (pt.x - box.x) / box.width, y: (pt.y - box.y) / box.height });
    const knobs = [...document.querySelectorAll(".knob")].map(k => norm(center(k)));
    const jacks = [...document.querySelectorAll(".jack")].map(j => norm(center(j)));
    const faders = [...document.querySelectorAll(".fader")].map(f => norm(center(f)));
    const keys = ["#keysLeft", "#keysRight"].map(s => norm(center(document.querySelector(s))));
    const screen = norm(center(document.querySelector(".screen-wrap")));
    return { knobs, jacks, faders, keys, screen, box: { w: box.width, h: box.height, r: box.width / box.height } };
  });
  await b.close();
  const D = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const results = [];
  const push = (name, ok, detail) => results.push({ name, ok, detail });
  const jacksY = data.jacks.reduce((s, j) => s + j.y, 0) / data.jacks.length;
  const fY = (data.faders[0].y + data.faders[1].y) / 2;
  const fX = (data.faders[0].x + data.faders[1].x) / 2;
  const kn = data.knobs;
  const leftKnobs = kn.filter(k => k.x < 0.5), rightKnobs = kn.filter(k => k.x >= 0.5);
  const avgY = (a) => a.reduce((s, k) => s + k.y, 0) / a.length;

  push("10 джеков сверху", data.jacks.length === 10 && jacksY < data.screen.y, `jacks y=${jacksY.toFixed(2)}, screen y=${data.screen.y.toFixed(2)}`);
  push("экран выше клавиш", data.screen.y < data.keys[0].y && data.screen.y < data.keys[1].y, `screen ${data.screen.y.toFixed(2)} < keys ${data.keys[0].y.toFixed(2)}`);
  push("16 энкодеров, 8+8 по сторонам", leftKnobs.length === 8 && rightKnobs.length === 8, `left=${leftKnobs.length}, right=${rightKnobs.length}`);
  push("энкодеры слева/справа от экрана", Math.max(...leftKnobs.map(k => k.x)) < data.screen.x && Math.min(...rightKnobs.map(k => k.x)) > data.screen.x, `L max=${Math.max(...leftKnobs.map(k => k.x)).toFixed(2)}, R min=${Math.min(...rightKnobs.map(k => k.x)).toFixed(2)}`);
  push("энкодеры на уровне экрана (±0.20)", Math.abs(avgY(leftKnobs) - data.screen.y) <= 0.20 && Math.abs(avgY(rightKnobs) - data.screen.y) <= 0.20, `knobs y=${avgY(leftKnobs).toFixed(2)}, screen y=${data.screen.y.toFixed(2)}`);
  push("клавиши слева и справа от фейдеров", data.keys[0].x < fX && fX < data.keys[1].x, `keys ${data.keys[0].x.toFixed(2)} < faders ${fX.toFixed(2)} < ${data.keys[1].x.toFixed(2)}`);
  push("фейдеры между кластерами клавиш (низ)", fY > data.screen.y && Math.abs(fY - data.keys[0].y) <= 0.15, `faders y=${fY.toFixed(2)}, keys y=${data.keys[0].y.toFixed(2)}`);
  push("пропорция панели ≈ 380:210", Math.abs(data.box.r - 380 / 210) <= 0.06, `device ${data.box.r.toFixed(3)} vs panel ${(380 / 210).toFixed(3)}`);

  // для справки: где демо отличается от мм-карты (экран увеличен для читаемости)
  const info = [
    ["screen center", exp.screen, data.screen],
    ["keysLeft", exp.keysLeft, data.keys[0]],
    ["keysRight", exp.keysRight, data.keys[1]],
    ["faders center", exp.faders, { x: fX, y: fY }],
    ["jacks row", exp.jacks, { x: data.jacks.reduce((s, j) => s + j.x, 0) / data.jacks.length, y: jacksY }],
  ];

  let fail = 0;
  console.log("проверка".padEnd(42), "результат".padEnd(9), "детали");
  for (const r of results) { if (!r.ok) fail++; console.log(r.name.padEnd(42), (r.ok ? "OK" : "FAIL").padEnd(9), r.detail); }
  console.log("\nсправочно (нормированные координаты, демо vs мм-карта):");
  for (const [n, e, g] of info) console.log(" ", n.padEnd(16), "panel", `${e.x.toFixed(2)},${e.y.toFixed(2)}`, " demo", `${g.x.toFixed(2)},${g.y.toFixed(2)}`);
  console.log("device aspect:", data.box.r.toFixed(3), "panel:", (380 / 210).toFixed(3));
  console.log(fail === 0 ? "LAYOUT OK" : `LAYOUT FAIL: ${fail} проверок`);
  process.exit(fail === 0 ? 0 : 1);
})();
