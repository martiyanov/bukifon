// SPDX-License-Identifier: GPL-3.0-or-later
// Tests for the USB HS UAC2 8-in/8-out descriptor builder.
#include <cstdio>
#include <cstring>
#include <string>

#include "test_framework.hpp"
#include "usb/uac2_8x8.hpp"

using namespace bukifon::usb;

namespace {

struct EndpointInfo {
  uint8_t address = 0;
  uint8_t attributes = 0;
  uint16_t maxPacket = 0;
  uint8_t interval = 0;
};

int collectEndpoints(const Uac2DescriptorSet& set, EndpointInfo* out, int max) {
  int count = 0;
  const std::vector<uint8_t>& c = set.config;
  for (size_t i = 0; i + 1 < c.size();) {
    const uint8_t length = c[i];
    if (length == 0) break;
    if (c[i + 1] == 0x05 && count < max) {
      EndpointInfo& e = out[count++];
      e.address = c[i + 2];
      e.attributes = c[i + 3];
      e.maxPacket = static_cast<uint16_t>(c[i + 4] | (c[i + 5] << 8));
      e.interval = c[i + 6];
    }
    i += length;
  }
  return count;
}

int countInterfaces(const Uac2DescriptorSet& set) {
  // bNumInterfaces counts unique interface numbers; alt settings are extra
  // interface descriptors with the same bInterfaceNumber.
  bool seen[32] = {};
  const std::vector<uint8_t>& c = set.config;
  for (size_t i = 0; i + 1 < c.size();) {
    const uint8_t length = c[i];
    if (length == 0) break;
    if (c[i + 1] == 0x04 && c[i + 2] < 32) seen[c[i + 2]] = true;
    i += length;
  }
  int count = 0;
  for (bool flag : seen) {
    if (flag) ++count;
  }
  return count;
}

const EndpointInfo* findEndpoint(const EndpointInfo* endpoints, int count, uint8_t address) {
  for (int i = 0; i < count; ++i) {
    if (endpoints[i].address == address) return &endpoints[i];
  }
  return nullptr;
}

}  // namespace

TEST(Uac2MultichannelBuildsAndFitsBudget) {
  Uac2_8x8Builder builder;
  builder.setVidPid(0x1209, 0x0001);
  CHECK(builder.build());
  const Uac2DescriptorSet& d = builder.descriptors();
  CHECK(d.device.size() == 18);
  CHECK(d.device[0] == 18 && d.device[1] == 0x01);
  CHECK(d.device[2] == 0x00 && d.device[3] == 0x02);  // bcdUSB 2.00 (HS capable)
  CHECK(d.configTotalLength == d.config.size());
  CHECK(d.configTotalLength > 100 && d.configTotalLength < 512);
  CHECK(d.interfaces == 8);
  CHECK(d.endpoints == 9);
  CHECK(d.budget.isoData == 2);
  CHECK(d.budget.feedback == 1);
  CHECK(d.budget.midi == 2);
  CHECK(d.budget.cdc == 3);
  CHECK(d.budget.hid == 1);
  CHECK(d.budget.total() == 9);
  CHECK(d.budget.fits());
  INFO("UAC2 8x8 multichannel: %u bytes config, 8 interfaces, 9/15 endpoints",
       d.configTotalLength);
}

TEST(Uac2EndpointAddressesUnique) {
  Uac2_8x8Builder builder;
  CHECK(builder.build());
  EndpointInfo endpoints[32];
  const int count = collectEndpoints(builder.descriptors(), endpoints, 32);
  CHECK(count == 9);
  bool seen[256] = {};
  for (int i = 0; i < count; ++i) {
    CHECK(!seen[endpoints[i].address]);
    seen[endpoints[i].address] = true;
  }
  CHECK(seen[0x01] && seen[0x81]);  // ISO data OUT/IN
  CHECK(seen[0x82]);                // feedback
  CHECK(seen[0x02] && seen[0x83]);  // MIDI bulk
  CHECK(seen[0x84] && seen[0x03] && seen[0x85]);  // CDC notify + data
  CHECK(seen[0x86]);                // HID interrupt
  INFO("endpoint addresses: 9 unique (ISO 0x01/0x81, feedback 0x82, MIDI, CDC, HID)");
}

TEST(Uac2PerChannelBudgetFails) {
  Uac2_8x8Builder builder;
  const EndpointBudget multichannel = builder.analyzeBudget(Uac2EndpointMode::Multichannel, 8);
  CHECK(multichannel.fits());
  const EndpointBudget perChannel = builder.analyzeBudget(Uac2EndpointMode::PerChannel, 8);
  CHECK(perChannel.isoData == 16);
  CHECK(perChannel.total() == 23);
  CHECK(!perChannel.fits());
  CHECK(std::strstr(perChannel.note, "cannot coexist") != nullptr);
  CHECK(Uac2_8x8Builder::maxPerChannelChannelsForFit() == 4);
  const EndpointBudget four = builder.analyzeBudget(Uac2EndpointMode::PerChannel, 4);
  CHECK(four.isoData == 8 && four.total() == 15 && four.fits());
  const EndpointBudget five = builder.analyzeBudget(Uac2EndpointMode::PerChannel, 5);
  CHECK(!five.fits());
  INFO("budget: UAC2 aggregation=9/15 fits; per-channel 8ch=23/15 fails; <=4 channels fit");
}

TEST(Uac2ClockAndFormatDescriptors) {
  Uac2_8x8Builder builder;
  CHECK(builder.build());
  const std::vector<uint8_t>& c = builder.descriptors().config;
  bool clockFound = false;
  bool formatFound = false;
  bool asFound = false;
  for (size_t i = 0; i + 3 < c.size();) {
    const uint8_t length = c[i];
    if (length == 0) break;
    if (c[i + 1] == 0x24 && c[i + 2] == 0x0A && length == 8) {
      clockFound = true;
      CHECK(c[i + 3] == 1);       // bClockID
      CHECK((c[i + 4] & 0x03) == 0x03);  // internal fixed
    }
    if (c[i + 1] == 0x24 && c[i + 2] == 0x02 && length == 6) {
      formatFound = true;
      CHECK(c[i + 4] == 3);   // subslot 24 bit
      CHECK(c[i + 5] == 24);  // bit resolution
    }
    if (c[i + 1] == 0x24 && c[i + 2] == 0x01 && length == 16) {
      asFound = true;
      CHECK(c[i + 7] == 8);  // bNrChannels
    }
    i += length;
  }
  CHECK(clockFound && formatFound && asFound);
  CHECK(kUac2SampleRate == 48000);
  CHECK(kUac2Bits == 24);
  INFO("UAC2 clock source (internal 48 kHz), 24-bit format, 8-channel AS interfaces present");
}

TEST(Uac2FeedbackAndIsoPacketSizing) {
  Uac2_8x8Builder builder;
  CHECK(builder.build());
  EndpointInfo endpoints[32];
  const int count = collectEndpoints(builder.descriptors(), endpoints, 32);
  const EndpointInfo* feedback = findEndpoint(endpoints, count, 0x82);
  CHECK(feedback != nullptr);
  if (feedback) {
    CHECK(feedback->maxPacket == 4);
    CHECK(feedback->attributes == 0x01);
    CHECK(feedback->interval == 4);
  }
  const EndpointInfo* isoOut = findEndpoint(endpoints, count, 0x01);
  CHECK(isoOut != nullptr);
  if (isoOut) {
    CHECK(isoOut->maxPacket == kUac2IsoPacketBytes);
    CHECK(isoOut->maxPacket == 8 * 3 * 6);  // 8ch * 3B * 6 samples/microframe
  }
  CHECK(kUac2IsoPacketBytes == 144);
  INFO("8x8/24/48: ISO packet 144 B/microframe, feedback 4 B, interval 4");
}

TEST(Uac2DescriptorWalkConsistency) {
  Uac2_8x8Builder builder;
  CHECK(builder.build());
  const Uac2DescriptorSet& d = builder.descriptors();
  size_t offset = 0;
  while (offset < d.config.size()) {
    const uint8_t length = d.config[offset];
    CHECK(length >= 2);
    CHECK(offset + length <= d.config.size());
    offset += length;
  }
  CHECK(offset == d.config.size());
  CHECK(countInterfaces(d) == d.interfaces);
  CHECK(d.config[4] == d.interfaces);  // bNumInterfaces
  INFO("descriptor walk: %u bytes, %u interfaces, no zero/garbage lengths",
       d.configTotalLength, d.interfaces);
}

TEST(Uac2PerChannelDiagnosticBuild) {
  Uac2_8x8Builder builder;
  builder.setMode(Uac2EndpointMode::PerChannel);
  builder.setPerChannelChannels(8);
  CHECK(builder.build());
  const Uac2DescriptorSet& d = builder.descriptors();
  CHECK(!d.budget.fits());
  CHECK(d.mode == Uac2EndpointMode::PerChannel);
  EndpointInfo endpoints[32];
  const int count = collectEndpoints(d, endpoints, 32);
  CHECK(count == 17);  // 8 OUT + 8 IN + feedback
  INFO("per-channel diagnostic: %d endpoints built, budget honestly reported as FAIL", count);
}

TEST(Uac2JsonDump) {
  Uac2_8x8Builder builder;
  CHECK(builder.build());
  const std::string json = builder.toJson();
  CHECK(json.find("bukifon-usb-uac2-8x8-v1") != std::string::npos);
  CHECK(json.find("\"channels\": 8") != std::string::npos);
  CHECK(json.find("\"bits\": 24") != std::string::npos);
  CHECK(json.find("\"sample_rate\": 48000") != std::string::npos);
  CHECK(json.find("\"fits\": true") != std::string::npos);
  CHECK(json.find("\"endpoints\": 9") != std::string::npos);
  CHECK(json.find("\"device\": \"") != std::string::npos);
  CHECK(json.find("\"config\": \"") != std::string::npos);
  const char* path = "../tests/out/uac2_8x8.json";
  CHECK(builder.writeJson(path));
  std::FILE* file = std::fopen(path, "rb");
  CHECK(file != nullptr);
  if (file) {
    std::fseek(file, 0, SEEK_END);
    CHECK(std::ftell(file) > 200);
    std::fclose(file);
  }
  std::remove(path);
  INFO("JSON dump includes hex descriptor bytes for USB-analyser comparison");
}

TEST(Uac2HidMidiCdcPresent) {
  Uac2_8x8Builder builder;
  CHECK(builder.build());
  const std::vector<uint8_t>& c = builder.descriptors().config;
  bool hid = false;
  bool midi = false;
  bool cdc = false;
  for (size_t i = 0; i + 6 < c.size();) {
    const uint8_t length = c[i];
    if (length == 0) break;
    if (c[i + 1] == 0x04) {
      const uint8_t classCode = c[i + 5];
      if (classCode == 0x03) hid = true;
      if (classCode == 0x01 && c[i + 6] == 0x03) midi = true;
      if (classCode == 0x02) cdc = true;
    }
    i += length;
  }
  CHECK(hid && midi && cdc);
  CHECK(builder.descriptors().hidReport.size() == 45);
  INFO("HID keyboard + MIDI (MS subclass) + CDC interfaces included beside UAC2");
}
