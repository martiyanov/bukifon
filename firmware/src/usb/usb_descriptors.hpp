// SPDX-License-Identifier: GPL-3.0-or-later
// USB composite descriptor builder — HID keyboard + MIDI + UAC2 + CDC.
//
// The builder is pure C++ (no TinyUSB dependency) so it can be unit-tested on
// the host.  On P4/S3 the produced byte arrays are handed to TinyUSB
// descriptors (the actual TinyUSB glue is a device-side TODO, see
// app/esp32_main.cpp and REPORT.md).
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace bukifon {
namespace usb {

struct UsbCompositeDescriptor {
  std::vector<uint8_t> device;       // 18-byte device descriptor
  std::vector<uint8_t> config;       // full configuration descriptor
  std::vector<uint8_t> hidReport;    // HID report descriptor (6KRO keyboard)
  uint8_t interfaceCount = 0;
  uint8_t endpointCount = 0;
  uint16_t configTotalLength = 0;
};

class UsbCompositeBuilder {
 public:
  void setVidPid(uint16_t vendorId, uint16_t productId);
  void includeHidKeyboard(bool enabled) { hidKeyboard_ = enabled; }
  void includeMidi(bool enabled) { midi_ = enabled; }
  void includeUac2(bool enabled) { uac2_ = enabled; }
  void includeCdc(bool enabled) { cdc_ = enabled; }
  void setMaxPowerMa(uint16_t milliamps) { maxPowerMa_ = milliamps; }

  bool build();
  const UsbCompositeDescriptor& descriptors() const { return result_; }

  // Helpers used by tests and the device layer.
  static uint16_t u16(uint8_t lo, uint8_t hi) {
    return static_cast<uint16_t>(lo | (hi << 8));
  }
  static size_t hidKeyboardReportDescriptor(uint8_t* out, size_t capacity);
  static size_t hidReportSize();

 private:
  void appendDevice();
  void appendHidInterface();
  void appendMidiInterface(uint8_t firstInterface);
  void appendUac2Interfaces(uint8_t firstInterface);
  void appendCdcInterfaces(uint8_t firstInterface);
  void patchConfigLength();

  uint16_t vendorId_ = 0x2E8A;   // Raspberry Pi (placeholder for Bukifon VID)
  uint16_t productId_ = 0x000A;
  uint16_t maxPowerMa_ = 100;
  bool hidKeyboard_ = true;
  bool midi_ = true;
  bool uac2_ = true;
  bool cdc_ = true;
  bool built_ = false;
  UsbCompositeDescriptor result_;
};

// Descriptor constants used by tests/device code.
constexpr uint8_t kDeviceDescriptorSize = 18;
constexpr uint8_t kConfigDescriptorSize = 9;
constexpr uint8_t kInterfaceDescriptorSize = 9;
constexpr uint8_t kEndpointDescriptorSize = 7;
constexpr uint8_t kHidDescriptorSize = 9;

}  // namespace usb
}  // namespace bukifon
