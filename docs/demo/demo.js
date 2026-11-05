/* Букифон — интерактивное веб-демо (UI/UX-модель, не прошивка).
   800×480, 4 партии ×16 шагов, 16 энкодеров, 4 страницы параметров, 4 темы экрана,
   42 клавиши, 2 фейдера, 10 джеков, Web MIDI in/out, share через URL. */
"use strict";

const W = 800, H = 480;
const cv = document.getElementById("screen");
const ctx = cv.getContext("2d");
const $ = (id) => document.getElementById(id);

const MODES = ["SYNTH", "SAMPLER", "DAW", "USB-KBD"];
const PAGES = ["MAIN", "FM", "ENV", "FX"];
const PAGE_PARAMS = [
  ["CUTOFF", "RESON", "ENV AMT", "DRIVE", "ATK", "DEC", "SUS", "REL"],
  ["RATIO", "DEPTH", "DETUNE", "OP2", "FM ENV", "FEEDBK", "NOISE", "SUB"],
  ["ATK", "DEC", "SUS", "REL", "FILT ENV", "VEL SENS", "GLIDE", "LFO RATE"],
  ["DELAY MIX", "FEEDBK", "TIME", "DRIVE", "CRUSH", "WIDTH", "REVERB", "MASTER"],
];
const PAGE_MIN = [[80,0,0,0,1,20,0,20],[1,0,0,0,0,0,0,0],[1,20,0,20,0,0,0,0],[0,0,20,0,0,0,0,0]];
const PAGE_MAX = [[12000,100,100,100,2000,3000,100,3000],[8,100,50,100,100,100,100,100],[2000,3000,100,3000,100,100,500,100],[100,100,800,100,100,100,100,100]];
const THEMES = {
  night:  { name:"Night",   bg:"#0a1a1d", panel:"#0d2428", card:"#0e2024", line:"#1e3a3f", text:"#d7ecef", muted:"#7fb6bc", accent:"#4fd1e0", green:"#38c172", orange:"#f6993f", blue:"#4aa3ff", red:"#ff5c5c", purple:"#b07cff" },
  amber:  { name:"Amber",   bg:"#0e0b08", panel:"#1a130c", card:"#1f1710", line:"#3a2a16", text:"#f2e6d2", muted:"#b99b74", accent:"#ffb347", green:"#7fbf5f", orange:"#f08a24", blue:"#5fa8d3", red:"#e5544b", purple:"#c9a0dc" },
  green:  { name:"Phosphor",bg:"#0a140c", panel:"#102016", card:"#12261a", line:"#23402c", text:"#d8f5dc", muted:"#7fbf92", accent:"#5cff8a", green:"#38c172", orange:"#c9d96b", blue:"#6fd3c0", red:"#ff6b5c", purple:"#9ccf7a" },
  cream:  { name:"Cream",   bg:"#e8e2d4", panel:"#dcd4c4", card:"#f2ede2", line:"#b9ae9a", text:"#2a241c", muted:"#6e6253", accent:"#c8452c", green:"#4f8a3d", orange:"#d97724", blue:"#3d6e8f", red:"#b0301f", purple:"#8a5a9e" },
};
const PART_NAMES = ["FAT SAW", "FM BELL", "POLY VOX", "LADDER LEAD"];
const SCALES = [[0,0,7,12,3,10,5,7],[0,12,7,16,19,24,14,21],[0,7,12,16,19,21,24,28],[0,2,5,7,12,14,17,19]];
const JACKS = ["CV OUT 1","CV OUT 2","CV OUT 3","CV OUT 4","CV IN 1","CV IN 2","GATE OUT","GATE IN","CLK OUT","CLK IN"];
const CC_BASE = [[74,71,73,91,73,75,76,72],[20,21,22,23,24,25,26,27],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]];

const state = { mode:0, page:0, theme:"night", faderMode:"TRACK", bpm:120, playing:false, step:0, selPart:0, volume:0.7, delayMix:0.25, cables:new Set(), parts:[], capture:false, pads:[], recording:false, recStarted:0 };
function defaultPart(i) {
  return {
    name: PART_NAMES[i], active: i < 2, mute:false, level: 0.85, sceneX: 0,
    root: [48,72,60,55][i],
    steps: Array.from({length:16},(_,s)=>({on:s%4===0||(s%7===3), note:SCALES[i][s%8], accent:s%4===0})),
    pages: [
      [3200-i*700, 20+i*15, 40, 15, 10+i*15, 240+i*80, 60, 420],
      [[2,3,1.5,4][i], 55-i*8, 6, 40, 30, 10, 0, 25],
      [10+i*15, 240+i*80, 60, 420, 30, 60, 0, 20],
      [25, 30, 280, 10, 0, 50, 15, 70],
    ],
  };
}
state.parts = [0,1,2,3].map(defaultPart);
let T = THEMES[state.theme];
const COLOR = [T.green, T.orange, T.blue, T.purple];
const undoStack = [];

/* ---------- helpers ---------- */
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function partColor(i){ return [T.green,T.orange,T.blue,T.purple][i]; }
function roundRect(x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}
function pmin(page,i){ return PAGE_MIN[page][i]; }
function pmax(page,i){ return PAGE_MAX[page][i]; }
function pval(){ return state.parts[state.selPart].pages[state.page]; }
function snapshot(){ try { undoStack.push(JSON.stringify(state.parts)); if (undoStack.length>30) undoStack.shift(); } catch(e){} }
function undo(){ const s=undoStack.pop(); if(!s) return; try { state.parts=JSON.parse(s); paintKnobs(); save(); flashMsg("undo"); } catch(e){} }

/* ---------- audio ---------- */
let AC=null, master, comp, delay, delayGain, analyser, masterData, recNode=null;
function audioInit(){
  if (AC) return;
  AC = new (window.AudioContext||window.webkitAudioContext)();
  master=AC.createGain(); master.gain.value=state.volume;
  comp=AC.createDynamicsCompressor(); comp.threshold.value=-12; comp.knee.value=12; comp.ratio.value=6;
  delay=AC.createDelay(1.2); delay.delayTime.value=0.28;
  const fb=AC.createGain(); fb.gain.value=0.32;
  delayGain=AC.createGain(); delayGain.gain.value=state.delayMix;
  analyser=AC.createAnalyser(); analyser.fftSize=512; masterData=new Uint8Array(analyser.fftSize);
  master.connect(comp); comp.connect(AC.destination); comp.connect(analyser);
  // запись выхода: ScriptProcessor-тап (без аллокаций в реальном железе — здесь для демо)
  recNode = AC.createScriptProcessor(4096, 2, 2);
  const silent = AC.createGain(); silent.gain.value = 0;
  comp.connect(recNode); recNode.connect(silent); silent.connect(AC.destination);
  recNode.onaudioprocess = (ev) => {
    if (!state.recording) return;
    const l = ev.inputBuffer.getChannelData(0), r = ev.inputBuffer.getChannelData(1);
    recChunks.push([new Float32Array(l), new Float32Array(r)]);
    if (AC.currentTime - state.recStarted > 30) finishRec();
  };
  master.connect(delay); delay.connect(fb); fb.connect(delay); delay.connect(delayGain); delayGain.connect(comp);
}
const mtof=(m)=>440*Math.pow(2,(m-69)/12);
const voices=[];
let recChunks=[];
function noteOn(midi, vel=0.8, part=state.parts[state.selPart]){
  audioInit(); if (AC.state==="suspended") AC.resume();
  const now=AC.currentTime;
  const m=part.pages[0], f=part.pages[1], e=part.pages[2], x=part.pages[3];
  vel = vel * (part.level != null ? part.level : 1);
  const v={midi, part, vel, dead:false,
    carrier:AC.createOscillator(), mod:AC.createOscillator(), modGain:AC.createGain(),
    amp:AC.createGain(), filt:AC.createBiquadFilter()};
  const cutoff=clamp(m[0],80,12000), q=clamp(m[1],0,100), drive=(clamp(m[3],0,100)+clamp(x[3],0,100))/200;
  const ratio=clamp(f[0],1,8), depth=f[1]/100, detune=f[2]/100;
  v.carrier.frequency.value=mtof(midi)*(1+detune*0.02);
  v.mod.frequency.value=mtof(midi)*ratio;
  v.modGain.gain.value=mtof(midi)*(0.4+depth*3);
  v.mod.connect(v.modGain); v.modGain.connect(v.carrier.frequency);
  v.filt.type="lowpass"; v.filt.frequency.value=cutoff; v.filt.Q.value=q/12;
  v.carrier.connect(v.filt); v.filt.connect(v.amp); v.amp.connect(master);
  const atk=Math.max(0.002,e[0]/1000), dec=Math.max(0.02,e[1]/1000), sus=clamp(e[2]/100,0,1), rel=Math.max(0.02,e[3]/1000);
  v.amp.gain.setValueAtTime(0,now);
  v.amp.gain.linearRampToValueAtTime(vel*0.9,now+atk);
  v.amp.gain.linearRampToValueAtTime(vel*0.9*(0.25+sus*0.75),now+atk+dec);
  v.carrier.start(now); v.mod.start(now); voices.push(v);
  if (voices.length>24) killVoice(voices.shift());
  return v;
}
function killVoice(v, rel=null){
  if(!v||v.dead) return;
  v.dead=true; audioInit();
  const now=AC.currentTime, r=rel ?? Math.max(0.02, v.part.pages[2][3]/1000);
  try{ v.amp.gain.cancelScheduledValues(now); v.amp.gain.setValueAtTime(Math.max(0.0001,v.amp.gain.value),now); v.amp.gain.exponentialRampToValueAtTime(0.0001,now+r); v.carrier.stop(now+r+0.05); v.mod.stop(now+r+0.05);}catch(e){try{v.carrier.stop();v.mod.stop();}catch(e2){}}
}
function noteOff(midi){ voices.filter(v=>v.midi===midi&&!v.dead).forEach(v=>killVoice(v)); }
function allNotesOff(){ voices.forEach(v=>killVoice(v)); }

/* ---------- запись выхода (ресемплинг) ---------- */
function toggleRec(){ audioInit(); if (AC.state==="suspended") AC.resume(); if(state.recording){ finishRec(); } else { recChunks=[]; state.recording=true; state.recStarted=AC.currentTime; flashMsg("REC ●"); } }
function finishRec(){
  if(!state.recording) return;
  state.recording=false;
  let len=0; for(const c of recChunks) len+=c[0].length;
  if(len<2048){ flashMsg("REC: слишком коротко"); return; }
  const buf=AC.createBuffer(2, len, AC.sampleRate);
  const L=buf.getChannelData(0), R=buf.getChannelData(1);
  let off=0; for(const [l,r] of recChunks){ L.set(l,off); R.set(r,off); off+=l.length; }
  const n=state.pads.length+1;
  state.pads.push({name:`REC ${String(n).padStart(2,"0")}`, buffer:buf, loop:false});
  recChunks=[];
  flashMsg(`REC → PAD ${state.pads.length} (${(len/AC.sampleRate).toFixed(1)} с)`);
  save();
}
function playPad(i){
  const pad=state.pads[i]; if(!pad||!AC) return;
  const src=AC.createBufferSource(); src.buffer=pad.buffer; src.loop=!!pad.loop;
  const g=AC.createGain(); g.gain.value=0.9;
  src.connect(g); g.connect(master); src.start();
  pad._src=src;
}
function stopAllPads(){ state.pads.forEach(p=>{ try{ p._src && p._src.stop(); }catch(e){} p._src=null; }); }

/* ---------- sequencer ---------- */
let seqTimer=null, nextStepTime=0, lookahead=0.1;
const stepDur=()=>60/state.bpm/4;
function startSeq(){ audioInit(); if(AC.state==="suspended")AC.resume(); state.playing=true; nextStepTime=AC.currentTime+0.05; state.step=0; if(seqTimer)clearInterval(seqTimer); seqTimer=setInterval(scheduler,25); save(); }
function stopSeq(){ state.playing=false; if(seqTimer){clearInterval(seqTimer);seqTimer=null;} voices.forEach(v=>killVoice(v,0.08)); save(); }
function scheduler(){ if(!state.playing) return; while(nextStepTime<AC.currentTime+lookahead){ scheduleStep(state.step,nextStepTime); nextStepTime+=stepDur(); state.step=(state.step+1)%16; } }
function scheduleStep(step,when){
  for (const part of state.parts){
    if(!part.active||part.mute) continue;
    const s=part.steps[step]; if(!s.on) continue;
    const dt=Math.max(0,(when-AC.currentTime)*1000);
    setTimeout(()=>{ noteOn(part.root+s.note, s.accent?1:0.65, part); },dt);
  }
}

/* ---------- MIDI ---------- */
let midiAccess=null, midiOut=null;
function sendCC(cc,val){ if(midiOut){ try{ midiOut.send([0xB0,cc,clamp(Math.round(val),0,127)]); }catch(e){} } }
function midiInit(){
  if(!navigator.requestMIDIAccess) return;
  navigator.requestMIDIAccess({sysex:false}).then((access)=>{
    midiAccess=access;
    const bind=()=>{
      const inputs=[...access.inputs.values()], outputs=[...access.outputs.values()];
      midiOut=outputs[0]||null;
      $("midiState").textContent = (inputs.length?`MIDI: ${inputs.map(i=>i.name).join(", ").slice(0,26)}`:"MIDI: нет входов") + (midiOut?" · OUT OK":"");
      inputs.forEach(input=>{ input.onmidimessage=onMidi; });
    };
    bind(); access.onstatechange=bind;
  }).catch(()=>{ $("midiState").textContent="MIDI: нет доступа"; });
}
function onMidi(msg){
  const [st,d1,d2]=msg.data, cmd=st&0xf0;
  if(cmd===0x90&&d2>0){ noteOn(d1,d2/127); markKey(d1,true); }
  else if(cmd===0x80||(cmd===0x90&&d2===0)){ noteOff(d1); markKey(d1,false); }
  else if(cmd===0xB0){ // CC из внешнего мира двигает текущую страницу
    const idx=CC_BASE[state.page].indexOf(d1);
    if(idx>=0){ const p=pval(); p[idx]=pmin(state.page,idx)+(d2/127)*(pmax(state.page,idx)-pmin(state.page,idx)); paintKnobs(); }
  }
}

/* ---------- keyboard ---------- */
const QWERTY=["KeyA","KeyW","KeyS","KeyE","KeyD","KeyF","KeyT","KeyG","KeyY","KeyH","KeyU","KeyJ","KeyK","KeyO","KeyL","KeyP","Semicolon"];
const pressed=new Map(), keyEls=new Map();
function buildKeys(){
  // Два кластера 3×7 = 42 клавиши, как на реальной панели Lapka-42: левый −18°, правый +18°.
  const CLUSTERS = {
    keysLeft:  { rot:-18, base:48, rows:[["Й","Ц","У","К","Е","Н","Г"],["Ф","Ы","В","А","П","Р","О"],["Я","Ч","С","М","И","Т","Ь"]] },
    keysRight: { rot:18,  base:69, rows:[["Ш","Щ","З","Х","Ъ","Ж","Э"],["Л","Д","Ж","Э","Ю","Б","⇧"],["Ё",",",".","/","⏎","⏫","⌫"]] },
  };
  for (const side of ["keysLeft","keysRight"]){
    const cfg=CLUSTERS[side], host=$(side);
    host.innerHTML=""; host.className="cluster"+(side==="keysRight"?" right":" left");
    host.style.setProperty("--rot",cfg.rot+"deg");
    let idx=0;
    cfg.rows.forEach((row,ri)=>{
      const r=document.createElement("div"); r.className="krow";
      row.forEach((label,ci)=>{
        const midi=cfg.base+idx; idx++;
        const b=document.createElement("button"); b.className="glabel";
        b.innerHTML=`<b>${label}</b><i>${noteName(midi)}</i>`;
        b.dataset.midi=midi;
        bindKey(b,midi); r.appendChild(b); keyEls.set(midi,b);
      });
      host.appendChild(r);
    });
  }
}
function bindKey(b,midi){
  b.addEventListener("pointerdown",(e)=>{e.preventDefault();noteOn(midi,0.85);markKey(midi,true);b.setPointerCapture(e.pointerId);});
  b.addEventListener("pointerup",()=>{noteOff(midi);markKey(midi,false);});
  b.addEventListener("pointerleave",()=>{noteOff(midi);markKey(midi,false);});
}
const noteName=(m)=>{const n=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];return n[m%12]+(Math.floor(m/12)-1);};
function markKey(midi,on){ const el=keyEls.get(midi); if(el) el.classList.toggle("on",on); }
addEventListener("keydown",(e)=>{
  if(e.repeat) return;
  const n=QWERTY.indexOf(e.code);
  if(n>=0 && !e.metaKey && !e.ctrlKey){ const midi=48+n; noteOn(midi,0.8); pressed.set(e.code,midi); markKey(midi,true); e.preventDefault(); }
  if(e.code==="Space"){ state.playing?stopSeq():startSeq(); e.preventDefault(); }
  if(e.code==="KeyR" && !e.metaKey && !e.ctrlKey){ toggleRec(); e.preventDefault(); }
  if(["Digit1","Digit2","Digit3","Digit4"].includes(e.code)){ playPad(+e.code.slice(-1)-1); e.preventDefault(); }
  if((e.metaKey||e.ctrlKey) && e.code==="KeyZ"){ undo(); e.preventDefault(); }
  if((e.metaKey||e.ctrlKey) && e.code==="KeyC"){ copyPattern(); e.preventDefault(); }
  if((e.metaKey||e.ctrlKey) && e.code==="KeyV"){ pastePattern(); e.preventDefault(); }
});
addEventListener("keyup",(e)=>{ const n=pressed.get(e.code); if(n!=null){noteOff(n);markKey(n,false);pressed.delete(e.code);} });

/* ---------- knobs/faders/jacks ---------- */
const knobEls=[], macroEls=[];
const MACRO = [
  { key:"cut",  label:"CUT",  get:()=>state.parts[state.selPart].pages[0][0], set:(v)=>state.parts[state.selPart].pages[0][0]=v, min:80, max:12000 },
  { key:"res",  label:"RES",  get:()=>state.parts[state.selPart].pages[0][1], set:(v)=>state.parts[state.selPart].pages[0][1]=v, min:0, max:100 },
  { key:"atk",  label:"ATK",  get:()=>state.parts[state.selPart].pages[2][0], set:(v)=>state.parts[state.selPart].pages[2][0]=v, min:1, max:2000 },
  { key:"rel",  label:"REL",  get:()=>state.parts[state.selPart].pages[2][3], set:(v)=>state.parts[state.selPart].pages[2][3]=v, min:20, max:3000 },
  { key:"dly",  label:"DLY",  get:()=>state.parts[state.selPart].pages[3][0], set:(v)=>state.parts[state.selPart].pages[3][0]=v, min:0, max:100 },
  { key:"drv",  label:"DRV",  get:()=>state.parts[state.selPart].pages[0][3], set:(v)=>state.parts[state.selPart].pages[0][3]=v, min:0, max:100 },
  { key:"crsh", label:"CRSH", get:()=>state.parts[state.selPart].pages[3][4], set:(v)=>state.parts[state.selPart].pages[3][4]=v, min:0, max:100 },
  { key:"mst",  label:"MST",  get:()=>state.volume*100, set:(v)=>{ state.volume=v/100; if(master) master.gain.value=state.volume; }, min:0, max:100 },
];
function makeKnob(host, i, opts){
  const wrap=document.createElement("div"); wrap.className="k";
  const k=document.createElement("div"); k.className="knob"; k.dataset.i=i;
  const label=document.createElement("span"); label.textContent="—";
  wrap.appendChild(k); wrap.appendChild(label); host.appendChild(wrap);
  let startY=null,startVal=0;
  const down=(e)=>{ e.preventDefault(); audioInit(); snapshot(); startY=e.clientY; startVal=opts.get(); k.setPointerCapture(e.pointerId); };
  const move=(e)=>{ if(startY==null) return; const range=opts.max-opts.min; const val=clamp(startVal+(startY-e.clientY)/120*range,opts.min,opts.max);
    opts.set(val); paintKnobs(); save(); if(opts.onChange) opts.onChange(); };
  const up=()=>{ startY=null; };
  k.addEventListener("pointerdown",down); k.addEventListener("pointermove",move); k.addEventListener("pointerup",up); k.addEventListener("pointercancel",up);
  return k;
}
function buildKnobs(){
  const host=$("knobs"); host.innerHTML=""; knobEls.length=0;
  const letters=["А","Б","В","Г","Д","Е","Ж","З"];
  for(let i=0;i<8;i++){
    const k=makeKnob(host,i,{ get:()=>pval()[i], set:(v)=>{ pval()[i]=v; if(state.page===3) applyFx(); }, min:0, max:1, onChange:null });
    k.parentElement.dataset.letter=letters[i];
    knobEls.push(k);
  }
  const host2=$("knobsMacro"); if(host2){ host2.innerHTML=""; macroEls.length=0;
    const letters2=["И","Й","К","Л","М","Н","О","П"];
    for(let i=0;i<8;i++){
      const m=MACRO[i];
      const k=makeKnob(host2,i,{ get:()=>m.get(), set:(v)=>{ m.set(v); if(m.key==="dly"&&AC) delayGain.gain.value=clamp(m.get()/100,0,1); }, min:m.min, max:m.max });
      k.parentElement.dataset.letter=letters2[i];
      macroEls.push(k);
    }
  }
}
function paintKnobs(){
  const p=pval(), page=state.page;
  const names=["CUT","RES","ENV","DRV","ATK","DEC","SUS","REL"];
  knobEls.forEach((k,i)=>{
    const frac=(p[i]-pmin(page,i))/(pmax(page,i)-pmin(page,i));
    k.style.setProperty("--a",(frac*260-130).toFixed(1)+"deg");
    const lab=k.parentElement.querySelector("span");
    if(lab) lab.textContent=(k.parentElement.dataset.letter?k.parentElement.dataset.letter+" · ":"") + (PAGE_PARAMS[page][i]||"");
  });
  macroEls.forEach((k,i)=>{
    const m=MACRO[i], frac=(m.get()-m.min)/(m.max-m.min);
    k.style.setProperty("--a",(frac*260-130).toFixed(1)+"deg");
    const lab=k.parentElement.querySelector("span");
    if(lab) lab.textContent=(k.parentElement.dataset.letter?k.parentElement.dataset.letter+" · ":"") + m.label;
  });
}
function applyFx(){
  const p=state.parts[state.selPart].pages[3];
  if(!AC) return;
  delay.delayTime.value=clamp(p[2]/1000,0.02,1);
}
/* ---------- фейдеры: режимы ---------- */
function sceneTargets(){ return state.parts[state.selPart]; }
function applyScene(x){
  const part=state.parts[state.selPart];
  const A=part.sceneA, B=part.sceneB; if(!A||!B) return;
  const p0=part.pages[0], p2=part.pages[2], p1=part.pages[1];
  const keys=[["p0",0],["p0",1],["p0",3],["p2",0],["p2",1],["p2",3],["p1",1],["p1",5]];
  const valsA=[A.cut,A.res,A.drive,A.atk,A.dec,A.rel,A.depth,A.fbk];
  const valsB=[B.cut,B.res,B.drive,B.atk,B.dec,B.rel,B.depth,B.fbk];
  keys.forEach(([page,idx],k)=>{ const v=valsA[k]+(valsB[k]-valsA[k])*x; if(page==="p0")p0[idx]=v; else if(page==="p2")p2[idx]=v; else p1[idx]=v; });
  part.sceneX=x; paintKnobs(); save();
}
function ensureScenes(part){
  if(!part.sceneA){
    const p0=part.pages[0];
    part.sceneA={cut:p0[0],res:p0[1],drive:p0[3],atk:part.pages[2][0],dec:part.pages[2][1],rel:part.pages[2][3],depth:part.pages[1][1],fbk:part.pages[3][1]};
    part.sceneB={cut:Math.min(12000,p0[0]*2.2),res:Math.min(100,p0[1]+35),drive:Math.min(100,p0[3]+30),atk:Math.max(2,part.pages[2][0]*0.5),dec:Math.max(30,part.pages[2][1]*0.7),rel:Math.max(40,part.pages[2][3]*0.7),depth:Math.min(100,part.pages[1][1]+30),fbk:Math.min(100,part.pages[3][1]+25)};
  }
}
function setFaderMode(m){
  state.faderMode=m;
  document.querySelectorAll("[data-fmode]").forEach(b=>b.classList.toggle("active",b.dataset.fmode===m));
  paintFaderLabels(); save(); flashMsg("фейдеры: "+m);
}
function paintFaderLabels(){
  const f0=document.querySelector('[data-fader="0"] span'), f1=document.querySelector('[data-fader="1"] span');
  const L={TRACK:["PART LEVEL","MASTER"],SCENE:["SCENE A ↔ B","MASTER"],DJ:["DECK A","DECK B"]}[state.faderMode]||["FADER 1","FADER 2"];
  if(f0) f0.textContent=L[0]; if(f1) f1.textContent=L[1];
}
function buildFaders(){
  document.querySelectorAll(".fader").forEach(f=>{
    let startY=null,startVal=0;
    const currentVal=()=>{
      if(state.faderMode==="TRACK") return f.dataset.fader==="0"?state.parts[state.selPart].level:state.volume;
      if(state.faderMode==="SCENE") return f.dataset.fader==="0"?state.parts[state.selPart].sceneX||0:state.volume;
      if(state.faderMode==="DJ") return f.dataset.fader==="0"?state.parts[0].level:state.parts[2].level;
      return state.volume;
    };
    const down=(e)=>{e.preventDefault();audioInit();startY=e.clientY;startVal=currentVal();if(state.faderMode==="SCENE")ensureScenes(state.parts[state.selPart]);f.setPointerCapture(e.pointerId);};
    const move=(e)=>{ if(startY==null)return; const dy=startY-e.clientY, val=clamp(startVal+dy/140,0,1);
      const isShift=e.shiftKey;
      if(isShift){ state.volume=val; if(master)master.gain.value=val; }
      else if(state.faderMode==="TRACK"){ if(f.dataset.fader==="0"){state.parts[state.selPart].level=val;} else {state.volume=val; if(master)master.gain.value=val;} }
      else if(state.faderMode==="SCENE"){ if(f.dataset.fader==="0"){ applyScene(val); } else {state.volume=val; if(master)master.gain.value=val;} }
      else if(state.faderMode==="DJ"){ if(f.dataset.fader==="0"){ state.parts[0].level=val; state.parts[1].level=val; } else { state.parts[2].level=val; state.parts[3].level=val; } }
      f.style.setProperty("--top",((1-val)*100).toFixed(1)+"%"); paintFaderLabels(); save();};
    const up=()=>{startY=null;};
    f.addEventListener("pointerdown",down);f.addEventListener("pointermove",move);f.addEventListener("pointerup",up);f.addEventListener("pointercancel",up);
    const v=f.dataset.fader==="0"?state.volume:state.delayMix;
    f.style.setProperty("--top",((1-v)*100).toFixed(1)+"%");
  });
}
function buildJacks(){
  const host=$("jacks"); host.innerHTML="";
  JACKS.forEach((name,i)=>{
    const d=document.createElement("div"); d.className="jack"; d.dataset.i=i;
    d.innerHTML=`<i></i><span>${name}</span>`;
    d.addEventListener("click",()=>{ state.cables.has(i)?state.cables.delete(i):state.cables.add(i); d.classList.toggle("active"); });
    host.appendChild(d);
  });
}

/* ---------- pattern copy/paste ---------- */
let clipboard=null;
function copyPattern(){ clipboard=JSON.stringify(state.parts); flashMsg("паттерн скопирован"); }
function pastePattern(){ if(!clipboard) return; snapshot(); state.parts=JSON.parse(clipboard); paintKnobs(); save(); flashMsg("паттерн вставлен"); }
let msg="", msgT=0, lastPadClick=null;
function flashMsg(t){ msg=t; msgT=Date.now(); }

/* ---------- доп. фишки ---------- */
function randomizePattern(){ snapshot();
  state.parts.forEach((p,pi)=>{ p.steps.forEach((st,si)=>{ const r=Math.random(); st.on=r<0.35; st.accent=st.on&&si%4===0; st.note=SCALES[pi][Math.floor(Math.random()*SCALES[pi].length)]; }); });
  paintKnobs(); save(); flashMsg("случайный паттерн");
}
function transpose(semi){ snapshot(); state.parts.forEach(p=>{ p.steps.forEach(st=>{ st.note=clamp(st.note+semi,-24,48); }); }); save(); flashMsg("транспозиция "+semi); }

/* ---------- themes ---------- */
function setTheme(name){ if(!THEMES[name]) return; state.theme=name; T=THEMES[name]; document.documentElement.style.setProperty("--accent",T.accent); save(); }
function drawThemeSwatches(){
  const names=Object.keys(THEMES);
  names.forEach((n,i)=>{
    const x=700-i*0, y=0; // swatches рисуются внизу справа
  });
}

/* ---------- canvas UI ---------- */
function draw(){
  ctx.clearRect(0,0,W,H); ctx.fillStyle=T.bg; ctx.fillRect(0,0,W,H);
  // header
  ctx.fillStyle=T.panel; ctx.fillRect(0,0,W,44);
  ctx.fillStyle=T.accent; ctx.font="700 24px Inter, system-ui, sans-serif"; ctx.fillText("БУКИФОН",14,30);
  MODES.forEach((m,i)=>{
    const x=196+i*104,y=8;
    ctx.fillStyle=i===state.mode?T.accent:T.card; roundRect(x,y,96,22,5); ctx.fill();
    ctx.fillStyle=i===state.mode?"#04140b":T.muted; ctx.font="700 11px Inter"; ctx.textAlign="center"; ctx.fillText(m,x+48,y+15); ctx.textAlign="left";
  });
  // info
  const info=[["BPM",String(state.bpm)],["STEP",String(state.step).padStart(2,"0")],["PAGE",PAGES[state.page]],["THEME",T.name]];
  info.forEach(([k,v],i)=>{ ctx.fillStyle=T.muted; ctx.font="600 10px Inter"; ctx.fillText(k,20+i*70,62); ctx.fillStyle=T.text; ctx.font="700 14px Inter"; ctx.fillText(v,20+i*70,78); });
  if(state.playing){ ctx.fillStyle=T.green; ctx.fillRect(300,58,8,8); ctx.fillStyle=T.muted; ctx.font="600 10px Inter"; ctx.fillText("PLAY",312,66); }
  if(state.recording){ const a=0.5+0.5*Math.sin(Date.now()/180); ctx.fillStyle=`rgba(255,92,92,${a.toFixed(2)})`; ctx.beginPath(); ctx.arc(372,62,6,0,Math.PI*2); ctx.fill(); ctx.fillStyle=T.red; ctx.font="700 10px Inter"; ctx.fillText("REC",384,66); }

  if(state.mode===0) drawSynth();
  else if(state.mode===1) drawSampler();
  else if(state.mode===2) drawDaw();
  else drawUsbKbd();
  drawStatusBar();
  if(msg && Date.now()-msgT<1600){ ctx.fillStyle=T.accent; ctx.font="700 12px Inter"; ctx.fillText(msg,W-220,462); }
}
function drawStatusBar(){
  const lvl=analyser?analyseLevel():0;
  ctx.fillStyle=T.panel; ctx.fillRect(0,444,W,36);
  ctx.fillStyle=T.muted; ctx.font="600 10px Inter"; ctx.fillText("MASTER",14,466);
  ctx.fillStyle=T.line; ctx.fillRect(70,456,220,10);
  ctx.fillStyle=T.green; ctx.fillRect(70,456,220*clamp(lvl,0,1),10);
  ctx.fillStyle=T.muted; ctx.font="600 10px Inter"; ctx.fillText(`FADERS: ${state.faderMode} · SHIFT+ФЕЙДЕР = ГРОМКОСТЬ · SPACE = PLAY · Ctrl+Z = UNDO`,306,466);
}
function drawSynth(){
  const top=96, rowH=66;
  for(let pi=0;pi<4;pi++){
    const part=state.parts[pi], y=top+pi*rowH, color=partColor(pi);
    ctx.fillStyle=T.card; roundRect(8,y,W-16,rowH-6,6); ctx.fill();
    if(pi===state.selPart){ ctx.strokeStyle=T.accent; ctx.lineWidth=1.5; roundRect(8,y,W-16,rowH-6,6); ctx.stroke(); }
    ctx.fillStyle=color; ctx.font="700 12px Inter"; ctx.fillText(`PART ${pi+1}`,18,y+18);
    ctx.fillStyle=part.mute?T.red:T.muted; ctx.font="600 10px Inter";
    ctx.fillText(part.name+(part.mute?" · MUTE":"")+(part.active?"":" · OFF"),18,y+34);
    ctx.fillStyle=color; ctx.fillRect(18,y+42,70*clamp(part.pages[0][0]/12000,0,1),4);
    for(let s=0;s<16;s++){
      const x=128+s*40, sy=y+12, sw=36, sh=rowH-44, st=part.steps[s];
      ctx.fillStyle=state.playing&&state.step===s?T.line:T.bg; roundRect(x,sy,sw,sh,4); ctx.fill();
      if(st.on){ ctx.fillStyle=st.accent?T.orange:(s%4===0?color:T.green); roundRect(x+2,sy+2,sw-4,sh-4,3); ctx.fill(); }
      if(state.playing&&state.step===s){ ctx.strokeStyle=T.accent; ctx.lineWidth=2; roundRect(x-1,sy-1,sw+2,sh+2,5); ctx.stroke(); }
      ctx.fillStyle=T.muted; ctx.font="9px Inter"; ctx.fillText(String(s+1),x+2,sy-3);
    }
  }
  // page tabs
  PAGES.forEach((pg,i)=>{
    const x=18+i*92,y=372;
    ctx.fillStyle=i===state.page?T.accent:T.line; roundRect(x,y,84,18,4); ctx.fill();
    ctx.fillStyle=i===state.page?"#04140b":T.muted; ctx.font="700 10px Inter"; ctx.textAlign="center"; ctx.fillText(pg,x+42,y+13); ctx.textAlign="left";
  });
  // params
  const p=pval();
  for(let i=0;i<8;i++){
    const x=18+i*97, y=400;
    ctx.fillStyle=T.muted; ctx.font="600 9px Inter"; ctx.fillText(PAGE_PARAMS[state.page][i],x,y+10);
    ctx.fillStyle=T.line; ctx.fillRect(x,y+16,86,5);
    ctx.fillStyle=T.accent; ctx.fillRect(x,y+16,86*clamp((p[i]-pmin(state.page,i))/(pmax(state.page,i)-pmin(state.page,i)),0,1),5);
    ctx.fillStyle=T.text; ctx.font="700 11px Inter"; ctx.fillText(fmtParam(state.page,i,p[i]),x,y+40);
    ctx.fillStyle=T.line; ctx.font="600 8px Inter"; ctx.fillText(`E${i+1}`,x+70,y+40);
  }
  // theme switcher (small swatches bottom-right)
  const names=Object.keys(THEMES);
  names.forEach((n,i)=>{
    const x=690-i*0, y=0;
  });
  Object.keys(THEMES).forEach((n,i)=>{
    const x=W-18-18-i*22, y=404;
    ctx.beginPath(); ctx.arc(x,y,8,0,Math.PI*2); ctx.fillStyle=THEMES[n].bg; ctx.fill();
    ctx.strokeStyle=n===state.theme?T.accent:T.line; ctx.lineWidth=n===state.theme?2:1; ctx.stroke();
  });
}
function fmtParam(page,i,v){
  if(state.page===0&&i===0) return v>=1000?(v/1000).toFixed(1)+" кГц":Math.round(v)+" Гц";
  if((state.page===0&&(i===4||i===5||i===7))||(state.page===2&&(i===0||i===1||i===3))) return Math.round(v)+" мс";
  if(state.page===3&&i===2) return Math.round(v)+" мс";
  if(state.page===3&&i===0) return Math.round(v)+"%";
  return Math.round(v);
}
function drawSampler(){
  ctx.fillStyle=T.accent; ctx.font="700 16px Inter"; ctx.fillText("SAMPLER · SD + RESAMPLE",20,110);
  const recTxt = state.recording ? `● REC ${(AC? (AC.currentTime-state.recStarted):0).toFixed(1)} с / 30 с` : "REC — кнопка или клавиша R: запись выхода, затем PAD";
  ctx.fillStyle = state.recording ? T.red : T.muted; ctx.font="600 11px Inter"; ctx.fillText(recTxt, 20, 132);
  const pads = state.pads.length ? state.pads.slice(0,4) : [];
  for(let i=0;i<4;i++){
    const x=18+i*192, y=148, w=180, h=150;
    ctx.fillStyle=T.card; roundRect(x,y,w,h,6); ctx.fill();
    if(i===state.selPart%4){ ctx.strokeStyle=T.accent; ctx.lineWidth=1.5; roundRect(x,y,w,h,6); ctx.stroke(); }
    const pad=pads[i];
    ctx.fillStyle=pad?T.text:T.muted; ctx.font="700 14px Inter";
    ctx.fillText(pad?pad.name:`PAD ${i+1}`,x+12,y+24);
    ctx.fillStyle=T.muted; ctx.font="600 10px Inter";
    ctx.fillText(pad?(pad.loop?"LOOP":"ONE-SHOT"):"пусто · запиши REC",x+12,y+40);
    if(pad){
      const data=pad.buffer.getChannelData(0), step=Math.max(1,Math.floor(data.length/w));
      ctx.fillStyle=T.line; ctx.fillRect(x+12,y+52,w-24,70);
      for(let px=0;px<w-24;px++){
        let peak=0; for(let k=0;k<step;k+=8){ const v=Math.abs(data[px*step+k]||0); if(v>peak)peak=v; }
        const hh=Math.min(1,peak*1.5)*(70/2);
        ctx.fillStyle=T.accent; ctx.fillRect(x+12+px, y+52+35-hh, 1, hh*2);
      }
      ctx.fillStyle=T.muted; ctx.font="10px Inter"; ctx.fillText((pad.buffer.duration).toFixed(2)+" с",x+12,y+138);
    } else {
      ctx.fillStyle=T.line; ctx.fillRect(x+12,y+52,w-24,70);
    }
  }
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText("клик по пэду = играть · двойной клик = LOOP · R = REC · клавиши 1–4 = пэды",20,330);
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText("записанный сэмпл можно сразу играть/зациклить и сохранить на SD (в демо — в памяти)",20,352);
}
function drawDaw(){
  ctx.fillStyle=T.accent; ctx.font="700 16px Inter"; ctx.fillText("DAW · USB HID + MIDI",20,110);
  [["CC 16-31","CUTOFF 74","RESO 71","DRIVE 91","ATK 73"],["CC 32-47","DEC 75","SUS 76","REL 72","PAN 10"]].forEach((bank,bi)=>{
    ctx.fillStyle=T.card; roundRect(14,126+bi*110,W-28,96,6); ctx.fill();
    ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText(bank[0],26,148+bi*110);
    for(let i=0;i<16;i++){
      const x=120+i*40,y=158+bi*110; ctx.fillStyle=i<4?T.blue:T.line; roundRect(x,y,34,38,4); ctx.fill();
      ctx.fillStyle=i<4?"#04140b":T.muted; ctx.font="700 10px Inter"; ctx.fillText(String(i+16+bi*16),x+5,y+15);
      ctx.font="8px Inter"; ctx.fillText(i<4?bank[1+i].split(" ")[0]:"",x+2,y+30);
    }
  });
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter"; ctx.fillText("Транспорт: PLAY / STOP · 16 энкодеров = CC · Web MIDI in/out",20,390);
}
function drawUsbKbd(){
  ctx.fillStyle=T.accent; ctx.font="700 16px Inter"; ctx.fillText("USB-KEYBOARD · HID",20,110);
  ctx.fillStyle=T.card; roundRect(14,126,W-28,180,6); ctx.fill();
  ["q w e r t y u i o p","a s d f g h j k l ;","z x c v b n m , . /"].forEach((r,i)=>{ ctx.fillStyle=T.text; ctx.font="600 18px ui-monospace, monospace"; ctx.fillText(r,34,170+i*46); });
  ctx.fillStyle=T.muted; ctx.font="600 11px Inter";
  ctx.fillText("42 клавиши = 42 клавиши HID; слои BASE / SHIFT / SYMBOLS; LAYER переключается энкодером E8.",20,340);
}
function analyseLevel(){ if(!analyser) return 0; analyser.getByteTimeDomainData(masterData); let s=0; for(let i=0;i<masterData.length;i++){const v=(masterData[i]-128)/128;s+=v*v;} return Math.sqrt(s/masterData.length); }

/* ---------- canvas hit testing ---------- */
function canvasPos(e){ const r=cv.getBoundingClientRect(); return {x:(e.clientX-r.left)*(W/r.width), y:(e.clientY-r.top)*(H/r.height)}; }
cv.addEventListener("pointerdown",(e)=>{
  const {x,y}=canvasPos(e);
  if(y<44){ const i=Math.floor((x-196)/104); if(i>=0&&i<4){ state.mode=i; save(); } return; }
  if(state.mode===1){
    if(y>140&&y<310&&x>18&&x<786){ const i=Math.floor((x-18)/192); if(i>=0&&i<4){ lastPadClick = lastPadClick && (Date.now()-lastPadClick.t<350) && lastPadClick.i===i ? {i,t:Date.now(),dbl:true} : {i,t:Date.now(),dbl:false};
        if(lastPadClick.dbl){ if(state.pads[i]) state.pads[i].loop=!state.pads[i].loop; } else playPad(i); } }
    return;
  }
  if(state.mode!==0) return;
  // смена темы — правый нижний угол
  if(y>392&&y<416&&x>640){ const names=Object.keys(THEMES); const idx=Math.round((W-18-x)/22); const n=names[idx]; if(n) setTheme(n); return; }
  const pi=Math.floor((y-96)/66);
  if(pi<0||pi>3) return;
  // mute по клику на имя партии
  if(x<120){ state.parts[pi].mute=!state.parts[pi].mute; save(); return; }
  if(x>120&&x<776){ const s=Math.floor((x-128)/40); if(s>=0&&s<=15){ snapshot(); const part=state.parts[pi], st=part.steps[s]; st.on=!st.on; if(st.on) st.accent=s%4===0; state.selPart=pi; paintKnobs(); save(); startPreview(part,s); } }
});
function startPreview(part,s){ if(!state.playing){ const n=part.root+part.steps[s].note; noteOn(n,0.8,part); setTimeout(()=>noteOff(n),180); } }

/* ---------- share ---------- */
function encodeState(){
  const compact={b:state.bpm,s:state.selPart,p:state.parts.map(p=>({r:p.root,a:p.active?1:0,m:p.mute?1:0,pg:p.pages.map(pg=>pg.map(x=>Math.round(x))),st:p.steps.map(x=>(x.on?(x.accent?2:1):0)*128+x.note)}))};
  return btoa(JSON.stringify(compact)).replace(/=+$/,"");
}
function decodeState(b64){
  try{ const c=JSON.parse(atob(b64)); if(c.b) state.bpm=clamp(c.b,40,220); if(c.s!=null) state.selPart=clamp(c.s,0,3);
    (c.p||[]).forEach((cp,i)=>{ const p=state.parts[i]; if(!p)return; p.root=cp.r; p.active=!!cp.a; p.mute=!!cp.m;
      if(cp.pg) p.pages=cp.pg;
      (cp.st||[]).forEach((v,s)=>{ const on=Math.floor(v/128)>0; p.steps[s].on=on; p.steps[s].accent=Math.floor(v/128)===2; p.steps[s].note=v%128; });
    }); paintKnobs(); return true; }catch(e){ return false; }
}
function copyShareLink(){ const url=location.origin+location.pathname+"#p="+encodeState(); if(navigator.clipboard) navigator.clipboard.writeText(url).catch(()=>{}); flashMsg("ссылка скопирована"); $("shareState").textContent="ссылка скопирована"; setTimeout(()=>{$("shareState").textContent="";},2000); }
function loadFromHash(){ const m=location.hash.match(/#p=(.+)/); if(m) return decodeState(m[1]); return false; }

/* ---------- storage / init ---------- */
const KEY="bukifon-demo-v2";
function save(){ try{ localStorage.setItem(KEY, JSON.stringify({bpm:state.bpm,volume:state.volume,delayMix:state.delayMix,faderMode:state.faderMode,parts:state.parts,page:state.page,theme:state.theme,mode:state.mode,sel:state.selPart})); }catch(e){} }
function load(){
  try{ const p=JSON.parse(localStorage.getItem(KEY)||"null"); if(!p) return;
    state.bpm=p.bpm??120; state.volume=p.volume??0.7; state.delayMix=p.delayMix??0.25; state.faderMode=p.faderMode||"TRACK";
    state.page=p.page??0; state.theme=p.theme||"night"; state.mode=p.mode??0; state.selPart=p.sel??0;
    if(Array.isArray(p.parts)) p.parts.forEach((x,i)=>{ if(x&&x.pages){ state.parts[i]=x; } });
  }catch(e){}
}
function bindUI(){
  $("btnPlay").addEventListener("click",()=>state.playing?stopSeq():startSeq());
  $("btnStop").addEventListener("click",()=>stopSeq());
  const share=$("btnShare"); if(share) share.addEventListener("click",copyShareLink);
  const recBtn=$("btnRec"); if(recBtn) recBtn.addEventListener("click",toggleRec);
  const rand=$("btnRandom"); if(rand) rand.addEventListener("click",randomizePattern);
  const td=$("btnTransDown"); if(td) td.addEventListener("click",()=>transpose(-12));
  const tu=$("btnTransUp"); if(tu) tu.addEventListener("click",()=>transpose(12));
  const themeSel=$("themeSel");
  if(themeSel){ Object.keys(THEMES).forEach(n=>{ const o=document.createElement("option"); o.value=n; o.textContent=THEMES[n].name; themeSel.appendChild(o); }); themeSel.value=state.theme; themeSel.addEventListener("change",(e)=>setTheme(e.target.value)); }
  $("bpm").value=state.bpm; $("bpm").addEventListener("change",(e)=>{ state.bpm=clamp(+e.target.value||120,40,220); save(); });
  $("volume").value=Math.round(state.volume*100); $("volume").addEventListener("input",(e)=>{ state.volume=+e.target.value/100; if(master)master.gain.value=state.volume; save(); });
  document.querySelectorAll("[data-fmode]").forEach(b=>b.addEventListener("click",()=>setFaderMode(b.dataset.fmode)));
  setFaderMode(state.faderMode); paintFaderLabels();
  document.querySelectorAll(".fader").forEach(f=>{ const v=f.dataset.fader==="0"?state.volume:state.delayMix; f.style.setProperty("--top",((1-v)*100).toFixed(1)+"%"); });
}
load(); if(loadFromHash()) {}
const params = new URLSearchParams(location.search);
if (params.get("theme") && THEMES[params.get("theme")]) state.theme = params.get("theme");
if (params.get("page") != null) state.page = clamp(+params.get("page")||0, 0, 3);
if (params.get("mode") != null) state.mode = clamp(+params.get("mode")||0, 0, 3);
if (params.get("capture") === "1") document.body.classList.add("capture");
setTheme(state.theme); buildKeys(); buildKnobs(); buildFaders(); buildJacks(); bindUI(); paintKnobs(); midiInit();

(function loop(){ draw(); requestAnimationFrame(loop); })();
