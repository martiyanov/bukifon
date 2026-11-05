// SPDX-License-Identifier: GPL-3.0-or-later
// GENERATED FILE — do not edit. Generator: firmware/tools/gen_font.py
#pragma once

#include <cstdint>

namespace bukifon {
constexpr int kFontWidth = 6;
constexpr int kFontHeight = 8;
// ASCII 32..127, 8 rows per glyph, bit 0 = leftmost pixel.
extern const uint8_t kFont6x8[96][8];
}  // namespace bukifon
