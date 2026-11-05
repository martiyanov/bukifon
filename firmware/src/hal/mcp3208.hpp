// SPDX-License-Identifier: GPL-3.0-or-later
// MCP3208 8-channel 12-bit SPI ADC.
//
// CH0/CH1 = sliders SL1/SL2, CH2/CH3 = CV IN 1/2 jacks, CH4/CH5 = CV IN 3/4 bus,
// CH6 = FSR / velocity multiplexer, CH7 = SYS_MON (unused after pin map update).
// HARDWARE STATUS: not verified on real silicon (single-ended read protocol).
#pragma once

#include <cstdint>

#include "hal/pinmap.hpp"

#if defined(ARDUINO)
#include <SPI.h>
#endif

namespace bukifon {
namespace hal {

class Mcp3208 {
 public:
  bool begin() {
#if defined(ARDUINO)
    pinMode(pins::kMcp3208Cs, OUTPUT);
    digitalWrite(pins::kMcp3208Cs, HIGH);
    SPI.begin();
    SPI.beginTransaction(SPISettings(pins::kSpiClockHz, MSBFIRST, SPI_MODE0));
    ready_ = true;
#endif
    return true;
  }

  // Single-ended read: returns 0..4095 (0xFFFF on failure).
  uint16_t read(uint8_t channel) {
    if (channel > 7) return 0xFFFF;
#if defined(ARDUINO)
    if (!ready_) begin();
    digitalWrite(pins::kMcp3208Cs, LOW);
    SPI.transfer(static_cast<uint8_t>(0x06 | ((channel & 0x07) >> 2)));  // start, single-ended
    const uint8_t hi = SPI.transfer(static_cast<uint8_t>((channel & 0x03) << 6));
    const uint8_t lo = SPI.transfer(0x00);
    digitalWrite(pins::kMcp3208Cs, HIGH);
    const uint16_t value = static_cast<uint16_t>(((hi & 0x0F) << 8) | lo);
    last_[channel & 7] = value;
    return value;
#else
    last_[channel] = 0;
    return 0;
#endif
  }

  // Slider helper with 4-sample moving average and 2 LSB dead-zone (spec §4).
  uint16_t readSlider(uint8_t channel) {
    const uint16_t raw = read(channel);
    sliderAcc_[channel & 1] = static_cast<uint16_t>(sliderAcc_[channel & 1] - sliderHist_[channel & 1][sliderPos_[channel & 1]] + raw);
    sliderHist_[channel & 1][sliderPos_[channel & 1]] = raw;
    sliderPos_[channel & 1] = static_cast<uint8_t>((sliderPos_[channel & 1] + 1) & 3);
    const uint16_t avg = static_cast<uint16_t>(sliderAcc_[channel & 1] / 4);
    const int16_t delta = static_cast<int16_t>(avg) - static_cast<int16_t>(sliderLast_[channel & 1]);
    if (delta > 1 || delta < -1) sliderLast_[channel & 1] = avg;
    return sliderLast_[channel & 1];
  }

  uint16_t last(uint8_t channel) const { return last_[channel & 7]; }

 private:
  bool ready_ = false;
  uint16_t last_[8] = {};
  uint16_t sliderHist_[2][4] = {};
  uint16_t sliderAcc_[2] = {};
  uint16_t sliderLast_[2] = {};
  uint8_t sliderPos_[2] = {};
};

}  // namespace hal
}  // namespace bukifon
