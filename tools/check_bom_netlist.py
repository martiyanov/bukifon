#!/usr/bin/env python3
"""Сверка BOM ↔ netlist: все refs из BOM есть в netlist и наоборот (без #PWR/TP/FID).

Использование:
  python3 tools/check_bom_netlist.py --netlist hardware/core2/netlist.net --bom hardware/core2/BOM-core2.csv
  python3 tools/check_bom_netlist.py ... --json
"""
import argparse, csv, json, re, sys

REF_RE = re.compile(r'\(ref\s+"([^"]+)"')
IGNORE = re.compile(r'^(#|TP\d+$|FID|MH|H\d+$|LOGO|G\d*$|ANT\d*$)', re.I)

def parse_positions(s):
    s = (s or "").strip()
    if not s: return []
    out = []
    for tok in re.split(r"[\s,;]+", s):
        if not tok: continue
        m = re.fullmatch(r"([A-Za-z]+)(\d+)-([A-Za-z]*)(\d+)", tok)
        if m:
            p, a, _, b = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            out += [f"{p}{i}" for i in range(a, b + 1)]
        else:
            out.append(tok)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--bom", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    net = set()
    for line in open(a.netlist, encoding="utf-8", errors="ignore"):
        m = REF_RE.search(line)
        if m: net.add(m.group(1))
    net = {r for r in net if not IGNORE.match(r)}
    rows = list(csv.DictReader(open(a.bom, newline="", encoding="utf-8-sig"), delimiter=";"))
    pos_col = next((c for c in rows[0].keys() if c and any(k in c for k in ("Позиции","Позиционное","Positions","refs","Refs"))), None) if rows else None
    if not pos_col:
        print("BOM: не найдена колонка позиций", file=sys.stderr); return 2
    fp_col = next((c for c in rows[0].keys() if c and any(k in c for k in ("Корпус","Footprint","footprint"))), None) if rows else None
    note_col = next((c for c in rows[0].keys() if c and any(k in c for k in ("Примечание","Note","note"))), None) if rows else None
    bom = set()
    for r in rows:
        fp = (r.get(fp_col) or "").strip() if fp_col else ""
        note = (r.get(note_col) or "").lower() if note_col else ""
        if "off-board" in note:
            continue
        bom.update(parse_positions(r.get(pos_col)))
    bom = {r for r in bom if not IGNORE.match(r)}
    missing_in_net = sorted(bom - net)
    missing_in_bom = sorted(net - bom)
    ok = not missing_in_net and not missing_in_bom
    if a.json:
        print(json.dumps({"netlist": a.netlist, "bom": a.bom, "net_refs": len(net), "bom_refs": len(bom),
                          "in_bom_not_netlist": missing_in_net, "in_netlist_not_bom": missing_in_bom, "ok": ok}, ensure_ascii=False, indent=1))
    else:
        print(f"netlist refs: {len(net)}, BOM refs: {len(bom)}")
        if missing_in_net: print("в BOM, но нет в netlist:", ", ".join(missing_in_net[:40]))
        if missing_in_bom: print("в netlist, но нет в BOM:", ", ".join(missing_in_bom[:40]))
        print("BOM↔netlist:", "OK" if ok else "РАСХОЖДЕНИЯ")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
