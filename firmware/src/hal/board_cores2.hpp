// SPDX-License-Identifier: GPL-3.0-or-later
// CORE-2 (Bukifon first SKU, ESP32-P4NRW32) board HAL.
//
// Pin map source of truth: hardware/core2/pinmap.csv (rev.0, PRE-FREEZE).
// P4 features: I2S0 codecs, RGB565 LCD_CAM (or DSI as a stub), I2C0 rails/
// expanders, MIDI UART1, SDMMC slot0 4-bit, USB HS PHY, ESP32-C6 over shared
// SPI2 (CS/HS/DR/RST), BOOT/RESET strapping.
//
// The display RGB/DSI backend and the C6 esp-hosted link are explicit TODO(hw)
// stubs; this HAL is a compiling skeleton for bring-up and the factory self-test.
#pragma once

#include <cstdint>

namespace bukifon {
namespace hal {
namespace cores2 {

struct Core2Pin {
  const char* signal;
  int gpio;
};

// hardware/core2/pinmap.csv — 55 GPIO signals (54 occupied + GPIO36 strap).
constexpr Core2Pin kPins[] = {
    {"SD_D0", 39},
    {"SD_D1", 40},
    {"SD_D2", 41},
    {"SD_D3", 42},
    {"SD_CLK", 43},
    {"SD_CMD", 44},
    {"SD_CD", 45},
    {"I2S_MCLK", 20},
    {"I2S_BCK", 16},
    {"I2S_LRCK", 17},
    {"I2S_DAC_DIN", 18},
    {"I2S_ADC_DOUT", 19},
    {"I2C0_SDA", 21},
    {"I2C0_SCL", 22},
    {"SPI2_SCK", 6},
    {"SPI2_MOSI", 7},
    {"SPI2_MISO", 8},
    {"MCP3208_CS", 9},
    {"MIDI_TX", 10},
    {"MIDI_RX", 11},
    {"UART0_TX", 37},
    {"UART0_RX", 38},
    {"LCD_PCLK", 12},
    {"LCD_DE", 13},
    {"LCD_HSYNC", 14},
    {"LCD_VSYNC", 15},
    {"LCD_B0", 0},
    {"LCD_B1", 1},
    {"LCD_B2", 2},
    {"LCD_B3", 3},
    {"LCD_B4", 4},
    {"LCD_G0", 5},
    {"LCD_G1", 23},
    {"LCD_G2", 28},
    {"LCD_G3", 29},
    {"LCD_G4", 30},
    {"LCD_G5", 31},
    {"LCD_R0", 32},
    {"LCD_R1", 33},
    {"LCD_R2", 34},
    {"LCD_R3", 46},
    {"LCD_R4", 47},
    {"BL_PWM", 49},
    {"LED_GPIO", 48},
    {"PANEL_IRQ", 51},
    {"GATE1_GPIO", 52},
    {"GATE2_GPIO", 53},
    {"C6_CS", 26},
    {"C6_HS", 24},
    {"C6_DR", 25},
    {"C6_RST", 27},
    {"BOOT", 35},
    {"STRAP36", 36},
    {"VBUS_DET", 54},
    {"LCD_DISP", 50},
};
constexpr int kPinCount = static_cast<int>(sizeof(kPins) / sizeof(kPins[0]));

// Named pins used by the HAL/factory code.
constexpr int kSdD0 = 39;
constexpr int kSdD1 = 40;
constexpr int kSdD2 = 41;
constexpr int kSdD3 = 42;
constexpr int kSdClk = 43;
constexpr int kSdCmd = 44;
constexpr int kSdCd = 45;
constexpr int kI2sMclk = 20;
constexpr int kI2sBck = 16;
constexpr int kI2sLrck = 17;
constexpr int kI2sDacDin = 18;
constexpr int kI2sAdcDout = 19;
constexpr int kI2cSda = 21;
constexpr int kI2cScl = 22;
constexpr int kSpi2Sck = 6;
constexpr int kSpi2Mosi = 7;
constexpr int kSpi2Miso = 8;
constexpr int kMcp3208Cs = 9;
constexpr int kMidiTx = 10;
constexpr int kMidiRx = 11;
constexpr int kLcdPclk = 12;
constexpr int kLcdDe = 13;
constexpr int kLcdHsync = 14;
constexpr int kLcdVsync = 15;
constexpr int kBlPwm = 49;
constexpr int kLedGpio = 48;
constexpr int kPanelIrq = 51;
constexpr int kGate1 = 52;
constexpr int kGate2 = 53;
constexpr int kC6Cs = 26;
constexpr int kC6Hs = 24;
constexpr int kC6Dr = 25;
constexpr int kC6Rst = 27;
constexpr int kBoot = 35;
constexpr int kStrap36 = 36;
constexpr int kVbusDet = 54;
constexpr int kLcdDisp = 50;

struct BoardCore2Config {
  uint32_t cpuMhz;
  uint32_t psramMhz;
  uint32_t sdClockHz;
  uint32_t i2cHz;
  uint32_t i2sSampleRate;
  bool usbHs;
  bool c6OverSpi;
  bool displayRgbStub;
  explicit BoardCore2Config(uint32_t cpu = 400, uint32_t psram = 200,
                            uint32_t sdClock = 40000000, uint32_t i2c = 400000,
                            uint32_t i2s = 48000, bool usbHighSpeed = true,
                            bool c6 = true, bool displayStub = true)
      : cpuMhz(cpu), psramMhz(psram), sdClockHz(sdClock), i2cHz(i2c), i2sSampleRate(i2s),
        usbHs(usbHighSpeed), c6OverSpi(c6), displayRgbStub(displayStub) {}
};

struct BoardCore2Status {
  bool pinsConfigured = false;
  bool displayReady = false;  // TODO(hw): RGB565/DSI backend
  bool sdReady = false;       // SDMMC 4-bit mount
  bool i2cReady = false;
  bool i2sReady = false;      // TODO(hw): I2S driver
  bool midiReady = false;
  bool usbHsReady = false;    // HS PHY + TinyUSB composite
  bool c6Released = false;    // C6 reset released, esp-hosted not linked
  bool c6Ready = false;       // TODO(hw): esp-hosted SPI link
  uint32_t cpuMhz = 0;
  uint32_t psramMhz = 0;
  uint32_t freeHeapBytes = 0;
  uint32_t errors = 0;
};

class BoardCore2 {
 public:
  bool begin();
  void end();
  bool begun() const { return begun_; }
  const BoardCore2Status& status() const { return status_; }
  const BoardCore2Config& config() const { return config_; }
  static const char* name() { return "CORE-2 / ESP32-P4NRW32"; }
  static constexpr int kFunctionalPins = 54;
  static constexpr int kReservedGpio = 1;  // GPIO36 strap
  static constexpr int kTotalGpio = 55;
  static bool pinsUnique();

 private:
  BoardCore2Config config_{};
  BoardCore2Status status_{};
  bool begun_ = false;
};

}  // namespace cores2
}  // namespace hal
}  // namespace bukifon
