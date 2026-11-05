// SPDX-License-Identifier: GPL-3.0-or-later
// P4 factory hardware access — TODO(hw) stubs.
//
// Real implementations for the P4 devkit/board are not written yet: the P4
// PlatformIO platform is unavailable in this environment (official espressif32
// 8.0.0 has no P4 board).  The self-test runner/validators are ready; the
// methods below return false so a P4 run reports honest failures instead of
// fabricating PASSes.  Wire them to board_cores2 + esp_tinyusb + I2S/SD/I2C
// drivers on the first working P4 toolchain.
#pragma once

#include "factory/selftest.hpp"

namespace bukifon {
namespace factory {

class P4FactoryHardware : public Hardware {
 public:
  uint32_t nowMs() override;
  bool readPower(PowerInfo*) override;
  bool scanI2c(I2cScanInfo*) override;
  bool testMcp23017(Mcp23017Info*) override;
  bool readMcp3208(Mcp3208Info*) override;
  bool dacAdcLoopback(DacAdcInfo*) override;
  bool codecLoopback(CodecInfo*) override;
  bool sdScratch(SdInfo*) override;
  bool displayPatterns(DisplayInfo*) override;
  bool ws2812Current(Ws2812Info*) override;
  bool readMax17048(Max17048Info*) override;
  bool usbComposite(UsbInfo*) override;
  bool controls(ControlsInfo*) override;
  bool cvGateLoopback(CvGateInfo*) override;
  bool midiLoopback(MidiInfo*) override;

 private:
  uint32_t clockMs_ = 0;
};

}  // namespace factory
}  // namespace bukifon
