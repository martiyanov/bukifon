// SPDX-License-Identifier: GPL-3.0-or-later
// Factory backend enable hooks: REAL/MOCK per subsystem, no fabricated PASS.
#include <cstdint>
#include <cstring>

#include "factory/hw_backends.hpp"
#include "factory/mock_hardware.hpp"
#include "factory/p4_hardware.hpp"
#include "factory/selftest.hpp"
#include "test_framework.hpp"

using namespace bukifon::factory;

namespace {

// Expected factory-test ids failing when a single backend uses the P4 stub.
const int kExpectedFailing[][3] = {
    {0, 1, 2},   // I2C: power, i2c scan, mcp23017 (MAX17048 handled below)
    {3, -1, -1}, // ADC
    {4, -1, -1}, // DAC
    {5, -1, -1}, // I2S
    {6, -1, -1}, // SD
    {7, 8, -1},  // DISPLAY: display patterns + WS2812 current
    {10, -1, -1},// USB
    {11, -1, -1},// CONTROLS
    {12, -1, -1},// CV
    {13, -1, -1},// MIDI
};

bool isExpected(int backend, int testId) {
  for (int i = 0; i < 3; ++i) {
    if (kExpectedFailing[backend][i] == testId) return true;
  }
  if (backend == 0 && testId == 9) return true;  // MAX17048 is I2C
  return false;
}

}  // namespace

TEST(FactoryHwBackendNamesAndDefaults) {
  CHECK(kHwBackendCount == 10);
  HwConfig config;
  CHECK(config.realCount() == 0);  // host build: all MOCK by default
  CHECK(config.allMock());
  for (int i = 0; i < kHwBackendCount; ++i) {
    CHECK(hwBackendName(static_cast<HwBackend>(i))[0] != '\0');
    CHECK(!hwRealDefault(static_cast<HwBackend>(i)));
  }
  CHECK(std::strcmp(hwBackendName(HwBackend::I2c), "I2C") == 0);
  CHECK(std::strcmp(hwBackendName(HwBackend::Midi), "MIDI") == 0);
  CHECK(BUKIFON_HW_MOCK == 0 && BUKIFON_HW_REAL == 1);
  INFO("backends: I2C/ADC/DAC/I2S/SD/DISPLAY/USB/CONTROLS/CV/MIDI, default MOCK in host");
}

TEST(FactoryHwAllMockPasses) {
  MockHardware real;
  MockHardware mock;
  HwConfig config;
  HybridHardware hybrid(real, mock, config);
  const Report report = runSelfTest(hybrid);
  CHECK(report.count == 14);
  CHECK(report.passCount == 14);
  CHECK(report.overallPass);
  INFO("all backends MOCK: 14/14 PASS (mock is not a hardware test)");
}

TEST(FactoryHwAllRealP4StubsFail) {
  P4FactoryHardware real;  // TODO(hw) stubs return false
  MockHardware mock;
  HwConfig config;
  for (int i = 0; i < kHwBackendCount; ++i) config.set(static_cast<HwBackend>(i), HwMode::Real);
  HybridHardware hybrid(real, mock, config);
  const Report report = runSelfTest(hybrid);
  CHECK(report.failCount == 14);
  CHECK(!report.overallPass);
  CHECK(report.passCount == 0);  // mock must NOT fabricate PASS for REAL backends
  INFO("all backends REAL (P4 stubs): 14/14 FAIL — no fabricated PASS");
}

TEST(FactoryHwSingleBackendSwitches) {
  for (int backend = 0; backend < kHwBackendCount; ++backend) {
    P4FactoryHardware real;
    MockHardware mock;
    HwConfig config;
    config.set(static_cast<HwBackend>(backend), HwMode::Real);
    HybridHardware hybrid(real, mock, config);
    const Report report = runSelfTest(hybrid);
    for (int testId = 0; testId < kTestCount; ++testId) {
      const TestStatus status = report.tests[testId].status;
      if (isExpected(backend, testId)) {
        CHECK(status == TestStatus::Fail);
      } else {
        CHECK(status == TestStatus::Pass);
      }
    }
    CHECK(!report.overallPass);
  }
  INFO("one-by-one switch: only the mapped factory tests fail; MOCK stays PASS");
}

TEST(FactoryHwRealProviderWorkingPasses) {
  // Simulates a working real driver set (values are plausible): all REAL -> PASS.
  MockHardware real;
  MockHardware mock;
  HwConfig config;
  for (int i = 0; i < kHwBackendCount; ++i) config.set(static_cast<HwBackend>(i), HwMode::Real);
  HybridHardware hybrid(real, mock, config);
  const Report report = runSelfTest(hybrid);
  CHECK(report.overallPass);
  CHECK(report.passCount == 14);
  INFO("all backends REAL with working providers: 14/14 PASS (enable order is runtime)");
}

TEST(FactoryHwFlagsAreIndependent) {
  MockHardware real;
  MockHardware mock;
  HwConfig config;
  HybridHardware hybrid(real, mock, config);
  hybrid.setMode(HwBackend::I2c, HwMode::Real);
  CHECK(hybrid.config().real(HwBackend::I2c));
  CHECK(!hybrid.config().real(HwBackend::Adc));
  CHECK(hybrid.config().realCount() == 1);
  hybrid.setMode(HwBackend::I2c, HwMode::Mock);
  CHECK(hybrid.config().allMock());
  // Enable order from docs/46: I2C -> panel -> codec -> display -> SD -> USB -> CV/MIDI.
  const HwBackend order[] = {HwBackend::I2c, HwBackend::Display, HwBackend::I2s,
                             HwBackend::Sd, HwBackend::Usb, HwBackend::Cv,
                             HwBackend::Midi};
  for (HwBackend backend : order) hybrid.setMode(backend, HwMode::Real);
  CHECK(hybrid.config().realCount() == 7);
  INFO("runtime flags independent; bench enable order documented in docs/46");
}
