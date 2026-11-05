#!/usr/bin/env bash
# Конвертация тяжёлых PNG-рендеров/превью в JPEG + отчёт по экономии.
# PNG с текстом/UI (плоские цвета) не трогаем: JPEG мылит текст.
# Запуск: bash tools/optimize_images.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=/tmp/msvenv/bin/python
DRY=${1:-}
MIN_KB=${MIN_KB:-250}
LIST=$(git ls-files '*.png')
CONVERTED=0; SAVED_KB=0
for f in $LIST; do
  [ -f "$f" ] || continue
  KB=$(du -k "$f" | cut -f1)
  [ "$KB" -lt "$MIN_KB" ] && continue
  # не трогаем UI-скриншоты (плоский текст) и мелкую графику
  case "$f" in
    firmware/artifacts/ui/*|docs/assets/*) continue;;
  esac
  OUT="${f%.png}.jpg"
  if [ -n "$DRY" ]; then echo "would convert $f ($KB KB) -> $OUT"; continue; fi
  $PY - "$f" "$OUT" <<'PYEOF'
import sys
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src)
if im.mode in ("RGBA", "LA", "P"):
    im = im.convert("RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[-1])
    im = bg
else:
    im = im.convert("RGB")
if max(im.size) > 1600:
    im.thumbnail((1600, 1600), Image.LANCZOS)
im.save(dst, "JPEG", quality=85, optimize=True, progressive=True)
PYEOF
  NEWKB=$(du -k "$OUT" | cut -f1)
  SAVED_KB=$((SAVED_KB + KB - NEWKB)); CONVERTED=$((CONVERTED+1))
  git rm -q --cached "$f" >/dev/null 2>&1 || true
  rm -f "$f"
  echo "converted $f ($KB KB) -> $OUT ($NEWKB KB)"
done
if [ -n "$DRY" ]; then echo "dry-run: проверь список"; exit 0; fi
# обновить ссылки в текстовых файлах: name.png -> name.jpg (только сконвертированные)
if [ "$CONVERTED" -gt 0 ]; then
  $PY - <<'PYEOF'
import subprocess, re, os
files = subprocess.run(["git","ls-files","*.md","*.html","*.txt","*.csv","*.json","*.yml","*.yaml"],
                       capture_output=True, text=True).stdout.splitlines()
changed = 0
for p in files:
    try: s = open(p, encoding="utf-8").read()
    except Exception: continue
    # заменяем только если рядом лежит .jpg с тем же именем
    def repl(m):
        base = m.group(1)
        if os.path.exists(base + ".jpg"):
            return base + ".jpg"
        return m.group(0)
    ns = re.sub(r'([\w./-]+)\.png', repl, s)
    if ns != s:
        open(p, "w", encoding="utf-8").write(ns); changed += 1
print(f"ссылок обновлено в {changed} файлах")
PYEOF
fi
echo "ИТОГО: сконвертировано $CONVERTED PNG, экономия ~$((SAVED_KB/1024)) МБ"
