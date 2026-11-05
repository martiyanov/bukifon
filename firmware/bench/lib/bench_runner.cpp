// SPDX-License-Identifier: GPL-3.0-or-later
// Benchmark runner: warm-up, per-block timing, percentiles, overruns and the
// determinism check (same scenario prepared with the same seed twice).
#include "bench_types.hpp"

#include <cstring>
#include <vector>

#include "bench_timing.hpp"

namespace bukifon {
namespace bench {

ScenarioResult runNamedScenario(const char* name, const RunConfig& config) {
  ScenarioResult result;
  result.name = name ? name : "";
  result.blockFrames = config.blockFrames;
  result.blocks = config.blocks;
  result.failReason = "";

  IScenario* scenario = createScenario(name);
  if (!scenario) {
    result.description = "";
    result.failReason = "unknown scenario";
    return result;
  }
  result.name = scenario->name();
  result.description = scenario->description();
  result.criteria = scenario->criteria();
  if (!scenario->prepare(config)) {
    result.failReason = "prepare failed";
    delete scenario;
    return result;
  }

  const int maxFrames = 256;
  if (config.blockFrames > static_cast<uint32_t>(maxFrames)) {
    result.failReason = "blockFrames too large for runner buffers";
    delete scenario;
    return result;
  }
  float left[maxFrames];
  float right[maxFrames];
  std::memset(left, 0, sizeof(left));
  std::memset(right, 0, sizeof(right));

  for (uint32_t i = 0; i < config.warmup; ++i) {
    scenario->processBlock(left, right, static_cast<int>(config.blockFrames));
  }

  std::vector<double> blockTimes(static_cast<size_t>(config.blocks > 0 ? config.blocks : 1));
  uint32_t overruns = 0;
  for (uint32_t i = 0; i < config.blocks; ++i) {
    const uint64_t start = nowNs();
    scenario->processBlock(left, right, static_cast<int>(config.blockFrames));
    const uint64_t end = nowNs();
    const double us = nsToUs(end - start);
    blockTimes[i] = us;
    if (us > result.criteria.deadlineUs) ++overruns;
  }
  result.overruns = overruns;
  result.checksum = scenario->checksum();

  if (config.determinismCheck) {
    scenario->rewind();
    for (uint32_t i = 0; i < config.warmup; ++i) {
      scenario->processBlock(left, right, static_cast<int>(config.blockFrames));
    }
    for (uint32_t i = 0; i < config.blocks; ++i) {
      scenario->processBlock(left, right, static_cast<int>(config.blockFrames));
    }
    result.deterministic = (scenario->checksum() == result.checksum);
  } else {
    result.deterministic = true;
  }

  computeStats(blockTimes.data(), config.blocks, &result.stats);
  const char* reason = "";
  result.pass = criteriaPass(result.criteria, result.stats, result.overruns, &reason);
  result.failReason = reason;
  if (result.pass) {
    const char* extraReason = "";
    if (!scenario->scenarioCriteriaPass(result.stats.maxUs, &extraReason)) {
      result.pass = false;
      result.failReason = extraReason;
    }
  }
  if (!result.deterministic) {
    result.pass = false;
    result.failReason = "non-deterministic output";
  }
  int metricCount = 0;
  scenario->collectMetrics(result.stats.meanUs, result.metrics, &metricCount);
  result.metricCount = metricCount > 8 ? 8 : metricCount;
  delete scenario;
  return result;
}

}  // namespace bench
}  // namespace bukifon
