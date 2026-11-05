#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# make_release_bundle.sh — собирает публичный релизный набор Букифона.
#
#   bash tools/make_release_bundle.sh
#
# Результат: dist/release-v<VERSION>/
#   stl/ pdf/ bom/ docs/ spec/ firmware/ licenses/
#   SBOM.txt, MANIFEST.md, SHA256SUMS, README.txt
#
# Требования: bash, tar, find, shasum/sha256sum. dist/ — в .gitignore.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
V="$(tr -d '[:space:]' < VERSION)"
DATE="$(date -u +%Y-%m-%d)"
OUT="dist/release-v$V"

echo "== Букифон release bundle v$V =="
echo "root: $ROOT"
echo "out : $OUT"

rm -rf "$OUT"
mkdir -p "$OUT"/{stl,pdf,bom,docs,spec,firmware,licenses}

# ---------- helpers ----------
warn() { echo "WARN: $*" >&2; }
copy() { # copy <src> <dst-dir>
  if [ -e "$1" ]; then cp -R "$1" "$2/"; else warn "нет $1 — пропущено"; fi
}

# ---------- STL/3MF ----------
mkdir -p "$OUT/stl"
copy mechanical/stl_v05_B_light "$OUT/stl"; mv "$OUT/stl/stl_v05_B_light" "$OUT/stl/B_light"
copy mechanical/stl_v05_B       "$OUT/stl"; mv "$OUT/stl/stl_v05_B"       "$OUT/stl/B"
copy mechanical/stl_v05_C       "$OUT/stl"; mv "$OUT/stl/stl_v05_C"       "$OUT/stl/C"
# A (flat, исторический v0.4) — из архива
if [ -d archive/v0.4/mechanical/stl_v04 ]; then
  cp -R archive/v0.4/mechanical/stl_v04 "$OUT/stl/A_flat"
else
  warn "нет archive/v0.4/mechanical/stl_v04 — A/flat пропущен"
fi

# ---------- PDF-шаблоны 1:1 (только наши/Bukifon+Lapka; чужие refs не включаем) ----------
for f in \
  bukifon_assembly_map_1to1.pdf \
  bukifon_paperkit_1to1.pdf \
  bukifon_v04_panel_1to1.pdf \
  bukifon_v05_wedge8_profile_1to1.pdf \
  lapka42_keycaps_1to1.pdf \
  lapka42_layout_1to1.pdf \
  lapka42_layout_left_1to1.pdf \
  lapka42_layout_right_1to1.pdf ; do
  copy "renders/templates/$f" "$OUT/pdf"
done

# ---------- BOM ----------
for f in BOM.csv BOM-p4.csv BOM-s3.csv \
         hardware/core/BOM-core.csv hardware/panel/BOM-panel.csv \
         hardware/modules/BOM-modules.csv hardware/power/BOM-power.csv \
         hardware/core2/BOM-core2.csv hardware/cores3/BOM-cores3.csv \
         hardware/panel2/BOM-panel2.csv hardware/power2/BOM-power2.csv \
         hardware/power2/bench-bom.csv ; do
  if [ -f "$f" ]; then
    mkdir -p "$OUT/bom/$(dirname "$f")"
    cp "$f" "$OUT/bom/$f"
  else
    warn "нет $f — пропущено"
  fi
done

# ---------- документация ----------
docs_public=(
  docs/00-overview.md docs/01-quickstart.md docs/02-build-guide.md
  docs/09-licensing.md docs/12-roadmap.md docs/21-ergonomics.md
  docs/24-module-sdk.md docs/27-costdown.md docs/33-bom-s3.md
  docs/34-assembly.md docs/35-print-first.md docs/36-rc-definition.md
  docs/37-compliance.md docs/38-dfm-testability.md docs/40-kit-contents.md
  docs/42-dfm-review-gpt.md docs/43-p4-bringup.md docs/44-pwr-bench.md
  docs/45-case-variants.md docs/46-factory-test.md docs/47-display-selection.md
  docs/50-downloads.md docs/BOM.md
)
for f in "${docs_public[@]}"; do
  [ -f "$f" ] && cp "$f" "$OUT/docs/" || warn "нет $f — пропущено"
done
# механика/сборка/печать
for f in mechanical/README.md mechanical/prints.md mechanical/assembly.md \
         mechanical/fit_check.md mechanical/LICENSE ; do
  [ -f "$f" ] && cp "$f" "$OUT/docs/" || warn "нет $f — пропущено"
done

# ---------- спецификации ----------
for f in spec/00-vision.md spec/10-panel-ui.md spec/20-electronics.md \
         spec/30-mechanics.md spec/40-firmware.md spec/90-requirements-registry.md \
         spec/panel-spec-v0.4.json ; do
  [ -f "$f" ] && cp "$f" "$OUT/spec/" || warn "нет $f — пропущено"
done

# ---------- лицензии и корневые документы ----------
for f in LICENSE LICENSE-CERN-OHL-S-2.0 LICENSE-GPL-3.0-or-later \
         LICENSE-CC-BY-SA-4.0 NOTICE CITATION.cff \
         VERSION CHANGELOG.md README.md ; do
  [ -f "$f" ] && cp "$f" "$OUT/licenses/" || warn "нет $f — пропущено"
done

# ---------- прошивка: исходники + бинарные артефакты + UI ----------
tar -cf - -C "$ROOT" \
  --exclude='build*' --exclude='.pio' --exclude='out' \
  --exclude='__pycache__' --exclude='*.o' --exclude='*.a' --exclude='*.d' \
  --exclude='artifacts' firmware | tar -xf - -C "$OUT"
mkdir -p "$OUT/firmware/artifacts"
for f in bukifon-pico.uf2 bukifon-pico.elf ; do
  [ -f "firmware/artifacts/$f" ] && cp "firmware/artifacts/$f" "$OUT/firmware/artifacts/" || warn "нет firmware/artifacts/$f"
done
mkdir -p "$OUT/firmware/artifacts/ui"
for f in firmware/artifacts/ui/*.png ; do
  [ -f "$f" ] && cp "$f" "$OUT/firmware/artifacts/ui/" || true
done

# ---------- корневой манифест набора ----------
[ -f RELEASE_BUNDLE.md ] && cp RELEASE_BUNDLE.md "$OUT/" || warn "нет RELEASE_BUNDLE.md"

# ---------- SBOM (минимальный, по NOTICE/лицензиям; полный — TODO) ----------
cat > "$OUT/SBOM.txt" <<SBOM
Букифон (Bukifon) v$V — SBOM (минимальный), $DATE
Проект: https://github.com/martiyanov/bukifon

Компоненты проекта:
  * Аппаратура/механика — CERN-OHL-S-2.0 (LICENSE-CERN-OHL-S-2.0)
  * Прошивка — GPL-3.0-or-later (LICENSE-GPL-3.0-or-later)
  * Документация/рендеры — CC-BY-SA-4.0 (LICENSE-CC-BY-SA-4.0)

Третьи стороны (полный перечень — NOTICE):
  * Raspberry Pi Pico/RP2040 — hardware terms; SDK BSD-3-Clause
  * arduino-pico core — LGPL-2.1
  * TinyUSB — MIT
  * ESP32 / ESP-IDF (Espressif) — Apache-2.0; ESP32-P4/C6 — trademarks Espressif
  * KiCad symbol/footprint libraries — CC-BY-SA-4.0 with exception (attribution: KiCad)
  * Blender — GPL-2.0-or-later (только рендеры)
  * Trimesh/manifold3d/shapely/numpy/matplotlib — MIT/BSD/Apache-2.0 (build-time)
  * Lapka-42 (braindefender/lapka-42) — геометрия клавиш, атрибуция обязательна
  * Даташиты производителей — справочные данные; trademarks их владельцев

Полный SBOM с версиями зависимостей прошивки — TODO (docs/09 §10, Lead).
SBOM

# ---------- SHA256 + MANIFEST ----------
HASHER="shasum -a 256"
command -v sha256sum >/dev/null 2>&1 && HASHER="sha256sum -b"
# список файлов (относительно OUT), кроме служебных
LIST="$OUT/.filelist"
( cd "$OUT" && find . -type f ! -name SHA256SUMS ! -name MANIFEST.md ! -name README.txt ! -name SBOM.txt ! -name .filelist | sort ) > "$LIST"
( cd "$OUT" && while IFS= read -r f; do $HASHER "$f"; done < .filelist ) > "$OUT/SHA256SUMS"
rm -f "$LIST"

{
  echo "# MANIFEST — Букифон v$V ($DATE)"
  echo
  echo "Полный список файлов с размерами и SHA256. Проверка: \`shasum -a 256 -c SHA256SUMS\`."
  echo
  echo "| # | Артефакт (путь) | Размер, КБ | SHA256 |"
  echo "|---:|---|---:|---|"
  n=0
  ( cd "$OUT" && find . -type f ! -name SHA256SUMS ! -name MANIFEST.md ! -name README.txt ! -name SBOM.txt | sort ) | while IFS= read -r f; do
    n=$((n+1))
    sz=$(stat -f%z "$OUT/$f" 2>/dev/null || stat -c%s "$OUT/$f")
    h=$( (cd "$OUT" && $HASHER "$f") | awk '{print $1}')
    printf '| %d | `%s` | %d | `%s` |\n' "$n" "${f#./}" "$((sz/1024))" "$h"
  done
} > "$OUT/MANIFEST.md"

# ---------- README.txt ----------
FILES=$(find "$OUT" -type f | wc -l | tr -d ' ')
SIZE=$(du -sh "$OUT" | awk '{print $1}')
cat > "$OUT/README.txt" <<TXT
Букифон (Bukifon) — официальный release bundle v$V ($DATE)
================================================================

Состав:
  stl/       — STL/3MF: B_light (230 г/11.1 ч), B (277 г), C (314 г), A_flat (302 г, v0.4)
  pdf/       — печатные 1:1: панель v0.4, профиль 8°, paperkit, assembly map, Lapka-42
  bom/       — BOM: мастерский, product P4/S3, BOM плат, bench-bom
  docs/      — quickstart, build guide, assembly, prints, RC DoD, compliance, лицензии
  spec/      — контракты (vision, panel, electronics, mechanics, firmware, R-реестр)
  firmware/  — исходники + артефакты (bukifon-pico.uf2/elf, UI PNG), recovery — в прошивке
  licenses/  — LICENSE/NOTICE/CITATION, VERSION, CHANGELOG, README

Проверка целостности:
  shasum -a 256 -c SHA256SUMS        (macOS/Linux)
  sha256sum -c SHA256SUMS            (Linux)
Полный манифест: MANIFEST.md. SBOM: SBOM.txt.

Статус: v1.0-rc / PRE-FREEZE. PCB-герберы в этот набор НЕ входят — ждать DRC/DFM
и решения Lead (см. RELEASE_BUNDLE.md). Прошивка: прототип RP2040 (UF2) + исходники
S3/P4-веток; бинарник под P4/S3 — после сборки на выделенной машине.

Всего файлов: $FILES, объём: $SIZE.
TXT

echo "== готово =="
echo "файлов: $FILES, объём: $SIZE"
[ "$(du -sm "$OUT" | awk '{print $1}')" -lt 100 ] || warn "размер >100 МБ — проверить состав"
echo "проверка: (cd $OUT && shasum -a 256 -c SHA256SUMS | tail -3)"
