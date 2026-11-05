#!/usr/bin/env bash
# Вынос вычислений на домашний ПК (Tailscale: sym@100.75.89.89, host "pole").
# Использование:
#   bash tools/home_offload.sh sync                 # rsync рабочего дерева
#   bash tools/home_offload.sh run "make -C firmware/host test"
#   bash tools/home_offload.sh run "pio run -d firmware -e s3base"
#   bash tools/home_offload.sh fetch firmware/tests/out firmware/bench/results
#   bash tools/home_offload.sh shell                 # интерактивно
set -euo pipefail
cd "$(dirname "$0")/.."
HOST=${BUKIFON_HOME:-sym@100.75.89.89}
DIR=${BUKIFON_HOME_DIR:-bukifon/work}
SSH="ssh -o BatchMode=yes -o ConnectTimeout=10 $HOST"
RSYNC_EXCLUDES=(--exclude=.git --exclude=dist --exclude='firmware/host/build*' --exclude='firmware/bench/build*' --exclude='.pio' --exclude='firmware/spike_s3/.pio' --exclude='firmware/idf_p4/build' --exclude='*.o')
cmd=${1:-}
case "$cmd" in
  sync)
    $SSH "mkdir -p ~/$DIR"
    rsync -az --delete "${RSYNC_EXCLUDES[@]}" ./ "$HOST:~/$DIR/"
    echo "синхронизировано: $HOST:~/$DIR"
    ;;
  run)
    shift; [ $# -gt 0 ] || { echo "нужна команда"; exit 1; }
    $SSH "cd ~/$DIR && $*"
    ;;
  fetch)
    shift; [ $# -gt 0 ] || { echo "нужны пути"; exit 1; }
    for p in "$@"; do
      mkdir -p "$(dirname "$p")"
      rsync -az "$HOST:~/$DIR/$p" "$(dirname "$p")/"
      echo "забрано: $p"
    done
    ;;
  shell) exec ssh "$HOST" ;;
  *) sed -n '2,10p' "$0"; exit 1 ;;
esac
