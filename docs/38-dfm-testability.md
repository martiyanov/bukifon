# DFM / testability пакет — P4-ветка (CORE-2 + PANEL-2 + PWR-2)

> **Статус: PRE-FREEZE / DO NOT FABRICATE.** Документ — приоритетный для **P4-ветки**
> (первый SKU по решению заказчика: P4 + RGB565/DSI). **S3-base — «lite later»**; его
> сокращённый пакет — `hardware/cores3/dfm.md`, полный DFM для него не блокирует P4.
> Основание: `docs/36-rc-definition.md` §2 (критерии приёмки) и §4.4 (DFM до разводки).

## 1. Что входит

| Плата | DFM-документ | Основное |
|---|---|---|
| **CORE-2 (P4)** — главная | `hardware/core2/dfm.md` | TP ≤30, self-test 20, серийник (24C32/OTP/flash), recovery (UART0/BOOT/OTA), DFM 6 слоёв/USB HS/FPC-40/6×M3, чек-лист 20 |
| **PANEL-2** | `hardware/panel2/dfm.md` | TP ≤20, self-test матрицы/энкодеров/фейдеров/LED/джеков, DFM FFC-40/IDC, чек-лист 15 |
| **PWR-2** | `hardware/power2/dfm.md` | TP рельсов/PWR_GOOD/EN, self-test БП/гейджа/NTC, DFM 3 А/J3, чек-лист 15 |
| CORE-S3 (lite later) | `hardware/cores3/dfm.md` | сокращённо: TP, self-test lite, O-17/O-18, краткий DFM |

## 2. Test points — сводка

- **CORE-2:** TP1–TP30 (все в схеме rev.2+rev.3-итерация: TP28 `LED_RET`, TP29 `I2S_BCK`, TP30 `I2S_LRCK`). Рельсы: VSYS, +12, −12 (N12_EXT), +5 (5V_EXT), +3V3, +3V3_C6,
  +3V3_MCU, 5V_LED, BL_20V, LED_RET; сигналы: I2S (MCLK/BCK/LRCK/DIN/DOUT), USB HS D+/D−,
  SDIO, I2C, SPI2/C6, CV, MIDI, UART0/BOOT. Доступ после сборки, не под разъёмами/шлейфами.
- **PANEL-2:** 3V3/5V/GND, I2C/INT, LED_DATA, BL_PWM/BL_ANODE, CV/GATE (J14), фейдеры.
- **PWR-2:** PACK+/VBAT/VSYS, +12/−12/+5/5V_LED/LED_RET, PWR_GOOD, EN-линии, FUEL I2C, NTC.
- **CORE-S3 (lite):** TP2/5/6/20/23/24/25/26 + сигнальные TP9–TP18/27.

## 3. Self-test — уровни

| Уровень | Кто | Что | Время |
|---|---|---|---|
| **L0** | фабрика/сборка | визуальный контроль, ICT/прозвонка рельсов, полярность, TP | 2–3 мин |
| **L1** | прошивка bring-up | boot, рельсы (PWR_GOOD/BATT_MON), I2C-скан, EEPROM SN, USB enumerate | 30 с |
| **L2** | BIST | C6 линк, MCP23017/MCP4728/MCP3208, кодек loopback, RGB-дисплей, SD, панель (матрица/энкодеры/фейдеры/LED), CV/GATE loopback, MAX17048/NTC | 2–5 мин |
| **L3** | soak | audio/UI/USB/SD стресс 30–60 мин + 24 ч, тепловой контроль | 0.5–24 ч |

Полные таблицы «тест → метод → pass/fail» — в §2 `hardware/core2/dfm.md` (20 тестов),
`hardware/panel2/dfm.md` §2 (8), `hardware/power2/dfm.md` §2 (8).

## 4. Связь с RC DoD (`docs/36`)

`docs/36` — Definition of Done для v1.0-rc (S3-base), но его §2 задаёт общие критерии,
которые переносятся на P4-ветку (с поправкой на P4: 8×8 UAC2/HS USB, RGB565/DSI, 32 МБ PSRAM):

| Тест docs/36 §2 | Как закрывается DFM/self-test |
|---|---|
| 1. Audio stress 1 ч | L3 audio soak; кодек loopback (CORE-2 §2 т.8), BIST метрики |
| 2. UI 10 мин | L2 дисплей/панель тесты; L3 UI soak; fps full/partial |
| 3. USB composite 30–60 мин | L2 USB enumerate; L3 soak; HS D+/D− TP11/12 |
| 4. Power/load-step | PWR-2 §2 (рельсы/тепло); CORE-2 TP2/3/4/5/6/7 |
| 5. SD corruption/recovery | L2 SDIO тест; L3 hot-remove; recovery-сценарий |
| 6. 24 ч soak | L3; журнал метрик прошивки |
| 7. Сборка 3–5 шт. | DFM/сборочный чек-лист, корпус docs/21 |
| 8. Self-test PASS | L1+L2 BIST (этот пакет) |

## 5. Производственный тест (поток)

1. **Входной контроль** плат/шлейфов/разъёмов (визуал, FPC-40 ключ).
2. **L0** — рельсы/КЗ/полярность на стенде (TP + ICT-адаптер при серии).
3. **L1+L2** — прошивка BIST через USB/UART0; лог в EEPROM/файл; SN/QR.
4. **L3** — выборочно (1 из N) + 100 % короткий soak.
5. **QC-выборка** (docs/39-kit) и запись результата в EEPROM лог (offset 0x100).

## 6. Открытые вопросы к Lead

1. **P4 JTAG/DFU:** подтвердить на P1 — recovery через UART0+BOOT (P4 ROM) или нужен USB DFU
   (в приложении esp_tinyusb); отдельный JTAG-разъём не заложен.
2. **24C32** использовать как основной носитель SN/калибровки (есть, I2C 0x57) — подтвердить
   карту (этот пакет) до разводки.
3. **TP28–TP30** добавлены в `CORE-2.kicad_sch` (DFM-пады); отдельной правки схемы не требуется.
4. **MAX17048 (0x36) и EN-линии** приходят с PWR-2 — подтвердить адреса/полярности на связке.
5. **S3 lite:** O-17 исправлен (TL074 = 4 корпуса), O-18 зафиксирован (TPS63000 placeholder
   → TPS63802/TPS63020); замена символа/футпринта — до PCB lite-платы, P4 не блокирует.
6. **FPC-40 RGB pinout (D-19)** и выбор панели/DSI — до финального DFM-ревью CORE-2.
