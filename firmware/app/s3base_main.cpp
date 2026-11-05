// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon S3-base firmware skeleton (ESP32-S3-WROOM-1-N16R8, CORE-S3).
//
// Uses the CORE-S3 board HAL (hardware/cores3/pinmap.csv), the portable engine,
// the 800x480 UI shell and device modes.  The host simulator
// (firmware/app/sim_main.cpp) is the verified path; board-specific data paths
// (SPI display, I2S codec, SDMMC, USB composite) are explicit TODO(hw) stubs.
#include <Arduino.h>
#include <stdio.h>

#include "audio/engine.hpp"
#include "core/device_mode.hpp"
#include "core/params.hpp"
#include "hal/board_cores3.hpp"
#include "io/daw_controller.hpp"
#include "io/hid_keyboard.hpp"
#include "net/wireless.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

hal::cores3::BoardCores3 g_board;
Engine g_engine;
DeviceModeManager g_modes;
net::WirelessManager g_wireless;
DawController g_daw;
HidKeyboardMapper g_keyboard;
ui::Framebuffer800* g_framebuffer = nullptr;

uint32_t g_lastFrameUs = 0;
bool g_playing = true;

void buildSnapshot(ui::UiSnapshot* snapshot) {
  ui::uiSnapshotDemo(snapshot, ui::Screen::Main);
  ui::uiSnapshotForDeviceMode(snapshot, g_modes.mode());
  snapshot->bpm = g_engine.globals().v[Bpm];
  snapshot->playing = g_playing;
  std::snprintf(snapshot->status, sizeof(snapshot->status), "%s", g_playing ? "PLAY" : "STOP");
  snapshot->activeVoices = g_engine.activeVoices();
  snapshot->masterLevel = g_engine.lastTelemetry().peak;
  for (int t = 0; t < kNumParts; ++t) {
    snapshot->tracks[t].level = g_engine.partMeter(t);
    snapshot->tracks[t].voices = g_engine.voicesInPart(t);
  }
  const hal::cores3::BoardCores3Status& status = g_board.status();
  std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                "S3-BASE %s | PSRAM:%s | SPI2 %u MHz | USB FS stereo", hal::cores3::BoardCores3::name(),
                status.psramDetected ? "8MiB" : "absent",
                static_cast<unsigned>(g_board.config().lcdSpiHz / 1000000u));
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("Bukifon S3-base (CORE-S3 rev.0, PRE-FREEZE)");
  const bool ok = g_board.begin();
  const hal::cores3::BoardCores3Status& status = g_board.status();
  Serial.printf("board HAL: %s, pins unique=%d, cpu=%u MHz, psram=%u MHz\n",
                hal::cores3::BoardCores3::name(), ok ? 1 : 0,
                static_cast<unsigned>(status.cpuMhz), static_cast<unsigned>(status.psramMhz));
  Serial.printf("status: lcd=%d sd=%d i2c=%d i2s=%d midi=%d usb=%d psram=%d heap=%u\n",
                status.displayReady ? 1 : 0, status.sdReady ? 1 : 0, status.i2cReady ? 1 : 0,
                status.i2sReady ? 1 : 0, status.midiReady ? 1 : 0, status.usbFsReady ? 1 : 0,
                status.psramDetected ? 1 : 0, static_cast<unsigned>(status.freeHeapBytes));

  g_engine.init();
  g_engine.loadFactoryPatch(0);
  g_modes.init(DeviceMode::Synth);
  g_wireless.init();
  g_wireless.setTransport(net::Transport::Usb);
  g_daw.init();
  g_keyboard.setLayer(KeyboardLayer::Base);

  g_framebuffer = new ui::Framebuffer800();
  if (!g_framebuffer || !g_framebuffer->valid()) {
    Serial.println("ERROR: 800x480 framebuffer allocation failed (needs PSRAM)");
  }
  // TODO(hw): TinyUSB composite (HID+MIDI+CDC+stereo UAC2), SPI2 panel init,
  // I2S0 DMA ring (2x256), SDMMC sample streaming.
}

void loop() {
  const uint32_t nowUs = micros();
  if (nowUs - g_lastFrameUs >= 33000) {  // ~30 fps UI
    g_lastFrameUs = nowUs;
    if (g_framebuffer && g_framebuffer->valid()) {
      ui::UiSnapshot snapshot;
      buildSnapshot(&snapshot);
      ui::drawUi800(*g_framebuffer, snapshot);
      // TODO(hw): push dirty rows through the SPI2 bounce buffers.
    }
  }
  // Audio rendering is owned by the I2S DMA callback/worker on device; the
  // host simulator is the verified rendering path (see firmware/bench).
  static float l[64];
  static float r[64];
  g_engine.process(l, r, 64);
}
