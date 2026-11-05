// SPDX-License-Identifier: GPL-3.0-or-later
// Parameter tables for the 4 parts and global settings.
//
// Each parameter is a float in [min..max]; discrete/flag bits describe how the
// value is shown, quantised and stored in a patch (uint8 normalised).
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum ParamFlags : uint16_t {
  PF_NONE = 0,
  PF_LOG = 1u << 0,        // logarithmic mapping for normalisation / UI
  PF_DISCRETE = 1u << 1,   // integer steps
  PF_BIPOLAR = 1u << 2,    // -1..+1 style parameter
  PF_SECONDS = 1u << 3,    // display in s / ms
  PF_CENTS = 1u << 4,
  PF_HZ = 1u << 5,
  PF_PERCENT = 1u << 6,
  PF_SEMITONES = 1u << 7,
  PF_RATIO = 1u << 8,
};

struct ParamMeta {
  const char* name;  // short label for the 320x240 UI (<= 12 chars)
  float min;
  float max;
  float def;
  uint16_t flags;
};

// --- per-part parameters (91) ---------------------------------------------
// X(id, label, min, max, default, flags)
#define BUKIFON_PART_PARAM_LIST(X)                                   \
  X(Osc1Wave, "WAVE1", 0.0f, 7.0f, 0.0f, PF_DISCRETE)               \
  X(Osc1Coarse, "COARSE1", -24.0f, 24.0f, 0.0f, PF_SEMITONES)        \
  X(Osc1Fine, "FINE1", -100.0f, 100.0f, 0.0f, PF_CENTS)              \
  X(Osc1Level, "LEVEL1", 0.0f, 1.0f, 0.7f, PF_NONE)                  \
  X(Osc1Mode, "MODE1", 0.0f, 5.0f, 0.0f, PF_DISCRETE)                \
  X(Osc1Unison, "UNI1", 1.0f, 4.0f, 1.0f, PF_DISCRETE)               \
  X(Osc1Detune, "DETUNE1", 0.0f, 1.0f, 0.15f, PF_NONE)               \
  X(Osc1Spread, "SPREAD1", 0.0f, 1.0f, 0.5f, PF_NONE)                \
  X(Osc2Wave, "WAVE2", 0.0f, 7.0f, 4.0f, PF_DISCRETE)                \
  X(Osc2Coarse, "COARSE2", -24.0f, 24.0f, 0.0f, PF_SEMITONES)        \
  X(Osc2Fine, "FINE2", -100.0f, 100.0f, 0.0f, PF_CENTS)              \
  X(Osc2Level, "LEVEL2", 0.0f, 1.0f, 0.0f, PF_NONE)                  \
  X(Osc2Mode, "MODE2", 0.0f, 5.0f, 0.0f, PF_DISCRETE)                \
  X(Osc2Unison, "UNI2", 1.0f, 4.0f, 1.0f, PF_DISCRETE)               \
  X(Osc2Detune, "DETUNE2", 0.0f, 1.0f, 0.15f, PF_NONE)               \
  X(Osc2Spread, "SPREAD2", 0.0f, 1.0f, 0.5f, PF_NONE)                \
  X(FmAlgorithm, "FM ALGO", 0.0f, 7.0f, 0.0f, PF_DISCRETE)           \
  X(FmRatio1, "RATIO1", 0.5f, 32.0f, 1.0f, PF_RATIO)                 \
  X(FmRatio2, "RATIO2", 0.5f, 32.0f, 1.0f, PF_RATIO)                 \
  X(FmRatio3, "RATIO3", 0.5f, 32.0f, 2.0f, PF_RATIO)                 \
  X(FmRatio4, "RATIO4", 0.5f, 32.0f, 3.0f, PF_RATIO)                 \
  X(FmLevel1, "FMLEV1", 0.0f, 1.0f, 1.0f, PF_NONE)                   \
  X(FmLevel2, "FMLEV2", 0.0f, 1.0f, 0.5f, PF_NONE)                   \
  X(FmLevel3, "FMLEV3", 0.0f, 1.0f, 0.3f, PF_NONE)                   \
  X(FmLevel4, "FMLEV4", 0.0f, 1.0f, 0.2f, PF_NONE)                   \
  X(FmFeedback, "FM FB", 0.0f, 1.0f, 0.0f, PF_NONE)                  \
  X(FmMode, "FM MODE", 0.0f, 2.0f, 0.0f, PF_DISCRETE)                \
  X(SubLevel, "SUB", 0.0f, 1.0f, 0.0f, PF_NONE)                      \
  X(SubShape, "SUBSHAPE", 0.0f, 2.0f, 0.0f, PF_DISCRETE)             \
  X(NoiseLevel, "NOISE", 0.0f, 1.0f, 0.0f, PF_NONE)                  \
  X(FilterChar, "CHARACTER", 0.0f, 2.0f, 1.0f, PF_DISCRETE)          \
  X(Cutoff, "CUTOFF", 20.0f, 20000.0f, 2000.0f, PF_LOG | PF_HZ)              \
  X(Resonance, "RESONANCE", 0.0f, 1.0f, 0.2f, PF_NONE)               \
  X(FilterDrive, "DRIVE", 0.0f, 1.0f, 0.1f, PF_NONE)                 \
  X(FilterMode, "FILTER", 0.0f, 4.0f, 0.0f, PF_DISCRETE)             \
  X(FilterEnvAmt, "ENV AMT", -1.0f, 1.0f, 0.3f, PF_BIPOLAR)          \
  X(FilterKeytrack, "KEYTRACK", 0.0f, 1.0f, 0.3f, PF_NONE)           \
  X(Env1A, "ATK1", 0.0005f, 20.0f, 0.005f, PF_SECONDS | PF_LOG)      \
  X(Env1D, "DEC1", 0.0005f, 20.0f, 0.3f, PF_SECONDS | PF_LOG)        \
  X(Env1S, "SUS1", 0.0f, 1.0f, 0.7f, PF_NONE)                        \
  X(Env1R, "REL1", 0.0005f, 20.0f, 0.4f, PF_SECONDS | PF_LOG)        \
  X(Env1Curve, "CURVE1", -1.0f, 1.0f, -0.3f, PF_BIPOLAR)             \
  X(Env1Mode, "EMODE1", 0.0f, 3.0f, 0.0f, PF_DISCRETE)               \
  X(Env2A, "ATK2", 0.0005f, 20.0f, 0.01f, PF_SECONDS | PF_LOG)       \
  X(Env2D, "DEC2", 0.0005f, 20.0f, 0.4f, PF_SECONDS | PF_LOG)        \
  X(Env2S, "SUS2", 0.0f, 1.0f, 0.2f, PF_NONE)                        \
  X(Env2R, "REL2", 0.0005f, 20.0f, 0.3f, PF_SECONDS | PF_LOG)        \
  X(Env2Curve, "CURVE2", -1.0f, 1.0f, -0.2f, PF_BIPOLAR)             \
  X(Env2Mode, "EMODE2", 0.0f, 3.0f, 0.0f, PF_DISCRETE)               \
  X(Env3A, "ATK3", 0.0005f, 20.0f, 0.2f, PF_SECONDS | PF_LOG)        \
  X(Env3D, "DEC3", 0.0005f, 20.0f, 0.5f, PF_SECONDS | PF_LOG)        \
  X(Env3S, "SUS3", 0.0f, 1.0f, 0.5f, PF_NONE)                        \
  X(Env3R, "REL3", 0.0005f, 20.0f, 0.5f, PF_SECONDS | PF_LOG)        \
  X(Env3Curve, "CURVE3", -1.0f, 1.0f, 0.0f, PF_BIPOLAR)              \
  X(Env3Mode, "EMODE3", 0.0f, 3.0f, 0.0f, PF_DISCRETE)               \
  X(Env4A, "ATK4", 0.0005f, 20.0f, 0.2f, PF_SECONDS | PF_LOG)        \
  X(Env4D, "DEC4", 0.0005f, 20.0f, 0.5f, PF_SECONDS | PF_LOG)        \
  X(Env4S, "SUS4", 0.0f, 1.0f, 0.5f, PF_NONE)                        \
  X(Env4R, "REL4", 0.0005f, 20.0f, 0.5f, PF_SECONDS | PF_LOG)        \
  X(Env4Curve, "CURVE4", -1.0f, 1.0f, 0.0f, PF_BIPOLAR)              \
  X(Env4Mode, "EMODE4", 0.0f, 3.0f, 0.0f, PF_DISCRETE)              \
  X(Lfo1Rate, "LFO1", 0.02f, 2000.0f, 2.0f, PF_HZ | PF_LOG)          \
  X(Lfo1Shape, "LFO1SH", 0.0f, 7.0f, 0.0f, PF_DISCRETE)              \
  X(Lfo1Sync, "LFO1SYNC", 0.0f, 1.0f, 0.0f, PF_DISCRETE)             \
  X(Lfo1Retrig, "LFO1RT", 0.0f, 1.0f, 1.0f, PF_DISCRETE)             \
  X(Lfo1Keytrack, "LFO1KT", 0.0f, 1.0f, 0.0f, PF_NONE)               \
  X(Lfo1Fade, "LFO1FADE", 0.0f, 2.0f, 0.0f, PF_SECONDS)              \
  X(Lfo2Rate, "LFO2", 0.02f, 2000.0f, 0.3f, PF_HZ | PF_LOG)          \
  X(Lfo2Shape, "LFO2SH", 0.0f, 7.0f, 1.0f, PF_DISCRETE)              \
  X(Lfo2Sync, "LFO2SYNC", 0.0f, 1.0f, 0.0f, PF_DISCRETE)             \
  X(Lfo2Retrig, "LFO2RT", 0.0f, 1.0f, 0.0f, PF_DISCRETE)             \
  X(Lfo2Keytrack, "LFO2KT", 0.0f, 1.0f, 0.0f, PF_NONE)               \
  X(Lfo2Fade, "LFO2FADE", 0.0f, 2.0f, 0.0f, PF_SECONDS)              \
  X(Lfo3Rate, "LFO3", 0.02f, 2000.0f, 5.0f, PF_HZ | PF_LOG)          \
  X(Lfo3Shape, "LFO3SH", 0.0f, 7.0f, 2.0f, PF_DISCRETE)              \
  X(Lfo3Sync, "LFO3SYNC", 0.0f, 1.0f, 1.0f, PF_DISCRETE)             \
  X(Lfo3Retrig, "LFO3RT", 0.0f, 1.0f, 1.0f, PF_DISCRETE)             \
  X(Lfo3Keytrack, "LFO3KT", 0.0f, 1.0f, 0.0f, PF_NONE)               \
  X(Lfo3Fade, "LFO3FADE", 0.0f, 2.0f, 0.0f, PF_SECONDS)              \
  X(Lfo4Rate, "LFO4", 0.02f, 2000.0f, 0.7f, PF_HZ | PF_LOG)          \
  X(Lfo4Shape, "LFO4SH", 0.0f, 7.0f, 3.0f, PF_DISCRETE)              \
  X(Lfo4Sync, "LFO4SYNC", 0.0f, 1.0f, 0.0f, PF_DISCRETE)             \
  X(Lfo4Retrig, "LFO4RT", 0.0f, 1.0f, 0.0f, PF_DISCRETE)             \
  X(Lfo4Keytrack, "LFO4KT", 0.0f, 1.0f, 0.0f, PF_NONE)               \
  X(Lfo4Fade, "LFO4FADE", 0.0f, 2.0f, 0.0f, PF_SECONDS)              \
  X(CrushBits, "CRUSH", 1.0f, 16.0f, 16.0f, PF_DISCRETE)             \
  X(CrushMix, "CRUSHMIX", 0.0f, 1.0f, 0.0f, PF_NONE)                 \
  X(EnsembleAmount, "ENSEMBLE", 0.0f, 1.0f, 0.0f, PF_NONE)           \
  X(EnsembleRate, "ENS RATE", 0.05f, 8.0f, 0.5f, PF_HZ | PF_LOG)     \
  X(PartPan, "PAN", -1.0f, 1.0f, 0.0f, PF_BIPOLAR)                   \
  X(PartLevel, "LEVEL", 0.0f, 1.0f, 0.8f, PF_NONE)

// --- global parameters (24) -----------------------------------------------
#define BUKIFON_GLOBAL_PARAM_LIST(X)                                  \
  X(MasterVolume, "MASTER", 0.0f, 1.0f, 0.8f, PF_NONE)                \
  X(Bpm, "TEMPO", 40.0f, 300.0f, 120.0f, PF_NONE)                     \
  X(PolyMode, "VOICE MODE", 0.0f, 2.0f, 0.0f, PF_DISCRETE)            \
  X(Glide, "GLIDE", 0.0f, 2.0f, 0.0f, PF_SECONDS)                     \
  X(BendRange, "BEND RANGE", 0.0f, 48.0f, 2.0f, PF_SEMITONES)         \
  X(FxDelayTime, "DELAY TIME", 0.01f, 1.0f, 0.25f, PF_SECONDS)        \
  X(FxDelayFb, "DELAY FB", 0.0f, 0.95f, 0.35f, PF_NONE)               \
  X(FxDelayMix, "DELAY MIX", 0.0f, 1.0f, 0.25f, PF_NONE)              \
  X(FxChorusRate, "CHORUS RT", 0.05f, 8.0f, 0.4f, PF_HZ | PF_LOG)     \
  X(FxChorusDepth, "CHORUS DP", 0.0f, 1.0f, 0.4f, PF_NONE)            \
  X(FxChorusMix, "CHORUS MX", 0.0f, 1.0f, 0.2f, PF_NONE)              \
  X(FxDrive, "FX DRIVE", 0.0f, 1.0f, 0.1f, PF_NONE)                   \
  X(FxLimiterThreshold, "LIMITER", 0.3f, 1.0f, 0.95f, PF_NONE)        \
  X(FxLimiterRelease, "LIM REL", 0.01f, 1.0f, 0.2f, PF_SECONDS)       \
  X(SeqMode, "SEQ MODE", 0.0f, 4.0f, 0.0f, PF_DISCRETE)               \
  X(SeqLength, "SEQ LEN", 1.0f, 16.0f, 16.0f, PF_DISCRETE)            \
  X(SeqSwing, "SWING", 0.0f, 0.7f, 0.0f, PF_NONE)                     \
  X(SeqTranspose, "TRANSPOSE", -12.0f, 12.0f, 0.0f, PF_SEMITONES)     \
  X(ArpMode, "ARP MODE", 0.0f, 4.0f, 0.0f, PF_DISCRETE)               \
  X(ArpOctaves, "ARP OCT", 1.0f, 4.0f, 1.0f, PF_DISCRETE)             \
  X(Part1Voices, "PART1", 0.0f, 8.0f, 2.0f, PF_DISCRETE)              \
  X(Part2Voices, "PART2", 0.0f, 8.0f, 2.0f, PF_DISCRETE)              \
  X(Part3Voices, "PART3", 0.0f, 8.0f, 2.0f, PF_DISCRETE)              \
  X(Part4Voices, "PART4", 0.0f, 8.0f, 2.0f, PF_DISCRETE)              \
  X(Cv1Amount, "CV1 AMT", -1.0f, 1.0f, 0.0f, PF_BIPOLAR)              \
  X(Cv2Amount, "CV2 AMT", -1.0f, 1.0f, 0.0f, PF_BIPOLAR)              \
  X(Cv3Amount, "CV3 AMT", -1.0f, 1.0f, 0.0f, PF_BIPOLAR)              \
  X(Cv4Amount, "CV4 AMT", -1.0f, 1.0f, 0.0f, PF_BIPOLAR)              \
  X(Gate1Time, "GATE1", 0.001f, 2.0f, 0.05f, PF_SECONDS | PF_LOG)     \
  X(Gate2Time, "GATE2", 0.001f, 2.0f, 0.05f, PF_SECONDS | PF_LOG)     \
  X(Gate1Mode, "G1 MODE", 0.0f, 2.0f, 0.0f, PF_DISCRETE)              \
  X(Gate2Mode, "G2 MODE", 0.0f, 2.0f, 0.0f, PF_DISCRETE)

#define PM_ENUM(name, ...) name,
enum PartParam : uint8_t { BUKIFON_PART_PARAM_LIST(PM_ENUM) kNumPartParams };
enum GlobalParam : uint8_t { BUKIFON_GLOBAL_PARAM_LIST(PM_ENUM) kNumGlobalParams };
#undef PM_ENUM

extern const ParamMeta kPartParamMeta[kNumPartParams];
extern const ParamMeta kGlobalParamMeta[kNumGlobalParams];

struct PartParams {
  float v[kNumPartParams] = {};
  void reset();
  float get(int id) const { return v[id]; }
  void set(int id, float value);
};

struct GlobalParams {
  float v[kNumGlobalParams] = {};
  void reset();
  float get(int id) const { return v[id]; }
  void set(int id, float value);
};

// Value <-> 0..1 normalisation (respecting PF_LOG). Discrete params snap.
float paramToNorm(const ParamMeta& m, float value);
float paramFromNorm(const ParamMeta& m, float norm);
float clampPartParam(int id, float value);
float clampGlobalParam(int id, float value);

// Quantise a part parameter (discrete params round, others clamp).
float snapPartParam(int id, float value);
float snapGlobalParam(int id, float value);

}  // namespace bukifon
