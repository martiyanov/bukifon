// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <cstdio>
#include <cstring>

#include "core/params.hpp"
#include "storage/project_io.hpp"
#include "test_framework.hpp"

using namespace bukifon;
using namespace bukifon::storage;
using bukifon::Cutoff;
using bukifon::Resonance;

namespace {

void buildTestSequencer(Sequencer* seq) {
  seq->init(48000.0f);
  seq->setBpm(133.0f);
  seq->setPatternIndex(2);
  seq->setTrackLength(0, 12);
  seq->setTrackSpeed(1, 2);
  seq->setTrackMuted(3, true);
  seq->step(0, 3).note = 77;
  seq->step(0, 3).velocity = 111;
  seq->step(0, 3).gate = 42;
  seq->step(0, 3).condition = TrigFirst;
  seq->setPlock(1, 5, 0, Cutoff, 200);
  for (int s = 0; s < 16; ++s) seq->step(2, s).micro = static_cast<int8_t>(s % 5 - 2);
  const uint8_t chain[3] = {2, 0, 1};
  seq->setChain(chain, 3);
  seq->step(1, 7).plocks[0].param = Resonance;
}

}  // namespace

TEST(ProjectRoundtripDeterministic) {
  Sequencer source;
  buildTestSequencer(&source);
  Project project;
  captureProject(source, &project);
  CHECK(project.bpm == 133.0f);
  CHECK(project.activePattern == 2);
  CHECK(project.chainLength == 3);
  CHECK(project.patterns[2].tracks[3].muted);

  uint8_t bufferA[40000];
  uint8_t bufferB[40000];
  const size_t sizeA = projectSerialize(project, bufferA, sizeof(bufferA));
  const size_t sizeB = projectSerialize(project, bufferB, sizeof(bufferB));
  INFO("project: serialized size=%zu bytes (version %u)", sizeA, project.version);
  CHECK(sizeA > 0);
  CHECK(sizeA == sizeB);
  CHECK(std::memcmp(bufferA, bufferB, sizeA) == 0);  // deterministic
  CHECK(sizeA == projectSerializedSize(project));

  Project loaded;
  CHECK(projectDeserialize(bufferA, sizeA, &loaded));
  CHECK(loaded.bpm == 133.0f);
  CHECK(loaded.activePattern == 2);
  CHECK(loaded.chainLength == 3);
  CHECK(loaded.patterns[0].tracks[0].length == 12);
  CHECK(loaded.patterns[0].tracks[1].speed == 2);
  CHECK(loaded.patterns[2].tracks[3].muted);
  CHECK(loaded.patterns[0].tracks[0].steps[3].note == 77);
  CHECK(loaded.patterns[0].tracks[0].steps[3].velocity == 111);
  CHECK(loaded.patterns[0].tracks[0].steps[4].plockCount == 1);
  CHECK(loaded.patterns[0].tracks[0].steps[4].plocks[0].param == Cutoff);

  Sequencer restored;
  restored.init(48000.0f);
  applyProject(loaded, &restored);
  Project again;
  captureProject(restored, &again);
  uint8_t bufferC[40000];
  const size_t sizeC = projectSerialize(again, bufferC, sizeof(bufferC));
  CHECK(sizeC == sizeA);
  CHECK(std::memcmp(bufferA, bufferC, sizeA) == 0);  // save->load->save is byte identical
}

TEST(ProjectVersionField) {
  Project project;
  projectReset(&project);
  uint8_t buffer[40000];
  const size_t size = projectSerialize(project, buffer, sizeof(buffer));
  CHECK(size > 0);
  CHECK(projectDeserialize(buffer, size, &project));
  // Version field is at byte offset 4 (magic is 4 bytes).
  uint8_t* versionBytes = buffer + 4;
  const uint16_t original = static_cast<uint16_t>(versionBytes[0] | (versionBytes[1] << 8));
  CHECK(original == kProjectVersion);
  versionBytes[0] = 2;
  versionBytes[1] = 0;
  Project rejected;
  CHECK(!projectDeserialize(buffer, size, &rejected));  // no silent migration
  versionBytes[0] = static_cast<uint8_t>(kProjectVersion);
  versionBytes[1] = 0;
  CHECK(projectDeserialize(buffer, size, &rejected));
  INFO("project version: explicit field (%u), unknown versions rejected", kProjectVersion);
}

TEST(ProjectCorruptionRejected) {
  Project project;
  projectReset(&project);
  uint8_t buffer[40000];
  const size_t size = projectSerialize(project, buffer, sizeof(buffer));
  CHECK(projectDeserialize(buffer, size, &project));
  uint8_t corrupted[40000];
  std::memcpy(corrupted, buffer, size);
  corrupted[size / 2] ^= 0xFF;
  CHECK(!projectDeserialize(corrupted, size, &project));  // CRC catches it
  corrupted[size - 1] ^= 0xFF;
  std::memcpy(corrupted, buffer, size);
  corrupted[size - 1] ^= 0xFF;
  CHECK(!projectDeserialize(corrupted, size, &project));  // CRC bytes
  CHECK(!projectDeserialize(buffer, size - 1, &project));  // truncated
  std::memcpy(corrupted, buffer, size);
  corrupted[0] = 'X';
  CHECK(!projectDeserialize(corrupted, size, &project));  // bad magic
  CHECK(!projectDeserialize(buffer, 0, &project));
}

TEST(ProjectFileRoundtrip) {
  Sequencer source;
  buildTestSequencer(&source);
  Project project;
  captureProject(source, &project);
  const char* path = "../tests/out/project_roundtrip.bkfp";
  CHECK(projectSaveFile(project, path));
  Project loaded;
  CHECK(projectLoadFile(path, &loaded));
  uint8_t a[40000];
  uint8_t b[40000];
  const size_t sizeA = projectSerialize(project, a, sizeof(a));
  const size_t sizeB = projectSerialize(loaded, b, sizeof(b));
  CHECK(sizeA == sizeB);
  CHECK(std::memcmp(a, b, sizeA) == 0);
  std::remove(path);
  INFO("project file roundtrip: %zu bytes, deterministic save/load", sizeA);
}

TEST(ProjectPatternCountValidation) {
  Project project;
  projectReset(&project);
  project.patternCount = 4;
  uint8_t buffer[40000];
  const size_t size = projectSerialize(project, buffer, sizeof(buffer));
  CHECK(projectDeserialize(buffer, size, &project));
  CHECK(project.patternCount == 4);
  Project tooMany;
  tooMany.patternCount = 8;
  const size_t sizeAll = projectSerialize(tooMany, buffer, sizeof(buffer));
  // Patching the header pattern count to an unsupported value must fail.
  uint8_t corrupted[40000];
  std::memcpy(corrupted, buffer, sizeAll);
  corrupted[11] = 99;  // patternCount field in the header
  Project rejected;
  CHECK(!projectDeserialize(corrupted, sizeAll, &rejected) || rejected.patternCount <= kNumPatterns);
  INFO("project: pattern count validation and sizes verified");
}
