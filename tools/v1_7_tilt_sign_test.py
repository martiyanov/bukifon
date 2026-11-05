#!/usr/bin/env python3
"""Сравнение двух направлений наклона половин — сверка с фото макета."""
import math, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lapka42_geometry as L

PW, PH = 340.0, 185.0
THUMB = {10, 15, 16, 18, 19, 20, 21}  # нижняя дуга/тамбы (по позициям y>56 или углам ~±180)


def place(tilt_sign):
    raw = L.LAPKA42_LEFT
    c = (sum(p[0] for p in raw) / 21, sum(p[1] for p in raw) / 21)
    halves = []
    for side in ("L", "R"):
        ang = tilt_sign * 15.0 * (-1 if side == "L" else 1)
        a = math.radians(ang)
        ca, sa = math.cos(a), math.sin(a)
        ks = []
        for (x, y, r) in raw:
            dx, dy = x - c[0], y - c[1]
            if side == "R":
                dx = -dx
                r = -r
            ks.append((c[0] + ca * dx - sa * dy, c[1] + sa * dx + ca * dy, r + ang))
        xs = [k[0] for k in ks]; ys = [k[1] for k in ks]
        # прижать наружу и вниз
        if side == "L":
            tx, ty = 5 - min(xs), 180 - max(ys)
        else:
            tx, ty = 335 - max(xs), 180 - max(ys)
        halves.append([(x + tx, y + ty, r) for x, y, r in ks])
    return halves


fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), dpi=150)
for ax, (sign, name) in zip(axes, [(-1, "ВАРИАНТ A: L повёрнут −15°"), (+1, "ВАРИАНТ B: L повёрнут +15°")]):
    ax.set_xlim(-10, PW + 10); ax.set_ylim(PH + 10, -14)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(mp.Rectangle((0, 0), PW, PH, fc="#fafaf6", ec="#222", lw=1.6))
    for i, keys in enumerate(place(sign)):
        for j, (x, y, r) in enumerate(keys, 1):
            col = "#e88" if j in THUMB else "#bcd6ef"
            ax.add_patch(mp.Rectangle((x - 8.75, y - 8.25), 17.5, 16.5, angle=r,
                                      rotation_point="center", fc=col, ec="#345", lw=0.6))
    ax.set_title(name + f"  (красное = тамбы, y>56)", fontsize=9)

out = os.path.join(os.path.dirname(HERE), "renders", "templates", "v1_7_tilt_sign_AB.png")
fig.savefig(out, bbox_inches="tight", facecolor="white")
print(out)
