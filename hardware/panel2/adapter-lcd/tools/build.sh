#!/bin/bash
# LCD FFC-40 adapter build: generate schematic/docs, ERC, exports, PII sanitation.
set -euo pipefail
cd "$(dirname "$0")/.."
KC="${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/kicad-cache}"
mkdir -p "$XDG_CACHE_HOME" erc

python3 tools/gen_lcd_adapter.py

echo "== ERC"
"$KC" sch erc -o "erc/LCD-ADAPTER-erc.rpt" "LCD-ADAPTER.kicad_sch" 2>/dev/null >/dev/null || true
grep -E "ERC messages" "erc/LCD-ADAPTER-erc.rpt" || true

echo "== exports"
"$KC" sch export netlist -o "LCD-ADAPTER.net" "LCD-ADAPTER.kicad_sch" 2>/dev/null >/dev/null
"$KC" sch export pdf -o "LCD-ADAPTER.pdf" "LCD-ADAPTER.kicad_sch" 2>/dev/null >/dev/null
"$KC" sch export svg -o "svg" "LCD-ADAPTER.kicad_sch" 2>/dev/null >/dev/null

echo "== PII sanitation"
python3 tools/sanitize_exports.py
