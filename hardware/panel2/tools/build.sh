#!/bin/bash
# PANEL-2 (PRE-FREEZE) build: generate schematic/tables, ERC, exports, verify.
#   ./tools/build.sh        (needs KiCad 10 CLI; override with KICAD_CLI=...)
set -euo pipefail
cd "$(dirname "$0")/.."
KC="${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/kicad-cache}"
mkdir -p "$XDG_CACHE_HOME" erc

python3 tools/gen_panel2.py

echo "== ERC"
"$KC" sch erc -o "erc/PANEL-2-erc.rpt" "PANEL-2.kicad_sch" 2>/dev/null >/dev/null || true
grep -E "ERC messages" "erc/PANEL-2-erc.rpt" || true

echo "== exports"
"$KC" sch export netlist -o "PANEL-2.net" "PANEL-2.kicad_sch" 2>/dev/null >/dev/null
"$KC" sch export pdf -o "PANEL-2.pdf" "PANEL-2.kicad_sch" 2>/dev/null >/dev/null
"$KC" sch export svg -o "svg" "PANEL-2.kicad_sch" 2>/dev/null >/dev/null
"$KC" sch export bom -o "erc/PANEL-2-kicad-bom.csv" \
      --fields "Reference;Value;Footprint;QUANTITY" --labels "Refs;Value;Footprint;Qty" \
      --group-by "Value;Footprint" "PANEL-2.kicad_sch" 2>/dev/null >/dev/null || true

echo "== netlist vs contract"
python3 tools/verify_netlist.py
