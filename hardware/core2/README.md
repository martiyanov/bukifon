# CORE-2 (rev.2) — исследовательская схема ядра на ESP32-P4

> ## ⛔ PRE-FREEZE / DO NOT FABRICATE
> **Схема не готова к заказу плат.** Нельзя отправлять в производство до:
> 1) бенчмарка P1 (реальные токи/тепло/производительность ESP32-P4 + PSRAM),
> 2) подписи требований `spec/90-requirements-registry.md` (design freeze),
> 3) выбора физического MCU-модуля/адаптера под слот J-MCU.
> Это исследовательская ревизия (rev.2) новой архитектуры, а не релиз.

**MCU:** ESP32-P4NRW32 (ESP32-P4, 55 GPIO, 32 МБ PSRAM в корпусе, QFN104).
**Сопроцессор радио:** ESP32-C6-MINI-1 (Wi-Fi 6 + BLE 5.3), связь с P4 по SPI
(esp-hosted), отдельный LDO +3V3_C6. Для сборки на ESP32-S3 (радио нативно) C6 —
**DNP**, площадка не паяется.


## 0a. rev.2 (документы) — синхронизация с PWR-2

> **P4-ветка — главная** (решение заказчика): DFM/testability — [`dfm.md`](dfm.md) и
> [`docs/38`](../../docs/38-dfm-testability.md); S3-base — «lite later» (`hardware/cores3/`).

> **Схема `CORE-2.kicad_sch` — rev.2** (ERC 0 errors / 0 warnings): J17/J18, входы
> N12_EXT/+5V_EXT, EN от MCP23017, re-pin J14/J15/J16 по PANEL-2, DNP-флаги.
> Подробности — [`rev2-plan.md`](rev2-plan.md) §10. Решения: D-32…D-36, открытые: O-1…O-12.

| Что | rev.2 |
|---|---|
| Питание | рельсы **±12 В / +5 В / 5V_LED** приходят с **PWR-2** (J17 = IDC-20, ответный PWR-2 J3); CORE-2 формирует только +3V3 / +3V3_C6 / +3V3_MCU / BL_20 В |
| DNP | MT3608 #1 (+12 В), MT3608 #2 (+5 В), MC34063 (−12 В), BMS+пакет (U23/Q1/Q2/J2/TH1), level shifter LED (U44/R90), EXPRESSION/SPARE (R5/J13/R73/C99/R74/C100/TB2) — **46 позиций** (39 по D-34 + 7 по N-2) |
| Новые входы | `12V_EXT` (существующий D2 SS34), **`N12_EXT`** (D19 SS34 + D20 SMAJ15A + C112/C113), `+5V_EXT` (C114/C115), `5V_LED`/`LED_RET` |
| Разъёмы | **J17** IDC-20 (PWR-2 J3, пары PGND), **J18** IDC-12 (PWR-2 J4: BATT_MON, NTC, I2C, PWR_GOOD, 4× EN); при 3 А — альтернатива Micro-Fit 3.0 (O-5) |
| EN | 4 EN PWR-2 ← **2 линии MCP23017 PANEL-2 0x23**: GPA7 = `EN_RAILS` (+12/−12/+5), GPB6 = `EN_LED5`; дефолт: рельсы ON, LED OFF (D-33) |
| +5 В | бюджет **1.0 → 1.6 А**; рекомендация — **вариант (b)**: MP1584 остаётся на +5 (1500 мА из 1.6 А / 2.0 А), +12 остаётся 150 мА; вариант (a) (MP1584 на +12) — только после 2S/стенда, т.к. +12 366/420 = запас 13 % (O-1) |
| VSYS | пик 2.74 А @3.7 В (3.38 А @3.0) при 3 А power-path → прошивочный cap WS2812 0.55 А + профиль яркости, внешний 12 В для +12; O-2 |
| PANEL-2 sync | J13.9/13 `5V`→`5V_LED`, J13.16 `GND`→`LED_RET`, J13.15 NC→`EN_RAILS` (0x23 GPA7), J14.25 NC→`EN_LED5` (0x23 GPB6); J14/J15/J16 re-pin по PANEL-2 канону (открытые N-2/N-3) |

Артефакты rev.2: [`rev2-plan.md`](rev2-plan.md), обновлены [`power-tree.md`](power-tree.md)
(импортируемые рельсы, VSYS), [`interfaces.md`](interfaces.md) §0/§3a/§7, [`pinmap.md`](pinmap.md)
(J17/J18, EN-карта, rev.2 harness), [`BOM-core2.csv`](BOM-core2.csv) (колонка rev.2: DNP/NEW).

**Открытые O-8…O-12 (решения для rev.2):** O-8 `PWR_GOOD`/`FUEL_ALRT` → свободные GPIO ESP32-C6
(для S3 — опрос MAX17048 по I2C); O-9 CVIN3/4 → MCP3208 CH4/CH5 (U45 TL074), GATE_IN — на PANEL-2
(MCP23017 0x23 GPB7), EXPRESSION убран; O-10 цифровое расширение TDM/I2S+SPI отложено до rev.3;
O-11 J3 — IDC-20 для прототипа, Micro-Fit 3.0 для rev.2 (D-40); O-12 CV OUT 5/6 не выведены
в PANEL-2 J14 (только CV OUT1-4) — тест-пэды/резерв до rev.3.

---

## 1. Что в CORE-2

| Блок | Состав |
|---|---|
| **MCU** | слот J-MCU 2×32 (64 pin) — *логический контракт* под модуль/адаптер ESP32-P4; 6×100 nF + 2×10 uF на +3V3_MCU; RESET (RC), BOOT (GPIO35, download boot), UART0 TP (GPIO37/38), VBUS-детект (GPIO54) |
| **USB** | один USB-C 16P: USB 2.0 **HS** (выделенные USB_DM/DP pin49/50), ESD USBLC6-2SC6, CC 5.1 к (UFP), VBUS → polyfuse 1.5 A → BQ24074. TinyUSB composite: HID + MIDI + UAC2 + CDC |
| **Радио** | ESP32-C6-MINI-1 (SPI esp-hosted + handshake/data-ready + reset), keep-out ≥15 мм, внутренняя PCB-антенна; +3V3_C6 отдельный LDO 600 мА; DNP для S3 |
| **SD** | microSD **SDIO 4-bit** (SDMMC slot0, GPIO39…44), CD, pull-up 10 к, 10 uF/100 nF |
| **Питание** | USB-C 5 V → BQ24074 (power-path) → VSYS; **rev.2:** ±12 В/+5 В/5V_LED с PWR-2 (J17), DNP MT3608 #1/#2, MC34063, BMS; остаются **BL boost +20 В**, MP1584 → +3V3_MCU, AP2112K ×2 → +3V3/+3V3_C6; ферриты + 3 «земли» (AGND/DGND/PGND) с net-tie |
| **Аудио** | PCM5102A (I2S DAC) + PCM1808 (I2S ADC, 24/96), общие MCLK/BCK/LRCK; TL072 буферы LINE/PHONES; задние джеки LINE OUT L/R, PHONES, AUDIO IN L/R |
| **CV** | 2× MCP4728 (0x60/0x61, LDAC=GND) + 6× TL074 ×4.9 (+1к/BAT54S) → CV OUT 1…6; CV IN 1/2: 100к/16.5к + сдвиг 1.65 В; MCP3208 CH0…7 (CV IN ×2, фейдеры ×2, EXPRESSION, резерв, BATT_MON, TEMP_MON) |
| **MIDI** | TRS-A IN (6N137 + 220R) / OUT (74HCT125 + 33R/220R), 5 В логика |
| **Шина** | 2× IDC-26 аналоговая (R-11/R-22): ±12 В, CV1…4, GATE1/2, AUDIO IN/OUT L/R; на каждый порт polyfuse + SS34 + TVS; отдельный J-DIG-EXP (IDC-16) для TDM/I2S + SPI mailbox + I2C |
| **PANEL-2** | 4× MCP23017 (0x20…0x23, 61 линия) → 3 сигнала SDA/SCL/INT; J14 IDC-26 (I2C, фейдеры, CV/GATE, LED_DATA) + J15 FFC-40 (RGB565 800×480: 20 + I2C(2) + INT + BL_PWM + BL_ANODE/CATHODE = 25 сигналов). 10 верхних джеков: CV OUT 1…6 + CV IN 1/2 + GATE 1/2 |
| **Задняя панель** | 5 × 3.5 мм аудиоджеков (LINE L/R, PHONES, AUDIO IN L/R), MIDI TRS in/out, DC 12 V, EXPRESSION, USB-C |

## 2. Файлы

| Файл | Что это |
|---|---|
| `CORE-2.kicad_sch` + `CORE-2.kicad_pro` | схема KiCad 10 **rev.2** (S-expression, 1 лист A0) |
| `rev3-plan.md` | план rev.2 → rev.3 (P4-first/RGB565/DSI), keep/drop/change, **fallback H743**, что ждёт P1 |
| `dfm.md` | DFM/testability P4: TP1–TP30 (все в схеме), self-test 20, серийник (24C32), recovery, DFM 6 слоёв, чек-лист 20 |
| `rev2-plan.md` | rev.1 → rev.2: DNP (46), входы ±12/+5, EN, J17/J18, +5 бюджет, PANEL-2 sync, O-8…O-12; §10 — что уже внесено в схему |
| `picomod.kicad_sym`, `sym-lib-table` | проектная библиотека (ESP32-P4_MOD, ESP32-C6-MINI-1, PCM1808, MP1584_MOD, 74HCT125, 74HCT1G125, TP) |
| `CORE-2.pdf`, `CORE-2.svg.gz` | экспорт схемы (баннер PRE-FREEZE на первой странице) |
| `erc/erc.rpt`, `erc/erc.json` | ERC-отчёт (`kicad-cli sch erc --severity-all`) |
| `netlist.net`, `netlist.xml` | netlist (относительные пути в `<source>`) |
| `BOM-core2.csv` | черновой BOM (внутренние артикулы + draft MPN) |
| `pinmap.csv` | машинно-читаемая карта: signal→GPIO→peripheral→voltage→direction→pull→boot→slot→connector |
| `pinmap.md` | человекочитаемая карта пинов + таблицы всех разъёмов |
| `power-tree.md` | дерево питания: worst-case токи, пуск, power-path, brownout/watchdog, тестпоинты |
| `interfaces.md` | контракты: I2S/аудио, USB composite/HS, C6 (Wi-Fi/BLE), CV, MIDI, шина, PANEL-2, клоки/mute/reset |
| `gen_core2_sch.py` | генератор схемы + ERC + экспорты + BOM (санитайзинг путей) |
| `tools/board_def.py` | единый источник истины: пины, рельсы, разъёмы, экспандеры панели |
| `tools/gen_pinmap.py`, `gen_power.py`, `gen_interfaces.py` | генераторы документов |
| `tools/check_pinmap.py` | проверка ресурсов (дубли, boot, резерв) |
| `tools/check_schematic.py` | сверка netlist ↔ board_def (конфликты соединений) |

## 3. GPIO-бюджет (с ESP32-C6)

| Параметр | Значение |
|---|---|
| Всего GPIO ESP32-P4 | 55 (GPIO0…GPIO54) |
| Занято сигналами | **54** |
| Зарезервировано (GPIO36 boot strap) | **1** |
| Свободно | **0** — 0 % |
| Конфликтов GPIO | **0** (`check_pinmap.py` → PASS) |
| Конфликтов соединений | **0** (`check_schematic.py` → 0 mismatches) |
| Резерв GPIO | **отсутствует**; расширение — I2C MCP23017 ×4 на PANEL-2 (энкодеры, матрица 42 клавиш) и J-DIG-EXP |

Распределение по функциям: LCD RGB565+синхро — 20; SDIO — 6 (+CD); I2S — 5;
I2C0 — 2; SPI2 — 4 (+CS C6); MIDI — 2; C6-хост — 4; UART0 TP — 2; CV/GATE — 2;
LED_DATA — 1; BL_PWM — 1; LCD_DISP — 1; PANEL_IRQ — 1; BOOT — 1; VBUS_DET — 1; USB HS — 0 GPIO
(выделенные pin49/50).
Энкодеры (16: A/B + push = 48 линий) и матрица 42 клавиш (6×7 = 13 линий) **не занимают
GPIO P4** — PANEL-2 ставит **4× MCP23017 (0x20, 0x21, 0x22, 0x23)**, всего 61 линия;
на CORE-2 идут только 3 сигнала I2C0 (SDA/SCL) + INT (open-drain wire-OR, 10k PU R91
на CORE-2). Подтяжки I2C 2.2k — R78/R79 на CORE-2. См. `pinmap.md` §5.

**P4 ↔ ESP32-C6:** GPIO26 = C6_CS, GPIO24 = C6_HS, GPIO25 = C6_DR, GPIO27 = C6_RST;
данные — по общей SPI2 (GPIO6/7/8, CS0 = MCP3208, CS1 = C6). SDIO не используется:
это +6 GPIO, которых нет в бюджете; по ТЗ допустима альтернатива UART+SPI, выбран SPI
(esp-hosted). **USB HS:** выделенные USB_DM (pin49) / USB_DP (pin50), не GPIO;
VBUS-детект — GPIO54 через делитель 100к/100к.

## 4. ERC и проверки

- `kicad-cli sch erc --severity-all` (rev.2): **0 errors, 0 warnings** (`erc/erc.rpt`).
- `python3 tools/check_pinmap.py`: **PASS**, 0 ошибок, 1 warning — «резерв GPIO
  отсутствует (0 %)» — объявлено осознанно.
- `python3 tools/check_schematic.py`: **PASS**, 0 mismatches (все пины слотов и
  разъёмов совпадают с `board_def.py`).
- Абсолютных домашних путей в артефактах нет (генератор санитайзит экспорты);
  `<source>` в netlist — `hardware/core2/CORE-2.kicad_sch`.

## 5. Отклонения и открытые решения (важно для приёмки)

1. **C6 по SPI, а не SDIO** — из-за исчерпанного бюджета GPIO (SDIO +6). Если нужен
   именно SDIO: освободить 6 GPIO = отказаться от 4 бит LCD (перейти на DSI) либо
   от UART0 TP/части LCD; это решение уровня архитектуры, не разводки.
2. **J13 IDC-16 (дека)** — на PANEL-2; CORE-2 имеет парные J12 (FFC-40) и J14 (IDC-26).
   Прямого deck-разъёма на CORE-2 нет (дека подключается к панели).
3. **LCD_DISP** выведен на последний свободный GPIO50 (последний GPIO бюджета).
4. **GPIO36 strapping** переведён с 10k PD на 10k PU: иначе недостижим joint download
   boot (нужно GPIO35=0 + GPIO36=1); теперь прошивка/даунлоад — по USB HS кнопкой BOOT.
5. **+20 V подсветки** формируется на CORE-2 (MT3608 #3), на PANEL-2 — только
   BL_ANODE/BL_CATHODE/BL_PWM; токовый лимит/драйвер — на панели (pre-freeze).
6. **VSYS**: запас относительно worst-case 3 А — 3 % (ниже 25 %). Это не регулятор,
   а путь батарея/BQ24074; ограничение — BMS FET ≥5 А и 1S2P 0.6C. Требует замера
   на P1; при 8 дорожках/высокой яркости LED возможен переход на 2S или второй boost.
7. **MCU-слот** — логический (2×32). Физический модуль/адаптер P4 не выбран; pinout
   адаптера проверить по datasheet платы до трассировки.
8. **BOM**: MPN — черновые (draft), цены/поставщики не выдумывались; плата не заказана.
9. **S3-вариант**: ESP32-S3-WROOM на той же плате не разведён в этой ревизии;
   C6-площадка помечена DNP, но замена MCU-слота на S3 требует отдельного адаптера.

## 6. Что нельзя заказывать до бенчмарка P1

1. Плату и корпус — до подписи `spec/90` и design freeze.
2. Ток/тепло +5 В и WS2812 (74 LED) — замерить; brightness-cap обязателен.
3. LCD: RGB565 (20 GPIO) vs MIPI-DSI — R-18 открыт; 800×480@30–60 fps проверить.
4. SDIO vs SPI для C6 — если SDIO обязателен, нужен пересмотр GPIO/экрана.
5. Тепловой режим MT3608 #2/#3 и −12 В (пульсации) — замер на макете.
6. Выбор физического P4-модуля (32 МБ PSRAM) и его power-up sequence.

## 7. Как перегенерировать и проверить

```bash
cd hardware/core2
/opt/homebrew/bin/python3 gen_core2_sch.py          # схема + ERC + PDF/SVG/netlist + BOM
/opt/homebrew/bin/python3 gen_core2_sch.py --no-export
/opt/homebrew/bin/python3 tools/gen_pinmap.py       # pinmap.csv/md
/opt/homebrew/bin/python3 tools/gen_power.py        # power-tree.md
/opt/homebrew/bin/python3 tools/gen_interfaces.py   # interfaces.md
/opt/homebrew/bin/python3 tools/check_pinmap.py     # PASS (0 errors)
/opt/homebrew/bin/python3 tools/check_schematic.py  # PASS (0 mismatches)
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc --severity-all \
    --format report -o erc/erc.rpt CORE-2.kicad_sch
```

## 8. Лицензии

Аппаратура — CERN-OHL-S-2.0; документация — CC BY-SA 4.0. Часть архитектурных
требований — `spec/90-requirements-registry.md` (R-01…R-24), журнал решений D-01…D-12.
