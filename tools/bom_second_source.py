#!/usr/bin/env python3
"""Аудит вторых источников по BOM-p4.csv/BOM-s3.csv: альтернативы и риск single-source.

Использование: python3 tools/bom_second_source.py [BOM-p4.csv] [--json]
Печатает таблицу: артикул, MPN, кол-во, замена, риск (нет замены = HIGH).
"""
import csv, json, sys

def main():
    path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "BOM-p4.csv"
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig"), delimiter=";"))
    out = []
    for r in rows:
        mpn = (r.get("наименование") or "").strip()
        alt = (r.get("замена") or "").strip()
        qty = (r.get("кол-во") or "").strip()
        ref = (r.get("ref") or "").strip()
        if not mpn: continue
        risk = "HIGH" if alt in ("", "—", "-", "нет") else "ok"
        out.append({"ref": ref, "mpn": mpn, "qty": qty, "alt": alt, "risk": risk})
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"{'risk':4} {'qty':>4}  {'MPN':45} {'замена':35}")
        for o in out:
            if o["risk"] == "HIGH":
                print(f'{o["risk"]:4} {o["qty"]:>4}  {o["mpn"][:45]:45} {o["alt"][:35]:35}')
        highs = sum(1 for o in out if o["risk"] == "HIGH")
        print(f"\nвсего позиций: {len(out)}; без замены (HIGH): {highs}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
