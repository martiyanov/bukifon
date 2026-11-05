// SPDX-License-Identifier: GPL-3.0-or-later
#include "factory/hw_backends.hpp"

namespace bukifon {
namespace factory {
namespace {

HwMode fromMacro(int value) { return value == BUKIFON_HW_REAL ? HwMode::Real : HwMode::Mock; }

}  // namespace

const char* hwBackendName(HwBackend backend) {
  switch (backend) {
    case HwBackend::I2c: return "I2C";
    case HwBackend::Adc: return "ADC";
    case HwBackend::Dac: return "DAC";
    case HwBackend::I2s: return "I2S";
    case HwBackend::Sd: return "SD";
    case HwBackend::Display: return "DISPLAY";
    case HwBackend::Usb: return "USB";
    case HwBackend::Controls: return "CONTROLS";
    case HwBackend::Cv: return "CV";
    case HwBackend::Midi: return "MIDI";
    default: return "";
  }
}

bool hwRealDefault(HwBackend backend) {
  switch (backend) {
    case HwBackend::I2c: return fromMacro(BUKIFON_HW_I2C) == HwMode::Real;
    case HwBackend::Adc: return fromMacro(BUKIFON_HW_ADC) == HwMode::Real;
    case HwBackend::Dac: return fromMacro(BUKIFON_HW_DAC) == HwMode::Real;
    case HwBackend::I2s: return fromMacro(BUKIFON_HW_I2S) == HwMode::Real;
    case HwBackend::Sd: return fromMacro(BUKIFON_HW_SD) == HwMode::Real;
    case HwBackend::Display: return fromMacro(BUKIFON_HW_DISPLAY) == HwMode::Real;
    case HwBackend::Usb: return fromMacro(BUKIFON_HW_USB) == HwMode::Real;
    case HwBackend::Controls: return fromMacro(BUKIFON_HW_CONTROLS) == HwMode::Real;
    case HwBackend::Cv: return fromMacro(BUKIFON_HW_CV) == HwMode::Real;
    case HwBackend::Midi: return fromMacro(BUKIFON_HW_MIDI) == HwMode::Real;
    default: return false;
  }
}

HwConfig::HwConfig() {
  for (int i = 0; i < kHwBackendCount; ++i) {
    modes[i] = hwRealDefault(static_cast<HwBackend>(i)) ? HwMode::Real : HwMode::Mock;
  }
}

void HwConfig::set(HwBackend backend, HwMode mode) {
  const int index = static_cast<int>(backend);
  if (index >= 0 && index < kHwBackendCount) modes[index] = mode;
}

HwMode HwConfig::get(HwBackend backend) const {
  const int index = static_cast<int>(backend);
  return (index >= 0 && index < kHwBackendCount) ? modes[index] : HwMode::Mock;
}

int HwConfig::realCount() const {
  int count = 0;
  for (int i = 0; i < kHwBackendCount; ++i) {
    if (modes[i] == HwMode::Real) ++count;
  }
  return count;
}

HybridHardware::HybridHardware(Hardware& real, Hardware& mock, const HwConfig& config)
    : real_(real), mock_(mock), config_(config) {}

Hardware& HybridHardware::pick(HwBackend backend) { return config_.real(backend) ? real_ : mock_; }

uint32_t HybridHardware::nowMs() {
  return config_.allMock() ? mock_.nowMs() : real_.nowMs();
}

bool HybridHardware::readPower(PowerInfo* out) { return pick(HwBackend::I2c).readPower(out); }
bool HybridHardware::scanI2c(I2cScanInfo* out) { return pick(HwBackend::I2c).scanI2c(out); }
bool HybridHardware::testMcp23017(Mcp23017Info* out) {
  return pick(HwBackend::I2c).testMcp23017(out);
}
bool HybridHardware::readMcp3208(Mcp3208Info* out) {
  return pick(HwBackend::Adc).readMcp3208(out);
}
bool HybridHardware::dacAdcLoopback(DacAdcInfo* out) {
  return pick(HwBackend::Dac).dacAdcLoopback(out);
}
bool HybridHardware::codecLoopback(CodecInfo* out) {
  return pick(HwBackend::I2s).codecLoopback(out);
}
bool HybridHardware::sdScratch(SdInfo* out) { return pick(HwBackend::Sd).sdScratch(out); }
bool HybridHardware::displayPatterns(DisplayInfo* out) {
  return pick(HwBackend::Display).displayPatterns(out);
}
bool HybridHardware::ws2812Current(Ws2812Info* out) {
  return pick(HwBackend::Display).ws2812Current(out);
}
bool HybridHardware::readMax17048(Max17048Info* out) {
  return pick(HwBackend::I2c).readMax17048(out);
}
bool HybridHardware::usbComposite(UsbInfo* out) { return pick(HwBackend::Usb).usbComposite(out); }
bool HybridHardware::controls(ControlsInfo* out) {
  return pick(HwBackend::Controls).controls(out);
}
bool HybridHardware::cvGateLoopback(CvGateInfo* out) {
  return pick(HwBackend::Cv).cvGateLoopback(out);
}
bool HybridHardware::midiLoopback(MidiInfo* out) {
  return pick(HwBackend::Midi).midiLoopback(out);
}

}  // namespace factory
}  // namespace bukifon
