// SPDX-License-Identifier: GPL-3.0-or-later
#include "storage/preset_bank.hpp"

#include <cstdio>
#include <cstring>

namespace bukifon {
namespace {

constexpr size_t kSlotBytes = sizeof(bool) + 24 + sizeof(GenParams) * kSeqTracks + sizeof(uint8_t);
constexpr size_t kPayloadBytes = kSlotBytes * PresetBank::kSlots;

void setError(char* error, size_t len, const char* text) {
  if (error && len) std::snprintf(error, len, "%s", text);
}

uint32_t crc32Bytes(const uint8_t* data, size_t size) {
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < size; ++i) {
    crc ^= data[i];
    for (int k = 0; k < 8; ++k) crc = (crc >> 1) ^ (0xEDB88320u & (~(crc & 1u) + 1u));
  }
  return crc ^ 0xFFFFFFFFu;
}

}  // namespace

void PresetBank::clear() {
  for (int i = 0; i < kSlots; ++i) slots_[i] = PresetSlot{};
}

bool PresetBank::load(const char* path) {
  if (!path) return false;
  std::FILE* file = std::fopen(path, "rb");
  if (!file) return false;
  uint8_t header[20] = {};
  bool ok = std::fread(header, 1, sizeof(header), file) == sizeof(header);
  uint32_t crc = 0;
  if (ok) {
    const uint32_t magic = static_cast<uint32_t>(header[0]) |
                           (static_cast<uint32_t>(header[1]) << 8) |
                           (static_cast<uint32_t>(header[2]) << 16) |
                           (static_cast<uint32_t>(header[3]) << 24);
    const uint16_t version = static_cast<uint16_t>(header[4] | (header[5] << 8));
    const uint32_t count = static_cast<uint32_t>(header[6]) |
                           (static_cast<uint32_t>(header[7]) << 8) |
                           (static_cast<uint32_t>(header[8]) << 16) |
                           (static_cast<uint32_t>(header[9]) << 24);
    std::memcpy(&crc, header + 16, sizeof(crc));
    ok = magic == kMagic && version == kVersion && count == static_cast<uint32_t>(kSlots);
  }
  PresetSlot loaded[kSlots];
  if (ok) ok = std::fread(loaded, sizeof(PresetSlot), kSlots, file) == static_cast<size_t>(kSlots);
  std::fclose(file);
  if (!ok) {
    clear();
    return false;
  }
  const uint32_t computed = crc32Bytes(reinterpret_cast<const uint8_t*>(loaded), sizeof(loaded));
  if (computed != crc) {
    clear();
    return false;
  }
  for (int i = 0; i < kSlots; ++i) slots_[i] = loaded[i];
  return true;
}

bool PresetBank::save(const char* path) const {
  if (!path) return false;
  std::FILE* file = std::fopen(path, "wb");
  if (!file) return false;
  uint8_t header[20] = {};
  header[0] = static_cast<uint8_t>(kMagic & 0xFF);
  header[1] = static_cast<uint8_t>((kMagic >> 8) & 0xFF);
  header[2] = static_cast<uint8_t>((kMagic >> 16) & 0xFF);
  header[3] = static_cast<uint8_t>((kMagic >> 24) & 0xFF);
  header[4] = static_cast<uint8_t>(kVersion & 0xFF);
  header[5] = static_cast<uint8_t>(kVersion >> 8);
  header[6] = static_cast<uint8_t>(kSlots);
  const uint32_t crc =
      crc32Bytes(reinterpret_cast<const uint8_t*>(slots_), sizeof(slots_));
  std::memcpy(header + 16, &crc, sizeof(crc));
  bool ok = std::fwrite(header, 1, sizeof(header), file) == sizeof(header);
  if (ok) ok = std::fwrite(slots_, sizeof(PresetSlot), kSlots, file) == static_cast<size_t>(kSlots);
  std::fclose(file);
  return ok;
}

bool PresetBank::writeSlot(int slot, const char* name, const GenParams* gen, int parts,
                           uint8_t selectedParts, char* error, size_t errorLen) {
  if (slot < 0 || slot >= kSlots || !name || !name[0] || !gen || parts <= 0) {
    setError(error, errorLen, "invalid slot/name/gen");
    return false;
  }
  PresetSlot& target = slots_[slot];
  target = PresetSlot{};
  target.used = true;
  std::snprintf(target.name, sizeof(target.name), "%s", name);
  const int count = parts < kSeqTracks ? parts : kSeqTracks;
  for (int i = 0; i < count; ++i) target.gen[i] = gen[i];
  target.selectedParts = selectedParts;
  setError(error, errorLen, "");
  return true;
}

bool PresetBank::readSlot(int slot, PresetSlot* out) const {
  if (slot < 0 || slot >= kSlots || !out || !slots_[slot].used) return false;
  *out = slots_[slot];
  return true;
}

bool PresetBank::hasSlot(int slot) const {
  return slot >= 0 && slot < kSlots && slots_[slot].used;
}

const char* PresetBank::slotName(int slot) const {
  return hasSlot(slot) ? slots_[slot].name : "";
}

int PresetBank::usedCount() const {
  int count = 0;
  for (int i = 0; i < kSlots; ++i) count += slots_[i].used ? 1 : 0;
  return count;
}

int PresetBank::slotIndexByName(const char* name) const {
  if (!name) return -1;
  for (int i = 0; i < kSlots; ++i) {
    if (slots_[i].used && std::strcmp(slots_[i].name, name) == 0) return i;
  }
  return -1;
}

}  // namespace bukifon
