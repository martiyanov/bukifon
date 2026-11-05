#!/usr/bin/env python3
"""Букифон v1.8 — раскладка панели строго по handoff заказчика v0.3.

Источник геометрии (единственный): refs/v03_handoff/bukifon_layout_v03.json
(фото-реконструкция ±1–2 мм; провизор для производства до импорта KiCad Lapka-42).

Система координат v0.3 = наша: X вправо, Y вниз от верхней (задней) кромки,
положительный угол — по часовой на виде сверху (поворот колпачка вокруг центра).

Выход:
  spec/panel-spec-v1.8.json            — нормализованная спецификация (для case-генератора)
  renders/templates/bukifon_v1_8_full.png     — вид сверху
  renders/v1_8_layout_report.txt       — проверки + отклонения от KiCad-Lapka
  renders/templates/bukifon_v1_8_overlay.png — наложение на эталонный PNG (IoU)
"""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from shapely.geometry import Point, Polygon, box as Box
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V03 = json.load(open(os.path.join(ROOT, "refs", "v03_handoff", "bukifon_layout_v03.json")))
C = V03["controls"]

PW = V03["panel"]["width_mm"]      # 380
PH = V03["panel"]["height_mm"]     # 210
PT = V03["panel"]["front_panel_thickness_mm"]

CAP_W, CAP_H = 17.5, 16.5
WIN_CLEAR = 1.0                    # окно = колпачок + 1 мм (макетный вариант)

lcd = C["lcd"]["active_cutout"]
SCREEN = dict(x=lcd["center_mm"][0] - lcd["opening_size_mm"][0] / 2,
              y=lcd["center_mm"][1] - lcd["opening_size_mm"][1] / 2,
              w=lcd["opening_size_mm"][0], h=lcd["opening_size_mm"][1])
JACKS = [(j["center_mm"][0], j["center_mm"][1], j["panel_hole_diameter_mm"])
         for j in C["jacks"]]
KNOBS = []
for grp in ("encoders_left", "encoders_right"):
    for e in C[grp]:
        KNOBS.append((e["center_mm"][0], e["center_mm"][1], e["knob_outer_diameter_mm"]))
FADERS = [(f["slot"]["center_mm"][0],
           f["slot"]["center_mm"][1] - f["slot"]["slot_size_mm"][1] / 2,
           f["slot"]["center_mm"][1] + f["slot"]["slot_size_mm"][1] / 2,
           f["slot"]["slot_size_mm"][0],
           f["rear_envelope"]["rear_envelope_size_mm"][0],
           f["rear_envelope"]["rear_envelope_size_mm"][1])
          for f in C["faders"]]
KEYS = [dict(x=k["center_mm"][0], y=k["center_mm"][1], angle=k["angle_deg"],
             half="L" if k["id"].startswith("L") else "R", id=k["id"])
        for grp in ("keyboard_left", "keyboard_right") for k in C[grp]]


def cap_poly(x, y, ang, grow=0.0, w=CAP_W, h=CAP_H):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    hw, hh = w / 2 + grow, h / 2 + grow
    pts = [(x + ca * sx * hw - sa * sy * hh, y + sa * sx * hw + ca * sy * hh)
           for sx in (-1, 1) for sy in (-1, 1)]
    return Polygon(pts).convex_hull


def main():
    rep = []
    w = rep.append
    wins = [cap_poly(k["x"], k["y"], k["angle"], WIN_CLEAR) for k in KEYS]
    uKB = unary_union(wins)
    screen = Box(SCREEN["x"], SCREEN["y"], SCREEN["x"] + SCREEN["w"], SCREEN["y"] + SCREEN["h"])
    jacks_g = unary_union([Point(x, y).buffer(d / 2 + 2.0) for x, y, d in JACKS])
    knobs_g = unary_union([Point(x, y).buffer(d / 2 + 1.0) for x, y, d in KNOBS])
    fad_slots = [Box(f[0] - f[3] / 2 - 1, f[1] - 1, f[0] + f[3] / 2 + 1, f[2] + 1)
                 for f in FADERS]
    fad_env = unary_union([Box(f[0] - f[4] / 2, f[1], f[0] + f[4] / 2, f[2])
                           for f in FADERS])
    panel = Box(0, 0, PW, PH)

    w("Букифон v1.8 = раскладка handoff v0.3 (источник: bukifon_layout_v03.json)")
    w("=" * 74)
    w("панель %.0f × %.0f × %.0f; экран вырез %.1f × %.1f центр (%.1f, %.1f)"
      % (PW, PH, PT, SCREEN["w"], SCREEN["h"], lcd["center_mm"][0], lcd["center_mm"][1]))
    w("джеки: %d шт., Y=%.1f, X %.1f…%.1f (шаг 11)"
      % (len(JACKS), JACKS[0][1], JACKS[0][0], JACKS[-1][0]))
    w("энкодеры: %d шт., Y %s" % (len(KNOBS), sorted({y for _, y, _ in KNOBS})))
    w("фейдеры: X %s, паз %.1f × %.0f, Y %.1f…%.1f"
      % ([f[0] for f in FADERS], FADERS[0][3], FADERS[0][2] - FADERS[0][1],
         FADERS[0][1], FADERS[0][2]))
    for s in ("L", "R"):
        ks = [k for k in KEYS if k["half"] == s]
        xs = [k["x"] for k in ks]; ys = [k["y"] for k in ks]
        w("клавиатура %s: центры X %.1f…%.1f, Y %.1f…%.1f (21 клавиша, углы %.0f…%.0f°)"
          % (s, min(xs), max(xs), min(ys), max(ys),
             min(k["angle"] for k in ks), max(k["angle"] for k in ks)))
    w("")

    fails = []

    def check(name, a, b, min_gap=0.0):
        d = a.distance(b)
        ok = d >= min_gap
        if not ok:
            fails.append(name)
        w("  %-46s зазор %6.2f  %s" % (name, d, "✔" if ok else "✘"))

    w("[Проверки]")
    check("джеки ↔ экран", jacks_g, screen)
    check("джеки ↔ кромка Y=0", jacks_g, Box(0, -99, PW, 0))
    check("джеки ↔ ручки", jacks_g, knobs_g)
    check("ручки ↔ экран", knobs_g, screen)
    check("клавиши L ↔ R", unary_union([p for p, k in zip(wins, KEYS) if k["half"] == "L"]),
          unary_union([p for p, k in zip(wins, KEYS) if k["half"] == "R"]), 2.0)
    check("клавиши ↔ ручки", uKB, knobs_g, 2.0)
    check("клавиши ↔ экран (корпус LCD 120.7×75.8 не считаем)", uKB, screen, 1.0)
    lcd_body = Box(190 - 60.35, 61.4 - 37.9, 190 + 60.35, 61.4 + 37.9)
    d = uKB.distance(lcd_body)
    w("  %-46s зазор %6.2f  %s (по handoff ≥ ~3.9)"
      % ("клавиши ↔ корпус LCD сзади", d, "✔" if d >= 0 else "✘"))
    for i, fs in enumerate(fad_slots):
        check(f"клавиши ↔ паз фейдера F{i+1}", uKB, fs, 1.0)
    off = [k for k, p in zip(KEYS, wins) if not panel.contains(p)]
    w("  %-46s %s" % ("окна внутри панели", "✔" if not off else "✘ %s" % [k['id'] for k in off]))
    if off:
        fails.append("окна за краем")
    w("")

    # --- позиции швов и стоек (для case-генератора) --------------------------
    # Схема v1.8: «шапка» X1..X2 до Y_H (джеки+экран), ниже — Т-образные
    # левая/правая детали, вертикальный шов X=190 (между фейдерами).
    # Требуем ≥2.5 мм от окон/гайки джеков (гайка Ø10).
    jacks_nut = unary_union([Point(x, y).buffer(5.0 + 1.0) for x, y, d in JACKS])

    def seam_ok(x1, x2, yh):
        v1 = Box(x1 - 1.5, 0, x1 + 1.5, yh)          # левый край шапки
        v2 = Box(x2 - 1.5, 0, x2 + 1.5, yh)          # правый край шапки
        h1 = Box(x1 - 1.5, yh - 1.5, 190, yh + 1.5)  # горизонталь L
        h2 = Box(190, yh - 1.5, x2 + 1.5, yh + 1.5)  # горизонталь R
        v3 = Box(190 - 1.5, yh, 190 + 1.5, PH)       # низ по центру
        zone = unary_union([v1, v2, h1, h2, v3])
        # корпус фейдера ПОД панелью — шву не мешает; важны только сквозные
        obst = [screen, jacks_nut, knobs_g] + fad_slots + wins
        return all(zone.distance(p) >= 1.75 for p in obst), zone

    seam = None
    for yh in (98.0, 97.5, 98.5, 99, 96.5):
        for x1 in (131.2, 131.0, 131.4, 130.8):
            for x2 in (249.1, 248.9, 249.3):
                ok, _ = seam_ok(x1, x2, yh)
                if ok:
                    seam = (x1, x2, yh)
                    break
            if seam:
                break
        if seam:
            break
    w("[Шов панели v1.8] шапка X %.1f…%.1f до Y=%.1f; ниже — шов X=190: %s"
      % (seam[0] if seam else 0, seam[1] if seam else 0, seam[2] if seam else 0,
         "найден, ≥1.75 мм от окон/гаек ✔" if seam else "✘ не найден"))
    if seam is None:
        fails.append("seam")
    w("")

    # --- нормализованный spec (формат case-генератора) ------------------------
    spec = {
        "project": "Bukifon (Букифон)", "variant": "v1.8",
        "source": "refs/v03_handoff/bukifon_layout_v03.json (заказчик, фото-реконструкция)",
        "panel": {"w": PW, "h": PH, "thickness": PT, "units": "mm",
                  "origin": "x right, y down from rear edge; angle CW+ on top view"},
        "screen": {"x": SCREEN["x"], "y": SCREEN["y"], "w": SCREEN["w"], "h": SCREEN["h"],
                   "module_envelope": [120.7, 75.8]},
        "jacks": [{"x": x, "y": y, "type": "3.5mm", "hole": d} for x, y, d in JACKS],
        "faders": [{"x": f[0], "y0": f[1], "y1": f[2], "slot_w": f[3],
                    "env_w": f[4], "env_h": f[5]} for f in FADERS],
        "knobs": [dict(x=x, y=y, d=d) for x, y, d in KNOBS],
        "keyboard": {
            "model": "по handoff v0.3 (фото-реконструкция, ±1–2 мм, НЕ KiCad Lapka)",
            "keycap": {"w": CAP_W, "h": CAP_H},
            "window_clearance": WIN_CLEAR,
            "keys_42": [dict(x=k["x"], y=k["y"], angle_deg=k["angle"],
                             half=k["half"], id=k["id"]) for k in KEYS],
        },
        "seam_s": {"x1": seam[0], "x2": seam[1], "y_h": seam[2]} if seam else {},
        "notes": [
            "Экран без рамки, вырез = активная область",
            "Динамиков нет, разъёмов под экраном нет",
            "Углы клавиш — из handoff v0.3 (фото): до импорта KiCad Lapka-42",
            "окна = колпачок + 1 мм (макетная панель для проверки эргономики)",
        ],
    }
    with open(os.path.join(ROOT, "spec", "panel-spec-v1.8.json"), "w") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)

    # --- вид сверху + наложение на эталон -------------------------------------
    fig, ax = plt.subplots(figsize=(13.4, 7.6), dpi=160)
    ax.set_xlim(-8, PW + 8)
    ax.set_ylim(PH + 8, -10)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0, 0), PW, PH, boxstyle="round,pad=0,rounding_size=4",
                                   fc="#f8f8f5", ec="#222", lw=1.8))
    for gx in range(0, int(PW) + 1, 10):
        ax.plot([gx, gx], [0, PH], color="#eeeee9", lw=0.25)
    for gy in range(0, int(PH) + 1, 10):
        ax.plot([0, PW], [gy, gy], color="#eeeee9", lw=0.25)
    for (x, y, d) in KNOBS:
        ax.add_patch(mp.Circle((x, y), d / 2, fc="#ececec", ec="#333", lw=1.0, zorder=4))
        ax.plot([x, x], [y + 2.2, y + 6.4], color="#0a0", lw=1.2, zorder=5)
    ax.add_patch(mp.FancyBboxPatch((SCREEN["x"], SCREEN["y"]), SCREEN["w"], SCREEN["h"],
                                   boxstyle="round,pad=0,rounding_size=1.2",
                                   fc="#101a10", ec="#333", lw=0.8, zorder=4))
    ax.text(190, 61.4, "5.0″ 800×480\nвырез 108 × 64.8", ha="center", va="center",
            fontsize=6.5, color="#7fae7f", zorder=5)
    for (x, y, d) in JACKS:
        ax.add_patch(mp.Circle((x, y), d / 2, fc="#e9e9e4", ec="#333", lw=0.7, zorder=4))
    for f in FADERS:
        ax.add_patch(mp.Rectangle((f[0] - f[3] / 2, f[1]), f[3], f[2] - f[1],
                                  fc="#dcdcdc", ec="#444", lw=0.8, zorder=4))
        ax.add_patch(mp.Rectangle((f[0] - 8, 149 - 5), 16, 10, fc="#333",
                                  ec="#111", lw=0.5, zorder=5))
    for k in KEYS:
        ax.add_patch(mp.Rectangle((k["x"] - CAP_W / 2, k["y"] - CAP_H / 2), CAP_W, CAP_H,
                                  angle=k["angle"], rotation_point="center",
                                  fc="#d8e6f7", ec="#4a6b8a", lw=0.6, zorder=6))
    if seam:
        x1, x2, yh = seam
        ax.plot([x1, x1, 190, 190, x2, x2], [0, yh, yh, PH, yh, 0],
                color="#c33", lw=1.0, ls=(0, (4, 3)), zorder=7)
    ax.set_title("Букифон v1.8 = handoff v0.3 · панель 380 × 210 · 16 ручек, экран 5″, "
                 "10 mini-jack, 2 фейдера (паз 2.5×63), 42 клавиши (углы из v0.3)",
                 fontsize=10, pad=8)
    fig.savefig(os.path.join(ROOT, "renders", "templates", "bukifon_v1_8_full.png"),
                bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # IoU наложения на эталонный PNG
    ref = Image.open(os.path.join(ROOT, "refs", "v03_handoff", "bukifon_top_view.png")).convert("L")
    rw, rh = 1100, int(1100 * PH / PW)
    ref_a = np.asarray(ref.resize((rw, rh)))
    mine = Image.open(os.path.join(ROOT, "renders", "templates", "bukifon_v1_8_full.png")).convert("L")
    # вырезаем область панели из нашего превью по рамке
    arr = np.asarray(mine)
    dark_rows = np.where((arr < 120).sum(axis=1) > 50)[0]
    dark_cols = np.where((arr < 120).sum(axis=0) > 50)[0]
    if len(dark_rows) and len(dark_cols):
        crop = mine.crop((dark_cols[0], dark_rows[0], dark_cols[-1], dark_rows[-1]))
        # рамка панели — тёмная; вырезаем внутренность с отступом 0.5%
        cw, ch = crop.size
        crop = crop.crop((int(cw * 0.005), int(ch * 0.005), int(cw * 0.995), int(ch * 0.995)))
        mine_a = np.asarray(crop.resize((rw, rh)))
        # у эталона элементы СВЕТЛЫЕ на тёмной панели, у нас — тёмные на светлой
        b_ref = ref_a > 120
        b_my = mine_a < 128
        inter = (b_ref & b_my).sum()
        union = (b_ref | b_my).sum()
        iou = inter / union
        w("IoU наложения на bukifon_top_view.png: %.3f (грубая бинарная оценка)" % iou)
        ov = Image.fromarray(((b_ref.astype(np.uint8) * 90 + b_my.astype(np.uint8) * 165)))
        ov.save(os.path.join(ROOT, "renders", "templates", "bukifon_v1_8_overlay.png"))

    w("")
    w("ИТОГ: %s" % ("ВСЁ ЧИСТО ✔" if not fails else "ОШИБКИ: %s" % fails))
    txt = "\n".join(rep)
    print(txt)
    with open(os.path.join(ROOT, "renders", "v1_8_layout_report.txt"), "w") as f:
        f.write(txt + "\n")


if __name__ == "__main__":
    main()
