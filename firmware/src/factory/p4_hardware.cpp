// SPDX-License-Identifier: GPL-3.0-or-later
#include "factory/p4_hardware.hpp"

#if defined(ARDUINO)
#include <Arduino.h>
#endif

namespace bukifon {
namespace factory {

uint32_t P4FactoryHardware::nowMs() {
#if defined(ARDUINO)
  return millis();
#else
  clockMs_ += 1;  // host build only (never used by tests/CLI)
  return clockMs_;
#endif
}

#define BUKIFON_P4_STUB(method, type) \
  bool P4FactoryHardware::method(type*) { return false; }  // TODO(hw)

BUKIFON_P4_STUB(readPower, PowerInfo)
BUKIFON_P4_STUB(scanI2c, I2cScanInfo)
BUKIFON_P4_STUB(testMcp23017, Mcp23017Info)
BUKIFON_P4_STUB(readMcp3208, Mcp3208Info)
BUKIFON_P4_STUB(dacAdcLoopback, DacAdcInfo)
BUKIFON_P4_STUB(codecLoopback, CodecInfo)
BUKIFON_P4_STUB(sdScratch, SdInfo)
BUKIFON_P4_STUB(displayPatterns, DisplayInfo)
BUKIFON_P4_STUB(ws2812Current, Ws2812Info)
BUKIFON_P4_STUB(readMax17048, Max17048Info)
BUKIFON_P4_STUB(usbComposite, UsbInfo)
BUKIFON_P4_STUB(controls, ControlsInfo)
BUKIFON_P4_STUB(cvGateLoopback, CvGateInfo)
BUKIFON_P4_STUB(midiLoopback, MidiInfo)
BUKIFON_P4_STUB(eepromTest, EepromInfo)
BUKIFON_P4_STUB(mcp4728Test, Mcp4728Info)
BUKIFON_P4_STUB(c6Link, C6LinkInfo)
BUKIFON_P4_STUB(cvInputs, CvInputInfo)
BUKIFON_P4_STUB(uartBoot, UartBootInfo)
BUKIFON_P4_STUB(serialQr, SerialQrInfo)
BUKIFON_P4_STUB(micTest, MicInfo)

#undef BUKIFON_P4_STUB

}  // namespace factory
}  // namespace bukifon
