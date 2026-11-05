// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon audio engine: 4 independent parts, 8 shared voices, 16-slot 3D
// modulation matrix per part (cross-part + feedback), global FX chain.
// Portable C++17 with no Arduino dependencies (host tests + RP2040 core1).
#pragma once

#include <cstdint>

#include "audio/part.hpp"
#include "audio/voice.hpp"
#include "core/config.hpp"
#include "core/events.hpp"
#include "core/params.hpp"
#include "dsp/effects.hpp"
#include "io/arp.hpp"
#include "io/sequencer.hpp"

namespace bukifon {

class Engine : public SequencerSink, public ArpSink {
 public:
  static constexpr int kMaxBlock = kBlockSize;

  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();

  // --- parameter access (UI core0 writes, audio core1 reads) ---------------
  GlobalParams& globals() { return globalBase_; }
  const GlobalParams& globals() const { return globalBase_; }
  PartParams& partBase(int part) { return parts_[part].baseRef(); }
  const PartParams& partBase(int part) const { return parts_[part].base(); }
  const PartParams& partParams(int part) const { return parts_[part].params(); }
  void setGlobalParam(int id, float value);
  void setPartParam(int part, int id, float value);

  // --- note / performance API (also driven by events/MIDI) -----------------
  void noteOn(int note, int velocity, int part = 0, int channel = 0);
  void noteOff(int note, int part = 0);
  void allNotesOff();
  void setPitchBend(float normalized, int channel = 0);
  void setAftertouch(float value, int channel = 0);
  void setModWheel(float value);
  void setMidiCc(float normalized);
  void setCv(int index, float volts);
  void setMacro(int index, float value);
  float macro(int index) const { return (index >= 0 && index < kNumMacros) ? macros_[index] : 0.0f; }
  void setTransport(bool running);
  void setFillMode(bool fill);
  void loadFactoryPatch(int index);

  // --- rendering ------------------------------------------------------------
  // Renders `n` stereo samples (n <= kBlockSize) into outL/outR (additive is NOT
  // used: buffers are overwritten).
  void process(float* outL, float* outR, int n);

  // --- telemetry / event plumbing ------------------------------------------
  EventQueue& eventQueue() { return events_; }
  TelemetryQueue& telemetryQueue() { return telemetry_; }
  bool popTelemetry(Telemetry* t) { return telemetry_.pop(t); }

  int activeVoices() const;
  int voicesInPart(int part) const;
  float partMeter(int part) const { return parts_[part].meter(); }
  const PartParams& modulatedPartParams(int part) const { return parts_[part].params(); }
  const GlobalParams& modulatedGlobals() const { return globalMod_; }
  float cpuLoad() const { return cpuLoad_; }
  void setCpuLoad(float load) { cpuLoad_ = load; }
  Dither& dither() { return dither_; }
  const Telemetry& lastTelemetry() const { return lastTelemetry_; }
  float sampleRate() const { return sampleRate_; }

  Part& part(int i) { return parts_[i]; }
  const Part& part(int i) const { return parts_[i]; }
  void setSequencer(Sequencer* seq) {
    sequencer_ = seq;
    if (seq) seq->setSink(this);
  }

  // SequencerSink / ArpSink (engine plays the sequenced/arpeggiated notes).
  void onSeqNoteOn(int track, int note, int velocity) override;
  void onSeqNoteOff(int track, int note) override;
  void onSeqPlock(int track, int param, float normalized) override;
  void onSeqSoundLock(int track, int preset) override;
  void onArpNoteOn(int part, int note, int velocity) override;
  void onArpNoteOff(int part, int note) override;
  float seqParamBase(int track, int param) const override;
  void onSeqPlockRestore(int track, int param) override;

  // Direct slot editing helper (also used by UI / patch loading).
  void setModSlot(int part, int slot, const ModSlotData& data);
  const ModSlotData& modSlot(int part, int slot) const { return parts_[part].slot(slot); }

 private:
  void handleEvent(const Event& e);
  void triggerNote(int note, int velocity, int part, int channel);
  int allocateVoice(int part, int note, int velocity, int channel);
  int findVoice(int note, int part) const;
  void updateModulation(int n);
  void applyGlobalOffsets();
  void applyGlobalMod(int id, float offset);
  float velocityForPart(int part) const;
  float keytrackForPart(int part) const;
  EventQueue& eventsRef() { return events_; }

  float sampleRate_ = static_cast<float>(kSampleRate);
  Part parts_[kNumParts];
  Voice voices_[kMaxVoices];
  GlobalParams globalBase_{};
  GlobalParams globalMod_{};
  float globalOffsets_[kNumGlobalParams] = {};
  float partOffsets_[kNumParts][kNumPartParams] = {};
  float slotDepthOffsets_[kNumParts][kModSlots] = {};
  float plockSaved_[kNumParts][kNumPartParams] = {};
  bool plockSavedValid_[kNumParts][kNumPartParams] = {};
  ModContext modCtx_[kNumParts];

  float bend_[16] = {};
  float aftertouch_[16] = {};
  float modWheel_ = 0.0f;
  float midiCc_ = 0.0f;
  float cvVolts_[kNumCvIn] = {};
  float macros_[kNumMacros] = {};
  bool transport_ = false;
  bool fill_ = false;
  uint32_t clockTicks_ = 0;

  // Part output buffers (stereo per part).
  float partL_[kNumParts][kBlockSize] = {};
  float partR_[kNumParts][kBlockSize] = {};
  float busL_[kBlockSize] = {};
  float busR_[kBlockSize] = {};

  // Per-part FX.
  BitcrushFx partCrush_[kNumParts];
  Ensemble partEnsemble_[kNumParts];

  // Global FX.
  DriveFx drive_;
  Ensemble chorus_;
  StereoDelay delay_;
  Limiter limiter_;
  Dither dither_;

  EventQueue events_;
  TelemetryQueue telemetry_;
  Telemetry lastTelemetry_;
  float cpuLoad_ = 0.0f;
  Sequencer* sequencer_ = nullptr;
  Arpeggiator arps_[kNumParts];
  int lastVoicePart_[kMaxVoices] = {};
  bool lastVoiceActive_[kMaxVoices] = {};
};

}  // namespace bukifon
