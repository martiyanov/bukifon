// SPDX-License-Identifier: GPL-3.0-or-later
// UI palette tests: frozen docs/62 values, theme selection, persistence,
// token-based rendering for SYNTH + 4 device modes, no raw colours in the UI.
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

#include "bukifon_ui_theme.h"
#include "test_framework.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

uint64_t framebufferChecksum(const ui::Framebuffer800& fb) {
  uint64_t hash = 1469598103934665603ull;
  for (int y = 0; y < fb.height(); y += 5) {
    for (int x = 0; x < fb.width(); x += 5) {
      hash ^= fb.at(x, y);
      hash *= 1099511628211ull;
    }
  }
  return hash;
}

int nonBlackPixels(const ui::Framebuffer800& fb) {
  int count = 0;
  for (int y = 0; y < fb.height(); y += 3) {
    for (int x = 0; x < fb.width(); x += 3) {
      if (fb.at(x, y) != 0) ++count;
    }
  }
  return count;
}

uint16_t expectedRgb565(uint32_t rgb) {
  const uint8_t r = static_cast<uint8_t>((rgb >> 16) & 0xFF);
  const uint8_t g = static_cast<uint8_t>((rgb >> 8) & 0xFF);
  const uint8_t b = static_cast<uint8_t>(rgb & 0xFF);
  return static_cast<uint16_t>(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}

bool hasRawColorLiteral(const std::string& source) {
  // Flag 6/8-digit hex colours (0xRRGGBB / 0xAARRGGBB); short masks like 0x1F
  // and note numbers like 0x14 are not colours.
  for (size_t pos = source.find("0x"); pos != std::string::npos; pos = source.find("0x", pos + 1)) {
    size_t digits = 0;
    size_t i = pos + 2;
    while (i < source.size() && std::isxdigit(static_cast<unsigned char>(source[i]))) {
      ++digits;
      ++i;
    }
    if (digits >= 6) return true;
  }
  return false;
}

std::string readSource(const char* path) {
  std::FILE* file = std::fopen(path, "rb");
  if (!file) return std::string();
  std::string out;
  char buffer[4096];
  size_t n = 0;
  while ((n = std::fread(buffer, 1, sizeof(buffer), file)) > 0) out.append(buffer, n);
  std::fclose(file);
  return out;
}

}  // namespace

TEST(UiThemeCountAndNames) {
  CHECK(bukifon_ui_theme_count() == 4);
  CHECK(std::strcmp(bukifon_ui_theme_name(0), "Night") == 0);
  CHECK(std::strcmp(bukifon_ui_theme_name(1), "Amber") == 0);
  CHECK(std::strcmp(bukifon_ui_theme_name(2), "Phosphor") == 0);
  CHECK(std::strcmp(bukifon_ui_theme_name(3), "Cream") == 0);
  CHECK(bukifon_ui_theme_info(4) == nullptr);
  CHECK(bukifon_ui_theme_info(-1) == nullptr);
  CHECK(bukifon_ui_theme_set("Night"));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_NIGHT);
  INFO("themes: Night/Amber/Phosphor/Cream, default Night");
}

TEST(UiThemeNightValuesMatchDocs62) {
  const uint32_t expected[12] = {0x0a1a1d, 0x0d2428, 0x0e2024, 0x1e3a3f, 0xd7ecef, 0x7fb6bc,
                                 0x4fd1e0, 0x38c172, 0xf6993f, 0x4aa3ff, 0xff5c5c, 0xb07cff};
  for (int token = 0; token < 12; ++token) {
    CHECK(bukifon_ui_theme_rgb(BUKIFON_UI_THEME_NIGHT, token) == expected[token]);
    CHECK(bukifon_ui_theme_rgb565(BUKIFON_UI_THEME_NIGHT, token) == expectedRgb565(expected[token]));
  }
  INFO("Night palette matches docs/62 exactly (12 tokens)");
}

TEST(UiThemeAmberValuesMatchDocs62) {
  const uint32_t expected[12] = {0x0e0b08, 0x1a130c, 0x1f1710, 0x3a2a16, 0xf2e6d2, 0xb99b74,
                                 0xffb347, 0x7fbf5f, 0xf08a24, 0x5fa8d3, 0xe5544b, 0xc9a0dc};
  for (int token = 0; token < 12; ++token) {
    CHECK(bukifon_ui_theme_rgb(BUKIFON_UI_THEME_AMBER, token) == expected[token]);
  }
  INFO("Amber palette matches docs/62 exactly (12 tokens)");
}

TEST(UiThemePhosphorValuesMatchDocs62) {
  const uint32_t expected[12] = {0x0a140c, 0x102016, 0x12261a, 0x23402c, 0xd8f5dc, 0x7fbf92,
                                 0x5cff8a, 0x38c172, 0xc9d96b, 0x6fd3c0, 0xff6b5c, 0x9ccf7a};
  for (int token = 0; token < 12; ++token) {
    CHECK(bukifon_ui_theme_rgb(BUKIFON_UI_THEME_PHOSPHOR, token) == expected[token]);
  }
  INFO("Phosphor palette matches docs/62 exactly (12 tokens)");
}

TEST(UiThemeCreamValuesMatchDocs62) {
  const uint32_t expected[12] = {0xe8e2d4, 0xdcd4c4, 0xf2ede2, 0xb9ae9a, 0x2a241c, 0x5f5548,
                                 0xa8321f, 0x3f6f2e, 0x9a4a10, 0x3d6e8f, 0x9c2a1a, 0x8a5a9e};
  for (int token = 0; token < 12; ++token) {
    CHECK(bukifon_ui_theme_rgb(BUKIFON_UI_THEME_CREAM, token) == expected[token]);
  }
  INFO("Cream palette matches docs/62 exactly (12 tokens)");
}

TEST(UiThemeSelectByApiAndBounds) {
  CHECK(bukifon_ui_theme_set("Cream"));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_CREAM);
  CHECK(bukifon_ui_theme_set("amber"));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_AMBER);
  CHECK(bukifon_ui_theme_set("PHOSPHOR"));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_PHOSPHOR);
  CHECK(!bukifon_ui_theme_set("neon"));
  CHECK(!bukifon_ui_theme_set(nullptr));
  CHECK(!bukifon_ui_theme_set(""));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_PHOSPHOR);
  CHECK(bukifon_ui_theme_rgb(99, 0) == 0);
  CHECK(bukifon_ui_theme_rgb565(0, 99) == 0);
  bukifon_ui_theme_set("Night");
  INFO("ui_theme_set(name) case-insensitive, invalid names/ids rejected");
}

TEST(UiThemePersistenceFile) {
  const char* path = "../tests/out/ui_theme_test.cfg";
  CHECK(bukifon_ui_theme_set("Cream"));
  CHECK(bukifon_ui_theme_save(path));
  CHECK(bukifon_ui_theme_set("Amber"));
  CHECK(bukifon_ui_theme_load(path));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_CREAM);
  CHECK(!bukifon_ui_theme_load("../tests/out/no_such_theme_file.cfg"));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_CREAM);  // unchanged on missing file
  // Corrupt value must not change the current theme.
  std::FILE* file = std::fopen(path, "wb");
  CHECK(file != nullptr);
  if (file) {
    std::fputs("neon\n", file);
    std::fclose(file);
  }
  CHECK(!bukifon_ui_theme_load(path));
  CHECK(bukifon_ui_theme_current() == BUKIFON_UI_THEME_CREAM);
  std::remove(path);
  CHECK(bukifon_ui_theme_settings_path() != nullptr);
  CHECK(std::strlen(bukifon_ui_theme_settings_path()) > 0);
  bukifon_ui_theme_set("Night");
  INFO("theme persistence: host file save/load, missing/corrupt file keeps state");
}

TEST(UiThemeSynthScreenRendersAllThemes) {
  ui::Framebuffer800 fb;
  CHECK(fb.valid());
  uint64_t checksums[4] = {};
  for (int theme = 0; theme < 4; ++theme) {
    CHECK(bukifon_ui_theme_set(bukifon_ui_theme_name(theme)));
    fb.clear(0);
    ui::UiSnapshot snapshot;
    ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
    ui::uiSnapshotForDeviceMode(&snapshot, DeviceMode::Synth);
    ui::drawUi800(fb, snapshot);
    CHECK(nonBlackPixels(fb) > 2000);
    checksums[theme] = framebufferChecksum(fb);
  }
  CHECK(checksums[0] != checksums[1]);
  CHECK(checksums[1] != checksums[2]);
  CHECK(checksums[2] != checksums[3]);
  CHECK(checksums[0] != checksums[3]);
  bukifon_ui_theme_set("Night");
  INFO("SYNTH screen renders with all 4 themes; distinct pixel checksums");
}

TEST(UiThemeFourModesAllThemes) {
  const DeviceMode modes[4] = {DeviceMode::Synth, DeviceMode::Sampler,
                               DeviceMode::DawController, DeviceMode::UsbKeyboard};
  uint64_t checksums[4][4] = {};
  for (int theme = 0; theme < 4; ++theme) {
    CHECK(bukifon_ui_theme_set(bukifon_ui_theme_name(theme)));
    for (int mode = 0; mode < 4; ++mode) {
      ui::Framebuffer800 fb;
      CHECK(fb.valid());
      ui::UiSnapshot snapshot;
      ui::uiSnapshotForDeviceMode(&snapshot, modes[mode]);
      ui::drawUi800(fb, snapshot);
      CHECK(nonBlackPixels(fb) > 2000);
      checksums[theme][mode] = framebufferChecksum(fb);
    }
  }
  for (int mode = 0; mode < 4; ++mode) {
    CHECK(checksums[0][mode] != checksums[3][mode]);  // Night vs Cream
  }
  bukifon_ui_theme_set("Night");
  INFO("4 device modes × 4 themes render from the same tokens");
}

TEST(UiThemeNoRawColorsInRenderer) {
  const std::string ui800 = readSource("../src/ui/ui800.cpp");
  const std::string menu = readSource("../src/ui/menu.cpp");
  CHECK(!ui800.empty());
  CHECK(!menu.empty());
  for (const std::string* source : {&ui800, &menu}) {
    CHECK(source->find("colors::") == std::string::npos);
    CHECK(source->find("rgb565(") == std::string::npos);
    CHECK(!hasRawColorLiteral(*source));  // no raw 0xRRGGBB colour literals
  }
  CHECK(ui800.find("bukifon_ui_theme.h") != std::string::npos);
  CHECK(menu.find("bukifon_ui_theme.h") != std::string::npos);
  INFO("renderers contain no raw colours: only bukifon_ui_theme.h tokens");
}
