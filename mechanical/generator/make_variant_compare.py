"""make_variant_compare.py — сравнение профилей A/B/C для заказчика.

Выход: mechanical/preview_v05_compare/side_profile_all.png
  A flat (0°, 63/63), B клин 8° (32/61.5), C клин 12° (32/76.6) в одном масштабе,
  подписи углов, высот и перепадов, линия стола.
"""
import os
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "mechanical", "preview_v05_compare", "side_profile_all.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

DEPTH = 210.0
VARIANTS = [
    ("A — flat (0°)", 0.0, 63.0, 63.0, "#777777", "-"),
    ("B — клин 8° (базовый v1.0-rc)", 8.0, 32.0, 61.5, "#c0392b", "-"),
    ("C — клин 12° + отсек + подставка", 12.0, 32.0, 76.6, "#2c6fbb", "-"),
]


def contour(front, rear, r=4.0):
    pts = [(0.0, 0.0)]
    if abs(rear - front) > 0.1:
        # наклонная верхняя линия с фаской R4 у передней кромки
        pts += [(0.0, rear), (DEPTH - r, front + r * (rear - front) / DEPTH)]
    else:
        pts += [(0.0, rear), (DEPTH - r, front)]
    # дуга R4: от верхней линии к передней стенке
    cx, cy = DEPTH - r, front - r * 0.35
    for i in range(1, 13):
        a = math.pi / 2 * i / 12
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts += [(DEPTH, 0.0)]
    return pts


def main():
    fig, ax = plt.subplots(figsize=(11.5, 5.6), dpi=170)
    for label, ang, front, rear, color, ls in VARIANTS:
        pts = contour(front, rear)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=2.4, ls=ls,
                label=f"{label}: перед {front:.0f} / зад {rear:.0f} мм")
        ax.annotate(f"{ang:.0f}°", xy=(18, rear - 2.0), fontsize=10, color=color,
                    fontweight="bold")
    ax.axhline(0, color="#444", lw=0.8)
    ax.text(4, -6, "стол (Z=0)", fontsize=7, color="#444")
    ax.set_aspect("equal")
    ax.set_xlim(-18, 250)
    ax.set_ylim(-10, 92)
    ax.grid(alpha=0.22, lw=0.5)
    ax.set_xlabel("Y — глубина, мм (зад → перед)")
    ax.set_ylabel("Z — высота, мм")
    ax.set_title("Букифон v0.5: сравнение печатных вариантов корпуса (боковой профиль)")
    ax.legend(loc="upper left", fontsize=8.6)
    ax.annotate("Δ29.5 мм (210·tan8°)", xy=(208, 47), xytext=(218, 52), fontsize=8,
                color="#c0392b")
    ax.annotate("Δ44.6 мм (210·tan12°)", xy=(208, 54), xytext=(218, 66), fontsize=8,
                color="#2c6fbb")
    ax.text(196, 12, "все варианты: глубина 210, ширина 380,\nпанель 193+190 с шипом, R4",
            fontsize=7.2, color="#333")
    fig.tight_layout()
    fig.savefig(OUT)
    print("PNG:", OUT)


if __name__ == "__main__":
    main()
