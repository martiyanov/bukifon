// SPDX-License-Identifier: GPL-3.0-or-later
// Wavetable oscillator with unison, sync, waveshaper/folder/ring-mod modes.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum OscMode : uint8_t {
  OscWavetable = 0,
  OscAdditive = 1,
  OscWaveShaper = 2,
  OscWaveFolder = 3,
  OscHardSync = 4,
  OscRingMod = 5,
  kNumOscModes = 6
};

class Oscillator {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();

  void setWave(int wave);
  void setMode(int mode);
  void setFrequency(float hz);
  void setUnison(int count);
  void setDetune(float amount);    // 0..1 -> +/- 25 cents spread
  void setSpread(float amount);    // 0..1 -> initial phase spread
  void setPulseWidth(float pw);    // 0.02..0.98 (additive mode)
  void retrigger(float phase01 = 0.0f);
  void setVelocity(float v) { velocity_ = v; }

  float tick();
  int wave() const { return wave_; }
  int mode() const { return mode_; }

 private:
  float sampleRate_ = static_cast<float>(kSampleRate);
  float frequency_ = 440.0f;
  float detune_ = 0.0f;
  float spread_ = 0.0f;
  float pulseWidth_ = 0.5f;
  float velocity_ = 1.0f;
  int wave_ = 0;
  int mode_ = OscWavetable;
  int unison_ = 1;
  int mip_ = 0;
  uint32_t phase_[kMaxUnison] = {};
  uint32_t inc_[kMaxUnison] = {};
  uint32_t syncPhase_ = 0;
  uint32_t syncInc_ = 0;
  float lastMasterPhase_ = 0.0f;
};

}  // namespace bukifon
