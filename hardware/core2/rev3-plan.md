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
| 5 | DFM/TP | TP1–TP27 | **TP1–TP32** (TP28 LED_RET, TP29 I2S_BCK, TP30 I2S_LRCK — уже в схеме), **pogo-поле 6 падов**, fiducials 3×1 мм, 6 слоёв, BOOT/RESET/UART0 пады | нет (можно до P1) |
| 6 | Serialization | 24C32 U41 @0x57 | 24C32 + карта SN/rev/date/batch/калибровки (dfm.md §3), **QR/DataMatrix** на корпусе/плате | нет |
| 7 | Recovery | UART0 J4 + BOOT/RESET, OTA rollback | сохранить; тест-пады BOOT/GPIO35/36, UART0; recovery-процедура docs/43 | нет |
| 8 | Питание | +3V3/+3V3_C6/+3V3_MCU; +5/±12/5V_LED с PWR-2 J17 | сохранить; при H743 — те же 3.3 В (ядро 1.2 В внутр.), бюджет +0.3–0.5 А проверить | частично |
| 9 | Wi-Fi/BLE | ESP32-C6 по SPI (D-21) | сохранить C6 (для H743 — единственный радио-путь), footprint оставить | да: C6 vs без |
| 9a | **Mic-вход (D-91)** | нет | **I2S1 RX** MEMS с PANEL-2 (BCK/WS/DATA, GPIO40/41/42, J19 IDC-6) + **3.5 мм jack → MAX9814 AGC → TS5A23157 line/mic → PCM1808 VINL/VINR**; MIC_SEL=GPIO54; TP31/TP32; SW3 mute + LED «MIC ON» (D-92); **SDIO 4-bit→1-bit** (D1–D3 отданы I2S1; ~6 МБ/с) | нет (можно до P1) |
| 10 | PANEL-2 | J14/J15/J16 canon rev.2 | canon rev.3: RGB565 FPC-40 + J14/J16; **J19 IDC-6 mic (MEMS I2S1, canon 1=BCK 2=GND 3=WS 4=GND 5=DATA 6=+3V3)**; DSI — J19? → выделить J21 (опция); PANEL-2 rev.3: MEMS ICS-43434/SPH0645 | да (D-19/D-91) |
| 11 | Несущая/крепёж | 6×M3, docs/21 | 6×M3 + зона под pogo/шлейфы, панелизация 2×2, antenna keepout C6 | нет |
| 12 | DFM-стек | — | 6 слоёв, USB HS 90 Ω, RGB matched, 20 В BL зазоры, FPC key, **mic: экран J19/аналоговый keepout** | нет (цена/фабрика) |

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

## 4a. Mic (D-91) — реализация в rev.3

| Узел | Реализация | Nets/пины |
|---|---|---|
| MEMS на PANEL-2 | I2S1 RX, slave, 24 бит/48 кГц; PANEL-2 rev.3 (ICS-43434/SPH0645), акустический порт/сетка | `MIC_BCK` GPIO40, `MIC_WS` GPIO41, `MIC_DATA` GPIO42; `3V3_MIC` |
| Разъём MEMS | J19 IDC-6 canon: **1 BCK, 2 GND, 3 WS, 4 GND, 5 DATA, 6 +3V3** (mates PANEL-2 J16 1:1); экранированный кабель ≤150 мм | 3.3 В через FB8 + 10 мкФ/100 нФ; ESD USBLC6 ×2 |
| 3.5 мм jack | J20 TRS (tip=signal, ring=bias 2.2 к), D30 SMAJ5.0A, C127 100 нФ | `MIC_IN`, `MIC_BIAS` |
| MAX9814 | AGC 40–60 дБ; CT 470 нФ, CG 2.2 мкФ, BIAS 470 нФ; **TH = делитель 150k/100k от MICBIAS**, EP(15)→GND; SHDN active-low (SW3 mute) | U46; `MIC_AGC` → C126 1 мкФ |
| Line/mic switch | TS5A23157 (сверено): 1 IN1, 2 NO1(MIC), 3 GND, 4 NO2(MIC), 5 IN2, 6 COM2, 7 NC2(LINE R), 8 V+, 9 NC1(LINE L), 10 COM1; COM1/COM2 → C78/C80 → PCM1808; IN=L→NC=LINE, IN=H→NO=MIC | U47; `MIC_SEL` GPIO54 (0=LINE, 1=MIC), R110 100k PD |
| Приватность | SW3 (MIC MUTE) тянет SHDN→GND; Q5+D31 «MIC ON» | D-92 |
| TP | TP31 `MIC_DATA`, TP32 `MIC_BCK` | доступ после сборки |
| Изменения в rev.2 | удалены R25/R26/C52 (VBUS_DET), R32-R34 (SDIO D1-D3 pull-ups); J5 → 1-bit SDMMC (DAT1/2/3 NC) | — |

**Компромисс:** SDIO 4-bit → **1-bit** (D1-D3 отданы I2S1): ~6 МБ/с достаточно для 8-дорожечного
стриминга/записи, но загрузка проекта медленнее; если нужен 4-bit — освободить GATE2 (GPIO53),
SD_CD (GPIO45), VBUS_DET (уже занят MIC_SEL) и найти третий (LED/BL_PWM/PANEL_IRQ) — не рекомендуется.
**Остаётся:** PANEL-2 rev.3 (MEMS + J19-ответка), прошивка I2S1 DMA/VAD (docs/71), проверка pinout
MAX9814/TDFN-14 и TS5A23157/DGS по datasheet до PCB, сертификация/ESD по doc 37.

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
8. Mic (D-91): PANEL-2 rev.3 MEMS (MPN/порт) и ответный J19; **pinout MAX9814/TDFN-14 и
   TS5A23157/DGS сверены с datasheet 2026-11-06 — ЗАКРЫТО** (dfm.md §5a, docs/71 §6);
   MIC_SEL = GPIO54 (бывший VBUS_DET) — подтвердить потерю VBUS-детекта (USB-режим через BQ/перечисление).
9. D-92: SW3 mute + LED «MIC ON» — в rev.3; прошивка запрещает запись при mute; нужен ли второй
   аппаратный mute для MEMS на PANEL-2.
