// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon project v2 (.bkfp) — one file for the whole instrument state.
//
// Layout: magic/version/flags + metadata/transport header, typed sections
// (internal v1 project payload, GEN, EXTP, mic/pads, modules) and CRC32 over
// the whole file.  Reading is transactional: a damaged/unsupported file never
// modifies the destination object.
//
// Backward compatibility: a v1 .bkfp file (project_io.cpp) is detected by the
// version field and migrated into v2 with defaults for the new sections; the
// patterns/BPM/chain are preserved and the preset bank stays untouched.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "io/ext_sequencer.hpp"
#include "io/gen.hpp"
#include "io/mic.hpp"
#include "storage/project_io.hpp"

namespace bukifon {
namespace storage {

constexpr uint16_t kProjectV2Version = 2;
constexpr uint32_t kProjectV2Magic = kProjectMagic;  // "BKFP"
constexpr int kMaxProjectModules = 8;
constexpr int kProjectPadCount = 8;

struct ProjectMicPad {
  bool used = false;
  char name[24] = {};
  uint32_t frames = 0;
  float peak = 0.0f;
  uint8_t storage = 0;  // MicStorage
};

struct ProjectModuleState {
  char id[64] = {};
  char version[16] = {};
  char sha256[65] = {};
  struct Param {
    uint16_t id = 0;
    float value = 0.0f;
  } params[16];
  uint8_t paramCount = 0;
};

struct ProjectV2 {
  uint16_t version = kProjectV2Version;
  uint16_t flags = 0;
  // Metadata.
  char name[64] = "UNTITLED";
  char author[64] = "BUKIFON";
  char created[24] = "";
  char appVersion[16] = "0.2.0";
  // Transport / UI state.
  float bpm = 120.0f;
  float swing = 0.0f;
  char faderMode[10] = "TRACK";
  int selectedPart = 0;
  int selectedTrack = 0;
  int currentPattern = 0;
  uint8_t themeId = 0;  // BukifonUiThemeId
  char themeName[16] = "Night";
  uint8_t language = 0;  // Lang: 0=RU, 1=EN
  // Internal patterns/parts (v1 project embedded as the INTP section).
  Project internal{};
  GenParams gen[kSeqTracks + kExtTracks] = {};
  // External MIDI tracks (EXTP payload from ExtSequencer).
  ExtSequencer external{};
  // Mic settings + 8 pad descriptors (no audio payload).
  MicConfig mic{};
  ProjectMicPad pads[kProjectPadCount];
  // Installed module identities/parameters (id/version/sha256/params).
  ProjectModuleState modules[kMaxProjectModules];
  int moduleCount = 0;
};

void projectV2Reset(ProjectV2* project);
// Capture the shared sequencer state (patterns, GEN, external tracks) into v2.
void captureProjectV2(const Sequencer& sequencer, ProjectV2* project);
// Apply internal patterns/BPM/GEN/external tracks; returns false on bad state.
bool applyProjectV2(const ProjectV2& project, Sequencer* sequencer);

// Serialisation / parsing.
size_t projectV2SerializedSize(const ProjectV2& project);
size_t projectV2Serialize(const ProjectV2& project, uint8_t* out, size_t capacity);
bool projectV2Deserialize(const uint8_t* data, size_t size, ProjectV2* out,
                          char* error = nullptr, size_t errorLen = 0);
bool projectV2Validate(const ProjectV2& project, char* error = nullptr, size_t errorLen = 0);

bool projectV2Save(const ProjectV2& project, const char* path);
bool projectV2Load(const char* path, ProjectV2* out, char* error = nullptr,
                   size_t errorLen = 0);

// Test/debug JSON: summary fields + hex-encoded binary payload; fromJson
// accepts the same format and reconstructs the project losslessly.
bool projectV2ToJson(const ProjectV2& project, char* out, size_t capacity);
bool projectV2FromJson(const char* json, ProjectV2* out, char* error = nullptr,
                       size_t errorLen = 0);

}  // namespace storage
}  // namespace bukifon
