// SPDX-License-Identifier: GPL-3.0-or-later
// 42-key "Lapka-42" deck as a USB HID keyboard with layers and macros.
//
// Layout: 3x6 + 3 thumbs per half (Corne-like), 42 keys total (KEY1..KEY42).
// HID reports are the standard boot-protocol 6KRO keyboard report (8 modifier
// bits + 6 keycodes).  This is the mapping used by the USB-keyboard and DAW
// modes; the same physical keys stay synth notes in the other modes.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum HidModifier : uint8_t {
  HidLeftCtrl = 1u << 0,
  HidLeftShift = 1u << 1,
  HidLeftAlt = 1u << 2,
  HidLeftGui = 1u << 3,
  HidRightCtrl = 1u << 4,
  HidRightShift = 1u << 5,
  HidRightAlt = 1u << 6,
  HidRightGui = 1u << 7
};

// Keyboard/Keypad HID usage IDs used by the default keymap.
namespace hid_usage {
constexpr uint8_t kNone = 0x00;
constexpr uint8_t kA = 0x04;
constexpr uint8_t kEnter = 0x28;
constexpr uint8_t kEscape = 0x29;
constexpr uint8_t kBackspace = 0x2A;
constexpr uint8_t kTab = 0x2B;
constexpr uint8_t kSpace = 0x2C;
constexpr uint8_t kMinus = 0x2D;
constexpr uint8_t kEqual = 0x2E;
constexpr uint8_t kLeftBracket = 0x2F;
constexpr uint8_t kRightBracket = 0x30;
constexpr uint8_t kBackslash = 0x31;
constexpr uint8_t kSemicolon = 0x33;
constexpr uint8_t kQuote = 0x34;
constexpr uint8_t kGrave = 0x35;
constexpr uint8_t kComma = 0x36;
constexpr uint8_t kPeriod = 0x37;
constexpr uint8_t kSlash = 0x38;
constexpr uint8_t kF1 = 0x3A;
}  // namespace hid_usage

enum class KeyboardLayer : uint8_t {
  Base = 0,   // QWERTY
  Shift,      // shifted letters
  Symbols,    // F-keys / punctuation / arrows
  Daw,        // transport-oriented keys
  Macro,      // macro stubs (strings)
  kNumLayers
};

const char* keyboardLayerName(KeyboardLayer layer);

struct HidKey {
  uint8_t modifier = 0;
  uint8_t keycode = 0;
};

struct HidReport {
  uint8_t modifiers = 0;
  uint8_t keycodes[6] = {};
  uint8_t keyCount = 0;
};

class HidKeyboardMapper {
 public:
  HidKeyboardMapper();

  void setLayer(KeyboardLayer layer) { layer_ = layer; }
  KeyboardLayer layer() const { return layer_; }
  bool setLayerIndex(int index);

  // Mapping of one physical key (0..41) on the current layer.
  HidKey key(int keyIndex) const;
  HidKey key(int keyIndex, KeyboardLayer layer) const;

  // Builds a report from the pressed-key bitmap (42 bits in a bool array).
  void buildReport(const bool pressed[kNumKeys], HidReport* report) const;

  // Macro layer: a short human-readable macro per key (stub, no execution yet).
  const char* macroFor(int keyIndex) const;

  static constexpr int keyCount() { return kNumKeys; }

 private:
  KeyboardLayer layer_ = KeyboardLayer::Base;
};

// HID report byte layout: [modifiers, reserved, key1..key6] = 8 bytes.
constexpr int kHidReportBytes = 8;
void encodeHidReport(const HidReport& report, uint8_t out[kHidReportBytes]);

}  // namespace bukifon
