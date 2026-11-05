// SPDX-License-Identifier: GPL-3.0-or-later
// Global stereo FX: delay, chorus (re-used Ensemble), drive, bitcrush, limiter.
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "dsp/ensemble.hpp"

namespace bukifon {

class StereoDelay {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();
  void setTime(float seconds);
  void setFeedback(float feedback);
  void setMix(float mix);
  void setPingPong(bool pingPong);
  void setDamping(float hz);
  void process(float* l, float* r, int n);
  float timeSamples() const { return timeSamples_; }

 private:
  float read(int channel, float delaySamples) const;
  float sampleRate_ = static_cast<float>(kSampleRate);
  float timeSamples_ = 12000.0f;
  float feedback_ = 0.35f;
  float mix_ = 0.25f;
  bool pingPong_ = false;
  float damp_ = 0.35f;
  int write_ = 0;
  int16_t buffer_[2][kDelayMaxSamples] = {};
  float dampState_[2] = {};
};

class DriveFx {
 public:
  void init();
  void reset() { lp_ = 0.0f; }
  void setAmount(float a);
  void setTone(float t);      // 0 dark .. 1 bright
  void setMix(float m);
  void process(float* l, float* r, int n);

 private:
  float amount_ = 0.1f;
  float tone_ = 0.6f;
  float mix_ = 1.0f;
  float lp_ = 0.0f;
};

class BitcrushFx {
 public:
  void init();
  void reset() { holdCounter_ = 0; holdL_ = holdR_ = 0.0f; }
  void setBits(float bits);       // 1..16
  void setRate(float rate);       // 0..1 -> decimation 1..64
  void setMix(float mix);
  void process(float* l, float* r, int n);

 private:
  int bits_ = 16;
  float rate_ = 0.0f;
  float mix_ = 0.0f;
  int holdCounter_ = 0;
  float holdL_ = 0.0f, holdR_ = 0.0f;
};

class Limiter {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset() { env_ = 0.0f; }
  void setThreshold(float t);   // 0.3..1
  void setRelease(float s);
  void process(float* l, float* r, int n);

 private:
  float sampleRate_ = static_cast<float>(kSampleRate);
  float threshold_ = 0.95f;
  float releaseCoef_ = 0.001f;
  float env_ = 0.0f;
};

// TPDF dither for the 16-bit PCM5102A output.
class Dither {
 public:
  void seed(uint32_t s) { rng_ = s ? s : 0x9E3779B9u; }
  float tick();
  int16_t toPcm16(float x);

 private:
  uint32_t rng_ = 0x9E3779B9u;
};

}  // namespace bukifon
