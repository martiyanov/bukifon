// SPDX-License-Identifier: GPL-3.0-or-later
// Example module: generative Euclid arpeggiator (control/sequencer). SDK v0.2.
#pragma once
#include <cstdint>
#include <cstring>

#include "io/gen.hpp"

namespace bukifon {
namespace examples {

class EuclidArpModel {
 public:
  void init(uint32_t seed = 1) {
    params_ = GenParams{};
    params_.seed = seed;
    params_.euclid = 5;
    params_.arpOn = true;
    params_.arpRate = GenArpRate16;
    params_.arpMode = GenArpUp;
    mask_ = genEuclidMask(params_.euclid, 16);
    arp_.setParams(params_.arpRate, params_.arpMode);
  }
  void setEuclid(uint8_t density) {
    params_.euclid = density > 16 ? 16 : density;
    mask_ = genEuclidMask(params_.euclid, 16);
  }
  void setSeed(uint32_t seed) { params_.seed = seed; }
  uint16_t mask() const { return mask_; }
  bool triggerAt(int step) const { return step >= 0 && step < 16 && ((mask_ >> step) & 1u) != 0; }
  int renderBar(uint8_t* steps, uint8_t* velocities, int* count) {
    if (!steps || !velocities) return 0;
    int n = 0;
    for (int step = 0; step < 16; ++step) {
      if (!triggerAt(step)) continue;
      steps[n] = static_cast<uint8_t>(step);
      const int velocity = 64 + static_cast<int>(genHash(params_.seed, 0, step) % 64u);
      velocities[n] = static_cast<uint8_t>(velocity);
      ++n;
    }
    if (count) *count = n;
    return n;
  }
  int noteForStep(const uint8_t* held, int heldCount, int tick32) const {
    return arp_.noteAt(held, heldCount, static_cast<uint32_t>(tick32));
  }

 private:
  GenParams params_{};
  GenArp arp_{};
  uint16_t mask_ = 0;
};

}  // namespace examples
}  // namespace bukifon
