// SPDX-License-Identifier: GPL-3.0-or-later
#include "factory/selftest.hpp"

#include <cmath>
#include <cstdarg>
#include <cstring>

namespace bukifon {
namespace factory {
namespace {

const char* kNames[kTestCount] = {
    "power_on",        "i2c_scan",      "mcp23017_walking", "mcp3208_vector",
    "dac_adc_loopback", "codec_loopback", "sd_scratch",     "display_patterns",
    "ws2812_current",  "max17048",      "usb_composite",   "controls",
    "cv_gate_loopback", "midi_loopback"};

// docs/42 §2 nominal times (ms).
const uint32_t kNominalMs[kTestCount] = {1000, 300, 1500, 800, 1500, 2000, 2000,
                                         1000, 1000, 400, 2500, 20000, 3000, 1000};

const uint8_t kExpectedI2c[] = {0x20, 0x21, 0x22, 0x23, 0x36, 0x57, 0x60, 0x61};

template <typename T>
bool near(T value, T target, T tolerance) {
  return std::fabs(static_cast<double>(value) - static_cast<double>(target)) <=
         static_cast<double>(tolerance);
}

bool hasAddress(const I2cScanInfo& info, uint8_t address) {
  for (uint8_t i = 0; i < info.count && i < 16; ++i) {
    if (info.addresses[i] == address) return true;
  }
  return false;
}

void setDetail(char* detail, size_t len, const char* text) {
  if (detail && len) std::snprintf(detail, len, "%s", text);
}

}  // namespace

const char* testName(TestId id) {
  const int index = static_cast<int>(id);
  return (index >= 0 && index < kTestCount) ? kNames[index] : "";
}

uint32_t nominalTimeMs(TestId id) {
  const int index = static_cast<int>(id);
  return (index >= 0 && index < kTestCount) ? kNominalMs[index] : 0;
}

uint32_t timeoutMs(TestId id) {
  const uint32_t nominal = nominalTimeMs(id);
  return nominal * 3u + 500u;
}

const char* statusName(TestStatus status) {
  switch (status) {
    case TestStatus::Pass:
      return "PASS";
    case TestStatus::Fail:
      return "FAIL";
    case TestStatus::Timeout:
      return "TIMEOUT";
    case TestStatus::Skip:
      return "SKIP";
    default:
      return "PENDING";
  }
}

// --- validators (criteria: docs/42 §2) -------------------------------------
bool checkPower(const PowerInfo& info, char* detail, size_t len) {
  if (!info.powerGood) {
    setDetail(detail, len, "PWR_GOOD low");
    return false;
  }
  if (info.brownoutCount != 0) {
    std::snprintf(detail, len, "brownout count=%llu",
                  static_cast<unsigned long long>(info.brownoutCount));
    return false;
  }
  if (info.resetReason != 1) {  // ESP_RST_POWERON
    std::snprintf(detail, len, "reset reason=%llu (expected 1)",
                  static_cast<unsigned long long>(info.resetReason));
    return false;
  }
  setDetail(detail, len, "reset reason POWERON, PWR_GOOD high, 0 brownouts");
  return true;
}

bool checkI2c(const I2cScanInfo& info, char* detail, size_t len) {
  if (info.count != sizeof(kExpectedI2c)) {
    std::snprintf(detail, len, "found %u devices, expected %u", info.count,
                  static_cast<unsigned>(sizeof(kExpectedI2c)));
    return false;
  }
  for (uint8_t expected : kExpectedI2c) {
    if (!hasAddress(info, expected)) {
      std::snprintf(detail, len, "missing I2C address 0x%02X", expected);
      return false;
    }
  }
  setDetail(detail, len, "addresses 0x20-0x23,0x36,0x57,0x60,0x61 present");
  return true;
}

bool checkMcp23017(const Mcp23017Info& info, char* detail, size_t len) {
  for (int i = 0; i < 4; ++i) {
    if (!info.addressesAck[i]) {
      std::snprintf(detail, len, "MCP23017 0x%02X no ACK", 0x20 + i);
      return false;
    }
  }
  if (!info.irqToggles) {
    setDetail(detail, len, "PANEL_IRQ did not toggle");
    return false;
  }
  setDetail(detail, len, "4 expanders walking-bit OK, IRQ toggles");
  return true;
}

bool checkMcp3208(const Mcp3208Info& info, char* detail, size_t len) {
  static const float kExpected[8] = {0.25f, 1.25f, 2.50f, 0.25f,
                                     1.25f, 2.50f, 0.25f, 1.25f};
  for (int ch = 0; ch < 8; ++ch) {
    if (!near(info.volts[ch], kExpected[ch], 0.003f)) {  // ±2 LSB @3.3 V
      std::snprintf(detail, len, "CH%d=%.3f V, expected %.2f V (+-2 LSB)", ch,
                    static_cast<double>(info.volts[ch]), static_cast<double>(kExpected[ch]));
      return false;
    }
  }
  setDetail(detail, len, "8 channels match 0.25/1.25/2.50 V vector (+-2 LSB)");
  return true;
}

bool checkDacAdc(const DacAdcInfo& info, char* detail, size_t len) {
  for (int i = 0; i < 4; ++i) {
    if (std::fabs(info.errorsMv[i]) > 20.0f) {
      std::snprintf(detail, len, "CV%d error %.1f mV > 20 mV", i + 1,
                    static_cast<double>(info.errorsMv[i]));
      return false;
    }
  }
  setDetail(detail, len, "4 CV channels <=20 mV after calibration");
  return true;
}

bool checkCodec(const CodecInfo& info, char* detail, size_t len) {
  if (!near(info.toneHz, 1000.0f, 5.0f)) {
    std::snprintf(detail, len, "tone %.1f Hz, expected 1 kHz", static_cast<double>(info.toneHz));
    return false;
  }
  if (!near(info.levelDbfs, -12.0f, 1.0f)) {
    std::snprintf(detail, len, "level %.1f dBFS, expected -12 dBFS",
                  static_cast<double>(info.levelDbfs));
    return false;
  }
  if (std::fabs(info.gainDb) > 1.0f) {
    std::snprintf(detail, len, "loopback gain %.2f dB (limit +-1 dB)",
                  static_cast<double>(info.gainDb));
    return false;
  }
  if (info.thdDb > -60.0f) {
    std::snprintf(detail, len, "THD+N %.1f dB (must be < -60 dB)",
                  static_cast<double>(info.thdDb));
    return false;
  }
  setDetail(detail, len, "1 kHz/-12 dBFS, gain +-1 dB, THD+N < -60 dB");
  return true;
}

bool checkSd(const SdInfo& info, char* detail, size_t len) {
  if (info.bytes < 1024u * 1024u) {
    std::snprintf(detail, len, "transferred %lu bytes < 1 MiB",
                  static_cast<unsigned long>(info.bytes));
    return false;
  }
  if (!info.crcOk) {
    setDetail(detail, len, "CRC32 mismatch on scratch file");
    return false;
  }
  if (info.throughputKbps < 700.0f) {
    std::snprintf(detail, len, "throughput %.0f KB/s < 700 KB/s",
                  static_cast<double>(info.throughputKbps));
    return false;
  }
  std::snprintf(detail, len, "1 MiB write/read CRC32 OK, %.0f KB/s",
                static_cast<double>(info.throughputKbps));
  return true;
}

bool checkDisplay(const DisplayInfo& info, char* detail, size_t len) {
  if (info.patternsShown < 4) {
    std::snprintf(detail, len, "%u/4 patterns displayed",
                  static_cast<unsigned>(info.patternsShown));
    return false;
  }
  if (!info.operatorSeenNoBands) {
    setDetail(detail, len, "operator did not confirm RGB/white/black/checker");
    return false;
  }
  setDetail(detail, len, "4 patterns, no bands (operator confirmed)");
  return true;
}

bool checkWs2812(const Ws2812Info& info, char* detail, size_t len) {
  if (info.ledsTotal == 0 || info.ledsOk != info.ledsTotal) {
    std::snprintf(detail, len, "%u/%u LEDs OK", info.ledsOk, info.ledsTotal);
    return false;
  }
  if (info.expectedMa <= 0.0f) {
    setDetail(detail, len, "no expected current");
    return false;
  }
  const float tolerance = info.expectedMa * 0.20f;
  if (!near(info.currentMa, info.expectedMa, tolerance)) {
    std::snprintf(detail, len, "current %.0f mA, expected %.0f+-20%%",
                  static_cast<double>(info.currentMa), static_cast<double>(info.expectedMa));
    return false;
  }
  std::snprintf(detail, len, "%u LEDs, current %.0f mA (+-20%%)", info.ledsTotal,
                static_cast<double>(info.currentMa));
  return true;
}

bool checkMax17048(const Max17048Info& info, char* detail, size_t len) {
  if (!near(info.cellVolts, info.dmmVolts, 0.030f)) {
    std::snprintf(detail, len, "VCELL %.3f V vs DMM %.3f V (>30 mV)",
                  static_cast<double>(info.cellVolts), static_cast<double>(info.dmmVolts));
    return false;
  }
  setDetail(detail, len, "MAX17048 VCELL matches DMM within 30 mV");
  return true;
}

bool checkUsb(const UsbInfo& info, char* detail, size_t len) {
  if (!info.enumerated) {
    setDetail(detail, len, "device not enumerated");
    return false;
  }
  const uint32_t missing = kUsbRequiredClasses & ~info.classMask;
  if (missing != 0) {
    std::snprintf(detail, len, "missing USB classes mask=0x%X", info.classMask);
    return false;
  }
  setDetail(detail, len, "CDC+MIDI+HID+UAC enumerated");
  return true;
}

bool checkControls(const ControlsInfo& info, char* detail, size_t len) {
  if (info.keysOk != info.keysTotal || info.keysTotal != 42) {
    std::snprintf(detail, len, "keys %u/%u (expected 42)", info.keysOk, info.keysTotal);
    return false;
  }
  if (info.encodersOk != info.encodersTotal || info.encodersTotal != 16) {
    std::snprintf(detail, len, "encoders %u/%u (expected 16)", info.encodersOk,
                  info.encodersTotal);
    return false;
  }
  if (info.fadersOk != info.fadersTotal || info.fadersTotal != 2) {
    std::snprintf(detail, len, "faders %u/%u (expected 2)", info.fadersOk, info.fadersTotal);
    return false;
  }
  setDetail(detail, len, "42 keys, 16 encoders (A/B/SW), 2 faders all read");
  return true;
}

bool checkCvGate(const CvGateInfo& info, char* detail, size_t len) {
  for (int i = 0; i < 4; ++i) {
    if (std::fabs(info.errorsMv[i]) > 20.0f) {
      std::snprintf(detail, len, "CV loopback %d error %.1f mV > 20 mV", i + 1,
                    static_cast<double>(info.errorsMv[i]));
      return false;
    }
  }
  if (!info.gateLoopback) {
    setDetail(detail, len, "GATE loopback not detected");
    return false;
  }
  setDetail(detail, len, "4x CV OUT->IN <=20 mV, GATE OUT->IN OK");
  return true;
}

bool checkMidi(const MidiInfo& info, char* detail, size_t len) {
  if (info.sent < 100 || info.received < 100) {
    std::snprintf(detail, len, "MIDI packets sent=%u received=%u", info.sent, info.received);
    return false;
  }
  if (info.errors != 0) {
    std::snprintf(detail, len, "%u MIDI loopback errors", info.errors);
    return false;
  }
  setDetail(detail, len, "100 packets sent/received, 0 errors");
  return true;
}

// --- runner -----------------------------------------------------------------
namespace {

void applyTestResult(Report* report, TestId id, uint32_t duration, bool hardwareOk,
                     bool valid, const char* detail) {
  TestResult& result = report->tests[report->count++];
  result.id = id;
  result.nominalMs = nominalTimeMs(id);
  result.durationMs = duration;
  result.status = TestStatus::Fail;
  if (duration > timeoutMs(id)) {
    result.status = TestStatus::Timeout;
    std::snprintf(result.detail, sizeof(result.detail), "timeout: %u ms > %u ms", duration,
                  timeoutMs(id));
  } else if (!hardwareOk) {
    result.status = TestStatus::Fail;
    setDetail(result.detail, sizeof(result.detail), "hardware read failed");
  } else if (!valid) {
    result.status = TestStatus::Fail;
    if (detail && detail[0]) setDetail(result.detail, sizeof(result.detail), detail);
  } else {
    result.status = TestStatus::Pass;
    if (detail) setDetail(result.detail, sizeof(result.detail), detail);
  }
}

}  // namespace

Report runSelfTest(Hardware& hardware, bool stopOnFail) {
  Report report;
  report.count = 0;
  const uint32_t runStart = hardware.nowMs();

  for (uint8_t i = 0; i < kTestCount; ++i) {
    const TestId id = static_cast<TestId>(i);
    const uint32_t start = hardware.nowMs();
    bool hardwareOk = false;
    bool valid = false;
    char detail[96] = {};
    switch (id) {
      case TestId::PowerOn: {
        PowerInfo info;
        hardwareOk = hardware.readPower(&info);
        valid = hardwareOk && checkPower(info, detail, sizeof(detail));
        break;
      }
      case TestId::I2cScan: {
        I2cScanInfo info;
        hardwareOk = hardware.scanI2c(&info);
        valid = hardwareOk && checkI2c(info, detail, sizeof(detail));
        break;
      }
      case TestId::Mcp23017Walking: {
        Mcp23017Info info;
        hardwareOk = hardware.testMcp23017(&info);
        valid = hardwareOk && checkMcp23017(info, detail, sizeof(detail));
        break;
      }
      case TestId::Mcp3208Vector: {
        Mcp3208Info info;
        hardwareOk = hardware.readMcp3208(&info);
        valid = hardwareOk && checkMcp3208(info, detail, sizeof(detail));
        break;
      }
      case TestId::DacAdcLoopback: {
        DacAdcInfo info;
        hardwareOk = hardware.dacAdcLoopback(&info);
        valid = hardwareOk && checkDacAdc(info, detail, sizeof(detail));
        break;
      }
      case TestId::CodecLoopback: {
        CodecInfo info;
        hardwareOk = hardware.codecLoopback(&info);
        valid = hardwareOk && checkCodec(info, detail, sizeof(detail));
        break;
      }
      case TestId::SdScratch: {
        SdInfo info;
        hardwareOk = hardware.sdScratch(&info);
        valid = hardwareOk && checkSd(info, detail, sizeof(detail));
        break;
      }
      case TestId::DisplayPatterns: {
        DisplayInfo info;
        hardwareOk = hardware.displayPatterns(&info);
        valid = hardwareOk && checkDisplay(info, detail, sizeof(detail));
        break;
      }
      case TestId::Ws2812Current: {
        Ws2812Info info;
        hardwareOk = hardware.ws2812Current(&info);
        valid = hardwareOk && checkWs2812(info, detail, sizeof(detail));
        break;
      }
      case TestId::Max17048: {
        Max17048Info info;
        hardwareOk = hardware.readMax17048(&info);
        valid = hardwareOk && checkMax17048(info, detail, sizeof(detail));
        break;
      }
      case TestId::UsbComposite: {
        UsbInfo info;
        hardwareOk = hardware.usbComposite(&info);
        valid = hardwareOk && checkUsb(info, detail, sizeof(detail));
        break;
      }
      case TestId::Controls: {
        ControlsInfo info;
        hardwareOk = hardware.controls(&info);
        valid = hardwareOk && checkControls(info, detail, sizeof(detail));
        break;
      }
      case TestId::CvGateLoopback: {
        CvGateInfo info;
        hardwareOk = hardware.cvGateLoopback(&info);
        valid = hardwareOk && checkCvGate(info, detail, sizeof(detail));
        break;
      }
      case TestId::MidiLoopback: {
        MidiInfo info;
        hardwareOk = hardware.midiLoopback(&info);
        valid = hardwareOk && checkMidi(info, detail, sizeof(detail));
        break;
      }
      default:
        break;
    }
    const uint32_t end = hardware.nowMs();
    applyTestResult(&report, id, end - start, hardwareOk, valid, detail);
    if (stopOnFail && report.tests[report.count - 1].status != TestStatus::Pass) break;
  }

  report.totalDurationMs = hardware.nowMs() - runStart;
  report.overallPass = report.count == kTestCount;
  for (uint8_t i = 0; i < report.count; ++i) {
    switch (report.tests[i].status) {
      case TestStatus::Pass:
        ++report.passCount;
        break;
      case TestStatus::Timeout:
        ++report.timeoutCount;
        ++report.failCount;
        report.overallPass = false;
        break;
      case TestStatus::Skip:
        ++report.skipCount;
        break;
      default:
        ++report.failCount;
        report.overallPass = false;
        break;
    }
  }
  return report;
}

// --- JSON -------------------------------------------------------------------
bool reportToJson(const Report& report, char* out, size_t capacity) {
  if (!out || capacity == 0) return false;
  size_t used = 0;
  auto append = [&](const char* format, ...) -> bool {
    if (used >= capacity) return false;
    va_list args;
    va_start(args, format);
    const int written = std::vsnprintf(out + used, capacity - used, format, args);
    va_end(args);
    if (written < 0 || static_cast<size_t>(written) >= capacity - used) return false;
    used += static_cast<size_t>(written);
    return true;
  };
  if (!append("{\"schema\":\"bukifon-factory-selftest-v1\",\"product\":\"BUKIFON\","
              "\"factory_version\":\"0.1.0\",\"overall_pass\":%s,\"total_ms\":%u,"
              "\"count\":%u,\"pass\":%u,\"fail\":%u,\"timeout\":%u,\"skip\":%u,\"tests\":[",
              report.overallPass ? "true" : "false",
              static_cast<unsigned>(report.totalDurationMs), static_cast<unsigned>(report.count),
              static_cast<unsigned>(report.passCount), static_cast<unsigned>(report.failCount),
              static_cast<unsigned>(report.timeoutCount),
              static_cast<unsigned>(report.skipCount))) {
    return false;
  }
  for (uint8_t i = 0; i < report.count; ++i) {
    const TestResult& test = report.tests[i];
    char detail[96];
    std::snprintf(detail, sizeof(detail), "%s", test.detail);
    for (char* p = detail; *p; ++p) {
      if (*p == '"') *p = '\'';
      if (*p == '\n' || *p == '\r') *p = ' ';
    }
    if (!append("%s{\"id\":%u,\"name\":\"%s\",\"status\":\"%s\",\"nominal_ms\":%u,"
                "\"duration_ms\":%u,\"detail\":\"%s\"}",
                i == 0 ? "" : ",", static_cast<unsigned>(test.id), testName(test.id),
                statusName(test.status), static_cast<unsigned>(test.nominalMs),
                static_cast<unsigned>(test.durationMs), detail)) {
      return false;
    }
  }
  return append("]}\n");
}

// --- CLI --------------------------------------------------------------------
int factoryCliMain(int argc, char** argv, Hardware& hardware, std::FILE* out) {
  if (!out) return 2;
  bool jsonOnly = false;
  bool stopOnFail = false;
  const char* outPath = nullptr;
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "--json") == 0) {
      jsonOnly = true;
    } else if (std::strcmp(argv[i], "--stop-on-fail") == 0) {
      stopOnFail = true;
    } else if (std::strcmp(argv[i], "--out") == 0 && i + 1 < argc) {
      outPath = argv[++i];
    } else if (std::strcmp(argv[i], "--help") == 0) {
      std::fprintf(out,
                   "usage: factory [--json] [--out PATH] [--stop-on-fail]\n"
                   "  --json          machine-readable report only\n"
                   "  --out PATH      also write the JSON report to PATH\n"
                   "  --stop-on-fail  stop at the first failed test\n");
      return 0;
    } else {
      std::fprintf(out, "unknown argument: %s\n", argv[i]);
      return 2;
    }
  }

  const Report report = runSelfTest(hardware, stopOnFail);
  char json[4096];
  const bool jsonOk = reportToJson(report, json, sizeof(json));

  if (!jsonOnly) {
    std::fprintf(out, "BUKIFON factory self-test (%s)\n", "host/device");
    std::fprintf(out, " #  test                status   time/nominal  detail\n");
    for (uint8_t i = 0; i < report.count; ++i) {
      const TestResult& test = report.tests[i];
      std::fprintf(out, "%2u  %-18s  %-7s %5u/%-5u  %s\n", static_cast<unsigned>(test.id + 1),
                   testName(test.id), statusName(test.status),
                   static_cast<unsigned>(test.durationMs), static_cast<unsigned>(test.nominalMs),
                   test.detail);
    }
    std::fprintf(out, "TOTAL: %u/%u passed, %u failed, %u timeout, %u ms (%s)\n",
                 static_cast<unsigned>(report.passCount), static_cast<unsigned>(report.count),
                 static_cast<unsigned>(report.failCount),
                 static_cast<unsigned>(report.timeoutCount),
                 static_cast<unsigned>(report.totalDurationMs),
                 report.overallPass ? "PASS" : "FAIL");
  }
  if (jsonOnly && jsonOk) std::fprintf(out, "%s", json);
  if (outPath && jsonOk) {
    std::FILE* file = std::fopen(outPath, "wb");
    if (!file) {
      std::fprintf(out, "ERROR: cannot write %s\n", outPath);
      return 2;
    }
    std::fwrite(json, 1, std::strlen(json), file);
    std::fclose(file);
  }
  return report.overallPass ? 0 : 1;
}

}  // namespace factory
}  // namespace bukifon
