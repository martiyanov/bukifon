// SPDX-License-Identifier: GPL-3.0-or-later
// Deck abstraction: DECK-PAD (18 pads, 3x6 MCP23017 matrix) and DECK-KEYS
// (42 keys, 6x7 matrix + diodes), FSR velocity, debouncing, key mapping.
#pragma once

#include <cmath>
#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum class DeckType : uint8_t { None = 0, Pad = 1, Keys = 2 };

// Hardware abstraction: MCP23017 ports and MCP3208 ADC channels.
class IDeckIo {
 public:
  virtual ~IDeckIo() = default;
  virtual void writePort(uint8_t port, uint8_t value) = 0;  // 0 = GPA, 1 = GPB
  virtual uint8_t readPort(uint8_t port) = 0;
  virtual uint16_t readAdc(uint8_t channel) = 0;  // 12 bit, MCP3208
};

class DeckSink {
 public:
  virtual ~DeckSink() = default;
  virtual void onPad(uint8_t index, uint8_t velocity, bool pressed) {
    (void)index; (void)velocity; (void)pressed;
  }
  virtual void onKey(uint8_t index, uint8_t velocity, bool pressed) {
    (void)index; (void)velocity; (void)pressed;
  }
};

struct DeckConfig {
  DeckType type = DeckType::Pad;
  uint8_t rows = 3;          // pad: 3, keys: 6
  uint8_t columns = 6;       // pad: 6, keys: 7
  uint32_t debounceUs = 5000;  // 5 ms pads, 3 ms keys
  uint16_t fsrBaseline = 0;
  bool fsrEnabled = false;
};

// Scans the deck matrix and produces debounced pad/key events.
class DeckScanner {
 public:
  void init(DeckType type, IDeckIo* io, DeckSink* sink);
  void setFsrEnabled(bool enabled) { config_.fsrEnabled = enabled; }
  void poll(uint32_t nowUs);
  DeckType type() const { return config_.type; }
  int ledCount() const { return config_.type == DeckType::Keys ? kKeyLeds : kPadLeds; }
  uint8_t buttonCount() const {
    return config_.type == DeckType::Keys ? static_cast<uint8_t>(kNumKeys)
                                          : static_cast<uint8_t>(kNumPads);
  }
  bool pressed(int index) const;
  const DeckConfig& config() const { return config_; }

 private:
  struct ButtonState {
    uint8_t stable = 0;
    uint8_t raw = 0;
    uint32_t lastChangeUs = 0;
  };
  void scanOnce(uint32_t nowUs);
  void updateButton(int index, bool raw, uint32_t nowUs);

  DeckConfig config_{};
  IDeckIo* io_ = nullptr;
  DeckSink* sink_ = nullptr;
  ButtonState buttons_[kNumKeys] = {};
  uint16_t fsrBaseline_ = 0;
  bool fsrPrimed_ = false;
};

// Maps the 42-key deck to MIDI notes. Layout 0 = chromatic from C3 (default);
// layout 1 = isomorphic (major thirds columns, like the Corne/Janko idea).
class KeyboardMapper {
 public:
  static int keyToNote(int keyIndex, int layout = 0, int octaveShift = 0);
  static int keyToSemitone(int keyIndex, int layout = 0);
  static int noteToKey(int note, int layout = 0);
};

// DECK_ID auto-detection (spec/20-electronics.md §6.2).
class DeckDetector {
 public:
  static DeckType typeFromVolts(float volts) {
    if (volts >= 2.8f && volts <= 3.4f) return DeckType::Keys;
    if (volts >= 0.0f && volts <= 0.5f) return DeckType::Pad;
    return DeckType::None;
  }
  static DeckType typeFromAdc(uint16_t raw, uint16_t fullScale = 4095) {
    const float volts = 3.3f * static_cast<float>(raw) / static_cast<float>(fullScale);
    return typeFromVolts(volts);
  }
  static int ledCount(DeckType type) {
    return kPanelLeds + ((type == DeckType::Keys) ? kKeyLeds : kPadLeds);
  }
};

// FSR velocity from the force ramp (0..1) with a musical response curve.
class FsrVelocity {
 public:
  static uint8_t fromForceDelta(uint16_t baseline, uint16_t current) {
    if (current <= baseline) return 1;
    const int delta = static_cast<int>(current) - static_cast<int>(baseline);
    // sqrt-ish response; delta is in 12-bit ADC counts.
    const float norm = static_cast<float>(delta) / 4095.0f;
    const int vel = 1 + static_cast<int>(std::sqrt(std::fmin(norm * 4.0f, 1.0f)) * 126.0f);
    return static_cast<uint8_t>(vel > 127 ? 127 : (vel < 1 ? 1 : vel));
  }
};

}  // namespace bukifon
