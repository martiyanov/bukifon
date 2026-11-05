// SPDX-License-Identifier: GPL-3.0-or-later
// ST7789 2.8" 320x240 SPI display (SPI1 GP10/11 + CS/DC/RST/BL GP12..15).
//
// Implements ICanvas so the portable UI (src/ui/menu.cpp) draws straight onto
// the panel. HARDWARE STATUS: not verified on real glass; init sequence is a
// standard ST7789 320x240 preset. TODO(hw): verify orientation/offset and BL PWM.
#pragma once

#include <cstddef>
#include <cstdint>

#include "hal/pinmap.hpp"
#include "ui/canvas.hpp"

#if defined(ARDUINO)
#include <SPI.h>
#endif

namespace bukifon {
namespace hal {

class St7789 : public ICanvas {
 public:
  bool begin() {
#if defined(ARDUINO)
    pinMode(pins::kLcdCs, OUTPUT);
    pinMode(pins::kLcdDc, OUTPUT);
    pinMode(pins::kLcdRst, OUTPUT);
    pinMode(pins::kLcdBl, OUTPUT);
    digitalWrite(pins::kLcdCs, HIGH);
    digitalWrite(pins::kLcdBl, HIGH);
    digitalWrite(pins::kLcdRst, LOW);
    delay(20);
    digitalWrite(pins::kLcdRst, HIGH);
    delay(120);
    SPI1.begin();
    SPI1.beginTransaction(SPISettings(40000000, MSBFIRST, SPI_MODE0));
    command(0x01);  // SWRESET
    delay(150);
    command(0x11);  // SLPOUT
    delay(120);
    command(0x3A);  // COLMOD 16 bit
    data(0x55);
    command(0x36);  // MADCTL
    data(0x00);
    command(0x21);  // inversion on (common for IPS panels)
    delay(10);
    command(0x13);  // NORON
    delay(10);
    command(0x29);  // DISPON
    delay(20);
    ready_ = true;
#endif
    return true;
  }

  int width() const override { return 320; }
  int height() const override { return 240; }

  void fillRect(int x, int y, int w, int h, uint16_t color) override {
    if (w <= 0 || h <= 0) return;
    setWindow(x, y, x + w - 1, y + h - 1);
#if defined(ARDUINO)
    if (!ready_) begin();
    digitalWrite(pins::kLcdDc, HIGH);
    digitalWrite(pins::kLcdCs, LOW);
    for (int i = 0; i < w * h; ++i) {
      SPI1.transfer16(color);
    }
    digitalWrite(pins::kLcdCs, HIGH);
#endif
  }

  void drawPixel(int x, int y, uint16_t color) override {
    if (x < 0 || y < 0 || x >= width() || y >= height()) return;
    // Point writes are slow on ST7789; the UI uses fillRect for everything
    // large. TODO(hw): batch pixels through a line buffer.
    fillRect(x, y, 1, 1, color);
  }

  void drawChar(int x, int y, char c, uint16_t color) override {
    if (c < 32 || c > 127) c = '?';
    const uint8_t* glyph = kFont6x8[static_cast<int>(c) - 32];
    for (int row = 0; row < kFontHeight; ++row) {
      for (int col = 0; col < kFontWidth; ++col) {
        if (glyph[row] & (1u << col)) drawPixel(x + col, y + row, color);
      }
    }
  }

  void setBacklight(uint8_t level) {
#if defined(ARDUINO)
    analogWrite(pins::kLcdBl, level);
#else
    (void)level;
#endif
  }

 private:
  void setWindow(int x0, int y0, int x1, int y1) {
#if defined(ARDUINO)
    command(0x2A);
    data(static_cast<uint8_t>(x0 >> 8));
    data(static_cast<uint8_t>(x0 & 0xFF));
    data(static_cast<uint8_t>(x1 >> 8));
    data(static_cast<uint8_t>(x1 & 0xFF));
    command(0x2B);
    data(static_cast<uint8_t>(y0 >> 8));
    data(static_cast<uint8_t>(y0 & 0xFF));
    data(static_cast<uint8_t>(y1 >> 8));
    data(static_cast<uint8_t>(y1 & 0xFF));
    command(0x2C);  // RAMWR
#else
    (void)x0;
    (void)y0;
    (void)x1;
    (void)y1;
#endif
  }

  void command(uint8_t cmd) {
#if defined(ARDUINO)
    if (!ready_) {
      digitalWrite(pins::kLcdCs, LOW);
      digitalWrite(pins::kLcdDc, LOW);
      SPI1.transfer(cmd);
      digitalWrite(pins::kLcdCs, HIGH);
      return;
    }
    digitalWrite(pins::kLcdCs, LOW);
    digitalWrite(pins::kLcdDc, LOW);
    SPI1.transfer(cmd);
    digitalWrite(pins::kLcdCs, HIGH);
#else
    (void)cmd;
#endif
  }

  void data(uint8_t value) {
#if defined(ARDUINO)
    digitalWrite(pins::kLcdCs, LOW);
    digitalWrite(pins::kLcdDc, HIGH);
    SPI1.transfer(value);
    digitalWrite(pins::kLcdCs, HIGH);
#else
    (void)value;
#endif
  }

  bool ready_ = false;
};

}  // namespace hal
}  // namespace bukifon
