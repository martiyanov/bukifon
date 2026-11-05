// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <vector>

#include "core/math.hpp"
#include "dsp/effects.hpp"
#include "dsp/ensemble.hpp"
#include "dsp/envelope.hpp"
#include "dsp/filter.hpp"
#include "dsp/lfo.hpp"
#include "dsp/oscillator.hpp"
#include "dsp/wavetable.hpp"
#include "test_framework.hpp"
#include "test_helpers.hpp"

using namespace bukifon;

namespace {

// Measures the number of samples a stage lasts (stage boundary is the exact
// envelope definition; the tolerance is copied from the spec: +/-2 %).
int measureStage(Envelope& env, Envelope::Stage target, int maxSamples) {
  int n = 0;
  while (env.stage() != target && n < maxSamples) {
    env.tick();
    ++n;
  }
  return n;
}

}  // namespace

TEST(EnvelopeTiming) {
  Envelope env;
  env.init(48000.0f);
  env.setParams(0.010f, 0.050f, 0.5f, 0.020f, 0.0f, EnvAdsr);
  env.noteOn(1.0f);
  const int attack = measureStage(env, Envelope::Decay, 48000);
  const int decay = measureStage(env, Envelope::Sustain, 48000);
  env.noteOff();
  const int release = measureStage(env, Envelope::Idle, 48000);
  const double expA = 0.010 * 48000.0, expD = 0.050 * 48000.0, expR = 0.020 * 48000.0;
  INFO("ADSR samples: A=%d (exp %.0f, %+.2f%%) D=%d (exp %.0f, %+.2f%%) R=%d (exp %.0f, %+.2f%%)",
       attack, expA, (attack - expA) / expA * 100.0, decay, expD, (decay - expD) / expD * 100.0,
       release, expR, (release - expR) / expR * 100.0);
  CHECK(std::fabs(attack - expA) / expA < 0.02);
  CHECK(std::fabs(decay - expD) / expD < 0.02);
  CHECK(std::fabs(release - expR) / expR < 0.02);
}

TEST(EnvelopeClicks) {
  Envelope env;
  env.init(48000.0f);
  env.setParams(0.005f, 0.02f, 0.6f, 0.02f, -0.2f, EnvAdsr);
  env.noteOn(1.0f);
  float prev = 0.0f, maxDelta = 0.0f;
  bool finite = true;
  for (int i = 0; i < 2400; ++i) {
    const float l = env.tick();
    if (!std::isfinite(l)) finite = false;
    maxDelta = std::fmax(maxDelta, std::fabs(l - prev));
    prev = l;
  }
  env.noteOff();
  bool endedAtZero = false;
  for (int i = 0; i < 4800; ++i) {
    const float l = env.tick();
    maxDelta = std::fmax(maxDelta, std::fabs(l - prev));
    prev = l;
    if (env.stage() == Envelope::Idle) {
      endedAtZero = (l == 0.0f);
      break;
    }
  }
  INFO("envelope edges: max step delta=%.5f, release ends at 0=%d", maxDelta, endedAtZero ? 1 : 0);
  CHECK(finite);
  CHECK(maxDelta < 0.01f);  // no click on the edges (+/- 1 sample)
  CHECK(endedAtZero);
}

TEST(EnvelopeLoopMode) {
  Envelope env;
  env.init(48000.0f);
  env.setParams(0.005f, 0.010f, 0.5f, 0.01f, 0.0f, EnvLoop);
  env.noteOn(1.0f);
  float prev = 0.0f, maxDelta = 0.0f, minL = 1.0f, maxL = 0.0f;
  int attackVisits = 0;
  bool inAttack = false;
  for (int i = 0; i < 48000; ++i) {
    const float l = env.tick();
    maxDelta = std::fmax(maxDelta, std::fabs(l - prev));
    prev = l;
    minL = std::fmin(minL, l);
    maxL = std::fmax(maxL, l);
    if (env.stage() == Envelope::Attack && !inAttack) ++attackVisits;
    inAttack = env.stage() == Envelope::Attack;
  }
  INFO("loop envelope: cycles=%d, range=[%.3f..%.3f], max step delta=%.5f", attackVisits, minL, maxL,
       maxDelta);
  CHECK(maxDelta < 0.01f);  // loop restarts continuously (no jump)
  CHECK(minL >= 0.0f && maxL <= 1.0f);
  CHECK(attackVisits > 5);
}

TEST(EnvelopeTimeModulationNoClick) {
  Envelope env;
  env.init(48000.0f);
  env.setParams(0.01f, 0.05f, 0.5f, 0.02f, 0.0f, EnvAdsr);
  env.noteOn(1.0f);
  float prev = 0.0f;
  for (int i = 0; i < 100; ++i) {
    prev = env.tick();
  }
  env.setTimes(0.5f, 0.05f, 0.02f);  // matrix modulates envelope time mid-stage
  const float next = env.tick();
  INFO("modulated envelope time: level jump=%.6f", std::fabs(next - prev));
  CHECK(std::fabs(next - prev) < 0.01f);
  CHECK(env.stage() == Envelope::Attack);
}

TEST(LfoShapes) {
  const int n = 48000;
  for (int shape = 0; shape < kNumLfoShapes; ++shape) {
    Lfo lfo;
    lfo.init(48000.0f);
    lfo.setParams(2.0f, shape, false, true, 0.0f, 0.0f, 120.0f);
    lfo.noteOn(60.0f);
    double acc = 0.0, sq = 0.0;
    float mn = 2.0f, mx = -2.0f;
    float absMin = 2.0f;
    bool finite = true;
    for (int i = 0; i < n; ++i) {
      const float v = lfo.tick();
      if (!std::isfinite(v)) finite = false;
      if (i >= n / 2) {
        acc += v;
        sq += static_cast<double>(v) * v;
        absMin = std::fmin(absMin, std::fabs(v));
      }
      mn = std::fmin(mn, v);
      mx = std::fmax(mx, v);
    }
    const double mean = acc / (n / 2);
    const double rms = std::sqrt(sq / (n / 2));
    INFO("LFO shape %d: min=%.3f max=%.3f mean=%+.4f rms=%.3f", shape, mn, mx, mean, rms);
    CHECK(finite);
    CHECK(mn >= -1.001f && mx <= 1.001f);
    CHECK(rms > ((shape == LfoSampleHold || shape == LfoSmoothRandom) ? 0.05 : 0.3));
    if (shape == LfoSquare || shape == LfoPulse25) {
      CHECK(absMin > 0.99f);  // two-level waveform
    }
    if (shape == LfoSine || shape == LfoTriangle) CHECK(std::fabs(mean) < 0.05);
  }
}

TEST(WavetableMipSelection) {
  // For all notes whose fundamental is low enough for the 8 mip levels, the
  // selected level must stay band-limited below Nyquist.
  const float notes[5] = {20.0f, 110.0f, 440.0f, 1000.0f, 3000.0f};
  for (float f : notes) {
    const int mip = WavetableBank::mipForFrequency(f);
    const int maxH = WavetableBank::mipMaxHarmonic(mip);
    const float topHarmonic = static_cast<float>(maxH) * f;
    INFO("mip: f0=%6.1f Hz -> level %d (harmonics 1..%d, top %.0f Hz)", f, mip, maxH, topHarmonic);
    CHECK(mip >= 0 && mip < kMipLevels);
    CHECK(topHarmonic <= 24000.0f);
  }
}

TEST(OscillatorTuning) {
  const float notes[3] = {110.0f, 440.0f, 1000.0f};
  for (float f : notes) {
    Oscillator osc;
    osc.init(48000.0f);
    osc.setWave(4);  // sine
    osc.setUnison(1);
    osc.setFrequency(f);
    osc.retrigger(0.0f);
    std::vector<float> buf(48000);
    for (int i = 0; i < 48000; ++i) buf[static_cast<size_t>(i)] = osc.tick();
    const double measured = testutil::zeroCrossFrequency(buf, 0.1, 0.9);
    const double err = (measured - f) / f * 100.0;
    INFO("oscillator: target %.1f Hz, measured %.4f Hz, error %+.4f %%", f, measured, err);
    CHECK(std::fabs(err) < 0.1);
  }
}

TEST(OscillatorModes) {
  for (int mode = 0; mode < kNumOscModes; ++mode) {
    Oscillator osc;
    osc.init(48000.0f);
    osc.setWave(0);
    osc.setMode(mode);
    osc.setUnison(2);
    osc.setDetune(0.3f);
    osc.setSpread(0.4f);
    osc.setPulseWidth(0.3f);
    osc.setFrequency(220.0f);
    osc.retrigger(0.0f);
    float p = 0.0f;
    double acc = 0.0;
    bool finite = true;
    for (int i = 0; i < 24000; ++i) {
      const float v = osc.tick();
      if (!std::isfinite(v)) finite = false;
      p = std::fmax(p, std::fabs(v));
      acc += static_cast<double>(v) * v;
    }
    INFO("oscillator mode %d: peak=%.3f rms=%.3f", mode, p, std::sqrt(acc / 24000));
    CHECK(finite);
    CHECK(p <= 1.5f);
    CHECK(std::sqrt(acc / 24000) > 0.01);
  }
}

TEST(FilterSvfSlope) {
  auto measure = [](float freq) {
    Filter f;
    f.init(48000.0f);
    f.setCharacter(CharSvf);
    f.setMode(Fm_LP24);
    f.setCutoff(1000.0f);
    f.setResonance(0.0f);
    f.setDrive(0.0f);
    const double inc = 2.0 * M_PI * freq / 48000.0;
    double phase = 0.0, acc = 0.0;
    const int n = 48000;
    for (int i = 0; i < n; ++i) {
      const float x = 0.5f * static_cast<float>(std::sin(phase));
      phase += inc;
      const float y = f.process(x);
      if (i > n / 2) acc += static_cast<double>(y) * y;
    }
    return std::sqrt(acc / (n / 2));
  };
  const double at100 = measure(100.0f);
  const double at4000 = measure(4000.0f);
  const double db = 20.0 * std::log10(at4000 / at100 + 1e-12);
  INFO("SVF LP24: 100 Hz rms=%.5f, 4 kHz rms=%.5f, attenuation=%+.1f dB (expect ~-48 dB)", at100,
       at4000, db);
  CHECK(db < -40.0);
  CHECK(db > -56.0);
}

TEST(FilterLadderStability) {
  Filter f;
  f.init(48000.0f);
  f.setCharacter(CharMoog);
  f.setMode(Fm_LP24);
  f.setCutoff(600.0f);
  f.setResonance(1.0f);
  f.setDrive(0.7f);
  float p = 0.0f;
  double tail = 0.0;
  bool finite = true;
  for (int i = 0; i < 96000; ++i) {
    const float in = (i == 0) ? 1.0f : 0.0f;
    const float y = f.process(in);
    if (!std::isfinite(y)) finite = false;
    p = std::fmax(p, std::fabs(y));
    if (i > 48000) tail += static_cast<double>(y) * y;
  }
  INFO("Moog ladder impulse res=100%%: finite=%d peak=%.3f tail_rms=%.4f", finite ? 1 : 0, p,
       std::sqrt(tail / 48000));
  CHECK(finite);
  CHECK(p < 10.0f);
  CHECK(std::sqrt(tail / 48000) > 0.0001);  // self-oscillation still alive
}

TEST(FilterPolyvoxCharacter) {
  Filter f;
  f.init(48000.0f);
  f.setCharacter(CharPolyvox);
  f.setCutoff(700.0f);
  f.setResonance(0.8f);
  f.setDrive(0.2f);
  double acc = 0.0;
  bool finite = true;
  for (int i = 0; i < 48000; ++i) {
    const float x = 0.4f * static_cast<float>(std::sin(2.0 * M_PI * 200.0 * i / 48000.0));
    const float y = f.process(x);
    if (!std::isfinite(y)) finite = false;
    if (i > 24000) acc += static_cast<double>(y) * y;
  }
  const double r = std::sqrt(acc / 24000);
  INFO("Polyvox formant filter: finite=%d rms=%.4f", finite ? 1 : 0, r);
  CHECK(finite);
  CHECK(r > 0.01);
}

TEST(DelayEchoTiming) {
  StereoDelay delay;
  delay.init(48000.0f);
  delay.setTime(0.05f);
  delay.setFeedback(0.0f);
  delay.setMix(1.0f);
  delay.setDamping(20000.0f);
  std::vector<float> l(48000, 0.0f), r(48000, 0.0f);
  l[0] = 0.5f;
  r[0] = 0.5f;
  for (int i = 0; i < 48000; i += 256) {
    const int n = std::min(256, 48000 - i);
    delay.process(&l[static_cast<size_t>(i)], &r[static_cast<size_t>(i)], n);
  }
  // Find the echo peak after the first sample.
  int peakIdx = 0;
  float peakVal = 0.0f;
  for (int i = 100; i < 48000; ++i) {
    if (std::fabs(l[static_cast<size_t>(i)]) > peakVal) {
      peakVal = std::fabs(l[static_cast<size_t>(i)]);
      peakIdx = i;
    }
  }
  INFO("delay: echo at sample %d (expected %d), level=%.3f", peakIdx, static_cast<int>(0.05 * 48000),
       peakVal);
  CHECK(std::abs(peakIdx - static_cast<int>(0.05 * 48000)) <= 3);
  CHECK(peakVal > 0.1f);
}

TEST(LimiterCeiling) {
  Limiter limiter;
  limiter.init(48000.0f);
  limiter.setThreshold(0.9f);
  limiter.setRelease(0.1f);
  std::vector<float> l(48000), r(48000);
  for (int i = 0; i < 48000; ++i) {
    l[static_cast<size_t>(i)] = 2.0f * static_cast<float>(std::sin(2.0 * M_PI * 220.0 * i / 48000.0));
    r[static_cast<size_t>(i)] = -l[static_cast<size_t>(i)];
  }
  for (int i = 0; i < 48000; i += 256) {
    const int n = std::min(256, 48000 - i);
    limiter.process(&l[static_cast<size_t>(i)], &r[static_cast<size_t>(i)], n);
  }
  float p = 0.0f;
  for (int i = 0; i < 48000; ++i) {
    p = std::fmax(p, std::fmax(std::fabs(l[static_cast<size_t>(i)]),
                               std::fabs(r[static_cast<size_t>(i)])));
  }
  INFO("limiter: threshold 0.900, measured ceiling %.4f", p);
  CHECK(p <= 0.9f + 1e-3f);
  CHECK(p > 0.5f);
}

TEST(BitcrushQuantisation) {
  BitcrushFx fx;
  fx.init();
  fx.setBits(4.0f);
  fx.setRate(0.0f);
  fx.setMix(1.0f);
  const float step = 1.0f / 8.0f;  // 4 bit -> 3 fraction bits
  bool quantised = true;
  bool finite = true;
  for (int i = 0; i < 4800; ++i) {
    float l = 0.4f * static_cast<float>(std::sin(2.0 * M_PI * 110.0 * i / 48000.0));
    float r = l;
    fx.process(&l, &r, 1);
    if (!std::isfinite(l)) finite = false;
    const float q = l / step;
    if (std::fabs(q - std::round(q)) > 1e-4f) quantised = false;
  }
  INFO("bitcrush 4 bit: quantised=%d, step=%.4f", quantised ? 1 : 0, step);
  CHECK(finite);
  CHECK(quantised);
}

TEST(EnsembleStereo) {
  Ensemble ens;
  ens.init(48000.0f);
  ens.setAmount(1.0f);
  ens.setRate(0.5f);
  std::vector<float> l(48000), r(48000);
  for (int i = 0; i < 48000; ++i) {
    const float s = 0.3f * static_cast<float>(std::sin(2.0 * M_PI * 220.0 * i / 48000.0));
    l[static_cast<size_t>(i)] = s;
    r[static_cast<size_t>(i)] = s;
  }
  for (int i = 0; i < 48000; i += 256) {
    const int n = std::min(256, 48000 - i);
    ens.process(&l[static_cast<size_t>(i)], &r[static_cast<size_t>(i)], n);
  }
  double accL = 0.0, accDiff = 0.0;
  bool finite = true;
  for (int i = 0; i < 48000; ++i) {
    if (!std::isfinite(l[static_cast<size_t>(i)]) || !std::isfinite(r[static_cast<size_t>(i)])) {
      finite = false;
    }
    accL += static_cast<double>(l[static_cast<size_t>(i)]) * l[static_cast<size_t>(i)];
    const double d = l[static_cast<size_t>(i)] - r[static_cast<size_t>(i)];
    accDiff += d * d;
  }
  INFO("ensemble: rms=%.4f stereo-difference rms=%.4f", std::sqrt(accL / 48000),
       std::sqrt(accDiff / 48000));
  CHECK(finite);
  CHECK(std::sqrt(accL / 48000) > 0.05);
  CHECK(std::sqrt(accDiff / 48000) > 0.001);  // ensemble produces width
}
