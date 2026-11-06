// SPDX-License-Identifier: GPL-3.0-or-later
// Factory self-test tests: 21 docs/42/DFM tests, validators, timeouts, JSON report,
// CLI and mock hardware.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "factory/mock_hardware.hpp"
#include "factory/selftest.hpp"
#include "io/ext_sequencer.hpp"
#include "factory/p4_hardware.hpp"
#include "test_framework.hpp"

using namespace bukifon::factory;
using bukifon::ExtSeqSink;
using bukifon::ExtSequencer;
using bukifon::MidiOutRouter;
using bukifon::RouterExtSink;


TEST(FactoryTestList) {
  CHECK(kTestCount == 21);
  static const char* expected[21] = {
      "power_on",         "i2c_scan",       "mcp23017_walking", "mcp3208_vector",
      "dac_adc_loopback", "codec_loopback", "sd_scratch",       "display_patterns",
      "ws2812_current",   "max17048",       "usb_composite",    "controls",
      "cv_gate_loopback", "midi_loopback",  "eeprom",           "mcp4728",
      "c6_link",          "cv_inputs",      "uart_boot",        "serial_qr",
      "mic"};
  uint32_t totalNominal = 0;
  for (int i = 0; i < kTestCount; ++i) {
    CHECK(std::strcmp(testName(static_cast<TestId>(i)), expected[i]) == 0);
    CHECK(nominalTimeMs(static_cast<TestId>(i)) > 0);
    CHECK(timeoutMs(static_cast<TestId>(i)) > nominalTimeMs(static_cast<TestId>(i)));
    totalNominal += nominalTimeMs(static_cast<TestId>(i));
  }
  CHECK(totalNominal > 40000 && totalNominal < 55000);  // ~46 s automation
  INFO("factory: 21 tests, nominal automation %.1f s (EOL 2-2.5 min with operator)",
       static_cast<double>(totalNominal) / 1000.0);
}

TEST(FactoryAllPassMock) {
  MockHardware hardware;
  const Report report = runSelfTest(hardware);
  CHECK(report.count == 21);
  CHECK(report.passCount == 21);
  CHECK(report.failCount == 0);
  CHECK(report.overallPass);
  CHECK(report.totalDurationMs > 0);
  CHECK(hardware.clockMs() >= report.totalDurationMs);
  INFO("factory all-pass mock: 21/21, total %u ms", report.totalDurationMs);
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
  CHECK(report.passCount == 20);
  CHECK(report.tests[static_cast<int>(TestId::CodecLoopback)].status == TestStatus::Fail);
  INFO("fail injection: single failed test -> overall FAIL, 20 pass");
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
    CHECK(report.count == 21);  // without stopOnFail all tests still run
    CHECK(!report.overallPass);
    CHECK(report.tests[i].status == TestStatus::Fail);
  }
  INFO("all 21 tests can independently fail and are reported");
}

TEST(FactoryJsonReport) {
  MockHardware hardware;
  const Report report = runSelfTest(hardware);
  char json[16384];
  CHECK(reportToJson(report, json, sizeof(json)));
  CHECK(std::strstr(json, "\"schema\":\"bukifon-factory-selftest-v1\"") != nullptr);
  CHECK(std::strstr(json, "\"overall_pass\":true") != nullptr);
  CHECK(std::strstr(json, "\"count\":21") != nullptr);
  CHECK(std::strstr(json, "\"power_on\"") != nullptr);
  CHECK(std::strstr(json, "\"midi_loopback\"") != nullptr);
  CHECK(std::strstr(json, "\"status\":\"PASS\"") != nullptr);
  char tiny[8];
  CHECK(!reportToJson(report, tiny, sizeof(tiny)));
  INFO("JSON report: schema, 21 tests, statuses, details; small buffer rejected");
}

TEST(FactoryJsonFailPath) {
  MockHardware hardware;
  hardware.failTest(TestId::UsbComposite, true);
  const Report report = runSelfTest(hardware);
  char json[16384];
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

// --------------------------------------------------------------------------
// Round 19: factory self-test 21 items (DFM CORE-2 §2), SKIP, mic, MIDI/EXT.
// --------------------------------------------------------------------------
#include "io/mic.hpp"

TEST(FactoryReportTwentyOne) {
  MockHardware hardware;
  const Report report = runSelfTest(hardware);
  CHECK(report.count == 21);
  CHECK(report.passCount == 21);
  CHECK(report.failCount == 0);
  CHECK(report.skipCount == 0);
  CHECK(report.overallPass);
  CHECK(report.totalDurationMs > 0);
  INFO("factory report: 21/21 PASS, %u ms", report.totalDurationMs);
}

TEST(FactoryNewItemsInList) {
  static const char* newNames[7] = {"eeprom", "mcp4728", "c6_link",
                                    "cv_inputs", "uart_boot", "serial_qr", "mic"};
  for (int i = 0; i < 7; ++i) {
    const TestId id = static_cast<TestId>(14 + i);
    CHECK(std::strcmp(testName(id), newNames[i]) == 0);
    CHECK(nominalTimeMs(id) > 0);
    CHECK(timeoutMs(id) > nominalTimeMs(id));
  }
  CHECK(std::strcmp(testName(TestId::Mic), "mic") == 0);
  INFO("21-item list includes EEPROM/MCP4728/C6/CV-in/UART-boot/QR/mic");
}

TEST(FactoryNewValidatorsPass) {
  char detail[96];
  CHECK(checkEeprom(EepromInfo{true, 32, 32, "BKF-2026A1", true}, detail, sizeof(detail)));
  Mcp4728Info dac{};
  dac.addressesAck[0] = true;
  dac.addressesAck[1] = true;
  dac.channelsOk = 8;
  dac.channelsTotal = 8;
  dac.maxLsbError = 1;
  CHECK(checkMcp4728(dac, detail, sizeof(detail)));
  CHECK(checkC6Link(C6LinkInfo{true, 25000u, 0x0301u, true}, detail, sizeof(detail)));
  CvInputInfo cv{};
  cv.errorsPercent[0] = 0.2f;
  cv.errorsPercent[1] = -0.4f;
  cv.errorsPercent[2] = 0.3f;
  cv.errorsPercent[3] = -0.5f;
  cv.tvsOk = true;
  CHECK(checkCvInputs(cv, detail, sizeof(detail)));
  CHECK(checkUartBoot(UartBootInfo{true, true, 115200u}, detail, sizeof(detail)));
  CHECK(checkSerialQr(SerialQrInfo{true, true, true, true}, detail, sizeof(detail)));
  CHECK(checkMic(MicInfo{true, -18.0f, true, true, true, true, true, 70.0f, 3.5f},
                 detail, sizeof(detail)));
  INFO("new validators: EEPROM/MCP4728/C6/CV in/UART/QR/MIC accept nominal values");
}

TEST(FactoryEepromFails) {
  char detail[96];
  CHECK(!checkEeprom(EepromInfo{false, 32, 32, "SN", true}, detail, sizeof(detail)));
  CHECK(!checkEeprom(EepromInfo{true, 31, 32, "SN", true}, detail, sizeof(detail)));
  CHECK(!checkEeprom(EepromInfo{true, 32, 32, "", true}, detail, sizeof(detail)));
  INFO("EEPROM validator rejects missing magic/short read/no serial");
}

TEST(FactoryMcp4728Fails) {
  char detail[96];
  Mcp4728Info dac{};
  dac.addressesAck[0] = true;
  dac.channelsOk = 8;
  dac.channelsTotal = 8;
  CHECK(!checkMcp4728(dac, detail, sizeof(detail)));  // second chip missing
  dac.addressesAck[1] = true;
  dac.channelsOk = 7;
  CHECK(!checkMcp4728(dac, detail, sizeof(detail)));  // channel missing
  dac.channelsOk = 8;
  dac.maxLsbError = 2;
  CHECK(!checkMcp4728(dac, detail, sizeof(detail)));  // readback error >1 LSB
  INFO("MCP4728 validator rejects missing chip/channel/readback error");
}

TEST(FactoryC6LinkFails) {
  char detail[96];
  CHECK(!checkC6Link(C6LinkInfo{false, 25000u, 1u, true}, detail, sizeof(detail)));
  CHECK(!checkC6Link(C6LinkInfo{true, 150000u, 1u, true}, detail, sizeof(detail)));
  CHECK(!checkC6Link(C6LinkInfo{true, 25000u, 0u, true}, detail, sizeof(detail)));
  CHECK(!checkC6Link(C6LinkInfo{true, 25000u, 1u, false}, detail, sizeof(detail)));
  INFO("C6 link validator rejects no response, >100 ms, bad version, no Wi-Fi scan");
}

TEST(FactoryCvInputsFails) {
  char detail[96];
  CvInputInfo cv{};
  cv.tvsOk = true;
  cv.errorsPercent[2] = 1.5f;
  CHECK(!checkCvInputs(cv, detail, sizeof(detail)));
  cv.errorsPercent[2] = 0.2f;
  cv.tvsOk = false;
  CHECK(!checkCvInputs(cv, detail, sizeof(detail)));
  INFO("CV input validator rejects >1% error and TVS/protection failure");
}

TEST(FactoryUartBootFails) {
  char detail[96];
  CHECK(!checkUartBoot(UartBootInfo{false, true, 115200u}, detail, sizeof(detail)));
  CHECK(!checkUartBoot(UartBootInfo{true, false, 115200u}, detail, sizeof(detail)));
  CHECK(!checkUartBoot(UartBootInfo{true, true, 57600u}, detail, sizeof(detail)));
  INFO("UART/BOOT validator rejects missing log/strap/wrong baud");
}

TEST(FactorySerialQrFails) {
  char detail[96];
  CHECK(!checkSerialQr(SerialQrInfo{false, true, true, true}, detail, sizeof(detail)));
  CHECK(!checkSerialQr(SerialQrInfo{true, false, true, true}, detail, sizeof(detail)));
  CHECK(!checkSerialQr(SerialQrInfo{true, true, false, true}, detail, sizeof(detail)));
  CHECK(!checkSerialQr(SerialQrInfo{true, true, true, false}, detail, sizeof(detail)));
  INFO("serial/QR validator rejects each SN/rev/date/QR mismatch");
}

TEST(FactoryMicValidatorPassAndMute) {
  char detail[96];
  CHECK(checkMic(MicInfo{true, -18.0f, true, true, true, true, true, 70.0f, 3.5f},
                 detail, sizeof(detail)));
  CHECK(std::strstr(detail, "mute+LED") != nullptr);
  CHECK(!checkMic(MicInfo{true, -18.0f, true, true, false, true, true, 70.0f, 3.5f},
                  detail, sizeof(detail)));
  CHECK(std::strstr(detail, "mute") != nullptr);
  INFO("MIC validator: SW3 mute blocks recording (fails without it)");
}

TEST(FactoryMicLedAndSnr) {
  char detail[96];
  CHECK(!checkMic(MicInfo{true, -18.0f, true, true, true, false, true, 70.0f, 3.5f},
                  detail, sizeof(detail)));  // LED off
  CHECK(!checkMic(MicInfo{true, -18.0f, true, true, true, true, true, 60.0f, 3.5f},
                  detail, sizeof(detail)));  // SNR <65
  CHECK(!checkMic(MicInfo{true, -18.0f, true, true, true, true, true, 70.0f, 8.0f},
                  detail, sizeof(detail)));  // latency >5 ms
  INFO("MIC validator rejects LED off, SNR <65 dB, latency >5 ms");
}

TEST(FactorySkipWithoutHardwareP4) {
  P4FactoryHardware hardware;
  const Report report = runSelfTest(hardware);
  CHECK(report.count == 21);
  CHECK(report.skipCount == 21);
  CHECK(report.passCount == 0);
  CHECK(report.failCount == 0);
  CHECK(!report.overallPass);
  for (int i = 0; i < report.count; ++i) CHECK(report.tests[i].status == TestStatus::Skip);
  INFO("P4 without toolchain: 21 SKIP (honest, no fabricated PASS/FAIL)");
}

TEST(FactorySkipStatusName) {
  CHECK(std::strcmp(statusName(TestStatus::Skip), "SKIP") == 0);
  CHECK(std::strcmp(statusName(TestStatus::Pass), "PASS") == 0);
  CHECK(std::strcmp(statusName(TestStatus::Fail), "FAIL") == 0);
  INFO("factory status names include SKIP/PASS/FAIL/TIMEOUT");
}

TEST(FactoryControls42And16) {
  char detail[96];
  CHECK(checkControls(ControlsInfo{42, 42, 16, 16, 2, 2}, detail, sizeof(detail)));
  CHECK(!checkControls(ControlsInfo{41, 42, 16, 16, 2, 2}, detail, sizeof(detail)));
  CHECK(!checkControls(ControlsInfo{42, 42, 15, 16, 2, 2}, detail, sizeof(detail)));
  INFO("keyboard matrix 42 keys + 16 encoders validated");
}

TEST(FactoryDisplayGradientCheck) {
  char detail[96];
  CHECK(checkDisplay(DisplayInfo{4, true}, detail, sizeof(detail)));
  CHECK(!checkDisplay(DisplayInfo{3, true}, detail, sizeof(detail)));
  CHECK(!checkDisplay(DisplayInfo{4, false}, detail, sizeof(detail)));
  INFO("display gradient/checker test: 4 patterns + no bands required");
}

TEST(FactoryMidiRouterNoDuplicates) {
  MidiOutRouter router;
  RouterExtSink sink(&router);
  sink.onExtProgramChange(0, 1, 0);
  sink.onExtStart();
  sink.onExtNoteOn(0, 1, 60, 100);
  sink.onExtControlChange(0, 1, 74, 64);
  sink.onExtClock();
  sink.onExtStop();
  CHECK(router.dinCount() == 6);
  CHECK(router.usbCount() == 6);
  CHECK(!router.hasDuplicates());
  for (int i = 0; i < router.dinCount(); ++i) {
    CHECK(router.dinAt(i).status == router.usbAt(i).status);
    CHECK(router.dinAt(i).data1 == router.usbAt(i).data1);
  }
  INFO("factory MIDI/EXT loopback: DIN+USB no duplicates for note/CC/PC/clock/transport");
}

TEST(FactoryMidiClock24Ppqn) {
  ExtSequencer seq;
  struct ClockSink : ExtSeqSink {
    int clocks = 0;
    void onExtClock() override { ++clocks; }
  } sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  seq.setBpm(120.0f);
  seq.start();
  seq.process(24000);
  CHECK(sink.clocks == 24);
  seq.stop();
  INFO("factory MIDI clock: 24 ppqn (24 clocks per quarter at 120 BPM)");
}

TEST(FactoryJsonTwentyOne) {
  MockHardware hardware;
  const Report report = runSelfTest(hardware);
  char json[16384];
  CHECK(reportToJson(report, json, sizeof(json)));
  CHECK(std::strstr(json, "\"count\":21") != nullptr);
  CHECK(std::strstr(json, "\"pass\":21") != nullptr);
  CHECK(std::strstr(json, "\"eeprom\"") != nullptr);
  CHECK(std::strstr(json, "\"mcp4728\"") != nullptr);
  CHECK(std::strstr(json, "\"c6_link\"") != nullptr);
  CHECK(std::strstr(json, "\"mic\"") != nullptr);
  CHECK(std::strstr(json, "\"overall_pass\":true") != nullptr);
  INFO("JSON factory report serializes 21/21 with new test names");
}

TEST(FactoryMicCaptureSelfTestModel) {
  bukifon::MicCapture mic;
  mic.init(48000.0f);
  bukifon::MicConfig config = mic.config();
  config.gainDb = 0.0f;
  config.threshold = 0.02f;
  mic.setConfig(config);
  std::vector<float> oneSecond(48000, 0.2f);
  mic.push(oneSecond.data(), static_cast<int>(oneSecond.size()));
  CHECK(mic.level() > config.threshold);
  CHECK(mic.vadActive());
  CHECK(!mic.beginRecording("FACTORY", 0));  // mute by default
  mic.privacy().setMuteSwitch(false);
  CHECK(mic.beginRecording("FACTORY", 0));
  mic.push(oneSecond.data(), 1000);
  CHECK(mic.endRecording());
  CHECK(mic.take().valid);
  CHECK(mic.privacy().led);
  INFO("factory mic model: 1 s record, VAD RMS>threshold, SW3 mute blocks, LED on");
}

TEST(FactoryNewItemsCanFailInRunner) {
  for (int id = 14; id < 21; ++id) {
    MockHardware hardware;
    hardware.failTest(static_cast<TestId>(id), true);
    const Report report = runSelfTest(hardware);
    CHECK(report.count == 21);
    CHECK(report.tests[id].status == TestStatus::Fail);
    CHECK(report.passCount == 20);
    CHECK(!report.overallPass);
  }
  INFO("each of the 7 new 21-item tests can fail independently");
}
