// SPDX-License-Identifier: GPL-3.0-or-later
#include "modules/hw_module.hpp"

#include <cstring>

#include "core/patch.hpp"

namespace bukifon {

size_t buildHwDescriptor(const HwModuleDescriptor& descriptor, uint8_t* out, size_t capacity) {
  if (!out || capacity < kHwDescriptorBytes) return 0;
  std::memset(out, 0, kHwDescriptorBytes);
  std::memcpy(out, descriptor.magic, 4);
  out[4] = descriptor.transport;
  out[5] = descriptor.kind;
  out[6] = descriptor.params;
  out[7] = descriptor.version;
  std::memcpy(out + 8, descriptor.name, 16);
  std::memcpy(out + 24, descriptor.cvRoutes, 4);
  out[28] = static_cast<uint8_t>(descriptor.maxCurrentMa10 & 0xFF);
  out[29] = static_cast<uint8_t>((descriptor.maxCurrentMa10 >> 8) & 0xFF);
  const uint16_t crc = crc16Ccitt(out, 30);
  out[30] = static_cast<uint8_t>(crc & 0xFF);
  out[31] = static_cast<uint8_t>((crc >> 8) & 0xFF);
  return kHwDescriptorBytes;
}

bool parseHwDescriptor(const uint8_t* raw, size_t length, HwModuleDescriptor* out) {
  if (!raw || !out || length < kHwDescriptorBytes) return false;
  if (std::memcmp(raw, "PMOD", 4) != 0) return false;
  const uint16_t stored = static_cast<uint16_t>(raw[30]) | (static_cast<uint16_t>(raw[31]) << 8);
  if (crc16Ccitt(raw, 30) != stored) return false;
  HwModuleDescriptor d;
  std::memcpy(d.magic, raw, 4);
  d.transport = raw[4];
  d.kind = raw[5];
  d.params = raw[6];
  d.version = raw[7];
  std::memcpy(d.name, raw + 8, 16);
  d.name[15] = '\0';
  std::memcpy(d.cvRoutes, raw + 24, 4);
  d.maxCurrentMa10 = static_cast<uint16_t>(raw[28] | (raw[29] << 8));
  if (d.params > 16) return false;
  *out = d;
  return true;
}

bool HwModuleProxy::setParam(int index, float value) {
  if (descriptor_.transport != 1 || !bus_) return false;
  if (index < 0 || index >= 16) return false;
  const uint8_t msg[4] = {static_cast<uint8_t>(0x10 + index),  // SET_PARAM opcode + index
                          static_cast<uint8_t>(value <= 0.0f
                                                   ? 0
                                                   : (value >= 1.0f
                                                          ? 255
                                                          : static_cast<int>(value * 255.0f + 0.5f))),
                          0, 0};
  const uint8_t address = static_cast<uint8_t>(0x40 + port_);
  return bus_->writeModuleI2c(port_, address, msg, 2);
}

void HwModuleManager::scan() {
  for (int port = 0; port < kPorts; ++port) present_[port] = false;
  if (!bus_) return;
  for (int port = 0; port < kPorts; ++port) {
    if (!bus_->portPresent(port)) continue;
    uint8_t raw[kHwDescriptorBytes] = {};
    const uint8_t address = static_cast<uint8_t>(0x50 + port);
    if (!bus_->readModuleEeprom(port, address, raw, sizeof(raw))) continue;
    HwModuleDescriptor d;
    if (!parseHwDescriptor(raw, sizeof(raw), &d)) continue;
    descriptors_[port] = d;
    proxies_[port] = HwModuleProxy(port, d, bus_);
    present_[port] = true;
  }
}

void HwModuleManager::poll(bool portPresence[kPorts]) {
  for (int port = 0; port < kPorts; ++port) {
    const bool presence = portPresence[port];
    if (!presence) {
      present_[port] = false;
      continue;
    }
    if (!present_[port] && bus_) {
      uint8_t raw[kHwDescriptorBytes] = {};
      const uint8_t address = static_cast<uint8_t>(0x50 + port);
      if (bus_->readModuleEeprom(port, address, raw, sizeof(raw))) {
        HwModuleDescriptor d;
        if (parseHwDescriptor(raw, sizeof(raw), &d)) {
          descriptors_[port] = d;
          proxies_[port] = HwModuleProxy(port, d, bus_);
          present_[port] = true;
        }
      }
    }
  }
}

bool HwModuleManager::present(int port) const {
  if (port < 0 || port >= kPorts) return false;
  return present_[port];
}

const HwModuleDescriptor* HwModuleManager::descriptor(int port) const {
  if (port < 0 || port >= kPorts || !present_[port]) return nullptr;
  return &descriptors_[port];
}

HwModuleProxy* HwModuleManager::proxy(int port) {
  if (port < 0 || port >= kPorts || !present_[port]) return nullptr;
  return &proxies_[port];
}

int HwModuleManager::count() const {
  int n = 0;
  for (int port = 0; port < kPorts; ++port) n += present_[port] ? 1 : 0;
  return n;
}

}  // namespace bukifon
