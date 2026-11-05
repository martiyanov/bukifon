// SPDX-License-Identifier: GPL-3.0-or-later
// One of the four independent parts: timbre parameters, 4 envelopes, 4 LFOs and
// its own 16-slot 3D modulation matrix (Kaleidoscope-style, cross-part capable).
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "core/events.hpp"
#include "core/modulation_defs.hpp"
#include "core/params.hpp"
#include "dsp/envelope.hpp"
#include "dsp/lfo.hpp"

namespace bukifon {

struct ModContext {
  float cv[kNumCvIn] = {0, 0, 0, 0};
  float modWheel = 0.0f;
  float midiCc = 0.0f;
  float aftertouch = 0.0f;
  float velocity = 0.0f;
  float keytrack = 0.0f;
  float macros[kNumMacros] = {0, 0, 0, 0};
  float seqTrack[kSeqTracks] = {0, 0, 0, 0};
  float partOut[kNumParts] = {0, 0, 0, 0};
  uint32_t bar = 0;
  bool fill = false;
  bool firstOfBar = true;
  float bpm = 120.0f;
};

class Part {
 public:
  void init(int index, float sampleRate = static_cast<float>(kSampleRate));
  void reset();

  void setSlot(int index, const ModSlotData& slot);
  const ModSlotData& slot(int index) const { return slots_[index]; }
  ModSlotData& slotRef(int index) { return slots_[index]; }

  void setBaseParam(int id, float value);
  const PartParams& base() const { return base_; }
  const PartParams& params() const { return mod_; }
  PartParams& baseRef() { return base_; }

  // Called by the engine on part note events.
  void triggerNoteOn(float velocity, int note);
  void triggerNoteOff();

  // Advances envelopes/LFOs by `samples` (block control rate).
  void tickGenerators(int samples, float bpm);

  // Computes the 16 slot outputs (sources include the previous block's slots).
  void evaluateSlots(const ModContext& ctx, float globalSources[kNumModSources]);

  // Applies accumulated normalised modulation offsets to the output parameters.
  void applyOffsets(const float* paramOffsets, const float* slotDepthOffsets);

  float envLevel(int i) const { return envLevel_[i]; }
  float lfoValue(int i) const { return lfo_[i].value(); }
  const float* slotOutputs() const { return slotOut_; }
  float meter() const { return meter_; }
  void setMeter(float m) { meter_ = m; }
  int index() const { return index_; }
  const float* paramOffsets() const { return offsets_; }

 private:
  float evaluateSource(uint8_t source, const ModContext& ctx,
                       const float globalSources[kNumModSources]) const;
  static float applyCurve(float v, ModCurve curve);
  static bool evaluateCondition(ModCondition cond, const ModContext& ctx, uint32_t slotIndex);
  static float modulatedValue(int id, float base, float offset);

  int index_ = 0;
  float sampleRate_ = static_cast<float>(kSampleRate);

  PartParams base_{};
  PartParams mod_{};

  ModSlotData slots_[kModSlots] = {};
  Envelope env_[kNumEnvs];
  Lfo lfo_[kNumLfos];
  float envLevel_[kNumEnvs] = {};
  float slotOut_[kModSlots] = {};
  float slotPrev_[kModSlots] = {};
  float slotDepthMod_[kModSlots] = {};
  float offsets_[kNumPartParams] = {};
  float meter_ = 0.0f;
  float lastVelocity_ = 1.0f;
  int lastNote_ = 60;
  bool gateOn_ = false;
};

}  // namespace bukifon
