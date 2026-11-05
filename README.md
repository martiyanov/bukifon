# Букифон (Bukifon) — открытая платформа: сэмплер + синтезатор + модули

**Версия: 0.12.2** · сайт (опубликован): **https://martiyanov.github.io/bukifon/** (см. [`VERSION`](VERSION), [`CHANGELOG.md`](CHANGELOG.md))

**Букифон** — настольный музыкальный инструмент-платформа, который собирается из
доступных компонентов, печатается на 3D-принтере, расширяется модулями и полностью
открыт: схемы (KiCad), прошивка (C++), механика (STL/генератор), документация.

## Народный синтезатор

Букифон задуман как **народный инструмент**: доступный, повторяемый и открытый. Целевые
ориентиры комплекта (без печати и работы): «народный» на ESP32-S3 — **≤ $200**,
«стандарт» на ESP32-P4 — **≤ $300**, «полный» с аналоговыми картриджами — **≤ $400**.
Подробности и cost-down план — [spec/00-vision.md §13](spec/00-vision.md).

## Что это по сути

Один корпус **380 × 210 × 63 мм**, три режима:

- **Sampler** (в духе Elektron Digitakt) — сэмплы, запись/импорт по USB-C и SD,
  срезы, гранулярность, insert-FX, p-locks, условия триггеров;
- **Synth** (в духе Elektron Syntakt) — 4 части, 8 голосов, 4-оп FM, wavetable,
  ZDF-фильтры, лестница Муга, 3D-мод-матрица 16 слотов;
- **Hybrid** — сэмплы как источники синтеза, общий секвенсор и мод-матрица.

Плюс **режим компьютерной клавиатуры/контроллера**: USB-C композит (HID-клавиатура + MIDI +
UAC2 аудио), DAW-режим (16 энкодеров как CC, transport), **Wi-Fi и Bluetooth** (BLE-MIDI,
BLE HID, передача проектов). То есть Букифон — ещё и необычная механическая клавиатура
с 16 ручками.

**Свои модули может писать каждый:** программный модуль (SDK `BukifonModule`, C++/Lua),
аналоговый картридж на шине 26-pin или сменная панельная дека (18 пэдов / 42 клавиши).
Подробнее — [spec/00-vision.md §12](spec/00-vision.md).

## Текущее состояние (v0.12.2)

| Блок | Состояние |
|---|---|
| **Панель v0.4** | 380 × 210 × 3 мм: 42 клавиши Lapka-42 (точная геометрия, ±18°), 16 энкодеров Ø14, экран 5.0″ 800×480 без рамки, 10 mini-jack, 2 фейдера 60 мм; пересечений 0 |
| **Корпус v0.5-B** | **клин 8°**: 380 × 210 × 61.5 мм (перед 32 / зад 61.5), 6 деталей watertight, печать без поддержек 279 г / 18.3 ч, fitcheck 32/0, профиль 1:1 для картонной проверки |
| **Дисплей** | RGB565 поверх RGB888 FPC-40: **TFT-H050A1SVIST4R40** (HotLCD/ST7262, 40-pin, 1000 нит, $18–25), резерв NHD/EJ050NA; DSI — rev.3.1 (`docs/47`) |
| **PWR-стенд** | 13 измерений до PCB (`docs/44`); BOM: база $123.92 + EVM $153 = **$276.92** (вариант A, D-79); breadboard запрещён |
| **Корпуса** | A flat 302 г · B 8° 277 г · **B-light 230 г / 11.1 ч** · C 12° 314 г (батарейный отсек, подставка) — `docs/45` |
| **Factory test** | 14 тестов, CLI `factory --json`, loopback-плаг, EOL 2–2.5 мин (`docs/46`); **183/183 тестов** |
| **Product BOM P4 (первый SKU)** | `BOM-p4.csv` + `docs/33/40`: COGS **$219/$194/$176** на 1/10/25; **P4 Standard $299** (gross 35 % на 10), Full Bundle $399; S3 lite — второй профиль ($199/$175/$157) |
| **Сборка** | `renders/templates/bukifon_assembly_map_1to1.pdf` (4 стр: слои, панель 1:1, крепёж/шлейфы), `docs/34`, `docs/35` print-first, 3D exploded |
| **Прошивка v0.7** | **160/160 тестов**; S3 HAL сборка SUCCESS; spike `spike_s3` SUCCESS; **P1 P4-профиль** PASS (RGB/DSI 52 fps, HS UAC2 8×8, max block 320 µs); UI 4 режимов; Module API v0.1 |
| **CORE-2 rev.2 (основная плата)** | ESP32-P4 + ESP32-C6, 32 МБ PSRAM, USB HS, RGB565/DSI, ERC 0/0; DFM/DFT: 30 TP, 20 self-test, recovery, 6 слоёв — PRE-FREEZE |
| **Корпус B-light** | **230 г / 11.1 ч** (−17 % массы, −39 % времени): стенки 2.0/дно 1.8, 3 периметра + локальные рёбра, панели-оболочки; 6 STL watertight, fitcheck 32/0 |
| **CORE-2 rev.2** | схема внесена: J17/J18, входы 12V_EXT/N12_EXT/+5V_EXT/5V_LED, EN-развязки, CV IN3/4 на MCP3208, re-pin J14/J15/J16, DNP 46; **ERC 0/0**, pinmap PASS |
| **PANEL-2 rev.2** | J13/J14 (5V_LED, LED_RET, EN_RAILS, EN_LED5), re-pin по канону, GATE_IN на MCP23017 0x23, LED_DATA 3.3 В + shifter; **ERC 0 err/6 warn**, verify 1290/0 |
| **PWR-2 rev.1** | батарея 1S2P + BMS BQ297 + **MAX17048** + рельсы шины: +12 В 330 мА (TPS61088), −12 В 95 мА (LMR33630 IBB), +5 В 1.6 А, +5V_LED; master load-switch, EN рельсов, питание только от BQ24074 OUT/VSYS; ERC **0/0**, PRE-FREEZE |
| **Электроника rev.1** | **CORE-2** (ESP32-P4 + ESP32-C6 Wi-Fi/BLE по SPI, USB HS composite, аудио PCM5102A/PCM1808, CV, MIDI, шина) — ERC **0/0**, pinmap PASS (54/55 GPIO), **PRE-FREEZE**; **PANEL-2** (16 энкодеров + 42 клавиши через 4× MCP23017, LCD, 10 джеков, 2 фейдера, 3 шлейфа) — ERC 0 errors / 6 warnings, **PRE-FREEZE**. Не заказывать до бенчмарка P1 |
| **Прошивка v0.6** | host-демо UI 800×480, секвенсор 4×16 (хранение 8 дорожек), save/load с CRC16, Module API v0, режимы Synth/Sampler/DAW/USB-keyboard, каркасы USB composite и BLE/Wi-Fi; **120/120 тестов**; сборки ESP32-S3 и RP2040; P4 — toolchain пока нет |
| **P1-стенд** | `docs/26` — что купить (P4 EV, H743, S3, PCM5102A/1808, дисплей, SD, БП/нагрузка), схема стенда, протокол измерений и таблица решения; без стенда MCU не фиксируется |
| **Cost-down / первый SKU** | `docs/27`: product BOM вместо «мастерской», S3-base **kit $199** (партия 10–25, direct-sale), P4 $299 после P1, full $399 bundle; батарея — не россыпь 18650 |
| **Бумажный макет** | `renders/templates/bukifon_paperkit_1to1.pdf` (4 стр: панель 1:1 ×2, профиль 8°, карта 7 проверок) + `docs/28` |
| **Бенчмарк P1** | workload freeze + харнесс `firmware/bench` (7 сценариев, JSON/CSV, детерминизм, 0 аллокаций): host worst **218 µs** = 16.4 % дедлайна, 431 µs запаса до критерия 650 µs; `bench_s3` собран, стенды P4/H743 — следующие |
| **SDK модулей** | Module API v0 (10 функций, лимиты, WCET/bypass), каталог `modules/` (template + gain_fx C++ + LFO Lua), `tools/validate_module.py`, `tools/new_module.sh`, CI `modules.yml` |
| **BOM (draft)** | 92 позиции: база ≈ 21 657 ₽ (~$271), полный ≈ 32 518 ₽ (~$406); «народная» цель ≤ $200 / стандарт ≤ $300 — cost-down план в spec/00 §13 |
| **Безопасность** | история очищена от GPS EXIF и vendor-PDF с IP, санитизация путей, `SECURITY.md`, `tools/security_scan.sh` |

## Ключевые документы

| Документ | О чём |
|---|---|
| [spec/90-requirements-registry.md](spec/90-requirements-registry.md) | реестр требований R-01…, журнал решений D-01… — единственный источник истины |
| [docs/12-roadmap.md](docs/12-roadmap.md) | дорожная карта P0–P8 с числовыми критериями выхода |
| [docs/10-elektron-hardware.md](docs/10-elektron-hardware.md) | что стоит внутри Elektron (ColdFire, DSP56300, SHARC, FPGA) |
| [docs/11-esp32-feasibility.md](docs/11-esp32-feasibility.md) | можно ли на ESP32: расчёт нагрузки, P4/S3/H743/Teensy |
| [docs/03-second-opinion-mcu.md](docs/03-second-opinion-mcu.md) | независимое ревью плана (DeepSeek) |
| [docs/04-consultation-gpt.md](docs/04-consultation-gpt.md) | консультация GPT/Codex (gpt-5.6) по MCU и архитектуре |
| [docs/00-context-transfer.md](docs/00-context-transfer.md) | контекст проекта для передачи другим агентам |
| [PULL_REQUEST.md](PULL_REQUEST.md) | описание MR v0.4 |
| [docs/20-analog-projects.md](docs/20-analog-projects.md) | разведка аналогов (Deluge, M8, Polyend, Daisy, PreenFM, Norns…) |
| [docs/21-ergonomics.md](docs/21-ergonomics.md) | эргономика: клин 8°, 32/61.5 мм, экран 35° |
| [docs/22-night-plan.md](docs/22-night-plan.md) | ночной план и scope freeze |
| [docs/23-nightly-report.md](docs/23-nightly-report.md) | отчёт ночи: что готово/симулируется/нельзя заказывать |
| [docs/24-module-sdk.md](docs/24-module-sdk.md) | SDK модулей: Module API v0, упаковка, ограничения |
| [docs/25-power-architecture.md](docs/25-power-architecture.md) | питание: ±12 В, BQ24074, MAX17048, земля, стенд до PCB |
| [docs/26-p1-bench-kit.md](docs/26-p1-bench-kit.md) | P1-стенд: закупка, схема, протокол измерений, таблица решения MCU |
| [docs/27-costdown.md](docs/27-costdown.md) | cost-down, product BOM, первый SKU S3-kit $199, батарея, дефицит |
| [docs/28-paper-kit.md](docs/28-paper-kit.md) | бумажный макет 1:1 за 30 минут: 7 проверок эргономики |
| [docs/29-p1-order.md](docs/29-p1-order.md) | точный список заказа P1-стенда (что, где, сколько) |
| [docs/30-security-purge.md](docs/30-security-purge.md) | запрос на purge старых PII-объектов GitHub (SHA) |
| [docs/31-core-s3-constraints.md](docs/31-core-s3-constraints.md) | CORE-S3: GPIO 31, 1-bit SD, USB endpoint ceiling, RGB+1FB, TPS63802 |
| [docs/32-progress-report.md](docs/32-progress-report.md) | сводный отчёт v0.4→v0.9.1: вехи, блокеры, следующий шаг |
| [docs/33-bom-s3.md](docs/33-bom-s3.md) | product BOM S3-base: COGS 1/10/25, опции, маржа |
| [docs/34-assembly.md](docs/34-assembly.md) | пошаговая сборка S3-base (B-light) |
| [docs/35-print-first.md](docs/35-print-first.md) | что печатать первым и как проверить жёсткость |
| [docs/36-rc-definition.md](docs/36-rc-definition.md) | Definition of Done для v1.0-rc (S3-base) |
| [docs/37-compliance.md](docs/37-compliance.md) | RED/GPSR, батарея, EMC, SBOM, гарантия, SKU-экономика |
| [docs/05-benchmark-workload.md](docs/05-benchmark-workload.md) | workload freeze P1 и критерии |
| [docs/05a-benchmark-howto.md](docs/05a-benchmark-howto.md) | как запустить бенчмарк на S3/P4/H743 |
| [modules/](modules/) | каталог модулей: шаблон, примеры gain_fx и LFO |
| [firmware/bench/](firmware/bench/) | харнесс P1 (fm/granular/mix/psram/ui/usb, JSON/CSV) |
| [SECURITY.md](SECURITY.md) | политика безопасности и приватности |

## Компоновка панели v0.4

Канон — [`spec/panel-spec-v0.4.json`](spec/panel-spec-v0.4.json) (координаты всех элементов в мм).
Печать 1:1: [renders/templates/bukifon_v04_panel_1to1.pdf](renders/templates/bukifon_v04_panel_1to1.pdf)
(2 листа A4, перекрытие 10 мм; печатать 100 %, проверить линейку 50 мм).

| Элемент | Координаты (мм) |
|---|---|
| Клавиши | 2 × 21 Lapka-42, Choc 18 × 17, половины ±18°, кластеры центром (83, 148) и (297, 148) |
| Энкодеры Ø14 | X = 25.2 / 54.1 / 82.6 / 111.4 и 269.3 / 297.8 / 326.6 / 355.8; Y = 35.7 / 68.5 |
| Экран 5.0″ | вырез 108 × 64.8, центр (190, 58.7), без рамки |
| Mini-jack 3.5 | 10 шт., X = 129.9…247.8 (шаг 13.1), Y = 10.5 |
| Фейдеры | X = 175.1 / 204.0, центр Y = 150, прорезь 2.5 × 63 |
| Динамики | **нет** (по ТЗ) |
| Разъёмы под экраном | **нет** (по ТЗ) |

Превью: [renders/templates/bukifon_v04_render.png](renders/templates/bukifon_v04_render.png),
сравнение с концептом заказчика: [renders/templates/bukifon_v04_vs_concept.png](renders/templates/bukifon_v04_vs_concept.png).

## 3D-печать (корпус v0.4)

- STL/3MF: [`mechanical/stl_v04/`](mechanical/stl_v04/) — panel_L/panel_R, body_L/body_R, foot, keycap;
  сборка `bukifon_v04_assembly.3mf`;
- рендеры: [`mechanical/preview_v04/`](mechanical/preview_v04/) (изометрия, вид сверху,
  наложение на 2D-эталон, разнесённый вид, close-up);
- параметры печати и время: [mechanical/prints.md](mechanical/prints.md);
- сборка: [mechanical/assembly.md](mechanical/assembly.md), проверки: [mechanical/fit_check.md](mechanical/fit_check.md).

## Сборка прошивки (прототип RP2040)

```bash
export PLATFORMIO_CORE_DIR=/tmp/piocore
/tmp/msvenv/bin/pio run -d firmware/Bukifon      # сборка UF2
cd firmware/host && make test                    # host-тесты DSP (67 тестов)
```

## Структура репозитория

Текущее — в рабочих папках, всё старое — в [`archive/`](archive/README.md); карта — [STRUCTURE.md](STRUCTURE.md).


```
spec/            требования, архитектура, электрика, механика, прошивка, реестр требований
docs/            обзор, гайд сборки, лицензии, ревью MCU, консультация GPT, дорожная карта
hardware/        KiCad: CORE-1, PANEL-1, деки, аналоговые модули, питание
firmware/        прошивка (движок, драйверы, UI, тесты)
mechanical/      параметрический генератор корпуса, STL/3MF, рендеры, печать/сборка
tools/           генераторы раскладок, печатных листов, трассировка концепта
renders/         шаблоны 1:1 и превью (templates/)
refs/            эскизы и фото заказчика, пакет handoff v0.3
BOM.csv          сводный BOM
```

## Версионирование

SemVer + аннотированный тег на каждый релиз. Правила — в [AGENTS.md](AGENTS.md).
История — [CHANGELOG.md](CHANGELOG.md). Теги: `v0.1.0` (прототип 315×145), `v0.2.0`
(печатные листы), `v0.3.0` (раскладка 380×210), `v0.4.0` (канон v0.4).

## Лицензии и атрибуция

- аппаратура и механика — CERN-OHL-S-2.0;
- прошивка — GPL-3.0-or-later;
- документация — CC BY-SA 4.0;
- раскладка Lapka-42 — атрибуция braindefender/lapka-42 (см. [NOTICE](NOTICE)).

## Репозиторий

**https://github.com/martiyanov/bukifon** — `main` (стабильная ветка), работа ведётся
в `feature/panel-v04-canonical` до слияния MR.
