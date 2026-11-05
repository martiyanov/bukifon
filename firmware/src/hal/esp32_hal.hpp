// SPDX-License-Identifier: GPL-3.0-or-later
// ESP32-P4 / S3 hardware adapter skeleton.
//
// Everything here is compile-safe on both the host and arduino-esp32.  The real
// panel/I2S/USB/radio initialisation is TODO(hw): v0.5 ships only the host
// demo; this file exists so the device build has a single HAL seam and does not
// depend on ESP-IDF-specific code anywhere else.
#pragma once

#include <cstdint>

#include "ui/canvas.hpp"

namespace bukifon {
namespace ui {
class Framebuffer800;
}  // namespace ui
namespace hal {

class Esp32Hal {
 public:
  bool begin() {
    // TODO(hw): RGB/DSI panel init (800x480), I2S codec, MCP23017/3208 via
    // I2C/SPI, USB composite descriptors from usb/usb_descriptors.cpp, NimBLE
    // (S3) / ESP32-C6 coprocessor bridge (P4).  Returns true so the UI shell can
    // still run on a bare devkit.
    initialized_ = true;
    return true;
  }

  bool initialized() const { return initialized_; }

  // Pushes the rendered framebuffer to the panel (TODO(hw): DMA2D/RGB).
  void present(ui::Framebuffer800& framebuffer) {
    (void)framebuffer;
    // TODO(hw): RGB/DSI flush, target 30 fps at 800x480 RGB565.
  }

  // 1 kHz control tick (encoders/deck/MIDI).  TODO(hw): real drivers.
  void tick(uint32_t micros) {
    (void)micros;
    ++tickCount_;
  }

  uint32_t tickCount() const { return tickCount_; }

  const char* platformName() const {
#if defined(BUKIFON_ESP32_P4)
    return "ESP32-P4";
#elif defined(BUKIFON_ESP32_S3)
    return "ESP32-S3";
#else
    return "host";
#endif
  }

 private:
  bool initialized_ = false;
  uint32_t tickCount_ = 0;
};

}  // namespace hal
}  // namespace bukifon
