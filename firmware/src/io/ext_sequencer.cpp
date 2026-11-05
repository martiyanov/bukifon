// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/ext_sequencer.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace bukifon {
namespace {

constexpr int kMidiClockPpqn = 24;
constexpr int kTicksPerStep = kMidiClockPpqn / 4;  // 16th notes

uint8_t clamp7(int value) { return static_cast<uint8_t>(value < 0 ? 0 : (value > 127 ? 127 : value)); }
uint8_t clampChannel(int value) { return static_cast<uint8_t>(value < 1 ? 1 : (value > 16 ? 16 : value)); }

void putU16(uint8_t* p, uint16_t v) {
  p[0] = static_cast<uint8_t>(v);
  p[1] = static_cast<uint8_t>(v >> 8);
}
void putU32(uint8_t* p, uint32_t v) {
  p[0] = static_cast<uint8_t>(v);
  p[1] = static_cast<uint8_t>(v >> 8);
  p[2] = static_cast<uint8_t>(v >> 16);
  p[3] = static_cast<uint8_t>(v >> 24);
}
uint16_t getU16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
uint32_t getU32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

}  // namespace

void ExtSequencer::init(float sampleRate) {
  sampleRate_ = sampleRate;
  bpm_ = 120.0f;
  swing_ = 0.0f;
  playing_ = false;
  clockMaster_ = true;
  clockSlave_ = false;
  sink_ = nullptr;
  maxJitterUs_ = 0.0f;
  clockCount_ = 0;
  slaveTicks_ = 0;
  clockAccumulator_ = 0.0;
  absoluteSamples_ = 0.0;
  lastClockTime_ = 0.0;
  for (int t = 0; t < kExtTracks; ++t) {
    tracks_[t] = ExtTrack{};
    tracks_[t].channel = static_cast<uint8_t>(t + 1);
    tracks_[t].program = static_cast<uint8_t>(t);
    gen_[t] = GenParams{};
    gen_[t].seed = static_cast<uint32_t>(1 + t * 17);
    arp_[t].setParams(gen_[t].arpRate, gen_[t].arpMode);
    runtime_[t] = Runtime{};
    lastRecordStep_[t] = -1;
    lastRecordNote_[t] = -1;
  }
}

ExtTrack& ExtSequencer::track(int index) {
  static ExtTrack fallback;
  if (index < 0 || index >= kExtTracks) return fallback;
  return tracks_[index];
}
const ExtTrack& ExtSequencer::track(int index) const {
  static const ExtTrack fallback;
  return (index >= 0 && index < kExtTracks) ? tracks_[index] : fallback;
}

void ExtSequencer::setChannel(int index, int channel) {
  if (index >= 0 && index < kExtTracks) tracks_[index].channel = clampChannel(channel);
}
void ExtSequencer::setProgram(int index, int program) {
  if (index >= 0 && index < kExtTracks) tracks_[index].program = clamp7(program);
}
void ExtSequencer::setTrackMuted(int index, bool muted) {
  if (index >= 0 && index < kExtTracks) tracks_[index].muted = muted;
}
bool ExtSequencer::trackMuted(int index) const {
  return index >= 0 && index < kExtTracks && tracks_[index].muted;
}

void ExtSequencer::setPlaying(bool playing) {
  if (playing && !playing_) {
    start();
  } else if (!playing && playing_) {
    stop();
  }
}

void ExtSequencer::start() {
  playing_ = true;
  clockAccumulator_ = 0.0;
  lastClockTime_ = absoluteSamples_;
  idealClockSample_ = absoluteSamples_ + sampleRate_ * 60.0 / bpm_ / 24.0;
  slaveTicks_ = 0;
  for (int t = 0; t < kExtTracks; ++t) {
    runtime_[t] = Runtime{};
    runtime_[t].untilNext = 0.0;
  }
  emitProgramChanges();
  if (sink_) sink_->onExtStart();
}

void ExtSequencer::stop() {
  playing_ = false;
  for (int t = 0; t < kExtTracks; ++t) noteOffIfPending(t);
  if (sink_) sink_->onExtStop();
}

void ExtSequencer::continuePlay() {
  playing_ = true;
  if (sink_) sink_->onExtContinue();
}

float ExtSequencer::stepLengthSamples() const {
  return sampleRate_ * 60.0f / bpm_ / 4.0f;
}

int ExtSequencer::currentStep(int trackIndex) const {
  if (trackIndex < 0 || trackIndex >= kExtTracks) return 0;
  const ExtTrack& t = tracks_[trackIndex];
  if (t.steps[runtime_[trackIndex].step].active) return runtime_[trackIndex].step;
  return runtime_[trackIndex].step;
}
uint32_t ExtSequencer::passCount(int trackIndex) const {
  return (trackIndex >= 0 && trackIndex < kExtTracks) ? runtime_[trackIndex].pass : 0;
}

void ExtSequencer::setGenParams(int index, const GenParams& params) {
  if (index < 0 || index >= kExtTracks) return;
  gen_[index] = params;
  arp_[index].setParams(params.arpRate, params.arpMode);
}
const GenParams& ExtSequencer::genParams(int index) const {
  static const GenParams kNeutral;
  return (index >= 0 && index < kExtTracks) ? gen_[index] : kNeutral;
}
GenParams& ExtSequencer::genParams(int index) {
  static GenParams fallback;
  if (index < 0 || index >= kExtTracks) return fallback;
  return gen_[index];
}

void ExtSequencer::noteOffIfPending(int index) {
  Runtime& rt = runtime_[index];
  if (rt.pendingNote >= 0 && sink_) sink_->onExtNoteOff(index, rt.pendingChannel, rt.pendingNote);
  rt.pendingNote = -1;
  rt.noteOffCountdown = 0.0;
}

void ExtSequencer::triggerStep(int index) {
  ExtTrack& track = tracks_[index];
  Runtime& rt = runtime_[index];
  const int stepIndex = rt.step % kExtSteps;
  ExtStep& step = track.steps[stepIndex];
  const GenParams& gen = gen_[index];
  if (!track.muted && step.active) {
    int note = step.note;
    int velocity = step.velocity;
    const int globalStep = static_cast<int>(rt.pass) * kExtSteps + stepIndex;
    GenStepResult generated = genApplyStep(gen, index, globalStep, note, velocity);
    if (gen.arpOn) {
      uint8_t held[16];
      int heldCount = 0;
      for (int s = 0; s < kExtSteps && heldCount < 16; ++s) {
        if (track.steps[s].active) held[heldCount++] = track.steps[s].note;
      }
      const int arpNote = arp_[index].noteAt(held, heldCount,
                                             static_cast<uint32_t>(globalStep) * 2u);
      if (arpNote >= 0) {
        generated.note = genScaleLockNote(arpNote, gen.scale);
        generated.trigger = true;
      }
    }
    if (generated.trigger) {
      noteOffIfPending(index);
      if (sink_) sink_->onExtNoteOn(index, track.channel, generated.note, generated.velocity);
      rt.pendingNote = generated.note;
      rt.pendingChannel = track.channel;
      rt.noteOffCountdown = static_cast<double>(stepLengthSamples()) * step.length / 100.0;
    }
  }
  // 1 CC p-lock per step (CC# is per track, value per step).
  if (step.ccPlocked && sink_) {
    sink_->onExtControlChange(index, track.channel, track.ccNumber, step.ccValue);
  }
  rt.step = (rt.step + 1) % kExtSteps;
  if (rt.step == 0) ++rt.pass;
}

void ExtSequencer::process(int samples) {
  for (int i = 0; i < samples; ++i) {
    ++absoluteSamples_;
    if (!playing_ || clockSlave_) continue;
    for (int t = 0; t < kExtTracks; ++t) {
      Runtime& rt = runtime_[t];
      if (rt.pendingNote >= 0) {
        rt.noteOffCountdown -= 1.0;
        if (rt.noteOffCountdown <= 0.0) noteOffIfPending(t);
      }
      rt.untilNext -= 1.0;
      if (rt.untilNext <= 0.0) {
        triggerStep(t);
        double stepSamples = stepLengthSamples();
        // Swing pushes the odd steps later (global swing, docs/70 §4).
        if ((rt.step % 2) == 1) stepSamples *= 1.0 + swing_ * 0.5;
        else stepSamples *= 1.0 - swing_ * 0.5;
        rt.untilNext += stepSamples;
      }
    }
    if (clockMaster_) {
      const double quarterSamples = sampleRate_ * 60.0 / bpm_;
      const double tickSamples = quarterSamples / kMidiClockPpqn;
      clockAccumulator_ += 1.0;
      if (clockAccumulator_ >= tickSamples) {
        clockAccumulator_ -= tickSamples;
        ++clockCount_;
        // Jitter vs the ideal 24 ppqn grid (model/measurement, docs/70 §4).
        const double jitterSamples = std::fabs(absoluteSamples_ - idealClockSample_);
        const float jitterUs = static_cast<float>(jitterSamples * 1000000.0 / sampleRate_);
        if (jitterUs > maxJitterUs_) maxJitterUs_ = jitterUs;
        idealClockSample_ += tickSamples;
        lastClockTime_ = absoluteSamples_;
        if (sink_) sink_->onExtClock();
      }
    }
  }
}

void ExtSequencer::emitProgramChanges() {
  if (!sink_) return;
  for (int t = 0; t < kExtTracks; ++t) {
    if (!tracks_[t].muted) sink_->onExtProgramChange(t, tracks_[t].channel, tracks_[t].program);
  }
}

void ExtSequencer::onClockIn() {
  if (!clockSlave_) return;
  ++slaveTicks_;
  if (slaveTicks_ < kTicksPerStep) return;
  slaveTicks_ = 0;
  for (int t = 0; t < kExtTracks; ++t) {
    Runtime& rt = runtime_[t];
    if (rt.pendingNote >= 0) noteOffIfPending(t);
    triggerStep(t);
  }
}

void ExtSequencer::liveRecordNoteOn(int trackIndex, int note, int velocity, int quantizedStep) {
  if (trackIndex < 0 || trackIndex >= kExtTracks) return;
  int step = quantizedStep;
  if (step < 0) step = runtime_[trackIndex].step;
  step %= kExtSteps;
  ExtTrack& track = tracks_[trackIndex];
  ExtStep& target = track.steps[step];
  target.active = true;
  target.note = clamp7(note);
  target.velocity = clamp7(velocity);
  target.length = 50;
  lastRecordStep_[trackIndex] = step;
  lastRecordNote_[trackIndex] = note;
}

void ExtSequencer::liveRecordNoteOff(int trackIndex, int note, int quantizedStep) {
  if (trackIndex < 0 || trackIndex >= kExtTracks) return;
  int step = quantizedStep;
  if (step < 0) step = runtime_[trackIndex].step;
  step %= kExtSteps;
  ExtTrack& track = tracks_[trackIndex];
  if (note >= 0) {
    for (int s = 0; s < kExtSteps; ++s) {
      if (track.steps[s].active && track.steps[s].note == note) {
        // Quantized gate: length up to 100 % of one step (simple live record).
        int length = 50;
        if (lastRecordStep_[trackIndex] >= 0) {
          int delta = (step - lastRecordStep_[trackIndex] + kExtSteps) % kExtSteps;
          length = 10 + delta * 80 / kExtSteps;
        }
        track.steps[s].length = static_cast<uint8_t>(length > 100 ? 100 : length);
      }
    }
  }
  lastRecordStep_[trackIndex] = -1;
  lastRecordNote_[trackIndex] = -1;
}

size_t ExtSequencer::serializedSize() const {
  // magic+version + 8 tracks*(channel,program,muted,ccNumber + 16 steps*6) + crc
  return 4 + 2 + kExtTracks * (4 + kExtSteps * 6) + 4;
}

uint32_t ExtSequencer::crc32(const uint8_t* data, size_t size) {
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < size; ++i) {
    crc ^= data[i];
    for (int k = 0; k < 8; ++k) crc = (crc >> 1) ^ (0xEDB88320u & (~(crc & 1u) + 1u));
  }
  return crc ^ 0xFFFFFFFFu;
}

size_t ExtSequencer::serialize(uint8_t* out, size_t capacity) const {
  const size_t size = serializedSize();
  if (!out || capacity < size) return 0;
  size_t pos = 0;
  putU32(out + pos, kMagic);
  pos += 4;
  putU16(out + pos, kVersion);
  pos += 2;
  for (int t = 0; t < kExtTracks; ++t) {
    out[pos++] = tracks_[t].channel;
    out[pos++] = tracks_[t].program;
    out[pos++] = tracks_[t].muted ? 1 : 0;
    out[pos++] = tracks_[t].ccNumber;
    for (int s = 0; s < kExtSteps; ++s) {
      const ExtStep& step = tracks_[t].steps[s];
      out[pos++] = step.active ? 1 : 0;
      out[pos++] = step.ccPlocked ? 1 : 0;
      out[pos++] = step.note;
      out[pos++] = step.velocity;
      out[pos++] = step.length;
      out[pos++] = step.ccValue;
    }
  }
  const uint32_t crc = crc32(out, pos);
  putU32(out + pos, crc);
  pos += 4;
  return pos;
}

bool ExtSequencer::deserialize(const uint8_t* data, size_t size) {
  const size_t expected = serializedSize();
  if (!data || size < expected) return false;
  if (getU32(data) != kMagic || getU16(data + 4) != kVersion) return false;
  const uint32_t storedCrc = getU32(data + expected - 4);
  if (crc32(data, expected - 4) != storedCrc) return false;
  ExtSequencer loaded;
  loaded.init(sampleRate_);
  size_t pos = 6;
  for (int t = 0; t < kExtTracks; ++t) {
    loaded.tracks_[t].channel = clampChannel(data[pos++]);
    loaded.tracks_[t].program = clamp7(data[pos++]);
    loaded.tracks_[t].muted = data[pos++] != 0;
    loaded.tracks_[t].ccNumber = clamp7(data[pos++]);
    for (int s = 0; s < kExtSteps; ++s) {
      ExtStep& step = loaded.tracks_[t].steps[s];
      step.active = data[pos++] != 0;
      step.ccPlocked = data[pos++] != 0;
      step.note = clamp7(data[pos++]);
      step.velocity = clamp7(data[pos++]);
      step.length = data[pos++];
      step.ccValue = clamp7(data[pos++]);
    }
  }
  for (int t = 0; t < kExtTracks; ++t) {
    tracks_[t] = loaded.tracks_[t];
    gen_[t] = gen_[t];
  }
  return true;
}

void MidiOutRouter::clear() {
  dinCount_ = 0;
  usbCount_ = 0;
  tick_ = 0;
}

MidiOutMessage MidiOutRouter::make(uint8_t status, uint8_t d1, uint8_t d2) const {
  MidiOutMessage message;
  message.tick = tick_;
  message.status = status;
  message.data1 = d1;
  message.data2 = d2;
  return message;
}

void MidiOutRouter::send(const MidiOutMessage& message) {
  if (dinCount_ < kMaxMessages) din_[dinCount_++] = message;
  if (usbCount_ < kMaxMessages) usb_[usbCount_++] = message;
  ++tick_;
}

bool MidiOutRouter::hasDuplicates() const {
  for (int i = 1; i < dinCount_; ++i) {
    if (din_[i].tick == din_[i - 1].tick && din_[i].status == din_[i - 1].status &&
        din_[i].data1 == din_[i - 1].data1 && din_[i].data2 == din_[i - 1].data2) {
      return true;
    }
  }
  for (int i = 1; i < usbCount_; ++i) {
    if (usb_[i].tick == usb_[i - 1].tick && usb_[i].status == usb_[i - 1].status &&
        usb_[i].data1 == usb_[i - 1].data1 && usb_[i].data2 == usb_[i - 1].data2) {
      return true;
    }
  }
  return false;
}

void RouterExtSink::onExtNoteOn(int, int channel, int note, int velocity) {
  router_->send(router_->make(static_cast<uint8_t>(0x90 | ((channel - 1) & 0x0F)),
                             clamp7(note), clamp7(velocity)));
}
void RouterExtSink::onExtNoteOff(int, int channel, int note) {
  router_->send(router_->make(static_cast<uint8_t>(0x80 | ((channel - 1) & 0x0F)), clamp7(note), 0));
}
void RouterExtSink::onExtProgramChange(int, int channel, int program) {
  router_->send(router_->make(static_cast<uint8_t>(0xC0 | ((channel - 1) & 0x0F)), clamp7(program), 0));
}
void RouterExtSink::onExtControlChange(int, int channel, int cc, int value) {
  router_->send(router_->make(static_cast<uint8_t>(0xB0 | ((channel - 1) & 0x0F)), clamp7(cc),
                             clamp7(value)));
}
void RouterExtSink::onExtClock() { router_->send(router_->make(0xF8, 0, 0)); }
void RouterExtSink::onExtStart() { router_->send(router_->make(0xFA, 0, 0)); }
void RouterExtSink::onExtStop() { router_->send(router_->make(0xFC, 0, 0)); }
void RouterExtSink::onExtContinue() { router_->send(router_->make(0xFB, 0, 0)); }

}  // namespace bukifon
