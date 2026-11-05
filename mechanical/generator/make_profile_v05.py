"""make_profile_v05.py — картонный профиль 1:1 (PDF) и сравнение профилей A/B/C (PNG).

PDF: renders/templates/bukifon_v05_wedge8_profile_1to1.pdf
     (единственный файл, который задача v0.5 разрешает вне mechanical/)
PNG: mechanical/preview_v05_compare/profiles.png

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/make_profile_v05.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PDF = os.path.join(ROOT, "renders", "templates", "bukifon_v05_wedge8_profile_1to1.pdf")
PNG_DIR = os.path.join(ROOT, "mechanical", "preview_v05_compare")
OS = os.makedirs(PNG_DIR, exist_ok=True)

A4W, A4H = 297.0, 210.0
FRONT, REAR, DEPTH, ANG = 32.0, 62.0, 210.0, 8.0
R = 4.0


def profile_pts(front, rear, depth, r=0.0, n=24):
    """Контур бокового профиля (Y от задней кромки, Z вверх)."""
    pts = [(0.0, 0.0), (0.0, rear)]
    # верх от зада к переду
    if r > 0:
        # скругление R в переднем верхнем углу: касание сверху за R до кромки
        pts.append((depth - r, front + r * 0 - (depth - r) * 0.0 + (rear - front) * 0.0))
    # считаем верхнюю линию от (0,rear) до (depth - r*tan?, front)
    pts = [(0.0, 0.0), (0.0, rear), (depth, front), (depth, 0.0)]
    if r > 0:
        # фаска R4 на передней кромке: заменяем нижний отрезок передней стенки дугой
        pts = [(0.0, 0.0), (0.0, rear), (depth, front),
               (depth, r)]
        # дуга от (depth, r) к (depth-r, 0) с центром (depth-r, r)
        import math
        arc = []
        for i in range(n + 1):
            a = math.pi / 2 * i / n
            arc.append((depth - r + r * math.cos(a), r - r * math.sin(a)))
        pts += arc[1:]
    else:
        pts = [(0.0, 0.0), (0.0, rear), (depth, front), (depth, 0.0)]
    return pts


def make_pdf():
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(0, A4H)
    ax.set_aspect("equal")
    ax.axis("off")
    ox, oy = 36.0, 30.0

    # рамка листа
    ax.add_patch(Rectangle((5, 5), A4W - 10, A4H - 10, fc="white", ec="#ccc", lw=0.4))
    ax.text(A4W / 2, A4H - 12,
            "БУКИФОН v0.5-B — КАРТОННЫЙ ПРОФИЛЬ 1:1 (клин 8°)",
            ha="center", fontsize=12, fontweight="bold")
    ax.text(A4W / 2, A4H - 18,
            "Печать A4 100% (без «масштабировать по странице»). Вырезать по сплошной, "
            "согнуть/склеить по пунктиру. Проверка: линейка 50 мм ниже.",
            ha="center", fontsize=6.2, color="#444")

    pts = profile_pts(FRONT, REAR, DEPTH, R)
    xs = [ox + p[0] for p in pts]
    ys = [oy + p[1] for p in pts]
    ax.plot(xs, ys, color="#111", lw=1.6)
    ax.fill(xs, ys, color="#eeeeee", zorder=0)

    # место панели (3 мм) — линия над верхом
    ax.plot([ox, ox + DEPTH], [oy + REAR, oy + FRONT], color="#1f4e9c", lw=2.2,
            linestyle=(0, (6, 3)))
    ax.text(ox + DEPTH * 0.52, oy + (FRONT + REAR) / 2 + 7,
            "МЕСТО ПАНЕЛИ 380 × 210 × 3\nнаклеить bukifon_v04_panel_1to1.pdf",
            fontsize=6.4, color="#1f4e9c", ha="center", rotation=-2.1)

    # размеры
    def dim(x1, y1, x2, y2, text, off=0, horiz=True, fs=7):
        ax.annotate("", xy=(x1, y1), xytext=(x2, y2),
                    arrowprops=dict(arrowstyle="<->", lw=0.7, color="#900"))
        ax.text((x1 + x2) / 2 + (0 if horiz else off),
                (y1 + y2) / 2 + (off if horiz else 0), text,
                ha="center", va="center", fontsize=fs, color="#900")

    dim(ox, oy + 0, ox + DEPTH, oy + 0, "210 мм (глубина, Y)", off=-9, fs=7)
    dim(ox, oy + 0, ox, oy + REAR, "62", off=-5, horiz=False, fs=7)
    dim(ox + DEPTH, oy + 0, ox + DEPTH, oy + FRONT, "32", off=5, horiz=False, fs=7)
    # перепад
    ax.annotate("", xy=(ox + 18, oy + FRONT), xytext=(ox + 18, oy + REAR),
                arrowprops=dict(arrowstyle="<->", lw=0.7, color="#060"))
    ax.text(ox + 22, oy + (FRONT + REAR) / 2, "29.5 мм\n(210·tan8°)",
            fontsize=6.6, color="#060", va="center")
    # угол
    ax.add_patch(Arc((ox, oy + REAR), 60, 60, theta1=-8.0, theta2=0.0,
                     color="#060", lw=0.7))
    ax.text(ox + 17, oy + REAR - 4.5, "8°", fontsize=8, color="#060")
    ax.annotate("R4 (запястье)", xy=(ox + DEPTH - 1.5, oy + 1.5),
                xytext=(ox + DEPTH - 52, oy - 8), fontsize=6.4, color="#333",
                arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.text(ox + 4, oy + REAR - 6, "задняя стенка 62", fontsize=6.2, color="#333")

    # линейка 50 мм
    rx, ry = 210.0, 26.0
    ax.plot([rx, rx + 50], [ry, ry], color="#000", lw=1.0)
    for i in range(0, 51):
        h = 4.0 if i % 10 == 0 else (2.5 if i % 5 == 0 else 1.4)
        ax.plot([rx + i, rx + i], [ry, ry + h], color="#000", lw=0.5)
    ax.text(rx + 25, ry - 4, "50 мм — контроль печати 1:1", ha="center", fontsize=6.4)

    # вырез для панели (пунктир) и примечания
    ax.text(ox + 4, oy - 18,
            "Сборка проверки: вырезать профиль, поставить вертикально; на верхнюю "
            "линию наклеить панель 1:1.\nЭкран — картонка 108 × 64.8 на шарнире, "
            "проверить 30/35/45° к панели. Ручки — цилиндры Ø14 × 15.",
            fontsize=6.0, color="#333")
    fig.savefig(PDF, format="pdf")
    plt.close(fig)
    print("PDF:", PDF)


def make_compare():
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=160)
    for label, front, rear, color in (
            ("A — flat (v0.4): 63 / 63", 63.0, 63.0, "#888888"),
            ("B — клин 8°: перед 32, зад 62 (выбран)", 32.0, 62.0, "#c0392b"),
            ("C — клин 12°: перед 32, зад 76.6 (отклонён)", 32.0, 76.6, "#2c6fbb")):
        pts = profile_pts(front, rear, 210.0, 4.0 if front < 63 else 0.0)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], lw=2.2, color=color,
                label=label)
    ax.set_aspect("equal")
    ax.set_xlim(-16, 236)
    ax.set_ylim(-6, 88)
    ax.grid(alpha=0.25, lw=0.5)
    ax.set_xlabel("Y — глубина, мм (зад → перед)")
    ax.set_ylabel("Z — высота, мм")
    ax.set_title("Букифон v0.5: сравнение профилей корпуса (боковая проекция)")
    ax.legend(loc="upper left", fontsize=9)
    ax.annotate("Δ29.5 мм", xy=(210, 47), xytext=(222, 50), fontsize=9, color="#c0392b")
    ax.annotate("Δ44.6 мм", xy=(210, 54), xytext=(222, 62), fontsize=9, color="#2c6fbb")
    fig.tight_layout()
    out = os.path.join(PNG_DIR, "profiles_compare.png")
    fig.savefig(out)
    plt.close(fig)
    print("PNG:", out)


if __name__ == "__main__":
    make_pdf()
    make_compare()
