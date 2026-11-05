// SPDX-License-Identifier: GPL-3.0-or-later
// Scenarios granular_track and mix_bus — frozen by docs/05-benchmark-workload.md.
//
// granular_track: 8 mono tracks x 4 grains (2048-sample grains, Hann window,
// 4-point Catmull-Rom interpolation), per-track SVF, insert drive, 2 send buses
// (fixed 250/375 ms delays with feedback) and a master limiter.
//
// mix_bus: the mixing/effects half of the desk — 8 track inserts + 2 send
// returns + master limiter, block 64.
#include <cmath>
#include <cstring>

#include "core/math.hpp"
#include "dsp/effects.hpp"
#include "dsp/filter.hpp"
#include "scenario_factories.hpp"

namespace bukifon {
namespace bench {
namespace {

constexpr int kTracks = 8;
constexpr int kGrains = 4;
constexpr int kGrainSize = 2048;
constexpr int kMemorySamples = 1 << 20;  // 4 MiB float working set
constexpr int kSendLen = 48000;
constexpr int kSend0Delay = 12000;  // 250 ms
constexpr int kSend1Delay = 18000;  // 375 ms

inline uint32_t xorshift(uint32_t* state) {
  uint32_t x = *state;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  *state = x;
  return x;
}

inline float readCubic(const float* buffer, uint32_t size, float position) {
  const uint32_t mask = size - 1;
  uint32_t index = static_cast<uint32_t>(position);
  const float frac = position - static_cast<float>(index);
  const float y0 = buffer[(index - 1) & mask];
  const float y1 = buffer[index & mask];
  const float y2 = buffer[(index + 1) & mask];
  const float y3 = buffer[(index + 2) & mask];
  const float a = -0.5f * y0 + 1.5f * y1 - 1.5f * y2 + 0.5f * y3;
  const float b = y0 - 2.5f * y1 + 2.0f * y2 - 0.5f * y3;
  const float c = -0.5f * y0 + 0.5f * y2;
  return ((a * frac + b) * frac + c) * frac + y1;
}

inline void fnvMix(float value, uint64_t* hash) {
  uint32_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  *hash ^= bits;
  *hash *= 1099511628211ull;
}

// --- granular_track --------------------------------------------------------
struct Grain {
  uint32_t base = 0;
  float phase = 0.0f;
};

struct GranularTrack {
  Filter filter;
  float panL = 0.7f;
  float panR = 0.7f;
  Grain grains[kGrains];
};

class GranularTrackScenario final : public IScenario {
 public:
  ~GranularTrackScenario() override {
    delete[] memory_;
    delete[] window_;
    delete[] send0_;
    delete[] send1_;
  }
  const char* name() const override { return "granular_track"; }
  const char* description() const override {
    return "8 tracks x [4 grains (2048 smp, Hann, 4-pt interp) + SVF + insert + "
           "2 sends + master limiter], random reads from 4 MiB buffer";
  }
  Criteria criteria() const override { return Criteria::audio(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    rng_ = static_cast<uint32_t>(config.seed | 1u);
    if (!memory_) {
      memory_ = new float[kMemorySamples];
      window_ = new float[kGrainSize];
      send0_ = new float[kSendLen];
      send1_ = new float[kSendLen];
      if (!memory_ || !window_ || !send0_ || !send1_) return false;
      for (int i = 0; i < kMemorySamples; ++i) {
        const float tone = std::sin(static_cast<float>(i) * 0.0021f) * 0.35f +
                           std::sin(static_cast<float>(i) * 0.00043f) * 0.25f;
        const float noise = (static_cast<float>(xorshift(&rng_) % 2001u) / 1000.0f - 1.0f) * 0.05f;
        memory_[i] = tone + noise;
      }
      const float twoPi = 6.28318530718f;
      for (int i = 0; i < kGrainSize; ++i) {
        window_[i] = 0.5f - 0.5f * std::cos(twoPi * static_cast<float>(i) /
                                            static_cast<float>(kGrainSize - 1));
      }
    }
    std::memset(send0_, 0, sizeof(float) * kSendLen);
    std::memset(send1_, 0, sizeof(float) * kSendLen);
    sendWrite_ = 0;
    limiter_.init();
    rng_ = static_cast<uint32_t>(config.seed | 1u);
    for (int t = 0; t < kTracks; ++t) {
      GranularTrack& track = tracks_[t];
      track.filter.init();
      track.filter.setCharacter(CharSvf);
      track.filter.setMode(Fm_LP24);
      track.filter.setCutoff(700.0f + 140.0f * static_cast<float>(t));
      track.filter.setResonance(0.45f);
      track.filter.setDrive(0.15f);
      const float pan = (t % 2 == 0) ? -0.35f : 0.35f;
      const float angle = (pan * 0.5f + 0.5f) * 3.14159265f * 0.5f;
      track.panL = std::cos(angle);
      track.panR = std::sin(angle);
      for (int g = 0; g < kGrains; ++g) {
        track.grains[g].base = xorshift(&rng_) & (kMemorySamples - 1);
        track.grains[g].phase = static_cast<float>(g) / static_cast<float>(kGrains);
      }
    }
    return true;
  }

  void processBlock(float* l, float* r, int frames) override {
    float sendMix0[256];
    float sendMix1[256];
    if (frames > 256) frames = 256;
    for (int f = 0; f < frames; ++f) {
      l[f] = 0.0f;
      r[f] = 0.0f;
      sendMix0[f] = 0.0f;
      sendMix1[f] = 0.0f;
    }
    for (int t = 0; t < kTracks; ++t) {
      GranularTrack& track = tracks_[t];
      for (int f = 0; f < frames; ++f) {
        float sum = 0.0f;
        for (int g = 0; g < kGrains; ++g) {
          Grain& grain = track.grains[g];
          const float position = static_cast<float>(grain.base) +
                                 grain.phase * static_cast<float>(kGrainSize - 1);
          const float sample = readCubic(memory_, kMemorySamples, position);
          const int windowIndex = static_cast<int>(grain.phase * static_cast<float>(kGrainSize - 1));
          sum += sample * window_[windowIndex];
          grain.phase += 1.0f / static_cast<float>(kGrainSize);
          if (grain.phase >= 1.0f) {
            grain.phase -= 1.0f;
            grain.base = xorshift(&rng_) & (kMemorySamples - 1);
          }
        }
        float sample = track.filter.process(sum * 0.30f);
        sample = math::fastTanh(sample * 1.4f) * 0.7f;
        l[f] += sample * track.panL;
        r[f] += sample * track.panR;
        sendMix0[f] += sample * 0.35f;
        sendMix1[f] += sample * 0.18f;
      }
    }
    for (int f = 0; f < frames; ++f) {
      const int index = (sendWrite_ + f) % kSendLen;
      const float read0 = send0_[(index + kSend0Delay) % kSendLen];
      send0_[index] = sendMix0[f] + read0 * 0.30f;
      const float read1 = send1_[(index + kSend1Delay) % kSendLen];
      send1_[index] = sendMix1[f] + read1 * 0.25f;
      l[f] += read0 * 0.25f + read1 * 0.18f;
      r[f] += read0 * 0.22f + read1 * 0.20f;
    }
    sendWrite_ = (sendWrite_ + frames) % kSendLen;
    limiter_.process(l, r, frames);
    for (int f = 0; f < frames; ++f) {
      fnvMix(l[f], &checksum_);
      fnvMix(r[f], &checksum_);
    }
    if (checksum_ == 0) checksum_ = 1;
  }

  uint64_t checksum() const override { return checksum_; }

  void rewind() override { prepare(config_); }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    if (!out || !count) return;
    int n = 0;
    out[n++] = Metric{"tracks", static_cast<double>(kTracks), "tracks"};
    out[n++] = Metric{"grains", static_cast<double>(kGrains), "per track"};
    out[n++] = Metric{"grain_size", static_cast<double>(kGrainSize), "samples"};
    out[n++] = Metric{"random_reads", static_cast<double>(kTracks * kGrains * kBlockFrames),
                      "per block"};
    out[n++] = Metric{"block_us", meanBlockUs, "us"};
    *count = n;
  }

 private:
  RunConfig config_{};
  GranularTrack tracks_[kTracks];
  float* memory_ = nullptr;
  float* window_ = nullptr;
  float* send0_ = nullptr;
  float* send1_ = nullptr;
  Limiter limiter_;
  uint32_t rng_ = 1;
  int sendWrite_ = 0;
  uint64_t checksum_ = 0;
};

// --- mix_bus ---------------------------------------------------------------
class MixBusScenario final : public IScenario {
 public:
  ~MixBusScenario() override {
    delete[] sine_;
    delete[] send0_;
    delete[] send1_;
  }
  const char* name() const override { return "mix_bus"; }
  const char* description() const override {
    return "8 mono track inserts + 2 send returns + master limiter, block 64";
  }
  Criteria criteria() const override { return Criteria::audio(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    rng_ = static_cast<uint32_t>(config.seed | 1u);
    if (!sine_) {
      sine_ = new float[2048];
      send0_ = new float[kSendLen];
      send1_ = new float[kSendLen];
      if (!sine_ || !send0_ || !send1_) return false;
      for (int i = 0; i < 2048; ++i) {
        sine_[i] = std::sin(6.28318530718f * static_cast<float>(i) / 2048.0f);
      }
    }
    std::memset(send0_, 0, sizeof(float) * kSendLen);
    std::memset(send1_, 0, sizeof(float) * kSendLen);
    sendWrite_ = 0;
    limiter_.init();
    for (int t = 0; t < kTracks; ++t) {
      phases_[t] = static_cast<uint32_t>(xorshift(&rng_));
      increments_[t] = static_cast<uint32_t>(static_cast<double>(220.0 + 40.0 * t) / 48000.0 *
                                             4294967296.0);
      filters_[t].init();
      filters_[t].setCharacter(CharSvf);
      filters_[t].setMode(Fm_LP12);
      filters_[t].setCutoff(1200.0f + 300.0f * static_cast<float>(t));
      filters_[t].setResonance(0.3f);
      const float pan = (t % 2 == 0) ? -0.4f : 0.4f;
      const float angle = (pan * 0.5f + 0.5f) * 3.14159265f * 0.5f;
      panL_[t] = std::cos(angle);
      panR_[t] = std::sin(angle);
    }
    return true;
  }

  void processBlock(float* l, float* r, int frames) override {
    float sendMix0[256];
    float sendMix1[256];
    for (int f = 0; f < frames; ++f) {
      l[f] = 0.0f;
      r[f] = 0.0f;
      sendMix0[f] = 0.0f;
      sendMix1[f] = 0.0f;
    }
    for (int t = 0; t < kTracks; ++t) {
      for (int f = 0; f < frames; ++f) {
        const float sample =
            sine_[(phases_[t] >> 21) & 2047u] * 0.12f;
        phases_[t] += increments_[t];
        float processed = filters_[t].process(sample);
        processed = math::fastTanh(processed * 1.3f);
        l[f] += processed * panL_[t];
        r[f] += processed * panR_[t];
        sendMix0[f] += processed * 0.30f;
        sendMix1[f] += processed * 0.15f;
      }
    }
    for (int f = 0; f < frames; ++f) {
      const int index = (sendWrite_ + f) % kSendLen;
      const float read0 = send0_[(index + kSend0Delay) % kSendLen];
      send0_[index] = sendMix0[f] + read0 * 0.30f;
      const float read1 = send1_[(index + kSend1Delay) % kSendLen];
      send1_[index] = sendMix1[f] + read1 * 0.25f;
      l[f] += read0 * 0.25f + read1 * 0.18f;
      r[f] += read0 * 0.22f + read1 * 0.20f;
    }
    sendWrite_ = (sendWrite_ + frames) % kSendLen;
    limiter_.process(l, r, frames);
    for (int f = 0; f < frames; ++f) {
      fnvMix(l[f], &checksum_);
      fnvMix(r[f], &checksum_);
    }
    if (checksum_ == 0) checksum_ = 1;
  }

  uint64_t checksum() const override { return checksum_; }
  void rewind() override { prepare(config_); }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    if (!out || !count) return;
    int n = 0;
    out[n++] = Metric{"tracks", static_cast<double>(kTracks), "tracks"};
    out[n++] = Metric{"inserts", static_cast<double>(kTracks), "fx"};
    out[n++] = Metric{"sends", 2.0, "buses"};
    out[n++] = Metric{"block_us", meanBlockUs, "us"};
    *count = n;
  }

 private:
  RunConfig config_{};
  float* sine_ = nullptr;
  float* send0_ = nullptr;
  float* send1_ = nullptr;
  uint32_t phases_[kTracks] = {};
  uint32_t increments_[kTracks] = {};
  float panL_[kTracks] = {};
  float panR_[kTracks] = {};
  Filter filters_[kTracks];
  Limiter limiter_;
  uint32_t rng_ = 1;
  int sendWrite_ = 0;
  uint64_t checksum_ = 0;
};

}  // namespace

IScenario* createGranularTrackScenario() { return new GranularTrackScenario(); }
IScenario* createMixBusScenario() { return new MixBusScenario(); }

}  // namespace bench
}  // namespace bukifon
