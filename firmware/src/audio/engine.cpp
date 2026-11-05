// SPDX-License-Identifier: GPL-3.0-or-later
#include "audio/engine.hpp"

#include <cmath>
#include <cstring>

#include "core/math.hpp"
#include "core/patch.hpp"

namespace bukifon {
namespace {
constexpr float kInv127 = 1.0f / 127.0f;

int globalParamForTarget(uint8_t target) {
  switch (target) {
    case MtFxDelayTime: return FxDelayTime;
    case MtFxDelayFb: return FxDelayFb;
    case MtFxDelayMix: return FxDelayMix;
    case MtFxChorusDepth: return FxChorusDepth;
    case MtFxDrive: return FxDrive;
    case MtFxLimiterThreshold: return FxLimiterThreshold;
    case MtSeqSwing: return SeqSwing;
    case MtSeqTranspose: return SeqTranspose;
    default: return -1;
  }
}
}  // namespace

void Engine::init(float sampleRate) {
  sampleRate_ = sampleRate;
  globalBase_.reset();
  globalMod_ = globalBase_;
  for (int p = 0; p < kNumParts; ++p) {
    parts_[p].init(p, sampleRate_);
    // Sensible default matrix per part: LFO1 -> cutoff, velocity -> cutoff,
    // ENV2 -> cutoff.  (Loaded presets overwrite this.)
    ModSlotData s0;
    s0.source = MsLfo1;
    s0.target = Cutoff;
    s0.depth = 18;
    modSlotSetPart(s0, p);
    ModSlotData s1;
    s1.source = MsVelocity;
    s1.target = Cutoff;
    s1.depth = 30;
    modSlotSetPart(s1, p);
    ModSlotData s2;
    s2.source = MsEnv2;
    s2.target = Cutoff;
    s2.depth = 35;
    modSlotSetPart(s2, p);
    modSlotSetCurve(s2, McExp);
    parts_[p].setSlot(0, s0);
    parts_[p].setSlot(1, s1);
    parts_[p].setSlot(2, s2);
    partL_[p][0] = 0.0f;
  }
  for (int i = 0; i < kMaxVoices; ++i) {
    voices_[i].init(sampleRate_);
    lastVoicePart_[i] = 0;
    lastVoiceActive_[i] = false;
  }
  for (int p = 0; p < kNumParts; ++p) {
    arps_[p].init(sampleRate_);
    arps_[p].setSink(this);
  }
  for (int i = 0; i < kNumParts; ++i) {
    partCrush_[i].init();
    partEnsemble_[i].init(sampleRate_);
  }
  drive_.init();
  chorus_.init(sampleRate_);
  delay_.init(sampleRate_);
  limiter_.init(sampleRate_);
  dither_.seed(0xC0FFEEu);
  reset();
}

void Engine::reset() {
  for (int i = 0; i < kMaxVoices; ++i) {
    voices_[i].reset();
    lastVoiceActive_[i] = false;
  }
  for (int p = 0; p < kNumParts; ++p) {
    parts_[p].reset();
    // Restore defaults for the part base params (patches call setPartParam).
    partCrush_[p].reset();
    partEnsemble_[p].reset();
    for (int i = 0; i < kNumPartParams; ++i) partOffsets_[p][i] = 0.0f;
    for (int s = 0; s < kModSlots; ++s) slotDepthOffsets_[p][s] = 0.0f;
  }
  drive_.reset();
  chorus_.reset();
  delay_.reset();
  limiter_.reset();
  for (int i = 0; i < kNumGlobalParams; ++i) globalOffsets_[i] = 0.0f;
  for (int ch = 0; ch < 16; ++ch) {
    bend_[ch] = 0.0f;
    aftertouch_[ch] = 0.0f;
  }
  clockTicks_ = 0;
  transport_ = false;
}

void Engine::setGlobalParam(int id, float value) {
  if (id < 0 || id >= kNumGlobalParams) return;
  globalBase_.v[id] = snapGlobalParam(id, value);
  globalMod_.v[id] = globalBase_.v[id];
}

void Engine::setPartParam(int part, int id, float value) {
  if (part < 0 || part >= kNumParts) return;
  parts_[part].setBaseParam(id, value);
}

void Engine::setModSlot(int part, int slot, const ModSlotData& data) {
  if (part < 0 || part >= kNumParts || slot < 0 || slot >= kModSlots) return;
  parts_[part].setSlot(slot, data);
}

void Engine::loadFactoryPatch(int index) {
  Patch patch;
  makeFactoryPatch(index, &patch);
  for (int p = 0; p < kNumParts; ++p) {
    parts_[p].baseRef() = patch.parts[p];
    for (int s = 0; s < kModSlots; ++s) parts_[p].setSlot(s, patch.slots[s]);
  }
  globalBase_ = patch.global;
  globalMod_ = globalBase_;
  reset();
}

// --- voice management ------------------------------------------------------
int Engine::voicesInPart(int part) const {
  int n = 0;
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == part) ++n;
  }
  return n;
}

int Engine::activeVoices() const {
  int n = 0;
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active()) ++n;
  }
  return n;
}

int Engine::findVoice(int note, int part) const {
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == part && voices_[i].note() == note) return i;
  }
  return -1;
}

int Engine::allocateVoice(int part, int note, int velocity, int channel) {
  (void)note;
  (void)velocity;
  (void)channel;
  const int limit = math::clampInt(
      static_cast<int>(std::lround(globalBase_.v[Part1Voices + part])), 0, kMaxVoices);
  if (limit == 0) return -1;

  const int used = voicesInPart(part);
  int best = -1;
  if (used < limit) {
    // Prefer a completely inactive voice.
    for (int i = 0; i < kMaxVoices; ++i) {
      if (!voices_[i].active()) {
        best = i;
        break;
      }
    }
  }
  if (best < 0) {
    // Steal: prefer the oldest releasing voice in this part, then oldest overall.
    uint32_t bestAge = 0;
    for (int i = 0; i < kMaxVoices; ++i) {
      if (!voices_[i].active()) continue;
      const bool ownPart = (voices_[i].part() == part);
      if (used < limit && !ownPart) continue;
      if (voices_[i].releasing() || best < 0) {
        if (best < 0 || voices_[i].age() > bestAge) {
          best = i;
          bestAge = voices_[i].age();
        }
      }
    }
    if (best < 0) {
      for (int i = 0; i < kMaxVoices; ++i) {
        if (!voices_[i].active()) continue;
        if (best < 0 || voices_[i].age() > bestAge) {
          best = i;
          bestAge = voices_[i].age();
        }
      }
    }
  }
  if (best >= 0) {
    const int oldPart = voices_[best].part();
    voices_[best].kill();
    if (oldPart != part && voicesInPart(oldPart) == 0) parts_[oldPart].triggerNoteOff();
  }
  return best;
}

float Engine::velocityForPart(int part) const {
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == part) return voices_[i].velocity();
  }
  return lastTelemetry_.activeVoices > 0 ? 0.7f : 0.0f;
}

float Engine::keytrackForPart(int part) const {
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == part) {
      return math::clamp((static_cast<float>(voices_[i].note()) - 60.0f) / 48.0f, -1.0f, 1.0f);
    }
  }
  return 0.0f;
}

void Engine::noteOn(int note, int velocity, int part, int channel) {
  part = math::clampInt(part, 0, kNumParts - 1);
  if (arps_[part].enabled()) {
    arps_[part].noteOn(note, math::clampInt(velocity, 1, 127));
    return;
  }
  triggerNote(note, velocity, part, channel);
}

void Engine::triggerNote(int note, int velocity, int part, int channel) {
  channel = math::clampInt(channel, 0, 15);
  note = math::clampInt(note, 0, 127);
  velocity = math::clampInt(velocity, 1, 127);
  const float vel = static_cast<float>(velocity) * kInv127;
  const int polyMode = static_cast<int>(std::lround(globalBase_.v[PolyMode]));

  if (polyMode > 0) {
    int idx = -1;
    for (int i = 0; i < kMaxVoices; ++i) {
      if (voices_[i].active() && voices_[i].part() == part && !voices_[i].releasing()) {
        idx = i;
        break;
      }
    }
    if (idx < 0) {
      for (int i = 0; i < kMaxVoices; ++i) {
        if (voices_[i].active() && voices_[i].part() == part) {
          idx = i;
          break;
        }
      }
    }
    if (idx < 0) idx = allocateVoice(part, note, velocity, channel);
    if (idx < 0) return;
    const bool legato = (polyMode == 2) && voices_[idx].active();
    if (legato) {
      voices_[idx].setNote(note);
    } else {
      voices_[idx].noteOn(note, vel, static_cast<uint8_t>(part), static_cast<uint8_t>(channel),
                          false);
      parts_[part].triggerNoteOn(vel, note);
    }
    return;
  }

  const int idx = allocateVoice(part, note, velocity, channel);
  if (idx < 0) return;
  voices_[idx].noteOn(note, vel, static_cast<uint8_t>(part), static_cast<uint8_t>(channel), false);
  parts_[part].triggerNoteOn(vel, note);
}

void Engine::noteOff(int note, int part) {
  part = math::clampInt(part, 0, kNumParts - 1);
  if (arps_[part].enabled()) {
    arps_[part].noteOff(note);
    return;
  }
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == part && voices_[i].note() == note) {
      voices_[i].noteOff();
    }
  }
  int held = 0;
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == part && !voices_[i].releasing()) ++held;
  }
  if (held == 0) parts_[part].triggerNoteOff();
}

void Engine::allNotesOff() {
  for (int i = 0; i < kMaxVoices; ++i) voices_[i].noteOff();
  for (int p = 0; p < kNumParts; ++p) parts_[p].triggerNoteOff();
}

void Engine::setPitchBend(float normalized, int channel) {
  channel = math::clampInt(channel, 0, 15);
  bend_[channel] = math::clamp(normalized, -1.0f, 1.0f);
}
void Engine::setAftertouch(float value, int channel) {
  channel = math::clampInt(channel, 0, 15);
  aftertouch_[channel] = math::clamp(value, 0.0f, 1.0f);
}
void Engine::setModWheel(float value) { modWheel_ = math::clamp(value, 0.0f, 1.0f); }
void Engine::setMidiCc(float normalized) { midiCc_ = math::clamp(normalized, 0.0f, 1.0f); }
void Engine::setCv(int index, float volts) {
  if (index < 0 || index >= kNumCvIn) return;
  cvVolts_[index] = math::clamp(volts, -12.0f, 12.0f);
}
void Engine::setMacro(int index, float value) {
  if (index < 0 || index >= kNumMacros) return;
  macros_[index] = math::clamp(value, 0.0f, 1.0f);
}
void Engine::setTransport(bool running) {
  transport_ = running;
  if (!running) allNotesOff();
}
void Engine::setFillMode(bool fill) { fill_ = fill; }

// --- modulation ------------------------------------------------------------
void Engine::updateModulation(int n) {
  const float bpm = globalBase_.v[Bpm];
  for (int p = 0; p < kNumParts; ++p) {
    for (int i = 0; i < kNumCvIn; ++i) {
      modCtx_[p].cv[i] = math::clamp(cvVolts_[i] * 0.1f, -1.0f, 1.0f);
    }
    modCtx_[p].modWheel = modWheel_;
    modCtx_[p].midiCc = midiCc_;
    modCtx_[p].aftertouch = aftertouch_[p];
    modCtx_[p].velocity = velocityForPart(p);
    modCtx_[p].keytrack = keytrackForPart(p);
    for (int i = 0; i < kNumMacros; ++i) modCtx_[p].macros[i] = macros_[i];
    for (int i = 0; i < kSeqTracks; ++i) modCtx_[p].seqTrack[i] = 0.0f;
    for (int i = 0; i < kNumParts; ++i) modCtx_[p].partOut[i] = parts_[i].meter();
    modCtx_[p].bar = clockTicks_ / 96u;
    modCtx_[p].firstOfBar = (clockTicks_ % 96u) == 0u;
    modCtx_[p].fill = fill_;
    modCtx_[p].bpm = bpm;
    parts_[p].tickGenerators(n, bpm);
  }

  std::memset(partOffsets_, 0, sizeof(partOffsets_));
  std::memset(slotDepthOffsets_, 0, sizeof(slotDepthOffsets_));
  std::memset(globalOffsets_, 0, sizeof(globalOffsets_));

  static float globalSources[kNumModSources];
  for (int i = 0; i < kNumModSources; ++i) globalSources[i] = 0.0f;

  for (int p = 0; p < kNumParts; ++p) parts_[p].evaluateSlots(modCtx_[p], globalSources);

  for (int p = 0; p < kNumParts; ++p) {
    const float* outs = parts_[p].slotOutputs();
    for (int s = 0; s < kModSlots; ++s) {
      const ModSlotData& data = parts_[p].slot(s);
      if (data.source == MsNone) continue;
      const float value = outs[s];
      const uint8_t target = data.target;
      const int targetPart = math::clampInt(modSlotPart(data), 0, kNumParts - 1);
      if (target < kNumPartParams) {
        partOffsets_[targetPart][target] += value;
      } else if (target >= MtSlotDepth && target < MtSlotDepth + kModSlots) {
        slotDepthOffsets_[targetPart][target - MtSlotDepth] += value;
      } else {
        const int gid = globalParamForTarget(target);
        if (gid >= 0) globalOffsets_[gid] += value;
      }
    }
  }

  for (int p = 0; p < kNumParts; ++p) {
    parts_[p].applyOffsets(partOffsets_[p], slotDepthOffsets_[p]);
  }

  // Global params (FX / seq) follow their base values plus matrix offsets.
  for (int id = 0; id < kNumGlobalParams; ++id) {
    const float offset = math::clamp(globalOffsets_[id], -4.0f, 4.0f);
    applyGlobalMod(id, offset);
  }
}

void Engine::applyGlobalMod(int id, float offset) {
  const ParamMeta& m = kGlobalParamMeta[id];
  float v = globalBase_.v[id];
  if (offset != 0.0f) {
    if (m.flags & PF_LOG) {
      v = v * std::pow(2.0f, offset * 4.0f);
    } else {
      v = v + offset * (m.max - m.min);
    }
    if (m.flags & PF_DISCRETE) v = std::round(v);
  }
  globalMod_.v[id] = math::clamp(v, m.min, m.max);
}

// --- event handling --------------------------------------------------------
void Engine::handleEvent(const Event& e) {
  switch (e.type) {
    case EventType::NoteOn: {
      const int part = e.channel % kNumParts;
      noteOn(e.index, static_cast<int>(e.value * 127.0f + 0.5f), part, e.channel);
      break;
    }
    case EventType::NoteOff: {
      const int part = e.channel % kNumParts;
      noteOff(e.index, part);
      break;
    }
    case EventType::AllNotesOff:
    case EventType::Panic:
      allNotesOff();
      break;
    case EventType::PitchBend:
      setPitchBend(e.value, e.channel);
      break;
    case EventType::Aftertouch:
      setAftertouch(e.value, e.channel);
      break;
    case EventType::PolyAftertouch: {
      for (int i = 0; i < kMaxVoices; ++i) {
        if (voices_[i].active() && voices_[i].note() == e.index) {
          // poly AT is exposed as channel AT for that part (simplified)
          aftertouch_[voices_[i].part()] = math::clamp(e.value, 0.0f, 1.0f);
        }
      }
      break;
    }
    case EventType::ModWheel:
      setModWheel(e.value);
      break;
    case EventType::ControlChange:
      setMidiCc(e.value);
      break;
    case EventType::ParamSet:
      setGlobalParam(e.index, e.value);
      break;
    case EventType::ParamSetNorm: {
      if (e.index < kNumGlobalParams) {
        setGlobalParam(e.index, paramFromNorm(kGlobalParamMeta[e.index], e.value));
      }
      break;
    }
    case EventType::PartParamSet: {
      if (e.channel < kNumParts && e.index < kNumPartParams) {
        setPartParam(e.channel, e.index, e.value);
      }
      break;
    }
    case EventType::ProgramChange:
      loadFactoryPatch(e.index);
      break;
    case EventType::MacroSet:
      setMacro(e.index, e.value);
      break;
    case EventType::Clock:
      if (transport_) ++clockTicks_;
      break;
    case EventType::Start:
      transport_ = true;
      clockTicks_ = 0;
      break;
    case EventType::Stop:
      setTransport(false);
      break;
    case EventType::Continue:
      transport_ = true;
      break;
    case EventType::CvIn:
      setCv(e.channel, e.value);
      break;
    case EventType::CtrlAll:
      // ctrl-all (R1 held) is handled by the UI layer before events arrive.
      break;
    default:
      break;
  }
}

// --- rendering -------------------------------------------------------------
void Engine::process(float* outL, float* outR, int n) {
  if (n <= 0) return;
  if (n > kBlockSize) n = kBlockSize;

  Event e;
  while (events_.pop(&e)) handleEvent(e);

  // Part arpeggiators: driven by the global arp mode.
  for (int p = 0; p < kNumParts; ++p) {
    const int arpMode = static_cast<int>(std::lround(globalBase_.v[ArpMode]));
    arps_[p].setParams(arpMode, static_cast<int>(std::lround(globalBase_.v[ArpOctaves])), 0.6f,
                       false);
    if (arps_[p].enabled()) arps_[p].process(n, globalBase_.v[Bpm], p);
  }
  if (sequencer_) sequencer_->process(n);

  updateModulation(n);

  // Push modulated global values into the FX units.
  drive_.setAmount(globalMod_.v[FxDrive]);
  drive_.setTone(0.55f);
  drive_.setMix(1.0f);
  chorus_.setAmount(math::clamp(globalMod_.v[FxChorusMix], 0.0f, 1.0f));
  chorus_.setRate(globalMod_.v[FxChorusRate]);
  delay_.setTime(globalMod_.v[FxDelayTime]);
  delay_.setFeedback(globalMod_.v[FxDelayFb]);
  delay_.setMix(globalMod_.v[FxDelayMix]);
  delay_.setDamping(6500.0f);
  limiter_.setThreshold(globalMod_.v[FxLimiterThreshold]);
  limiter_.setRelease(globalMod_.v[FxLimiterRelease]);

  for (int p = 0; p < kNumParts; ++p) {
    std::memset(partL_[p], 0, sizeof(float) * static_cast<size_t>(n));
    std::memset(partR_[p], 0, sizeof(float) * static_cast<size_t>(n));
  }

  // --- voices --------------------------------------------------------------
  for (int i = 0; i < kMaxVoices; ++i) {
    Voice& v = voices_[i];
    if (!v.active()) {
      lastVoiceActive_[i] = false;
      continue;
    }
    const int p = v.part();
    VoiceContext ctx;
    ctx.params = &parts_[p].params();
    ctx.partEnv2 = parts_[p].envLevel(1);
    ctx.bendSemitones = bend_[v.channel()] * globalBase_.v[BendRange];
    ctx.glideSeconds = globalBase_.v[Glide];
    v.render(partL_[p], partR_[p], n, ctx);
    v.ageTick();
    lastVoiceActive_[i] = true;
    lastVoicePart_[i] = p;
  }

  // --- per-part processing (crush, Polyvox ensemble) -----------------------
  for (int p = 0; p < kNumParts; ++p) {
    const PartParams& pp = parts_[p].params();
    partCrush_[p].setBits(pp.v[CrushBits]);
    partCrush_[p].setRate(0.0f);
    partCrush_[p].setMix(pp.v[CrushMix]);
    partCrush_[p].process(partL_[p], partR_[p], n);

    if (static_cast<int>(pp.v[FilterChar] + 0.5f) == CharPolyvox && pp.v[EnsembleAmount] > 0.001f) {
      partEnsemble_[p].setAmount(pp.v[EnsembleAmount]);
      partEnsemble_[p].setRate(pp.v[EnsembleRate]);
      partEnsemble_[p].process(partL_[p], partR_[p], n);
    }

    float sum = 0.0f;
    for (int i = 0; i < n; ++i) {
      sum += partL_[p][i] * partL_[p][i] + partR_[p][i] * partR_[p][i];
    }
    const float meter = std::sqrt(sum / static_cast<float>(2 * n));
    parts_[p].setMeter(meter);
  }

  // --- bus + global FX -----------------------------------------------------
  std::memset(busL_, 0, sizeof(float) * static_cast<size_t>(n));
  std::memset(busR_, 0, sizeof(float) * static_cast<size_t>(n));
  for (int p = 0; p < kNumParts; ++p) {
    for (int i = 0; i < n; ++i) {
      busL_[i] += partL_[p][i];
      busR_[i] += partR_[p][i];
    }
  }

  drive_.process(busL_, busR_, n);
  if (globalMod_.v[FxChorusMix] > 0.001f) chorus_.process(busL_, busR_, n);
  if (globalMod_.v[FxDelayMix] > 0.001f) delay_.process(busL_, busR_, n);

  const float master = globalMod_.v[MasterVolume];
  for (int i = 0; i < n; ++i) {
    busL_[i] *= master;
    busR_[i] *= master;
  }
  limiter_.process(busL_, busR_, n);

  // --- output + telemetry --------------------------------------------------
  Telemetry& t = lastTelemetry_;
  float peak = 0.0f;
  double accL = 0.0, accR = 0.0;
  for (int i = 0; i < n; ++i) {
    const float l = busL_[i];
    const float r = busR_[i];
    outL[i] = l;
    outR[i] = r;
    accL += static_cast<double>(l) * l;
    accR += static_cast<double>(r) * r;
    peak = std::fmax(peak, std::fmax(std::fabs(l), std::fabs(r)));
  }
  t.rmsL = static_cast<float>(std::sqrt(accL / n));
  t.rmsR = static_cast<float>(std::sqrt(accR / n));
  t.peak = peak;
  t.cpuLoad = cpuLoad_;
  t.activeVoices = static_cast<uint16_t>(activeVoices());
  for (int p = 0; p < kNumParts; ++p) {
    t.voicesPerPart[p] = static_cast<uint16_t>(voicesInPart(p));
    t.partLevel[p] = parts_[p].meter();
    t.modulated[p][0] = parts_[p].params().v[Cutoff];
    t.modulated[p][1] = parts_[p].params().v[Resonance];
  }
  t.frames += static_cast<uint32_t>(n);
  for (int i = 0; i < kNumCvOut; ++i) t.cvOut[i] = 0.0f;
  telemetry_.push(t);
}

// --- SequencerSink / ArpSink ------------------------------------------------
void Engine::onSeqNoteOn(int track, int note, int velocity) {
  if (track < 0 || track >= kNumParts) return;
  triggerNote(note, velocity, track, track);
}

void Engine::onSeqNoteOff(int track, int note) {
  if (track < 0 || track >= kNumParts) return;
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == track && voices_[i].note() == note) {
      voices_[i].noteOff();
    }
  }
}

void Engine::onSeqPlock(int track, int param, float normalized) {
  if (track < 0 || track >= kNumParts || param < 0 || param >= kNumPartParams) return;
  setPartParam(track, param, paramFromNorm(kPartParamMeta[param], normalized));
}

void Engine::onSeqSoundLock(int track, int preset) {
  if (track < 0 || track >= kNumParts) return;
  Patch patch;
  makeFactoryPatch(preset, &patch);
  for (int i = 0; i < kNumPartParams; ++i) setPartParam(track, i, patch.parts[track].v[i]);
}

void Engine::onArpNoteOn(int part, int note, int velocity) {
  if (part < 0 || part >= kNumParts) return;
  triggerNote(note, velocity, part, part);
}

void Engine::onArpNoteOff(int part, int note) {
  if (part < 0 || part >= kNumParts) return;
  for (int i = 0; i < kMaxVoices; ++i) {
    if (voices_[i].active() && voices_[i].part() == part && voices_[i].note() == note) {
      voices_[i].noteOff();
    }
  }
}

}  // namespace bukifon
