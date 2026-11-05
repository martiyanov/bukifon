// SPDX-License-Identifier: GPL-3.0-or-later
// CORE-2 (first SKU, ESP32-P4NRW32) board HAL tests: pin map from
// hardware/core2/pinmap.csv, uniqueness, bus shapes and host-side status.
#include <cstring>

#include "hal/board_cores2.hpp"
#include "test_framework.hpp"

using namespace bukifon::hal::cores2;

TEST(BoardCore2PinmapCountAndUniqueness) {
  CHECK(kPinCount == 55);
  CHECK(BoardCore2::kTotalGpio == 55);
  CHECK(BoardCore2::kFunctionalPins == 54);
  CHECK(BoardCore2::kReservedGpio == 1);  // GPIO36 strap
  CHECK(BoardCore2::pinsUnique());
  CHECK(std::strstr(BoardCore2::name(), "ESP32-P4NRW32") != nullptr);
  INFO("CORE-2 pin map: 55 GPIO signals (54 functional + GPIO36 strap), no duplicates");
}

TEST(BoardCore2I2sI2cSpiMidiPins) {
  CHECK(kI2sMclk == 20);
  CHECK(kI2sBck == 16);
  CHECK(kI2sLrck == 17);
  CHECK(kI2sDacDin == 18);
  CHECK(kI2sAdcDout == 19);
  CHECK(kI2cSda == 21);
  CHECK(kI2cScl == 22);
  CHECK(kSpi2Sck == 6);
  CHECK(kSpi2Mosi == 7);
  CHECK(kSpi2Miso == 8);
  CHECK(kMcp3208Cs == 9);
  CHECK(kMidiTx == 10);
  CHECK(kMidiRx == 11);
  INFO("CORE-2: I2S0 20/16/17/18/19, I2C0 21/22, SPI2 6/7/8, MCP3208 CS 9, MIDI 10/11");
}

TEST(BoardCore2SdAndDisplayPins) {
  CHECK(kSdD0 == 39);
  CHECK(kSdD1 == 40);
  CHECK(kSdD2 == 41);
  CHECK(kSdD3 == 42);
  CHECK(kSdClk == 43);
  CHECK(kSdCmd == 44);
  CHECK(kSdCd == 45);
  CHECK(kLcdPclk == 12);
  CHECK(kLcdDe == 13);
  CHECK(kLcdHsync == 14);
  CHECK(kLcdVsync == 15);
  CHECK(kBlPwm == 49);
  CHECK(kLcdDisp == 50);
  INFO("CORE-2: SDMMC 4-bit 39-44 + CD45; LCD_CAM PCLK/DE/HS/VS 12-15, BL 49, DISP 50");
}

TEST(BoardCore2C6BootAndUsbPins) {
  CHECK(kC6Cs == 26);
  CHECK(kC6Hs == 24);
  CHECK(kC6Dr == 25);
  CHECK(kC6Rst == 27);
  CHECK(kBoot == 35);
  CHECK(kStrap36 == 36);
  CHECK(kVbusDet == 54);
  CHECK(kPanelIrq == 51);
  CHECK(kGate1 == 52);
  CHECK(kGate2 == 53);
  CHECK(kLedGpio == 48);
  INFO("CORE-2: C6 CS/HS/DR/RST 26/24/25/27, BOOT35, STRAP36, VBUS54, IRQ51, GATE 52/53");
}

TEST(BoardCore2HostBeginStatus) {
  BoardCore2 board;
  CHECK(!board.begun());
  CHECK(board.begin());
  CHECK(board.begun());
  const BoardCore2Status& status = board.status();
  CHECK(status.pinsConfigured);
  CHECK(status.cpuMhz == 400);
  CHECK(status.psramMhz == 200);
  // Host has no P4 hardware: display/I2S/USB/C6 are honestly not ready.
  CHECK(!status.displayReady);
  CHECK(!status.i2sReady);
  CHECK(!status.c6Ready);
  board.end();
  CHECK(!board.begun());
  INFO("host begin(): CORE-2 pins configured, RGB/DSI + I2S + C6 reported as TODO(hw)");
}

TEST(BoardCore2ConfigDefaults) {
  BoardCore2Config defaults;
  CHECK(defaults.cpuMhz == 400);
  CHECK(defaults.psramMhz == 200);
  CHECK(defaults.sdClockHz == 40000000u);
  CHECK(defaults.i2cHz == 400000u);
  CHECK(defaults.i2sSampleRate == 48000u);
  CHECK(defaults.usbHs);
  CHECK(defaults.c6OverSpi);
  BoardCore2Config custom(400, 200, 20000000, 400000, 48000, true, true, false);
  CHECK(custom.displayRgbStub == false);
  INFO("CORE-2 config: 400 MHz CPU, 32 MB PSRAM, USB HS, C6 over SPI2, RGB/DSI stub");
}
