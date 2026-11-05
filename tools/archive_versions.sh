#!/usr/bin/env bash
# Раскладка старых версий в archive/<version>/ (история сохраняется через git mv).
set -euo pipefail
cd "$(dirname "$0")/.."
mv_dir() { [ -e "$1" ] && { mkdir -p "$(dirname "$2")"; git mv "$1" "$2"; echo "dir  $1 -> $2"; } || true; }
mv_file() { [ -e "$1" ] && { mkdir -p "$(dirname "$2")"; git mv "$1" "$2"; echo "file $1 -> $2"; } || true; }

# v1.0 — базовый прототип 315×145
mv_dir  mechanical/stl        archive/v1.0/mechanical/stl
mv_dir  mechanical/preview    archive/v1.0/mechanical/preview
mv_file mechanical/exploded.png archive/v1.0/mechanical/exploded.png
mv_dir  mechanical/test_fit   archive/v1.0/mechanical/test_fit
mv_dir  renders/mech          archive/v1.0/renders/mech
for f in panel_layout.png panel_layout_keys.png panel_layout_report.txt \
         v1_2_deck_lapka.png v1_2_deck_pads.png v1_2_head.png v1_2_report.txt \
         v1_3_option_A.png v1_3_option_B.png v1_3_option_B_outward.png \
         v1_3_option_C.png v1_3_option_C_outward.png v1_3_option_D.png \
         variantB_panel.png; do mv_file "renders/$f" "archive/v1.0/renders/$f"; done
mv_file renders/templates/panel_1to1_left.pdf  archive/v1.0/renders/templates/panel_1to1_left.pdf
mv_file renders/templates/panel_1to1_right.pdf archive/v1.0/renders/templates/panel_1to1_right.pdf
mv_file renders/templates/panel_preview.png    archive/v1.0/renders/templates/panel_preview.png
mv_file firmware/artifacts/bukifon-pico.uf2    archive/v1.0/firmware/bukifon-pico.uf2
mv_file firmware/artifacts/bukifon-pico.elf    archive/v1.0/firmware/bukifon-pico.elf

# v0.3 — handoff-раскладка
mv_file spec/panel-spec-v0.3.json archive/v0.3/spec/panel-spec-v0.3.json
for f in $(git ls-files 'renders/templates/bukifon_v03_*'); do mv_file "$f" "archive/v0.3/renders/templates/$(basename "$f")"; done

# v1.4 / v1.5 / v1.6
mv_file spec/panel-spec-v1.4.1.json archive/v1.4/spec/panel-spec-v1.4.1.json
for f in $(git ls-files 'renders/templates/bukifon_v1_4_*'); do mv_file "$f" "archive/v1.4/renders/templates/$(basename "$f")"; done
mv_file spec/panel-spec-v1.5.json archive/v1.5/spec/panel-spec-v1.5.json
for f in $(git ls-files 'renders/templates/bukifon_v1_5_*'); do mv_file "$f" "archive/v1.5/renders/templates/$(basename "$f")"; done
for f in $(git ls-files 'renders/templates/bukifon_v1_6_*'); do mv_file "$f" "archive/v1.6/renders/templates/$(basename "$f")"; done

# v1.7 / v1.8
mv_file spec/panel-spec-v1.7.json archive/v1.7/spec/panel-spec-v1.7.json
mv_dir  mechanical/stl_v17     archive/v1.7/mechanical/stl_v17
mv_dir  mechanical/preview_v17 archive/v1.7/mechanical/preview_v17
mv_dir  mechanical/step_v17    archive/v1.7/mechanical/step_v17
mv_file mechanical/fit_check_v17.md archive/v1.7/mechanical/fit_check_v17.md
for f in $(git ls-files 'renders/templates/bukifon_v1_7_*' 'renders/templates/v1_7_*'); do mv_file "$f" "archive/v1.7/renders/templates/$(basename "$f")"; done
mv_file renders/v1_7_layout_report.txt archive/v1.7/renders/v1_7_layout_report.txt

mv_file spec/panel-spec-v1.8.json archive/v1.8/spec/panel-spec-v1.8.json
mv_dir  mechanical/stl_v18     archive/v1.8/mechanical/stl_v18
mv_dir  mechanical/step_v18    archive/v1.8/mechanical/step_v18
mv_file mechanical/fit_check_v18.md archive/v1.8/mechanical/fit_check_v18.md
for f in $(git ls-files 'renders/templates/bukifon_v1_8_*' 'renders/templates/compare_ref_v18_v04.png' 'renders/templates/v1_8_side_by_side.png'); do mv_file "$f" "archive/v1.8/renders/templates/$(basename "$f")"; done
mv_dir  renders/v1_8           archive/v1.8/renders/v1_8
mv_file renders/v1_8_layout_report.txt archive/v1.8/renders/v1_8_layout_report.txt

# v0.4 — плоский корпус/панель (панель v0.4 остаётся ТЕКУЩЕЙ геометрией,
# поэтому spec/panel-spec-v0.4.json и bukifon_v04_* НЕ переносим)
mv_dir  mechanical/stl_v04     archive/v0.4/mechanical/stl_v04
mv_dir  mechanical/preview_v04 archive/v0.4/mechanical/preview_v04

echo "готово. Проверь: git status"
