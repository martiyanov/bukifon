// SPDX-License-Identifier: GPL-3.0-or-later
// Cyrillic bitmap font coverage, UTF-8 lookup, width metrics, RU rendering.
#include <cstdint>
#include <cstring>
#include <string>

#include "bukifon_i18n.h"
#include "test_framework.hpp"
#include "ui/font_cyrillic6x8.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

int nonBlack(const ui::Framebuffer800& fb) {
  int count = 0;
  for (int y = 0; y < fb.height(); y += 3) {
    for (int x = 0; x < fb.width(); x += 3) count += fb.at(x, y) != 0 ? 1 : 0;
  }
  return count;
}

uint64_t checksum(const ui::Framebuffer800& fb) {
  uint64_t hash = 1469598103934665603ull;
  for (int y = 0; y < fb.height(); y += 5) {
    for (int x = 0; x < fb.width(); x += 5) {
      hash ^= fb.at(x, y);
      hash *= 1099511628211ull;
    }
  }
  return hash;
}

bool glyphHasPixels(const uint8_t glyph[8]) {
  for (int row = 0; row < 8; ++row) {
    if (glyph[row] != 0) return true;
  }
  return false;
}

}  // namespace

TEST(FontCyrillicUppercaseCoverage) {
  for (uint32_t cp = 0x0410; cp <= 0x042F; ++cp) {
    const uint8_t* glyph = uiFontGlyph(cp);
    CHECK(glyph != nullptr);
    if (glyph) CHECK(glyphHasPixels(glyph));
  }
  INFO("font: А..Я (32 uppercase Cyrillic glyphs) present and non-empty");
}

TEST(FontCyrillicLowercaseCoverage) {
  for (uint32_t cp = 0x0430; cp <= 0x044F; ++cp) {
    const uint8_t* glyph = uiFontGlyph(cp);
    CHECK(glyph != nullptr);
    if (glyph) CHECK(glyphHasPixels(glyph));
  }
  INFO("font: а..я (32 lowercase Cyrillic glyphs) present and non-empty");
}

TEST(FontCyrillicYoGlyphs) {
  const uint8_t* upper = uiFontGlyph(0x0401);
  const uint8_t* lower = uiFontGlyph(0x0451);
  CHECK(upper != nullptr && lower != nullptr);
  if (upper) CHECK(glyphHasPixels(upper));
  if (lower) CHECK(glyphHasPixels(lower));
  CHECK(uiFontHasGlyph(0x0401));
  CHECK(uiFontHasGlyph(0x0451));
  INFO("font: Ё/ё glyphs present (uppercase/lowercase)");
}

TEST(FontCyrillicBitmapTable) {
  CHECK(kCyrillicGlyphCount == 66);
  int nonEmpty = 0;
  for (int i = 0; i < kCyrillicGlyphCount; ++i) {
    if (glyphHasPixels(kCyrillic6x8[i])) ++nonEmpty;
  }
  CHECK(nonEmpty == 66);
  INFO("font: 66 Cyrillic glyph records, all with pixels");
}

TEST(FontUtf8CodepointsMetric) {
  CHECK(uiUtf8Codepoints("ABC") == 3);
  CHECK(uiUtf8Codepoints("ПРИВЕТ") == 6);
  CHECK(uiUtf8Codepoints("МИК ✅") == 5);  // emoji counts as one codepoint
  CHECK(uiUtf8Codepoints("") == 0);
  INFO("font: UTF-8 codepoint counting for width metrics");
}

TEST(FontAllRuKeysGlyphCoverage) {
  setLanguage(Lang::Ru);
  for (int i = 0; i < kUiKeyCount; ++i) {
    const char* text = tr(static_cast<UiKey>(i));
    CHECK(text != nullptr);
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(text); *p;) {
      uint32_t cp = *p;
      if (cp < 0x80) {
        ++p;
      } else if ((cp & 0xE0) == 0xC0 && p[1]) {
        cp = ((cp & 0x1F) << 6) | (p[1] & 0x3F);
        p += 2;
      } else if ((cp & 0xF0) == 0xE0 && p[1] && p[2]) {
        cp = ((cp & 0x0F) << 12) | ((p[1] & 0x3F) << 6) | (p[2] & 0x3F);
        p += 3;
      } else {
        cp = '?';
        ++p;
      }
      if (cp == ' ' || cp == '\n' || cp == '-') continue;
      CHECK(uiFontHasGlyph(cp));
    }
  }
  setLanguage(Lang::En);
  INFO("font: every RU key uses only glyphs present in the Cyrillic table");
}

TEST(FontAllTranslationsFitCellWidth) {
  for (int i = 0; i < kUiKeyCount; ++i) {
    for (Lang language : {Lang::Ru, Lang::En}) {
      const int width = ui::uiTextPixelWidth(tr(static_cast<UiKey>(i), language),
                                             ui::UiTextRole::Caption);
      CHECK(width <= 94);  // kParamCellW - 2
    }
  }
  INFO("font: every RU/EN string fits the 94 px caption cell");
}

TEST(FontRuEnFramesDiffer) {
  setLanguage(Lang::En);
  ui::UiSnapshot en;
  ui::uiSnapshotDemo(&en, ui::Screen::Main);
  ui::Framebuffer800 enFb;
  ui::drawUi800(enFb, en);
  setLanguage(Lang::Ru);
  ui::UiSnapshot ru;
  ui::uiSnapshotDemo(&ru, ui::Screen::Main);
  ui::Framebuffer800 ruFb;
  ui::drawUi800(ruFb, ru);
  CHECK(nonBlack(enFb) > 2000);
  CHECK(nonBlack(ruFb) > 2000);
  CHECK(checksum(enFb) != checksum(ruFb));
  setLanguage(Lang::En);
  INFO("font: RU and EN frames are pixel-different");
}

TEST(FontRuSnapshotLabels) {
  setLanguage(Lang::Ru);
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  CHECK(std::strcmp(snapshot.params[0].label, "СРЕЗ") == 0);
  CHECK(std::strcmp(snapshot.macros[0].label, "СРЕЗ") == 0);
  CHECK(uiUtf8Codepoints(snapshot.params[1].label) > 0);
  setLanguage(Lang::En);
  INFO("font: RU snapshot labels are real Cyrillic UTF-8 strings");
}

TEST(FontCyrillicRendersNotFallback) {
  ui::Framebuffer800 cyrillic;
  ui::Framebuffer800 question;
  bukifon::ICanvas& a = cyrillic;
  bukifon::ICanvas& b = question;
  ui::drawTextRole(a, 20, 20, "Ж", 0xFFFF, ui::UiTextRole::Value);
  ui::drawTextRole(b, 20, 20, "?", 0xFFFF, ui::UiTextRole::Value);
  CHECK(nonBlack(cyrillic) > 0);
  CHECK(checksum(cyrillic) != checksum(question));
  INFO("font: Cyrillic glyph is rendered, not the '?' fallback");
}

TEST(FontSevenPagesRuSmoke) {
  setLanguage(Lang::Ru);
  const ui::Screen screens[7] = {ui::Screen::Main, ui::Screen::Sequencer, ui::Screen::Mixer,
                                 ui::Screen::Modules, ui::Screen::Gen, ui::Screen::Ext,
                                 ui::Screen::Mic};
  for (ui::Screen screen : screens) {
    ui::UiSnapshot snapshot;
    ui::uiSnapshotDemo(&snapshot, screen);
    ui::Framebuffer800 fb;
    ui::drawUi800(fb, snapshot);
    CHECK(nonBlack(fb) > 1500);
  }
  setLanguage(Lang::En);
  INFO("font: all 7 pages render in RU without missing-glyph crashes");
}

TEST(FontSevenPagesEnSmoke) {
  setLanguage(Lang::En);
  const ui::Screen screens[7] = {ui::Screen::Main, ui::Screen::Sequencer, ui::Screen::Mixer,
                                 ui::Screen::Modules, ui::Screen::Gen, ui::Screen::Ext,
                                 ui::Screen::Mic};
  for (ui::Screen screen : screens) {
    ui::UiSnapshot snapshot;
    ui::uiSnapshotDemo(&snapshot, screen);
    ui::Framebuffer800 fb;
    ui::drawUi800(fb, snapshot);
    CHECK(nonBlack(fb) > 1500);
  }
  INFO("font: all 7 pages render in EN (ASCII path)");
}

TEST(FontGlyphLookupFallbackAndAscii) {
  CHECK(uiFontGlyph('A') != nullptr);
  CHECK(uiFontGlyph('0') != nullptr);
  CHECK(uiFontGlyph(' ') != nullptr);
  CHECK(uiFontGlyph(0x0410) != nullptr);
  CHECK(uiFontGlyph(0x044F) != nullptr);
  CHECK(uiFontGlyph(0x1F600) == nullptr);  // emoji: no glyph, caller uses '?'
  CHECK(uiFontHasGlyph('-'));
  INFO("font: ASCII/Cyrillic lookup; unsupported codepoint returns nullptr");
}

TEST(FontWidthMetricsCompare) {
  CHECK(ui::uiTextPixelWidth("AB", ui::UiTextRole::Caption) ==
        2 * ui::uiTextWidth(ui::UiTextRole::Caption));
  CHECK(ui::uiTextPixelWidth("АБ", ui::UiTextRole::Caption) ==
        2 * ui::uiTextWidth(ui::UiTextRole::Caption));
  CHECK(ui::uiTextPixelWidth("", ui::UiTextRole::Caption) == 0);
  INFO("font: width metric counts UTF-8 codepoints (ASCII and Cyrillic equal)");
}
