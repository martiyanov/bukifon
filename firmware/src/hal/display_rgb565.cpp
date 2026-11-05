// SPDX-License-Identifier: GPL-3.0-or-later
#include "hal/display_rgb565.hpp"

#include <cstring>

namespace bukifon {
namespace hal {
namespace {
constexpr int kBytesPerPixel = 2;
}

bool DisplayRgb565::init(const Rgb565Config& config) {
  if (config.width <= 0 || config.height <= 0 || config.pixelClockHz == 0 ||
      config.bounceRows <= 0 || config.bounceRows > 16) {
    return false;
  }
  config_ = config;
  metrics_ = Rgb565Metrics{};
  dirtyCount_ = 0;
  // TODO(hw): esp_lcd_new_rgb_panel / DSI bus + PPA/DMA2D flush + bounce buffers
  // in internal SRAM.  Host: framebuffer must be attached by the caller.
  metrics_.modeledFullFps = static_cast<double>(config_.pixelClockHz) /
                            (static_cast<double>(config_.width) * config_.height);
  metrics_.modeledPartialFps = metrics_.modeledFullFps * 2.5;  // ~40% dirty area
  return true;
}

bool DisplayRgb565::attachFramebuffer(uint16_t* framebuffer) {
  if (!framebuffer) return false;
  framebuffer_ = framebuffer;
  return true;
}

void DisplayRgb565::clear(uint16_t color) {
  if (!framebuffer_) return;
  const size_t count = static_cast<size_t>(config_.width) * config_.height;
  for (size_t i = 0; i < count; ++i) framebuffer_[i] = color;
}

void DisplayRgb565::fillRect(int x, int y, int w, int h, uint16_t color) {
  if (!framebuffer_) return;
  for (int row = y; row < y + h && row < config_.height; ++row) {
    if (row < 0) continue;
    for (int col = x; col < x + w && col < config_.width; ++col) {
      if (col < 0) continue;
      framebuffer_[row * config_.width + col] = color;
    }
  }
}

void DisplayRgb565::beginFrame() { dirtyCount_ = 0; }

bool DisplayRgb565::addDirtyRect(int x, int y, int w, int h) {
  if (dirtyCount_ >= kMaxDirtyRects || w <= 0 || h <= 0) {
    ++metrics_.droppedBands;
    return false;
  }
  if (x < 0) { w += x; x = 0; }
  if (y < 0) { h += y; y = 0; }
  if (x + w > config_.width) w = config_.width - x;
  if (y + h > config_.height) h = config_.height - y;
  if (w <= 0 || h <= 0) {
    ++metrics_.droppedBands;
    return false;
  }
  dirty_[dirtyCount_++] = DisplayRect{x, y, w, h};
  return true;
}

uint32_t DisplayRgb565::flushRows(int startRow, int rows) {
  if (!framebuffer_ || startRow < 0 || rows <= 0) return 0;
  int count = rows;
  if (startRow + count > config_.height) count = config_.height - startRow;
  if (count <= 0) return 0;
  // TODO(hw): copy rows to internal-SRAM bounce buffer and start an esp_lcd
  // async flush (DMA).  Returns immediately after queuing there.
  const uint32_t bytes = static_cast<uint32_t>(count) * config_.width * kBytesPerPixel;
  const uint32_t pixels = static_cast<uint32_t>(count) * config_.width;
  const uint32_t us = static_cast<uint32_t>(
      (static_cast<double>(pixels) * 1000000.0) / config_.pixelClockHz);
  metrics_.bytesFlushed += bytes;
  return us;
}

uint32_t DisplayRgb565::flushFull() {
  uint32_t totalUs = 0;
  for (int row = 0; row < config_.height; row += config_.bounceRows) {
    totalUs += flushRows(row, config_.bounceRows);
  }
  ++metrics_.fullFrames;
  metrics_.lastFullUs = totalUs;
  return totalUs;
}

uint32_t DisplayRgb565::flushPartial(const DisplayRect& rect) {
  if (!framebuffer_ || rect.w <= 0 || rect.h <= 0) return 0;
  uint32_t totalUs = 0;
  for (int row = rect.y; row < rect.y + rect.h; row += config_.bounceRows) {
    totalUs += flushRows(row, config_.bounceRows);
  }
  ++metrics_.partialUpdates;
  metrics_.lastPartialUs = totalUs;
  return totalUs;
}

void DisplayRgb565::hostSimulateFrame(bool full) {
  if (full) {
    flushFull();
  } else {
    for (int i = 0; i < dirtyCount_; ++i) flushPartial(dirty_[i]);
    beginFrame();
  }
  const uint32_t fullUs = modeledFullFrameUs();
  metrics_.modeledFullFps =
      fullUs > 0 ? 1000000.0 / static_cast<double>(fullUs) : 0.0;
  metrics_.modeledPartialFps = metrics_.modeledFullFps * 2.5;
}

uint32_t DisplayRgb565::modeledFullFrameUs() const {
  const double pixels = static_cast<double>(config_.width) * config_.height;
  return static_cast<uint32_t>((pixels * 1000000.0) / config_.pixelClockHz);
}

uint32_t DisplayRgb565::modeledPartialFrameUs(int pixels) const {
  if (pixels <= 0) return 0;
  return static_cast<uint32_t>((static_cast<double>(pixels) * 1000000.0) / config_.pixelClockHz);
}

uint64_t DisplayRgb565::checksum() const {
  if (!framebuffer_) return 0;
  uint64_t hash = 1469598103934665603ull;
  for (int y = 0; y < config_.height; y += 7) {
    for (int x = 0; x < config_.width; x += 7) {
      hash ^= framebuffer_[y * config_.width + x];
      hash *= 1099511628211ull;
    }
  }
  return hash;
}

const char* DisplayRgb565::backendName() { return "rgb565 host-sim (accel: TODO esp_lcd)"; }

}  // namespace hal
}  // namespace bukifon
