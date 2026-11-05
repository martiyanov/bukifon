// SPDX-License-Identifier: GPL-3.0-or-later
#include "sim/simulator.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "core/math.hpp"

namespace bukifon {
namespace sim {
namespace {
constexpr int kNumParams = ui::kNumParams;
constexpr int kNumHints = ui::kNumHints;
constexpr int kAudioBlockMax = 256;

void copyString(char* dst, size_t cap, const char* src) {
  if (!dst || cap == 0) return;
  if (!src) src = "";
  std::snprintf(dst, cap, "%s", src);
}

}  // namespace

void Simulator::init(const Options& options) {
  options_ = options;
  if (options_.blockFrames <= 0 || options_.blockFrames > kAudioBlockMax) {
    options_.blockFrames = 128;
  }
  modeManager_.init(DeviceMode::Synth);
  engine_.init(options_.sampleRate);
  sequencer_.init(options_.sampleRate);
  sequencer_.setSink(this);
  reset();
  initialized_ = true;
}

void Simulator::reset() {
  engine_.reset();
  sequencer_.reset();
  sequencer_.setSink(this);
  pending_.clear();
  pendingIndex_ = 0;
  observation_.clear();
  frame_ = 0;
  stats_ = Stats{};
  lastPeak_ = 0.0f;
  selectedParam_ = 0;
  for (int p = 0; p < kNumParts; ++p) {
    for (int k = 0; k < kNumPartParams; ++k) plockSavedValid_[p][k] = false;
  }
  ui::uiSnapshotInit(&cachedSnapshot_);
}

void Simulator::addEvent(const SimEvent& event) {
  pending_.add(event);
  pending_.sortByFrame();
}

void Simulator::addEvent(uint64_t frame, SimEventType type, uint8_t a, uint8_t b, float value) {
  SimEvent e;
  e.frame = frame;
  e.type = type;
  e.a = a;
  e.b = b;
  e.value = value;
  addEvent(e);
}

bool Simulator::loadEvents(const char* path) {
  EventLog loaded;
  if (!loaded.loadFromFile(path)) return false;
  pending_ = loaded;
  pending_.sortByFrame();
  pendingIndex_ = 0;
  return true;
}

bool Simulator::saveEvents(const char* path) const { return pending_.saveToFile(path); }

void Simulator::observe(SimEventType type, uint8_t a, uint8_t b, float value) {
  if (!options_.recordObservationLog) return;
  SimEvent e;
  e.frame = frame_;
  e.type = type;
  e.a = a;
  e.b = b;
  e.value = value;
  observation_.add(e);
}

void Simulator::play() {
  sequencer_.setPlaying(true);
  engine_.setTransport(true);
  observe(SimEventType::Transport, 0, 0, 1.0f);
}

void Simulator::stop() {
  sequencer_.setPlaying(false);
  engine_.setTransport(false);
  engine_.allNotesOff();
  observe(SimEventType::Transport, 0, 0, 0.0f);
}

void Simulator::togglePlay() {
  if (playing()) {
    stop();
  } else {
    play();
  }
}

void Simulator::setBpm(float bpm) {
  bpm = math::clamp(bpm, 40.0f, 300.0f);
  sequencer_.setBpm(bpm);
  engine_.setGlobalParam(Bpm, bpm);
  observe(SimEventType::Tempo, 0, 0, bpm);
}

void Simulator::setPattern(int pattern) {
  sequencer_.setPatternIndex(pattern);
  observe(SimEventType::Pattern, static_cast<uint8_t>(sequencer_.patternIndex()), 0, 0.0f);
}

void Simulator::setTrackMuted(int track, bool muted) {
  sequencer_.setTrackMuted(track, muted);
  observe(SimEventType::Mute, static_cast<uint8_t>(track), 0, muted ? 1.0f : 0.0f);
}

void Simulator::setPartParam(int part, int paramId, float value) {
  engine_.setPartParam(part, paramId, value);
  observe(SimEventType::PartParam, static_cast<uint8_t>(part), static_cast<uint8_t>(paramId),
          value);
}

bool Simulator::setDeviceMode(DeviceMode mode) {
  const bool changed = modeManager_.setMode(mode);
  observe(SimEventType::Marker, 10, static_cast<uint8_t>(mode), changed ? 1.0f : 0.0f);
  return changed;
}

void Simulator::setGlobalParam(int paramId, float value) {
  engine_.setGlobalParam(paramId, value);
  observe(SimEventType::Param, static_cast<uint8_t>(paramId), 0, value);
}

void Simulator::applyEvent(const SimEvent& event) {
  switch (event.type) {
    case SimEventType::NoteOn:
      engine_.noteOn(event.b, static_cast<int>(event.value), event.a, event.a);
      break;
    case SimEventType::NoteOff:
      engine_.noteOff(event.b, event.a);
      break;
    case SimEventType::Param:
      engine_.setGlobalParam(event.a, event.value);
      break;
    case SimEventType::PartParam:
      engine_.setPartParam(event.a, event.b, event.value);
      break;
    case SimEventType::Transport:
      if (event.value != 0.0f) {
        sequencer_.setPlaying(true);
        engine_.setTransport(true);
      } else {
        sequencer_.setPlaying(false);
        engine_.setTransport(false);
        engine_.allNotesOff();
      }
      break;
    case SimEventType::Encoder:
      selectedParam_ = math::clampInt(selectedParam_ + static_cast<int>(event.value), 0, 7);
      break;
    case SimEventType::Mute:
      sequencer_.setTrackMuted(event.a, event.value != 0.0f);
      break;
    case SimEventType::Plock:
      engine_.setPartParam(event.a, event.b,
                           paramFromNorm(kPartParamMeta[event.b], event.value));
      break;
    case SimEventType::Pattern:
      sequencer_.setPatternIndex(event.a);
      break;
    case SimEventType::Tempo:
      sequencer_.setBpm(event.value);
      engine_.setGlobalParam(Bpm, event.value);
      break;
    case SimEventType::Marker:
    default:
      break;
  }
  observe(event.type, event.a, event.b, event.value);
}

uint64_t Simulator::samplesPerBar(float bpm, float sampleRate) {
  const double secondsPerBeat = 60.0 / static_cast<double>(bpm);
  return static_cast<uint64_t>(std::llround(secondsPerBeat * 4.0 * sampleRate));
}

void Simulator::runSamples(uint64_t frames) {
  if (!initialized_) init();
  const uint64_t end = frame_ + frames;
  static float l[kAudioBlockMax];
  static float r[kAudioBlockMax];
  while (frame_ < end) {
    // Apply all external events scheduled for this frame (stable order).
    while (pendingIndex_ < pending_.size() && pending_[pendingIndex_].frame <= frame_) {
      applyEvent(pending_[pendingIndex_]);
      ++pendingIndex_;
    }
    uint64_t chunk = static_cast<uint64_t>(options_.blockFrames);
    if (chunk > end - frame_) chunk = end - frame_;
    if (pendingIndex_ < pending_.size()) {
      const uint64_t next = pending_[pendingIndex_].frame;
      if (next > frame_ && next - frame_ < chunk) chunk = next - frame_;
    }
    if (chunk == 0) continue;
    sequencer_.process(static_cast<int>(chunk));
    engine_.process(l, r, static_cast<int>(chunk));
    updateAudioPeak(l, r, static_cast<int>(chunk));
    frame_ += chunk;
    ++stats_.blocks;
  }
  stats_.frames = frame_;
  stats_.seconds = seconds();
}

void Simulator::updateAudioPeak(const float* l, const float* r, int frames) {
  for (int i = 0; i < frames; ++i) {
    const float p = std::fmax(std::fabs(l[i]), std::fabs(r[i]));
    if (p > stats_.peak) stats_.peak = p;
    if (p > lastPeak_) lastPeak_ = p;
  }
}

void Simulator::runSeconds(double seconds) {
  const uint64_t frames = static_cast<uint64_t>(seconds * options_.sampleRate + 0.5);
  runSamples(frames);
}

void Simulator::runBars(int bars) {
  if (bars <= 0) return;
  const uint64_t perBar = samplesPerBar(sequencer_.bpm(), options_.sampleRate);
  runSamples(perBar * static_cast<uint64_t>(bars));
}

void Simulator::buildDemoPattern() {
  sequencer_.init(options_.sampleRate);
  sequencer_.setSink(this);
  sequencer_.setBpm(120.0f);
  sequencer_.setPatternIndex(0);
  engine_.setGlobalParam(Bpm, 120.0f);
  engine_.setTransport(false);
  const int scale[8] = {0, 2, 4, 5, 7, 9, 11, 12};
  for (int track = 0; track < kSeqTracks; ++track) {
    for (int step = 0; step < kSeqSteps; ++step) {
      SequenceStep& s = sequencer_.step(track, step);
      s = SequenceStep{};
      s.active = true;
      s.note = static_cast<uint8_t>(48 + track * 12 + scale[(step + track) % 8]);
      s.velocity = static_cast<uint8_t>(70 + (step * 7 + track * 5) % 40);
      s.gate = 60;
      s.condition = TrigAlways;
      s.micro = 0;
      s.plockCount = 0;
    }
    sequencer_.setTrackLength(track, kSeqSteps);
    sequencer_.setTrackSpeed(track, 1);
    sequencer_.setTrackMuted(track, false);
  }
  // Vertical slice: exactly one p-lock (track 1, step 5, cutoff 60 %).
  sequencer_.setPlock(0, 4, 0, Cutoff, 153);
}

const EventLog& Simulator::runDemo(int bars) {
  reset();
  buildDemoPattern();
  observe(SimEventType::Marker, 1, 0, 0.0f);
  play();
  runBars(bars);
  stop();
  const auto t0 = std::chrono::steady_clock::now();
  stats_.renderSeconds =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  observe(SimEventType::Marker, 2, 0, static_cast<float>(frame_));
  return observation_;
}

// --- SequencerSink ---------------------------------------------------------
void Simulator::onSeqNoteOn(int track, int note, int velocity) {
  engine_.noteOn(note, velocity, track, track);
  observe(SimEventType::NoteOn, static_cast<uint8_t>(track), static_cast<uint8_t>(note),
          static_cast<float>(velocity));
}

void Simulator::onSeqNoteOff(int track, int note) {
  engine_.noteOff(note, track);
  observe(SimEventType::NoteOff, static_cast<uint8_t>(track), static_cast<uint8_t>(note), 0.0f);
}

void Simulator::onSeqPlock(int track, int param, float normalized) {
  if (track < 0 || track >= kNumParts || param < 0 || param >= kNumPartParams) return;
  if (!plockSavedValid_[track][param]) {
    plockSaved_[track][param] = engine_.partBase(track).v[param];
    plockSavedValid_[track][param] = true;
  }
  engine_.setPartParam(track, param, paramFromNorm(kPartParamMeta[param], normalized));
  observe(SimEventType::Plock, static_cast<uint8_t>(track), static_cast<uint8_t>(param),
          normalized);
}

void Simulator::onSeqPlockRestore(int track, int param) {
  if (track < 0 || track >= kNumParts || param < 0 || param >= kNumPartParams) return;
  if (!plockSavedValid_[track][param]) return;
  engine_.setPartParam(track, param, plockSaved_[track][param]);
  plockSavedValid_[track][param] = false;
  observe(SimEventType::Plock, static_cast<uint8_t>(track), static_cast<uint8_t>(param),
          paramToNorm(kPartParamMeta[param], plockSaved_[track][param]));
}

void Simulator::onSeqSoundLock(int track, int preset) {
  (void)track;
  (void)preset;
  // Sound locks are out of scope for the vertical slice; ignore but keep the log
  // honest by recording a marker.
  observe(SimEventType::Marker, 3, 0, 0.0f);
}

void Simulator::onSeqStep(int track, int step, uint32_t pass) {
  (void)track;
  (void)step;
  (void)pass;
}

float Simulator::seqParamBase(int track, int param) const {
  if (track < 0 || track >= kNumParts || param < 0 || param >= kNumPartParams) return 0.0f;
  return paramToNorm(kPartParamMeta[param], engine_.partBase(track).v[param]);
}

// --- UI snapshot -----------------------------------------------------------
void Simulator::formatParamValue(const ParamMeta& meta, float value, char* out, size_t capacity) {
  if (!out || capacity == 0) return;
  if (meta.flags & PF_DISCRETE) {
    std::snprintf(out, capacity, "%d", static_cast<int>(std::lround(value)));
    return;
  }
  if (meta.flags & PF_HZ) {
    if (value >= 1000.0f) {
      std::snprintf(out, capacity, "%.2fk", value / 1000.0f);
    } else {
      std::snprintf(out, capacity, "%.0fHz", value);
    }
    return;
  }
  if (meta.flags & PF_SECONDS) {
    if (value < 1.0f) {
      std::snprintf(out, capacity, "%.0fms", value * 1000.0f);
    } else {
      std::snprintf(out, capacity, "%.2fs", value);
    }
    return;
  }
  if (meta.flags & PF_CENTS) {
    std::snprintf(out, capacity, "%+.0fct", value);
    return;
  }
  if (meta.flags & PF_SEMITONES) {
    std::snprintf(out, capacity, "%+.0fst", value);
    return;
  }
  if (meta.flags & PF_RATIO) {
    std::snprintf(out, capacity, "%.2fx", value);
    return;
  }
  if (meta.flags & PF_BIPOLAR) {
    std::snprintf(out, capacity, "%+.2f", value);
    return;
  }
  std::snprintf(out, capacity, "%.2f", value);
}

void Simulator::fillParamsForScreen(ui::UiSnapshot* snapshot, ui::Screen screen) const {
  const ParamMeta* meta = nullptr;
  const float* values = nullptr;
  float fallback[kNumParams] = {};
  if (screen == ui::Screen::Main) {
    const PartParams& part = engine_.modulatedPartParams(0);
    static const uint8_t ids[kNumParams] = {Cutoff,          Resonance, FilterEnvAmt, FilterDrive,
                                            Env1A,          Env1D,     Env1S,        Env1R};
    for (int i = 0; i < kNumParams; ++i) {
      meta = &kPartParamMeta[ids[i]];
      snapshot->params[i].norm = paramToNorm(*meta, part.v[ids[i]]);
      formatParamValue(*meta, part.v[ids[i]], snapshot->params[i].value,
                       sizeof(snapshot->params[i].value));
      copyString(snapshot->params[i].label, sizeof(snapshot->params[i].label), meta->name);
    }
    static const char* hints[8] = {"CUTOFF", "RESON", "ENVAMT", "DRIVE",
                                   "ATK",    "DEC",   "SUS",    "REL"};
    for (int i = 0; i < kNumHints; ++i) copyString(snapshot->hints[i], sizeof(snapshot->hints[i]), hints[i]);
    return;
  }
  if (screen == ui::Screen::Sequencer) {
    static const char* labels[8] = {"MODE", "LEN", "SWING", "TRANSPOSE",
                                    "PLOCK", "COND", "MICRO", "TEMPO"};
    char valuesText[8][12];
    std::snprintf(valuesText[0], 12, "%s", "FWD");
    std::snprintf(valuesText[1], 12, "%d", sequencer_.trackLength(0));
    std::snprintf(valuesText[2], 12, "%.0f%%", sequencer_.swing() * 100.0f);
    std::snprintf(valuesText[3], 12, "%+d", static_cast<int>(engine_.globals().v[SeqTranspose]));
    std::snprintf(valuesText[4], 12, "%d", sequencer_.step(0, 4).plockCount);
    std::snprintf(valuesText[5], 12, "%s", "1ST");
    std::snprintf(valuesText[6], 12, "%+d", static_cast<int>(sequencer_.step(0, 0).micro));
    std::snprintf(valuesText[7], 12, "%.0f", engine_.globals().v[Bpm]);
    for (int i = 0; i < kNumParams; ++i) {
      copyString(snapshot->params[i].label, sizeof(snapshot->params[i].label), labels[i]);
      copyString(snapshot->params[i].value, sizeof(snapshot->params[i].value), valuesText[i]);
      snapshot->params[i].norm = 0.35f + 0.07f * static_cast<float>(i);
    }
    static const char* hints[8] = {"MODE", "LEN", "SWING", "TRANSP", "PLOCK", "COND", "MICRO", "BPM"};
    for (int i = 0; i < kNumHints; ++i) copyString(snapshot->hints[i], sizeof(snapshot->hints[i]), hints[i]);
    return;
  }
  if (screen == ui::Screen::Mixer) {
    static const uint8_t fxIds[8] = {FxDelayTime,   FxDelayFb,      FxChorusRate,     FxChorusDepth,
                                     FxDrive,       FxLimiterThreshold, SeqSwing, MasterVolume};
    static const char* labels[8] = {"DELAY", "FEEDBACK", "CHORUS", "CH DEPTH",
                                    "DRIVE", "LIMIT",    "SWING",  "MASTER"};
    for (int i = 0; i < kNumParams; ++i) {
      meta = &kGlobalParamMeta[fxIds[i]];
      const float v = engine_.modulatedGlobals().v[fxIds[i]];
      fallback[i] = v;
      (void)fallback;
      snapshot->params[i].norm = paramToNorm(*meta, v);
      formatParamValue(*meta, v, snapshot->params[i].value, sizeof(snapshot->params[i].value));
      copyString(snapshot->params[i].label, sizeof(snapshot->params[i].label), labels[i]);
    }
    static const char* hints[8] = {"DLY", "FB", "CHR", "CHDP", "DRV", "LIM", "SWG", "MST"};
    for (int i = 0; i < kNumHints; ++i) copyString(snapshot->hints[i], sizeof(snapshot->hints[i]), hints[i]);
    (void)values;
    return;
  }
  // Modules screen: API v0 descriptors are rendered from a static list for the
  // skeleton (the real loader lives in modules/module_host_v0).
  static const char* labels[8] = {"DRIVE", "TONE", "MIX", "STATE", "PARAMS", "API", "BUDGET", "BYPASS"};
  static const char* valuesText[8] = {"55%", "45%", "85%", "64B", "3", "v0", "1600us", "NO"};
  for (int i = 0; i < kNumParams; ++i) {
    copyString(snapshot->params[i].label, sizeof(snapshot->params[i].label), labels[i]);
    copyString(snapshot->params[i].value, sizeof(snapshot->params[i].value), valuesText[i]);
    snapshot->params[i].norm = 0.2f + 0.1f * static_cast<float>(i);
  }
  static const char* hints[8] = {"DRIVE", "TONE", "MIX", "LOAD", "SAVE", "RESET", "BYPASS", "INFO"};
  for (int i = 0; i < kNumHints; ++i) copyString(snapshot->hints[i], sizeof(snapshot->hints[i]), hints[i]);
}

void Simulator::buildSnapshot(ui::UiSnapshot* snapshot, ui::Screen screen) const {
  if (!snapshot) return;
  ui::uiSnapshotInit(snapshot);
  snapshot->screen = screen;
  static const char* pages[] = {"MAIN", "SEQUENCER", "MIXER", "MODULES", "GEN", "EXT"};
  const int screenIndex = static_cast<int>(screen);
  copyString(snapshot->page, sizeof(snapshot->page),
             pages[screenIndex >= 0 && screenIndex < 6 ? screenIndex : 0]);
  snapshot->bpm = sequencer_.bpm();
  snapshot->pattern = sequencer_.patternIndex() + 1;
  snapshot->playing = playing();
  copyString(snapshot->status, sizeof(snapshot->status), playing() ? "PLAY" : "STOP");
  snapshot->activeStep = sequencer_.currentStep(0);
  std::snprintf(snapshot->deviceMode, sizeof(snapshot->deviceMode), "%s",
                deviceModeShortName(modeManager_.mode()));
  snapshot->fill = sequencer_.fill();
  snapshot->trackCount = kSeqTracks;
  snapshot->stepCount = kSeqSteps;
  const uint64_t perBar = samplesPerBar(sequencer_.bpm(), options_.sampleRate);
  snapshot->bar = perBar > 0 ? static_cast<int>(frame_ / perBar) : 0;
  snapshot->activeVoices = engine_.activeVoices();
  snapshot->masterLevel = engine_.lastTelemetry().peak > 0.0f ? engine_.lastTelemetry().peak
                                                              : lastPeak_;
  const Pattern& pattern = sequencer_.pattern(sequencer_.patternIndex());
  for (int t = 0; t < kSeqTracks; ++t) {
    ui::UiTrack& track = snapshot->tracks[t];
    std::snprintf(track.name, sizeof(track.name), "PART %d", t + 1);
    std::snprintf(track.patch, sizeof(track.patch), "PATCH %d", t + 1);
    track.muted = pattern.tracks[t].muted;
    track.active = engine_.voicesInPart(t) > 0;
    track.voices = engine_.voicesInPart(t);
    track.currentStep = sequencer_.currentStep(t);
    track.length = sequencer_.trackLength(t);
    track.level = engine_.partMeter(t);
    track.peak = engine_.partMeter(t);
    track.cutoff = engine_.modulatedPartParams(t).v[Cutoff];
    track.pan = engine_.modulatedPartParams(t).v[PartPan];
    for (int st = 0; st < kSeqSteps; ++st) {
      const SequenceStep& step = pattern.tracks[t].steps[st];
      track.stepActive[st] = step.active;
      track.note[st] = step.note;
      track.stepPlocked[st] = step.plockCount > 0;
    }
  }
  snapshot->selectedParam = selectedParam_;
  if (screen == ui::Screen::Modules) {
    snapshot->moduleCount = 4;
    copyString(snapshot->modules[0], sizeof(snapshot->modules[0]), "DIODE DRIVE  v0.1");
    copyString(snapshot->modules[1], sizeof(snapshot->modules[1]), "LFO MOD      v0.1");
    copyString(snapshot->modules[2], sizeof(snapshot->modules[2]), "SOFT DELAY   builtin");
    copyString(snapshot->modules[3], sizeof(snapshot->modules[3]), "SOFT CHORUS  builtin");
    copyString(snapshot->moduleApi, sizeof(snapshot->moduleApi), "MODULE API v0 (EXP)");
  }
  fillParamsForScreen(snapshot, screen);
  if (screen == ui::Screen::Gen) {
    // The GEN page is display-only in the host demo: use the curated demo
    // values (the real engine GenParams are covered by tests and the CLI).
    ui::UiSnapshot genDemo;
    ui::uiSnapshotGenDemo(&genDemo);
    for (int t = 0; t < kSeqTracks; ++t) {
      snapshot->gen[t] = genDemo.gen[t];
      snapshot->genPartSelected[t] = genDemo.genPartSelected[t];
    }
    snapshot->euclidMask = genDemo.euclidMask;
    snapshot->scaleName[sizeof(snapshot->scaleName) - 1] = '\0';
    copyString(snapshot->scaleName, sizeof(snapshot->scaleName), genDemo.scaleName);
    copyString(snapshot->arpRateText, sizeof(snapshot->arpRateText), genDemo.arpRateText);
    copyString(snapshot->arpModeText, sizeof(snapshot->arpModeText), genDemo.arpModeText);
    for (int i = 0; i < 8; ++i) copyString(snapshot->presetNames[i], sizeof(snapshot->presetNames[i]), genDemo.presetNames[i]);
    for (int i = 0; i < kNumParams; ++i) snapshot->paramModulated[i] = genDemo.paramModulated[i];
    snapshot->abCompare = genDemo.abCompare;
    snapshot->abShowB = genDemo.abShowB;
    snapshot->presetSlot = genDemo.presetSlot;
    for (int i = 0; i < kNumHints; ++i) copyString(snapshot->hints[i], sizeof(snapshot->hints[i]), genDemo.hints[i]);
  }
  if (screen == ui::Screen::Ext) {
    ui::UiSnapshot extDemo;
    ui::uiSnapshotExtDemo(&extDemo);
    for (int t = 0; t < 8; ++t) snapshot->extTracks[t] = extDemo.extTracks[t];
    snapshot->extSelectedTrack = extDemo.extSelectedTrack;
    snapshot->extSelectedStep = extDemo.extSelectedStep;
    for (int i = 0; i < kNumParams; ++i) {
      copyString(snapshot->params[i].label, sizeof(snapshot->params[i].label), extDemo.params[i].label);
      copyString(snapshot->params[i].value, sizeof(snapshot->params[i].value), extDemo.params[i].value);
      snapshot->params[i].norm = extDemo.params[i].norm;
    }
    for (int i = 0; i < kNumHints; ++i) copyString(snapshot->hints[i], sizeof(snapshot->hints[i]), extDemo.hints[i]);
    copyString(snapshot->selectedLabel, sizeof(snapshot->selectedLabel), extDemo.selectedLabel);
    copyString(snapshot->footer, sizeof(snapshot->footer), extDemo.footer);
  }
  std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                "16 bars | 4 tracks | p-lock t1 s5 | %d voices | %.1f s | MODE %s",
                engine_.activeVoices(), seconds(), deviceModeName(modeManager_.mode()));
}

ui::UiSnapshot Simulator::snapshot(ui::Screen screen) const {
  ui::UiSnapshot snapshot;
  buildSnapshot(&snapshot, screen);
  return snapshot;
}

}  // namespace sim
}  // namespace bukifon
