#!/usr/bin/env python3
"""Сравнение трёх вариантов габарита панели — эскиз для согласования с заказчиком."""
import math, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lapka42_geometry as L
CAP_W, CAP_H = L.KEYCAP_W, L.KEYCAP_H


def keys_for(pw, ph, tilt, edge):
    raw = L.LAPKA42_LEFT
    c = (sum(p[0] for p in raw) / 21, sum(p[1] for p in raw) / 21)
    out = {}
    for side, ang in (("L", -tilt), ("R", tilt)):
        a = math.radians(ang)
        ca, sa = math.cos(a), math.sin(a)
        ks = []
        for (x, y, r) in raw:
            dx, dy = x - c[0], y - c[1]
            if side == "R":
                dx, r = -dx, -r
            ks.append((c[0] + ca * dx - sa * dy, c[1] + sa * dx + ca * dy, r + ang))
        # bbox по колпачкам +1 мм
        xs, ys = [], []
        for x, y, r in ks:
            aa = math.radians(r)
            ca2, sa2 = math.cos(aa), math.sin(aa)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    xs.append(x + ca2 * sx * 9.25 - sa2 * sy * 9.25)
                    ys.append(y + sa2 * sx * 9.25 + ca2 * sy * 9.25)
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        ty = (ph - edge) - y1
        tx = edge - x0 if side == "L" else (pw - edge) - x1
        out[side] = [(x + tx, y + ty, r) for x, y, r in ks]
        out[side + "_bb"] = (x0 + tx, y0 + ty, x1 + tx, y1 + ty)
    return out


VARIANTS = [
    (340.0, 185.0, 5.0, "A. 340 × 185 · наклон ±5°\n(габарит Octatrack, наклон почти пропал;\nвпритык: поля 0 мм, фейдеры встречают тамбы)"),
    (365.0, 200.0, 15.0, "B. 365 × 200 · наклон ±15°\n(компромисс: поля ~2–4 мм, зазор тамбов 6 мм)"),
    (380.0, 210.0, 20.0, "C. 380 × 210 · наклон ±20°  ← РЕКОМЕНДУЮ\n(как бумажный макет; поля 7 мм, канал фейдеров 58 мм)"),
]

fig, axes = plt.subplots(3, 1, figsize=(9.5, 13.2), dpi=150)
for ax, (pw, ph, tilt, title) in zip(axes, VARIANTS):
    d = keys_for(pw, ph, tilt, 5.0 if tilt <= 5 else 7.0)
    ax.set_xlim(-14, pw + 14)
    ax.set_ylim(ph + 12, -16)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0, 0), pw, ph, boxstyle="round,pad=0,rounding_size=4",
                                   fc="#fafaf5", ec="#222", lw=1.8))
    # экран + джеки + ручки + фейдеры (масштаб тот же, положение по центру)
    sw, sh = 108.0, 64.8
    ax.add_patch(mp.Rectangle(((pw - sw) / 2, 11.5), sw, sh, fc="#101a10", ec="#333", lw=0.8))
    for i in range(10):
        ax.add_patch(mp.Circle(((pw - 99) / 2 + 11 * i, 7), 3, fc="#e9e9e4", ec="#333", lw=0.6))
    cols = [22, 49, 76, 103]
    for x in cols + [pw - x for x in cols]:
        for y in (26, 53):
            ax.add_patch(mp.Circle((x, y), 7, fc="#ececec", ec="#333", lw=0.8))
    for fx in (pw / 2 - 10, pw / 2 + 10):
        ax.add_patch(mp.Rectangle((fx - 4, ph * 0.55), 8, ph * 0.39, fc="#dcdcdc",
                                  ec="#444", lw=0.7))
    for s in ("L", "R"):
        for (x, y, r) in d[s]:
            ax.add_patch(mp.Rectangle((x - CAP_W / 2, y - CAP_H / 2), CAP_W, CAP_H,
                                      angle=r, rotation_point="center",
                                      fc="#d8e6f7", ec="#4a6b8a", lw=0.55))
    x0, y0, x1, y1 = d["L_bb"]
    ax.text(pw / 2, ph + 8, title, ha="center", va="top", fontsize=9.5,
            fontweight="bold" if "РЕКОМЕНДУЮ" in title else "normal")
    ch = d["R_bb"][0] - x1
    ax.text(pw / 2, -6, f"зазор между тамбами: {ch:.0f} мм", ha="center", fontsize=7.5, color="#555")

out = os.path.join(os.path.dirname(HERE), "renders", "templates", "bukifon_v1_7_variants.png")
fig.savefig(out, bbox_inches="tight", facecolor="white")
print(out)
