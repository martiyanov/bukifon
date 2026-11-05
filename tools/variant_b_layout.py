#!/usr/bin/env python3
"""Bukifon — вариант B (компактный «A5», свёрнутый A4): 210 × 148 мм.

Раскладка по эскизу заказчика refs/sketch2-folded-a4.jpg: 16 ручек (8+8),
экран в обрамлении 8 кнопок (4+4), 2 слайдера, две группы 3×3 пэдов.
Запуск: MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python tools/variant_b_layout.py
Выход:  renders/variantB_panel.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 210.0, 148.0

KNOB_R = 5.5
LEFT_KNOBS = [(x, y) for x in (10, 27, 44, 61) for y in (14, 34)]
RIGHT_KNOBS = [(W - x, y) for x, y in LEFT_KNOBS]
KNOBS = LEFT_KNOBS + RIGHT_KNOBS

SCREEN = (105.0, 30.0, 54.0, 42.0)
SCR_BTN = [(73.0, y) for y in (12, 24, 36, 48)] + [(137.0, y) for y in (12, 24, 36, 48)]
FADERS = [(94.0, 92.0, 122.0), (116.0, 92.0, 122.0)]
PADS = [(x, y) for x in (16, 35, 54) for y in (90, 109, 128)] + \
       [(x, y) for x in (156, 175, 194) for y in (90, 109, 128)]
PAD = 16.0
STATUS = (105.0, 66.0)


def check():
    issues = []
    # ручки между собой
    for i in range(len(KNOBS)):
        for j in range(i + 1, len(KNOBS)):
            d = np.hypot(KNOBS[i][0] - KNOBS[j][0], KNOBS[i][1] - KNOBS[j][1])
            if d < 2 * KNOB_R + 1.5:
                issues.append(f"ENC{i+1} <-> ENC{j+1}: зазор {d - 2*KNOB_R:.1f}")
    # ручки vs экран
    sx, sy, sw, sh = SCREEN
    for i, (x, y) in enumerate(KNOBS):
        if abs(x - sx) < sw / 2 + KNOB_R and abs(y - sy) < sh / 2 + KNOB_R:
            issues.append(f"ENC{i+1} пересекает экран")
    # кнопки vs экран/ручки
    for i, (x, y) in enumerate(SCR_BTN):
        if abs(x - sx) < sw / 2 + 4.5 and abs(y - sy) < sh / 2 + 4.5:
            issues.append(f"BTN{i+1} пересекает экран")
    # пэды
    for i, (x, y) in enumerate(PADS):
        if not (PAD / 2 + 1 <= x <= W - PAD / 2 - 1 and 80 <= y <= H - PAD / 2 - 1):
            issues.append(f"PAD{i+1} за пределами")
    return issues


def main():
    issues = check()
    print("\n".join(issues) if issues else "OK: коллизий нет")

    fig, ax = plt.subplots(figsize=(12.6, 8.9), dpi=170)
    ax.set_xlim(-22, W + 30)
    ax.set_ylim(H + 26, -10)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Bukifon · вариант B «A5» (свёрнутый A4) — 210 × 148 мм", fontsize=13, pad=10)

    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle="round,pad=0,rounding_size=6",
                                lw=2.2, ec="#222", fc="#f7f7f5", zorder=0))

    # экран
    sx, sy, sw, sh = SCREEN
    ax.add_patch(Rectangle((sx - sw / 2, sy - sh / 2), sw, sh, fc="#203040", ec="#111", lw=1.3, zorder=4))
    ax.add_patch(Rectangle((sx - sw / 2 - 3, sy - sh / 2 - 3), sw + 6, sh + 6,
                           fc="none", ec="#46788f", lw=1.0, ls="--", zorder=3))
    ax.text(sx, sy, '2.8"\n320×240', color="#dfe9f3", ha="center", va="center", fontsize=8, zorder=5)

    # ручки
    for i, (x, y) in enumerate(KNOBS):
        ax.add_patch(Circle((x, y), KNOB_R, fc="#ececec", ec="#333", lw=1.2, zorder=6))
        ax.add_patch(Circle((x, y), KNOB_R - 1.6, fc="none", ec="#bbb", lw=0.6, zorder=7))
        ax.plot([x, x], [y - KNOB_R + 1, y - 0.8], color="#d33", lw=1.4, zorder=8)
        ax.text(x, y + KNOB_R + 1.6, f"E{i+1}", ha="center", va="top", fontsize=5, color="#666")

    # кнопки у экрана
    for i, (x, y) in enumerate(SCR_BTN):
        ax.add_patch(FancyBboxPatch((x - 4.5, y - 4.5), 9, 9, boxstyle="round,pad=0,rounding_size=1.2",
                                    fc="#dde8f2", ec="#4a6b8a", lw=1.0, zorder=6))
        ax.text(x, y, f"{i+1}", ha="center", va="center", fontsize=5.5, color="#2c4a63", zorder=7)

    # слайдеры
    for i, (x, y0, y1) in enumerate(FADERS):
        ax.add_patch(FancyBboxPatch((x - 4, y0 - 4), 8, (y1 - y0) + 8,
                                    boxstyle="round,pad=0,rounding_size=3",
                                    fc="#dcdcdc", ec="#444", lw=1.0, zorder=5))
        ax.add_patch(Rectangle((x - 7, y0 + 6), 14, 8, fc="#444", ec="#111", lw=0.8, zorder=6))
        ax.text(x, y1 + 9, f"SL{i+1}", ha="center", va="top", fontsize=7, color="#555")

    # пэды
    for i, (x, y) in enumerate(PADS):
        ax.add_patch(FancyBboxPatch((x - PAD / 2, y - PAD / 2), PAD, PAD,
                                    boxstyle="round,pad=0,rounding_size=1.5",
                                    fc="#f6c85f", ec="#8a6a1f", lw=1.0, zorder=6))
        ax.text(x, y, f"{i+1}", ha="center", va="center", fontsize=6.5, color="#4a3608", zorder=7)

    # статус
    ax.add_patch(Circle(STATUS, 1.8, fc="#2a2", ec="#171", lw=0.8, zorder=6))

    # стороны/разъёмы
    ax.text(W / 2, H + 11, "передняя кромка · держать/играть", ha="center", va="bottom", fontsize=7.5, color="#888")
    ax.text(W / 2, -3, "задняя кромка: DC · USB-C DATA · USB-C CHARGE · MIDI TRS ×2 · CV ×4 · GATE ×2 · LINE/PHONES · AUDIO IN · EXPR",
            ha="center", va="top", fontsize=6.5, color="#777")
    ax.annotate("", xy=(0, H + 4), xytext=(W, H + 4), arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(W / 2, H + 4.6, "210 мм", ha="center", va="top", fontsize=8, color="#666")
    ax.annotate("", xy=(-6, 0), xytext=(-6, H), arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(-7, H / 2, "148 мм", va="center", rotation=90, fontsize=8, color="#666")

    out = os.path.join(ROOT, "renders", "variantB_panel.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("saved:", out)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
