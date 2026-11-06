// SPDX-License-Identifier: GPL-3.0-or-later
// Storage backend + atomic A/B writes (docs/70 §9/§10, docs/42).
//
// The same AtomicStorage API is used by project v2, presets, UI language and
// device settings.  Two slots (A/B) carry a record with sequence + size + CRC32:
// write inactive -> read-back verify -> keep sequence switch -> erase old.
// A power cut/corruption never destroys the last good copy; load recovers the
// other slot and reports recovery.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "bukifon_i18n.h"
#include "storage/preset_bank.hpp"
#include "storage/project_v2.hpp"

namespace bukifon {
namespace storage {

constexpr uint32_t kAtomicMagic = 0x31414B42u;  // "BKA1"
constexpr uint16_t kAtomicVersion = 1;
constexpr size_t kAtomicHeaderBytes = 18;
constexpr size_t kAtomicMaxPayload = 64 * 1024;

class StorageBackend {
 public:
  virtual ~StorageBackend() = default;
  virtual bool begin() = 0;
  virtual bool write(const char* ns, const char* key, const uint8_t* data, size_t size) = 0;
  virtual bool read(const char* ns, const char* key, uint8_t* out, size_t capacity,
                    size_t* outSize) const = 0;
  virtual bool erase(const char* ns, const char* key) = 0;
  virtual bool exists(const char* ns, const char* key) const = 0;
  virtual size_t size(const char* ns, const char* key) const = 0;
  virtual const char* name() const = 0;
};

// --- MockFlash: host test backend with failure injection ------------------
class MockFlash : public StorageBackend {
 public:
  static constexpr size_t kCapacity = 256 * 1024;
  bool begin() override { return true; }
  bool write(const char* ns, const char* key, const uint8_t* data, size_t size) override;
  bool read(const char* ns, const char* key, uint8_t* out, size_t capacity,
            size_t* outSize) const override;
  bool erase(const char* ns, const char* key) override;
  bool exists(const char* ns, const char* key) const override;
  size_t size(const char* ns, const char* key) const override;
  const char* name() const override { return "mock-flash"; }

  // Failure injection.  Counters are global write/erase operations.
  void setFailAfterWrites(int writes) { failAfterWrites_ = writes; }
  void setPowerCutAtWrite(int writeIndex) { powerCutAtWrite_ = writeIndex; }
  void setBitFlipAtWrite(int writeIndex, size_t offset) {
    bitFlipAtWrite_ = writeIndex;
    bitFlipOffset_ = offset;
  }
  void setMaxBytes(size_t bytes) { maxBytes_ = bytes; }
  void resetErrors() {
    failAfterWrites_ = -1;
    powerCutAtWrite_ = -1;
    bitFlipAtWrite_ = -1;
    bitFlipOffset_ = 0;
  }
  uint32_t writeCount() const { return writeCount_; }
  uint32_t eraseCount() const { return eraseCount_; }
  uint32_t failedWrites() const { return failedWrites_; }
  bool powerCutSeen() const { return powerCutSeen_; }
  void resetCounters();
  void corrupt(const char* ns, const char* key, size_t offset);

  struct Entry {
    std::string ns;
    std::string key;
    std::vector<uint8_t> data;
    bool valid = true;
  };
  std::vector<Entry> entries;

 private:
  int failAfterWrites_ = -1;
  int powerCutAtWrite_ = -1;
  int bitFlipAtWrite_ = -1;
  size_t bitFlipOffset_ = 0;
  size_t maxBytes_ = kCapacity;
  uint32_t writeCount_ = 0;
  uint32_t eraseCount_ = 0;
  uint32_t failedWrites_ = 0;
  bool powerCutSeen_ = false;
};

// --- SD file backend (host model; real SDMMC driver TODO(hw)) -------------
class SdFileBackend : public StorageBackend {
 public:
  explicit SdFileBackend(const char* root);
  bool begin() override;
  bool write(const char* ns, const char* key, const uint8_t* data, size_t size) override;
  bool read(const char* ns, const char* key, uint8_t* out, size_t capacity,
            size_t* outSize) const override;
  bool erase(const char* ns, const char* key) override;
  bool exists(const char* ns, const char* key) const override;
  size_t size(const char* ns, const char* key) const override;
  const char* name() const override { return "sd-file"; }
  const std::string& root() const { return root_; }

 private:
  std::string pathFor(const char* ns, const char* key) const;
  std::string root_;
};

// --- NVS backend: in-memory host stub, ESP-IDF nvs implementation TODO(hw) -
class NvsBackend : public StorageBackend {
 public:
  bool begin() override { return true; }
  bool write(const char* ns, const char* key, const uint8_t* data, size_t size) override;
  bool read(const char* ns, const char* key, uint8_t* out, size_t capacity,
            size_t* outSize) const override;
  bool erase(const char* ns, const char* key) override;
  bool exists(const char* ns, const char* key) const override;
  size_t size(const char* ns, const char* key) const override;
  const char* name() const override { return "nvs-stub"; }

 private:
  struct Entry {
    std::string ns;
    std::string key;
    std::vector<uint8_t> data;
  };
  std::vector<Entry> entries_;
};

// --- Atomic A/B key-value layer -------------------------------------------
class AtomicStorage {
 public:
  AtomicStorage(StorageBackend* backend, const char* ns = "bukifon");
  bool write(const char* key, const uint8_t* data, size_t size);
  bool read(const char* key, uint8_t* out, size_t capacity, size_t* outSize) const;
  bool erase(const char* key);
  bool exists(const char* key) const;
  uint32_t sequence(const char* key) const;
  bool lastLoadRecovered() const { return lastRecovery_; }
  uint32_t recoveryCount() const { return recoveryCount_; }
  uint32_t writeCount() const { return writeCount_; }
  uint32_t eraseCount() const { return eraseCount_; }
  const char* namespaceName() const { return ns_.c_str(); }

  static const char* slotKey(const char* key, char slot, char* out, size_t capacity);

 private:
  struct Record {
    bool valid = false;
    uint32_t sequence = 0;
    std::vector<uint8_t> payload;
  };
  bool loadRecord(const char* key, char slot, Record* out) const;
  bool writeRecord(const char* key, char slot, uint32_t sequence, const uint8_t* data,
                   size_t size);

  StorageBackend* backend_ = nullptr;
  std::string ns_;
  mutable bool lastRecovery_ = false;
  mutable uint32_t recoveryCount_ = 0;
  uint32_t writeCount_ = 0;
  uint32_t eraseCount_ = 0;
};

// --- Integration helpers: project v2 / presets / language ------------------
constexpr const char* kDefaultNamespace = "bukifon";
constexpr const char* kProjectKey = "project";
constexpr const char* kPresetsKey = "presets";
constexpr const char* kLanguageKey = "language";

bool projectV2SaveToStore(const ProjectV2& project, AtomicStorage* store);
bool projectV2LoadFromStore(AtomicStorage* store, ProjectV2* out, char* error = nullptr,
                            size_t errorLen = 0);

bool presetBankSaveToStore(const PresetBank& bank, AtomicStorage* store);
bool presetBankLoadFromStore(AtomicStorage* store, PresetBank* out);

bool languageSaveToStore(Lang language, AtomicStorage* store);
bool languageLoadFromStore(AtomicStorage* store, Lang* out);

}  // namespace storage
}  // namespace bukifon
