// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/hid_keyboard.hpp"

#include <cstring>

namespace bukifon {
namespace {

constexpr uint8_t K = hid_usage::kNone;
constexpr uint8_t A = hid_usage::kA;

// Lapka-42 (Corne-like).  Index 0..20 = left half rows + thumbs, 21..41 = right.
// Left rows:   Q W E R T Y / A S D F G H / Z X C V B N / LCMD LCTRL LALT
// Right rows:  U I O P [ ] / J K L ; ' \ / M , . / RSHIFT RALT / SPACE ENTER BSPC
const uint8_t kBaseMap[kNumKeys] = {
    // Left half
    A + 16, A + 22, A + 4,  A + 17, A + 19, A + 24,   // Q W E R T Y
    A + 0,  A + 18, A + 3,  A + 5,  A + 6,  A + 7,    // A S D F G H
    A + 25, A + 23, A + 2,  A + 21, A + 1,  A + 13,   // Z X C V B N
    K,      K,      K,                                // LCTRL LSHIFT LALT (mod only)
    // Right half
    A + 20, A + 8,  A + 14, A + 15, hid_usage::kLeftBracket, hid_usage::kRightBracket,  // U I O P [ ]
    A + 9,  A + 10, A + 11, hid_usage::kSemicolon, hid_usage::kQuote, hid_usage::kBackslash,  // J K L ; quote backslash
    A + 12, hid_usage::kComma, hid_usage::kPeriod, hid_usage::kSlash, K, K,  // M , . / RSHIFT RALT
    hid_usage::kSpace, hid_usage::kEnter, hid_usage::kBackspace,             // SPACE ENTER BSPC
};

// Symbols/function layer (left and right halves).
const uint8_t kSymbolMap[kNumKeys] = {
    hid_usage::kEscape, hid_usage::kF1, hid_usage::kF1 + 1, hid_usage::kF1 + 2, hid_usage::kF1 + 3,
    hid_usage::kF1 + 4,
    hid_usage::kF1 + 5, hid_usage::kF1 + 6, hid_usage::kF1 + 7, hid_usage::kF1 + 8,
    hid_usage::kF1 + 9, hid_usage::kF1 + 10,
    hid_usage::kGrave, hid_usage::kMinus, hid_usage::kEqual, hid_usage::kTab,
    hid_usage::kLeftBracket, hid_usage::kRightBracket,
    K, K, K,
    // Right half: punctuation and arrows
    hid_usage::kMinus, hid_usage::kEqual, hid_usage::kLeftBracket, hid_usage::kRightBracket,
    hid_usage::kBackslash, hid_usage::kSemicolon,
    hid_usage::kQuote, hid_usage::kComma, hid_usage::kPeriod, hid_usage::kSlash, 0x4F, 0x50,
    0x51, 0x52, K, K,
    hid_usage::kSpace, hid_usage::kEnter, hid_usage::kBackspace,
};

// DAW layer: transport / navigation keys (the host DAW maps these itself).
const uint8_t kDawMap[kNumKeys] = {
    hid_usage::kSpace, K, hid_usage::kSpace, K, K, K,
    K, K, K, K, K, K,
    K, K, K, K, K, K,
    K, K, K,
    K, K, K, K, K, K,
    K, K, K, K, 0x4F, 0x50,
    0x51, 0x52, K, K, K, K,
    hid_usage::kSpace, hid_usage::kEnter, hid_usage::kBackspace,
};

const uint8_t kMacroMap[kNumKeys] = {
    A + 2, A + 0, A + 19, A + 4, A + 22, A + 5, A + 13, A + 8, A + 22, A + 4, A + 20, A + 18,
    A + 18, A + 0, A + 21, A + 4, A + 5, A + 3, A + 18, A + 0, A + 21, A + 2, A + 0, A + 18,
    A + 8, A + 4, A + 20, A + 13, A + 0, A + 4, A + 22, A + 0, A + 8, A + 18, A + 8, A + 22,
    A + 4, A + 18, A + 22, A + 22, A + 4, A + 22,
};

const char* kMacroNames[kNumKeys] = {
    "CUT 2400", "RES 62", "ENV AMT", "DRIVE", "ATK 10ms", "DEC 340",
    "SUS 65",   "REL 420", "BPM 120", "BPM 140", "PLAY",    "STOP",
    "REC",      "LOOP",    "SHIFT",   "FILL",   "MUTE P1", "MUTE P2",
    "BANK 1",   "BANK 2",  "BANK 3",  "BANK 4", "UNDO",    "REDO",
    "SAVE",     "LOAD",    "COPY",    "PASTE",  "PAGE 1",  "PAGE 2",
    "PAGE 3",   "PAGE 4",  "DELAY",   "CHORUS", "CRUSH",   "LIMIT",
    "MODULE",   "SYNTH",   "DAW",     "KBD",    "HID",     "MIDI",
};

uint8_t modifierForKey(int keyIndex, KeyboardLayer layer) {
  // Thumb modifier keys: left thumbs 18..20 = LCTRL/LSHIFT/LALT,
  // right thumb area 36..38 = RSHIFT/RALT/... (see map below).
  if (layer == KeyboardLayer::Shift) return HidLeftShift;
  switch (keyIndex) {
    case 18: return HidLeftCtrl;
    case 19: return HidLeftShift;
    case 20: return HidLeftAlt;
    case 37: return HidRightShift;
    case 38: return HidRightAlt;
    default: return 0;
  }
}

const uint8_t* mapForLayer(KeyboardLayer layer) {
  switch (layer) {
    case KeyboardLayer::Symbols: return kSymbolMap;
    case KeyboardLayer::Daw: return kDawMap;
    case KeyboardLayer::Macro: return kMacroMap;
    case KeyboardLayer::Shift:
    case KeyboardLayer::Base:
    default: return kBaseMap;
  }
}

}  // namespace

const char* keyboardLayerName(KeyboardLayer layer) {
  switch (layer) {
    case KeyboardLayer::Base: return "BASE";
    case KeyboardLayer::Shift: return "SHIFT";
    case KeyboardLayer::Symbols: return "SYMBOLS";
    case KeyboardLayer::Daw: return "DAW";
    case KeyboardLayer::Macro: return "MACRO";
    default: return "?";
  }
}

HidKeyboardMapper::HidKeyboardMapper() = default;

bool HidKeyboardMapper::setLayerIndex(int index) {
  if (index < 0 || index >= static_cast<int>(KeyboardLayer::kNumLayers)) return false;
  layer_ = static_cast<KeyboardLayer>(index);
  return true;
}

HidKey HidKeyboardMapper::key(int keyIndex) const { return key(keyIndex, layer_); }

HidKey HidKeyboardMapper::key(int keyIndex, KeyboardLayer layer) const {
  HidKey out;
  if (keyIndex < 0 || keyIndex >= kNumKeys) return out;
  out.keycode = mapForLayer(layer)[keyIndex];
  out.modifier = modifierForKey(keyIndex, layer);
  return out;
}

void HidKeyboardMapper::buildReport(const bool pressed[kNumKeys], HidReport* report) const {
  if (!report) return;
  report->modifiers = 0;
  report->keyCount = 0;
  std::memset(report->keycodes, 0, sizeof(report->keycodes));
  for (int k = 0; k < kNumKeys; ++k) {
    if (!pressed[k]) continue;
    const HidKey mapped = key(k);
    report->modifiers |= mapped.modifier;
    if (mapped.keycode != hid_usage::kNone && report->keyCount < 6) {
      report->keycodes[report->keyCount++] = mapped.keycode;
    }
  }
}

const char* HidKeyboardMapper::macroFor(int keyIndex) const {
  if (keyIndex < 0 || keyIndex >= kNumKeys) return "";
  return kMacroNames[keyIndex];
}

void encodeHidReport(const HidReport& report, uint8_t out[kHidReportBytes]) {
  if (!out) return;
  out[0] = report.modifiers;
  out[1] = 0;
  for (int i = 0; i < 6; ++i) out[2 + i] = report.keycodes[i];
}

}  // namespace bukifon
