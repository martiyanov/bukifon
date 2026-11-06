#!/usr/bin/env python3
"""Проверка измерений PWR-стенда против лимитов docs/51 (T1–T13).

Использование:
  python3 tools/pwr_bench_check.py docs/pwr-results-template.csv
  python3 tools/pwr_bench_check.py results.csv --json --strict

Лимиты в CSV: '<=30', '>=85', '12.0 ±5%', '45-55', '4.15-4.25', '<=3.3'.
Пустой measured = SKIP (ещё не измерено). --strict → exit 1 при любом FAIL.
"""
import csv, json, re, sys

def parse_limit(s):
    s = s.strip().replace(',', '.')
    m = re.fullmatch(r"<=\s*(-?\d+(?:\.\d+)?)", s)
    if m: return ("le", float(m.group(1)))
    m = re.fullmatch(r">=\s*(-?\d+(?:\.\d+)?)", s)
    if m: return ("ge", float(m.group(1)))
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*±\s*(\d+(?:\.\d+)?)\s*%", s)
    if m: return ("pm", float(m.group(1)), float(m.group(2)))
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", s)
    if m: return ("range", float(m.group(1)), float(m.group(2)))
    raise ValueError(f"непонятный лимит: {s!r}")

def check(measured, lim):
    kind = lim[0]
    if kind == "le": return measured <= lim[1]
    if kind == "ge": return measured >= lim[1]
    if kind == "pm": return abs(measured - lim[1]) <= abs(lim[1]) * lim[2] / 100.0
    if kind == "range": return lim[1] <= measured <= lim[2]
    return False

def main(argv):
    if not argv:
        print(__doc__); return 2
    path = argv[0]
    as_json = "--json" in argv
    strict = "--strict" in argv
    rows, fails, measured_n = [], 0, 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            tid = (r.get("test_id") or "").strip()
            lim_s = (r.get("limit") or "").strip()
            meas_s = (r.get("measured") or "").strip().replace(",", ".")
            if not tid or not lim_s: continue
            item = {"id": tid, "name": (r.get("test_name") or "").strip(), "limit": lim_s, "measured": meas_s or None, "status": "SKIP"}
            if meas_s:
                measured_n += 1
                try:
                    lim = parse_limit(lim_s); val = float(meas_s)
                    item["status"] = "PASS" if check(val, lim) else "FAIL"
                except ValueError as e:
                    item["status"] = "ERROR"; item["detail"] = str(e)
                if item["status"] != "PASS": fails += 1
            rows.append(item)
    if as_json:
        print(json.dumps({"file": path, "tests": rows, "measured": measured_n, "fails": fails, "gate": "PASS" if fails == 0 and measured_n else ("SKIP" if not measured_n else "FAIL")}, ensure_ascii=False, indent=1))
    else:
        for it in rows:
            ms = it["measured"] if it["measured"] is not None else "—"
            print(f'{it["status"]:5} {it["id"]:>3}  {it["name"] or "":40} limit {it["limit"]:>10}  measured {ms}')
        print(f"\nизмерено: {measured_n}/{len(rows)}; FAIL: {fails}; gate: {'PASS' if fails == 0 and measured_n else ('SKIP' if not measured_n else 'FAIL')}")
    if strict and fails: return 1
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
