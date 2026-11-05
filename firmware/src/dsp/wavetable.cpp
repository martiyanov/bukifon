// SPDX-License-Identifier: GPL-3.0-or-later
#include "dsp/wavetable.hpp"

#include "core/math.hpp"

namespace bukifon {
namespace {
constexpr float kInvInt16 = 1.0f / 32768.0f;
}  // namespace

int WavetableBank::mipForFrequency(float hz, float sampleRate) {
  if (hz <= 0.0f) return kMipLevels - 1;
  const float maxHarm = 0.95f * 0.5f * sampleRate / hz;
  int level = 0;
  while (level < kMipLevels - 1 && static_cast<float>(mipMaxHarmonic(level)) > maxHarm) ++level;
  return level;
}

float WavetableBank::samplePhase(int wave, int mip, uint32_t phase) {
  const int16_t* table = kWavetableData[wave & (kWaveCount - 1)][mip & (kMipLevels - 1)];
  const uint32_t idx = phase >> 21;                  // 0..2047
  const float frac = static_cast<float>(phase & 0x1FFFFFu) * (1.0f / 2097152.0f);
  const int i0 = static_cast<int>((idx + kTableSize - 1) & (kTableSize - 1));
  const int i1 = static_cast<int>(idx);
  const int i2 = static_cast<int>((idx + 1) & (kTableSize - 1));
  const int i3 = static_cast<int>((idx + 2) & (kTableSize - 1));
  const float y0 = table[i0] * kInvInt16;
  const float y1 = table[i1] * kInvInt16;
  const float y2 = table[i2] * kInvInt16;
  const float y3 = table[i3] * kInvInt16;
  // Catmull-Rom cubic interpolation (much lower alias/imaging than linear).
  const float a = -0.5f * y0 + 1.5f * y1 - 1.5f * y2 + 0.5f * y3;
  const float b = y0 - 2.5f * y1 + 2.0f * y2 - 0.5f * y3;
  const float c = -0.5f * y0 + 0.5f * y2;
  return ((a * frac + b) * frac + c) * frac + y1;
}

float WavetableBank::sampleNormalized(int wave, int mip, float phase01) {
  phase01 -= std::floor(phase01);
  return samplePhase(wave, mip, static_cast<uint32_t>(phase01 * 4294967296.0f));
}

}  // namespace bukifon
