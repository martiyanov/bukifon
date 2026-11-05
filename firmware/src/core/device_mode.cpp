// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/device_mode.hpp"

#include <cstddef>

namespace bukifon {
namespace {

const char* kNames[] = {"SYNTH", "SAMPLER", "DAW", "USB-KBD"};
const char* kShortNames[] = {"SYN", "SMP", "DAW", "KBD"};

static_assert(sizeof(kNames) / sizeof(kNames[0]) == static_cast<size_t>(DeviceMode::kNumModes),
              "device mode name table out of sync");

}  // namespace

const char* deviceModeName(DeviceMode mode) {
  const int index = static_cast<int>(mode);
  if (index < 0 || index >= static_cast<int>(DeviceMode::kNumModes)) return "?";
  return kNames[index];
}

const char* deviceModeShortName(DeviceMode mode) {
  const int index = static_cast<int>(mode);
  if (index < 0 || index >= static_cast<int>(DeviceMode::kNumModes)) return "?";
  return kShortNames[index];
}

void DeviceModeManager::init(DeviceMode initial) {
  mode_ = initial;
  switches_ = 0;
  for (int i = 0; i < static_cast<int>(DeviceMode::kNumModes); ++i) enterCount_[i] = 0;
  enterCount_[static_cast<int>(mode_)] = 1;
}

bool DeviceModeManager::setMode(DeviceMode mode) {
  if (static_cast<unsigned>(mode) >= static_cast<unsigned>(DeviceMode::kNumModes)) {
    return false;
  }
  ++switches_;
  const bool changed = mode != mode_;
  mode_ = mode;
  ++enterCount_[static_cast<int>(mode_)];
  return changed;
}

DeviceMode DeviceModeManager::nextMode() const {
  const int next = (static_cast<int>(mode_) + 1) % static_cast<int>(DeviceMode::kNumModes);
  return static_cast<DeviceMode>(next);
}

bool DeviceModeManager::setNextMode() { return setMode(nextMode()); }

uint32_t DeviceModeManager::modeEnterCount(DeviceMode mode) const {
  const int index = static_cast<int>(mode);
  if (index < 0 || index >= static_cast<int>(DeviceMode::kNumModes)) return 0;
  return enterCount_[index];
}

bool DeviceModeManager::usesUsbMidi(DeviceMode mode) {
  return mode == DeviceMode::Synth || mode == DeviceMode::Sampler ||
         mode == DeviceMode::DawController || mode == DeviceMode::UsbKeyboard;
}

bool DeviceModeManager::usesHidKeyboard(DeviceMode mode) {
  return mode == DeviceMode::UsbKeyboard || mode == DeviceMode::DawController;
}

bool DeviceModeManager::usesDawCc(DeviceMode mode) { return mode == DeviceMode::DawController; }

bool DeviceModeManager::usesSampler(DeviceMode mode) { return mode == DeviceMode::Sampler; }

}  // namespace bukifon
