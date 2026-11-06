// SPDX-License-Identifier: GPL-3.0-or-later
#include "factory/mock_hardware.hpp"

#include <cstring>

namespace bukifon {
namespace factory {

MockHardware::MockHardware() {
  for (int i = 0; i < kTestCount; ++i) {
    durationMs_[i] = nominalTimeMs(static_cast<TestId>(i));
    fail_[i] = false;
  }
}

void MockHardware::failTest(TestId id, bool fail) {
  const int index = static_cast<int>(id);
  if (index >= 0 && index < kTestCount) fail_[index] = fail;
}

bool MockHardware::failing(TestId id) const {
  const int index = static_cast<int>(id);
  return index >= 0 && index < kTestCount && fail_[index];
}

void MockHardware::setDurationMs(TestId id, uint32_t ms) {
  const int index = static_cast<int>(id);
  if (index >= 0 && index < kTestCount) durationMs_[index] = ms;
}

uint32_t MockHardware::durationMs(TestId id) const {
  const int index = static_cast<int>(id);
  return (index >= 0 && index < kTestCount) ? durationMs_[index] : 0;
}

uint32_t MockHardware::advance(TestId id) {
  clockMs_ += durationMs(id);
  return clockMs_;
}

bool MockHardware::readPower(PowerInfo* out) {
  advance(TestId::PowerOn);
  if (failing(TestId::PowerOn) || !out) return false;
  *out = PowerInfo{1, 0, true};
  return true;
}

bool MockHardware::scanI2c(I2cScanInfo* out) {
  advance(TestId::I2cScan);
  if (failing(TestId::I2cScan) || !out) return false;
  const uint8_t addresses[] = {0x20, 0x21, 0x22, 0x23, 0x36, 0x57, 0x60, 0x61};
  out->count = static_cast<uint8_t>(sizeof(addresses));
  std::memcpy(out->addresses, addresses, sizeof(addresses));
  return true;
}

bool MockHardware::testMcp23017(Mcp23017Info* out) {
  advance(TestId::Mcp23017Walking);
  if (failing(TestId::Mcp23017Walking) || !out) return false;
  for (int i = 0; i < 4; ++i) out->addressesAck[i] = true;
  out->irqToggles = true;
  return true;
}

bool MockHardware::readMcp3208(Mcp3208Info* out) {
  advance(TestId::Mcp3208Vector);
  if (failing(TestId::Mcp3208Vector) || !out) return false;
  const float values[8] = {0.251f, 1.249f, 2.501f, 0.250f, 1.250f, 2.499f, 0.252f, 1.248f};
  std::memcpy(out->volts, values, sizeof(values));
  return true;
}

bool MockHardware::dacAdcLoopback(DacAdcInfo* out) {
  advance(TestId::DacAdcLoopback);
  if (failing(TestId::DacAdcLoopback) || !out) return false;
  const float errors[4] = {4.0f, -6.5f, 9.0f, -12.0f};
  std::memcpy(out->errorsMv, errors, sizeof(errors));
  return true;
}

bool MockHardware::codecLoopback(CodecInfo* out) {
  advance(TestId::CodecLoopback);
  if (failing(TestId::CodecLoopback) || !out) return false;
  *out = CodecInfo{1000.2f, 0.15f, -71.0f, -12.1f};
  return true;
}

bool MockHardware::sdScratch(SdInfo* out) {
  advance(TestId::SdScratch);
  if (failing(TestId::SdScratch) || !out) return false;
  *out = SdInfo{1024u * 1024u, 0xDEADBEEFu, true, 1150.0f};
  return true;
}

bool MockHardware::displayPatterns(DisplayInfo* out) {
  advance(TestId::DisplayPatterns);
  if (failing(TestId::DisplayPatterns) || !out) return false;
  *out = DisplayInfo{4, true};
  return true;
}

bool MockHardware::ws2812Current(Ws2812Info* out) {
  advance(TestId::Ws2812Current);
  if (failing(TestId::Ws2812Current) || !out) return false;
  *out = Ws2812Info{118.0f, 120.0f, 16, 16};
  return true;
}

bool MockHardware::readMax17048(Max17048Info* out) {
  advance(TestId::Max17048);
  if (failing(TestId::Max17048) || !out) return false;
  *out = Max17048Info{4.180f, 4.190f};
  return true;
}

bool MockHardware::usbComposite(UsbInfo* out) {
  advance(TestId::UsbComposite);
  if (failing(TestId::UsbComposite) || !out) return false;
  *out = UsbInfo{0x0Fu, true};
  return true;
}

bool MockHardware::controls(ControlsInfo* out) {
  advance(TestId::Controls);
  if (failing(TestId::Controls) || !out) return false;
  *out = ControlsInfo{42, 42, 16, 16, 2, 2};
  return true;
}

bool MockHardware::cvGateLoopback(CvGateInfo* out) {
  advance(TestId::CvGateLoopback);
  if (failing(TestId::CvGateLoopback) || !out) return false;
  const float errors[4] = {3.0f, -5.0f, 7.0f, -9.0f};
  std::memcpy(out->errorsMv, errors, sizeof(errors));
  out->gateLoopback = true;
  return true;
}

bool MockHardware::midiLoopback(MidiInfo* out) {
  advance(TestId::MidiLoopback);
  if (failing(TestId::MidiLoopback) || !out) return false;
  *out = MidiInfo{100, 100, 0};
  return true;
}


bool MockHardware::eepromTest(EepromInfo* out) {
  advance(TestId::Eeprom);
  if (failing(TestId::Eeprom) || !out) return false;
  *out = EepromInfo{true, 32, 32, "BKF-2026A1", true};
  return true;
}

bool MockHardware::mcp4728Test(Mcp4728Info* out) {
  advance(TestId::Mcp4728);
  if (failing(TestId::Mcp4728) || !out) return false;
  out->addressesAck[0] = true;
  out->addressesAck[1] = true;
  out->channelsOk = 8;
  out->channelsTotal = 8;
  out->maxLsbError = 0;
  return true;
}

bool MockHardware::c6Link(C6LinkInfo* out) {
  advance(TestId::C6Link);
  if (failing(TestId::C6Link) || !out) return false;
  *out = C6LinkInfo{true, 25000u, 0x0301u, true};
  return true;
}

bool MockHardware::cvInputs(CvInputInfo* out) {
  advance(TestId::CvInputs);
  if (failing(TestId::CvInputs) || !out) return false;
  const float errors[4] = {0.2f, -0.4f, 0.3f, -0.5f};
  std::memcpy(out->errorsPercent, errors, sizeof(errors));
  out->tvsOk = true;
  return true;
}

bool MockHardware::uartBoot(UartBootInfo* out) {
  advance(TestId::UartBoot);
  if (failing(TestId::UartBoot) || !out) return false;
  *out = UartBootInfo{true, true, 115200u};
  return true;
}

bool MockHardware::serialQr(SerialQrInfo* out) {
  advance(TestId::SerialQr);
  if (failing(TestId::SerialQr) || !out) return false;
  *out = SerialQrInfo{true, true, true, true};
  return true;
}

bool MockHardware::micTest(MicInfo* out) {
  advance(TestId::Mic);
  if (failing(TestId::Mic) || !out) return false;
  *out = MicInfo{true, -18.0f, true, true, true, true, true, 70.0f, 3.5f};
  return true;
}

}  // namespace factory
}  // namespace bukifon
