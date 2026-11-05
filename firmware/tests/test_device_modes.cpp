// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstring>
#include <string>
#include <vector>

#include "core/device_mode.hpp"
#include "sim/simulator.hpp"
#include "test_framework.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;
using namespace bukifon::sim;

namespace {

class ModeCanvas : public ui::Framebuffer800 {
 public:
  void drawText(int x, int y, const char* text, uint16_t color, uint16_t bg = 0xFFFF) override {
    texts.emplace_back(text ? text : "");
    ui::Framebuffer800::drawText(x, y, text, color, bg);
  }
  bool has(const char* needle) const {
    for (const auto& t : texts) {
      if (t.find(needle) != std::string::npos) return true;
    }
    return false;
  }
  std::vector<std::string> texts;
};

}  // namespace

TEST(DeviceModeSwitching) {
  CHECK(std::strcmp(deviceModeName(DeviceMode::Synth), "SYNTH") == 0);
  CHECK(std::strcmp(deviceModeName(DeviceMode::DawController), "DAW") == 0);
  CHECK(std::strcmp(deviceModeShortName(DeviceMode::UsbKeyboard), "KBD") == 0);
  DeviceModeManager manager;
  manager.init(DeviceMode::Synth);
  CHECK(manager.mode() == DeviceMode::Synth);
  CHECK(manager.modeEnterCount(DeviceMode::Synth) == 1);
  CHECK(manager.setMode(DeviceMode::DawController));
  CHECK(manager.mode() == DeviceMode::DawController);
  CHECK(manager.switchCount() == 1);
  CHECK(!manager.setMode(DeviceMode::DawController));  // already there
  CHECK(manager.switchCount() == 2);
  CHECK(manager.setNextMode());
  CHECK(manager.mode() == DeviceMode::UsbKeyboard);
  CHECK(manager.setNextMode());  // wraps to Synth
  CHECK(manager.mode() == DeviceMode::Synth);
  CHECK(manager.modeEnterCount(DeviceMode::Synth) == 2);
  CHECK(manager.nextMode() == DeviceMode::Sampler);
  // Capability matrix.
  CHECK(DeviceModeManager::usesUsbMidi(DeviceMode::Synth));
  CHECK(DeviceModeManager::usesHidKeyboard(DeviceMode::UsbKeyboard));
  CHECK(DeviceModeManager::usesHidKeyboard(DeviceMode::DawController));
  CHECK(!DeviceModeManager::usesHidKeyboard(DeviceMode::Synth));
  CHECK(DeviceModeManager::usesDawCc(DeviceMode::DawController));
  CHECK(DeviceModeManager::usesSampler(DeviceMode::Sampler));
  INFO("device modes: 4 modes, switching without reboot, capability matrix OK");
}

TEST(DeviceModeInSimulatorNoReboot) {
  Simulator sim;
  sim.init();
  sim.buildDemoPattern();
  sim.play();
  sim.runSamples(1000);
  const uint64_t frameBefore = sim.frame();
  const int voicesBefore = sim.engine().activeVoices();
  CHECK(std::strcmp(sim.snapshot(ui::Screen::Main).deviceMode, "SYN") == 0);
  CHECK(sim.setDeviceMode(DeviceMode::DawController));
  CHECK(sim.deviceMode() == DeviceMode::DawController);
  CHECK(sim.frame() == frameBefore);  // no reboot / no time reset
  CHECK(sim.engine().activeVoices() == voicesBefore);
  const ui::UiSnapshot snapshot = sim.snapshot(ui::Screen::Main);
  CHECK(std::strcmp(snapshot.deviceMode, "DAW") == 0);
  sim.setDeviceMode(DeviceMode::UsbKeyboard);
  CHECK(std::strcmp(sim.snapshot(ui::Screen::Main).deviceMode, "KBD") == 0);
  CHECK(!sim.setDeviceMode(DeviceMode::UsbKeyboard));  // no change
  INFO("device mode in simulator: frame=%llu preserved across two mode switches",
       static_cast<unsigned long long>(sim.frame()));
}

TEST(DeviceModeUiIndicator) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  std::snprintf(snapshot.deviceMode, sizeof(snapshot.deviceMode), "DAW");
  ModeCanvas canvas;
  ui::drawUi800(canvas, snapshot);
  CHECK(canvas.has("MODE DAW"));
  std::snprintf(snapshot.deviceMode, sizeof(snapshot.deviceMode), "KBD");
  ModeCanvas canvas2;
  ui::drawUi800(canvas2, snapshot);
  CHECK(canvas2.has("MODE KBD"));
  ui::UiSnapshot demo;
  ui::uiSnapshotDemo(&demo, ui::Screen::Mixer);
  ModeCanvas canvas3;
  ui::drawUi800(canvas3, demo);
  CHECK(canvas3.has("MODE SYNTH"));
  INFO("UI: device mode indicator rendered for DAW/KBD/SYNTH");
}
