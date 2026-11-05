#!/usr/bin/env python3
"""Печатные листы 1:1: клавиши Lapka-42 для вырезания + эталонная раскладка.

Выход:
  renders/templates/lapka42_keycaps_1to1.pdf   A4 landscape: 42 колпачка 17.5×16.5 с номерами
  renders/templates/lapka42_layout_1to1.pdf    A4: 2 страницы — левая и правая половины 1:1
  renders/templates/lapka42_keycaps_preview.png
Печать: A4, 100% (проверка — линейка 50 мм).
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
CAP_W, CAP_H = 17.5, 16.5
GAP = 4.0
COLS, ROWS = 6, 7


def scale_bar(ax, x, y, label=True):
    ax.plot([x, x + 50], [y, y], color="#111", lw=1.6)
    for t in (0, 10, 25, 40, 50):
        ax.plot([x + t, x + t], [y - 2.2, y + 2.2], color="#111", lw=0.9)
    if label:
        ax.text(x + 25, y + 4, "50 мм — проверка масштаба (должно быть ровно 50)",
                ha="center", va="bottom", fontsize=6, color="#333")


def cutout_sheet():
    pdf_path = os.path.join(OUT, "lapka42_keycaps_1to1.pdf")
    with PdfPages(pdf_path) as pdf:
        fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, A4W)
        ax.set_ylim(A4H, 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))

        ax.text(A4W / 2, 9, "Букифон · клавиши Lapka-42 для вырезания · масштаб 1:1",
                ha="center", fontsize=12, fontweight="bold")
        ax.text(A4W / 2, 16,
                "Печать A4 100% без масштабирования. Вырезать по внешнему контуру (пунктир). "
                "Колпачок Choc: 17.5 × 16.5 мм, шаг 18 × 17.",
                ha="center", fontsize=6.4, color="#555")

        pitch_x = CAP_W + GAP
        pitch_y = CAP_H + GAP
        grid_w = COLS * pitch_x - GAP
        grid_h = ROWS * pitch_y - GAP
        x0 = (A4W - grid_w) / 2
        y0 = 24 + (A4H - 34 - grid_h) / 2

        n = 1
        for r in range(ROWS):
            for c in range(COLS):
                x = x0 + c * pitch_x
                y = y0 + r * pitch_y
                cx, cy = x + CAP_W / 2, y + CAP_H / 2
                # контур вырезания (внешний)
                ax.add_patch(mp.Rectangle((x - 0.7, y - 0.7), CAP_W + 1.4, CAP_H + 1.4,
                                          fc="none", ec="#888", lw=0.5, ls=(0, (2, 1.5))))
                # колпачок
                ax.add_patch(mp.FancyBboxPatch((x, y), CAP_W, CAP_H,
                                               boxstyle="round,pad=0,rounding_size=2",
                                               fc="#f2f2ee", ec="#111", lw=0.9))
                ax.add_patch(mp.Circle((cx, cy), 0.6, fc="#999", ec="none"))
                ax.text(cx, cy + 2.6, str(n), ha="center", va="center", fontsize=7.5)
                n += 1

        scale_bar(ax, 14, A4H - 12)
        ax.text(A4W - 14, A4H - 13, "42 клавиши = 2 × 21 (левая / правая половина)",
                ha="right", fontsize=6.4, color="#555")
        pdf.savefig(fig)
        plt.close(fig)

        # превью
        fig.savefig(os.path.join(OUT, "lapka42_keycaps_preview.png"),
                    bbox_inches="tight", facecolor="white", dpi=150)
    return pdf_path


def ordered_left():
    """Пространственный порядок (сверху вниз, слева направо) — для нумерации."""
    return sorted(L.LAPKA42_LEFT, key=lambda t: (round(t[1] / 17.0), t[0]))


def layout_sheet():
    pdf_path = os.path.join(OUT, "lapka42_layout_1to1.pdf")
    keys_left = ordered_left()
    x0, y0, x1, y1 = _bbox(keys_left)
    bw, bh = x1 - x0, y1 - y0

    with PdfPages(pdf_path) as pdf:
        for half in ("left", "right"):
            fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_xlim(0, A4W)
            ax.set_ylim(A4H, 0)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))

            title = ("Букифон · эталон Lapka-42 1:1 · ЛЕВАЯ половина (21 клавиша)"
                     if half == "left" else
                     "Букифон · эталон Lapka-42 1:1 · ПРАВАЯ половина (зеркало)")
            ax.text(A4W / 2, 9, title, ha="center", fontsize=12, fontweight="bold")
            ax.text(A4W / 2, 16, "Печать A4 100%. Номера соответствуют листу для вырезания.",
                    ha="center", fontsize=6.4, color="#555")

            ox = (A4W - bw) / 2
            oy = 26 + (A4H - 40 - bh) / 2
            n = 1
            for (x, y, rot) in keys_left:
                px = ox + (x - x0) if half == "left" else ox + (bw - (x - x0))
                py = oy + (y - y0)
                # matplotlib: ось Y инвертирована, поэтому знак поворота берём обратным.
                # Координаты (позиции) клавиш — ровно как в KiCad Lapka-42, без изменений.
                a = -rot if half == "left" else rot
                ax.add_patch(mp.Rectangle((px - CAP_W / 2, py - CAP_H / 2), CAP_W, CAP_H,
                                          angle=a, rotation_point="center",
                                          fc="#eef3f9", ec="#111", lw=0.8))
                ax.text(px, py, str(n), ha="center", va="center", fontsize=6)
                n += 1

            if half == "left":
                # кисть подходит из левого нижнего угла, пальцы — вверх-вправо
                ax.annotate("", xy=(A4W * 0.34, A4H - 40), xytext=(A4W * 0.16, A4H - 12),
                            arrowprops=dict(arrowstyle="-|>", color="#b03", lw=1.4))
                ax.text(A4W * 0.18, A4H - 10, "левая кисть подходит отсюда (слева-снизу)",
                        ha="left", va="bottom", fontsize=7.5, color="#b03")
            else:
                ax.annotate("", xy=(A4W * 0.66, A4H - 40), xytext=(A4W * 0.84, A4H - 12),
                            arrowprops=dict(arrowstyle="-|>", color="#03b", lw=1.4))
                ax.text(A4W * 0.82, A4H - 10, "правая кисть подходит отсюда (справа-снизу)",
                        ha="right", va="bottom", fontsize=7.5, color="#03b")
            scale_bar(ax, 14, A4H - 12)
            pdf.savefig(fig)
            plt.close(fig)
    return pdf_path


def _bbox(keys):
    hw, hh = CAP_W / 2, CAP_H / 2
    xs, ys = [], []
    for x, y, rot in keys:
        a = math.radians(rot)
        ca, sa = math.cos(a), math.sin(a)
        for sx in (-1, 1):
            for sy in (-1, 1):
                xs.append(x + ca * sx * hw - sa * sy * hh)
                ys.append(y + sa * sx * hw + ca * sy * hh)
    return min(xs), min(ys), max(xs), max(ys)


def main():
    print("saved:", cutout_sheet())
    print("saved:", layout_sheet())


if __name__ == "__main__":
    main()
