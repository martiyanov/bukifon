// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstring>
#include <set>
#include <vector>

#include "test_framework.hpp"
#include "usb/usb_descriptors.hpp"

using namespace bukifon;
using namespace bukifon::usb;

namespace {

struct WalkResult {
  int interfaces = 0;
  int endpoints = 0;
  int hidDescriptors = 0;
  std::set<uint8_t> endpointAddresses;
  std::set<uint8_t> interfaceClasses;
  uint16_t totalLength = 0;
  bool valid = true;
};

WalkResult walkConfig(const std::vector<uint8_t>& config) {
  WalkResult r;
  if (config.size() < kConfigDescriptorSize) {
    r.valid = false;
    return r;
  }
  r.totalLength = u16(config[2], config[3]);
  size_t pos = 0;
  while (pos + 2 <= config.size()) {
    const uint8_t length = config[pos];
    const uint8_t type = config[pos + 1];
    if (length < 2 || pos + length > config.size()) {
      r.valid = false;
      break;
    }
    if (type == 0x04 && length == kInterfaceDescriptorSize) {
      ++r.interfaces;
      r.interfaceClasses.insert(config[pos + 5]);
    } else if (type == 0x05 && length == kEndpointDescriptorSize) {
      ++r.endpoints;
      r.endpointAddresses.insert(config[pos + 2]);
    } else if (type == 0x21 && length == kHidDescriptorSize) {
      ++r.hidDescriptors;
    }
    pos += length;
  }
  if (pos != config.size()) r.valid = false;
  return r;
}

}  // namespace

TEST(UsbCompositeDescriptorBuild) {
  UsbCompositeBuilder builder;
  builder.setVidPid(0x1209, 0x0001);
  CHECK(builder.build());
  const UsbCompositeDescriptor& d = builder.descriptors();
  INFO("USB composite: device=%zu B, config=%zu B, interfaces=%u, endpoints=%u, HID report=%zu B",
       d.device.size(), d.config.size(), d.interfaceCount, d.endpointCount, d.hidReport.size());
  CHECK(d.device.size() == kDeviceDescriptorSize);
  CHECK(d.device[0] == kDeviceDescriptorSize && d.device[1] == 0x01);
  CHECK(u16(d.device[8], d.device[9]) == 0x1209);
  CHECK(u16(d.device[10], d.device[11]) == 0x0001);
  CHECK(d.config.size() >= kConfigDescriptorSize);
  CHECK(d.config[0] == kConfigDescriptorSize && d.config[1] == 0x02);
  CHECK(u16(d.config[2], d.config[3]) == d.config.size());
  CHECK(d.config[4] == d.interfaceCount);
  CHECK(d.hidReport.size() == 45);
  CHECK(d.hidReport.front() == 0x05 && d.hidReport[1] == 0x01);
  CHECK(d.hidReport.back() == 0xC0);
}

TEST(UsbCompositeDescriptorInterfacesAndEndpoints) {
  UsbCompositeBuilder builder;
  CHECK(builder.build());
  const UsbCompositeDescriptor& d = builder.descriptors();
  const WalkResult walk = walkConfig(d.config);
  CHECK(walk.valid);
  CHECK(walk.interfaces == d.interfaceCount);
  CHECK(walk.endpoints == d.endpointCount);
  CHECK(walk.hidDescriptors == 1);
  CHECK(walk.endpointAddresses.size() == d.endpointCount);  // all unique
  CHECK(walk.totalLength == d.config.size());
  CHECK(walk.interfaceClasses.count(0x03) == 1);  // HID
  CHECK(walk.interfaceClasses.count(0x01) == 1);  // audio (MIDI/UAC2)
  CHECK(walk.interfaceClasses.count(0x02) == 1);  // CDC
  INFO("USB walk: %d interfaces, %d endpoints, total length=%u, HID report descriptors=%d",
       walk.interfaces, walk.endpoints, walk.totalLength, walk.hidDescriptors);
}

TEST(UsbCompositeDescriptorVariants) {
  UsbCompositeBuilder minimal;
  minimal.includeHidKeyboard(true);
  minimal.includeMidi(false);
  minimal.includeUac2(false);
  minimal.includeCdc(false);
  CHECK(minimal.build());
  const UsbCompositeDescriptor& m = minimal.descriptors();
  const WalkResult minimalWalk = walkConfig(m.config);
  INFO("USB minimal: interfaces=%u endpoints=%u config=%zu B", m.interfaceCount, m.endpointCount,
       m.config.size());
  CHECK(m.interfaceCount == 1);
  CHECK(m.endpointCount == 1);
  CHECK(minimalWalk.valid);
  CHECK(minimalWalk.interfaces == 1);

  UsbCompositeBuilder full;
  CHECK(full.build());
  CHECK(full.descriptors().config.size() > m.config.size());

  UsbCompositeBuilder bidirectional;
  bidirectional.setVidPid(0xCAFE, 0x1234);
  bidirectional.setMaxPowerMa(500);
  CHECK(bidirectional.build());
  const UsbCompositeDescriptor& b = bidirectional.descriptors();
  CHECK(u16(b.device[8], b.device[9]) == 0xCAFE);
  CHECK(u16(b.device[10], b.device[11]) == 0x1234);
  CHECK(b.config[kConfigDescriptorSize - 1] == 250);  // bMaxPower in 2 mA units
  INFO("USB variants: minimal config=%zu B, full=%zu B, maxPower encoded", m.config.size(),
       b.config.size());
}

TEST(UsbHidReportDescriptorHelper) {
  uint8_t buffer[64] = {};
  CHECK(UsbCompositeBuilder::hidReportSize() == 45);
  const size_t size = UsbCompositeBuilder::hidKeyboardReportDescriptor(buffer, sizeof(buffer));
  CHECK(size == 45);
  CHECK(buffer[0] == 0x05 && buffer[1] == 0x01);   // usage page generic desktop
  CHECK(buffer[2] == 0x09 && buffer[3] == 0x06);   // usage keyboard
  CHECK(buffer[4] == 0xA1 && buffer[5] == 0x01);   // collection application
  CHECK(buffer[size - 1] == 0xC0);                 // end collection
  uint8_t tiny[8] = {};
  CHECK(UsbCompositeBuilder::hidKeyboardReportDescriptor(tiny, sizeof(tiny)) == 0);
  INFO("HID report descriptor: %zu bytes, 6KRO keyboard", size);
}
