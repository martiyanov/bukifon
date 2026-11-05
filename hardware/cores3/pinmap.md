# CORE-S3 — пин-карта (PRE-FREEZE / DO NOT FABRICATE)

ESP32-S3-WROOM-1-N16R8: 16 MB flash, 8 MB octal PSRAM. FPGA нет;
GPIO33-37 заняты octal PSRAM, GPIO26-32 flash, GPIO19/20 — USB FS.
Полезных на модуле: **31** (GPIO0-18, 21, 38-48; 43/44 = RXD0/TXD0).

| # | Сигнал | GPIO | Периферия | Напр. | Примечание |
|---|---|---:|---|---|---|
| 1 | `LCD_SCK` | GPIO12 | SPI2 FSPICLK (IOMUX) | out | SPI display prototytpe variant |
| 2 | `LCD_MOSI` | GPIO11 | SPI2 FSPID (IOMUX) | out |  |
| 3 | `LCD_CS` | GPIO10 | SPI2 FSPICS0 | out |  |
| 4 | `LCD_DC` | GPIO9 | GPIO | out |  |
| 5 | `LCD_RST` | GPIO8 | GPIO | out |  |
| 6 | `BL_PWM` | GPIO21 | LEDC PWM | out | backlight PWM -> BL boost |
| 7 | `SPI3_SCK` | GPIO4 | SPI3 SCK (matrix) | out | MCP3208, 10 MHz |
| 8 | `SPI3_MOSI` | GPIO5 | SPI3 MOSI | out |  |
| 9 | `SPI3_MISO` | GPIO6 | SPI3 MISO | in | MCP3208 DOUT |
| 10 | `MCP3208_CS` | GPIO7 | SPI3 CS0 | out |  |
| 11 | `SD_CLK` | GPIO15 | SDMMC CLK | out | microSD 1-bit SDMMC |
| 12 | `SD_CMD` | GPIO14 | SDMMC CMD | bidir |  |
| 13 | `SD_D0` | GPIO13 | SDMMC D0 | bidir |  |
| 14 | `I2C0_SDA` | GPIO16 | I2C0 SDA | bidir | MCP4728 x2, 24C32, PANEL-2 |
| 15 | `I2C0_SCL` | GPIO17 | I2C0 SCL | out | 400 kHz |
| 16 | `I2S_MCLK` | GPIO18 | I2S0 MCLK | out | 12.288 MHz = 256 fs |
| 17 | `I2S_BCK` | GPIO1 | I2S0 BCK | out | 3.072 MHz |
| 18 | `I2S_LRCK` | GPIO2 | I2S0 WS | out | 48 kHz |
| 19 | `I2S_DAC_DIN` | GPIO38 | I2S0 SD_OUT | out | PCM5102A |
| 20 | `I2S_ADC_DOUT` | GPIO39 | I2S0 SD_IN | in | PCM1808 |
| 21 | `MIDI_TX` | GPIO40 | UART1 TX (matrix) | out | 74HCT125 |
| 22 | `MIDI_RX` | GPIO41 | UART1 RX (matrix) | in | 6N137 |
| 23 | `LED_DATA` | GPIO42 | RMT | out | WS2812 (level shifter on PANEL-2) |
| 24 | `PANEL_IRQ` | GPIO47 | GPIO in | in | 4x MCP23017 INTA (10k PU) |
| 25 | `GATE1_GPIO` | GPIO48 | GPIO | out | 2N7000 gate out (GATE2 dropped) |
| 26 | `PWR_GOOD` | GPIO3 | GPIO in | in | PWR-2 supervisor (100k PU) |
| 27 | `BOOT` | GPIO0 | GPIO / strapping | in | BOOT button (USB-JTAG also available) |

**Занято: 27 / 31; свободно: 4 (GPIO43, GPIO44, GPIO45, GPIO46) — 13 % запас.**

## Разъёмы (канон PANEL-2 rev.2 + PWR-2)

### J14 (IDC-26) — аналоговое поле PANEL-2 J14

| Pin | Цепь | Pin | Цепь |
|---|---|---|---|
| 1 | `CVOUT1` | 2 | `AGND` |
| 3 | `CVOUT2` | 4 | `AGND` |
| 5 | `CVOUT3` | 6 | `AGND` |
| 7 | `CVOUT4` | 8 | `AGND` |
| 9 | `CVIN1` | 10 | `AGND` |
| 11 | `CVIN2` | 12 | `AGND` |
| 13 | `CVIN3` | 14 | `AGND` |
| 15 | `CVIN4` | 16 | `AGND` |
| 17 | `GATE1` | 18 | `AGND` |
| 19 | `NC` | 20 | `AGND` |
| 21 | `FADER1` | 22 | `AGND` |
| 23 | `FADER2` | 24 | `AGND` |
| 25 | `EN_LED5` | 26 | `AGND` |

### J15 (FFC-40) — LCD: SPI-подмножество на разъёме PANEL-2 J12

| Pin | Цепь | Pin | Цепь |
|---|---|---|---|
| 1 | `DGND` | 2 | `DGND` |
| 3 | `LCD_SCK` | 4 | `LCD_MOSI` |
| 5 | `LCD_CS` | 6 | `LCD_DC` |
| 7 | `LCD_RST` | 8 | `BL_PWM` |
| 9 | `3V3_PANEL` | 10 | `DGND` |
| 11 | `BL_20V` | 12 | `BL_CATHODE` |
| 13 | `DGND` | 14 | `DGND` |
| 15 | `DGND` | 16 | `DGND` |
| 17 | `DGND` | 18 | `DGND` |
| 19 | `DGND` | 20 | `DGND` |
| 21 | `DGND` | 22 | `DGND` |
| 23 | `DGND` | 24 | `DGND` |
| 25 | `DGND` | 26 | `DGND` |
| 27 | `3V3_PANEL` | 28 | `3V3_PANEL` |
| 29 | `DGND` | 30 | `DGND` |
| 31 | `DGND` | 32 | `DGND` |
| 33 | `DGND` | 34 | `DGND` |
| 35 | `DGND` | 36 | `DGND` |
| 37 | `DGND` | 38 | `DGND` |
| 39 | `DGND` | 40 | `DGND` |

### J16 (IDC-16) — цифра/питание PANEL-2 J13

| Pin | Цепь | Pin | Цепь |
|---|---|---|---|
| 1 | `I2C0_SDA` | 2 | `DGND` |
| 3 | `I2C0_SCL` | 4 | `DGND` |
| 5 | `PANEL_IRQ` | 6 | `DGND` |
| 7 | `LED_DATA` | 8 | `DGND` |
| 9 | `5V_LED` | 10 | `DGND` |
| 11 | `3V3_PANEL` | 12 | `DGND` |
| 13 | `5V_LED` | 14 | `DGND` |
| 15 | `EN_RAILS` | 16 | `LED_RET` |

### J17 (IDC-20) — PWR-2 J3 (силовой)

| Pin | Цепь | Pin | Цепь |
|---|---|---|---|
| 1 | `VSYS` | 2 | `VSYS` |
| 3 | `BATT_P` | 4 | `BATT_P` |
| 5 | `12V_EXT` | 6 | `12V_EXT` |
| 7 | `PGND` | 8 | `PGND` |
| 9 | `N12_EXT` | 10 | `N12_EXT` |
| 11 | `PGND` | 12 | `PGND` |
| 13 | `5V_EXT` | 14 | `5V_EXT` |
| 15 | `PGND` | 16 | `PGND` |
| 17 | `5V_LED` | 18 | `LED_RET` |
| 19 | `PGND` | 20 | `PGND` |

### J18 (IDC-12) — PWR-2 J4 (управление)

| Pin | Цепь | Pin | Цепь |
|---|---|---|---|
| 1 | `BATT_MON_RAW` | 2 | `NTC_PACK` |
| 3 | `I2C0_SDA` | 4 | `I2C0_SCL` |
| 5 | `FUEL_ALRT` | 6 | `PWR_GOOD` |
| 7 | `EN_BUS12` | 8 | `EN_N12` |
| 9 | `EN_LED5` | 10 | `EN_5V` |
| 11 | `PGND` | 12 | `PGND` |

## PANEL-2 expanders (0x23) — занятые линии

| Линия 0x23 | Назначение |
|---|---|
| GPA0..GPA6 | матрица COL0..6 |
| GPB0..GPB5 | матрица ROW0..5 |
| GPA7 | EN_RAILS (PWR-2 EN_BUS12/N12/5V) |
| GPB6 | EN_LED5 |
| GPB7 | GATE_IN_CLEAN (PANEL-2) |

Свободных линий 0x23 **нет** (16/16). Поэтому GATE OUT / LCD DISP / SD-detect
не могут быть на MCP23017 без второго чипа (запрещено ТЗ); LCD DISP — к +3V3,
GATE2 в CORE-S3 не разводится, SD-detect отсутствует (SD только 1-bit).
