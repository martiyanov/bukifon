// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstring>
#include <vector>

#include "audio/engine.hpp"
#include "core/patch.hpp"
#include "io/midi_parser.hpp"
#include "io/midi_router.hpp"
#include "test_framework.hpp"
#include "test_helpers.hpp"

using namespace bukifon;

namespace {

class RecordingSink : public MidiSink {
 public:
  void onNoteOn(uint8_t channel, uint8_t note, uint8_t velocity) override {
    noteOns.push_back({channel, note, velocity});
  }
  void onNoteOff(uint8_t channel, uint8_t note, uint8_t velocity) override {
    noteOffs.push_back({channel, note, velocity});
  }
  void onControlChange(uint8_t channel, uint8_t cc, uint8_t value) override {
    ccs.push_back({channel, cc, value});
  }
  void onPitchBend(uint8_t channel, int16_t bend) override { bends.push_back({channel, bend}); }
  void onAftertouch(uint8_t channel, uint8_t value) override { aftertouch.push_back({channel, 0, value}); }
  void onPolyAftertouch(uint8_t channel, uint8_t note, uint8_t value) override { polyAt.push_back({channel, note, value}); }
  void onProgramChange(uint8_t channel, uint8_t program) override { programs.push_back({channel, program}); }
  void onSysEx(const uint8_t* data, size_t length) override {
    sysex.assign(data, data + length);
  }
  void onClock() override { clockCount++; }
  void onStart() override { startCount++; }
  void onStop() override { stopCount++; }
  void onContinue() override { continueCount++; }

  struct Note {
    uint8_t channel, note, velocity;
  };
  struct Cc {
    uint8_t channel, cc, value;
  };
  std::vector<Note> noteOns, noteOffs;
  std::vector<Cc> ccs;
  std::vector<std::pair<uint8_t, int16_t>> bends;
  std::vector<Cc> aftertouch;
  std::vector<Note> polyAt;
  std::vector<std::pair<uint8_t, uint8_t>> programs;
  std::vector<uint8_t> sysex;
  int clockCount = 0, startCount = 0, stopCount = 0, continueCount = 0;
};

}  // namespace

TEST(MidiNoteOnOffAndRunningStatus) {
  RecordingSink sink;
  MidiParser parser(&sink);
  const uint8_t msg[] = {0x90, 60, 100, 62, 90, 0x80, 60, 0, 64, 0};
  parser.feed(msg, sizeof(msg));
  INFO("MIDI notes: noteOns=%zu noteOffs=%zu", sink.noteOns.size(), sink.noteOffs.size());
  CHECK(sink.noteOns.size() == 2);
  CHECK(sink.noteOns[0].note == 60 && sink.noteOns[0].velocity == 100);
  CHECK(sink.noteOns[1].note == 62 && sink.noteOns[1].velocity == 90);
  CHECK(sink.noteOffs.size() == 2);
  CHECK(sink.noteOffs[0].note == 60);
  CHECK(sink.noteOffs[1].note == 64);  // note-on with velocity 0 -> note-off
}

TEST(MidiRealtimeInterleaving) {
  RecordingSink sink;
  MidiParser parser(&sink);
  const uint8_t msg[] = {0x90, 60, 100, 0xF8, 64, 100, 0xF8, 0xFA, 0x80, 60, 0};
  parser.feed(msg, sizeof(msg));
  INFO("MIDI realtime: clocks=%d starts=%d noteOns=%zu", sink.clockCount, sink.startCount,
       sink.noteOns.size());
  CHECK(sink.clockCount == 2);
  CHECK(sink.startCount == 1);
  CHECK(sink.noteOns.size() == 2);  // second note comes from running status
  CHECK(sink.noteOns[0].note == 60);
  CHECK(sink.noteOns[1].note == 64);
  CHECK(sink.noteOffs.size() == 1);
}

TEST(MidiCcBendAftertouchProgram) {
  RecordingSink sink;
  MidiParser parser(&sink);
  const uint8_t cc[] = {0xB0, 74, 100, 1, 64};
  parser.feed(cc, sizeof(cc));
  const uint8_t bendMin[] = {0xE0, 0x00, 0x00};
  const uint8_t bendMax[] = {0xE1, 0x7F, 0x7F};
  parser.feed(bendMin, sizeof(bendMin));
  parser.feed(bendMax, sizeof(bendMax));
  const uint8_t at[] = {0xD2, 64, 0xA2, 60, 90};
  parser.feed(at, sizeof(at));
  const uint8_t pc[] = {0xC3, 5};
  parser.feed(pc, sizeof(pc));
  INFO("MIDI CC: ccs=%zu bends=%zu aftertouch=%zu polys=%zu programs=%zu", sink.ccs.size(),
       sink.bends.size(), sink.aftertouch.size(), sink.polyAt.size(), sink.programs.size());
  CHECK(sink.ccs.size() == 2);
  CHECK(sink.ccs[0].cc == 74 && sink.ccs[0].value == 100);
  CHECK(sink.ccs[1].cc == 1 && sink.ccs[1].value == 64);
  CHECK(sink.bends.size() == 2);
  CHECK(sink.bends[0].second == -8192);
  CHECK(sink.bends[1].second == 8191);
  CHECK(sink.aftertouch.size() == 1 && sink.aftertouch[0].value == 64);
  CHECK(sink.polyAt.size() == 1 && sink.polyAt[0].note == 60);
  CHECK(sink.programs.size() == 1 && sink.programs[0].second == 5);
}

TEST(MidiSysExAndOverflow) {
  RecordingSink sink;
  MidiParser parser(&sink);
  const uint8_t sysex[] = {0xF0, 0x7D, 'P', 'M', 'D', 0x02, 0xF7};
  parser.feed(sysex, sizeof(sysex));
  INFO("MIDI SysEx: length=%zu", sink.sysex.size());
  CHECK(sink.sysex.size() == 5);
  CHECK(sink.sysex[0] == 0x7D);
  CHECK(!parser.inSysEx());

  // Oversized SysEx must not overflow the fixed buffer.
  std::vector<uint8_t> big;
  big.push_back(0xF0);
  for (int i = 0; i < 700; ++i) big.push_back(static_cast<uint8_t>(i & 0x7F));
  big.push_back(0xF7);
  parser.feed(big.data(), big.size());
  CHECK(parser.sysexOverflowed());
  CHECK(!parser.inSysEx());
}

TEST(MidiRouterDrivesEngine) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  engine.setGlobalParam(Part1Voices + 1, 2.0f);  // enable part 1 for channel 1
  MidiRouter router;
  router.setEngine(&engine);
  MidiParser parser(&router);
  const uint8_t on[] = {0x91, 60, 100};  // channel 1 -> part 1 according to default map
  const uint8_t off[] = {0x81, 60, 0};
  parser.feed(on, sizeof(on));
  testutil::Rendered r = testutil::render(engine, 0.1);
  INFO("MIDI router: active voices after note-on=%d (part1=%d)", engine.activeVoices(),
       engine.voicesInPart(1));
  CHECK(engine.voicesInPart(1) == 1);
  CHECK(testutil::allFinite(r));
  parser.feed(off, sizeof(off));
  testutil::render(engine, 0.3);
  CHECK(engine.activeVoices() == 0);
}

TEST(MidiSysExPatchDumpAppliesPatch) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  MidiRouter router;
  router.setEngine(&engine);
  MidiParser parser(&router);

  Patch patch;
  makeFactoryPatch(3, &patch);
  patch.parts[0].v[Cutoff] = 1234.0f;
  patch.global.v[Bpm] = 133.0f;
  uint8_t packed[700];
  const size_t packedLen = patchToSysEx(patch, packed, sizeof(packed));
  std::vector<uint8_t> msg;
  msg.push_back(0xF0);
  msg.push_back(0x7D);
  msg.push_back('P');
  msg.push_back('M');
  msg.push_back('D');
  msg.push_back(0x03);
  for (size_t i = 0; i < packedLen; ++i) msg.push_back(packed[i]);
  msg.push_back(0xF7);
  parser.feed(msg.data(), msg.size());
  INFO("SysEx patch dump: %zu bytes, engine cutoff=%.1f Hz bpm=%.0f", msg.size(),
       engine.partBase(0).v[Cutoff], engine.globals().v[Bpm]);
  CHECK(std::fabs(engine.partBase(0).v[Cutoff] - 1234.0f) < 30.0f);
  CHECK(std::fabs(engine.globals().v[Bpm] - 133.0f) < 2.0f);
}

TEST(MidiVersionRequestReplies) {
  Engine engine;
  engine.init();
  MidiRouter router;
  router.setEngine(&engine);
  std::vector<uint8_t> reply;
  router.setSender([&reply](const uint8_t* d, size_t n) { reply.assign(d, d + n); });
  MidiParser parser(&router);
  const uint8_t req[] = {0xF0, 0x7D, 'P', 'M', 'D', 0x02, 0xF7};
  parser.feed(req, sizeof(req));
  INFO("MIDI version reply: %zu bytes", reply.size());
  CHECK(reply.size() == 8);
  CHECK(reply[0] == 0xF0 && reply[7] == 0xF7);
  CHECK(reply[6] == 0x10);  // version 1.0
}
