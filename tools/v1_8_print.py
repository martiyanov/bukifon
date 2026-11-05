#!/usr/bin/env python3
"""Букифон v1.8 — чертёж панели 1:1 (PDF, A4 альбомная, 2 листа с перекрытием)
+ лист с таблицей координат. Геометрия — spec/panel-spec-v1.8.json (= handoff v0.3).
"""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "spec", "panel-spec-v1.8.json")))
PW, PH = SPEC["panel"]["w"], SPEC["panel"]["h"]
OUT = os.path.join(ROOT, "renders", "templates")
A4W, A4H = 297.0, 210.0
SEAM = SPEC["seam_s"]


def draw(ax, ox, oy, detail=True):
    ax.add_patch(mp.Rectangle((ox, oy), PW, PH, fill=False, ec="#111", lw=1.2))
    kb = SPEC["keyboard"]
    cl = kb["window_clearance"]
    for k in kb["keys_42"]:
        w = kb["keycap"]["w"] + 2 * cl
        h = kb["keycap"]["h"] + 2 * cl
        # Rectangle с поворотом (углы R1.5 — см. примечание на листе координат)
        ax.add_patch(mp.Rectangle(
            (ox + k["x"] - w / 2, oy + k["y"] - h / 2), w, h,
            angle=k["angle_deg"], rotation_point=(ox + k["x"], oy + k["y"]),
            fill=False, ec="#0a58ca", lw=0.8))
    for j in SPEC["jacks"]:
        ax.add_patch(mp.Circle((ox + j["x"], oy + j["y"]), j["hole"] / 2,
                               fill=False, ec="#0a58ca", lw=0.8))
    for k in SPEC["knobs"]:
        ax.add_patch(mp.Circle((ox + k["x"], oy + k["y"]), 7.2 / 2,
                               fill=False, ec="#0a58ca", lw=0.8))
        ax.add_patch(mp.Circle((ox + k["x"], oy + k["y"]), k["d"] / 2,
                               fill=False, ec="#999", lw=0.4, ls=(0, (2, 2))))
    s = SPEC["screen"]
    ax.add_patch(mp.FancyBboxPatch((ox + s["x"], oy + s["y"]), s["w"], s["h"],
                                   boxstyle="round,pad=0,rounding_size=1.2",
                                   fill=False, ec="#0a58ca", lw=1.0))
    for f in SPEC["faders"]:
        ax.add_patch(mp.FancyBboxPatch(
            (ox + f["x"] - f["slot_w"] / 2 + 1.1, oy + f["y0"] + 1.1),
            f["slot_w"] - 2.2, f["y1"] - f["y0"] - 2.2,
            boxstyle="round,pad=1.1,rounding_size=1.1",
            fill=False, ec="#0a58ca", lw=0.8))
    if detail and SEAM:
        x1, x2, yh = SEAM["x1"], SEAM["x2"], SEAM["y_h"]
        ax.plot([ox + x1, ox + x1, ox + 190, ox + 190, ox + x2, ox + x2],
                [oy, oy + yh, oy + yh, oy + PH, oy + yh, oy],
                color="#c33", lw=0.7, ls=(0, (3, 2)))


def page(pdf, x_from, x_to, title):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))
    ax.text(A4W / 2, 10, title, ha="center", fontsize=10, fontweight="bold")
    ax.text(A4W / 2, 15.5, "Печать 100% (без масштабирования). Панель 380 × 210 × 3 мм. "
                           "Синее = сквозные вырезы; красный пунктир = швы 3 деталей.",
            ha="center", fontsize=6, color="#555")
    ox, oy = 8.0, 24.0
    show = x_to - x_from
    draw(ax, ox - x_from, oy)
    clip = mp.Rectangle((ox, oy), show, PH, transform=ax.transData)
    for art in list(ax.get_children()):
        try:
            art.set_clip_on(True)
            art.set_clip_path(clip)
        except Exception:
            pass
    ax.add_patch(mp.Rectangle((ox, oy), show, PH, fc="none", ec="#c33", lw=0.6,
                              ls=(0, (2, 2))))
    ax.annotate("", xy=(ox, oy + PH + 4), xytext=(ox + show, oy + PH + 4),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.7))
    ax.text(ox + show / 2, oy + PH + 5, f"X {x_from:.0f}…{x_to:.0f} мм", ha="center",
            va="top", fontsize=6.5, color="#666")
    ax.plot([ox + 4, ox + 54], [oy + PH + 10, oy + PH + 10], color="#111", lw=1.5)
    for t in (0, 25, 50):
        ax.plot([ox + 4 + t, ox + 4 + t], [oy + PH + 8.5, oy + PH + 11.5], color="#111", lw=0.8)
    ax.text(ox + 29, oy + PH + 12.3, "50 мм — проверка масштаба", ha="center", va="top",
            fontsize=6, color="#333")
    pdf.savefig(fig)
    plt.close(fig)


def table_page(pdf):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.axis("off")
    ax.text(A4W / 2, 10, "Букифон v1.8 — координаты элементов (мм, Y от верхней кромки)",
            ha="center", fontsize=10, fontweight="bold")
    rows = []
    s = SPEC["screen"]
    rows.append(("LCD", "вырез 108.0 × 64.8", f"X {s['x']:.1f}…{s['x']+s['w']:.1f}",
                 f"Y {s['y']:.1f}…{s['y']+s['h']:.1f}", "0°"))
    for i, j in enumerate(SPEC["jacks"], 1):
        rows.append((f"J{i:02d}", "джек 3.5 Ø6.0", f"X {j['x']:.1f}", f"Y {j['y']:.1f}", "—"))
    for k in SPEC["knobs"]:
        rows.append((f"ENC", f"вал Ø7.2 / ручка Ø14", f"X {k['x']:.1f}",
                     f"Y {k['y']:.1f}", "—"))
    for i, f in enumerate(SPEC["faders"], 1):
        rows.append((f"F{i}", f"паз {f['slot_w']:.1f} × {f['y1']-f['y0']:.0f}",
                     f"X {f['x']:.1f}", f"Y {f['y0']:.1f}…{f['y1']:.1f}", "0°"))
    kb = SPEC["keyboard"]
    for k in kb["keys_42"]:
        rows.append((k["id"], f"окно 19.5 × 18.5 R1.5", f"X {k['x']:.1f}",
                     f"Y {k['y']:.1f}", f"{k['angle_deg']:+.1f}°"))
    y = 22
    for r in rows:
        ax.text(12, y, r[0], fontsize=5.2, family="monospace")
        ax.text(34, y, r[1], fontsize=5.2, family="monospace")
        ax.text(86, y, r[2], fontsize=5.2, family="monospace")
        ax.text(120, y, r[3], fontsize=5.2, family="monospace")
        ax.text(160, y, r[4], fontsize=5.2, family="monospace")
        y += 3.05
        if y > A4H - 10:
            y = 22
    ax.text(A4W / 2, A4H - 6,
            f"Источник: handoff v0.3 (фото-реконструкция ±1–2 мм); до производства — "
            f"импорт KiCad Lapka-42. Швы панели: шапка X {SEAM['x1']}…{SEAM['x2']} до "
            f"Y {SEAM['y_h']}, ниже X=190.", ha="center", fontsize=5.5, color="#555")
    pdf.savefig(fig)
    plt.close(fig)


def main():
    path = os.path.join(OUT, "bukifon_v1_8_panel_1to1.pdf")
    with PdfPages(path) as pdf:
        page(pdf, 0.0, 190.0, "Букифон v1.8 · панель 1:1 · лист 1 (X 0…190 мм)")
        page(pdf, 180.0, 380.0, "Букифон v1.8 · панель 1:1 · лист 2 (X 180…380 мм)")
        table_page(pdf)
    print("saved:", path)


if __name__ == "__main__":
    main()
