# День 1 с железом: пошаговый прогон (PWR → P1 → CORE-2)

Runbook на момент, когда приходят стенды/платы. Цель — за минимум дней получить ответ:
**PWR проходит 13/13? P4 тянет? Какой MCU фиксируем?** Всё остальное — потом.

## 0. Что должно быть на столе

- PWR-стенд (EVM вариант A + bare IC + электронная нагрузка) — docs/44, bench-bom;
- P1-стенд: P4 Function-EV, H743 Nucleo, S3 DevKit, кодеки, LCD 800×480 + FPC-адаптер;
- мультиметр, осциллограф (ripple), USB-UART 3.3 В, кабели, ПК с ESP-IDF 5.5;
- программатор/щупы, DMM-логи: **docs/pwr-results-template.csv**.

## 1. PWR: 13 измерений (2.5 дня)

1. Собрать нагрузку по bench-bom; **не подключать платы**, только EVM.
2. Заполнять `docs/pwr-results-template.csv` по мере измерений.
3. Гейт: `python3 tools/pwr_bench_check.py docs/pwr-results.csv --strict`.
4. **Stop/go**: любой FAIL в T3/T4/T5/T6 (рельсы/load-step) → фикс макета, повтор;
   **PCB не заказывать**, пока gate не PASS 13/13.
5. Тепло: T11 ≤70 °C при 5 В/1 А (10 мин). Если выше — снизить ток или радиатор.

## 2. CORE-2 (собранная) — bring-up 15 шагов

| # | Действие | Ожидаемо | Провал → |
|---|---|---|---|
| 1 | Визуальный осмотр, прозвонка 3V3/5V/GND (без питания) | нет КЗ, <1 Ом GND | искать пайку |
| 2 | Подать 5 В (ток-лимит 0.3 А) | ток 60–120 мА, PWR_GOOD | rails, F1 |
| 3 | UART0 115200, BOOT+RESET | лог `target=esp32p4`, PSRAM 32 МБ | USB/UART, boot strap |
| 4 | Flash hello (`idf.py -p PORT flash monitor`) | лого + I2C-скан | драйвер, порт |
| 5 | I2C-скан (MCP23017 ×4, MCP3208, 24C32, MAX17048, MCP4728 ×2) | 8/8 адресов | адреса/пайка |
| 6 | Display test (RGB565 паттерн) | 800×480, без полос | FPC, BL, init |
| 7 | Matrix test 42/16/2 | все клавиши/энкодеры/фейдеры | матрица/разъёмы |
| 8 | DAC/ADC loopback (PCM5102A/PCM1808) | синус 1 кГц, THD <0.1 % | I2S, MCLK |
| 9 | CV/GATE loopback | 0–5 В, шаг 1/12 В | MCP4728/калибровка |
| 10 | MIDI DIN/USB loopback | note/CC/PC/clock без дублей | TRS, TinyUSB |
| 11 | Микрофон: MEMS 1 с/VAD, SNR ≥65 дБ; SW3 mute → запись блокируется | PASS | J16/J19, MAX9814, SW3 |
| 12 | SD/PSRAM | запись/чтение | SDIO 1-bit |
| 13 | C6 link (esp-hosted) | RPC <100 мс, Wi-Fi scan | прошивка C6 |
| 14 | Self-test 21 | **21/21 PASS** | docs/42 §8 |
| 15 | 24 ч burn-in | без ресетов/перегрева | питание/тепло |

## 3. P1: P4 vs H743 (2–3 дня)

1. P4 EV: `idf.py set-target esp32p4 && idf.py build && idf.py flash monitor` — hello.
2. Display: esp_lcd RGB565 800×480 — 30+ fps, без tearing.
3. Engine + UI: перенести engine, прогнать `firmware/bench/p4_profile` (max block ≤650 µs, UI ≥30 fps).
4. USB: TinyUSB UAC2 8×8 + MIDI + HID; проверить на ПК (ASIO/CoreAudio).
5. H743: тот же engine/P1-скрипт, max block ≤650 µs, USB FS stereo (без 8×8).
6. Записать результаты в `docs/56-p1-measurements.md` + таблица решений.
7. **Гейт MCU**: P4 проходит → P4 primary; нет → H743 (CORE-2-H743), P4 — в lite.

## 4. Что делать, если…

| Симптом | Быстрая проверка |
|---|---|
| PWR не стартует | ток-лимит, PWR_GOOD, EN, вход 5 В |
| P4 не виден по USB | BOOT strap, USB-C SBU, кабель data |
| Экран белый/полосы | FPC защёлка, BL_EN, RGB565 порядок, PCLK |
| Микрофон шумит/тихий | поролон/сетка, GAIN, MIC_SEL, J19 канон |
| I2C-скан пуст | подтяжки, адреса (A0–A2), питание 3V3 |
| Self-test FAIL | JSON отчёт (id/detail) → docs/42 §8 |

## 5. Артефакты дня 1

- `docs/pwr-results.csv` + gate PASS;
- `docs/56-p1-measurements.md` (P4/H743/S3);
- self-test JSON 21/21;
- решение о MCU (D-xx в spec/90) и go/no-go PCB.
