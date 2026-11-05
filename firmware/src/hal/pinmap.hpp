// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon hardware pin map — CORE-1 / PANEL-1 / DECK (spec/20-electronics.md §2).
//
// Updated per Lead's 2025-11-05 contract update:
//   GATE1 = GP22, GATE2 = GP26, DECK_ID = GP27 (ADC1), DECK_INT = GP28.
// The old SYS_MON function moved off GP26 (now GATE2); system monitoring is
// done at the power stage and is not sampled by this firmware anymore.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {
namespace hal {
namespace pins {

// CORE-1 (Raspberry Pi Pico)
constexpr int kMidiTx = 0;      // UART0 TX -> MIDI OUT (74HCT125)
constexpr int kMidiRx = 1;      // UART0 RX <- MIDI IN (6N137)
constexpr int kSpi0Sck = 2;     // MCP3208 SCLK + 74HC165 CP
constexpr int kSpi0Mosi = 3;    // MCP3208 DIN
constexpr int kSpi0Miso = 4;    // MCP3208 DOUT + 74HC165 QH
constexpr int kMcp3208Cs = 5;
constexpr int kHc165Pl = 6;
constexpr int kLedData = 7;     // WS2812 chain (27 or 51 LEDs)
constexpr int kI2cSda = 8;      // MCP4728 + 24C32
constexpr int kI2cScl = 9;
constexpr int kLcdSck = 10;     // SPI1
constexpr int kLcdMosi = 11;
constexpr int kLcdCs = 12;
constexpr int kLcdDc = 13;
constexpr int kLcdRst = 14;
constexpr int kLcdBl = 15;
constexpr int kI2sBck = 16;     // PIO I2S
constexpr int kI2sLrck = 17;
constexpr int kI2sDin = 18;
constexpr int kPort0Cs = 19;
constexpr int kPort1Cs = 20;
constexpr int kPort2Cs = 21;
constexpr int kGate1 = 22;      // 2N7000 open drain
constexpr int kGate2 = 26;      // contract update: was SYS_MON
constexpr int kDeckId = 27;     // ADC1, DECK_PAD 0.3 V / DECK_KEYS 3.0 V
constexpr int kDeckInt = 28;    // MCP23017 INT (contract update)

// MCP23017 deck expander: GPA0..A5 rows, GPB0..B6 columns; 0x20.
constexpr uint8_t kDeckMcpAddress = 0x20;
constexpr uint8_t kReserveMcpAddress = 0x21;
constexpr uint8_t kMcp4728Address = 0x60;
constexpr uint8_t kEepromAddress = 0x50;   // 24C32
constexpr int kI2cClockHz = 400000;
constexpr int kSpiClockHz = 8000000;

// Audio: I2S 48 kHz, 16 bit stereo, double buffer 2 x 256 frames.
constexpr int kAudioBlock = kBlockSize;  // 256 frames per half-buffer
constexpr int kAudioBuffers = 2;

}  // namespace pins
}  // namespace hal
}  // namespace bukifon
