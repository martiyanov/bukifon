#!/usr/bin/env python3
"""Букифон v1.3 — варианты нижней клавишной зоны.

Вид панели: как в v1.0 (315 × 145), сверху динамики над экраном, 8 ручек,
2 слайдера; внизу — ряды клавиш Lapka-42 (splay), но без «крайних» рядов.
Варианты:
  A — только домашний ряд (по 6 клавиш на половину) = 12 клавиш (1 октава)
  B — домашний ряд + тамб-клавиши = 18 клавиш
  C — домашний + нижний ряд = 24 клавиши (2 октавы)
  D — все три ряда без тамбов = 36 клавиш (3 октавы)
Запуск: MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python tools/v1_3_options.py
Выход:  renders/v1_3_option_A.png … _D.png
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lapka42_geometry as L

W, H = 315.0, 145.0
SPEAKERS = [(145.0, 8.0), (170.0, 8.0)]
SPK_D = 16.0
SCREEN = (157.5, 42.0, 60.0, 46.0)
KNOBS = [(x, y) for x in (30.0, 66.0) for y in (26.0, 56.0)] + \
        [(x, y) for x in (249.0, 285.0) for y in (26.0, 56.0)]
SHOULDER = [(12.0, 8.0), (30.0, 8.0), (285.0, 8.0), (303.0, 8.0)]
FADERS = [(147.0, 84.0, 124.0), (167.0, 84.0, 124.0)]
STATUS = (157.5, 71.0)


def columns():
    ks = sorted(L.LAPKA42_LEFT, key=lambda t: t[0])
    cols, cur = [], []
    for k in ks:
        if cur and k[0] - cur[-1][0] > 8:
            cols.append(sorted(cur, key=lambda t: t[1]))
            cur = []
        cur.append(k)
    if cur:
        cols.append(sorted(cur, key=lambda t: t[1]))
    # оставляем 6 «пальцевых» колонок (в них по 3 клавиши)
    return [c for c in cols if len(c) == 3]


COLS = columns()
THUMBS = [(86.76, 59.05, 180.0), (106.10, 60.75, 170.0), (124.85, 65.77, 160.0)]

VARIANTS = {
    "A": dict(name="только домашний ряд (12 клавиш, 1 октава)",
              keys=[c[1] for c in COLS], thumbs=[]),
    "B": dict(name="домашний ряд + тамб-клавиши (18 клавиш)",
              keys=[c[1] for c in COLS], thumbs=THUMBS),
    "C": dict(name="домашний + нижний ряд (24 клавиши, 2 октавы)",
              keys=[c[1] for c in COLS] + [c[2] for c in COLS], thumbs=[]),
    "D": dict(name="три ряда без тамбов (36 клавиш, 3 октавы)",
              keys=[k for c in COLS for k in c], thumbs=[]),
}


def bbox(keys):
    hw, hh = L.KEYCAP_W / 2, L.KEYCAP_H / 2
    xs, ys = [], []
    for x, y, rot in keys:
        a = math.radians(rot)
        ca, sa = math.cos(a), math.sin(a)
        for sx in (-1, 1):
            for sy in (-1, 1):
                xs.append(x + ca * sx * hw - sa * sy * hh)
                ys.append(y + sa * sx * hw + ca * sy * hh)
    return min(xs), min(ys), max(xs), max(ys)


def draw_panel_base(ax):
    ax.set_xlim(-10, W + 10)
    ax.set_ylim(H + 12, -12)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0, 0), W, H, boxstyle="round,pad=0,rounding_size=7",
                                   lw=2.0, ec="#222", fc="#f8f8f6", zorder=0))
    for i, (x, y) in enumerate(SPEAKERS):
        ax.add_patch(mp.Circle((x, y), SPK_D / 2, fc="#dcdcdc", ec="#333", lw=1.0, zorder=5))
        ax.add_patch(mp.Circle((x, y), SPK_D / 2 - 1.5, fc="#c2c2c2", ec="#777", lw=0.5, zorder=6))
        ax.add_patch(mp.Circle((x, y), 1.9, fc="#888", ec="#555", lw=0.4, zorder=7))
        ax.text(x, y - SPK_D / 2 - 1.4, f"SPK{i+1}", fontsize=5, ha="center", va="top", color="#666")
    cx, cy, sw, sh = SCREEN
    ax.add_patch(mp.Rectangle((cx - sw / 2 - 4, cy - sh / 2 - 4), sw + 8, sh + 8,
                              fc="#e4e4e0", ec="#999", lw=0.7, zorder=3))
    ax.add_patch(mp.Rectangle((cx - sw / 2, cy - sh / 2), sw, sh, fc="#203040", ec="#111", lw=1.1, zorder=4))
    ax.text(cx, cy, '2.8" 320×240', color="#dfe9f3", ha="center", va="center", fontsize=6.5, zorder=5)
    for i, (x, y) in enumerate(KNOBS):
        ax.add_patch(mp.Circle((x, y), 9.0, fc="#ececec", ec="#333", lw=1.0, zorder=5))
        ax.add_patch(mp.Circle((x, y), 6.6, fc="none", ec="#bbb", lw=0.4, zorder=6))
        ax.plot([x, x], [y - 7.4, y - 1.2], color="#d33", lw=1.3, zorder=7)
        ax.text(x, y + 10.4, f"E{i+1}", fontsize=4.6, ha="center", color="#666")
    for i, (x, y) in enumerate(SHOULDER):
        ax.add_patch(mp.Circle((x, y), 4.0, fc="#dde", ec="#334", lw=0.8, zorder=5))
        ax.text(x, y, "L1 L2 R1 R2".split()[i], fontsize=4.0, ha="center", va="center", zorder=6)
    ax.add_patch(mp.Circle(STATUS, 1.7, fc="#2a2", ec="#171", lw=0.6, zorder=5))
    for i, (x, y0, y1) in enumerate(FADERS):
        ax.add_patch(mp.FancyBboxPatch((x - 4.5, y0 - 4), 9, (y1 - y0) + 8,
                                       boxstyle="round,pad=0,rounding_size=3.4",
                                       fc="#dcdcdc", ec="#444", lw=0.9, zorder=5))
        ax.add_patch(mp.Rectangle((x - 8, y0 + 10), 16, 9, fc="#444", ec="#111", lw=0.6, zorder=6))
        ax.text(x, y1 + 7, f"SL{i+1}", fontsize=5.4, ha="center", color="#555")


def draw_keys(ax, keys, thumbs, label, flip=True):
    """Левая половина как есть, правая — зеркало относительно центра панели."""
    hw, hh = L.KEYCAP_W / 2, L.KEYCAP_H / 2
    if not keys:
        return
    x0, y0, x1, y1 = bbox(keys + thumbs)
    bw, bh = x1 - x0, y1 - y0
    left_x = 12.0
    top_y = 76.0
    # сдвигаем так, чтобы bbox сел в левый нижний угол зоны; правую зеркалим
    dx = left_x - x0
    dy = top_y - y0
    n = 1
    for (x, y, rot) in keys + thumbs:
        for sign in (1, -1):
            px = dx + x if sign == 1 else W - (dx + x)
            py = dy + y
            # ось Y графика инвертирована -> знак поворота обратный; позиции не меняются
            a = (-rot if flip else rot) if sign == 1 else (rot if flip else -rot)
            ax.add_patch(mp.Rectangle((px - hw, py - hh), L.KEYCAP_W, L.KEYCAP_H,
                                      angle=a, rotation_point="center",
                                      fc="#cfe3f7" if sign == 1 else "#d8e6f5",
                                      ec="#4a6b8a", lw=0.7, zorder=7))
            ax.text(px, py, str(n), fontsize=3.2, ha="center", va="center", color="#24384a", zorder=8)
            n += 1
    ax.text(W / 2, H - 3, label, ha="center", va="bottom", fontsize=6.2, color="#777")


def render(code, spec, flip=False):
    fig, ax = plt.subplots(figsize=(13.0, 6.4), dpi=170)
    draw_panel_base(ax)
    draw_keys(ax, spec["keys"], spec["thumbs"], spec["name"], flip=flip)
    ax.set_title(f"Букифон · панель 315×145 · нижняя зона: {spec['name']}", fontsize=10.5, pad=8)
    fig.tight_layout()
    out = os.path.join(ROOT, "renders", f"v1_3_option_{code}.png")
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    outs = [render(code, spec) for code, spec in VARIANTS.items()]
    # «разворот наружу» (исправленное направление splay): левая половина -rot, правая +rot
    outs.append(render("B_outward", dict(VARIANTS["B"], name="домашний ряд + тамбы · разворот наружу (исправленный splay)"),
                       flip=True))
    outs.append(render("C_outward", dict(VARIANTS["C"], name="домашний + нижний ряд · разворот наружу (исправленный splay)"),
                       flip=True))
    for o in outs:
        print("saved:", o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
