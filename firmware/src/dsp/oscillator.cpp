// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/oscillator.hpp"

#include <cmath>

#include "core/math.hpp"
#include "dsp/wavetable.hpp"

namespace bukifon {
namespace {
inline uint32_t hzToInc(float hz, float sr) {
  return static_cast<uint32_t>(static_cast<double>(hz) / sr * 4294967296.0);
}
}  // namespace

void Oscillator::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
}

void Oscillator::reset() {
  for (int i = 0; i < kMaxUnison; ++i) phase_[i] = 0;
  syncPhase_ = 0;
  lastMasterPhase_ = 0.0f;
}

void Oscillator::setWave(int wave) { wave_ = math::clampInt(wave, 0, kNumWaves - 1); }
void Oscillator::setMode(int mode) { mode_ = math::clampInt(mode, 0, kNumOscModes - 1); }
void Oscillator::setFrequency(float hz) {
  frequency_ = math::clamp(hz, 0.01f, sampleRate_ * 0.49f);
  mip_ = WavetableBank::mipForFrequency(frequency_, sampleRate_);
  const int uni = unison_;
  for (int i = 0; i < kMaxUnison; ++i) {
    float cents = 0.0f;
    if (i < uni && uni > 1) {
      const float pos = static_cast<float>(i) / static_cast<float>(uni - 1) - 0.5f;
      cents = pos * 2.0f * detune_ * 25.0f;
    }
    const float f = frequency_ * math::centsToRatio(cents);
    inc_[i] = hzToInc(f, sampleRate_);
  }
  syncInc_ = hzToInc(frequency_ * 1.5f, sampleRate_);
}

void Oscillator::setUnison(int count) {
  // Never touches the running phases: phase offsets are applied on retrigger.
  unison_ = math::clampInt(count, 1, kMaxUnison);
  setFrequency(frequency_);
}

void Oscillator::setDetune(float amount) { detune_ = math::clamp(amount, 0.0f, 1.0f); }
void Oscillator::setSpread(float amount) {
  // Phase spread is applied at note-on (retrigger); changing it must not reset
  // the running phases or the oscillator pitch would jump.
  spread_ = math::clamp(amount, 0.0f, 1.0f);
}
void Oscillator::setPulseWidth(float pw) { pulseWidth_ = math::clamp(pw, 0.02f, 0.98f); }

void Oscillator::retrigger(float phase01) {
  const uint32_t p = static_cast<uint32_t>(phase01 * 4294967296.0f);
  for (int i = 0; i < kMaxUnison; ++i) {
    const float off = (unison_ > 1) ? (static_cast<float>(i) / static_cast<float>(unison_)) * spread_
                                    : 0.0f;
    phase_[i] = p + static_cast<uint32_t>(off * 4294967296.0f);
  }
  syncPhase_ = p;
}

float Oscillator::tick() {
  const int uni = unison_;
  const float master = static_cast<float>(phase_[0]) * (1.0f / 4294967296.0f);
  float sum = 0.0f;
  for (int i = 0; i < uni; ++i) {
    const uint32_t ph = phase_[i];
    float s = WavetableBank::samplePhase(wave_, mip_, ph);
    switch (mode_) {
      case OscAdditive: {
        // Additive: fundamental + weighted 2nd/3rd harmonics (sine table).
        const float f = static_cast<float>(ph) * (1.0f / 4294967296.0f);
        s = WavetableBank::sampleNormalized(4, kMipLevels - 1, f) +
            0.5f * WavetableBank::sampleNormalized(4, kMipLevels - 1, f * 2.0f) +
            0.25f * WavetableBank::sampleNormalized(4, kMipLevels - 1, f * 3.0f + pulseWidth_);
        s *= 0.5f;
        break;
      }
      case OscWaveShaper:
        s = math::fastTanh(s * (1.0f + 3.0f * pulseWidth_));
        break;
      case OscWaveFolder: {
        // Triangle wavefolder: fold the shaper output around +/-1.
        float x = s * (1.0f + 4.0f * pulseWidth_);
        x = std::fabs(std::fmod(x + 1.0f, 4.0f) - 2.0f) - 1.0f;
        s = math::fastTanh(x);
        break;
      }
      case OscHardSync: {
        // Slave oscillator resets whenever the master wraps; ratio 1.5x.
        syncPhase_ += syncInc_;
        s = WavetableBank::samplePhase(wave_, mip_, syncPhase_);
        if (static_cast<uint32_t>(ph + inc_[i]) < ph) syncPhase_ = 0;
        break;
      }
      case OscRingMod: {
        const uint32_t ringPhase = ph * 3u;  // ~1.5x fundamental
        s *= WavetableBank::samplePhase(4, kMipLevels - 1, ringPhase);
        break;
      }
      case OscWavetable:
      default:
        break;
    }
    sum += s;
    phase_[i] += inc_[i];
  }
  // hardsync wrap detection uses the master phase before/after the increment
  lastMasterPhase_ = master;
  return sum / static_cast<float>(uni) * velocity_;
}

}  // namespace bukifon
