// SPDX-License-Identifier: GPL-3.0-or-later
// DAW-controller mode: 16 encoders as MIDI CC with 4 banks x 16, transport
// buttons, and 42 keys as notes or hotkeys.  Mackie/HUI support is a skeleton.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum class DawTransport : uint8_t { Play = 0, Stop, Record, Loop, kNumActions };

class DawController {
 public:
  static constexpr int kEncoderCount = 16;  // two MCP23017 banks on the v1.0 panel
  static constexpr int kBankCount = 4;
  static constexpr int kCcPerBank = 16;

  void init();

  // --- encoders / CC banks --------------------------------------------------
  bool setBank(int bank);
  int bank() const { return bank_; }
  int nextBank();
  uint8_t ccForEncoder(int encoder) const;   // 0..127, bank-dependent
  uint8_t valueForEncoder(int encoder) const;  // 0..127
  void setEncoderValue(int encoder, float normalized);  // 0..1
  uint8_t applyEncoderDelta(int encoder, int delta, int stepsPerTurn = 100);

  // --- transport ------------------------------------------------------------
  // Returns the CC number that was emitted (or 0xFF if unused).
  uint8_t transportAction(DawTransport action);
  uint8_t lastTransportCc() const { return lastTransportCc_; }
  uint8_t lastTransportValue() const { return lastTransportValue_; }
  bool lastWasNote() const { return lastWasNote_; }
  uint8_t lastTransportNote() const { return lastTransportNote_; }
  void setTransportUsesNotes(bool notes) { transportNotes_ = notes; }

  // --- 42 keys --------------------------------------------------------------
  enum class KeyMode : uint8_t { Notes = 0, Hotkeys };
  void setKeyMode(KeyMode mode) { keyMode_ = mode; }
  KeyMode keyMode() const { return keyMode_; }
  uint8_t noteForKey(int keyIndex) const;    // C3 + key, clamped
  uint8_t hotkeyCcForKey(int keyIndex) const;  // CC 100..141 (banked)

  // --- Mackie / HUI skeleton ------------------------------------------------
  bool mackieSupported() const { return false; }  // TODO(daw): MCU/HUI emulation
  const char* protocolName() const { return keyMode_ == KeyMode::Notes ? "MIDI-NOTES" : "MIDI-CC"; }

 private:
  int bank_ = 0;
  uint8_t encoderValues_[kEncoderCount] = {};
  uint8_t lastTransportCc_ = 0xFF;
  uint8_t lastTransportValue_ = 0;
  bool transportNotes_ = false;
  uint8_t lastTransportNote_ = 0;
  bool lastWasNote_ = false;
  KeyMode keyMode_ = KeyMode::Notes;
};

}  // namespace bukifon
