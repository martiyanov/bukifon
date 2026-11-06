# CORE-2 rev.1 — PCB scaffold (PRE-FREEZE)

> **Не заказывать PCB.** Это каркас разводки из `mechanical/board-fit/`: контур, крепёж,
> keepout-зоны и стек. Нет посадочных мест компонентов (кроме крепежа), нет netlist/связей,
> нет меди/трасс. Следующий шаг — импорт схемы CORE-2 rev.3 (netlist) и посадочных мест.

## Что есть

| Файл | Что |
|---|---|
| `CORE-2-rev1.kicad_pcb` | плата: Edge.Cuts 200×108 мм, 4×M3 (Ø3.4, H1–H4), keepout-зоны, стек 6 слоёв 1.6 мм |
| `CORE-2-rev1.svg/.pdf` | контур + шелкография (для проверки/обсуждения) |
| `CORE-2-rev1.drc.rpt` | `kicad-cli pcb drc --severity-all`: **0 нарушений, 0 unconnected** |
| `gen_scaffold.py` | генератор из `mechanical/board-fit/board-spec.json` (общий для CORE/PANEL/PWR) |
| `verify_scaffold.py` | сверка координат с board-spec, допуск **±0.05 мм** — **PASS** |

## Параметры

- Контур: прямоугольник 200×108 мм (origin world 90;51), площадь 21 600 мм².
- Крепёж: 4×M3 Ø3.4 (NPTH, стойка Ø7) — H1 (5;8), H2 (195;8), H3 (5;100), H4 (195;100) в локальных мм.
- Стек: 6 меди (F.Cu / In1–In4 / B.Cu), FR4, 1.6 мм; толщина меди 0.035 мм (1 oz), диэлектрик распределён.
- Keepout (только медь/трассы/via, NPTH-пады разрешены): `C6-antenna` 40×20 + правило ≥15 мм,
  `analog` (DAC/ADC, звезда GND), `DC-DC` (тепловой/горячий контур).
  `USB-C` keepout из board-spec лежит вне контура платы (окно в задней стенке корпуса) — в плату не переносится.

## Проверки

- **DRC**: 0 errors / 0 warnings / 0 unconnected (`CORE-2-rev1.drc.rpt`).
- **Сверка с board-spec**: PASS (±0.05 мм): контур, 4 отверстия, толщина 1.6, 6 Cu, keepout-зоны.
- Импорт DXF (`mechanical/board-fit/core2.dxf`) в KiCad: File→Import→DXF→Edge.Cuts —
  альтернатива; текстовые сегменты сгенерированы точно по `board-spec.json` (DXF-круги
  крепежа заменены NPTH-падами, как требует DFM).

## Что дальше

1. Импорт netlist CORE-2 rev.3 (`hardware/core2/CORE-2.kicad_sch` → Update PCB) после снятия PRE-FREEZE.
2. Посадочные места (модуль P4, C6, FPC-40, IDC, аудио/джеки, TP-пады) + правила DRC.
3. Медная заливка/GND-полигоны, стек-ап импедансов (USB HS 90 Ω), keepout-механика (антенна vs H1).
4. DFM-ревью `hardware/core2/dfm.md` + `docs/38`, затем заказ прототипов 3–5 шт.

## Нетлист и посадочные места — первый импорт (2026-11-06)

- Источник: `hardware/core2/netlist.xml` (CORE-2 rev.3) + `BOM-core2.csv` (footprint по позициям).
- **Refs: 373/373** на плате; 4 NPTH-крепления (H1–H4) — из каркаса.
- **Footprints: 373** (имена из BOM; в PCB — bare-имена и упрощённые пады 0.5×0.8/шаг 1.0 с
  корректными номерами/числом; реальные `.kicad_mod` подтянуть при разводке). Pads: **1224**.
- **Placeholder: 16** — требуют реальных футпринтов до трассировки:
  `A1` (P4-модуль/адаптер), `U31` (C6-MINI-1), `U22` (BQ24074), `U26` (MP1584),
  `J6/J7/J8/J9/J10` (TRS/3.5 джеки), `J11` (audio jack), `J12` (DC jack), `J13` (mic TRS),
  `J20` (mic TRS), `SW1/SW2/SW3` (кнопки/тумблер).
- Зоны: `J1` USB-C у задней кромки, `U31` C6 — рядом с антенной (вне keepout), `A1` — центр;
  остальное — сетка по секциям (DC-DC/аналог — при ручной разводке).
- **DRC: 0 errors / 0 warnings; unconnected (неразведённые) = 499** — допустимо на этом этапе.
- Перегенерация: `python gen_scaffold.py && python import_netlist.py && python verify_import.py`
  (из корня репозитория пути уже учтены; скрипты лежат в `hardware/core2/rev1/`).
- Дальше: заменить 16 placeholder на реальные посадочные места, затем трассировка — после MCU freeze.

## Реальные футпринты и DRC-правила (2026-11-06)

- **Placeholder'ы заменены полностью (0):** A1 — custom `A1_P4_MODULE_ADAPTER` (2×32, шаг 2.54,
  габарит адаптера 90×28), U31 — custom `C6_MINI_1` (13.2×16.6), U26 — custom `MP1584_MODULE`
  (4 пада), U22 — `Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.75x1.75mm`, J6–J11/J13/J20 —
  `Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal`, J12 — `Connector_BarrelJack:BarrelJack_CUI_PJ-063AH_Horizontal`,
  SW1–SW3 — `Button_Switch_THT:SW_PUSH_6mm`. Кастомные `.kicad_mod` — в `footprints/`
  (+`fp-lib-table`), вставлены через **pcbnew Python API** (реальная геометрия, пады с net).
- **Стандартные пассивные/IC**: footprint-имена из BOM (KiCad-библиотеки); в каркасе пады
  упрощённые (0.5×0.8/шаг 1.0) — полные `.kicad_mod` подтягиваются при разводке
  (`import_netlist.py`: generic-пады; `add_real_footprints.py`: реальные для заменённых).
- **Footprints: 373** (+4 NPTH), pads **1259**; refs 373/373; **DRC 0 errors / 0 warnings**,
  unconnected 499 (неразведённые).
- **DRC-правила/классы** (`CORE-2-rev1.kicad_pro`): `Default`, `Power` (+12/−12/5/3.3/VSYS…,
  ширина 1.0 мм), `USB_HS` (90 Ω: diff 0.2/0.2, clearance 0.15), `Audio` (0.25 мм),
  `RF` (C6 SPI); track widths 0.2–2.0, via 0.6/0.3 и 0.8/0.45, diff pair 0.2/0.2;
  правила-исключения для каркаса (silk/courtyard) — в `rule_severities`.
- **GND-полигоны (план, без заливки):** F.Cu/B.Cu GND-заливка после трассировки; аналоговая
  зона (DAC/ADC) — отдельный AGND-полигон, звезда в NT1/NT2; PGND — силовая зона, соединение
  в одной точке у J17; под антенной C6 — запрет меди (keepout 40×20 + ≥15 мм). Заливку делать
  только после MCU freeze/трассировки.
