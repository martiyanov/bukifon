// SPDX-License-Identifier: GPL-3.0-or-later
// Scenarios psram_stream, ui_frame and usb_descriptor (docs/05 §5-§7).
#include <cmath>
#include <cstring>

#include "ui/canvas.hpp"
#include "ui/ui800.hpp"
#include "usb/usb_descriptors.hpp"
#include "scenario_factories.hpp"

namespace bukifon {
namespace bench {
namespace {

inline uint32_t xorshift(uint32_t* state) {
  uint32_t x = *state;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  *state = x;
  return x;
}

inline void fnvMix(uint32_t value, uint64_t* hash) {
  *hash ^= value;
  *hash *= 1099511628211ull;
}

// --- psram_stream ----------------------------------------------------------
constexpr size_t kPsramBytes = 8u << 20;   // 8 MiB working set
constexpr int kLinesPerBlock = 512;        // 8 tracks x 4 grains x 16 lines
constexpr int kLineBytes = 64;             // PSRAM/cache line

class PsramStreamScenario final : public IScenario {
 public:
  ~PsramStreamScenario() override { delete[] memory_; }
  const char* name() const override { return "psram_stream"; }
  const char* description() const override {
    return "512 random 64-byte line reads per block from an 8 MiB buffer "
           "(granular working set; host DRAM proxy for PSRAM)";
  }
  Criteria criteria() const override { return Criteria::audio(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    rng_ = static_cast<uint32_t>(config.seed | 1u);
    if (!memory_) {
      memory_ = new uint8_t[kPsramBytes];
      if (!memory_) return false;
      for (size_t i = 0; i < kPsramBytes; ++i) {
        memory_[i] = static_cast<uint8_t>(xorshift(&rng_) & 0xFFu);
      }
    }
    rng_ = static_cast<uint32_t>(config.seed | 1u);
    return true;
  }

  void processBlock(float* l, float* r, int frames) override {
    (void)l;
    (void)r;
    (void)frames;
    uint64_t sum = 0;
    for (int i = 0; i < kLinesPerBlock; ++i) {
      const uint32_t offset = xorshift(&rng_) % (kPsramBytes - kLineBytes);
      uint64_t line[kLineBytes / sizeof(uint64_t)];
      std::memcpy(line, memory_ + offset, kLineBytes);
      sum += line[0] ^ line[1] ^ line[2] ^ line[3] ^ line[4] ^ line[5] ^ line[6] ^ line[7];
    }
    fnvMix(static_cast<uint32_t>(sum & 0xFFFFFFFFu), &checksum_);
    fnvMix(static_cast<uint32_t>(sum >> 32), &checksum_);
    if (checksum_ == 0) checksum_ = 1;
  }

  uint64_t checksum() const override { return checksum_; }
  void rewind() override { prepare(config_); }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    if (!out || !count) return;
    const double blocksPerSecond = 48000.0 / 64.0;
    const double bytesPerBlock = kLinesPerBlock * kLineBytes;
    int n = 0;
    out[n++] = Metric{"mb_per_s", bytesPerBlock * blocksPerSecond / 1e6, "MB/s"};
    out[n++] = Metric{"ns_per_line", meanBlockUs * 1000.0 / kLinesPerBlock, "ns"};
    out[n++] = Metric{"lines_per_block", static_cast<double>(kLinesPerBlock), "reads"};
    out[n++] = Metric{"working_set", static_cast<double>(kPsramBytes) / (1024.0 * 1024.0), "MiB"};
    *count = n;
  }

 private:
  RunConfig config_{};
  uint8_t* memory_ = nullptr;
  uint32_t rng_ = 1;
  uint64_t checksum_ = 0;
};

// --- ui_frame --------------------------------------------------------------
class UiFrameScenario final : public IScenario {
 public:
  explicit UiFrameScenario(bool partial) : partial_(partial) {}
  ~UiFrameScenario() override { delete framebuffer_; }
  const char* name() const override { return partial_ ? "ui_frame_partial" : "ui_frame"; }
  const char* description() const override {
    return partial_ ? "800x480 UI partial redraw (~43% of pixels: header, one track, params, hints)"
                    : "800x480 UI full-redraw into an RGB565 framebuffer (snapshot-driven shell)";
  }
  Criteria criteria() const override { return Criteria::ui(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    if (!framebuffer_) framebuffer_ = new ui::Framebuffer800();
    if (!framebuffer_ || !framebuffer_->valid()) return false;
    ui::uiSnapshotDemo(&snapshot_, ui::Screen::Sequencer);
    return true;
  }

  void processBlock(float* l, float* r, int frames) override {
    (void)l;
    (void)r;
    (void)frames;
    if (partial_) {
      drawPartial();
    } else {
      ui::drawUi800(*framebuffer_, snapshot_);
    }
    // Deterministic checksum over a sparse sample of the framebuffer.
    for (int y = 0; y < framebuffer_->height(); y += 7) {
      for (int x = 0; x < framebuffer_->width(); x += 7) {
        fnvMix(framebuffer_->at(x, y), &checksum_);
      }
    }
    if (checksum_ == 0) checksum_ = 1;
  }

  uint64_t checksum() const override { return checksum_; }
  void rewind() override { prepare(config_); }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    if (!out || !count) return;
    int n = 0;
    out[n++] = Metric{"fps", 1e6 / (meanBlockUs > 0.0 ? meanBlockUs : 1.0), "fps"};
    out[n++] = Metric{"pixels", 800.0 * 480.0, "px"};
    out[n++] = Metric{"partial", partial_ ? 1.0 : 0.0, "flag"};
    out[n++] = Metric{"frame_us", meanBlockUs, "us"};
    *count = n;
  }

 private:
  void drawPartial() {
    ui::Framebuffer800& fb = *framebuffer_;
    // Dirty rect 1: status bar.
    fb.fillRect(0, 0, 800, 56, colors::kDim);
    fb.drawText(12, 38, "SEQUENCER", colors::kGrey);
    // Dirty rect 2: first track card.
    fb.fillRect(10, 62, 780, 56, colors::kPanel);
    fb.drawText(16, 70, "PART 1", colors::kWhite);
    // Dirty rect 3: parameter panel (2 rows x 4 cells).
    fb.fillRect(10, 308, 780, 88, colors::kDim);
    for (int i = 0; i < 4; ++i) fb.drawText(20 + i * 194, 318, "PARAM", colors::kValue);
    // Dirty rect 4: encoder hints.
    fb.fillRect(0, 400, 800, 30, colors::kPanel);
    for (int i = 0; i < 8; ++i) fb.drawText(10 + i * 98, 410, "ENC", colors::kGrey);
  }

  RunConfig config_{};
  bool partial_ = false;
  ui::Framebuffer800* framebuffer_ = nullptr;
  ui::UiSnapshot snapshot_{};
  uint64_t checksum_ = 0;
};

// --- usb_descriptor --------------------------------------------------------
class UsbDescriptorScenario final : public IScenario {
 public:
  const char* name() const override { return "usb_descriptor"; }
  const char* description() const override {
    return "USB composite descriptor build (HID keyboard + MIDI + UAC2 + CDC) and "
           "UAC2 8x8/24/48 bandwidth feasibility check";
  }
  Criteria criteria() const override { return Criteria::usb(); }

  bool prepare(const RunConfig& config) override {
    config_ = config;
    checksum_ = 0;
    builder_.setVidPid(0x1209, 0x0001);
    return builder_.build();
  }

  void processBlock(float* l, float* r, int frames) override {
    (void)l;
    (void)r;
    (void)frames;
    if (!builder_.build()) {
      checksum_ = 0;
      return;
    }
    const auto& d = builder_.descriptors();
    for (uint8_t byte : d.device) fnvMix(byte, &checksum_);
    for (uint8_t byte : d.config) fnvMix(byte, &checksum_);
    for (uint8_t byte : d.hidReport) fnvMix(byte, &checksum_);
    if (checksum_ == 0) checksum_ = 1;
  }

  uint64_t checksum() const override { return checksum_; }
  void rewind() override { prepare(config_); }

  void collectMetrics(double meanBlockUs, Metric* out, int* count) const override {
    if (!out || !count) return;
    const auto& d = builder_.descriptors();
    int n = 0;
    out[n++] = Metric{"config_bytes", static_cast<double>(d.config.size()), "bytes"};
    out[n++] = Metric{"interfaces", static_cast<double>(d.interfaceCount), "ifaces"};
    out[n++] = Metric{"endpoints", static_cast<double>(d.endpointCount), "eps"};
    out[n++] = Metric{"uac2_required_mb_s", kUsbUac2MbPerSec, "MB/s"};
    out[n++] = Metric{"usb_fs_feasible", 0.0, "flag"};  // ~1 MB/s isoch < 2.304
    out[n++] = Metric{"usb_hs_feasible", 1.0, "flag"};  // HS ~60 MB/s >> 2.304
    out[n++] = Metric{"build_us", meanBlockUs, "us"};
    *count = n;
  }

 private:
  RunConfig config_{};
  usb::UsbCompositeBuilder builder_;
  uint64_t checksum_ = 0;
};

}  // namespace

IScenario* createPsramStreamScenario() { return new PsramStreamScenario(); }
IScenario* createUiFrameScenario(bool partial) { return new UiFrameScenario(partial); }
IScenario* createUsbDescriptorScenario() { return new UsbDescriptorScenario(); }

}  // namespace bench
}  // namespace bukifon
