// SPDX-License-Identifier: GPL-3.0-or-later
// 4-operator FM core with 8 algorithms, per-operator feedback and 2x
// oversampling (anti-aliasing) as required by spec/40-firmware.md §2.1.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

class FmCore {
 public:
  void init(float outputSampleRate = static_cast<float>(kSampleRate));
  void reset();

  // algorithm 0..7, ratios/levels 0..3 = operator 1..4, feedback 0..1.
  void setParams(int algorithm, const float ratios[kFmOperators],
                 const float levels[kFmOperators], float feedback);
  void setFrequency(float hz);
  void noteOn(float hz, float phase01 = 0.0f);

  // Renders one output-rate sample (2 oversampled FM samples + decimation).
  float tick();

  int algorithm() const { return algorithm_; }
  int activeOperators() const;

 private:
  float evaluateOversampled();
  float decimateFilter(float x);

  float outputRate_ = static_cast<float>(kSampleRate);
  float fmRate_ = static_cast<float>(kFmSampleRate);
  float frequency_ = 440.0f;
  float ratios_[kFmOperators] = {1.0f, 1.0f, 2.0f, 3.0f};
  float levels_[kFmOperators] = {1.0f, 0.5f, 0.3f, 0.2f};
  float feedback_ = 0.0f;
  int algorithm_ = 0;

  uint32_t phase_[kFmOperators] = {};
  uint32_t inc_[kFmOperators] = {};
  float lastOp_[kFmOperators] = {};

  // Decimation filter: 4 cascaded TPT one-poles at ~19 kHz (96 kHz domain).
  float lpState_[4] = {};
  float lpG_ = 0.5f;
};

}  // namespace bukifon
