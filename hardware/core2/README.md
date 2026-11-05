# CORE-2 (rev.1) — исследовательская схема ядра на ESP32-P4

> ## ⛔ PRE-FREEZE / DO NOT FABRICATE
> **Схема не готова к заказу плат.** Нельзя отправлять в производство до:
> 1) бенчмарка P1 (реальные токи/тепло/производительность ESP32-P4 + PSRAM),
> 2) подписи требований `spec/90-requirements-registry.md` (design freeze),
> 3) выбора физического MCU-модуля/адаптера под слот J-MCU.
> Это исследовательская ревизия (rev.1) новой архитектуры, а не релиз.

**MCU:** ESP32-P4NRW32 (ESP32-P4, 55 GPIO, 32 МБ PSRAM в корпусе, QFN104).
**Сопроцессор радио:** ESP32-C6-MINI-1 (Wi-Fi 6 + BLE 5.3), связь с P4 по SPI
(esp-hosted), отдельный LDO +3V3_C6. Для сборки на ESP32-S3 (радио нативно) C6 —
**DNP**, площадка не паяется.

---

## 1. Что в CORE-2

| Блок | Состав |
|---|---|
| **MCU** | слот J-MCU 2×32 (64 pin) — *логический контракт* под модуль/адаптер ESP32-P4; 6×100 nF + 2×10 uF на +3V3_MCU; RESET (RC), BOOT (GPIO35, download boot), UART0 TP (GPIO37/38), VBUS-детект (GPIO54) |
| **USB** | один USB-C 16P: USB 2.0 **HS** (выделенные USB_DM/DP pin49/50), ESD USBLC6-2SC6, CC 5.1 к (UFP), VBUS → polyfuse 1.5 A → BQ24074. TinyUSB composite: HID + MIDI + UAC2 + CDC |
| **Радио** | ESP32-C6-MINI-1 (SPI esp-hosted + handshake/data-ready + reset), keep-out ≥15 мм, внутренняя PCB-антенна; +3V3_C6 отдельный LDO 600 мА; DNP для S3 |
| **SD** | microSD **SDIO 4-bit** (SDMMC slot0, GPIO39…44), CD, pull-up 10 к, 10 uF/100 nF |
| **Питание** | USB-C 5 V → BQ24074 (power-path) → VSYS; BMS BQ297xy + 2× N-MOS для 1S2P; MT3608 ×3: +12 V, +5 V, **+20 V BL**; MP1584 → +3V3_MCU; AP2112K ×2 → +3V3, +3V3_C6; MC34063 → −12 V; ферриты + 3 «земли» (AGND/DGND/PGND) с net-tie |
| **Аудио** | PCM5102A (I2S DAC) + PCM1808 (I2S ADC, 24/96), общие MCLK/BCK/LRCK; TL072 буферы LINE/PHONES; задние джеки LINE OUT L/R, PHONES, AUDIO IN L/R |
| **CV** | 2× MCP4728 (0x60/0x61, LDAC=GND) + 6× TL074 ×4.9 (+1к/BAT54S) → CV OUT 1…6; CV IN 1/2: 100к/16.5к + сдвиг 1.65 В; MCP3208 CH0…7 (CV IN ×2, фейдеры ×2, EXPRESSION, резерв, BATT_MON, TEMP_MON) |
| **MIDI** | TRS-A IN (6N137 + 220R) / OUT (74HCT125 + 33R/220R), 5 В логика |
| **Шина** | 2× IDC-26 аналоговая (R-11/R-22): ±12 В, CV1…4, GATE1/2, AUDIO IN/OUT L/R; на каждый порт polyfuse + SS34 + TVS; отдельный J-DIG-EXP (IDC-16) для TDM/I2S + SPI mailbox + I2C |
| **PANEL-2** | J14 IDC-26 (I2C, фейдеры, CV/GATE, LED_DATA) + J15 FFC-40 (RGB565 800×480: 20 + I2C(2) + INT + BL_PWM + BL_ANODE/CATHODE = 25 сигналов). 10 верхних джеков: CV OUT 1…6 + CV IN 1/2 + GATE 1/2 |
| **Задняя панель** | 5 × 3.5 мм аудиоджеков (LINE L/R, PHONES, AUDIO IN L/R), MIDI TRS in/out, DC 12 V, EXPRESSION, USB-C |

## 2. Файлы

| Файл | Что это |
|---|---|
| `CORE-2.kicad_sch` + `CORE-2.kicad_pro` | схема KiCad 10 (S-expression, 1 лист A0) |
| `picomod.kicad_sym`, `sym-lib-table` | проектная библиотека (ESP32-P4_MOD, ESP32-C6-MINI-1, PCM1808, MP1584_MOD, 74HCT125, 74HCT1G125, TP) |
| `CORE-2.pdf`, `CORE-2.svg` | экспорт схемы (баннер PRE-FREEZE на первой странице) |
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
| Резерв GPIO | **отсутствует**; расширение — I2C MCP23017 ×3 на PANEL-2 (энкодеры, матрица 42 клавиш) и J-DIG-EXP |

Распределение по функциям: LCD RGB565+синхро — 20; SDIO — 6 (+CD); I2S — 5;
I2C0 — 2; SPI2 — 4 (+CS C6); MIDI — 2; C6-хост — 4; UART0 TP — 2; CV/GATE — 2;
LED_DATA — 1; BL_PWM — 1; LCD_DISP — 1; PANEL_IRQ — 1; BOOT — 1; VBUS_DET — 1; USB HS — 0 GPIO
(выделенные pin49/50).
Энкодеры (16) и матрица (6×7) **не занимают GPIO P4** — 3× MCP23017 на PANEL-2
(0x20/0x21/0x22, I2C0), см. `pinmap.md` §5.

**P4 ↔ ESP32-C6:** GPIO26 = C6_CS, GPIO24 = C6_HS, GPIO25 = C6_DR, GPIO27 = C6_RST;
данные — по общей SPI2 (GPIO6/7/8, CS0 = MCP3208, CS1 = C6). SDIO не используется:
это +6 GPIO, которых нет в бюджете; по ТЗ допустима альтернатива UART+SPI, выбран SPI
(esp-hosted). **USB HS:** выделенные USB_DM (pin49) / USB_DP (pin50), не GPIO;
VBUS-детект — GPIO54 через делитель 100к/100к.

## 4. ERC и проверки

- `kicad-cli sch erc --severity-all`: **0 errors, 0 warnings** (`erc/erc.rpt`).
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
