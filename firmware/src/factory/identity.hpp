// SPDX-License-Identifier: GPL-3.0-or-later
// Factory identity (serial + revisions + MAC + calibration + CRC32).
//
// This is the format written to `factory_data` in flash (two copies + CRC) and
// linked to the 24C32 calibration record.  Real flash/24C32 programming is
// TODO(hw); the host `IdentityStore` models the two-slot flash layout and is
// used by the factory CLI and tests.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace bukifon {
namespace factory {

constexpr uint32_t kIdentityMagic = 0x424B4944u;  // "BKID"
constexpr uint16_t kIdentityVersion = 1;
constexpr size_t kIdentityProductLen = 10;
constexpr size_t kIdentitySerialLen = 20;
constexpr size_t kIdentityCoreLen = 12;
constexpr size_t kIdentityPanelLen = 8;
constexpr size_t kIdentityPwrLen = 8;
constexpr size_t kIdentityDateLen = 12;
constexpr size_t kIdentityBatchLen = 8;
constexpr size_t kIdentityCalLen = 12;
constexpr size_t kIdentityTestLen = 8;
constexpr size_t kIdentitySerializedSize = 114;  // 4+2+10+20+12+8+8+12+8+6+12+8+4

struct Identity {
  uint32_t magic = kIdentityMagic;
  uint16_t version = kIdentityVersion;
  char product[kIdentityProductLen] = "BUKIFON";
  char serial[kIdentitySerialLen] = {};
  char coreRev[kIdentityCoreLen] = {};
  char panelRev[kIdentityPanelLen] = {};
  char pwrRev[kIdentityPwrLen] = {};
  char date[kIdentityDateLen] = {};
  char batch[kIdentityBatchLen] = {};
  uint8_t mac[6] = {};
  char calibrationVersion[kIdentityCalLen] = {};
  char testResult[kIdentityTestLen] = {};
  uint32_t crc32 = 0;
};

// SN format: BKS3-<YY><batch letter>-<4 digits>, e.g. BKS3-26A-0001.
bool identitySerialValid(const char* serial, char* error = nullptr, size_t errorLen = 0);
bool identityDateValid(const char* date);
bool identityValidate(const Identity& identity, char* error = nullptr, size_t errorLen = 0);
bool identityVerifyCrc(const Identity& identity);

uint32_t identityComputeCrc(const Identity& identity);
void identitySeal(Identity* identity);

// Explicit little-endian serialization (no struct padding/layout surprises).
bool identitySerialize(const Identity& identity, uint8_t* out, size_t capacity,
                       size_t* written = nullptr);
bool identityDeserialize(const uint8_t* data, size_t size, Identity* out,
                         char* error = nullptr, size_t errorLen = 0);

std::string identityToJson(const Identity& identity);
bool identityFromJson(const char* json, Identity* out, char* error = nullptr,
                      size_t errorLen = 0);

// Host model of the flash `factory_data` area: two copies, alternating writes,
// CRC-checked reads, duplicate-serial rejection.  Real flash/24C32 write is
// TODO(hw) — this class is the validated format/store contract for it.
class IdentityStore {
 public:
  static constexpr int kSlots = 2;
  void clear();
  int count() const { return usedCount_; }
  // Validates + seals + checks duplicate serial before writing the next slot.
  bool write(const Identity& identity, char* error = nullptr, size_t errorLen = 0);
  bool read(Identity* out, int* slot = nullptr) const;  // latest valid copy
  bool hasSerial(const char* serial) const;
  bool writeRaw(int slot, const Identity& identity);  // test hook: no validation
  bool readSlot(int slot, Identity* out) const;

 private:
  Identity slots_[kSlots] = {};
  bool used_[kSlots] = {};
  int slotCount_ = 0;  // total writes, used to pick alternating slot
  int usedCount_ = 0;
};

}  // namespace factory
}  // namespace bukifon
