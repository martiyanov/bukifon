#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Bukifon host test runner: build, unit tests, WAV render, FFT report.
#
#   firmware/tests/run_tests.sh
#
# Everything printed here is real tool output (no fabricated numbers).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/tests/out"
LOG="$OUT/test_log.txt"
PYTHON="${PYTHON:-/opt/homebrew/bin/python3}"
CXX="${CXX:-/usr/bin/g++}"
mkdir -p "$OUT"

FAILED=0
{
  echo "Bukifon host test run"
  echo "date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "host: $(uname -s) $(uname -m)"
  echo "compiler: $($CXX --version | head -1)"
  echo "python: $($PYTHON --version 2>&1)"
  echo

  echo "=== 1. clean host build (make -C firmware/host) ==="
  make -C "$ROOT/host" clean all
  BUILD_RC=$?
  echo "build exit code: $BUILD_RC"
  if [ "$BUILD_RC" -ne 0 ]; then
    echo "BUILD FAILED"
    exit 1
  fi
  echo

  echo "=== 2. unit tests (build/bukifon_tests) ==="
  ( cd "$ROOT/host" && ./build/bukifon_tests )
  TEST_RC=$?
  echo "unit test exit code: $TEST_RC"
  echo

  echo "=== 3. render WAV files (48 kHz / 16 bit / stereo) ==="
  "$ROOT/host/build/bukifon_render" "$OUT"
  RENDER_RC=$?
  echo "render exit code: $RENDER_RC"
  echo

  echo "=== 4. FFT / spectral checks (fft_analyze.py) ==="
  "$PYTHON" "$ROOT/tests/fft_analyze.py"
  FFT_RC=$?
  echo "fft exit code: $FFT_RC"
  echo

  if [ "$TEST_RC" -ne 0 ] || [ "$RENDER_RC" -ne 0 ] || [ "$FFT_RC" -ne 0 ]; then
    echo "RESULT: FAILED"
    exit 1
  fi
  echo "RESULT: ALL HOST TESTS PASSED"
} 2>&1 | tee "$LOG"

STATUS=${PIPESTATUS[0]}
echo
echo "full log: $LOG"
exit "$STATUS"
