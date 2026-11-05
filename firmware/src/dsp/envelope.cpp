// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/envelope.hpp"

#include "core/math.hpp"

namespace bukifon {

void Envelope::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
}

void Envelope::reset() {
  stage_ = Idle;
  level_ = 0.0f;
  pos_ = 0.0f;
  releaseStart_ = 0.0f;
  startLevel_ = 0.0f;
}

void Envelope::setParams(float attackS, float decayS, float sustain, float releaseS, float curve,
                         int mode) {
  setTimes(attackS, decayS, releaseS);
  sustain_ = math::clamp(sustain, 0.0f, 1.0f);
  curve_ = math::clamp(curve, -1.0f, 1.0f);
  mode_ = math::clampInt(mode, 0, kNumEnvModes - 1);
}

void Envelope::setTimes(float attackS, float decayS, float releaseS) {
  attackS_ = math::clamp(attackS, 0.0005f, 20.0f);
  decayS_ = math::clamp(decayS, 0.0005f, 20.0f);
  releaseS_ = math::clamp(releaseS, 0.0005f, 20.0f);
}

float Envelope::shape(float x) const { return math::curveShape(x, curve_); }

void Envelope::noteOn(float velocity) {
  velocity_ = math::clamp(velocity, 0.0f, 1.0f);
  startLevel_ = level_;
  pos_ = 0.0f;
  stage_ = Attack;
  if (attackS_ <= 0.0005f) {
    level_ = 1.0f;
    stage_ = Decay;
    pos_ = 0.0f;
  }
}

void Envelope::noteOff() {
  if (stage_ == Idle) return;
  releaseStart_ = level_;
  pos_ = 0.0f;
  stage_ = Release;
}

float Envelope::tickN(int n) {
  if (n <= 0 || stage_ == Idle) return (stage_ == Idle) ? 0.0f : level_ * velocity_;
  if (stage_ == Sustain) {
    level_ = (mode_ == EnvGate) ? 1.0f : sustain_;
    if (mode_ == EnvLoop) {
      startLevel_ = level_;
      pos_ = 0.0f;
      stage_ = Attack;
    }
    return level_ * velocity_;
  }
  const float time = (stage_ == Attack) ? attackS_ : ((stage_ == Decay) ? decayS_ : releaseS_);
  pos_ += static_cast<float>(n) / (time * sampleRate_);
  if (pos_ < 1.0f) {
    if (stage_ == Attack) {
      level_ = startLevel_ + (1.0f - startLevel_) * shape(pos_);
    } else if (stage_ == Decay) {
      const float target = (mode_ == EnvLoop) ? 0.0f : sustain_;
      level_ = target + (1.0f - target) * (1.0f - shape(pos_));
    } else {
      level_ = releaseStart_ * (1.0f - shape(pos_));
    }
    level_ = math::clamp(level_, 0.0f, 1.0f);
    return level_ * velocity_;
  }
  pos_ = 1.0f;
  tick();  // complete the stage (one extra sample, negligible for control rate)
  return level_ * velocity_;
}

float Envelope::tick() {
  switch (stage_) {
    case Idle:
      return 0.0f;

    case Attack: {
      pos_ += 1.0f / (attackS_ * sampleRate_);
      if (pos_ >= 1.0f) {
        level_ = 1.0f;
        pos_ = 0.0f;
        stage_ = (mode_ == EnvGate) ? Sustain : Decay;
      } else {
        level_ = startLevel_ + (1.0f - startLevel_) * shape(pos_);
      }
      break;
    }

    case Decay: {
      pos_ += 1.0f / (decayS_ * sampleRate_);
      const float sustainTarget = (mode_ == EnvLoop) ? 0.0f : sustain_;
      if (pos_ >= 1.0f) {
        level_ = sustainTarget;
        pos_ = 0.0f;
        if (mode_ == EnvLoop) {
          // Function generator: restart attack from 0 -> no discontinuity.
          startLevel_ = level_;
          stage_ = Attack;
        } else if (mode_ == EnvOneShot) {
          // One-shot: automatically release after the decay stage.
          releaseStart_ = level_;
          stage_ = Release;
        } else {
          stage_ = Sustain;
        }
      } else {
        level_ = sustainTarget + (1.0f - sustainTarget) * (1.0f - shape(pos_));
        // One-shot/loop always decay to their target.
        if (mode_ != EnvAdsr && mode_ != EnvGate) level_ = math::clamp(level_, 0.0f, 1.0f);
      }
      break;
    }

    case Sustain:
      level_ = (mode_ == EnvGate) ? 1.0f : sustain_;
      if (mode_ == EnvLoop) {
        // Loop mode continues running like a function generator even at sustain.
        startLevel_ = level_;
        pos_ = 0.0f;
        stage_ = Attack;
      }
      break;

    case Release: {
      pos_ += 1.0f / (releaseS_ * sampleRate_);
      if (pos_ >= 1.0f) {
        level_ = 0.0f;
        pos_ = 0.0f;
        stage_ = Idle;
      } else {
        level_ = releaseStart_ * (1.0f - shape(pos_));
      }
      break;
    }
  }
  if (stage_ == Idle) return 0.0f;
  // Velocity scales the amplitude envelope (envelopes 2..4 are used as mod
  // sources and velocity scaling is harmless for them).
  level_ = math::clamp(level_, 0.0f, 1.0f);
  return level_ * velocity_;
  // NOTE: velocity scaling is applied on the returned value; internal level_
  // stays 0..1 so stage transitions and timing stay exact.
}

}  // namespace bukifon
