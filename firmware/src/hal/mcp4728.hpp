// SPDX-License-Identifier: GPL-3.0-or-later
// MCP4728 quad 12-bit I2C DAC (CV outputs 1..4, 0..10 V after the TL074 x4.883).
//
// Channel map: A/B = CV1/CV2 (bus), C/D = CV OUT 1/2 jacks.
// Calibration is applied by the caller (io/cv.hpp CvCalibration).
// HARDWARE STATUS: not verified on real silicon; register sequence follows the
// MCP4728 datasheet "Write DAC Register" command.
#pragma once

#include <cstdint>

#include "hal/pinmap.hpp"

#if defined(ARDUINO)
#include <Wire.h>
#endif

namespace bukifon {
namespace hal {

class Mcp4728 {
 public:
  bool begin() {
#if defined(ARDUINO)
    Wire.begin();
    return true;
#else
    return false;
#endif
  }

  // code = 12-bit value; updates one channel (0=A..3=D).
  bool setChannel(uint8_t channel, uint16_t code) {
    if (channel > 3) return false;
    code &= 0x0FFF;
#if defined(ARDUINO)
    Wire.beginTransmission(pins::kMcp4728Address);
    Wire.write(static_cast<uint8_t>(0x40 | (channel << 1)));  // Write DAC register, channel
    Wire.write(static_cast<uint8_t>((code >> 8) & 0x0F));
    Wire.write(static_cast<uint8_t>(code & 0xFF));
    return Wire.endTransmission() == 0;
#else
    lastCode_[channel] = code;
    return true;
#endif
  }

  // Fast 4-channel update (1 kHz control loop).
  bool updateAll(const uint16_t codes[4]) {
    bool ok = true;
    for (uint8_t ch = 0; ch < 4; ++ch) ok = setChannel(ch, codes[ch]) && ok;
    return ok;
  }

  uint16_t lastCode(uint8_t channel) const { return lastCode_[channel & 3]; }

 private:
  uint16_t lastCode_[4] = {};
};

}  // namespace hal
}  // namespace bukifon
