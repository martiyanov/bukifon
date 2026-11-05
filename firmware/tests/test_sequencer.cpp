// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <vector>

#include "audio/engine.hpp"
#include "io/arp.hpp"
#include "io/sequencer.hpp"
#include "test_framework.hpp"
#include "test_helpers.hpp"

using namespace bukifon;

namespace {

class RecordingSeqSink : public SequencerSink {
 public:
  struct NoteEv {
    int track, note, velocity;
    long sample;
  };
  void onSeqNoteOn(int track, int note, int velocity) override {
    noteOns.push_back({track, note, velocity, now});
  }
  void onSeqNoteOff(int track, int note) override { noteOffs.push_back({track, note}); }
  void onSeqPlock(int track, int param, float normalized) override {
    plocks.push_back({track, param, normalized});
  }
  void onSeqSoundLock(int track, int preset) override { soundLocks.push_back({track, preset}); }
  void onSeqStep(int track, int step, uint32_t pass) override {
    steps.push_back({track, step, static_cast<long>(pass)});
  }
  std::vector<NoteEv> noteOns;
  std::vector<std::pair<int, int>> noteOffs;
  struct Plock {
    int track, param;
    float normalized;
  };
  std::vector<Plock> plocks;
  std::vector<std::pair<int, int>> soundLocks;
  struct StepEv {
    int track, step;
    long pass;
  };
  std::vector<StepEv> steps;
  long now = 0;
};

void soloTrack0(Sequencer& seq) {
  for (int t = 1; t < kSeqTracks; ++t) {
    for (int st = 0; st < kSeqSteps; ++st) seq.step(t, st).active = false;
  }
}

void runSamples(Sequencer& seq, RecordingSeqSink& sink, int total) {
  for (int i = 0; i < total; ++i) {
    sink.now = i;
    seq.process(1);
  }
}

}  // namespace

TEST(SequencerBasicTiming) {
  Sequencer seq;
  seq.init(48000.0f);
  seq.setSink(nullptr);
  RecordingSeqSink sink;
  seq.setSink(&sink);
  seq.setBpm(120.0f);  // 16th = 6000 samples
  soloTrack0(seq);
  seq.setPlaying(true);
  runSamples(seq, sink, 23999);
  INFO("sequencer: 4 steps in 24000 samples, noteOns=%zu, expected intervals 6000", sink.noteOns.size());
  CHECK(sink.noteOns.size() == 4);
  if (sink.noteOns.size() >= 3) {
    CHECK(sink.noteOns[0].sample == 0);
    CHECK(std::abs(sink.noteOns[1].sample - 6000) <= 1);
    CHECK(std::abs(sink.noteOns[2].sample - 12000) <= 1);
  }
  CHECK(seq.currentStep(0) == 4);
}

TEST(SequencerSwingAndMicroTiming) {
  {
    Sequencer seq;
    seq.init(48000.0f);
    RecordingSeqSink sink;
    seq.setSink(&sink);
    seq.setBpm(120.0f);
    soloTrack0(seq);
    seq.setSwing(0.5f);
    seq.setPlaying(true);
    runSamples(seq, sink, 16000);
    // Trigger 0 at 0, trigger 1 delayed by swing/2 of the step.
    const long expected = static_cast<long>(6000 + 0.5 * 0.5 * 6000);
    INFO("swing: second trigger at sample %ld (expected %ld)", sink.noteOns[1].sample, expected);
    CHECK(std::abs(sink.noteOns[1].sample - expected) <= 2);
  }
  {
    Sequencer seq;
    seq.init(48000.0f);
    RecordingSeqSink sink;
    seq.setSink(&sink);
    seq.setBpm(120.0f);
    soloTrack0(seq);
    seq.setSwing(0.0f);
    seq.step(0, 1).micro = 8;  // +1/2 step late
    seq.setPlaying(true);
    runSamples(seq, sink, 20000);
    const long expected = 6000 + 3000;
    INFO("micro timing: second trigger at sample %ld (expected %ld)", sink.noteOns[1].sample,
         expected);
    CHECK(std::abs(sink.noteOns[1].sample - expected) <= 2);
  }
}

TEST(SequencerTrigConditions) {
  Sequencer seq;
  seq.init(48000.0f);
  RecordingSeqSink sink;
  seq.setSink(&sink);
  seq.setBpm(120.0f);
  soloTrack0(seq);
  // Only step 0 plays, and only on the first pass.
  for (int s = 0; s < kSeqSteps; ++s) seq.step(0, s).active = false;
  seq.step(0, 0).active = true;
  seq.step(0, 0).note = 60;
  seq.step(0, 0).condition = TrigFirst;
  seq.setPlaying(true);
  runSamples(seq, sink, 6000 * 32);  // two full passes
  INFO("trig condition 1st: %zu triggers over 2 passes (expected 1)", sink.noteOns.size());
  CHECK(sink.noteOns.size() == 1);
  CHECK(seq.passCount(0) == 2);

  // A:B condition 2:3 -> triggers on pass 1, 4, 7 (0-based pass%3==1).
  Sequencer seq2;
  seq2.init(48000.0f);
  RecordingSeqSink sink2;
  seq2.setSink(&sink2);
  seq2.setBpm(120.0f);
  soloTrack0(seq2);
  for (int s = 0; s < kSeqSteps; ++s) seq2.step(0, s).active = false;
  seq2.step(0, 0).active = true;
  seq2.step(0, 0).condition = TrigAB;
  seq2.step(0, 0).condA = 2;
  seq2.step(0, 0).condB = 3;
  seq2.setPlaying(true);
  runSamples(seq2, sink2, 6000 * 16 * 7);  // 7 passes
  INFO("trig condition 2:3: %zu triggers over 7 passes (expected 2)", sink2.noteOns.size());
  CHECK(sink2.noteOns.size() == 2);
}

TEST(SequencerPlocksAndSoundLocks) {
  Sequencer seq;
  seq.init(48000.0f);
  RecordingSeqSink sink;
  seq.setSink(&sink);
  seq.setBpm(120.0f);
  soloTrack0(seq);
  seq.step(0, 0).plockCount = 0;
  seq.setPlock(0, 0, 0, Cutoff, 128);
  seq.setPlock(0, 0, 1, Resonance, 200);
  seq.step(0, 0).soundLock = 7;
  seq.setPlaying(true);
  runSamples(seq, sink, 100);
  INFO("plocks: %zu plocks on first step, sound locks=%zu", sink.plocks.size(),
       sink.soundLocks.size());
  CHECK(sink.plocks.size() == 2);
  CHECK(sink.plocks[0].param == Cutoff);
  CHECK(std::fabs(sink.plocks[0].normalized - 128.0f / 255.0f) < 1e-5f);
  CHECK(sink.soundLocks.size() == 1);
  CHECK(sink.soundLocks[0].second == 7);
}

TEST(SequencerTrackLengthSpeedAndChain) {
  Sequencer seq;
  seq.init(48000.0f);
  RecordingSeqSink sink;
  seq.setSink(&sink);
  seq.setBpm(120.0f);
  soloTrack0(seq);
  seq.setTrackLength(0, 4);
  seq.setTrackSpeed(0, 2);  // 12000 samples per step
  CHECK(seq.trackLength(0) == 4);
  CHECK(seq.trackSpeed(0) == 2);
  seq.setPlaying(true);
  runSamples(seq, sink, 48000);
  INFO("track length 4 / speed 2: %zu triggers in 48000 samples (expected 4)", sink.noteOns.size());
  CHECK(sink.noteOns.size() == 4);
  const uint8_t chain[2] = {0, 1};
  seq.setChain(chain, 2);
  seq.setPatternIndex(0);
  seq.advanceChain();
  CHECK(seq.patternIndex() == 1);
  seq.advanceChain();
  CHECK(seq.patternIndex() == 0);
}

TEST(SequencerExternalClock) {
  Sequencer seq;
  seq.init(48000.0f);
  RecordingSeqSink sink;
  seq.setSink(&sink);
  seq.setExternalClock(true);
  soloTrack0(seq);
  seq.setPlaying(true);
  // 6 MIDI clock ticks = one 16th note at speed 1.
  for (int i = 0; i < 6; ++i) seq.onClockTick();
  CHECK(seq.currentStep(0) == 1);
  CHECK(sink.noteOns.size() == 1);
  seq.process(6000);  // internal timing must be idle in external clock mode
  CHECK(sink.noteOns.size() == 1);
  for (int i = 0; i < 6; ++i) seq.onClockTick();
  CHECK(seq.currentStep(0) == 2);
  INFO("external clock: step advanced on 6 ticks, internal process ignored");
}

TEST(SequencerGenerativeModulators) {
  Sequencer seq;
  seq.init(48000.0f);
  RecordingSeqSink sink;
  seq.setSink(&sink);
  seq.setBpm(120.0f);
  soloTrack0(seq);
  for (int s = 0; s < kSeqSteps; ++s) {
    seq.step(0, s).note = 60;
    seq.step(0, s).velocity = 100;
  }
  seq.modulator(0, 0).mode = StepModulator::Saw;
  seq.pattern(0).tracks[0].modCount = 1;
  seq.setPlaying(true);
  runSamples(seq, sink, 6000 * 8);
  int distinct = 0;
  int used[128] = {};
  for (const auto& n : sink.noteOns) {
    if (!used[n.note]) ++distinct;
    used[n.note] = 1;
  }
  INFO("generative modulator: %zu notes, %d distinct pitches", sink.noteOns.size(), distinct);
  CHECK(sink.noteOns.size() == 8);
  CHECK(distinct >= 3);

  // Deterministic: a fresh run produces the same note sequence.
  Sequencer seq2;
  seq2.init(48000.0f);
  RecordingSeqSink sink2;
  seq2.setSink(&sink2);
  seq2.setBpm(120.0f);
  soloTrack0(seq2);
  for (int s = 0; s < kSeqSteps; ++s) seq2.step(0, s).note = 60;
  seq2.modulator(0, 0).mode = StepModulator::Saw;
  seq2.pattern(0).tracks[0].modCount = 1;
  seq2.setPlaying(true);
  runSamples(seq2, sink2, 6000 * 8);
  bool same = sink2.noteOns.size() == sink.noteOns.size();
  for (size_t i = 0; same && i < sink.noteOns.size(); ++i) {
    same = sink2.noteOns[i].note == sink.noteOns[i].note;
  }
  CHECK(same);
}

TEST(SequencerUndo) {
  Sequencer seq;
  seq.init(48000.0f);
  const int original = seq.step(0, 1).note;
  seq.step(0, 0).note = 72;
  seq.copyStep(0, 0, 1);
  CHECK(seq.step(0, 1).note == 72);
  CHECK(seq.undoAvailable());
  seq.undo();
  INFO("undo: step note restored to %d", seq.step(0, 1).note);
  CHECK(seq.step(0, 1).note == original);
  CHECK(!seq.undoAvailable());
}

TEST(SequencerToEngineIntegration) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  Sequencer seq;
  seq.init(48000.0f);
  seq.setBpm(120.0f);
  engine.setSequencer(&seq);
  seq.step(0, 0).note = 60;
  seq.step(0, 0).condition = TrigAlways;
  seq.setPlaying(true);
  testutil::Rendered r = testutil::render(engine, 0.1);
  INFO("sequencer->engine: active voices=%d", engine.activeVoices());
  CHECK(engine.activeVoices() >= 1);
  CHECK(testutil::allFinite(r));
  // Stop the sequencer and release everything.
  seq.setPlaying(false);
  engine.allNotesOff();
  testutil::render(engine, 0.5);
  CHECK(engine.activeVoices() == 0);
}

namespace {
class RecordingArpSink : public ArpSink {
 public:
  void onArpNoteOn(int part, int note, int velocity) override {
    (void)part;
    notes.push_back(note);
    (void)velocity;
  }
  void onArpNoteOff(int part, int note) override {
    (void)part;
    (void)note;
  }
  std::vector<int> notes;
};
}  // namespace

TEST(ArpeggiatorModes) {
  {
    Arpeggiator arp;
    arp.init(48000.0f);
    RecordingArpSink sink;
    arp.setSink(&sink);
    arp.setParams(ArpUp, 2, 0.5f, false);
    arp.noteOn(60, 100);
    arp.noteOn(64, 100);
    arp.noteOn(67, 100);
    for (int i = 0; i < 6000 * 6; ++i) arp.process(1, 120.0f, 0);
    INFO("arp up 2 oct: notes=%zu first six:", sink.notes.size());
    for (size_t i = 0; i < sink.notes.size() && i < 6; ++i) {
      testfw::info("  arp[%zu] = %d", i, sink.notes[i]);
    }
    CHECK(sink.notes.size() >= 6);
    const int expected[6] = {60, 64, 67, 72, 76, 79};
    for (int i = 0; i < 6; ++i) CHECK(sink.notes[static_cast<size_t>(i)] == expected[i]);
  }
  {
    Arpeggiator arp;
    arp.init(48000.0f);
    RecordingArpSink sink;
    arp.setSink(&sink);
    arp.setParams(ArpDown, 1, 0.5f, false);
    arp.noteOn(60, 100);
    arp.noteOn(64, 100);
    arp.noteOn(67, 100);
    for (int i = 0; i < 6000 * 4; ++i) arp.process(1, 120.0f, 0);
    CHECK(sink.notes.size() >= 3);
    CHECK(sink.notes[0] == 67);
    CHECK(sink.notes[1] == 64);
    CHECK(sink.notes[2] == 60);
  }
  {
    Arpeggiator arp;
    arp.init(48000.0f);
    RecordingArpSink sink;
    arp.setSink(&sink);
    arp.setParams(ArpUp, 1, 0.5f, true);  // latch
    arp.noteOn(60, 100);
    arp.noteOn(64, 100);
    arp.noteOff(60);
    arp.noteOff(64);
    for (int i = 0; i < 6000 * 2; ++i) arp.process(1, 120.0f, 0);
    CHECK(sink.notes.size() >= 2);  // latched notes keep playing
    arp.noteOn(67, 100);            // new chord replaces the latched one
    for (int i = 0; i < 6000 * 2; ++i) arp.process(1, 120.0f, 0);
    CHECK(sink.notes.back() == 67);
  }
}

TEST(ArpeggiatorToEngine) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  engine.setGlobalParam(ArpMode, 1.0f);  // up
  engine.setGlobalParam(ArpOctaves, 1.0f);
  engine.noteOn(60, 100, 0, 0);
  engine.noteOn(64, 100, 0, 0);
  testutil::Rendered r = testutil::render(engine, 0.6);
  INFO("engine arp: active voices=%d, rms=%.4f", engine.activeVoices(), testutil::rms(r.l));
  CHECK(engine.activeVoices() >= 1);
  CHECK(testutil::rms(r.l) > 0.001);
  CHECK(testutil::allFinite(r));
}
