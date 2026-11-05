// SPDX-License-Identifier: GPL-3.0-or-later
// Static scenario registry.  Names are part of the frozen workload contract and
// must match docs/05-benchmark-workload.md.
#include <cstring>

#include "scenario_factories.hpp"

namespace bukifon {
namespace bench {
namespace {

struct Entry {
  const char* name;
  IScenario* (*create)();
};

const Entry kEntries[] = {
    {"fm_voice", createFmVoiceScenario},
    {"granular_track", createGranularTrackScenario},
    {"mix_bus", createMixBusScenario},
    {"psram_stream", createPsramStreamScenario},
    {"ui_frame", []() -> IScenario* { return createUiFrameScenario(false); }},
    {"ui_frame_partial", []() -> IScenario* { return createUiFrameScenario(true); }},
    {"usb_descriptor", createUsbDescriptorScenario},
    {"s3_profile", createS3ProfileScenario},
    {"p4_profile", createP4ProfileScenario},
};

constexpr int kCount = static_cast<int>(sizeof(kEntries) / sizeof(kEntries[0]));

}  // namespace

int scenarioCount() { return kCount; }

const char* scenarioNameAt(int index) {
  if (index < 0 || index >= kCount) return "";
  return kEntries[index].name;
}

IScenario* createScenario(const char* name) {
  if (!name) return nullptr;
  for (int i = 0; i < kCount; ++i) {
    if (std::strcmp(kEntries[i].name, name) == 0) return kEntries[i].create();
  }
  return nullptr;
}

}  // namespace bench
}  // namespace bukifon
