// SPDX-License-Identifier: GPL-3.0-or-later
#include "storage/project_v2.hpp"

#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

#include "bukifon_ui_theme.h"

namespace bukifon {
namespace storage {
namespace {

constexpr uint32_t kTagIntp = 0x50544E49u;  // "INTP"
constexpr uint32_t kTagGenp = 0x504E4547u;  // "GENP"
constexpr uint32_t kTagExtp = 0x50545845u;  // "EXTP"
constexpr uint32_t kTagMic1 = 0x3143494Du;  // "MIC1"
constexpr uint32_t kTagMods = 0x53444F4Du;  // "MODS"
constexpr size_t kHeaderBytes = 214;
constexpr size_t kCrcBytes = 4;
constexpr size_t kSectionHeaderBytes = 8;
constexpr size_t kGenPayloadBytes = 1 + (kSeqTracks + kExtTracks) * 12;
constexpr size_t kMicPayloadBytes = 15 + kProjectPadCount * 34;
constexpr size_t kExtCapacity = 4096;

void putU8(std::vector<uint8_t>& out, uint8_t v) { out.push_back(v); }
void putU16(std::vector<uint8_t>& out, uint16_t v) {
  out.push_back(static_cast<uint8_t>(v));
  out.push_back(static_cast<uint8_t>(v >> 8));
}
void putU32(std::vector<uint8_t>& out, uint32_t v) {
  for (int i = 0; i < 4; ++i) out.push_back(static_cast<uint8_t>(v >> (8 * i)));
}
void putF32(std::vector<uint8_t>& out, float v) {
  uint8_t bytes[4];
  std::memcpy(bytes, &v, sizeof(bytes));
  out.insert(out.end(), bytes, bytes + 4);
}
void putBytes(std::vector<uint8_t>& out, const void* data, size_t size) {
  const uint8_t* p = static_cast<const uint8_t*>(data);
  out.insert(out.end(), p, p + size);
}
void putString(std::vector<uint8_t>& out, const char* text, size_t fixed) {
  char buffer[128] = {};
  std::snprintf(buffer, sizeof(buffer), "%s", text ? text : "");
  out.insert(out.end(), buffer, buffer + fixed);
}
void putSectionHeader(std::vector<uint8_t>& out, uint32_t tag, size_t size) {
  putU32(out, tag);
  putU32(out, static_cast<uint32_t>(size));
}

struct Reader {
  const uint8_t* data;
  size_t size;
  size_t pos = 0;
  bool ok = true;
  uint8_t u8() {
    if (pos + 1 > size) { ok = false; return 0; }
    return data[pos++];
  }
  uint16_t u16() {
    if (pos + 2 > size) { ok = false; return 0; }
    const uint16_t v = static_cast<uint16_t>(data[pos] | (data[pos + 1] << 8));
    pos += 2;
    return v;
  }
  uint32_t u32() {
    if (pos + 4 > size) { ok = false; return 0; }
    uint32_t v = 0;
    for (int i = 0; i < 4; ++i) v |= static_cast<uint32_t>(data[pos + i]) << (8 * i);
    pos += 4;
    return v;
  }
  float f32() {
    float v = 0.0f;
    if (pos + 4 > size) { ok = false; return v; }
    std::memcpy(&v, data + pos, 4);
    pos += 4;
    return v;
  }
  void bytes(void* out, size_t count) {
    if (pos + count > size) { ok = false; return; }
    std::memcpy(out, data + pos, count);
    pos += count;
  }
  const uint8_t* at() const { return data + pos; }
};

uint32_t crc32(const uint8_t* data, size_t size) {
  return ExtSequencer::crc32(data, size);
}

bool isHex(const char* text) {
  if (!text) return false;
  for (const char* p = text; *p; ++p) {
    if (!std::isxdigit(static_cast<unsigned char>(*p))) return false;
  }
  return true;
}

}  // namespace

void projectV2Reset(ProjectV2* project) {
  if (!project) return;
  *project = ProjectV2{};
  projectReset(&project->internal);
  project->external.init();
  project->external.setSink(nullptr);
  project->mic = MicConfig{};
  for (int i = 0; i < kProjectPadCount; ++i) project->pads[i] = ProjectMicPad{};
  for (int i = 0; i < kSeqTracks + kExtTracks; ++i) project->gen[i] = GenParams{};
  std::snprintf(project->created, sizeof(project->created), "%s", "1970-01-01T00:00:00Z");
  project->themeId = static_cast<uint8_t>(bukifon_ui_theme_current());
  std::snprintf(project->themeName, sizeof(project->themeName), "%s",
                bukifon_ui_theme_name(project->themeId));
}

void captureProjectV2(const Sequencer& sequencer, ProjectV2* project) {
  if (!project) return;
  projectV2Reset(project);
  captureProject(sequencer, &project->internal);
  project->bpm = sequencer.bpm();
  project->swing = sequencer.swing();
  project->currentPattern = sequencer.patternIndex();
  for (int i = 0; i < kSeqTracks; ++i) project->gen[i] = sequencer.genParams(i);
  project->external = sequencer.external();
  project->external.setSink(nullptr);
  for (int i = 0; i < kExtTracks; ++i) project->gen[kSeqTracks + i] = sequencer.external().genParams(i);
  project->themeId = static_cast<uint8_t>(bukifon_ui_theme_current());
  std::snprintf(project->themeName, sizeof(project->themeName), "%s",
                bukifon_ui_theme_name(project->themeId));
}

bool applyProjectV2(const ProjectV2& project, Sequencer* sequencer) {
  if (!sequencer) return false;
  if (project.version != kProjectV2Version) return false;
  applyProject(project.internal, sequencer);
  sequencer->setBpm(project.bpm);
  sequencer->setSwing(project.swing);
  sequencer->setPatternIndex(project.currentPattern);
  for (int i = 0; i < kSeqTracks; ++i) sequencer->setGenParams(i, project.gen[i]);
  sequencer->external() = project.external;
  sequencer->external().setSink(nullptr);
  for (int i = 0; i < kExtTracks; ++i) {
    sequencer->external().setGenParams(i, project.gen[kSeqTracks + i]);
  }
  if (project.themeId < BUKIFON_UI_THEME_COUNT) {
    bukifon_ui_theme_set(bukifon_ui_theme_name(project.themeId));
  }
  return true;
}

size_t projectV2SerializedSize(const ProjectV2& project) {
  size_t body = kSectionHeaderBytes + projectSerializedSize(project.internal);
  body += kSectionHeaderBytes + kGenPayloadBytes;
  body += kSectionHeaderBytes + project.external.serializedSize();
  body += kSectionHeaderBytes + kMicPayloadBytes;
  size_t mods = 1;
  const int count = project.moduleCount < kMaxProjectModules ? project.moduleCount
                                                             : kMaxProjectModules;
  for (int i = 0; i < count; ++i) {
    mods += 64 + 16 + 65 + 1 + static_cast<size_t>(project.modules[i].paramCount) * 6;
  }
  body += kSectionHeaderBytes + mods;
  return kHeaderBytes + body + kCrcBytes;
}

size_t projectV2Serialize(const ProjectV2& project, uint8_t* out, size_t capacity) {
  if (!out) return 0;
  const size_t total = projectV2SerializedSize(project);
  if (capacity < total) return 0;
  std::vector<uint8_t> buffer;
  buffer.reserve(total);
  putU32(buffer, kProjectV2Magic);
  putU16(buffer, kProjectV2Version);
  putU16(buffer, project.flags);
  putU32(buffer, 0);  // body size placeholder
  putString(buffer, project.name, 64);
  putString(buffer, project.author, 64);
  putString(buffer, project.created, 24);
  putString(buffer, project.appVersion, 16);
  putU16(buffer, static_cast<uint16_t>(std::lround(project.bpm * 10.0f)));
  putU16(buffer, static_cast<uint16_t>(std::lround(project.swing * 1000.0f)));
  putString(buffer, project.faderMode, 10);
  putU8(buffer, static_cast<uint8_t>(project.selectedPart));
  putU8(buffer, static_cast<uint8_t>(project.selectedTrack));
  putU8(buffer, static_cast<uint8_t>(project.currentPattern));
  putU8(buffer, project.themeId);
  putString(buffer, project.themeName, 16);
  if (buffer.size() != kHeaderBytes) return 0;

  std::vector<uint8_t> internalBytes(projectSerializedSize(project.internal));
  const size_t internalSize = projectSerialize(project.internal, internalBytes.data(),
                                               internalBytes.size());
  if (internalSize == 0) return 0;
  putSectionHeader(buffer, kTagIntp, internalSize);
  putBytes(buffer, internalBytes.data(), internalSize);

  std::vector<uint8_t> gen;
  putU8(gen, static_cast<uint8_t>(kSeqTracks + kExtTracks));
  for (int i = 0; i < kSeqTracks + kExtTracks; ++i) {
    const GenParams& g = project.gen[i];
    putU8(gen, g.probability);
    putU8(gen, g.euclid);
    putU8(gen, g.mutate);
    putU8(gen, static_cast<uint8_t>(g.scale));
    putU8(gen, g.evolve ? 1 : 0);
    putU8(gen, g.arpRate);
    putU8(gen, g.arpMode);
    putU8(gen, g.arpOn ? 1 : 0);
    putU32(gen, g.seed);
  }
  if (gen.size() != kGenPayloadBytes) return 0;
  putSectionHeader(buffer, kTagGenp, gen.size());
  putBytes(buffer, gen.data(), gen.size());

  std::vector<uint8_t> ext(kExtCapacity);
  const size_t extSize = project.external.serialize(ext.data(), ext.size());
  if (extSize == 0) return 0;
  putSectionHeader(buffer, kTagExtp, extSize);
  putBytes(buffer, ext.data(), extSize);

  std::vector<uint8_t> mic;
  putU8(mic, static_cast<uint8_t>(project.mic.source));
  putF32(mic, project.mic.gainDb);
  putF32(mic, project.mic.threshold);
  putF32(mic, project.mic.sensitivity);
  putU8(mic, project.mic.monitor ? 1 : 0);
  putU8(mic, project.mic.beatbox ? 1 : 0);
  for (int i = 0; i < kProjectPadCount; ++i) {
    const ProjectMicPad& pad = project.pads[i];
    putU8(mic, pad.used ? 1 : 0);
    putString(mic, pad.name, 24);
    putU32(mic, pad.frames);
    putF32(mic, pad.peak);
    putU8(mic, pad.storage);
  }
  if (mic.size() != kMicPayloadBytes) return 0;
  putSectionHeader(buffer, kTagMic1, mic.size());
  putBytes(buffer, mic.data(), mic.size());

  const int moduleCount = project.moduleCount < kMaxProjectModules ? project.moduleCount
                                                                   : kMaxProjectModules;
  std::vector<uint8_t> mods;
  putU8(mods, static_cast<uint8_t>(moduleCount));
  for (int i = 0; i < moduleCount; ++i) {
    const ProjectModuleState& module = project.modules[i];
    putString(mods, module.id, 64);
    putString(mods, module.version, 16);
    putString(mods, module.sha256, 65);
    const uint8_t paramCount = module.paramCount > 16 ? 16 : module.paramCount;
    putU8(mods, paramCount);
    for (int p = 0; p < paramCount; ++p) {
      putU16(mods, module.params[p].id);
      putF32(mods, module.params[p].value);
    }
  }
  putSectionHeader(buffer, kTagMods, mods.size());
  putBytes(buffer, mods.data(), mods.size());

  const size_t bodySize = buffer.size() - kHeaderBytes;
  for (int i = 0; i < 4; ++i) buffer[8 + i] = static_cast<uint8_t>(bodySize >> (8 * i));
  const uint32_t crc = crc32(buffer.data(), buffer.size());
  putU32(buffer, crc);
  if (buffer.size() != total) return 0;
  std::memcpy(out, buffer.data(), buffer.size());
  return buffer.size();
}

bool projectV2Validate(const ProjectV2& project, char* error, size_t errorLen) {
  if (error && errorLen) error[0] = '\0';
  if (project.version != kProjectV2Version) {
    std::snprintf(error, errorLen, "version %u != %u", project.version, kProjectV2Version);
    return false;
  }
  if (project.bpm < 20.0f || project.bpm > 300.0f) {
    std::snprintf(error, errorLen, "bpm %.1f out of 20..300", static_cast<double>(project.bpm));
    return false;
  }
  if (!(project.swing >= -1.0f && project.swing <= 1.0f)) {
    std::snprintf(error, errorLen, "swing out of -1..1");
    return false;
  }
  if (project.selectedPart < 0 || project.selectedPart >= kSeqTracks ||
      project.selectedTrack < 0 || project.selectedTrack >= kExtTracks) {
    std::snprintf(error, errorLen, "selected part/track out of range");
    return false;
  }
  if (project.themeId >= BUKIFON_UI_THEME_COUNT) {
    std::snprintf(error, errorLen, "theme id %u out of range", project.themeId);
    return false;
  }
  if (project.moduleCount < 0 || project.moduleCount > kMaxProjectModules) {
    std::snprintf(error, errorLen, "module count %d > %d", project.moduleCount, kMaxProjectModules);
    return false;
  }
  for (int i = 0; i < project.moduleCount; ++i) {
    const ProjectModuleState& module = project.modules[i];
    if (module.id[0] == '\0' || module.paramCount > 16) {
      std::snprintf(error, errorLen, "module %d invalid id/param count", i);
      return false;
    }
    if (module.sha256[0] != '\0' && (!isHex(module.sha256) || std::strlen(module.sha256) != 64)) {
      std::snprintf(error, errorLen, "module %d sha256 invalid", i);
      return false;
    }
  }
  return true;
}

bool projectV2Deserialize(const uint8_t* data, size_t size, ProjectV2* out, char* error,
                          size_t errorLen) {
  if (error && errorLen) error[0] = '\0';
  if (!data || !out || size < kHeaderBytes + 1 + kCrcBytes) {
    std::snprintf(error, errorLen, "file too short");
    return false;
  }
  Reader reader{data, size, 0, true};
  if (reader.u32() != kProjectV2Magic) {
    std::snprintf(error, errorLen, "bad magic (not a Bukifon project)");
    return false;
  }
  const uint16_t version = reader.u16();
  if (version == 1) {
    // Migration: v1 .bkfp contains the old project_io payload only.
    ProjectV2 migrated;
    projectV2Reset(&migrated);
    if (!projectDeserialize(data, size, &migrated.internal)) {
      std::snprintf(error, errorLen, "invalid v1 project payload");
      return false;
    }
    migrated.bpm = migrated.internal.bpm;
    migrated.currentPattern = migrated.internal.activePattern;
    if (!projectV2Validate(migrated, error, errorLen)) return false;
    *out = migrated;
    return true;
  }
  if (version != kProjectV2Version) {
    std::snprintf(error, errorLen, "unsupported version %u (want 1 or %u)", version,
                  kProjectV2Version);
    return false;
  }
  ProjectV2 project;
  projectV2Reset(&project);
  project.flags = reader.u16();
  const uint32_t bodySize = reader.u32();
  char text[64];
  reader.bytes(text, 64);
  std::memcpy(project.name, text, sizeof(project.name));
  reader.bytes(text, 64);
  std::memcpy(project.author, text, sizeof(project.author));
  char created[24];
  reader.bytes(created, sizeof(created));
  std::memcpy(project.created, created, sizeof(project.created));
  char app[16];
  reader.bytes(app, sizeof(app));
  std::memcpy(project.appVersion, app, sizeof(project.appVersion));
  project.bpm = static_cast<float>(reader.u16()) / 10.0f;
  project.swing = static_cast<float>(reader.u16()) / 1000.0f;
  char fader[10];
  reader.bytes(fader, sizeof(fader));
  std::memcpy(project.faderMode, fader, sizeof(project.faderMode));
  project.selectedPart = reader.u8();
  project.selectedTrack = reader.u8();
  project.currentPattern = reader.u8();
  project.themeId = reader.u8();
  char theme[16];
  reader.bytes(theme, sizeof(theme));
  std::memcpy(project.themeName, theme, sizeof(project.themeName));
  if (!reader.ok || reader.pos != kHeaderBytes) {
    std::snprintf(error, errorLen, "header truncated");
    return false;
  }
  if (bodySize != size - kHeaderBytes - kCrcBytes) {
    std::snprintf(error, errorLen, "body size %u mismatch file size", bodySize);
    return false;
  }
  const uint32_t storedCrc = Reader{data + size - 4, 4}.u32();
  if (crc32(data, size - 4) != storedCrc) {
    std::snprintf(error, errorLen, "CRC32 mismatch");
    return false;
  }
  const size_t bodyEnd = size - kCrcBytes;
  bool haveInternal = false;
  bool haveGen = false;
  bool haveExt = false;
  while (reader.pos < bodyEnd) {
    if (reader.pos + kSectionHeaderBytes > bodyEnd) {
      std::snprintf(error, errorLen, "truncated section header");
      return false;
    }
    const uint32_t tag = reader.u32();
    const uint32_t sectionSize = reader.u32();
    if (reader.pos + sectionSize > bodyEnd) {
      std::snprintf(error, errorLen, "section 0x%08X overruns file", tag);
      return false;
    }
    const size_t sectionEnd = reader.pos + sectionSize;
    if (tag == kTagIntp) {
      if (!projectDeserialize(reader.at(), sectionSize, &project.internal)) {
        std::snprintf(error, errorLen, "invalid INTP section");
        return false;
      }
      haveInternal = true;
      reader.pos = sectionEnd;
    } else if (tag == kTagGenp) {
      Reader gen{reader.at(), sectionSize, 0, true};
      const uint8_t count = gen.u8();
      if (count != kSeqTracks + kExtTracks) {
        std::snprintf(error, errorLen, "GENP count %u != %u", count, kSeqTracks + kExtTracks);
        return false;
      }
      for (int i = 0; i < kSeqTracks + kExtTracks; ++i) {
        GenParams& g = project.gen[i];
        g.probability = gen.u8();
        g.euclid = gen.u8();
        g.mutate = gen.u8();
        g.scale = static_cast<GenScale>(gen.u8());
        g.evolve = gen.u8() != 0;
        g.arpRate = gen.u8();
        g.arpMode = gen.u8();
        g.arpOn = gen.u8() != 0;
        g.seed = gen.u32();
        if (g.probability > 100 || g.euclid > 16 || g.mutate > 12 ||
            g.scale >= GenScale::kNumScales || g.arpRate >= kNumGenArpRates ||
            g.arpMode >= kNumGenArpModes) {
          std::snprintf(error, errorLen, "GENP part %d out of bounds", i);
          return false;
        }
      }
      if (!gen.ok) {
        std::snprintf(error, errorLen, "GENP truncated");
        return false;
      }
      haveGen = true;
      reader.pos = sectionEnd;
    } else if (tag == kTagExtp) {
      if (!project.external.deserialize(reader.at(), sectionSize)) {
        std::snprintf(error, errorLen, "invalid EXTP section");
        return false;
      }
      haveExt = true;
      reader.pos = sectionEnd;
    } else if (tag == kTagMic1) {
      Reader mic{reader.at(), sectionSize, 0, true};
      project.mic.source = static_cast<MicSource>(mic.u8());
      project.mic.gainDb = mic.f32();
      project.mic.threshold = mic.f32();
      project.mic.sensitivity = mic.f32();
      project.mic.monitor = mic.u8() != 0;
      project.mic.beatbox = mic.u8() != 0;
      for (int i = 0; i < kProjectPadCount; ++i) {
        ProjectMicPad& pad = project.pads[i];
        pad.used = mic.u8() != 0;
        char padName[24];
        mic.bytes(padName, sizeof(padName));
        std::memcpy(pad.name, padName, sizeof(pad.name));
        pad.frames = mic.u32();
        pad.peak = mic.f32();
        pad.storage = mic.u8();
      }
      if (!mic.ok) {
        std::snprintf(error, errorLen, "MIC1 truncated");
        return false;
      }
      reader.pos = sectionEnd;
    } else if (tag == kTagMods) {
      Reader mods{reader.at(), sectionSize, 0, true};
      const uint8_t count = mods.u8();
      if (count > kMaxProjectModules) {
        std::snprintf(error, errorLen, "MODS count %u > %d", count, kMaxProjectModules);
        return false;
      }
      project.moduleCount = count;
      for (int i = 0; i < count; ++i) {
        ProjectModuleState& module = project.modules[i];
        mods.bytes(module.id, sizeof(module.id));
        mods.bytes(module.version, sizeof(module.version));
        mods.bytes(module.sha256, sizeof(module.sha256));
        module.paramCount = mods.u8();
        if (module.paramCount > 16) {
          std::snprintf(error, errorLen, "MODS param count > 16");
          return false;
        }
        for (int p = 0; p < module.paramCount; ++p) {
          module.params[p].id = mods.u16();
          module.params[p].value = mods.f32();
        }
      }
      if (!mods.ok) {
        std::snprintf(error, errorLen, "MODS truncated");
        return false;
      }
      reader.pos = sectionEnd;
    } else {
      // Unknown section: forward-compatible skip.
      reader.pos = sectionEnd;
    }
    if (!reader.ok) {
      std::snprintf(error, errorLen, "section parse error");
      return false;
    }
  }
  if (!haveInternal) {
    std::snprintf(error, errorLen, "missing INTP (internal patterns) section");
    return false;
  }
  project.version = kProjectV2Version;
  project.bpm = project.internal.bpm > 0.0f ? project.bpm : project.internal.bpm;
  if (!projectV2Validate(project, error, errorLen)) return false;
  (void)haveGen;
  (void)haveExt;
  *out = project;  // transactional: only assign after full validation
  return true;
}

bool projectV2Save(const ProjectV2& project, const char* path) {
  if (!path) return false;
  const size_t size = projectV2SerializedSize(project);
  std::vector<uint8_t> buffer(size);
  const size_t written = projectV2Serialize(project, buffer.data(), buffer.size());
  if (written == 0) return false;
  std::FILE* file = std::fopen(path, "wb");
  if (!file) return false;
  const size_t ok = std::fwrite(buffer.data(), 1, written, file);
  std::fclose(file);
  return ok == written;
}

bool projectV2Load(const char* path, ProjectV2* out, char* error, size_t errorLen) {
  if (error && errorLen) error[0] = '\0';
  if (!path || !out) return false;
  std::FILE* file = std::fopen(path, "rb");
  if (!file) {
    std::snprintf(error, errorLen, "cannot open %s", path);
    return false;
  }
  std::fseek(file, 0, SEEK_END);
  const long size = std::ftell(file);
  std::fseek(file, 0, SEEK_SET);
  if (size <= 0) {
    std::fclose(file);
    std::snprintf(error, errorLen, "empty project file");
    return false;
  }
  std::vector<uint8_t> buffer(static_cast<size_t>(size));
  const size_t read = std::fread(buffer.data(), 1, buffer.size(), file);
  std::fclose(file);
  if (read != buffer.size()) {
    std::snprintf(error, errorLen, "short read");
    return false;
  }
  return projectV2Deserialize(buffer.data(), buffer.size(), out, error, errorLen);
}

bool projectV2ToJson(const ProjectV2& project, char* out, size_t capacity) {
  if (!out || capacity == 0) return false;
  std::vector<uint8_t> data(projectV2SerializedSize(project));
  const size_t size = projectV2Serialize(project, data.data(), data.size());
  if (size == 0) return false;
  static const char* hex = "0123456789abcdef";
  std::vector<char> hexData(size * 2 + 1);
  for (size_t i = 0; i < size; ++i) {
    hexData[i * 2] = hex[data[i] >> 4];
    hexData[i * 2 + 1] = hex[data[i] & 0xF];
  }
  hexData[size * 2] = '\0';
  const int written = std::snprintf(
      out, capacity,
      "{\"schema\":\"bukifon.project.v2\",\"name\":\"%s\",\"author\":\"%s\","
      "\"created\":\"%s\",\"app\":\"%s\",\"bpm\":%.1f,\"theme\":\"%s\","
      "\"externalTracks\":8,\"data\":\"%s\"}",
      project.name, project.author, project.created, project.appVersion,
      static_cast<double>(project.bpm), project.themeName, hexData.data());
  return written > 0 && static_cast<size_t>(written) < capacity;
}

bool projectV2FromJson(const char* json, ProjectV2* out, char* error, size_t errorLen) {
  if (error && errorLen) error[0] = '\0';
  if (!json || !out) return false;
  const char* dataKey = std::strstr(json, "\"data\":\"");
  if (!dataKey) {
    std::snprintf(error, errorLen, "missing data");
    return false;
  }
  dataKey += std::strlen("\"data\":\"");
  const char* end = std::strchr(dataKey, '"');
  if (!end) {
    std::snprintf(error, errorLen, "unterminated data");
    return false;
  }
  const size_t hexLen = static_cast<size_t>(end - dataKey);
  if (hexLen % 2 != 0) {
    std::snprintf(error, errorLen, "odd hex length");
    return false;
  }
  std::vector<uint8_t> bytes(hexLen / 2);
  for (size_t i = 0; i < bytes.size(); ++i) {
    auto nibble = [](char c) -> int {
      if (c >= '0' && c <= '9') return c - '0';
      if (c >= 'a' && c <= 'f') return c - 'a' + 10;
      if (c >= 'A' && c <= 'F') return c - 'A' + 10;
      return -1;
    };
    const int hi = nibble(dataKey[i * 2]);
    const int lo = nibble(dataKey[i * 2 + 1]);
    if (hi < 0 || lo < 0) {
      std::snprintf(error, errorLen, "non-hex data");
      return false;
    }
    bytes[i] = static_cast<uint8_t>((hi << 4) | lo);
  }
  return projectV2Deserialize(bytes.data(), bytes.size(), out, error, errorLen);
}

}  // namespace storage
}  // namespace bukifon
