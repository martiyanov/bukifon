# PANEL-2 ↔ CORE-2 — карта линий (PRE-FREEZE)

Сгенерировано `tools/gen_panel2.py`; сверено с netlist скриптом `tools/verify_netlist.py`.

## 1. Сколько линий нужно и хватает ли одного разъёма

| Группа | Линий | Куда |
|---|---:|---|
| LCD RGB 16 бит: R0-R4 (5) + G0-G5 (6) + B0-B4 (5) | 16 | J12 FFC-40 |
| LCD sync/clock: PCLK, DE, HSYNC, VSYNC | 4 | J12 FFC-40 |
| LCD подсветка: BL_PWM (драйвер/boost на CORE-2) + BL_ANODE/BL_CATHODE | 3 | J12 FFC-40 |
| Энкодеры 16 × (A,B,SW) = 48 → I2C (SDA, SCL) + INT | 3 | J13 IDC-16 |
| EN рельсов: EN_RAILS (0x23 GPA7), EN_LED5 (0x23 GPB6) | 2 | J13.15 / J14.25 |
| Матрица 42 клавиш 6×7 = 13 → MCP23017 (на той же I2C) | 0 доп. | J13 IDC-16 |
| LED-цепочка 17 × WS2812B: LED_DATA | 1 | J13 IDC-16 |
| Джек-поле: 4 CV OUT + 4 CV IN + GATE OUT + GATE IN | 10 | J14 IDC-26 |
| Фейдеры 2 × 10k → MCP3208 (CORE-2) | 2 | J14 IDC-26 |
| Питание: 5V_LED + отдельный LED_RET (цепочка LED, 0.55 А), +3V3 (логика), GND/GNDA | 2 рельса + 2 возврата | J13/J14 |

**Итого сигналов: 40** (16 RGB + 4 синхро + BL_PWM + BL_ANODE + BL_CATHODE = 23 по J12; I2C 2 + INT + LED_DATA + EN_RAILS = 5 по J13; 4 CV OUT + 4 CV IN + GATE_OUT + 2 фейдера + EN_LED5 = 12 по J14). GATE_IN читается на PANEL-2 (0x23 GPB7) и на шлейф не выходит.
**Одного IDC-26 не хватает:** в IDC-26 максимум 13 сигнальных пинов при «сигнал/земля»; даже без LCD нужно 16 сигналов (3 + 1 + 12). Поэтому:

1. **J12 FFC-40** — LCD RGB-шина (23 сигнала, включая BL_PWM и клеммы LED-линейки) + питание: высокочастотные линии нельзя тащить через IDC-26 вместе с аналогом и I2C;
2. **J13 IDC-16** — цифровое: I2C (2) + INT (1) + LED_DATA (1) + +5V/+3V3/GND;
3. **J14 IDC-26** — аналоговое поле: 12 сигналов на нечётных пинах, GNDA на чётных (экранировка «сигнал/земля»).

Мультиплексирование: 48 линий энкодеров + 13 матрицы = **61 GPIO** + 2 EN + GATE_IN свёрнуты в 3 линии благодаря 4 × MCP23017 (2 × 16 для A/B, 1 × 16 для кнопок, 1 × 13 для матрицы). Без этого панель потребовала бы 3–4 шлейфа IDC-26 только под органы управления.

## 2. J12 — FPC-40 (LCD RGB-шина, PANEL-2 → CORE-2)

| Pin | Сигнал | Направление | Уровень | Примечание |
|---:|---|---|---|---|
| 1 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 2 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 3 | `R0` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 4 | `R1` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 5 | `R2` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 6 | `R3` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 7 | `R4` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 8 | `G0` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 9 | `G1` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 10 | `G2` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 11 | `G3` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 12 | `G4` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 13 | `G5` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 14 | `B0` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 15 | `B1` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 16 | `B2` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 17 | `B3` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 18 | `B4` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 19 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 20 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 21 | `PCLK` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 22 | `DE` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 23 | `HSYNC` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 24 | `VSYNC` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 25 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 26 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 27 | `LCD_3V3` | core→panel | — | LCD RGB-шина к CORE-2 |
| 28 | `LCD_3V3` | core→panel | — | LCD RGB-шина к CORE-2 |
| 29 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 30 | `BL_PWM` | core→panel | 3.3 В | LCD RGB-шина к CORE-2 |
| 31 | `BL_ANODE` | core→panel | 19…22 В (LED string) | подсветка LCD (драйвер — на CORE-2) |
| 32 | `BL_CATHODE` | panel→core | 0…22 В (возврат) | подсветка LCD (драйвер — на CORE-2) |
| 33 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 34 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 35 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 36 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 37 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 38 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 39 | `GND` | — | — | LCD RGB-шина к CORE-2 |
| 40 | `GND` | — | — | LCD RGB-шина к CORE-2 |

## 3. J13 — IDC-16 (цифровое/питание)

| Pin | Сигнал | Направление | Уровень | Примечание |
|---:|---|---|---|---|
| 1 | `SDA` | bidir | 3.3 В | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 2 | `GND` | — | — | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 3 | `SCL` | core→panel | 3.3 В | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 4 | `GND` | — | — | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 5 | `INT` | panel→core | 3.3 В | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 6 | `GND` | — | — | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 7 | `LED_DATA` | core→panel | 3.3 В (5 В после U6) | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 8 | `GND` | — | — | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 9 | `5V_LED` | core→panel | 5.0 В | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 10 | `GND` | — | — | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 11 | `+3V3` | core→panel | 3.3 В | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 12 | `GND` | — | — | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 13 | `5V_LED` | core→panel | 5.0 В | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 14 | `GND` | — | — | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 15 | `EN_RAILS` | panel→core | 0/3.3 В (high-Z = rails ON) | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |
| 16 | `LED_RET` | panel→core | возврат LED, до 0.55 А | цифровой/питание (rev.2: 5V_LED/LED_RET/EN_RAILS) |

## 4. J14 — IDC-26 (аналоговое поле; нечётные = сигнал, чётные = GNDA)

| Pin | Сигнал | Направление | Уровень | Примечание |
|---:|---|---|---|---|
| 1 | `CVOUT1` | core→panel | 0..10 В | аналоговое поле |
| 3 | `CVOUT2` | core→panel | 0..10 В | аналоговое поле |
| 5 | `CVOUT3` | core→panel | 0..10 В | аналоговое поле |
| 7 | `CVOUT4` | core→panel | 0..10 В | аналоговое поле |
| 9 | `CVIN1` | panel→core | ±10 В | аналоговое поле |
| 11 | `CVIN2` | panel→core | ±10 В | аналоговое поле |
| 13 | `CVIN3` | panel→core | ±10 В | аналоговое поле |
| 15 | `CVIN4` | panel→core | ±10 В | аналоговое поле |
| 17 | `GATE_OUT` | core→panel | 0/5 В | аналоговое поле |
| 19 | `NC` | — | — | аналоговое поле |
| 21 | `FADER1` | panel→core | 0..3.3 В | аналоговое поле |
| 23 | `FADER2` | panel→core | 0..3.3 В | аналоговое поле |
| 25 | `EN_LED5` | panel→core | 0/3.3 В (active-high enable) | аналоговое поле |
| 2 | `GNDA` | — | — | аналоговое поле |
| 4 | `GNDA` | — | — | аналоговое поле |
| 6 | `GNDA` | — | — | аналоговое поле |
| 8 | `GNDA` | — | — | аналоговое поле |
| 10 | `GNDA` | — | — | аналоговое поле |
| 12 | `GNDA` | — | — | аналоговое поле |
| 14 | `GNDA` | — | — | аналоговое поле |
| 16 | `GNDA` | — | — | аналоговое поле |
| 18 | `GNDA` | — | — | аналоговое поле |
| 20 | `GNDA` | — | — | аналоговое поле |
| 22 | `GNDA` | — | — | аналоговое поле |
| 24 | `GNDA` | — | — | аналоговое поле |
| 26 | `GNDA` | — | — | аналоговое поле |

## 5. J11 — FPC-40 (LCD panel tail, на PANEL-2)

| Pin | Сигнал | Примечание |
|---:|---|---|
| 1 | `GND` | земля |
| 2 | `GND` | земля |
| 3 | `R0` | данные/синхро |
| 4 | `R1` | данные/синхро |
| 5 | `R2` | данные/синхро |
| 6 | `R3` | данные/синхро |
| 7 | `R4` | данные/синхро |
| 8 | `G0` | данные/синхро |
| 9 | `G1` | данные/синхро |
| 10 | `G2` | данные/синхро |
| 11 | `G3` | данные/синхро |
| 12 | `G4` | данные/синхро |
| 13 | `G5` | данные/синхро |
| 14 | `B0` | данные/синхро |
| 15 | `B1` | данные/синхро |
| 16 | `B2` | данные/синхро |
| 17 | `B3` | данные/синхро |
| 18 | `B4` | данные/синхро |
| 19 | `GND` | земля |
| 20 | `GND` | земля |
| 21 | `PCLK` | данные/синхро |
| 22 | `DE` | данные/синхро |
| 23 | `HSYNC` | данные/синхро |
| 24 | `VSYNC` | данные/синхро |
| 25 | `GND` | земля |
| 26 | `GND` | земля |
| 27 | `LCD_3V3` | питание панели |
| 28 | `LCD_3V3` | питание панели |
| 29 | `GND` | земля |
| 30 | `BL_CATHODE` | подсветка |
| 31 | `BL_ANODE` | подсветка |
| 32 | `GND` | земля |
| 33 | `NC` | NC |
| 34 | `NC` | NC |
| 35 | `NC` | NC |
| 36 | `NC` | NC |
| 37 | `NC` | NC |
| 38 | `NC` | NC |
| 39 | `GND` | земля |
| 40 | `GND` | земля |

> ⚠️ Распиновка FPC-40 **зависит от выбранной панели**: таблица выше — предлагаемый контракт для 5.0" 800×480 RGB 16-бит (40-pin, 0.5 мм). Перед заказом сверить с datasheet панели; J11 монтируется на PANEL-2, J12 — шлейф в CORE-2.

## 6. Сводка по разъёмам

| Разъём | Тип | Что несёт | Сигнальных линий |
|---|---|---|---|
| J11 | FPC-40 0.5 мм | LCD panel tail | 20 RGB/синхро + BL_ANODE/BL_CATHODE + питание |
| J12 | FFC-40 0.5 мм | LCD RGB в CORE-2 (+BL_PWM, BL_ANODE/BL_CATHODE) | 23 + питание |
| J13 | IDC-16 2×8 | цифровое/питание | 4 + питание |
| J14 | IDC-26 2×13 | аналоговое поле | 12 |

Всего по PANEL-2: 4 разъёма (J11-J14) + J15 (1×14, SPI-альтернатива экрана, DNP).

