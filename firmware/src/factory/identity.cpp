// SPDX-License-Identifier: GPL-3.0-or-later
#include "factory/identity.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace bukifon {
namespace factory {
namespace {

void setError(char* error, size_t len, const char* text) {
  if (error && len) std::snprintf(error, len, "%s", text);
}

bool isDigit(char c) { return c >= '0' && c <= '9'; }
bool isUpper(char c) { return c >= 'A' && c <= 'Z'; }
bool isPrintableNonEmpty(const char* s, size_t cap) {
  if (!s || s[0] == '\0') return false;
  size_t length = 0;
  for (; length < cap && s[length]; ++length) {
    const unsigned char c = static_cast<unsigned char>(s[length]);
    if (c < 0x20 || c > 0x7E) return false;
  }
  return length > 0 && length < cap;
}

void putU16(uint8_t* p, uint16_t v) {
  p[0] = static_cast<uint8_t>(v & 0xFF);
  p[1] = static_cast<uint8_t>(v >> 8);
}
void putU32(uint8_t* p, uint32_t v) {
  p[0] = static_cast<uint8_t>(v & 0xFF);
  p[1] = static_cast<uint8_t>((v >> 8) & 0xFF);
  p[2] = static_cast<uint8_t>((v >> 16) & 0xFF);
  p[3] = static_cast<uint8_t>((v >> 24) & 0xFF);
}
uint16_t getU16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
uint32_t getU32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}
void putFixed(uint8_t* p, const char* s, size_t cap) {
  std::memset(p, 0, cap);
  std::memcpy(p, s, std::strlen(s) < cap ? std::strlen(s) : cap - 1);
}
void getFixed(const uint8_t* p, char* s, size_t cap) {
  std::memcpy(s, p, cap);
  s[cap - 1] = '\0';
}

const char* kJsonStart(const char* json, const char* key) {
  if (!json || !key) return nullptr;
  char pattern[64];
  std::snprintf(pattern, sizeof(pattern), "\"%s\"", key);
  const char* at = std::strstr(json, pattern);
  if (!at) return nullptr;
  at = std::strchr(at + std::strlen(pattern), ':');
  if (!at) return nullptr;
  ++at;
  while (*at == ' ' || *at == '\t' || *at == '\n' || *at == '\r') ++at;
  return at;
}

bool jsonString(const char* json, const char* key, char* out, size_t cap) {
  const char* at = kJsonStart(json, key);
  if (!at || *at != '"') return false;
  ++at;
  size_t n = 0;
  while (*at && *at != '"' && n + 1 < cap) out[n++] = *at++;
  out[n] = '\0';
  return *at == '"';
}

bool jsonU32(const char* json, const char* key, uint32_t* out) {
  const char* at = kJsonStart(json, key);
  if (!at) return false;
  char* end = nullptr;
  const unsigned long v = std::strtoul(at, &end, 0);
  if (end == at) return false;
  *out = static_cast<uint32_t>(v);
  return true;
}

bool parseMac(const char* text, uint8_t mac[6]) {
  if (!text) return false;
  unsigned values[6] = {};
  if (std::sscanf(text, "%2x:%2x:%2x:%2x:%2x:%2x", &values[0], &values[1], &values[2],
                  &values[3], &values[4], &values[5]) != 6) {
    return false;
  }
  for (int i = 0; i < 6; ++i) {
    if (values[i] > 0xFF) return false;
    mac[i] = static_cast<uint8_t>(values[i]);
  }
  return true;
}

}  // namespace

bool identitySerialValid(const char* serial, char* error, size_t errorLen) {
  if (!serial || std::strlen(serial) != 13) {
    setError(error, errorLen, "serial must be BKS3-YYA-NNNN (13 chars)");
    return false;
  }
  if (std::strncmp(serial, "BKS3-", 5) != 0) {
    setError(error, errorLen, "serial prefix must be BKS3-");
    return false;
  }
  if (!isDigit(serial[5]) || !isDigit(serial[6]) || !isUpper(serial[7])) {
    setError(error, errorLen, "serial batch must be YYA (two digits + letter)");
    return false;
  }
  if (serial[8] != '-' || !isDigit(serial[9]) || !isDigit(serial[10]) || !isDigit(serial[11]) ||
      !isDigit(serial[12])) {
    setError(error, errorLen, "serial tail must be four digits");
    return false;
  }
  setError(error, errorLen, "");
  return true;
}

bool identityDateValid(const char* date) {
  if (!date || std::strlen(date) != 10) return false;
  if (!isDigit(date[0]) || !isDigit(date[1]) || !isDigit(date[2]) || !isDigit(date[3]) ||
      date[4] != '-' || !isDigit(date[5]) || !isDigit(date[6]) || date[7] != '-' ||
      !isDigit(date[8]) || !isDigit(date[9])) {
    return false;
  }
  const int year = (date[0] - '0') * 1000 + (date[1] - '0') * 100 + (date[2] - '0') * 10 +
                   (date[3] - '0');
  const int month = (date[5] - '0') * 10 + (date[6] - '0');
  const int day = (date[8] - '0') * 10 + (date[9] - '0');
  return year >= 2020 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31;
}

bool identityValidate(const Identity& identity, char* error, size_t errorLen) {
  if (identity.magic != kIdentityMagic) {
    setError(error, errorLen, "bad identity magic");
    return false;
  }
  if (identity.version != kIdentityVersion) {
    setError(error, errorLen, "unsupported identity version");
    return false;
  }
  if (std::strncmp(identity.product, "BUKIFON", kIdentityProductLen) != 0) {
    setError(error, errorLen, "product must be BUKIFON");
    return false;
  }
  if (!identitySerialValid(identity.serial, error, errorLen)) return false;
  // Batch must match the serial batch component (BKS3-26A-0001 -> 26A).
  if (std::strncmp(identity.batch, identity.serial + 5, 3) != 0 || identity.batch[3] != '\0') {
    setError(error, errorLen, "batch does not match serial batch");
    return false;
  }
  if (!identityDateValid(identity.date)) {
    setError(error, errorLen, "date must be YYYY-MM-DD");
    return false;
  }
  if (!isPrintableNonEmpty(identity.coreRev, kIdentityCoreLen)) {
    setError(error, errorLen, "core revision missing");
    return false;
  }
  if (!isPrintableNonEmpty(identity.panelRev, kIdentityPanelLen)) {
    setError(error, errorLen, "panel revision missing");
    return false;
  }
  if (!isPrintableNonEmpty(identity.pwrRev, kIdentityPwrLen)) {
    setError(error, errorLen, "power revision missing");
    return false;
  }
  if (!isPrintableNonEmpty(identity.calibrationVersion, kIdentityCalLen)) {
    setError(error, errorLen, "calibration version missing");
    return false;
  }
  if (!isPrintableNonEmpty(identity.testResult, kIdentityTestLen)) {
    setError(error, errorLen, "test result missing");
    return false;
  }
  bool macZero = true;
  for (int i = 0; i < 6; ++i) macZero = macZero && identity.mac[i] == 0;
  if (macZero) {
    setError(error, errorLen, "MAC must be programmed (eFuse anchor)");
    return false;
  }
  setError(error, errorLen, "");
  return true;
}

uint32_t identityComputeCrc(const Identity& identity) {
  uint8_t bytes[kIdentitySerializedSize] = {};
  // Build the layout explicitly (same as serialize) for CRC stability.
  std::memcpy(bytes, &identity.magic, 4);  // little-endian host (ESP32/x86/ARM64 all LE)
  bytes[4] = static_cast<uint8_t>(identity.version & 0xFF);
  bytes[5] = static_cast<uint8_t>(identity.version >> 8);
  putFixed(bytes + 6, identity.product, kIdentityProductLen);
  putFixed(bytes + 16, identity.serial, kIdentitySerialLen);
  putFixed(bytes + 36, identity.coreRev, kIdentityCoreLen);
  putFixed(bytes + 48, identity.panelRev, kIdentityPanelLen);
  putFixed(bytes + 56, identity.pwrRev, kIdentityPwrLen);
  putFixed(bytes + 64, identity.date, kIdentityDateLen);
  putFixed(bytes + 76, identity.batch, kIdentityBatchLen);
  std::memcpy(bytes + 84, identity.mac, 6);
  putFixed(bytes + 90, identity.calibrationVersion, kIdentityCalLen);
  putFixed(bytes + 102, identity.testResult, kIdentityTestLen);
  static uint32_t table[256];
  static bool ready = false;
  if (!ready) {
    for (uint32_t i = 0; i < 256; ++i) {
      uint32_t c = i;
      for (int k = 0; k < 8; ++k) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
      table[i] = c;
    }
    ready = true;
  }
  uint32_t crc = 0xFFFFFFFFu;
  for (size_t i = 0; i < kIdentitySerializedSize - 4; ++i) {
    crc = table[(crc ^ bytes[i]) & 0xFF] ^ (crc >> 8);
  }
  return crc ^ 0xFFFFFFFFu;
}

void identitySeal(Identity* identity) {
  if (identity) identity->crc32 = identityComputeCrc(*identity);
}

bool identityVerifyCrc(const Identity& identity) {
  return identityComputeCrc(identity) == identity.crc32;
}

bool identitySerialize(const Identity& identity, uint8_t* out, size_t capacity,
                       size_t* written) {
  if (!out || capacity < kIdentitySerializedSize) return false;
  std::memset(out, 0, kIdentitySerializedSize);
  putU32(out, identity.magic);
  putU16(out + 4, identity.version);
  putFixed(out + 6, identity.product, kIdentityProductLen);
  putFixed(out + 16, identity.serial, kIdentitySerialLen);
  putFixed(out + 36, identity.coreRev, kIdentityCoreLen);
  putFixed(out + 48, identity.panelRev, kIdentityPanelLen);
  putFixed(out + 56, identity.pwrRev, kIdentityPwrLen);
  putFixed(out + 64, identity.date, kIdentityDateLen);
  putFixed(out + 76, identity.batch, kIdentityBatchLen);
  std::memcpy(out + 84, identity.mac, 6);
  putFixed(out + 90, identity.calibrationVersion, kIdentityCalLen);
  putFixed(out + 102, identity.testResult, kIdentityTestLen);
  putU32(out + 110, identity.crc32);
  if (written) *written = kIdentitySerializedSize;
  return true;
}

bool identityDeserialize(const uint8_t* data, size_t size, Identity* out, char* error,
                         size_t errorLen) {
  if (!data || !out || size < kIdentitySerializedSize) {
    setError(error, errorLen, "identity blob too short");
    return false;
  }
  Identity identity;
  identity.magic = getU32(data);
  identity.version = getU16(data + 4);
  getFixed(data + 6, identity.product, kIdentityProductLen);
  getFixed(data + 16, identity.serial, kIdentitySerialLen);
  getFixed(data + 36, identity.coreRev, kIdentityCoreLen);
  getFixed(data + 48, identity.panelRev, kIdentityPanelLen);
  getFixed(data + 56, identity.pwrRev, kIdentityPwrLen);
  getFixed(data + 64, identity.date, kIdentityDateLen);
  getFixed(data + 76, identity.batch, kIdentityBatchLen);
  std::memcpy(identity.mac, data + 84, 6);
  getFixed(data + 90, identity.calibrationVersion, kIdentityCalLen);
  getFixed(data + 102, identity.testResult, kIdentityTestLen);
  identity.crc32 = getU32(data + 110);
  if (!identityValidate(identity, error, errorLen)) return false;
  if (!identityVerifyCrc(identity)) {
    setError(error, errorLen, "identity CRC mismatch");
    return false;
  }
  *out = identity;
  return true;
}

std::string identityToJson(const Identity& identity) {
  char mac[24];
  std::snprintf(mac, sizeof(mac), "%02X:%02X:%02X:%02X:%02X:%02X", identity.mac[0],
                identity.mac[1], identity.mac[2], identity.mac[3], identity.mac[4],
                identity.mac[5]);
  char buffer[768];
  std::snprintf(buffer, sizeof(buffer),
                "{\"product\":\"%.*s\",\"serial\":\"%s\",\"core_rev\":\"%s\","
                "\"panel_rev\":\"%s\",\"pwr_rev\":\"%s\",\"date\":\"%s\",\"batch\":\"%s\","
                "\"mac\":\"%s\",\"calibration_version\":\"%s\",\"test_result\":\"%s\","
                "\"crc32\":%u}",
                static_cast<int>(kIdentityProductLen), identity.product, identity.serial,
                identity.coreRev, identity.panelRev, identity.pwrRev, identity.date,
                identity.batch, mac, identity.calibrationVersion, identity.testResult,
                static_cast<unsigned>(identity.crc32));
  return std::string(buffer);
}

bool identityFromJson(const char* json, Identity* out, char* error, size_t errorLen) {
  if (!json || !out) {
    setError(error, errorLen, "empty identity JSON");
    return false;
  }
  Identity identity;
  if (!jsonString(json, "product", identity.product, sizeof(identity.product))) {
    setError(error, errorLen, "missing product");
    return false;
  }
  if (!jsonString(json, "serial", identity.serial, sizeof(identity.serial))) {
    setError(error, errorLen, "missing serial");
    return false;
  }
  if (!jsonString(json, "core_rev", identity.coreRev, sizeof(identity.coreRev)) ||
      !jsonString(json, "panel_rev", identity.panelRev, sizeof(identity.panelRev)) ||
      !jsonString(json, "pwr_rev", identity.pwrRev, sizeof(identity.pwrRev)) ||
      !jsonString(json, "date", identity.date, sizeof(identity.date)) ||
      !jsonString(json, "batch", identity.batch, sizeof(identity.batch)) ||
      !jsonString(json, "calibration_version", identity.calibrationVersion,
                  sizeof(identity.calibrationVersion)) ||
      !jsonString(json, "test_result", identity.testResult, sizeof(identity.testResult))) {
    setError(error, errorLen, "missing identity field");
    return false;
  }
  char macText[24] = {};
  if (!jsonString(json, "mac", macText, sizeof(macText)) || !parseMac(macText, identity.mac)) {
    setError(error, errorLen, "bad MAC (expected AA:BB:CC:DD:EE:FF)");
    return false;
  }
  uint32_t providedCrc = 0;
  const bool hasCrc = jsonU32(json, "crc32", &providedCrc);
  identitySeal(&identity);
  if (!identityValidate(identity, error, errorLen)) return false;
  if (hasCrc && providedCrc != identity.crc32) {
    setError(error, errorLen, "identity JSON CRC mismatch");
    return false;
  }
  *out = identity;
  return true;
}

void IdentityStore::clear() {
  for (int i = 0; i < kSlots; ++i) {
    slots_[i] = Identity{};
    used_[i] = false;
  }
  slotCount_ = 0;
  usedCount_ = 0;
}

bool IdentityStore::hasSerial(const char* serial) const {
  if (!serial) return false;
  for (int i = 0; i < kSlots; ++i) {
    if (used_[i] && std::strcmp(slots_[i].serial, serial) == 0) return true;
  }
  return false;
}

bool IdentityStore::write(const Identity& identity, char* error, size_t errorLen) {
  Identity sealed = identity;
  identitySeal(&sealed);
  if (!identityValidate(sealed, error, errorLen)) return false;
  if (!identityVerifyCrc(sealed)) {
    setError(error, errorLen, "identity CRC mismatch");
    return false;
  }
  if (hasSerial(sealed.serial)) {
    setError(error, errorLen, "duplicate serial");
    return false;
  }
  const int slot = slotCount_ % kSlots;
  slots_[slot] = sealed;
  used_[slot] = true;
  ++slotCount_;
  if (usedCount_ < kSlots) ++usedCount_;
  setError(error, errorLen, "");
  return true;
}

bool IdentityStore::read(Identity* out, int* slot) const {
  if (!out || usedCount_ == 0) return false;
  for (int attempt = 0; attempt < kSlots; ++attempt) {
    const int index = (slotCount_ - 1 - attempt + kSlots * 2) % kSlots;
    if (!used_[index]) continue;
    Identity copy;
    char error[64];
    if (identityValidate(slots_[index], error, sizeof(error)) &&
        identityVerifyCrc(slots_[index])) {
      *out = slots_[index];
      if (slot) *slot = index;
      return true;
    }
  }
  return false;
}

bool IdentityStore::writeRaw(int slot, const Identity& identity) {
  if (slot < 0 || slot >= kSlots) return false;
  slots_[slot] = identity;
  used_[slot] = true;
  if (usedCount_ < kSlots) ++usedCount_;
  return true;
}

bool IdentityStore::readSlot(int slot, Identity* out) const {
  if (slot < 0 || slot >= kSlots || !used_[slot] || !out) return false;
  *out = slots_[slot];
  return true;
}

}  // namespace factory
}  // namespace bukifon
