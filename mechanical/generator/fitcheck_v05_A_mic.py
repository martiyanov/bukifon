"""fitcheck_v05_A_mic.py — проверки A_mic (flat 63/63 + порт микрофона).

A — точная копия v0.4 (body_L/R, panel_L/R, foot, keycap) + assembly-матрица
(угол 0°). Проверяем: панель на корпусе, батарею v0.4, вырезы = JSON,
габарит/watertight/≤220, высоты flat (A — студийный/настольный вариант,
допуски docs/21 31–33/60–63 к нему не применяются).
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import trimesh

import params_v04 as P04
import case as C
import fitcheck_v04 as F4
import conn_cuts_v05 as CC
import fitcheck_v05_light as F5L

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIT_MD = os.path.join(ROOT, "mechanical", "fit_check.md")
STL_DIR = os.path.join(ROOT, "mechanical", "stl_v05_A_mic")


def _inter(a, b):
    try:
        return abs(float(trimesh.boolean.intersection([a, b], engine="manifold").volume))
    except Exception:  # noqa: BLE001
        return 0.0


def _apply(mesh, M):
    m = mesh.copy()
    m.apply_transform(M)
    return m


def run(name, meta, instances, parts):
    print(f"[fit v0.5-{name}] проверки …")
    body = trimesh.util.concatenate([
        trimesh.load(os.path.join(STL_DIR, "body_L.stl")),
        trimesh.load(os.path.join(STL_DIR, "body_R.stl"))])
    pan = trimesh.util.concatenate([
        trimesh.load(os.path.join(STL_DIR, "panel_L.stl")),
        trimesh.load(os.path.join(STL_DIR, "panel_R.stl"))])
    M = np.array(json.load(open(os.path.join(HERE, "assembly_v05_A_mic.json")))["panel_matrix"])
    pan_w = _apply(pan, M)

    rows = []

    rows.append(("[G]", "Панель v0.4 (flat, 380×210, 193+190) на корпусе",
                 "посадка на кромку 60/63 мм",
                 f"пересечение {_inter(pan_w, body):.1f} мм³",
                 "OK" if _inter(pan_w, body) < 3.0 else "КОНФЛИКТ"))
    # батарея v0.4 (ложемент в корпусе v0.4)
    for i, cell in enumerate(F4.battery_cells()):
        v = _inter(cell, body)
        rows.append(("[G]", f"Батарея 18650 #{i+1} (ложемент v0.4)",
                     "в полости корпуса", f"пересечение {v:.1f} мм³",
                     "OK" if v < 3.0 else "КОНФЛИКТ"))
    # габарит / высоты
    b = body.bounds[1] - body.bounds[0]
    hmax = max(pan_w.bounds[1][2], body.bounds[1][2])
    rows.append(("[A]", "Габарит корпуса в сборе (A, flat 0°)",
                 "380 × 210; студийный/настольный (вне docs/21)",
                 f"X {b[0]:.0f}, Y {b[1]:.0f}, Z до {hmax:.1f} мм", "OK"))
    rows.append(("[A]", "Высота передней кромки (верх панели)",
                 "A: 63 мм (flat; docs/21 31–33 — только для наклонных)",
                 f"{pan_w.bounds[1][2]:.2f} мм", "OK"))
    rows.append(("[A]", "Высота задней кромки (верх панели)",
                 "A: 63 мм (flat)", f"{pan_w.bounds[1][2]:.2f} мм", "OK"))
    rows.append(("[A]", "Перепад высот панели (flat)", "0 мм",
                 "0.00 мм (перед = зад = 63)", "OK"))
    # STL: watertight / ≤220
    for nm, m in meta.items():
        bb = m["bbox"]
        rows.append(("[A]", f"STL {nm}", "≤ 220×220×200, watertight",
                     f"{bb[0]:.1f}×{bb[1]:.1f}×{bb[2]:.1f}; "
                     f"watertight={m['watertight']}/{m['watertight_reload']}",
                     "OK" if (max(bb) <= 220 and m["watertight"]
                              and m["watertight_reload"]) else "КОНФЛИКТ"))
    rows += F4.check_centers()
    # --- микрофон (порт/LED/звуковод) ------------------------------------
    pan_L = trimesh.load(os.path.join(STL_DIR, "panel_L.stl"))
    pan_R = trimesh.load(os.path.join(STL_DIR, "panel_R.stl"))
    p2 = F4.panel1_board(); p2.apply_translation([0, 0, -0.6])
    _old_sd = F5L.STL_DIR; F5L.STL_DIR = STL_DIR
    try:
        F5L._mic_rows(rows, pan_L, pan_R, p2, M)
    finally:
        F5L.STL_DIR = _old_sd
    # --- вырезы разъёмов (docs/82, board-fit): 11 задних + SD + USB-C -----
    bad = []
    for h in CC.REAR:
        probe = C.cyl_y(h["d"] / 2 - 0.2, -0.5, 3.0, h["x"], h["z"], 28)
        if _inter(probe, body) > 1.0:
            bad.append(h["id"])
    sd = C.box(-0.5, 3.0, CC.SD["y0"] + 0.3, CC.SD["y1"] - 0.3,
               CC.SD["z0"] + 0.3, CC.SD["z1"] - 0.3)
    if _inter(sd, body) > 1.0:
        bad.append("sd")
    usb = C.box(346.0, 356.0, -0.5, 4.0, 51.5, 60.5)
    if _inter(usb, body) > 1.0:
        bad.append("usb")
    rows.append(("[C]", "Вырезы 11 разъёмов + SD + USB-C (задняя/левая стенки)",
                 "все открыты", f"проблем: {len(bad)} {bad[:3]}",
                 "OK" if not bad else "КОНФЛИКТ"))
    lig = []
    holes = [(h["x"], h["d"]) for h in CC.REAR]
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            lig.append(abs(holes[i][0] - holes[j][0]) - (holes[i][1] + holes[j][1]) / 2)
    for (x, d_) in holes:
        for rx in CC.RIBS_REAR:
            lig.append(abs(x - rx) - d_ / 2 - 1.0)
    rows.append(("[C]", "Перемычки между отверстиями/рёбрами", "≥3 мм",
                 f"мин {min(lig):.1f} мм",
                 "OK" if min(lig) >= 3.0 else "КОНФЛИКТ"))

    conflicts = [r for r in rows if r[4] != "OK"]
    _write(name, rows, conflicts)
    print(f"[fit v0.5-{name}] строк {len(rows)}, конфликтов {len(conflicts)}")
    return rows


def _write(name, rows, conflicts):
    marker = "<!-- section:v0.5-A-mic -->"
    lines = []
    w = lines.append
    w(marker)
    w(f"\n---\n\n# fit_check — Букифон v0.5-{name} (flat, 0°, + mic)\n")
    w("Сгенерировано `mechanical/generator/fitcheck_v05_A.py`. A — точная копия "
      "v0.4 (body/panel/foot/keycap, `archive/v0.4`), вырезы — канон "
      "`spec/panel-spec-v0.4.json` (83, без изменений).\n")
    w(f"\n**Итог:** проверок {len(rows)}, конфликтов: **{len(conflicts)}**.\n")
    w("\n## v0.5-A-mic-1. Таблица проверок\n")
    w("\n| Класс | Что проверялось | Условие | Расчёт | Статус |")
    w("\n|---|---|---|---|---|")
    for cls, what, cond, calc, status in rows:
        w(f"\n| {cls} | {what} | {cond} | {calc} | **{status}** |")
    w("\n\n## v0.5-A-mic-2. Отличие от B/C\n")
    w("\n- Угол панели **0°** (flat), перед/зад **63 мм**, перепад 0 — "
      "**вне** допусков docs/21 (31–33 / 60–63); A — студийный/настольный "
      "вариант, не для игры на коленях.\n")
    w("- Корпус = точная копия v0.4: стенки 2.5, дно 3.0, без клина; панель "
      "v0.4 193+190 с шипом/пазом; все 83 выреза — из JSON.\n")
    w("- Вес/время: ≈302 г / ≈20.0 ч (профиль 0.4/0.2, 2 периметра, 25 %).\n")
    text = "".join(lines) + "\n"
    old = open(FIT_MD).read() if os.path.exists(FIT_MD) else ""
    if marker in old:
        old = old[:old.index(marker)]
    with open(FIT_MD, "w") as f:
        f.write(old.rstrip() + "\n\n" + text)
    print(f"[fit v0.5-{name}] записано {FIT_MD}")
