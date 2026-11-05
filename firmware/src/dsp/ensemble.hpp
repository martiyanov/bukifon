// SPDX-License-Identifier: GPL-3.0-or-later
// Polyvox-style 3-voice ensemble / BBD chorus (digital model, per part).
#pragma once

#include <array>
#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

class Ensemble {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();
  void setAmount(float amount);   // 0..1 dry/wet
  void setRate(float hz);         // base LFO rate

  // Stereo in-place processing.
  void process(float* l, float* r, int n);

  float lastDelayMs() const { return lastDelayMs_; }

 private:
  float readDelay(int channel, float delaySamples) const;

  float sampleRate_ = static_cast<float>(kSampleRate);
  float amount_ = 0.0f;
  float rate_ = 0.5f;
  float phase_[3] = {0.0f, 0.33f, 0.66f};
  float delayLine_[2][kChorusMaxSamples] = {};
  int writeIndex_ = 0;
  float lastDelayMs_ = 0.0f;
};

}  // namespace bukifon
