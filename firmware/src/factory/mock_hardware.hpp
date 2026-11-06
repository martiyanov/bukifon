// SPDX-License-Identifier: GPL-3.0-or-later
// Host mock for the factory self-test (pattern: spike_s3 host simulation).
// All values are plausible and PASS by default; tests inject failures/timeouts.
#pragma once

#include "factory/selftest.hpp"

namespace bukifon {
namespace factory {

class MockHardware : public Hardware {
 public:
  MockHardware();
  void failTest(TestId id, bool fail);
  bool failing(TestId id) const;
  void setDurationMs(TestId id, uint32_t ms);
  uint32_t durationMs(TestId id) const;
  void resetClock() { clockMs_ = 0; }
  uint32_t clockMs() const { return clockMs_; }

  uint32_t nowMs() override { return clockMs_; }
  bool readPower(PowerInfo* out) override;
  bool scanI2c(I2cScanInfo* out) override;
  bool testMcp23017(Mcp23017Info* out) override;
  bool readMcp3208(Mcp3208Info* out) override;
  bool dacAdcLoopback(DacAdcInfo* out) override;
  bool codecLoopback(CodecInfo* out) override;
  bool sdScratch(SdInfo* out) override;
  bool displayPatterns(DisplayInfo* out) override;
  bool ws2812Current(Ws2812Info* out) override;
  bool readMax17048(Max17048Info* out) override;
  bool usbComposite(UsbInfo* out) override;
  bool controls(ControlsInfo* out) override;
  bool cvGateLoopback(CvGateInfo* out) override;
  bool midiLoopback(MidiInfo* out) override;
  bool eepromTest(EepromInfo* out) override;
  bool mcp4728Test(Mcp4728Info* out) override;
  bool c6Link(C6LinkInfo* out) override;
  bool cvInputs(CvInputInfo* out) override;
  bool uartBoot(UartBootInfo* out) override;
  bool serialQr(SerialQrInfo* out) override;
  bool micTest(MicInfo* out) override;

 private:
  uint32_t advance(TestId id);
  uint32_t clockMs_ = 0;
  uint32_t durationMs_[kTestCount] = {};
  bool fail_[kTestCount] = {};
};

}  // namespace factory
}  // namespace bukifon
