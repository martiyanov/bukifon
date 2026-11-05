// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <vector>

#include "audio/engine.hpp"
#include "core/events.hpp"
#include "core/math.hpp"
#include "dsp/envelope.hpp"
#include "dsp/fm.hpp"
#include "dsp/filter.hpp"
#include "test_framework.hpp"
#include "test_helpers.hpp"

using namespace bukifon;
using namespace testutil;

TEST(EngineA4Tuning) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(0, Osc1Wave, 4.0f);  // sine
  bool started = false;
  const Rendered r = render(e, 1.2, [&](Engine& eng, double) {
    if (!started) {
      eng.noteOn(69, 100, 0, 0);
      started = true;
    }
  });
  const double f = zeroCrossFrequency(r.l, 0.2, 1.1);
  const double errPct = (f - 440.0) / 440.0 * 100.0;
  INFO("A4: measured %.4f Hz, error %+.4f %% (target 440 +/- 0.1%%)", f, errPct);
  CHECK(allFinite(r));
  CHECK(std::fabs(errPct) < 0.1);
}

TEST(EngineEightVoices) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(0, Osc1Wave, 0.0f);
  const int notes[8] = {60, 62, 64, 65, 67, 69, 71, 72};
  bool started = false;
  const Rendered r = render(e, 1.0, [&](Engine& eng, double) {
    if (!started) {
      for (int n : notes) eng.noteOn(n, 90, 0, 0);
      started = true;
    }
  });
  INFO("8 voices: active=%d, peak=%.3f, rms=%.4f", e.activeVoices(), peak(r.l), rms(r.l));
  CHECK(e.activeVoices() == 8);
  CHECK(e.voicesInPart(0) == 8);
  CHECK(allFinite(r));
  CHECK(rms(r.l) > 0.01);
  CHECK(peak(r.l) <= 1.0f);
}

TEST(EngineVoiceStealing) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setGlobalParam(Part1Voices, 2.0f);
  e.noteOn(60, 100, 0, 0);
  e.noteOn(64, 100, 0, 0);
  e.noteOn(67, 100, 0, 0);
  const Rendered r = render(e, 0.2);
  INFO("voice stealing: active=%d (limit 2), peak=%.3f", e.activeVoices(), peak(r.l));
  CHECK(e.activeVoices() <= 2);
  CHECK(e.voicesInPart(0) == 2);
  CHECK(allFinite(r));
}

TEST(EngineMultitimbralParts) {
  Engine e;
  e.init();
  drySetup(e, 0);
  // Enable 2 voices on parts 0 and 1, pin part 1 hard right.
  for (int p = 0; p < kNumParts; ++p) e.setGlobalParam(Part1Voices + p, p < 2 ? 2.0f : 0.0f);
  e.setPartParam(1, Osc1Wave, 0.0f);
  e.setPartParam(1, PartPan, 1.0f);
  bool started = false;
  const Rendered r = render(e, 0.5, [&](Engine& eng, double) {
    if (!started) {
      eng.noteOn(60, 100, 0, 0);
      eng.noteOn(67, 100, 1, 1);
      started = true;
    }
  });
  INFO("multitimbral: part0 meter=%.4f, part1 meter=%.4f, rmsL=%.4f, rmsR=%.4f",
       e.partMeter(0), e.partMeter(1), rms(r.l), rms(r.r));
  CHECK(e.partMeter(0) > 0.001f);
  CHECK(e.partMeter(1) > 0.001f);
  CHECK(e.voicesInPart(0) == 1);
  CHECK(e.voicesInPart(1) == 1);
  CHECK(rms(r.r) > rms(r.l));  // part 1 panned right
  CHECK(allFinite(r));
}

TEST(EnginePartVoiceLimits) {
  Engine e;
  e.init();
  drySetup(e, 0);
  for (int p = 0; p < kNumParts; ++p) e.setGlobalParam(Part1Voices + p, 2.0f);
  for (int i = 0; i < 3; ++i) e.noteOn(60 + i, 100, 0, 0);
  for (int i = 0; i < 2; ++i) e.noteOn(70 + i, 100, 1, 1);
  const Rendered r = render(e, 0.2);
  INFO("part voice limits: part0=%d part1=%d total=%d", e.voicesInPart(0), e.voicesInPart(1),
       e.activeVoices());
  CHECK(e.voicesInPart(0) == 2);
  CHECK(e.voicesInPart(1) == 2);
  CHECK(e.activeVoices() == 4);
  CHECK(allFinite(r));
}

TEST(EngineMonoAndLegato) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setGlobalParam(PolyMode, 1.0f);  // mono
  bool started = false;
  const Rendered r = render(e, 0.4, [&](Engine& eng, double t) {
    if (!started) {
      eng.noteOn(60, 100, 0, 0);
      eng.noteOn(64, 100, 0, 0);
      started = true;
    }
    (void)t;
  });
  INFO("mono: active=%d", e.activeVoices());
  CHECK(e.activeVoices() == 1);
  CHECK(allFinite(r));

  Engine e2;
  e2.init();
  drySetup(e2, 0);
  e2.setGlobalParam(PolyMode, 2.0f);  // legato
  e2.noteOn(60, 100, 0, 0);
  render(e2, 0.1);
  e2.noteOn(67, 100, 0, 0);
  const Rendered r2 = render(e2, 0.1);
  INFO("legato: active=%d", e2.activeVoices());
  CHECK(e2.activeVoices() == 1);
  CHECK(allFinite(r2));
}

TEST(EngineMatrixCrossPart) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(1, Cutoff, 800.0f);
  e.setPartParam(0, Lfo1Rate, 5.0f);
  ModSlotData slot;
  slot.source = MsLfo1;
  slot.target = static_cast<uint8_t>(Cutoff);
  slot.depth = 100;
  modSlotSetPart(slot, 1);  // receiver = part 1 (cross-part modulation)
  modSlotSetCurve(slot, McLinear);
  e.setModSlot(0, 0, slot);
  float minCut = 1e9f, maxCut = -1e9f;
  bool started = false;
  const Rendered r = render(e, 0.5, [&](Engine& eng, double) {
    if (!started) {
      eng.noteOn(60, 100, 0, 0);
      eng.noteOn(55, 100, 1, 1);
      started = true;
    }
    const float cut = eng.modulatedPartParams(1).v[Cutoff];
    minCut = std::fmin(minCut, cut);
    maxCut = std::fmax(maxCut, cut);
  });
  INFO("cross-part matrix: part1 cutoff modulated %.1f .. %.1f Hz (base 800)", minCut, maxCut);
  CHECK(std::isfinite(minCut) && std::isfinite(maxCut));
  CHECK(maxCut - minCut > 100.0f);
  CHECK(minCut >= 20.0f && maxCut <= 20000.0f);
  CHECK(allFinite(r));
}

TEST(EngineMatrixFeedbackStable) {
  Engine e;
  e.init();
  drySetup(e, 0);
  // All 16 slots active with feedback into other slots' depths + cross-part
  // targets + global FX targets; must stay finite and bounded.
  for (int s = 0; s < kModSlots; ++s) {
    ModSlotData d;
    d.source = static_cast<uint8_t>(MsSlotBase + ((s + 1) % kModSlots));
    d.depth = (s % 2 == 0) ? 100 : -100;
    if (s < 8) {
      d.target = static_cast<uint8_t>((s * 5) % kNumPartParams);
    } else if (s < 12) {
      d.target = static_cast<uint8_t>(MtSlotDepth + (s % 4));
    } else {
      d.target = static_cast<uint8_t>(MtFxDelayMix);
    }
    modSlotSetPart(d, static_cast<uint8_t>(s % kNumParts));
    modSlotSetCurve(d, static_cast<ModCurve>(s % 4));
    e.setModSlot(0, s, d);
  }
  e.setPartParam(0, Lfo1Rate, 4.0f);
  bool started = false;
  const Rendered r = render(e, 3.0, [&](Engine& eng, double) {
    if (!started) {
      eng.noteOn(60, 110, 0, 0);
      started = true;
    }
  });
  INFO("matrix feedback: finite=%d peak=%.3f rms=%.4f", allFinite(r) ? 1 : 0, peak(r.l),
       rms(r.l));
  CHECK(allFinite(r));
  CHECK(peak(r.l) <= 1.0f);
  CHECK(peak(r.r) <= 1.0f);
  CHECK(rms(r.l) > 0.001);
}

TEST(EngineMoogLadderStability) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(0, Osc1Wave, 0.0f);
  e.setPartParam(0, FilterChar, 1.0f);   // Moog ladder
  e.setPartParam(0, FilterMode, 0.0f);   // 24 dB
  e.setPartParam(0, Cutoff, 300.0f);
  e.setPartParam(0, Resonance, 1.0f);    // self-oscillation edge
  e.setPartParam(0, FilterDrive, 0.8f);
  bool started = false;
  const Rendered r = render(e, 3.0, [&](Engine& eng, double) {
    if (!started) {
      eng.noteOn(45, 110, 0, 0);
      started = true;
    }
  });
  INFO("ladder res=100%%: finite=%d peak=%.3f rms=%.4f", allFinite(r) ? 1 : 0, peak(r.l),
       rms(r.l, 48000, 144000));
  CHECK(allFinite(r));
  CHECK(peak(r.l) <= 1.0f);
  CHECK(peak(r.r) <= 1.0f);
  CHECK(rms(r.l, 48000, 144000) > 0.001);  // still sounding (no dead filter)
}

TEST(EngineFmAlgorithms) {
  for (int algo = 0; algo < kFmAlgorithms; ++algo) {
    FmCore fm;
    fm.init();
    const float ratios[4] = {1.0f, 1.0f, 2.0f, 3.0f};
    const float levels[4] = {1.0f, 0.35f, 0.3f, 0.25f};
    fm.setParams(algo, ratios, levels, 0.15f);
    fm.noteOn(440.0f);
    std::vector<float> out(48000);
    float p = 0.0f;
    for (int i = 0; i < 48000; ++i) {
      out[static_cast<size_t>(i)] = fm.tick();
      p = std::fmax(p, std::fabs(out[static_cast<size_t>(i)]));
    }
    bool finite = true;
    for (float v : out) if (!std::isfinite(v)) finite = false;
    const double fund = goertzel(out, 440.0, 4800, 48000);
    const double sub = goertzel(out, 220.0, 4800, 48000);
    const double ratio = sub / (fund + 1e-12);
    INFO("FM algo %d: peak=%.3f fundamental=%.4f subharmonic(220Hz)=%.2f dB rel", algo, p, fund,
         20.0 * std::log10(ratio + 1e-12));
    CHECK(finite);
    CHECK(p > 0.01f);
    CHECK(fm.activeOperators() == 4);
    CHECK(ratio < 0.01);  // no subharmonic content (< -40 dB)
    CHECK(goertzel(out, 440.0, 4800, 48000) > 0.001);
  }
}
