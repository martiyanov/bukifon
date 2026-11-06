# Итоговый отчёт по проекту «Букифон» (на срез v0.50.0)

Документ-срез для быстрого входа: что сделано, где лежит, что проверено, что блокирует
v1.0-rc и что делать дальше. Обновляется при каждом релизе.

## 1. Что уже есть

| Слой | Артефакты | Доказательства |
|---|---|---|
| Панель/эргономика | канон 380×210, 83 выреза, paperkit 1:1, сборочная карта | `spec/panel-spec-v0.4.json`, fitcheck 0 |
| Корпуса | A (flat), B, **B-light 228.9 г/11.0 ч**, C, B_mic/C_mic; 11 задних вырезов + SD/USB-C; 3MF/STL/STEP | `mechanical/`, docs/45/50, fitcheck 41/0… |
| Электроника | CORE-2 rev.3 (P4+C6, USB HS, mic), PANEL-2 rev.3 (MEMS, J16), PWR-2 rev.1; ERC 0/0, 0/6w, 0/0 | `hardware/`, docs/38/42/71 |
| PCB rev.1 | 4 каркаса KiCad, контуры/крепёж/keepout, нетлист/футпринты, **DRC 0/0**, fab dry-run PASS | `hardware/*/rev1/`, `fab/*/rev1-scaffold/`, docs/82/83 |
| Прошивка | 407/407 тестов; UI 7 вкладок; 12 треков (4+8); GEN; project v2; storage A/B+recovery; self-test 21; SDK v0.2; RU/EN+кириллица; P4 bring-up | `firmware/`, docs/61/66/70/42 |
| P4 | IDF 5.5: bin **369 552 Б**, factory 1 МиБ (65 % free), partitions/NVS | docs/59, `firmware/idf_p4/` |
| Веб | **https://bukifon.ru/** (канон, HTTPS), .com→301; демо RU/EN, PWA/DAW-плагин — бэклог | docs/88, docs/86 |
| Документация | 90+ документов: философия, читаемость, аналоги, сборка, FAQ, пресс-кит, supply, cost-down | `docs/`, сайт |
| Проверки | `check_all` 8/8, security, 407 тестов, 683 ссылки 0 битых, BOM↔netlist OK | `tools/` |

## 2. Что проверено (последние прогоны)

- `bash tools/check_all.sh` → ✅ (8 групп, включая BOM↔netlist и docs-ссылки);
- `bash tools/security_scan.sh` → ✅ (секреты/PII/EXIF/абсолютные пути);
- `firmware/tests/run_tests.sh` → **407/407 PASS**; GCC 13 на home — то же;
- `idf.py build` (P4, IDF 5.5) → SUCCESS, 0 warnings, bin 369 552 Б;
- `node tools/test_demo_ux.js both` → RU/EN **8/8**, a11y/EXT/ширина — PASS;
- `tools/ci_p4_remote.sh` → host **407/407**, P4 build 369 552 Б (65 % free), 0 warnings;
- `tools/check_fab_package.py fab/*` → **PASS** (dry-run, не для заказа);
- `tools/verify_release_bundle.sh` → SHA256 0 нарушений, PII ok.


## 2a. Финальная проверка (06.11.2025, v0.52.1)

| Проверка | Результат |
|---|---|
| `tools/check_all.sh` | ✅ 8/8 |
| `tools/security_scan.sh` | ✅ секреты/PII/EXIF/пути |
| `firmware/tests/run_tests.sh` | **407/407 PASS**; GCC 13 на home — 407/407 |
| `tools/ci_p4_remote.sh` | P4 build **369 552 Б**, factory 65 % free, 0 warnings |
| `node tools/test_demo_ux.js both` | **RU PASS · EN PASS** (8/8, a11y/EXT/ширина) |
| `node tools/test_demo_mic.js` / `check_demo_layout.js` | MIC-DEMO OK / LAYOUT OK |
| DRC 4 платы (`kicad-cli pcb drc`) | **0 нарушений** на каждой |
| `tools/check_fab_package.py` ×4 | **PASS** (dry-run, не для заказа) |
| `tools/verify_release_bundle.sh` | SHA256 0 нарушений, PII ok |

## 3. Что блокирует v1.0-rc (только физика)

| # | Блокер | Действие владельца |
|---|---|---|
| 1 | **Заказ P1-стенда ~$442** | оплатить по docs/54 |
| 2 | **Заказ PWR-стенда ~$277** | оплатить по docs/44 |
| 3 | **LCD-адаптер + образцы ~$73** | оплатить по docs/49 |
| 4 | **Печать половинки B-light 228.9 г** | принтер/мастерская, docs/35 |
| 5 | **Пересоздать репозиторий** | docs/41, бандл `dist/bukifon-fresh-v0.50.0.bundle` |

После 1–3: 13 измерений PWR (2.5 дня) → P1 P4 vs H743 → MCU freeze → трассировка PCB
(каркасы готовы) → PCB rev.1 → 3–5 прототипов → RC DoD + UX-тест 5 людей → **v1.0-rc**.

## 4. Что осознанно отложено

- **Веб-приложение (PWA)**: Web MIDI, микрофон, 4+8 треков, WAV/stems — docs/86;
- **DAW-плагин**: VST3/AU + CLAP (JUCE 8) — docs/86;
- **лупер/вокодер** — v1.1; **4 CC p-lock** — v1.1; **USB-MIDI host** — опция rev.3;
- полные футпринты пассивов + GND-заливка — на этапе трассировки (docs/82 §12).

## 5. Где смотреть

- сайт: https://bukifon.ru/ · демо `/demo/` · GitHub: https://github.com/martiyanov/bukifon
- статус/ворота: docs/75; отчёт: этот файл; утренний срез: docs/73; ограничения: docs/76;
- заказ: docs/54; сборка: docs/72; день-1: docs/80; RC notes: docs/87; сайт/деплой: docs/88.
