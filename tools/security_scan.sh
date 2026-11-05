#!/usr/bin/env bash
# Проверка репозитория на секреты, PII и метаданные. Запуск: bash tools/security_scan.sh
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
say(){ printf '\n=== %s\n' "$1"; }

say "1. Секреты в отслеживаемых файлах"
pat='AAG0t|8604502531|127583377|ghp_[A-Za-z0-9]{20,}|github_pat_|sk-[A-Za-z0-9]{20,}|xox[baprs]-|BEGIN [A-Z ]*PRIVATE KEY|api[_-]?key[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9_-]{16,}'
if git grep -nE "$pat" -- . ':!*.pdf' ':!tools/security_scan.sh' >/tmp/sec_hits.txt 2>/dev/null; then
  echo "НАЙДЕНО:"; cat /tmp/sec_hits.txt; fail=1
else echo "чисто"; fi

say "2. Абсолютные домашние пути"
if git grep -nE "/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/" -- . ':!tools/security_scan.sh' ':!SECURITY.md' >/tmp/sec_paths.txt 2>/dev/null; then
  echo "НАЙДЕНО (заменить на ~ или <repo>):"; head -10 /tmp/sec_paths.txt; fail=1
else echo "чисто"; fi

say "3. EXIF/GPS в изображениях"
/tmp/msvenv/bin/python - <<'PY' || fail=1
import glob, sys
from PIL import Image
bad=[]
for f in glob.glob('**/*.jpg', recursive=True)+glob.glob('**/*.jpeg', recursive=True)+glob.glob('**/*.png', recursive=True):
    try:
        ex=Image.open(f).getexif()
        if not ex: continue
        gps = bool(ex.get_ifd(0x8825))
        risky = gps or any(k in ex for k in (271, 272, 315, 33432))  # Make, Model, Artist, Serial
        if risky: bad.append((f, "GPS" if gps else "EXIF", list(ex.keys())[:5]))
    except Exception: pass
if bad:
    print("EXIF найден:", bad); sys.exit(1)
print("чисто")
PY

say "4. Запрещённые файлы в индексе"
bad=$(git ls-files | grep -iE "\.heic$|\.heif$|/datasheets/|/attach/|\.env$|id_rsa|\.pem$|\.key$|\.DS_Store$" || true)
if [ -n "$bad" ]; then echo "НАЙДЕНО: $bad"; fail=1; else echo "чисто"; fi

say "ИТОГ"
[ "$fail" = "0" ] && echo "✅ security ok" || echo "❌ есть проблемы"
exit $fail
