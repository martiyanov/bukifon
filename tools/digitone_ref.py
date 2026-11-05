#!/usr/bin/env python3
"""Печатные листы 1:1: блок «экран + ручки» как у Elektron Digitone II.

Габарит Digitone II: 215 × 176 × 63 мм (Электрон/Thomann/Reverb).
Внутренние размеры (экран, ручки) измерены по официальному виду сверху
(elektron.se, Digitone-II-top) и приведены с точностью ±1 мм:
  * экран-модуль (безель): 73.4 × 51.0 мм, левый край X=31.8, верх Y=22.1;
  * активное поле 128×64: 56.5 × 28.2 мм;
  * 8 энкодеров Ø15: сетка 26 × 26 мм, X = 119.1 / 145.1 / 171.1 / 197.1,
    Y = 31.1 / 57.1;
  * ручки MAIN VOLUME и LEVEL/DATA: X = 14.0, Y = 28.1 / 56.3, Ø15.

Выход:
  renders/templates/digitone2_top_1to1.pdf   — 2 страницы A4 landscape:
      стр.1: панель Digitone II 1:1 (для сверки/обмера);
      стр.2: тот же блок, наложенный на нашу панель 315×145 (1:1).
  renders/templates/digitone2_top_preview.png
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

# --- Digitone II (мм) --------------------------------------------------------
DG_W, DG_D = 215.0, 176.0
SCR = dict(x=31.8, y=22.1, w=73.4, h=51.0)          # безель экрана
SCR_ACTIVE = dict(w=56.5, h=28.2)                    # поле 128×64
KNOB_D = 15.0
VOL_KNOBS = [(14.0, 28.1), (14.0, 56.3)]
ENC_X = [119.1, 145.1, 171.1, 197.1]
ENC_Y = [31.1, 57.1]
ENC_LABELS = [["A", "B", "C", "D"], ["E", "F", "G", "H"]]

# --- наша панель v1.0/v1.3 -------------------------------------------------
PANEL_W, PANEL_H = 315.0, 145.0


def scale_bar(ax, x, y):
    ax.plot([x, x + 50], [y, y], color="#111", lw=1.6)
    for t in (0, 10, 25, 40, 50):
        ax.plot([x + t, x + t], [y - 2.2, y + 2.2], color="#111", lw=0.9)
    ax.text(x + 25, y + 4, "50 мм — проверка масштаба (ровно 50)", ha="center",
            va="bottom", fontsize=6, color="#333")


def draw_digitone_block(ax, dx, dy, with_labels=True):
    """Рисует блок Digitone II в координатах листа со смещением (dx, dy)."""
    # экран (безель + активное поле)
    ax.add_patch(mp.FancyBboxPatch((dx + SCR["x"], dy + SCR["y"]), SCR["w"], SCR["h"],
                                   boxstyle="round,pad=0,rounding_size=1.5",
                                   fc="#1b1b1b", ec="#555", lw=1.0))
    act_w, act_h = SCR_ACTIVE["w"], SCR_ACTIVE["h"]
    ax.add_patch(mp.Rectangle((dx + SCR["x"] + (SCR["w"] - act_w) / 2, dy + SCR["y"] + 4.5),
                              act_w, act_h, fc="#0d1a0d", ec="#7a7", lw=0.5))
    if with_labels:
        ax.text(dx + SCR["x"] + SCR["w"] / 2, dy + SCR["y"] + 4.5 + act_h / 2,
                "128 × 64 OLED", ha="center", va="center", fontsize=5.5, color="#9c9")
        ax.text(dx + SCR["x"], dy + SCR["y"] + SCR["h"] + 1.6, "экран-модуль 73.4 × 51.0",
                ha="left", va="top", fontsize=5.6, color="#444")

    # MAIN VOLUME / LEVEL-DATA
    for (x, y), name in zip(VOL_KNOBS, ("MAIN\nVOLUME", "LEVEL /\nDATA")):
        ax.add_patch(mp.Circle((dx + x, dy + y), KNOB_D / 2, fc="#2a2a2a", ec="#888", lw=0.8))
        ax.add_patch(mp.Circle((dx + x, dy + y), 1.1, fc="#ccc", ec="none"))
        ax.text(dx + x, dy + y + KNOB_D / 2 + 1.4, name, ha="center", va="top",
                fontsize=5.2, color="#444", linespacing=1.4)
    # 8 энкодеров
    for r, row in enumerate(ENC_Y):
        for c, x in enumerate(ENC_X):
            ax.add_patch(mp.Circle((dx + x, dy + row), KNOB_D / 2, fc="#2a2a2a", ec="#888", lw=0.8))
            ax.add_patch(mp.Circle((dx + x, dy + row), 1.1, fc="#ccc", ec="none"))
            ax.text(dx + x, dy + row + KNOB_D / 2 + 1.2, ENC_LABELS[r][c],
                    ha="center", va="top", fontsize=5.2, color="#444")


def page_digitone(pdf):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))

    ax.text(A4W / 2, 9, "Elektron Digitone II · верхняя панель 1:1 · экран + 8 энкодеров",
            ha="center", fontsize=11.5, fontweight="bold")
    ax.text(A4W / 2, 15.5, "Габарит 215 × 176 × 63 мм. Внутренние размеры — промер по официальному "
                           "виду сверху, ±1 мм. Печать A4 100%.",
            ha="center", fontsize=5.8, color="#555")

    ox, oy = (A4W - DG_W) / 2, 26
    ax.add_patch(mp.FancyBboxPatch((ox, oy), DG_W, DG_D,
                                   boxstyle="round,pad=0,rounding_size=4",
                                   fc="#f2f2ef", ec="#222", lw=1.6))
    # сетка 10 мм
    for gx in range(0, int(DG_W) + 1, 10):
        ax.plot([ox + gx, ox + gx], [oy, oy + DG_D], color="#e3e3de", lw=0.25)
    for gy in range(0, int(DG_D) + 1, 10):
        ax.plot([ox, ox + DG_W], [oy + gy, oy + gy], color="#e3e3de", lw=0.25)
    draw_digitone_block(ax, ox, oy)
    ax.text(ox + DG_W / 2, oy + DG_D - 8, "нижняя часть панели: 16 триг-кнопок, транспорт, "
                                          "страницы (не прорисовываются)",
            ha="center", va="top", fontsize=5.6, color="#999")
    # размеры
    ax.annotate("", xy=(ox, oy + DG_D + 5), xytext=(ox + DG_W, oy + DG_D + 5),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(ox + DG_W / 2, oy + DG_D + 6, "215 мм", ha="center", va="top", fontsize=6.5, color="#666")
    ax.annotate("", xy=(ox - 5, oy), xytext=(ox - 5, oy + DG_D),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(ox - 6, oy + DG_D / 2, "176 мм", va="center", rotation=90, fontsize=6.5, color="#666")
    scale_bar(ax, 14, A4H - 12)
    pdf.savefig(fig)
    plt.close(fig)


def page_on_our_panel(pdf):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(A4H, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))

    ax.text(A4W / 2, 9, "Букифон · панель 315 × 145 · блок Digitone II наложен 1:1",
            ha="center", fontsize=11.5, fontweight="bold")
    ax.text(A4W / 2, 15.5, "Проверка, как ляжет «экран + 8 энкодеров» Elektron на нашу панель. "
                           "Справа остаётся свободная зона под динамики/слайдеры/разъёмы.",
            ha="center", fontsize=5.8, color="#555")

    px, py = 2, 28
    shown_w = 289.0          # A4 297 - 2*2 мм поля; правая часть 26 мм — на листе A3
    ax.add_patch(mp.Rectangle((px, py), shown_w, PANEL_H, fc="#f7f7f4", ec="#222", lw=1.6))
    ax.plot([px + shown_w, px + shown_w], [py, py + PANEL_H], color="#c33", lw=0.8, ls=(0, (3, 2)))
    ax.text(px + shown_w - 1, py + PANEL_H - 2, "панель 315 мм: правая часть 26 мм —\nпродолжение на листе A3",
            ha="right", va="top", fontsize=5.0, color="#c33")
    for gx in range(0, int(shown_w) + 1, 10):
        ax.plot([px + gx, px + gx], [py, py + PANEL_H], color="#ecece7", lw=0.25)
    for gy in range(0, int(PANEL_H) + 1, 10):
        ax.plot([px, px + shown_w], [py + gy, py + gy], color="#ecece7", lw=0.25)

    dx, dy = px + 6, py + 4
    draw_digitone_block(ax, dx, dy)

    # свободная зона справа
    free_x = dx + DG_W + 2
    free_w = px + shown_w - 1 - free_x
    ax.add_patch(mp.Rectangle((free_x, py + 6), free_w, PANEL_H - 12,
                              fc="#f0f6f0", ec="#7a9", lw=0.8, ls=(0, (4, 3))))
    ax.text(free_x + free_w / 2, py + PANEL_H / 2,
            "свободно\n~%d × %d мм" % (int(free_w), int(PANEL_H - 12)),
            ha="center", va="center", fontsize=6.4, color="#3a6")
    # нижняя зона под клавиши
    ax.add_patch(mp.Rectangle((px + 2, py + 84), PANEL_W - 4, PANEL_H - 88,
                              fc="#fbf7ec", ec="#c9b98a", lw=0.7, ls=(0, (4, 3))))
    ax.text(px + PANEL_W / 2, py + 86, "нижняя зона под клавиши Lapka-42 (см. шаблон панели)",
            ha="center", va="top", fontsize=5.8, color="#a08a55")
    ax.annotate("", xy=(px, py + PANEL_H + 5), xytext=(px + shown_w, py + PANEL_H + 5),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(px + shown_w / 2, py + PANEL_H + 6, "289 из 315 мм (1:1)", ha="center", va="top",
            fontsize=6.5, color="#666")
    scale_bar(ax, 14, A4H - 12)
    pdf.savefig(fig)
    plt.close(fig)


def preview():
    fig, axs = plt.subplots(2, 1, figsize=(10.5, 12.5), dpi=110)
    for ax, (kind, title) in zip(axs, [("dg", "Digitone II 1:1"), ("our", "Блок Digitone II на панели Букифон 1:1")]):
        ax.set_xlim(0, A4W)
        ax.set_ylim(A4H, 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd"))
        ax.set_title(title, fontsize=9)
        if kind == "dg":
            ox, oy = (A4W - DG_W) / 2, 30
            ax.add_patch(mp.FancyBboxPatch((ox, oy), DG_W, DG_D, boxstyle="round,pad=0,rounding_size=4",
                                           fc="#f2f2ef", ec="#222", lw=1.2))
            draw_digitone_block(ax, ox, oy)
        else:
            px, py = 8, 45
            ax.add_patch(mp.FancyBboxPatch((px, py), PANEL_W, PANEL_H, boxstyle="round,pad=0,rounding_size=6",
                                           fc="#f7f7f4", ec="#222", lw=1.2))
            draw_digitone_block(ax, px + 6, py + 4)
            fx = px + 6 + DG_W + 2
            ax.add_patch(mp.Rectangle((fx, py + 6), px + PANEL_W - 8 - fx, PANEL_H - 12,
                                      fc="#f0f6f0", ec="#7a9", lw=0.6, ls=(0, (4, 3))))
            ax.text((fx + px + PANEL_W - 8) / 2, py + PANEL_H / 2, "свободно", ha="center",
                    va="center", fontsize=6, color="#3a6")
    fig.savefig(os.path.join(OUT, "digitone2_top_preview.png"), bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def main():
    with PdfPages(os.path.join(OUT, "digitone2_top_1to1.pdf")) as pdf:
        page_digitone(pdf)
        page_on_our_panel(pdf)
    preview()
    print("saved:", os.path.join(OUT, "digitone2_top_1to1.pdf"))


if __name__ == "__main__":
    main()
