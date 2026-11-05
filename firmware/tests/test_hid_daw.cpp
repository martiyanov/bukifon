// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstring>
#include <set>

#include "core/device_mode.hpp"
#include "io/daw_controller.hpp"
#include "io/hid_keyboard.hpp"
#include "test_framework.hpp"

using namespace bukifon;

TEST(HidKeyboardBaseMapping) {
  HidKeyboardMapper mapper;
  CHECK(mapper.key(0).keycode == hid_usage::kA + 16);   // Q
  CHECK(mapper.key(1).keycode == hid_usage::kA + 22);   // W
  CHECK(mapper.key(19).modifier == HidLeftShift);       // left thumb LSHIFT
  CHECK(mapper.key(19).keycode == hid_usage::kNone);    // modifier only
  CHECK(mapper.key(37).modifier == HidRightShift);      // right RSHIFT key
  CHECK(mapper.key(39).keycode == hid_usage::kSpace);   // right thumb SPACE
  CHECK(mapper.key(41).keycode == hid_usage::kBackspace);
  CHECK(mapper.key(21).keycode == hid_usage::kA + 20);  // U
  CHECK(mapper.keyCount() == kNumKeys);
  CHECK(kNumKeys == 42);
  INFO("HID base: key0=Q, key19=LShift, key37=RShift, key39=Space, 42 keys");
}

TEST(HidKeyboardLayersAndReport) {
  HidKeyboardMapper mapper;
  CHECK(std::strcmp(keyboardLayerName(KeyboardLayer::Base), "BASE") == 0);
  CHECK(std::strcmp(keyboardLayerName(KeyboardLayer::Macro), "MACRO") == 0);
  CHECK(mapper.setLayerIndex(static_cast<int>(KeyboardLayer::Shift)));
  CHECK(mapper.layer() == KeyboardLayer::Shift);
  CHECK(mapper.key(0).modifier == HidLeftShift);  // shifted Q
  CHECK(mapper.key(0).keycode == hid_usage::kA + 16);
  CHECK(!mapper.setLayerIndex(99));

  // Symbols layer: F-keys are mapped.
  CHECK(mapper.setLayerIndex(static_cast<int>(KeyboardLayer::Symbols)));
  CHECK(mapper.key(1).keycode == hid_usage::kF1);

  // Base report from three keys + shift thumb.
  mapper.setLayerIndex(static_cast<int>(KeyboardLayer::Base));
  bool pressed[kNumKeys] = {};
  pressed[0] = true;
  pressed[1] = true;
  pressed[2] = true;
  pressed[19] = true;
  HidReport report;
  mapper.buildReport(pressed, &report);
  INFO("HID report: modifiers=0x%02X keyCount=%u first=0x%02X", report.modifiers, report.keyCount,
       report.keycodes[0]);
  CHECK(report.modifiers == HidLeftShift);
  CHECK(report.keyCount == 3);
  CHECK(report.keycodes[0] == hid_usage::kA + 16);  // Q
  uint8_t bytes[kHidReportBytes] = {};
  encodeHidReport(report, bytes);
  CHECK(bytes[0] == report.modifiers);
  CHECK(bytes[1] == 0);
  CHECK(bytes[2] == report.keycodes[0]);
  CHECK(bytes[kHidReportBytes - 1] == report.keycodes[5]);

  // 6KRO cap: 10 pressed keys -> 6 keycodes.
  bool many[kNumKeys] = {};
  for (int k = 0; k < 10; ++k) many[k] = true;
  mapper.buildReport(many, &report);
  CHECK(report.keyCount == 6);
  INFO("HID layers: Shift/Symbols mapping and 6KRO report cap verified");
}

TEST(HidKeyboardMacros) {
  HidKeyboardMapper mapper;
  CHECK(mapper.setLayerIndex(static_cast<int>(KeyboardLayer::Macro)));
  int nonEmpty = 0;
  for (int k = 0; k < kNumKeys; ++k) {
    const char* macro = mapper.macroFor(k);
    if (macro && std::strlen(macro) > 0) ++nonEmpty;
  }
  INFO("HID macro layer: %d/42 keys have macro stubs", nonEmpty);
  CHECK(nonEmpty == kNumKeys);
  CHECK(std::strcmp(mapper.macroFor(0), "CUT 2400") == 0);
}

TEST(DawControllerCcBanks) {
  DawController daw;
  daw.init();
  CHECK(DawController::kEncoderCount == 16);
  CHECK(DawController::kBankCount == 4);
  CHECK(DawController::kCcPerBank == 16);
  std::set<int> ccs;
  for (int bank = 0; bank < DawController::kBankCount; ++bank) {
    CHECK(daw.setBank(bank));
    for (int enc = 0; enc < DawController::kEncoderCount; ++enc) {
      const int cc = daw.ccForEncoder(enc);
      CHECK(cc >= 16 && cc < 80);
      ccs.insert(cc);
    }
  }
  CHECK(ccs.size() == 64);  // 4 banks x 16 encoders = 64 unique CCs
  CHECK(!daw.setBank(-1));
  CHECK(!daw.setBank(4));
  CHECK(daw.nextBank() == 0);  // wrapped from bank 3
  CHECK(daw.ccForEncoder(0) == 16);
  CHECK(daw.setBank(1));
  CHECK(daw.ccForEncoder(0) == 32);
  INFO("DAW CC banks: 4 banks x 16 encoders = 64 unique CCs (%d..%d)", *ccs.begin(), *ccs.rbegin());
}

TEST(DawControllerTransportAndKeys) {
  DawController daw;
  daw.init();
  daw.setEncoderValue(0, 0.5f);
  const uint8_t mid = daw.valueForEncoder(0);
  CHECK(mid >= 62 && mid <= 65);
  const uint8_t cc = daw.applyEncoderDelta(0, 10);
  CHECK(cc == 16);
  CHECK(daw.valueForEncoder(0) > mid);
  daw.setEncoderValue(0, 1.0f);
  daw.applyEncoderDelta(0, 100);  // clamped at maximum
  CHECK(daw.valueForEncoder(0) == 127);

  CHECK(daw.transportAction(DawTransport::Play) == 118);
  CHECK(daw.lastTransportValue() == 127);
  CHECK(daw.transportAction(DawTransport::Stop) == 117);
  CHECK(daw.transportAction(DawTransport::Record) == 119);
  CHECK(daw.transportAction(DawTransport::Loop) == 120);
  daw.setTransportUsesNotes(true);
  daw.transportAction(DawTransport::Play);
  CHECK(daw.lastWasNote());
  CHECK(daw.lastTransportNote() == 24);

  daw.setKeyMode(DawController::KeyMode::Notes);
  CHECK(daw.noteForKey(0) == 48);
  CHECK(daw.noteForKey(41) == 89);
  daw.setKeyMode(DawController::KeyMode::Hotkeys);
  CHECK(daw.hotkeyCcForKey(0) == 100);
  CHECK(daw.hotkeyCcForKey(41) >= 100 && daw.hotkeyCcForKey(41) < 120);
  CHECK(!daw.mackieSupported());  // stubbed
  CHECK(std::strcmp(daw.protocolName(), "MIDI-CC") == 0);
  INFO("DAW: transport CCs 117..120, notes 48..89, hotkeys CC 100..119 (MCU/HUI stub)");
}

TEST(DawModeUsesHidAndCc) {
  CHECK(DeviceModeManager::usesDawCc(DeviceMode::DawController));
  CHECK(DeviceModeManager::usesHidKeyboard(DeviceMode::DawController));
  CHECK(DeviceModeManager::usesUsbMidi(DeviceMode::DawController));
  CHECK(!DeviceModeManager::usesDawCc(DeviceMode::Synth));
  INFO("DAW mode capability wiring: HID + MIDI CC + USB MIDI");
}
