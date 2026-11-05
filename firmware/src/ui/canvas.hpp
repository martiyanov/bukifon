// SPDX-License-Identifier: GPL-3.0-or-later
// Minimal drawing abstraction for the 320x240 ST7789 UI (portable).
#pragma once

#include <cstdint>

#include "ui/font6x8.hpp"

namespace bukifon {

constexpr uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return static_cast<uint16_t>(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}

namespace colors {
constexpr uint16_t kBlack = rgb565(0, 0, 0);
constexpr uint16_t kWhite = rgb565(255, 255, 255);
constexpr uint16_t kGrey = rgb565(120, 120, 120);
constexpr uint16_t kDim = rgb565(40, 44, 52);
constexpr uint16_t kPanel = rgb565(16, 18, 24);
constexpr uint16_t kAccent = rgb565(80, 220, 255);
constexpr uint16_t kValue = rgb565(255, 210, 90);
constexpr uint16_t kGreen = rgb565(80, 255, 120);
constexpr uint16_t kRed = rgb565(255, 80, 80);
}  // namespace colors

class ICanvas {
 public:
  virtual ~ICanvas() = default;
  virtual int width() const = 0;
  virtual int height() const = 0;
  virtual void fillRect(int x, int y, int w, int h, uint16_t color) = 0;
  virtual void drawPixel(int x, int y, uint16_t color) = 0;
  virtual void drawRect(int x, int y, int w, int h, uint16_t color) {
    fillRect(x, y, w, 1, color);
    fillRect(x, y + h - 1, w, 1, color);
    fillRect(x, y, 1, h, color);
    fillRect(x + w - 1, y, 1, h, color);
  }
  virtual void drawText(int x, int y, const char* text, uint16_t color, uint16_t bg = 0xFFFF) {
    drawTextImpl(x, y, text, color, bg);
  }
  virtual void drawChar(int x, int y, char c, uint16_t color) = 0;

  // Default text renderer uses the generated 6x8 font.
  void drawTextImpl(int x, int y, const char* text, uint16_t color, uint16_t bg) {
    int cx = x;
    for (const char* p = text; *p; ++p) {
      if (bg != 0xFFFF) fillRect(cx, y, kFontWidth, kFontHeight, bg);
      drawChar(cx, y, *p, color);
      cx += kFontWidth;
    }
  }
};

// Software framebuffer canvas used by the host tests and as a fallback.
class FrameBufferCanvas : public ICanvas {
 public:
  static constexpr int kWidth = 320;
  static constexpr int kHeight = 240;

  FrameBufferCanvas() { clear(colors::kBlack); }
  int width() const override { return kWidth; }
  int height() const override { return kHeight; }
  void clear(uint16_t color) {
    for (int i = 0; i < kWidth * kHeight; ++i) pixels_[i] = color;
  }
  void fillRect(int x, int y, int w, int h, uint16_t color) override {
    for (int yy = y; yy < y + h; ++yy) {
      if (yy < 0 || yy >= kHeight) continue;
      for (int xx = x; xx < x + w; ++xx) {
        if (xx < 0 || xx >= kWidth) continue;
        pixels_[yy * kWidth + xx] = color;
      }
    }
  }
  void drawPixel(int x, int y, uint16_t color) override {
    if (x < 0 || x >= kWidth || y < 0 || y >= kHeight) return;
    pixels_[y * kWidth + x] = color;
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
  uint16_t at(int x, int y) const {
    if (x < 0 || x >= kWidth || y < 0 || y >= kHeight) return 0;
    return pixels_[y * kWidth + x];
  }

 private:
  uint16_t pixels_[kWidth * kHeight] = {};
};

}  // namespace bukifon
