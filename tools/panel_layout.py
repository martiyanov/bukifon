#!/usr/bin/env python3
"""Bukifon — генератор чертежа панели по spec/10-panel-ui.md.

Проверяет коллизии органов управления и рисует вид сверху.
Запуск: /tmp/msvenv/bin/python tools/panel_layout.py
Выход:  renders/panel_layout.png, renders/panel_layout_keys.png, отчёт в stdout.
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)

# ---- геометрия из spec/10-panel-ui.md -------------------------------------
W, H = 315.0, 145.0                       # корпус
PANEL_TOP = 66.0                          # Y 0..66 — верхняя панель
DECK_Y0, DECK_Y1 = 66.0, 145.0            # ниша деки
DECK_PLATE = (296.0, 78.0)                # пластина 296 x 78

SCREEN = dict(cx=157.5, cy=37.0, w=60.0, h=46.0, r=2.0)

KNOBS = [
    (30.0, 24.0), (66.0, 24.0), (30.0, 56.0), (66.0, 56.0),
    (249.0, 24.0), (285.0, 24.0), (249.0, 56.0), (285.0, 56.0),
]
KNOB_D = 18.0
SHOULDER = [(16.0, 8.0), (52.0, 8.0), (263.0, 8.0), (299.0, 8.0)]
SHOULDER_D = 10.0

FADERS = [(137.0, 98.0, 128.0), (178.0, 98.0, 128.0)]  # x, y0, y1
FADER_SLOT = (8.0, 34.0)

PADS = [(x, y) for x in (22.0, 48.0, 74.0) for y in (78.0, 104.0, 130.0)] + \
       [(x, y) for x in (241.0, 267.0, 293.0) for y in (78.0, 104.0, 130.0)]
PAD_SIZE = 20.6

# DECK-KEYS: Corne-подобная раскладка, 21+21
KEY_PITCH_X, KEY_PITCH_Y = 18.0, 17.0
LEFT_COLS = [20.0, 38.0, 56.0, 74.0, 92.0, 110.0]
RIGHT_COLS = [315.0 - x for x in LEFT_COLS]
KEY_ROWS = [74.0, 91.0, 108.0]
THUMBS_L = [(39.0, 126.0), (57.0, 126.0), (75.0, 126.0)]
THUMBS_R = [(315.0 - x, y) for x, y in THUMBS_L]
KEY_SIZE = 14.2

STATUS = (120.0, 8.0)
DOCK_TOP = (157.5, 6.0, 36.0, 10.0)


def collisions():
    """Проверка пересечений круговых/прямоугольных зон."""
    issues = []

    def circ_circ(a, b, ra, rb, name_a, name_b):
        d = np.hypot(a[0] - b[0], a[1] - b[1])
        if d < (ra + rb) * 0.86:
            issues.append(f"{name_a} <-> {name_b}: зазор {d - ra - rb:+.1f} мм")

    # ручки между собой
    for i in range(len(KNOBS)):
        for j in range(i + 1, len(KNOBS)):
            circ_circ(KNOBS[i], KNOBS[j], KNOB_D / 2, KNOB_D / 2, f"ENC{i+1}", f"ENC{j+1}")
    # ручки в окно экрана
    sx0, sx1 = SCREEN["cx"] - SCREEN["w"] / 2, SCREEN["cx"] + SCREEN["w"] / 2
    sy0, sy1 = SCREEN["cy"] - SCREEN["h"] / 2, SCREEN["cy"] + SCREEN["h"] / 2
    for i, (x, y) in enumerate(KNOBS):
        if sx0 - KNOB_D/2 < x < sx1 + KNOB_D/2 and sy0 - KNOB_D/2 < y < sy1 + KNOB_D/2:
            issues.append(f"ENC{i+1} пересекает окно экрана")
    # ручки/плечевые с краем
    for i, (x, y) in enumerate(KNOBS):
        if not (KNOB_D/2 + 1 <= x <= W - KNOB_D/2 - 1 and KNOB_D/2 + 1 <= y <= PANEL_TOP - KNOB_D/2 - 1):
            issues.append(f"ENC{i+1} ({x},{y}) выходит за верхнюю панель")
    for i, (x, y) in enumerate(SHOULDER):
        if not (SHOULDER_D/2 + 1 <= x <= W - SHOULDER_D/2 - 1 and SHOULDER_D/2 + 1 <= y <= 14):
            issues.append(f"BTN{i+1} выходит за кромку")
    # пады между собой и с краем
    for i, (x, y) in enumerate(PADS):
        if not (PAD_SIZE/2 + 1 <= x <= W - PAD_SIZE/2 - 1 and DECK_Y0 + PAD_SIZE/2 + 1 <= y <= H - PAD_SIZE/2 - 1):
            issues.append(f"PAD{i+1} выходит за нишу деки")
    for i in range(len(PADS)):
        for j in range(i + 1, len(PADS)):
            if abs(PADS[i][0] - PADS[j][0]) < PAD_SIZE and abs(PADS[i][1] - PADS[j][1]) < PAD_SIZE:
                issues.append(f"PAD{i+1} <-> PAD{j+1} пересекаются")
    # пады vs слайдеры
    for i, (x, y) in enumerate(PADS):
        for k, (fx, fy0, fy1) in enumerate(FADERS):
            if abs(x - fx) < (PAD_SIZE + FADER_SLOT[0]) / 2 and y + PAD_SIZE/2 > fy0 - 8 and y - PAD_SIZE/2 < fy1 + 8:
                issues.append(f"PAD{i+1} конфликтует со SL{k+1}")
    # ручки vs плечевые
    for i, k in enumerate(KNOBS):
        for j, s in enumerate(SHOULDER):
            circ_circ(k, s, KNOB_D / 2, SHOULDER_D / 2, f"ENC{i+1}", f"BTN{j+1}")
    return issues


def key_collisions():
    issues = []
    keys = [(x, y) for x in LEFT_COLS for y in KEY_ROWS] + \
           [(x, y) for x in RIGHT_COLS for y in KEY_ROWS] + THUMBS_L + THUMBS_R
    # ключи с краем и между собой
    for i, (x, y) in enumerate(keys):
        if not (KEY_SIZE/2 + 0.5 <= x <= W - KEY_SIZE/2 - 0.5 and DECK_Y0 + KEY_SIZE/2 - 1.5 <= y <= H - KEY_SIZE/2 - 1):
            issues.append(f"KEY{i+1} ({x:.1f},{y:.1f}) за пределами ниши")
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if abs(keys[i][0]-keys[j][0]) < KEY_SIZE and abs(keys[i][1]-keys[j][1]) < KEY_SIZE:
                issues.append(f"KEY{i+1} <-> KEY{j+1} пересекаются")
    # ключи vs слайдеры
    for i, (x, y) in enumerate(keys):
        for k, (fx, fy0, fy1) in enumerate(FADERS):
            if abs(x - fx) < (KEY_SIZE + FADER_SLOT[0]) / 2 and y + KEY_SIZE/2 > fy0 - 8 and y - KEY_SIZE/2 < fy1 + 8:
                issues.append(f"KEY{i+1} конфликтует со SL{k+1}")
    return issues


def draw_common(ax, title):
    ax.set_xlim(-8, W + 8)
    ax.set_ylim(H + 8, -8)          # Y вниз (как на эскизе: задняя кромка сверху)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=11, pad=8)

    # корпус и рукоятки
    body = FancyBboxPatch((0, 0), W, H, boxstyle="round,pad=0,rounding_size=8",
                          linewidth=2.2, edgecolor="#222", facecolor="#f7f7f5", zorder=0)
    ax.add_patch(body)
    for gx in (0, W - 60):
        ax.add_patch(FancyBboxPatch((gx + 2, 24), 56, 92, boxstyle="round,pad=0,rounding_size=14",
                                    linewidth=1.0, edgecolor="#bbb", facecolor="none",
                                    linestyle=(0, (4, 3)), zorder=1))
        ax.text(gx + 30, 20, "рукоятка", ha="center", va="bottom", fontsize=7, color="#999")

    # граница верхней панели и ниши деки
    ax.plot([0, W], [PANEL_TOP, PANEL_TOP], color="#999", lw=0.8, ls=(0, (6, 3)))
    ax.text(W - 3, PANEL_TOP - 3, "верхняя панель", ha="right", va="top", fontsize=7, color="#888")
    ax.text(W - 3, H - 3, "сменная дека (DECK)", ha="right", va="bottom", fontsize=7, color="#888")

    # окно экрана
    ax.add_patch(Rectangle((SCREEN["cx"] - SCREEN["w"]/2, SCREEN["cy"] - SCREEN["h"]/2),
                           SCREEN["w"], SCREEN["h"], facecolor="#203040",
                           edgecolor="#111", lw=1.2, zorder=3))
    ax.text(SCREEN["cx"], SCREEN["cy"], "2.8\"\n320×240", color="#dfe9f3",
            ha="center", va="center", fontsize=7.5, zorder=4)
    ax.add_patch(Rectangle((SCREEN["cx"] - 85/2, SCREEN["cy"] - 50/2), 85, 50,
                           facecolor="none", edgecolor="#6a8", lw=0.8, ls="--", zorder=2))

    # ручки
    for i, (x, y) in enumerate(KNOBS):
        ax.add_patch(Circle((x, y), KNOB_D/2, facecolor="#e8e8e8", edgecolor="#333",
                            lw=1.2, zorder=5))
        ax.add_patch(Circle((x, y), KNOB_D/2 - 2.2, facecolor="none", edgecolor="#aaa", lw=0.6, zorder=6))
        ax.plot([x, x], [y - KNOB_D/2 + 1.5, y - 1.0], color="#d33", lw=1.6, zorder=7)
        ax.text(x, y + KNOB_D/2 + 2.0, f"ENC{i+1}", ha="center", va="top", fontsize=6, color="#555")

    # плечевые
    for i, (x, y) in enumerate(SHOULDER):
        ax.add_patch(Circle((x, y), SHOULDER_D/2, facecolor="#dde", edgecolor="#334", lw=1.0, zorder=5))
        ax.text(x, y, "L1 L2 R1 R2".split()[i], ha="center", va="center", fontsize=5.5, zorder=6)

    # окно верхнего дока
    dx, dy, dw, dh = DOCK_TOP
    ax.add_patch(Rectangle((dx - dw/2, dy - dh/2), dw, dh, facecolor="#f2d9b0",
                           edgecolor="#a76", lw=1.0, zorder=2))
    ax.text(dx, dy, "PORT0", ha="center", va="center", fontsize=5.5, color="#7a5320", zorder=3)

    # статус
    ax.add_patch(Circle(STATUS, 2.0, facecolor="#2a2", edgecolor="#171", lw=0.8, zorder=5))

    # слайдеры
    for i, (x, y0, y1) in enumerate(FADERS):
        ax.add_patch(FancyBboxPatch((x - FADER_SLOT[0]/2, y0 - 4), FADER_SLOT[0],
                                    (y1 - y0) + 8, boxstyle="round,pad=0,rounding_size=4",
                                    facecolor="#dcdcdc", edgecolor="#444", lw=1.0, zorder=4))
        ax.add_patch(Rectangle((x - 8, y0 + 8), 16, 9, facecolor="#444", edgecolor="#111", lw=0.8, zorder=5))
        ax.text(x, y1 + 12, f"SL{i+1}", ha="center", va="top", fontsize=7, color="#555")


def draw_pads(ax):
    for i, (x, y) in enumerate(PADS):
        ax.add_patch(FancyBboxPatch((x - PAD_SIZE/2, y - PAD_SIZE/2), PAD_SIZE, PAD_SIZE,
                                    boxstyle="round,pad=0,rounding_size=2",
                                    facecolor="#f6c85f", edgecolor="#8a6a1f", lw=1.0, zorder=6))
        ax.text(x, y, f"{i+1}", ha="center", va="center", fontsize=7.5,
                color="#4a3608", zorder=7)


def draw_keys(ax):
    keys = [(x, y) for x in LEFT_COLS for y in KEY_ROWS] + \
           [(x, y) for x in RIGHT_COLS for y in KEY_ROWS] + THUMBS_L + THUMBS_R
    for i, (x, y) in enumerate(keys):
        ax.add_patch(FancyBboxPatch((x - KEY_SIZE/2, y - KEY_SIZE/2), KEY_SIZE, KEY_SIZE,
                                    boxstyle="round,pad=0,rounding_size=1.5",
                                    facecolor="#cfe3f7", edgecolor="#4a6b8a", lw=0.8, zorder=6))
        ax.text(x, y, f"{i+1}", ha="center", va="center", fontsize=4.6,
                color="#24384a", zorder=7)


def render(kind, fname, title):
    fig, ax = plt.subplots(figsize=(13.5, 6.6), dpi=160)
    draw_common(ax, title)
    if kind == "pads":
        draw_pads(ax)
        # подписи групп
        ax.text(48, 143, "LEFT · перфоманс", ha="center", va="bottom", fontsize=7, color="#8a6a1f")
        ax.text(267, 143, "RIGHT · секвенсор", ha="center", va="bottom", fontsize=7, color="#8a6a1f")
    else:
        draw_keys(ax)
        ax.text(56, 140, "LEFT · 21 клавиша", ha="center", va="bottom", fontsize=7, color="#4a6b8a")
        ax.text(259, 140, "RIGHT · 21 клавиша", ha="center", va="bottom", fontsize=7, color="#4a6b8a")
        ax.text(157.5, 138, "центр: 2 слайдера", ha="center", va="bottom", fontsize=6.5, color="#666")
    # размеры
    ax.annotate("", xy=(0, H + 6), xytext=(W, H + 6),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(W/2, H + 7, "315 mm", ha="center", va="top", fontsize=8, color="#666")
    ax.annotate("", xy=(W + 5, 0), xytext=(W + 5, H),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(W + 6, H/2, "145 mm", va="center", fontsize=8, color="#666", rotation=90)
    fig.tight_layout()
    path = os.path.join(OUT, fname)
    fig.savefig(path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


def main():
    iss = collisions()
    kiss = key_collisions()
    print("=== DECK-PAD ===")
    print("\n".join(iss) if iss else "OK: коллизий нет")
    print("=== DECK-KEYS ===")
    print("\n".join(kiss) if kiss else "OK: коллизий нет")
    p1 = render("pads", "panel_layout.png", "Bukifon · панель, вариант DECK-PAD (18 пэдов + 2 слайдера)")
    p2 = render("keys", "panel_layout_keys.png", "Bukifon · панель, вариант DECK-KEYS (42 клавиши + 2 слайдера)")
    print("saved:", p1)
    print("saved:", p2)
    # краткий отчёт
    with open(os.path.join(OUT, "panel_layout_report.txt"), "w", encoding="utf-8") as f:
        f.write("Bukifon panel layout check\n\nDECK-PAD:\n")
        f.write("\n".join(iss) if iss else "OK: коллизий нет")
        f.write("\n\nDECK-KEYS:\n")
        f.write("\n".join(kiss) if kiss else "OK: коллизий нет")
        f.write("\n")
    return 0 if not iss and not kiss else 1


if __name__ == "__main__":
    sys.exit(main())
