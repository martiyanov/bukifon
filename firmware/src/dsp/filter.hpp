// SPDX-License-Identifier: GPL-3.0-or-later
// Per-part filter: ZDF SVF (LP/BP/HP/Notch, 12/24 dB), Moog-style 4-pole ZDF
// ladder with saturation, and the Polyvox formant character.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum FilterCharacter : uint8_t {
  CharSvf = 0,
  CharMoog = 1,
  CharPolyvox = 2,
  kNumFilterChars = 3
};

enum FilterMode : uint8_t {
  Fm_LP24 = 0,
  Fm_LP12 = 1,
  Fm_BP = 2,
  Fm_HP = 3,
  Fm_Notch = 4,
  kNumFilterModes = 5
};

class Filter {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();

  void setCharacter(int character);
  void setMode(int mode);
  void setCutoff(float hz);
  void setResonance(float r);   // 0..1
  void setDrive(float drive);   // 0..1

  float process(float x);
  float lastLowpass() const { return lastLp_; }

 private:
  float processSvf(float x);
  float processLadder(float x);
  float processPolyvox(float x);
  void updateCoefficients();

  float sampleRate_ = static_cast<float>(kSampleRate);
  int character_ = CharMoog;
  int mode_ = Fm_LP24;
  float cutoff_ = 2000.0f;
  float resonance_ = 0.2f;
  float drive_ = 0.1f;

  // SVF state (TPT)
  float g_ = 0.1f;
  float k_ = 1.5f;
  float a1_ = 0.0f, a2_ = 0.0f, a3_ = 0.0f;
  float ic1_ = 0.0f, ic2_ = 0.0f;

  // Second SVF stage for 24 dB / notch
  float ic1b_ = 0.0f, ic2b_ = 0.0f;

  // Moog ladder state (4 x TPT one-pole)
  float ladder_[4] = {};
  float G_ = 0.1f;
  float feedback_ = 0.0f;

  // Polyvox formant SVF states (3 bandpass)
  float formantIc1_[3] = {};
  float formantIc2_[3] = {};
  float formantG_[3] = {};

  float lastLp_ = 0.0f;
};

}  // namespace bukifon
