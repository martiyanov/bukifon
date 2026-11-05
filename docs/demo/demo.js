/* Букифон — интерактивное веб-демо интерфейса и звука.
   Это НЕ прошивка: упрощённый 2-оп FM на WebAudio, 4 партии ×16 шагов.
   Цель — дать будущему пользователю потрогать логику UI: секвенсор, 16 энкодеров,
   42 клавиши, фейдеры, джеки, режимы Synth/Sampler/DAW/USB-KBD. */
"use strict";

const W = 800, H = 480;
const cv = document.getElementById("screen");
const ctx = cv.getContext("2d");
const $ = (id) => document.getElementById(id);

const MODES = ["SYNTH", "SAMPLER", "DAW", "USB-KBD"];
const PARAM_NAMES = ["CUTOFF", "RESON", "ENV AMT", "DRIVE", "ATK", "DEC", "SUS", "REL"];
const PARAM_MIN = [80, 0, 0, 0, 1, 20, 0, 20];
const PARAM_MAX = [12000, 100, 100, 100, 2000, 3000, 100, 3000];
const PART_COLORS = ["#38c172", "#f6993f", "#4aa3ff", "#b07cff"];
const PART_NAMES = ["FAT SAW", "FM BELL", "POLY VOX", "LADDER LEAD"];
const JACKS = ["CV OUT 1", "CV OUT 2", "CV OUT 3", "CV OUT 4", "CV IN 1", "CV IN 2", "GATE OUT", "GATE IN", "CLK OUT", "CLK IN"];

const state = {
  mode: 0, bpm: 120, playing: false, step: 0, selPart: 0,
  parts: [], volume: 0.7, delayMix: 0.25, cables: new Set(),
  masterL: 0, masterR: 0,
};

function defaultPart(i) {
  const scales = [[0, 0, 7, 12, 3, 10, 5, 7], [0, 12, 7, 16, 19, 24, 14, 21], [0, 7, 12, 16, 19, 21, 24, 28], [0, 2, 5, 7, 12, 14, 17, 19]];
  const steps = Array.from({ length: 16 }, (_, s) => ({ on: s % 4 === 0 || (s % 7 === 3), note: scales[i][s % 8], accent: s % 4 === 0 }));
  return {
    name: PART_NAMES[i], color: PART_COLORS[i], active: i === 0 ? true : i < 2,
    mute: false, root: [48, 72, 60, 55][i],
    steps,
    params: [/*cutoff*/ 3200 - i * 700, /*res*/ 20 + i * 15, /*env*/ 40, /*drive*/ 15, /*atk*/ 10 + i * 15, /*dec*/ 240 + i * 80, /*sus*/ 60, /*rel*/ 420],
  };
}
state.parts = [0, 1, 2, 3].map(defaultPart);

/* ---------- storage ---------- */
const KEY = "bukifon-demo-v1";
function save() {
  const p = { bpm: state.bpm, volume: state.volume, delayMix: state.delayMix, parts: state.parts, mode: state.mode, sel: state.selPart };
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) {}
}
function load() {
  try {
    const p = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!p) return;
    state.bpm = p.bpm ?? state.bpm; state.volume = p.volume ?? state.volume;
    state.delayMix = p.delayMix ?? state.delayMix; state.mode = p.mode ?? 0; state.selPart = p.sel ?? 0;
    if (Array.isArray(p.parts)) p.parts.forEach((x, i) => { if (x && x.steps) state.parts[i] = x; });
  } catch (e) {}
}

/* ---------- audio ---------- */
let AC = null, master, comp, delay, delayGain, analyser, masterData;
function audioInit() {
  if (AC) return;
  AC = new (window.AudioContext || window.webkitAudioContext)();
  master = AC.createGain(); master.gain.value = state.volume;
  comp = AC.createDynamicsCompressor(); comp.threshold.value = -12; comp.knee.value = 12; comp.ratio.value = 6;
  delay = AC.createDelay(1.0); delay.delayTime.value = 0.28;
  const fb = AC.createGain(); fb.gain.value = 0.32;
  delayGain = AC.createGain(); delayGain.gain.value = state.delayMix;
  analyser = AC.createAnalyser(); analyser.fftSize = 512; masterData = new Uint8Array(analyser.fftSize);
  master.connect(comp); comp.connect(AC.destination); comp.connect(analyser);
  master.connect(delay); delay.connect(fb); fb.connect(delay); delay.connect(delayGain); delayGain.connect(comp);
}
function mtof(m) { return 440 * Math.pow(2, (m - 69) / 12); }

const voices = [];
function noteOn(midi, vel = 0.8, part = state.parts[state.selPart]) {
  audioInit();
  if (AC.state === "suspended") AC.resume();
  const now = AC.currentTime;
  const v = {
    midi, part, vel, t0: now, rel: 0, dead: false,
    carrier: AC.createOscillator(), mod: AC.createOscillator(), modGain: AC.createGain(),
    amp: AC.createGain(), filt: AC.createBiquadFilter(),
  };
  const p = part.params, c = clamp(p[0], 80, 12000), q = clamp(p[1], 0, 100), drive = clamp(p[3], 0, 100) / 100;
  const ratio = [1, 2.01, 1.5, 0.5][state.parts.indexOf(part)] || 1;
  v.carrier.frequency.value = mtof(midi);
  v.mod.frequency.value = mtof(midi) * ratio;
  v.modGain.gain.value = mtof(midi) * (0.5 + (p[2] / 100) * 3) * (0.6 + drive);
  v.mod.connect(v.modGain); v.modGain.connect(v.carrier.frequency);
  v.filt.type = "lowpass"; v.filt.frequency.value = c; v.filt.Q.value = q / 12;
  v.carrier.connect(v.filt); v.filt.connect(v.amp); v.amp.connect(master);
  const atk = Math.max(0.002, p[4] / 1000), dec = Math.max(0.02, p[5] / 1000), sus = p[6] / 100, rel = Math.max(0.02, p[7] / 1000);
  v.amp.gain.setValueAtTime(0, now);
  v.amp.gain.linearRampToValueAtTime(vel * 0.9, now + atk);
  v.amp.gain.linearRampToValueAtTime(vel * 0.9 * (0.25 + sus * 0.75), now + atk + dec);
  v.carrier.start(now); v.mod.start(now);
  voices.push(v);
  if (voices.length > 24) { killVoice(voices.shift()); }
  return v;
}
function killVoice(v, rel = null) {
  if (!v || v.dead) return;
  v.dead = true;
  audioInit();
  const now = AC.currentTime, r = rel ?? Math.max(0.02, v.part.params[7] / 1000);
  try {
    v.amp.gain.cancelScheduledValues(now);
    v.amp.gain.setValueAtTime(Math.max(0.0001, v.amp.gain.value), now);
    v.amp.gain.exponentialRampToValueAtTime(0.0001, now + r);
    v.carrier.stop(now + r + 0.05); v.mod.stop(now + r + 0.05);
  } catch (e) { try { v.carrier.stop(); v.mod.stop(); } catch (e2) {} }
}
function noteOff(midi) { voices.filter((v) => v.midi === midi && !v.dead).forEach((v) => killVoice(v)); }
function allNotesOff() { voices.forEach((v) => killVoice(v)); }

function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

/* ---------- sequencer ---------- */
let seqTimer = null, nextStepTime = 0, lookahead = 0.1;
function stepDur() { return 60 / state.bpm / 4; } // 16th note
function startSeq() {
  audioInit();
  if (AC.state === "suspended") AC.resume();
  state.playing = true; nextStepTime = AC.currentTime + 0.05; state.step = 0;
  if (seqTimer) clearInterval(seqTimer);
  seqTimer = setInterval(scheduler, 25);
  save();
}
function stopSeq() {
  state.playing = false; if (seqTimer) { clearInterval(seqTimer); seqTimer = null; }
  for (const v of voices) killVoice(v, 0.08);
  save();
}
function scheduler() {
  if (!state.playing) return;
  while (nextStepTime < AC.currentTime + lookahead) {
    scheduleStep(state.step, nextStepTime);
    nextStepTime += stepDur();
    state.step = (state.step + 1) % 16;
  }
}
function scheduleStep(step, when) {
  for (const part of state.parts) {
    if (!part.active || part.mute) continue;
    const s = part.steps[step];
    if (!s || !s.on) continue;
    const midi = part.root + s.note;
    const vel = s.accent ? 1.0 : 0.65;
    // планируем «как есть»: WebAudio без точного времени для FM-голоса — стартуем сразу,
    // но при небольшом lookahead это звучит ровно; для точности используем setTimeout.
    const dt = Math.max(0, (when - AC.currentTime) * 1000);
    setTimeout(() => { noteOn(midi, vel, part); }, dt);
  }
}

/* ---------- keyboard / MIDI ---------- */
const keyMap = ["KeyA", "KeyW", "KeyS", "KeyE", "KeyD", "KeyF", "KeyT", "KeyG", "KeyY", "KeyH", "KeyU", "KeyJ", "KeyK", "KeyO", "KeyL", "KeyP", "Semicolon"];
const pressed = new Map();
function noteFromQwerty(code) {
  const i = keyMap.indexOf(code);
  return i < 0 ? null : 48 + i; // C3..E4
}
addEventListener("keydown", (e) => {
  if (e.repeat) return;
  const n = noteFromQwerty(e.code);
  if (n != null && !e.metaKey && !e.ctrlKey) { noteOn(n, 0.8); pressed.set(e.code, n); markKey(n, true); e.preventDefault(); }
  if (e.code === "Space") { state.playing ? stopSeq() : startSeq(); e.preventDefault(); }
});
addEventListener("keyup", (e) => {
  const n = pressed.get(e.code); if (n != null) { noteOff(n); markKey(n, false); pressed.delete(e.code); }
});

let midiAccess = null, midiOut = null;
function sendCC(cc, val) { if (midiOut) { try { midiOut.send([0xB0, cc, clamp(Math.round(val), 0, 127)]); } catch (e) {} } }
function midiInit() {
  if (!navigator.requestMIDIAccess) return;
  navigator.requestMIDIAccess({ sysex: false }).then((access) => {
    midiAccess = access;
    const bind = () => {
      const inputs = [...access.inputs.values()];
      const outputs = [...access.outputs.values()];
      midiOut = outputs[0] || null;
      $("midiState").textContent = inputs.length ? `MIDI: ${inputs.map((i) => i.name).join(", ").slice(0, 30)}` : "MIDI: нет входов";
      if (outputs.length) $("midiState").textContent += " · OUT OK";
      inputs.forEach((input) => { input.onmidimessage = onMidi; });
    };
    bind(); access.onstatechange = bind;
  }).catch(() => { $("midiState").textContent = "MIDI: нет доступа"; });
}
function onMidi(msg) {
  const [st, d1, d2] = msg.data;
  const cmd = st & 0xf0;
  if (cmd === 0x90 && d2 > 0) { noteOn(d1, d2 / 127); markKey(d1, true); }
  else if (cmd === 0x80 || (cmd === 0x90 && d2 === 0)) { noteOff(d1); markKey(d1, false); }
}

/* ---------- on-screen panel ---------- */
const keyEls = new Map();
function buildKeys() {
  // 2 половины по 21 клавише = 12 белых (C..B, C..B) + 9 чёрных, как Lapka-42
  const SEMI = [0, 2, 4, 5, 7, 9, 11];
  const blackAfterWhite = { 0: 1, 1: 3, 3: 6, 4: 8, 5: 10 }; // белая нота -> полутон чёрной
  for (const side of ["keysLeft", "keysRight"]) {
    const host = $(side); host.innerHTML = ""; host.classList.add("keys-piano");
    host.style.position = "relative"; host.style.height = "78px";
    const base = side === "keysLeft" ? 48 : 67;
    const white = document.createElement("div"); white.className = "row whites";
    white.style.display = "flex"; white.style.gap = "2px"; white.style.height = "100%";
    const blacks = document.createElement("div"); blacks.className = "blacks";
    blacks.style.position = "absolute"; blacks.style.inset = "0"; blacks.style.pointerEvents = "none";
    for (let k = 0; k < 12; k++) {
      const midi = base + [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19][k];
      const b = document.createElement("button"); b.textContent = noteName(midi); b.dataset.midi = midi;
      b.style.flex = "1"; b.style.height = "100%"; b.style.fontSize = "9px";
      b.addEventListener("pointerdown", (e) => { e.preventDefault(); noteOn(midi, 0.85); markKey(midi, true); b.setPointerCapture(e.pointerId); });
      b.addEventListener("pointerup", () => { noteOff(midi); markKey(midi, false); });
      b.addEventListener("pointerleave", () => { noteOff(midi); markKey(midi, false); });
      white.appendChild(b); keyEls.set(midi, b);
    }
    const bw = 100 / 12; // ширина белой клавиши в %
    const blacksPerHalf = [[0, 1], [1, 3], [3, 6], [4, 8], [5, 10], [7, 13], [8, 15], [10, 18], [11, 20]];
    for (const [wIdx, midi] of blacksPerHalf) {
      const b = document.createElement("button"); b.className = "black"; b.textContent = noteName(base + midi); b.dataset.midi = base + midi;
      b.style.position = "absolute"; b.style.height = "58%"; b.style.width = (bw * 0.62) + "%";
      b.style.left = ((wIdx + 0.7) * bw) + "%"; b.style.top = "0"; b.style.zIndex = 2; b.style.pointerEvents = "auto"; b.style.fontSize = "8px";
      b.addEventListener("pointerdown", (e) => { e.preventDefault(); noteOn(base + midi, 0.82); markKey(base + midi, true); b.setPointerCapture(e.pointerId); });
      b.addEventListener("pointerup", () => { noteOff(base + midi); markKey(base + midi, false); });
      b.addEventListener("pointerleave", () => { noteOff(base + midi); markKey(base + midi, false); });
      blacks.appendChild(b); keyEls.set(base + midi, b);
    }
    host.appendChild(white); host.appendChild(blacks);
  }
}
function noteName(m) { const n = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]; return n[m % 12] + (Math.floor(m / 12) - 1); }
function markKey(midi, on) { const el = keyEls.get(midi); if (el) el.classList.toggle("on", on); }

/* knobs */
const knobEls = [];
function buildKnobs() {
  const host = $("knobs"); host.innerHTML = "";
  for (let i = 0; i < 8; i++) {
    const wrap = document.createElement("div"); wrap.className = "k";
    const k = document.createElement("div"); k.className = "knob"; k.dataset.i = i;
    const label = document.createElement("span"); label.textContent = ["CUT", "RES", "ENV", "DRV", "ATK", "DEC", "SUS", "REL"][i];
    wrap.appendChild(k); wrap.appendChild(label); host.appendChild(wrap); knobEls.push(k);
    let startY = null, startVal = 0;
    const down = (e) => { e.preventDefault(); audioInit(); startY = e.clientY; startVal = state.parts[state.selPart].params[i]; k.setPointerCapture(e.pointerId); };
    const move = (e) => {
      if (startY == null) return;
      const dy = startY - e.clientY, range = PARAM_MAX[i] - PARAM_MIN[i];
      const val = clamp(startVal + (dy / 120) * range, PARAM_MIN[i], PARAM_MAX[i]);
      state.parts[state.selPart].params[i] = val; paintKnobs(); save(); sendCC(74 + i, ((val - PARAM_MIN[i]) / (PARAM_MAX[i] - PARAM_MIN[i])) * 127);
    };
    const up = () => { startY = null; };
    k.addEventListener("pointerdown", down); k.addEventListener("pointermove", move); k.addEventListener("pointerup", up); k.addEventListener("pointercancel", up);
  }
}
function paintKnobs() {
  const p = state.parts[state.selPart].params;
  knobEls.forEach((k, i) => {
    const frac = (p[i] - PARAM_MIN[i]) / (PARAM_MAX[i] - PARAM_MIN[i]);
    k.style.setProperty("--a", (frac * 260 - 130).toFixed(1) + "deg");
  });
}

/* faders */
function buildFaders() {
  const shareBtn = document.getElementById("btnShare");
  if (shareBtn) shareBtn.addEventListener("click", copyShareLink);
  document.querySelectorAll(".fader").forEach((f) => {
    let startY = null, startVal = 0;
    const down = (e) => { e.preventDefault(); startY = e.clientY; startVal = f.dataset.fader === "0" ? state.volume : state.delayMix; f.setPointerCapture(e.pointerId); };
    const move = (e) => {
      if (startY == null) return;
      const dy = startY - e.clientY;
      const val = clamp(startVal + dy / 140, 0, 1);
      if (f.dataset.fader === "0") { state.volume = val; master.gain.value = val; } else { state.delayMix = val; delayGain.gain.value = val; }
      f.style.setProperty("--top", ((1 - val) * 100).toFixed(1) + "%"); save();
    };
    const up = () => { startY = null; };
    f.addEventListener("pointerdown", down); f.addEventListener("pointermove", move); f.addEventListener("pointerup", up); f.addEventListener("pointercancel", up);
    f.style.setProperty("--top", ((1 - (f.dataset.fader === "0" ? state.volume : state.delayMix)) * 100).toFixed(1) + "%");
  });
}

/* jacks */
function buildJacks() {
  const host = $("jacks"); host.innerHTML = "";
  JACKS.forEach((name, i) => {
    const d = document.createElement("div"); d.className = "jack"; d.dataset.i = i;
    d.innerHTML = `<i></i><span>${name}</span>`;
    d.addEventListener("click", () => { state.cables.has(i) ? state.cables.delete(i) : state.cables.add(i); d.classList.toggle("active"); });
    host.appendChild(d);
  });
}

/* ---------- canvas UI ---------- */
function draw() {
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#0a1a1d"; ctx.fillRect(0, 0, W, H);
  // header
  ctx.fillStyle = "#0d2428"; ctx.fillRect(0, 0, W, 44);
  ctx.fillStyle = "#4fd1e0"; ctx.font = "700 26px Inter, system-ui, sans-serif"; ctx.fillText("БУКИФОН", 14, 30);
  ctx.font = "600 12px Inter, sans-serif"; ctx.fillStyle = "#7fb6bc";
  const infos = [["BPM", String(state.bpm)], ["BAR", "004"], ["PAT", "01"], ["STEP", String(state.step).padStart(2, "0")], ["MODE", MODES[state.mode]]];
  infos.forEach(([k, v], i) => { ctx.fillText(k, 20 + i * 42, 58); ctx.fillStyle = "#d7ecef"; ctx.font = "700 14px Inter, sans-serif"; ctx.fillText(v, 20 + i * 42, 74); ctx.fillStyle = "#7fb6bc"; ctx.font = "600 11px Inter, sans-serif"; });
  // mode tabs
  MODES.forEach((m, i) => {
    const x = 236 + i * 96, y = 6;
    ctx.fillStyle = i === state.mode ? "#4fd1e0" : "#103035";
    roundRect(x, y, 88, 20, 4); ctx.fill();
    ctx.fillStyle = i === state.mode ? "#04140b" : "#8fc4c9";
    ctx.font = "700 11px Inter"; ctx.textAlign = "center";
    ctx.fillText(m, x + 44, y + 14); ctx.textAlign = "left";
  });

  if (state.mode === 0) drawSynth();
  else if (state.mode === 1) drawSampler();
  else if (state.mode === 2) drawDaw();
  else drawUsbKbd();

  // meters bottom
  const lvl = analyser ? analyseLevel() : 0;
  ctx.fillStyle = "#0d2428"; ctx.fillRect(0, 444, W, 36);
  ctx.fillStyle = "#7fb6bc"; ctx.font = "600 11px Inter"; ctx.fillText("MASTER", 14, 466);
  ctx.fillStyle = "#17363b"; ctx.fillRect(88, 456, 320, 12);
  ctx.fillStyle = "#38c172"; ctx.fillRect(88, 456, 320 * clamp(lvl, 0, 1), 12);
  ctx.fillStyle = "#7fb6bc"; ctx.fillText("FADER 1 = MASTER · FADER 2 = DELAY · SPACE = PLAY/STOP", 430, 466);
}

function drawSynth() {
  const top = 96, rowH = 68;
  for (let pi = 0; pi < 4; pi++) {
    const part = state.parts[pi], y = top + pi * rowH;
    ctx.fillStyle = "#0e2024"; roundRect(8, y, W - 16, rowH - 8, 6); ctx.fill();
    ctx.fillStyle = part.color; ctx.font = "700 13px Inter"; ctx.fillText(`PART ${pi + 1}`, 18, y + 20);
    ctx.fillStyle = "#7fb6bc"; ctx.font = "600 11px Inter"; ctx.fillText(part.name + (part.mute ? " · MUTE" : "") + (pi === state.selPart ? " · EDIT" : ""), 18, y + 38);
    ctx.fillStyle = part.color; ctx.fillRect(18, y + 48, 92 * clamp(part.params[0] / 12000, 0, 1), 5);
    // steps
    for (let s = 0; s < 16; s++) {
      const x = 128 + s * 40, sy = y + 14, sw = 36, sh = rowH - 52;
      const st = part.steps[s];
      ctx.fillStyle = state.playing && state.step === s ? "#1e4a52" : "#081417";
      roundRect(x, sy, sw, sh, 4); ctx.fill();
      if (st.on) {
        ctx.fillStyle = st.accent ? "#f6993f" : (s % 4 === 0 ? "#38c172" : "#2e9e63");
        roundRect(x + 2, sy + 2, sw - 4, sh - 4, 3); ctx.fill();
      }
      if (state.playing && state.step === s) { ctx.strokeStyle = "#4fd1e0"; ctx.lineWidth = 2; roundRect(x - 1, sy - 1, sw + 2, sh + 2, 5); ctx.stroke(); }
      ctx.fillStyle = "#6f969b"; ctx.font = "9px Inter"; ctx.fillText(String(s + 1), x + 2, sy - 3);
    }
  }
  // params panel
  const p = state.parts[state.selPart].params;
  const py = 376;
  ctx.fillStyle = "#0e2024"; roundRect(8, py, W - 16, 64, 6); ctx.fill();
  for (let i = 0; i < 8; i++) {
    const x = 18 + i * 97;
    ctx.fillStyle = "#7fb6bc"; ctx.font = "600 10px Inter"; ctx.fillText(PARAM_NAMES[i], x, py + 16);
    ctx.fillStyle = "#17363b"; ctx.fillRect(x, py + 22, 88, 6);
    ctx.fillStyle = "#4fd1e0"; ctx.fillRect(x, py + 22, 88 * clamp((p[i] - PARAM_MIN[i]) / (PARAM_MAX[i] - PARAM_MIN[i]), 0, 1), 6);
    ctx.fillStyle = "#d7ecef"; ctx.font = "700 12px Inter"; ctx.fillText(fmtParam(i, p[i]), x, py + 46);
  }
  // encoder hints row (как на железе: E1..E8)
  for (let i = 0; i < 8; i++) {
    const x = 18 + i * 97;
    ctx.fillStyle = i === 0 ? "#38c172" : "#17363b"; ctx.fillRect(x, py - 18, 88, 14);
    ctx.fillStyle = i === 0 ? "#04140b" : "#7fb6bc"; ctx.font = "600 9px Inter"; ctx.fillText(`E${i + 1} ${PARAM_NAMES[i]}`, x + 4, py - 8);
  }
}
function fmtParam(i, v) {
  if (i === 0) return v >= 1000 ? (v / 1000).toFixed(1) + " кГц" : Math.round(v) + " Гц";
  if (i === 4 || i === 5 || i === 7) return Math.round(v) + " мс";
  return Math.round(v) + "%";
}
function drawSampler() {
  ctx.fillStyle = "#4fd1e0"; ctx.font = "700 18px Inter"; ctx.fillText("SAMPLER · SD", 20, 78);
  const rows = [["01", "kick_808.wav", "1.2 s", 0.62], ["02", "snare_dust.wav", "0.8 s", 0.34], ["03", "vinyl_loop.wav", "4.0 s", 0.78], ["04", "granular_pad.wav", "8.0 s", 0.22]];
  rows.forEach(([n, name, len, pos], i) => {
    const y = 96 + i * 52;
    ctx.fillStyle = "#0e2024"; roundRect(14, y, W - 28, 42, 5); ctx.fill();
    ctx.fillStyle = "#38c172"; ctx.fillText(n, 24, y + 26);
    ctx.fillStyle = "#d7ecef"; ctx.fillText(name, 54, y + 26);
    ctx.fillStyle = "#7fb6bc"; ctx.fillText(len, 320, y + 26);
    ctx.fillStyle = "#17363b"; ctx.fillRect(380, y + 18, 380, 8);
    ctx.fillStyle = "#4fd1e0"; ctx.fillRect(380, y + 18, 380 * pos, 8);
    ctx.fillStyle = "#7fb6bc"; ctx.font = "11px Inter"; ctx.fillText("GRAIN  " + Math.round(pos * 100) + "%", 380, y + 40);
    ctx.font = "600 12px Inter";
  });
  ctx.fillStyle = "#7fb6bc"; ctx.font = "600 12px Inter"; ctx.fillText("START / END / GRAIN / PITCH — E1…E8 · клик по дорожке = проиграть", 20, 360);
}
function drawDaw() {
  ctx.fillStyle = "#4fd1e0"; ctx.font = "700 18px Inter"; ctx.fillText("DAW · USB HID + MIDI", 20, 78);
  const banks = [["CC 16-31", "CUTOFF 74", "RESO 71", "DRIVE 91", "ATK 73"], ["CC 32-47", "DEC 75", "SUS 76", "REL 72", "PAN 10"]];
  banks.forEach((bank, bi) => {
    ctx.fillStyle = "#0e2024"; roundRect(14, 96 + bi * 120, W - 28, 104, 6); ctx.fill();
    ctx.fillStyle = "#7fb6bc"; ctx.fillText(bank[0], 26, 118 + bi * 120);
    for (let i = 0; i < 16; i++) {
      const x = 120 + i * 40, y = 132 + bi * 120;
      ctx.fillStyle = i < 4 ? "#4aa3ff" : "#17363b"; roundRect(x, y, 34, 40, 4); ctx.fill();
      ctx.fillStyle = i < 4 ? "#04140b" : "#7fb6bc"; ctx.font = "700 11px Inter"; ctx.fillText(String(i + 16 + bi * 16), x + 6, y + 16);
      ctx.font = "9px Inter"; ctx.fillText(i < 4 ? bank[1 + i].split(" ")[0] : "", x + 4, y + 32);
    }
  });
  ctx.fillStyle = "#7fb6bc"; ctx.font = "600 12px Inter"; ctx.fillText("Транспорт: PLAY / STOP · 16 энкодеров = CC · Web MIDI подключается автоматически", 20, 400);
}
function drawUsbKbd() {
  ctx.fillStyle = "#4fd1e0"; ctx.font = "700 18px Inter"; ctx.fillText("USB-KEYBOARD · HID", 20, 78);
  ctx.fillStyle = "#0e2024"; roundRect(14, 92, W - 28, 200, 6); ctx.fill();
  const rows = [["q w e r t y u i o p", "a s d f g h j k l ;", "z x c v b n m , . /"]];
  rows[0].forEach((r, i) => { ctx.fillStyle = "#d7ecef"; ctx.font = "600 18px ui-monospace, monospace"; ctx.fillText(r, 34, 140 + i * 50); });
  ctx.fillStyle = "#7fb6bc"; ctx.font = "600 12px Inter";
  ctx.fillText("42 клавиши = 42 клавиши HID; слои: BASE / SHIFT / SYMBOLS; LAYER переключается энкодером E8.", 20, 330);
  ctx.fillText("Клавиатура работает как MIDI-клавиатура и как печатная — одна прошивка, два режима.", 20, 356);
}
function analyseLevel() {
  if (!analyser) return 0;
  analyser.getByteTimeDomainData(masterData);
  let sum = 0;
  for (let i = 0; i < masterData.length; i++) { const v = (masterData[i] - 128) / 128; sum += v * v; }
  return Math.sqrt(sum / masterData.length);
}
function roundRect(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

/* ---------- canvas interaction: steps / mode tabs ---------- */
function canvasPos(e) {
  const r = cv.getBoundingClientRect();
  return { x: (e.clientX - r.left) * (W / r.width), y: (e.clientY - r.top) * (H / r.height) };
}
cv.addEventListener("pointerdown", (e) => {
  const { x, y } = canvasPos(e);
  if (y < 44) {
    const i = Math.floor((x - 236) / 96);
    if (i >= 0 && i < 4) { state.mode = i; save(); }
    return;
  }
  if (state.mode === 0) {
    // выбор партии по клику слева/на шаге
    const pi = Math.floor((y - 52) / 78);
    if (pi >= 0 && pi <= 3 && x > 120 && x < 776) {
      const s = Math.floor((x - 128) / 40);
      if (s >= 0 && s <= 15) {
        const part = state.parts[pi]; part.steps[s].on = !part.steps[s].on;
        if (part.steps[s].on) part.steps[s].accent = s % 4 === 0;
        state.selPart = pi; paintKnobs(); save(); startPreview(part, s);
      }
    }
  }
});
function startPreview(part, s) { if (!state.playing) { const n = part.root + part.steps[s].note; noteOn(n, 0.8, part); setTimeout(() => noteOff(n), 180); } }

/* ---------- share pattern via URL ---------- */
function encodeState() {
  const compact = { b: state.bpm, s: state.selPart, p: state.parts.map((p) => ({ r: p.root, a: p.active ? 1 : 0, m: p.mute ? 1 : 0, q: p.params.map((x) => Math.round(x)), st: p.steps.map((x) => (x.on ? (x.accent ? 2 : 1) : 0) * 128 + x.note) })) };
  return btoa(JSON.stringify(compact)).replace(/=+$/, "");
}
function decodeState(b64) {
  try {
    const compact = JSON.parse(atob(b64));
    if (compact.b) state.bpm = clamp(compact.b, 40, 220);
    if (compact.s != null) state.selPart = clamp(compact.s, 0, 3);
    (compact.p || []).forEach((cp, i) => {
      const p = state.parts[i]; if (!p) return;
      p.root = cp.r; p.active = !!cp.a; p.mute = !!cp.m; p.params = (cp.q || p.params).slice(0, 8);
      (cp.st || []).forEach((v, s2) => { const on = Math.floor(v / 128) > 0; p.steps[s2].on = on; p.steps[s2].accent = Math.floor(v / 128) === 2; p.steps[s2].note = v % 128; });
    });
    return true;
  } catch (e) { return false; }
}
function copyShareLink() {
  const url = location.origin + location.pathname + "#p=" + encodeState();
  navigator.clipboard && navigator.clipboard.writeText(url).catch(() => {});
  $("shareState").textContent = "ссылка скопирована";
  setTimeout(() => { $("shareState").textContent = ""; }, 2000);
}
function loadFromHash() { const m = location.hash.match(/#p=(.+)/); if (m) return decodeState(m[1]); return false; }

/* ---------- init ---------- */
function bindUI() {
  $("btnPlay").addEventListener("click", () => state.playing ? stopSeq() : startSeq());
  $("btnStop").addEventListener("click", () => stopSeq());
  $("bpm").value = state.bpm;
  $("bpm").addEventListener("change", (e) => { state.bpm = clamp(+e.target.value || 120, 40, 220); save(); });
  $("volume").value = Math.round(state.volume * 100);
  $("volume").addEventListener("input", (e) => { state.volume = +e.target.value / 100; if (master) master.gain.value = state.volume; save(); });
  const shareBtn = document.getElementById("btnShare");
  if (shareBtn) shareBtn.addEventListener("click", copyShareLink);
  document.querySelectorAll(".fader").forEach((f) => {
    const v = f.dataset.fader === "0" ? state.volume : state.delayMix;
    f.style.setProperty("--top", ((1 - v) * 100).toFixed(1) + "%");
  });
}
load(); loadFromHash(); buildKeys(); buildKnobs(); buildFaders(); buildJacks(); bindUI(); paintKnobs(); midiInit();
(function loop() { draw(); requestAnimationFrame(loop); })();
