# fab/ — fab-пакеты плат

Здесь появятся пакеты для фабрикации (после MCU freeze, DRC/DFM и gate PWR 13/13):

- `core2/rev1/` — CORE-2 (6 слоёв, USB HS, I2S, микрофон);
- `panel2/rev1/` — PANEL-2 (4 слоя, 380×210, 42 клавиши, 16 энкодеров);
- `power2/rev1/` — PWR-2 (4 слоя, 2 oz, TPS61088/BMS).

Состав и чек-лист — [docs/83-fab-package.md](../docs/83-fab-package.md); проверка —
`python3 tools/check_fab_package.py fab/core2/rev1`. Сейчас пакетов нет — PRE-FREEZE.
