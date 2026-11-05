#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Bukifon host demo: build the simulator, play the deterministic 16-bar demo
# twice, diff the event logs, render the 4 UI screenshots to PNG and verify
# the artefacts.  This is the command to reproduce the v0.5 demo.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-/opt/homebrew/bin/python3}"
SIM="$ROOT/host/build/bukifon_sim"
OUT="$ROOT/artifacts/ui"
SIMOUT="$ROOT/artifacts/sim"
mkdir -p "$OUT" "$SIMOUT"

echo "=== 1. build host simulator ==="
make -C "$ROOT/host" sim || exit 1

echo
echo "=== 2. 16-bar demo (deterministic event log) ==="
"$SIM" --out "$OUT" --log "$SIMOUT/event_log.txt" | tee "$SIMOUT/demo_log.txt"
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
  echo "DEMO FAILED (simulator exit $status)"
  exit 1
fi

echo
echo "=== 3. determinism: second run, diff event logs ==="
"$SIM" --no-determinism --out "$OUT" --log "$SIMOUT/event_log_rerun.txt" > "$SIMOUT/demo_log_rerun.txt" 2>&1
if diff -q "$SIMOUT/event_log.txt" "$SIMOUT/event_log_rerun.txt" >/dev/null; then
  echo "determinism: PASS (run 1 and run 2 logs are identical)"
else
  echo "determinism: FAIL (event logs differ)"
  exit 1
fi
lines=$(wc -l < "$SIMOUT/event_log.txt" | tr -d ' ')
echo "event log: $lines lines"

echo
echo "=== 4. UI screenshots PPM -> PNG ==="
"$PYTHON" "$ROOT/tools/ppm_to_png.py" "$OUT" || exit 1

echo
echo "=== 5. artefacts ==="
for name in main sequencer mixer modules; do
  png="$OUT/$name.png"
  if [ -s "$png" ]; then
    size=$(wc -c < "$png" | tr -d ' ')
    echo "OK  $png ($size bytes)"
  else
    echo "MISSING $png"
    exit 1
  fi
done
echo
echo "DEMO OK — screenshots in $OUT, event logs in $SIMOUT"
