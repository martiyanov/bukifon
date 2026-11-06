// SPDX-License-Identifier: GPL-3.0-or-later
#include "modules/module_manifest.hpp"

#include <cctype>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>

namespace bukifon {
namespace {

const char* findKey(const char* begin, const char* end, const char* key) {
  if (!begin || !end || !key) return nullptr;
  char pattern[64];
  std::snprintf(pattern, sizeof(pattern), "\"%s\"", key);
  const size_t len = std::strlen(pattern);
  for (const char* p = begin; p + len <= end; ++p) {
    if (std::strncmp(p, pattern, len) != 0) continue;
    const char* after = p + len;
    while (after < end && (*after == ' ' || *after == '\t' || *after == '\r' || *after == '\n')) {
      ++after;
    }
    if (after < end && *after == ':') return after;  // key, not a string value
  }
  return nullptr;
}

const char* skipSpace(const char* p, const char* end) {
  while (p && p < end && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) ++p;
  return p;
}

bool getString(const char* begin, const char* end, const char* key, char* out, size_t cap) {
  const char* p = findKey(begin, end, key);
  if (!p) return false;
  p = skipSpace(p, end);
  if (p >= end || *p != ':') return false;
  p = skipSpace(p + 1, end);
  if (p >= end || *p != '"') return false;
  ++p;
  size_t used = 0;
  while (p < end && *p != '"') {
    if (*p == '\\' && p + 1 < end) ++p;
    if (used + 1 < cap) out[used++] = *p;
    ++p;
  }
  if (p >= end) return false;
  out[used] = '\0';
  return used > 0;
}

bool getNumber(const char* begin, const char* end, const char* key, double* out) {
  const char* p = findKey(begin, end, key);
  if (!p) return false;
  p = skipSpace(p, end);
  if (p >= end || *p != ':') return false;
  p = skipSpace(p + 1, end);
  char* numberEnd = nullptr;
  const double value = std::strtod(p, &numberEnd);
  if (numberEnd == p || numberEnd > end) return false;
  *out = value;
  return true;
}

bool isHex64(const char* text) {
  if (!text || std::strlen(text) != 64) return false;
  for (const char* p = text; *p; ++p) {
    if (!std::isxdigit(static_cast<unsigned char>(*p))) return false;
  }
  return true;
}

bool parseSemver(const char* text, uint16_t* major, uint16_t* minor, uint16_t* patch) {
  if (!text) return false;
  unsigned a = 0, b = 0, c = 0;
  char tail = 0;
  if (std::sscanf(text, "%u.%u.%u%c", &a, &b, &c, &tail) != 3) return false;
  if (major) *major = static_cast<uint16_t>(a);
  if (minor) *minor = static_cast<uint16_t>(b);
  if (patch) *patch = static_cast<uint16_t>(c);
  return true;
}

bool idValid(const char* id) {
  if (!id) return false;
  const size_t len = std::strlen(id);
  if (len < 3 || len > 63) return false;
  for (size_t i = 0; i < len; ++i) {
    const char c = id[i];
    if (!(std::islower(static_cast<unsigned char>(c)) || std::isdigit(static_cast<unsigned char>(c)) ||
          c == '.' || c == '_' || c == '-')) {
      return false;
    }
  }
  return true;
}

bool hasToken(const char* begin, const char* end, const char* token) {
  if (!begin || !end || !token) return false;
  const size_t len = std::strlen(token);
  for (const char* p = begin; p + len <= end; ++p) {
    if (std::strncmp(p, token, len) == 0) return true;
  }
  return false;
}

bool parsePermissionList(const char* begin, const char* end, uint32_t* out) {
  const char* p = findKey(begin, end, "permissions");
  if (!p) return false;
  p = skipSpace(p, end);
  if (p >= end || *p != ':') return false;
  p = skipSpace(p + 1, end);
  if (p >= end || *p != '[') return false;
  const char* close = std::strchr(p, ']');
  if (!close || close > end) return false;
  uint32_t mask = 0;
  if (hasToken(p, close, "\"audio\"")) mask |= kPermAudio;
  if (hasToken(p, close, "\"params\"")) mask |= kPermParams;
  if (hasToken(p, close, "\"seq\"")) mask |= kPermSeq;
  if (hasToken(p, close, "\"io\"")) mask |= kPermIo;
  *out = mask;
  return true;
}

bool parseParams(const char* begin, const char* end, ModuleManifest* out, char* error,
                 size_t errorLen) {
  const char* p = findKey(begin, end, "params");
  if (!p) {
    std::snprintf(error, errorLen, "params[] missing");
    return false;
  }
  p = skipSpace(p, end);
  if (p >= end || *p != ':') return false;
  p = skipSpace(p + 1, end);
  if (p >= end || *p != '[') {
    std::snprintf(error, errorLen, "params must be an array");
    return false;
  }
  const char* close = std::strchr(p, ']');
  if (!close || close > end) {
    std::snprintf(error, errorLen, "params array not closed");
    return false;
  }
  int count = 0;
  const char* cursor = p;
  while (cursor < close) {
    const char* open = std::strchr(cursor, '{');
    if (!open || open > close) break;
    const char* objectEnd = std::strchr(open, '}');
    if (!objectEnd || objectEnd > close) break;
    if (count >= kManifestMaxParams) {
      std::snprintf(error, errorLen, "params: >%d entries", kManifestMaxParams);
      return false;
    }
    ModuleParamV2& param = out->params[count];
    double id = 0;
    double minV = 0;
    double maxV = 0;
    double defV = 0;
    if (!getNumber(open, objectEnd, "id", &id)) {
      std::snprintf(error, errorLen, "params[%d].id missing", count);
      return false;
    }
    if (!getString(open, objectEnd, "name", param.name, sizeof(param.name))) {
      std::snprintf(error, errorLen, "params[%d].name missing", count);
      return false;
    }
    getString(open, objectEnd, "type", param.type, sizeof(param.type));
    getString(open, objectEnd, "unit", param.unit, sizeof(param.unit));
    if (!getNumber(open, objectEnd, "min", &minV) || !getNumber(open, objectEnd, "max", &maxV) ||
        !getNumber(open, objectEnd, "default", &defV)) {
      std::snprintf(error, errorLen, "params[%d] min/max/default missing", count);
      return false;
    }
    if (id < 0 || id > 65535) {
      std::snprintf(error, errorLen, "params[%d].id out of range", count);
      return false;
    }
    if (minV >= maxV) {
      std::snprintf(error, errorLen, "params[%d] min >= max", count);
      return false;
    }
    if (defV < minV || defV > maxV) {
      std::snprintf(error, errorLen, "params[%d] default outside min..max", count);
      return false;
    }
    param.id = static_cast<uint16_t>(id);
    param.minValue = static_cast<float>(minV);
    param.maxValue = static_cast<float>(maxV);
    param.defaultValue = static_cast<float>(defV);
    ++count;
    cursor = objectEnd + 1;
  }
  if (count < 1) {
    std::snprintf(error, errorLen, "params: at least 1 parameter required");
    return false;
  }
  out->paramCount = count;
  return true;
}

}  // namespace

const char* modulePermissionName(uint32_t bit) {
  switch (bit) {
    case kPermAudio: return "audio";
    case kPermParams: return "params";
    case kPermSeq: return "seq";
    case kPermIo: return "io";
    default: return "?";
  }
}

bool moduleApiCompatible(uint16_t major, uint16_t minor) {
  return major == kModuleApiMajor && minor <= kModuleApiMinor;
}

bool moduleAbiAccepted(const char* abi) {
  if (!abi || !*abi) return false;
  return std::strcmp(abi, "host") == 0 || std::strcmp(abi, "p4") == 0 ||
         std::strcmp(abi, "s3") == 0 || std::strcmp(abi, "any") == 0;
}

bool moduleManifestParse(const char* json, ModuleManifest* out, char* error,
                         size_t errorLen) {
  if (error && errorLen) error[0] = '\0';
  if (!json || !out) {
    std::snprintf(error, errorLen, "null manifest/output");
    return false;
  }
  const char* begin = json;
  const char* end = json + std::strlen(json);
  while (begin < end && std::isspace(static_cast<unsigned char>(*begin))) ++begin;
  while (end > begin && std::isspace(static_cast<unsigned char>(*(end - 1)))) --end;
  if (begin >= end || *begin != '{' || *(end - 1) != '}') {
    std::snprintf(error, errorLen, "manifest is not a JSON object");
    return false;
  }
  *out = ModuleManifest{};
  if (!getString(begin, end, "schema", out->schema, sizeof(out->schema))) {
    std::snprintf(error, errorLen, "schema missing");
    return false;
  }
  if (std::strcmp(out->schema, "bukifon.module.v2") != 0) {
    std::snprintf(error, errorLen, "unsupported schema '%s' (want bukifon.module.v2)",
                  out->schema);
    return false;
  }
  if (!getString(begin, end, "id", out->id, sizeof(out->id))) {
    std::snprintf(error, errorLen, "id missing");
    return false;
  }
  if (!idValid(out->id)) {
    std::snprintf(error, errorLen, "invalid id '%s' (a-z0-9._-, 3..63)", out->id);
    return false;
  }
  if (!getString(begin, end, "name", out->name, sizeof(out->name))) {
    std::snprintf(error, errorLen, "name missing");
    return false;
  }
  if (!getString(begin, end, "version", out->version, sizeof(out->version))) {
    std::snprintf(error, errorLen, "version missing");
    return false;
  }
  if (!parseSemver(out->version, nullptr, nullptr, nullptr)) {
    std::snprintf(error, errorLen, "version '%s' is not SemVer x.y.z", out->version);
    return false;
  }
  if (!getString(begin, end, "api", out->api, sizeof(out->api))) {
    std::snprintf(error, errorLen, "api missing");
    return false;
  }
  uint16_t apiMajor = 0;
  uint16_t apiMinor = 0;
  if (!parseSemver(out->api, &apiMajor, &apiMinor, nullptr)) {
    std::snprintf(error, errorLen, "api '%s' is not SemVer x.y.z", out->api);
    return false;
  }
  out->apiMajor = apiMajor;
  out->apiMinor = apiMinor;
  if (!moduleApiCompatible(apiMajor, apiMinor)) {
    std::snprintf(error, errorLen, "API %u.%u incompatible (host %u.%u)", apiMajor, apiMinor,
                  kModuleApiMajor, kModuleApiMinor);
    return false;
  }
  if (!getString(begin, end, "author", out->author, sizeof(out->author))) {
    std::snprintf(error, errorLen, "author missing");
    return false;
  }
  if (!getString(begin, end, "abi", out->abi, sizeof(out->abi))) {
    std::snprintf(error, errorLen, "abi missing");
    return false;
  }
  if (!moduleAbiAccepted(out->abi)) {
    std::snprintf(error, errorLen, "unsupported abi target '%s'", out->abi);
    return false;
  }
  if (!parsePermissionList(begin, end, &out->permissions)) {
    std::snprintf(error, errorLen, "permissions missing/invalid");
    return false;
  }
  if (out->permissions == 0 || (out->permissions & ~kPermAll) != 0) {
    std::snprintf(error, errorLen, "permissions must be a non-empty known subset");
    return false;
  }
  if (!getString(begin, end, "dsp", out->dsp, sizeof(out->dsp))) {
    std::snprintf(error, errorLen, "dsp entry missing");
    return false;
  }
  double size = 0;
  if (!getNumber(begin, end, "size", &size) || size <= 0 || size > 64.0 * 1024 * 1024) {
    std::snprintf(error, errorLen, "size missing/out of range (1..64 MiB)");
    return false;
  }
  out->size = static_cast<uint32_t>(size);
  if (!getString(begin, end, "sha256", out->sha256, sizeof(out->sha256))) {
    std::snprintf(error, errorLen, "sha256 missing");
    return false;
  }
  if (!isHex64(out->sha256)) {
    std::snprintf(error, errorLen, "sha256 must be 64 hex chars");
    return false;
  }
  getString(begin, end, "license", out->license, sizeof(out->license));
  getString(begin, end, "description", out->description, sizeof(out->description));
  if (!parseParams(begin, end, out, error, errorLen)) return false;
  for (int i = 0; i < out->paramCount; ++i) {
    for (int j = i + 1; j < out->paramCount; ++j) {
      if (out->params[i].id == out->params[j].id) {
        std::snprintf(error, errorLen, "duplicate param id %u", out->params[i].id);
        return false;
      }
    }
  }
  return true;
}

// --- SHA-256 ---------------------------------------------------------------
namespace {
struct Sha256 {
  uint32_t h[8];
  uint64_t bits;
  uint8_t block[64];
  size_t used;
};
constexpr uint32_t kShaK[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
    0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
    0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
    0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
    0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
    0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
    0xc67178f2};
uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
void transform(Sha256* s, const uint8_t* block) {
  uint32_t w[64];
  for (int i = 0; i < 16; ++i) {
    w[i] = (static_cast<uint32_t>(block[i * 4]) << 24) |
           (static_cast<uint32_t>(block[i * 4 + 1]) << 16) |
           (static_cast<uint32_t>(block[i * 4 + 2]) << 8) | block[i * 4 + 3];
  }
  for (int i = 16; i < 64; ++i) {
    const uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
    const uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }
  uint32_t a = s->h[0], b = s->h[1], c = s->h[2], d = s->h[3];
  uint32_t e = s->h[4], f = s->h[5], g = s->h[6], h = s->h[7];
  for (int i = 0; i < 64; ++i) {
    const uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
    const uint32_t ch = (e & f) ^ (~e & g);
    const uint32_t t1 = h + S1 + ch + kShaK[i] + w[i];
    const uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
    const uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
    const uint32_t t2 = S0 + maj;
    h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
  }
  s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d;
  s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
void shaInit(Sha256* s) {
  s->h[0] = 0x6a09e667; s->h[1] = 0xbb67ae85; s->h[2] = 0x3c6ef372; s->h[3] = 0xa54ff53a;
  s->h[4] = 0x510e527f; s->h[5] = 0x9b05688c; s->h[6] = 0x1f83d9ab; s->h[7] = 0x5be0cd19;
  s->bits = 0;
  s->used = 0;
}
void shaUpdate(Sha256* s, const uint8_t* data, size_t size) {
  for (size_t i = 0; i < size; ++i) {
    s->block[s->used++] = data[i];
    if (s->used == 64) {
      transform(s, s->block);
      s->bits += 512;
      s->used = 0;
    }
  }
}
void shaFinal(Sha256* s, uint8_t out[32]) {
  const uint64_t totalBits = s->bits + static_cast<uint64_t>(s->used) * 8u;
  s->block[s->used++] = 0x80;
  if (s->used > 56) {
    while (s->used < 64) s->block[s->used++] = 0;
    transform(s, s->block);
    s->used = 0;
  }
  while (s->used < 56) s->block[s->used++] = 0;
  for (int i = 7; i >= 0; --i) s->block[s->used++] = static_cast<uint8_t>(totalBits >> (i * 8));
  transform(s, s->block);
  for (int i = 0; i < 8; ++i) {
    out[i * 4] = static_cast<uint8_t>(s->h[i] >> 24);
    out[i * 4 + 1] = static_cast<uint8_t>(s->h[i] >> 16);
    out[i * 4 + 2] = static_cast<uint8_t>(s->h[i] >> 8);
    out[i * 4 + 3] = static_cast<uint8_t>(s->h[i]);
  }
}
}  // namespace

void moduleSha256(const uint8_t* data, size_t size, char outHex[65]) {
  Sha256 state;
  shaInit(&state);
  if (data && size) shaUpdate(&state, data, size);
  uint8_t digest[32];
  shaFinal(&state, digest);
  static const char* hex = "0123456789abcdef";
  for (int i = 0; i < 32; ++i) {
    outHex[i * 2] = hex[digest[i] >> 4];
    outHex[i * 2 + 1] = hex[digest[i] & 0xF];
  }
  outHex[64] = '\0';
}

bool moduleSha256Matches(const uint8_t* data, size_t size, const char* expectedHex) {
  if (!expectedHex) return false;
  char actual[65];
  moduleSha256(data, size, actual);
  return std::strcmp(actual, expectedHex) == 0;
}

}  // namespace bukifon
