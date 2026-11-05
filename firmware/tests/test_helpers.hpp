// SPDX-License-Identifier: GPL-3.0-or-later
// Shared helpers for the host tests: dry engine setup, offline rendering and
// signal analysis (frequency estimation, Goertzel, RMS).
#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <functional>
#include <vector>

#include "audio/engine.hpp"
#include "core/config.hpp"
#include "core/modulation_defs.hpp"
#include "core/params.hpp"

namespace testutil {

using bukifon::Engine;
using bukifon::kBlockSize;
using bukifon::kMaxVoices;
using bukifon::kModSlots;
using bukifon::kNumParts;
using bukifon::kSampleRate;
using bukifon::ModSlotData;
using bukifon::MsNone;

inline void resetMatrix(Engine& e) {
  for (int p = 0; p < kNumParts; ++p) {
    for (int s = 0; s < kModSlots; ++s) {
      ModSlotData d;
      d.source = MsNone;
      d.target = 0;
      d.depth = 0;
      bukifon::modSlotSetPart(d, static_cast<uint8_t>(p));
      e.setModSlot(p, s, d);
    }
  }
}

// Dry, predictable test patch: sine osc on one part, filter wide open, no FX.
inline void drySetup(Engine& e, int part = 0) {
  e.reset();
  resetMatrix(e);
  e.setGlobalParam(bukifon::FxDrive, 0.0f);
  e.setGlobalParam(bukifon::FxChorusMix, 0.0f);
  e.setGlobalParam(bukifon::FxDelayMix, 0.0f);
  e.setGlobalParam(bukifon::FxLimiterThreshold, 1.0f);
  e.setGlobalParam(bukifon::MasterVolume, 0.9f);
  e.setGlobalParam(bukifon::BendRange, 2.0f);
  for (int p = 0; p < kNumParts; ++p) {
    e.setGlobalParam(bukifon::Part1Voices + p, p == part ? 8.0f : 0.0f);
    e.setPartParam(p, bukifon::Osc1Wave, 4.0f);
    e.setPartParam(p, bukifon::Osc1Level, 1.0f);
    e.setPartParam(p, bukifon::Osc2Level, 0.0f);
    e.setPartParam(p, bukifon::SubLevel, 0.0f);
    e.setPartParam(p, bukifon::NoiseLevel, 0.0f);
    e.setPartParam(p, bukifon::FmMode, 0.0f);
    e.setPartParam(p, bukifon::FilterChar, 0.0f);
    e.setPartParam(p, bukifon::FilterMode, 1.0f);
    e.setPartParam(p, bukifon::Cutoff, 20000.0f);
    e.setPartParam(p, bukifon::Resonance, 0.0f);
    e.setPartParam(p, bukifon::FilterDrive, 0.0f);
    e.setPartParam(p, bukifon::FilterEnvAmt, 0.0f);
    e.setPartParam(p, bukifon::FilterKeytrack, 0.0f);
    e.setPartParam(p, bukifon::Env1A, 0.002f);
    e.setPartParam(p, bukifon::Env1D, 0.1f);
    e.setPartParam(p, bukifon::Env1S, 1.0f);
    e.setPartParam(p, bukifon::Env1R, 0.05f);
    e.setPartParam(p, bukifon::Env1Mode, 0.0f);
    e.setPartParam(p, bukifon::PartLevel, 0.9f);
    e.setPartParam(p, bukifon::PartPan, 0.0f);
    e.setPartParam(p, bukifon::EnsembleAmount, 0.0f);
    e.setPartParam(p, bukifon::CrushMix, 0.0f);
  }
}

struct Rendered {
  std::vector<float> l;
  std::vector<float> r;
};

// Renders `seconds`, calling `onBlock(engine, t)` once per block.
inline Rendered render(Engine& e, double seconds,
                       const std::function<void(Engine&, double)>& onBlock = nullptr) {
  Rendered out;
  const int total = static_cast<int>(seconds * kSampleRate + 0.5);
  out.l.resize(static_cast<size_t>(total));
  out.r.resize(static_cast<size_t>(total));
  int frame = 0;
  float lbuf[kBlockSize];
  float rbuf[kBlockSize];
  while (frame < total) {
    const int n = std::min(kBlockSize, total - frame);
    if (onBlock) onBlock(e, static_cast<double>(frame) / kSampleRate);
    e.process(lbuf, rbuf, n);
    for (int i = 0; i < n; ++i) {
      out.l[static_cast<size_t>(frame + i)] = lbuf[i];
      out.r[static_cast<size_t>(frame + i)] = rbuf[i];
    }
    frame += n;
  }
  return out;
}

inline bool allFinite(const Rendered& x) {
  for (float v : x.l) if (!std::isfinite(v)) return false;
  for (float v : x.r) if (!std::isfinite(v)) return false;
  return true;
}

inline float peak(const std::vector<float>& x) {
  float p = 0.0f;
  for (float v : x) p = std::max(p, std::fabs(v));
  return p;
}

inline double rms(const std::vector<float>& x, int from = 0, int to = -1) {
  if (to < 0 || to > static_cast<int>(x.size())) to = static_cast<int>(x.size());
  if (from >= to) return 0.0;
  double acc = 0.0;
  for (int i = from; i < to; ++i) acc += static_cast<double>(x[static_cast<size_t>(i)]) * x[static_cast<size_t>(i)];
  return std::sqrt(acc / (to - from));
}

// Upward zero-crossing frequency estimate using linear interpolation. Works for
// sine-like signals; returns 0 when no crossings are found.
inline double zeroCrossFrequency(const std::vector<float>& x, double startSec, double endSec) {
  const int start = static_cast<int>(startSec * kSampleRate);
  const int end = std::min(static_cast<int>(endSec * kSampleRate), static_cast<int>(x.size()));
  int count = 0;
  double firstT = 0.0, lastT = 0.0;
  for (int i = start + 1; i < end; ++i) {
    const float a = x[static_cast<size_t>(i - 1)];
    const float b = x[static_cast<size_t>(i)];
    if (a <= 0.0f && b > 0.0f) {
      const double frac = (0.0 - a) / (b - a);
      const double t = (i - 1 + frac) / static_cast<double>(kSampleRate);
      if (count == 0) firstT = t;
      lastT = t;
      ++count;
    }
  }
  if (count < 2) return 0.0;
  return (count - 1) / (lastT - firstT);
}

// Goertzel magnitude normalised by N/2 (amplitude of a sinusoid at `freq`).
inline double goertzel(const std::vector<float>& x, double freq, int from, int to) {
  if (to > static_cast<int>(x.size())) to = static_cast<int>(x.size());
  const double w = 2.0 * M_PI * freq / static_cast<double>(kSampleRate);
  const double coeff = 2.0 * std::cos(w);
  double s0 = 0.0, s1 = 0.0, s2 = 0.0;
  for (int i = from; i < to; ++i) {
    s0 = x[static_cast<size_t>(i)] + coeff * s1 - s2;
    s2 = s1;
    s1 = s0;
  }
  const double real = s1 - s2 * std::cos(w);
  const double imag = s2 * std::sin(w);
  return std::sqrt(real * real + imag * imag) / ((to - from) * 0.5);
}

}  // namespace testutil
