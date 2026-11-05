// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "core/patch.hpp"
#include "modules/hw_module.hpp"
#include "modules/module.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

class FakeBus : public IBusIo {
 public:
  bool readModuleEeprom(int port, uint8_t address, uint8_t* data, size_t length) override {
    (void)address;
    auto it = eeprom.find(port);
    if (it == eeprom.end() || length > it->second.size()) return false;
    std::memcpy(data, it->second.data(), length);
    return true;
  }
  bool writeModuleI2c(int port, uint8_t address, const uint8_t* data, size_t length) override {
    writes.push_back({port, address, std::vector<uint8_t>(data, data + length)});
    return true;
  }
  bool portPresent(int port) override {
    return port >= 0 && port < 3 && present[port];
  }
  struct Write {
    int port;
    uint8_t address;
    std::vector<uint8_t> data;
  };
  bool present[3] = {true, false, true};
  std::map<int, std::vector<uint8_t>> eeprom;
  std::vector<Write> writes;
};

HwModuleDescriptor descriptorFor(const char* name, uint8_t transport) {
  HwModuleDescriptor d;
  d.transport = transport;
  d.kind = KindOscillator;
  d.params = 8;
  d.version = 1;
  std::strncpy(d.name, name, sizeof(d.name) - 1);
  d.name[15] = '\0';
  d.cvRoutes[0] = 1;
  d.cvRoutes[1] = 2;
  d.maxCurrentMa10 = 60;  // 600 mA in the descriptor unit
  return d;
}

}  // namespace

TEST(ModuleRegistryBuiltins) {
  registerBuiltinModules();
  ModuleRegistry& reg = ModuleRegistry::instance();
  INFO("module registry: %d built-in modules", reg.count());
  CHECK(reg.count() >= 6);
  CHECK(reg.info(0) != nullptr);
  bool found = false;
  for (int i = 0; i < reg.count(); ++i) {
    if (std::strcmp(reg.info(i)->name, "Soft Delay") == 0) found = true;
  }
  CHECK(found);
  IModule* fx = reg.createByName("Soft Delay");
  CHECK(fx != nullptr);
  CHECK(std::strcmp(fx->name(), "Soft Delay") == 0);
  float l[256] = {};
  float r[256] = {};
  fx->process(l, r, 256);
  bool finite = true;
  for (int i = 0; i < 256; ++i) {
    if (!std::isfinite(l[i]) || !std::isfinite(r[i])) finite = false;
  }
  CHECK(finite);
  delete fx;
  IModule* lfo = reg.createByName("Soft LFO");
  CHECK(lfo != nullptr);
  lfo->tick();
  delete lfo;
  CHECK(reg.createByName("No Such Module") == nullptr);
  CHECK(reg.create(999) == nullptr);
}

TEST(HwDescriptorParse) {
  const HwModuleDescriptor d = descriptorFor("VCO-1", 1);
  uint8_t raw[kHwDescriptorBytes] = {};
  CHECK(buildHwDescriptor(d, raw, sizeof(raw)) == kHwDescriptorBytes);
  HwModuleDescriptor parsed;
  CHECK(parseHwDescriptor(raw, sizeof(raw), &parsed));
  INFO("hw descriptor: name='%s' transport=%d kind=%d params=%d", parsed.name, parsed.transport,
       parsed.kind, parsed.params);
  CHECK(std::strcmp(parsed.name, "VCO-1") == 0);
  CHECK(parsed.transport == 1);
  CHECK(parsed.params == 8);
  CHECK(parsed.cvRoutes[0] == 1 && parsed.cvRoutes[1] == 2);
  CHECK(parsed.maxCurrentMa10 == 60);
  // Bad magic and bad CRC are rejected.
  uint8_t bad[kHwDescriptorBytes];
  std::memcpy(bad, raw, sizeof(bad));
  bad[0] = 'X';
  CHECK(!parseHwDescriptor(bad, sizeof(bad), &parsed));
  std::memcpy(bad, raw, sizeof(bad));
  bad[12] ^= 0x01;
  CHECK(!parseHwDescriptor(bad, sizeof(bad), &parsed));
  CHECK(!parseHwDescriptor(raw, 31, &parsed));
}

TEST(HwModuleManagerScanAndProxy) {
  FakeBus bus;
  bus.eeprom[0] = std::vector<uint8_t>(kHwDescriptorBytes);
  bus.eeprom[2] = std::vector<uint8_t>(kHwDescriptorBytes);
  buildHwDescriptor(descriptorFor("VCO-1", 1), bus.eeprom[0].data(), kHwDescriptorBytes);
  buildHwDescriptor(descriptorFor("LADDER-1", 0), bus.eeprom[2].data(), kHwDescriptorBytes);

  HwModuleManager manager;
  manager.init(&bus);
  manager.scan();
  INFO("hw bus scan: %d modules (port0=%d port1=%d port2=%d), port0 proxy name=%s",
       manager.count(), manager.present(0), manager.present(1), manager.present(2),
       manager.proxy(0) ? manager.proxy(0)->name() : "-");
  CHECK(manager.count() == 2);
  CHECK(manager.present(0));
  CHECK(!manager.present(1));
  CHECK(manager.present(2));
  CHECK(!manager.proxy(0)->passive());
  CHECK(manager.proxy(2)->passive());
  CHECK(std::strcmp(manager.proxy(0)->name(), "VCO-1") == 0);

  CHECK(manager.proxy(0)->setParam(3, 0.5f));
  CHECK(bus.writes.size() == 1);
  CHECK(bus.writes[0].port == 0);
  CHECK(bus.writes[0].address == 0x40);
  CHECK(bus.writes[0].data[0] == 0x13);  // SET_PARAM(3)
  CHECK(bus.writes[0].data[1] == 128);   // 0.5 -> 128
  CHECK(!manager.proxy(2)->setParam(0, 0.5f));  // analog module: passive

  // Hot-plug: port 1 appears with a valid descriptor.
  bus.present[1] = true;
  bus.eeprom[1] = std::vector<uint8_t>(kHwDescriptorBytes);
  buildHwDescriptor(descriptorFor("FX-1", 1), bus.eeprom[1].data(), kHwDescriptorBytes);
  bool presence[3] = {true, true, true};
  manager.poll(presence);
  INFO("hw hot-plug: modules=%d", manager.count());
  CHECK(manager.count() == 3);
  CHECK(manager.present(1));
  CHECK(std::strcmp(manager.proxy(1)->name(), "FX-1") == 0);
  // Removing a port clears it without affecting the others.
  presence[0] = false;
  manager.poll(presence);
  CHECK(!manager.present(0));
  CHECK(manager.present(1));
  CHECK(manager.present(2));
}
