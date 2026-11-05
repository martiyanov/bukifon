// SPDX-License-Identifier: GPL-3.0-or-later
// Band-limited wavetable lookup with 8 mip levels and 4-point interpolation.
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "dsp/wavetable_data.hpp"

namespace bukifon {

class WavetableBank {
 public:
  // Highest harmonic present in a mip level (level 0 = 1023 harmonics).
  static constexpr int mipMaxHarmonic(int mip) { return (kTableSize / 2 - 1) >> mip; }

  // Pick the lowest mip level whose highest harmonic stays below Nyquist.
  static int mipForFrequency(float hz, float sampleRate = static_cast<float>(kSampleRate));

  // phase is 0..2^32 wrap, cubic (Catmull-Rom) interpolation, returns -1..+1.
  static float samplePhase(int wave, int mip, uint32_t phase);
  static float sampleNormalized(int wave, int mip, float phase01);
};

}  // namespace bukifon
