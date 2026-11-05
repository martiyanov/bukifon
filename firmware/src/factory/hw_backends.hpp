// SPDX-License-Identifier: GPL-3.0-or-later
// Factory hardware backend selection: REAL vs MOCK per subsystem.
//
// On the bench bring-up path real drivers are enabled one by one (docs/46 §9):
// I2C -> panel -> codec -> display -> SD -> USB -> CV/MIDI.  Every backend has a
// compile-time default (`BUKIFON_HW_*`) overridable per build, and a runtime
// HwConfig for the station.  A backend left on MOCK never reports hardware
// values, so a P4 stub (REAL) failing cannot be masked by the mock.
//
// Mapping:
//   I2C      -> power/reset, I2C scan, MCP23017 walking-bit, MAX17048
//   ADC      -> MCP3208 vector
//   DAC      -> MCP4728->MCP3208/CV loopback
//   I2S      -> codec loopback
//   SD       -> SD scratch file
//   DISPLAY  -> display patterns + WS2812 current
//   USB      -> USB composite enumeration
//   CONTROLS -> 42 keys / 16 encoders / 2 faders
//   CV       -> CV/GATE external loopback
//   MIDI     -> MIDI DIN loopback
#pragma once

#include "factory/selftest.hpp"

namespace bukifon {
namespace factory {

#define BUKIFON_HW_MOCK 0
#define BUKIFON_HW_REAL 1

#ifndef BUKIFON_HW_I2C
#define BUKIFON_HW_I2C BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_ADC
#define BUKIFON_HW_ADC BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_DAC
#define BUKIFON_HW_DAC BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_I2S
#define BUKIFON_HW_I2S BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_SD
#define BUKIFON_HW_SD BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_DISPLAY
#define BUKIFON_HW_DISPLAY BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_USB
#define BUKIFON_HW_USB BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_CONTROLS
#define BUKIFON_HW_CONTROLS BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_CV
#define BUKIFON_HW_CV BUKIFON_HW_MOCK
#endif
#ifndef BUKIFON_HW_MIDI
#define BUKIFON_HW_MIDI BUKIFON_HW_MOCK
#endif

enum class HwBackend : uint8_t {
  I2c = 0,
  Adc,
  Dac,
  I2s,
  Sd,
  Display,
  Usb,
  Controls,
  Cv,
  Midi,
  Count = 10
};
constexpr int kHwBackendCount = 10;

enum class HwMode : uint8_t { Mock = 0, Real = 1 };

const char* hwBackendName(HwBackend backend);
bool hwRealDefault(HwBackend backend);

struct HwConfig {
  HwMode modes[kHwBackendCount];
  HwConfig();
  void set(HwBackend backend, HwMode mode);
  HwMode get(HwBackend backend) const;
  bool real(HwBackend backend) const { return get(backend) == HwMode::Real; }
  int realCount() const;
  bool allMock() const { return realCount() == 0; }
};

// Delegating Hardware: each method is served by the real provider if its
// backend is set to REAL, otherwise by the mock provider.
class HybridHardware : public Hardware {
 public:
  HybridHardware(Hardware& real, Hardware& mock, const HwConfig& config);
  const HwConfig& config() const { return config_; }
  void setMode(HwBackend backend, HwMode mode) { config_.set(backend, mode); }

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
  Hardware& pick(HwBackend backend);

  Hardware& real_;
  Hardware& mock_;
  HwConfig config_;
};

}  // namespace factory
}  // namespace bukifon
