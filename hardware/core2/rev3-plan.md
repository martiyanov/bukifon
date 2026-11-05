# CORE-2 rev.3 — план под P4-first / RGB565 / DSI

> **STATUS: PRE-FREEZE / DO NOT FABRICATE.** Решение заказчика **D-58**: первый SKU — P4-версия
> с RGB565/DSI, S3-base — «lite later». Rev.3 — целевая плата P4-ветки; этот документ фиксирует
> дельту от rev.2 и **provides H743-fallback**, чтобы rev.3 не стала тупиком, если P1-стенд
> покажет проблему P4. Схема rev.2 уже содержит TP1–TP30; см. `dfm.md`, `docs/38`, `docs/43`.

## 1. Таблица rev.2 → rev.3

| # | Узел | rev.2 (сделано) | rev.3 (план) | Ждёт P1? |
|---|---|---|---|---|
| 1 | Дисплей | FFC-40 RGB565, 25 сигналов (20 LCD + I2C + INT + BL_PWM + DISP + BL_ANODE/CATHODE), PANEL-2 J12 canon | **RGB565 FPC-40** под выбранную панель: pinout/ключ/stiffener по D-19; **DSI — опция rev.3.1** (MIPI DSI 2-lane, отдельный FFC-30/40 + адаптер); BL boost остаётся на CORE-2 | да: MPN панели, RGB vs DSI |
| 2 | MCU | слот 2×32 «логический контракт» P4-модуля | финальный **mezzanine/слот** под P4-модуль (P1) с альтернативной посадкой H743 | да: P4 vs H743 |
| 3 | PSRAM | 32 МБ (модуль TBD) | 32 МБ PSRAM, частота/тайминги по P1 | да |
| 4 | USB HS | выделенные pin49/50, USB-C composite, ESD/CC/VBUS-детект | сохранить; добавить impedance/TP, при H743 — **ULPI PHY** (USB3300) footprint | частично |
| 5 | DFM/TP | TP1–TP27 | **TP1–TP30** (TP28 LED_RET, TP29 I2S_BCK, TP30 I2S_LRCK — уже в схеме), **pogo-поле 6 падов**, fiducials 3×1 мм, 6 слоёв, BOOT/RESET/UART0 пады | нет (можно до P1) |
| 6 | Serialization | 24C32 U41 @0x57 | 24C32 + карта SN/rev/date/batch/калибровки (dfm.md §3), **QR/DataMatrix** на корпусе/плате | нет |
| 7 | Recovery | UART0 J4 + BOOT/RESET, OTA rollback | сохранить; тест-пады BOOT/GPIO35/36, UART0; recovery-процедура docs/43 | нет |
| 8 | Питание | +3V3/+3V3_C6/+3V3_MCU; +5/±12/5V_LED с PWR-2 J17 | сохранить; при H743 — те же 3.3 В (ядро 1.2 В внутр.), бюджет +0.3–0.5 А проверить | частично |
| 9 | Wi-Fi/BLE | ESP32-C6 по SPI (D-21) | сохранить C6 (для H743 — единственный радио-путь), footprint оставить | да: C6 vs без |
| 10 | PANEL-2 | J14/J15/J16 canon rev.2 | canon rev.3: RGB565 FPC-40 + J14/J16; DSI — J19 (опция) | да (D-19) |
| 11 | Несущая/крепёж | 6×M3, docs/21 | 6×M3 + зона под pogo/шлейфы, панелизация 2×2, antenna keepout C6 | нет |
| 12 | DFM-стек | — | 6 слоёв, USB HS 90 Ω, RGB matched, 20 В BL зазоры, FPC key | нет (цена/фабрика) |

## 2. Keep / drop / change по узлам

**Keep (без изменений):** аудио PCM5102A+PCM1808 + TL072; CV 2×MCP4728 + MCP3208 + TL074;
MIDI TRS; USB-C + BQ24074 charge/path; BL boost MT3608 #3; ферриты/защита входов; PANEL-2 J14/J16
canon; PWR-2 J17/J18; 24C32; DNP-список rev.2 (MT3608 #1/#2, MC34063, BMS, EXPRESSION).

**Change:** дисплейный разъём/пинаут под выбранную RGB565-панель (D-19); MCU-посадочное место
(финальный P4-модуль + опция H743); DFM-пакет (30 TP + pogo + fiducials + 6 слоёв); серийник/QR;
recovery-пады; при DSI — дополнительный FFC и перепиновка J15 (rev.3.1).

**Option (rev.3.1 / fallback):** DSI-панель (MIPI DSI 2-lane) вместо RGB565; H743-мезонин
(LTDC RGB, ULPI, SDRAM); второй C6-линк (SDIO) если появятся GPIO; внешний 5 В вход.

**Drop:** идея «разводить RGB565 и DSI одновременно на одном FFC» — несовместимо; выбор один.

## 3. Что ждёт P1-замеров (P4 vs H743)

1. P4-стенд: PSRAM 32 МБ, DMA/DSI, USB HS, аудио, C6-link — пропускная способность/латентность.
2. P1 должен ответить: **P4 проходит** (-> rev.3 P4) или **нет** (-> H743 fallback).
3. Выбор панели: RGB565 MPN + DE-only/HS/VS; DSI-панель как rev.3.1.
4. Финальный физический модуль P4 (или H743-мезонин) и его посадочное место.
5. Бюджеты PWR-2 на связке (VSYS 3 А, +5 1.6 А) при 32 МБ PSRAM и RGB — подтвердить.
6. DFM: импедансы/стекло 6 слоёв и цены фабрики; pogo/TP доступность.

## 4. H743 fallback — чтобы rev.3 не была тупиком

Если P1 покажет, что P4 не проходит, CORE-2 rev.3 должна допускать H743 **без респина**.

| Что меняется | Как заложить в rev.3 |
|---|---|
| MCU | **Мезонин/слот** с двумя посадками: P4-модуль (2×32) и H743-модуль (LQFP176/BGA); общий коннектор/крепёж, разные keep-out |
| Дисплей | H743 — **LTDC RGB565** (те же FPC-40, другой pin mapping); DSI у H743 нет -> RGB565 остаётся общим знаменателем |
| USB HS | H743 — **ULPI** (USB3300 + 60 МГц); заложить footprint PHY + клок + 3.3 В |
| Память | H743 — **SDRAM 32 МБ** (FMC) рядом с мезонином; P4 — PSRAM на модуле (SDRAM DNP) |
| Тактирование | P4 40 МГц vs H743 25 МГц — два кристалла/перемычки |
| Recovery | H743 — DFU через USB (ULPI) или BOOT0; P4 — UART0; оба: BOOT/RESET/UART0 пады |
| Радио | H743 без Wi-Fi/BLE -> **C6 остаётся обязательным** (SPI esp-hosted, D-21) |
| Питание | H743: ядро 1.2 В внутр., IO 3.3 В; +3V3 rail тот же, бюджет +0.3–0.5 А; VTref/SWD |
| JTAG/SWD | добавить SWD/JTAG пады (H743), у P4 — UART0/BOOT |
| Софт | абстракция HAL: display (LTDC vs DSI/LCD_CAM), USB (ULPI vs HS PHY), radio (C6 SPI) — firmware spike |

**Вывод:** rev.3 = «MCU-мезонин + общий RGB565 FPC-40 + C6 + ULPI/SDRAM option footprints».
Это удорожает плату (~+$5–10) и площадь, но исключает второй респин при смене MCU.

## 5. Что можно делать до P1

1. Утвердить этот план и DNP/keep-list; обновить реестр (D-58..) и docs/38/43.
2. DFM-пакет: 30 TP + pogo-поле (6 падов: 3V3, GND, UART0 TX/RX, BOOT, RESET), fiducials,
   стекло 6 слоёв, импедансы — отдать фабрике на review.
3. Библиотека посадочных мест: P4-модуль, H743-мезонин, ULPI PHY, SDRAM, RGB565 FPC-40 (два MPN),
   DSI FFC (rev.3.1), pogo.
4. Серийник/QR: карта 24C32, генератор QR, поле на шелкографии.
5. Recovery/bring-up: docs/43, прошивка self-test (dfm.md §2).
6. Shortlist панелей RGB565 (MPN, FPC-40, ключ) и DSI (rev.3.1); запросить datasheet (D-19).
7. Смета rev.3 (BOM + PCB 6 слоёв + мезонин/опции) и план прототипов.

## 6. Открытые вопросы

1. P1-результат P4 vs H743 (кто выигрывает) — от него зависит populate-вариант.
2. Панель RGB565 MPN + DE-only/HS/VS; DSI — нужен ли rev.3.1 вообще.
3. Мезонин: один коннектор на два MCU или два варианта платы (цена/надёжность).
4. ULPI/SDRAM option: populate по умолчанию DNP или отдельный SKU.
5. Pogo-поле: 6 падов достаточно (3V3/GND/UART0/BOOT/RESET)?
6. Бюджет PWR-2 при 32 МБ PSRAM/RGB: подтвердить на P1.
7. DNP-список rev.2 остаётся (46 позиций) или что-то возвращается под P4-first.
