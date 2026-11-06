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
