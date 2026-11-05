# CORE-1 — таблица соединений джеков и клеммников

Сгенерировано `gen_core_sch.py` из той же таблицы, что и схема. Джеки — панельные (вне платы), подключаются проводами к клеммникам TB1/TB2 3.81 мм; на CORE-1 нет паяных джеков (см. `spec/20-electronics.md` §8).

## 1. Джеки → цепь → клеммник → CORE-1

| Джек | Контакт | Цепь | Клеммник | Шина P1..P3 | PANEL J15 | Примечание |
|---|---|---|---|---|---|---|
| J1 | Tip | `AUDL_OUT` | TB1.1, TB1.4 | — | — | LINE OUT 3.5mm stereo |
| J1 | Ring | `AUDR_OUT` | TB1.2, TB1.5 | — | — | LINE OUT 3.5mm stereo |
| J1 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | LINE OUT 3.5mm stereo |
| J2 | Tip | `AUDL_OUT` | TB1.1, TB1.4 | — | — | PHONES 3.5mm stereo |
| J2 | Ring | `AUDR_OUT` | TB1.2, TB1.5 | — | — | PHONES 3.5mm stereo |
| J2 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | PHONES 3.5mm stereo |
| J5 | Tip | `CV5` | TB1.7 | — | — | CV OUT 1 (CV5) |
| J5 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | CV OUT 1 (CV5) |
| J6 | Tip | `CV6` | TB1.9 | — | — | CV OUT 2 (CV6) |
| J6 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | CV OUT 2 (CV6) |
| J7 | Tip | `CVIN1_IN` | TB1.11 | — | — | CV IN 1 |
| J7 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | CV IN 1 |
| J8 | Tip | `CVIN2_IN` | TB2.1 | — | — | CV IN 2 |
| J8 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | CV IN 2 |
| J9 | Tip | `GATE1` | P1.17, P2.17, P3.17, TB2.3 | P1.17, P2.17, P3.17 | — | GATE 1 |
| J9 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | GATE 1 |
| J10 | Tip | `GATE2` | P1.18, P2.18, P3.18, TB2.5 | P1.18, P2.18, P3.18 | — | GATE 2 |
| J10 | Sleeve | `AGND` | AGND (общий, звезда на PCB) | — | — | GATE 2 |
| J11 | Tip | `MIDI_IN_T` | TB2.7 | — | — | MIDI IN (TRS-A) |
| J11 | Ring | `MIDI_IN_R` | TB2.8 | — | — | MIDI IN (TRS-A) |
| J11 | Sleeve | `DGND` | DGND (общий, звезда на PCB) | — | — | MIDI IN (TRS-A) |
| J12 | Tip | `MIDI_OUT_T` | TB2.10 | — | — | MIDI OUT (TRS-A) |
| J12 | Ring | `MIDI_OUT_R` | TB2.11 | — | — | MIDI OUT (TRS-A) |
| J12 | Sleeve | `DGND` | DGND (общий, звезда на PCB) | — | — | MIDI OUT (TRS-A) |

## 2. Клеммники TB1 / TB2 (3.81 мм, 2×12)

| Клеммник | Пин | Цепь | Что на плате | Шина |
|---|---|---|---|---|
| TB1 | 1 | `AUDL_OUT` | R30.2, C45.1 | — |
| TB1 | 2 | `AUDR_OUT` | R31.2, C46.1 | — |
| TB1 | 3 | `AGND` | общий провод | — |
| TB1 | 4 | `AUDL_OUT` | R30.2, C45.1 | — |
| TB1 | 5 | `AUDR_OUT` | R31.2, C46.1 | — |
| TB1 | 6 | `AGND` | общий провод | — |
| TB1 | 7 | `CV5` | R81.2, D17.3 | — |
| TB1 | 8 | `AGND` | общий провод | — |
| TB1 | 9 | `CV6` | R82.2, D18.3 | — |
| TB1 | 10 | `AGND` | общий провод | — |
| TB1 | 11 | `CVIN1_IN` | R44.1 | — |
| TB1 | 12 | `AGND` | общий провод | — |
| TB2 | 1 | `CVIN2_IN` | R46.1 | — |
| TB2 | 2 | `AGND` | общий провод | — |
| TB2 | 3 | `GATE1` | Q1.3, R11.2 | P1.17, P2.17, P3.17 |
| TB2 | 4 | `AGND` | общий провод | — |
| TB2 | 5 | `GATE2` | Q2.3, R14.2 | P1.18, P2.18, P3.18 |
| TB2 | 6 | `AGND` | общий провод | — |
| TB2 | 7 | `MIDI_IN_T` | U7.3 | — |
| TB2 | 8 | `MIDI_IN_R` | R5.1 | — |
| TB2 | 9 | `DGND` | общий провод | — |
| TB2 | 10 | `MIDI_OUT_T` | R7.2 | — |
| TB2 | 11 | `MIDI_OUT_R` | R8.2 | — |
| TB2 | 12 | `DGND` | общий провод | — |

## 3. Шина Bukifon (P1/P2/P3, IDC-26)

| Pin | Сигнал (spec §7) | Направление | Цепь в схеме |
|---|---|---|---|
| 1 | +12V | пит. | `12V_B` |
| 2 | GND |  | `DGND` |
| 3 | -12V | пит. | `-12V_B` |
| 4 | GND |  | `DGND` |
| 5 | +5V | пит. | `5V_B` |
| 6 | GND |  | `DGND` |
| 7 | +3V3 | пит. | `3V3_B` |
| 8 | GND |  | `DGND` |
| 9 | CV1 | core→mod | `CV1` |
| 10 | GND |  | `AGND` |
| 11 | CV2 | core→mod | `CV2` |
| 12 | GND |  | `AGND` |
| 13 | CV3 | core→mod | `CV3` |
| 14 | GND |  | `AGND` |
| 15 | CV4 | core→mod | `CV4` |
| 16 | GND |  | `AGND` |
| 17 | GATE1 | core→mod | `GATE1` |
| 18 | GATE2 | core→mod | `GATE2` |
| 19 | AUD_IN | core→mod | `AUD_IN` |
| 20 | AUD_OUT | mod→core | `AUD_P0` |
| 21 | SDA | I2C | `I2C_SDA` |
| 22 | SCL | I2C | `I2C_SCL` |
| 23 | SCK | SPI0 | `SPI_SCK` |
| 24 | MOSI | SPI0 | `SPI_MOSI` |
| 25 | MISO | SPI0 | `SPI_MISO` |
| 26 | CS | core→mod/CS | `PORT0_CS` |

## 4. J-PANEL (J15, IDC-32)

| Pin | Функция | Цепь |
|---|---|---|
| 1 | +3V3 | `3V3` |
| 2 | DGND | `DGND` |
| 3 | SPI1_SCK | `SPI1_SCK` |
| 4 | DGND | `DGND` |
| 5 | SPI1_MOSI | `SPI1_MOSI` |
| 6 | DGND | `DGND` |
| 7 | LCD_CS | `LCD_CS` |
| 8 | DGND | `DGND` |
| 9 | LCD_DC | `LCD_DC` |
| 10 | LCD_RST | `LCD_RST` |
| 11 | LCD_BL | `LCD_BL` |
| 12 | DGND | `DGND` |
| 13 | SPI_SCK | `SPI_SCK` |
| 14 | DGND | `DGND` |
| 15 | SPI_MISO | `SPI_MISO` |
| 16 | DGND | `DGND` |
| 17 | HC165_PL | `HC165_PL` |
| 18 | DGND | `DGND` |
| 19 | DECK_INT | `DECK_INT` |
| 20 | LED_DATA | `LED_DATA` |
| 21 | I2C_SDA | `I2C_SDA` |
| 22 | I2C_SCL | `I2C_SCL` |
| 23 | +5V | `5V` |
| 24 | DGND | `DGND` |
| 25 | SL1_IN | `SL1_IN` |
| 26 | AGND | `AGND` |
| 27 | SL2_IN | `SL2_IN` |
| 28 | AGND | `AGND` |
| 29 | FSR_IN | `FSR_IN` |
| 30 | AGND | `AGND` |
| 31 | DECK_ID_IN | `DECK_ID_IN` |
| 32 | DGND | `DGND` |

## 5. MCP3208 (U6) — карта каналов

| Канал | Цепь | Назначение |
|---|---|---|
| CH0 | `SL1_ADC` | слайдер SL1 (PANEL-1 / DECK) |
| CH1 | `SL2_ADC` | слайдер SL2 |
| CH2 | `CVIN1_ADC` | CV IN 1 (джек J7) |
| CH3 | `CVIN2_ADC` | CV IN 2 (джек J8) |
| CH4 | `AGND` | резерв (притянут к AGND) |
| CH5 | `AGND` | резерв (притянут к AGND) |
| CH6 | `FSR_ADC` | FSR / deck velocity |
| CH7 | `SYS_MON` | +5V делитель 12k/18k |

## 6. MCP4728 — карта каналов (2 корпуса)

| Корпус (адрес) | Канал | Цепь | Назначение |
|---|---|---|---|
| U4 (0x60) | CHA | `DAC_A` | CV1 (шина P0/P1/P2 pin 9) |
| U4 (0x60) | CHB | `DAC_B` | CV2 (шина pin 11) |
| U4 (0x60) | CHC | `DAC_C` | CV3 (шина pin 13) |
| U4 (0x60) | CHD | `DAC_D` | CV4 (шина pin 15) |
| U16 (0x61) | CHA | `DAC_E` | CV5 (джек CV OUT 1) |
| U16 (0x61) | CHB | `DAC_F` | CV6 (джек CV OUT 2) |

## 7. Pico (A1) — карта пинов (по spec §2)

| GPIO | Функция | Цепь |
|---|---|---|
| GP0 | UART0 TX | `UART_TX` |
| GP1 | UART0 RX | `UART_RX` |
| GP2 | SPI0 SCK | `SPI_SCK` |
| GP3 | SPI0 MOSI | `SPI_MOSI` |
| GP4 | SPI0 MISO | `SPI_MISO` |
| GP5 | MCP3208 CS | `ADC_CS` |
| GP6 | 74HC165 PL | `HC165_PL` |
| GP7 | LED_DATA | `LED_G` |
| GP8 | I2C0 SDA | `I2C_SDA` |
| GP9 | I2C0 SCL | `I2C_SCL` |
| GP10 | SPI1 SCK | `SPI1_SCK` |
| GP11 | SPI1 MOSI | `SPI1_MOSI` |
| GP12 | LCD_CS | `LCD_CS` |
| GP13 | LCD_DC | `LCD_DC` |
| GP14 | LCD_RST | `LCD_RST` |
| GP15 | LCD_BL PWM | `LCD_BL_P` |
| GP16 | I2S BCK | `I2S_BCK` |
| GP17 | I2S LRCK | `I2S_LRCK` |
| GP18 | I2S DIN | `I2S_DIN` |
| GP19 | PORT0_CS | `PORT0_CS` |
| GP20 | PORT1_CS | `PORT1_CS` |
| GP21 | PORT2_CS | `PORT2_CS` |
| GP22 | GATE1 | `GATE1_G` |
| GP26 | GATE2 | `GATE2_G` |
| GP27 | ADC1 DECK_ID | `DECK_ID` |
| GP28 | DECK_INT | `DECK_INT` |
