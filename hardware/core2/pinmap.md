# CORE-2 — карта пинов и распределение ресурсов

> **STATUS: PRE-FREEZE / DO NOT FABRICATE.** Схема — исследовательская,
> не для заказа плат до бенчмарка P1 и подписи требований (spec/90).
> Машинно-читаемая версия: [`pinmap.csv`](pinmap.csv);
> проверка: `python3 tools/check_pinmap.py`.

**MCU:** ESP32-P4NRW32 (ESP32-P4, 32 MB PSRAM in package, QFN104). **Слот:** J-MCU: 2x32 (64 pin, 2.54 mm) MCU-module slot defined by this board (pre-freeze).
Источник фактов: ESP32-P4 Series Datasheet v0.7 (Espressif) —
55 GPIO, boot strapping GPIO35…GPIO38, USB HS PHY на выделенных USB_DM/USB_DP,
SDMMC slot0 на падах GPIO39…GPIO48, LCD_CAM (parallel RGB 16 бит) и 3× I2S через GPIO matrix.

## 1. Сводка

| Параметр | Значение |
|---|---|
| Всего GPIO у ESP32-P4 | 55 (GPIO0…GPIO54) |
| Занято сигналами платы | **54** |
| Зарезервировано (USB FS/JTAG, strapping) | **1** |
| Свободно | **0** (0.0 %) |
| Конфликтов GPIO | **0** (проверено `check_pinmap.py`) |
| Конфликтов boot/strapping | **0** (GPIO35 = BOOT с 10k PU; GPIO36 = 10k PD; GPIO37/38 = UART0) |
| Резерв GPIO | **фактически отсутствует** (1 свободный GPIO54) — расширение только по I2C/SPI |

Свободные GPIO: нет.

**Резерв GPIO — отсутствует (1 из 55 = 1.8 %).** Это осознанное решение PRE-FREEZE:
16 энкодеров и матрица 42 клавиш вынесены на 4× MCP23017 (I2C) на PANEL-2,
а цифровое расширение модулей — на отдельный J-DIG-EXP (TDM/I2S + SPI mailbox, R-22).
Если потребуется ещё GPIO — только ревизия с расширителем (MCP23S17 по SPI) или
перенос части функций на PANEL-2; в v1.0-rc места нет.
Расширение (энкодеры, матрица клавиш) — не на GPIO, а по I2C (4× MCP23017 на PANEL-2, адреса 0x20/0x21/0x22/0x23, 48 линий энкодеров + 13 матрицы = 61) — см. §5.

## 2. Занятые GPIO

| # | Сигнал | GPIO | Периферия | Напряжение | Направление | Подтяжка | Boot-состояние | Слот J-MCU | Разъём | Примечание |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `SD_D0` | GPIO39 | SDMMC SLOT0 D0 | 3.3 | bidir | 10k PU | high | 23 | J-SD.DAT0 | IO MUX SD1_CDATA0 |
| 2 | `SD_D1` | GPIO40 | SDMMC SLOT0 D1 | 3.3 | bidir | 10k PU | high | 24 | J-SD.DAT1 | IO MUX SD1_CDATA1 |
| 3 | `SD_D2` | GPIO41 | SDMMC SLOT0 D2 | 3.3 | bidir | 10k PU | high | 25 | J-SD.DAT2 | IO MUX SD1_CDATA2 |
| 4 | `SD_D3` | GPIO42 | SDMMC SLOT0 D3 | 3.3 | bidir | 10k PU | high | 26 | J-SD.DAT3/CD | IO MUX SD1_CDATA3 |
| 5 | `SD_CLK` | GPIO43 | SDMMC SLOT0 CLK | 3.3 | out | none | low | 27 | J-SD.CLK | IO MUX SD1_CCLK |
| 6 | `SD_CMD` | GPIO44 | SDMMC SLOT0 CMD | 3.3 | bidir | 10k PU | high | 28 | J-SD.CMD | IO MUX SD1_CCMD |
| 7 | `SD_CD` | GPIO45 | GPIO in (card detect) | 3.3 | in | 10k PU | high | 29 | J-SD.DET | card detect switch to GND |
| 8 | `I2S_MCLK` | GPIO20 | I2S0 MCLK out | 3.3 | out | none | low | 30 | U9.SCK / U10.SCKI | 256fs = 12.288 MHz @48k |
| 9 | `I2S_BCK` | GPIO16 | I2S0 BCK out | 3.3 | out | none | low | 31 | U9.BCK / U10.BCK | 64fs = 3.072 MHz @48k |
| 10 | `I2S_LRCK` | GPIO17 | I2S0 WS/LRCK out | 3.3 | out | none | low | 32 | U9.LRCK / U10.LRCK | 48 kHz |
| 11 | `I2S_DAC_DIN` | GPIO18 | I2S0 SD out | 3.3 | out | none | low | 33 | U9.DIN | to PCM5102A |
| 12 | `I2S_ADC_DOUT` | GPIO19 | I2S0 SD in | 3.3 | in | none | high | 34 | U10.DOUT | from PCM1808 |
| 13 | `I2C0_SDA` | GPIO21 | I2C0 SDA | 3.3 | bidir | 2.2k PU | high | 35 | J-PANEL.5 / J-LCD.34 / U4/U5/U11/U12 | MCP4728 x2, 24C32, MCP23017 x4 (0x20..0x23) |
| 14 | `I2C0_SCL` | GPIO22 | I2C0 SCL | 3.3 | out | 2.2k PU | high | 36 | J-PANEL.7 / J-LCD.35 / U4/U5/U11/U12 | 400 kHz |
| 15 | `SPI2_SCK` | GPIO6 | GP-SPI2 SCK | 3.3 | out | none | low | 37 | U6.CLK / U-C6.SCK | shared bus, per-device CS |
| 16 | `SPI2_MOSI` | GPIO7 | GP-SPI2 MOSI | 3.3 | out | none | low | 38 | U6.DIN / U-C6.MOSI |  |
| 17 | `SPI2_MISO` | GPIO8 | GP-SPI2 MISO | 3.3 | in | none | high | 39 | U6.DOUT / U-C6.MISO |  |
| 18 | `MCP3208_CS` | GPIO9 | GP-SPI2 CS0 | 3.3 | out | 10k PU | high | 40 | U6.CS | active low |
| 19 | `MIDI_TX` | GPIO10 | UART1 TX | 3.3 | out | none | high | 41 | U11.2 (74HCT125 A) | via 74HCT125 to TRS OUT |
| 20 | `MIDI_RX` | GPIO11 | UART1 RX | 3.3 | in | 4.7k PU | high | 42 | U7.VO (6N137) | from TRS IN |
| 21 | `UART0_TX` | GPIO37 | UART0 TX | 3.3 | out | none | high | 21 | J-UART.2 | boot log / testpoint |
| 22 | `UART0_RX` | GPIO38 | UART0 RX | 3.3 | in | none | high | 22 | J-UART.3 | testpoint |
| 23 | `LCD_PCLK` | GPIO12 | LCD_CAM PCLK | 3.3 | out | none | low | 43 | J-LCD.7 |  |
| 24 | `LCD_DE` | GPIO13 | LCD_CAM DE | 3.3 | out | none | low | 44 | J-LCD.9 |  |
| 25 | `LCD_HSYNC` | GPIO14 | LCD_CAM HSYNC | 3.3 | out | none | low | 45 | J-LCD.11 |  |
| 26 | `LCD_VSYNC` | GPIO15 | LCD_CAM VSYNC | 3.3 | out | none | low | 46 | J-LCD.13 |  |
| 27 | `LCD_B0` | GPIO0 | LCD_CAM data B0 | 3.3 | out | none | low | 47 | J-LCD.15 | RGB565: B0..B4 |
| 28 | `LCD_B1` | GPIO1 | LCD_CAM data B1 | 3.3 | out | none | low | 48 | J-LCD.16 |  |
| 29 | `LCD_B2` | GPIO2 | LCD_CAM data B2 | 3.3 | out | none | low | 49 | J-LCD.17 |  |
| 30 | `LCD_B3` | GPIO3 | LCD_CAM data B3 | 3.3 | out | none | low | 50 | J-LCD.18 |  |
| 31 | `LCD_B4` | GPIO4 | LCD_CAM data B4 | 3.3 | out | none | low | 51 | J-LCD.19 |  |
| 32 | `LCD_G0` | GPIO5 | LCD_CAM data G0 | 3.3 | out | none | low | 52 | J-LCD.20 | G0..G5 |
| 33 | `LCD_G1` | GPIO23 | LCD_CAM data G1 | 3.3 | out | none | low | 53 | J-LCD.21 |  |
| 34 | `LCD_G2` | GPIO28 | LCD_CAM data G2 | 3.3 | out | none | low | 54 | J-LCD.22 |  |
| 35 | `LCD_G3` | GPIO29 | LCD_CAM data G3 | 3.3 | out | none | low | 55 | J-LCD.23 |  |
| 36 | `LCD_G4` | GPIO30 | LCD_CAM data G4 | 3.3 | out | none | low | 56 | J-LCD.24 |  |
| 37 | `LCD_G5` | GPIO31 | LCD_CAM data G5 | 3.3 | out | none | low | 57 | J-LCD.25 |  |
| 38 | `LCD_R0` | GPIO32 | LCD_CAM data R0 | 3.3 | out | none | low | 58 | J-LCD.26 | R0..R4 |
| 39 | `LCD_R1` | GPIO33 | LCD_CAM data R1 | 3.3 | out | none | low | 59 | J-LCD.27 |  |
| 40 | `LCD_R2` | GPIO34 | LCD_CAM data R2 | 3.3 | out | none | low | 60 | J-LCD.28 |  |
| 41 | `LCD_R3` | GPIO46 | LCD_CAM data R3 | 3.3 | out | none | low | 61 | J-LCD.29 |  |
| 42 | `LCD_R4` | GPIO47 | LCD_CAM data R4 | 3.3 | out | none | low | 62 | J-LCD.30 |  |
| 43 | `BL_PWM` | GPIO49 | LEDC PWM | 3.3 | out | none | low | 16 | J-LCD.31 | backlight PWM -> panel BL driver |
| 44 | `LED_GPIO` | GPIO48 | RMT TX (WS2812) | 3.3 -> 5 V | out | none | low | 15 | U-1G125.A | level shifter + 330R -> J-PANEL.11 LED_DATA |
| 45 | `PANEL_IRQ` | GPIO51 | GPIO in | 3.3 | in | 10k PU | high | 18 | J-PANEL.9 / J-LCD.36 | MCP23017 INTA (open drain) |
| 46 | `GATE1_GPIO` | GPIO52 | GPIO out (2N7000) | 5.0 (open drain) | out | none | low | 19 | J-PANEL.25 / BUS | 0/5 V gate, 4.7k PU to +5V_BUS |
| 47 | `GATE2_GPIO` | GPIO53 | GPIO out (2N7000) | 5.0 (open drain) | out | none | low | 20 | J-PANEL.26 / BUS | 0/5 V gate |
| 48 | `C6_CS` | GPIO26 | GP-SPI2 CS1 | 3.3 | out | 10k PU | high | 10 | U-C6.SPI_CS | C6 select (shared SPI2) |
| 49 | `C6_HS` | GPIO24 | GPIO (handshake) | 3.3 | bidir | 10k PU | high | 11 | U-C6.HANDSHAKE | esp-hosted SPI handshake |
| 50 | `C6_DR` | GPIO25 | GPIO (data ready IRQ) | 3.3 | in | 10k PU | high | 12 | U-C6.DATA_READY | GPIO25 has USB_PU strap at reset (kept high) |
| 51 | `C6_RST` | GPIO27 | GPIO out (C6 reset) | 3.3 | out | 10k PD | low | 13 | U-C6.EN | resets C6 at power-up; released by firmware |
| 52 | `BOOT` | GPIO35 | boot strapping (GPIO35) | 3.3 | in (strap) | 10k PU + button to GND | high (SPI boot) | 8 | SW-BOOT | low at reset = joint download boot (USB HS / UART0) |
| 53 | `VBUS_DET` | GPIO54 | GPIO in (VBUS detect) | 3.3 | in | 100k/100k divider | low | 14 | D1/R | USB-C attach detect (100k/100k + 100nF) |
| 54 | `LCD_DISP` | GPIO50 | GPIO out (LCD power/enable) | 3.3 | out | none | low | 17 | J-LCD.37 | display enable; final controllable GPIO |

## 3. Выделенные и не-GPIO выводы модуля

| Сигнал | GPIO | Периферия | Напряжение | Направление | Boot | Слот | Разъём |
|---|---|---|---|---|---|---|---|
| `USB_HS_DP` | — | USB 2.0 HS OTG D+ (dedicated pin 50) | USB | bidir | USB | 6 | J-USB.A6/B6 |
| `USB_HS_DM` | — | USB 2.0 HS OTG D- (dedicated pin 49) | USB | bidir | USB | 7 | J-USB.A7/B7 |
| `CHIP_PU` | — | reset (CHIP_PU) | 3.3 | in | high | 5 | SW-RESET |
| `3V3_MCU` | — | MCU/PSRAM supply | 3.3 | power | - | 3 | U26 out |
| `3V3_MCU` | — | MCU/PSRAM supply | 3.3 | power | - | 4 | U26 out |
| `GND` | — | ground | 0 | power | - | 1 | GND |
| `GND` | — | ground | 0 | power | - | 2 | GND |
| `GND` | — | ground | 0 | power | - | 63 | GND |
| `GND` | — | ground | 0 | power | - | 64 | GND |

## 4. Зарезервированные GPIO

| GPIO | Причина |
|---|---|
| GPIO36 | boot strapping GPIO36 - 10k PU (must be 1 for joint download boot) |

## 5. PANEL-2: расширители I2C (на плате панели)

| Адрес | Позиция | Функция | Распиновка |
|---|---|---|---|
| 0x20 | U-P1 | ENC1..ENC8 A/B (16 lines) | GPA0..GPA7 = ENC1_A..ENC8_A<br>GPB0..GPB7 = ENC1_B..ENC8_B<br>INTA -> PANEL_IRQ |
| 0x21 | U-P2 | ENC9..ENC16 A/B (16 lines) | GPA0..GPA7 = ENC9_A..ENC16_A<br>GPB0..GPB7 = ENC9_B..ENC16_B<br>INTA -> PANEL_IRQ |
| 0x22 | U-P3 | 16 encoder push buttons (16 lines) | GPA0..GPA7 = ENC1_PUSH..ENC8_PUSH<br>GPB0..GPB7 = ENC9_PUSH..ENC16_PUSH<br>INTA -> PANEL_IRQ |
| 0x23 | U-P4 | 42-key matrix 6 rows x 7 cols (13 lines, 3 spare) | GPA0..GPA6 = COL0..COL6 (inputs, 10k PU)<br>GPB0..GPB5 = ROW0..ROW5 (outputs, scan)<br>INTA -> PANEL_IRQ (key press) |

I2C0 (GPIO21/22) — общая шина: 2× MCP4728 (0x60/0x61), 24C32 (0x57),
4× MCP23017 (0x20/0x21/0x22/0x23): 48 линий энкодеров (16× A/B/push) + 13 линий матрицы 6×7 = 61; 3 линии резерв. Наружу — только SDA/SCL/INT (wire-OR INTA). Подтяжки I2C 2.2 к и INT 10 к — на CORE-2; ёмкость шины ≤ 200 pF.

## 6. Фейдеры и джеки

| Элемент | Цепь | Схема |
|---|---|---|
| FADER1 | `FADER1` | 1k + 100nF -> MCP3208 CH2 |
| FADER2 | `FADER2` | 1k + 100nF -> MCP3208 CH3 |
| CV OUT 1 | `CVOUT1` | MCP4728#1 CHA -> TL074 x4.883 -> 1k + BAT54S (panel, J-PANEL.21) |
| CV OUT 2 | `CVOUT2` | MCP4728#1 CHB -> TL074 x4.883 -> 1k + BAT54S (panel) |
| CV OUT 3 | `CVOUT3` | MCP4728#1 CHC -> TL074 x4.883 -> 1k + BAT54S (panel) |
| CV OUT 4 | `CVOUT4` | MCP4728#1 CHD -> TL074 x4.883 -> 1k + BAT54S (panel) |
| CV OUT 5 | `CVOUT5` | MCP4728#2 CHA -> TL074 x4.883 -> 1k + BAT54S (panel, J-PANEL.4) |
| CV OUT 6 | `CVOUT6` | MCP4728#2 CHB -> TL074 x4.883 -> 1k + BAT54S (panel, J-PANEL.10) |
| CV IN 1 | `CVIN1` | 100k/16.5k + 1.65 V offset -> BAT54S -> 1k/100nF -> MCP3208 CH0 (panel) |
| CV IN 2 | `CVIN2` | 100k/16.5k + 1.65 V offset -> BAT54S -> 1k/100nF -> MCP3208 CH1 (panel) |
| GATE OUT 1 | `GATE1` | 2N7000 open-drain + 4.7k to +5V + 1k (panel) |
| GATE OUT 2 | `GATE2` | 2N7000 open-drain + 4.7k to +5V + 1k (panel) |
| LINE OUT L | `AUDOUT_L` | rear 3.5 mm: PCM5102A OUTL -> 10uF -> TL072 -> 100R (TB1.1) |
| LINE OUT R | `AUDOUT_R` | rear 3.5 mm: PCM5102A OUTR -> 10uF -> TL072 -> 100R (TB1.2) |
| PHONES L/R | `PHONES_L/R` | rear 3.5 mm stereo, TL072 buffer -> 100R (TB1.4/5) |
| AUDIO IN L | `AUDIN_L` | rear 3.5 mm -> 1k + BAT54S + 100pF -> 1uF -> PCM1808 VINL (TB1.7) |
| AUDIO IN R | `AUDIN_R` | rear 3.5 mm -> 1k + BAT54S + 100pF -> 1uF -> PCM1808 VINR (TB1.8) |
| MIDI IN | `MIDI_IN_T/R` | 6N137 + 220R (rear TRS-A, TB2.1/2) |
| MIDI OUT | `MIDI_OUT_T/R` | 74HCT125 + 33R/220R (rear TRS-A, TB2.4/5) |
| DC 12 V | `12V_EXT` | rear 5.5/2.1 mm, from PWR-2 / external PSU (TB2.7/8), diode-OR to +12V |
| EXPRESSION | `EXPR` | rear 6.35/3.5 mm, 3V3->pot->tip; RC 1k/100nF -> MCP3208 CH4 (TB2.9/10) |

## 7. Разъёмы (полные таблицы)

### J-MCU — слот MCU-модуля (2×32, 64 pin)

| Pin | Цепь |
|---|---|
| 1 | `GND` |
| 2 | `GND` |
| 3 | `3V3_MCU` |
| 4 | `3V3_MCU` |
| 5 | `CHIP_PU` |
| 6 | `USB_HS_DP` |
| 7 | `USB_HS_DM` |
| 8 | `BOOT` |
| 9 | `STRAP36` |
| 10 | `C6_CS` |
| 11 | `C6_HS` |
| 12 | `C6_DR` |
| 13 | `C6_RST` |
| 14 | `VBUS_DET` |
| 15 | `LED_GPIO` |
| 16 | `BL_PWM` |
| 17 | `LCD_DISP` |
| 18 | `PANEL_IRQ` |
| 19 | `GATE1_GPIO` |
| 20 | `GATE2_GPIO` |
| 21 | `UART0_TX` |
| 22 | `UART0_RX` |
| 23 | `SD_D0` |
| 24 | `SD_D1` |
| 25 | `SD_D2` |
| 26 | `SD_D3` |
| 27 | `SD_CLK` |
| 28 | `SD_CMD` |
| 29 | `SD_CD` |
| 30 | `I2S_MCLK` |
| 31 | `I2S_BCK` |
| 32 | `I2S_LRCK` |
| 33 | `I2S_DAC_DIN` |
| 34 | `I2S_ADC_DOUT` |
| 35 | `I2C0_SDA` |
| 36 | `I2C0_SCL` |
| 37 | `SPI2_SCK` |
| 38 | `SPI2_MOSI` |
| 39 | `SPI2_MISO` |
| 40 | `MCP3208_CS` |
| 41 | `MIDI_TX` |
| 42 | `MIDI_RX` |
| 43 | `LCD_PCLK` |
| 44 | `LCD_DE` |
| 45 | `LCD_HSYNC` |
| 46 | `LCD_VSYNC` |
| 47 | `LCD_B0` |
| 48 | `LCD_B1` |
| 49 | `LCD_B2` |
| 50 | `LCD_B3` |
| 51 | `LCD_B4` |
| 52 | `LCD_G0` |
| 53 | `LCD_G1` |
| 54 | `LCD_G2` |
| 55 | `LCD_G3` |
| 56 | `LCD_G4` |
| 57 | `LCD_G5` |
| 58 | `LCD_R0` |
| 59 | `LCD_R1` |
| 60 | `LCD_R2` |
| 61 | `LCD_R3` |
| 62 | `LCD_R4` |
| 63 | `GND` |
| 64 | `GND` |

### J-PANEL — PANEL-2 (IDC-26): I2C, энкодеры*, матрица*, фейдеры, CV, GATE, LED

| Pin | Цепь |
|---|---|
| 1 | `3V3` |
| 2 | `DGND` |
| 3 | `5V` |
| 4 | `CVOUT5` |
| 5 | `I2C0_SDA` |
| 6 | `DGND` |
| 7 | `I2C0_SCL` |
| 8 | `DGND` |
| 9 | `PANEL_IRQ` |
| 10 | `CVOUT6` |
| 11 | `LED_DATA` |
| 12 | `DGND` |
| 13 | `FADER1` |
| 14 | `AGND` |
| 15 | `FADER2` |
| 16 | `AGND` |
| 17 | `CVIN1` |
| 18 | `AGND` |
| 19 | `CVIN2` |
| 20 | `AGND` |
| 21 | `CVOUT1` |
| 22 | `CVOUT2` |
| 23 | `CVOUT3` |
| 24 | `CVOUT4` |
| 25 | `GATE1` |
| 26 | `GATE2` |

### J-LCD — дисплей 800×480 (FFC-40, 0.5 мм): RGB565 + синхро + BL/DISP + AUDIO IN

| Pin | Цепь |
|---|---|
| 1 | `5V` |
| 2 | `5V` |
| 3 | `DGND` |
| 4 | `DGND` |
| 5 | `3V3` |
| 6 | `DGND` |
| 7 | `LCD_PCLK` |
| 8 | `DGND` |
| 9 | `LCD_DE` |
| 10 | `DGND` |
| 11 | `LCD_HSYNC` |
| 12 | `DGND` |
| 13 | `LCD_VSYNC` |
| 14 | `DGND` |
| 15 | `LCD_B0` |
| 16 | `LCD_B1` |
| 17 | `LCD_B2` |
| 18 | `LCD_B3` |
| 19 | `LCD_B4` |
| 20 | `LCD_G0` |
| 21 | `LCD_G1` |
| 22 | `LCD_G2` |
| 23 | `LCD_G3` |
| 24 | `LCD_G4` |
| 25 | `LCD_G5` |
| 26 | `LCD_R0` |
| 27 | `LCD_R1` |
| 28 | `LCD_R2` |
| 29 | `LCD_R3` |
| 30 | `LCD_R4` |
| 31 | `BL_PWM` |
| 32 | `BL_ANODE` |
| 33 | `BL_CATHODE` |
| 34 | `I2C0_SDA` |
| 35 | `I2C0_SCL` |
| 36 | `PANEL_IRQ` |
| 37 | `LCD_DISP` |
| 38 | `DGND` |
| 39 | `DGND` |
| 40 | `DGND` |

### J-BUS1/J-BUS2 — аналоговая шина модулей (IDC-26, 2 шт.)

| Pin | Цепь |
|---|---|
| 1 | `12V_B` |
| 2 | `PGND` |
| 3 | `-12V_B` |
| 4 | `PGND` |
| 5 | `CVOUT1` |
| 6 | `AGND` |
| 7 | `CVOUT2` |
| 8 | `AGND` |
| 9 | `CVOUT3` |
| 10 | `AGND` |
| 11 | `CVOUT4` |
| 12 | `AGND` |
| 13 | `GATE1` |
| 14 | `DGND` |
| 15 | `GATE2` |
| 16 | `DGND` |
| 17 | `AUDIN_L` |
| 18 | `AGND` |
| 19 | `AUDIN_R` |
| 20 | `AGND` |
| 21 | `AUDOUT_L` |
| 22 | `AGND` |
| 23 | `AUDOUT_R` |
| 24 | `AGND` |
| 25 | `SPARE1` |
| 26 | `SPARE2` |

### J-DIG-EXP — цифровое расширение умных модулей (R-22: TDM/I2S + SPI mailbox)

| Pin | Цепь |
|---|---|
| 1 | `3V3` |
| 2 | `DGND` |
| 3 | `5V` |
| 4 | `DGND` |
| 5 | `I2S_BCK` |
| 6 | `I2S_LRCK` |
| 7 | `I2S_DAC_DIN` |
| 8 | `I2S_ADC_DOUT` |
| 9 | `SPI2_SCK` |
| 10 | `SPI2_MOSI` |
| 11 | `SPI2_MISO` |
| 12 | `DGND` |
| 13 | `I2C0_SDA` |
| 14 | `I2C0_SCL` |
| 15 | `DGND` |
| 16 | `DGND` |

### J-USB DATA — USB-C 16P (USB HS)

| Pin | Цепь |
|---|---|
| A4/B4/A9/B9 | `VBUS_CHG` |
| A6/B6 | `USB_HS_DP` |
| A7/B7 | `USB_HS_DM` |
| A5 | `CC1` |
| B5 | `CC2` |
| A1/B1/A12/B12 | `GND` |
| SH | `SHIELD` |

> Один USB-C 16P: USB 2.0 HS данные + 5 В заряд/питание (раздельные USB-C DATA/CHARGE — опция ревизии).

### TB1/TB2 — задние джеки (MIDI, LINE/PHONES, DC, EXPRESSION)

| Pin | Цепь |
|---|---|
| TB1.1 | `AUDOUT_L` |
| TB1.2 | `AUDOUT_R` |
| TB1.3 | `AGND` |
| TB1.4 | `PHONES_L` |
| TB1.5 | `PHONES_R` |
| TB1.6 | `AGND` |
| TB1.7 | `AUDIN_L` |
| TB1.8 | `AUDIN_R` |
| TB1.9 | `AGND` |
| TB1.10 | `AGND` |
| TB2.1 | `MIDI_IN_T` |
| TB2.2 | `MIDI_IN_R` |
| TB2.3 | `DGND` |
| TB2.4 | `MIDI_OUT_T` |
| TB2.5 | `MIDI_OUT_R` |
| TB2.6 | `DGND` |
| TB2.7 | `12V_EXT` |
| TB2.8 | `PGND` |
| TB2.9 | `EXPR` |
| TB2.10 | `3V3` |

\* энкодеры и матрица клавиш считываются MCP23017 на PANEL-2; на CORE-2 идут только I2C + IRQ.

> В таблицах разъёмов указаны *логические* цепи. На плате питания панели идут через
> фильтры: `3V3 -> 3V3_PANEL`, `5V -> 5V_PANEL` (ферриты FB4/FB5), `BL_ANODE -> BL_20V`
> (+20 В boost), `BL_CATHODE` — возврат LED-линейки (0R на PGND на CORE-2).
> J13 IDC-16 (дека) находится на PANEL-2; на CORE-2 ему соответствуют J15 FFC-40 (J12)
> и J14 IDC-26 (J14) — см. `interfaces.md` §7.

## 8. Дисплей и аудио-контракт (кратко; полностью — `interfaces.md`)

| Параметр | Значение |
|---|---|
| display.interface | LCD_CAM parallel RGB565 (16-bit) + PCLK/DE/HSYNC/VSYNC |
| display.resolution | 800x480 |
| display.pins | 25 signals: 20 LCD + I2C(2) + INT + BL_PWM + DISP (+BL_ANODE/BL_CATHODE) |
| display.connector | J-LCD (FFC-40, 0.5 mm; PANEL-2 J12) + J-PANEL (IDC-26; J14) |
| display.bl | BL_ANODE/BL_CATHODE from CORE-2 +20 V boost, BL_PWM (LEDC) to panel driver |
| display.disp | LCD_DISP on GPIO50 (last free GPIO); active-high enable |
| audio.fs | 48 kHz (44.1 kHz also supported by PLL) |
| audio.mclk | 12.288 MHz = 256 fs |
| audio.bck | 3.072 MHz = 64 fs |
| audio.lrck | 48 kHz |
| audio.dac | PCM5102A, I2S, 24-bit, SCK = shared MCLK |
| audio.dac_cfg | FMT=0 (I2S), DEMP=0, FLT=0, XSMT=1 (unmute via 10k PU) |
| audio.adc | PCM1808, I2S slave, 24-bit, MD0=MD1=0 (slave, 256/384/512fs auto), FMT=0 (I2S) |
| audio.adc_supply | VCC=5 V, VDD=3.3 V, VREF 0.1uF+10uF |
| audio.mute | PCM5102A XSMT low at power-up (RC), unmuted by firmware after I2S clock lock; PCM1808 clock-halt reset; DAC out muted by XSMT; relay not used |
| audio.rear_jacks | LINE OUT L/R + PHONES + AUDIO IN L/R (5 x 3.5 mm) on CORE-2 rear wall (TB1) |
| usb.device | USB 2.0 HS OTG, 480 Mbit/s, D+/D- dedicated PHY pins USB_DP/USB_DM |
| usb.esd | USBLC6-2SC6 |
| usb.cc | 5.1k UFP resistors (CC1/CC2) |
| usb.diff | 90 ohm differential pair, matched +-0.5 mm, GND guard |
| usb.connector | USB-C 16P (USB 2.0 only) - single connector: data + charge |
| usb.power | VBUS -> USBLC6 -> polyfuse 1.5 A -> BQ24074 (power-path) |
| usb.composite | TinyUSB: HID keyboard + MIDI class + UAC2 audio (2 in / 2 out) + CDC debug; one USB-C cable for data, MIDI, audio and charging |
| usb.vbus_detect | GPIO54 via 100k/100k divider (device role / host detect) |
| usb.c6 | ESP32-C6-MINI-1 coprocessor for Wi-Fi 6 + BLE 5.3 (P4 has no radio); link: esp-hosted over SPI2 (shared with MCP3208, CS1) + handshake/data-ready + reset; separate +3V3_C6 LDO; DNP for ESP32-S3 build (native radio) |

