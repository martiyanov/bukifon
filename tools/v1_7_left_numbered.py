#!/usr/bin/env python3
"""Левая половина v1.7 крупно, с номерами клавиш (сверка нумерации с фото)."""
import math, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lapka42_geometry as L

TILT = 20.0
raw = L.LAPKA42_LEFT
c = (sum(p[0] for p in raw) / 21, sum(p[1] for p in raw) / 21)
a = math.radians(-TILT)
ks = []
for (x, y, r) in raw:
    dx, dy = x - c[0], y - c[1]
    ks.append((c[0] + math.cos(a) * dx - math.sin(a) * dy,
               c[1] + math.sin(a) * dx + math.cos(a) * dy, r - TILT))

fig, ax = plt.subplots(figsize=(7.2, 5.6), dpi=110)
ax.set_aspect("equal")
ax.axis("off")
for i, (x, y, r) in enumerate(ks, 1):
    ax.add_patch(mp.Rectangle((x - 8.75, y - 8.25), 17.5, 16.5, angle=r,
                              rotation_point="center",
                              fc="#d8e6f7" if i not in (18, 20, 21) else "#f7c8c8",
                              ec="#345", lw=0.8))
    ax.text(x, y, str(i), ha="center", va="center", fontsize=7, color="#123")
ax.set_title("Моя отрисовка: левая половина, номера в порядке lapka42_geometry (18/20/21 = тамбы)")
out = os.path.join(os.path.dirname(HERE), "renders", "templates", "v1_7_left_numbered.png")
fig.savefig(out, bbox_inches="tight", facecolor="white")
print(out)
