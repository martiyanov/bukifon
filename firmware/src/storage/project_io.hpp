// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon project (song) serialisation — patterns + transport, versioned and
// CRC protected.  This is the save/load path used by the host simulator and the
// device preset storage.  Format layout is fixed (no padding) so that
// serialise(save(load(x))) is byte-identical: the determinism test relies on it.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "io/sequencer.hpp"

namespace bukifon {
namespace storage {

constexpr uint16_t kProjectVersion = 1;
constexpr uint32_t kProjectMagic = 0x50464B42u;  // "BKFP" little endian

struct Project {
  uint16_t version = kProjectVersion;
  uint16_t flags = 0;
  float bpm = 120.0f;
  uint8_t activePattern = 0;
  uint8_t patternCount = kNumPatterns;
  uint8_t chainLength = 0;
  uint8_t chain[kMaxPatternChain] = {};
  Pattern patterns[kNumPatterns];
};

void projectReset(Project* project);

// Copy the current sequencer state (all patterns, mutes, tempo, chain) into a
// project structure.
void captureProject(const Sequencer& sequencer, Project* project);
void applyProject(const Project& project, Sequencer* sequencer);

// Serialised size (header + payload + CRC16).
size_t projectSerializedSize(const Project& project);
size_t projectSerialize(const Project& project, uint8_t* out, size_t capacity);
bool projectDeserialize(const uint8_t* data, size_t size, Project* out);

bool projectSaveFile(const Project& project, const char* path);
bool projectLoadFile(const char* path, Project* out);

// CRC16-CCITT (same polynomial as the patch format).
uint16_t projectCrc16(const uint8_t* data, size_t size);

}  // namespace storage
}  // namespace bukifon
