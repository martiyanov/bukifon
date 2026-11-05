// SPDX-License-Identifier: GPL-3.0-or-later
#include "bench_types.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace bukifon {
namespace bench {

Criteria Criteria::audio() { return Criteria{kDeadlineUs, kMaxBlockTimeUs, 0, "audio-block"}; }
Criteria Criteria::ui() { return Criteria{kUiDeadlineUs, kUiMaxFrameUs, 0, "ui-frame"}; }
Criteria Criteria::usb() { return Criteria{2000.0, 2000.0, 0, "usb-descriptor"}; }

// Evaluates the frozen pass criterion and explains the failure.
bool criteriaPass(const Criteria& criteria, const TimingStats& stats, uint32_t overruns,
                  const char** reason) {
  if (stats.maxUs > criteria.maxBlockTimeUs) {
    if (reason) *reason = "max block time above criterion";
    return false;
  }
  if (overruns > criteria.maxOverruns) {
    if (reason) *reason = "overruns above criterion";
    return false;
  }
  if (reason) *reason = "";
  return true;
}

void computeStats(const double* samples, uint32_t count, TimingStats* stats) {
  if (!samples || !stats || count == 0) return;
  stats->minUs = samples[0];
  stats->maxUs = samples[0];
  double sum = 0.0;
  for (uint32_t i = 0; i < count; ++i) {
    stats->minUs = std::min(stats->minUs, samples[i]);
    stats->maxUs = std::max(stats->maxUs, samples[i]);
    sum += samples[i];
  }
  stats->meanUs = sum / static_cast<double>(count);
  // Percentiles: copy and sort (outside the audio path).
  const uint32_t maxSort = 8192;
  const uint32_t n = count < maxSort ? count : maxSort;
  double sorted[8192];
  std::memcpy(sorted, samples, sizeof(double) * n);
  std::sort(sorted, sorted + n);
  auto percentile = [&](double q) {
    if (n == 0) return 0.0;
    double index = q * (static_cast<double>(n) - 1.0);
    uint32_t lo = static_cast<uint32_t>(std::floor(index));
    uint32_t hi = static_cast<uint32_t>(std::ceil(index));
    if (hi >= n) hi = n - 1;
    const double frac = index - static_cast<double>(lo);
    return sorted[lo] * (1.0 - frac) + sorted[hi] * frac;
  };
  stats->p50Us = percentile(0.50);
  stats->p95Us = percentile(0.95);
  stats->p99Us = percentile(0.99);
}

}  // namespace bench
}  // namespace bukifon
