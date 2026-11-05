// SPDX-License-Identifier: GPL-3.0-or-later
#include "usb/usb_descriptors.hpp"

#include <cstring>

namespace bukifon {
namespace usb {
namespace {

void append(std::vector<uint8_t>& v, std::initializer_list<uint8_t> bytes) {
  v.insert(v.end(), bytes);
}

void appendEndpoint(std::vector<uint8_t>& v, uint8_t address, uint8_t attributes,
                    uint16_t maxPacket, uint8_t interval) {
  append(v, {kEndpointDescriptorSize, 0x05, address, attributes, static_cast<uint8_t>(maxPacket & 0xFF),
             static_cast<uint8_t>(maxPacket >> 8), interval});
}

void appendInterface(std::vector<uint8_t>& v, uint8_t number, uint8_t alternate,
                     uint8_t endpoints, uint8_t classCode, uint8_t subclass, uint8_t protocol,
                     uint8_t stringIndex) {
  append(v, {kInterfaceDescriptorSize, 0x04, number, alternate, endpoints, classCode, subclass,
             protocol, stringIndex});
}

}  // namespace

size_t UsbCompositeBuilder::hidReportSize() { return 45; }

size_t UsbCompositeBuilder::hidKeyboardReportDescriptor(uint8_t* out, size_t capacity) {
  // Standard boot-protocol-compatible 6KRO keyboard:
  //   8 modifier bits, 1 reserved byte, 6 keycodes.
  static const uint8_t kReport[45] = {
      0x05, 0x01,        // Usage Page (Generic Desktop)
      0x09, 0x06,        // Usage (Keyboard)
      0xA1, 0x01,        // Collection (Application)
      0x05, 0x07,        //   Usage Page (Keyboard/Keypad)
      0x19, 0xE0,        //   Usage Minimum (Left Control)
      0x29, 0xE7,        //   Usage Maximum (Right GUI)
      0x15, 0x00,        //   Logical Minimum (0)
      0x25, 0x01,        //   Logical Maximum (1)
      0x75, 0x01,        //   Report Size (1)
      0x95, 0x08,        //   Report Count (8)
      0x81, 0x02,        //   Input (Data, Variable, Absolute) — modifiers
      0x95, 0x01,        //   Report Count (1)
      0x75, 0x08,        //   Report Size (8)
      0x81, 0x01,        //   Input (Constant) — reserved byte
      0x95, 0x06,        //   Report Count (6)
      0x75, 0x08,        //   Report Size (8)
      0x15, 0x00,        //   Logical Minimum (0)
      0x25, 0x65,        //   Logical Maximum (101)
      0x05, 0x07,        //   Usage Page (Keyboard/Keypad)
      0x19, 0x00,        //   Usage Minimum (0)
      0x29, 0x65,        //   Usage Maximum (101)
      0x81, 0x00,        //   Input (Data, Array) — 6 keycodes
      0xC0,              // End Collection
  };
  if (!out || capacity < sizeof(kReport)) return 0;
  std::memcpy(out, kReport, sizeof(kReport));
  return sizeof(kReport);
}

void UsbCompositeBuilder::setVidPid(uint16_t vendorId, uint16_t productId) {
  vendorId_ = vendorId;
  productId_ = productId;
}

bool UsbCompositeBuilder::build() {
  result_ = UsbCompositeDescriptor{};
  result_.hidReport.resize(hidReportSize());
  if (hidKeyboardReportDescriptor(result_.hidReport.data(), result_.hidReport.size()) == 0) {
    return false;
  }
  appendDevice();
  // Configuration descriptor (length patched later) with:
  //   bLength, bDescriptorType, wTotalLength, bNumInterfaces, bConfigValue, iConfig,
  //   bmAttributes, bMaxPower
  append(result_.config, {kConfigDescriptorSize, 0x02, 0x00, 0x00, 0x00, 0x01, 0x00, 0x80,
                          static_cast<uint8_t>((maxPowerMa_ + 1) / 2)});
  uint8_t interface = 0;
  uint8_t endpoints = 0;
  if (hidKeyboard_) {
    appendHidInterface();
    interface += 1;
    endpoints += 1;
  }
  if (midi_) {
    appendMidiInterface(static_cast<uint8_t>(interface));
    interface += 2;  // MIDI has a control interface + streaming interface
    endpoints += 2;
  }
  if (uac2_) {
    appendUac2Interfaces(static_cast<uint8_t>(interface));
    interface += 2;
    endpoints += 1;
  }
  if (cdc_) {
    appendCdcInterfaces(static_cast<uint8_t>(interface));
    interface += 2;
    endpoints += 3;
  }
  result_.interfaceCount = interface;
  result_.endpointCount = endpoints;
  result_.config[4] = interface;  // bNumInterfaces
  patchConfigLength();
  built_ = true;
  return true;
}

void UsbCompositeBuilder::appendDevice() {
  result_.device = {
      kDeviceDescriptorSize, 0x01,        // bLength, DEVICE
      0x00, 0x02,                          // bcdUSB 2.00
      0xEF, 0x02, 0x01,                    // class/subclass/protocol (misc, IAD)
      0x40,                                // bMaxPacketSize0 = 64
      static_cast<uint8_t>(vendorId_ & 0xFF), static_cast<uint8_t>(vendorId_ >> 8),
      static_cast<uint8_t>(productId_ & 0xFF), static_cast<uint8_t>(productId_ >> 8),
      0x00, 0x01,                          // bcdDevice 1.00
      0x01, 0x02, 0x03,                    // iManufacturer/iProduct/iSerial
      0x01,                                // bNumConfigurations
  };
}

void UsbCompositeBuilder::appendHidInterface() {
  // Interface 0: HID keyboard.
  appendInterface(result_.config, 0, 0, 1, 0x03, 0x01, 0x01, 0x00);
  // HID descriptor.
  append(result_.config, {kHidDescriptorSize, 0x21, 0x11, 0x01, 0x00, 0x01, 0x22,
                          static_cast<uint8_t>(hidReportSize()), 0x00});
  appendEndpoint(result_.config, 0x81, 0x03, 64, 10);  // interrupt IN
}

void UsbCompositeBuilder::appendMidiInterface(uint8_t firstInterface) {
  // Audio control interface for MIDI (class 0x01, subclass 0x03 = MIDI streaming).
  appendInterface(result_.config, firstInterface, 0, 0, 0x01, 0x03, 0x00, 0x00);
  // Class-specific MIDIStreaming interface header (bLength 7).
  append(result_.config, {0x07, 0x24, 0x01, 0x00, 0x01, 0x41, 0x00});
  // MIDI streaming interface with 2 bulk endpoints (OUT + IN).
  appendInterface(result_.config, static_cast<uint8_t>(firstInterface + 1), 0, 2, 0x01, 0x03, 0x00,
                  0x00);
  appendEndpoint(result_.config, 0x02, 0x02, 64, 0);  // bulk OUT
  appendEndpoint(result_.config, 0x82, 0x02, 64, 0);  // bulk IN
}

void UsbCompositeBuilder::appendUac2Interfaces(uint8_t firstInterface) {
  // UAC2 audio control interface (skeleton: descriptors valid, no real streams).
  appendInterface(result_.config, firstInterface, 0, 0, 0x01, 0x01, 0x00, 0x00);
  // Class-specific AC header (bLength 9): bcdADC 2.00, categories, total length.
  append(result_.config, {0x09, 0x24, 0x01, 0x00, 0x02, 0x04, 0x00, 0x00, 0x00});
  // Audio streaming interface, alt 0 (zero-bandwidth) and alt 1 with one isochronous IN EP.
  appendInterface(result_.config, static_cast<uint8_t>(firstInterface + 1), 0, 0, 0x01, 0x02, 0x20,
                  0x00);
  appendInterface(result_.config, static_cast<uint8_t>(firstInterface + 1), 1, 1, 0x01, 0x02, 0x20,
                  0x00);
  appendEndpoint(result_.config, 0x83, 0x05, 192, 1);  // isochronous IN
}

void UsbCompositeBuilder::appendCdcInterfaces(uint8_t firstInterface) {
  // CDC communication interface.
  appendInterface(result_.config, firstInterface, 0, 1, 0x02, 0x02, 0x01, 0x00);
  // Header functional descriptor + call management + ACM + union.
  append(result_.config, {0x05, 0x24, 0x00, 0x10, 0x01});
  append(result_.config, {0x05, 0x24, 0x01, 0x00, 0x01});
  append(result_.config, {0x04, 0x24, 0x02, 0x02});
  append(result_.config, {0x05, 0x24, 0x06, static_cast<uint8_t>(firstInterface),
                          static_cast<uint8_t>(firstInterface + 1)});
  appendEndpoint(result_.config, 0x84, 0x03, 16, 16);  // notification interrupt IN
  // CDC data interface.
  appendInterface(result_.config, static_cast<uint8_t>(firstInterface + 1), 0, 2, 0x0A, 0x00, 0x00,
                  0x00);
  appendEndpoint(result_.config, 0x03, 0x02, 64, 0);  // bulk OUT
  appendEndpoint(result_.config, 0x85, 0x02, 64, 0);  // bulk IN
}

void UsbCompositeBuilder::patchConfigLength() {
  const uint16_t total = static_cast<uint16_t>(result_.config.size());
  result_.config[2] = static_cast<uint8_t>(total & 0xFF);
  result_.config[3] = static_cast<uint8_t>(total >> 8);
  result_.configTotalLength = total;
}

}  // namespace usb
}  // namespace bukifon
