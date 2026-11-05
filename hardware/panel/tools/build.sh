#!/bin/bash
# Build all Bukifon panel/deck artefacts:
#   * regenerate the three schematics (python3 tools/gen.py)
#   * run ERC  -> erc/<board>-erc.rpt
#   * export netlist / PDF / SVG / KiCad BOM per board
#   * verify the exported netlists against the spec tables (tools/verify_netlist.py)
#
# Requires KiCad 10 CLI. Usage:  ./tools/build.sh
set -euo pipefail
cd "$(dirname "$0")/.."
KC="${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/kicad-cache}"
mkdir -p "$XDG_CACHE_HOME" erc

python3 tools/gen.py

for b in panel-1 deck-pad deck-keys; do
  echo "== $b: ERC"
  "$KC" sch erc -o "erc/$b-erc.rpt" "$b/$b.kicad_sch" 2>/dev/null >/dev/null
  grep -E "ERC messages" "erc/$b-erc.rpt" || true
  echo "== $b: exports"
  "$KC" sch export netlist -o "$b/$b.net" "$b/$b.kicad_sch" 2>/dev/null >/dev/null
  "$KC" sch export pdf -o "$b/$b.pdf" "$b/$b.kicad_sch" 2>/dev/null >/dev/null
  "$KC" sch export svg -o "$b/svg" "$b/$b.kicad_sch" 2>/dev/null >/dev/null
  "$KC" sch export bom -o "erc/$b-bom.csv" --fields "Reference;Value;Footprint;QUANTITY" \
        --labels "Refs;Value;Footprint;Qty" --group-by "Value;Footprint" \
        "$b/$b.kicad_sch" 2>/dev/null >/dev/null
done

echo "== netlist verification"
python3 tools/verify_netlist.py
