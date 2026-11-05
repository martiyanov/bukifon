// SPDX-License-Identifier: GPL-3.0-or-later
#include "bench_timing.hpp"

#if defined(ARDUINO)
#include <Arduino.h>
#else
#include <chrono>
#endif

namespace bukifon {
namespace bench {

uint64_t nowNs() {
#if defined(ARDUINO)
  return static_cast<uint64_t>(micros()) * 1000ull;
#else
  return static_cast<uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(
          std::chrono::steady_clock::now().time_since_epoch())
          .count());
#endif
}

double nsToUs(uint64_t deltaNs) { return static_cast<double>(deltaNs) / 1000.0; }

}  // namespace bench
}  // namespace bukifon
