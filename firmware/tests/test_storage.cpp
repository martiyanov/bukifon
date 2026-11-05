// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "core/patch.hpp"
#include "modules/hw_module.hpp"
#include "storage/eeprom.hpp"
#include "storage/preset_store.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

class FakeFileSystem : public IFileSystem {
 public:
  bool writeFile(const char* path, const uint8_t* data, size_t length) override {
    files[path] = std::vector<uint8_t>(data, data + length);
    return true;
  }
  bool readFile(const char* path, uint8_t* data, size_t maxLength, size_t* outLength) override {
    auto it = files.find(path);
    if (it == files.end() || it->second.size() > maxLength) return false;
    std::memcpy(data, it->second.data(), it->second.size());
    *outLength = it->second.size();
    return true;
  }
  bool exists(const char* path) override { return files.count(path) != 0; }
  bool remove(const char* path) override { return files.erase(path) != 0; }
  std::map<std::string, std::vector<uint8_t>> files;
};

class FakeEeprom : public IEeprom {
 public:
  FakeEeprom() : data_(4096, 0) {}
  bool read(uint16_t address, uint8_t* data, size_t length) override {
    if (address + length > data_.size()) return false;
    std::memcpy(data, data_.data() + address, length);
    return true;
  }
  bool write(uint16_t address, const uint8_t* data, size_t length) override {
    if (address + length > data_.size()) return false;
    std::memcpy(data_.data() + address, data, length);
    return true;
  }
  std::vector<uint8_t> data_;
};

}  // namespace

TEST(PresetStoreSaveLoad) {
  FakeFileSystem fs;
  PresetStore store;
  store.init(&fs);
  Patch patch;
  makeFactoryPatch(4, &patch);
  patch.name[0] = 'T';
  CHECK(store.save(10, patch));
  CHECK(store.exists(10));
  Patch loaded;
  CHECK(store.load(10, &loaded));
  INFO("preset store: saved/loaded patch '%s' (%zu file bytes)", loaded.name,
       fs.files.begin()->second.size());
  CHECK(std::strncmp(patch.name, loaded.name, 15) == 0);
  CHECK(std::fabs(loaded.global.v[Bpm] - patch.global.v[Bpm]) < 2.0f);
  CHECK(store.cached(10) != nullptr);
  CHECK(store.load(11, &loaded) == false);  // nothing stored there
  CHECK(store.erase(10));
  CHECK(!store.exists(10));
}

TEST(PresetStoreFactoryBank) {
  FakeFileSystem fs;
  PresetStore store;
  store.init(&fs);
  store.loadFactoryBank();
  INFO("preset store: factory bank cached %d patches", store.cachedCount());
  CHECK(store.cachedCount() == kNumFactoryPatches);
  const Patch* p = store.cached(0);
  CHECK(p != nullptr);
  CHECK(p->version == 1);
  char path[32];
  PresetStore::presetPath(3, path, sizeof(path));
  INFO("preset path example: %s", path);
  CHECK(std::strcmp(path, "/presets/03.pmp") == 0);
}

TEST(EepromStoreRoundtrip) {
  FakeEeprom eeprom;
  EepromStore store;
  store.init(&eeprom);
  store.cvCalibration().setPoint(1, 0, 0.0f, 5);
  store.cvCalibration().setPoint(1, 3, 10.0f, 4090);
  store.setDeckCalibration(0.28f, 3.05f);
  uint8_t descriptor[kHwDescriptorBytes] = {};
  const size_t n = buildHwDescriptor(HwModuleDescriptor{}, descriptor, sizeof(descriptor));
  CHECK(n == kHwDescriptorBytes);
  store.setModuleDescriptor(2, descriptor);
  store.addHours(1234);
  CHECK(store.save());

  EepromStore restored;
  restored.init(&eeprom);
  CHECK(restored.load());
  CHECK(restored.ok());
  uint8_t imageCheck[EepromStore::kImageBytes] = {};
  INFO("EEPROM store: deck cal pad=%.2f V keys=%.2f V, hours=%u, image=%zu bytes",
       restored.deckPadVolts(), restored.deckKeysVolts(), restored.hours(),
       store.serialize(imageCheck, sizeof(imageCheck)));
  CHECK(std::fabs(restored.deckPadVolts() - 0.28f) < 0.001f);
  CHECK(std::fabs(restored.deckKeysVolts() - 3.05f) < 0.001f);
  CHECK(restored.hours() == 1234u);
  CHECK(restored.moduleDescriptor(2) != nullptr);
  CHECK(restored.cvCalibration().codeForVolts(1, 10.0f) == 4090);
  // CRC corruption must be detected.
  eeprom.data_[20] ^= 0xFF;
  EepromStore broken;
  broken.init(&eeprom);
  CHECK(!broken.load());
  CHECK(!broken.ok());
}

TEST(EepromImageSize) {
  EepromStore store;
  uint8_t image[EepromStore::kImageBytes] = {};
  const size_t length = store.serialize(image, sizeof(image));
  INFO("EEPROM image: %zu bytes (CRC protected, fits 24C32 4096 bytes)", length);
  CHECK(length > 0);
  CHECK(length <= EepromStore::kImageBytes);
  EepromStore restored;
  CHECK(restored.deserialize(image, length));
}
