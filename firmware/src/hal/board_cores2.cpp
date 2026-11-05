// SPDX-License-Identifier: GPL-3.0-or-later
#include "hal/board_cores2.hpp"

#if defined(ARDUINO)
#include <Arduino.h>
#include <SD_MMC.h>
#include <SPI.h>
#include <Wire.h>
#endif

namespace bukifon {
namespace hal {
namespace cores2 {

bool BoardCore2::pinsUnique() {
  for (int i = 0; i < kPinCount; ++i) {
    for (int j = i + 1; j < kPinCount; ++j) {
      if (kPins[i].gpio == kPins[j].gpio) return false;
    }
  }
  return kPinCount == kTotalGpio;
}

bool BoardCore2::begin() {
  status_ = BoardCore2Status{};
  status_.pinsConfigured = pinsUnique();
  status_.cpuMhz = config_.cpuMhz;
  status_.psramMhz = config_.psramMhz;
#if defined(ARDUINO)
  // I2C0 rails/expanders.
  Wire.begin(kI2cSda, kI2cScl, config_.i2cHz);
  status_.i2cReady = true;
  // MIDI UART1.
  Serial1.begin(31250, SERIAL_8N1, kMidiRx, kMidiTx);
  status_.midiReady = true;
  // SDMMC slot0, 4-bit.
  SD_MMC.setPins(kSdClk, kSdCmd, kSdD0, kSdD1, kSdD2, kSdD3);
  status_.sdReady = SD_MMC.begin("/sdcard", false, false, config_.sdClockHz / 1000);
  // Shared SPI2 (MCP3208 + ESP32-C6).
  SPI.begin(kSpi2Sck, kSpi2Miso, kSpi2Mosi, -1);
  pinMode(kMcp3208Cs, OUTPUT);
  digitalWrite(kMcp3208Cs, HIGH);
  pinMode(kC6Cs, OUTPUT);
  digitalWrite(kC6Cs, HIGH);
  // C6 reset: hold low, release; esp-hosted link is TODO(hw).
  pinMode(kC6Rst, OUTPUT);
  pinMode(kC6Hs, INPUT_PULLUP);
  pinMode(kC6Dr, INPUT_PULLUP);
  digitalWrite(kC6Rst, LOW);
  delay(10);
  digitalWrite(kC6Rst, HIGH);
  status_.c6Released = true;
  status_.c6Ready = false;
  // LCD control pins; RGB565/DSI backend is TODO(hw).
  pinMode(kLcdDisp, OUTPUT);
  digitalWrite(kLcdDisp, HIGH);
  pinMode(kBlPwm, OUTPUT);
  analogWrite(kBlPwm, 0);
  status_.displayReady = false;
  // I2S0 pins (driver TODO(hw)).
  pinMode(kI2sMclk, OUTPUT);
  pinMode(kI2sBck, OUTPUT);
  pinMode(kI2sLrck, OUTPUT);
  pinMode(kI2sDacDin, OUTPUT);
  pinMode(kI2sAdcDout, INPUT);
  status_.i2sReady = false;
  // USB HS is a dedicated PHY; TinyUSB composite is TODO(hw).
  status_.usbHsReady = true;
  status_.freeHeapBytes = ESP.getFreeHeap();
  status_.cpuMhz = getCpuFrequencyMhz();
#endif
  begun_ = true;
  return status_.pinsConfigured;
}

void BoardCore2::end() {
  if (!begun_) return;
#if defined(ARDUINO)
  analogWrite(kBlPwm, 0);
  SD_MMC.end();
#endif
  status_ = BoardCore2Status{};
  begun_ = false;
}

}  // namespace cores2
}  // namespace hal
}  // namespace bukifon
