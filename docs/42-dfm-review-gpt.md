# DFM/DFT-ревью (GPT): единый пого-поле, self-test, серийники, recovery

Источник — консультация GPT по производству. Внедряется в `hardware/*/dfm.md`,
`docs/38-dfm-testability.md` и RC DoD (docs/36). Платы пока PRE-FREEZE — это требования
к разводке, а не разрешение заказывать.

## 1. Test points: 30-точечное одностороннее пого-поле

Все точки: круглые пады Ø1.3–1.5 мм, mask opening Ø1.8–2.0 мм, шаг ≥2.54 мм, keepout 1 мм,
одна сторона, не ближе 3 мм к краю и 5 мм к стойкам/высоким деталям.

| Плата | Точек | Обязательные |
|---|---:|---|
| **CORE** | 14 | PGND/DGND/AGND, VBUS_CHG, VSYS, +3V3, USB D+/D−, CHIP_PU/RESET, BOOT/GPIO0, I2S_MCLK, I2S_ADC_DOUT, SD_CLK, SPI3_SCK |
| **PANEL-2** | 7 | GNDA/GND, +3V3_PANEL, +5V_LED, SDA, SCL, PANEL_IRQ, LED_DATA после shifter |
| **PWR-2** | 9 | BATT_CELL_P (Kelvin), VBAT после BMS, VSYS_SW, +12V, −12V, +5V, LED_RET, PWR_GOOD, PGND |

Не дублировать на CORE то, что доступно через PWR/PANEL-разъёмы (12V, −12V, 5V, 5V_LED,
N12_EXT, BATT_MON, LED_DATA, PWR_GOOD, EN_RAILS, BL_20V, LCD_CS). I²C проверять на PANEL-2.
Экономия — не за счёт падов, а за счёт числа pogo-контактов фикстуры: для 25 шт. хватает
ручного 30-pin прижима; BOOT/RESET/земли/силовые TP не убирать.

## 2. Self-test прошивки (по отбраковке на секунду)

| # | Тест | Время | Критерий |
|---:|---|---:|---|
| 1 | Power-on + brownout log | 1 с | 1 старт, reset reason ожидаемый |
| 2 | I²C scan | 0.3 с | строго адреса `20–23, 36, 57, 60, 61` |
| 3 | MCP23017 walking-bit | 1.5 с | 4 адреса, IRQ переключается |
| 4 | MCP3208 fixture vector | 0.8 с | 8 каналов 0.25/1.25/2.50 В, ±2 LSB |
| 5 | MCP4728→MCP3208/CV loopback | 1.5 с | 0–4 В, ошибка ≤20 мВ после калибровки |
| 6 | Codec loopback | 2.0 с | 1 кГц, −12 dBFS, gain ±1 dB, THD+N <−60 dB |
| 7 | SD scratch-file | 1.5–2.5 с | 1 МиБ write/read + CRC32, ≥0.7 MB/s |
| 8 | Display patterns | 1 с + 2 с оператор | RGB/white/black/checker без полос |
| 9 | WS2812 chase/current | 1.0 с | все LED, ток ±20 % |
| 10 | MAX17048 | 0.4 с | VCELL vs DMM ≤30 мВ |
| 11 | USB composite enum | 2–3 с | CDC+MIDI+HID+UAC |
| 12 | Органы управления | 15–25 с | 42 клавиши, 16×A/B/SW, 2 фейдера |
| 13 | CV/GATE external loopback | 3 с | 4 CV OUT→IN, GATE→IN |
| 14 | MIDI DIN loopback | 1 с | 100 пакетов, 0 ошибок |

**Loopback-плаг** для founders beta: CV OUT1–4→IN1–4, GATE→IN, LINE OUT→AUDIO IN через
10–20 кОм, MIDI OUT→IN; резистивная подпись — fixture ID. Панель — акриловая прижимная
«гребёнка» (42 клавиши группами 6–7), энкодеры — один щелчок CW/CCW/нажатие.
Целевое EOL: **2–2.5 мин** автоматики+оператора; полный цикл с прошивкой/наклейкой/упаковкой —
**6–8 мин/устройство**. Полный цикл батареи/FFT рельсов/30-мин прогон — квалификация партии,
не каждого экземпляра.

## 3. Serialization и traceability

- Отдельную EEPROM ради серийника **не ставить**: на CORE есть 24C32 (0x57) — для калибровок;
- identity — во flash `factory_data` (8–16 КиБ, две копии + CRC);
- eFuse MAC — неизменяемый якорь;
- OTP не прожигать в founders beta.
- Запись: magic, version, product, serial (`BKS3-26A-0001`), ревизии CORE/PANEL/PWR, дата,
  PCB/assembly batch, display MPN/lot, firmware factory version, calibration version,
  test station, test timestamp/result, MAC, CRC32.
- Чтение: прошивка `factory info`, CDC CLI `bukifon factory --json`, короткая строка в boot log;
  QR — серийник+ревизии, без персональных данных.
- **Метка на корпусе нужна**: 25×12/30×15 мм (лазер/термотрансфер), SN+ревизии+QR в нижнем отсеке;
  на внешней стороне — короткий SN.

## 4. Recovery/bootloader

- ESP32 ROM USB Serial/JTAG download (BOOT+RESET) — базовый аварийный путь; CDC — только
  интерфейс работающей прошивки.
- До PCB добавить: физические BOOT и RESET, доступные без разбора; их же на TP/pogo;
  USB D+/D− ESD и TP; UART0 TX/RX/GND как три DNP-пада; 10 кОм pull-up CHIP_PU + RC-reset;
  recovery при отключённых PANEL/PWR; known-good recovery image.
- Flash 16 МБ: bootloader/table/NVS 0.5 МБ, OTA A 4 МБ, OTA B 4 МБ, recovery/factory 2 МБ,
  factory data/coredump/assets — остаток.
- Политика: OTA pending → подтверждение после 30 с, audio task, mount SD, без brownout;
  3 неуспешных загрузки → rollback; клавиша при старте → safe mode (без Wi-Fi, сторонних
  модулей, SD-проектов и ±12 В); factory reset ≠ firmware recovery (не стирать калибровки).

## 5. DFM

- **Не 3 слоя**: CORE/PWR — 4 слоя (Signal/GND/Power/Signal); PANEL-2 — 4 слоя
  (2 слоя только после route-review); bow/twist PANEL-2 ≤0.75 %, лучше ≤0.5 %.
- Медь от M3: ≥1.5 мм до края шайбы, keepout Ø7–8 мм; fiducials Ø1 мм глобальные + local
  у FPC/QFN; tooling holes в панели.
- FPC-40: зафиксировать MPN, contacts top/bottom, pin 1 на шелке и сборочном чертеже;
  радиус FFC ≥5 мм, не под стойкой; разные интерфейсы не должны физически путаться.
- IDC — только shrouded/keyed; pin 1 треугольником на меди/шелке; силовой J3 — Micro-Fit 3.0.
- WS2812: 100 нФ на LED, bulk 470–1000 мкФ, series 22–47 Ω, первый LED ≤50–100 мм от shifter,
  широкие 5V/return, инжекция с двух концов, LED_RET не через AGND, fixture меряет ток.
- Панелизация: PANEL-2 360×190 — сама панель; CORE/PWR 2×2/2×3, rails 8–10 мм, 3 tooling holes,
  mouse-bites не у FPC/Micro-Fit/джеков, компоненты ≥3 мм от routed edge, QR ревизии/позиции.

## 6. Что обычно ломается на первых прототипах

1. Зеркальный/перевёрнутый FPC, неверный pitch/contact side.
2. Strap GPIO0/RESET не даёт войти в bootloader.
3. MCP4728 с одинаковым адресом/не запрограммированы 0x60/0x61.
4. WS2812 от ЛБП ок, при общей нагрузке — reset/шум.
5. Полярность/нумерация IDC, нестабильный I²C из-за длинного шлейфа.
6. QFN power IC: thermal pad/vias/силовой loop не по datasheet.
7. Крепёж/стойка касается дорожки или гнёт PANEL-2.
8. CV/GATE защита меняет точность/клиппирует раньше.
9. Аудио loopback ок, но Wi-Fi/BL/LED дают spur.
10. Корпус закрыт, а BOOT/RESET/SD недоступны.

## 7. План founders beta (3 инженерных + 2 валидационных)

| Этап | Проверка | Время |
|---|---|---:|
| A1 | AOI, полярность, сопротивление рельсов | 10 мин |
| A2 | PWR отдельно, current-limited | 20 мин |
| A3 | CORE отдельно: 3V3, boot, USB, flash | 15 мин |
| A4 | PANEL отдельно: I²C/IRQ/LED/матрица | 15 мин |
| A5 | Интеграция + автоматический self-test | 10 мин |
| A6 | Ручные controls/display/jacks | 10 мин |
| A7 | Power load/ripple/audio FFT | 30–45 мин |
| A8 | Thermal soak 60 мин | 60 мин |
| A9 | USB/SD/audio soak 4–24 ч | unattended |
| A10 | 10 циклов разборки/шлейфов | 20 мин |

На первых трёх: **60–90 мин активного труда** + soak. Затем ещё 2 units «по инструкции»:
сборка ≤90 мин, EOL ≤8 мин, **first-pass yield ≥80 %** на 5 прототипах, после ремонта — 100 %.

Не ремонтировать для выдачи founders: повреждение PCB/FPC, межслойное КЗ, нестабильный
USB/boot, повторный brownout, BMS/заряд вне порогов, hotspot >85 °C, аудио-шум от изгиба,
коробление PANEL-2 с заеданием клавиш. Ремонт допустим: непропай/перемычка, замена разъёма/
энкодера/LED, перепрошивка адреса MCP4728, калибровки.

## 8. Обязательно до заказа PCB

- [ ] MPN, pitch, contact side и полный pinout дисплея/FPC;
- [ ] TPS63000 placeholder → TPS63802/TPS63020 (или P4-аналог) с проверенным footprint;
- [ ] devkit-spike: USB composite, дисплей, SD, I2S, PSRAM, Wi-Fi одновременно;
- [ ] макет PWR: −12 V IBB, ripple, load-step, BQ24074 thermal/power-path;
- [ ] сверить символы/land patterns TPS61088, LMR33630, MAX17048, BQ297;
- [ ] пересчитать BOM (аномалия TL074 qty=20);
- [ ] Micro-Fit для силового production-интерфейса;
- [ ] DRC, creepage/current/thermal review, 1:1 mechanical print;
- [ ] TP/fixture keepout, fiducials, serial/revision/QR;
- [ ] доступ к BOOT/RESET/recovery при отключённых PANEL/PWR.

## Вердикт

1. DFT-база хорошая, но нужен единый 30-точечный pogo-поле до разводки.
2. EOL 2–2.5 мин реалистичен; полный цикл 6–8 мин/устройство.
3. Серийник — flash/NVS + MAC-якорь, калибровки — 24C32, на корпусе — SN/QR.
4. Стоп-факторы: PWR-стенд, devkit-spike, точный дисплей/FPC, TPS63802, recovery hardware.
5. Сначала 3 платы каждой ревизии, затем 2 validation units; партия 10–25 — после soak.

---

## 8. Factory self-test v1.0-rc: 21 пункт (реализация в прошивке)

`firmware/src/factory/selftest.*` расширен с 14 до **21** проверки по DFM CORE-2 §2;
`Hardware`-интерфейс, mock и P4-заглушки; runner/report/JSON; CLI `factory [--json]`
(`app/factory_main.cpp`). P4 без toolchain теперь отдаёт **SKIP** (`isAvailable=false`),
а не фальшивый FAIL/PASS.

| # | id | Что проверяется | Критерий | TODO(hw) |
|---:|---|---|---|---|
| 1 | power_on | rails, PWR_GOOD, reset reason, brownout | 1 старт, PWR_GOOD high, 0 brownout | реальные TP2–7/19/23–25 + PWR_GOOD |
| 2 | i2c_scan | I2C0 400 кГц | адреса `20–23,36,57,60,61` | шина на CORE-2/PANEL-2/PWR-2 |
| 3 | mcp23017_walking | 4 expander, IODIR/GPIO, INT | 4 ACK + IRQ toggles | панель + INT wire-OR |
| 4 | mcp3208_vector | fixture vector CH0–7 | 0.25/1.25/2.50 В ±2 LSB | fixture-резисторы |
| 5 | dac_adc_loopback | MCP4728→MCP3208/CV | ≤20 мВ | loopback-плаг |
| 6 | codec_loopback | PCM5102A→PCM1808 1 кГц | −12 dBFS, THD+N <−60 dB | аудио-кабель/фикстура |
| 7 | sd_scratch | 1 МиБ write/read | CRC32, ≥700 КБ/с | SDIO |
| 8 | display_patterns | RGB/white/black/checker, BL | 4 паттерна, нет полос | оператор + BL_PWM |
| 9 | ws2812_current | chase/current | все LED, ток ±20 % | LED_DATA/питание |
| 10 | max17048 | VCELL vs DMM | ≤30 мВ | I2C 0x36 PWR-2 |
| 11 | usb_composite | CDC+MIDI+HID+UAC | все классы, enumerate | USB HS |
| 12 | controls | 42 клавиши 6×7, 16 энкодеров, 2 фейдера | 42/42, 16/16, 2/2 | оператор/скан |
| 13 | cv_gate_loopback | CV OUT→IN, GATE | ≤20 мВ, gate OK | loopback-плаг |
| 14 | midi_loopback | DIN/USB note/CC/PC/clock | 100 пакетов, 0 ошибок, без дублей | DIN TRS + TinyUSB |
| 15 | eeprom | 24C32 @0x57, magic/SN | 32/32 байт, SN читается | I2C |
| 16 | mcp4728 | 2× MCP4728, readback | 8/8 каналов, ±1 LSB | DAC-калибровка |
| 17 | c6_link | esp-hosted RPC/version/Wi-Fi scan | <100 мс, версия, скан | C6 SPI-линк |
| 18 | cv_inputs | CV IN1–4, TVS | ±1 % FS, TVS не греется | калибратор + TVS |
| 19 | uart_boot | UART0 115200 + BOOT strap | лог + download boot | UART0/BOOT |
| 20 | serial_qr | EEPROM SN/rev/date vs QR | всё совпадает | 24C32 + QR-сканер |
| 21 | mic (D-91) | MEMS I2S1 1 с / VAD; MIC_SEL; SW3 mute; LED; electret loopback | RMS −60…0 dBFS, SNR ≥65 дБ, mute глушит, LED, ≤5 мс | I2S1/MAX9814/SW3/LED |

**Результат:** mock PASS **21/21** (JSON: schema `bukifon-factory-selftest-v1`,
`count:21`), P4 без toolchain — 21 SKIP. Скриншот станции:
[`firmware/artifacts/factory/selftest.png`](../firmware/artifacts/factory/selftest.png).
Тесты: 331/331 host (20 новых, включая SKIP, mic mute, MIDI no-duplicates, 42/16).
