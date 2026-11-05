#!/usr/bin/env python3
"""Удаляет дубликаты SVG-экспортов (одинаковое содержимое), оставляя копию в svg/."""
import hashlib, subprocess, os, re, sys

files = subprocess.run(["git","ls-files","*.svg"], capture_output=True, text=True).stdout.splitlines()
groups = {}
for f in files:
    h = hashlib.sha256(open(f,"rb").read()).hexdigest()
    groups.setdefault(h, []).append(f)

removed = []
for h, fs in groups.items():
    if len(fs) < 2: continue
    # предпочитаем путь, содержащий '/svg/'
    keep = sorted(fs, key=lambda p: ("/svg/" not in p, len(p)))[0]
    for f in fs:
        if f == keep: continue
        old = os.path.relpath(f)
        new = os.path.relpath(keep)
        # обновляем ссылки в текстовых файлах: старый путь -> новый
        subprocess.run(["git","rm","-q",f], check=False)
        if os.path.exists(f): os.remove(f)
        removed.append((f, keep))
        for p in subprocess.run(["git","ls-files","*.md","*.html","*.txt"],
                                capture_output=True, text=True).stdout.splitlines():
            s = open(p, encoding="utf-8", errors="ignore").read()
            if old in s:
                s = s.replace(old, new); open(p,"w",encoding="utf-8").write(s)
print(f"удалено дубликатов: {len(removed)}")
for a,b in removed: print("  ", a, "->", b)
