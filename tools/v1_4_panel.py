#!/usr/bin/env python3
"""Букифон v1.4 — панель 340 × 185 (габарит Octatrack), по макету заказчика.

Состав (по фото IMG_0704 и уточнениям):
  * 16 ручек: два блока 4 × 2 по бокам от экрана, Ø14, шаг 27 мм;
  * экран-модуль 73.8 × 51.0 (128 × 64 OLED) по центру;
  * мини-джеки 3.5 мм: ряд НАД экраном (сколько влезает) + два ряда под экраном;
  * два фейдера «как на Octatrack» между клавиатурами, под экраном;
  * две половины Lapka-42 (по 21 клавише) внизу слева и справа, зеркально.
Печать: A4 landscape, 2 страницы 1:1 (340 > 297), перекрытие 10 мм.
Выход: renders/templates/bukifon_v1_4_panel_1to1.pdf + preview PNG.
"""
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
sys.path.insert(0, HERE)
import lapka42_geometry as L

OUT = os.path.join(ROOT, "renders", "templates")
os.makedirs(OUT, exist_ok=True)
A4W, A4H = 297.0, 210.0

PW, PH = 340.0, 185.0

# --- верхняя зона -----------------------------------------------------------
KNOB_D = 14.0
KNOB_COLS = [22.0, 49.0, 76.0, 103.0]
KNOB_ROWS = [26.0, 53.0]
KNOBS_L = [(x, y) for x in KNOB_COLS for y in KNOB_ROWS]
KNOBS_R = [(PW - x, y) for x, y in KNOBS_L]
KNOB_LABELS = ["ABCD", "EFGH"]

SCREEN = dict(x=133.1, y=16.0, w=73.8, h=51.0)
JACKS_TOP = [(120.0 + i * 11.0, 7.0) for i in range(9)]
JACKS_BOT = [(142.0 + i * 13.0, y) for y in (78.0, 92.0) for i in range(6)]
SPEAKERS = [(122.0, 85.0), (218.0, 85.0)]
SPK_D = 16.0

# --- фейдеры ---------------------------------------------------------------
FADERS = [(158.0, 104.0, 168.0), (182.0, 104.0, 168.0)]   # x, y0, y1 (ход 45…60)
FADER_SLOT_W = 8.0

# --- клавиатуры -------------------------------------------------------------
KEY_TOP = 97.0
CAP_W, CAP_H = L.KEYCAP_W, L.KEYCAP_H
_hw, _hh = CAP_W / 2, CAP_H / 2


def _bbox(keys):
    xs, ys = [], []
    for x, y, rot in keys:
        a = math.radians(rot)
        ca, sa = math.cos(a), math.sin(a)
        for sx in (-1, 1):
            for sy in (-1, 1):
                xs.append(x + ca * sx * _hw - sa * sy * _hh)
                ys.append(y + sa * sx * _hw + ca * sy * _hh)
    return min(xs), min(ys), max(xs), max(ys)


_KB = _bbox(L.LAPKA42_LEFT)
KEY_DX = -_KB[0]                     # левая половина начинается с X=0
KEY_DY = KEY_TOP - _KB[1]
HALF_W = _KB[2] - _KB[0]
HALF_H = _KB[3] - _KB[1]
print(f"half bbox: {HALF_W:.2f} × {HALF_H:.2f} мм; panel {PW}×{PH}")


def key_positions():
    out = []
    for (x, y, rot) in L.LAPKA42_LEFT:
        out.append((KEY_DX + x, KEY_DY + y, -rot))               # левая: ось Y инверт.
    for (x, y, rot) in L.LAPKA42_LEFT:
        out.append((PW - KEY_DX - x, KEY_DY + y, rot))           # правая: зеркало
    return out


def draw_panel(ax, dx, dy, detail=True):
    ax.add_patch(mp.FancyBboxPatch((dx, dy), PW, PH, boxstyle="round,pad=0,rounding_size=5",
                                   fc="#f8f8f5", ec="#222", lw=1.8, zorder=0))
    # сетка 10 мм
    for gx in range(0, int(PW) + 1, 10):
        ax.plot([dx + gx, dx + gx], [dy, dy + PH], color="#ecece7", lw=0.25, zorder=1)
    for gy in range(0, int(PH) + 1, 10):
        ax.plot([dx, dx + PW], [dy + gy, dy + gy], color="#ecece7", lw=0.25, zorder=1)

    # ручки (16)
    for i, (x, y) in enumerate(KNOBS_L + KNOBS_R):
        ax.add_patch(mp.Circle((dx + x, dy + y), KNOB_D / 2, fc="#ececec", ec="#333", lw=1.0, zorder=4))
        ax.add_patch(mp.Circle((dx + x, dy + y), 5.2, fc="none", ec="#bbb", lw=0.5, zorder=5))
        ax.plot([dx + x, dx + x], [dy + y - 5.6, dy + y - 1.0], color="#d33", lw=1.1, zorder=6)
        row = 0 if y < 40 else 1
        if x in KNOB_COLS:
            ci = KNOB_COLS.index(x)
        else:
            ci = 3 - KNOB_COLS.index(PW - x)      # правый блок: A слева
        ax.text(dx + x, dy + y + KNOB_D / 2 + 1.0, KNOB_LABELS[row][ci],
                ha="center", va="top", fontsize=4.2, color="#555", zorder=6)

    # экран
    ax.add_patch(mp.FancyBboxPatch((dx + SCREEN["x"], dy + SCREEN["y"]), SCREEN["w"], SCREEN["h"],
                                   boxstyle="round,pad=0,rounding_size=1.5",
                                   fc="#1b1b1b", ec="#555", lw=1.0, zorder=4))
    act_w, act_h = 56.5, 28.2
    ax.add_patch(mp.Rectangle((dx + SCREEN["x"] + (SCREEN["w"] - act_w) / 2,
                               dy + SCREEN["y"] + (SCREEN["h"] - act_h) / 2), act_w, act_h,
                              fc="#0d1a0d", ec="#7a7", lw=0.5, zorder=5))
    if detail:
        ax.text(dx + 8, dy + 3, "БУКИФОН", fontsize=6.5, color="#b9b9b0", va="top", zorder=4)

    # мини-джеки
    for (x, y) in JACKS_TOP:
        ax.add_patch(mp.Circle((dx + x, dy + y), 3.2, fc="#e9e9e4", ec="#333", lw=0.7, zorder=4))
        ax.add_patch(mp.Circle((dx + x, dy + y), 1.1, fc="#555", ec="none", zorder=5))
    for (x, y) in JACKS_BOT:
        ax.add_patch(mp.Circle((dx + x, dy + y), 3.0, fc="#e9e9e4", ec="#333", lw=0.7, zorder=4))
        ax.add_patch(mp.Circle((dx + x, dy + y), 1.0, fc="#555", ec="none", zorder=5))
    ax.text(dx + PW / 2, dy + 12.2, "9 × mini-jack 3.5 мм над экраном", ha="center",
            va="top", fontsize=4.0, color="#888", zorder=6)
    ax.text(dx + PW / 2, dy + 69.5, "12 × mini-jack 3.5 мм под экраном (2 ряда)",
            ha="center", va="top", fontsize=4.0, color="#888", zorder=6)

    # динамики
    for i, (x, y) in enumerate(SPEAKERS):
        ax.add_patch(mp.Circle((dx + x, dy + y), SPK_D / 2, fc="#dcdcdc", ec="#333", lw=0.8, zorder=4))
        ax.add_patch(mp.Circle((dx + x, dy + y), 2.2, fc="#9a9a9a", ec="#666", lw=0.4, zorder=5))
        ax.text(dx + x, dy + y + SPK_D / 2 + 1.0, f"SPK{i+1}", ha="center", va="top",
                fontsize=4.0, color="#666", zorder=5)

    # фейдеры между клавиатурами
    for i, (x, y0, y1) in enumerate(FADERS):
        ax.add_patch(mp.FancyBboxPatch((dx + x - FADER_SLOT_W / 2, dy + y0 - 3),
                                       FADER_SLOT_W, (y1 - y0) + 6,
                                       boxstyle="round,pad=0,rounding_size=3.4",
                                       fc="#dcdcdc", ec="#444", lw=0.8, zorder=4))
        ax.add_patch(mp.Rectangle((dx + x - 8, dy + y0 + (y1 - y0) / 2 - 4), 16, 8,
                                  fc="#444", ec="#111", lw=0.5, zorder=5))
        ax.text(dx + x + 10, dy + (y0 + y1) / 2, f"F{i+1}", ha="left", va="center",
                fontsize=5, color="#555")

    # клавиатуры Lapka-42
    for (x, y, rot) in key_positions():
        ax.add_patch(mp.Rectangle((dx + x - _hw, dy + y - _hh), CAP_W, CAP_H,
                                  angle=rot, rotation_point="center",
                                  fc="#d8e6f7", ec="#4a6b8a", lw=0.6, zorder=6))


def page(pdf, x_from, x_to, title, png=None):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))
    ax.text(A4W / 2, 9, title, ha="center", fontsize=11, fontweight="bold")
    ax.text(A4W / 2, 15, "Печать A4 100%. Панель 340 × 185 мм (как Octatrack); "
                         "2 страницы с перекрытием 10 мм.", ha="center", fontsize=5.8, color="#555")

    ox, oy = 8.0, 22.0
    show = x_to - x_from
    n0 = len(ax.get_children())
    draw_panel(ax, ox - x_from, oy)
    clip = mp.Rectangle((ox, oy), show, PH, transform=ax.transData)
    for art in ax.get_children()[n0:]:
        try:
            art.set_clip_on(True)
            art.set_clip_path(clip)
        except Exception:
            pass
    ax.add_patch(mp.Rectangle((ox, oy), show, PH, fc="none", ec="#c33", lw=0.7, ls=(0, (2, 2))))
    if x_from > 0:
        ax.add_patch(mp.Rectangle((ox, oy), 10, PH, fc="#fffbe8", ec="none", alpha=0.6, zorder=7))
    ax.annotate("", xy=(ox, oy + PH + 4), xytext=(ox + show, oy + PH + 4),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.7))
    ax.text(ox + show / 2, oy + PH + 5, f"X {x_from:.0f}…{x_to:.0f} мм", ha="center", va="top",
            fontsize=6, color="#666")
    # линейка 50 мм
    ax.plot([ox + 4, ox + 54], [oy + PH + 10, oy + PH + 10], color="#111", lw=1.5)
    for t in (0, 25, 50):
        ax.plot([ox + 4 + t, ox + 4 + t], [oy + PH + 8.5, oy + PH + 11.5], color="#111", lw=0.8)
    ax.text(ox + 29, oy + PH + 12.5, "50 мм — проверка масштаба", ha="center", va="top",
            fontsize=5.5, color="#333")
    pdf.savefig(fig)
    if png:
        fig.savefig(os.path.join(OUT, png), facecolor="white", dpi=150)
    plt.close(fig)


def preview():
    """Превью: две страницы рядом (уменьшены)."""
    from PIL import Image
    imgs = []
    for name in ("bukifon_v1_4_page1.png", "bukifon_v1_4_page2.png"):
        fp = os.path.join(OUT, name)
        if os.path.exists(fp):
            im = Image.open(fp).convert("RGB")
            im.thumbnail((900, 900))
            imgs.append(im)
    if not imgs:
        return
    w = sum(i.width for i in imgs) + 10
    h = max(i.height for i in imgs)
    canvas = Image.new("RGB", (w, h), "white")
    x = 0
    for im in imgs:
        canvas.paste(im, (x, 0))
        x += im.width + 10
    canvas.save(os.path.join(OUT, "bukifon_v1_4_panel_preview.png"))
    print("preview saved")


def full_preview():
    """Вся панель целиком (масштаб 1:1.3 для иллюстрации)."""
    fig, ax = plt.subplots(figsize=(13.2, 7.4), dpi=170)
    ax.set_xlim(-6, PW + 6)
    ax.set_ylim(PH + 10, -8)
    ax.set_aspect("equal")
    ax.axis("off")
    draw_panel(ax, 0, 0)
    ax.set_title("Букифон v1.4 · панель 340 × 185 мм (габарит Octatrack) · 16 ручек, "
                 "9 + 12 mini-jack, 2 фейдера, 2 × 21 клавиши", fontsize=10, pad=8)
    ax.annotate("", xy=(0, PH + 4), xytext=(PW, PH + 4),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.7))
    ax.text(PW / 2, PH + 5, "340 мм", ha="center", va="top", fontsize=6.5, color="#666")
    ax.annotate("", xy=(PW + 3, 0), xytext=(PW + 3, PH),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.7))
    ax.text(PW + 4, PH / 2, "185 мм", va="center", rotation=90, fontsize=6.5, color="#666")
    fig.savefig(os.path.join(OUT, "bukifon_v1_4_full.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    with PdfPages(os.path.join(OUT, "bukifon_v1_4_panel_1to1.pdf")) as pdf:
        page(pdf, 0.0, 170.0, "Букифон v1.4 · панель 1:1 · левая часть (X 0…170 мм)",
             "bukifon_v1_4_page1.png")
        page(pdf, 160.0, 340.0, "Букифон v1.4 · панель 1:1 · правая часть (X 160…340 мм)",
             "bukifon_v1_4_page2.png")
    preview()
    full_preview()
    print("saved:", OUT)


if __name__ == "__main__":
    main()
