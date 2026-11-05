# Структура репозитория (текущая версия)

Правило: **текущая версия — только в рабочих папках; всё старое — в `archive/<version>/`.**
При релизе: обновить версию → перенести устаревшее (`tools/archive_versions.sh`) → обновить
этот файл и `archive/README.md` → тег.

```
spec/                       требования и текущая геометрия
  panel-spec-v0.4.json      ← единственный канон раскладки (380×210)
  90-requirements-registry.md
  00-vision.md … 60-v1.2.md (исторические спеки; актуальное — реестр)
docs/                       документация и отчёты (00…42)
  36-rc-definition.md, 37-compliance.md, 38-dfm-testability.md, 40-kit-contents.md, 42-dfm-review-gpt.md
hardware/                   KiCad, pre-freeze
  core2/                    CORE-2 (ESP32-P4 + C6, rev.2)
  cores3/                   CORE-S3 (lite later)
  panel2/                   PANEL-2 rev.2
  power2/                   PWR-2 rev.1
  modules/                  аналоговые модули (шина 26-pin)
  core/, panel/, power/     v1.0 (историческое, не менять)
firmware/                   прошивка
  src/, app/, include/      движок, HAL, UI, SDK
  spike_s3/                 devkit-spike (lite-концепт, переносится на P4)
  bench/                    P1-бенчмарк (host, p4_profile, s3_profile)
  tests/                    160+ тестов, REPORT.md
  artifacts/ui/             скриншоты 4 режимов + экраны
mechanical/                 текущий корпус и печать
  stl_v05_B/, stl_v05_B_light/
  preview_v05_B/, preview_v05_B_light/, preview_v05_compare/
  generator/                параметрические генераторы, paperkit, assembly map
  prints.md, assembly.md, fit_check.md
renders/                    текущие шаблоны и превью
  templates/                панель 1:1, профиль 8°, paperkit, assembly map, референсы (Lapka/Digitone/Octatrack)
archive/                    замороженные версии (v1.0, v0.3, v0.4, v1.4…v1.8)
music/ modules/ tools/ refs/ site-files в docs/
BOM-p4.csv, BOM-s3.csv, BOM.csv (мастерский), CHANGELOG.md, VERSION
```

## Что где искать

| Нужно | Файл |
|---|---|
| Раскладка панели и координаты | `spec/panel-spec-v0.4.json`, `renders/templates/bukifon_v04_panel_1to1.pdf` |
| Корпус v0.5-B / B-light | `mechanical/stl_v05_B/`, `mechanical/stl_v05_B_light/` |
| Профиль и бумажный макет | `renders/templates/bukifon_v05_wedge8_profile_1to1.pdf`, `bukifon_paperkit_1to1.pdf` |
| Сборочная карта | `renders/templates/bukifon_assembly_map_1to1.pdf`, `docs/34-assembly.md` |
| Product BOM | `BOM-p4.csv` (P4 Standard), `BOM-s3.csv` (S3 lite), `docs/33-bom-s3.md`, `docs/40-kit-contents.md` |
| Платы | `hardware/core2/`, `hardware/panel2/`, `hardware/power2/`, DFM в `*/dfm.md` |
| Прошивка | `firmware/src/`, `firmware/spike_s3/`, `firmware/bench/` |
| RC DoD / compliance | `docs/36-rc-definition.md`, `docs/37-compliance.md` |
| DFM/DFT | `docs/38-dfm-testability.md`, `docs/42-dfm-review-gpt.md` |
| Старые версии | `archive/README.md` |
