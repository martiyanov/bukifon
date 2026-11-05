#!/usr/bin/env bash
# Ночная/предрелизная проверка целостности проекта.
# Запуск: bash tools/check_all.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PY=/tmp/msvenv/bin/python
export MPLCONFIGDIR=/tmp/mplcache
fail=0
say() { printf '\n=== %s\n' "$1"; }

say "1/6 Панель v0.4: 1:1 шаблон + рендер + пересечения"
$PY tools/panel_from_json.py spec/panel-spec-v0.4.json bukifon_v04 2>&1 | tail -3 || fail=1
$PY - <<'PY' || fail=1
import json,sys
d=json.load(open('renders/templates/bukifon_v04_collisions.json'))
print("пересечения:", d["count"])
sys.exit(1 if d["count"] else 0)
PY

say "2/6 Корпус v0.4: STL + fitcheck"
if [ -f mechanical/generator/case_v04.py ]; then $PY mechanical/generator/case_v04.py 2>&1 | tail -3 || fail=1; fi
if [ -f mechanical/generator/fitcheck_v04.py ]; then $PY mechanical/generator/fitcheck_v04.py 2>&1 | tail -3 || fail=1; fi

say "3/6 Прошивка: host-тесты"
if [ -f firmware/host/Makefile ]; then (cd firmware/host && make -s test 2>&1 | tail -5) || fail=1; else echo "skip: firmware/host/Makefile нет"; fi

say "4/6 Сайт: HTML/ассеты/SEO-файлы"
$PY - <<'PY' || fail=1
import os,sys
from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.links=[]; s.stack=[]
    def handle_starttag(s,t,a):
        if t not in ("meta","link","br","img","hr","input"): s.stack.append(t)
        for k,v in a:
            if k in ("href","src") and v: s.links.append(v)
    def handle_endtag(s,t):
        if t in s.stack:
            while s.stack and s.stack.pop()!=t: pass
bad=[]
for f in ("docs/index.html","docs/en/index.html"):
    if not os.path.exists(f): bad.append(f); continue
    p=P(); p.feed(open(f,encoding="utf-8").read())
    for l in p.links:
        if l.startswith(("assets/","../assets/")):
            path=os.path.normpath(os.path.join(os.path.dirname(f), l))
            if not os.path.exists(path): bad.append(path)
    if p.stack: bad.append(f+" unclosed "+str(p.stack))
for f in ("docs/sitemap.xml","docs/robots.txt","docs/llms.txt"):
    if not os.path.exists(f): bad.append(f)
print("сайт:", "ok" if not bad else bad)
sys.exit(1 if bad else 0)
PY

say "5/6 Версии и документация"
$PY - <<'PY' || fail=1
import json,re,sys
ver=open('VERSION').read().strip()
cl=open('CHANGELOG.md',encoding='utf-8').read()
rd=open('README.md',encoding='utf-8').read()
ok = re.match(r'^\d+\.\d+\.\d+$', ver) and f"[{ver}]" in cl and ver in rd
print(f"VERSION={ver}; в CHANGELOG: {f'[{ver}]' in cl}; в README: {ver in rd} -> {'ok' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY

say "6/6 Требования/реестр"
[ -f spec/90-requirements-registry.md ] && echo "реестр: ok" || { echo "реестр: НЕТ"; fail=1; }

say "ИТОГ"
if [ "$fail" = "0" ]; then echo "✅ все проверки пройдены"; else echo "❌ есть ошибки (см. выше)"; fi
exit $fail
