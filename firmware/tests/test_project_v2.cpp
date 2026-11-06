// SPDX-License-Identifier: GPL-3.0-or-later
// Project v2 (.bkfp): full roundtrip, v1 migration, CRC/version/short-file
// rejection, defaults, EXT/mic/modules sections, determinism, limits and
// preset-bank integration.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "bukifon_ui_theme.h"
#include "storage/preset_bank.hpp"
#include "storage/project_v2.hpp"
#include "test_framework.hpp"

using namespace bukifon;
using namespace bukifon::storage;

namespace {

ProjectV2 makePopulatedProject() {
  ProjectV2 project;
  projectV2Reset(&project);
  std::snprintf(project.name, sizeof(project.name), "%s", "NIGHT DRIVE");
  std::snprintf(project.author, sizeof(project.author), "%s", "firmware-dsp");
  std::snprintf(project.created, sizeof(project.created), "%s", "2026-11-06T12:00:00Z");
  std::snprintf(project.appVersion, sizeof(project.appVersion), "%s", "1.0-rc");
  project.bpm = 137.5f;
  project.swing = 0.54f;
  std::snprintf(project.faderMode, sizeof(project.faderMode), "%s", "SCENE");
  project.selectedPart = 2;
  project.selectedTrack = 6;
  project.currentPattern = 3;
  project.themeId = 2;  // Phosphor
  std::snprintf(project.themeName, sizeof(project.themeName), "%s", "Phosphor");
  // Internal pattern data (v1 payload inside INTP).
  project.internal.bpm = 137.5f;
  project.internal.activePattern = 3;
  for (int t = 0; t < kSeqTracks; ++t) {
    for (int s = 0; s < kSeqSteps; ++s) {
      project.internal.patterns[2].tracks[t].steps[s].active = ((s + t) % 3) == 0;
      project.internal.patterns[2].tracks[t].steps[s].note = static_cast<uint8_t>(48 + t + s);
      project.internal.patterns[2].tracks[t].steps[s].velocity = static_cast<uint8_t>(70 + t);
    }
  }
  // GEN for internal + external parts.
  for (int i = 0; i < kSeqTracks + kExtTracks; ++i) {
    project.gen[i].seed = 1000u + static_cast<uint32_t>(i);
    project.gen[i].probability = static_cast<uint8_t>(40 + i);
    project.gen[i].euclid = static_cast<uint8_t>(i % 9);
    project.gen[i].scale = static_cast<GenScale>(i % static_cast<int>(GenScale::kNumScales));
  }
  // External MIDI tracks.
  for (int t = 0; t < kExtTracks; ++t) {
    ExtTrack& ext = project.external.track(t);
    ext.channel = static_cast<uint8_t>(t + 1);
    ext.program = static_cast<uint8_t>(t * 3);
    ext.muted = (t == 5);
    ext.ccNumber = static_cast<uint8_t>(70 + t);
    for (int s = 0; s < kExtSteps; ++s) {
      ext.steps[s].active = ((s + t) % 2) == 0;
      ext.steps[s].note = static_cast<uint8_t>(36 + t + s);
      ext.steps[s].velocity = static_cast<uint8_t>(80 + t);
      ext.steps[s].length = 25;
      ext.steps[s].ccPlocked = (s % 4 == 0);
      ext.steps[s].ccValue = static_cast<uint8_t>(10 + s);
    }
  }
  // Mic settings and pad descriptors.
  project.mic.source = MicSource::Line;
  project.mic.gainDb = 34.5f;
  project.mic.threshold = 0.031f;
  project.mic.sensitivity = 0.72f;
  project.mic.monitor = true;
  project.mic.beatbox = true;
  for (int p = 0; p < kProjectPadCount; ++p) {
    project.pads[p].used = p < 3;
    std::snprintf(project.pads[p].name, sizeof(project.pads[p].name), "PAD%d", p + 1);
    project.pads[p].frames = 48000u + static_cast<uint32_t>(p);
    project.pads[p].peak = 0.5f + 0.05f * static_cast<float>(p);
    project.pads[p].storage = static_cast<uint8_t>(p % 2);
  }
  // Module identities/last parameter values.
  project.moduleCount = 2;
  std::snprintf(project.modules[0].id, sizeof(project.modules[0].id), "%s",
                "bukifon.mod_tape_delay");
  std::snprintf(project.modules[0].version, sizeof(project.modules[0].version), "%s", "0.2.0");
  std::snprintf(project.modules[0].sha256, sizeof(project.modules[0].sha256),
                "%064x", 0x1234567u);
  project.modules[0].paramCount = 3;
  project.modules[0].params[0] = {0, 0.25f};
  project.modules[0].params[1] = {1, 0.5f};
  project.modules[0].params[2] = {2, 0.75f};
  std::snprintf(project.modules[1].id, sizeof(project.modules[1].id), "%s",
                "bukifon.mod_euclid_arp");
  std::snprintf(project.modules[1].version, sizeof(project.modules[1].version), "%s", "0.2.0");
  project.modules[1].sha256[0] = '\0';
  project.modules[1].paramCount = 1;
  project.modules[1].params[0] = {0, 5.0f};
  return project;
}

}  // namespace

TEST(ProjectV2RoundtripFull) {
  const ProjectV2 original = makePopulatedProject();
  std::vector<uint8_t> bytes(projectV2SerializedSize(original));
  const size_t size = projectV2Serialize(original, bytes.data(), bytes.size());
  CHECK(size == bytes.size());
  ProjectV2 loaded;
  char error[192];
  CHECK(projectV2Deserialize(bytes.data(), size, &loaded, error, sizeof(error)));
  CHECK(std::strcmp(loaded.name, "NIGHT DRIVE") == 0);
  CHECK(std::strcmp(loaded.author, "firmware-dsp") == 0);
  CHECK(std::fabs(loaded.bpm - 137.5f) < 0.01f);
  CHECK(std::fabs(loaded.swing - 0.54f) < 0.001f);
  CHECK(std::strcmp(loaded.faderMode, "SCENE") == 0);
  CHECK(loaded.selectedPart == 2);
  CHECK(loaded.selectedTrack == 6);
  CHECK(loaded.currentPattern == 3);
  CHECK(loaded.themeId == 2);
  CHECK(std::strcmp(loaded.themeName, "Phosphor") == 0);
  CHECK(loaded.internal.patterns[2].tracks[1].steps[2].active);
  CHECK(loaded.internal.patterns[2].tracks[1].steps[2].note == static_cast<uint8_t>(48 + 1 + 2));
  CHECK(loaded.internal.bpm == loaded.bpm);
  CHECK(loaded.gen[0].seed == 1000u);
  CHECK(loaded.gen[4].probability == 44);
  CHECK(loaded.gen[11].scale == static_cast<GenScale>(11 % 5));
  INFO("project v2: full metadata/transport/internal/GEN roundtrip");
}

TEST(ProjectV2ExtTracksRoundtrip) {
  const ProjectV2 original = makePopulatedProject();
  std::vector<uint8_t> bytes(projectV2SerializedSize(original));
  const size_t size = projectV2Serialize(original, bytes.data(), bytes.size());
  ProjectV2 loaded;
  CHECK(projectV2Deserialize(bytes.data(), size, &loaded));
  for (int t = 0; t < kExtTracks; ++t) {
    const ExtTrack& a = original.external.track(t);
    const ExtTrack& b = loaded.external.track(t);
    CHECK(a.channel == b.channel);
    CHECK(a.program == b.program);
    CHECK(a.muted == b.muted);
    CHECK(a.ccNumber == b.ccNumber);
    for (int s = 0; s < kExtSteps; ++s) {
      CHECK(a.steps[s].active == b.steps[s].active);
      CHECK(a.steps[s].note == b.steps[s].note);
      CHECK(a.steps[s].velocity == b.steps[s].velocity);
      CHECK(a.steps[s].length == b.steps[s].length);
      CHECK(a.steps[s].ccPlocked == b.steps[s].ccPlocked);
      CHECK(a.steps[s].ccValue == b.steps[s].ccValue);
    }
  }
  INFO("project v2: 8 external MIDI tracks (ch/PC/note/vel/len/mute/CC p-lock) preserved");
}

TEST(ProjectV2MicPadsAndModules) {
  const ProjectV2 original = makePopulatedProject();
  std::vector<uint8_t> bytes(projectV2SerializedSize(original));
  const size_t size = projectV2Serialize(original, bytes.data(), bytes.size());
  ProjectV2 loaded;
  CHECK(projectV2Deserialize(bytes.data(), size, &loaded));
  CHECK(loaded.mic.source == MicSource::Line);
  CHECK(std::fabs(loaded.mic.gainDb - 34.5f) < 0.001f);
  CHECK(std::fabs(loaded.mic.threshold - 0.031f) < 0.0001f);
  CHECK(std::fabs(loaded.mic.sensitivity - 0.72f) < 0.001f);
  CHECK(loaded.mic.monitor);
  CHECK(loaded.mic.beatbox);
  CHECK(loaded.pads[0].used && loaded.pads[2].used && !loaded.pads[3].used);
  CHECK(std::strcmp(loaded.pads[1].name, "PAD2") == 0);
  CHECK(loaded.pads[2].frames == 48002u);
  CHECK(loaded.moduleCount == 2);
  CHECK(std::strcmp(loaded.modules[0].id, "bukifon.mod_tape_delay") == 0);
  CHECK(loaded.modules[0].paramCount == 3);
  CHECK(std::fabs(loaded.modules[0].params[2].value - 0.75f) < 0.001f);
  CHECK(loaded.modules[1].sha256[0] == '\0');
  INFO("project v2: mic settings/pad descriptors and module id/version/sha/params");
}

TEST(ProjectV2MigrationFromV1) {
  Sequencer seq;
  seq.init(48000.0f);
  seq.setBpm(142.0f);
  seq.setPatternIndex(2);
  seq.step(0, 0).active = true;
  seq.step(0, 0).note = 55;
  Project old;
  captureProject(seq, &old);
  const char* path = "../tests/out/project_v1_for_migration.bkfp";
  CHECK(projectSaveFile(old, path));
  ProjectV2 migrated;
  char error[192];
  CHECK(projectV2Load(path, &migrated, error, sizeof(error)));
  CHECK(migrated.version == kProjectV2Version);
  CHECK(std::fabs(migrated.bpm - 142.0f) < 0.01f);
  CHECK(migrated.internal.activePattern == 2);
  CHECK(migrated.internal.patterns[2].tracks[0].steps[0].active);
  CHECK(migrated.internal.patterns[2].tracks[0].steps[0].note == 55);
  // New sections get defaults; the old file must still load.
  CHECK(migrated.external.track(0).channel == 1);
  CHECK(migrated.moduleCount == 0);
  CHECK(migrated.pads[0].used == false);
  std::remove(path);
  INFO("v1 -> v2 migration: patterns/BPM kept, EXTP/mic/modules defaulted");
}

TEST(ProjectV2RejectsCrcVersionShort) {
  const ProjectV2 original = makePopulatedProject();
  std::vector<uint8_t> bytes(projectV2SerializedSize(original));
  const size_t size = projectV2Serialize(original, bytes.data(), bytes.size());
  ProjectV2 out;
  char error[192];
  std::vector<uint8_t> corrupt = bytes;
  corrupt[size - 5] ^= 0xFF;
  CHECK(!projectV2Deserialize(corrupt.data(), corrupt.size(), &out, error, sizeof(error)));
  CHECK(std::strstr(error, "CRC") != nullptr);
  std::vector<uint8_t> badVersion = bytes;
  badVersion[4] = 9;  // low byte of version
  badVersion[5] = 0;
  CHECK(!projectV2Deserialize(badVersion.data(), badVersion.size(), &out, error, sizeof(error)));
  CHECK(std::strstr(error, "version") != nullptr);
  CHECK(!projectV2Deserialize(bytes.data(), size - 10, &out, error, sizeof(error)));
  CHECK(std::strstr(error, "short") != nullptr || std::strstr(error, "size") != nullptr);
  INFO("project v2 rejects CRC/version/short files with readable errors");
}

TEST(ProjectV2TransactionalNoPartialLoad) {
  const ProjectV2 original = makePopulatedProject();
  std::vector<uint8_t> bytes(projectV2SerializedSize(original));
  const size_t size = projectV2Serialize(original, bytes.data(), bytes.size());
  ProjectV2 out;
  projectV2Reset(&out);
  std::snprintf(out.name, sizeof(out.name), "%s", "SENTINEL");
  bytes[size / 2] ^= 0x5A;
  char error[192];
  CHECK(!projectV2Deserialize(bytes.data(), size, &out, error, sizeof(error)));
  CHECK(std::strcmp(out.name, "SENTINEL") == 0);
  INFO("project v2 load is transactional: failed file never partially overwrites");
}

TEST(ProjectV2DefaultsWhenOptionalSectionsAbsent) {
  ProjectV2 project;
  projectV2Reset(&project);
  project.internal.bpm = 120.0f;
  std::vector<uint8_t> bytes(projectV2SerializedSize(project));
  CHECK(projectV2Serialize(project, bytes.data(), bytes.size()) > 0);
  ProjectV2 loaded;
  CHECK(projectV2Deserialize(bytes.data(), bytes.size(), &loaded));
  CHECK(loaded.moduleCount == 0);
  CHECK(loaded.pads[0].used == false);
  INFO("empty/default project v2 roundtrips with zero modules/pads");
}

TEST(ProjectV2SerializationDeterministic) {
  const ProjectV2 project = makePopulatedProject();
  std::vector<uint8_t> a(projectV2SerializedSize(project));
  std::vector<uint8_t> b(projectV2SerializedSize(project));
  const size_t as = projectV2Serialize(project, a.data(), a.size());
  const size_t bs = projectV2Serialize(project, b.data(), b.size());
  CHECK(as == bs);
  CHECK(as > 0);
  CHECK(std::memcmp(a.data(), b.data(), as) == 0);
  INFO("project v2 serialization is byte-identical for the same state");
}

TEST(ProjectV2LimitsAndValidation) {
  ProjectV2 project = makePopulatedProject();
  char error[192];
  CHECK(projectV2Validate(project, error, sizeof(error)));
  project.moduleCount = kMaxProjectModules + 1;
  CHECK(!projectV2Validate(project, error, sizeof(error)));
  project = makePopulatedProject();
  project.bpm = 999.0f;
  CHECK(!projectV2Validate(project, error, sizeof(error)));
  project = makePopulatedProject();
  project.selectedTrack = 8;
  CHECK(!projectV2Validate(project, error, sizeof(error)));
  project = makePopulatedProject();
  project.gen[0].probability = 200;
  std::vector<uint8_t> bytes(projectV2SerializedSize(project));
  CHECK(projectV2Serialize(project, bytes.data(), bytes.size()) > 0);
  ProjectV2 loaded;
  CHECK(!projectV2Deserialize(bytes.data(), bytes.size(), &loaded, error, sizeof(error)));
  CHECK(std::strstr(error, "GENP") != nullptr);
  INFO("project v2 limits: modules<=8, bpm, selected track, GEN bounds");
}

TEST(ProjectV2JsonRoundtrip) {
  const ProjectV2 project = makePopulatedProject();
  std::vector<char> json(65536);
  CHECK(projectV2ToJson(project, json.data(), json.size()));
  CHECK(std::strstr(json.data(), "\"schema\":\"bukifon.project.v2\"") != nullptr);
  CHECK(std::strstr(json.data(), "\"externalTracks\":8") != nullptr);
  ProjectV2 loaded;
  char error[192];
  CHECK(projectV2FromJson(json.data(), &loaded, error, sizeof(error)));
  CHECK(std::strcmp(loaded.name, project.name) == 0);
  CHECK(std::fabs(loaded.bpm - project.bpm) < 0.01f);
  CHECK(loaded.external.track(7).steps[15].ccValue == project.external.track(7).steps[15].ccValue);
  INFO("project v2 toJson/fromJson roundtrip (summary + hex payload)");
}

TEST(ProjectV2PresetBankIntegration) {
  PresetBank bank;
  GenParams gen[kSeqTracks];
  gen[0].seed = 777;
  CHECK(bank.writeSlot(0, "TECHNO", gen, kSeqTracks, 1));
  CHECK(bank.writeSlot(7, "EVOLVE", gen, kSeqTracks, 0x0F));
  const char* presetPath = "../tests/out/project_v2_presets.bin";
  CHECK(bank.save(presetPath));
  ProjectV2 project = makePopulatedProject();
  const char* projectPath = "../tests/out/project_v2_presets.bkfp";
  CHECK(projectV2Save(project, projectPath));
  PresetBank loadedBank;
  CHECK(loadedBank.load(presetPath));
  CHECK(loadedBank.usedCount() == 2);
  CHECK(std::strcmp(loadedBank.slotName(7), "EVOLVE") == 0);
  ProjectV2 loadedProject;
  CHECK(projectV2Load(projectPath, &loadedProject));
  CHECK(loadedProject.moduleCount == 2);
  std::remove(presetPath);
  std::remove(projectPath);
  INFO("project v2 save/load does not conflict with 8-slot preset bank");
}

TEST(ProjectV2ApplyToSequencer) {
  ProjectV2 project = makePopulatedProject();
  Sequencer seq;
  seq.init(48000.0f);
  CHECK(applyProjectV2(project, &seq));
  CHECK(std::fabs(seq.bpm() - 137.5f) < 0.01f);
  CHECK(std::fabs(seq.swing() - 0.54f) < 0.01f);
  CHECK(seq.patternIndex() == 3);
  CHECK(seq.genParams(0).seed == 1000u);
  CHECK(seq.external().track(0).channel == 1);
  CHECK(seq.external().track(7).program == 21);
  CHECK(seq.external().track(5).muted);
  INFO("project v2 applies patterns/GEN/EXT/transport to the shared sequencer");
}

TEST(ProjectV2CaptureFromSequencer) {
  Sequencer seq;
  seq.init(48000.0f);
  seq.setBpm(123.0f);
  seq.setSwing(0.33f);
  seq.setPatternIndex(1);
  seq.setGenSeed(0, 4242u);
  seq.external().track(2).channel = 11;
  seq.external().track(2).program = 42;
  ProjectV2 project;
  captureProjectV2(seq, &project);
  CHECK(std::fabs(project.bpm - 123.0f) < 0.01f);
  CHECK(std::fabs(project.swing - 0.33f) < 0.01f);
  CHECK(project.currentPattern == 1);
  CHECK(project.gen[0].seed == 4242u);
  CHECK(project.external.track(2).channel == 11);
  CHECK(project.external.track(2).program == 42);
  CHECK(project.internal.activePattern == 1);
  INFO("project v2 captures the shared sequencer into one state");
}

TEST(ProjectV2LoadMissingFile) {
  ProjectV2 out;
  char error[192];
  CHECK(!projectV2Load("../tests/out/does_not_exist_v2.bkfp", &out, error, sizeof(error)));
  CHECK(std::strstr(error, "cannot open") != nullptr);
  INFO("project v2 load reports a missing file without touching the output");
}
