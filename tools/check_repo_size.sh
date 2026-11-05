#!/usr/bin/env bash
# Отчёт по размеру репозитория: tracked-файлы, топ-10 тяжёлых, предупреждения.
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp)
git ls-files -z | while IFS= read -r -d '' f; do printf "%s\t%s\n" "$(du -k "$f" | cut -f1)" "$f"; done > "$TMP"
TOTAL=$(awk -F'\t' '{s+=$1} END{print s/1024}' "$TMP")
echo "tracked: ${TOTAL%.*} МБ, .git: $(du -sh .git | cut -f1)"
echo "--- топ-10:"
sort -rn "$TMP" | head -10 | awk -F'\t' '{printf "%7d КБ  %s\n",$1,$2}'
echo "--- предупреждения (png >300 КБ, svg >300 КБ):"
awk -F'\t' '($2 ~ /\.png$/ || $2 ~ /\.svg$/) && $1>300 {printf "  %7d КБ  %s\n",$1,$2}' "$TMP" | head -20
rm -f "$TMP"
