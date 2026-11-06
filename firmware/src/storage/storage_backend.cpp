// SPDX-License-Identifier: GPL-3.0-or-later
#include "storage/storage_backend.hpp"

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <sys/stat.h>

#include "bukifon_i18n.h"

namespace bukifon {
namespace storage {
namespace {

uint32_t crc32(const uint8_t* data, size_t size) {
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < size; ++i) {
    crc ^= data[i];
    for (int k = 0; k < 8; ++k) crc = (crc >> 1) ^ (0xEDB88320u & (~(crc & 1u) + 1u));
  }
  return crc ^ 0xFFFFFFFFu;
}

void putU32(uint8_t* p, uint32_t v) {
  p[0] = static_cast<uint8_t>(v);
  p[1] = static_cast<uint8_t>(v >> 8);
  p[2] = static_cast<uint8_t>(v >> 16);
  p[3] = static_cast<uint8_t>(v >> 24);
}
uint32_t getU32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}
void putU16(uint8_t* p, uint16_t v) {
  p[0] = static_cast<uint8_t>(v);
  p[1] = static_cast<uint8_t>(v >> 8);
}
uint16_t getU16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }

uint32_t recordCrc(const uint8_t* header, const uint8_t* payload, size_t size) {
  // CRC over sequence/size header fields + payload.
  uint32_t crc = 0xFFFFFFFFu;
  auto mix = [&](const uint8_t* data, size_t count) {
    for (size_t i = 0; i < count; ++i) {
      crc ^= data[i];
      for (int k = 0; k < 8; ++k) crc = (crc >> 1) ^ (0xEDB88320u & (~(crc & 1u) + 1u));
    }
  };
  mix(header + 6, 6);  // sequence + payload size
  mix(payload, size);
  return crc ^ 0xFFFFFFFFu;
}

}  // namespace

// --- MockFlash -------------------------------------------------------------
bool MockFlash::write(const char* ns, const char* key, const uint8_t* data, size_t size) {
  if (!ns || !key || !data) return false;
  const uint32_t index = writeCount_++;
  if (failAfterWrites_ >= 0 && static_cast<int>(index) >= failAfterWrites_) {
    ++failedWrites_;
    return false;
  }
  size_t used = 0;
  for (const Entry& entry : entries) used += entry.data.size();
  for (const Entry& entry : entries) {
    if (entry.ns == ns && entry.key == key) used -= entry.data.size();
  }
  if (used + size > maxBytes_) {
    ++failedWrites_;
    return false;
  }
  size_t storeSize = size;
  if (powerCutAtWrite_ == static_cast<int>(index)) {
    powerCutSeen_ = true;
    storeSize = size / 2;  // partial write, no valid record
  }
  Entry* target = nullptr;
  for (Entry& entry : entries) {
    if (entry.ns == ns && entry.key == key) {
      target = &entry;
      break;
    }
  }
  if (!target) {
    entries.push_back(Entry{ns, key, {}, true});
    target = &entries.back();
  }
  target->data.assign(data, data + storeSize);
  target->valid = true;
  if (powerCutAtWrite_ == static_cast<int>(index)) {
    target->valid = false;
    ++failedWrites_;
    return false;
  }
  if (bitFlipAtWrite_ == static_cast<int>(index) && bitFlipOffset_ < target->data.size()) {
    target->data[bitFlipOffset_] ^= 0x5A;
  }
  return true;
}

bool MockFlash::read(const char* ns, const char* key, uint8_t* out, size_t capacity,
                     size_t* outSize) const {
  if (outSize) *outSize = 0;
  for (const Entry& entry : entries) {
    if (entry.ns == ns && entry.key == key && entry.valid) {
      if (entry.data.size() > capacity) return false;
      std::memcpy(out, entry.data.data(), entry.data.size());
      if (outSize) *outSize = entry.data.size();
      return true;
    }
  }
  return false;
}

bool MockFlash::erase(const char* ns, const char* key) {
  for (auto it = entries.begin(); it != entries.end(); ++it) {
    if (it->ns == ns && it->key == key) {
      entries.erase(it);
      ++eraseCount_;
      return true;
    }
  }
  return false;
}

bool MockFlash::exists(const char* ns, const char* key) const {
  for (const Entry& entry : entries) {
    if (entry.ns == ns && entry.key == key) return true;
  }
  return false;
}

size_t MockFlash::size(const char* ns, const char* key) const {
  for (const Entry& entry : entries) {
    if (entry.ns == ns && entry.key == key) return entry.valid ? entry.data.size() : 0;
  }
  return 0;
}

void MockFlash::resetCounters() {
  writeCount_ = 0;
  eraseCount_ = 0;
  failedWrites_ = 0;
  powerCutSeen_ = false;
}

void MockFlash::corrupt(const char* ns, const char* key, size_t offset) {
  for (Entry& entry : entries) {
    if (entry.ns == ns && entry.key == key && offset < entry.data.size()) {
      entry.data[offset] ^= 0x5A;
      return;
    }
  }
}

// --- SdFileBackend ---------------------------------------------------------
SdFileBackend::SdFileBackend(const char* root) : root_(root ? root : ".") {}

bool SdFileBackend::begin() {
  if (mkdir(root_.c_str(), 0755) != 0 && errno != EEXIST) return false;
  return true;
}

std::string SdFileBackend::pathFor(const char* ns, const char* key) const {
  std::string nsText = ns ? ns : "";
  std::string keyText = key ? key : "";
  for (char& c : nsText) if (c == '/' || c == '\\\\') c = '_';
  for (char& c : keyText) if (c == '/' || c == '\\\\') c = '_';
  return root_ + "/" + nsText + "_" + keyText + ".bin";
}

bool SdFileBackend::write(const char* ns, const char* key, const uint8_t* data, size_t size) {
  if (!data) return false;
  std::FILE* file = std::fopen(pathFor(ns, key).c_str(), "wb");
  if (!file) return false;
  const size_t ok = std::fwrite(data, 1, size, file);
  std::fclose(file);
  return ok == size;
}

bool SdFileBackend::read(const char* ns, const char* key, uint8_t* out, size_t capacity,
                         size_t* outSize) const {
  if (outSize) *outSize = 0;
  std::FILE* file = std::fopen(pathFor(ns, key).c_str(), "rb");
  if (!file) return false;
  std::fseek(file, 0, SEEK_END);
  const long size = std::ftell(file);
  std::fseek(file, 0, SEEK_SET);
  if (size < 0 || static_cast<size_t>(size) > capacity) {
    std::fclose(file);
    return false;
  }
  const size_t read = std::fread(out, 1, static_cast<size_t>(size), file);
  std::fclose(file);
  if (read != static_cast<size_t>(size)) return false;
  if (outSize) *outSize = static_cast<size_t>(size);
  return true;
}

bool SdFileBackend::erase(const char* ns, const char* key) {
  return std::remove(pathFor(ns, key).c_str()) == 0;
}

bool SdFileBackend::exists(const char* ns, const char* key) const {
  std::FILE* file = std::fopen(pathFor(ns, key).c_str(), "rb");
  if (file) std::fclose(file);
  return file != nullptr;
}

size_t SdFileBackend::size(const char* ns, const char* key) const {
  std::FILE* file = std::fopen(pathFor(ns, key).c_str(), "rb");
  if (!file) return 0;
  std::fseek(file, 0, SEEK_END);
  const long size = std::ftell(file);
  std::fclose(file);
  return size > 0 ? static_cast<size_t>(size) : 0;
}

// --- NvsBackend stub -------------------------------------------------------
bool NvsBackend::write(const char* ns, const char* key, const uint8_t* data, size_t size) {
  if (!ns || !key || !data) return false;
  for (Entry& entry : entries_) {
    if (entry.ns == ns && entry.key == key) {
      entry.data.assign(data, data + size);
      return true;
    }
  }
  entries_.push_back(Entry{ns, key, std::vector<uint8_t>(data, data + size)});
  return true;
}

bool NvsBackend::read(const char* ns, const char* key, uint8_t* out, size_t capacity,
                      size_t* outSize) const {
  if (outSize) *outSize = 0;
  for (const Entry& entry : entries_) {
    if (entry.ns == ns && entry.key == key) {
      if (entry.data.size() > capacity) return false;
      std::memcpy(out, entry.data.data(), entry.data.size());
      if (outSize) *outSize = entry.data.size();
      return true;
    }
  }
  return false;
}

bool NvsBackend::erase(const char* ns, const char* key) {
  for (auto it = entries_.begin(); it != entries_.end(); ++it) {
    if (it->ns == ns && it->key == key) {
      entries_.erase(it);
      return true;
    }
  }
  return false;
}

bool NvsBackend::exists(const char* ns, const char* key) const {
  for (const Entry& entry : entries_) {
    if (entry.ns == ns && entry.key == key) return true;
  }
  return false;
}

size_t NvsBackend::size(const char* ns, const char* key) const {
  for (const Entry& entry : entries_) {
    if (entry.ns == ns && entry.key == key) return entry.data.size();
  }
  return 0;
}

// --- AtomicStorage ---------------------------------------------------------
AtomicStorage::AtomicStorage(StorageBackend* backend, const char* ns)
    : backend_(backend), ns_(ns && ns[0] ? ns : kDefaultNamespace) {}

const char* AtomicStorage::slotKey(const char* key, char slot, char* out, size_t capacity) {
  std::snprintf(out, capacity, "%s.%c", key ? key : "", slot);
  return out;
}

bool AtomicStorage::writeRecord(const char* key, char slot, uint32_t sequence,
                                const uint8_t* data, size_t size) {
  char slotName[96];
  slotKey(key, slot, slotName, sizeof(slotName));
  std::vector<uint8_t> record(kAtomicHeaderBytes + size);
  putU32(record.data(), kAtomicMagic);
  putU16(record.data() + 4, kAtomicVersion);
  putU32(record.data() + 6, sequence);
  putU32(record.data() + 10, static_cast<uint32_t>(size));
  std::memcpy(record.data() + 14, data, size);
  putU32(record.data() + 14 + size, recordCrc(record.data(), data, size));
  return backend_->write(ns_.c_str(), slotName, record.data(), record.size());
}

bool AtomicStorage::loadRecord(const char* key, char slot, Record* out) const {
  if (!out) return false;
  *out = Record{};
  char slotName[96];
  slotKey(key, slot, slotName, sizeof(slotName));
  if (!backend_->exists(ns_.c_str(), slotName)) return false;
  const size_t size = backend_->size(ns_.c_str(), slotName);
  if (size < kAtomicHeaderBytes || size > kAtomicHeaderBytes + kAtomicMaxPayload) return false;
  std::vector<uint8_t> record(size);
  size_t readSize = 0;
  if (!backend_->read(ns_.c_str(), slotName, record.data(), record.size(), &readSize) ||
      readSize != size) {
    return false;
  }
  if (getU32(record.data()) != kAtomicMagic || getU16(record.data() + 4) != kAtomicVersion) {
    return false;
  }
  const uint32_t sequence = getU32(record.data() + 6);
  const uint32_t payloadSize = getU32(record.data() + 10);
  if (payloadSize > kAtomicMaxPayload || kAtomicHeaderBytes + payloadSize != size) return false;
  const uint8_t* payload = record.data() + 14;
  const uint32_t storedCrc = getU32(record.data() + 14 + payloadSize);
  if (recordCrc(record.data(), payload, payloadSize) != storedCrc) return false;
  out->valid = true;
  out->sequence = sequence;
  out->payload.assign(payload, payload + payloadSize);
  return true;
}

bool AtomicStorage::write(const char* key, const uint8_t* data, size_t size) {
  if (!backend_ || !key || !data || size > kAtomicMaxPayload) return false;
  Record a;
  Record b;
  loadRecord(key, 'a', &a);
  loadRecord(key, 'b', &b);
  uint32_t latest = 0;
  if (a.valid) latest = a.sequence;
  if (b.valid && b.sequence > latest) latest = b.sequence;
  const uint32_t sequence = latest + 1;
  // Write the inactive slot: if B is newer, write A, otherwise B.
  const char target = (b.valid && b.sequence >= latest && b.sequence > (a.valid ? a.sequence : 0))
                          ? 'a'
                          : (a.valid ? 'b' : 'a');
  if (!writeRecord(key, target, sequence, data, size)) return false;
  Record check;
  if (!loadRecord(key, target, &check) || !check.valid || check.sequence != sequence ||
      check.payload.size() != size || std::memcmp(check.payload.data(), data, size) != 0) {
    return false;  // read-back failed; leave the old copy untouched
  }
  // Keep the old copy until the new one is proven; then erase it.
  const char oldSlot = target == 'a' ? 'b' : 'a';
  char oldName[96];
  slotKey(key, oldSlot, oldName, sizeof(oldName));
  backend_->erase(ns_.c_str(), oldName);
  ++writeCount_;
  lastRecovery_ = false;
  return true;
}

bool AtomicStorage::read(const char* key, uint8_t* out, size_t capacity,
                         size_t* outSize) const {
  if (outSize) *outSize = 0;
  Record a;
  Record b;
  loadRecord(key, 'a', &a);
  loadRecord(key, 'b', &b);
  if (!a.valid && !b.valid) {
    lastRecovery_ = false;
    return false;
  }
  const bool useB = b.valid && (!a.valid || b.sequence > a.sequence);
  Record& selected = useB ? b : a;
  if (selected.payload.size() > capacity) return false;
  // Recovery when the other slot exists but is invalid (power cut/CRC damage).
  char otherName[96];
  slotKey(key, useB ? 'a' : 'b', otherName, sizeof(otherName));
  const bool otherExists = backend_ && backend_->exists(ns_.c_str(), otherName);
  lastRecovery_ = otherExists && !(useB ? a.valid : b.valid);
  if (lastRecovery_) ++recoveryCount_;
  std::memcpy(out, selected.payload.data(), selected.payload.size());
  if (outSize) *outSize = selected.payload.size();
  return true;
}

bool AtomicStorage::erase(const char* key) {
  char name[96];
  bool ok = false;
  slotKey(key, 'a', name, sizeof(name));
  ok = backend_->erase(ns_.c_str(), name) || ok;
  slotKey(key, 'b', name, sizeof(name));
  ok = backend_->erase(ns_.c_str(), name) || ok;
  if (ok) ++eraseCount_;
  return ok;
}

bool AtomicStorage::exists(const char* key) const {
  char name[96];
  slotKey(key, 'a', name, sizeof(name));
  if (backend_->exists(ns_.c_str(), name)) return true;
  slotKey(key, 'b', name, sizeof(name));
  return backend_->exists(ns_.c_str(), name);
}

uint32_t AtomicStorage::sequence(const char* key) const {
  Record a;
  Record b;
  loadRecord(key, 'a', &a);
  loadRecord(key, 'b', &b);
  uint32_t latest = 0;
  if (a.valid) latest = a.sequence;
  if (b.valid && b.sequence > latest) latest = b.sequence;
  return latest;
}

// --- Integration helpers ---------------------------------------------------
bool projectV2SaveToStore(const ProjectV2& project, AtomicStorage* store) {
  if (!store) return false;
  std::vector<uint8_t> bytes(projectV2SerializedSize(project));
  const size_t size = projectV2Serialize(project, bytes.data(), bytes.size());
  return size > 0 && store->write(kProjectKey, bytes.data(), size);
}

bool projectV2LoadFromStore(AtomicStorage* store, ProjectV2* out, char* error,
                            size_t errorLen) {
  if (!store || !out) return false;
  std::vector<uint8_t> bytes(kAtomicMaxPayload);
  size_t readSize = 0;
  if (!store->read(kProjectKey, bytes.data(), bytes.size(), &readSize)) {
    if (error && errorLen) std::snprintf(error, errorLen, "project not found");
    return false;
  }
  return projectV2Deserialize(bytes.data(), readSize, out, error, errorLen);
}

bool presetBankSaveToStore(const PresetBank& bank, AtomicStorage* store) {
  if (!store) return false;
  std::vector<uint8_t> bytes(bank.serializedSize());
  const size_t size = bank.serialize(bytes.data(), bytes.size());
  return size > 0 && store->write(kPresetsKey, bytes.data(), size);
}

bool presetBankLoadFromStore(AtomicStorage* store, PresetBank* out) {
  if (!store || !out) return false;
  std::vector<uint8_t> bytes(4096);
  size_t readSize = 0;
  if (!store->read(kPresetsKey, bytes.data(), bytes.size(), &readSize)) return false;
  return out->deserialize(bytes.data(), readSize);
}

bool languageSaveToStore(Lang language, AtomicStorage* store) {
  if (!store) return false;
  const char* name = languageName(language);
  return store->write(kLanguageKey, reinterpret_cast<const uint8_t*>(name),
                      std::strlen(name));
}

bool languageLoadFromStore(AtomicStorage* store, Lang* out) {
  if (!store || !out) return false;
  char text[8] = {};
  size_t size = 0;
  if (!store->read(kLanguageKey, reinterpret_cast<uint8_t*>(text), sizeof(text) - 1, &size)) {
    return false;
  }
  text[size] = '\0';
  return languageFromName(text, out);
}

}  // namespace storage
}  // namespace bukifon
