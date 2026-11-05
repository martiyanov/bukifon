// SPDX-License-Identifier: GPL-3.0-or-later
// EC11 quadrature decoding with speed-dependent acceleration (1/2/4/8 steps).
#pragma once

#include <cstdint>

namespace bukifon {

class Encoder {
 public:
  void init(bool acceleration = true) {
    reset();
    acceleration_ = acceleration;
  }

  // One detent = 4 valid quadrature transitions (00->01->11->10).
  int feed(uint8_t ab, uint32_t nowUs) {
    ab &= 0x03;
    const uint8_t idx = static_cast<uint8_t>((prev_ << 2) | ab);
    static const int8_t kTable[16] = {0, 1, -1, 0, -1, 0, 0, 1, 1, 0, 0, -1, 0, -1, 1, 0};
    const int8_t step = kTable[idx];
    prev_ = ab;
    if (step != 0) {
      accum_ += step;
      if (accum_ >= 4) {
        accum_ -= 4;
        ++delta_;
        lastDelta_ = nowUs - lastDetentUs_;
        lastDetentUs_ = nowUs;
      } else if (accum_ <= -4) {
        accum_ += 4;
        --delta_;
        lastDelta_ = nowUs - lastDetentUs_;
        lastDetentUs_ = nowUs;
      }
    }
    return delta_;
  }

  int takeDelta() {
    const int d = delta_;
    delta_ = 0;
    if (!acceleration_ || d == 0) return d;
    // Acceleration based on the time between two detents.
    const uint32_t dt = lastDelta_;
    if (dt < 8000u) return d * 8;
    if (dt < 20000u) return d * 4;
    if (dt < 50000u) return d * 2;
    return d;
  }

  void reset() {
    prev_ = 0;
    accum_ = 0;
    delta_ = 0;
    lastDetentUs_ = 0;
    lastDelta_ = 0;
  }

 private:
  uint8_t prev_ = 0;
  int accum_ = 0;
  int delta_ = 0;
  bool acceleration_ = true;
  uint32_t lastDetentUs_ = 0;
  uint32_t lastDelta_ = 0;
};

}  // namespace bukifon
