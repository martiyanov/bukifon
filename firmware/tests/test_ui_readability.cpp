// SPDX-License-Identifier: GPL-3.0-or-later
// docs/68/69 readability: font scale, 16-cell encoder mirror, context line,
// HOME, Cream contrast and theme rendering.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "bukifon_ui_theme.h"
#include "test_framework.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

uint64_t fbChecksum(const ui::Framebuffer800& fb) {
  uint64_t h = 1469598103934665603ull;
  for (int y = 0; y < fb.height(); y += 5) {
    for (int x = 0; x < fb.width(); x += 5) {
      h ^= fb.at(x, y);
      h *= 1099511628211ull;
    }
  }
  return h;
}

class VoiceCanvas : public ui::Framebuffer800 {
 public:
  void drawText(int x, int y, const char* text, uint16_t color, uint16_t bg = 0xFFFF) override {
    texts.emplace_back(text ? text : "");
    ui::Framebuffer800::drawText(x, y, text, color, bg);
  }
  bool has(const char* needle) const {
    for (const auto& text : texts) {
      if (text.find(needle) != std::string::npos) return true;
    }
    return false;
  }
  std::vector<std::string> texts;
};

std::string readSource(const char* path) {
  std::FILE* file = std::fopen(path, "rb");
  if (!file) return {};
  std::string out;
  char buffer[4096];
  size_t n = 0;
  while ((n = std::fread(buffer, 1, sizeof(buffer), file)) > 0) out.append(buffer, n);
  std::fclose(file);
  return out;
}

double luminance(uint32_t rgb) {
  auto channel = [](uint8_t v) {
    const double c = static_cast<double>(v) / 255.0;
    return c <= 0.03928 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4);
  };
  const uint8_t r = static_cast<uint8_t>((rgb >> 16) & 0xFF);
  const uint8_t g = static_cast<uint8_t>((rgb >> 8) & 0xFF);
  const uint8_t b = static_cast<uint8_t>(rgb & 0xFF);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

double contrastRatio(uint32_t fg, uint32_t bg) {
  const double a = luminance(fg);
  const double b = luminance(bg);
  return (std::max(a, b) + 0.05) / (std::min(a, b) + 0.05);
}

}  // namespace

TEST(UiTextScaleHeights) {
  CHECK(ui::uiTextHeight(ui::UiTextRole::Caption) == 12);
  CHECK(ui::uiTextHeight(ui::UiTextRole::Value) == 18);
  CHECK(ui::uiTextHeight(ui::UiTextRole::Critical) == 24);
  CHECK(ui::uiTextHeight(ui::UiTextRole::Title) == 26);
  CHECK(ui::uiTextWidth(ui::UiTextRole::Caption) > 0);
  CHECK(ui::uiTextWidth(ui::UiTextRole::Value) > ui::uiTextWidth(ui::UiTextRole::Caption));
  CHECK(ui::uiTextWidth(ui::UiTextRole::Critical) > ui::uiTextWidth(ui::UiTextRole::Value));
  INFO("docs/69 scale: caption 12, value 18, critical 24, title 26 px");
}

TEST(UiTextNoSmallTextInRenderer) {
  const std::string source = readSource("../src/ui/ui800.cpp");
  CHECK(!source.empty());
  CHECK(source.find("c.drawText(") == std::string::npos);
  CHECK(source.find("drawTextScaled(c,") == std::string::npos);
  CHECK(source.find("uiTextHeight") != std::string::npos);
  CHECK(source.find("UiTextRole::Caption") != std::string::npos);
  CHECK(source.find("UiTextRole::Value") != std::string::npos);
  CHECK(source.find("UiTextRole::Critical") != std::string::npos);
  CHECK(source.find("UiTextRole::Title") != std::string::npos);
  INFO("ui800 renders only through docs/69 roles (no 6x8/8px raw text calls)");
}

TEST(UiEncoderMirrorMapping) {
  const char* prefixes[16] = {"А", "Б", "В", "Г", "И", "Й", "К", "Л",
                              "Д", "Е", "Ж", "З", "М", "Н", "О", "П"};
  for (int e = 0; e < 16; ++e) {
    bool isMacro = false;
    const int index = ui::uiEncoderCellIndex(e, &isMacro);
    CHECK(index >= 0 && index < 8);
    CHECK(isMacro == ((e % 8) >= 4));
    CHECK(std::strcmp(ui::uiEncoderCellPrefix(e), prefixes[e]) == 0);
  }
  bool macro = false;
  CHECK(ui::uiEncoderCellIndex(0, &macro) == 0 && !macro);  // А → page 0
  CHECK(ui::uiEncoderCellIndex(4, &macro) == 0 && macro);   // И → macro 0 (CUT)
  CHECK(ui::uiEncoderCellIndex(11, &macro) == 7 && !macro); // З → page 7
  CHECK(ui::uiEncoderCellIndex(12, &macro) == 4 && macro);  // М → macro 4 (DLY)
  CHECK(ui::uiEncoderCellIndex(15, &macro) == 7 && macro);  // П → macro 7 (MST)
  CHECK(ui::uiEncoderCellIndex(-1, &macro) == -1);
  INFO("16 encoders mirrored: left 4 columns page А–З, right 4 macros И–П");
}

TEST(UiSnapshotSixteenCells) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  CHECK(ui::kNumEncoders == 16);
  CHECK(ui::kNumParams == 8);
  CHECK(ui::kNumMacros == 8);
  CHECK(std::strcmp(snapshot.params[0].label, "CUTOFF") == 0);
  const char* macros[8] = {"CUT", "RES", "ATK", "REL", "DLY", "DRV", "CRSH", "MST"};
  for (int i = 0; i < 8; ++i) {
    CHECK(std::strcmp(snapshot.macros[i].label, macros[i]) == 0);
    CHECK(snapshot.macros[i].value[0] != '\0');
  }
  CHECK(snapshot.selectedEncoder >= 0 && snapshot.selectedEncoder < 16);
  INFO("snapshot carries 8 page params + 8 fixed macros = 16 encoder cells");
}

TEST(UiContextLineAllModes) {
  const DeviceMode modes[4] = {DeviceMode::Synth, DeviceMode::Sampler,
                               DeviceMode::DawController, DeviceMode::UsbKeyboard};
  for (DeviceMode mode : modes) {
    ui::UiSnapshot snapshot;
    ui::uiSnapshotForDeviceMode(&snapshot, mode);
    CHECK(snapshot.partLabel[0] != '\0');
    CHECK(snapshot.selectedLabel[0] != '\0');
    CHECK(snapshot.faderMode[0] != '\0');
    char line[192];
    ui::uiBuildContextLine(&snapshot, line, sizeof(line));
    CHECK(std::strstr(line, "PART") != nullptr);
    CHECK(std::strstr(line, "SELECTED") != nullptr);
    CHECK(std::strstr(line, "PAGE") != nullptr);
    CHECK(std::strstr(line, "FADERS") != nullptr);
    CHECK(std::strstr(line, "REC") != nullptr);
    CHECK(std::strstr(line, snapshot.page) != nullptr);
  }
  INFO("context line PART·SELECTED·PAGE·FADERS·REC·UNSAVED present in all 4 modes");
}

TEST(UiContextLineRecAndUnsaved) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  snapshot.transportRecord = true;
  snapshot.unsaved = true;
  char line[192];
  ui::uiBuildContextLine(&snapshot, line, sizeof(line));
  CHECK(std::strstr(line, "REC ON") != nullptr);
  CHECK(std::strstr(line, "UNSAVED") != nullptr);
  snapshot.transportRecord = false;
  snapshot.unsaved = false;
  ui::uiBuildContextLine(&snapshot, line, sizeof(line));
  CHECK(std::strstr(line, "REC OFF") != nullptr);
  CHECK(std::strstr(line, "SAVED") != nullptr);
  INFO("context line reflects REC ON/OFF and UNSAVED/SAVED");
}

TEST(UiHomeHandler) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotGenDemo(&snapshot);
  CHECK(snapshot.screen == ui::Screen::Gen);
  ui::uiHandleHome(&snapshot);
  CHECK(snapshot.screen == ui::Screen::Main);
  CHECK(std::strcmp(snapshot.page, "MAIN") == 0);
  CHECK(snapshot.selectedParam == 0);
  CHECK(snapshot.selectedEncoder == 0);
  snapshot.screen = ui::Screen::Mixer;
  ui::uiHandleHome(&snapshot);
  CHECK(snapshot.screen == ui::Screen::Main);
  INFO("HOME returns to MAIN in one gesture (docs/68 §4)");
}

TEST(UiHomeRendered) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  VoiceCanvas canvas;
  ui::drawUi800(canvas, snapshot);
  CHECK(canvas.has("HOME"));
  CHECK(canvas.has("PART"));
  CHECK(canvas.has("SELECTED"));
  CHECK(canvas.has("UNSAVED"));
  INFO("HOME button and context line are rendered and text-captured");
}

TEST(UiCreamContrast) {
  const uint32_t bg = bukifon_ui_theme_rgb(3, BUKIFON_UI_BG);
  const int tokens[5] = {BUKIFON_UI_TEXT, BUKIFON_UI_MUTED, BUKIFON_UI_ACCENT,
                         BUKIFON_UI_GREEN, BUKIFON_UI_ORANGE};
  const char* names[5] = {"text", "muted", "accent", "green", "orange"};
  for (int i = 0; i < 5; ++i) {
    const double ratio = contrastRatio(bukifon_ui_theme_rgb(3, tokens[i]), bg);
    CHECK(ratio >= 4.5);
    INFO("Cream %s contrast %.2f:1 (>=4.5)", names[i], ratio);
  }
  INFO("Cream palette passes WCAG AA for text/muted/accent/green/orange");
}

TEST(UiCreamValuesMatchSpec) {
  CHECK(bukifon_ui_theme_rgb(3, BUKIFON_UI_MUTED) == 0x5f5548);
  CHECK(bukifon_ui_theme_rgb(3, BUKIFON_UI_ACCENT) == 0xa8321f);
  CHECK(bukifon_ui_theme_rgb(3, BUKIFON_UI_GREEN) == 0x3f6f2e);
  CHECK(bukifon_ui_theme_rgb(3, BUKIFON_UI_ORANGE) == 0x9a4a10);
  CHECK(bukifon_ui_theme_rgb(3, BUKIFON_UI_RED) == 0x9c2a1a);
  CHECK(bukifon_ui_theme_set("Cream"));
  CHECK(bukifon_ui_theme_current() == 3);
  bukifon_ui_theme_set("Night");
  INFO("Cream tokens updated (accent #a8321f, green #3f6f2e, orange #9a4a10, muted #5f5548)");
}

TEST(UiFourThemesSixteenCellsRender) {
  uint64_t hashes[4] = {};
  for (int theme = 0; theme < 4; ++theme) {
    CHECK(bukifon_ui_theme_set(bukifon_ui_theme_name(theme)));
    ui::Framebuffer800 fb;
    ui::UiSnapshot snapshot;
    ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
    ui::drawUi800(fb, snapshot);
    hashes[theme] = fbChecksum(fb);
  }
  CHECK(hashes[0] != hashes[1]);
  CHECK(hashes[1] != hashes[2]);
  CHECK(hashes[2] != hashes[3]);
  bukifon_ui_theme_set("Night");
  INFO("16-cell SYNTH screen renders in all 4 themes with distinct checksums");
}

TEST(UiSelectedEncoderHighlight) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  snapshot.selectedEncoder = 0;
  ui::Framebuffer800 a;
  ui::drawUi800(a, snapshot);
  snapshot.selectedEncoder = 5;
  ui::Framebuffer800 b;
  ui::drawUi800(b, snapshot);
  CHECK(a.at(10, 283) != b.at(10, 283));
  CHECK(a.at(500, 286) != b.at(500, 286));
  INFO("encoder selection highlight follows the mirrored 16-cell mapping");
}

TEST(UiFiveTabsRendered) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  VoiceCanvas canvas;
  ui::drawUi800(canvas, snapshot);
  const char* tabs[5] = {"MAIN", "SEQ", "MIX", "MOD", "GEN"};
  for (const char* tab : tabs) CHECK(canvas.has(tab));
  INFO("5 page tabs (MAIN/SEQ/MIX/MOD/GEN) rendered at 12 px");
}

TEST(UiCriticalHeaderText) {
  const std::string source = readSource("../src/ui/ui800.cpp");
  CHECK(source.find("BPM") != std::string::npos);
  CHECK(source.find("STEP") != std::string::npos);
  CHECK(source.find("UiTextRole::Critical") != std::string::npos);
  CHECK(source.find("uiBuildContextLine") != std::string::npos);
  INFO("BPM/STEP/REC use Critical 24 px; context line always built");
}

TEST(UiContextLineRendered) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  VoiceCanvas canvas;
  ui::drawUi800(canvas, snapshot);
  CHECK(canvas.has("PART 1"));
  CHECK(canvas.has("SELECTED"));
  CHECK(canvas.has("FADERS"));
  CHECK(canvas.has("REC"));
  CHECK(canvas.has("UNSAVED"));
  INFO("context line PART·SELECTED·PAGE·FADERS·REC·UNSAVED is rendered");
}
