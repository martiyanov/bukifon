// SPDX-License-Identifier: GPL-3.0-or-later
// S3 vertical-slice spike — board configuration.
//
// Pins are frozen from hardware/cores3/pinmap.csv (CORE-S3 rev.0).  The spike
// runs on an ESP32-S3-WROOM-1-N16R8 devkit (16 MB flash, 8 MB octal PSRAM @80 MHz,
// 240 MHz CPU) with a real 800x480 SPI display, PCM5102A/PCM1808 codecs,
// 1-bit SD card and (optionally) I2C MCP23017 panel expanders.
#pragma once

#include <cstdint>

namespace bukifon {
namespace spike {

// --- pins (hardware/cores3/pinmap.csv) -------------------------------------
struct SpikePin {
  const char* signal;
  int gpio;
};

constexpr SpikePin kPins[] = {
    {"LCD_SCK", 12},     {"LCD_MOSI", 11},   {"LCD_CS", 10},      {"LCD_DC", 9},
    {"LCD_RST", 8},      {"BL_PWM", 21},     {"SPI3_SCK", 4},     {"SPI3_MOSI", 5},
    {"SPI3_MISO", 6},    {"MCP3208_CS", 7},  {"SD_CLK", 15},      {"SD_CMD", 14},
    {"SD_D0", 13},       {"I2C0_SDA", 16},   {"I2C0_SCL", 17},    {"I2S_MCLK", 18},
    {"I2S_BCK", 1},      {"I2S_LRCK", 2},    {"I2S_DAC_DIN", 38}, {"I2S_ADC_DOUT", 39},
    {"MIDI_TX", 40},     {"MIDI_RX", 41},    {"LED_DATA", 42},    {"PANEL_IRQ", 47},
    {"GATE1_GPIO", 48},  {"PWR_GOOD", 3},    {"BOOT", 0},
};
constexpr int kPinCount = static_cast<int>(sizeof(kPins) / sizeof(kPins[0]));

// Named pin constants used by spike_main.cpp.
constexpr int kLcdSck = 12;
constexpr int kLcdMosi = 11;
constexpr int kLcdCs = 10;
constexpr int kLcdDc = 9;
constexpr int kLcdRst = 8;
constexpr int kBlPwm = 21;
constexpr int kSdClk = 15;
constexpr int kSdCmd = 14;
constexpr int kSdD0 = 13;
constexpr int kI2cSda = 16;
constexpr int kI2cScl = 17;
constexpr int kI2sMclk = 18;
constexpr int kI2sBck = 1;
constexpr int kI2sLrck = 2;
constexpr int kI2sDacDin = 38;
constexpr int kI2sAdcDout = 39;
constexpr int kMidiTx = 40;
constexpr int kMidiRx = 41;
constexpr int kLedData = 42;
constexpr int kPanelIrq = 47;
constexpr int kGate1 = 48;
constexpr int kPwrGood = 3;
constexpr int kBoot = 0;

// --- clocks / memory -------------------------------------------------------
constexpr uint32_t kCpuMhz = 240;
constexpr uint32_t kPsramMhz = 80;
constexpr uint32_t kLcdSpiHz = 80000000;  // SPI2 display clock (D-51 model)
constexpr uint32_t kI2cHz = 400000;
constexpr uint32_t kAudioSampleRate = 48000;
constexpr uint32_t kAudioBlockFrames = 64;  // 1.333 ms deadline
constexpr uint32_t kUsbRxBytes = 4096;
constexpr uint32_t kUsbTxBytes = 4096;

// --- display ---------------------------------------------------------------
constexpr int kDisplayWidth = 800;
constexpr int kDisplayHeight = 480;
constexpr int kBounceRows = 16;  // 8-16 rows in internal SRAM
constexpr int kBounceBytes = kDisplayWidth * kBounceRows * 2;

// --- test timing (docs/36 acceptance tests) --------------------------------
constexpr uint32_t kAudioBudgetUs = 650;     // max block <= 650 us
constexpr uint32_t kAudioP99BudgetUs = 500;  // p99 <= 500 us
constexpr uint32_t kAudioDeadlineUs = 1333;  // 64 frames @ 48 kHz
constexpr uint32_t kSdLatencyBudgetUs = 10000;
constexpr uint32_t kPanelPollMs = 10;
constexpr uint32_t kSdBenchBytes = 4096;
constexpr uint32_t kUsbSoakDefaultSeconds = 1800;  // 30-60 min protocol

// Optional compile-time phases (seconds): 0 disables a phase.
#ifndef BUKIFON_SPIKE_AUDIO_SECONDS
#define BUKIFON_SPIKE_AUDIO_SECONDS 60
#endif
#ifndef BUKIFON_SPIKE_DISPLAY_SECONDS
#define BUKIFON_SPIKE_DISPLAY_SECONDS 60
#endif
#ifndef BUKIFON_SPIKE_USB_SECONDS
#define BUKIFON_SPIKE_USB_SECONDS 60
#endif

}  // namespace spike
}  // namespace bukifon
