// SPDX-License-Identifier: GPL-3.0-or-later
// CORE-S3 board HAL tests: pin map contract (hardware/cores3/pinmap.csv),
// uniqueness, bus shapes, host-side begin/status behaviour and config.
#include "hal/board_cores3.hpp"
#include "test_framework.hpp"

using namespace bukifon::hal::cores3;

TEST(BoardCores3DisplayAndBacklightPins) {
  CHECK(kLcdSck == 12);
  CHECK(kLcdMosi == 11);
  CHECK(kLcdCs == 10);
  CHECK(kLcdDc == 9);
  CHECK(kLcdRst == 8);
  CHECK(kBlPwm == 21);
  CHECK(BoardCores3::kDisplayPins == 6);
  INFO("CORE-S3 display: SPI2 SCK=12 MOSI=11 CS=10 DC=9 RST=8, BL_PWM=21");
}

TEST(BoardCores3SdI2sI2cMidiPins) {
  CHECK(kSdClk == 15);
  CHECK(kSdCmd == 14);
  CHECK(kSdD0 == 13);
  CHECK(kI2cSda == 16);
  CHECK(kI2cScl == 17);
  CHECK(kI2sMclk == 18);
  CHECK(kI2sBck == 1);
  CHECK(kI2sLrck == 2);
  CHECK(kI2sDacDin == 38);
  CHECK(kI2sAdcDout == 39);
  CHECK(kMidiTx == 40);
  CHECK(kMidiRx == 41);
  CHECK(kSpi3Sck == 4);
  CHECK(kSpi3Mosi == 5);
  CHECK(kSpi3Miso == 6);
  CHECK(kMcp3208Cs == 7);
  INFO("CORE-S3: SD 1-bit 15/14/13, I2C 16/17, I2S0 18/1/2/38/39, MIDI UART1 40/41, SPI3 4/5/6/7");
}

TEST(BoardCores3PanelGatePowerPins) {
  CHECK(kLedData == 42);
  CHECK(kPanelIrq == 47);
  CHECK(kGate1 == 48);
  CHECK(kPwrGood == 3);
  CHECK(kBoot == 0);
  CHECK(BoardCores3::kPanelPins == 1);
  INFO("CORE-S3: WS2812=42, PANEL_IRQ=47, GATE1=48, PWR_GOOD=3, BOOT=0 (GATE2 not routed)");
}

TEST(BoardCores3PinsUnique) {
  CHECK(BoardCores3::pinsUnique());
  CHECK(BoardCores3::kTotalFunctionalPins == 27);
  CHECK(BoardCores3::kSdPins == 3);
  CHECK(BoardCores3::kI2sPins == 5);
  CHECK(BoardCores3::kMidiPins == 2);
  CHECK(BoardCores3::kI2cPins == 2);
  CHECK(BoardCores3::kDisplayPins + BoardCores3::kSdPins + BoardCores3::kI2sPins +
            BoardCores3::kI2cPins + BoardCores3::kMidiPins + BoardCores3::kPanelPins +
            BoardCores3::kMemoryProfilePins + 1 /*GATE1*/ + 1 /*PWR_GOOD*/ + 1 /*BOOT*/ +
            4 /*SPI3*/ + 1 /*BL*/ ==
        27);
  INFO("CORE-S3 pin map: 27 functional GPIOs, no duplicates");
}

TEST(BoardCores3HostBeginStatus) {
  BoardCores3 board;
  CHECK(!board.begun());
  CHECK(board.begin());
  CHECK(board.begun());
  const BoardCores3Status& status = board.status();
  CHECK(status.pinsConfigured);
  CHECK(status.cpuMhz == 240);
  CHECK(status.psramMhz == 80);
  // Host has no hardware: display/I2S/SD/USB are honestly not ready.
  CHECK(!status.displayReady);
  CHECK(!status.i2sReady);
  CHECK(!status.usbFsReady);
  board.end();
  CHECK(!board.begun());
  INFO("host begin(): pins configured, hardware paths reported as not ready (TODO(hw))");
}

TEST(BoardCores3ConfigAndName) {
  BoardCores3Config defaults;
  CHECK(defaults.cpuMhz == 240);
  CHECK(defaults.psramMhz == 80);
  CHECK(defaults.lcdSpiHz == 80000000u);
  CHECK(defaults.i2sSampleRate == 48000u);
  CHECK(defaults.usbFsStereoUac);
  BoardCores3Config custom(240, 80, 40000000, 10000000, 400000, 48000, true);
  CHECK(custom.lcdSpiHz == 40000000u);
  CHECK(custom.sdClockHz == 10000000u);
  CHECK(std::strstr(BoardCores3::name(), "ESP32-S3-N16R8") != nullptr);
  INFO("CORE-S3 config: 240 MHz CPU, octal PSRAM 80 MHz, SPI2 80 MHz, USB FS stereo UAC2");
}
