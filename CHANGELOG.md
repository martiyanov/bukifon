# Changelog

Формат: [SemVer](https://semver.org/lang/ru/). Даты — локальные (Europe/Moscow).

## [0.10.0] — 2025-11-06 — «RC-контур»

### Добавлено
- **Product BOM S3-base** `BOM-s3.csv` + `docs/33`: 68 позиций (61 kit + 7 опций),
  COGS **$189 / $166 / $149** на 1/10/25 шт; $199 — founders beta, S3 Complete $249–269,
  P4 $299, full $399; опции (аккум-пак 1S2P+NTC, БП, SD, картриджи, DECK-PAD) вне kit.
- **Сборочный комплект**: `renders/templates/bukifon_assembly_map_1to1.pdf` (4 стр: слои,
  панель 1:1, крепёж и шлейфы), `docs/34-assembly.md` (пошагово, моменты затяжки, чек-лист),
  `docs/35-print-first.md` (body_L 70 г/3.4 ч → приёмка → комплект), 3D exploded.
- **Прошивка v0.6**: S3 HAL `board_cores3` по pinmap, env `s3base` — сборка **SUCCESS**
  (flash 11.3 %, RAM 62.7 %); UI 4 режимов (synth/sampler/daw/usb_kbd); P1 S3-профиль
  в bench (`host_s3.json` PASS: max block 192 µs; SPI full 13 fps < 15 — риск D-51,
  partial 32.5/с, RGB-модель 52 fps); **Module API v0.1** (12 колбэков, host services,
  события, smoothing; 2 новых примера); **146/146 тестов**.
- **RC Definition of Done** `docs/36` (8 критериев приёмки, S3-ветка 10–14 недель)
  и **compliance** `docs/37` (RED/GPSR, батарея, EMC, SBOM, гарантия, метрики).
- Решения D-53…D-57; открытые O-17…O-19 (TL074 qty, TPS63802, display MPN).

### Изменено
- README/сайт: SKU-линейка (beta/complete/P4/full), 4 режима UI, ссылки на docs/33–37.

## [0.9.1] — 2025-11-06 — «Сводный отчёт»

### Добавлено
- `docs/32-progress-report.md` — карта проекта от v0.4 до v0.9.1: вехи, что готово,
  блокеры, следующий шаг P1, единственные источники истины.
- README/сайт: ссылка на сводный отчёт, версия 0.9.1.

## [0.9.0] — 2025-11-06 — «CORE-S3 и лёгкий корпус»

### Добавлено
- **CORE-S3 rev.0** (`hardware/cores3/`): ESP32-S3-WROOM-1-N16R8, USB FS
  (HID+MIDI+CDC+стерео UAC2), 1-bit SDMMC, **SPI-дисплей 800×480**, TPS63000 placeholder
  (цель TPS63802), канон PANEL-2/PWR-2; **ERC 0/0**, 27/31 GPIO занято, PRE-FREEZE;
  сравнение CORE-2 vs CORE-S3, endpoint-бюджет USB, devkit-план 2–3 дня.
- **Корпус v0.5-B-light**: **230 г / 11.1 ч** вместо 277 г / 18.3 ч (−17 % массы,
  −39 % времени) при сохранении жёсткости: стенки 2.0/дно 1.8, 3 периметра + локальные
  рёбра, панели-оболочки; 6 STL watertight, fitcheck 32/0.
- **P1: точный список заказа** `docs/29` (P4 EV, NUCLEO-H743ZI2, S3-N16R8, PCM5102A/1808,
  дисплей, SD, БП/нагрузка; бюджет $110–320) и **запрос на purge** `docs/30` с SHA
  старых PII-объектов для GitHub Support.
- **CORE-S3 ограничения** `docs/31`: почему RGB565 не влезает на N16R8 (31 линия),
  USB endpoint ceiling, один framebuffer + dirty rects, профиль S3-base в бенчмарке.
- Решения D-46…D-52; O-12 (DISP) — в D-51/D-52.

### Изменено
- Профиль бенчмарка: S3 — полноценный третий профиль (4 МиБ pool + FB, 1-bit SD,
  ≥15 fps full / ≥30 partial), а не «reference only» (D-46).

## [0.8.1] — 2025-11-06 — «Rev.2 плат»

### Добавлено
- **CORE-2 rev.2** — схема внесена: J17 IDC-20/J18 IDC-12 к PWR-2, входы `12V_EXT`/`N12_EXT`/`+5V_EXT`/`5V_LED`,
  D19/D20/C112–C119/FB7, EN-развязки R94–R96, **CV IN3/4 → MCP3208 CH4/CH5** (U45 TL074),
  re-pin J14/J15/J16; **DNP 46 позиций**; ERC **0/0**, pinmap PASS, BOM 241 строка.
- **PANEL-2 rev.2** — J13/J14 (5V_LED, LED_RET, EN_RAILS на 0x23 GPA7, EN_LED5 на GPB6),
  re-pin по канону CORE-2, CVIN3/4 → MCP3208, GATE_IN на 0x23 GPB7, LED_DATA 3.3 В + level shifter;
  ERC 0 errors / 6 warnings, verify 1290/0.

### Изменено
- Реестр: O-13/O-14 закрыты, O-15/O-16 добавлены; решения D-44 (EXPRESSION убран, CV OUT 5/6 — rev.3),
  D-45 (J3 прототип IDC, rev.2 Micro-Fit).

## [0.8.0] — 2025-11-06 — «Стенд, цена, бумага»

### Добавлено
- **P1-стенд** `docs/26-p1-bench-kit.md`: закупка (ESP32-P4 EV, Nucleo-H743ZI2, S3, PCM5102A/PCM1808,
  дисплей, SD, БП/электронная нагрузка, осциллограф), схема стенда, 8-шаговый протокол измерений,
  таблица решения P4/H743/S3 и бюджет стенда $110–320.
- **Cost-down и первый SKU** `docs/27-costdown.md`: разбор BOM ($271 — это «мастерская», не изделие),
  продуктовая нормализация ($205–225 P4 / $183–202 S3), **S3-base kit $199** (партия 10–25,
  direct-sale, limited DIY/beta), батарея (без россыпи 18650), печать (225–245 г / 11–14 ч),
  дефицит/подделки в РФ, решения по конфликтам (Micro-Fit, 3.3 В buck-boost, LED-cap).
- **Бумажный набор 1:1** `renders/templates/bukifon_paperkit_1to1.pdf` (4 стр: панель ×2, профиль
  8°, карта проверки) + `docs/28-paper-kit.md`; раздел в `mechanical/prints.md`.
- **CORE-2 rev.2** (доки/интерфейсы): `hardware/core2/rev2-plan.md` — DNP 39 позиций
  (MT3608 #1/#2, MC34063, BMS), входы `12V_EXT`/`N12_EXT`/`+5V_EXT`, J17 IDC-20 + J18 IDC-12,
  EN с MCP23017 0x23 (2 линии), +5 В 1.6 А; ERC 0/0, pinmap PASS.
- Решения D-37…D-43, открытые O-1…O-6 закрыты, O-8…O-11 (PWR_GOOD/C6, CVIN3/4, GATE_IN, J3, TDM) — в реестре.

### Изменено
- Сайт: разделы «Бенчмарк (P1)» и «Модули и SDK», бейдж v0.8.0, ссылки на стенд/цена/бумага.

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
