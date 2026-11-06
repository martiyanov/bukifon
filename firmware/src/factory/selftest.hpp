// SPDX-License-Identifier: GPL-3.0-or-later
// Factory self-test — 21 tests from docs/42 §2 / hardware/core2/dfm.md (bring-up + EOL production test).
//
// Portable core: hardware access is behind the `Hardware` interface, so the
// same runner/validators run on the P4 (P4FactoryHardware, TODO(hw) stubs) and
// on a host with `MockHardware` (CI/CLI).  Every test has a nominal time and a
// timeout; results are PASS/FAIL/TIMEOUT with a JSON report and a CLI
// (`factory --json`) for the production station.
#pragma once

#include <cstdint>
#include <cstdio>

namespace bukifon {
namespace factory {

class IdentityStore;  // factory/identity.hpp

constexpr int kTestCount = 21;

enum class TestId : uint8_t {
  PowerOn = 0,
  I2cScan,
  Mcp23017Walking,
  Mcp3208Vector,
  DacAdcLoopback,
  CodecLoopback,
  SdScratch,
  DisplayPatterns,
  Ws2812Current,
  Max17048,
  UsbComposite,
  Controls,
  CvGateLoopback,
  MidiLoopback,
  Eeprom,
  Mcp4728,
  C6Link,
  CvInputs,
  UartBoot,
  SerialQr,
  Mic,
  Count = 21
};

enum class TestStatus : uint8_t { Pending = 0, Pass, Fail, Timeout, Skip };

const char* testName(TestId id);
uint32_t nominalTimeMs(TestId id);
uint32_t timeoutMs(TestId id);

struct TestResult {
  TestId id = TestId::PowerOn;
  TestStatus status = TestStatus::Pending;
  uint32_t nominalMs = 0;
  uint32_t durationMs = 0;
  char detail[96] = {};
};

struct Report {
  TestResult tests[kTestCount];
  uint8_t count = 0;
  bool overallPass = false;
  uint32_t totalDurationMs = 0;
  uint8_t passCount = 0;
  uint8_t failCount = 0;
  uint8_t timeoutCount = 0;
  uint8_t skipCount = 0;
};

// --- hardware values measured by each test --------------------------------
struct PowerInfo {
  uint32_t resetReason = 0;
  uint32_t brownoutCount = 0;
  bool powerGood = false;
};
struct I2cScanInfo {
  uint8_t addresses[16] = {};
  uint8_t count = 0;
};
struct Mcp23017Info {
  bool addressesAck[4] = {};
  bool irqToggles = false;
};
struct Mcp3208Info {
  float volts[8] = {};
};
struct DacAdcInfo {
  float errorsMv[4] = {};
};
struct CodecInfo {
  float toneHz = 0.0f;
  float gainDb = 0.0f;
  float thdDb = 0.0f;
  float levelDbfs = 0.0f;
};
struct SdInfo {
  uint32_t bytes = 0;
  uint32_t crc32 = 0;
  bool crcOk = false;
  float throughputKbps = 0.0f;
};
struct DisplayInfo {
  uint8_t patternsShown = 0;
  bool operatorSeenNoBands = false;
};
struct Ws2812Info {
  float currentMa = 0.0f;
  float expectedMa = 0.0f;
  uint8_t ledsOk = 0;
  uint8_t ledsTotal = 0;
};
struct Max17048Info {
  float cellVolts = 0.0f;
  float dmmVolts = 0.0f;
};
struct UsbInfo {
  uint32_t classMask = 0;
  bool enumerated = false;
};
struct ControlsInfo {
  uint16_t keysOk = 0;
  uint16_t keysTotal = 42;
  uint8_t encodersOk = 0;
  uint8_t encodersTotal = 16;
  uint8_t fadersOk = 0;
  uint8_t fadersTotal = 2;
};
struct CvGateInfo {
  float errorsMv[4] = {};
  bool gateLoopback = false;
};
struct MidiInfo {
  uint16_t sent = 0;
  uint16_t received = 0;
  uint16_t errors = 0;
};
struct EepromInfo {
  bool magicOk = false;
  uint8_t bytesOk = 0;
  uint8_t bytesTotal = 0;
  char serial[16] = {};
  bool serialReads = false;
};
struct Mcp4728Info {
  bool addressesAck[2] = {};
  uint8_t channelsOk = 0;
  uint8_t channelsTotal = 8;
  int8_t maxLsbError = 0;
};
struct C6LinkInfo {
  bool responded = false;
  uint32_t rpcLatencyUs = 0;
  uint32_t firmwareVersion = 0;
  bool wifiScanOk = false;
};
struct CvInputInfo {
  float errorsPercent[4] = {};
  bool tvsOk = false;
};
struct UartBootInfo {
  bool uartLog = false;
  bool bootStrap = false;
  uint32_t baud = 0;
};
struct SerialQrInfo {
  bool serialMatches = false;
  bool revisionMatches = false;
  bool dateMatches = false;
  bool qrMatches = false;
};
struct MicInfo {
  bool memsRecording = false;
  float rmsDbfs = -120.0f;
  bool vad = false;
  bool micSel = false;      // TS5A MIC_SEL: LINE/MIC switch
  bool muteBlocks = false;  // SW3 mute stops recording
  bool ledOn = false;       // LED MIC ON model
  bool electretLoopback = false;
  float snrDb = 0.0f;
  float latencyMs = 100.0f;
};

// Common bus/class masks.
constexpr uint32_t kUsbCdc = 1u << 0;
constexpr uint32_t kUsbMidi = 1u << 1;
constexpr uint32_t kUsbHid = 1u << 2;
constexpr uint32_t kUsbUac = 1u << 3;
constexpr uint32_t kUsbRequiredClasses = kUsbCdc | kUsbMidi | kUsbHid | kUsbUac;

// --- hardware abstraction --------------------------------------------------
class Hardware {
 public:
  virtual ~Hardware() = default;
  virtual uint32_t nowMs() = 0;
  virtual bool readPower(PowerInfo* out) = 0;
  virtual bool scanI2c(I2cScanInfo* out) = 0;
  virtual bool testMcp23017(Mcp23017Info* out) = 0;
  virtual bool readMcp3208(Mcp3208Info* out) = 0;
  virtual bool dacAdcLoopback(DacAdcInfo* out) = 0;
  virtual bool codecLoopback(CodecInfo* out) = 0;
  virtual bool sdScratch(SdInfo* out) = 0;
  virtual bool displayPatterns(DisplayInfo* out) = 0;
  virtual bool ws2812Current(Ws2812Info* out) = 0;
  virtual bool readMax17048(Max17048Info* out) = 0;
  virtual bool usbComposite(UsbInfo* out) = 0;
  virtual bool controls(ControlsInfo* out) = 0;
  virtual bool cvGateLoopback(CvGateInfo* out) = 0;
  virtual bool midiLoopback(MidiInfo* out) = 0;
  virtual bool eepromTest(EepromInfo* out) = 0;
  virtual bool mcp4728Test(Mcp4728Info* out) = 0;
  virtual bool c6Link(C6LinkInfo* out) = 0;
  virtual bool cvInputs(CvInputInfo* out) = 0;
  virtual bool uartBoot(UartBootInfo* out) = 0;
  virtual bool serialQr(SerialQrInfo* out) = 0;
  virtual bool micTest(MicInfo* out) = 0;
  // Hardware may report a test as not present (SKIP) instead of failing it.
  virtual bool isAvailable(TestId id) {
    (void)id;
    return true;
  }
};

// --- validators (exposed for unit tests) -----------------------------------
bool checkPower(const PowerInfo& info, char* detail, size_t len);
bool checkI2c(const I2cScanInfo& info, char* detail, size_t len);
bool checkMcp23017(const Mcp23017Info& info, char* detail, size_t len);
bool checkMcp3208(const Mcp3208Info& info, char* detail, size_t len);
bool checkDacAdc(const DacAdcInfo& info, char* detail, size_t len);
bool checkCodec(const CodecInfo& info, char* detail, size_t len);
bool checkSd(const SdInfo& info, char* detail, size_t len);
bool checkDisplay(const DisplayInfo& info, char* detail, size_t len);
bool checkWs2812(const Ws2812Info& info, char* detail, size_t len);
bool checkMax17048(const Max17048Info& info, char* detail, size_t len);
bool checkUsb(const UsbInfo& info, char* detail, size_t len);
bool checkControls(const ControlsInfo& info, char* detail, size_t len);
bool checkCvGate(const CvGateInfo& info, char* detail, size_t len);
bool checkMidi(const MidiInfo& info, char* detail, size_t len);
bool checkEeprom(const EepromInfo& info, char* detail, size_t len);
bool checkMcp4728(const Mcp4728Info& info, char* detail, size_t len);
bool checkC6Link(const C6LinkInfo& info, char* detail, size_t len);
bool checkCvInputs(const CvInputInfo& info, char* detail, size_t len);
bool checkUartBoot(const UartBootInfo& info, char* detail, size_t len);
bool checkSerialQr(const SerialQrInfo& info, char* detail, size_t len);
bool checkMic(const MicInfo& info, char* detail, size_t len);

// Runs all 14 tests (allocation-free, fixed arrays).  Stops early only when
// `stopOnFail` is true (production may continue to log all failures).
Report runSelfTest(Hardware& hardware, bool stopOnFail = false);

// JSON report (schema bukifon-factory-selftest-v1).
bool reportToJson(const Report& report, char* out, size_t capacity);
const char* statusName(TestStatus status);

// CLI: `factory [--json] [--out PATH] [--stop-on-fail]
//                [--identity PATH.json] [--print-identity]`.
// Identity actions write/read the two-slot store (real flash is TODO(hw)).
// Returns 0 when PASS / identity OK, 1 for FAIL, 2 usage, 3 no identity.
int factoryCliMain(int argc, char** argv, Hardware& hardware, std::FILE* out,
                   IdentityStore* identityStore = nullptr);

}  // namespace factory
}  // namespace bukifon
