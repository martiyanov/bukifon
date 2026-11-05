// SPDX-License-Identifier: GPL-3.0-or-later
// MIDI I/O: TRS MIDI on UART0 (GP0 TX / GP1 RX, 31250 baud) and USB-MIDI via
// TinyUSB (Adafruit TinyUSB library when available).
// HARDWARE STATUS: UART tested only logically through the portable parser;
// USB-MIDI requires the TinyUSB core option and is TODO(hw) verified.
#pragma once

#include <cstddef>
#include <cstdint>

#include "hal/pinmap.hpp"
#include "io/midi_parser.hpp"

#if defined(ARDUINO)
#include <Arduino.h>
#endif

namespace bukifon {
namespace hal {

class MidiIo {
 public:
  bool begin(MidiParser* parser) {
    parser_ = parser;
#if defined(ARDUINO)
    Serial1.setRX(pins::kMidiRx);
    Serial1.setTX(pins::kMidiTx);
    Serial1.begin(31250);
    trsReady_ = true;
#endif
    return true;
  }

  // Polls the TRS UART (call at ~1 kHz).
  void poll() {
#if defined(ARDUINO)
    if (!trsReady_ || !parser_) return;
    while (Serial1.available() > 0) {
      parser_->feedByte(static_cast<uint8_t>(Serial1.read()));
    }
#endif
  }

  // Sends a raw MIDI message to both TRS and (if present) USB-MIDI.
  void send(const uint8_t* data, size_t length) {
#if defined(ARDUINO)
    if (trsReady_) {
      for (size_t i = 0; i < length; ++i) Serial1.write(data[i]);
    }
#if __has_include(<Adafruit_TinyUSB.h>)
    // TODO(hw): route through the project's Adafruit_USBD_MIDI instance.
#endif
#else
    (void)data;
    (void)length;
#endif
  }

  void sendCC(uint8_t channel, uint8_t cc, uint8_t value) {
    const uint8_t msg[3] = {static_cast<uint8_t>(0xB0 | (channel & 0x0F)), cc, value};
    send(msg, sizeof(msg));
  }
  void sendNoteOn(uint8_t channel, uint8_t note, uint8_t velocity) {
    const uint8_t msg[3] = {static_cast<uint8_t>(0x90 | (channel & 0x0F)), note, velocity};
    send(msg, sizeof(msg));
  }
  void sendNoteOff(uint8_t channel, uint8_t note) {
    const uint8_t msg[3] = {static_cast<uint8_t>(0x80 | (channel & 0x0F)), note, 0};
    send(msg, sizeof(msg));
  }

 private:
  MidiParser* parser_ = nullptr;
  bool trsReady_ = false;
};

}  // namespace hal
}  // namespace bukifon
