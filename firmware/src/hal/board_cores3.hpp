// SPDX-License-Identifier: GPL-3.0-or-later
// CORE-S3 (Bukifon S3-base) board HAL — ESP32-S3-WROOM-1-N16R8.
//
// Pin map source of truth: hardware/cores3/pinmap.csv (rev.0, PRE-FREEZE).
// Display: SPI 800x480 RGB565 (SPI2 + DC/RST/BL) — D-51; one PSRAM framebuffer
// + 8-16 line bounce buffers in internal SRAM.  SD: 1-bit SDMMC.  Audio:
// I2S0 (MCLK/BCK/LRCK/DIN/DOUT) for PCM5102A/PCM1808.  USB: FS composite
// (HID+MIDI+CDC+stereo UAC2 — D-48; 8x8 UAC2 is P4/H743 only).
//
// The class configures pins and probes what it can; the actual display/I2S/SD
// data paths are TODO(hw) stubs until the devkit spike (P1).
#pragma once

#include <cstdint>

namespace bukifon {
namespace hal {
namespace cores3 {

// --- pins (hardware/cores3/pinmap.csv) -------------------------------------
constexpr int kLcdSck = 12;    // SPI2 FSPICLK
constexpr int kLcdMosi = 11;   // SPI2 FSPID
constexpr int kLcdCs = 10;     // SPI2 FSPICS0
constexpr int kLcdDc = 9;
constexpr int kLcdRst = 8;
constexpr int kBlPwm = 21;     // LEDC PWM -> BL boost 19-22 V

constexpr int kSpi3Sck = 4;    // SPI3 (MCP3208, 10 MHz)
constexpr int kSpi3Mosi = 5;
constexpr int kSpi3Miso = 6;
constexpr int kMcp3208Cs = 7;

constexpr int kSdClk = 15;     // SDMMC 1-bit
constexpr int kSdCmd = 14;
constexpr int kSdD0 = 13;

constexpr int kI2cSda = 16;    // I2C0: MCP4728 x2, 24C32, PANEL-2
constexpr int kI2cScl = 17;

constexpr int kI2sMclk = 18;   // I2S0: 12.288 MHz = 256 fs
constexpr int kI2sBck = 1;     // 3.072 MHz = 64 fs
constexpr int kI2sLrck = 2;    // 48 kHz
constexpr int kI2sDacDin = 38; // PCM5102A SD_OUT
constexpr int kI2sAdcDout = 39;  // PCM1808 SD_IN

constexpr int kMidiTx = 40;    // UART1 (matrix) -> 74HCT125
constexpr int kMidiRx = 41;    // UART1 <- 6N137
constexpr int kLedData = 42;   // RMT WS2812
constexpr int kPanelIrq = 47;  // 4x MCP23017 INTA
constexpr int kGate1 = 48;     // 2N7000 gate out (GATE2 not routed — D-52)
constexpr int kPwrGood = 3;    // PWR-2 supervisor
constexpr int kBoot = 0;       // BOOT strap / USB-JTAG

struct BoardCores3Config {
  uint32_t cpuMhz;
  uint32_t psramMhz;        // octal PSRAM @80 MHz on N16R8
  uint32_t lcdSpiHz;        // SPI2 assumed 80 MHz for the D-51 model
  uint32_t sdClockHz;       // 1-bit SDMMC
  uint32_t i2cHz;
  uint32_t i2sSampleRate;
  bool usbFsStereoUac;      // FS composite: HID+MIDI+CDC+stereo UAC2
  explicit BoardCores3Config(uint32_t cpu = 240, uint32_t psram = 80,
                             uint32_t lcdSpi = 80000000, uint32_t sdClock = 20000000,
                             uint32_t i2c = 400000, uint32_t i2s = 48000,
                             bool usbStereo = true)
      : cpuMhz(cpu),
        psramMhz(psram),
        lcdSpiHz(lcdSpi),
        sdClockHz(sdClock),
        i2cHz(i2c),
        i2sSampleRate(i2s),
        usbFsStereoUac(usbStereo) {}
};

struct BoardCores3Status {
  bool pinsConfigured = false;
  bool displayReady = false;  // TODO(hw): SPI2 panel init
  bool sdReady = false;       // 1-bit SDMMC mount
  bool i2cReady = false;
  bool i2sReady = false;      // TODO(hw): I2S0 driver
  bool midiReady = false;     // UART1 at 31250
  bool usbFsReady = false;    // USB CDC stack started
  bool psramDetected = false;
  uint32_t cpuMhz = 0;
  uint32_t psramMhz = 0;
  uint32_t freeHeapBytes = 0;
  uint32_t errors = 0;
};

class BoardCores3 {
 public:
  bool begin();
  void end();
  bool begun() const { return begun_; }
  const BoardCores3Status& status() const { return status_; }
  const BoardCores3Config& config() const { return config_; }
  static const char* name() { return "CORE-S3 / ESP32-S3-N16R8"; }

  // Bus shape (used by tests and the UI/bench memory profile).
  static constexpr int kDisplayPins = 6;
  static constexpr int kSdPins = 3;
  static constexpr int kI2sPins = 5;
  static constexpr int kMidiPins = 2;
  static constexpr int kI2cPins = 2;
  static constexpr int kPanelPins = 1;  // PANEL_IRQ
  static constexpr int kMemoryProfilePins = 1;  // LED_DATA / RMT
  static constexpr int kTotalFunctionalPins = 27;

  // True when no GPIO is assigned to two functions (pinmap.csv contract).
  static bool pinsUnique();

 private:
  BoardCores3Config config_{};
  BoardCores3Status status_{};
  bool begun_ = false;
};

}  // namespace cores3
}  // namespace hal
}  // namespace bukifon
