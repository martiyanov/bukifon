// SPDX-License-Identifier: GPL-3.0-or-later
// LFO: 8 shapes, free/sync, retrigger, keytrack, fade-in, audio-rate capable.
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "core/math.hpp"

namespace bukifon {

enum LfoShape : uint8_t {
  LfoSine = 0,
  LfoTriangle,
  LfoSawUp,
  LfoSawDown,
  LfoSquare,
  LfoSampleHold,
  LfoSmoothRandom,
  LfoPulse25,
  kNumLfoShapes
};

class Lfo {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();
  void setParams(float rateHz, int shape, bool sync, bool retrigger, float keytrack, float fadeS,
                 float bpm);
  void noteOn(float midiNote);
  float tick();
  // Advances by n samples in one step (control-rate matrix sources).
  float tickN(int n);
  float value() const { return value_; }
  void setPhase(float phase01);

 private:
  float render(float phase) const;

  float sampleRate_ = static_cast<float>(kSampleRate);
  float rateHz_ = 2.0f;
  float fadeS_ = 0.0f;
  float bpm_ = 120.0f;
  float note_ = 60.0f;
  float keytrack_ = 0.0f;
  int shape_ = LfoSine;
  bool sync_ = false;
  bool retrigger_ = true;
  float phase_ = 0.0f;
  float fadePos_ = 1.0f;
  float value_ = 0.0f;
  float randomTarget_ = 0.0f;
  float smoothValue_ = 0.0f;
  uint32_t rng_ = 0x2545F491u;
};

}  // namespace bukifon
