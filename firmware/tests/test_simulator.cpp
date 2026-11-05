// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <cstdio>
#include <cstring>

#include "sim/simulator.hpp"
#include "test_framework.hpp"

using namespace bukifon;
using namespace bukifon::sim;

namespace {

int countEvents(const EventLog& log, SimEventType type, int aFilter = -1) {
  int n = 0;
  for (const SimEvent& e : log.events()) {
    if (e.type != type) continue;
    if (aFilter >= 0 && e.a != aFilter) continue;
    ++n;
  }
  return n;
}

}  // namespace

TEST(SimulatorTransport) {
  Simulator sim;
  sim.init();
  sim.buildDemoPattern();
  CHECK(!sim.playing());
  CHECK(std::strcmp(sim.snapshot(ui::Screen::Main).status, "STOP") == 0);
  sim.play();
  CHECK(sim.playing());
  const ui::UiSnapshot playing = sim.snapshot(ui::Screen::Main);
  CHECK(std::strcmp(playing.status, "PLAY") == 0);
  CHECK(playing.bpm == 120.0f);
  CHECK(playing.trackCount == 4);
  sim.runSamples(1000);
  sim.stop();
  CHECK(!sim.playing());
  CHECK(std::strcmp(sim.snapshot(ui::Screen::Main).status, "STOP") == 0);
  INFO("transport: play/stop works, observation events=%zu", sim.observationLog().size());
}

TEST(SimulatorOneBarWrap) {
  Simulator sim;
  sim.init();
  sim.buildDemoPattern();
  sim.play();
  const uint64_t bar = Simulator::samplesPerBar(120.0f, 48000.0f);
  CHECK(bar == 96000);
  sim.runSamples(bar - 1);
  const EventLog::Summary summary = sim.observationLog().summarize();
  INFO("one bar: frames=%llu notes on/off=%zu/%zu currentStep=%d passCount=%u",
       static_cast<unsigned long long>(sim.frame()), summary.notesOn, summary.notesOff,
       sim.sequencer().currentStep(0), sim.sequencer().passCount(0));
  CHECK(summary.notesOn == 4 * 16);
  CHECK(summary.notesOff == 4 * 16);
  CHECK(summary.monotonic);
  CHECK(sim.sequencer().currentStep(0) == 0);  // wrapped back to step 0
  CHECK(sim.sequencer().passCount(0) == 1);
  for (int track = 0; track < kSeqTracks; ++track) {
    CHECK(countEvents(sim.observationLog(), SimEventType::NoteOn, track) == 16);
  }
}

TEST(SimulatorTrackMute) {
  Simulator sim;
  sim.init();
  sim.buildDemoPattern();
  sim.setTrackMuted(2, true);
  sim.play();
  sim.runSamples(Simulator::samplesPerBar(120.0f, 48000.0f) - 1);
  const int mutedCount = countEvents(sim.observationLog(), SimEventType::NoteOn, 2);
  INFO("mute: track2 notes=%d, track0 notes=%d", mutedCount,
       countEvents(sim.observationLog(), SimEventType::NoteOn, 0));
  CHECK(mutedCount == 0);
  CHECK(countEvents(sim.observationLog(), SimEventType::NoteOn, 0) == 16);
  CHECK(countEvents(sim.observationLog(), SimEventType::Mute, 2) == 1);
  sim.setTrackMuted(2, false);
  sim.runSamples(Simulator::samplesPerBar(120.0f, 48000.0f) - 1);
  CHECK(countEvents(sim.observationLog(), SimEventType::NoteOn, 2) == 16);
}

TEST(SimulatorPlockOneStep) {
  Simulator sim;
  sim.init();
  sim.buildDemoPattern();
  // The demo has exactly one p-lock: track 0, step 5 (index 4), Cutoff 60 %.
  const Pattern& pattern = sim.sequencer().pattern(0);
  CHECK(pattern.tracks[0].steps[4].plockCount == 1);
  CHECK(pattern.tracks[0].steps[4].plocks[0].param == Cutoff);
  const float baseCutoff = sim.engine().partBase(0).v[Cutoff];
  const float lockedCutoff =
      paramFromNorm(kPartParamMeta[Cutoff],
                    static_cast<float>(pattern.tracks[0].steps[4].plocks[0].value) / 255.0f);
  sim.play();
  sim.runSamples(4 * 6000 + 200);  // step 5 (index 4) has just triggered
  const float afterTrigger = sim.engine().partBase(0).v[Cutoff];
  INFO("p-lock: base=%.1f Hz, locked=%.1f Hz, after step5 trigger=%.1f Hz", baseCutoff,
       lockedCutoff, afterTrigger);
  CHECK(std::fabs(afterTrigger - lockedCutoff) < 1.0f);
  CHECK(std::fabs(afterTrigger - baseCutoff) > 1.0f);
  // The next step restores the base value: one-step p-lock semantics.
  sim.runSamples(6000 + 200);
  const float afterNext = sim.engine().partBase(0).v[Cutoff];
  INFO("p-lock: after next step cutoff=%.1f Hz (base %.1f Hz)", afterNext, baseCutoff);
  CHECK(std::fabs(afterNext - baseCutoff) < 1.0f);
}

TEST(SimulatorDeterministicDemo) {
  Simulator a;
  a.init();
  const EventLog& logA = a.runDemo(2);
  Simulator b;
  b.init();
  const EventLog& logB = b.runDemo(2);
  const EventLog::Summary summary = logA.summarize();
  INFO("demo: 2 bars, events=%zu, notes=%zu, plocks=%zu, peak=%.3f", summary.count,
       summary.notesOn, summary.plocks, a.stats().peak);
  CHECK(logA.equals(logB));
  CHECK(summary.notesOn == 2 * 16 * 4);
  CHECK(summary.plocks > 0);
  CHECK(summary.monotonic);
  CHECK(a.stats().peak > 0.0f);
  CHECK(a.stats().peak <= 1.0f);
}

TEST(SimulatorEventReplay) {
  Simulator sim;
  sim.init();
  sim.addEvent(0, SimEventType::Tempo, 0, 0, 140.0f);
  sim.addEvent(0, SimEventType::Transport, 0, 0, 1.0f);
  sim.addEvent(100, SimEventType::NoteOn, 0, 60, 100.0f);
  sim.addEvent(5000, SimEventType::NoteOff, 0, 60, 0.0f);
  const char* path = "../tests/out/sim_events.txt";
  CHECK(sim.saveEvents(path));
  Simulator loaded;
  loaded.init();
  // Start from an empty pattern so the transport event does not trigger the
  // default sequencer pattern: this test checks external-event replay only.
  for (int t = 0; t < kSeqTracks; ++t) {
    for (int st = 0; st < kSeqSteps; ++st) loaded.sequencer().step(t, st).active = false;
  }
  loaded.engine().setPartParam(0, Env1R, 0.01f);  // short release for the test
  CHECK(loaded.loadEvents(path));
  CHECK(loaded.pendingEventCount() == 4);
  loaded.runSamples(12000);
  INFO("event replay: notes=%zu, bpm=%.0f, peak=%.3f",
       loaded.observationLog().summarize().notesOn, loaded.sequencer().bpm(), loaded.stats().peak);
  CHECK(loaded.observationLog().summarize().notesOn == 1);
  CHECK(std::fabs(loaded.sequencer().bpm() - 140.0f) < 0.01f);
  CHECK(loaded.engine().activeVoices() == 0);  // note released
  CHECK(loaded.stats().peak > 0.0f);
  std::remove(path);
}

TEST(SimulatorSnapshotsPerScreen) {
  Simulator sim;
  sim.init();
  sim.buildDemoPattern();
  sim.play();
  sim.runSamples(20000);
  const char* pages[4] = {"MAIN", "SEQUENCER", "MIXER", "MODULES"};
  const ui::Screen screens[4] = {ui::Screen::Main, ui::Screen::Sequencer, ui::Screen::Mixer,
                                 ui::Screen::Modules};
  for (int i = 0; i < 4; ++i) {
    const ui::UiSnapshot snapshot = sim.snapshot(screens[i]);
    CHECK(snapshot.trackCount == 4);
    CHECK(snapshot.stepCount == 16);
    CHECK(std::strcmp(snapshot.page, pages[i]) == 0);
    CHECK(std::strlen(snapshot.params[0].label) > 0);
    CHECK(std::strlen(snapshot.hints[0]) > 0);
    CHECK(snapshot.bpm > 0.0f);
  }
  const ui::UiSnapshot modules = sim.snapshot(ui::Screen::Modules);
  CHECK(modules.moduleCount == 4);
  CHECK(std::strstr(modules.moduleApi, "v0") != nullptr);
  INFO("snapshots: 4 screens, pages %s/%s/%s/%s", pages[0], pages[1], pages[2], pages[3]);
}
