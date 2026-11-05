# RELEASE BUNDLE — Букифон v1.0-rc (v0.12.2)

**Официальный состав публичного релизного набора** «народного» проекта.
Собирается одной командой; `dist/` в `.gitignore` и **не коммитится**.

```bash
bash tools/make_release_bundle.sh
# → dist/release-v0.12.2/   (~15 МБ, 339 файлов, SHA256SUMS, MANIFEST.md, SBOM.txt, README.txt)
```

**Версия:** 0.12.2 ([`VERSION`](VERSION)) · **Дата:** 2026-11-05 · **Статус:** v1.0-rc / **PRE-FREEZE**
**Репозиторий:** <https://github.com/martiyanov/bukifon> · **Страница загрузок:** [`docs/50-downloads.md`](docs/50-downloads.md)

> **Тег:** релиз помечается аннотированным тегом `v0.12.2` (AGENTS.md §1). В публичном
> репозитории теги пока до `v0.9.1` — `v0.12.2` создаёт Lead; содержимое этого
> бандла соответствует рабочему дереву при `VERSION=0.12.2`.

---

## 1. Состав набора

| Группа | Что | Файлов | Объём |
|---|---|---:|---:|
| `stl/` | STL/3MF: **B-light** (230 г/11.1 ч), **B** (277 г), **C** (314 г), **A_flat** (302 г, v0.4) | 64 | 9.0 МБ |
| `pdf/` | 1:1 шаблоны: панель v0.4, профиль 8°, paperkit, assembly map, Lapka-42 (раскладка/колпачки/половины) | 8 | 544 КБ |
| `bom/` | `BOM.csv` (workshop), `BOM-p4.csv`, `BOM-s3.csv`, BOM всех плат (`hardware/*/BOM-*.csv`), `bench-bom.csv` | 10 | 176 КБ |
| `docs/` | quickstart, build guide, assembly, prints, RC-DoD, compliance, BOM.md, 33/34/35/36/37/38/40/42/43/44/45/46/47/50, mechanical README/prints/assembly/fit_check | 34 | 508 КБ |
| `spec/` | контракты: vision, panel-ui, electronics, mechanics, firmware, R-реестр, `panel-spec-v0.4.json` | 7 | 124 КБ |
| `firmware/` | полный исходник (без build/.pio/out) + `bukifon-pico.uf2`/`.elf` + 8 UI PNG (800×480) | 200+ | 4.3 МБ |
| `licenses/` | LICENSE (×4), NOTICE, CITATION, VERSION, CHANGELOG, README | 10 | 132 КБ |
| корень | `RELEASE_BUNDLE.md`, `SHA256SUMS`, `MANIFEST.md`, `README.txt`, `SBOM.txt` | 5 | ~56 КБ |

**Итого:** **339 файлов, 15 МБ** (<100 МБ лимита).

## 2. Манифест ключевых артефактов (SHA256)

Полный список — `dist/release-v0.12.2/MANIFEST.md` (все 339 файлов с размерами и SHA256);
контрольные суммы — `SHA256SUMS`. Проверка:

```bash
cd dist/release-v0.12.2 && shasum -a 256 -c SHA256SUMS     # macOS/Linux
```

| Артефакт | Путь в bundle | Размер | SHA256 |
|---|---|---:|---|
| Product BOM P4 Standard | `bom/BOM-p4.csv` | 14.0 КБ | `57f3046ec7df00ddec07ab2b0c9e14e2f222936091b9e2b333f877b07b7871a4` |
| Product BOM S3 lite | `bom/BOM-s3.csv` | 14.0 КБ | `e4a29daaabdb16014dfc240b0624c7581aca0d63557e9b658769d537465daae0` |
| Мастерский BOM | `bom/BOM.csv` | 24.8 КБ | `c7188724eafb59eb44f3c117138836ba164c8a7d5ce2d280659b7e83f04fc585` |
| Прошивка Pico (UF2) | `firmware/artifacts/bukifon-pico.uf2` | 778.8 КБ | `ea8ad65a68aef7177a7f605e1bb12f9dbff8a13cc3303b859b9a226f959c9a61` |
| Прошивка Pico (ELF) | `firmware/artifacts/bukifon-pico.elf` | 1.18 МБ | `5b24f046fb5bae2a67a221cd073918b7774bbda3b81281cf40671cd5a4ba6ecf` |
| Панель v0.4, 1:1 | `pdf/bukifon_v04_panel_1to1.pdf` | 60.2 КБ | `d8e7442c7d8155aa62b9ed220581b8d0dc282e74eb431f7aa7461749ed466123` |
| Профиль клина 8°, 1:1 | `pdf/bukifon_v05_wedge8_profile_1to1.pdf` | 44.0 КБ | `79ccec5c010a13035d3ef1943726da0cf49ab00487b82a954d993b942799d13d` |
| Paperkit (бумажный макет) | `pdf/bukifon_paperkit_1to1.pdf` | 182.6 КБ | `238f6169609e2218abb76242a86a32890bf922ca24ff7af7f0288e7db89ceb56` |
| Сборочная карта | `pdf/bukifon_assembly_map_1to1.pdf` | 116.6 КБ | `f2eeba2f91a16601c9b7c49b01fda17b67c57cc7fe816c3d4f3217545956bfbc` |
| NOTICE (атрибуция) | `licenses/NOTICE` | 1.8 КБ | `d656e378a3c6bb683453ec0d9497fdea6c68e15f3c7681ff727632bedca0c001` |
| VERSION | `licenses/VERSION` | 7 Б | `f482d06e4ee83158e42999dcf951d5909861dad7e03317deb2b1e2ddd5c46274` |
| Страница загрузок | `docs/50-downloads.md` | 13.0 КБ | `f0ef31f77ab199ecc2602c4d16c775f5412172aabcde7a463e806013a784a242` |

> SHA256 набора пересчитывается при каждом запуске скрипта; таблица выше — снимок
> текущей сборки. Для официального релиза публикуются `SHA256SUMS` + `MANIFEST.md` из bundle.

## 3. Чек-лист публикации v1.0-rc

| # | Пункт | Статус |
|---|---|---|
| 1 | **Source snapshot** (тег `v0.12.2`, `VERSION`, `CHANGELOG`) | ⚠️ тег создаёт Lead (в репо до `v0.9.1`); VERSION/CHANGELOG — есть |
| 2 | **STL/3MF** 4 варианта + `SHA256SUMS` | ✅ 64 файла, 9.0 МБ |
| 3 | **PDF 1:1** (панель, профиль, paperkit, assembly map, Lapka-42) | ✅ 8 файлов |
| 4 | **BOM CSV** (product + платы + bench) | ✅ 10 файлов |
| 5 | **Герберы/CPL (pick-and-place)** | ❌ **нет — PRE-FREEZE**, ждать DRC/DFM + RC-DoD (`docs/36`, `docs/42`) |
| 6 | **Прошивка: bin + source** | ✅ source + Pico UF2/ELF + UI PNG; ⚠️ S3/P4-бинарники — после сборки на выделенной машине |
| 7 | **Recovery** | ⚠️ Pico: BOOTSEL/UF2 (есть); S3/P4 recovery-образы — после сборки |
| 8 | **Гайды** (quickstart, build guide, assembly, prints) | ✅ docs/ + mechanical/ |
| 9 | **Known limitations** | ✅ [`docs/36`](docs/36-rc-definition.md), [`docs/37`](docs/37-compliance.md) §8 |
| 10 | **Safety** (батарея/±12 В/ESD) | ✅ [`docs/37`](docs/37-compliance.md) §2, [`docs/40`](docs/40-kit-contents.md) §5–6 |
| 11 | **Лицензии** (CERN-OHL-S, GPL, CC BY-SA, NOTICE, Lapka-42) | ✅ licenses/ |
| 12 | **SBOM** | ⚠️ минимальный (`SBOM.txt`); полный с версиями зависимостей — TODO (`docs/09` §10) |

**Публикация:** после закрытия п.5 и п.6 (герберы + бинарники S3/P4) — собрать bundle,
проверить `SHA256SUMS`, приложить к GitHub Release, обновить [`docs/50`](docs/50-downloads.md)
и README. Герберы войдут в `dist/release-v<версия>/gerbers/` + CPL.

## 4. Что осталось (не блокирует печать/панель)

1. **Герберы/CPL/DRC/DFM** — критический путь релиза плат (`docs/42`, `docs/38`).
2. **Бинарники S3-base и P4** — PlatformIO-сборка S3/P4 на выделенной машине
   (`firmware/README.md` §Build status; `docs/48` home-compute).
3. **Recovery-образы** S3/P4 + инструкция восстановления.
4. **Полный SBOM** с версиями (ESP-IDF/TinyUSB/LittleFS и т.д.) и автоматической проверкой лицензий.
5. **Тег `v0.12.2`** и GitHub Release (зона Lead, AGENTS.md §1).
6. **EVM/стенд PWR** — закупка утверждена (D-79, `docs/44`), результаты — `docs/51`.

## 5. Known limitations / статус (кратко)

- **PRE-FREEZE**: схемы CORE-2/CORE-S3/PANEL-2/PWR-2 не для производства; PCB не заказывать.
- **Прошивка**: движок/тесты — 183 unit-теста (host); S3-скелет собирается, **P4 — подготовлен,
  но не собирается** установленной платформой; периферия (I2S/USB/дисплей) — `TODO(hw)`.
- **S3 lite**: USB FS (stereo UAC2, не 8×8), SPI-дисплей 10–20 fps; P4 — RGB/DSI, HS USB.
- **Батарея**: в первую партию не входит (D-56); старт от внешнего БП.
- **UI/аудио**: 800×480 full ≥15 fps / partial ≥30 (S3); 8 mono-движков / до 6 голосов (S3).
- **Сборка**: DIY-кит, пайка + печать; гарантия/RMA — [`docs/37`](docs/37-compliance.md) §5.

## 6. Лицензии

- Аппаратура/механика — **CERN-OHL-S-2.0** ([`LICENSE-CERN-OHL-S-2.0`](LICENSE-CERN-OHL-S-2.0));
- Прошивка — **GPL-3.0-or-later** ([`LICENSE-GPL-3.0-or-later`](LICENSE-GPL-3.0-or-later));
- Документация/рендеры — **CC BY-SA 4.0** ([`LICENSE-CC-BY-SA-4.0`](LICENSE-CC-BY-SA-4.0));
- Lapka-42 — атрибуция braindefender/lapka-42 ([`NOTICE`](NOTICE)); чужие эталоны
  (Digitone/Octatrack) и проприетарные даташиты в публичный bundle **не входят**.
Подробно — [`docs/09-licensing.md`](docs/09-licensing.md).

## 7. Ссылки

[`docs/50-downloads.md`](docs/50-downloads.md) · [`tools/make_release_bundle.sh`](tools/make_release_bundle.sh) ·
[`VERSION`](VERSION) · [`CHANGELOG.md`](CHANGELOG.md) · [`README.md`](README.md) ·
[`docs/36-rc-definition.md`](docs/36-rc-definition.md) · [`docs/37-compliance.md`](docs/37-compliance.md) ·
[`docs/40-kit-contents.md`](docs/40-kit-contents.md) · [`docs/42-dfm-review-gpt.md`](docs/42-dfm-review-gpt.md) ·
[`docs/44-pwr-bench.md`](docs/44-pwr-bench.md) · [`docs/47-display-selection.md`](docs/47-display-selection.md).
