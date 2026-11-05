#!/usr/bin/env python3
"""Печатные листы 1:1: Elektron Octatrack MKII (верхняя панель).

Габарит: 340 × 185 × 63 мм (Elektron/Thomann/CDM; 128×64 OLED).
Верхняя поверхность панели: 340 × 178 мм (промер по официальному виду сверху,
elektron.se/octatrack-mkii-top, точность ±1 мм). Ключевые размеры:
  * экран-модуль 73.8 × 54.8 мм, левый край X=125.3, верх Y=28.5;
  * 8 энкодеров Ø14: X = 246.0 / 273.0 / 300.3 / 327.7, Y = 42.6 / 69.7;
  * кроссфейдер: X 248.2…300.6, Y 103.8…120.6 (ход 52 мм);
  * большие A и B: (229.6, 115.7) и (323.8, 115.9), Ø16;
  * 16 триг-кнопок: шаг 18.9 мм, первая X=20.7, Y=149.9, размер 16.4 × 15.3;
  * 4 малые ручки A/B/C/D: Y=47.8, X = 49.8 / 65.3 / 81.4 / 97.5, Ø10.

Выход: renders/templates/octatrack_mk2_1to1.pdf (3 страницы A4 landscape):
  стр.1 — левая часть панели 1:1 (X 0…160 мм);
  стр.2 — правая часть 1:1 (X 150…340 мм, перекрытие 10 мм);
  стр.3 — триг-ряд и экран Octatrack 1:1, наложенные на нашу панель 315×145.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "renders", "templates")
os.makedirs(OUT, exist_ok=True)

A4W, A4H = 297.0, 210.0

OT_W, OT_D = 340.0, 178.0
SCR = dict(x=125.3, y=28.5, w=73.8, h=54.8)
SCR_ACT = dict(w=45.0, h=22.5)
ENC_X = [246.0, 273.0, 300.3, 327.7]
ENC_Y = [42.6, 69.7]
ENC_D = 14.0
BIG = [(229.6, 115.7, "A"), (323.8, 115.9, "B")]
BIG_D = 16.0
XFADE = dict(x0=248.2, x1=300.6, y0=103.8, y1=120.6)
TRIG = dict(x0=20.7, pitch=18.9, y=149.9, w=16.4, h=15.3, n=16)
SMALL = [(49.8, 47.8, "A"), (65.3, 47.8, "B"), (81.4, 47.8, "C"), (97.5, 47.8, "D")]

PANEL_W, PANEL_H = 315.0, 145.0


def scale_bar(ax, x, y):
    ax.plot([x, x + 50], [y, y], color="#111", lw=1.6)
    for t in (0, 10, 25, 40, 50):
        ax.plot([x + t, x + t], [y - 2.2, y + 2.2], color="#111", lw=0.9)
    ax.text(x + 25, y + 4.2, "50 мм — проверка масштаба (ровно 50)", ha="center", va="bottom",
            fontsize=6, color="#333")


def draw_ot(ax, dx, dy, full=True):
    # корпус
    ax.add_patch(mp.FancyBboxPatch((dx, dy), OT_W, OT_D, boxstyle="round,pad=0,rounding_size=4",
                                   fc="#f2f2ef", ec="#222", lw=1.5))
    for gx in range(0, int(OT_W) + 1, 10):
        ax.plot([dx + gx, dx + gx], [dy, dy + OT_D], color="#e4e4df", lw=0.22, zorder=1)
    for gy in range(0, int(OT_D) + 1, 10):
        ax.plot([dx, dx + OT_W], [dy + gy, dy + gy], color="#e4e4df", lw=0.22, zorder=1)

    # экран-модуль
    ax.add_patch(mp.FancyBboxPatch((dx + SCR["x"], dy + SCR["y"]), SCR["w"], SCR["h"],
                                   boxstyle="round,pad=0,rounding_size=1.5",
                                   fc="#161616", ec="#555", lw=1.0, zorder=3))
    aw, ah = SCR_ACT["w"], SCR_ACT["h"]
    ax.add_patch(mp.Rectangle((dx + SCR["x"] + (SCR["w"] - aw) / 2, dy + SCR["y"] + 5),
                              aw, ah, fc="#0d1a0d", ec="#7a7", lw=0.5, zorder=4))
    ax.text(dx + SCR["x"] + SCR["w"] / 2, dy + SCR["y"] + 5 + ah / 2, "128 × 64 OLED",
            ha="center", va="center", fontsize=5.2, color="#9c9", zorder=5)
    ax.text(dx + SCR["x"], dy + SCR["y"] + SCR["h"] + 1.5, "экран-модуль 73.8 × 54.8",
            fontsize=5.4, color="#444", va="top", zorder=5)

    # 8 энкодеров
    for r, y in enumerate(ENC_Y):
        for c, x in enumerate(ENC_X):
            ax.add_patch(mp.Circle((dx + x, dy + y), ENC_D / 2, fc="#2b2b2b", ec="#888", lw=0.8, zorder=4))
            ax.add_patch(mp.Circle((dx + x, dy + y), 1.1, fc="#ddd", ec="none", zorder=5))
            ax.text(dx + x, dy + y + ENC_D / 2 + 1.2, "ABCD"[c] if r == 0 else "EFGH"[c],
                    ha="center", va="top", fontsize=4.6, color="#444", zorder=5)
    ax.text(dx + sum(ENC_X) / 4, dy + ENC_Y[0] - 10, "8 энкодеров, сетка 27 × 27 мм",
            ha="center", fontsize=5.2, color="#666", zorder=5)

    # большие A/B + кроссфейдер
    for x, y, name in BIG:
        ax.add_patch(mp.Circle((dx + x, dy + y), BIG_D / 2, fc="#2b2b2b", ec="#888", lw=0.8, zorder=4))
        ax.add_patch(mp.Circle((dx + x, dy + y), 1.3, fc="#ddd", ec="none", zorder=5))
        ax.text(dx + x, dy + y + BIG_D / 2 + 1.2, name, ha="center", va="top", fontsize=5, color="#444")
    x0, x1, y0, y1 = XFADE["x0"], XFADE["x1"], XFADE["y0"], XFADE["y1"]
    ax.add_patch(mp.Rectangle((dx + x0, dy + y0), x1 - x0, y1 - y0, fc="#dcdcd6", ec="#444", lw=0.7, zorder=4))
    ax.add_patch(mp.Rectangle((dx + x0 + 4, dy + y0 + 2), 9, y1 - y0 - 4, fc="#333", ec="#111", lw=0.5, zorder=5))
    ax.text(dx + (x0 + x1) / 2, dy + y1 + 1.6, "кроссфейдер 52 мм", ha="center", va="top",
            fontsize=5, color="#444")
    # риски кроссфейдера
    for t in range(1, 12):
        xx = dx + x0 + (x1 - x0) * t / 12
        ax.plot([xx, xx], [dy + y0 + 1, dy + y1 - 1], color="#999", lw=0.3, zorder=5)

    # 16 триг-кнопок
    for i in range(TRIG["n"]):
        cx = dx + TRIG["x0"] + i * TRIG["pitch"]
        ax.add_patch(mp.FancyBboxPatch((cx - TRIG["w"] / 2, dy + TRIG["y"] - TRIG["h"] / 2),
                                       TRIG["w"], TRIG["h"],
                                       boxstyle="round,pad=0,rounding_size=1.4",
                                       fc="#e9e9e5", ec="#333", lw=0.6, zorder=4))
        ax.text(cx, dy + TRIG["y"], str(i + 1), ha="center", va="center", fontsize=4.4, color="#222", zorder=5)
    ax.text(dx + (TRIG["x0"] + TRIG["x0"] + 15 * TRIG["pitch"]) / 2, dy + TRIG["y"] + TRIG["h"] / 2 + 1.4,
            "16 триг-кнопок: шаг 18.9 мм", ha="center", va="top", fontsize=5.2, color="#444")

    # 4 малые ручки A-D
    for x, y, name in SMALL:
        ax.add_patch(mp.Circle((dx + x, dy + y), 5.0, fc="#2b2b2b", ec="#888", lw=0.7, zorder=4))
        ax.text(dx + x, dy + y + 6.2, name, ha="center", va="top", fontsize=4.2, color="#555")

    # зоны, которые не прорисовываются
    ax.add_patch(mp.Rectangle((dx + 8, dy + 26), 112, 118, fc="none", ec="#c00", lw=0.7, ls=(0, (3, 2))))
    ax.text(dx + 64, dy + 84, "FUNC / транспорт / треки /\nрекорд — не прорисовываются",
            ha="center", va="center", fontsize=5.4, color="#c00", zorder=5)


def page_part(pdf, x_from, x_to, title, png=None):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))

    ax.text(A4W / 2, 9, title, ha="center", fontsize=11.5, fontweight="bold")
    ax.text(A4W / 2, 15.5, "Габарит 340 × 185 × 63 мм, OLED 128×64. Печать A4 100%, "
                           "внутренние размеры — промер по официальному виду сверху (±1 мм).",
            ha="center", fontsize=5.6, color="#555")

    offx, offy = 12.0, 26.0
    show_w = x_to - x_from
    # рисуем панель целиком, обрезая окном
    ax.add_patch(mp.Rectangle((offx, offy), show_w, OT_D, fc="#f7f7f4", ec="#222", lw=1.5))
    n_before = len(ax.get_children())
    draw_ot(ax, offx - x_from, offy)
    # обрезаем всё, что нарисовано для панели, окном страницы
    clip = mp.Rectangle((offx, offy), show_w, OT_D, transform=ax.transData)
    for art in ax.get_children()[n_before:]:
        try:
            art.set_clip_on(True)
            art.set_clip_path(clip)
        except Exception:
            pass
    ax.add_patch(mp.Rectangle((offx, offy), show_w, OT_D, fc="none", ec="#c33", lw=0.7, ls=(0, (2, 2))))
    # перекрытие
    ov = 10.0
    if x_from > 0:
        ax.add_patch(mp.Rectangle((offx, offy), ov, OT_D, fc="#ffffee", ec="none", alpha=0.5, zorder=2))
    ax.text(offx + show_w / 2, offy + OT_D + 5, f"участок панели X {x_from:.0f}…{x_to:.0f} мм",
            ha="center", va="bottom", fontsize=6.2, color="#666")
    scale_bar(ax, 14, A4H - 12)
    pdf.savefig(fig)
    if png:
        fig.savefig(os.path.join(OUT, png), facecolor="white", dpi=150)
    plt.close(fig)


def page_overlay(pdf, png=None):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))
    ax.text(A4W / 2, 9, "Octatrack MKII 1:1 на панели Букифон 315 × 145: триг-ряд, экран, кроссфейдер",
            ha="center", fontsize=10.5, fontweight="bold")
    ax.text(A4W / 2, 15.5, "Триг-ряд Octatrack (312.9 мм) почти точно ложится на нашу панель 315 мм. "
                           "8 энкодеров Octatrack выходят за край на ~13 мм — видно, где нужен сдвиг/уплотнение.",
            ha="center", fontsize=5.8, color="#555")

    px, py, shown = 2.0, 28.0, 289.0
    ax.add_patch(mp.Rectangle((px, py), shown, PANEL_H, fc="#f7f7f4", ec="#222", lw=1.5))
    ax.plot([px + shown, px + shown], [py, py + PANEL_H], color="#c33", lw=0.8, ls=(0, (3, 2)))
    # триг-ряд на нашей панели
    for i in range(TRIG["n"]):
        cx = px + TRIG["x0"] + i * TRIG["pitch"]
        ax.add_patch(mp.FancyBboxPatch((cx - TRIG["w"] / 2, py + 112), TRIG["w"], TRIG["h"],
                                       boxstyle="round,pad=0,rounding_size=1.4",
                                       fc="#e9f0f7", ec="#4a6b8a", lw=0.6))
        ax.text(cx, py + 112 + TRIG["h"] / 2, str(i + 1), ha="center", va="center", fontsize=4.2, color="#24384a")
    # экран
    ax.add_patch(mp.FancyBboxPatch((px + 16, py + 26), SCR["w"], SCR["h"],
                                   boxstyle="round,pad=0,rounding_size=1.5", fc="#161616", ec="#555", lw=0.9))
    ax.text(px + 16 + SCR["w"] / 2, py + 26 + SCR["h"] / 2, "экран 1:1\n73.8 × 54.8",
            ha="center", va="center", fontsize=4.6, color="#9c9")
    # кроссфейдер
    ax.add_patch(mp.Rectangle((px + 196, py + 96), XFADE["x1"] - XFADE["x0"], 12,
                              fc="#dcdcd6", ec="#444", lw=0.7))
    ax.text(px + 196 + (XFADE["x1"] - XFADE["x0"]) / 2, py + 93, "кроссфейдер 52 мм", ha="center",
            va="bottom", fontsize=5, color="#444")
    ax.text(px + 300, py + 130, "← 13 мм", ha="left", va="center", fontsize=6, color="#c33")
    ax.text(px + 8, py + 132, "нижняя зона: клавиши Lapka-42 / триг-ряд", fontsize=5.4, color="#a08a55")
    ax.annotate("", xy=(px, py + PANEL_H + 5), xytext=(px + shown, py + PANEL_H + 5),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(px + shown / 2, py + PANEL_H + 6, "289 из 315 мм (1:1); правая часть — продолжение на A3",
            ha="center", va="top", fontsize=6.2, color="#666")
    scale_bar(ax, 14, A4H - 12)
    pdf.savefig(fig)
    if png:
        fig.savefig(os.path.join(OUT, png), facecolor="white", dpi=150)
    plt.close(fig)


def preview():
    """Превью: три страницы рядом (уменьшены)."""
    from PIL import Image
    imgs = []
    for name in ("octatrack_mk2_page1.png", "octatrack_mk2_page2.png", "octatrack_mk2_overlay.png"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
            im.thumbnail((820, 820))
            imgs.append(im)
    if not imgs:
        return
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + 10 * (len(imgs) - 1)
    canvas = Image.new("RGB", (w, h), "white")
    y = 0
    for im in imgs:
        canvas.paste(im, (0, y))
        y += im.height + 10
    canvas.save(os.path.join(OUT, "octatrack_mk2_preview.png"))


def main():
    with PdfPages(os.path.join(OUT, "octatrack_mk2_1to1.pdf")) as pdf:
        page_part(pdf, 0.0, 160.0, "Elektron Octatrack MKII · 1:1 · левая часть панели (X 0…160 мм)",
                  "octatrack_mk2_page1.png")
        page_part(pdf, 150.0, 340.0, "Elektron Octatrack MKII · 1:1 · правая часть панели (X 150…340 мм)",
                  "octatrack_mk2_page2.png")
        page_overlay(pdf, "octatrack_mk2_overlay.png")
    preview()
    print("saved:", os.path.join(OUT, "octatrack_mk2_1to1.pdf"))


if __name__ == "__main__":
    main()
