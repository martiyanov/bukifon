// SPDX-License-Identifier: GPL-3.0-or-later
#include "storage/project_io.hpp"

#include <cstdio>
#include <cstring>
#include <new>

#include "core/patch.hpp"

namespace bukifon {
namespace storage {
namespace {

constexpr size_t kHeaderBytes = 30;  // magic..chain (see below)
constexpr size_t kTrackHeaderBytes = 4;
constexpr size_t kStepBytes = 11;
constexpr size_t kPlockBytes = 2;
constexpr size_t kModBytes = 5;
constexpr size_t kCrcBytes = 2;

void writeU8(uint8_t* out, size_t* pos, uint8_t v) { out[(*pos)++] = v; }
void writeU16(uint8_t* out, size_t* pos, uint16_t v) {
  out[(*pos)++] = static_cast<uint8_t>(v & 0xFF);
  out[(*pos)++] = static_cast<uint8_t>((v >> 8) & 0xFF);
}
void writeF32(uint8_t* out, size_t* pos, float v) {
  std::memcpy(out + *pos, &v, sizeof(float));
  *pos += sizeof(float);
}

uint8_t readU8(const uint8_t* in, size_t* pos) { return in[(*pos)++]; }
uint16_t readU16(const uint8_t* in, size_t* pos) {
  const uint16_t v = static_cast<uint16_t>(in[*pos] | (in[*pos + 1] << 8));
  *pos += 2;
  return v;
}
float readF32(const uint8_t* in, size_t* pos) {
  float v = 0.0f;
  std::memcpy(&v, in + *pos, sizeof(float));
  *pos += sizeof(float);
  return v;
}

size_t patternTracksSize() {
  return static_cast<size_t>(kMaxSeqTracks) *
         (kTrackHeaderBytes + kSeqSteps * (kStepBytes + kPlocksPerStep * kPlockBytes) +
          kStepMods * kModBytes);
}

size_t payloadSize(size_t patternCount) {
  // One patternCount byte followed by patternCount blocks of tracks.
  return 1 + static_cast<size_t>(patternCount) * patternTracksSize();
}

void serializeTrack(uint8_t* out, size_t* pos, const SequenceTrack& track) {
  writeU8(out, pos, track.muted ? 1 : 0);
  writeU8(out, pos, track.length);
  writeU8(out, pos, track.speed);
  writeU8(out, pos, track.modCount);
  for (int s = 0; s < kSeqSteps; ++s) {
    const SequenceStep& step = track.steps[s];
    writeU8(out, pos, step.note);
    writeU8(out, pos, step.velocity);
    writeU8(out, pos, step.gate);
    writeU8(out, pos, step.condition);
    writeU8(out, pos, step.condA);
    writeU8(out, pos, step.condB);
    writeU8(out, pos, step.percent);
    writeU8(out, pos, static_cast<uint8_t>(step.soundLock));
    writeU8(out, pos, static_cast<uint8_t>(step.micro));
    writeU8(out, pos, step.active ? 1 : 0);
    writeU8(out, pos, step.plockCount);
    for (int p = 0; p < kPlocksPerStep; ++p) {
      writeU8(out, pos, step.plocks[p].param);
      writeU8(out, pos, step.plocks[p].value);
    }
  }
  for (int m = 0; m < kStepMods; ++m) {
    writeU8(out, pos, track.mods[m].mode);
    writeF32(out, pos, track.mods[m].value);
  }
}

bool deserializeTrack(const uint8_t* in, size_t* pos, size_t end, SequenceTrack* track) {
  if (*pos + kTrackHeaderBytes > end) return false;
  track->muted = readU8(in, pos) != 0;
  track->length = readU8(in, pos);
  track->speed = readU8(in, pos);
  track->modCount = readU8(in, pos);
  if (track->length < 1 || track->length > kSeqSteps) return false;
  if (track->speed < 1 || track->speed > 8) return false;
  if (track->modCount > kStepMods) return false;
  for (int s = 0; s < kSeqSteps; ++s) {
    if (*pos + kStepBytes + kPlocksPerStep * kPlockBytes > end) return false;
    SequenceStep& step = track->steps[s];
    step.note = readU8(in, pos);
    step.velocity = readU8(in, pos);
    step.gate = readU8(in, pos);
    step.condition = readU8(in, pos);
    step.condA = readU8(in, pos);
    step.condB = readU8(in, pos);
    step.percent = readU8(in, pos);
    step.soundLock = static_cast<int8_t>(readU8(in, pos));
    step.micro = static_cast<int8_t>(readU8(in, pos));
    step.active = readU8(in, pos) != 0;
    step.plockCount = readU8(in, pos);
    if (step.plockCount > kPlocksPerStep) return false;
    for (int p = 0; p < kPlocksPerStep; ++p) {
      step.plocks[p].param = readU8(in, pos);
      step.plocks[p].value = readU8(in, pos);
    }
  }
  for (int m = 0; m < kStepMods; ++m) {
    track->mods[m].mode = readU8(in, pos);
    track->mods[m].value = readF32(in, pos);
    if (track->mods[m].mode >= StepModulator::kNumModes) return false;
  }
  return true;
}

}  // namespace

uint16_t projectCrc16(const uint8_t* data, size_t size) {
  return crc16Ccitt(data, size);
}

void projectReset(Project* project) {
  if (!project) return;
  *project = Project{};
}

void captureProject(const Sequencer& sequencer, Project* project) {
  if (!project) return;
  projectReset(project);
  project->bpm = sequencer.bpm();
  project->activePattern = static_cast<uint8_t>(sequencer.patternIndex());
  project->patternCount = kNumPatterns;
  project->chainLength = static_cast<uint8_t>(sequencer.chainLength());
  if (sequencer.chainLength() > 0) {
    std::memcpy(project->chain, sequencer.chain(), static_cast<size_t>(sequencer.chainLength()));
  }
  for (int p = 0; p < kNumPatterns; ++p) project->patterns[p] = sequencer.pattern(p);
}

void applyProject(const Project& project, Sequencer* sequencer) {
  if (!sequencer) return;
  for (int p = 0; p < kNumPatterns; ++p) sequencer->pattern(p) = project.patterns[p];
  sequencer->setPatternIndex(project.activePattern);
  sequencer->setBpm(project.bpm);
  sequencer->setChain(project.chain, project.chainLength);
}

size_t projectSerializedSize(const Project& project) {
  const size_t count = project.patternCount > kNumPatterns ? kNumPatterns : project.patternCount;
  return kHeaderBytes + payloadSize(count) + kCrcBytes;
}

size_t projectSerialize(const Project& project, uint8_t* out, size_t capacity) {
  if (!out) return 0;
  const size_t count = project.patternCount > kNumPatterns ? kNumPatterns : project.patternCount;
  const size_t total = kHeaderBytes + payloadSize(count) + kCrcBytes;
  if (capacity < total) return 0;
  size_t pos = 0;
  writeU16(out, &pos, static_cast<uint16_t>(kProjectMagic & 0xFFFF));
  writeU16(out, &pos, static_cast<uint16_t>((kProjectMagic >> 16) & 0xFFFF));
  writeU16(out, &pos, project.version);
  writeU16(out, &pos, project.flags);
  writeU16(out, &pos, static_cast<uint16_t>(project.bpm * 10.0f + 0.5f));
  writeU8(out, &pos, project.activePattern);
  writeU8(out, &pos, static_cast<uint8_t>(count));
  writeU8(out, &pos, project.chainLength);
  writeU8(out, &pos, 0);  // reserved
  for (int i = 0; i < kMaxPatternChain; ++i) writeU8(out, &pos, project.chain[i]);
  // Header must be exactly kHeaderBytes.
  while (pos < kHeaderBytes) writeU8(out, &pos, 0);
  writeU8(out, &pos, static_cast<uint8_t>(count));
  for (size_t p = 0; p < count; ++p) {
    for (int t = 0; t < kMaxSeqTracks; ++t) serializeTrack(out, &pos, project.patterns[p].tracks[t]);
  }
  const uint16_t crc = projectCrc16(out, pos);
  out[pos++] = static_cast<uint8_t>(crc & 0xFF);
  out[pos++] = static_cast<uint8_t>(crc >> 8);
  return pos;
}

bool projectDeserialize(const uint8_t* data, size_t size, Project* out) {
  if (!data || !out || size < kHeaderBytes + kCrcBytes + 1) return false;
  size_t pos = 0;
  const uint32_t magic =
      static_cast<uint32_t>(readU16(data, &pos)) | (static_cast<uint32_t>(readU16(data, &pos)) << 16);
  if (magic != kProjectMagic) return false;
  Project project;
  project.version = readU16(data, &pos);
  if (project.version != kProjectVersion) return false;  // explicit version field
  project.flags = readU16(data, &pos);
  project.bpm = static_cast<float>(readU16(data, &pos)) / 10.0f;
  project.activePattern = readU8(data, &pos);
  const uint8_t patternCount = readU8(data, &pos);
  project.chainLength = readU8(data, &pos);
  (void)readU8(data, &pos);  // reserved
  if (patternCount > kNumPatterns) return false;
  if (project.chainLength > kMaxPatternChain) return false;
  if (project.activePattern >= patternCount && patternCount > 0) return false;
  for (int i = 0; i < kMaxPatternChain; ++i) project.chain[i] = readU8(data, &pos);
  if (pos != kHeaderBytes) return false;
  const size_t expected = kHeaderBytes + payloadSize(patternCount) + kCrcBytes;
  if (size != expected) return false;
  const uint16_t stored =
      static_cast<uint16_t>(data[size - 2]) | (static_cast<uint16_t>(data[size - 1]) << 8);
  if (projectCrc16(data, size - 2) != stored) return false;
  const uint8_t payloadPatternCount = readU8(data, &pos);
  if (payloadPatternCount != patternCount) return false;
  for (size_t p = 0; p < patternCount; ++p) {
    for (int t = 0; t < kMaxSeqTracks; ++t) {
      if (!deserializeTrack(data, &pos, size - kCrcBytes, &project.patterns[p].tracks[t])) {
        return false;
      }
    }
  }
  if (pos != size - kCrcBytes) return false;
  *out = project;
  return true;
}

bool projectSaveFile(const Project& project, const char* path) {
  if (!path) return false;
  const size_t size = projectSerializedSize(project);
  uint8_t* buffer = new (std::nothrow) uint8_t[size];
  if (!buffer) return false;
  const size_t written = projectSerialize(project, buffer, size);
  bool ok = written != 0;
  if (ok) {
    FILE* f = std::fopen(path, "wb");
    ok = f != nullptr && std::fwrite(buffer, 1, written, f) == written;
    if (f) std::fclose(f);
  }
  delete[] buffer;
  return ok;
}

bool projectLoadFile(const char* path, Project* out) {
  if (!path || !out) return false;
  FILE* f = std::fopen(path, "rb");
  if (!f) return false;
  std::fseek(f, 0, SEEK_END);
  const long fileSize = std::ftell(f);
  std::fseek(f, 0, SEEK_SET);
  if (fileSize <= 0) {
    std::fclose(f);
    return false;
  }
  uint8_t* buffer = new (std::nothrow) uint8_t[static_cast<size_t>(fileSize)];
  if (!buffer) {
    std::fclose(f);
    return false;
  }
  const size_t size = std::fread(buffer, 1, static_cast<size_t>(fileSize), f);
  std::fclose(f);
  const bool ok = projectDeserialize(buffer, size, out);
  delete[] buffer;
  return ok;
}

}  // namespace storage
}  // namespace bukifon
