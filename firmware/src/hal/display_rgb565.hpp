// SPDX-License-Identifier: GPL-3.0-or-later
// RGB565 display backend skeleton (P4 first SKU; docs/31, host_p4 profile).
//
// Interface: init / attachFramebuffer / flushRows / flushFull / flushPartial /
// dirty-rect tracking.  The actual esp_lcd RGB/DSI + DMA2D/PPA path is TODO(hw);
// on the host it simulates frame flushes and reports the P4 model metrics
// (52.1 full fps, 130.2 partial fps at 800x480, 20 MHz pixel clock).
#pragma once

#include <cstddef>
#include <cstdint>

namespace bukifon {
namespace hal {

struct Rgb565Config {
  int width = 800;
  int height = 480;
  uint32_t pixelClockHz = 20000000;  // P4 RGB565 target model (docs/31)
  int bounceRows = 16;               // 8-16 rows in internal SRAM
  bool dsi = false;                  // RGB parallel (false) or DSI (true)
};

struct Rgb565Metrics {
  uint64_t fullFrames = 0;
  uint64_t partialUpdates = 0;
  uint64_t bytesFlushed = 0;
  uint64_t droppedBands = 0;
  uint32_t lastFullUs = 0;
  uint32_t lastPartialUs = 0;
  double modeledFullFps = 0.0;
  double modeledPartialFps = 0.0;
};

struct DisplayRect {
  int x = 0;
  int y = 0;
  int w = 0;
  int h = 0;
};

class DisplayRgb565 {
 public:
  static constexpr int kMaxDirtyRects = 8;

  bool init(const Rgb565Config& config);
  bool attachFramebuffer(uint16_t* framebuffer);
  uint16_t* framebuffer() { return framebuffer_; }
  const uint16_t* framebuffer() const { return framebuffer_; }
  const Rgb565Config& config() const { return config_; }
  const Rgb565Metrics& metrics() const { return metrics_; }

  void clear(uint16_t color);
  void fillRect(int x, int y, int w, int h, uint16_t color);

  // Dirty-rect bookkeeping (bounded, allocation-free).
  void beginFrame();
  bool addDirtyRect(int x, int y, int w, int h);
  int dirtyRectCount() const { return dirtyCount_; }
  const DisplayRect& dirtyRect(int index) const { return dirty_[index]; }

  // Host simulation of the P4 flush: advances metrics only, no hardware.
  // Returns the modelled microseconds of the strip.
  uint32_t flushRows(int startRow, int rows);
  uint32_t flushFull();
  uint32_t flushPartial(const DisplayRect& rect);
  void hostSimulateFrame(bool full);

  uint32_t modeledFullFrameUs() const;
  uint32_t modeledPartialFrameUs(int pixels) const;
  uint64_t checksum() const;
  static const char* backendName();

 private:
  Rgb565Config config_{};
  uint16_t* framebuffer_ = nullptr;
  Rgb565Metrics metrics_{};
  DisplayRect dirty_[kMaxDirtyRects] = {};
  int dirtyCount_ = 0;
};

}  // namespace hal
}  // namespace bukifon
