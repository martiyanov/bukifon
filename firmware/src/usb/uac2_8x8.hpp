// SPDX-License-Identifier: GPL-3.0-or-later
// USB HS UAC2 8-in/8-out descriptor builder (P4 first SKU).
//
// Pure C++ (no TinyUSB), testable on the host.  USB 2.0 HS has 16 endpoint
// addresses (EP0 + 15); UAC2 carries 8 channels in ONE isochronous endpoint per
// direction, so 8x8 uses 2 ISO endpoints + 1 feedback endpoint, leaving room for
// MIDI (2), CDC (3) and HID (1): 9 endpoints total.  A per-channel endpoint
// layout (16 ISO + feedback) cannot fit and is reported as a hard failure with
// the required mitigation (channel aggregation, or <=4 channels per-channel).
//
// 24 bit / 48 kHz, asynchronous OUT with explicit feedback; clock source is
// internal fixed 48 kHz (UAC2 clock descriptor).  Descriptor bytes are handed to
// esp_tinyusb on P4 (device glue TODO(hw)); JSON dump feeds the USB analyser.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace bukifon {
namespace usb {

constexpr int kUac2Channels = 8;
constexpr int kUac2Bits = 24;
constexpr uint32_t kUac2SampleRate = 48000;
constexpr int kUac2BytesPerSample = kUac2Bits / 8;
constexpr int kUsbHsEndpointLimit = 15;  // EP0 + 15 addresses
constexpr uint16_t kUac2IsoPacketBytes =
    static_cast<uint16_t>(kUac2Channels * kUac2BytesPerSample * 6);  // 6 samples/microframe @48k

enum class Uac2EndpointMode : uint8_t {
  Multichannel = 0,    // one ISO endpoint per direction (UAC2 standard) — fits
  PerChannel = 1       // one ISO endpoint per channel — diagnostic/negative
};

struct EndpointBudget {
  int isoData = 0;
  int feedback = 0;
  int midi = 0;
  int cdc = 0;
  int hid = 0;
  int total() const { return isoData + feedback + midi + cdc + hid; }
  int limit = kUsbHsEndpointLimit;
  bool fits() const { return total() <= limit; }
  const char* note = "";
};

struct Uac2DescriptorSet {
  std::vector<uint8_t> device;      // 18-byte device descriptor
  std::vector<uint8_t> config;      // full configuration descriptor
  std::vector<uint8_t> hidReport;   // 6KRO report descriptor (45 bytes)
  uint16_t configTotalLength = 0;   // wTotalLength as encoded
  uint8_t interfaces = 0;
  uint8_t endpoints = 0;
  Uac2EndpointMode mode = Uac2EndpointMode::Multichannel;
  EndpointBudget budget;
};

class Uac2_8x8Builder {
 public:
  void setVidPid(uint16_t vid, uint16_t pid);
  void setMode(Uac2EndpointMode mode) { mode_ = mode; }
  void setPerChannelChannels(int channels) { perChannelChannels_ = channels; }
  int perChannelChannels() const { return perChannelChannels_; }
  Uac2EndpointMode mode() const { return mode_; }

  bool build();
  const Uac2DescriptorSet& descriptors() const { return set_; }

  // Endpoint-budget analysis (multichannel: 9 endpoints; per-channel: 2N+7).
  EndpointBudget analyzeBudget(Uac2EndpointMode mode, int perChannelChannels) const;
  static int maxPerChannelChannelsForFit();  // 4 with MIDI+CDC+HID present

  // JSON dump for the USB analyser / artifacts.
  std::string toJson() const;
  bool writeJson(const char* path) const;

 private:
  void appendDevice();
  void appendConfigHeader();
  void appendUac2Control();
  void appendUac2Streaming(uint8_t interfaceNumber, bool input, uint8_t endpoint);
  void appendMidi(uint8_t firstInterface);
  void appendHid(uint8_t interfaceNumber);
  void appendCdc(uint8_t firstInterface);
  void appendUac2PerChannelEndpoints();
  void patchTotalLength();

  uint16_t vid_ = 0x2E8A;
  uint16_t pid_ = 0x000B;
  Uac2EndpointMode mode_ = Uac2EndpointMode::Multichannel;
  int perChannelChannels_ = kUac2Channels;
  Uac2DescriptorSet set_;
  uint8_t nextInterface_ = 0;
  uint8_t endpointNumber_ = 1;
};

}  // namespace usb
}  // namespace bukifon
