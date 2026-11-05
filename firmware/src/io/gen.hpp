// SPDX-License-Identifier: GPL-3.0-or-later
// Generative sequencer functions (docs/65 UX pattern "GEN").
//
// Per-part deterministic generation: probability, Euclidean gate/accent,
// mutation, scale lock, evolve and a simple arpeggiator.  Everything is a pure
// function of (seed, part, step/bar), so the same seed always produces the same
// sequence and the host demo, firmware and tests agree.
#pragma once

#include <cstdint>

namespace bukifon {

enum class GenScale : uint8_t {
  Off = 0,
  Minor,
  Major,
  Penta,
  Dorian,
  kNumScales
};

enum GenArpRate : uint8_t { GenArpRate8 = 0, GenArpRate16 = 1, GenArpRate32 = 2, kNumGenArpRates };
enum GenArpMode : uint8_t { GenArpUp = 0, GenArpDown = 1, GenArpUpDown = 2, kNumGenArpModes };

struct GenParams {
  uint8_t probability = 100;  // 0..100 %
  uint8_t euclid = 0;         // 0..16 pulses out of 16 steps (0 = off)
  uint8_t mutate = 0;         // 0..12 semitones (two-sided hash offset)
  GenScale scale = GenScale::Off;
  bool evolve = false;        // mutate the pattern at each bar boundary
  uint8_t arpRate = GenArpRate16;
  uint8_t arpMode = GenArpUp;
  bool arpOn = false;
  uint32_t seed = 1;          // per-part deterministic seed
};

// FNV-1a mix of seed/part/step/salt; stable across hosts and MCU.
uint32_t genHash(uint32_t seed, int part, int step, uint32_t salt = 0);

// Probability 0..100 (100 always, 0 never).
bool genProbability(uint32_t seed, int part, int step, uint8_t probability);

// Euclidean mask (bit i = trigger on step i) and accents on 1/5/9/13 (i%4==0).
// 0 = no gates, 16 = all gates.  Distribution is the standard Euclidean rhythm.
uint16_t genEuclidMask(uint8_t density, uint8_t steps = 16);
bool genEuclidGate(uint16_t mask, int step);
bool genEuclidAccent(int step);  // accents on 1/5/9/13 (step 0,4,8,12)

// Deterministic two-sided semitone offset in [-max..+max].
int genMutateOffset(uint32_t seed, int part, int step, uint8_t maxSemitones);

// Nearest note in the scale (pitch classes); Off returns the note unchanged.
int genScaleLockNote(int note, GenScale scale);
const char* genScaleName(GenScale scale);

// Evolve: deterministic new note at a bar boundary (used to mutate the pattern).
int genEvolveNote(uint32_t seed, int part, int bar, int step, int note, uint8_t range = 2);

// One-step application (probability + euclid + mutate + scale lock + accent).
struct GenStepResult {
  bool trigger = true;
  bool accent = false;
  int note = 60;
  int velocity = 100;
};

GenStepResult genApplyStep(const GenParams& params, int part, int step, int baseNote,
                           int baseVelocity);

// Simple arpeggiator over held notes; tick is in 1/32-note units.
class GenArp {
 public:
  void setParams(uint8_t rate, uint8_t mode) {
    rate_ = rate;
    mode_ = mode;
  }
  uint8_t rate() const { return rate_; }
  uint8_t mode() const { return mode_; }
  static int periodTicks32(uint8_t rate);  // 1/8=4, 1/16=2, 1/32=1
  int noteAt(const uint8_t* heldNotes, int count, uint32_t tick32) const;
  const char* rateName() const;
  const char* modeName() const;

 private:
  uint8_t rate_ = GenArpRate16;
  uint8_t mode_ = GenArpUp;
};

const char* genArpRateName(uint8_t rate);
const char* genArpModeName(uint8_t mode);

}  // namespace bukifon
