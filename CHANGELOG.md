# Changelog

Формат: [SemVer](https://semver.org/lang/ru/). Даты — локальные (Europe/Moscow).

## [0.7.0] — 2025-11-06 — «PWR-2 + бенчмарк + SDK»

### Добавлено
- **PWR-2 rev.1** (PRE-FREEZE): батарея 1S2P + BMS BQ297, MAX17048 (I²C) + резервный ADC,
  **+12 В 330 мА** (TPS61088 sync boost + π), **−12 В 95 мА** (LMR33630 inverting buck-boost),
  +5 В 1.6 А, +5V_LED, master load-switch, EN рельсов; питание только от BQ24074 OUT/VSYS,
  NTC→TS, fuse 5 А; ERC **0/0**; power-tree и м��жплатные интерфейсы; решения D-27…D-36.
- **P1-бенчмарк**: workload freeze `docs/05`, howto `docs/05a`, харнесс `firmware/bench`
  (fm_voice, granular_track, mix_bus, psram_stream, ui_frame(+partial), usb_descriptor),
  max/p50/p95/p99, детерминизм, JSON/CSV; host PASS (worst 218 µs = 16.4 % дедлайна,
  запас 431 µs до 650 µs); `bench_s3` сборка; envs P4/H743 подготовлены.
- **SDK модулей**: `docs/24-module-sdk.md`, каталог `modules/` (template, gain_fx C++,
  lfo_module Lua — компилируются), `tools/validate_module.py`, `tools/new_module.sh`,
  CI `.github/workflows/modules.yml`.
- **Архитектура питания** `docs/25` по консультации GPT: бюджет ±12 В, отказ от MC34063,
  BQ24074 OUT/VSYS, MAX17048, земля/тепло, 13 обязательных измерений до PCB.

### Изменено
- Прошивка: 120/120 тестов (было 112), bench-раздел в REPORT.md.
- Сайт: разделы «Бенчмарк (P1)» и «Модули и SDK»; бейдж v0.7.0.

### Открытые конфликты (зафиксированы в spec/90)
- +5 В бюджет CORE-2 занижен (1.0 → 1.6 А: пропущен вход MP1584→+3V3_MCU);
- VSYS 3 А vs пик 2.74–3.38 А — нужен прошивочный cap LED или 2S во rev.2;
- CORE-2 rev.2 требует DNP MT3608#2/MC34063/BMS; 4 EN-линии брать с MCP23017;
- J3 при 3 А — проверить IDC vs Micro-Fit; 1S2P vs 2S решить после замеров.

## [0.6.2] — 2025-11-06 — «VERSION и публикация»

### Исправлено
- `VERSION` = 0.6.2: в v0.6.1 файл остался 0.6.0 (перезапись при публикации сайта).
- `tools/publish_site.sh` больше не делает `git reset --hard` в рабочем дереве — использует
  временный индекс (`GIT_INDEX_FILE`), не теряет незакоммиченные изменения.
- README/CHANGELOG приведены в соответствие; бейдж сайта — v0.6.2.

## [0.6.1] — 2025-11-06 — «Синхронизация плат»

### Исправлено
- CORE-2: PANEL-2 согласован на **4× MCP23017 (0x20–0x23)** — 48 линий энкодеров + 13 матрицы,
  наружу SDA/SCL/INT; в схему добавлена подтяжка **R91 10k PANEL_IRQ→+3V3** (wire-OR INT),
  BOM-core2 — 201 группа; ERC 0/0, pinmap PASS.
- Документация CORE-2 (README/pinmap/power-tree/interfaces) и генераторы синхронизированы.

## [0.6.0] — 2025-11-06 — «Ночная сборка v1.0-rc»

### Добавлено
- **Корпус v0.5-B «клин 8°»**: 380 × 210 × 61.5 мм (перед 32 / зад 61.5), 6 STL watertight,
  печать без поддержек 279 г / 18.3 ч, fitcheck 32/0; профиль 1:1 для картонной проверки;
  сравнение A/B/C (плоский/8°/12°).
- **CORE-2 rev.1** (PRE-FREEZE): ESP32-P4 + ESP32-C6 (Wi-Fi 6/BLE 5.3 по SPI), USB HS composite
  (HID+MIDI+UAC2+CDC), PCM5102A/PCM1808, CV (MCP4728/MCP3208), MIDI TRS, шина модулей, BQ24074;
  ERC 0/0, pinmap PASS (54/55 GPIO), PII вычищен.
- **PANEL-2 rev.1** (PRE-FREEZE): 16 энкодеров + 42 клавиши через 4× MCP23017, LCD FPC-40,
  10 джеков CV/GATE, 2 фейдера, BL_PWM; ERC 0 errors, 1288 проверок, 3 шлейфа.
- **Прошивка v0.5**: host-демо 800×480, секвенсор 4×16, BPM/mute/p-lock, save/load CRC16,
  Module API v0 (2 примера), режимы Synth/Sampler/DAW/USB-keyboard, каркасы USB composite
  и BLE/Wi-Fi; **112/112 тестов**, покрытие 83.5 %; сборки S3 и RP2040.
- **«Народный синтезатор»**: позиционирование, целевые цены ($200/$300/$400), cost-down план
  (spec/00 §13), README и сайт.
- **Клавиатура/DAW + Wi-Fi/BT** как обязательные требования (R-25…R-28, spec/00 §14).
- docs/20 (разведка аналогов), docs/21 (эргономика), docs/22 (ночной план), docs/23 (отчёт).
- **Безопасность**: SECURITY.md, tools/security_scan.sh, tools/sanitize_paths.sh; из истории
  удалены GPS EXIF-фото, PDF с IP и абсолютные пути; .gitignore для секретов/сборок.

### Изменено
- Корпус: v0.4 (плоский) → v0.5-B (клин 8°) как базовый для v1.0-rc.
- BOM: 92 позиции (draft), база ≈ 21 657 ₽ (~$271), полный ≈ 32 518 ₽ (~$406).
- Сайт обновлён до v0.6.0 (host-демо, корпус, статус).

## [0.5.1] — 2025-11-05 — «Сайт опубликован»

### Исправлено / добавлено
- GitHub Pages включён автоматически при пуше ветки `gh-pages`: сайт живой
  (https://martiyanov.github.io/bukifon/ и /en/), все страницы и SEO-файлы отдают 200.
- Добавлен скрипт `tools/publish_site.sh` — пересборка `gh-pages` из `docs/` одной командой.
- `docs/github-metadata.md` обновлён под фактическую схему публикации (ветка `gh-pages`;
  Actions-вариант — опционально).

## [0.5.0] — 2025-11-05 — «Сайт проекта RU/EN»

### Добавлено
- **GitHub Pages** сайт: `docs/index.html` (RU) и `docs/en/index.html` (EN) — описание проекта,
  режимы, железо, статус, ссылки на документы и файлы; `docs/assets/` с оптимизированными изображениями.
- SEO/индексация: `docs/sitemap.xml` (RU+EN, hreflang), `docs/robots.txt` (разрешены поисковые и
  AI-краулеры), `docs/llms.txt`, JSON-LD `SoftwareApplication`, Open Graph/Twitter Card,
  `docs/.nojekyll`.
- Деплой: `.github/workflows/pages.yml` (GitHub Actions → Pages).
- `CITATION.cff` для цитирования; `docs/github-metadata.md` — описание/темы репозитория и
  включение Pages одной командой.
- README: раздел «Сайт проекта», версия 0.5.0.

## [0.4.0] — 2025-11-05 — «Канон v0.4»

### Добавлено
- **Каноническая панель v0.4** (`spec/panel-spec-v0.4.json`): 380 × 210 × 3 мм,
  42 клавиши — точная геометрия Lapka-42 (21 на половину, половины ±18°),
  16 энкодеров Ø14, 10 mini-jack, экран 5.0″ 800×480 (вырез 108 × 64.8, без рамки),
  2 фейдера 60 мм. Проверка пересечений — 0.
- Печать 1:1: `renders/templates/bukifon_v04_panel_1to1.pdf` (2 × A4 с перекрытием),
  рендер `bukifon_v04_render.png`, сравнение `bukifon_v04_vs_concept.png`.
- **3D-корпус v0.4** (`mechanical/stl_v04/`): 6 деталей, 380 × 210 × 63 мм, watertight,
  83 выреза, fitcheck — 0 конфликтов, печать без поддержек.
- Принят машиночитаемый пакет заказчика v0.3 (`refs/handoff_v03/`, `spec/panel-spec-v0.3.json`).
- Документы: `docs/10-elektron-hardware.md` (что внутри Elektron),
  `docs/11-esp32-feasibility.md` (ESP32-P4/S3/H743), `docs/03-second-opinion-mcu.md`,
  `docs/04-consultation-gpt.md` (GPT/Codex), `docs/12-roadmap.md`,
  `spec/90-requirements-registry.md` (реестр R-01…R-19, решения D-01…D-07).
- Позиционирование: сэмплер (Digitakt-класс) + синтезатор (Syntakt-класс) +
  открытые модули сообщества (`spec/00-vision.md §12`, `README.md`).
- `PULL_REQUEST.md` — описание MR v0.4.

### Изменено
- Наклон клавиатур: вместо трассировки по фото (±22°) принят ±18° с точной
  геометрией Lapka-42 — иначе две половины + 5″ экран не влезают в 210 мм высоты.
- Порядок разработки: сначала бенчмарк и cut-list, только потом платы (по ревью).

### Исправлено
- Убраны расхождения «315×145 / 8 ручек / 2.8″» из новых документов (старые спеки
  помечены к правке в `spec/90`).

## [0.3.0] — 2025-11-05 — «380 × 210 по концепту»
- Раскладка v1.7/v1.8: 380 × 210, 42 клавиши, 16 ручек, 10 джеков, 2 фейдера.
- Первая 3D-модель корпуса v1.7/v1.8 (380 × 210 × 63) и рендеры.
- Документ передачи контекста `docs/00-context-transfer.md`.

## [0.2.0] — 2025-11-05 — «Печатные листы и 340 × 185»
- Листы 1:1 Digitone II и Octatrack MKII, шаблон Lapka-42 (левая/правая половины).
- Варианты панели 340 × 185 (v1.4.1, ±5°), 380 × 210 (v1.5, ±20°).

## [0.1.0] — 2025-11-05 — «Базовый прототип»
- Корпус 315 × 145 × 48, 20 STL, схемы CORE-1/PANEL-1/деки/модули/PWR (ERC 0),
  прошивка RP2040 (host-тесты 67/67, UF2), BOM, документация.
