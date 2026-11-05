#!/usr/bin/env python3
"""Валидация module.json и структуры модулей Букифона (Module API v0)."""
import json, os, re, sys, hashlib

REQUIRED = {"schema","id","name","version","abi","kind","language","license","author","description","params","files","limits"}
KINDS = {"audio","control","analog"}
LANGS = {"cpp","lua"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
LIMITS = {"stack_bytes": 8192, "state_bytes": 4096, "max_frames": 64}

def check(path, seen):
    errs, warns = [], []
    mdir = os.path.dirname(path)
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"{path}: JSON не читается: {e}"], []
    missing = REQUIRED - d.keys()
    if missing: errs.append(f"нет полей: {sorted(missing)}")
    if d.get("schema") != "bukifon.module.v1": errs.append("schema должен быть bukifon.module.v1")
    if not ID.match(str(d.get("id",""))): errs.append("id: только [a-z0-9._-], 3…64")
    if not SEMVER.match(str(d.get("version",""))): errs.append("version: нужен SemVer x.y.z")
    if d.get("abi") != 0: errs.append("abi должен быть 0 (experimental)")
    if d.get("kind") not in KINDS: errs.append(f"kind ∈ {sorted(KINDS)}")
    if d.get("language") not in LANGS: errs.append(f"language ∈ {sorted(LANGS)}")
    if not d.get("license"): errs.append("license пустая")
    params = d.get("params", [])
    if not (1 <= len(params) <= 16): errs.append("params: 1…16")
    ids = [p.get("id") for p in params]
    if len(ids) != len(set(ids)): errs.append("params: повторяющиеся id")
    for p in params:
        for k in ("id","name","type","min","max","default"):
            if k not in p: errs.append(f"param {p.get('id','?')}: нет {k}")
    lim = d.get("limits", {})
    for k, mx in LIMITS.items():
        v = lim.get(k)
        if v is None: errs.append(f"limits.{k} отсутствует")
        elif v > mx: errs.append(f"limits.{k}={v} > {mx}")
    files = d.get("files", [])
    if not files: errs.append("files пустой")
    for f in files:
        if not os.path.exists(os.path.join(mdir, f)): errs.append(f"файл не найден: {f}")
    for must in ("README.md","LICENSE"):
        if not os.path.exists(os.path.join(mdir, must)): errs.append(f"нет {must}")
    if d.get("id") in seen: errs.append(f"дубликат id: {d['id']}")
    seen.add(d.get("id"))
    # эвристика: запрещённые вызовы в исходниках
    for f in files:
        fp = os.path.join(mdir, f)
        if not os.path.exists(fp) or not f.endswith((".c",".cc",".cpp",".h",".hpp",".lua")): continue
        src = open(fp, encoding="utf-8", errors="ignore").read()
        for bad in ("malloc(", "calloc(", "realloc(", "fopen(", "printf("):
            if bad in src: warns.append(f"{f}: найдено {bad} (проверить, что не в process())")
    return errs, warns

def main():
    roots = sys.argv[1:] or ["modules"]
    seen, all_errs, all_warns, n = set(), [], [], 0
    for root in roots:
        if os.path.isfile(root):
            paths = [root]
        else:
            paths = [os.path.join(dp, "module.json") for dp, _, fs in os.walk(root) if "module.json" in fs]
        for p in sorted(paths):
            n += 1
            e, w = check(p, seen)
            all_errs += e; all_warns += w
            print(("✅" if not e else "❌"), p, (f"({len(w)} warn)" if w else ""))
    for w in all_warns: print("  ⚠️ ", w)
    for e in all_errs: print("  ❌ ", e)
    print(f"\nмодулей: {n}, ошибок: {len(all_errs)}, предупреждений: {len(all_warns)}")
    return 1 if all_errs else 0

if __name__ == "__main__":
    sys.exit(main())
