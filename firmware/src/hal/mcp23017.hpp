// SPDX-License-Identifier: GPL-3.0-or-later
// MCP23017 deck expander (16 I/O): matrix scanning + FSR multiplexer control.
// Address 0x20 on I2C0; INT on GP28 (contract update).
// HARDWARE STATUS: not verified on real HW.
#pragma once

#include <cstdint>

#include "hal/pinmap.hpp"
#include "io/deck.hpp"

#if defined(ARDUINO)
#include <Wire.h>
#endif

namespace bukifon {
namespace hal {

class Mcp23017 : public IDeckIo {
 public:
  bool begin(uint8_t address = pins::kDeckMcpAddress) {
    address_ = address;
#if defined(ARDUINO)
    Wire.begin();
    // GPA = row drive outputs, GPB = column inputs with pull-ups.
    writeRegister(0x00, 0x00);  // IODIRA
    writeRegister(0x01, 0xFF);  // IODIRB
    writeRegister(0x0C, 0xFF);  // GPPUB pull-ups on columns
    writeRegister(0x0D, 0x00);  // GPPUA off
    writeRegister(0x12, 0xFF);  // GPIOA all high (rows inactive)
    configured_ = true;
#endif
    return true;
  }

  void writePort(uint8_t port, uint8_t value) override {
    activePort_[port & 1] = value;
#if defined(ARDUINO)
    if (!configured_) begin();
    writeRegister(static_cast<uint8_t>((port & 1) ? 0x13 : 0x12), value);
#endif
  }

  uint8_t readPort(uint8_t port) override {
#if defined(ARDUINO)
    if (!configured_) begin();
    return readRegister(static_cast<uint8_t>((port & 1) ? 0x13 : 0x12));
#else
    return static_cast<uint8_t>(port ? inputs_ : activePort_[0]);
#endif
  }

  uint16_t readAdc(uint8_t) override { return 0; }  // deck ADC comes via MCP3208

  // 2 x 74HC4067 channel select for the optional FSR velocity film.
  void selectFsrChannel(uint8_t channel) {
    // EN + S0..S3 are wired to MCP23017 spare pins (GPA4..GPA7); mapping is
    // documented in the hardware repo. TODO(hw): verify wiring.
    const uint8_t s = static_cast<uint8_t>(channel & 0x0F);
    const uint8_t bits = static_cast<uint8_t>(0x10 | (s & 0x0F));
    writePort(0, static_cast<uint8_t>(~bits));
  }

  void setSimulatedInput(uint8_t value) { inputs_ = value; }

 private:
  void writeRegister(uint8_t reg, uint8_t value) {
#if defined(ARDUINO)
    Wire.beginTransmission(address_);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
#else
    (void)reg;
    (void)value;
#endif
  }
  uint8_t readRegister(uint8_t reg) {
#if defined(ARDUINO)
    Wire.beginTransmission(address_);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(static_cast<int>(address_), 1);
    return Wire.available() ? static_cast<uint8_t>(Wire.read()) : 0xFF;
#else
    (void)reg;
    return inputs_;
#endif
  }

  uint8_t address_ = pins::kDeckMcpAddress;
  bool configured_ = false;
  uint8_t activePort_[2] = {0xFF, 0xFF};
  uint8_t inputs_ = 0xFF;
};

}  // namespace hal
}  // namespace bukifon
