#!/usr/bin/env bash
# Ревью в ChatGPT. Два пути:
#   1) Codex CLI (ChatGPT-аккаунт, работает сейчас):  bash tools/chatgpt_review.sh codex <prompt-file> [out]
#   2) Playwright-браузер (нужен одноразовый логин):   bash tools/chatgpt_review.sh browser <prompt-file> [out]
# По умолчанию: codex.
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=${1:-codex}; PROMPT_FILE=${2:-}; OUT=${3:-}
[ -n "${PROMPT_FILE:-}" ] && [ -f "$PROMPT_FILE" ] || { echo "usage: $0 [codex|browser] prompt.txt [out.md]"; exit 1; }
DATE=$(date +%F); OUT=${OUT:-docs/reviews/chatgpt-review-${DATE}.md}
mkdir -p "$(dirname "$OUT")"
PROMPT=$(cat "$PROMPT_FILE")
{
  echo "# ChatGPT review — $DATE ($MODE)"; echo; echo "## Промпт"; echo '```'; cat "$PROMPT_FILE"; echo '```'; echo; echo "## Ответ"; echo
} > "$OUT"
if [ "$MODE" = "codex" ]; then
  codex exec --sandbox read-only --skip-git-repo-check "$PROMPT" >> "$OUT" 2>/tmp/codex-review.err || { echo "codex failed:"; tail -5 /tmp/codex-review.err; exit 1; }
else
  CHATGPT_PROFILE=${CHATGPT_PROFILE:-$HOME/.openclaw/chatgpt-bridge-profile} node tools/chatgpt_review.js ask "$PROMPT" >> "$OUT" 2>/tmp/pw-review.err || { echo "browser failed:"; tail -5 /tmp/pw-review.err; exit 1; }
fi
echo "сохранено: $OUT ($(wc -l < "$OUT") строк)"
