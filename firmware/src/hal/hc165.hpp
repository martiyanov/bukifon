// SPDX-License-Identifier: GPL-3.0-or-later
// 6 x 74HC165 shift-register input chain (48 bits: encoders A/B, encoder
// buttons, shoulder buttons, spare) — SPI0, PL = GP6, CP = GP2, QH = GP4.
// HARDWARE STATUS: not verified on real HW (timing/chain order to be checked).
#pragma once

#include <cstdint>

#include "hal/pinmap.hpp"

#if defined(ARDUINO)
#include <SPI.h>
#endif

namespace bukifon {
namespace hal {

class Hc165Chain {
 public:
  static constexpr int kChips = 6;
  static constexpr int kBits = kChips * 8;

  bool begin() {
#if defined(ARDUINO)
    pinMode(pins::kHc165Pl, OUTPUT);
    digitalWrite(pins::kHc165Pl, HIGH);
    SPI.begin();
    ready_ = true;
#endif
    return true;
  }

  // Latches and shifts the whole 48-bit chain into `shifted` (bit 0 = first bit).
  bool read(uint64_t* shifted) {
    if (!shifted) return false;
#if defined(ARDUINO)
    if (!ready_) begin();
    digitalWrite(pins::kHc165Pl, LOW);
    delayMicroseconds(1);
    digitalWrite(pins::kHc165Pl, HIGH);
    delayMicroseconds(1);
    uint64_t value = 0;
    SPI.beginTransaction(SPISettings(pins::kSpiClockHz, MSBFIRST, SPI_MODE0));
    for (int chip = 0; chip < kChips; ++chip) {
      const uint8_t byte = SPI.transfer(0x00);
      value = (value << 8) | byte;
    }
    SPI.endTransaction();
    *shifted = value;
    last_ = value;
    return true;
#else
    *shifted = last_;
    return true;
#endif
  }

  // Bit layout from spec/20-electronics.md §6.1:
  // 0..15 encoder A/B (ENC1..8), 16..23 encoder pushes, 24..27 shoulder buttons.
  uint64_t last() const { return last_; }
  int8_t encoderPhase(int encoder) const {
    const int bit = encoder * 2;
    return static_cast<int8_t>((last_ >> bit) & 0x3);
  }
  bool encoderPressed(int encoder) const { return ((last_ >> (16 + encoder)) & 1u) != 0; }
  bool shoulder(uint8_t index) const { return index < 4 && ((last_ >> (24 + index)) & 1u) != 0; }

 private:
  bool ready_ = false;
  uint64_t last_ = 0;
};

}  // namespace hal
}  // namespace bukifon
