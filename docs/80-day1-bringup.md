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

---

## 6. P4 bring-up app (round 21): команды и ожидаемые выводы

Исходник: `firmware/idf_p4/main/app_main.cpp`; всё bring-up под
`CONFIG_IDF_TARGET_ESP32P4`, host-тесты не затрагиваются.

### Сборка/прошивка

```bash
cd firmware/idf_p4
idf.py set-target esp32p4
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor   # UART0 115200; или /dev/ttyACM0 (USB-JTAG)
```

### Ожидаемый лог (порядок)

```
I (xxx) bukifon: ==================================================
I (xxx) bukifon:  Bukifon P4 bring-up
I (xxx) bukifon:  target=esp32p4 rev=... cores=... features=0x...
I (xxx) bukifon:  IDF version: v5.5...
I (xxx) bukifon:  CPU: 400000000 Hz
I (xxx) bukifon:  flash: 16.0 MiB
I (xxx) bukifon:  PSRAM: 32.0 MiB (init=1)
I (xxx) bukifon:  free heap: ...
I (xxx) bukifon: I2C0 init OK: SDA=21 SCL=22 400000 Hz
I (xxx) bukifon:  I2C range 0x20-0x27: 4 device(s)
I (xxx) bukifon:  I2C range 0x48-0x4F: ...
I (xxx) bukifon:  I2C range 0x50-0x57: 1 device(s)
I (xxx) bukifon: I2C scan found N [0x20 0x21 0x22 0x23 0x36 0x57 0x60 0x61 ]
I (xxx) bukifon: I2C expected 8/8 PASS (...)
I (xxx) bukifon: display pattern color-bars (800x480 RGB565) — 5 s
I (xxx) bukifon: display pattern checkerboard ... — 5 s
I (xxx) bukifon: display pattern 1px-grid ... — 5 s
I (xxx) bukifon: display pattern text ... — 5 s
I (xxx) bukifon: engine bench: 1000 blocks x 64 frames, max=... us, mean=... us -> PASS
I (xxx) bukifon: engine bench criterion: max block <= 650 us
I (xxx) bukifon: mic I2S1: 48000 samples, RMS=... dBFS peak=... dBFS -> PASS
I (xxx) bukifon: mic criterion: RMS > -60 dBFS ...
I (xxx) bukifon: P4 bring-up sequence complete; heartbeat every 10 s
```

### Что делает каждый блок

| Блок | API IDF 5.5 | PASS/поведение |
|---|---|---|
| UART | `uart_set_baudrate(UART_NUM_0, 115200)`, `ESP_LOGI` | баннер/chip/rev/flash/PSRAM/IDF |
| I2C | `driver/i2c_master` (`i2c_new_master_bus`, `i2c_master_probe`) | диапазоны 0x20–0x27, 0x48–0x4F, 0x50–0x57 + реальные 0x36/0x60/0x61; PASS при 8/8 |
| Display | `esp_lcd_panel_rgb` + `esp_lcd_panel_draw_bitmap`, LEDC BL GPIO49 | 4 паттерна ×5 с; при ошибке init — log, без паники |
| Engine bench | `esp_timer_get_time`, модель p4_profile (8 FM voices + ZDF + limiter), 1000×64 | max ≤650 µs → PASS, иначе FAIL |
| Mic | `driver/i2s_std` I2S1, BCK40/WS41/DIN42, 48 кГц/24 бит, MIC_SEL54=1, 1 с | RMS/peak; PASS > −60 dBFS, нет данных → SKIP |

### Что проверить на железе (не проверено локально)

- Сборка `idf.py build` на home; возможны правки имён полей `esp_lcd_rgb_panel_config_t`
  (версия IDF 5.5) и `i2s_std_config_t` — API уже подобран под 5.5, но это
  первый реальный build.
- Timings RGB565 (PCLK 16 МГц, porches), полярность `pclk_active_neg`, порядок
  data_gpio_nums, HotLCD/ST7262 pinout; BL_PWM 49 (LEDC 5 кГц) и LCD_DISP 50.
- I2S MEMS: 24-бит left-justified в 32-бит слоте (`>>8`); если RMS нулевой —
  проверить J19/MIC_SEL/SW3/LED и формат слота.
- SW3 mute/LED и MAX9814 (line/mic) — day-2/factory self-test, не в этом app.
- USB HS composite/C6/SD/CV/GATE — следующие шаги; этот app их не трогает.
