// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/lfo.hpp"

#include <cmath>

namespace bukifon {

void Lfo::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
}

void Lfo::reset() {
  phase_ = 0.0f;
  fadePos_ = (fadeS_ > 0.0f) ? 0.0f : 1.0f;
  value_ = 0.0f;
  smoothValue_ = 0.0f;
  randomTarget_ = 0.0f;
  rng_ = 0x2545F491u;
}

void Lfo::setParams(float rateHz, int shape, bool sync, bool retrigger, float keytrack, float fadeS,
                    float bpm) {
  rateHz_ = math::clamp(rateHz, 0.02f, 2000.0f);
  shape_ = math::clampInt(shape, 0, kNumLfoShapes - 1);
  sync_ = sync;
  retrigger_ = retrigger;
  keytrack_ = math::clamp(keytrack, 0.0f, 1.0f);
  fadeS_ = math::clamp(fadeS, 0.0f, 20.0f);
  bpm_ = bpm;
  if (fadePos_ > 0.0f && fadeS_ <= 0.0f) fadePos_ = 1.0f;
}

void Lfo::noteOn(float midiNote) {
  note_ = midiNote;
  if (retrigger_) {
    phase_ = 0.0f;
    if (fadeS_ > 0.0f) fadePos_ = 0.0f;
  }
}

void Lfo::setPhase(float phase01) { phase_ = phase01 - std::floor(phase01); }

float Lfo::render(float phase) const {
  switch (shape_) {
    case LfoSine:
      return std::sin(math::kTwoPi * phase);
    case LfoTriangle:
      return 1.0f - 4.0f * std::fabs(phase - 0.5f);
    case LfoSawUp:
      return 2.0f * phase - 1.0f;
    case LfoSawDown:
      return 1.0f - 2.0f * phase;
    case LfoSquare:
      return phase < 0.5f ? 1.0f : -1.0f;
    case LfoPulse25:
      return phase < 0.25f ? 1.0f : -1.0f;
    case LfoSampleHold:
    case LfoSmoothRandom:
      return randomTarget_;
    default:
      return 0.0f;
  }
}

float Lfo::tickN(int n) {
  if (n <= 0) return value_;
  float hz = rateHz_;
  if (sync_) hz = (bpm_ / 60.0f) * (rateHz_ / 4.0f);
  if (keytrack_ > 0.0f) hz *= std::pow(2.0f, (note_ - 60.0f) / 12.0f * keytrack_);
  hz = math::clamp(hz, 0.001f, 2000.0f);
  phase_ += hz * static_cast<float>(n) / sampleRate_;
  bool wrapped = false;
  while (phase_ >= 1.0f) {
    phase_ -= 1.0f;
    wrapped = true;
  }
  if ((shape_ == LfoSampleHold || shape_ == LfoSmoothRandom) && wrapped) {
    rng_ ^= rng_ << 13;
    rng_ ^= rng_ >> 17;
    rng_ ^= rng_ << 5;
    randomTarget_ = static_cast<float>(static_cast<int32_t>(rng_)) * (1.0f / 2147483648.0f);
  }
  if (shape_ == LfoSmoothRandom) {
    smoothValue_ += (randomTarget_ - smoothValue_) * 0.25f;
    value_ = smoothValue_;
  } else {
    value_ = render(phase_);
  }
  if (fadeS_ > 0.0f && fadePos_ < 1.0f) {
    fadePos_ = math::clamp(fadePos_ + static_cast<float>(n) / (fadeS_ * sampleRate_), 0.0f, 1.0f);
    value_ *= fadePos_;
  }
  return value_;
}

float Lfo::tick() {
  // Effective rate: sync ties the LFO to the tempo (rate parameter = beats).
  float hz = rateHz_;
  if (sync_) hz = (bpm_ / 60.0f) * (rateHz_ / 4.0f);
  if (keytrack_ > 0.0f) hz *= std::pow(2.0f, (note_ - 60.0f) / 12.0f * keytrack_);
  hz = math::clamp(hz, 0.001f, 2000.0f);

  phase_ += hz / sampleRate_;
  bool wrapped = false;
  if (phase_ >= 1.0f) {
    phase_ -= std::floor(phase_);
    wrapped = true;
  }
  if (shape_ == LfoSampleHold && wrapped) {
    rng_ ^= rng_ << 13;
    rng_ ^= rng_ >> 17;
    rng_ ^= rng_ << 5;
    randomTarget_ = static_cast<float>(static_cast<int32_t>(rng_)) * (1.0f / 2147483648.0f);
  } else if (shape_ == LfoSmoothRandom) {
    if (wrapped) {
      rng_ ^= rng_ << 13;
      rng_ ^= rng_ >> 17;
      rng_ ^= rng_ << 5;
      randomTarget_ = static_cast<float>(static_cast<int32_t>(rng_)) * (1.0f / 2147483648.0f);
    }
    // One-pole smoothing of the random target.
    const float coef = math::clamp(hz / sampleRate_ * 8.0f, 0.001f, 0.5f);
    smoothValue_ += (randomTarget_ - smoothValue_) * coef;
    value_ = smoothValue_;
  } else {
    value_ = render(phase_);
  }

  if (fadeS_ > 0.0f && fadePos_ < 1.0f) {
    fadePos_ = math::clamp(fadePos_ + 1.0f / (fadeS_ * sampleRate_), 0.0f, 1.0f);
    value_ *= fadePos_;
  }
  return value_;
}

}  // namespace bukifon
