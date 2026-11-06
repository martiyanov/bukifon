// SPDX-License-Identifier: GPL-3.0-or-later
// Module SDK v0.2 — manifest schema + loader validation (docs/60/68).
//
// Schema "bukifon.module.v2":
//   schema, id, name, version, api (semver), author, abi (host|p4|s3|any),
//   permissions ["audio","params","seq","io"], params[], dsp (entry file),
//   size, sha256, license, description.
//
// The loader validates BEFORE any payload execution: schema, bounds, API
// compatibility (major match, host minor >= module minor), ABI target and the
// SHA-256 of the DSP payload.  Invalid manifests are rejected with a readable
// error and are never executed.
#pragma once

#include <cstddef>
#include <cstdint>

namespace bukifon {

constexpr uint16_t kModuleApiMajor = 0;
constexpr uint16_t kModuleApiMinor = 2;
constexpr int kManifestMaxParams = 16;

struct ModuleParamV2 {
  uint16_t id = 0;
  char name[24] = {};
  char type[12] = "float";
  float minValue = 0.0f;
  float maxValue = 1.0f;
  float defaultValue = 0.0f;
  char unit[8] = {};
};

struct ModuleManifest {
  char schema[32] = {};
  char id[64] = {};
  char name[48] = {};
  char version[16] = {};
  char api[16] = {};
  char author[48] = {};
  char abi[16] = {};
  uint32_t permissions = 0;  // bitmask, see ModulePermission
  char dsp[64] = {};
  uint32_t size = 0;
  char sha256[65] = {};
  char license[32] = {};
  char description[160] = {};
  ModuleParamV2 params[kManifestMaxParams];
  int paramCount = 0;
  uint16_t apiMajor = 0;
  uint16_t apiMinor = 0;
};

enum ModulePermission : uint32_t {
  kPermAudio = 1u << 0,
  kPermParams = 1u << 1,
  kPermSeq = 1u << 2,
  kPermIo = 1u << 3,
  kPermAll = 0x0Fu
};

// Parse + validate a v2 manifest.  Error messages are human-readable.
bool moduleManifestParse(const char* json, ModuleManifest* out, char* error,
                         size_t errorLen);
// API compatibility: same major and host minor >= module minor.
bool moduleApiCompatible(uint16_t major, uint16_t minor);
// ABI target accepted by the current build ("host", "p4", "s3" or "any").
bool moduleAbiAccepted(const char* abi);
const char* modulePermissionName(uint32_t bit);

// SHA-256 (lowercase hex) used for manifest payload integrity.
void moduleSha256(const uint8_t* data, size_t size, char outHex[65]);
bool moduleSha256Matches(const uint8_t* data, size_t size, const char* expectedHex);

}  // namespace bukifon
