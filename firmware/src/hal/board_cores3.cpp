// SPDX-License-Identifier: GPL-3.0-or-later
#include "hal/board_cores3.hpp"

#if defined(ARDUINO)
#include <Arduino.h>
#include <Wire.h>
#if __has_include(<esp_psram.h>)
#include <esp_psram.h>
#define BUKIFON_HAVE_ESP_PSRAM 1
#endif
#if __has_include(<SD_MMC.h>)
#include <SD_MMC.h>
#define BUKIFON_HAVE_SDMMC 1
#endif
#endif

namespace bukifon {
namespace hal {
namespace cores3 {

bool BoardCores3::pinsUnique() {
  const int pins[] = {
      kLcdSck, kLcdMosi, kLcdCs, kLcdDc, kLcdRst, kBlPwm,
      kSpi3Sck, kSpi3Mosi, kSpi3Miso, kMcp3208Cs,
      kSdClk, kSdCmd, kSdD0,
      kI2cSda, kI2cScl,
      kI2sMclk, kI2sBck, kI2sLrck, kI2sDacDin, kI2sAdcDout,
      kMidiTx, kMidiRx, kLedData, kPanelIrq, kGate1, kPwrGood, kBoot};
  const int count = static_cast<int>(sizeof(pins) / sizeof(pins[0]));
  for (int i = 0; i < count; ++i) {
    for (int j = i + 1; j < count; ++j) {
      if (pins[i] == pins[j]) return false;
    }
  }
  return count == kTotalFunctionalPins;
}

bool BoardCores3::begin() {
  status_ = BoardCores3Status{};
  status_.cpuMhz = config_.cpuMhz;
  status_.psramMhz = config_.psramMhz;
  status_.pinsConfigured = pinsUnique();

#if defined(ARDUINO)
  // --- display control pins (SPI2 data path is TODO(hw)) -------------------
  pinMode(kLcdCs, OUTPUT);
  pinMode(kLcdDc, OUTPUT);
  pinMode(kLcdRst, OUTPUT);
  digitalWrite(kLcdCs, HIGH);
  digitalWrite(kLcdDc, HIGH);
  digitalWrite(kLcdRst, HIGH);
  pinMode(kBlPwm, OUTPUT);
  analogWrite(kBlPwm, 0);  // backlight off until the panel is initialised
  // TODO(hw): SPI2.begin(kLcdSck, -1, kLcdMosi, kLcdCs); panel init sequence.
  status_.displayReady = false;

  // --- I2C0: MCP4728 x2 (0x60/0x61), 24C32, PANEL-2 -----------------------
  Wire.begin(kI2cSda, kI2cScl, config_.i2cHz);
  status_.i2cReady = true;

  // --- MIDI UART1 (TRS-A) -------------------------------------------------
  Serial1.begin(31250, SERIAL_8N1, kMidiRx, kMidiTx);
  status_.midiReady = true;

  // --- 1-bit SDMMC --------------------------------------------------------
#if defined(BUKIFON_HAVE_SDMMC)
  SD_MMC.setPins(kSdClk, kSdCmd, kSdD0);
  status_.sdReady = SD_MMC.begin("/sdcard", true, false, config_.sdClockHz / 1000);
#else
  status_.sdReady = false;  // no SD_MMC in this core
#endif

  // --- I2S0 (PCM5102A + PCM1808) -----------------------------------------
  // TODO(hw): i2s_driver_install with MCLK=12.288 MHz, BCK=3.072 MHz, 48 kHz,
  // 2x stereo, internal DMA ring; PCM5102A/PCM1808 are slaves.
  pinMode(kI2sMclk, OUTPUT);
  pinMode(kI2sBck, OUTPUT);
  pinMode(kI2sLrck, OUTPUT);
  pinMode(kI2sDacDin, OUTPUT);
  pinMode(kI2sAdcDout, INPUT);
  status_.i2sReady = false;

  // --- USB FS composite ---------------------------------------------------
  // The Arduino core brings up USB; HID/MIDI/CDC/UAC2 glue is TODO(hw).
  status_.usbFsReady = true;

#if defined(BUKIFON_HAVE_ESP_PSRAM)
  status_.psramDetected = esp_psram_is_initialized();
#else
  status_.psramDetected = false;
#endif
  status_.cpuMhz = getCpuFrequencyMhz();
  status_.freeHeapBytes = ESP.getFreeHeap();
#endif

  begun_ = true;
  return status_.pinsConfigured;
}

void BoardCores3::end() {
  if (!begun_) return;
#if defined(ARDUINO)
  analogWrite(kBlPwm, 0);
#if defined(BUKIFON_HAVE_SDMMC)
  SD_MMC.end();
#endif
#endif
  status_ = BoardCores3Status{};
  begun_ = false;
}

}  // namespace cores3
}  // namespace hal
}  // namespace bukifon
