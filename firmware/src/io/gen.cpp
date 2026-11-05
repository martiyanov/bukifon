// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/gen.hpp"

#include <algorithm>
#include <cstring>

namespace bukifon {
namespace {

const int kMinor[] = {0, 2, 3, 5, 7, 8, 10};
const int kMajor[] = {0, 2, 4, 5, 7, 9, 11};
const int kPenta[] = {0, 2, 4, 7, 9};
const int kDorian[] = {0, 2, 3, 5, 7, 9, 10};

const int* scaleIntervals(GenScale scale, int* count) {
  switch (scale) {
    case GenScale::Minor:
      *count = static_cast<int>(sizeof(kMinor) / sizeof(kMinor[0]));
      return kMinor;
    case GenScale::Major:
      *count = static_cast<int>(sizeof(kMajor) / sizeof(kMajor[0]));
      return kMajor;
    case GenScale::Penta:
      *count = static_cast<int>(sizeof(kPenta) / sizeof(kPenta[0]));
      return kPenta;
    case GenScale::Dorian:
      *count = static_cast<int>(sizeof(kDorian) / sizeof(kDorian[0]));
      return kDorian;
    default:
      *count = 0;
      return nullptr;
  }
}

}  // namespace

uint32_t genHash(uint32_t seed, int part, int step, uint32_t salt) {
  uint32_t h = 2166136261u ^ (seed * 16777619u);
  h ^= static_cast<uint32_t>(part) * 73856093u;
  h ^= static_cast<uint32_t>(step) * 19349663u;
  h ^= salt * 83492791u;
  h *= 16777619u;
  h ^= h >> 13;
  h *= 0x5bd1e995u;
  h ^= h >> 15;
  return h;
}

bool genProbability(uint32_t seed, int part, int step, uint8_t probability) {
  if (probability >= 100) return true;
  if (probability == 0) return false;
  return static_cast<int>(genHash(seed, part, step, 0x50524F42u) % 100u) < probability;
}

uint16_t genEuclidMask(uint8_t density, uint8_t steps) {
  if (steps == 0) return 0;
  uint16_t mask = 0;
  if (density >= steps) return static_cast<uint16_t>((1u << steps) - 1u);
  if (density == 0) return 0;
  // Euclidean/Bjorklund distribution via the bucket algorithm.
  int bucket = 0;
  for (uint8_t i = 0; i < steps; ++i) {
    bucket += density;
    if (bucket >= steps) {
      bucket -= steps;
      mask |= static_cast<uint16_t>(1u << i);
    }
  }
  return mask;
}

bool genEuclidGate(uint16_t mask, int step) {
  if (step < 0 || step > 15) return false;
  return (mask & (static_cast<uint16_t>(1u << step))) != 0;
}

bool genEuclidAccent(int step) { return step >= 0 && (step % 4) == 0; }

int genMutateOffset(uint32_t seed, int part, int step, uint8_t maxSemitones) {
  if (maxSemitones == 0) return 0;
  const uint32_t h = genHash(seed, part, step, 0x4D555441u);
  const uint32_t range = static_cast<uint32_t>(maxSemitones * 2 + 1);
  return static_cast<int>(h % range) - static_cast<int>(maxSemitones);
}

int genScaleLockNote(int note, GenScale scale) {
  if (scale == GenScale::Off) return note;
  int count = 0;
  const int* intervals = scaleIntervals(scale, &count);
  if (!intervals || count == 0) return note;
  const int pitchClass = ((note % 12) + 12) % 12;
  int bestDelta = 0;
  int bestDistance = 100;
  for (int i = 0; i < count; ++i) {
    int delta = intervals[i] - pitchClass;
    if (delta > 6) delta -= 12;
    if (delta < -6) delta += 12;
    const int distance = delta < 0 ? -delta : delta;
    // Prefer the lower note on a tie (deterministic, documented).
    if (distance < bestDistance || (distance == bestDistance && delta < bestDelta)) {
      bestDistance = distance;
      bestDelta = delta;
    }
  }
  int result = note + bestDelta;
  if (result < 0) result = 0;
  if (result > 127) result = 127;
  return result;
}

const char* genScaleName(GenScale scale) {
  switch (scale) {
    case GenScale::Minor: return "MINOR";
    case GenScale::Major: return "MAJOR";
    case GenScale::Penta: return "PENTA";
    case GenScale::Dorian: return "DORIAN";
    default: return "OFF";
  }
}

int genEvolveNote(uint32_t seed, int part, int bar, int step, int note, uint8_t range) {
  const int offset = genMutateOffset(seed ^ (static_cast<uint32_t>(bar) * 2654435761u), part, step,
                                     range);
  int result = note + offset;
  if (result < 0) result = 0;
  if (result > 127) result = 127;
  return result;
}

GenStepResult genApplyStep(const GenParams& params, int part, int step, int baseNote,
                           int baseVelocity) {
  GenStepResult result;
  result.note = baseNote;
  result.velocity = baseVelocity;
  if (params.euclid > 0) {
    const uint16_t mask = genEuclidMask(params.euclid, 16);
    if (!genEuclidGate(mask, step)) {
      result.trigger = false;
      return result;
    }
    result.accent = genEuclidAccent(step);
  }
  if (!genProbability(params.seed, part, step, params.probability)) {
    result.trigger = false;
    return result;
  }
  if (params.mutate > 0) {
    result.note += genMutateOffset(params.seed, part, step, params.mutate);
  }
  if (params.scale != GenScale::Off) {
    result.note = genScaleLockNote(result.note, params.scale);
  }
  if (result.note < 0) result.note = 0;
  if (result.note > 127) result.note = 127;
  if (result.accent) {
    result.velocity += 24;
    if (result.velocity > 127) result.velocity = 127;
  }
  return result;
}

int GenArp::periodTicks32(uint8_t rate) {
  switch (rate) {
    case GenArpRate8: return 4;
    case GenArpRate16: return 2;
    case GenArpRate32: return 1;
    default: return 2;
  }
}

int GenArp::noteAt(const uint8_t* heldNotes, int count, uint32_t tick32) const {
  if (!heldNotes || count <= 0) return -1;
  uint8_t sorted[16];
  const int n = count < 16 ? count : 16;
  std::memcpy(sorted, heldNotes, static_cast<size_t>(n));
  std::sort(sorted, sorted + n);
  const uint32_t index = tick32 / static_cast<uint32_t>(periodTicks32(rate_));
  switch (mode_) {
    case GenArpDown:
      return sorted[n - 1 - static_cast<int>(index % static_cast<uint32_t>(n))];
    case GenArpUpDown: {
      if (n == 1) return sorted[0];
      const int cycle = 2 * n - 2;
      int pos = static_cast<int>(index % static_cast<uint32_t>(cycle));
      if (pos >= n) pos = cycle - pos;
      return sorted[pos];
    }
    case GenArpUp:
    default:
      return sorted[index % static_cast<uint32_t>(n)];
  }
}

const char* GenArp::rateName() const { return genArpRateName(rate_); }
const char* GenArp::modeName() const { return genArpModeName(mode_); }

const char* genArpRateName(uint8_t rate) {
  switch (rate) {
    case GenArpRate8: return "1/8";
    case GenArpRate32: return "1/32";
    default: return "1/16";
  }
}

const char* genArpModeName(uint8_t mode) {
  switch (mode) {
    case GenArpDown: return "DOWN";
    case GenArpUpDown: return "UPDOWN";
    default: return "UP";
  }
}

}  // namespace bukifon
