#!/usr/bin/env python3
"""Bukifon — проверка целостности пакета и сводка результатов.

Запуск: /tmp/msvenv/bin/python tools/package_check.py
Проверяет наличие и содержимое артефактов, парсит ERC-отчёты, проверяет STL,
считает фильтры, выводит сводную таблицу. Возвращает 0, если всё критичное на месте.
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = True
rows = []


def row(name, status, note=""):
    global ok
    rows.append((name, status, note))
    if status.startswith("FAIL"):
        ok = False


def exists(pattern, optional=False):
    files = glob.glob(os.path.join(ROOT, pattern), recursive=True)
    return files


def check_file(rel, optional=False):
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        row(rel, "OK", f"{os.path.getsize(p) // 1024} KiB")
        return True
    row(rel, "SKIP" if optional else "FAIL", "нет файла")
    return False


# ---- spec / docs / licenses -------------------------------------------------
for f in ["README.md", "LICENSE", "NOTICE", "LICENSE-CERN-OHL-S-2.0",
          "LICENSE-GPL-3.0-or-later", "LICENSE-CC-BY-SA-4.0"]:
    check_file(f)

for f in ["spec/00-vision.md", "spec/10-panel-ui.md", "spec/20-electronics.md",
          "spec/30-mechanics.md", "spec/40-firmware.md",
          "docs/00-overview.md", "docs/01-quickstart.md", "docs/09-licensing.md",
          "docs/02-build-guide.md", "docs/BOM.md", "BOM.csv"]:
    check_file(f)

# ---- hardware schematics + ERC ---------------------------------------------
erc_patterns = [
    "hardware/core/erc/*.rpt",
    "hardware/panel/erc/*.rpt",
    "hardware/modules/erc/*.rpt",
    "hardware/power/erc/*.rpt",
]
total_err = total_warn = 0
erc_files = []
for pat in erc_patterns:
    erc_files += glob.glob(os.path.join(ROOT, pat))
if not erc_files:
    row("ERC-отчёты", "FAIL", "не найдены")
for f in erc_files:
    txt = open(f, encoding="utf-8", errors="replace").read()
    m = re.search(r"ERC messages:\s*(\d+)\s+Errors\s+(\d+)\s+Warnings\s+(\d+)", txt)
    if not m:
        continue
    e, w = int(m.group(2)), int(m.group(3))
    total_err += e
    total_warn += w
    row("ERC " + os.path.relpath(f, ROOT), "OK" if e == 0 else "FAIL", f"{e} err / {w} warn")

schematics = glob.glob(os.path.join(ROOT, "hardware/**/*.kicad_sch"), recursive=True)
row("KiCad схемы", "OK" if len(schematics) >= 8 else "FAIL", f"{len(schematics)} шт.")
pdfs = glob.glob(os.path.join(ROOT, "hardware/**/*.pdf"), recursive=True)
row("Схемы PDF", "OK" if len(pdfs) >= 8 else "FAIL", f"{len(pdfs)} шт.")
nets = glob.glob(os.path.join(ROOT, "hardware/**/*.net"), recursive=True) + \
       glob.glob(os.path.join(ROOT, "hardware/**/net/*.xml"), recursive=True)
row("Netlist", "OK" if len(nets) >= 8 else "FAIL", f"{len(nets)} шт.")
boms = glob.glob(os.path.join(ROOT, "hardware/**/BOM-*.csv"), recursive=True) + \
       glob.glob(os.path.join(ROOT, "hardware/panel/erc/*-bom.csv"), recursive=True)
row("BOM плат", "OK" if len(boms) >= 6 else "FAIL", f"{len(boms)} шт.: " +
    ", ".join(sorted(os.path.basename(b) for b in boms)))

# ---- mechanical -------------------------------------------------------------
stls = glob.glob(os.path.join(ROOT, "mechanical/stl/*.stl"))
row("STL деталей", "OK" if len(stls) >= 18 else "FAIL", f"{len(stls)} шт.")
try:
    import trimesh
    bad, total_g, max_dim = [], 0.0, 0.0
    for f in stls:
        m = trimesh.load(f, force="mesh")
        total_g += m.volume / 1000.0 * 1.27 * 0.35  # PETG, 35% infill
        d = max(m.extents)
        max_dim = max(max_dim, d)
        if not m.is_watertight:
            bad.append(os.path.basename(f))
        if d > 221:
            bad.append(os.path.basename(f) + " >220мм")
    row("STL watertight / габарит ≤220", "OK" if not bad else "FAIL",
        f"проблемы: {', '.join(bad) if bad else 'нет'}; max {max_dim:.0f} мм")
    row("Расход пластика (оценка)", "OK", f"~{total_g:.0f} г при 35% заполнении")
except Exception as exc:  # pragma: no cover
    row("STL проверка", "FAIL", str(exc))
for f in ["mechanical/prints.md", "mechanical/assembly.md", "mechanical/README.md",
          "mechanical/fit_check.md", "mechanical/generator/case.py"]:
    check_file(f)
fit = os.path.join(ROOT, "mechanical/fit_check.md")
if os.path.exists(fit):
    txt = open(fit, encoding="utf-8").read()
    m = re.search(r"конфликтов:\s*\*\*(\d+)\*\*", txt)
    row("fit_check: конфликтов", "OK" if m and int(m.group(1)) == 0 else "FAIL",
        (m.group(1) + " (должно быть 0)") if m else "не найдено")
# схема аккумулятора
check_file("hardware/power/PWR-BATT-1.pdf")
check_file("hardware/power/README.md")
check_file("mechanical/branding/bukifon_wordmark.svg")
check_file("mechanical/branding/bukifon_wordmark.png")
renders = glob.glob(os.path.join(ROOT, "mechanical/preview/*.png"))
row("Рендеры корпуса", "OK" if len(renders) >= 4 else "FAIL", f"{len(renders)} PNG")

# ---- firmware ---------------------------------------------------------------
check_file("firmware/host/Makefile")
check_file("firmware/host/build/bukifon_tests", optional=False)
check_file("firmware/tests/REPORT.md")
check_file("firmware/README.md")
check_file("firmware/Bukifon/platformio.ini")
check_file("firmware/Bukifon/Bukifon.ino")
fw_uf2 = glob.glob(os.path.join(ROOT, "firmware/artifacts/*.uf2"))
row("Прошивка RP2040 (uf2)", "OK" if fw_uf2 else "SKIP",
    f"{len(fw_uf2)} файл(ов)" if fw_uf2 else "не собиралась в этой среде — см. REPORT.md")
wavs = glob.glob(os.path.join(ROOT, "firmware/tests/out/*.wav"))
row("Тестовые WAV", "OK" if len(wavs) >= 5 else "FAIL", f"{len(wavs)} шт.")
metrics = os.path.join(ROOT, "firmware/tests/out/fft_metrics.json")
if os.path.exists(metrics):
    try:
        data = json.load(open(metrics))
        a4 = data.get("note_a4", {})
        row("FFT: A4 / алиасинг", "OK" if a4.get("pass_tuning") and a4.get("pass_aliasing") else "FAIL",
            f"{a4.get('fundamental_hz')} Гц, худший побочный {a4.get('worst_spurious_db')} дБ")
    except Exception as exc:
        row("FFT metrics", "FAIL", str(exc))
else:
    row("FFT metrics", "FAIL", "нет файла")
try:
    out = subprocess.run([os.path.join(ROOT, "firmware/host/build/bukifon_tests")],
                         capture_output=True, text=True, timeout=300)
    tail = [ln for ln in out.stdout.splitlines() if ln.startswith("tests:")]
    row("Host-тесты прошивки", "OK" if out.returncode == 0 else "FAIL",
        tail[-1] if tail else f"exit {out.returncode}")
except Exception as exc:  # pragma: no cover
    row("Host-тесты прошивки", "FAIL", str(exc))

# ---- panel layout -----------------------------------------------------------
for f in ["renders/panel_layout.png", "renders/panel_layout_keys.png",
          "renders/variantB_panel.png", "renders/v1_2_head.png",
          "renders/v1_2_deck_lapka.png", "renders/v1_2_deck_pads.png"]:
    check_file(f)

# ---- report ----------------------------------------------------------------
w = max(len(r[0]) for r in rows)
print("=" * (w + 40))
print("Bukifon — проверка пакета")
print("=" * (w + 40))
for name, status, note in rows:
    mark = {"OK": "✓", "SKIP": "–"}.get(status.split()[0], "✗")
    print(f"{mark} {name:<{w}}  {status:<10} {note}")
print("-" * (w + 40))
print(f"Итог: {'ПАКЕТ ГОТОВ' if ok else 'ЕСТЬ ПРОБЛЕМЫ'}; ERC ошибок: {total_err}, предупреждений: {total_warn}")
sys.exit(0 if ok else 1)
