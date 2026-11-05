// SPDX-License-Identifier: GPL-3.0-or-later
// GENERATED FILE — do not edit. Generator: firmware/tools/gen_wavetables.cpp
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

constexpr int kWaveCount = 8;
// Waveform names for the UI (index == table index).
extern const char* const kWaveNames[kWaveCount];
// Data[w][mip][sample], int16 full scale ~32767.
extern const int16_t kWavetableData[kWaveCount][kMipLevels][kTableSize];

}  // namespace bukifon
