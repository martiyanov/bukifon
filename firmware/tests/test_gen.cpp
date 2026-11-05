// SPDX-License-Identifier: GPL-3.0-or-later
// Generative sequencer functions: deterministic hash/probability/Euclid/
// mutate/scale/evolve/arp and integration in the 16-step sequencer.
#include <cstdint>
#include <cstring>
#include <vector>

#include "io/gen.hpp"
#include "io/sequencer.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

struct Event {
  int track;
  int note;
  int velocity;
};

struct CaptureSink : SequencerSink {
  std::vector<Event> events;
  void onSeqNoteOn(int track, int note, int velocity) override {
    events.push_back(Event{track, note, velocity});
  }
};

SequenceTrack makeTrack() {
  SequenceTrack track;
  for (int i = 0; i < kSeqSteps; ++i) {
    track.steps[i].note = static_cast<uint8_t>(48 + i);
    track.steps[i].active = true;
    track.steps[i].velocity = 100;
  }
  return track;
}

void runSequencer(Sequencer& seq, int samples) { seq.process(samples); }

}  // namespace

TEST(GenHashIsDeterministic) {
  const uint32_t a = genHash(1234, 2, 7, 42);
  const uint32_t b = genHash(1234, 2, 7, 42);
  CHECK(a == b);
  CHECK(genHash(1234, 2, 7, 42) != genHash(1234, 2, 8, 42));
  CHECK(genHash(1234, 3, 7, 42) != genHash(1234, 2, 7, 42));
  CHECK(genHash(1, 0, 0, 0) != genHash(2, 0, 0, 0));
  INFO("hash(seed,part,step,salt) stable across calls and sensitive to inputs");
}

TEST(GenProbabilityBoundsAndDeterminism) {
  CHECK(genProbability(1, 0, 0, 100));
  CHECK(!genProbability(1, 0, 0, 0));
  int pass = 0;
  for (int step = 0; step < 1000; ++step) pass += genProbability(7, 1, step, 50) ? 1 : 0;
  CHECK(pass > 400 && pass < 600);  // roughly 50 %, deterministic distribution
  CHECK(genProbability(7, 1, 3, 50) == genProbability(7, 1, 3, 50));
  INFO("PROB: 0/100 boundaries and ~50%% over 1000 deterministic steps (pass=%d)", pass);
}

TEST(GenEuclidMaskAndDistribution) {
  CHECK(genEuclidMask(0, 16) == 0);
  CHECK(genEuclidMask(16, 16) == 0xFFFF);
  const uint16_t five = genEuclidMask(5, 16);
  int bits = 0;
  for (int i = 0; i < 16; ++i) bits += genEuclidGate(five, i) ? 1 : 0;
  CHECK(bits == 5);
  // Euclidean distribution: no long gap (>3) and gates spread out.
  int maxGap = 0, gap = 0;
  for (int i = 0; i < 16; ++i) {
    if (genEuclidGate(five, i)) {
      if (gap > maxGap) maxGap = gap;
      gap = 0;
    } else {
      ++gap;
    }
  }
  CHECK(maxGap <= 3);
  INFO("EUCLID: 5/16 = %d gates, max gap %d (Bjorklund distribution)", bits, maxGap);
}

TEST(GenEuclidAccents) {
  CHECK(genEuclidAccent(0));
  CHECK(genEuclidAccent(4));
  CHECK(genEuclidAccent(8));
  CHECK(genEuclidAccent(12));
  CHECK(!genEuclidAccent(1));
  CHECK(!genEuclidAccent(3));
  INFO("EUCLID accents on 1/5/9/13 (steps 0/4/8/12)");
}

TEST(GenMutateBoundsAndDeterminism) {
  for (int step = 0; step < 100; ++step) {
    const int value = genMutateOffset(99, 2, step, 12);
    CHECK(value >= -12 && value <= 12);
    CHECK(value == genMutateOffset(99, 2, step, 12));
  }
  CHECK(genMutateOffset(1, 0, 0, 0) == 0);
  // Same seed/part/step, changed max only widens the range.
  CHECK(genMutateOffset(5, 1, 9, 1) >= -1 && genMutateOffset(5, 1, 9, 1) <= 1);
  INFO("MUTATE: deterministic hash(seed,part,step), range +-0..12 semitones");
}

TEST(GenScaleLockAllScales) {
  CHECK(genScaleLockNote(61, GenScale::Off) == 61);
  CHECK(genScaleLockNote(61, GenScale::Minor) == 60);
  CHECK(genScaleLockNote(61, GenScale::Major) == 60);
  const GenScale scales[] = {GenScale::Minor, GenScale::Major, GenScale::Penta, GenScale::Dorian};
  for (GenScale scale : scales) {
    for (int note = 30; note < 90; ++note) {
      const int locked = genScaleLockNote(note, scale);
      CHECK(locked >= 0 && locked <= 127);
      CHECK(locked == genScaleLockNote(note, scale));  // deterministic
    }
  }
  CHECK(genScaleLockNote(64, GenScale::Minor) == 63);   // E -> Eb
  CHECK(genScaleLockNote(66, GenScale::Major) == 65);   // F# -> F
  CHECK(genScaleLockNote(64, GenScale::Penta) == 64);   // E is in Penta
  INFO("SCALE LOCK: OFF identity, MINOR/MAJOR/PENTA/DORIAN nearest-note mapping");
}

TEST(GenEvolveDeterministic) {
  const int a = genEvolveNote(42, 1, 0, 3, 60, 2);
  const int b = genEvolveNote(42, 1, 0, 3, 60, 2);
  CHECK(a == b);
  CHECK(a >= 58 && a <= 62);
  // Different bar => the pattern is allowed to move.
  bool anyDifference = false;
  for (int step = 0; step < 16; ++step) {
    if (genEvolveNote(42, 1, 0, step, 60, 2) != genEvolveNote(42, 1, 1, step, 60, 2)) {
      anyDifference = true;
    }
  }
  CHECK(anyDifference);
  INFO("EVOLVE: bar boundary derivation is deterministic and changes over bars");
}

TEST(GenApplyStepPipeline) {
  GenParams params;
  params.seed = 123;
  params.probability = 100;
  params.euclid = 16;
  params.mutate = 0;
  params.scale = GenScale::Major;
  const GenStepResult result = genApplyStep(params, 0, 0, 61, 100);
  CHECK(result.trigger);
  CHECK(result.accent);
  CHECK(result.note == 60 || result.note == 62);  // scale-locked C major
  CHECK(result.velocity > 100);                   // accent
  params.probability = 0;
  const GenStepResult blocked = genApplyStep(params, 0, 1, 60, 100);
  CHECK(!blocked.trigger);
  INFO("apply step: Euclid gate + probability + mutate + scale lock + accent");
}

TEST(GenArpRatesAndModes) {
  CHECK(GenArp::periodTicks32(GenArpRate8) == 4);
  CHECK(GenArp::periodTicks32(GenArpRate16) == 2);
  CHECK(GenArp::periodTicks32(GenArpRate32) == 1);
  const uint8_t notes[3] = {67, 60, 64};
  GenArp arp;
  arp.setParams(GenArpRate16, GenArpUp);
  CHECK(arp.noteAt(notes, 3, 0) == 60);
  CHECK(arp.noteAt(notes, 3, 2) == 64);
  CHECK(arp.noteAt(notes, 3, 4) == 67);
  arp.setParams(GenArpRate16, GenArpDown);
  CHECK(arp.noteAt(notes, 3, 0) == 67);
  CHECK(arp.noteAt(notes, 3, 2) == 64);
  arp.setParams(GenArpRate16, GenArpUpDown);
  CHECK(arp.noteAt(notes, 3, 0) == 60);
  CHECK(arp.noteAt(notes, 3, 2) == 64);
  CHECK(arp.noteAt(notes, 3, 4) == 67);
  CHECK(arp.noteAt(notes, 3, 6) == 64);  // up-down mirrored
  INFO("ARP: 1/8,1/16,1/32 periods; UP/DOWN/UPDOWN over held notes");
}

TEST(SequencerGenDeterministic) {
  auto run = [](uint32_t seed) {
    Sequencer seq;
    seq.init(48000.0f);
    CaptureSink sink;
    seq.setSink(&sink);
    seq.pattern(0).tracks[0] = makeTrack();
    GenParams params;
    params.seed = seed;
    params.probability = 50;
    params.mutate = 3;
    seq.setGenParams(0, params);
    seq.setPlaying(true);
    runSequencer(seq, 48000);  // two bars
    return sink.events;
  };
  auto track0 = [](const std::vector<Event>& events) {
    std::vector<Event> out;
    for (const Event& event : events) {
      if (event.track == 0) out.push_back(event);
    }
    return out;
  };
  const auto first = run(1234);
  const auto second = run(1234);
  const auto other = run(4321);
  const auto a = track0(first);
  const auto b = track0(second);
  const auto c = track0(other);
  CHECK(a.size() == b.size());
  CHECK(a.size() > 0);
  bool same = true;
  for (size_t i = 0; i < a.size() && i < b.size(); ++i) same = same && a[i].note == b[i].note;
  CHECK(same);
  bool differs = a.size() != c.size();
  for (size_t i = 0; i < a.size() && i < c.size() && !differs; ++i) differs = a[i].note != c[i].note;
  CHECK(differs);
  INFO("sequencer GEN: same seed => identical events, different seed => different");
}

TEST(SequencerGenEuclidTriggerCount) {
  Sequencer seq;
  seq.init(48000.0f);
  CaptureSink sink;
  seq.setSink(&sink);
  seq.pattern(0).tracks[0] = makeTrack();
  GenParams params;
  params.euclid = 5;
  seq.setGenParams(0, params);
  seq.setBpm(480.0f);  // 16th = 1500 samples -> one bar = 24000 samples
  seq.setPlaying(true);
  runSequencer(seq, 24000);
  int track0Events = 0;
  for (const Event& event : sink.events) track0Events += event.track == 0 ? 1 : 0;
  CHECK(track0Events == 5);
  INFO("sequencer EUCLID: density 5/16 emits 5 triggers per bar");
}

TEST(SequencerGenScaleLockAndEvolve) {
  Sequencer seq;
  seq.init(48000.0f);
  CaptureSink sink;
  seq.setSink(&sink);
  seq.pattern(0).tracks[0] = makeTrack();
  GenParams params;
  params.scale = GenScale::Minor;
  params.evolve = true;
  seq.setGenParams(0, params);
  seq.setPlaying(true);
  runSequencer(seq, 48000);
  CHECK(!sink.events.empty());
  for (const Event& event : sink.events) {
    if (event.track != 0) continue;
    const int pc = ((event.note % 12) + 12) % 12;
    CHECK(pc == 0 || pc == 2 || pc == 3 || pc == 5 || pc == 7 || pc == 8 || pc == 10);
  }
  // Evolve mutates the pattern at bar boundaries; the change is deterministic.
  const uint8_t noteAfter = seq.pattern(0).tracks[0].steps[0].note;
  Sequencer other;
  other.init(48000.0f);
  CaptureSink otherSink;
  other.setSink(&otherSink);
  other.pattern(0).tracks[0] = makeTrack();
  other.setGenParams(0, params);
  other.setPlaying(true);
  runSequencer(other, 48000);
  CHECK(noteAfter == other.pattern(0).tracks[0].steps[0].note);
  INFO("sequencer: scale-locked notes + deterministic EVOLVE at bar boundaries");
}
