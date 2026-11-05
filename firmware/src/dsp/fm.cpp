// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/fm.hpp"

#include <cmath>

#include "core/math.hpp"
#include "dsp/wavetable.hpp"

namespace bukifon {
namespace {

// For every algorithm and operator (0 = carrier .. 3 = top), a bitmask of the
// operators that phase-modulate it.  Only operators with a higher index may
// modulate, which keeps evaluation order (3,2,1,0) acyclic.
constexpr uint8_t kFmRouting[kFmAlgorithms][kFmOperators] = {
    // 0: 4->3->2->1 stack
    {0b0010, 0b0100, 0b1000, 0b0000},
    // 1: stack plus 4->1
    {0b1010, 0b0100, 0b1000, 0b0000},
    // 2: 4->1, 3->2->1
    {0b1010, 0b0100, 0b0000, 0b0000},
    // 3: 4->2, 3->2, 2->1
    {0b0110, 0b1000, 0b0000, 0b0000},
    // 4: 4->2, 3->2, 2->1
    {0b0010, 0b1100, 0b0000, 0b0000},
    // 5: two independent pairs 4->3 and 2->1
    {0b0010, 0b0000, 0b1000, 0b0000},
    // 6: 4->2->1, 3->1
    {0b0110, 0b0000, 0b1000, 0b0000},
    // 7: 4->2->1 and 4->1 (branch)
    {0b1010, 0b0100, 0b1000, 0b0000},
};

constexpr float kPhaseScale = 4.0f;  // operator output -> radians

}  // namespace

void FmCore::init(float outputSampleRate) {
  outputRate_ = outputSampleRate;
  fmRate_ = outputSampleRate * static_cast<float>(kFmOversampling);
  lpG_ = math::tptG(19000.0f, fmRate_);
  reset();
}

void FmCore::reset() {
  for (int i = 0; i < kFmOperators; ++i) {
    phase_[i] = 0;
    lastOp_[i] = 0.0f;
  }
  for (int i = 0; i < 4; ++i) lpState_[i] = 0.0f;
}

void FmCore::setParams(int algorithm, const float ratios[kFmOperators],
                       const float levels[kFmOperators], float feedback) {
  algorithm_ = math::clampInt(algorithm, 0, kFmAlgorithms - 1);
  for (int i = 0; i < kFmOperators; ++i) {
    ratios_[i] = math::clamp(ratios[i], 0.25f, 32.0f);
    levels_[i] = math::clamp(levels[i], 0.0f, 1.0f);
  }
  feedback_ = math::clamp(feedback, 0.0f, 1.0f);
  setFrequency(frequency_);
}

void FmCore::setFrequency(float hz) {
  frequency_ = math::clamp(hz, 0.01f, outputRate_ * 0.49f);
  for (int i = 0; i < kFmOperators; ++i) {
    const float f = frequency_ * ratios_[i];
    inc_[i] = static_cast<uint32_t>(static_cast<double>(f) / fmRate_ * 4294967296.0);
  }
}

void FmCore::noteOn(float hz, float phase01) {
  const uint32_t p = static_cast<uint32_t>(phase01 * 4294967296.0f);
  for (int i = 0; i < kFmOperators; ++i) {
    phase_[i] = p;
    lastOp_[i] = 0.0f;
  }
  setFrequency(hz);
}

int FmCore::activeOperators() const {
  int n = 0;
  for (int i = 0; i < kFmOperators; ++i) {
    if (levels_[i] > 0.0f) ++n;
  }
  return n;
}

float FmCore::evaluateOversampled() {
  float out = 0.0f;
  const uint8_t* routing = kFmRouting[algorithm_];
  for (int op = kFmOperators - 1; op >= 0; --op) {
    float mod = 0.0f;
    const uint8_t mask = routing[op];
    for (int src = op + 1; src < kFmOperators; ++src) {
      if (mask & (1u << src)) mod += lastOp_[src];
    }
    phase_[op] += inc_[op];
    float pm = mod * kPhaseScale;
    if (op == kFmOperators - 1) pm += feedback_ * lastOp_[op] * kPhaseScale;
    // radians -> 32-bit phase offset (2^32 / 2*pi)
    const uint32_t phaseOffset =
        static_cast<uint32_t>(static_cast<int32_t>(pm * (4294967296.0f / (2.0f * math::kPi))));
    const float s = WavetableBank::samplePhase(4, kMipLevels - 1, phase_[op] + phaseOffset);
    lastOp_[op] = s * levels_[op];
    if (op == 0) out = lastOp_[op];
  }
  return out;
}

float FmCore::decimateFilter(float x) {
  float y = x;
  for (int i = 0; i < 4; ++i) {
    const float v = (y - lpState_[i]) * lpG_;
    y = v + lpState_[i];
    lpState_[i] = y + v;
  }
  return y;
}

float FmCore::tick() {
  const float s0 = evaluateOversampled();
  const float s1 = evaluateOversampled();
  const float y0 = decimateFilter(s0);
  const float y1 = decimateFilter(s1);
  return 0.5f * (y0 + y1);
}

}  // namespace bukifon
