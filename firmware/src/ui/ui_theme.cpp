// SPDX-License-Identifier: GPL-3.0-or-later
#include "bukifon_ui_theme.h"

#include <cctype>
#include <cstdio>
#include <cstring>

namespace {

// Exact values from docs/62-screen-palette.md (and docs/demo/demo.js THEMES).
const BukifonUiThemeInfo kThemes[BUKIFON_UI_THEME_COUNT] = {
    {"Night",
     {0x0a1a1d, 0x0d2428, 0x0e2024, 0x1e3a3f, 0xd7ecef, 0x7fb6bc, 0x4fd1e0,
      0x38c172, 0xf6993f, 0x4aa3ff, 0xff5c5c, 0xb07cff}},
    {"Amber",
     {0x0e0b08, 0x1a130c, 0x1f1710, 0x3a2a16, 0xf2e6d2, 0xb99b74, 0xffb347,
      0x7fbf5f, 0xf08a24, 0x5fa8d3, 0xe5544b, 0xc9a0dc}},
    {"Phosphor",
     {0x0a140c, 0x102016, 0x12261a, 0x23402c, 0xd8f5dc, 0x7fbf92, 0x5cff8a,
      0x38c172, 0xc9d96b, 0x6fd3c0, 0xff6b5c, 0x9ccf7a}},
    {"Cream",
     {0xe8e2d4, 0xdcd4c4, 0xf2ede2, 0xb9ae9a, 0x2a241c, 0x5f5548, 0xa8321f,
      0x3f6f2e, 0x9a4a10, 0x3d6e8f, 0x9c2a1a, 0x8a5a9e}},
};

int g_currentTheme = BUKIFON_UI_THEME_NIGHT;
const char kSettingsPath[] = "ui_theme.cfg";

bool equalsIgnoreCase(const char* a, const char* b) {
  if (!a || !b) return false;
  while (*a && *b) {
    if (std::tolower(static_cast<unsigned char>(*a)) !=
        std::tolower(static_cast<unsigned char>(*b))) {
      return false;
    }
    ++a;
    ++b;
  }
  return *a == '\0' && *b == '\0';
}

uint16_t toRgb565(uint32_t rgb) {
  const uint8_t r = static_cast<uint8_t>((rgb >> 16) & 0xFF);
  const uint8_t g = static_cast<uint8_t>((rgb >> 8) & 0xFF);
  const uint8_t b = static_cast<uint8_t>(rgb & 0xFF);
  return static_cast<uint16_t>(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}

}  // namespace

extern "C" {

int bukifon_ui_theme_count(void) { return BUKIFON_UI_THEME_COUNT; }

const BukifonUiThemeInfo* bukifon_ui_theme_info(int theme) {
  if (theme < 0 || theme >= BUKIFON_UI_THEME_COUNT) return nullptr;
  return &kThemes[theme];
}

const char* bukifon_ui_theme_name(int theme) {
  const BukifonUiThemeInfo* info = bukifon_ui_theme_info(theme);
  return info ? info->name : "";
}

int bukifon_ui_theme_current(void) { return g_currentTheme; }

int bukifon_ui_theme_set(const char* name) {
  if (!name || !name[0]) return 0;
  for (int i = 0; i < BUKIFON_UI_THEME_COUNT; ++i) {
    if (equalsIgnoreCase(name, kThemes[i].name)) {
      g_currentTheme = i;
      return 1;
    }
  }
  return 0;
}

uint32_t bukifon_ui_theme_rgb(int theme, int token) {
  if (theme < 0 || theme >= BUKIFON_UI_THEME_COUNT || token < 0 ||
      token >= BUKIFON_UI_COLOR_COUNT) {
    return 0;
  }
  return kThemes[theme].rgb[token];
}

uint16_t bukifon_ui_theme_rgb565(int theme, int token) {
  return toRgb565(bukifon_ui_theme_rgb(theme, token));
}

uint16_t bukifon_ui_theme_color(int token) {
  return bukifon_ui_theme_rgb565(g_currentTheme, token);
}

const char* bukifon_ui_theme_settings_path(void) { return kSettingsPath; }

int bukifon_ui_theme_save(const char* path) {
  const char* target = path && path[0] ? path : kSettingsPath;
  std::FILE* file = std::fopen(target, "wb");
  if (!file) return 0;
  const char* name = bukifon_ui_theme_name(g_currentTheme);
  const bool ok = std::fprintf(file, "%s\n", name) > 0;
  std::fclose(file);
  return ok ? 1 : 0;
}

int bukifon_ui_theme_load(const char* path) {
  const char* target = path && path[0] ? path : kSettingsPath;
  std::FILE* file = std::fopen(target, "rb");
  if (!file) return 0;
  char line[32] = {};
  const bool read = std::fgets(line, sizeof(line), file) != nullptr;
  std::fclose(file);
  if (!read) return 0;
  char* end = line;
  while (*end && *end != '\n' && *end != '\r') ++end;
  *end = '\0';
  return bukifon_ui_theme_set(line);
}

}  // extern "C"
