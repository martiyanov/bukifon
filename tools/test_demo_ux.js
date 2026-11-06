#!/usr/bin/env node
/* Авто-прогон blind UX-теста в демо (?test=1) на RU и EN: Playwright управляет браузером,
   проходит 8 задач в каждом языке и проверяет, что харнесс засчитывает их, что нет
   ошибок страницы, что все ключи RU/EN на месте, что текст в canvas-ячейках не
   переполняет их и что доступность (aria/роли/клавиатура) работает.

   Запуск:
     node tools/test_demo_ux.js          # RU (по умолчанию, без ?lang) + EN (?lang=en)
     node tools/test_demo_ux.js ru       # только RU
     node tools/test_demo_ux.js en       # только EN
*/
"use strict";
const path = require("path"), os = require("os");
const { chromium } = require(path.join(os.homedir(), ".openclaw/workspace/node_modules/playwright"));

const RUNS = [
  { lang: "ru", query: "?test=1" },              // язык по умолчанию — RU (без параметра)
  { lang: "en", query: "?test=1&lang=en" },      // EN через URL-параметр
];
const LANGS = { ru: ["ГЛАВН", "ОГИБ", "ГЕН"], en: ["MAIN", "ENV", "GEN"] };
const want = (process.argv[2] || "both").toLowerCase();
const runs = want === "both" ? RUNS : RUNS.filter(r => r.lang === want);
if (!runs.length) { console.log("usage: node tools/test_demo_ux.js [ru|en|both]"); process.exit(2); }

const URL = "file://" + path.join(__dirname, "..", "docs", "demo", "index.html");

async function runLang(browser, run) {
  const p = await browser.newPage({ viewport: { width: 1500, height: 1100 } });
  const errors = [];
  p.on("pageerror", e => errors.push(e.message));
  await p.addInitScript(() => { try { localStorage.removeItem("bukifon-demo-lang"); } catch (e) {} });
  await p.goto(URL + run.query, { waitUntil: "load" });
  await p.waitForTimeout(800);
  const canvas = await p.locator("#screen").boundingBox();
  const W = 800, H = 480;
  const clickCanvas = async (x, y) => { await p.mouse.click(canvas.x + x * canvas.width / W, canvas.y + y * canvas.height / H); };
  // 1: звук — клавиша A
  await p.keyboard.press("KeyA"); await p.waitForTimeout(350);
  // 2: ENV — клик по чипу страницы (по data-page, а не по тексту: язык может быть RU/EN)
  await p.locator('#pagechips button[data-page="env"]').click(); await p.waitForTimeout(300);
  // 3: замьютить две партии — клик по именам партий на канвасе
  await clickCanvas(40, 96 + 14); await clickCanvas(40, 96 + 56 + 14); await p.waitForTimeout(300);
  // 4: GEN → EUCLID (второй энкодер)
  await p.locator('#pagechips button[data-page="gen"]').click(); await p.waitForTimeout(300);
  console.log(`[${run.lang}] after GEN:`, await p.evaluate(() => ({ page: state.page, idx: state.test.idx, flags: window.TEST })));
  const knobs = p.locator("#knobs .knob");
  const k1 = await knobs.nth(1).boundingBox();
  await p.mouse.move(k1.x + k1.width / 2, k1.y + k1.height / 2); await p.mouse.down();
  await p.mouse.move(k1.x + k1.width / 2, k1.y - 40, { steps: 8 }); await p.mouse.up(); await p.waitForTimeout(400);
  console.log(`[${run.lang}] after knob1:`, await p.evaluate(() => ({ page: state.page, idx: state.test.idx, flags: window.TEST })));
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
  const probe = await p.evaluate(() => {
    const out = { i18n: window.__i18n.audit(), fit: window.__i18n.textFit(null) };
    out.lang = window.__i18n.lang();
    out.htmlLang = document.documentElement.lang;
    out.title = document.title;
    out.stored = (() => { try { return localStorage.getItem("bukifon-demo-lang"); } catch (e) { return null; } })();
    out.chips = [...document.querySelectorAll("#pagechips button")].map(b => b.textContent);
    const btns = [...document.querySelectorAll("button")].filter(b => b.offsetParent !== null);
    out.a11y = {
      buttonsNamed: btns.every(b => ((b.getAttribute("aria-label") || b.textContent || "").trim().length > 0)),
      knobs: [...document.querySelectorAll(".knob")].every(k => k.getAttribute("role") === "slider" && k.tabIndex === 0 && (k.getAttribute("aria-label") || "").length > 0 && k.getAttribute("aria-valuemin") != null),
      faders: [...document.querySelectorAll(".fader")].every(f => f.getAttribute("role") === "slider" && f.tabIndex === 0 && (f.getAttribute("aria-label") || "").length > 0),
      jacks: [...document.querySelectorAll(".jack")].every(j => j.getAttribute("role") === "button" && j.tabIndex === 0 && (j.getAttribute("aria-label") || "").length > 0),
      live: !!document.getElementById("live"),
      rawKeys: (document.body.innerText.match(/\b(?:app|btn|label|page|param|macro|msg|test|task|a11y|hint|block|ctx|col|ext|mode|theme|fader|overlay|unit|status|info|midi|preset|footer|nav)\.[a-zA-Z][a-zA-Z0-9]*/g) || []).length,
    };
    return out;
  });
  // видимый фокус при навигации с клавиатуры
  await p.keyboard.press("Tab"); await p.waitForTimeout(120);
  const focusRing = await p.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return { ok: false, tag: "body" };
    const cs = getComputedStyle(el);
    return { ok: cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0, tag: el.tagName, outline: cs.outlineStyle + " " + cs.outlineWidth };
  });
  // клавиатурная доступность: энкодер, фейдер, джек
  const kbBefore = await p.evaluate(() => { const k = document.querySelector("#knobs .knob"); k.focus(); return { focused: document.activeElement === k, val: +k.getAttribute("aria-valuenow") }; });
  await p.keyboard.press("ArrowUp"); await p.waitForTimeout(150);
  const kbAfter = await p.evaluate(() => { const k = document.querySelector("#knobs .knob"); return { focused: document.activeElement === k, val: +k.getAttribute("aria-valuenow") }; });
  const fbBefore = await p.evaluate(() => { const f = document.querySelector(".fader"); f.focus(); return { focused: document.activeElement === f, val: +f.getAttribute("aria-valuenow") }; });
  await p.keyboard.press("ArrowUp"); await p.waitForTimeout(150);
  const fbAfter = await p.evaluate(() => { const f = document.querySelector(".fader"); return { focused: document.activeElement === f, val: +f.getAttribute("aria-valuenow") }; });
  const jackBefore = await p.evaluate(() => { const j = document.querySelector(".jack"); j.focus(); return j.getAttribute("aria-pressed"); });
  await p.keyboard.press("Enter"); await p.waitForTimeout(150);
  const jackAfter = await p.evaluate(() => document.querySelector(".jack").getAttribute("aria-pressed"));
  // клавиша клавиатуры: Enter/пробел играет ноту и держит aria-pressed
  const keyBtn = await p.evaluate(() => { const b = document.querySelector("#keysLeft button"); b.focus(); return { focused: document.activeElement === b, labelled: (b.getAttribute("aria-label") || "").length > 0, pressed: b.getAttribute("aria-pressed") }; });
  await p.keyboard.down("Enter"); await p.waitForTimeout(120);
  const keyDown = await p.evaluate(() => document.querySelector("#keysLeft button").getAttribute("aria-pressed"));
  await p.keyboard.up("Enter"); await p.waitForTimeout(120);
  const keyUp = await p.evaluate(() => document.querySelector("#keysLeft button").getAttribute("aria-pressed"));

  // EXT: левые 8 энкодеров должны менять поля выбранного внешнего трека, а не page params
  const extBase = await p.evaluate(() => ({
    mode: state.mode,
    ch: state.extTracks[0].ch, prog: state.extTracks[0].prog,
    p0: state.parts[state.selPart].pages[0][0], p1: state.parts[state.selPart].pages[0][1],
  }));
  await clickCanvas(660, 20); await p.waitForTimeout(350); // таб EXT в шапке экрана
  const extMode = await p.evaluate(() => state.mode);
  const extKnob0 = await knobs.nth(0).boundingBox();
  await p.mouse.move(extKnob0.x + extKnob0.width / 2, extKnob0.y + extKnob0.height / 2); await p.mouse.down();
  await p.mouse.move(extKnob0.x + extKnob0.width / 2, extKnob0.y - 40, { steps: 8 }); await p.mouse.up(); await p.waitForTimeout(300);
  const extDrag = await p.evaluate(() => ({
    ch: state.extTracks[0].ch, prog: state.extTracks[0].prog,
    p0: state.parts[state.selPart].pages[0][0], p1: state.parts[state.selPart].pages[0][1],
    ariaMax0: document.querySelectorAll("#knobs .knob")[0].getAttribute("aria-valuemax"),
    label0: document.querySelectorAll("#knobs .knob")[0].getAttribute("aria-label"),
    vt0: document.querySelectorAll("#knobs .knob")[0].getAttribute("aria-valuetext"),
  }));
  await p.evaluate(() => document.querySelectorAll("#knobs .knob")[1].focus());
  await p.keyboard.press("ArrowUp"); await p.waitForTimeout(250);
  const extKey = await p.evaluate(() => ({
    ch: state.extTracks[0].ch, prog: state.extTracks[0].prog,
    p0: state.parts[state.selPart].pages[0][0], p1: state.parts[state.selPart].pages[0][1],
    ariaMax1: document.querySelectorAll("#knobs .knob")[1].getAttribute("aria-valuemax"),
    label1: document.querySelectorAll("#knobs .knob")[1].getAttribute("aria-label"),
  }));
  // Home/End по всем 8 полям: значения должны совпасть с EXT_MIN/EXT_MAX, page params — не тронуты
  const extEnds = [];
  for (let i = 0; i < 8; i++) {
    await p.evaluate((i) => document.querySelectorAll("#knobs .knob")[i].focus(), i);
    await p.keyboard.press("End"); await p.waitForTimeout(90);
    const hi = await p.evaluate((i) => ({ v: extVal(i), page: pval()[i] }), i);
    await p.keyboard.press("Home"); await p.waitForTimeout(90);
    const lo = await p.evaluate((i) => ({ v: extVal(i), page: pval()[i] }), i);
    extEnds.push({ i, hi: hi.v, min: lo.v, pageHi: hi.page, pageLo: lo.page });
  }
  const extAfter = await p.evaluate(() => ({
    p0: state.parts[state.selPart].pages[0][0], p1: state.parts[state.selPart].pages[0][1],
  }));

  // переключение языка на лету + состояние в URL/localStorage
  const other = run.lang === "ru" ? "en" : "ru";
  await p.locator(`[data-lang="${other}"]`).click(); await p.waitForTimeout(400);
  const switched = await p.evaluate(() => ({
    lang: window.__i18n.lang(), htmlLang: document.documentElement.lang,
    search: location.search, stored: (() => { try { return localStorage.getItem("bukifon-demo-lang"); } catch (e) { return null; } })(),
    chips: [...document.querySelectorAll("#pagechips button")].map(b => b.textContent),
  }));
  await p.locator(`[data-lang="${run.lang}"]`).click(); await p.waitForTimeout(300);
  const backLang = await p.evaluate(() => window.__i18n.lang());

  await p.close();
  if (!res) return { lang: run.lang, fail: "state недоступен", errors };
  const ok = res.results.filter(x => x.ok).length;
  const expectChips = LANGS[run.lang];
  const opt = probe.a11y;
  const fail = [];
  if (!(res.done && ok === 8 && res.results.length === 8)) fail.push(`UX ${ok}/8 done=${res.done}`);
  if (errors.length) fail.push(`pageErrors=${errors.length}`);
  if (probe.lang !== run.lang || probe.htmlLang !== run.lang) fail.push(`lang=${probe.lang}/${probe.htmlLang}`);
  if (probe.i18n.missingEn.length || probe.i18n.missingRu.length || probe.i18n.empty.length || probe.i18n.usedMissing.length) fail.push("i18n table: " + JSON.stringify(probe.i18n));
  if (probe.fit.overflows.length) fail.push("text overflow: " + probe.fit.overflows.map(o => o.str + "=" + o.w + ">" + o.max).join("; "));
  if (!expectChips.every(c => probe.chips.includes(c))) fail.push("page chips: " + probe.chips.join(","));
  if (run.lang === "en" && probe.stored !== "en") fail.push("localStorage lang=" + probe.stored);
  if (!opt.buttonsNamed || !opt.knobs || !opt.faders || !opt.jacks || !opt.live) fail.push("a11y: " + JSON.stringify(opt));
  if (!focusRing.ok) fail.push("focus ring: " + JSON.stringify(focusRing));
  if (opt.rawKeys) fail.push("raw i18n keys visible: " + opt.rawKeys);
  if (!(kbBefore.focused && kbAfter.focused && kbAfter.val > kbBefore.val)) fail.push(`knob keyboard ${JSON.stringify(kbBefore)}->${JSON.stringify(kbAfter)}`);
  if (!(fbBefore.focused && fbAfter.focused && fbAfter.val > fbBefore.val)) fail.push(`fader keyboard ${JSON.stringify(fbBefore)}->${JSON.stringify(fbAfter)}`);
  if (!(jackBefore === "false" && jackAfter === "true")) fail.push(`jack keyboard ${jackBefore}->${jackAfter}`);
  if (!(keyBtn.focused && keyBtn.labelled && keyBtn.pressed === "false" && keyDown === "true" && keyUp === "false")) fail.push(`key button keyboard ${JSON.stringify(keyBtn)} ${keyDown}->${keyUp}`);
  const EXT_MIN = [1, 0, 1, 1, 0, 0, 50, 0], EXT_MAX = [16, 127, 127, 16, 127, 127, 75, 1];
  const extOk = extBase.mode === 0 && extMode === 4 && extDrag.ch !== extBase.ch && extDrag.prog === extBase.prog &&
    extDrag.p0 === extBase.p0 && extDrag.p1 === extBase.p1 && extDrag.ariaMax0 === "16" && /^.+/.test(extDrag.label0 || "") &&
    /\s\d+$/.test(extDrag.vt0 || "") && // EXT-значения не должны получать page-единицы (Гц/мс)
    extKey.prog !== extBase.prog && extKey.ch === extDrag.ch && extKey.p0 === extBase.p0 && extKey.p1 === extBase.p1 && extKey.ariaMax1 === "127" &&
    extEnds.every((e) => e.hi === EXT_MAX[e.i] && e.min === EXT_MIN[e.i]) &&
    extAfter.p0 === extBase.p0 && extAfter.p1 === extBase.p1;
  if (!extOk) fail.push("EXT encoders: " + JSON.stringify({ extBase, extMode, extDrag, extKey, extEnds, extAfter }));
  if (switched.lang !== other || switched.htmlLang !== other) fail.push("switch lang: " + JSON.stringify(switched));
  if (other === "en" && !/lang=en/.test(switched.search)) fail.push("URL lang=en missing: " + switched.search);
  if (other === "ru" && /lang=ru/.test(switched.search)) fail.push("URL should drop lang for RU: " + switched.search);
  if (switched.stored !== other) fail.push("switch localStorage=" + switched.stored);
  if (!LANGS[other].every(c => switched.chips.includes(c))) fail.push("switch chips: " + switched.chips.join(","));
  if (backLang !== run.lang) fail.push("switch back lang=" + backLang);
  return {
    lang: run.lang, ok, total: res.results.length, done: res.done,
    results: res.results, errors, textFitRows: probe.fit.rows.length, overflows: probe.fit.overflows.length,
    i18n: probe.i18n, a11y: opt, focusRing, keyboard: { knob: [kbBefore.val, kbAfter.val], fader: [fbBefore.val, fbAfter.val], jack: [jackBefore, jackAfter], key: [keyBtn.pressed, keyDown, keyUp] },
    ext: { mode: extMode, chDrag: [extBase.ch, extDrag.ch], progKey: [extBase.prog, extKey.prog],
      pageParams: [extBase.p0, extAfter.p0], pageParamsOk: extAfter.p0 === extBase.p0 && extAfter.p1 === extBase.p1,
      ends: extEnds.map((e) => e.hi + "/" + e.min).join(",") },
    langSwitch: { to: other, search: switched.search, stored: switched.stored, htmlLang: switched.htmlLang, back: backLang },
    fail,
  };
}

(async () => {
  const b = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"] });
  const out = [];
  let bad = 0;
  for (const run of runs) {
    const r = await runLang(b, run);
    out.push(r);
    if (r.fail && r.fail.length) { bad++; console.log(`\n[${run.lang.toUpperCase()}] FAIL:`, r.fail); }
    else console.log(`\n[${run.lang.toUpperCase()}] OK`);
  }
  await b.close();
  for (const r of out) {
    console.log(`\n=== ${r.lang.toUpperCase()} ===`);
    if (r.results) console.log(JSON.stringify(r.results, null, 1));
    console.log(`UX-TEST ${r.lang.toUpperCase()}: ${r.ok}/${r.total} задач, done=${r.done}, pageErrors=${(r.errors || []).length}, ` +
      `textFit=${r.textFitRows - r.overflows}/${r.textFitRows} (overflow=${r.overflows}), ` +
      `keys RU/EN=${r.i18n ? r.i18n.ru + "/" + r.i18n.en + " missing=" + (r.i18n.missingEn.length + r.i18n.missingRu.length + r.i18n.usedMissing.length) : "n/a"}, ` +
      `a11y=${r.a11y ? (r.a11y.buttonsNamed && r.a11y.knobs && r.a11y.faders && r.a11y.jacks && r.a11y.live && !r.a11y.rawKeys && r.focusRing && r.focusRing.ok ? "OK" : "FAIL") : "n/a"}, ` +
      `keyboard=${r.keyboard ? "knob " + r.keyboard.knob.join("→") + ", fader " + r.keyboard.fader.join("→") + ", jack " + r.keyboard.jack.join("→") + ", key " + r.keyboard.key.join("→") : "n/a"}, ` +
      `switch=${r.langSwitch ? r.langSwitch.to + " (" + r.langSwitch.search + ", stored=" + r.langSwitch.stored + ") → back " + r.langSwitch.back : "n/a"}, ` +
      `ext=${r.ext ? "mode=" + r.ext.mode + ", CH " + r.ext.chDrag.join("→") + ", PROG " + r.ext.progKey.join("→") + ", page-param " + r.ext.pageParams.map(x => Math.round(x * 10) / 10).join("→") + " (unchanged=" + r.ext.pageParamsOk + "), Home/End=" + r.ext.ends : "n/a"}`);
    if (r.errors && r.errors.length) console.log("PAGE ERRORS:", r.errors.slice(0, 3));
  }
  console.log(`\nUX-TEST SUMMARY: ${out.map(r => r.lang.toUpperCase() + " " + (r.fail && r.fail.length ? "FAIL" : "PASS")).join(" · ")}`);
  process.exit(bad === 0 ? 0 : 1);
})();
