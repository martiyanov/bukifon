#!/usr/bin/env python3
"""Проверка относительных ссылок в markdown: docs/*.md и корневые README/AGENTS.

Использование: python3 tools/check_docs_links.py [--json]
Игнорирует http(s)://, mailto:, #anchor-only. Для ссылок вида path#anchor проверяет файл.
"""
import json, os, re, sys

LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
SKIP_DIRS = {".git", "dist", "firmware/host/build", "firmware/bench/build", "node_modules", ".pio", "archive"}

def iter_md():
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(root, f)

def main():
    bad = []
    total = 0
    for path in iter_md():
        base = os.path.dirname(path)
        for ln, line in enumerate(open(path, encoding="utf-8", errors="ignore"), 1):
            for m in LINK_RE.finditer(line):
                raw = m.group(1).strip()
                if not raw or raw.startswith(("http://", "https://", "mailto:", "#", "tel:")):
                    continue
                target = raw.split("#", 1)[0]
                if not target: continue
                total += 1
                cand = os.path.normpath(os.path.join(base, target))
                if not os.path.exists(cand):
                    bad.append({"file": path, "line": ln, "link": raw, "resolved": cand})
    if "--json" in sys.argv:
        print(json.dumps({"checked": total, "broken": bad}, ensure_ascii=False, indent=1))
    else:
        print(f"проверено ссылок: {total}; битых: {len(bad)}")
        for b in bad[:60]:
            print(f'{b["file"]}:{b["line"]}  ->  {b["link"]}')
    return 0 if not bad else 1

if __name__ == "__main__":
    sys.exit(main())
