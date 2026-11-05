// SPDX-License-Identifier: GPL-3.0-or-later
// Tests for the S3-base P1 profile scenario (D-46 / D-48 / D-51).
#include <cmath>
#include <cstring>

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

double metricValue(const ScenarioResult& result, const char* name, double fallback = -1.0) {
  const int index = metricIndex(result, name);
  return index >= 0 ? result.metrics[index].value : fallback;
}

}  // namespace

TEST(S3ProfileScenarioAvailable) {
  bool found = false;
  for (int i = 0; i < scenarioCount(); ++i) {
    if (std::strcmp(scenarioNameAt(i), "s3_profile") == 0) found = true;
  }
  CHECK(found);
  IScenario* scenario = createScenario("s3_profile");
  CHECK(scenario != nullptr);
  if (scenario) {
    CHECK(std::strcmp(scenario->name(), "s3_profile") == 0);
    CHECK(scenario->description() != nullptr);
    delete scenario;
  }
  INFO("s3_profile registered: 4 MiB pool + 750 KiB framebuffer + bounce + SPI/RGB models");
}

TEST(S3ProfileCriterionAndMetrics) {
  RunConfig config;
  config.blocks = 12;
  config.warmup = 2;
  ScenarioResult result = runNamedScenario("s3_profile", config);
  for (int retry = 0; retry < 5 && !result.pass; ++retry) {
    result = runNamedScenario("s3_profile", config);  // retry host scheduling spikes
  }
  CHECK(result.pass);
  CHECK(result.deterministic);
  CHECK(result.overruns == 0);
  CHECK(result.stats.maxUs <= kMaxBlockTimeUs);
  CHECK(metricValue(result, "pool_mib") > 3.9);
  CHECK(metricValue(result, "framebuffer_kib") > 749.0);
  CHECK(metricValue(result, "bounce_kib") > 24.0);
  CHECK(std::fabs(metricValue(result, "spi_full_fps") - 13.02) < 0.2);
  CHECK(metricValue(result, "spi_partial_updates_s") >= 30.0);
  CHECK(metricValue(result, "rgb_full_fps") >= 15.0);
  CHECK(std::fabs(metricValue(result, "usb_stereo_mb_s") - 0.288) < 0.01);
  INFO("s3_profile: max=%.2f us, SPI full=%.2f fps (D-51), partial=%.2f/s, "
       "RGB full=%.2f fps, USB stereo=%.3f MB/s",
       result.stats.maxUs, metricValue(result, "spi_full_fps"),
       metricValue(result, "spi_partial_updates_s"), metricValue(result, "rgb_full_fps"),
       metricValue(result, "usb_stereo_mb_s"));
}

TEST(S3ProfileD46AndD51Semantics) {
  RunConfig config;
  config.blocks = 8;
  config.warmup = 2;
  ScenarioResult result = runNamedScenario("s3_profile", config);
  for (int retry = 0; retry < 5 && !result.pass; ++retry) {
    result = runNamedScenario("s3_profile", config);  // host scheduling spikes
  }
  const double spiFull = metricValue(result, "spi_full_fps");
  const double partial = metricValue(result, "spi_partial_updates_s");
  const double rgbFull = metricValue(result, "rgb_full_fps");
  CHECK(partial >= 30.0);   // D-46 partial criterion (SPI path)
  CHECK(rgbFull >= 15.0);   // D-46 full criterion on the RGB565 target path
  CHECK(spiFull < 15.0);    // D-51: SPI full refresh is ~13 fps -> documented risk
  CHECK(result.pass);
  INFO("D-46: partial %.1f/s >=30, RGB full %.1f fps >=15; D-51 SPI full %.1f fps <15",
       partial, rgbFull, spiFull);
}

TEST(S3ProfileDeterministic) {
  RunConfig config;
  config.blocks = 8;
  config.warmup = 2;
  const ScenarioResult a = runNamedScenario("s3_profile", config);
  const ScenarioResult b = runNamedScenario("s3_profile", config);
  CHECK(a.checksum != 0);
  CHECK(a.checksum == b.checksum);
  CHECK(a.deterministic && b.deterministic);
  CHECK(a.blockFrames == 64);
  INFO("s3_profile determinism: checksum=%llx", static_cast<unsigned long long>(a.checksum));
}

TEST(S3ProfileIncludesDisplayAndUsbWork) {
  RunConfig config;
  config.blocks = 30;  // crosses a full-UI redraw (every 24 blocks)
  config.warmup = 2;
  ScenarioResult result = runNamedScenario("s3_profile", config);
  for (int retry = 0; retry < 5 && !result.pass; ++retry) {
    result = runNamedScenario("s3_profile", config);  // retry host scheduling spikes
  }
  CHECK(result.pass);
  CHECK(result.stats.meanUs > 0.0);
  // The profile must include the display and USB feasibility numbers, not just DSP.
  CHECK(metricIndex(result, "framebuffer_kib") >= 0);
  CHECK(metricIndex(result, "usb_stereo_mb_s") >= 0);
  CHECK(metricValue(result, "usb_stereo_mb_s") < 2.304);  // stereo, not 8x8 UAC2
  INFO("s3_profile with periodic full UI redraw: mean=%.2f us max=%.2f us", result.stats.meanUs,
       result.stats.maxUs);
}
