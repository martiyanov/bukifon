#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generates src/ui/font6x8.hpp (6x8 bitmap font) from a system monospace font.

The firmware needs a tiny text font for the 320x240 ST7789 UI; this script
rasterises ASCII 32..127 once (offline) and writes the table into the source.
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 6, 8
FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
]

def pick_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

out = []
for code in range(32, 128):
    ch = chr(code)
    img = Image.new("1", (W, H), 0)
    draw = ImageDraw.Draw(img)
    font = pick_font(8)
    bbox = draw.textbbox((0, 0), ch, font=font)
    text_h = bbox[3] - bbox[1]
    y = max(0, (H - text_h) // 2 - bbox[1])
    draw.text((0, y), ch, font=font, fill=1)
    rows = []
    for row in range(H):
        bits = 0
        for col in range(W):
            if img.getpixel((col, row)):
                bits |= (1 << col)
        rows.append(bits)
    out.append(rows)

# Ensure the space glyph is blank and pad to 8 rows/6 columns as-is.
hpp = ["// SPDX-License-Identifier: GPL-3.0-or-later",
       "// GENERATED FILE — do not edit. Generator: firmware/tools/gen_font.py",
       "#pragma once", "", "#include <cstdint>", "",
       "namespace bukifon {",
       "constexpr int kFontWidth = 6;",
       "constexpr int kFontHeight = 8;",
       "// ASCII 32..127, 8 rows per glyph, bit 0 = leftmost pixel.",
       "extern const uint8_t kFont6x8[96][8];",
       "}  // namespace bukifon", ""]
text = "\n".join(hpp)
with open("src/ui/font6x8.hpp", "w") as f:
    f.write(text)

cpp = ["// SPDX-License-Identifier: GPL-3.0-or-later",
       "// GENERATED FILE — do not edit. Generator: firmware/tools/gen_font.py",
       '#include "ui/font6x8.hpp"', "", "namespace bukifon {", "",
       "const uint8_t kFont6x8[96][8] = {"]
for code, rows in zip(range(32, 128), out):
    label = chr(code) if 32 <= code < 127 else "DEL"
    cpp.append(f"    {{{', '.join(str(r) for r in rows)}}},  // {code} '{label}'")
cpp += ["};", "", "}  // namespace bukifon", ""]
with open("src/ui/font6x8.cpp", "w") as f:
    f.write("\n".join(cpp))
print("generated src/ui/font6x8.hpp/.cpp (96 glyphs, 6x8)")
