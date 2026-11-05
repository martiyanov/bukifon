// SPDX-License-Identifier: GPL-3.0-or-later
// Hardware ("smart") module support: 32-byte I2C EEPROM descriptor, hot-plug
// scanning of the 3 bus ports and the HwModuleProxy wrapper.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "modules/module.hpp"

namespace bukifon {

struct HwModuleDescriptor {
  uint8_t magic[4] = {'P', 'M', 'O', 'D'};
  uint8_t transport = 0;  // 0 = analog, 1 = I2C controlled, 2 = SPI
  uint8_t kind = KindCustom;
  uint8_t params = 0;
  uint8_t version = 1;
  char name[16] = {};
  uint8_t cvRoutes[4] = {};  // 0 = none, 1..4 = CV1..CV4 into the module
  uint16_t maxCurrentMa10 = 0;
};

constexpr size_t kHwDescriptorBytes = 32;

// Serialise/parse the 32-byte descriptor (CRC16-CCITT at bytes 30..31).
size_t buildHwDescriptor(const HwModuleDescriptor& descriptor, uint8_t* out, size_t capacity);
bool parseHwDescriptor(const uint8_t* raw, size_t length, HwModuleDescriptor* out);

// Bus abstraction: EEPROM read at 0x50 + port, I2C SET_PARAM writes, hot-plug.
class IBusIo {
 public:
  virtual ~IBusIo() = default;
  virtual bool readModuleEeprom(int port, uint8_t address, uint8_t* data, size_t length) = 0;
  virtual bool writeModuleI2c(int port, uint8_t address, const uint8_t* data, size_t length) = 0;
  virtual bool portPresent(int port) = 0;
};

class HwModuleProxy : public IModule {
 public:
  HwModuleProxy() = default;
  HwModuleProxy(int port, const HwModuleDescriptor& descriptor, IBusIo* bus)
      : port_(port), descriptor_(descriptor), bus_(bus) {}

  const char* name() const override { return descriptor_.name; }
  void process(float* l, float* r, size_t n) override {
    (void)l;
    (void)r;
    (void)n;
  }
  void tick() override {}
  // I2C transport only: SET_PARAM(index, value).
  bool setParam(int index, float value);
  int port() const { return port_; }
  const HwModuleDescriptor& descriptor() const { return descriptor_; }
  bool passive() const { return descriptor_.transport == 0; }
  int cvInputForChannel(int channel) const {
    return (channel >= 0 && channel < 4) ? descriptor_.cvRoutes[channel] : 0;
  }

 private:
  int port_ = 0;
  HwModuleDescriptor descriptor_{};
  IBusIo* bus_ = nullptr;
};

// Scans all three bus ports; a missing/invalid EEPROM marks the port empty and
// never blocks the audio path.
class HwModuleManager {
 public:
  static constexpr int kPorts = kNumBusPorts;
  void init(IBusIo* bus) { bus_ = bus; }
  void scan();  // start-up scan
  void poll(bool portPresence[kPorts]);  // hot-plug monitoring (GP21/22)
  bool present(int port) const;
  const HwModuleDescriptor* descriptor(int port) const;
  HwModuleProxy* proxy(int port);
  int count() const;

 private:
  IBusIo* bus_ = nullptr;
  bool present_[kPorts] = {};
  HwModuleDescriptor descriptors_[kPorts] = {};
  HwModuleProxy proxies_[kPorts] = {};
};

}  // namespace bukifon
