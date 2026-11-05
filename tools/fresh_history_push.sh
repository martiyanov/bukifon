#!/usr/bin/env bash
# Готовит «свежую историю» для пересоздания репозитория (purge PII + уменьшение .git).
# Создаёт orphan-ветку с текущим деревом и коммитом, готовую к push в новый репозиторий.
# Использование: bash tools/fresh_history_push.sh [remote-url]
set -euo pipefail
cd "$(dirname "$0")/.."
V=$(cat VERSION)
BR="fresh/v${V}"
REMOTE="${1:-}"
if git rev-parse --verify "$BR" >/dev/null 2>&1; then git branch -D "$BR" >/dev/null; fi
git checkout --orphan "$BR" >/dev/null
git add -A
git commit -q -m "Букифон v${V} — начальная история (squash, чистая, без старых объектов)"
echo "Создана ветка $BR: $(git rev-parse --short HEAD), файлов: $(git ls-files | wc -l | tr -d ' ')"
git bundle create "dist/bukifon-fresh-v${V}.bundle" HEAD
echo "Bundle: dist/bukifon-fresh-v${V}.bundle ($(du -sh "dist/bukifon-fresh-v${V}.bundle" | cut -f1))"
git checkout -q feature/panel-v04-canonical
if [ -n "$REMOTE" ]; then
  git push --force "$REMOTE" "$BR:main" && git push --force "$REMOTE" "$BR:refs/tags/v${V}"
  echo "Запушено в $REMOTE (main + tag v${V})"
fi
