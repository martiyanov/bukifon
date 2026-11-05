// SPDX-License-Identifier: GPL-3.0-or-later
// WS2812 / SK6812 LED chain on GP7: 9 panel LEDs + 18 (PAD) or 42 (KEYS) deck.
//
// HARDWARE STATUS: TODO(hw) — this is a bit-banged fallback so the sketch is
// complete; the production firmware must use a PIO+DMA WS2812 driver (800 kHz,
// reset > 50 us) to avoid interrupt jitter. Timing constants below are for a
// 125 MHz RP2040 and are marked not hardware-verified.
#pragma once

#include <cstdint>

#include "hal/pinmap.hpp"
#include "io/leds.hpp"

#if defined(ARDUINO)
#include <Arduino.h>
#endif

namespace bukifon {
namespace hal {

class Ws2812Chain : public LedChain {
 public:
  bool begin() {
#if defined(ARDUINO)
    // TODO(hw): replace with PIO+DMA (pio_ws2812) driver.
    pinMode(pins::kLedData, OUTPUT);
    digitalWrite(pins::kLedData, LOW);
    ready_ = true;
#endif
    return true;
  }

  void setBrightness(uint8_t brightness) { brightness_ = brightness; }

  // Pushes the whole chain (bit-banged fallback).
  void show() {
#if defined(ARDUINO)
    if (!ready_) begin();
    noInterrupts();
    const int count = length();
    for (int i = 0; i < count; ++i) {
      const Rgb c = get(i);
      sendByte(static_cast<uint8_t>(c.g * brightness_ / 255));
      sendByte(static_cast<uint8_t>(c.r * brightness_ / 255));
      sendByte(static_cast<uint8_t>(c.b * brightness_ / 255));
    }
    interrupts();
    delayMicroseconds(80);  // reset gap
#endif
  }

 private:
#if defined(ARDUINO)
  void sendByte(uint8_t value) {
    for (int bit = 7; bit >= 0; --bit) {
      if (value & (1u << bit)) {
        digitalWrite(pins::kLedData, HIGH);
        delayMicroseconds(1);  // ~0.8 us high (T1H)
        digitalWrite(pins::kLedData, LOW);
        delayMicroseconds(1);  // ~0.45 us low (T1L)
      } else {
        digitalWrite(pins::kLedData, HIGH);
        delayMicroseconds(1);  // ~0.4 us high (T0H)
        digitalWrite(pins::kLedData, LOW);
        delayMicroseconds(1);  // ~0.85 us low (T0L)
      }
    }
  }
#endif
  bool ready_ = false;
  uint8_t brightness_ = 255;
};

}  // namespace hal
}  // namespace bukifon
