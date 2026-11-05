// SPDX-License-Identifier: GPL-3.0-or-later
// External MIDI sequencer v1.0-rc tests (docs/70): 8 tracks, channel/PC,
// notes/velocity/length, CC p-lock, GEN, transport, clock, live record,
// save/load (versioned CRC32) and DIN+USB no-duplicate routing.
#include <cstdint>
#include <cstring>
#include <vector>

#include "io/ext_sequencer.hpp"
#include "io/sequencer.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

struct ExtCapture : ExtSeqSink {
  struct Note { int track, channel, note, velocity; };
  std::vector<Note> ons;
  std::vector<Note> offs;
  std::vector<int> programs;
  std::vector<int> ccs;
  int clocks = 0;
  int starts = 0;
  int stops = 0;
  int continues = 0;
  void onExtNoteOn(int t, int ch, int n, int v) override { ons.push_back({t, ch, n, v}); }
  void onExtNoteOff(int t, int ch, int n) override { offs.push_back({t, ch, n, 0}); }
  void onExtProgramChange(int, int, int p) override { programs.push_back(p); }
  void onExtControlChange(int, int, int cc, int v) override { ccs.push_back(cc * 128 + v); }
  void onExtClock() override { ++clocks; }
  void onExtStart() override { ++starts; }
  void onExtStop() override { ++stops; }
  void onExtContinue() override { ++continues; }
};


void makeTrackPattern(ExtSequencer& seq) {
  ExtTrack& track = seq.track(0);
  for (int s = 0; s < kExtSteps; ++s) {
    track.steps[s].active = true;
    track.steps[s].note = static_cast<uint8_t>(60 + s);
    track.steps[s].velocity = 100;
    track.steps[s].length = 50;
  }
  for (int t = 1; t < kExtTracks; ++t) {
    for (int s = 0; s < kExtSteps; ++s) seq.track(t).steps[s].active = false;
  }
}

}  // namespace

TEST(ExtTracksDefaults) {
  ExtSequencer seq;
  seq.init(48000.0f);
  CHECK(seq.trackCount() == 8);
  CHECK(seq.stepCount() == 16);
  for (int t = 0; t < 8; ++t) {
    CHECK(seq.track(t).channel == t + 1);
    CHECK(seq.track(t).program == t);
    CHECK(!seq.track(t).muted);
  }
  CHECK(seq.bpm() == 120.0f);
  CHECK(seq.clockMaster());
  INFO("8 external tracks: default CH1..CH8, PC0..PC7, 16 steps each");
}

TEST(ExtChannelProgramBounds) {
  ExtSequencer seq;
  seq.init(48000.0f);
  seq.setChannel(0, 16);
  CHECK(seq.track(0).channel == 16);
  seq.setChannel(0, 99);
  CHECK(seq.track(0).channel == 16);
  seq.setChannel(1, 0);
  CHECK(seq.track(1).channel == 1);
  seq.setProgram(0, 127);
  CHECK(seq.track(0).program == 127);
  seq.setProgram(0, 200);
  CHECK(seq.track(0).program == 127);
  INFO("channel clamped 1..16, program clamped 0..127");
}

TEST(ExtMuteStopsNotes) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  makeTrackPattern(seq);
  seq.setTrackMuted(0, true);
  seq.start();
  seq.process(12000);  // two steps at 120 BPM
  CHECK(sink.ons.empty());
  seq.setTrackMuted(0, false);
  seq.process(12000);
  CHECK(!sink.ons.empty());
  INFO("mute suppresses external notes; unmute resumes");
}

TEST(ExtNoteVelocityLength) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  makeTrackPattern(seq);
  ExtTrack& track = seq.track(0);
  track.steps[0].note = 42;
  track.steps[0].velocity = 77;
  track.steps[0].length = 25;
  seq.start();
  seq.process(1500);  // a quarter of the 6000-sample step
  CHECK(!sink.ons.empty());
  if (!sink.ons.empty()) {
    CHECK(sink.ons[0].note == 42);
    CHECK(sink.ons[0].velocity == 77);
    CHECK(sink.ons[0].channel == 1);
  }
  // Gate length 25% => note-off before the next step.
  seq.process(2000);
  CHECK(!sink.offs.empty());
  INFO("note/velocity/length: 42/77/25% on CH1, note-off within the step");
}

TEST(ExtCcPlockPerStep) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  makeTrackPattern(seq);
  ExtTrack& track = seq.track(0);
  track.ccNumber = 74;
  track.steps[0].ccPlocked = true;
  track.steps[0].ccValue = 100;
  track.steps[1].ccPlocked = false;
  track.steps[2].ccPlocked = true;
  track.steps[2].ccValue = 20;
  seq.start();
  seq.process(6000 * 3);
  CHECK(sink.ccs.size() == 2);
  if (sink.ccs.size() == 2) {
    CHECK(sink.ccs[0] == 74 * 128 + 100);
    CHECK(sink.ccs[1] == 74 * 128 + 20);
  }
  INFO("1 CC p-lock per step: CC74 value 100/20 sent only on p-locked steps");
}

TEST(ExtTransportAndProgramChanges) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  seq.start();
  CHECK(sink.programs.size() == 8);  // PC for every unmuted track
  CHECK(sink.starts == 1);
  seq.stop();
  CHECK(sink.stops == 1);
  seq.continuePlay();
  CHECK(sink.continues == 1);
  seq.setPlaying(false);
  CHECK(!seq.playing());
  INFO("start sends PC 0..7 + start; stop/continue forwarded");
}

TEST(ExtClockOut24Ppqn) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  seq.setBpm(120.0f);  // quarter = 24000 samples
  seq.start();
  seq.process(24000);
  CHECK(sink.clocks == 24);
  seq.process(24000);
  CHECK(sink.clocks == 48);
  CHECK(seq.clockCount() == 48);
  CHECK(seq.maxClockJitterUs() < 1000.0f);
  INFO("clock out: 48 clocks per 2 quarters (24 ppqn), jitter %.3f us", seq.maxClockJitterUs());
}

TEST(ExtClockSlaveSteps) {
  ExtSequencer seq;
  seq.init(48000.0f);
  seq.setClockMaster(false);
  seq.setClockSlave(true);
  CHECK(seq.clockSlave());
  seq.setPlaying(true);
  CHECK(seq.currentStep(0) == 0);
  for (int i = 0; i < 6; ++i) seq.onClockIn();  // 6 MIDI clocks = one 16th
  CHECK(seq.currentStep(0) == 1);
  for (int i = 0; i < 6; ++i) seq.onClockIn();
  CHECK(seq.currentStep(0) == 2);
  INFO("clock-in slave: 6x24 ppqn clocks advance one 16th step");
}

TEST(ExtGenDeterministicAndSeed) {
  auto run = [](uint32_t seed) {
    ExtSequencer seq;
    ExtCapture sink;
    seq.init(48000.0f);
    seq.setSink(&sink);
    makeTrackPattern(seq);
    GenParams params;
    params.seed = seed;
    params.probability = 50;
    params.mutate = 3;
    seq.setGenParams(0, params);
    seq.start();
    seq.process(48000);
    std::vector<int> notes;
    for (const auto& n : sink.ons) notes.push_back(n.note);
    return notes;
  };
  const auto a = run(11);
  const auto b = run(11);
  const auto c = run(99);
  CHECK(a.size() == b.size());
  CHECK(!a.empty());
  bool same = true;
  for (size_t i = 0; i < a.size() && i < b.size(); ++i) same = same && a[i] == b[i];
  CHECK(same);
  bool differs = a.size() != c.size();
  for (size_t i = 0; i < a.size() && i < c.size() && !differs; ++i) differs = a[i] != c[i];
  CHECK(differs);
  INFO("GEN applies to external tracks; same seed => identical, different seed differs");
}

TEST(ExtGenEuclidAndScale) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  makeTrackPattern(seq);
  GenParams params;
  params.euclid = 5;
  params.scale = GenScale::Minor;
  seq.setGenParams(0, params);
  seq.setBpm(480.0f);  // 16th = 1500 samples
  seq.start();
  seq.process(24000);  // one bar of 16ths at 480 BPM
  CHECK(sink.ons.size() == 5);
  for (const auto& n : sink.ons) {
    const int pc = ((n.note % 12) + 12) % 12;
    CHECK(pc == 0 || pc == 2 || pc == 3 || pc == 5 || pc == 7 || pc == 8 || pc == 10);
  }
  INFO("EUCLID 5/16 emits 5 external notes, SCALE LOCK keeps them in minor");
}

TEST(ExtLiveRecordQuantized) {
  ExtSequencer seq;
  seq.init(48000.0f);
  seq.liveRecordNoteOn(0, 67, 110, 5);
  ExtTrack& track = seq.track(0);
  CHECK(track.steps[5].active);
  CHECK(track.steps[5].note == 67);
  CHECK(track.steps[5].velocity == 110);
  seq.liveRecordNoteOff(0, 67, 7);
  CHECK(track.steps[5].length >= 10 && track.steps[5].length <= 100);
  INFO("live record quantizes note-on to step 5 and derives gate length from step 7");
}

TEST(ExtSerializeRoundtrip) {
  ExtSequencer seq;
  seq.init(48000.0f);
  makeTrackPattern(seq);
  seq.track(0).channel = 9;
  seq.track(0).program = 33;
  seq.track(0).steps[3].ccPlocked = true;
  seq.track(0).steps[3].ccValue = 99;
  seq.setTrackMuted(1, true);
  uint8_t buffer[4096];
  const size_t size = seq.serialize(buffer, sizeof(buffer));
  CHECK(size == seq.serializedSize());
  CHECK(size > 100);
  ExtSequencer loaded;
  loaded.init(48000.0f);
  CHECK(loaded.deserialize(buffer, size));
  CHECK(loaded.track(0).channel == 9);
  CHECK(loaded.track(0).program == 33);
  CHECK(loaded.track(0).steps[3].ccPlocked);
  CHECK(loaded.track(0).steps[3].ccValue == 99);
  CHECK(loaded.track(1).muted);
  CHECK(loaded.track(0).steps[0].active);
  INFO("external tracks serialize/deserialize with version + CRC32 (%u bytes)",
       static_cast<unsigned>(size));
}

TEST(ExtSerializeCorruptionRejected) {
  ExtSequencer seq;
  seq.init(48000.0f);
  makeTrackPattern(seq);
  uint8_t buffer[4096];
  const size_t size = seq.serialize(buffer, sizeof(buffer));
  ExtSequencer loaded;
  CHECK(!loaded.deserialize(buffer, size - 2));  // short
  buffer[size / 2] ^= 0xFF;
  CHECK(!loaded.deserialize(buffer, size));      // CRC mismatch
  seq.serialize(buffer, sizeof(buffer));
  buffer[4] = 99;                                // version
  CHECK(!loaded.deserialize(buffer, size));
  INFO("ext payload: short/CRC/version corruption rejected");
}

TEST(ExtMidiRouterNoDuplicates) {
  MidiOutRouter router;
  RouterExtSink sink(&router);
  sink.onExtProgramChange(0, 1, 0);
  sink.onExtStart();
  sink.onExtNoteOn(0, 1, 60, 100);
  sink.onExtNoteOff(0, 1, 60);
  sink.onExtControlChange(0, 1, 74, 64);
  sink.onExtClock();
  sink.onExtStop();
  CHECK(router.dinCount() == 7);
  CHECK(router.usbCount() == 7);
  CHECK(!router.hasDuplicates());
  for (int i = 0; i < 7; ++i) {
    CHECK(router.dinAt(i).status == router.usbAt(i).status);
    CHECK(router.dinAt(i).data1 == router.usbAt(i).data1);
    CHECK(router.dinAt(i).data2 == router.usbAt(i).data2);
  }
  CHECK(router.dinAt(1).status == 0xFA);   // start
  CHECK(router.dinAt(2).status == 0x90);   // note on CH1
  CHECK(router.dinAt(3).status == 0x80);   // note off
  CHECK(router.dinAt(4).status == 0xB0);   // CC
  CHECK(router.dinAt(5).status == 0xF8);   // clock
  CHECK(router.dinAt(6).status == 0xFC);   // stop
  INFO("DIN and USB see every logical MIDI message exactly once (no duplicates)");
}

TEST(ExtMidiRouterFullRunNoDuplicates) {
  ExtSequencer seq;
  MidiOutRouter router;
  RouterExtSink sink(&router);
  seq.init(48000.0f);
  seq.setSink(&sink);
  makeTrackPattern(seq);
  seq.setBpm(120.0f);
  seq.start();
  seq.process(24000);
  seq.stop();
  CHECK(router.dinCount() == router.usbCount());
  CHECK(router.dinCount() > 20);
  CHECK(!router.hasDuplicates());
  // A start with PC per track: 8 PC + start at the beginning.
  int pcCount = 0;
  int startCount = 0;
  for (int i = 0; i < router.dinCount(); ++i) {
    if ((router.dinAt(i).status & 0xF0) == 0xC0) ++pcCount;
    if (router.dinAt(i).status == 0xFA) ++startCount;
  }
  CHECK(pcCount == 8);
  CHECK(startCount == 1);
  INFO("full bar run: DIN/USB identical, no duplicates, 8 PC + start + clocks/notes");
}

TEST(ExtSharedTransportWithInternalSequencer) {
  Sequencer seq;
  seq.init(48000.0f);
  seq.external().init(48000.0f);
  ExtCapture sink;
  seq.external().setSink(&sink);
  seq.setBpm(140.0f);
  CHECK(seq.external().bpm() == 140.0f);
  seq.setSwing(0.2f);
  CHECK(seq.external().swing() == 0.2f);
  seq.onStart();
  CHECK(seq.external().playing());
  seq.onStop();
  CHECK(!seq.external().playing());
  INFO("external sequencer shares tempo/swing/transport with the internal one");
}

TEST(ExtGenProbabilityZeroNoNotes) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  makeTrackPattern(seq);
  GenParams params;
  params.probability = 0;
  seq.setGenParams(0, params);
  seq.start();
  seq.process(48000);
  CHECK(sink.ons.empty());
  INFO("GEN PROB 0 suppresses all external notes");
}

TEST(ExtGenArpNotesCycle) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  makeTrackPattern(seq);
  for (int s = 0; s < 3; ++s) {
    seq.track(0).steps[s].note = static_cast<uint8_t>(s == 2 ? 67 : 60 + s * 4);  // C E G
    seq.track(0).steps[s].active = true;
  }
  for (int s = 3; s < kExtSteps; ++s) seq.track(0).steps[s].active = false;
  GenParams params;
  params.arpOn = true;
  params.arpRate = GenArpRate16;
  params.arpMode = GenArpUp;
  seq.setGenParams(0, params);
  seq.setBpm(480.0f);
  seq.start();
  seq.process(6000);  // four 16th steps
  CHECK(sink.ons.size() >= 3);
  if (sink.ons.size() >= 3) {
    CHECK(sink.ons[0].note == 60);
    CHECK(sink.ons[1].note == 64);
    CHECK(sink.ons[2].note == 67);
  }
  INFO("GEN ARP cycles held notes C/E/G on an external track");
}

TEST(ExtSerializeDeterministic) {
  ExtSequencer seq;
  seq.init(48000.0f);
  makeTrackPattern(seq);
  uint8_t a[4096];
  uint8_t b[4096];
  const size_t size = seq.serialize(a, sizeof(a));
  CHECK(size > 0);
  CHECK(seq.serialize(b, sizeof(b)) == size);
  CHECK(std::memcmp(a, b, size) == 0);
  INFO("ext payload serialization is byte-identical for the same state");
}

TEST(ExtClockJitterLongRun) {
  ExtSequencer seq;
  ExtCapture sink;
  seq.init(48000.0f);
  seq.setSink(&sink);
  seq.setBpm(140.0f);
  seq.start();
  seq.process(48000);  // 1 s of 24 ppqn clock
  CHECK(sink.clocks >= 55 && sink.clocks <= 56);  // 140 BPM * 24 / 60 = 56
  CHECK(seq.maxClockJitterUs() < 1000.0f);
  INFO("clock model at 140 BPM: %d ticks/s, max jitter %.3f us (<1 ms)",
       sink.clocks, seq.maxClockJitterUs());
}
