#!/usr/bin/env python3
"""Проверка fab-пакета (docs/83): состав, CPL/BOM, PII.

Использование: python3 tools/check_fab_package.py fab/core2/rev1 [--json]
"""
import csv, glob, json, os, re, sys

GERBER_MIN = 8

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    root = sys.argv[1].rstrip("/")
    problems, warnings = [], []
    need = ["bom.csv", "cpl.csv", "stackup.md", "fab-drawing.pdf", "assembly-drawing.pdf", "README.md"]
    for f in need:
        if not os.path.exists(os.path.join(root, f)):
            problems.append(f"нет обязательного файла: {f}")
    gerbers = glob.glob(os.path.join(root, "gerbers", "*.gbr")) + glob.glob(os.path.join(root, "gerbers", "*.gko")) + glob.glob(os.path.join(root, "gerbers", "*.drl"))
    drills = glob.glob(os.path.join(root, "drill", "*.drl"))
    if len(gerbers) < GERBER_MIN:
        problems.append(f"Gerber-слоёв {len(gerbers)} < {GERBER_MIN}")
    if not drills:
        problems.append("нет drill/*.drl")
    # CPL
    if os.path.exists(os.path.join(root, "cpl.csv")):
        rows = read_csv(os.path.join(root, "cpl.csv"))
        cols = set(rows[0].keys()) if rows else set()
        for c in ("ref", "val", "package", "x_mm", "y_mm", "rot", "side"):
            if c not in cols: problems.append(f"CPL: нет колонки {c}")
        for r in rows:
            if (r.get("side") or "").lower() not in ("top", "bottom", ""):
                problems.append(f"CPL: side={r.get('side')} у {r.get('ref')}")
        # BOM vs CPL
        if os.path.exists(os.path.join(root, "bom.csv")):
            bom = read_csv(os.path.join(root, "bom.csv"))
            brefs = {(r.get("ref") or "").strip() for r in bom if (r.get("ref") or "").strip()}
            crefs = {(r.get("ref") or "").strip() for r in rows if (r.get("ref") or "").strip()}
            missing = sorted(crefs - brefs)
            if missing: problems.append(f"CPL refs нет в BOM: {', '.join(missing[:10])}")
            dnp = {(r.get("ref") or "").strip() for r in bom if str(r.get("dnp") or "").strip() in ("1", "true", "yes")}
            bad = sorted(crefs & dnp)
            if bad: problems.append(f"DNP в CPL: {', '.join(bad[:10])}")
    # PII/абсолютные пути
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        if os.path.isfile(p) and p.endswith((".md", ".csv", ".txt", ".json")):
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if re.search(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/", txt):
                problems.append(f"абсолютный домашний путь: {os.path.relpath(p, root)}")
    if "--json" in sys.argv:
        print(json.dumps({"dir": root, "problems": problems, "warnings": warnings, "ok": not problems}, ensure_ascii=False, indent=1))
    else:
        print(f"fab-пакет: {root}")
        for w in warnings: print("  warn:", w)
        for p in problems: print("  FAIL:", p)
        print("ИТОГ:", "✅ пакет готов" if not problems else f"❌ проблем: {len(problems)}")
    return 0 if not problems else 1

if __name__ == "__main__":
    sys.exit(main())
