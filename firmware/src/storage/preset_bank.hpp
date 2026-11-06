// SPDX-License-Identifier: GPL-3.0-or-later
// 8 preset slots for the GEN/UX page (docs/65: presets/compare).
//
// Host implementation is a versioned binary file; on P4 this is replaced by NVS
// or a flash partition (TODO(hw)).  A slot stores the per-part GenParams, the
// multi-select mask and a display name.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "io/gen.hpp"

namespace bukifon {

struct PresetSlot {
  bool used = false;
  char name[24] = {};
  GenParams gen[kSeqTracks];
  uint8_t selectedParts = 1;  // bit mask, part 0 = bit 0
};

class PresetBank {
 public:
  static constexpr int kSlots = 8;
  static constexpr uint32_t kMagic = 0x424B5052u;  // "BKPR"
  static constexpr uint16_t kVersion = 1;

  void clear();
  bool load(const char* path);
  bool save(const char* path) const;
  size_t serializedSize() const;
  size_t serialize(uint8_t* out, size_t capacity) const;
  bool deserialize(const uint8_t* data, size_t size);

  bool writeSlot(int slot, const char* name, const GenParams* gen, int parts,
                 uint8_t selectedParts, char* error = nullptr, size_t errorLen = 0);
  bool readSlot(int slot, PresetSlot* out) const;
  bool hasSlot(int slot) const;
  const char* slotName(int slot) const;
  int usedCount() const;
  int slotIndexByName(const char* name) const;

 private:
  PresetSlot slots_[kSlots];
};

}  // namespace bukifon
