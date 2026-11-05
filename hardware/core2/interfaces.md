# CORE-2 — интерфейсные контракты (audio / USB / CV / MIDI / bus / PANEL-2)

> **STATUS: PRE-FREEZE / DO NOT FABRICATE.** До бенчмарка P1 и подписи
> требований (spec/90) схема не заказывается. Числа — расчётные/даташитные;
> смотреть вместе с [`pinmap.md`](pinmap.md) и [`power-tree.md`](power-tree.md).

## 1. Аудио: I2S-контракт

**I2S0 — master (ESP32-P4), общие клоки для DAC и ADC.**

| Сигнал | Частота / формат | GPIO | Куда |
|---|---|---|---|
| MCLK | 12.288 MHz = 256 fs | GPIO20 | PCM5102A SCK + PCM1808 SCKI (общий) |
| BCK/SCK | 3.072 MHz = 64 fs | GPIO16 | PCM5102A BCK + PCM1808 BCK |
| LRCK/WS | 48 kHz | GPIO17 | PCM5102A LRCK + PCM1808 LRCK |
| DIN (out) | 24-bit I2S | GPIO18 | PCM5102A DIN |
| DOUT (in) | 24-bit I2S | GPIO19 | PCM1808 DOUT |

Sample rate: **48 kHz (44.1 kHz also supported by PLL)**. MCLK = 256 fs, BCK = 64 fs. APLL ESP32-P4 используется
для I2S (не делитель USB/DSI PLL/SPLL) — клоки I2S не зависят от USB 480 МГц и
DSI/PPA (требование «развязка клоков от DSI/USB»). При смене fs прошивка
пересчитывает MCLK (APLL) и только затем перезапускает I2S; PCM1808 в slave-режиме
c автодетектом 256/384/512 fs (MD0=MD1=0).

**PCM5102A (DAC):** PCM5102A, I2S, 24-bit, SCK = shared MCLK; FMT=0 (I2S), DEMP=0, FLT=0, XSMT=1 (unmute via 10k PU). Выходы OUTL/OUTR — 2.1 В rms, AC-развязка 10 uF,
TL072-буфер + 100 Ом -> LINE OUT / PHONES (TB1). SCK = MCLK (не GND), т.к. MCLK есть.
DEMP=0 (de-emphasis off), FLT=0 (normal latency), FMT=0 (I2S).

**PCM1808 (ADC):** PCM1808, I2S slave, 24-bit, MD0=MD1=0 (slave, 256/384/512fs auto), FMT=0 (I2S); VCC=5 V, VDD=3.3 V, VREF 0.1uF+10uF. Питание: VCC=5 V, VDD=3.3 V, VREF 0.1uF+10uF.
Входы VINL/VINR: 1 uF AC-связь (внутренний 60 кОм -> HPF 2.7 Гц), опциональный
RC 1k/100pF на входе, защита BAT54S. MD0=MD1=0, FMT=0.

**Mute / power sequencing:** PCM5102A XSMT low at power-up (RC), unmuted by firmware after I2S clock lock; PCM1808 clock-halt reset; DAC out muted by XSMT; relay not used
Порядок: 3.3 В -> клоки I2S -> XSMT=1 (unmute) -> аудио. При выключении/
потере MCLK PCM1808 уходит в reset по clock-halt; PCM5102A XSMT=0 (mute).
Отдельного аналогового реле/mute-транзистора нет (pre-freeze).

## 2. USB 2.0 High-Speed

| Параметр | Значение |
|---|---|
| device | USB 2.0 HS OTG, 480 Mbit/s, D+/D- dedicated PHY pins USB_DP/USB_DM |
| esd | USBLC6-2SC6 |
| cc | 5.1k UFP resistors (CC1/CC2) |
| diff | 90 ohm differential pair, matched +-0.5 mm, GND guard |
| connector | USB-C 16P (USB 2.0 only) |
| power | VBUS -> BQ24074 charger input |

- USB HS PHY у P4 — **выделенные выводы** USB_DM/USB_DP (pin 49/50); через GPIO
  matrix HS-пара не выводится. Поэтому в слоте J-MCU это отдельные контакты 6/7.
- ESD: USBLC6-2SC6 на D+/D- и VBUS; последовательных резисторов на HS-паре нет.
- CC1/CC2: 5.1 к на GND (UFP, device). VBUS -> USBLC6 -> polyfuse 1.5 А -> BQ24074.
- Диффпара: 90 Ом, длина ±0.5 мм, без стабов, GND-полигон под парой.
- USB Serial/JTAG (GPIO24/25) — отдельный 4-pin header `J-DBG` для прошивки/логов;
  альтернативный USB 2.0 FS OTG (GPIO26/27) — зарезервирован, не разведён.

## 3. CV

| Параметр | Значение |
|---|---|
| out_range | 0..10.0 V (DAC 0..2.048 V x 4.883; implemented 4.9 with 39k/10k -> 10.04 V) |
| out_prot | 1k series + BAT54S to AGND/+12V |
| out_cal | 2-point calibration per channel in 24C32 EEPROM 0x57 |
| in_range | -10..+10 V -> 0..3.3 V: Vadc = 1.65 - 0.165*Vin (100k/16.5k + 1.65 V offset) |
| in_prot | BAT54S to AGND/+3V3 after 1k, RC 1k/100nF at ADC |

**CV OUT 1…6:** MCP4728 #1 (0x60) CH A…D -> CV1…4 (шина J-BUS1/2),
MCP4728 #2 (0x61) CH A/B -> CV5/CV6 (задние джеки). Vref внутренний 2.048 В,
усилитель TL074 неинвертирующий ×4.9 (39к/10к), затем 1 кОм + BAT54S (AGND/ +12 В).
Калибровка — 2 точки на канал в 24C32 (0x57). LDAC всех MCP4728 = GND (немедленное
обновление). RDY/BSY не используется (NC).

**CV IN 1…2:** -10..+10 V -> 0..3.3 V: Vadc = 1.65 - 0.165*Vin (100k/16.5k + 1.65 V offset)
Цепь: J-PANEL.17/19 -> 100 кОм -> узел (-) TL074; Rf 16.5 кОм; (+) = 1.65 В
(47к/47к от +3V3 через буфер TL074); выход -> BAT54S (AGND/+3V3) -> 1к/100нФ ->
MCP3208 CH0/CH1. Вход защищён по ±12 В внешним последовательным 1 кОм? —
**нет:** защита CV IN от ±12 В обеспечивается входным 100 кОм + BAT54S на узле
до ОУ (диоды к AGND/ +3V3); при аварии ток ограничен 100 кОм. В ревизии перед
заказом добавить TVS/PESD на джеки панели (PANEL-2).

**MCP3208 (SPI2, 10 МГц):**

| Канал | Цепь | Назначение |
|---|---|---|
| CH0 | `CVIN1` | CV IN 1 jack (100k/16.5k + 1.65 V offset) |
| CH1 | `CVIN2` | CV IN 2 jack |
| CH2 | `FADER1` | panel fader 1 (RC 1k/100nF) |
| CH3 | `FADER2` | panel fader 2 |
| CH4 | `SPARE_ADC1` | reserve / expansion (testpoint) |
| CH5 | `SPARE_ADC2` | reserve / expansion (testpoint) |
| CH6 | `BATT_MON` | battery 100k/47k divider, ADC battery monitor |
| CH7 | `TEMP_MON` | NTC 10k/10k divider (pack temperature) |

## 4. MIDI (TRS-A)

| Сигнал | Цепь |
|---|---|
| MIDI IN tip (pin 5 DIN) | `MIDI_IN_T` -> 6N137 cathode (pin 3) |
| MIDI IN ring (pin 4) | `MIDI_IN_R` -> 220 Ом -> 6N137 anode (pin 2) |
| MIDI OUT tip (pin 5) | `MIDI_OUT_T` <- 33 Ом <- 74HCT125 1Y |
| MIDI OUT ring (pin 4) | `MIDI_OUT_R` <- 220 Ом <- +5 В |
| Sleeve (pin 2) | DGND (TB1.3/6) |

6N137: VCC = +5 В, выход open-collector с pull-up 4.7 к на +3.3 В (UART1 RX),
EN = +5 В. 74HCT125 питается +5 В, вход TTL-совместим с 3.3 В (HCT).
MIDI IN/OUT — гальванически развязанный вход; земля MIDI IN соединяется с DGND
только на стороне оптрона (стандартная схема).

## 5. Шина модулей (J-BUS1/J-BUS2, IDC-26, только аналог)

По R-11/R-22 новая шина — **аналоговая**: ±12 В, 4× CV OUT, 2× GATE,
AUDIO IN/OUT (L/R), земли. Цифровое расширение — отдельный `J-DIG-EXP`.

| Пин | Сигнал | Защита на CORE-2 |
|---|---|---|
| 1 | `12V_B` | polyfuse 0.5 А + SS34 последовательно + SMAJ15A на порт |
| 2 | `PGND` | — (земля/питание) |
| 3 | `-12V_B` | polyfuse 0.3 А + SS34 последовательно |
| 4 | `PGND` | — (земля/питание) |
| 5 | `CVOUT1` | 1к + BAT54S |
| 6 | `AGND` | — (земля/питание) |
| 7 | `CVOUT2` | 1к + BAT54S |
| 8 | `AGND` | — (земля/питание) |
| 9 | `CVOUT3` | 1к + BAT54S |
| 10 | `AGND` | — (земля/питание) |
| 11 | `CVOUT4` | 1к + BAT54S |
| 12 | `AGND` | — (земля/питание) |
| 13 | `GATE1` | 2N7000 open-drain + 4.7к на +5 В (на CORE-2) |
| 14 | `DGND` | — (земля/питание) |
| 15 | `GATE2` | 2N7000 open-drain + 4.7к на +5 В (на CORE-2) |
| 16 | `DGND` | — (земля/питание) |
| 17 | `AUDIN_L` | 1к + BAT54S (±12 В) + 100pF |
| 18 | `AGND` | — (земля/питание) |
| 19 | `AUDIN_R` | 1к + BAT54S + 100pF |
| 20 | `AGND` | — (земля/питание) |
| 21 | `AUDOUT_L` | 100 Ом от TL072-буфера |
| 22 | `AGND` | — (земля/питание) |
| 23 | `AUDOUT_R` | 100 Ом от TL072-буфера |
| 24 | `AGND` | — (земля/питание) |
| 25 | `SPARE1` | — (земля/питание) |
| 26 | `SPARE2` | — (земля/питание) |

Аудио на шине — только AC (разделительные 10 uF на выходах буферов; на входе
PCM1808 — 1 uF). Постоянка на шину запрещена (R-11).

## 6. Цифровое расширение модулей (J-DIG-EXP, IDC-16)

| Пин | Сигнал |
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

TDM/I2S + SPI mailbox + I2C (R-22). Для умных модулей: EEPROM 0x50+порт на I2C,
SPI CS — отдельный от MCP3208 (CS1..CS2 GP-SPI2) в ревизии; сейчас в J-DIG только
общие SCK/MOSI/MISO, CS назначается перемычкой модуля.

## 7. PANEL-2

Два шлейфа: **J-PANEL** (IDC-26) — контроль/аналог, **J-LCD** (FFC-40) — дисплей и
аудиовход. Полные таблицы — `pinmap.md` §7.

| Блок | Интерфейс |
|---|---|
| 16 энкодеров EC11 | 2× MCP23017 (I2C 0x20/0x21), A/B на GPA/GPB, INT -> PANEL_IRQ |
| Матрица 42 клавиш (6×7) | MCP23017 #3 (0x22): 7 колонок GPA0..6 (входы, 10к PU), 6 строк GPB0..5 (выходы), INT -> PANEL_IRQ |
| 2 фейдера 10к | аналог -> J-PANEL.13/15 -> MCP3208 CH2/CH3 (RC 1к/100нФ) |
| 10 mini-jack | CV OUT1..4, CV IN1..2, GATE1..2, AUDIO IN L/R (см. §3/§4) |
| Экран 5.0" 800×480 | RGB565, 16 data + PCLK/DE/HSYNC/VSYNC (20 GPIO), BL (LEDC PWM), DISP |
| LED-цепочка | LED_DATA 5 В (74HCT1G125 + 330 Ом), 74 LED (42 клавиши + 16 ручек + статус) |
| Питание панели | +5V (LED/подсветка), +3V3 (логика/экран), 4 линии GND |

LCD timing (расчётно): 800×480 RGB565, PCLK 30–40 МГц при 60 Гц с blanking
(H: 800+80 fp/bp, V: 480+20); P4 LCD_CAM выдаёт PCLK из PLL, не делит USB/DSI.
Проверить на бенчмарке (P1).

## 8. Сброс, клоки, brownout

- CHIP_PU: 10 к на +3V3_MCU + 100 нФ на DGND + кнопка RESET на DGND;
  выход BQ24074 PGOOD не заводится на CHIP_PU (только индикация).
- BOOT (GPIO35): 10 к на +3V3_MCU, кнопка на DGND; удержание при reset —
  joint download boot (USB-Serial-JTAG/UART0); GPIO36 = 10 к на DGND (страховка).
- USB/PSRAM/DSI: HS PHY и DSI PHY используют свои PLL; I2S — APLL. Порядок
  включения: 3V3_MCU -> P4 ROM -> PSRAM init -> APLL/I2S -> audio unmute.
- Brownout: внутренний BOD P4; при просадке CHIP_PU сбрасывается. Внешний
  супервизор не ставится (pre-freeze); в ревизии — TPS3839 при необходимости.

## 9. Что нельзя заказывать до бенчмарка

1. Схема и PCB — **PRE-FREEZE**: не заказывать до P1 (замер реального тока/тепла/
   производительности P4 и выбора модуля/адаптера под слот J-MCU).
2. Слот J-MCU — логический контракт (2×32), физический модуль/адаптер ещё не
   выбран: pinout адаптера должен быть проверен по datasheet выбранной платы.
3. Ток +5 В/WS2812 и тепловой режим MT3608 требуют замера (см. `power-tree.md`).
4. LCD: RGB565 vs MIPI-DSI — решение R-18 открыто; RGB требует 20 GPIO и
   подтверждения PCLK на бенчмарке.
5. 24C32 (0x57) на CORE-2 и EEPROM модулей 0x50+порт — проверить адресацию.

