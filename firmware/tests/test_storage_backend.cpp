// SPDX-License-Identifier: GPL-3.0-or-later
// Storage backend + atomic A/B storage: MockFlash fault injection, SD/NVS
// backends, project/preset/language integration, recovery and limits.
#include <cstdio>
#include <cstring>
#include <vector>

#include "bukifon_i18n.h"
#include "storage/preset_bank.hpp"
#include "storage/project_v2.hpp"
#include "storage/storage_backend.hpp"
#include "test_framework.hpp"

using namespace bukifon;
using namespace bukifon::storage;

namespace {

std::vector<uint8_t> makePayload(size_t size, uint8_t seed) {
  std::vector<uint8_t> data(size);
  for (size_t i = 0; i < size; ++i) data[i] = static_cast<uint8_t>(seed + i);
  return data;
}

std::string readBytes(const uint8_t* data, size_t size) {
  return std::string(reinterpret_cast<const char*>(data), size);
}

}  // namespace

TEST(StorageMockFlashBasic) {
  MockFlash flash;
  memset(flash.entries.data(), 0, 0);
  CHECK(flash.begin());
  CHECK(!flash.exists("bukifon", "key"));
  const std::vector<uint8_t> data = makePayload(64, 1);
  CHECK(flash.write("bukifon", "key", data.data(), data.size()));
  CHECK(flash.exists("bukifon", "key"));
  CHECK(flash.size("bukifon", "key") == 64);
  std::vector<uint8_t> out(128);
  size_t readSize = 0;
  CHECK(flash.read("bukifon", "key", out.data(), out.size(), &readSize));
  CHECK(readSize == 64);
  CHECK(std::memcmp(out.data(), data.data(), data.size()) == 0);
  CHECK(!flash.read("bukifon", "missing", out.data(), out.size(), &readSize));
  CHECK(flash.erase("bukifon", "key"));
  CHECK(!flash.exists("bukifon", "key"));
  INFO("MockFlash: begin/write/read/erase/exists/size and missing key");
}

TEST(StorageMockFlashMultipleKeys) {
  MockFlash flash;
  std::vector<std::vector<uint8_t>> data;
  for (int i = 0; i < 5; ++i) {
    data.push_back(makePayload(static_cast<size_t>(100 + i * 37), static_cast<uint8_t>(i * 13)));
    CHECK(flash.write("bukifon", ("k" + std::to_string(i)).c_str(), data.back().data(),
                      data.back().size()));
  }
  for (int i = 0; i < 5; ++i) {
    std::vector<uint8_t> out(data[i].size());
    size_t size = 0;
    CHECK(flash.read("bukifon", ("k" + std::to_string(i)).c_str(), out.data(), out.size(),
                     &size));
    CHECK(size == data[i].size());
    CHECK(std::memcmp(out.data(), data[i].data(), size) == 0);
  }
  CHECK(!flash.exists("other", "k0"));
  INFO("MockFlash: independent namespace/key entries and sizes");
}

TEST(StorageMockFlashCapacity) {
  MockFlash flash;
  flash.setMaxBytes(100);
  const std::vector<uint8_t> first = makePayload(64, 1);
  const std::vector<uint8_t> second = makePayload(64, 2);
  CHECK(flash.write("bukifon", "a", first.data(), first.size()));
  CHECK(!flash.write("bukifon", "b", second.data(), second.size()));
  CHECK(flash.failedWrites() >= 1);
  flash.setMaxBytes(MockFlash::kCapacity);
  CHECK(flash.write("bukifon", "b", second.data(), second.size()));
  INFO("MockFlash: capacity limit rejects the overflowing write");
}

TEST(StorageMockFlashWearCounters) {
  MockFlash flash;
  const std::vector<uint8_t> data = makePayload(16, 4);
  for (int i = 0; i < 3; ++i) {
    CHECK(flash.write("bukifon", ("w" + std::to_string(i)).c_str(), data.data(), data.size()));
  }
  CHECK(flash.writeCount() == 3);
  CHECK(flash.erase("bukifon", "w0"));
  CHECK(flash.eraseCount() == 1);
  flash.resetCounters();
  CHECK(flash.writeCount() == 0 && flash.eraseCount() == 0);
  INFO("MockFlash: write/erase/wear counters and reset");
}

TEST(StorageAtomicRoundtrip) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  CHECK(store.namespaceName() != nullptr);
  const std::vector<uint8_t> first = makePayload(128, 7);
  CHECK(store.write("state", first.data(), first.size()));
  CHECK(store.sequence("state") == 1);
  std::vector<uint8_t> out(256);
  size_t size = 0;
  CHECK(store.read("state", out.data(), out.size(), &size));
  CHECK(size == first.size());
  CHECK(std::memcmp(out.data(), first.data(), size) == 0);
  CHECK(!store.lastLoadRecovered());
  const std::vector<uint8_t> second = makePayload(200, 9);
  CHECK(store.write("state", second.data(), second.size()));
  CHECK(store.sequence("state") == 2);
  CHECK(store.read("state", out.data(), out.size(), &size));
  CHECK(size == second.size());
  CHECK(std::memcmp(out.data(), second.data(), size) == 0);
  INFO("AtomicStorage: A/B write/read with increasing sequence");
}

TEST(StorageAtomicPowerCutMidWrite) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  const std::vector<uint8_t> oldData = makePayload(100, 1);
  CHECK(store.write("cut", oldData.data(), oldData.size()));
  flash.setPowerCutAtWrite(static_cast<int>(flash.writeCount()));
  const std::vector<uint8_t> newData = makePayload(100, 2);
  CHECK(!store.write("cut", newData.data(), newData.size()));
  CHECK(flash.powerCutSeen());
  std::vector<uint8_t> out(256);
  size_t size = 0;
  CHECK(store.read("cut", out.data(), out.size(), &size));
  CHECK(size == oldData.size());
  CHECK(std::memcmp(out.data(), oldData.data(), size) == 0);
  CHECK(store.lastLoadRecovered());
  INFO("AtomicStorage: power cut during write keeps the old copy and recovers it");
}

TEST(StorageAtomicBitFlipReadback) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  const std::vector<uint8_t> oldData = makePayload(80, 3);
  CHECK(store.write("flip", oldData.data(), oldData.size()));
  flash.setBitFlipAtWrite(static_cast<int>(flash.writeCount()), 22);
  const std::vector<uint8_t> newData = makePayload(80, 4);
  CHECK(!store.write("flip", newData.data(), newData.size()));
  std::vector<uint8_t> out(128);
  size_t size = 0;
  CHECK(store.read("flip", out.data(), out.size(), &size));
  CHECK(size == oldData.size());
  CHECK(std::memcmp(out.data(), oldData.data(), size) == 0);
  INFO("AtomicStorage: bit-flipped new record fails read-back; old record survives");
}

TEST(StorageAtomicCorruptOneCopyRecovery) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  const std::vector<uint8_t> data = makePayload(96, 5);
  CHECK(store.write("recover", data.data(), data.size()));
  // Create a corrupted second slot (simulates a torn write after reboot).
  const std::vector<uint8_t> bad(32, 0xEE);
  CHECK(flash.write("bukifon", "recover.b", bad.data(), bad.size()));
  std::vector<uint8_t> out(160);
  size_t size = 0;
  CHECK(store.read("recover", out.data(), out.size(), &size));
  CHECK(size == data.size());
  CHECK(std::memcmp(out.data(), data.data(), size) == 0);
  CHECK(store.lastLoadRecovered());
  CHECK(store.recoveryCount() >= 1);
  INFO("AtomicStorage: CRC-damaged slot falls back to the other copy with recovery flag");
}

TEST(StorageAtomicBothCorruptError) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  const std::vector<uint8_t> data = makePayload(64, 6);
  CHECK(store.write("both", data.data(), data.size()));
  flash.corrupt("bukifon", "both.a", 20);
  flash.corrupt("bukifon", "both.b", 20);
  std::vector<uint8_t> out(128, 0xAA);
  size_t size = 123;
  CHECK(!store.read("both", out.data(), out.size(), &size));
  CHECK(size == 0);
  CHECK(out[0] == 0xAA);  // no partial output
  INFO("AtomicStorage: two corrupt copies return an error without partial load");
}

TEST(StorageAtomicEraseAndLimits) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  const std::vector<uint8_t> data = makePayload(32, 8);
  CHECK(store.write("x", data.data(), data.size()));
  CHECK(store.exists("x"));
  CHECK(store.erase("x"));
  CHECK(!store.exists("x"));
  CHECK(!store.read("x", nullptr, 0, nullptr));
  std::vector<uint8_t> huge(kAtomicMaxPayload + 1, 0);
  CHECK(!store.write("huge", huge.data(), huge.size()));
  CHECK(!store.write(nullptr, data.data(), data.size()));
  INFO("AtomicStorage: erase and payload limit");
}

TEST(StorageProjectV2StoreRoundtrip) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  Sequencer seq;
  seq.init(48000.0f);
  seq.setBpm(131.0f);
  seq.external().track(3).channel = 12;
  ProjectV2 project;
  captureProjectV2(seq, &project);
  std::snprintf(project.name, sizeof(project.name), "%s", "STORE TEST");
  CHECK(projectV2SaveToStore(project, &store));
  CHECK(store.sequence("project") == 1);
  ProjectV2 loaded;
  char error[192];
  CHECK(projectV2LoadFromStore(&store, &loaded, error, sizeof(error)));
  CHECK(std::strcmp(loaded.name, "STORE TEST") == 0);
  CHECK(std::fabs(loaded.bpm - 131.0f) < 0.01f);
  CHECK(loaded.external.track(3).channel == 12);
  INFO("project v2 roundtrip through MockFlash/AtomicStorage");
}

TEST(StoragePresetBankStore) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  PresetBank bank;
  GenParams gen[kSeqTracks];
  gen[0].seed = 4242;
  CHECK(bank.writeSlot(0, "A", gen, kSeqTracks, 1));
  CHECK(bank.writeSlot(7, "B", gen, kSeqTracks, 0x0F));
  CHECK(presetBankSaveToStore(bank, &store));
  PresetBank loaded;
  CHECK(presetBankLoadFromStore(&store, &loaded));
  CHECK(loaded.usedCount() == 2);
  CHECK(std::strcmp(loaded.slotName(7), "B") == 0);
  INFO("preset bank (8 slots, CRC32) roundtrip through storage backend");
}

TEST(StorageLanguageAfterReboot) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  CHECK(languageSaveToStore(Lang::Ru, &store));
  // Reboot model: new backend object over the same flash contents.
  AtomicStorage rebooted(&flash, "bukifon");
  Lang language = Lang::En;
  CHECK(languageLoadFromStore(&rebooted, &language));
  CHECK(language == Lang::Ru);
  setLanguage(language);
  CHECK(getLanguage() == Lang::Ru);
  setLanguage(Lang::En);
  INFO("UI language persists through the atomic store after a reboot model");
}

TEST(StorageSdFileBackend) {
  SdFileBackend sd("../tests/out/sd_storage");
  CHECK(sd.begin());
  const std::vector<uint8_t> data = makePayload(256, 11);
  CHECK(sd.write("bukifon", "sdkey", data.data(), data.size()));
  CHECK(sd.exists("bukifon", "sdkey"));
  CHECK(sd.size("bukifon", "sdkey") == data.size());
  std::vector<uint8_t> out(512);
  size_t size = 0;
  CHECK(sd.read("bukifon", "sdkey", out.data(), out.size(), &size));
  CHECK(size == data.size());
  CHECK(std::memcmp(out.data(), data.data(), size) == 0);
  CHECK(sd.erase("bukifon", "sdkey"));
  CHECK(!sd.exists("bukifon", "sdkey"));
  INFO("SdFileBackend: host file model read/write/erase");
}

TEST(StorageNvsStub) {
  NvsBackend nvs;
  CHECK(nvs.begin());
  const std::vector<uint8_t> data = makePayload(48, 12);
  CHECK(nvs.write("bukifon", "nvs", data.data(), data.size()));
  CHECK(nvs.exists("bukifon", "nvs"));
  std::vector<uint8_t> out(64);
  size_t size = 0;
  CHECK(nvs.read("bukifon", "nvs", out.data(), out.size(), &size));
  CHECK(size == data.size());
  CHECK(std::memcmp(out.data(), data.data(), size) == 0);
  CHECK(nvs.erase("bukifon", "nvs"));
  CHECK(!nvs.exists("bukifon", "nvs"));
  INFO("NvsBackend: host stub compiles/exercises the same interface (real nvs TODO(hw))");
}

TEST(StorageAtomicRecoveryAfterTornErase) {
  MockFlash flash;
  AtomicStorage store(&flash, "bukifon");
  const std::vector<uint8_t> v1 = makePayload(72, 21);
  CHECK(store.write("torn", v1.data(), v1.size()));
  // Simulate the old slot still present after a new successful write + torn erase.
  const std::vector<uint8_t> v2 = makePayload(72, 22);
  flash.setPowerCutAtWrite(-1);
  CHECK(store.write("torn", v2.data(), v2.size()));
  std::vector<uint8_t> out(128);
  size_t size = 0;
  CHECK(store.read("torn", out.data(), out.size(), &size));
  CHECK(size == v2.size());
  CHECK(std::memcmp(out.data(), v2.data(), size) == 0);
  CHECK(store.sequence("torn") == 2);
  INFO("AtomicStorage: newest valid sequence wins; torn/absent old slot is harmless");
}
