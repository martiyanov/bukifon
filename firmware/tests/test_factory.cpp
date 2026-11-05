// SPDX-License-Identifier: GPL-3.0-or-later
// Factory self-test tests: 14 docs/42 tests, validators, timeouts, JSON report,
// CLI and mock hardware.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

#include "factory/mock_hardware.hpp"
#include "factory/selftest.hpp"
#include "test_framework.hpp"

using namespace bukifon::factory;


TEST(FactoryTestList) {
  CHECK(kTestCount == 14);
  static const char* expected[14] = {
      "power_on",         "i2c_scan",       "mcp23017_walking", "mcp3208_vector",
      "dac_adc_loopback", "codec_loopback", "sd_scratch",       "display_patterns",
      "ws2812_current",   "max17048",       "usb_composite",    "controls",
      "cv_gate_loopback", "midi_loopback"};
  uint32_t totalNominal = 0;
  for (int i = 0; i < kTestCount; ++i) {
    CHECK(std::strcmp(testName(static_cast<TestId>(i)), expected[i]) == 0);
    CHECK(nominalTimeMs(static_cast<TestId>(i)) > 0);
    CHECK(timeoutMs(static_cast<TestId>(i)) > nominalTimeMs(static_cast<TestId>(i)));
    totalNominal += nominalTimeMs(static_cast<TestId>(i));
  }
  CHECK(totalNominal > 35000 && totalNominal < 45000);  // ~38 s automation
  INFO("factory: 14 tests, nominal automation %.1f s (EOL 2-2.5 min with operator)",
       static_cast<double>(totalNominal) / 1000.0);
}

TEST(FactoryAllPassMock) {
  MockHardware hardware;
  const Report report = runSelfTest(hardware);
  CHECK(report.count == 14);
  CHECK(report.passCount == 14);
  CHECK(report.failCount == 0);
  CHECK(report.overallPass);
  CHECK(report.totalDurationMs > 0);
  CHECK(hardware.clockMs() >= report.totalDurationMs);
  INFO("factory all-pass mock: 14/14, total %u ms", report.totalDurationMs);
}

TEST(FactoryValidatorsPowerI2cMcp) {
  char detail[96];
  CHECK(checkPower(PowerInfo{1, 0, true}, detail, sizeof(detail)));
  CHECK(!checkPower(PowerInfo{1, 1, true}, detail, sizeof(detail)));  // brownout
  CHECK(std::strstr(detail, "brownout") != nullptr);
  CHECK(!checkPower(PowerInfo{3, 0, true}, detail, sizeof(detail)));  // wrong reset reason

  I2cScanInfo i2c{};
  const uint8_t addresses[] = {0x20, 0x21, 0x22, 0x23, 0x36, 0x57, 0x60, 0x61};
  i2c.count = 8;
  std::memcpy(i2c.addresses, addresses, sizeof(addresses));
  CHECK(checkI2c(i2c, detail, sizeof(detail)));
  i2c.addresses[5] = 0x58;  // wrong address instead of 0x57
  CHECK(!checkI2c(i2c, detail, sizeof(detail)));
  CHECK(std::strstr(detail, "0x57") != nullptr);

  Mcp23017Info mcp{};
  for (int i = 0; i < 4; ++i) mcp.addressesAck[i] = true;
  mcp.irqToggles = true;
  CHECK(checkMcp23017(mcp, detail, sizeof(detail)));
  mcp.irqToggles = false;
  CHECK(!checkMcp23017(mcp, detail, sizeof(detail)));
  INFO("validators: power/brownout, strict I2C address set, MCP23017 walking-bit");
}

TEST(FactoryValidatorsMcp3208Dac) {
  char detail[96];
  Mcp3208Info adc{};
  const float good[8] = {0.25f, 1.25f, 2.5f, 0.25f, 1.25f, 2.5f, 0.25f, 1.25f};
  std::memcpy(adc.volts, good, sizeof(good));
  CHECK(checkMcp3208(adc, detail, sizeof(detail)));
  adc.volts[7] = 1.30f;
  CHECK(!checkMcp3208(adc, detail, sizeof(detail)));

  DacAdcInfo dac{};
  const float errors[4] = {5.0f, -10.0f, 20.0f, 0.0f};
  std::memcpy(dac.errorsMv, errors, sizeof(errors));
  CHECK(checkDacAdc(dac, detail, sizeof(detail)));
  dac.errorsMv[2] = 20.1f;
  CHECK(!checkDacAdc(dac, detail, sizeof(detail)));
  INFO("validators: MCP3208 fixture vector +-2 LSB, MCP4728->MCP3208 <=20 mV");
}

TEST(FactoryValidatorsCodecSd) {
  char detail[96];
  CodecInfo codec{1000.0f, 0.2f, -70.0f, -12.0f};
  CHECK(checkCodec(codec, detail, sizeof(detail)));
  codec.thdDb = -55.0f;
  CHECK(!checkCodec(codec, detail, sizeof(detail)));
  CHECK(std::strstr(detail, "THD") != nullptr);
  codec = CodecInfo{980.0f, 0.0f, -70.0f, -12.0f};
  CHECK(!checkCodec(codec, detail, sizeof(detail)));

  SdInfo sd{1024u * 1024u, 1234u, true, 1200.0f};
  CHECK(checkSd(sd, detail, sizeof(detail)));
  sd.throughputKbps = 650.0f;
  CHECK(!checkSd(sd, detail, sizeof(detail)));
  sd.throughputKbps = 1200.0f;
  sd.crcOk = false;
  CHECK(!checkSd(sd, detail, sizeof(detail)));
  INFO("validators: codec 1 kHz/-12 dBFS/gain +-1 dB/THD<-60 dB; SD 1 MiB CRC+700 KB/s");
}

TEST(FactoryValidatorsDisplayLedBattery) {
  char detail[96];
  CHECK(checkDisplay(DisplayInfo{4, true}, detail, sizeof(detail)));
  CHECK(!checkDisplay(DisplayInfo{4, false}, detail, sizeof(detail)));
  CHECK(!checkDisplay(DisplayInfo{3, true}, detail, sizeof(detail)));

  CHECK(checkWs2812(Ws2812Info{118.0f, 120.0f, 16, 16}, detail, sizeof(detail)));
  CHECK(!checkWs2812(Ws2812Info{150.0f, 120.0f, 16, 16}, detail, sizeof(detail)));
  CHECK(!checkWs2812(Ws2812Info{118.0f, 120.0f, 15, 16}, detail, sizeof(detail)));

  CHECK(checkMax17048(Max17048Info{4.18f, 4.19f}, detail, sizeof(detail)));
  CHECK(!checkMax17048(Max17048Info{4.15f, 4.19f}, detail, sizeof(detail)));
  INFO("validators: display patterns, WS2812 current +-20%, MAX17048 <=30 mV");
}

TEST(FactoryValidatorsUsbControls) {
  char detail[96];
  CHECK(checkUsb(UsbInfo{0x0F, true}, detail, sizeof(detail)));
  CHECK(!checkUsb(UsbInfo{0x07, true}, detail, sizeof(detail)));  // missing UAC
  CHECK(std::strstr(detail, "missing USB") != nullptr);
  CHECK(!checkUsb(UsbInfo{0x0F, false}, detail, sizeof(detail)));

  ControlsInfo controls{42, 42, 16, 16, 2, 2};
  CHECK(checkControls(controls, detail, sizeof(detail)));
  controls.keysOk = 41;
  CHECK(!checkControls(controls, detail, sizeof(detail)));
  controls = ControlsInfo{42, 42, 15, 16, 2, 2};
  CHECK(!checkControls(controls, detail, sizeof(detail)));
  INFO("validators: USB composite class mask (CDC+MIDI+HID+UAC), 42 keys/16 enc/2 faders");
}

TEST(FactoryValidatorsCvGateMidi) {
  char detail[96];
  CvGateInfo cv{};
  const float errors[4] = {5.0f, -10.0f, 20.0f, -20.0f};
  std::memcpy(cv.errorsMv, errors, sizeof(errors));
  cv.gateLoopback = true;
  CHECK(checkCvGate(cv, detail, sizeof(detail)));
  cv.errorsMv[3] = -25.0f;
  CHECK(!checkCvGate(cv, detail, sizeof(detail)));
  cv.errorsMv[3] = -5.0f;
  cv.gateLoopback = false;
  CHECK(!checkCvGate(cv, detail, sizeof(detail)));

  CHECK(checkMidi(MidiInfo{100, 100, 0}, detail, sizeof(detail)));
  CHECK(!checkMidi(MidiInfo{100, 100, 1}, detail, sizeof(detail)));
  CHECK(!checkMidi(MidiInfo{50, 50, 0}, detail, sizeof(detail)));
  INFO("validators: 4x CV OUT->IN <=20 mV + GATE loopback; 100 MIDI packets, 0 errors");
}

TEST(FactoryFailInjection) {
  MockHardware hardware;
  hardware.failTest(TestId::CodecLoopback, true);
  const Report report = runSelfTest(hardware);
  CHECK(!report.overallPass);
  CHECK(report.failCount == 1);
  CHECK(report.passCount == 13);
  CHECK(report.tests[static_cast<int>(TestId::CodecLoopback)].status == TestStatus::Fail);
  INFO("fail injection: single failed test -> overall FAIL, 13 pass");
}

TEST(FactoryTimeoutDetection) {
  MockHardware hardware;
  hardware.setDurationMs(TestId::SdScratch, timeoutMs(TestId::SdScratch) + 1);
  const Report report = runSelfTest(hardware);
  CHECK(!report.overallPass);
  CHECK(report.timeoutCount == 1);
  CHECK(report.tests[static_cast<int>(TestId::SdScratch)].status == TestStatus::Timeout);
  CHECK(std::strstr(report.tests[static_cast<int>(TestId::SdScratch)].detail, "timeout") !=
        nullptr);
  INFO("timeout: test exceeding timeout is marked TIMEOUT and fails the report");
}

TEST(FactoryStopOnFail) {
  MockHardware hardware;
  hardware.failTest(TestId::Mcp23017Walking, true);
  const Report report = runSelfTest(hardware, true);
  CHECK(!report.overallPass);
  CHECK(report.count == 3);  // power, i2c, mcp23017
  CHECK(report.tests[2].status == TestStatus::Fail);
  INFO("stop-on-fail: runner stops after the failed test (production option)");
}

TEST(FactoryEveryTestCanFail) {
  for (int i = 0; i < kTestCount; ++i) {
    MockHardware hardware;
    hardware.failTest(static_cast<TestId>(i), true);
    const Report report = runSelfTest(hardware);
    CHECK(report.count == 14);  // without stopOnFail all tests still run
    CHECK(!report.overallPass);
    CHECK(report.tests[i].status == TestStatus::Fail);
  }
  INFO("all 14 tests can independently fail and are reported");
}

TEST(FactoryJsonReport) {
  MockHardware hardware;
  const Report report = runSelfTest(hardware);
  char json[4096];
  CHECK(reportToJson(report, json, sizeof(json)));
  CHECK(std::strstr(json, "\"schema\":\"bukifon-factory-selftest-v1\"") != nullptr);
  CHECK(std::strstr(json, "\"overall_pass\":true") != nullptr);
  CHECK(std::strstr(json, "\"count\":14") != nullptr);
  CHECK(std::strstr(json, "\"power_on\"") != nullptr);
  CHECK(std::strstr(json, "\"midi_loopback\"") != nullptr);
  CHECK(std::strstr(json, "\"status\":\"PASS\"") != nullptr);
  char tiny[8];
  CHECK(!reportToJson(report, tiny, sizeof(tiny)));
  INFO("JSON report: schema, 14 tests, statuses, details; small buffer rejected");
}

TEST(FactoryJsonFailPath) {
  MockHardware hardware;
  hardware.failTest(TestId::UsbComposite, true);
  const Report report = runSelfTest(hardware);
  char json[4096];
  CHECK(reportToJson(report, json, sizeof(json)));
  CHECK(std::strstr(json, "\"overall_pass\":false") != nullptr);
  CHECK(std::strstr(json, "\"name\":\"usb_composite\",\"status\":\"FAIL\"") != nullptr);
  INFO("JSON fail path: overall false + failed test status serialized");
}

TEST(FactoryCliJson) {
  MockHardware hardware;
  std::FILE* tmp = std::tmpfile();
  CHECK(tmp != nullptr);
  char arg0[] = "factory";
  char arg1[] = "--json";
  char* argv[] = {arg0, arg1, nullptr};
  const int rc = factoryCliMain(2, argv, hardware, tmp);
  CHECK(rc == 0);
  std::fflush(tmp);
  std::fseek(tmp, 0, SEEK_END);
  const long size = std::ftell(tmp);
  std::fseek(tmp, 0, SEEK_SET);
  std::string out(static_cast<size_t>(size), '\0');
  std::fread(&out[0], 1, static_cast<size_t>(size), tmp);
  std::fclose(tmp);
  CHECK(!out.empty());
  CHECK(out[0] == '{');
  CHECK(out.find("\"overall_pass\":true") != std::string::npos);
  INFO("CLI: factory --json prints only the JSON report, exit 0 on PASS");
}

TEST(FactoryCliOutFileAndHelp) {
  MockHardware hardware;
  std::FILE* tmp = std::tmpfile();
  const char* path = "../tests/out/factory_cli_report.json";
  char arg0[] = "factory";
  char arg1[] = "--out";
  char arg2[] = "../tests/out/factory_cli_report.json";
  char* argv[] = {arg0, arg1, arg2, nullptr};
  const int rc = factoryCliMain(3, argv, hardware, tmp);
  CHECK(rc == 0);
  std::FILE* file = std::fopen(path, "rb");
  CHECK(file != nullptr);
  if (file) std::fclose(file);
  std::remove(path);

  char h0[] = "factory";
  char h1[] = "--help";
  char* helpArgv[] = {h0, h1, nullptr};
  std::FILE* helpTmp = std::tmpfile();
  CHECK(factoryCliMain(2, helpArgv, hardware, helpTmp) == 0);
  std::fclose(helpTmp);
  std::fclose(tmp);

  char b0[] = "factory";
  char b1[] = "--bogus";
  char* badArgv[] = {b0, b1, nullptr};
  std::FILE* badTmp = std::tmpfile();
  CHECK(factoryCliMain(2, badArgv, hardware, badTmp) == 2);
  std::fclose(badTmp);
  INFO("CLI: --out writes JSON file; --help=0; unknown args=2");
}

TEST(FactoryCliFailExitCode) {
  MockHardware hardware;
  hardware.failTest(TestId::SdScratch, true);
  std::FILE* tmp = std::tmpfile();
  char arg0[] = "factory";
  char arg1[] = "--json";
  char* argv[] = {arg0, arg1, nullptr};
  CHECK(factoryCliMain(2, argv, hardware, tmp) == 1);
  std::fclose(tmp);
  INFO("CLI: failed report exits with code 1 (production station gate)");
}
