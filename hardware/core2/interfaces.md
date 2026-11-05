# CORE-2 — интерфейсные контракты (audio / USB / CV / MIDI / bus / PANEL-2)

> **STATUS: PRE-FREEZE / DO NOT FABRICATE.** Схема — **rev.2** (ERC 0/0). До бенчмарка P1 и подписи
> требований (spec/90) схема не заказывается. Числа — расчётные/даташитные;
> смотреть вместе с [`pinmap.md`](pinmap.md), [`power-tree.md`](power-tree.md)
> и **[`rev2-plan.md`](rev2-plan.md)** (rev.2: PWR-2, DNP, EN, J17/J18).

## 0. rev.2: триада CORE-2 / PANEL-2 / PWR-2 (D-32…D-36, O-1…O-7)

| Что | rev.2 |
|---|---|
| Рельсы ±12 В / +5 В / 5V_LED | приходят с **PWR-2 J3** (J17 IDC-20); на CORE-2 — только защита входов и локальные 3V3/3V3_C6/3V3_MCU/BL_20 |
| DNP на CORE-2 | MT3608 #1 (+12 В, рекомендуется), MT3608 #2 (+5 В), MC34063 (−12 В), BMS + пакет (J2/TH1), level shifter LED (U44/R90) — подробно `rev2-plan.md` §3 |
| Новые входы | `12V_EXT` (D2 SS34, уже есть) и **`N12_EXT`** (D19 SS34 + D20 SMAJ15A + C112/C113); `+5V_EXT` (C114/C115) |
| EN рельсов | 4 входа PWR-2 ← **2 линии MCP23017 PANEL-2 0x23** (GPA7 = EN_RAILS для +12/−12/+5; GPB6 = EN_LED5); дефолт: рельсы ON, LED OFF (D-33) |
| Power-path | BQ24074 остаётся на CORE-2; VSYS → PWR-2; пик VSYS 2.74…3.38 А при 3 А — firmware cap LED 0.55 А + профиль (O-2) |
| Монтаж | J17 (IDC-20, PWR-2 J3) + J18 (IDC-12, PWR-2 J4) — пары PGND; при 3 А — альтернатива Micro-Fit 3.0 (O-5) |
| **Реализовано в rev.2** | J17/J18 + D19/D20 + C112-C115 + R92-R96 + R98/R105 + U45 (CV IN3/4) + TP23-TP27; DNP-флаги 46 позиций; J14/J15/J16 re-pin по PANEL-2 |
| **O-8** | `PWR_GOOD`/`FUEL_ALRT` → свободные GPIO **ESP32-C6** (RPC esp-hosted); для S3 — опрос MAX17048 по I2C |
| **O-9** | CVIN3/4 (PANEL-2) → MCP3208 CH4/CH5 через U45 TL074; GATE_IN — на PANEL-2 (MCP23017 0x23 GPB7); EXPRESSION убран |
| **O-10** | цифровое расширение TDM/I2S+SPI (R-22) отложено до rev.3 |
| **O-11** | J3: IDC-20 для прототипа (тест ≤100 мВ/≤30 °C), Micro-Fit 3.0 для rev.2 (D-40) |
| **O-12** | CV OUT 5/6 (MCP4728 #2 CH A/B) в PANEL-2 J14 не выведены (только CV OUT1-4); тест-пэды/резерв до rev.3 |

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
TL072-буфер + 100 Ом -> задняя панель CORE-2: LINE OUT L/R + PHONES (3.5 мм, TB1).
Аудиовходы AUDIO IN L/R — тоже на задней панели (TB1.7/8 -> PCM1808). SCK = MCLK.
На верхней панели (PANEL-2) остаются только 10 CV/GATE-джеков.
DEMP=0 (de-emphasis off), FLT=0 (normal latency), FMT=0 (I2S).

**PCM1808 (ADC):** PCM1808, I2S slave, 24-bit, MD0=MD1=0 (slave, 256/384/512fs auto), FMT=0 (I2S); VCC=5 V, VDD=3.3 V, VREF 0.1uF+10uF.
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
| connector | USB-C 16P (USB 2.0 only) - single connector: data + charge |
| power | VBUS -> USBLC6 -> polyfuse 1.5 A -> BQ24074 (power-path) |
| composite | TinyUSB: HID keyboard + MIDI class + UAC2 audio (2 in / 2 out) + CDC debug; one USB-C cable for data, MIDI, audio and charging |
| vbus_detect | GPIO54 via 100k/100k divider (device role / host detect) |
| c6 | ESP32-C6-MINI-1 coprocessor for Wi-Fi 6 + BLE 5.3 (P4 has no radio); link: esp-hosted over SPI2 (shared with MCP3208, CS1) + handshake/data-ready + reset; separate +3V3_C6 LDO; DNP for ESP32-S3 build (native radio) |

- USB HS PHY у P4 — **выделенные выводы** USB_DM/USB_DP (pin 49/50); через GPIO
  matrix HS-пара не выводится. Поэтому в слоте J-MCU это отдельные контакты 6/7.
- ESD: USBLC6-2SC6 на D+/D- и VBUS; последовательных резисторов на HS-паре нет.
- CC1/CC2: 5.1 к на GND (UFP, device). VBUS -> USBLC6 -> polyfuse 1.5 А -> BQ24074.
- Диффпара: 90 Ом, длина ±0.5 мм, без стабов, GND-полигон под парой.
- **USB composite (TinyUSB, прошивка):** HID-клавиатура + MIDI class-compliant +
  UAC2 аудио (2 in / 2 out) + CDC debug — одновременно на одном USB-C. Схема
  обеспечивает: ESD (USBLC6-2SC6), CC 5.1 к (UFP), HS-пары с 90 Ом, VBUS-детект
  (GPIO54, делитель 100к/100к), питание/заряд (BQ24074). Скорость: HS 480 Мбит/с.
- USB Serial/JTAG (GPIO24/25) больше **не** используется: эти GPIO отданы
  сопроцессору C6. Прошивка/даунлоад — через USB HS (ROM joint download boot,
  кнопка BOOT: GPIO35=0 при GPIO36=1). UART0 (GPIO37/38) выведен на `J-UART`.

## 2a. Wi-Fi 6 / BLE 5.3: сопроцессор ESP32-C6-MINI-1

| Параметр | Значение |
|---|---|
| Модуль | ESP32-C6-MINI-1 (Wi-Fi 6 802.11ax + BLE 5.3, PCB-антенна) |
| Связь с P4 | esp-hosted по **SPI2** (общая шина с MCP3208, отдельный CS1) + handshake + data-ready + reset |
| GPIO P4 | C6_CS=GPIO26, C6_HS=GPIO24, C6_DR=GPIO25, C6_RST=GPIO27 |
| Питание | отдельный LDO **+3V3_C6** (AP2112K-3.3, 600 мА) от +5 В, 22 uF + 100 nF у модуля |
| Антенна | keep-out ≥15 мм от металла, батареи, стенок и шлейфов; модуль у края платы |
| Согласование | MINI-1 — внутренняя PCB-антенна (согласование не требуется);
  для варианта MINI-1U (внешняя антенна) — pi-матч 0R/NM + U.FL |
| Вариант S3 | ESP32-S3 имеет радио нативно: C6 **DNP**, площадка не паяется (см. BOM) |

SPI esp-hosted throughput (расчётно) 10–20 Мбит/с — достаточно для Wi-Fi 6 + BLE
управления/телеметрии; аудио-стриминг по Wi-Fi не входит в v1.0 (проверить на P1).
Альтернатива по ТЗ — SDIO (6 GPIO) — невозможна без отказа от части LCD/энкодеров:
SDIO-slots у P4 два, но GPIO-бюджет уже исчерпан (см. pinmap.md §1).

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
| CH0 | `CVIN1_ADC` | CV IN 1 (panel jack; 100k/16.5k + 1.65 V offset) |
| CH1 | `CVIN2_ADC` | CV IN 2 (panel jack) |
| CH2 | `FADER1_ADC` | panel fader 1 (RC 1k/100nF) |
| CH3 | `FADER2_ADC` | panel fader 2 (RC 1k/100nF) |
| CH4 | `EXPR_ADC` | EXPRESSION pedal (rear jack, 3V3 divider) |
| CH5 | `SPARE_ADC` | reserve / expansion (RC to AGND, testpad) |
| CH6 | `BATT_MON` | battery 100k/47k divider, ADC battery monitor |
| CH7 | `TEMP_MON` | NTC 10k/10k divider (pack temperature) |

## 3a. Связь с PWR-2: J17/J18, EN, VSYS

**J17 (IDC-20, ответный PWR-2 J3):** VSYS (CORE→PWR-2, 2 пина), VBAT (PWR-2→BQ24074 BAT),
+12V (→`12V_EXT` через D2), −12V (→`N12_EXT` через D19), +5V (→`+5V_EXT`), 5V_LED/LED_RET,
пары PGND (7/8, 11/12, 15/16, 19/20). Падение D7/D8 PWR-2 0.45 В -> 11.7/−11.55 В.
**J18 (IDC-12, ответный PWR-2 J4):** BATT_MON, NTC_PACK (→TS BQ24074), FUEL_SDA/SCL
(I2C0, MAX17048 0x36), FUEL_ALRT, PWR_GOOD (open-drain LOW при VSYS<2.70 В), EN_BUS12,
EN_N12, EN_LED5, EN_5V, PGND.

**EN семантика:** EN_BUS12/EN_N12/EN_5V — active-high disable (high-Z = ON; pull-up на
PWR-2), объединены на CORE-2 в `EN_RAILS`; EN_LED5 — active-high enable (default OFF).
Источник — MCP23017 0x23 (PANEL-2): GPA7 = EN_RAILS, GPB6 = EN_LED5; маршрут
J13.15/J14.25 → J16/J14 → J18.7/8/9/10. При high-Z (до инициализации экспандера)
PWR-2 держит рельсы ON, LED OFF — совпадает с D-33. **Fallback:** без правки PANEL-2 EN
не разводятся, дефолт PWR-2 (рельсы ON, LED OFF), включение LED — джампер JP1.

**VSYS / power-path:** BQ24074 OUT (≈3 А) → J17 → PWR-2. Сумма паспортных бюджетов
3.94…4.87 А недостижима; реалистичный пик 2.74 А @3.7 В (3.38 А @3.0 В) — запас 9 %
< 25 %, зафиксировано в O-2. Меры: прошивочный cap WS2812 0.55 А + профиль яркости
(на батарее ≤30 %, автоснижение по PWR_GOOD), последовательное включение рельсов,
внешний 12 В для +12-рельса (полный максимум +5 — только 2S/внешний 5 В, O-6).
**Реализовано (rev.2):** J17/J18, D19 SS34 + D20 SMAJ15A + C112/C113 (N12_EXT), C114/C115
+FB7+C117 (+5V_EXT→+5V), R92/R93 (pull-up PWR_GOOD/FUEL_ALRT), R94/R95/R96 (EN_RAILS→
EN_BUS12/EN_N12/EN_5V), R98 (LED_GPIO→LED_DATA bypass), R105 (LCD_DISP→3V3), U45 TL074 (CV IN3/4),
TP23-TP27. Старые диоды порта 1 перенумерованы D28/D29 (конфликт ref с D19/D20).

**PWR_GOOD / FUEL_ALRT** — open-drain, подтяжки 100k на CORE-2 (R92/R93); читать нечем
на P4 (0 GPIO) → предложение: свободные GPIO ESP32-C6 (N-1).

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
| 16 энкодеров EC11 (A/B + push) | 3× MCP23017: 0x20/0x21 (A/B), 0x22 (push) — 48 линий; INT wire-OR -> PANEL_IRQ (всего на PANEL-2 4× MCP23017, 0x20…0x23) |
| Матрица 42 клавиш (6×7) | MCP23017 0x23: 7 колонок GPA0..6 (входы, 10к PU), 6 строк GPB0..5 (выходы), 3 линии резерв; INT -> PANEL_IRQ |
| 2 фейдера 10к | аналог -> J-PANEL.13/15 -> MCP3208 CH2/CH3 (RC 1к/100нФ) |
| 10 mini-jack | CV OUT 1..6, CV IN 1..2, GATE 1..2 (верхняя панель; см. §3/§4) |
| Экран 5.0" 800×480 | RGB565: 16 data + PCLK/DE/HSYNC/VSYNC (20 GPIO) + I2C(2) + INT + BL_PWM + DISP = **25 сигналов** (PANEL-2 J12 FFC-40) |
| LED-цепочка | LED_DATA 5 В (74HCT1G125 + 330 Ом), 74 LED (42 клавиши + 16 ручек + статус) |
| Питание панели | +5V (LED/логика), +3V3 (логика/экран), +20 V BL_ANODE, линии GND |
| Коннекторы PANEL-2 | J12 FFC-40 (LCD), J13 IDC-16 (цифра/питание), J14 IDC-26 (аналоговое поле); на CORE-2 ответные — J15/J16/J14 |
| rev.2 sync PANEL-2 | J13.9/13 `5V`→`5V_LED`, J13.16 `GND`→`LED_RET`, J13.15 NC→`EN_RAILS` (0x23 GPA7), J14.25 NC→`EN_LED5` (0x23 GPB6); LED_DATA 3.3 В (level shifter уже на PANEL-2); J14 re-pin по PANEL-2 (CVIN3/4, GATE_IN_CLEAN) — открытые N-2/N-3 |

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

