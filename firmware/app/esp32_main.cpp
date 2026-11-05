// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon ESP32-P4/S3 firmware skeleton (v0.5).
//
// SCOPE: this file wires the portable engine + 800x480 UI shell + device modes
// + USB/BLE/Wi-Fi frameworks into a compiling device build.  The host demo and
// all unit tests are the verified artefact of this milestone; the ESP32
// hardware paths are explicit TODO(hw) stubs (see REPORT.md).
//
// Host equivalent: firmware/app/sim_main.cpp (deterministic simulator).
#include <Arduino.h>

#include "audio/engine.hpp"
#include "core/device_mode.hpp"
#include "core/params.hpp"
#include "hal/esp32_hal.hpp"
#include "io/daw_controller.hpp"
#include "io/hid_keyboard.hpp"
#include "net/wireless.hpp"
#include "usb/usb_descriptors.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

hal::Esp32Hal g_hal;
Engine g_engine;
DeviceModeManager g_modes;
net::WirelessManager g_wireless;
DawController g_daw;
HidKeyboardMapper g_keyboard;
usb::UsbCompositeBuilder g_usb;
ui::Framebuffer800* g_framebuffer = nullptr;

uint32_t g_lastFrameUs = 0;
uint32_t g_lastControlUs = 0;
bool g_playing = true;

void buildSnapshot(ui::UiSnapshot* snapshot) {
  if (!snapshot) return;
  ui::uiSnapshotDemo(snapshot, ui::Screen::Main);
  snapshot->bpm = g_engine.globals().v[Bpm];
  snapshot->playing = g_playing;
  std::snprintf(snapshot->status, sizeof(snapshot->status), "%s", g_playing ? "PLAY" : "STOP");
  std::snprintf(snapshot->deviceMode, sizeof(snapshot->deviceMode), "%s",
                deviceModeShortName(g_modes.mode()));
  snapshot->activeVoices = g_engine.activeVoices();
  snapshot->masterLevel = g_engine.lastTelemetry().peak;
  for (int t = 0; t < kNumParts; ++t) {
    snapshot->tracks[t].level = g_engine.partMeter(t);
    snapshot->tracks[t].voices = g_engine.voicesInPart(t);
    snapshot->tracks[t].cutoff = g_engine.modulatedPartParams(t).v[Cutoff];
    snapshot->tracks[t].pan = g_engine.modulatedPartParams(t).v[PartPan];
  }
  std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                "MODE %s | USB:%s BLE:%s Wi-Fi:%s | host-demo is the tested path",
                deviceModeName(g_modes.mode()), g_wireless.usbReady() ? "READY" : "STUB",
                g_wireless.bleReady() ? "READY" : "STUB", g_wireless.wifiReady() ? "READY" : "STUB");
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("Bukifon v0.5 firmware skeleton");
  g_hal.begin();

  g_engine.init();
  g_engine.loadFactoryPatch(0);
  g_modes.init(DeviceMode::Synth);
  g_wireless.init();
  g_wireless.setTransport(net::Transport::Usb);
  g_daw.init();
  g_keyboard.setLayer(KeyboardLayer::Base);

  if (g_usb.build()) {
    Serial.printf("USB composite: config %u bytes, %u interfaces, %u endpoints, HID report %u bytes\n",
                  static_cast<unsigned>(g_usb.descriptors().configTotalLength),
                  static_cast<unsigned>(g_usb.descriptors().interfaceCount),
                  static_cast<unsigned>(g_usb.descriptors().endpointCount),
                  static_cast<unsigned>(g_usb.descriptors().hidReport.size()));
  } else {
    Serial.println("USB descriptor build FAILED");
  }
  // TODO(hw): hand the descriptors to TinyUSB (HID + MIDI + UAC2 + CDC).
  // TODO(hw): NimBLE BLE-MIDI/HID on S3, ESP32-C6 coprocessor on P4.
  // TODO(hw): Wi-Fi AP + web page + OTA (net/wireless.hpp API is ready).

  g_framebuffer = new ui::Framebuffer800();
  if (!g_framebuffer || !g_framebuffer->valid()) {
    Serial.println("ERROR: 800x480 framebuffer allocation failed (PSRAM required)");
  }
}

void loop() {
  const uint32_t nowUs = micros();
  if (nowUs - g_lastControlUs >= 1000) {  // 1 kHz control tick
    g_lastControlUs = nowUs;
    g_hal.tick(nowUs);
    // TODO(hw): read encoders/deck/MIDI here and push events into the engine.
  }
  if (nowUs - g_lastFrameUs >= 33000) {  // ~30 fps UI
    g_lastFrameUs = nowUs;
    if (g_framebuffer && g_framebuffer->valid()) {
      ui::UiSnapshot snapshot;
      buildSnapshot(&snapshot);
      ui::drawUi800(*g_framebuffer, snapshot);
      g_hal.present(*g_framebuffer);
    }
  }
  // Audio callback stub: on the device the engine renders into I2S DMA from a
  // pinned task/core; the host simulator is the verified rendering path.
  static float l[64];
  static float r[64];
  g_engine.process(l, r, 64);
}
