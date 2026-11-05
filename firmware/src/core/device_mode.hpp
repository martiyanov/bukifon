// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon device modes — switching without a reboot.
//
// v0.5 adds the "computer controller" side: the same hardware can act as a
// synth, a sampler, a DAW controller or a USB keyboard.  The mode is a plain
// runtime state: the engine/UI/USB layers observe it; switching never resets
// the audio engine or reboots.
#pragma once

#include <cstdint>

namespace bukifon {

enum class DeviceMode : uint8_t {
  Synth = 0,
  Sampler,
  DawController,
  UsbKeyboard,
  kNumModes
};

const char* deviceModeName(DeviceMode mode);
const char* deviceModeShortName(DeviceMode mode);

class DeviceModeManager {
 public:
  void init(DeviceMode initial = DeviceMode::Synth);

  // Returns true when the mode actually changed.  No reboot, no engine reset.
  bool setMode(DeviceMode mode);
  DeviceMode mode() const { return mode_; }
  DeviceMode nextMode() const;
  bool setNextMode();

  uint32_t switchCount() const { return switches_; }
  uint32_t modeEnterCount(DeviceMode mode) const;

  // Capability matrix used by the UI and the host/device control loops.
  static bool usesUsbMidi(DeviceMode mode);
  static bool usesHidKeyboard(DeviceMode mode);
  static bool usesDawCc(DeviceMode mode);
  static bool usesSampler(DeviceMode mode);

 private:
  DeviceMode mode_ = DeviceMode::Synth;
  uint32_t switches_ = 0;
  uint32_t enterCount_[static_cast<int>(DeviceMode::kNumModes)] = {};
};

}  // namespace bukifon
