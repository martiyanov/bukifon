// SPDX-License-Identifier: GPL-3.0-or-later
// A single polyphonic voice: 2 oscillators (wavetable/FM hybrid), sub, noise,
// ladder/SVF/Polyvox filter and per-voice amplitude envelope with glide.
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "core/math.hpp"
#include "core/params.hpp"
#include "dsp/envelope.hpp"
#include "dsp/filter.hpp"
#include "dsp/fm.hpp"
#include "dsp/oscillator.hpp"

namespace bukifon {

struct VoiceContext {
  const PartParams* params = nullptr;
  float partEnv2 = 0.0f;      // part-level envelope 2 (filter envelope)
  float bendSemitones = 0.0f;
  float glideSeconds = 0.0f;
};

class Voice {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();

  void noteOn(int note, float velocity, uint8_t part, uint8_t channel, bool legato);
  void noteOff();
  void kill();
  void setNote(int note) { note_ = note; }  // mono/legato pitch change

  bool active() const { return env_.active(); }
  bool releasing() const { return env_.released(); }
  int note() const { return note_; }
  uint8_t part() const { return part_; }
  uint8_t channel() const { return channel_; }
  float velocity() const { return velocity_; }
  uint32_t age() const { return age_; }
  void ageTick() { ++age_; }
  float currentHz() const { return currentHz_; }

  void render(float* outL, float* outR, int n, const VoiceContext& ctx);

 private:
  float sampleRate_ = static_cast<float>(kSampleRate);
  Oscillator osc1_;
  Oscillator osc2_;
  FmCore fm_;
  Envelope env_;
  Filter filter_;
  math::WhiteNoise noise_;
  uint32_t subPhase_ = 0;
  uint32_t subInc_ = 0;

  int note_ = 60;
  uint8_t part_ = 0;
  uint8_t channel_ = 0;
  float velocity_ = 1.0f;
  float targetHz_ = 440.0f;
  float currentHz_ = 440.0f;
  uint32_t age_ = 0;
  float noiseLevel_ = 0.0f;
};

}  // namespace bukifon
