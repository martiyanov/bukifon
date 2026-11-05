// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "core/modulation_defs.hpp"
#include "core/params.hpp"

namespace bukifon {

struct Patch {
  uint8_t version = 1;
  uint8_t flags = 0;
  char name[16] = "Init";
  PartParams parts[kNumParts];
  GlobalParams global;
  ModSlotData slots[kModSlots];

  void initDefault();
};

// Compact, CRC-protected preset (timbre + matrix). Fits into 512 bytes.
// Layout: version, flags, name[16], parts[4][kNumPartParams] u8 normalised,
// global[kNumGlobalParams] u8, slots[16] x 5 bytes, CRC16 (LE).
constexpr size_t kPatchSerializedBytes =
    2 + 16 + kNumParts * kNumPartParams + kNumGlobalParams + kModSlots * 5 + 2;

static_assert(kPatchSerializedBytes <= kMaxPatchBytes, "Patch must fit into 512 bytes");

size_t patchSerialize(const Patch& patch, uint8_t* out, size_t capacity);
bool patchDeserialize(const uint8_t* data, size_t size, Patch* out);
bool patchValidate(const uint8_t* data, size_t size);

// SysEx (7-bit) transport for patch dumps. Returns number of bytes written.
size_t patchToSysEx(const Patch& patch, uint8_t* out, size_t capacity);
bool patchFromSysEx(const uint8_t* sysexPayload, size_t size, Patch* out);

uint16_t crc16Ccitt(const uint8_t* data, size_t size);

// 16 built-in factory patches (compiled in, deterministic).
void makeFactoryPatch(int index, Patch* out);
void makeFactoryBank(Patch* out, int count);

}  // namespace bukifon
