// SPDX-License-Identifier: GPL-3.0-or-later
// CV I/O: MCP4728 4-point calibration, MCP3208 input scaling, 1V/oct quantiser.
#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

struct CalPoint {
  float volts = 0.0f;
  uint16_t code = 0;
};

// 4-point calibration per CV output channel (0/25/50/100 % in EEPROM 24C32).
class CvCalibration {
 public:
  static constexpr int kPoints = 4;
  using Channel = CalPoint[kPoints];

  void reset();
  void setPoint(int channel, int index, float volts, uint16_t code);
  const CalPoint& point(int channel, int index) const;
  uint16_t codeForVolts(int channel, float volts) const;
  float voltsForCode(int channel, uint16_t code) const;
  // Serialised block: 4 channels x 4 points x (int16 millivolts, uint16 code) + CRC.
  static constexpr size_t kSerializedBytes = 4 * 4 * 4 + 2;
  size_t serialize(uint8_t* out, size_t capacity) const;
  bool deserialize(const uint8_t* data, size_t length);

 private:
  static float interpolateCode(const Channel& ch, float volts);
  static float interpolateVolts(const Channel& ch, uint16_t code);
  CalPoint channels_[kNumCvOut][kPoints] = {};
};

// MCP3208 CV input channel: 0..4095 raw -> volts with filtering.
class CvInput {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  // Input hardware: +/-10 V maps to 0..Vref through the divider; default 20 V FS.
  void setRange(float negativeVolts, float positiveVolts) {
    negativeVolts_ = negativeVolts;
    positiveVolts_ = positiveVolts;
  }
  float update(uint16_t raw);
  float lastVolts() const { return volts_; }
  static float quantize1VOct(float volts) { return std::round(volts * 12.0f) / 12.0f; }
  static int semitonesFromVolts(float volts) {
    return static_cast<int>(std::lround(volts * 12.0f));
  }

 private:
  float sampleRate_ = static_cast<float>(kSampleRate);
  float negativeVolts_ = -10.0f;
  float positiveVolts_ = 10.0f;
  float volts_ = 0.0f;
  float coef_ = 0.1f;
  bool primed_ = false;
};

}  // namespace bukifon
