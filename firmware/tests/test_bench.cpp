// SPDX-License-Identifier: GPL-3.0-or-later
// Tests for the P1 benchmark harness: frozen constants, pass/fail criterion,
// determinism, no allocations in the audio path, JSON/CSV output, metrics.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

#include "bench_alloc_probe.hpp"
#include "bench_report.hpp"
#include "bench_types.hpp"
#include "test_framework.hpp"

using namespace bukifon::bench;

namespace {

int metricIndex(const ScenarioResult& result, const char* name) {
  for (int i = 0; i < result.metricCount; ++i) {
    if (std::strcmp(result.metrics[i].name, name) == 0) return i;
  }
  return -1;
}

}  // namespace

TEST(BenchFrozenConstants) {
  CHECK(kSampleRate == 48000);
  CHECK(kBlockFrames == 64);
  CHECK(std::fabs(kDeadlineUs - 1333.3333) < 0.01);
  CHECK(std::fabs(kMaxBlockTimeUs - 650.0) < 1e-9);
  CHECK(std::fabs(kUiDeadlineUs - (1000000.0 / 30.0)) < 0.01);
  CHECK(std::fabs(kUsbUac2MbPerSec - 2.304) < 1e-9);
  INFO("bench: block=64 @48 kHz, deadline=%.3f us, criterion max<=%.0f us, UI deadline=%.1f us",
       kDeadlineUs, kMaxBlockTimeUs, kUiDeadlineUs);
}

TEST(BenchCriteriaPassFail) {
  const Criteria audio = Criteria::audio();
  TimingStats stats;
  stats.maxUs = 500.0;
  const char* reason = "x";
  CHECK(criteriaPass(audio, stats, 0, &reason));
  CHECK(std::strcmp(reason, "") == 0);
  stats.maxUs = 700.0;
  CHECK(!criteriaPass(audio, stats, 0, &reason));
  CHECK(std::strcmp(reason, "max block time above criterion") == 0);
  stats.maxUs = 500.0;
  CHECK(!criteriaPass(audio, stats, 1, &reason));
  CHECK(std::strcmp(reason, "overruns above criterion") == 0);
  const Criteria ui = Criteria::ui();
  stats.maxUs = 20000.0;  // 50 fps: fine for UI, not for audio
  CHECK(criteriaPass(ui, stats, 0, &reason));
  CHECK(!criteriaPass(Criteria::audio(), stats, 0, &reason));
  INFO("bench criterion: max<=650 us for audio blocks; UI frame criterion 33.3 ms");
}

TEST(BenchScenarioRegistry) {
  CHECK(scenarioCount() >= 7);
  const char* required[6] = {"fm_voice", "granular_track", "mix_bus", "psram_stream", "ui_frame",
                             "usb_descriptor"};
  for (const char* name : required) {
    bool found = false;
    for (int i = 0; i < scenarioCount(); ++i) {
      if (std::strcmp(scenarioNameAt(i), name) == 0) found = true;
    }
    CHECK(found);
  }
  CHECK(createScenario("no_such_scenario") == nullptr);
  for (int i = 0; i < scenarioCount(); ++i) {
    CHECK(scenarioNameAt(i) != nullptr);
    CHECK(std::strlen(scenarioNameAt(i)) > 0);
  }
  INFO("bench registry: %d scenarios (frozen names)", scenarioCount());
}

TEST(BenchScenarioDeterminism) {
  RunConfig config;
  config.blocks = 8;
  config.warmup = 2;
  config.determinismCheck = true;
  for (int i = 0; i < scenarioCount(); ++i) {
    const ScenarioResult result = runNamedScenario(scenarioNameAt(i), config);
    INFO("  %-18s mean=%9.2f us max=%9.2f us det=%s checksum=%llx", result.name,
         result.stats.meanUs, result.stats.maxUs, result.deterministic ? "yes" : "no",
         static_cast<unsigned long long>(result.checksum));
    CHECK(result.deterministic);
    CHECK(result.checksum != 0);
    CHECK(result.blocks == 8);
    CHECK(result.blockFrames == 64);
    CHECK(result.stats.maxUs >= result.stats.minUs);
    CHECK(result.stats.meanUs > 0.0);
  }
}

TEST(BenchNoAllocationsInAudioPath) {
  const char* audioScenarios[3] = {"fm_voice", "granular_track", "mix_bus"};
  RunConfig config;
  config.blocks = 4;
  config.warmup = 2;
  for (const char* name : audioScenarios) {
    IScenario* scenario = createScenario(name);
    CHECK(scenario != nullptr);
    if (!scenario) continue;
    CHECK(scenario->prepare(config));
    float left[64] = {};
    float right[64] = {};
    for (int i = 0; i < 2; ++i) scenario->processBlock(left, right, 64);
    allocProbeBegin();
    for (int i = 0; i < 4; ++i) scenario->processBlock(left, right, 64);
    allocProbeEnd();
    const uint64_t allocations = allocProbeCount();
    INFO("  %-16s allocations in 4 audio blocks: %llu", name,
         static_cast<unsigned long long>(allocations));
    CHECK(allocations == 0);
    delete scenario;
  }
  allocProbeReset();
}

TEST(BenchJsonCsvOutput) {
  RunConfig config;
  config.blocks = 4;
  config.warmup = 1;
  const ScenarioResult results[2] = {runNamedScenario("fm_voice", config),
                                     runNamedScenario("ui_frame", config)};
  BenchMeta meta;
  meta.platform = "host-test";
  meta.compiler = "test";
  meta.timestamp = "2026-01-01T00:00:00Z";
  meta.notes = "unit-test";
  const std::string json = resultsToJson(meta, results, 2);
  CHECK(json.find("bukifon-bench-v1") != std::string::npos);
  CHECK(json.find("\"fm_voice\"") != std::string::npos);
  CHECK(json.find("\"ui_frame\"") != std::string::npos);
  CHECK(json.find("\"all_pass\"") != std::string::npos);
  CHECK(json.find("\"times_us\"") != std::string::npos);
  CHECK(json.find("\"deterministic\"") != std::string::npos);
  const std::string csv = resultsToCsv(results, 2);
  CHECK(csv.find("scenario,blocks,block_frames") == 0);
  CHECK(csv.find("fm_voice,") != std::string::npos);
  const std::string table = resultsToTable(results, 2, false);
  CHECK(table.find("fm_voice") != std::string::npos);
  CHECK(table.find("RESULT: FAIL") != std::string::npos);
  const char* path = "../tests/out/bench_test.json";
  CHECK(writeTextFile(path, json));
  std::remove(path);
  INFO("bench JSON/CSV: schema, scenario rows and table rendering verified");
}

TEST(BenchMetrics) {
  RunConfig config;
  config.blocks = 4;
  config.warmup = 1;

  const ScenarioResult psram = runNamedScenario("psram_stream", config);
  const int mbIndex = metricIndex(psram, "mb_per_s");
  const int nsIndex = metricIndex(psram, "ns_per_line");
  CHECK(mbIndex >= 0 && nsIndex >= 0);
  if (mbIndex >= 0) {
    INFO("psram_stream: %.2f MB/s, %.1f ns/line (%u lines/block)",
         psram.metrics[mbIndex].value, psram.metrics[nsIndex].value, 512u);
    CHECK(std::fabs(psram.metrics[mbIndex].value - 24.576) < 0.1);
  }

  const ScenarioResult ui = runNamedScenario("ui_frame", config);
  const int fpsIndex = metricIndex(ui, "fps");
  CHECK(fpsIndex >= 0);
  if (fpsIndex >= 0) {
    INFO("ui_frame: %.2f fps equivalent on this host", ui.metrics[fpsIndex].value);
    CHECK(ui.metrics[fpsIndex].value > 5.0);
  }
  CHECK(ui.criteria.name != nullptr);
  CHECK(std::fabs(ui.criteria.deadlineUs - kUiDeadlineUs) < 0.01);

  const ScenarioResult usb = runNamedScenario("usb_descriptor", config);
  const int reqIndex = metricIndex(usb, "uac2_required_mb_s");
  const int fsIndex = metricIndex(usb, "usb_fs_feasible");
  const int hsIndex = metricIndex(usb, "usb_hs_feasible");
  CHECK(reqIndex >= 0 && fsIndex >= 0 && hsIndex >= 0);
  if (reqIndex >= 0) {
    CHECK(std::fabs(usb.metrics[reqIndex].value - 2.304) < 1e-6);
    CHECK(usb.metrics[fsIndex].value == 0.0);  // Full-Speed cannot carry 8x8/24/48
    CHECK(usb.metrics[hsIndex].value == 1.0);  // High-Speed can
    INFO("usb_descriptor: UAC2 8x8/24/48 requires %.3f MB/s; FS feasible=%d HS feasible=%d",
         usb.metrics[reqIndex].value, static_cast<int>(usb.metrics[fsIndex].value),
         static_cast<int>(usb.metrics[hsIndex].value));
  }
}

TEST(BenchUiPartialFrame) {
  RunConfig config;
  config.blocks = 4;
  config.warmup = 1;
  const ScenarioResult full = runNamedScenario("ui_frame", config);
  const ScenarioResult partial = runNamedScenario("ui_frame_partial", config);
  INFO("ui_frame full: mean %.2f us; partial: mean %.2f us", full.stats.meanUs,
       partial.stats.meanUs);
  CHECK(full.checksum != 0);
  CHECK(partial.checksum != 0);
  CHECK(full.deterministic);
  CHECK(partial.deterministic);
  CHECK(std::strcmp(partial.name, "ui_frame_partial") == 0);
}
