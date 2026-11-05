// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon P1 benchmark — frozen workload types and pass/fail criteria.
//
// The workload is frozen in docs/05-benchmark-workload.md.  Everything here is
// portable C++17: the same scenario code runs on the host and on S3/P4/H743.
#pragma once

#include <cstdint>

namespace bukifon {
namespace bench {

// Audio block geometry (docs/05 §2).
constexpr int kSampleRate = 48000;
constexpr int kBlockFrames = 64;
constexpr double kDeadlineUs = 1000000.0 * kBlockFrames / kSampleRate;  // 1333.33 us
constexpr double kMaxBlockTimeUs = 650.0;  // pass criterion: max block <= 650 us

// UI: 800x480 frame, 30 fps target.
constexpr double kUiDeadlineUs = 1000000.0 / 30.0;  // 33333.3 us
constexpr double kUiMaxFrameUs = 1000000.0 / 30.0;

// Default measurement protocol.
constexpr uint32_t kDefaultBlocks = 2000;
constexpr uint32_t kDefaultWarmup = 100;
constexpr uint64_t kDefaultSeed = 0xB0C0FFEEull;

// USB UAC2 8x8 / 24 bit / 48 kHz: 8*3*2*48000 = 2.304 MB/s payload.
constexpr double kUsbUac2MbPerSec = 2.304;

struct Criteria {
  double deadlineUs;
  double maxBlockTimeUs;
  uint32_t maxOverruns;
  const char* name;
  static Criteria audio();
  static Criteria ui();
  static Criteria usb();
};

struct TimingStats {
  double minUs = 0.0;
  double maxUs = 0.0;
  double meanUs = 0.0;
  double p50Us = 0.0;
  double p95Us = 0.0;
  double p99Us = 0.0;
};

struct Metric {
  const char* name = "";
  double value = 0.0;
  const char* unit = "";
};

struct RunConfig {
  uint32_t blockFrames = kBlockFrames;
  uint32_t blocks = kDefaultBlocks;
  uint32_t warmup = kDefaultWarmup;
  uint64_t seed = kDefaultSeed;
  bool determinismCheck = true;
};

struct ScenarioResult {
  const char* name = "";
  const char* description = "";
  Criteria criteria{0.0, 0.0, 0, ""};
  TimingStats stats;
  uint32_t blockFrames = kBlockFrames;
  uint32_t blocks = 0;
  uint32_t overruns = 0;  // blocks slower than the real-time deadline
  bool deterministic = false;
  bool pass = false;
  const char* failReason = "";
  uint64_t checksum = 0;
  Metric metrics[8];
  int metricCount = 0;
};

// A benchmark scenario: prepare() may allocate; processBlock() is the measured
// audio path and MUST NOT allocate, lock, log or do I/O.
class IScenario {
 public:
  virtual ~IScenario() = default;
  virtual const char* name() const = 0;
  virtual const char* description() const = 0;
  virtual bool prepare(const RunConfig& config) = 0;
  virtual void processBlock(float* l, float* r, int frames) = 0;
  virtual uint64_t checksum() const = 0;
  // Reset all DSP/RNG state and checksum to the state right after prepare(),
  // without allocating.  Used for the determinism check.
  virtual void rewind() = 0;
  virtual Criteria criteria() const { return Criteria::audio(); }
  virtual void collectMetrics(double meanBlockUs, Metric* out, int* count) const {
    (void)meanBlockUs;
    (void)out;
    (void)count;
  }
};

// Registry (implemented in bench_scenarios.cpp).
int scenarioCount();
const char* scenarioNameAt(int index);
IScenario* createScenario(const char* name);

}  // namespace bench
}  // namespace bukifon
