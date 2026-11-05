// SPDX-License-Identifier: GPL-3.0-or-later
#include "audio/voice.hpp"

#include <cmath>

#include "core/math.hpp"

namespace bukifon {

void Voice::init(float sampleRate) {
  sampleRate_ = sampleRate;
  osc1_.init(sampleRate_);
  osc2_.init(sampleRate_);
  fm_.init(sampleRate_);
  env_.init(sampleRate_);
  filter_.init(sampleRate_);
  reset();
}

void Voice::reset() {
  osc1_.reset();
  osc2_.reset();
  fm_.reset();
  env_.reset();
  filter_.reset();
  subPhase_ = 0;
  age_ = 0;
  currentHz_ = targetHz_ = 440.0f;
}

void Voice::noteOn(int note, float velocity, uint8_t part, uint8_t channel, bool legato) {
  note_ = note;
  part_ = part;
  channel_ = channel;
  velocity_ = math::clamp(velocity, 0.0f, 1.0f);
  targetHz_ = math::midiToHz(static_cast<float>(note));
  if (!legato) {
    currentHz_ = targetHz_;
    osc1_.retrigger(0.0f);
    osc2_.retrigger(0.25f);
    fm_.noteOn(targetHz_, 0.0f);
    filter_.reset();
    subPhase_ = 0;
    age_ = 0;
    env_.noteOn(velocity_);
  }
  // For legato, the envelope keeps running and currentHz_ glides to targetHz_.
}

void Voice::noteOff() { env_.noteOff(); }
void Voice::kill() {
  env_.reset();
  filter_.reset();
}

void Voice::render(float* outL, float* outR, int n, const VoiceContext& ctx) {
  if (!ctx.params) return;
  const PartParams& p = *ctx.params;

  // --- per-block control updates -------------------------------------------
  const float bendRatio = math::centsToRatio(ctx.bendSemitones * 100.0f);
  targetHz_ = math::midiToHz(static_cast<float>(note_)) * bendRatio;
  const float glide = ctx.glideSeconds;
  if (glide > 0.001f) {
    const float coef = 1.0f - std::exp(-static_cast<float>(n) / (glide * sampleRate_));
    currentHz_ += (targetHz_ - currentHz_) * coef;
  } else {
    currentHz_ = targetHz_;
  }

  const float baseHz = currentHz_;
  const float f1 = baseHz * math::centsToRatio(p.v[Osc1Coarse] * 100.0f + p.v[Osc1Fine]);
  const float f2 = baseHz * math::centsToRatio(p.v[Osc2Coarse] * 100.0f + p.v[Osc2Fine]);

  osc1_.setWave(static_cast<int>(p.v[Osc1Wave] + 0.5f));
  osc1_.setMode(static_cast<int>(p.v[Osc1Mode] + 0.5f));
  osc1_.setUnison(static_cast<int>(p.v[Osc1Unison] + 0.5f));
  osc1_.setDetune(p.v[Osc1Detune]);
  osc1_.setSpread(p.v[Osc1Spread]);
  osc1_.setFrequency(f1);

  osc2_.setWave(static_cast<int>(p.v[Osc2Wave] + 0.5f));
  osc2_.setMode(static_cast<int>(p.v[Osc2Mode] + 0.5f));
  osc2_.setUnison(static_cast<int>(p.v[Osc2Unison] + 0.5f));
  osc2_.setDetune(p.v[Osc2Detune]);
  osc2_.setSpread(p.v[Osc2Spread]);
  osc2_.setFrequency(f2);

  const int fmMode = static_cast<int>(p.v[FmMode] + 0.5f);
  if (fmMode != 0) {
    const float ratios[4] = {p.v[FmRatio1], p.v[FmRatio2], p.v[FmRatio3], p.v[FmRatio4]};
    const float levels[4] = {p.v[FmLevel1], p.v[FmLevel2], p.v[FmLevel3], p.v[FmLevel4]};
    fm_.setParams(static_cast<int>(p.v[FmAlgorithm] + 0.5f), ratios, levels, p.v[FmFeedback]);
    fm_.setFrequency(baseHz);
  }

  // --- filter cutoff (modulated cutoff + part envelope + keytrack) ---------
  float cutoff = p.v[Cutoff];
  const float envOct = ctx.partEnv2 * p.v[FilterEnvAmt] * 6.0f;
  const float keyOct = (static_cast<float>(note_) - 60.0f) / 12.0f * p.v[FilterKeytrack];
  cutoff *= std::pow(2.0f, envOct + keyOct);
  cutoff = math::clamp(cutoff, 20.0f, 20000.0f);
  filter_.setCharacter(static_cast<int>(p.v[FilterChar] + 0.5f));
  filter_.setMode(static_cast<int>(p.v[FilterMode] + 0.5f));
  filter_.setCutoff(cutoff);
  filter_.setResonance(p.v[Resonance]);
  filter_.setDrive(p.v[FilterDrive]);

  env_.setParams(p.v[Env1A], p.v[Env1D], p.v[Env1S], p.v[Env1R], p.v[Env1Curve],
                 static_cast<int>(p.v[Env1Mode] + 0.5f));

  subInc_ = static_cast<uint32_t>(static_cast<double>(baseHz * 0.5f) / sampleRate_ * 4294967296.0);
  noiseLevel_ = p.v[NoiseLevel];

  // --- per-sample synthesis -------------------------------------------------
  const float lvl1 = p.v[Osc1Level];
  const float lvl2 = p.v[Osc2Level];
  const float subLvl = p.v[SubLevel];
  const int subShape = static_cast<int>(p.v[SubShape] + 0.5f);
  const float fmGain = (fmMode == 1) ? 0.9f : (fmMode == 2 ? 0.45f : 0.0f);
  const float ampGain = p.v[PartLevel];
  const float pan = math::clamp(p.v[PartPan], -1.0f, 1.0f);
  const float panL = std::cos((pan * 0.5f + 0.5f) * math::kPi * 0.5f);
  const float panR = std::sin((pan * 0.5f + 0.5f) * math::kPi * 0.5f);

  for (int i = 0; i < n; ++i) {
    float s = osc1_.tick() * lvl1 + osc2_.tick() * lvl2;
    if (fmGain > 0.0f) s += fm_.tick() * fmGain;
    if (subLvl > 0.0f) {
      const float ph = static_cast<float>(subPhase_) * (1.0f / 4294967296.0f);
      float sub;
      if (subShape == 1) {
        sub = std::sin(math::kTwoPi * ph);
      } else if (subShape == 2) {
        sub = ph < 0.25f ? 1.0f : -1.0f;
      } else {
        sub = ph < 0.5f ? 1.0f : -1.0f;
      }
      s += sub * subLvl;
      subPhase_ += subInc_;
    }
    if (noiseLevel_ > 0.0f) s += noise_.tick() * noiseLevel_;
    s = filter_.process(s);
    s *= env_.tick();
    s *= ampGain;
    outL[i] += s * panL;
    outR[i] += s * panR;
  }
}

}  // namespace bukifon
