#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Host simulation of the S3 spike (no devkit required).  Generates SPIKE_METRIC
# and SPIKE_RESULT lines identical in format to the firmware serial log.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CXX="${CXX:-/usr/bin/g++}"
OUT="${OUT:-/tmp/spike_s3_host}"
mkdir -p "$OUT"
"$CXX" -std=c++17 -O2 -Wall -Wextra -I"$ROOT" "$ROOT/spike_sim.cpp" -o "$OUT/spike_sim" || exit 1
"$OUT/spike_sim" --blocks "${SPIKE_BLOCKS:-2000}" --out "$OUT/report.json" "$@"
status=$?
echo "host simulation report: $OUT/report.json"
exit "$status"
