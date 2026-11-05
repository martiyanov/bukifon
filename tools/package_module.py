#!/usr/bin/env python3
"""Упаковка модуля Букифона: манифест, SPDX-заголовок, проверки, zip.

Использование:
  python3 tools/package_module.py modules/examples/gain_fx --version 0.2.0 --out dist/modules
  python3 tools/package_module.py modules/examples/lfo_module --version 0.1.0
"""
import argparse, hashlib, json, os, re, subprocess, sys, zipfile

REQUIRED = ["module.json", "README.md"]
OPTIONAL_LICENSE = ["LICENSE", "LICENSE.md", "COPYING"]

def fail(msg):
    print("FAIL:", msg); sys.exit(1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path"); ap.add_argument("--version", required=True)
    ap.add_argument("--out", default="dist/modules"); ap.add_argument("--allow-missing-license", action="store_true")
    a = ap.parse_args()
    d = os.path.abspath(a.path)
    if not os.path.isdir(d): fail(f"нет каталога {d}")
    for f in REQUIRED:
        if not os.path.isfile(os.path.join(d, f)): fail(f"нет {f} в {d}")
    m = json.load(open(os.path.join(d, "module.json"), encoding="utf-8"))
    for k in ("schema", "id", "name", "version", "abi", "author", "description"):
        if k not in m: fail(f"module.json: нет поля {k}")
    if m["schema"] != "bukifon.module.v1": fail("schema должен быть bukifon.module.v1")
    if not re.fullmatch(r"\d+\.\d+\.\d+", a.version): fail("--version должен быть semver X.Y.Z")
    if not isinstance(m["abi"], int) or m["abi"] < 0: fail("abi должен быть целым >=0")
    if not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", m["id"]): print("WARN: id лучше vendor.name")
    for f in m.get("files", []):
        if not os.path.isfile(os.path.join(d, f)): print("WARN: files[] ссылается на отсутствующий", f)

    # SPDX в исходниках C/C++/Lua
    spdx = ["// SPDX-License-Identifier: " + m.get("license", "MIT")]
    missing_spdx = []
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith((".c", ".cpp", ".h", ".hpp", ".lua")):
                p = os.path.join(root, f)
                head = open(p, encoding="utf-8", errors="ignore").read(400)
                if "SPDX-License-Identifier" not in head: missing_spdx.append(os.path.relpath(p, d))
    if missing_spdx: print("WARN: нет SPDX-заголовка:", ", ".join(missing_spdx))

    lic = next((f for f in OPTIONAL_LICENSE if os.path.isfile(os.path.join(d, f))), None)
    if not lic and not a.allow_missing_license:
        print("WARN: нет LICENSE-файла (используйте --allow-missing-license, если это шаблон)")

    # контрольный список
    files = []
    for root, _, fs in os.walk(d):
        for f in sorted(fs):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, d)
            files.append((rel, hashlib.sha256(open(p, "rb").read()).hexdigest(), os.path.getsize(p)))
    files.sort()
    manifest = {
        "schema": "bukifon.module.package.v1", "id": m["id"], "name": m["name"],
        "version": a.version, "abi": m["abi"], "author": m.get("author"),
        "license": m.get("license", "MIT"), "description": m.get("description"),
        "created_by": "tools/package_module.py", "files": [{"path": p, "sha256": h, "size": s} for p, h, s in files],
    }
    os.makedirs(a.out, exist_ok=True)
    base = f"{m['id']}-{a.version}"
    zpath = os.path.join(a.out, base + ".zip")
    with open(os.path.join(d, "module.manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, _, _ in files: z.write(os.path.join(d, rel), rel)
        z.write(os.path.join(d, "module.manifest.json"), "module.manifest.json")
    print(f"OK: {zpath} ({os.path.getsize(zpath)} B, {len(files)} файлов)")
    print("manifest:", os.path.join(d, "module.manifest.json"))
    if missing_spdx: print("предупреждение: SPDX добавьте перед публикацией:", ", ".join(missing_spdx))

if __name__ == "__main__": main()
