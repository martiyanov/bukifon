#!/usr/bin/env python3
"""Печатный шаблон панели Букифон 1:1 для эскиза раскладки клавиш.

Выход:
  renders/templates/panel_1to1_left.pdf   A4 landscape, 100% (левая половина)
  renders/templates/panel_1to1_right.pdf  A4 landscape, 100% (правая половина)
  renders/templates/panel_preview.png     превью обеих страниц + инструкция

Печать: A4, масштаб 100% (без «по размеру страницы»). Панель 315×145 мм
шире A4 (297), поэтому она разбита на две страницы с перекрытием 10 мм.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "renders", "templates")
os.makedirs(OUT, exist_ok=True)

W, H = 315.0, 145.0
OVERLAP = 10.0
A4W, A4H = 297.0, 210.0

ZONES = [
    ("верхняя зона: динамики, экран, ручки, плечевые", 0, 0, W, 76, "#f4f4f0"),
    ("зона клавиш: здесь ставим свитчи/колпачки (сетка 18 × 17)", 0, 76, W, H, "#f8f4e8"),
]


def draw_page(pdf, x0, x1, title, hand):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")

    # страница
    ax.add_patch(mp.Rectangle((5, 5), A4W - 10, A4H - 10, fc="white", ec="#bbb", lw=0.6))

    # перенос: панель начинается с отступом 10 мм сверху
    offx, offy = 10.0, 12.0
    # видимая часть панели
    ax.add_patch(mp.FancyBboxPatch((offx, offy), W, H, boxstyle="round,pad=0,rounding_size=7",
                                   lw=1.4, ec="#111", fc="none", zorder=3))
    # рамка кадра (что печатается)
    ax.add_patch(mp.Rectangle((offx, offy), x1 - x0, H, fc="none", ec="#c33", lw=0.8, ls=(0, (2, 2)), zorder=4))

    # зоны
    for name, zx0, zy0, zx1, zy1, color in ZONES:
        ax.add_patch(mp.Rectangle((offx + zx0, offy + zy0), zx1 - zx0, zy1 - zy0,
                                  fc=color, ec="none", zorder=1))
    ax.plot([offx, offx + W], [offy + 76, offy + 76], color="#a08a55", lw=0.7, ls=(0, (6, 3)), zorder=3)

    # сетка 10 мм
    for gx in range(0, int(W) + 1, 10):
        ax.plot([offx + gx, offx + gx], [offy, offy + H], color="#e6e6e6", lw=0.25, zorder=2)
    for gy in range(0, int(H) + 1, 10):
        ax.plot([offx, offx + W], [offy + gy, offy + gy], color="#e6e6e6", lw=0.25, zorder=2)

    # сетка клавиш 18 × 17 в зоне клавиш (от Y=76)
    y = 76.0
    row = 0
    while y + 17 <= H + 0.1:
        xx = 0.0
        while xx + 18 <= W + 0.1:
            ax.add_patch(mp.Rectangle((offx + xx, offy + y), 18, 17, fc="none",
                                      ec="#c9b98a", lw=0.35, zorder=3))
            ax.add_patch(mp.Rectangle((offx + xx + 2, offy + y + 1.5), 14, 14, fc="none",
                                      ec="#e0d5b5", lw=0.25, zorder=3))
            xx += 18
        y += 17
        row += 1

    # верхняя зона: экран, ручки, динамики (ориентиры)
    cx, cy, sw, sh = 157.5, 42.0, 60.0, 46.0
    ax.add_patch(mp.Rectangle((offx + cx - sw / 2, offy + cy - sh / 2), sw, sh,
                              fc="none", ec="#333", lw=1.0, zorder=4))
    ax.text(offx + cx, offy + cy, "ЭКРАН 60×46\n(окно)", ha="center", va="center", fontsize=6, color="#444")
    for i, (kx, ky) in enumerate([(30, 26), (66, 26), (30, 56), (66, 56),
                                  (249, 26), (285, 26), (249, 56), (285, 56)]):
        ax.add_patch(mp.Circle((offx + kx, offy + ky), 9, fc="none", ec="#666", lw=0.7, ls=(0, (2, 2)), zorder=4))
        ax.text(offx + kx, offy + ky, f"E{i+1}", ha="center", va="center", fontsize=5, color="#777")
    for i, (sx, sy) in enumerate([(145, 8), (170, 8)]):
        ax.add_patch(mp.Circle((offx + sx, offy + sy), 8, fc="none", ec="#666", lw=0.7, zorder=4))
        ax.text(offx + sx, offy + sy, f"SPK{i+1}", ha="center", va="center", fontsize=5, color="#777")
    for i, (fx, fy0, fy1) in enumerate([(147, 84, 124), (167, 84, 124)]):
        ax.add_patch(mp.FancyBboxPatch((offx + fx - 4.5, offy + fy0), 9, fy1 - fy0,
                                       boxstyle="round,pad=0,rounding_size=3",
                                       fc="none", ec="#666", lw=0.7, ls=(0, (2, 2)), zorder=4))
        ax.text(offx + fx, offy + fy1 + 4, f"SL{i+1}", ha="center", va="top", fontsize=5, color="#777")

    # стрелки направления кистей (подсказка, как руки подходят)
    if hand == "left":
        ax.annotate("", xy=(offx + 70, offy + 128), xytext=(offx + 8, offy + 150),
                    arrowprops=dict(arrowstyle="-|>", color="#b03", lw=1.4))
        ax.text(offx + 10, offy + 152, "ЛЕВАЯ КИСТЬ: подходит\nслева-снизу, мизинец — внешний край",
                fontsize=6, color="#b03", va="bottom")
    else:
        ax.annotate("", xy=(offx + W - 70, offy + 128), xytext=(offx + W - 8, offy + 150),
                    arrowprops=dict(arrowstyle="-|>", color="#03b", lw=1.4))
        ax.text(offx + W - 10, offy + 152, "ПРАВАЯ КИСТЬ: подходит\nсправа-снизу, мизинец — внешний край",
                fontsize=6, color="#03b", va="bottom", ha="right")

    # ось симметрии и перекрытие
    ax.plot([offx + 157.5, offx + 157.5], [offy, offy + H], color="#999", lw=0.6, ls=(0, (8, 4)), zorder=3)
    ax.text(offx + 157.5, offy + 2, "центр панели 157.5", fontsize=5, color="#888", ha="center", va="top")

    # размеры и масштаб
    ax.annotate("", xy=(offx, offy + H + 5), xytext=(offx + W, offy + H + 5),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.7))
    ax.text(offx + W / 2, offy + H + 6.5, "315 мм (панель целиком; страница = её часть)", ha="center",
            va="top", fontsize=6, color="#666")
    ax.annotate("", xy=(offx - 5, offy), xytext=(offx - 5, offy + H),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.7))
    ax.text(offx - 6.5, offy + H / 2, "145 мм", va="center", rotation=90, fontsize=6, color="#666",
            ha="center")
    # линейка 50 мм
    ax.plot([offx + 5, offx + 55], [offy + H + 12, offy + H + 12], color="#111", lw=1.6)
    for t in (0, 25, 50):
        ax.plot([offx + 5 + t, offx + 5 + t], [offy + H + 10, offy + H + 14], color="#111", lw=0.9)
    ax.text(offx + 30, offy + H + 16, "50 мм — проверка масштаба (должно быть ровно 50)", ha="center",
            va="top", fontsize=5.5, color="#333")

    # заголовок/инструкция
    ax.text(A4W / 2, 7.5, title, ha="center", va="top", fontsize=9, color="#111")
    ax.text(A4W / 2, 4.5, "Печать A4, масштаб 100% (без «по размеру страницы»). "
                          "Страницы накладываются друг на друга на 10 мм по центру панели.",
            ha="center", va="top", fontsize=5.5, color="#555")

    pdf.savefig(fig)
    plt.close(fig)


def preview():
    fig, ax = plt.subplots(figsize=(11.7, 8.3), dpi=150)
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.Rectangle((0, 0), A4W, A4H, fc="white", ec="#bbb"))
    ax.text(A4W / 2, 12, "Букифон — печатный шаблон раскладки 1:1", ha="center", fontsize=15, fontweight="bold")
    ax.text(A4W / 2, 24, "Две страницы A4 (левая и правая половины панели 315 × 145 мм).",
            ha="center", fontsize=9)
    lines = [
        "1. Распечатайте оба PDF на A4 в масштабе 100% (проверьте линейку 50 мм).",
        "2. Наложите листы с перекрытием 10 мм, склейте по оси «центр панели 157.5».",
        "3. Положите на шаблон реальные Choc-свитчи (14×14) с колпачками 17.5×16.5 — или вырежьте",
        "   бумажные квадратики 17.5×16.5 и разложите их так, как удобно вашим рукам.",
        "4. Обведите получившуюся раскладку маркером, сфотографируйте сверху строго перпендикулярно",
        "   (телефон на штативе/книгах), приложите линейку в кадр — по ней я выставлю масштаб.",
        "5. Пришлите фото + подпишите: где левая/правая кисть, какие ряды оставить, где большие пальцы.",
    ]
    for i, t in enumerate(lines):
        ax.text(20, 45 + i * 12, t, fontsize=8.2, ha="left")
    ax.add_patch(mp.FancyBboxPatch((20, 120), A4W - 40, 70, boxstyle="round,pad=6,rounding_size=4",
                                   fc="#f7f3e8", ec="#c9b98a"))
    ax.text(A4W / 2, 132, "Альтернатива без принтера:", ha="center", fontsize=9, fontweight="bold")
    alt = [
        "• Keyboard Layout Editor (keyboard-layout-editor.com) — расставить клавиши, повернуть кластеры,",
        "  прислать ссылку-permalink или JSON;",
        "• Ergogen (ergogen.xyz) — YAML с splay/rotation, если хочется параметрически;",
        "• Inkscape / Figma — SVG с сеткой 18×17 мм (пришлите .svg);",
        "• лист в клетку + линейка: отмечайте центры клавиш, шаг 18 × 17 мм.",
    ]
    for i, t in enumerate(alt):
        ax.text(26, 144 + i * 8, t, fontsize=7.4, ha="left")
    fig.savefig(os.path.join(OUT, "panel_preview.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    with PdfPages(os.path.join(OUT, "panel_1to1_left.pdf")) as pdf:
        draw_page(pdf, 0, 162.5, "Шаблон 1:1 — левая половина панели (X 0…162.5 мм)", "left")
    with PdfPages(os.path.join(OUT, "panel_1to1_right.pdf")) as pdf:
        draw_page(pdf, 152.5, 315, "Шаблон 1:1 — правая половина панели (X 152.5…315 мм)", "right")
    preview()
    print("saved:", OUT)


if __name__ == "__main__":
    main()
