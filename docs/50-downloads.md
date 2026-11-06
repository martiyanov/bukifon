# 50. Скачать и собрать (Downloads)

**Версия:** 0.12.2 · **Статус:** v1.0-rc / **PRE-FREEZE** · **Дата:** 2026-11-05
**Репозиторий:** <https://github.com/martiyanov/bukifon> · **Сайт:** <https://martiyanov.github.io/bukifon/>

Всё, что нужно для сборки «народной» версии: печать → панель → платы → прошивка.
Полный официальный набор — [`RELEASE_BUNDLE.md`](../RELEASE_BUNDLE.md) (собирается
`bash tools/make_release_bundle.sh` → `dist/release-v0.12.2/`, ~15 МБ, SHA256SUMS).

> **Главное ограничение:** **печатных плат (герберов) пока НЕТ** — схемы в стадии
> PRE-FREEZE, PCB не заказывать до DRC/DFM и подписи RC-DoD (см. §4). Печатная часть
> и шаблоны панели — готовы и проверены.

---

## 1. STL/3MF: корпус (4 варианта)

Все детали ≤ 220×220, печать **без поддержек**; панель — по
[`spec/panel-spec-v0.4.json`](../spec/panel-spec-v0.4.json), 83 выреза, ±18°.
Сравнение вариантов и fitcheck — [`docs/45-case-variants.md`](45-case-variants.md),
карта печати — [`mechanical/prints.md`](../mechanical/prints.md).

| Вариант | Папка | Масса | Время | Для чего |
|---|---|---:|---:|---|
| **B-light** (рекомендуется) | [`mechanical/stl_v05_B_light/`](../mechanical/stl_v05_B_light/) | ≈230 г | ≈11.1 ч | народная версия, клин 8°, 3 периметра, gyroid 10% |
| **B** | [`mechanical/stl_v05_B/`](../mechanical/stl_v05_B/) | ≈277 г | ≈18.3 ч | классический PETG-профиль, запас жёсткости |
| **C** | [`mechanical/stl_v05_C/`](../mechanical/stl_v05_C/) | ≈314 г | ≈20.8 ч | клин 12° + **закрытый отсек 1S2P** + складная стойка |
| **B + mic** | [`mechanical/stl_v05_B_mic/`](../mechanical/stl_v05_B_mic/) | ≈278 г | ≈18.4 ч | B + порт MEMS/LED/звуковод/клипса (D-94) |
| **C + mic** | [`mechanical/stl_v05_C_mic/`](../mechanical/stl_v05_C_mic/) | ≈316 г | ≈20.9 ч | C + порт MEMS/LED/звуковод/клипса (D-94) |
| **A (flat)** | [`mechanical/stl_v05_A/`](../mechanical/stl_v05_A/) | ≈302 г | ≈20.0 ч | настольный/студийный, без наклона; fitcheck 17/0, панель = канон |

В каждой папке: `body_L/R`, `panel_L/R`, `foot`, `keycap_v17`, `*_assembly.3mf`;
у C дополнительно `battery_lid`, `stand`. Превью — `mechanical/preview_v05_*/`.
**Первый прогон:** [`docs/35-print-first.md`](35-print-first.md) (печать 1 половинки
и 1 панели, замер массы/времени).

> `mechanical/stl_v05_A/` — актуальный плоский вариант A (302 г/20 ч, flat 0°);
> `mechanical/stl_v04/` в рабочей папке — историческая заглушка (v0.4 в архиве).
> пока не существует — A не пересобирался под v0.5.

## 2. Печатные шаблоны 1:1 (PDF)

Печать **A4, 100 %, без «по размеру страницы»**; проверьте линейку 50 мм на листе.
Все файлы — [`renders/templates/`](../renders/templates/).

| Шаблон | Файл |
|---|---|
| Панель v0.4, 1:1 (2 листа A4, перекрытие 10 мм) | [`bukifon_v04_panel_1to1.pdf`](../renders/templates/bukifon_v04_panel_1to1.pdf) |
| Профиль клина 8°, 1:1 | [`bukifon_v05_wedge8_profile_1to1.pdf`](../renders/templates/bukifon_v05_wedge8_profile_1to1.pdf) |
| Бумажный макет (paperkit: панель + профиль + карта) | [`bukifon_paperkit_1to1.pdf`](../renders/templates/bukifon_paperkit_1to1.pdf) |
| Сборочная карта (слои 1→7) | [`bukifon_assembly_map_1to1.pdf`](../renders/templates/bukifon_assembly_map_1to1.pdf) |
| Lapka-42: раскладка + колпачки (1:1) | [`lapka42_layout_1to1.pdf`](../renders/templates/lapka42_layout_1to1.pdf), [`lapka42_keycaps_1to1.pdf`](../renders/templates/lapka42_keycaps_1to1.pdf) |
| Lapka-42: половины (левая/правая) | [`lapka42_layout_left_1to1.pdf`](../renders/templates/lapka42_layout_left_1to1.pdf), [`lapka42_layout_right_1to1.pdf`](../renders/templates/lapka42_layout_right_1to1.pdf) |

Чужие эталоны (Digitone/Octatrack) в публичный bundle **не входят** (геометрия
третьих лиц). Бумажный макет — [`docs/28-paper-kit.md`](28-paper-kit.md).

## 3. BOM (что покупать)

| Файл | Что это | Для чего |
|---|---|---|
| [`BOM-p4.csv`](../BOM-p4.csv) | **product BOM P4 Standard** ($299): COGS 1/10/25 | основная сборка |
| [`BOM-s3.csv`](../BOM-s3.csv) | product BOM S3 lite | «народный» вариант |
| [`BOM.csv`](../BOM.csv) | мастерский/workshop (катушки, инструмент) | закупка мастерской, **не COGS** |
| [`hardware/cores3/BOM-cores3.csv`](../hardware/cores3/BOM-cores3.csv) | CORE-S3 | плата |
| [`hardware/core2/BOM-core2.csv`](../hardware/core2/BOM-core2.csv) | CORE-2 (P4) | плата |
| [`hardware/panel2/BOM-panel2.csv`](../hardware/panel2/BOM-panel2.csv) | PANEL-2 rev.2 | панель |
| [`hardware/power2/BOM-power2.csv`](../hardware/power2/BOM-power2.csv) | PWR-2 rev.1 | питание |
| [`hardware/modules/BOM-modules.csv`](../hardware/modules/BOM-modules.csv) | 5 аналоговых картриджей | опция |
| [`hardware/power2/bench-bom.csv`](../hardware/power2/bench-bom.csv) | стенд PWR (EVM вариант A) | для тестов, не в изделие |

Методика/маржа — [`docs/33-bom-s3.md`](33-bom-s3.md); комплектация — [`docs/40-kit-contents.md`](40-kit-contents.md).

## 4. Герберы и PCB — **пока НЕ готовы**

**Не заказывать платы.** Схемы помечены `PRE-FREEZE / DO NOT FABRICATE`
([`hardware/cores3/README.md`](../hardware/cores3/README.md),
[`hardware/core2/README.md`](../hardware/core2/README.md)); нет `.kicad_pcb`, DRC/DFM,
герберов, CPL/pick-and-place. Условия для старта производства:

1. подписанный RC-DoD и 8 критериев приёмки — [`docs/36-rc-definition.md`](36-rc-definition.md);
2. DFM-ревью и тестабилити — [`docs/42-dfm-review-gpt.md`](42-dfm-review-gpt.md), [`docs/38-dfm-testability.md`](38-dfm-testability.md);
3. закрытые открытые вопросы спецификации (`spec/90`), включая TPS63802 и MCU-модуль;
4. EVM/стенд PWR — [`docs/44-pwr-bench.md`](44-pwr-bench.md) (вариант A утверждён).

Когда герберы появятся — они войдут в `dist/release-v<версия>/gerbers/` и в
[`RELEASE_BUNDLE.md`](../RELEASE_BUNDLE.md) (таблица артефактов).

## 5. Прошивка

**Версия:** тег `v0.12.2` (VERSION; в публичном репозитории теги пока до `v0.9.1` —
`v0.12.2` создаётся Lead, см. [`RELEASE_BUNDLE.md`](../RELEASE_BUNDLE.md)).
Лицензия GPL-3.0-or-later. Полный обзор — [`firmware/README.md`](../firmware/README.md).

| Что | Где / команда |
|---|---|
| **Native (host) — движок и тесты** | `make -C firmware/host test` (183 unit-теста); `firmware/tests/run_tests.sh` (+ WAV/FFT), `firmware/tests/run_sim_demo.sh` (16-бар демо, UI PNG) |
| **S3-base (скелет)** | `pio run -d firmware/Bukifon` (ESP32-S3; PlatformIO) |
| **Spike S3-стенд** | `firmware/spike_s3/` (`platformio.ini`, `run_host_spike.sh`) — проверка PSRAM/USB/дисплея |
| **P4** | подготовлен, но **не собирается** установленной платформой PlatformIO (см. `firmware/README.md` §Build status); нужна выделенная машина |
| **Pico-прототип (UF2)** | `firmware/artifacts/bukifon-pico.uf2` (+ `.elf`), `firmware/tools/build_pico.sh` |
| **UI-артефакты** | `firmware/artifacts/ui/*.png` (800×480: main, mixer, sampler, daw, sequencer, modules, synth, usb_kbd) |
| **Recovery** | загрузка UF2 (BOOTSEL) для Pico; для S3/P4 — bootloader/recovery по `firmware/README.md`; recovery-образы войдут в bundle после сборки |

Артефакты в релизном наборе: `dist/release-v0.12.2/firmware/artifacts/` (UF2/ELF + UI PNG)
и полный исходник `firmware/` (без build/.pio/out).

## 6. Документация

| Документ | Файл |
|---|---|
| Обзор проекта | [`docs/00-overview.md`](00-overview.md) |
| Quickstart владельца | [`docs/01-quickstart.md`](01-quickstart.md) |
| Руководство по сборке | [`docs/02-build-guide.md`](02-build-guide.md) |
| Пошаговая сборка v0.5-B-light | [`docs/34-assembly.md`](34-assembly.md) |
| Печать: первый прогон | [`docs/35-print-first.md`](35-print-first.md), [`mechanical/prints.md`](../mechanical/prints.md) |
| RC DoD и критерии | [`docs/36-rc-definition.md`](36-rc-definition.md) |
| Compliance / безопасность | [`docs/37-compliance.md`](37-compliance.md) |
| Комплектация SKU | [`docs/40-kit-contents.md`](40-kit-contents.md) |
| DFM и тестабилити | [`docs/38-dfm-testability.md`](38-dfm-testability.md), [`docs/42-dfm-review-gpt.md`](42-dfm-review-gpt.md) |
| Корпуса A/B/C/B-light | [`docs/45-case-variants.md`](45-case-variants.md) |
| Выбор дисплея | [`docs/47-display-selection.md`](47-display-selection.md) |
| PWR-стенд | [`docs/44-pwr-bench.md`](44-pwr-bench.md) |
| SDK модулей | [`docs/24-module-sdk.md`](24-module-sdk.md) |
| Дорожная карта | [`docs/12-roadmap.md`](12-roadmap.md) |

## 7. Лицензии и атрибуция

- Аппаратура/механика — **CERN-OHL-S-2.0** ([`LICENSE-CERN-OHL-S-2.0`](../LICENSE-CERN-OHL-S-2.0));
- прошивка — **GPL-3.0-or-later** ([`LICENSE-GPL-3.0-or-later`](../LICENSE-GPL-3.0-or-later));
- документация/рендеры — **CC BY-SA 4.0** ([`LICENSE-CC-BY-SA-4.0`](../LICENSE-CC-BY-SA-4.0));
- раскладка **Lapka-42** — атрибуция braindefender/lapka-42 ([`NOTICE`](../NOTICE)).
Подробно — [`docs/09-licensing.md`](09-licensing.md). Ссылка на проект — [`CITATION.cff`](../CITATION.cff).

## 8. Как контрибьютить

1. Форк/ветка, PR в `main`; SemVer и CHANGELOG — [`AGENTS.md`](../AGENTS.md).
2. Перед PR: `make -C firmware/host test`, `bash tools/check_all.sh`,
   `bash tools/security_scan.sh` (секреты/EXIF/абсолютные пути).
3. Геометрия — только через `spec/panel-spec-v0.4.json` и генераторы
   (`tools/`, `mechanical/generator/`); правки «руками» в STL не принимаются.
4. Модули: SDK [`docs/24-module-sdk.md`](24-module-sdk.md), SPDX-заголовки обязательны.
5. Не присылать чужие эталоны (Digitone/Octatrack и т.п.) и проприетарные даташиты.

## 9. Проверка релизного набора

```bash
bash tools/make_release_bundle.sh            # соберёт dist/release-v<версия>/
cd dist/release-v0.12.2
shasum -a 256 -c SHA256SUMS                  # macOS/Linux
sha256sum -c SHA256SUMS                      # Linux
cat MANIFEST.md                              # полный список + SHA256 + размеры
```

Состав: 330+ файлов, ~15 МБ; SHA256SUMS + MANIFEST.md + SBOM.txt + README.txt.
Герберов нет (PRE-FREEZE); SBOM — минимальный (полный — TODO).

---

## English (short)

**Downloads.** Version 0.12.2, status **v1.0-rc / PRE-FREEZE**.
- **STL/3MF:** `mechanical/stl_v05_B_light/` (231 g/11.2 h, уже с микрофоном),
  `stl_v05_B/` (277 g), `stl_v05_A/` (302 g, flat), `stl_v05_C/` (314 g);
  **с микрофоном:** `stl_v05_B_mic/` (278 g/18.4 h), `stl_v05_C_mic/` (316 g/20.9 h).
- **1:1 PDFs:** panel v0.4, 8° wedge profile, paperkit, assembly map, Lapka-42 layouts
  (`renders/templates/`).
- **BOM:** `BOM-p4.csv` (P4 Standard), `BOM-s3.csv` (S3 lite), `BOM.csv` (workshop),
  per-board BOMs, `hardware/power2/bench-bom.csv`.
- **Gerbers/PCB:** **not available — PRE-FREEZE, do not order** (see §4/Roadmap).
- **Firmware:** source + `firmware/artifacts/bukifon-pico.uf2`; native tests
  `make -C firmware/host test`; S3 skeleton `pio run -d firmware/Bukifon`;
  P4 prepared but not buildable in current PlatformIO.
- **Docs/licensing:** see §6–§7; hardware CERN-OHL-S-2.0, firmware GPL-3.0-or-later,
  docs CC BY-SA 4.0; Lapka-42 attribution in `NOTICE`.
- **Release bundle:** `bash tools/make_release_bundle.sh` → `dist/release-v0.12.2/`
  (~15 MB, `SHA256SUMS`, `MANIFEST.md`, `SBOM.txt`).
