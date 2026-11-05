// SPDX-License-Identifier: GPL-3.0-or-later
// Scenario s3_profile — S3-base P1 profile (D-46 / D-48 / D-51).
//
// Memory profile (D-51): 4 MiB sample pool + one 800x480 RGB565 framebuffer
// (750 KiB) + 16-line SPI bounce buffer (25 KiB).  Compute: 6 FM voices + 4
// granular tracks reading the pool + limiter, 64-frame audio block.  Display:
// dirty 16-line stripe copy each block plus a periodic full UI redraw (CPU
// model); SPI transfer is modelled as a frame-time (D-51: ~13 fps full), and
// the RGB565 target path (docs/31, 20 MHz pixel clock) as the D-46 full-frame
// criterion.  USB: FS stereo UAC2 24/48 (D-48), not 8x8 (P4/H743 only).
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

constexpr int kS3Voices = 6;
constexpr int kS3Tracks = 4;
constexpr int kS3Grains = 2;
constexpr int kPoolSamples = 1 << 20;  // 4 MiB float sample pool
constexpr int kStripeRows = 16;        // SPI bounce: 8-16 lines (25 KiB)

constexpr double kFrameBytes = 800.0 * 480.0 * 2.0;  // RGB565
constexpr double kSpiClockHz = 80000000.0;           // CORE-S3 SPI2 (D-51 model)
constexpr double kRgbPixelClockHz = 20000000.0;      // RGB565 target (docs/31)
constexpr double kPartialFraction = 0.40;            // dirty-rect area

constexpr double kSpiFullFps = kSpiClockHz / (kFrameBytes * 8.0);                    // ~13.0
constexpr double kSpiPartialUpdates = kSpiClockHz / (kFrameBytes * kPartialFraction * 8.0);  // ~32.5
constexpr double kRgbFullFps = kRgbPixelClockHz / (800.0 * 480.0);                   // ~52.1
constexpr double kRgbPartialFps = kRgbFullFps / kPartialFraction;
constexpr double kUsbStereoMbPerSec = 2.0 * 3.0 * 48000.0 / 1e6;  // 0.288 MB/s

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

inline void fnvMixBytes(const uint8_t* data, int bytes, uint64_t* hash) {
  for (int i = 0; i < bytes; ++i) {
    *hash ^= data[i];
    *hash *= 1099511628211ull;
  }
}

struct S3Voice {
  FmCore fm;
  Oscillator osc;
  Filter filter;
  Envelope env[2];
  Lfo lfo;
  float baseCutoff = 1200.0f;
  float panL = 0.7f;
  float panR = 0.7f;
};

struct S3Grain {
  uint32_t pos = 0;
  float phase = 0.0f;
};

struct S3Track {
  Filter filter;
  S3Grain grains[kS3Grains];
  float panL = 0.7f;
  float panR = 0.7f;
};

class S3ProfileScenario final : public IScenario {
 public:
  ~S3ProfileScenario() override {
    delete[] pool_;
    delete framebuffer_;
    delete[] bounce_;
  }
  const char* name() const override { return "s3_profile"; }
  const char* description() const override {
    return "S3-base: 4 MiB pool + 750 KiB framebuffer + 25 KiB bounce, 6 FM "
           "voices + 4 granular tracks, SPI (~13 fps full) / RGB565 (>=15 fps) "
           "models, USB FS stereo (D-46/D-48/D-51)";
  }
  Criteria criteria() const override { return Criteria::audio(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    rng_ = static_cast<uint32_t>(config.seed | 1u);
    blockCount_ = 0;
    stripeRow_ = 0;
    if (!pool_) {
      pool_ = new float[kPoolSamples];
      framebuffer_ = new ui::Framebuffer800();
      bounce_ = new uint16_t[800 * kStripeRows];
      if (!pool_ || !framebuffer_ || !framebuffer_->valid() || !bounce_) return false;
      for (int i = 0; i < kPoolSamples; ++i) {
        pool_[i] = std::sin(static_cast<float>(i) * 0.0019f) * 0.4f +
                   std::sin(static_cast<float>(i) * 0.00037f) * 0.25f;
      }
    }
    const float ratios[4] = {1.0f, 1.0f, 2.0f, 3.0f};
    const float levels[4] = {1.0f, 0.35f, 0.30f, 0.25f};
    for (int v = 0; v < kS3Voices; ++v) {
      S3Voice& voice = voices_[v];
      const int note = 48 + v * 3;
      const float hz = 440.0f * std::pow(2.0f, (static_cast<float>(note) - 69.0f) / 12.0f);
      voice.fm.init();
      voice.fm.setParams(v % 8, ratios, levels, 0.12f);
      voice.fm.noteOn(hz);
      voice.osc.init();
      voice.osc.setWave(v % 8);
      voice.osc.setUnison(1);
      voice.osc.setFrequency(hz * 1.004f);
      voice.filter.init();
      voice.filter.setCharacter(CharMoog);
      voice.filter.setMode(Fm_LP24);
      voice.baseCutoff = 800.0f + 180.0f * static_cast<float>(v);
      voice.filter.setCutoff(voice.baseCutoff);
      voice.filter.setResonance(0.6f);
      for (int e = 0; e < 2; ++e) {
        voice.env[e].init();
        voice.env[e].setParams(0.006f, 0.18f, 0.55f, 0.25f, -0.15f, EnvAdsr);
        voice.env[e].noteOn(0.8f);
      }
      voice.lfo.init();
      voice.lfo.setParams(0.7f, 0, false, false, 0.0f, 0.0f, 120.0f);
      voice.lfo.noteOn(60.0f);
      const float angle = ((v % 2 == 0 ? -0.4f : 0.4f) * 0.5f + 0.5f) * 3.14159265f * 0.5f;
      voice.panL = std::cos(angle);
      voice.panR = std::sin(angle);
    }
    for (int t = 0; t < kS3Tracks; ++t) {
      S3Track& track = tracks_[t];
      track.filter.init();
      track.filter.setCharacter(CharSvf);
      track.filter.setMode(Fm_LP24);
      track.filter.setCutoff(700.0f + 180.0f * static_cast<float>(t));
      track.filter.setResonance(0.4f);
      for (int g = 0; g < kS3Grains; ++g) {
        track.grains[g].pos = xorshift(&rng_) & (kPoolSamples - 1);
        track.grains[g].phase = static_cast<float>(g) / kS3Grains;
      }
      const float angle = ((t % 2 == 0 ? -0.3f : 0.3f) * 0.5f + 0.5f) * 3.14159265f * 0.5f;
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
    // --- 6 FM voices -------------------------------------------------------
    for (int v = 0; v < kS3Voices; ++v) {
      S3Voice& voice = voices_[v];
      const float lfo = voice.lfo.tickN(frames);
      voice.filter.setCutoff(voice.baseCutoff * std::pow(2.0f, lfo * 1.5f));
      for (int f = 0; f < frames; ++f) {
        float sample = voice.fm.tick() * 0.7f + voice.osc.tick() * 0.3f;
        sample = voice.filter.process(sample);
        sample *= voice.env[0].tick() * (0.85f + 0.15f * voice.env[1].tick());
        l[f] += sample * voice.panL;
        r[f] += sample * voice.panR;
      }
    }
    // --- 4 granular tracks (4 MiB pool) -----------------------------------
    for (int t = 0; t < kS3Tracks; ++t) {
      S3Track& track = tracks_[t];
      for (int f = 0; f < frames; ++f) {
        float sum = 0.0f;
        for (int g = 0; g < kS3Grains; ++g) {
          S3Grain& grain = track.grains[g];
          const float pos = static_cast<float>(grain.pos) +
                            grain.phase * static_cast<float>(kPoolSamples >> 10);
          sum += readCubic(pool_, kPoolSamples, pos) * 0.5f;
          grain.phase += 1.0f / 512.0f;
          if (grain.phase >= 1.0f) {
            grain.phase -= 1.0f;
            grain.pos = xorshift(&rng_) & (kPoolSamples - 1);
          }
        }
        float sample = track.filter.process(sum * 0.35f);
        sample = math::fastTanh(sample * 1.3f) * 0.7f;
        l[f] += sample * track.panL;
        r[f] += sample * track.panR;
      }
    }
    limiter_.process(l, r, frames);
    // --- UI: one dirty 16-line stripe per block + periodic full CPU redraw --
    const int y = stripeRow_;
    framebuffer_->fillRect(0, y, 800, kStripeRows, colors::kDim);
    framebuffer_->drawText(10, y + 6, "S3 PROFILE", colors::kGrey);
    std::memcpy(bounce_, framebuffer_->data() + y * 800, sizeof(uint16_t) * 800 * kStripeRows);
    stripeRow_ += kStripeRows;
    if (stripeRow_ >= 480) stripeRow_ = 0;
    ++blockCount_;
    if ((blockCount_ % 24) == 0) {  // ~30 ms: full UI redraw (CPU), DMA is async
      ui::drawUi800(*framebuffer_, snapshot_);
    }
    for (int f = 0; f < frames; ++f) {
      fnvMix(l[f], &checksum_);
      fnvMix(r[f], &checksum_);
    }
    fnvMixBytes(reinterpret_cast<const uint8_t*>(bounce_), 512, &checksum_);
    if (checksum_ == 0) checksum_ = 1;
  }

  uint64_t checksum() const override { return checksum_; }
  void rewind() override { prepare(config_); }

  bool scenarioCriteriaPass(double maxBlockUs, const char** reason) const override {
    if (maxBlockUs > kMaxBlockTimeUs) {
      if (reason) *reason = "S3 profile: max block above 650 us";
      return false;
    }
    if (kSpiPartialUpdates < 30.0) {
      if (reason) *reason = "S3 profile: partial updates < 30/s (D-46)";
      return false;
    }
    if (kRgbFullFps < 15.0) {
      if (reason) *reason = "S3 profile: RGB full refresh < 15 fps (D-46)";
      return false;
    }
    return true;
  }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    if (!out || !count) return;
    int n = 0;
    out[n++] = Metric{"pool_mib", static_cast<double>(kPoolSamples * 4) / (1024.0 * 1024.0), "MiB"};
    out[n++] = Metric{"framebuffer_kib", kFrameBytes / 1024.0, "KiB"};
    out[n++] = Metric{"bounce_kib", 800.0 * kStripeRows * 2.0 / 1024.0, "KiB"};
    out[n++] = Metric{"spi_full_fps", kSpiFullFps, "fps"};
    out[n++] = Metric{"spi_partial_updates_s", kSpiPartialUpdates, "updates/s"};
    out[n++] = Metric{"rgb_full_fps", kRgbFullFps, "fps"};
    out[n++] = Metric{"usb_stereo_mb_s", kUsbStereoMbPerSec, "MB/s"};
    *count = n;
    (void)meanBlockUs;
  }

 private:
  RunConfig config_{};
  float* pool_ = nullptr;
  ui::Framebuffer800* framebuffer_ = nullptr;
  uint16_t* bounce_ = nullptr;
  S3Voice voices_[kS3Voices];
  S3Track tracks_[kS3Tracks];
  Limiter limiter_;
  ui::UiSnapshot snapshot_{};
  uint32_t rng_ = 1;
  uint32_t blockCount_ = 0;
  int stripeRow_ = 0;
  uint64_t checksum_ = 0;
};

}  // namespace

IScenario* createS3ProfileScenario() { return new S3ProfileScenario(); }

}  // namespace bench
}  // namespace bukifon
