// SPDX-License-Identifier: GPL-3.0-or-later
#include "usb/uac2_8x8.hpp"

#include <cstdio>
#include <cstring>

namespace bukifon {
namespace usb {
namespace {

void append(std::vector<uint8_t>& v, std::initializer_list<uint8_t> bytes) {
  v.insert(v.end(), bytes);
}

void appendInterface(std::vector<uint8_t>& v, uint8_t number, uint8_t alternate,
                     uint8_t endpoints, uint8_t classCode, uint8_t subclass, uint8_t protocol) {
  append(v, {9, 0x04, number, alternate, endpoints, classCode, subclass, protocol, 0});
}

void appendEndpoint(std::vector<uint8_t>& v, uint8_t address, uint8_t attributes,
                    uint16_t maxPacket, uint8_t interval) {
  append(v, {7, 0x05, address, attributes, static_cast<uint8_t>(maxPacket & 0xFF),
             static_cast<uint8_t>(maxPacket >> 8), interval});
}

void appendHex(std::string& out, const std::vector<uint8_t>& bytes) {
  char buffer[4];
  for (size_t i = 0; i < bytes.size(); ++i) {
    std::snprintf(buffer, sizeof(buffer), i == 0 ? "%02X" : " %02X", bytes[i]);
    out += buffer;
  }
}

}  // namespace

void Uac2_8x8Builder::setVidPid(uint16_t vid, uint16_t pid) {
  vid_ = vid;
  pid_ = pid;
}

EndpointBudget Uac2_8x8Builder::analyzeBudget(Uac2EndpointMode mode,
                                              int perChannelChannels) const {
  EndpointBudget b;
  b.midi = 2;
  b.cdc = 3;
  b.hid = 1;
  b.feedback = 1;
  b.limit = kUsbHsEndpointLimit;
  if (mode == Uac2EndpointMode::Multichannel) {
    b.isoData = 2;  // one ISO endpoint per direction, 8 channels inside
    b.note = "UAC2 multichannel: 2 ISO data + 1 feedback + MIDI 2 + CDC 3 + HID 1";
  } else {
    b.isoData = 2 * (perChannelChannels > 0 ? perChannelChannels : kUac2Channels);
    b.note = "per-channel ISO endpoints cannot coexist with MIDI+CDC+HID beyond 4 channels";
  }
  return b;
}

int Uac2_8x8Builder::maxPerChannelChannelsForFit() {
  // 15 = 2*N ISO + 1 feedback + 2 MIDI + 3 CDC + 1 HID  =>  N = 4.
  return (kUsbHsEndpointLimit - 1 - 2 - 3 - 1) / 2;
}

void Uac2_8x8Builder::appendDevice() {
  append(set_.device, {18, 0x01, 0x00, 0x02, 0xEF, 0x02, 0x01, 0x40,
                       static_cast<uint8_t>(vid_ & 0xFF), static_cast<uint8_t>(vid_ >> 8),
                       static_cast<uint8_t>(pid_ & 0xFF), static_cast<uint8_t>(pid_ >> 8),
                       0x00, 0x01, 0x01, 0x02, 0x03, 0x01});
}

void Uac2_8x8Builder::appendConfigHeader() {
  // wTotalLength at offset 2 is patched after all descriptors are appended.
  append(set_.config, {9, 0x02, 0x00, 0x00, 0x00, 1, 0, 0x80, 250});
}

void Uac2_8x8Builder::appendUac2Control() {
  const uint8_t controlInterface = nextInterface_++;
  appendInterface(set_.config, controlInterface, 0, 0, 0x01, 0x01, 0x20);
  // Clock source: internal fixed 48 kHz (bClockID=1, bmAttributes internal fixed,
  // no host control, no association).
  append(set_.config, {8, 0x24, 0x0A, 1, 0x03, 0, 0, 0});
  // Input terminal (USB streaming) -> feature not needed here.
  append(set_.config, {17, 0x24, 0x02, 2, 0x01, 0x01, 0, 1,
                       static_cast<uint8_t>(kUac2Channels), 0, 0, 0, 0, 0, 0, 0, 0});
  // Output terminal (speaker) connected to the input terminal.
  append(set_.config, {12, 0x24, 0x03, 3, 0x01, 0x03, 0, 2, 1, 0, 0, 0});
}

void Uac2_8x8Builder::appendUac2Streaming(uint8_t interfaceNumber, bool input,
                                           uint8_t endpoint) {
  // Alternate setting 0: no endpoints (zero-bandwidth).
  appendInterface(set_.config, interfaceNumber, 0, 0, 0x01, 0x02, 0x20);
  // Alternate setting 1: one ISO data endpoint (+ feedback for OUT).
  appendInterface(set_.config, interfaceNumber, 1, input ? 1 : 2, 0x01, 0x02, 0x20);
  // AS interface descriptor: terminal link, format type I, 8 channels.
  append(set_.config, {16, 0x24, 0x01, input ? static_cast<uint8_t>(3) : static_cast<uint8_t>(2),
                       0, 1, 1, static_cast<uint8_t>(kUac2Channels), 0, 0, 0, 0, 0, 0, 0, 0});
  // Format type I: 24-bit subslots.
  append(set_.config, {6, 0x24, 0x02, 0x01, kUac2BytesPerSample, kUac2Bits});
  // Isochronous data endpoint (async), packet = 8ch*3B*6 samples/microframe.
  appendEndpoint(set_.config, endpoint, 0x05, kUac2IsoPacketBytes, 1);
  // Class-specific endpoint descriptor.
  append(set_.config, {8, 0x25, 0x01, 0, 0, 0, 0, 0});
  if (!input) {
    // Explicit feedback endpoint for the asynchronous OUT stream.
    appendEndpoint(set_.config, 0x82, 0x01, 4, 4);
  }
}

void Uac2_8x8Builder::appendMidi(uint8_t firstInterface) {
  appendInterface(set_.config, firstInterface, 0, 0, 0x01, 0x01, 0x00);
  append(set_.config, {7, 0x24, 0x01, 0x00, 0x01, 0x01, 0x00});  // MS AC header
  appendInterface(set_.config, firstInterface + 1, 0, 2, 0x01, 0x03, 0x00);
  append(set_.config, {6, 0x24, 0x01, 0x00, 0x01, 0x00});       // MS header
  appendEndpoint(set_.config, 0x02, 0x02, 64, 0);                 // bulk OUT
  appendEndpoint(set_.config, 0x83, 0x02, 64, 0);                 // bulk IN
}

void Uac2_8x8Builder::appendHid(uint8_t interfaceNumber) {
  appendInterface(set_.config, interfaceNumber, 0, 1, 0x03, 0x01, 0x01);
  append(set_.config, {9, 0x21, 0x11, 0x01, 0x00, 0x01, 0x22, 45, 0x00});
  appendEndpoint(set_.config, 0x86, 0x03, 8, 10);
}

void Uac2_8x8Builder::appendCdc(uint8_t firstInterface) {
  appendInterface(set_.config, firstInterface, 0, 1, 0x02, 0x02, 0x01);
  append(set_.config, {5, 0x24, 0x00, 0x10, 0x01});              // header
  append(set_.config, {5, 0x24, 0x01, 0x00, 0x01});              // call mgmt
  append(set_.config, {4, 0x24, 0x02, 0x02});                    // ACM
  append(set_.config, {5, 0x24, 0x06, 0x00, 0x01});              // union
  appendEndpoint(set_.config, 0x84, 0x03, 16, 10);               // notify IN
  appendInterface(set_.config, firstInterface + 1, 0, 2, 0x0A, 0x00, 0x00);
  appendEndpoint(set_.config, 0x03, 0x02, 64, 0);                 // data OUT
  appendEndpoint(set_.config, 0x85, 0x02, 64, 0);                 // data IN
}

void Uac2_8x8Builder::appendUac2PerChannelEndpoints() {
  // Diagnostic layout: one ISO endpoint per channel.  Budget analysis reports
  // that this cannot coexist with MIDI/CDC/HID on a 15-address HS device.
  const uint8_t channels = static_cast<uint8_t>(perChannelChannels_);
  const uint8_t outInterface = nextInterface_++;
  appendInterface(set_.config, outInterface, 0, 0, 0x01, 0x02, 0x20);
  appendInterface(set_.config, outInterface, 1, channels, 0x01, 0x02, 0x20);
  for (uint8_t ch = 0; ch < channels; ++ch) {
    appendEndpoint(set_.config, static_cast<uint8_t>(0x01 + ch), 0x05, 18, 1);
  }
  const uint8_t inInterface = nextInterface_++;
  appendInterface(set_.config, inInterface, 0, 0, 0x01, 0x02, 0x20);
  appendInterface(set_.config, inInterface, 1, static_cast<uint8_t>(channels + 1), 0x01, 0x02,
                  0x20);
  for (uint8_t ch = 0; ch < channels; ++ch) {
    appendEndpoint(set_.config, static_cast<uint8_t>(0x81 + ch), 0x05, 18, 1);
  }
  appendEndpoint(set_.config, static_cast<uint8_t>(0x80 + channels + 1), 0x01, 4, 4);  // feedback
}

void Uac2_8x8Builder::patchTotalLength() {
  const uint16_t total = static_cast<uint16_t>(set_.config.size());
  set_.config[2] = static_cast<uint8_t>(total & 0xFF);
  set_.config[3] = static_cast<uint8_t>(total >> 8);
  set_.configTotalLength = total;
}

bool Uac2_8x8Builder::build() {
  set_ = Uac2DescriptorSet{};
  set_.mode = mode_;
  set_.budget = analyzeBudget(mode_, perChannelChannels_);
  set_.hidReport.resize(45);
  // Reuse the existing 6KRO report descriptor bytes.
  static const uint8_t kHidReport[45] = {
      0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25,
      0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01, 0x75, 0x08, 0x81, 0x01, 0x95, 0x06,
      0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xC0};
  std::memcpy(set_.hidReport.data(), kHidReport, sizeof(kHidReport));

  appendDevice();
  nextInterface_ = 0;
  endpointNumber_ = 1;
  appendConfigHeader();
  if (mode_ == Uac2EndpointMode::PerChannel) {
    appendUac2Control();
    appendUac2PerChannelEndpoints();
  } else {
    appendUac2Control();
    appendUac2Streaming(nextInterface_++, false, 0x01);   // OUT
    appendUac2Streaming(nextInterface_++, true, 0x81);    // IN
    appendMidi(nextInterface_);
    nextInterface_ += 2;
    appendHid(nextInterface_++);
    appendCdc(nextInterface_);
    nextInterface_ += 2;
  }
  set_.config[4] = nextInterface_;  // bNumInterfaces
  set_.interfaces = nextInterface_;
  // Count endpoints by walking the configuration descriptor.
  uint8_t endpoints = 0;
  for (size_t i = 0; i + 1 < set_.config.size();) {
    const uint8_t length = set_.config[i];
    if (length == 0) break;
    if (set_.config[i + 1] == 0x05) ++endpoints;
    i += length;
  }
  set_.endpoints = endpoints;
  patchTotalLength();
  return true;
}

std::string Uac2_8x8Builder::toJson() const {
  std::string out;
  char buffer[256];
  out += "{\n  \"schema\": \"bukifon-usb-uac2-8x8-v1\",\n";
  std::snprintf(buffer, sizeof(buffer),
                "  \"mode\": \"%s\",\n  \"channels\": %d,\n  \"bits\": %d,\n"
                "  \"sample_rate\": %u,\n  \"bytes_per_sample\": %d,\n"
                "  \"iso_packet_bytes\": %u,\n",
                mode_ == Uac2EndpointMode::Multichannel ? "multichannel" : "per-channel",
                kUac2Channels, kUac2Bits, kUac2SampleRate, kUac2BytesPerSample,
                kUac2IsoPacketBytes);
  out += buffer;
  std::snprintf(buffer, sizeof(buffer),
                "  \"budget\": {\"iso_data\": %d, \"feedback\": %d, \"midi\": %d, \"cdc\": %d, "
                "\"hid\": %d, \"total\": %d, \"limit\": %d, \"fits\": %s},\n",
                set_.budget.isoData, set_.budget.feedback, set_.budget.midi, set_.budget.cdc,
                set_.budget.hid, set_.budget.total(), set_.budget.limit,
                set_.budget.fits() ? "true" : "false");
  out += buffer;
  std::snprintf(buffer, sizeof(buffer),
                "  \"config_total_length\": %u,\n  \"interfaces\": %u,\n  \"endpoints\": %u,\n",
                set_.configTotalLength, set_.interfaces, set_.endpoints);
  out += buffer;
  out += "  \"device\": \"";
  appendHex(out, set_.device);
  out += "\",\n  \"config\": \"";
  appendHex(out, set_.config);
  out += "\"\n}\n";
  return out;
}

bool Uac2_8x8Builder::writeJson(const char* path) const {
  if (!path) return false;
  const std::string json = toJson();
  std::FILE* file = std::fopen(path, "wb");
  if (!file) return false;
  const bool ok = std::fwrite(json.data(), 1, json.size(), file) == json.size();
  std::fclose(file);
  return ok;
}

}  // namespace usb
}  // namespace bukifon
