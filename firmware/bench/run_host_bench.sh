#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Host benchmark run used in firmware/tests/REPORT.md (section "bench").
# Builds the portable harness, runs all frozen scenarios and stores JSON+CSV.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$ROOT/results"
echo "=== build bench harness ==="
make -C "$ROOT" all || exit 1
echo
echo "=== run frozen workload (host reference) ==="
"$ROOT/build/bukifon_bench" --json "$ROOT/results/host.json" --csv "$ROOT/results/host.csv" \
  --blocks "${BENCH_BLOCKS:-2000}" --warmup "${BENCH_WARMUP:-100}"
status=$?
echo
echo "=== S3-base profile (host model) ==="
"$ROOT/build/bukifon_bench" --scenario s3_profile --json "$ROOT/results/host_s3.json" \
  --csv "$ROOT/results/host_s3.csv" --blocks "${BENCH_BLOCKS:-2000}" \
  --warmup "${BENCH_WARMUP:-100}"
s3_status=$?
echo
echo "results: $ROOT/results/host.json + host_s3.json"
[ "$status" -eq 0 ] && exit "$s3_status"
exit "$status"
