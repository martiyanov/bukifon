// SPDX-License-Identifier: GPL-3.0-or-later
// Small portable DSP math helpers (no Arduino, no exceptions).
#pragma once

#include <cmath>
#include <cstdint>

namespace bukifon {
namespace math {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTwoPi = 2.0f * kPi;
constexpr float kInvTwoPi = 1.0f / kTwoPi;

template <typename T>
constexpr T clampT(T v, T lo, T hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}

inline float clamp(float v, float lo, float hi) { return clampT(v, lo, hi); }
inline int clampInt(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }

inline float lerp(float a, float b, float t) { return a + (b - a) * t; }

// MIDI note -> Hz, A4 = 440 Hz (note 69). Exact by definition.
inline float midiToHz(float note) {
  return 440.0f * std::pow(2.0f, (note - 69.0f) / 12.0f);
}

inline float hzToMidi(float hz) {
  return 69.0f + 12.0f * (std::log2(hz / 440.0f));
}

inline float centsToRatio(float cents) { return std::pow(2.0f, cents / 1200.0f); }

// Rational tanh approximation, monotone, |out| < 1. Max error ~1e-3.
inline float fastTanh(float x) {
  if (x < -3.0f) return -1.0f;
  if (x > 3.0f) return 1.0f;
  const float x2 = x * x;
  return x * (27.0f + x2) / (27.0f + 9.0f * x2);
}

// Soft clip with a hard safety clamp (limiter stage).
inline float softClip(float x) { return fastTanh(x); }

inline float dbToGain(float db) { return std::pow(10.0f, db / 20.0f); }
inline float gainToDb(float g) { return 20.0f * std::log10(g < 1e-9f ? 1e-9f : g); }

// Deterministic white noise generator (xorshift32).
class WhiteNoise {
 public:
  explicit WhiteNoise(uint32_t seed = 0x12345678u) : state_(seed ? seed : 0x12345678u) {}
  float tick() {
    state_ ^= state_ << 13;
    state_ ^= state_ >> 17;
    state_ ^= state_ << 5;
    // Map to [-1, 1).
    return static_cast<float>(static_cast<int32_t>(state_)) * (1.0f / 2147483648.0f);
  }
  void seed(uint32_t s) { state_ = s ? s : 0x12345678u; }

 private:
  uint32_t state_;
};

// One-pole smoother for control values (per-block update, time constant in ms).
class Smoother {
 public:
  void init(float sampleRate, float ms) {
    setTime(sampleRate, ms);
    value_ = 0.0f;
    target_ = 0.0f;
  }
  void setTime(float sampleRate, float ms) {
    const float t = sampleRate * (ms * 0.001f);
    coef_ = t > 0.0f ? 1.0f - std::exp(-1.0f / t) : 1.0f;
  }
  void setTarget(float v) { target_ = v; }
  void snap(float v) { value_ = target_ = v; }
  float tick() {
    value_ += (target_ - value_) * coef_;
    return value_;
  }
  float value() const { return value_; }

 private:
  float coef_ = 1.0f;
  float value_ = 0.0f;
  float target_ = 0.0f;
};

// Monotone shaping of a 0..1 phase for envelope curves:
// curve < 0 -> slow start (quadratic-ish), curve > 0 -> fast start (smoothstep-ish).
inline float curveShape(float x, float curve) {
  x = clamp(x, 0.0f, 1.0f);
  if (curve > 0.0f) {
    const float s = x * x * (3.0f - 2.0f * x);
    return x + (s - x) * curve;
  }
  if (curve < 0.0f) {
    return x + (x * x - x) * curve;
  }
  return x;
}

// TPT one-pole coefficient g = tan(pi * fc / fs), clamped for stability.
inline float tptG(float fc, float fs) {
  fc = clamp(fc, 1.0f, fs * 0.49f);
  return std::tan(kPi * fc / fs);
}

}  // namespace math
}  // namespace bukifon
