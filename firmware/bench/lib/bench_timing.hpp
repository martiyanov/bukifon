// SPDX-License-Identifier: GPL-3.0-or-later
// Time source abstraction: host = steady_clock (ns), device = micros() (us).
#pragma once

#include <cstdint>

namespace bukifon {
namespace bench {

// Monotonic timestamp in nanoseconds.  On devices without a ns source this is
// micros()*1000 (1 us resolution is enough for ~0.3-1.3 ms blocks; the report
// states this limitation).
uint64_t nowNs();

// Converts a ns delta to microseconds.
double nsToUs(uint64_t deltaNs);

}  // namespace bench
}  // namespace bukifon
