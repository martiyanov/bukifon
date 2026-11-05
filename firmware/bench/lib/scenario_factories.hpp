// SPDX-License-Identifier: GPL-3.0-or-later
// Scenario factories for the benchmark registry.
#pragma once

#include "bench_types.hpp"

namespace bukifon {
namespace bench {

IScenario* createFmVoiceScenario();
IScenario* createGranularTrackScenario();
IScenario* createMixBusScenario();
IScenario* createPsramStreamScenario();
IScenario* createUiFrameScenario(bool partial);
IScenario* createUsbDescriptorScenario();

}  // namespace bench
}  // namespace bukifon
