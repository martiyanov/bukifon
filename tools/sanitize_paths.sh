#!/usr/bin/env bash
# Заменяет абсолютные домашние пути в текстовых файлах на относительные.
set -uo pipefail
cd "$(dirname "$0")/.."
n=0
while IFS= read -r f; do
  case "$f" in *.png|*.jpg|*.jpeg|*.pdf|*.stl|*.3mf|*.zip|*.bundle|*.heic|*.step|*.FCStd) continue;; esac
  if grep -qE "/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/" "$f" 2>/dev/null; then
    perl -0pi -e 's{/Users/[A-Za-z0-9._-]+/(?:[^"\s<]*/)?(?:Проекты/)?Синтезатор}{<repo>}g; s{/Users/[A-Za-z0-9._-]+}{~}g; s{/home/[A-Za-z0-9._-]+}{~}g' "$f"
    echo "sanitized: $f"; n=$((n+1))
  fi
done < <(git ls-files)
echo "файлов обработано: $n"
