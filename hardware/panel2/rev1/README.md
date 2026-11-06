# PANEL-2 rev.1

## Раскладка клавиш (исправлено 06.11.2025)

Клавиши размещены **по spec/panel-spec-v0.4.json** (точная геометрия Lapka-42,
upstream `braindefender/lapka-42`): левая плата — `KEY_L01…L21`, правая — `KEY_R01…R21`,
координаты/углы из `controls.keyboard_left/right`. Ранее refs делились по номеру без L/R —
клавиши накладывались; исправлено, DRC 0/0. Превью — `docs/assets/panel-lapka-*.png`. — PCB scaffolds left/right (PRE-FREEZE)

> **Не заказывать PCB.** Каркасы двух плат 180×190 из `mechanical/board-fit/`: контур с
> вырезами джеков, крепёж, keepout-зоны, стек 4 слоя. Нет посадочных мест/связей/меди.

## Файлы

| Файл | Что |
|---|---|
| `PANEL-2-left-rev1.kicad_pcb` | левая плата 180×190, 3×M3 (H1–H3), 5 вырезов J01–J05, keepout экрана/энкодеров/клавиш/фейдера/MIC_LED |
| `PANEL-2-right-rev1.kicad_pcb` | правая плата 180×190, 3×M3, 5 вырезов J06–J10, keepout + батарея |
| `*.svg/.pdf` | контур + шелкография |
| `*.drc.rpt` | DRC: **0 нарушений, 0 unconnected** на каждой |
| `../core2/rev1/gen_scaffold.py` | общий генератор (запускать из корня: `python hardware/core2/rev1/gen_scaffold.py`) |
| `../core2/rev1/verify_scaffold.py` | сверка с board-spec ±0.05 мм — **PASS** |

## Параметры

- Контуры: 180×190 мм каждая (левая origin 10;10, правая 190;10), площадь 34 200 мм².
- Крепёж: 3×M3 Ø3.4 (NPTH) на каждой.
- Вырезы джеков: Ø8.2 по задней кромке (J01–J05 / J06–J10), дуги точно по радиусу 4.1 мм из board-spec.
- Стек: 4 меди (F.Cu / In1 / In2 / B.Cu), 1.6 мм, 1 oz.
- Keepout: экран (без меди/высоких), 8 энкодеров Ø16, 21 клавиша, фейдер, MIC_LED,
  батарея (правая), джеки Ø10.
- PANEL-2 — **две платы** по шву X=190 (механический разрез панели 193+190 — 3 мм шип панели, не платы).

## Проверки

- DRC: 0 errors/warnings/unconnected на обеих.
- Сверка ±0.05: контуры, по 3 отверстия, 5 вырезов (радиус 4.1), 37 keepout-зон, 4 Cu, 1.6 мм — PASS.

## Что дальше

1. Импорт netlist/посадочных мест PANEL-2 rev.2 (экраны/клавиши/энкодеры/джеки/MCP23017).
2. FPC-40/IDC pinout и направление выхода (docs/82 §...); зоны MEMS ≥10 мм от LED/BL.
3. Крепёж: по board-fit **3×M3 на каждую плату (6 всего на панель)**; панель крепится к корпусу.
4. DFM `hardware/panel2/dfm.md`, затем заказ.

## Нетлист и посадочные места — первый импорт (2026-11-06)

- Источник: `hardware/panel2/PANEL-2.net` (PANEL-2 rev.2/3) + `BOM-panel2.csv`.
- Разбивка left/right по зонам board-fit: ENC1–8/KEY1–21/J01–J05/F1 — левая;
  ENC9–16/KEY22–42/J06–J10/F2 — правая; остальные refs — поровну.
- **Refs: left 181, right 174 (итого 355 + 6 H-креплений = 361)**.
- **Footprints: left 181 + 4 крепления, right 174 + 3 крепления**; pads left 585 / right 443.
- **Placeholder: 21 на каждой плате** — клавиши Choc (`KEY_L01…L21`, `KEY_R01…R21`);
  остальные (R/C/D/энкодеры/джеки) получили footprints из BOM (энкодеры/джеки — bare-имена
  кастомных библиотек, проверить при разводке).
- Зоны: энкодеры/клавиши/фельдеры/джеки — по центрам keepout/вырезов board-fit; остальное — сетка.
- **DRC: 0 errors / 0 warnings; unconnected: left 368 / right 265** — допустимо.
- Перегенерация: `python hardware/core2/rev1/gen_scaffold.py && python hardware/core2/rev1/import_netlist.py`.
- Дальше: реальные футпринты Choc/EC11/джеков/FPC-40/IDC, затем трассировка после MCU freeze.

## Реальные футпринты и DRC-правила (2026-11-06)

- **Placeholder'ы: 0** — 42 клавиши Choc заменены на custom `CHOC_V1` (18×18, 2 пада + NPTH
  центра 3.4/боковой 1.7, hot-swap) из `footprints/` (+`fp-lib-table`), вставлены pcbnew API.
- Остальные refs — footprint-имена из BOM (KiCad); в каркасе упрощённые пады (полные
  `.kicad_mod` — при разводке). Footprints left 181/right 174 (+крепёж), pads 630/488,
  refs 181/181 и 174/174; **DRC 0/0**, unconnected 367/264.
- **DRC-правила** (`.kicad_pro` left/right): классы Default/Power/USB_HS/Audio/RF, дорожки
  0.2–1.0 мм, via 0.6/0.3 и 0.8/0.45, diff pair 0.2/0.2; для каркаса silk/courtyard —
  `rule_severities` ignore.
- **GND-полигоны (план):** GND-заливка на F.Cu/B.Cu; аналоговое поле J14 — AGND-полигон,
  звезда; LED-цепочка — отдельный возврат к J13; экран/клавиши — без меди под FPC.

## Двусторонняя попытка (2026-11-06)

`rev1/two-sided/` — копии с реальными футпринтами на top+bottom и GND-зонами
(`build_two_sided.py`). DRC **FAIL** (упаковка courtyard/зазоры, zones_intersect) — в основную
версию **не промоутнуто**; main остаётся DRC 0/0 (328 упрощённых падов). Нужен floorplanner
после MCU freeze. Детали — docs/82 §13.
