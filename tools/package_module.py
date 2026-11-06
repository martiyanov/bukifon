#!/usr/bin/env python3
"""Module SDK v0.2 packaging/check tool.

Usage:
  python3 firmware/tools/package_module.py firmware/modules/examples/mod_tape_delay --check
  python3 firmware/tools/package_module.py path/to/module [--out dist/modules]

Manifest: bukifon.module.v2 (schema/id/name/version/api/author/abi/permissions/
params/dsp/size/sha256).  --check verifies the manifest and that size/sha256
match the DSP entry without writing anything.
"""
import argparse, hashlib, json, os, re, sys, zipfile

SCHEMA = "bukifon.module.v2"
API_MAJOR, API_MINOR = 0, 2
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
PERMS = {"audio", "params", "seq", "io"}


def fail(msg):
    print("FAIL:", msg)
    return 1


def validate(path):
    manifest_path = os.path.join(path, "module.json")
    if not os.path.isfile(manifest_path):
        return ["module.json missing"]
    try:
        m = json.load(open(manifest_path, encoding="utf-8"))
    except Exception as e:
        return [f"module.json not valid JSON: {e}"]
    errors = []
    for key in ("schema", "id", "name", "version", "api", "author", "abi",
                "permissions", "params", "dsp", "size", "sha256"):
        if key not in m:
            errors.append(f"missing {key}")
    if m.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if not ID.match(str(m.get("id", ""))):
        errors.append("id must match [a-z0-9._-]{3,63}")
    if not SEMVER.match(str(m.get("version", ""))):
        errors.append("version must be SemVer x.y.z")
    api = str(m.get("api", ""))
    if not SEMVER.match(api):
        errors.append("api must be SemVer x.y.z")
    else:
        major, minor, _ = [int(v) for v in api.split(".")]
        if major != API_MAJOR or minor > API_MINOR:
            errors.append(f"api {api} incompatible with host {API_MAJOR}.{API_MINOR}")
    if m.get("abi") not in ("host", "p4", "s3", "any"):
        errors.append("abi must be host/p4/s3/any")
    perms = m.get("permissions", [])
    if not isinstance(perms, list) or not perms or set(perms) - PERMS:
        errors.append(f"permissions must be a non-empty subset of {sorted(PERMS)}")
    params = m.get("params", [])
    if not (1 <= len(params) <= 16):
        errors.append("params must contain 1..16 entries")
    ids = [p.get("id") for p in params]
    if len(ids) != len(set(ids)):
        errors.append("duplicate param id")
    for p in params:
        if not all(k in p for k in ("id", "name", "min", "max", "default")):
            errors.append(f"param {p.get('id', '?')} missing id/name/min/max/default")
        elif not (p["min"] <= p["default"] <= p["max"]):
            errors.append(f"param {p.get('id')} default outside min..max")
    dsp = m.get("dsp")
    if dsp and not os.path.isfile(os.path.join(path, dsp)):
        errors.append(f"dsp file not found: {dsp}")
    if dsp and os.path.isfile(os.path.join(path, dsp)):
        data = open(os.path.join(path, dsp), "rb").read()
        if m.get("size") != len(data):
            errors.append(f"size mismatch: {m.get('size')} != {len(data)}")
        sha = hashlib.sha256(data).hexdigest()
        if str(m.get("sha256", "")).lower() != sha:
            errors.append(f"sha256 mismatch: manifest {m.get('sha256')} != payload {sha}")
    for required in ("README.md", "LICENSE"):
        if not os.path.isfile(os.path.join(path, required)):
            errors.append(f"{required} missing")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default="dist/modules")
    args = ap.parse_args()
    path = os.path.abspath(args.path)
    errors = validate(path)
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    m = json.load(open(os.path.join(path, "module.json"), encoding="utf-8"))
    if args.check:
        print(f"OK: {m['id']} {m['version']} api {m['api']} abi {m['abi']} "
              f"sha256 {m['sha256'][:16]}…")
        return 0
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    base = f"{m['id']}-{m['version']}"
    zpath = os.path.join(out, base + ".zip")
    files = []
    for root, _, names in os.walk(path):
        for name in sorted(names):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, path)
            data = open(full, "rb").read()
            files.append((rel, hashlib.sha256(data).hexdigest(), len(data)))
    package = {"schema": "bukifon.module.package.v2", "manifest": m,
               "files": [{"path": p, "sha256": h, "size": s} for p, h, s in files],
               "created_by": "firmware/tools/package_module.py"}
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, _, _ in files:
            z.write(os.path.join(path, rel), rel)
        z.writestr("module.package.json", json.dumps(package, indent=2, ensure_ascii=False))
    print(f"OK: {zpath} ({os.path.getsize(zpath)} B, {len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
