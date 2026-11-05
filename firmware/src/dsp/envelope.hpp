// SPDX-License-Identifier: GPL-3.0-or-later
// ADSR + function-generator envelope (loop / one-shot / gate modes).
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum EnvMode : uint8_t {
  EnvAdsr = 0,
  EnvOneShot = 1,  // A -> D -> release automatically (ignores gate off)
  EnvLoop = 2,     // A -> D -> A ... (function generator), gate controls run
  EnvGate = 3,     // A while gate on, R when off (ASR)
  kNumEnvModes = 4
};

class Envelope {
 public:
  enum Stage : uint8_t { Idle = 0, Attack, Decay, Sustain, Release };

  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();

  void setParams(float attackS, float decayS, float sustain, float releaseS, float curve,
                 int mode);
  // Mutate only the times (modulation targets envelope times while running).
  void setTimes(float attackS, float decayS, float releaseS);
  void noteOn(float velocity = 1.0f);
  void noteOff();
  void kill() { reset(); }

  float tick();
  // Advances by n samples in one step (used by part-level modulation sources).
  float tickN(int n);
  float level() const { return level_; }
  Stage stage() const { return stage_; }
  bool active() const { return stage_ != Idle; }
  bool released() const { return stage_ == Release; }
  float attackS() const { return attackS_; }
  float decayS() const { return decayS_; }
  float releaseS() const { return releaseS_; }

 private:
  float shape(float x) const;

  float sampleRate_ = static_cast<float>(kSampleRate);
  float attackS_ = 0.005f;
  float decayS_ = 0.3f;
  float sustain_ = 0.7f;
  float releaseS_ = 0.4f;
  float curve_ = 0.0f;
  int mode_ = EnvAdsr;

  Stage stage_ = Idle;
  float level_ = 0.0f;
  float startLevel_ = 0.0f;
  float pos_ = 0.0f;  // 0..1 within current stage
  float velocity_ = 1.0f;
  float releaseStart_ = 0.0f;
};

}  // namespace bukifon
