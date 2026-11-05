// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/effects.hpp"

#include <cmath>

#include "core/math.hpp"

namespace bukifon {

// --- StereoDelay -----------------------------------------------------------
void StereoDelay::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
  setTime(0.25f);
}

void StereoDelay::reset() {
  for (int c = 0; c < 2; ++c)
    for (int i = 0; i < kDelayMaxSamples; ++i) buffer_[c][i] = 0;
  write_ = 0;
  dampState_[0] = dampState_[1] = 0.0f;
}

void StereoDelay::setTime(float seconds) {
  timeSamples_ = math::clamp(seconds, 0.001f, static_cast<float>(kDelayMaxSamples - 4) / sampleRate_) *
                 sampleRate_;
}
void StereoDelay::setFeedback(float feedback) { feedback_ = math::clamp(feedback, 0.0f, 0.95f); }
void StereoDelay::setMix(float mix) { mix_ = math::clamp(mix, 0.0f, 1.0f); }
void StereoDelay::setPingPong(bool pingPong) { pingPong_ = pingPong; }
void StereoDelay::setDamping(float hz) {
  damp_ = math::clamp((hz * 0.001f) * (sampleRate_ / 48000.0f), 0.01f, 0.99f);
}

float StereoDelay::read(int channel, float delaySamples) const {
  float pos = static_cast<float>(write_) - delaySamples;
  while (pos < 0.0f) pos += static_cast<float>(kDelayMaxSamples);
  const int i0 = static_cast<int>(pos) % kDelayMaxSamples;
  const float frac = pos - std::floor(pos);
  const int i1 = (i0 + 1) % kDelayMaxSamples;
  const float a = static_cast<float>(buffer_[channel][i0]) * (1.0f / 32768.0f);
  const float b = static_cast<float>(buffer_[channel][i1]) * (1.0f / 32768.0f);
  return a + (b - a) * frac;
}

void StereoDelay::process(float* l, float* r, int n) {
  for (int i = 0; i < n; ++i) {
    const float dl = read(0, timeSamples_);
    const float dr = read(1, timeSamples_);
    // Damping lowpass in the feedback path.
    dampState_[0] += (dl - dampState_[0]) * damp_;
    dampState_[1] += (dr - dampState_[1]) * damp_;
    const float fbL = (pingPong_ ? dampState_[1] : dampState_[0]) * feedback_;
    const float fbR = (pingPong_ ? dampState_[0] : dampState_[1]) * feedback_;
    buffer_[0][write_] = static_cast<int16_t>(math::clamp((l[i] + fbL) * 32767.0f, -32767.0f, 32767.0f));
    buffer_[1][write_] = static_cast<int16_t>(math::clamp((r[i] + fbR) * 32767.0f, -32767.0f, 32767.0f));
    write_ = (write_ + 1) % kDelayMaxSamples;
    l[i] = l[i] * (1.0f - mix_ * 0.5f) + dl * mix_;
    r[i] = r[i] * (1.0f - mix_ * 0.5f) + dr * mix_;
  }
}

// --- DriveFx ---------------------------------------------------------------
void DriveFx::init() { reset(); }
void DriveFx::setAmount(float a) { amount_ = math::clamp(a, 0.0f, 1.0f); }
void DriveFx::setTone(float t) { tone_ = math::clamp(t, 0.0f, 1.0f); }
void DriveFx::setMix(float m) { mix_ = math::clamp(m, 0.0f, 1.0f); }

void DriveFx::process(float* l, float* r, int n) {
  const float gain = 1.0f + amount_ * 12.0f;
  const float comp = 1.0f / (1.0f + amount_ * 3.0f);
  const float lpCoef = math::clamp(0.02f + tone_ * 0.6f, 0.01f, 0.99f);
  for (int i = 0; i < n; ++i) {
    const float dl = math::fastTanh(l[i] * gain) * comp;
    const float dr = math::fastTanh(r[i] * gain) * comp;
    lp_ += ((dl + dr) * 0.5f - lp_) * lpCoef;
    l[i] = l[i] * (1.0f - mix_) + dl * mix_;
    r[i] = r[i] * (1.0f - mix_) + dr * mix_;
  }
}

// --- BitcrushFx ------------------------------------------------------------
void BitcrushFx::init() { reset(); }
void BitcrushFx::setBits(float bits) { bits_ = math::clampInt(static_cast<int>(bits + 0.5f), 1, 16); }
void BitcrushFx::setRate(float rate) { rate_ = math::clamp(rate, 0.0f, 1.0f); }
void BitcrushFx::setMix(float mix) { mix_ = math::clamp(mix, 0.0f, 1.0f); }

void BitcrushFx::process(float* l, float* r, int n) {
  if (mix_ <= 0.0f) return;
  const int hold = 1 + static_cast<int>(rate_ * 63.0f);
  const float step = 1.0f / static_cast<float>((1 << (bits_ - 1)));
  for (int i = 0; i < n; ++i) {
    if (holdCounter_ <= 0) {
      holdL_ = std::floor(l[i] / step + 0.5f) * step;
      holdR_ = std::floor(r[i] / step + 0.5f) * step;
      holdCounter_ = hold;
    }
    --holdCounter_;
    l[i] = l[i] * (1.0f - mix_) + holdL_ * mix_;
    r[i] = r[i] * (1.0f - mix_) + holdR_ * mix_;
  }
}

// --- Limiter ---------------------------------------------------------------
void Limiter::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
  setThreshold(0.95f);
  setRelease(0.2f);
}
void Limiter::setThreshold(float t) { threshold_ = math::clamp(t, 0.3f, 1.0f); }
void Limiter::setRelease(float s) {
  const float t = math::clamp(s, 0.01f, 2.0f) * sampleRate_;
  releaseCoef_ = std::exp(-1.0f / t);
}

void Limiter::process(float* l, float* r, int n) {
  const float invThr = 1.0f / threshold_;
  for (int i = 0; i < n; ++i) {
    const float peak = std::fmax(std::fabs(l[i]), std::fabs(r[i]));
    env_ = (peak > env_) ? peak : env_ * releaseCoef_ + peak * (1.0f - releaseCoef_);
    float gain = 1.0f;
    if (env_ > threshold_) gain = threshold_ / env_;
    // Soft-knee safety clip: |out| stays strictly below threshold.
    float outL = math::fastTanh(l[i] * gain * invThr * 1.05f) * threshold_;
    float outR = math::fastTanh(r[i] * gain * invThr * 1.05f) * threshold_;
    l[i] = math::clamp(outL, -threshold_, threshold_);
    r[i] = math::clamp(outR, -threshold_, threshold_);
  }
}

// --- Dither ----------------------------------------------------------------
float Dither::tick() {
  rng_ ^= rng_ << 13;
  rng_ ^= rng_ >> 17;
  rng_ ^= rng_ << 5;
  const float a = static_cast<float>(static_cast<int32_t>(rng_)) * (1.0f / 2147483648.0f);
  rng_ ^= rng_ << 13;
  rng_ ^= rng_ >> 17;
  rng_ ^= rng_ << 5;
  const float b = static_cast<float>(static_cast<int32_t>(rng_)) * (1.0f / 2147483648.0f);
  return (a - b) * (1.0f / 32768.0f);
}

int16_t Dither::toPcm16(float x) {
  const float v = math::clamp(x + tick(), -1.0f, 1.0f);
  const float scaled = v * 32767.0f;
  const int32_t rounded = static_cast<int32_t>(scaled >= 0.0f ? scaled + 0.5f : scaled - 0.5f);
  return static_cast<int16_t>(math::clampInt(rounded, -32768, 32767));
}

}  // namespace bukifon
