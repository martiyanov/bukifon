// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/ensemble.hpp"

#include <cmath>

#include "core/math.hpp"

namespace bukifon {
namespace {
constexpr float kBaseDelayMs = 7.0f;
constexpr float kModDepthMs = 3.5f;
}  // namespace

void Ensemble::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
}

void Ensemble::reset() {
  for (int c = 0; c < 2; ++c)
    for (int i = 0; i < kChorusMaxSamples; ++i) delayLine_[c][i] = 0.0f;
  writeIndex_ = 0;
}

void Ensemble::setAmount(float amount) { amount_ = math::clamp(amount, 0.0f, 1.0f); }
void Ensemble::setRate(float hz) { rate_ = math::clamp(hz, 0.02f, 10.0f); }

float Ensemble::readDelay(int channel, float delaySamples) const {
  // Linear interpolation with wrap-around.
  float d = delaySamples;
  while (d < 0.0f) d += static_cast<float>(kChorusMaxSamples);
  const float pos = static_cast<float>(writeIndex_) - d;
  int i0 = static_cast<int>(std::floor(pos));
  const float frac = pos - static_cast<float>(i0);
  int i1 = i0 + 1;
  i0 %= kChorusMaxSamples;
  if (i0 < 0) i0 += kChorusMaxSamples;
  i1 %= kChorusMaxSamples;
  if (i1 < 0) i1 += kChorusMaxSamples;
  return delayLine_[channel][i0] * (1.0f - frac) + delayLine_[channel][i1] * frac;
}

void Ensemble::process(float* l, float* r, int n) {
  if (amount_ <= 0.0f) {
    for (int i = 0; i < n; ++i) {
      delayLine_[0][writeIndex_] = l[i];
      delayLine_[1][writeIndex_] = r[i];
      writeIndex_ = (writeIndex_ + 1) % kChorusMaxSamples;
    }
    return;
  }
  const float sr = sampleRate_;
  const float phaseInc = rate_ / sr;
  const float base = kBaseDelayMs * 0.001f * sr;
  const float depth = kModDepthMs * 0.001f * sr;
  for (int i = 0; i < n; ++i) {
    delayLine_[0][writeIndex_] = l[i];
    delayLine_[1][writeIndex_] = r[i];

    float wetL = 0.0f, wetR = 0.0f;
    for (int v = 0; v < 3; ++v) {
      phase_[v] += phaseInc * (1.0f + 0.13f * static_cast<float>(v));
      if (phase_[v] >= 1.0f) phase_[v] -= 1.0f;
      const float lfo = std::sin(math::kTwoPi * phase_[v]);
      const float dL = base + depth * lfo;
      const float dR = base + depth * std::sin(math::kTwoPi * (phase_[v] + 0.5f));
      wetL += readDelay(0, dL);
      wetR += readDelay(1, dR);
    }
    wetL *= (1.0f / 3.0f);
    wetR *= (1.0f / 3.0f);
    lastDelayMs_ = (base + depth) / sr * 1000.0f;
    const float dry = 1.0f - amount_ * 0.5f;
    l[i] = l[i] * dry + wetL * amount_ * 0.8f;
    r[i] = r[i] * dry + wetR * amount_ * 0.8f;
    writeIndex_ = (writeIndex_ + 1) % kChorusMaxSamples;
  }
}

}  // namespace bukifon
