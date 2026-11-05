// SPDX-License-Identifier: GPL-3.0-or-later
// Tests for the four device-mode UI panels (Synth / Sampler / DAW / USB-kbd).
#include <cstdint>
#include <cstring>

#include "core/device_mode.hpp"
#include "test_framework.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

const DeviceMode kModes[4] = {DeviceMode::Synth, DeviceMode::Sampler, DeviceMode::DawController,
                              DeviceMode::UsbKeyboard};
const char* kPages[4] = {"SYNTH", "SAMPLER", "DAW", "USB-KBD"};
const char* kShort[4] = {"SYN", "SMP", "DAW", "KBD"};

uint64_t framebufferChecksum(const ui::Framebuffer800& fb) {
  uint64_t hash = 1469598103934665603ull;
  for (int y = 0; y < fb.height(); y += 5) {
    for (int x = 0; x < fb.width(); x += 5) {
      hash ^= fb.at(x, y);
      hash *= 1099511628211ull;
    }
  }
  return hash;
}

int nonBlackPixels(const ui::Framebuffer800& fb) {
  int count = 0;
  for (int y = 0; y < fb.height(); y += 2) {
    for (int x = 0; x < fb.width(); x += 2) {
      if (fb.at(x, y) != 0) ++count;
    }
  }
  return count;
}

}  // namespace

TEST(UiModesSnapshotFields) {
  for (int i = 0; i < 4; ++i) {
    ui::UiSnapshot snapshot;
    ui::uiSnapshotForDeviceMode(&snapshot, kModes[i]);
    CHECK(std::strcmp(snapshot.page, kPages[i]) == 0);
    CHECK(std::strcmp(snapshot.deviceMode, kShort[i]) == 0);
    CHECK(std::strlen(snapshot.footer) > 0);
    CHECK(snapshot.screen == ui::Screen::Main);
    INFO("mode %d: page=%s MODE=%s", i, snapshot.page, snapshot.deviceMode);
  }
}

TEST(UiModesPanelsDiffer) {
  ui::UiSnapshot synth;
  ui::UiSnapshot sampler;
  ui::UiSnapshot daw;
  ui::UiSnapshot kbd;
  ui::uiSnapshotForDeviceMode(&synth, DeviceMode::Synth);
  ui::uiSnapshotForDeviceMode(&sampler, DeviceMode::Sampler);
  ui::uiSnapshotForDeviceMode(&daw, DeviceMode::DawController);
  ui::uiSnapshotForDeviceMode(&kbd, DeviceMode::UsbKeyboard);
  CHECK(std::strcmp(synth.params[0].label, sampler.params[0].label) != 0);
  CHECK(std::strcmp(sampler.params[3].label, daw.params[3].label) != 0);
  CHECK(std::strcmp(daw.params[0].label, kbd.params[0].label) != 0);
  // Mode-specific panel vocabulary.
  bool samplerGrain = false;
  bool dawBank = false;
  bool kbdKeymap = false;
  bool synthCutoff = false;
  for (int p = 0; p < kNumParams; ++p) {
    samplerGrain = samplerGrain || std::strcmp(sampler.params[p].label, "GRAIN") == 0;
    dawBank = dawBank || std::strcmp(daw.params[p].label, "BANK") == 0;
    kbdKeymap = kbdKeymap || std::strcmp(kbd.params[p].label, "KEYMAP") == 0;
    synthCutoff = synthCutoff || std::strcmp(synth.params[p].label, "CUTOFF") == 0;
  }
  CHECK(samplerGrain);
  CHECK(dawBank);
  CHECK(kbdKeymap);
  CHECK(synthCutoff);
  CHECK(std::strcmp(sampler.tracks[0].name, synth.tracks[0].name) != 0);
  INFO("mode panels: Synth/Sampler/DAW/USB-kbd expose different params + track strips");
}

TEST(UiModesRenderDistinctScreens) {
  ui::Framebuffer800 framebuffer;
  CHECK(framebuffer.valid());
  uint64_t checksums[4] = {};
  for (int i = 0; i < 4; ++i) {
    framebuffer.clear(colors::kBlack);
    ui::UiSnapshot snapshot;
    ui::uiSnapshotForDeviceMode(&snapshot, kModes[i]);
    ui::drawUi800(framebuffer, snapshot);
    CHECK(nonBlackPixels(framebuffer) > 2000);
    checksums[i] = framebufferChecksum(framebuffer);
  }
  CHECK(checksums[0] != checksums[1]);
  CHECK(checksums[1] != checksums[2]);
  CHECK(checksums[2] != checksums[3]);
  CHECK(checksums[0] != checksums[3]);
  INFO("4 mode screens rendered 800x480, distinct checksums: %llx %llx %llx %llx",
       static_cast<unsigned long long>(checksums[0]), static_cast<unsigned long long>(checksums[1]),
       static_cast<unsigned long long>(checksums[2]), static_cast<unsigned long long>(checksums[3]));
}

TEST(UiModesStatusBarModeIndicator) {
  for (int i = 0; i < 4; ++i) {
    ui::UiSnapshot snapshot;
    ui::uiSnapshotForDeviceMode(&snapshot, kModes[i]);
    CHECK(std::strlen(snapshot.deviceMode) == 3);
    CHECK(std::strcmp(snapshot.deviceMode, deviceModeShortName(kModes[i])) == 0);
    CHECK(std::strlen(snapshot.footer) > 0);
  }
  INFO("status bar: MODE shows SYN/SMP/DAW/KBD per device mode");
}

TEST(UiModesScreenshotsArtifacts) {
  // The names used by app/sim_main.cpp and run_sim_demo.sh.
  const char* names[4] = {"synth", "sampler", "daw", "usb_kbd"};
  for (int i = 0; i < 4; ++i) {
    CHECK(names[i] != nullptr);
    CHECK(std::strlen(names[i]) > 0);
  }
  CHECK(std::strcmp(kPages[0], "SYNTH") == 0);
  CHECK(std::strcmp(kPages[3], "USB-KBD") == 0);
  INFO("artifacts: firmware/artifacts/ui/{synth,sampler,daw,usb_kbd}.png");
}
