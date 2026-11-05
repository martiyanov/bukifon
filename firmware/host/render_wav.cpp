// SPDX-License-Identifier: GPL-3.0-or-later
// Host renderer: renders the WAV files used by the FFT/stability reports.
//
//   bukifon_render <outdir>
//
// Produces (48 kHz / 16 bit / stereo):
//   demo_5s.wav        – 5 second multitimbral performance (mandatory test #1)
//   note_a4.wav        – dry saw A4 for tuning (A4 = 440 Hz ± 0.1 %)
//   eight_voices.wav   – 8 simultaneous voices
//   fm_algo0.wav .. fm_algo7.wav – the 8 FM algorithms (subharmonic test)
//   ladder_res100.wav  – Moog ladder at resonance 100 % (stability test)
//   matrix_stress.wav  – 16-slot matrix with feedback + cross-part routes
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>

#include "audio/engine.hpp"
#include "core/math.hpp"
#include "dsp/wavetable.hpp"
#include "wav_writer.hpp"

using namespace bukifon;

namespace {


void resetMatrix(Engine& e) {
  for (int p = 0; p < kNumParts; ++p) {
    for (int s = 0; s < kModSlots; ++s) {
      ModSlotData d;
      d.source = MsNone;
      d.target = Cutoff;
      d.depth = 0;
      modSlotSetPart(d, p);
      e.setModSlot(p, s, d);
    }
  }
}

void drySetup(Engine& e, int part = 0) {
  e.reset();
  resetMatrix(e);
  e.setGlobalParam(FxDrive, 0.0f);
  e.setGlobalParam(FxChorusMix, 0.0f);
  e.setGlobalParam(FxDelayMix, 0.0f);
  e.setGlobalParam(FxLimiterThreshold, 1.0f);
  e.setGlobalParam(MasterVolume, 0.9f);
  e.setGlobalParam(BendRange, 2.0f);
  for (int p = 0; p < kNumParts; ++p) {
    e.setGlobalParam(Part1Voices + p, p == part ? 8.0f : 0.0f);
    e.setPartParam(p, Osc1Wave, 4.0f);   // sine
    e.setPartParam(p, Osc1Level, 1.0f);
    e.setPartParam(p, Osc2Level, 0.0f);
    e.setPartParam(p, SubLevel, 0.0f);
    e.setPartParam(p, NoiseLevel, 0.0f);
    e.setPartParam(p, FmMode, 0.0f);
    e.setPartParam(p, FilterChar, 0.0f);  // SVF
    e.setPartParam(p, FilterMode, 1.0f);  // LP12
    e.setPartParam(p, Cutoff, 20000.0f);
    e.setPartParam(p, Resonance, 0.0f);
    e.setPartParam(p, FilterDrive, 0.0f);
    e.setPartParam(p, FilterEnvAmt, 0.0f);
    e.setPartParam(p, FilterKeytrack, 0.0f);
    e.setPartParam(p, Env1A, 0.002f);
    e.setPartParam(p, Env1D, 0.1f);
    e.setPartParam(p, Env1S, 1.0f);
    e.setPartParam(p, Env1R, 0.05f);
    e.setPartParam(p, Env1Mode, 0.0f);
    e.setPartParam(p, PartLevel, 0.9f);
    e.setPartParam(p, PartPan, 0.0f);
    e.setPartParam(p, EnsembleAmount, 0.0f);
    e.setPartParam(p, CrushMix, 0.0f);
  }
}

// Renders `seconds` of audio, calling `onBlock(engine, timeSeconds)` before each
// block. Returns peak absolute sample value of the rendered float stream.
float renderToFile(const std::string& path, Engine& e, double seconds,
                   const std::function<void(Engine&, double)>& onBlock) {
  WavWriter w;
  if (!w.open(path.c_str())) {
    std::fprintf(stderr, "cannot open %s\n", path.c_str());
    return 0.0f;
  }
  const int totalFrames = static_cast<int>(seconds * kSampleRate + 0.5);
  int frame = 0;
  float peak = 0.0f;
  while (frame < totalFrames) {
    const int n = std::min(kBlockSize, totalFrames - frame);
    const double t = static_cast<double>(frame) / kSampleRate;
    if (onBlock) onBlock(e, t);
    static float l[kBlockSize];
    static float r[kBlockSize];
    e.process(l, r, n);
    w.writeStereo(l, r, n, &e.dither());
    for (int i = 0; i < n; ++i) {
      peak = std::fmax(peak, std::fmax(std::fabs(l[i]), std::fabs(r[i])));
    }
    frame += n;
  }
  w.close();
  std::printf("rendered %-28s %6.2f s  peak=%.3f\n", path.c_str(), seconds, peak);
  return peak;
}

void renderNoteA4(const std::string& dir) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(0, Osc1Wave, 0.0f);  // saw for the mip/aliasing test
  e.setPartParam(0, Env1A, 0.001f);
  bool started = false;
  renderToFile(dir + "/note_a4.wav", e, 2.0, [&](Engine& eng, double t) {
    if (!started) {
      eng.noteOn(69, 100, 0, 0);
      started = true;
    }
    (void)t;
  });
}

void renderEightVoices(const std::string& dir) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(0, Osc1Wave, 0.0f);
  e.setPartParam(0, Env1A, 0.002f);
  bool started = false;
  const int notes[8] = {60, 62, 64, 65, 67, 69, 71, 72};
  renderToFile(dir + "/eight_voices.wav", e, 2.0, [&](Engine& eng, double t) {
    if (!started) {
      for (int i = 0; i < 8; ++i) eng.noteOn(notes[i], 90, 0, 0);
      started = true;
    }
    (void)t;
  });
}

void renderFmAlgorithms(const std::string& dir) {
  for (int algo = 0; algo < kFmAlgorithms; ++algo) {
    Engine e;
    e.init();
    drySetup(e, 0);
    e.setPartParam(0, Osc1Level, 0.0f);
    e.setPartParam(0, FmMode, 1.0f);
    e.setPartParam(0, FmAlgorithm, static_cast<float>(algo));
    e.setPartParam(0, FmRatio1, 1.0f);
    e.setPartParam(0, FmRatio2, 1.0f);
    e.setPartParam(0, FmRatio3, 2.0f);
    e.setPartParam(0, FmRatio4, 3.0f);
    e.setPartParam(0, FmLevel1, 1.0f);
    e.setPartParam(0, FmLevel2, 0.35f);
    e.setPartParam(0, FmLevel3, 0.3f);
    e.setPartParam(0, FmLevel4, 0.25f);
    e.setPartParam(0, FmFeedback, 0.15f);
    e.setPartParam(0, Env1A, 0.001f);
    bool started = false;
    char name[64];
    std::snprintf(name, sizeof(name), "/fm_algo%d.wav", algo);
    renderToFile(dir + name, e, 1.0, [&](Engine& eng, double t) {
      if (!started) {
        eng.noteOn(69, 100, 0, 0);
        started = true;
      }
      (void)t;
    });
  }
}

void renderLadderRes100(const std::string& dir) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(0, Osc1Wave, 0.0f);
  e.setPartParam(0, FilterChar, 1.0f);  // Moog ladder
  e.setPartParam(0, FilterMode, 0.0f);  // 24 dB
  e.setPartParam(0, Cutoff, 400.0f);
  e.setPartParam(0, Resonance, 1.0f);
  e.setPartParam(0, FilterDrive, 0.6f);
  e.setPartParam(0, Env1S, 1.0f);
  bool started = false;
  renderToFile(dir + "/ladder_res100.wav", e, 3.0, [&](Engine& eng, double t) {
    if (!started) {
      eng.noteOn(45, 110, 0, 0);
      started = true;
    }
    (void)t;
  });
}

void renderMatrixStress(const std::string& dir) {
  Engine e;
  e.init();
  drySetup(e, 0);
  e.setPartParam(0, Osc1Wave, 0.0f);
  // All 16 slots active: LFOs/envelopes/velocity/other slots -> parameters of
  // several parts (cross-part), including feedback into slot depths.
  const ModSource sources[16] = {MsLfo1, MsLfo2, MsEnv1, MsEnv2,
                                 static_cast<ModSource>(MsSlotBase + 0),
                                 static_cast<ModSource>(MsSlotBase + 1),
                                 static_cast<ModSource>(MsSlotBase + 2),
                                 static_cast<ModSource>(MsSlotBase + 3),
                                 static_cast<ModSource>(MsPartOutBase + 1), MsVelocity,
                                 MsLfo3, MsLfo4, MsEnv3, MsEnv4, MsRandom, MsConstant};
  for (int s = 0; s < kModSlots; ++s) {
    ModSlotData d;
    d.source = sources[s];
    if (s < 8) {
      d.target = static_cast<uint8_t>((s * 7) % kNumPartParams);
    } else if (s < 12) {
      d.target = static_cast<uint8_t>(MtSlotDepth + (s % 4));
    } else {
      d.target = static_cast<uint8_t>(MtFxDelayMix);
    }
    d.depth = (s % 2 == 0) ? 100 : -100;
    modSlotSetPart(d, static_cast<uint8_t>(s % kNumParts));
    modSlotSetCurve(d, static_cast<ModCurve>(s % 4));
    e.setModSlot(0, s, d);
  }
  e.setPartParam(0, Lfo1Rate, 3.0f);
  e.setPartParam(0, Lfo2Rate, 0.7f);
  e.setGlobalParam(FxDelayMix, 0.4f);
  bool started = false;
  renderToFile(dir + "/matrix_stress.wav", e, 2.0, [&](Engine& eng, double t) {
    if (!started) {
      eng.noteOn(60, 100, 0, 0);
      started = true;
    }
    (void)t;
  });
}

void renderDemo5s(const std::string& dir) {
  Engine e;
  e.init();
  e.loadFactoryPatch(1);
  e.setGlobalParam(MasterVolume, 0.85f);
  e.setGlobalParam(Bpm, 120.0f);
  // Give each part its own character: Moog, SVF, Polyvox ensemble, FM.
  e.setPartParam(0, FilterChar, 1.0f);
  e.setPartParam(1, FilterChar, 0.0f);
  e.setPartParam(2, FilterChar, 2.0f);
  e.setPartParam(2, EnsembleAmount, 0.55f);
  e.setPartParam(3, FmMode, 1.0f);
  e.setPartParam(3, FmAlgorithm, 3.0f);
  e.setGlobalParam(Part1Voices, 2.0f);
  e.setGlobalParam(Part2Voices, 2.0f);
  e.setGlobalParam(Part3Voices, 2.0f);
  e.setGlobalParam(Part4Voices, 2.0f);
  e.setGlobalParam(FxDelayMix, 0.28f);
  e.setGlobalParam(FxChorusMix, 0.18f);

  struct NoteEv {
    double t;
    int note;
    int part;
    int vel;
    bool on;
  };
  const NoteEv events[] = {
      {0.10, 48, 0, 100, true},  {0.10, 55, 0, 92, true},   {0.10, 60, 0, 88, true},
      {0.90, 43, 1, 110, true},  {1.70, 55, 2, 80, true},   {1.70, 60, 2, 75, true},
      {1.70, 67, 2, 70, true},   {2.50, 72, 3, 95, true},   {2.50, 76, 3, 90, true},
      {3.20, 48, 0, 100, false},{3.20, 55, 0, 92, false},  {3.20, 60, 0, 88, false},
      {3.30, 43, 1, 110, false},{3.40, 50, 1, 100, true},   {4.10, 55, 2, 80, false},
      {4.10, 60, 2, 75, false}, {4.10, 67, 2, 70, false},   {4.60, 72, 3, 95, false},
      {4.60, 76, 3, 90, false}, {4.60, 79, 3, 85, true},    {3.40, 55, 1, 90, true},
      {2.00, 60, 0, 90, true},  {4.20, 64, 0, 85, true},    {4.20, 67, 0, 80, true},
  };
  size_t evIndex = 0;
  renderToFile(dir + "/demo_5s.wav", e, 5.0, [&](Engine& eng, double t) {
    while (evIndex < sizeof(events) / sizeof(events[0]) && events[evIndex].t <= t) {
      const NoteEv& ev = events[evIndex];
      if (ev.on) {
        eng.noteOn(ev.note, ev.vel, ev.part, ev.part);
      } else {
        eng.noteOff(ev.note, ev.part);
      }
      ++evIndex;
    }
    // Slow filter sweep on part 0 and delay feedback ride.
    const float sweep = 350.0f * std::pow(2.0f, static_cast<float>(t) * 1.1f);
    eng.setPartParam(0, Cutoff, std::fmin(sweep, 9000.0f));
    eng.setPartParam(2, Cutoff, 1200.0f + 600.0f * std::sin(static_cast<float>(t) * 0.9f));
    eng.setGlobalParam(FxDelayFb, 0.25f + 0.1f * std::sin(static_cast<float>(t)));
    eng.setMacro(0, static_cast<float>(0.5 + 0.5 * std::sin(t * 0.7)));
  });
  // Keep the performance inside 5 s exactly; renderToFile already did.
}

}  // namespace

int main(int argc, char** argv) {
  const std::string dir = argc > 1 ? argv[1] : ".";
  std::printf("Bukifon host renderer — 48 kHz / 16 bit / stereo\n");
  renderDemo5s(dir);
  renderNoteA4(dir);
  renderEightVoices(dir);
  renderFmAlgorithms(dir);
  renderLadderRes100(dir);
  renderMatrixStress(dir);
  std::printf("done.\n");
  return 0;
}
