// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/filter.hpp"

#include <cmath>

#include "core/math.hpp"

namespace bukifon {
namespace {
inline void svfTick(float in, float k, float a1, float a2, float a3, float& ic1,
                    float& ic2, float& lp, float& bp, float& hp) {
  const float v3 = in - ic2;
  const float v1 = a1 * ic1 + a2 * v3;
  const float v2 = ic2 + a2 * ic1 + a3 * v3;
  ic1 = 2.0f * v1 - ic1;
  ic2 = 2.0f * v2 - ic2;
  bp = v1;
  lp = v2;
  hp = in - k * v1 - v2;
}
}  // namespace

void Filter::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
  updateCoefficients();
}

void Filter::reset() {
  ic1_ = ic2_ = ic1b_ = ic2b_ = 0.0f;
  for (int i = 0; i < 4; ++i) ladder_[i] = 0.0f;
  for (int i = 0; i < 3; ++i) {
    formantIc1_[i] = formantIc2_[i] = 0.0f;
  }
  lastLp_ = 0.0f;
}

void Filter::setCharacter(int character) {
  character_ = math::clampInt(character, 0, kNumFilterChars - 1);
  updateCoefficients();
}
void Filter::setMode(int mode) { mode_ = math::clampInt(mode, 0, kNumFilterModes - 1); }
void Filter::setCutoff(float hz) {
  hz = math::clamp(hz, 15.0f, sampleRate_ * 0.45f);
  if (hz == cutoff_) return;
  cutoff_ = hz;
  updateCoefficients();
}
void Filter::setResonance(float r) {
  r = math::clamp(r, 0.0f, 1.0f);
  if (r == resonance_) return;
  resonance_ = r;
  updateCoefficients();
}
void Filter::setDrive(float d) {
  d = math::clamp(d, 0.0f, 1.0f);
  if (d == drive_) return;
  drive_ = d;
  updateCoefficients();
}

void Filter::updateCoefficients() {
  const float fc = math::clamp(cutoff_, 15.0f, sampleRate_ * 0.45f);
  g_ = math::tptG(fc, sampleRate_);
  // SVF damping: resonance 0 -> k=2 (no res), 1 -> k=0.05 (high Q).
  k_ = 2.0f - 1.9f * resonance_;
  const float q = 1.0f / k_;
  const float g = g_;
  a1_ = 1.0f / (1.0f + g * (g + k_));
  a2_ = g * a1_;
  a3_ = g * a2_;
  (void)q;

  // Moog ladder: feedback grows to 4 at resonance = 1 (self-oscillation edge).
  G_ = g_ / (1.0f + g_);
  feedback_ = resonance_ * 4.60f;  // small-signal loop gain > 1 at res=1 -> self-oscillation

  // Polyvox formants: three bandpass sections around the cutoff.
  const float ratios[3] = {1.0f, 2.4f, 4.1f};
  for (int i = 0; i < 3; ++i) {
    const float f = math::clamp(fc * ratios[i], 30.0f, sampleRate_ * 0.45f);
    formantG_[i] = math::tptG(f, sampleRate_);
  }
}

float Filter::processSvf(float x) {
  const float driveGain = 1.0f + drive_ * 6.0f;
  const float in = math::fastTanh(x * driveGain) / (1.0f + drive_ * 2.0f);
  float lp, bp, hp;
  svfTick(in, k_, a1_, a2_, a3_, ic1_, ic2_, lp, bp, hp);
  switch (mode_) {
    case Fm_LP12:
      lastLp_ = lp;
      return lp;
    case Fm_BP:
      lastLp_ = lp;
      return bp * (1.0f + resonance_);
    case Fm_HP:
      lastLp_ = lp;
      return hp;
    case Fm_Notch:
      lastLp_ = lp;
      return hp + lp;
    case Fm_LP24:
    default: {
      float lp2, bp2, hp2;
      svfTick(lp, k_, a1_, a2_, a3_, ic1b_, ic2b_, lp2, bp2, hp2);
      lastLp_ = lp2;
      return lp2;
    }
  }
}

float Filter::processLadder(float x) {
  const float driveGain = 1.0f + drive_ * 8.0f;
  const float in = math::fastTanh(x * driveGain) / (1.0f + drive_ * 3.0f);
  const float G = G_;
  const float G2 = G * G;
  const float G3 = G2 * G;
  const float G4 = G3 * G;
  // Zero-delay feedback solution for the 4-pole ladder.
  const float C = (1.0f - G) * (ladder_[3] + G * ladder_[2] + G2 * ladder_[1] + G3 * ladder_[0]);
  const float y4 = (G4 * in + C) / (1.0f + feedback_ * G4);
  const float u = in - feedback_ * y4;

  float y = u;
  for (int i = 0; i < 4; ++i) {
    const float v = (y - ladder_[i]) * G;
    y = v + ladder_[i];
    // Saturate the stage output (bounded, musical ladder behaviour).
    y = math::fastTanh(y * 1.1f) / 1.1f;
    ladder_[i] = y + v;
  }
  lastLp_ = y;
  switch (mode_) {
    case Fm_LP12:
      return y * 0.7f + 0.3f * lastLp_;
    case Fm_BP:
      return (lastLp_ - y) * (1.0f + resonance_ * 2.0f);
    case Fm_HP:
      return in - y;
    case Fm_Notch:
      return in - 2.0f * y;
    case Fm_LP24:
    default:
      return y;
  }
}

float Filter::processPolyvox(float x) {
  const float driveGain = 1.0f + drive_ * 5.0f;
  const float in = math::fastTanh(x * driveGain) / (1.0f + drive_ * 2.0f);
  float sum = 0.0f;
  const float q = 2.0f + resonance_ * 8.0f;   // formant emphasis
  const float k = 1.0f / q;
  const float gains[3] = {1.0f, 0.55f, 0.35f};
  for (int i = 0; i < 3; ++i) {
    const float g = formantG_[i];
    const float a1 = 1.0f / (1.0f + g * (g + k));
    const float a2 = g * a1;
    const float a3 = g * a2;
    float lp, bp, hp;
    svfTick(in, k, a1, a2, a3, formantIc1_[i], formantIc2_[i], lp, bp, hp);
    sum += bp * gains[i];
  }
  // Add a little of the low end so the Polyvox character is not thin.
  lastLp_ = sum;
  const float lp = sum * 0.85f + in * 0.15f;
  lastLp_ = lp;
  return lp;
}

float Filter::process(float x) {
  const float y = (character_ == CharMoog)     ? processLadder(x)
                  : (character_ == CharPolyvox) ? processPolyvox(x)
                                                : processSvf(x);
  // Safety: never let a runaway filter poison the bus.
  if (!std::isfinite(y)) {
    reset();
    return 0.0f;
  }
  return math::clamp(y, -8.0f, 8.0f);
}

}  // namespace bukifon
