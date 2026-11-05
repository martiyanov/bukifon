// SPDX-License-Identifier: GPL-3.0-or-later
// S3 vertical-slice spike — portable core (buffers, metrics, parsers, host sim).
//
// This header is shared by the Arduino spike (`spike_main.cpp`), the host
// simulation (`spike_sim.cpp`) and the host test suite (`tests/test_spike.cpp`).
// It is header-only so the spike stays an isolated folder and does not touch the
// engine build.  Everything here is deterministic and allocation-free except the
// host simulation helpers.
//
// IMPORTANT: S3 is now the "lite" concept platform (customer decision: P4 with
// RGB565/DSI is the first SKU).  The same measurements validate PCM5102A/PCM1808,
// SD, USB composite and panel scan; display numbers are SPI-only and must be
// re-run on P4 with RGB565/DSI (see docs/39 and README).
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "spike_config.h"

namespace bukifon {
namespace spike {

// ---------------------------------------------------------------------------
// Metric accumulator: min/max/mean + 32 us histogram (device-safe p99 estimate).
// ---------------------------------------------------------------------------
struct MetricStats {
  static constexpr int kHistogramBins = 64;  // 32 us bins, 0..2048 us
  static constexpr double kBinUs = 32.0;

  double minValue = 0.0;
  double maxValue = 0.0;
  double sum = 0.0;
  uint64_t count = 0;
  uint64_t overBudget = 0;
  uint32_t histogram[kHistogramBins] = {};

  void reset() {
    minValue = 0.0;
    maxValue = 0.0;
    sum = 0.0;
    count = 0;
    overBudget = 0;
    std::memset(histogram, 0, sizeof(histogram));
  }

  void add(double valueUs, double budgetUs = 0.0) {
    if (count == 0) {
      minValue = valueUs;
      maxValue = valueUs;
    }
    if (valueUs < minValue) minValue = valueUs;
    if (valueUs > maxValue) maxValue = valueUs;
    sum += valueUs;
    ++count;
    if (budgetUs > 0.0 && valueUs > budgetUs) ++overBudget;
    int bin = static_cast<int>(valueUs / kBinUs);
    if (bin < 0) bin = 0;
    if (bin >= kHistogramBins) bin = kHistogramBins - 1;
    ++histogram[bin];
  }

  double mean() const { return count ? sum / static_cast<double>(count) : 0.0; }

  // p99 as the upper edge of the histogram bin where the cumulative count
  // reaches 99 %.  Resolution 32 us is enough for the 500 us criterion.
  double p99() const {
    if (count == 0) return 0.0;
    const double target = 0.99 * static_cast<double>(count);
    double cumulative = 0.0;
    for (int i = 0; i < kHistogramBins; ++i) {
      cumulative += histogram[i];
      if (cumulative >= target) return (i + 1) * kBinUs;
    }
    return kHistogramBins * kBinUs;
  }
};

// ---------------------------------------------------------------------------
// Spike metrics + docs/36 pass/fail + line log format.
// ---------------------------------------------------------------------------
struct SpikeMetrics {
  MetricStats blockUs;        // audio render/I2S block
  MetricStats fullFrameUs;    // full 800x480 flush
  MetricStats partialFrameUs; // dirty-rect flush
  MetricStats sdLatencyUs;    // SD write+read roundtrip
  MetricStats panelScanUs;    // MCP23017 scan

  uint64_t xruns = 0;
  uint64_t fullFrames = 0;
  uint64_t partialUpdates = 0;
  uint64_t usbDrops = 0;
  uint64_t usbReconnects = 0;
  uint64_t sdErrors = 0;
  uint64_t panelErrors = 0;
  uint64_t lcdDrift = 0;
  double fullFps = 0.0;
  double partialUpdatesPerSec = 0.0;
  uint32_t heapFree = 0;
  uint32_t psramFree = 0;

  void reset() {
    blockUs.reset();
    fullFrameUs.reset();
    partialFrameUs.reset();
    sdLatencyUs.reset();
    panelScanUs.reset();
    xruns = 0;
    fullFrames = 0;
    partialUpdates = 0;
    usbDrops = 0;
    usbReconnects = 0;
    sdErrors = 0;
    panelErrors = 0;
    lcdDrift = 0;
    fullFps = 0.0;
    partialUpdatesPerSec = 0.0;
    heapFree = 0;
    psramFree = 0;
  }

  // Criteria from docs/36 §2: audio stress, UI, USB, panel/SD health.
  bool pass(char* reason, size_t reasonLen) const {
    auto fail = [&](const char* text) {
      if (reason && reasonLen) std::snprintf(reason, reasonLen, "%s", text);
      return false;
    };
    if (blockUs.count == 0) return fail("no audio blocks measured");
    if (blockUs.maxValue > kAudioBudgetUs) return fail("audio max block > 650 us");
    if (blockUs.p99() > kAudioP99BudgetUs) return fail("audio p99 > 500 us");
    if (xruns != 0) return fail("audio xruns != 0");
    if (fullFps < 15.0) return fail("full UI < 15 fps");
    if (partialUpdatesPerSec < 30.0) return fail("partial UI < 30 updates/s");
    if (usbDrops != 0) return fail("USB drops != 0");
    if (usbReconnects != 0) return fail("USB reconnects != 0");
    if (sdErrors != 0) return fail("SD errors != 0");
    if (sdLatencyUs.maxValue > static_cast<double>(kSdLatencyBudgetUs))
      return fail("SD latency > 10 ms");
    if (panelErrors != 0) return fail("panel scan errors != 0");
    if (lcdDrift != 0) return fail("LCD drift != 0");
    if (reason && reasonLen) std::snprintf(reason, reasonLen, "PASS");
    return true;
  }

  // Machine-readable one-line log: "SPIKE_METRIC key=value ...".
  bool logLine(char* out, size_t len) const {
    if (!out || len == 0) return false;
    const int written = std::snprintf(
        out, len,
        "SPIKE_METRIC audio_max_us=%.2f audio_p99_us=%.2f audio_mean_us=%.2f "
        "audio_blocks=%llu xruns=%llu full_fps=%.2f partial_per_s=%.2f "
        "usb_drops=%llu usb_reconnects=%llu sd_max_us=%.2f sd_errors=%llu "
        "panel_max_us=%.2f panel_errors=%llu lcd_drift=%llu heap_free=%u psram_free=%u",
        blockUs.maxValue, blockUs.p99(), blockUs.mean(),
        static_cast<unsigned long long>(blockUs.count),
        static_cast<unsigned long long>(xruns), fullFps, partialUpdatesPerSec,
        static_cast<unsigned long long>(usbDrops),
        static_cast<unsigned long long>(usbReconnects), sdLatencyUs.maxValue,
        static_cast<unsigned long long>(sdErrors), panelScanUs.maxValue,
        static_cast<unsigned long long>(panelErrors),
        static_cast<unsigned long long>(lcdDrift), static_cast<unsigned>(heapFree),
        static_cast<unsigned>(psramFree));
    return written > 0 && static_cast<size_t>(written) < len;
  }
};

// ---------------------------------------------------------------------------
// Log parser (host side): turns SPIKE_METRIC lines into values.
// ---------------------------------------------------------------------------
struct SpikeLogValues {
  double audioMaxUs = 0.0;
  double audioP99Us = 0.0;
  double audioMeanUs = 0.0;
  uint64_t audioBlocks = 0;
  uint64_t xruns = 0;
  double fullFps = 0.0;
  double partialPerSec = 0.0;
  uint64_t usbDrops = 0;
  uint64_t usbReconnects = 0;
  double sdMaxUs = 0.0;
  uint64_t sdErrors = 0;
  double panelMaxUs = 0.0;
  uint64_t panelErrors = 0;
  uint64_t lcdDrift = 0;
  uint32_t heapFree = 0;
  uint32_t psramFree = 0;
  bool seenAudio = false;
  bool seenDisplay = false;
  bool seenUsb = false;
  bool seenSd = false;
};

struct SpikeLogParser {
  SpikeLogValues values{};

  void reset() { values = SpikeLogValues{}; }

  static bool extractDouble(const char* line, const char* key, double* out) {
    const char* at = std::strstr(line, key);
    if (!at) return false;
    at += std::strlen(key);
    if (*at != '=') return false;
    char* end = nullptr;
    const double value = std::strtod(at + 1, &end);
    if (end == at + 1) return false;
    *out = value;
    return true;
  }

  static bool extractU64(const char* line, const char* key, uint64_t* out) {
    const char* at = std::strstr(line, key);
    if (!at) return false;
    at += std::strlen(key);
    if (*at != '=') return false;
    char* end = nullptr;
    const unsigned long long value = std::strtoull(at + 1, &end, 10);
    if (end == at + 1) return false;
    *out = static_cast<uint64_t>(value);
    return true;
  }

  bool parseLine(const char* line) {
    if (!line || std::strncmp(line, "SPIKE_METRIC", 12) != 0) return false;
    SpikeLogValues v;
    bool ok = true;
    ok = extractDouble(line, "audio_max_us", &v.audioMaxUs) && ok;
    ok = extractDouble(line, "audio_p99_us", &v.audioP99Us) && ok;
    ok = extractDouble(line, "audio_mean_us", &v.audioMeanUs) && ok;
    ok = extractU64(line, "audio_blocks", &v.audioBlocks) && ok;
    ok = extractU64(line, "xruns", &v.xruns) && ok;
    ok = extractDouble(line, "full_fps", &v.fullFps) && ok;
    ok = extractDouble(line, "partial_per_s", &v.partialPerSec) && ok;
    ok = extractU64(line, "usb_drops", &v.usbDrops) && ok;
    ok = extractU64(line, "usb_reconnects", &v.usbReconnects) && ok;
    ok = extractDouble(line, "sd_max_us", &v.sdMaxUs) && ok;
    ok = extractU64(line, "sd_errors", &v.sdErrors) && ok;
    ok = extractDouble(line, "panel_max_us", &v.panelMaxUs) && ok;
    ok = extractU64(line, "panel_errors", &v.panelErrors) && ok;
    ok = extractU64(line, "lcd_drift", &v.lcdDrift) && ok;
    uint64_t heapFree = 0;
    uint64_t psramFree = 0;
    ok = extractU64(line, "heap_free", &heapFree) && ok;
    ok = extractU64(line, "psram_free", &psramFree) && ok;
    v.heapFree = static_cast<uint32_t>(heapFree);
    v.psramFree = static_cast<uint32_t>(psramFree);
    if (!ok) return false;
    v.seenAudio = true;
    v.seenDisplay = true;
    v.seenUsb = true;
    v.seenSd = true;
    values = v;
    return true;
  }
};

// ---------------------------------------------------------------------------
// Audio loopback ring (I2S out/in): stereo interleaved frames.
// ---------------------------------------------------------------------------
class AudioRing {
 public:
  bool init(float* storage, uint32_t capacityFrames, uint32_t channels = 2) {
    if (!storage || capacityFrames == 0 || channels == 0) return false;
    data_ = storage;
    capacityFrames_ = capacityFrames;
    channels_ = channels;
    reset();
    return true;
  }

  void reset() {
    writeFrame_ = 0;
    readFrame_ = 0;
    pushed_ = 0;
    popped_ = 0;
    overflows_ = 0;
    underruns_ = 0;
  }

  uint32_t available() const {
    const uint32_t used =
        (writeFrame_ + capacityFrames_ - readFrame_) % capacityFrames_;
    return used;
  }

  uint32_t push(const float* interleaved, uint32_t frames) {
    uint32_t accepted = 0;
    for (uint32_t f = 0; f < frames; ++f) {
      if (available() + 1 >= capacityFrames_) {
        ++overflows_;
        break;
      }
      for (uint32_t c = 0; c < channels_; ++c) {
        data_[writeFrame_ * channels_ + c] = interleaved ? interleaved[f * channels_ + c] : 0.0f;
      }
      writeFrame_ = (writeFrame_ + 1) % capacityFrames_;
      ++accepted;
      ++pushed_;
    }
    return accepted;
  }

  uint32_t pop(float* out, uint32_t frames) {
    uint32_t produced = 0;
    for (uint32_t f = 0; f < frames; ++f) {
      if (available() == 0) {
        ++underruns_;
        break;
      }
      for (uint32_t c = 0; c < channels_; ++c) {
        out[f * channels_ + c] = data_[readFrame_ * channels_ + c];
      }
      readFrame_ = (readFrame_ + 1) % capacityFrames_;
      ++produced;
      ++popped_;
    }
    return produced;
  }

  uint64_t pushed() const { return pushed_; }
  uint64_t popped() const { return popped_; }
  uint64_t overflows() const { return overflows_; }
  uint64_t underruns() const { return underruns_; }

 private:
  float* data_ = nullptr;
  uint32_t capacityFrames_ = 0;
  uint32_t channels_ = 2;
  uint32_t writeFrame_ = 0;
  uint32_t readFrame_ = 0;
  uint64_t pushed_ = 0;
  uint64_t popped_ = 0;
  uint64_t overflows_ = 0;
  uint64_t underruns_ = 0;
};

// ---------------------------------------------------------------------------
// USB byte ring (4 KiB RX/TX); drops counted, never blocks.
// ---------------------------------------------------------------------------
class ByteRing {
 public:
  bool init(uint8_t* storage, uint32_t capacity) {
    if (!storage || capacity == 0) return false;
    data_ = storage;
    capacity_ = capacity;
    reset();
    return true;
  }
  void reset() {
    head_ = 0;
    tail_ = 0;
    drops_ = 0;
    pushed_ = 0;
    popped_ = 0;
  }
  uint32_t available() const { return (head_ + capacity_ - tail_) % capacity_; }
  uint32_t push(const uint8_t* bytes, uint32_t count) {
    uint32_t accepted = 0;
    for (uint32_t i = 0; i < count; ++i) {
      if (available() + 1 >= capacity_) {
        ++drops_;
        break;
      }
      data_[head_] = bytes ? bytes[i] : 0;
      head_ = (head_ + 1) % capacity_;
      ++accepted;
      ++pushed_;
    }
    return accepted;
  }
  uint32_t pop(uint8_t* out, uint32_t count) {
    uint32_t produced = 0;
    for (uint32_t i = 0; i < count; ++i) {
      if (available() == 0) break;
      if (out) out[i] = data_[tail_];
      tail_ = (tail_ + 1) % capacity_;
      ++produced;
      ++popped_;
    }
    return produced;
  }
  uint64_t drops() const { return drops_; }
  uint64_t pushed() const { return pushed_; }
  uint64_t popped() const { return popped_; }

 private:
  uint8_t* data_ = nullptr;
  uint32_t capacity_ = 0;
  uint32_t head_ = 0;
  uint32_t tail_ = 0;
  uint64_t drops_ = 0;
  uint64_t pushed_ = 0;
  uint64_t popped_ = 0;
};

// ---------------------------------------------------------------------------
// RGB565 framebuffer + dirty rectangles + SPI bounce staging.
// ---------------------------------------------------------------------------
struct Framebuffer565 {
  uint16_t* pixels = nullptr;
  int width = 0;
  int height = 0;

  bool attach(uint16_t* memory, int w, int h) {
    if (!memory || w <= 0 || h <= 0) return false;
    pixels = memory;
    width = w;
    height = h;
    return true;
  }
  void clear(uint16_t color) {
    if (!pixels) return;
    for (int i = 0; i < width * height; ++i) pixels[i] = color;
  }
  void fillRect(int x, int y, int w, int h, uint16_t color) {
    if (!pixels) return;
    for (int row = y; row < y + h && row < height; ++row) {
      if (row < 0) continue;
      for (int col = x; col < x + w && col < width; ++col) {
        if (col < 0) continue;
        pixels[row * width + col] = color;
      }
    }
  }
  uint16_t at(int x, int y) const {
    if (!pixels || x < 0 || y < 0 || x >= width || y >= height) return 0;
    return pixels[y * width + x];
  }
};

struct DirtyRect {
  int x = 0;
  int y = 0;
  int w = 0;
  int h = 0;
};

class DirtyTracker {
 public:
  static constexpr int kMaxRects = 8;
  void reset() { count_ = 0; }
  bool add(int x, int y, int w, int h) {
    if (count_ >= kMaxRects || w <= 0 || h <= 0) return false;
    rects_[count_++] = DirtyRect{x, y, w, h};
    return true;
  }
  int count() const { return count_; }
  const DirtyRect& rect(int index) const { return rects_[index]; }

 private:
  DirtyRect rects_[kMaxRects] = {};
  int count_ = 0;
};

class BounceBuffer {
 public:
  bool init(uint16_t* storage, int width, int rows) {
    if (!storage || width <= 0 || rows <= 0) return false;
    storage_ = storage;
    width_ = width;
    rows_ = rows;
    reset();
    return true;
  }
  void reset() {
    stagedRows_ = 0;
    stagedBytes_ = 0;
    for (int r = 0; r < rows_; ++r) {
      for (int x = 0; x < width_; ++x) storage_[r * width_ + x] = 0;
    }
  }
  // Copies `rowCount` rows starting at `startRow` from a full framebuffer.
  int stageRows(const uint16_t* framebuffer, int fbWidth, int startRow, int rowCount) {
    if (!framebuffer || !storage_ || rowCount <= 0) return 0;
    int staged = 0;
    for (int r = 0; r < rowCount && r < rows_; ++r) {
      const int srcRow = startRow + r;
      if (srcRow < 0) continue;
      std::memcpy(storage_ + r * width_, framebuffer + srcRow * fbWidth,
                  sizeof(uint16_t) * static_cast<size_t>(width_));
      ++staged;
    }
    stagedRows_ += static_cast<uint64_t>(staged);
    stagedBytes_ += static_cast<uint64_t>(staged) * width_ * 2;
    return staged;
  }
  uint16_t* data() { return storage_; }
  const uint16_t* data() const { return storage_; }
  int width() const { return width_; }
  int rows() const { return rows_; }
  uint64_t stagedRows() const { return stagedRows_; }
  uint64_t stagedBytes() const { return stagedBytes_; }

 private:
  uint16_t* storage_ = nullptr;
  int width_ = 0;
  int rows_ = 0;
  uint64_t stagedRows_ = 0;
  uint64_t stagedBytes_ = 0;
};

// ---------------------------------------------------------------------------
// Pin map parser (validates spike_config.h against hardware/cores3/pinmap.csv).
// ---------------------------------------------------------------------------
struct ParsedPin {
  char signal[24] = {};
  int gpio = -1;
};

inline int parsePinmapCsv(const char* csv, ParsedPin* out, int maxPins) {
  if (!csv || !out || maxPins <= 0) return 0;
  int count = 0;
  const char* line = csv;
  while (*line && count < maxPins) {
    if (std::strncmp(line, "signal;", 7) == 0) {
      const char* nl = std::strchr(line, '\n');
      line = nl ? nl + 1 : line + std::strlen(line);
      continue;
    }
    const char* nl = std::strchr(line, '\n');
    const size_t lineLen = nl ? static_cast<size_t>(nl - line) : std::strlen(line);
    if (lineLen > 0) {
      const char* firstSemi = std::strchr(line, ';');
      if (firstSemi && static_cast<size_t>(firstSemi - line) < sizeof(out[0].signal)) {
        const size_t sigLen = static_cast<size_t>(firstSemi - line);
        std::memcpy(out[count].signal, line, sigLen);
        out[count].signal[sigLen] = '\0';
        char* end = nullptr;
        const long gpio = std::strtol(firstSemi + 1, &end, 10);
        out[count].gpio = (end && end != firstSemi + 1) ? static_cast<int>(gpio) : -1;
        if (out[count].gpio >= 0) ++count;
      }
    }
    line = nl ? nl + 1 : line + lineLen;
    if (lineLen == 0) break;
  }
  return count;
}

inline int findPin(const ParsedPin* pins, int count, const char* signal) {
  if (!pins || !signal) return -1;
  for (int i = 0; i < count; ++i) {
    if (std::strcmp(pins[i].signal, signal) == 0) return pins[i].gpio;
  }
  return -1;
}

inline bool pinsMatchConfig(const ParsedPin* pins, int count, char* mismatch, size_t len) {
  for (int i = 0; i < kPinCount; ++i) {
    const int gpio = findPin(pins, count, kPins[i].signal);
    if (gpio != kPins[i].gpio) {
      if (mismatch && len) {
        std::snprintf(mismatch, len, "%s expected %d, csv has %d", kPins[i].signal,
                      kPins[i].gpio, gpio);
      }
      return false;
    }
  }
  if (mismatch && len) mismatch[0] = '\0';
  return true;
}

// ---------------------------------------------------------------------------
// Host-side simulation (no hardware).  Deterministic; used by spike_sim.cpp
// and by the host test suite.  Device builds exclude it.
// ---------------------------------------------------------------------------
#if !defined(ARDUINO)
inline uint32_t spikeRandom(uint32_t* state) {
  *state = (*state * 1664525u) + 1013904223u;
  return *state;
}

inline bool runHostSpikeSimulation(uint32_t blocks, uint64_t seed, SpikeMetrics* metrics,
                                   char* report, size_t reportLen) {
  if (!metrics || blocks == 0) return false;
  metrics->reset();
  uint32_t rng = static_cast<uint32_t>(seed | 1u);
  const uint32_t fullPeriod = 50;    // blocks between full flushes (~15.2 fps)
  const uint32_t partialPeriod = 24; // blocks between partial updates (~31/s)
  for (uint32_t i = 0; i < blocks; ++i) {
    const double jitter = 190.0 + static_cast<double>(spikeRandom(&rng) % 200u);
    metrics->blockUs.add(jitter, kAudioBudgetUs);
    if (jitter > kAudioDeadlineUs) ++metrics->xruns;
    if ((i % fullPeriod) == 0) {
      metrics->fullFrames++;
      metrics->fullFrameUs.add(61500.0 + static_cast<double>(spikeRandom(&rng) % 1500u),
                               kAudioDeadlineUs);
    }
    if ((i % partialPeriod) == 0) {
      metrics->partialUpdates++;
      metrics->partialFrameUs.add(2400.0 + static_cast<double>(spikeRandom(&rng) % 900u));
    }
    if ((i % 200) == 0) {
      metrics->sdLatencyUs.add(1800.0 + static_cast<double>(spikeRandom(&rng) % 3500u),
                               kSdLatencyBudgetUs);
    }
    if ((i % 10) == 0) {
      metrics->panelScanUs.add(250.0 + static_cast<double>(spikeRandom(&rng) % 500u));
    }
  }
  const double seconds = static_cast<double>(blocks) * (static_cast<double>(kAudioBlockFrames) /
                                                        kAudioSampleRate);
  metrics->fullFps = static_cast<double>(metrics->fullFrames) / (seconds > 0 ? seconds : 1.0);
  metrics->partialUpdatesPerSec =
      static_cast<double>(metrics->partialUpdates) / (seconds > 0 ? seconds : 1.0);
  metrics->usbDrops = 0;
  metrics->usbReconnects = 0;
  metrics->heapFree = 180000;
  metrics->psramFree = 7000000;
  char reason[96] = {};
  const bool ok = metrics->pass(reason, sizeof(reason));
  if (report && reportLen) {
    std::snprintf(report, reportLen,
                  "{\"platform\":\"s3-lite-host-sim\",\"blocks\":%u,\"pass\":%s,"
                  "\"audio_max_us\":%.2f,\"full_fps\":%.2f,\"partial_per_s\":%.2f,"
                  "\"xruns\":%llu,\"reason\":\"%s\"}",
                  blocks, ok ? "true" : "false", metrics->blockUs.maxValue, metrics->fullFps,
                  metrics->partialUpdatesPerSec,
                  static_cast<unsigned long long>(metrics->xruns), reason);
  }
  return ok;
}
#endif

}  // namespace spike
}  // namespace bukifon
