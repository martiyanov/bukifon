// SPDX-License-Identifier: GPL-3.0-or-later
// Allocation probe for the "no allocation in the audio path" test.
//
// Replaces global operator new/delete in the bench/test executables.  While the
// probe is active every allocation is counted (it does not fail the allocation).
// The audio-path test arms it around processBlock() calls and expects zero.
#pragma once

#include <cstdint>

namespace bukifon {
namespace bench {

void allocProbeBegin();
void allocProbeEnd();
uint64_t allocProbeCount();
void allocProbeReset();

}  // namespace bench
}  // namespace bukifon
