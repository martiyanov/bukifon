// SPDX-License-Identifier: GPL-3.0-or-later
// Scenario p4_profile — first-SKU P4 profile (customer decision: P4 first).
//
// Memory: RGB565 framebuffer 750 KiB + 16-row bounce buffer (25 KiB) + 8 stereo
// tracks and 8 synth voices.  Display: RGB565/DSI target model (16 bpp, 20 MHz
// pixel clock; docs/31) with dirty-rect updates; HS USB 8x8 UAC2 24/48
// (2.304 MB/s, P4 only).  Audio criterion: max block <= 650 us, 0 xruns;
// 24 h soak is the device acceptance test (the scenario records its duration).
#include <cmath>
#include <cstring>

#include "core/math.hpp"
#include "dsp/effects.hpp"
#include "dsp/envelope.hpp"
#include "dsp/filter.hpp"
#include "dsp/fm.hpp"
#include "dsp/lfo.hpp"
#include "dsp/oscillator.hpp"
#include "scenario_factories.hpp"
#include "ui/ui800.hpp"

namespace bukifon {
namespace bench {
namespace {

constexpr int kP4Voices = 8;
constexpr int kP4Tracks = 8;
constexpr int kStripeRows = 16;

constexpr double kFramePixels = 800.0 * 480.0;
constexpr double kFrameBytes = kFramePixels * 2.0;       // RGB565
constexpr double kRgbPixelClockHz = 20000000.0;          // RGB565 target (docs/31)
constexpr double kPartialFraction = 0.40;
constexpr double kRgbFullFps = kRgbPixelClockHz / kFramePixels;              // ~52.1
constexpr double kRgbPartialFps = kRgbFullFps / kPartialFraction;            // ~130.2
constexpr double kUsb8x8MbPerSec = 2.304;  // 8 in + 8 out, 24 bit, 48 kHz
constexpr double kUsbHsCapacityMbPerSec = 60.0;  // USB 2.0 HS theoretical
constexpr uint32_t kSoakHours = 24;

inline uint32_t xorshift(uint32_t* state) {
  uint32_t x = *state;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  *state = x;
  return x;
}

inline void fnvMix(float value, uint64_t* hash) {
  uint32_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  *hash ^= bits;
  *hash *= 1099511628211ull;
}

struct P4Voice {
  FmCore fm;
  Oscillator osc;
  Filter filter;
  Envelope env[2];
  Lfo lfo;
  float baseCutoff = 1200.0f;
  float panL = 0.7f;
  float panR = 0.7f;
};

struct P4Track {
  Filter filterL;
  Filter filterR;
  float phaseL = 0.0f;
  float phaseR = 0.0f;
  float incL = 0.0f;
  float incR = 0.0f;
  float panL = 0.7f;
  float panR = 0.7f;
};

class P4ProfileScenario final : public IScenario {
 public:
  ~P4ProfileScenario() override {
    delete framebuffer_;
    delete[] bounce_;
  }
  const char* name() const override { return "p4_profile"; }
  const char* description() const override {
    return "P4 first SKU: RGB565 750 KiB framebuffer + 25 KiB bounce, 8 FM "
           "voices + 8 stereo tracks, RGB565/DSI display model (>=15 fps), "
           "HS USB 8x8 UAC2 2.304 MB/s, 24 h soak target";
  }
  Criteria criteria() const override { return Criteria::audio(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    blockCount_ = 0;
    rng_ = static_cast<uint32_t>(config.seed | 1u);
    if (!framebuffer_) {
      framebuffer_ = new ui::Framebuffer800();
      bounce_ = new uint16_t[800 * kStripeRows];
      if (!framebuffer_ || !framebuffer_->valid() || !bounce_) return false;
    }
    const float ratios[4] = {1.0f, 1.0f, 2.0f, 3.0f};
    const float levels[4] = {1.0f, 0.35f, 0.30f, 0.25f};
    for (int v = 0; v < kP4Voices; ++v) {
      P4Voice& voice = voices_[v];
      const int note = 48 + v * 2;
      const float hz = 440.0f * std::pow(2.0f, (static_cast<float>(note) - 69.0f) / 12.0f);
      voice.fm.init();
      voice.fm.setParams(v % 8, ratios, levels, 0.15f);
      voice.fm.noteOn(hz);
      voice.osc.init();
      voice.osc.setWave(v % 8);
      voice.osc.setUnison(1);
      voice.osc.setFrequency(hz * 1.004f);
      voice.filter.init();
      voice.filter.setCharacter(CharMoog);
      voice.filter.setMode(Fm_LP24);
      voice.baseCutoff = 900.0f + 180.0f * static_cast<float>(v);
      voice.filter.setCutoff(voice.baseCutoff);
      voice.filter.setResonance(0.62f);
      for (int e = 0; e < 2; ++e) {
        voice.env[e].init();
        voice.env[e].setParams(0.005f, 0.16f, 0.55f, 0.25f, -0.15f, EnvAdsr);
        voice.env[e].noteOn(0.8f);
      }
      voice.lfo.init();
      voice.lfo.setParams(0.65f, 0, false, false, 0.0f, 0.0f, 120.0f);
      voice.lfo.noteOn(60.0f);
      const float angle = ((v % 2 == 0 ? -0.4f : 0.4f) * 0.5f + 0.5f) * 3.14159265f * 0.5f;
      voice.panL = std::cos(angle);
      voice.panR = std::sin(angle);
    }
    for (int t = 0; t < kP4Tracks; ++t) {
      P4Track& track = tracks_[t];
      track.filterL.init();
      track.filterR.init();
      track.filterL.setCharacter(CharSvf);
      track.filterR.setCharacter(CharSvf);
      track.filterL.setMode(Fm_LP12);
      track.filterR.setMode(Fm_LP12);
      track.filterL.setCutoff(1500.0f + 250.0f * static_cast<float>(t));
      track.filterR.setCutoff(1500.0f + 250.0f * static_cast<float>(t));
      track.filterL.setResonance(0.3f);
      track.filterR.setResonance(0.3f);
      track.phaseL = static_cast<float>(xorshift(&rng_) % 1000u) / 1000.0f;
      track.phaseR = track.phaseL;
      track.incL = (220.0f + 40.0f * static_cast<float>(t)) / 48000.0f;
      track.incR = track.incL * 1.003f;
      const float angle = ((t % 2 == 0 ? -0.35f : 0.35f) * 0.5f + 0.5f) * 3.14159265f * 0.5f;
      track.panL = std::cos(angle);
      track.panR = std::sin(angle);
    }
    ui::uiSnapshotDemo(&snapshot_, ui::Screen::Main);
    ui::uiSnapshotForDeviceMode(&snapshot_, DeviceMode::Synth);
    limiter_.init();
    return true;
  }

  void processBlock(float* l, float* r, int frames) override {
    if (frames > 256) frames = 256;
    for (int f = 0; f < frames; ++f) {
      l[f] = 0.0f;
      r[f] = 0.0f;
    }
    // 8 synth voices.
    for (int v = 0; v < kP4Voices; ++v) {
      P4Voice& voice = voices_[v];
      const float lfo = voice.lfo.tickN(frames);
      voice.filter.setCutoff(voice.baseCutoff * std::pow(2.0f, lfo * 1.6f));
      for (int f = 0; f < frames; ++f) {
        float sample = voice.fm.tick() * 0.7f + voice.osc.tick() * 0.3f;
        sample = voice.filter.process(sample);
        sample *= voice.env[0].tick() * (0.85f + 0.15f * voice.env[1].tick());
        l[f] += sample * voice.panL;
        r[f] += sample * voice.panR;
      }
    }
    // 8 stereo tracks (sample-playback-style oscillators + filters + insert).
    for (int t = 0; t < kP4Tracks; ++t) {
      P4Track& track = tracks_[t];
      for (int f = 0; f < frames; ++f) {
        track.phaseL += track.incL;
        track.phaseR += track.incR;
        if (track.phaseL >= 1.0f) track.phaseL -= 1.0f;
        if (track.phaseR >= 1.0f) track.phaseR -= 1.0f;
        float left = std::sin(6.2831853f * track.phaseL) * 0.09f;
        float right = std::sin(6.2831853f * track.phaseR) * 0.09f;
        left = math::fastTanh(track.filterL.process(left) * 1.25f);
        right = math::fastTanh(track.filterR.process(right) * 1.25f);
        l[f] += left * track.panL;
        r[f] += right * track.panR;
      }
    }
    limiter_.process(l, r, frames);

    // RGB565 display work: one 16-row bounce stripe per block + periodic full
    // CPU redraw (the RGB/DSI flush itself is DMA on P4).
    if (framebuffer_ && bounce_) {
      const int row = (blockCount_ * kStripeRows) % 480;
      framebuffer_->fillRect(0, row, 800, kStripeRows, colors::kDim);
      framebuffer_->drawText(10, row + 6, "P4 PROFILE", colors::kGrey);
      std::memcpy(bounce_, framebuffer_->data() + row * 800,
                  sizeof(uint16_t) * 800 * kStripeRows);
      if ((blockCount_ % 50) == 0) {
        ui::drawUi800(*framebuffer_, snapshot_);
      }
    }
    for (int f = 0; f < frames; ++f) {
      fnvMix(l[f], &checksum_);
      fnvMix(r[f], &checksum_);
    }
    ++blockCount_;
    if (checksum_ == 0) checksum_ = 1;
  }

  uint64_t checksum() const override { return checksum_; }
  void rewind() override { prepare(config_); }

  bool scenarioCriteriaPass(double maxBlockUs, const char** reason) const override {
    if (maxBlockUs > kMaxBlockTimeUs) {
      if (reason) *reason = "P4 profile: max block above 650 us";
      return false;
    }
    if (kRgbFullFps < 15.0) {
      if (reason) *reason = "P4 profile: RGB565 full refresh < 15 fps (D-46)";
      return false;
    }
    if (kRgbPartialFps < 30.0) {
      if (reason) *reason = "P4 profile: RGB565 partial < 30 updates/s (D-46)";
      return false;
    }
    if (kUsb8x8MbPerSec > kUsbHsCapacityMbPerSec) {
      if (reason) *reason = "P4 profile: 8x8 UAC2 exceeds HS capacity";
      return false;
    }
    return true;
  }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    if (!out || !count) return;
    int n = 0;
    out[n++] = Metric{"framebuffer_kib", kFrameBytes / 1024.0, "KiB"};
    out[n++] = Metric{"bounce_kib", 800.0 * kStripeRows * 2.0 / 1024.0, "KiB"};
    out[n++] = Metric{"rgb_full_fps", kRgbFullFps, "fps"};
    out[n++] = Metric{"rgb_partial_fps", kRgbPartialFps, "fps"};
    out[n++] = Metric{"usb_8x8_mb_s", kUsb8x8MbPerSec, "MB/s"};
    out[n++] = Metric{"usb_hs_ok", 1.0, "flag"};
    out[n++] = Metric{"soak_hours", static_cast<double>(kSoakHours), "h"};
    out[n++] = Metric{"block_us", meanBlockUs, "us"};
    *count = n;
  }

 private:
  RunConfig config_{};
  ui::Framebuffer800* framebuffer_ = nullptr;
  uint16_t* bounce_ = nullptr;
  P4Voice voices_[kP4Voices];
  P4Track tracks_[kP4Tracks];
  Limiter limiter_;
  ui::UiSnapshot snapshot_{};
  uint32_t rng_ = 1;
  uint32_t blockCount_ = 0;
  uint64_t checksum_ = 0;
};

}  // namespace

IScenario* createP4ProfileScenario() { return new P4ProfileScenario(); }

}  // namespace bench
}  // namespace bukifon
