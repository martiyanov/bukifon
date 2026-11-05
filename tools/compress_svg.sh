#!/usr/bin/env bash
# KiCad SVG-экспорты весят десятки МБ. Сжимаем в .svg.gz (gzip -9), обновляем ссылки в текстах.
# PDF-экспорты остаются как человекочитаемые; .svg.gz при необходимости: gunzip file.svg.gz
set -euo pipefail
cd "$(dirname "$0")/.."
SAVED=0; N=0
while IFS= read -r f; do
  [ -f "$f" ] || continue
  KB=$(du -k "$f" | cut -f1)
  [ "$KB" -lt 300 ] && continue
  gzip -9 -c "$f" > "$f.gz"
  NEWKB=$(du -k "$f.gz" | cut -f1)
  SAVED=$((SAVED + KB - NEWKB)); N=$((N+1))
  git rm -q --cached "$f" >/dev/null 2>&1 || true
  rm -f "$f"
  git add "$f.gz"
  echo "gzip: $f ($KB KB) -> $f.gz ($NEWKB KB)"
done < <(git ls-files '*.svg')
if [ "$N" -gt 0 ]; then
  python3 - <<'PY'
import subprocess, os
files = subprocess.run(["git","ls-files","*.md","*.html","*.txt"],capture_output=True,text=True).stdout.splitlines()
changed=0
for p in files:
    try: s=open(p,encoding="utf-8").read()
    except Exception: continue
    ns=s
    for line in s.splitlines():
        pass
    # все .svg, у которых есть рядом .svg.gz
    import re
    def repl(m):
        path=m.group(1)
        return path+".gz" if os.path.exists(path+".gz") else m.group(0)
    ns=re.sub(r'([\w./-]+)\.svg\b', repl, s)
    if ns!=s:
        open(p,"w",encoding="utf-8").write(ns); changed+=1
print("ссылок обновлено в",changed,"файлах")
PY
fi
echo "ИТОГО: $N SVG сжато, экономия ~$((SAVED/1024)) МБ"
