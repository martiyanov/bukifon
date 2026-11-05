#!/usr/bin/env python3
"""Рендер панели Букифон из машиночитаемой спецификации (v0.3 handoff JSON).

Источник геометрии — spec/panel-spec-v0.3.json (единственный канон).
Координаты: левый верхний угол (0,0), X вправо, Y вниз, угол + = по часовой стрелке,
каждый колпачок вращается вокруг своего центра.

Выходы:
  renders/templates/bukifon_v03_panel_1to1.pdf   — 1:1, 2 листа A4 с перекрытием 10 мм
  renders/templates/bukifon_v03_template.png     — превью шаблона
  renders/templates/bukifon_v03_render.png       — «как будет выглядеть» (тёмная панель)
  renders/templates/bukifon_v03_vs_concept.png   — сравнение с концептом заказчика
  renders/templates/bukifon_v03_collisions.json  — проверка пересечений
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "spec", "panel-spec-v0.3.json")
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "bukifon_v03"
OUT = os.path.join(ROOT, "renders", "templates")
A4W, A4H = 297.0, 210.0
os.makedirs(OUT, exist_ok=True)

S = json.load(open(SPEC, encoding="utf-8"))
C = S["controls"]
PW = S["panel"]["width_mm"]
PH = S["panel"]["height_mm"]

KEYS = [dict(k, half="L") for k in C["keyboard_left"]] + \
       [dict(k, half="R") for k in C["keyboard_right"]]
ENC = C["encoders_left"] + C["encoders_right"]
JACKS = C["jacks"]
LCD = C["lcd"]["active_cutout"]
LCD_BODY = C["lcd"]["body_envelope"]
FADERS = C["faders"]


def rot_pts(cx, cy, w, h, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + ca * sx * w / 2 - sa * sy * h / 2, cy + sa * sx * w / 2 + ca * sy * h / 2)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def poly_overlap(p, q):
    """SAT для двух выпуклых многоугольников."""
    for poly in (p, q):
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            ax, ay = -(y2 - y1), x2 - x1
            pa = [ax * x + ay * y for x, y in p]
            pb = [ax * x + ay * y for x, y in q]
            if max(pa) <= min(pb) + 1e-9 or max(pb) <= min(pa) + 1e-9:
                return False
    return True


def collisions():
    caps = [(k["id"], rot_pts(*k["center_mm"], *k["size_mm"], k["angle_deg"])) for k in KEYS]
    bad = []
    for i in range(len(caps)):
        for j in range(i + 1, len(caps)):
            if poly_overlap(caps[i][1], caps[j][1]):
                bad.append([caps[i][0], caps[j][0], "key-key"])
    # колпачки vs корпуса экрана/фейдеров/ручек/джеков
    bodies = [(LCD_BODY["id"], rot_pts(*LCD_BODY["center_mm"], *LCD_BODY["rear_envelope_size_mm"], 0))]
    for f in FADERS:
        bodies.append((f["rear_envelope"]["id"],
                       rot_pts(*f["rear_envelope"]["center_mm"], *f["rear_envelope"]["rear_envelope_size_mm"], 0)))
    for kid, cpts in caps:
        for bid, bpts in bodies:
            if poly_overlap(cpts, bpts):
                bad.append([kid, bid, "key-body"])
    return bad


def draw(ax, dx, dy, style="template"):
    dark = style == "render"
    face = "#2b2b2b" if dark else "#fbfbf8"
    edge = "#111" if dark else "#222"
    ax.add_patch(mp.FancyBboxPatch((dx, dy), PW, PH, boxstyle="round,pad=0,rounding_size=6",
                                   fc=face, ec=edge, lw=1.6, zorder=0))
    if not dark:
        for gx in range(0, int(PW) + 1, 10):
            ax.plot([dx + gx, dx + gx], [dy, dy + PH], color="#ecece7", lw=0.22, zorder=1)
        for gy in range(0, int(PH) + 1, 10):
            ax.plot([dx, dx + PW], [dy + gy, dy + gy], color="#ecece7", lw=0.22, zorder=1)

    # 42 клавиши
    for k in KEYS:
        cx, cy = k["center_mm"]
        w, h = k["size_mm"]
        pts = rot_pts(cx, cy, w, h, k["angle_deg"])
        poly = mp.Polygon([(dx + x, dy + y) for x, y in pts], closed=True,
                          fc="#e9e4da" if dark else "#f3f1ec",
                          ec="#8a8378" if dark else "#555", lw=0.55, zorder=4)
        ax.add_patch(poly)
        if not dark and k["key_number"] and k["half"] == "L":
            pass

    # экран: вырез = активная область
    ax.add_patch(mp.FancyBboxPatch((dx + LCD["center_mm"][0] - LCD["opening_size_mm"][0] / 2,
                                    dy + LCD["center_mm"][1] - LCD["opening_size_mm"][1] / 2),
                                   *LCD["opening_size_mm"], boxstyle="round,pad=0,rounding_size=1",
                                   fc="#0b0f1a" if dark else "#111a11",
                                   ec="#666" if dark else "#333", lw=0.9, zorder=3))
    # корпус экрана — пунктиром
    ax.add_patch(mp.Rectangle((dx + LCD_BODY["center_mm"][0] - LCD_BODY["rear_envelope_size_mm"][0] / 2,
                               dy + LCD_BODY["center_mm"][1] - LCD_BODY["rear_envelope_size_mm"][1] / 2),
                              *LCD_BODY["rear_envelope_size_mm"], fc="none",
                              ec="#c00" if not dark else "#a55", lw=0.6, ls=(0, (3, 2)), zorder=2))

    # энкодеры
    for e in ENC:
        cx, cy = e["center_mm"]
        ax.add_patch(mp.Circle((dx + cx, dy + cy), e["knob_outer_diameter_mm"] / 2,
                               fc="#111" if dark else "none", ec="#777", lw=0.8, zorder=4))
        ax.add_patch(mp.Circle((dx + cx, dy + cy), e["nominal_panel_hole_diameter_mm"] / 2,
                               fc="#1d1d1d" if dark else "none", ec="#999", lw=0.5, zorder=5))
        ax.plot([dx + cx, dx + cx], [dy + cy - 6.5, dy + cy - 1.5],
                color="#e8e8e8" if dark else "#bbb", lw=1.2, zorder=6)
        ax.text(dx + cx, dy + cy + 9.2, e["id"].split("_")[-1], ha="center", va="top",
                fontsize=4.4, color="#ccc" if dark else "#666", zorder=6)

    # джеки
    for j in JACKS:
        cx, cy = j["center_mm"]
        ax.add_patch(mp.Circle((dx + cx, dy + cy), j["panel_hole_diameter_mm"] / 2,
                               fc="#111" if dark else "none", ec="#aaa", lw=0.8, zorder=4))
        ax.add_patch(mp.Circle((dx + cx, dy + cy), j["outer_nut_diameter_mm"] / 2,
                               fc="none", ec="#888", lw=0.4, ls=(0, (2, 1.5)), zorder=3))
        ax.text(dx + cx, dy + cy - 6.8, j["id"].replace("J", "").lstrip("0"),
                ha="center", va="bottom", fontsize=4.2,
                color="#ccc" if dark else "#666", zorder=5)

    # фейдеры
    for f in FADERS:
        s, env = f["slot"], f["rear_envelope"]
        sw, sh = s["slot_size_mm"]
        ax.add_patch(mp.FancyBboxPatch((dx + s["center_mm"][0] - sw / 2, dy + s["center_mm"][1] - sh / 2),
                                       sw, sh, boxstyle="round,pad=0,rounding_size=1.2",
                                       fc="#111" if dark else "#ddd", ec="#555", lw=0.6, zorder=3))
        ax.add_patch(mp.Rectangle((dx + env["center_mm"][0] - env["rear_envelope_size_mm"][0] / 2,
                                   dy + env["center_mm"][1] - env["rear_envelope_size_mm"][1] / 2),
                                  *env["rear_envelope_size_mm"], fc="none", ec="#c00",
                                  lw=0.5, ls=(0, (2, 2)), zorder=2))
        hx = dx + s["center_mm"][0]
        hy = dy + s["center_mm"][1]
        ax.add_patch(mp.Rectangle((hx - 7, hy - 3.2), 14, 6.4,
                                  fc="#222" if dark else "#999", ec="#888", lw=0.5, zorder=5))
        ax.plot([hx - 5.5, hx + 5.5], [hy, hy], color="#eee", lw=1.2, zorder=6)

    # винты, лого, подпись
    for sx, sy in ((7, 7), (PW - 7, 7), (7, PH - 7), (PW - 7, PH - 7)):
        ax.add_patch(mp.Circle((dx + sx, dy + sy), 2.2, fc="#555", ec="#222", lw=0.4, zorder=3))
    if dark:
        ax.text(dx + 20, dy + 17, "◉ БУКИФОН", fontsize=8.5, color="#dedede", va="center", zorder=4)
        ax.text(dx + PW - 12, dy + 14, "МОДУЛЬНЫЙ\nСИНТЕЗАТОР", fontsize=5, color="#9a9a9a",
                ha="right", va="center", zorder=4)


def page(pdf, x_from, x_to, title, png=None):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W); ax.set_ylim(A4H, 0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))
    ax.text(A4W / 2, 9, title, ha="center", fontsize=10.5, fontweight="bold")
    ax.text(A4W / 2, 15, f"Канон: {os.path.relpath(SPEC, ROOT)}. Печать A4 100%, 2 листа, "
                         "перекрытие 10 мм.", ha="center", fontsize=5.6, color="#555")
    ox, oy = 8.0, 22.0
    show = x_to - x_from
    n0 = len(ax.get_children())
    draw(ax, ox - x_from, oy, style="template")
    clip = mp.Rectangle((ox, oy), show, PH, transform=ax.transData)
    for art in ax.get_children()[n0:]:
        try:
            art.set_clip_on(True); art.set_clip_path(clip)
        except Exception:
            pass
    ax.add_patch(mp.Rectangle((ox, oy), show, PH, fc="none", ec="#c33", lw=0.7, ls=(0, (2, 2))))
    if x_from > 0:
        ax.add_patch(mp.Rectangle((ox, oy), 10, PH, fc="#fffbe8", ec="none", alpha=0.6, zorder=7))
    ax.plot([ox + 4, ox + 54], [oy + PH + 9, oy + PH + 9], color="#111", lw=1.5)
    for t in (0, 25, 50):
        ax.plot([ox + 4 + t, ox + 4 + t], [oy + PH + 7.5, oy + PH + 10.5], color="#111", lw=0.8)
    ax.text(ox + 29, oy + PH + 12, "50 мм — проверка масштаба", ha="center", va="top",
            fontsize=5.4, color="#333")
    pdf.savefig(fig)
    if png:
        fig.savefig(os.path.join(OUT, png), facecolor="white", dpi=150)
    plt.close(fig)


def render_png(name, dark, pad=8, dpi=170):
    fig, ax = plt.subplots(figsize=((PW + 20) / 25.4, (PH + 20) / 25.4), dpi=dpi)
    ax.set_xlim(-10, PW + 10); ax.set_ylim(PH + 10, -10)
    ax.set_aspect("equal"); ax.axis("off")
    draw(ax, 0, 0, style="render" if dark else "template")
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def vs_concept():
    from PIL import Image
    a = Image.open(os.path.join(ROOT, "refs", "concept-panel.jpg")).convert("RGB")
    b = Image.open(os.path.join(OUT, f"{PREFIX}_render.png")).convert("RGB")
    W = 1100
    a = a.resize((W, int(a.height * W / a.width)), Image.LANCZOS)
    b = b.resize((W, int(b.height * W / b.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, a.height + b.height + 12), "white")
    canvas.paste(a, (0, 0)); canvas.paste(b, (0, a.height + 12))
    canvas.save(os.path.join(OUT, f"{PREFIX}_vs_concept.png"))


def main():
    bad = collisions()
    json.dump({"collisions": bad, "count": len(bad)},
              open(os.path.join(OUT, f"{PREFIX}_collisions.json"), "w"), indent=1)
    print(f"пересечения: {len(bad)}", bad[:5])
    with PdfPages(os.path.join(OUT, f"{PREFIX}_panel_1to1.pdf")) as pdf:
        page(pdf, 0.0, 190.0, f"Букифон {PREFIX} · панель 1:1 · левая часть (X 0…190 мм)",
             f"{PREFIX}_page1.png")
        page(pdf, 180.0, 380.0, f"Букифон {PREFIX} · панель 1:1 · правая часть (X 180…380 мм)",
             f"{PREFIX}_page2.png")
    render_png(f"{PREFIX}_render.png", dark=True)
    render_png(f"{PREFIX}_template.png", dark=False)
    vs_concept()
    print("saved:", OUT)


if __name__ == "__main__":
    main()
