#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Builds the Bukifon RP2040 firmware (arduino-pico core) with PlatformIO.
#
# Usage:  firmware/tools/build_pico.sh
#
# Verified recipe (05.11.2025): PlatformIO Core 6.2.0 + community platform
# maxgerhardt (core arduino-pico). In sandboxes redirect the PlatformIO home:
#   export PLATFORMIO_CORE_DIR=/tmp/piocore
# Full build: SUCCESS, Flash 36.1 %, RAM 80.1 %, UF2 764 KiB.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIO="${PIO:-$HOME/.platformio/penv/bin/pio}"

echo "Bukifon RP2040 firmware build"
echo "project: $ROOT/Bukifon"
echo

if ! command -v "$PIO" >/dev/null 2>&1; then
  cat <<'EOF'
PlatformIO is not installed. Install it with one of:

  python3 -m pip install --user platformio
  # or
  curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py -o /tmp/get-platformio.py
  python3 /tmp/get-platformio.py

Then install the arduino-pico enabled platform (community platform, core is
selected via board_build.core = earlephilhower in firmware/Bukifon/platformio.ini):

  pio platform install raspberrypi

Alternative using arduino-cli:

  arduino-cli core install rp2040:rp2040
  arduino-cli compile --fqbn rp2040:rp2040:rpipico \
      --build-property "compiler.cpp.extra_flags=-I$ROOT/src -DBUKIFON_EMBEDDED" \
      "$ROOT/Bukifon"

Note: PlatformIO compiles firmware/src through Bukifon/engine_unity.cpp; if you
add/remove a .cpp file under firmware/src, update that unity file.
EOF
  exit 2
fi

"$PIO" run -d "$ROOT/Bukifon" "$@"
status=$?
if [ "$status" -eq 0 ]; then
  echo "firmware build OK: $ROOT/Bukifon/.pio/build/pico/firmware.uf2"
else
  echo "firmware build FAILED (exit $status)"
fi
exit "$status"
