# Fab-пакет: что отдаём фабрике/сборщику

Единый состав файлов для заказа PCB/PCBA. Пакет собирается **только** после MCU freeze
и DRC/DFM-ревью; проверяется `tools/check_fab_package.py`.

## 1. Состав пакета

```
fab/
  <board>/revX/
    gerbers/*.gbr            # X2, слои: F.Cu, In1..InN, B.Cu, F.Mask, B.Mask, F.Silk, B.Silk, Edge.Cuts
    drill/*.drl              # Excellon (PTH/NPTH)
    netlist.ipc356            # IPC-D-356 (опционально, для теста)
    bom.csv                   # ref,qty,mpn,value,package,dnp,note
    cpl.csv                   # ref,val,package,x_mm,y_mm,rot,side
    stackup.md                # стек, медь, толщина,импеданс
    fab-drawing.pdf           # контур, крепёж, допуски, покрытие
    assembly-drawing.pdf      # стороны, полярность, DNP
    README.md                 # версия, дата, кто/куда, особые требования
  MANIFEST.md                 # состав, контрольные суммы
```

## 2. Правила именования

- имя платы: `core2`, `panel2`, `power2`, `cores3`;
- ревизия: `rev1` (первая фабрикация), `rev1a` (фикс без смены схемы);
- Gerber: `<board>-<rev>-<layer>.gbr`; drill: `<board>-<rev>-pth.drl`/`npth.drl`.

## 3. Обязательные поля CPL

`ref,val,package,x_mm,y_mm,rot,side` — координаты **от левого нижнего угла платы**, мм,
поворот в градусах (KiCad convention); `side` = `top|bottom`. DNP — не включать в CPL,
но включать в BOM с `dnp=1`.

## 4. BOM для PCBA

`ref,qty,mpn,value,package,dnp,note` — каждая позиция; альтернативы и допуски; давальческие
помечать `consigned=1`. Сверка: **каждый ref из CPL есть в BOM** и наоборот (без DNP).

## 5. Чек-лист перед отправкой

- [ ] Gerber X2, все слои, Edge.Cuts замкнут; DRC 0; DFM 0;
- [ ] drill PTH/NPTH, металлизация; tooling holes/fiducials;
- [ ] stackup+импеданс (USB 90 Ω) подтверждены фабрикой;
- [ ] CPL/BOM сверены (`tools/check_fab_package.py`), DNP отмечены;
- [ ] test points/pogo (TP1–TP32/TP36–39) в шёлке;
- [ ] assembly drawing с полярностью/разъёмами; fab notes (покрытие, цвет, толщина);
- [ ] серийники/QR (docs/55) — поле/наклейка;
- [ ] NDA/договор, приёмка (AOI-отчёт, фото, тест-лог);
- [ ] `fab/README.md` с версией и контактом.

## 6. Приёмка (что требовать)

- AOI-отчёт + фото каждой платы; X-ray для QFN/BGA по запросу;
- тест-лог (pogo/self-test 21) или образец;
- упаковка ESD; маркировка партии/даты;
- брак: замена/переделка по договору (docs/72).

## 7. Хранение

`fab/` — в git (лёгкие файлы: PDF/CSV/MD; Gerber — zip в `dist/fab/<version>/`), версии тегами;
герберы не перезаписывать — новая ревизия = новая папка.
