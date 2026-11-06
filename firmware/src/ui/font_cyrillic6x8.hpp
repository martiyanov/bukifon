// SPDX-License-Identifier: GPL-3.0-or-later
// Cyrillic glyphs for the UI bitmap font (6x8), generated from Arial Narrow 7px.
// Order: U+0410..U+042F (А..Я), U+0430..U+044F (а..я), U+0401 (Ё), U+0451 (ё).
#pragma once

#include <cstdint>

namespace bukifon {
constexpr int kCyrillicGlyphCount = 66;
extern const uint8_t kCyrillic6x8[kCyrillicGlyphCount][8];

// UTF-8 -> glyph (ASCII 32..127 and Cyrillic); nullptr if the codepoint has no
// glyph in the bitmap font.
const uint8_t* uiFontGlyph(uint32_t codepoint);
bool uiFontHasGlyph(uint32_t codepoint);
// UTF-8 codepoint count (for width metrics/tests; invalid bytes count as '?').
int uiUtf8Codepoints(const char* text);
}  // namespace bukifon
