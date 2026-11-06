# PWR-2 rev.1 — PCB scaffold (PRE-FREEZE)

> **Не заказывать PCB.** Каркас 90×70 мм из `mechanical/board-fit/`: контур, 4×M2.5,
> keepout-зоны, 4 слоя **2 oz**. Нет посадочных мест/связей/меди.

## Файлы

| Файл | Что |
|---|---|
| `PWR-2-rev1.kicad_pcb` | плата 90×70, 4×M2.5 (Ø2.8, H1–H4), keepout `battery-conn` и `hot-loop`, стек 4 слоя 1.6 мм, медь 2 oz |
| `PWR-2-rev1.svg/.pdf` | контур + шелкография |
| `PWR-2-rev1.drc.rpt` | DRC: **0 нарушений, 0 unconnected** |
| `../core2/rev1/gen_scaffold.py`, `verify_scaffold.py` | генератор/сверка (±0.05 мм) — PASS |

## Параметры

- Контур: 90×70 мм (origin world 145;65), площадь 6 300 мм².
- Крепёж: 4×M2.5 Ø2.8 (NPTH, стойка Ø6).
- Стек: 4 меди (F.Cu/In1/In2/B.Cu), 1.6 мм, **2 oz** (0.07 мм) — силовые 3 А.
- Keepout: `battery-conn` (разъём/предохранитель/шунт у края), `hot-loop` (TPS61088 + индуктивность, тепловой).

## Проверки

- DRC: 0 errors/warnings/unconnected.
- Сверка ±0.05: контур, 4 отверстия, 2 keepout, 4 Cu (2 oz), 1.6 мм — PASS.

## Что дальше

1. Импорт netlist/посадочных мест PWR-2 rev.1 (TPS61088, LMR33630, BQ24074 EVM? — после стенда docs/44).
2. Силовые полигоны 3 А, тепловые vias, J3 (IDC-20 vs Micro-Fit, O-11), звезда PGND.
3. DFM `hardware/power2/dfm.md` + PWR 13/13 (docs/51), затем заказ.

## Нетлист и посадочные места — первый импорт (2026-11-06)

- Источник: `hardware/power2/netlist.xml` + `BOM-power2.csv`.
- **Refs: 128/128**; 4 NPTH-крепления M2.5 — из каркаса.
- **Footprints: 128**; pads **328**; **Placeholder: 0** (все footprint'ы есть в BOM/стандартных
  библиотеках; силовые — проверить thermal pad/2 oz).
- **DRC: 0 errors / 0 warnings; unconnected = 263** — допустимо.
- Зоны: силовая зона (hot-loop/battery-conn) — при ручной разводке; сетка — черновая.
- Перегенерация: `python hardware/core2/rev1/gen_scaffold.py && python hardware/core2/rev1/import_netlist.py`.
- Дальше: трассировка 3 А/тепловые полигоны после PWR 13/13; J3 (IDC vs Micro-Fit).
