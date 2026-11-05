// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon P1 benchmark — on-device runner skeleton.
//
// Builds for ESP32-S3/P4 and STM32H743 (arduino-core) and prints JSON/table over
// Serial/USB-CDC.  The measured code is the same as on the host; only the timing
// source changes (micros(), 1 us resolution — see bench_timing.cpp).
//
//   pio run -d firmware -e bench_s3      (compile/upload; env exists)
//   pio run -d firmware -e bench_p4      (P4: prepared, needs P4 platform)
//   pio run -d firmware -e bench_h743    (prepared, needs ststm32 platform)
#include "bench_report.hpp"
#include "bench_types.hpp"

#if defined(ARDUINO)
#include <Arduino.h>

using namespace bukifon::bench;

namespace {

constexpr uint32_t kDeviceBlocks = 2000;
constexpr uint32_t kDeviceWarmup = 100;

void runAllScenarios() {
  RunConfig config;
  config.blocks = kDeviceBlocks;
  config.warmup = kDeviceWarmup;
  config.determinismCheck = true;

  ScenarioResult results[16];
  int count = 0;
  for (int i = 0; i < scenarioCount() && count < 16; ++i) {
    results[count++] = runNamedScenario(scenarioNameAt(i), config);
  }
  bool allPass = true;
  for (int i = 0; i < count; ++i) allPass = allPass && results[i].pass;

  BenchMeta meta;
  meta.tool = "bukifon-bench-device";
  meta.platform =
#if defined(BUKIFON_ESP32_P4)
      "ESP32-P4";
#elif defined(BUKIFON_ESP32_S3)
      "ESP32-S3";
#elif defined(BUKIFON_H743)
      "STM32H743";
#else
      "device";
#endif
  meta.host = meta.platform;
  meta.compiler = "arm-gcc";
  meta.timestamp = "device";
  meta.build = "firmware-bench";
  meta.notes = "1 us timer resolution; max block time is the decision metric";

  const std::string table = resultsToTable(results, count, allPass);
  Serial.println(table.c_str());
  const std::string json = resultsToJson(meta, results, count);
  Serial.println(json.c_str());
  Serial.printf("RESULT: %s\n", allPass ? "PASS" : "FAIL");
}

// Optional long soak: build with -DBUKIFON_BENCH_SOAK_HOURS=24.
void runSoak(uint32_t hours) {
  const uint32_t started = millis();
  const uint32_t durationMs = hours * 3600UL * 1000UL;
  uint32_t iterations = 0;
  uint64_t totalOverruns = 0;
  double worstMaxUs = 0.0;
  uint32_t lastPrint = started;
  Serial.printf("SOAK: %.0f h workload starting\n", static_cast<double>(hours));
  while (static_cast<uint32_t>(millis() - started) < durationMs) {
    for (int i = 0; i < scenarioCount(); ++i) {
      RunConfig config;
      config.blocks = kDeviceBlocks;
      config.warmup = 10;  // warm-up already paid; keep the soak cadence fast
      config.determinismCheck = false;
      const ScenarioResult result = runNamedScenario(scenarioNameAt(i), config);
      totalOverruns += result.overruns;
      if (result.stats.maxUs > worstMaxUs) worstMaxUs = result.stats.maxUs;
    }
    ++iterations;
    if (static_cast<uint32_t>(millis() - lastPrint) >= 60000UL) {
      lastPrint = millis();
      Serial.printf("SOAK: %.0f min, iterations=%u, overruns=%llu, worst_max=%.2f us\n",
                    static_cast<double>(lastPrint - started) / 60000.0, iterations,
                    static_cast<unsigned long long>(totalOverruns), worstMaxUs);
    }
  }
  Serial.printf("SOAK RESULT: iterations=%u overruns=%llu worst_max=%.2f us -> %s\n",
                iterations, static_cast<unsigned long long>(totalOverruns), worstMaxUs,
                (totalOverruns == 0 && worstMaxUs <= kMaxBlockTimeUs) ? "PASS" : "FAIL");
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Bukifon P1 benchmark (device build)");
#if defined(BUKIFON_BENCH_SOAK_HOURS) && BUKIFON_BENCH_SOAK_HOURS > 0
  runSoak(BUKIFON_BENCH_SOAK_HOURS);
#else
  runAllScenarios();
#endif
}

void loop() { delay(1000); }

#else
int main() {
  // Device-only TU; the host uses bench_main.cpp.
  return 0;
}
#endif
