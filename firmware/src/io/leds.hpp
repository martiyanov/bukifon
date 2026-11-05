// SPDX-License-Identifier: GPL-3.0-or-later
// WS2812 LED chain model (27 or 51 LEDs) with music-oriented colour helpers.
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "io/deck.hpp"

namespace bukifon {

struct Rgb {
  uint8_t r = 0;
  uint8_t g = 0;
  uint8_t b = 0;
};

class LedChain {
 public:
  static constexpr int kMaxLeds = kPanelLeds + kKeyLeds;  // 51

  void setLength(int length) {
    length_ = (length < 0) ? 0 : (length > kMaxLeds ? kMaxLeds : length);
  }
  int length() const { return length_; }
  void clear() {
    for (int i = 0; i < kMaxLeds; ++i) pixels_[i] = Rgb{};
  }
  void set(int index, Rgb color) {
    if (index < 0 || index >= length_) return;
    pixels_[index] = color;
  }
  Rgb get(int index) const {
    if (index < 0 || index >= kMaxLeds) return Rgb{};
    return pixels_[index];
  }
  const Rgb* pixels() const { return pixels_; }
  const uint8_t* bytes() const { return reinterpret_cast<const uint8_t*>(pixels_); }
  static constexpr int byteCount(int length) { return length * 3; }

  // HSV -> RGB (h in 0..1, s/v in 0..1).
  static Rgb hsv(float h, float s, float v);
  static Rgb levelColor(float level);   // green -> yellow -> red
  static Rgb noteColor(int midiNote);   // rainbow over 4 octaves
  static Rgb dim(Rgb c, float scale);

 private:
  int length_ = kPanelLeds;
  Rgb pixels_[kMaxLeds] = {};
};

// Builds the panel + deck LED frame from a compact UI state.
struct LedState {
  float encoderValue[kNumEncoders] = {};  // 0..1
  uint8_t activeStep = 0;
  uint8_t pattern = 0;
  bool playing = false;
  bool shift = false;
  float masterLevel = 0.0f;
  uint8_t padPressedMask = 0;    // bit per pad (18)
  uint32_t keyPressedMask = 0;   // bit per key (42)
};

void buildLedFrame(const LedState& state, DeckType deckType, LedChain* chain);

}  // namespace bukifon
