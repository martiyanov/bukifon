// SPDX-License-Identifier: GPL-3.0-or-later
// Scenario fm_voice — frozen by docs/05-benchmark-workload.md §3.
//
// 8 voices, each: 4-operator FM (8 algorithms, feedback, 2x oversampling inside
// FmCore) + wavetable oscillator, Moog-style ZDF ladder (24 dB, per-block
// coefficient update), 4 ADSR envelopes (sample-accurate), 3 LFOs (block-rate).
#include <cmath>
#include <cstring>

#include "dsp/envelope.hpp"
#include "dsp/filter.hpp"
#include "dsp/fm.hpp"
#include "dsp/lfo.hpp"
#include "dsp/oscillator.hpp"
#include "scenario_factories.hpp"

namespace bukifon {
namespace bench {
namespace {

constexpr int kVoices = 8;

inline void fnvMix(uint64_t* hash, float value) {
  uint32_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  *hash ^= bits;
  *hash *= 1099511628211ull;
}

struct FmVoice {
  FmCore fm;
  Oscillator osc;
  Filter filter;
  Envelope env[4];
  Lfo lfo[3];
  float baseCutoff = 1200.0f;
  float panL = 0.7f;
  float panR = 0.7f;
};

class FmVoiceScenario final : public IScenario {
 public:
  const char* name() const override { return "fm_voice"; }
  const char* description() const override {
    return "8 voices x [4-op FM (algo 0..7, fb 0.15, 2x OS) + wavetable + Moog "
           "ZDF ladder + 4 env + 3 LFO], block 64";
  }
  Criteria criteria() const override { return Criteria::audio(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    panL_ = 0.0f;
    const float ratios[4] = {1.0f, 1.0f, 2.0f, 3.0f};
    const float levels[4] = {1.0f, 0.35f, 0.30f, 0.25f};
    for (int v = 0; v < kVoices; ++v) {
      FmVoice& voice = voices_[v];
      const int note = 48 + v * 2;
      const float hz = 440.0f * std::pow(2.0f, (static_cast<float>(note) - 69.0f) / 12.0f);
      voice.fm.init();
      voice.fm.setParams(v % 8, ratios, levels, 0.15f);
      voice.fm.noteOn(hz);
      voice.osc.init();
      voice.osc.setWave(v % 8);
      voice.osc.setUnison(1);
      voice.osc.setFrequency(hz * 1.003f);
      voice.osc.retrigger(0.1f * static_cast<float>(v));
      voice.filter.init();
      voice.filter.setCharacter(CharMoog);
      voice.filter.setMode(Fm_LP24);
      voice.baseCutoff = 900.0f + 160.0f * static_cast<float>(v);
      voice.filter.setCutoff(voice.baseCutoff);
      voice.filter.setResonance(0.65f);
      voice.filter.setDrive(0.20f);
      for (int e = 0; e < 4; ++e) {
        voice.env[e].init();
        voice.env[e].setParams(0.004f + 0.001f * static_cast<float>(e),
                               0.15f + 0.02f * static_cast<float>(e), 0.55f, 0.25f, -0.15f,
                               EnvAdsr);
        voice.env[e].noteOn(0.8f);
      }
      for (int l = 0; l < 3; ++l) {
        voice.lfo[l].init();
        const int shape = (l * 2) % static_cast<int>(kNumLfoShapes);
        voice.lfo[l].setParams(0.6f + 0.25f * static_cast<float>(l), shape, false, false, 0.0f,
                               0.0f, 120.0f);
        voice.lfo[l].noteOn(60.0f);
      }
      const float pan = (v % 2 == 0) ? -0.4f : 0.4f;
      const float panAngle = (pan * 0.5f + 0.5f) * 3.14159265f * 0.5f;
      voice.panL = std::cos(panAngle);
      voice.panR = std::sin(panAngle);
    }
    return true;
  }

  void processBlock(float* l, float* r, int frames) override {
    for (int f = 0; f < frames; ++f) {
      l[f] = 0.0f;
      r[f] = 0.0f;
    }
    for (int v = 0; v < kVoices; ++v) {
      FmVoice& voice = voices_[v];
      const float lfoSum = voice.lfo[0].tickN(frames) * 0.5f +
                           voice.lfo[1].tickN(frames) * 0.25f +
                           voice.lfo[2].tickN(frames) * 0.25f;
      voice.filter.setCutoff(voice.baseCutoff * std::pow(2.0f, lfoSum * 2.0f));
      for (int f = 0; f < frames; ++f) {
        float sample = voice.fm.tick() * 0.65f + voice.osc.tick() * 0.35f;
        sample = voice.filter.process(sample);
        const float amp = voice.env[0].tick();
        const float mod = voice.env[1].tick() * 0.5f + voice.env[2].tick() * 0.3f +
                          voice.env[3].tick() * 0.2f;
        sample *= amp * (0.8f + 0.2f * mod);
        l[f] += sample * voice.panL;
        r[f] += sample * voice.panR;
        fnvMix(&checksum_, l[f]);
        fnvMix(&checksum_, r[f]);
      }
    }
    if (checksum_ == 0) checksum_ = 1;  // never report a zero checksum
  }

  uint64_t checksum() const override { return checksum_; }

  void rewind() override {
    // FM/osc/filter/envelope/LFO preparation does not allocate: prepare() is
    // allocation-free for this scenario.
    prepare(config_);
  }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    (void)meanBlockUs;
    if (!out || !count) return;
    int n = 0;
    out[n++] = Metric{"voices", static_cast<double>(kVoices), "voices"};
    out[n++] = Metric{"fm_operators", 4.0, "ops"};
    out[n++] = Metric{"oversampling", 2.0, "x"};
    out[n++] = Metric{"deadline_use_percent", 0.0, "%"};
    *count = n;
  }

 private:
  RunConfig config_{};
  FmVoice voices_[kVoices];
  uint64_t checksum_ = 0;
  float panL_ = 0.0f;
};

}  // namespace

IScenario* createFmVoiceScenario() { return new FmVoiceScenario(); }

}  // namespace bench
}  // namespace bukifon
