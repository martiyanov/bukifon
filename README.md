# Букифон (Bukifon) — открытая платформа: сэмплер + синтезатор + модули

**Версия: 0.5.1** · сайт (опубликован): **https://martiyanov.github.io/bukifon/** (см. [`VERSION`](VERSION), [`CHANGELOG.md`](CHANGELOG.md))

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

## Текущее состояние (v0.4.0)

| Блок | Состояние |
|---|---|
| **Панель v0.4** | 380 × 210 × 3 мм: 42 клавиши Lapka-42 (точная геометрия, половины ±18°), 16 энкодеров Ø14, экран 5.0″ 800×480 без рамки, 10 mini-jack, 2 фейдера 60 мм. Пересечений — 0 |
| **Корпус v0.4** | 380 × 210 × 63 мм, 6 деталей, watertight, печать без поддержек (панель режется 193 + 190 мм с шипом), 83 выреза, fitcheck — 0 конфликтов, ≈304 г / ≈20 ч |
| **Схемы** | v1.0 (CORE-1, PANEL-1, деки, 5 аналоговых модулей, PWR-BATT-1), ERC 0 ошибок — под старую панель 315 × 145; rev.1 под v0.4 — после выбора MCU |
| **Прошивка** | прототип на RP2040: DSP-движок, host-тесты 67/67, UF2 собирается; порт на выбранный MCU — этап P4 |
| **Платформа** | идёт выбор: **ESP32-P4 (32 МБ PSRAM)** — фаворит, **STM32H743** — контрольный кандидат; сначала бенчмарк (P1) |

## Сайт проекта

- Русская страница (live): https://martiyanov.github.io/bukifon/
- English page (live): https://martiyanov.github.io/bukifon/en/
- Исходники сайта: [`docs/index.html`](docs/index.html), [`docs/en/index.html`](docs/en/index.html);
  SEO: [`docs/sitemap.xml`](docs/sitemap.xml), [`docs/robots.txt`](docs/robots.txt), [`docs/llms.txt`](docs/llms.txt);
  деплой: [`.github/workflows/pages.yml`](.github/workflows/pages.yml); метаданные репозитория —
  [`docs/github-metadata.md`](docs/github-metadata.md).

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
