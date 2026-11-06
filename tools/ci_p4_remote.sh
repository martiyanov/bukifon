#!/usr/bin/env bash
# Повторяемая P4-сборка на домашнем ПК (Tailscale) + host-тесты GCC.
# Использование: bash tools/ci_p4_remote.sh [--full]
set -uo pipefail
cd "$(dirname "$0")/.."
echo "== sync -> home"
bash tools/home_offload.sh sync || { echo "sync FAIL"; exit 1; }
echo "== host tests (GCC) + P4 build"
bash tools/home_offload.sh run "set -e; make -C firmware/host test 2>&1 | tail -3; cd firmware/idf_p4; . \$HOME/esp-idf/export.sh >/dev/null 2>&1; export PATH=\$HOME/.local/bin:\$PATH; idf.py build 2>&1 | grep -E 'Project build complete|binary size|warning:|error:' | tail -6" 2>&1 | tail -12
