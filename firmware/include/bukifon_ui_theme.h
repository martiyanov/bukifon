// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon UI palette — single source of truth for firmware, host demo and site.
//
// Values are frozen in docs/62-screen-palette.md (4 themes, 12 tokens each) and
// match docs/demo/demo.js -> THEMES.  The firmware UI must render only through
// these tokens (no hardcoded colours in src/ui/ui800.cpp / menu.cpp).
//
// Colours are stored as 24-bit RGB (0xRRGGBB) and converted to RGB565 at draw
// time; the current theme is a process-global selection (default Night) with a
// host file-backed settings stub (real NVS/flash persistence is TODO(hw)).
#ifndef BUKIFON_UI_THEME_H
#define BUKIFON_UI_THEME_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum BukifonUiThemeId {
  BUKIFON_UI_THEME_NIGHT = 0,
  BUKIFON_UI_THEME_AMBER = 1,
  BUKIFON_UI_THEME_PHOSPHOR = 2,
  BUKIFON_UI_THEME_CREAM = 3,
  BUKIFON_UI_THEME_COUNT = 4
} BukifonUiThemeId;

typedef enum BukifonUiColorToken {
  BUKIFON_UI_BG = 0,
  BUKIFON_UI_PANEL = 1,
  BUKIFON_UI_CARD = 2,
  BUKIFON_UI_LINE = 3,
  BUKIFON_UI_TEXT = 4,
  BUKIFON_UI_MUTED = 5,
  BUKIFON_UI_ACCENT = 6,
  BUKIFON_UI_GREEN = 7,
  BUKIFON_UI_ORANGE = 8,
  BUKIFON_UI_BLUE = 9,
  BUKIFON_UI_RED = 10,
  BUKIFON_UI_PURPLE = 11,
  BUKIFON_UI_COLOR_COUNT = 12
} BukifonUiColorToken;

typedef struct BukifonUiThemeInfo {
  const char* name;                 // "Night", "Amber", "Phosphor", "Cream"
  uint32_t rgb[BUKIFON_UI_COLOR_COUNT];  // 0xRRGGBB, docs/62
} BukifonUiThemeInfo;

int bukifon_ui_theme_count(void);
const BukifonUiThemeInfo* bukifon_ui_theme_info(int theme);
const char* bukifon_ui_theme_name(int theme);

// Current theme (process-global; default Night).
int bukifon_ui_theme_current(void);
// Select by name (case-insensitive); returns 1 on success, 0 for unknown/none.
int bukifon_ui_theme_set(const char* name);

// 24-bit RGB and RGB565 for an explicit/current theme + token.
uint32_t bukifon_ui_theme_rgb(int theme, int token);
uint16_t bukifon_ui_theme_rgb565(int theme, int token);
uint16_t bukifon_ui_theme_color(int token);  // current theme, RGB565

// Host settings stub: save/load the current theme name to a plain file.
// On device this is replaced by NVS/flash persistence (TODO(hw)).
const char* bukifon_ui_theme_settings_path(void);
int bukifon_ui_theme_save(const char* path);
int bukifon_ui_theme_load(const char* path);

#ifdef __cplusplus
}
#endif

#ifdef __cplusplus
namespace bukifon {
namespace ui {
inline uint16_t themeColor(BukifonUiColorToken token) {
  return bukifon_ui_theme_color(static_cast<int>(token));
}
inline bool setTheme(const char* name) { return bukifon_ui_theme_set(name) != 0; }
inline const char* currentThemeName() { return bukifon_ui_theme_name(bukifon_ui_theme_current()); }
}  // namespace ui
}  // namespace bukifon
#endif

#endif  // BUKIFON_UI_THEME_H
