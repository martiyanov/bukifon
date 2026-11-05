// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon P1 benchmark — host runner.
//
//   ./bukifon_bench [--json results/host.json] [--csv results/host.csv]
//                   [--blocks N] [--warmup N] [--scenario NAME|all]
//                   [--seed N] [--no-determinism] [--quick]
#include <cstdio>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

#include "bench_report.hpp"
#include "bench_types.hpp"

using namespace bukifon::bench;

namespace {

struct Args {
  const char* jsonPath = "results/host.json";
  const char* csvPath = "results/host.csv";
  const char* scenario = "all";
  uint32_t blocks = kDefaultBlocks;
  uint32_t warmup = kDefaultWarmup;
  uint64_t seed = kDefaultSeed;
  bool determinism = true;
};

void usage() {
  std::printf(
      "usage: bukifon_bench [--json PATH] [--csv PATH] [--scenario NAME|all]\n"
      "                     [--blocks N] [--warmup N] [--seed N] [--no-determinism] [--quick]\n");
}

Args parseArgs(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "--json") == 0 && i + 1 < argc) {
      args.jsonPath = argv[++i];
    } else if (std::strcmp(argv[i], "--csv") == 0 && i + 1 < argc) {
      args.csvPath = argv[++i];
    } else if (std::strcmp(argv[i], "--scenario") == 0 && i + 1 < argc) {
      args.scenario = argv[++i];
    } else if (std::strcmp(argv[i], "--blocks") == 0 && i + 1 < argc) {
      args.blocks = static_cast<uint32_t>(std::atoi(argv[++i]));
    } else if (std::strcmp(argv[i], "--warmup") == 0 && i + 1 < argc) {
      args.warmup = static_cast<uint32_t>(std::atoi(argv[++i]));
    } else if (std::strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
      args.seed = static_cast<uint64_t>(std::strtoull(argv[++i], nullptr, 0));
    } else if (std::strcmp(argv[i], "--no-determinism") == 0) {
      args.determinism = false;
    } else if (std::strcmp(argv[i], "--quick") == 0) {
      args.blocks = 100;
      args.warmup = 10;
    } else if (std::strcmp(argv[i], "--help") == 0) {
      usage();
      std::exit(0);
    } else {
      usage();
      std::exit(2);
    }
  }
  if (args.blocks == 0) args.blocks = 1;
  if (args.blocks > 100000) args.blocks = 100000;
  return args;
}

std::string makeTimestamp() {
  const std::time_t now = std::time(nullptr);
  std::tm tm{};
#if defined(_WIN32)
  localtime_s(&tm, &now);
#else
  localtime_r(&now, &tm);
#endif
  char buffer[32];
  std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &tm);
  return std::string(buffer);
}

const char* compilerName() {
#if defined(__clang__)
  return "clang " __clang_version__;
#elif defined(__GNUC__)
  return "gcc " __VERSION__;
#else
  return "unknown";
#endif
}

const char* platformName() {
#if defined(__APPLE__) && defined(__aarch64__)
  return "macOS arm64";
#elif defined(__APPLE__)
  return "macOS x86_64";
#elif defined(__linux__)
  return "Linux";
#else
  return "host";
#endif
}

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);
  RunConfig config;
  config.blocks = args.blocks;
  config.warmup = args.warmup;
  config.seed = args.seed;
  config.determinismCheck = args.determinism;

  std::vector<ScenarioResult> results;
  std::printf("Bukifon P1 benchmark (host reference run)\n");
  std::printf("block=%d frames @ %d Hz, deadline %.3f us, criterion max %.1f us\n",
              kBlockFrames, kSampleRate, kDeadlineUs, kMaxBlockTimeUs);
  std::printf("blocks=%u warmup=%u determinism=%s seed=0x%llx\n\n", config.blocks,
              config.warmup, config.determinismCheck ? "on" : "off",
              static_cast<unsigned long long>(config.seed));

  const bool runAll = std::strcmp(args.scenario, "all") == 0;
  for (int i = 0; i < scenarioCount(); ++i) {
    const char* name = scenarioNameAt(i);
    if (!runAll && std::strcmp(name, args.scenario) != 0) continue;
    const ScenarioResult result = runNamedScenario(name, config);
    results.push_back(result);
    std::printf("  %-18s mean %8.3f us  max %8.3f us  p99 %8.3f us  overruns %u  %s%s\n",
                result.name, result.stats.meanUs, result.stats.maxUs, result.stats.p99Us,
                result.overruns, result.pass ? "PASS" : "FAIL",
                result.deterministic ? "" : " (non-deterministic)");
  }
  if (results.empty()) {
    std::printf("ERROR: scenario '%s' not found\n", args.scenario);
    return 2;
  }

  bool allPass = true;
  for (const ScenarioResult& r : results) allPass = allPass && r.pass;
  std::printf("\n%s\n", resultsToTable(results.data(), static_cast<int>(results.size()),
                                      allPass)
                               .c_str());

  BenchMeta meta;
  meta.tool = "bukifon-bench";
  meta.platform = platformName();
  meta.host = "host";
  meta.compiler = compilerName();
  const std::string timestamp = makeTimestamp();
  meta.timestamp = timestamp.c_str();
  meta.build = "host-native";
  meta.notes = "Host timings are a reference for workload sanity, not a device verdict";

  const std::string json =
      resultsToJson(meta, results.data(), static_cast<int>(results.size()));
  const std::string csv = resultsToCsv(results.data(), static_cast<int>(results.size()));
  if (!writeTextFile(args.jsonPath, json)) {
    std::printf("ERROR: cannot write %s\n", args.jsonPath);
    return 3;
  }
  if (!writeTextFile(args.csvPath, csv)) {
    std::printf("ERROR: cannot write %s\n", args.csvPath);
    return 3;
  }
  std::printf("json: %s\ncsv:  %s\n", args.jsonPath, args.csvPath);
  std::printf("RESULT: %s\n", allPass ? "PASS" : "FAIL");
  return allPass ? 0 : 1;
}
