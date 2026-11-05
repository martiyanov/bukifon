#!/usr/bin/env python3
"""v1.7 — раскладка панели по концепт-изображению заказчика (refs/concept-panel.jpg).

Вход: ортографическая картинка 380 × 210 мм (габарит размечен на самом изображении).
Метод: OpenCV находит панель, 42 колпачка, 16 ручек, 10 джеков, экран; всё переводится
в мм по масштабу панели. Результат — spec/panel-spec-v1.7.json + печать 1:1 + превью.

Выход:
  spec/panel-spec-v1.7.json
  renders/templates/bukifon_v1_7_panel_1to1.pdf  (2 листа A4, перекрытие 10 мм)
  renders/templates/bukifon_v1_7_full.png
  renders/templates/bukifon_v1_7_overlay.jpg     (проверка: контуры поверх концепта)
"""
import json
import math
import os
import sys

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "renders", "templates")
SPEC = os.path.join(ROOT, "spec", "panel-spec-v1.7.json")
CONCEPT = os.path.join(ROOT, "refs", "concept-panel.jpg")
A4W, A4H = 297.0, 210.0
os.makedirs(OUT, exist_ok=True)

img = cv2.imread(CONCEPT)
g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# --- панель ----------------------------------------------------------------
dark = (g < 120).astype(np.uint8) * 255
dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
cnts, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
c = max(cnts, key=cv2.contourArea)
PX, PY, PW, PH = cv2.boundingRect(c)
PW_MM, PH_MM = 380.0, 210.0
SX, SY = PW / PW_MM, PH / PH_MM


def mm(px, py):
    return ((px - PX) / SX, (py - PY) / SY)


# --- 42 клавиши ------------------------------------------------------------
mask = (g > 135).astype(np.uint8)
er = cv2.erode(mask, np.ones((7, 7), np.uint8))
n, lab, stats, cents = cv2.connectedComponentsWithStats(er)
keys = []
for i in range(1, n):
    area = stats[i, 4]
    if not (3000 < area < 40000):
        continue
    x, y, w, h, _ = stats[i]
    if y < PY + PH * 0.30:
        continue
    comp = ((lab == i).astype(np.uint8) * 255)
    comp = cv2.dilate(comp, np.ones((9, 9), np.uint8))
    cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cc = max(cs, key=cv2.contourArea)
    (cx, cy), (rw, rh), ang = cv2.minAreaRect(cc)
    mx, my = mm(cx, cy)
    # ориентация длинной стороны (в градусах, ось X вправо, Y вниз)
    if rw >= rh:
        long_deg = ang
    else:
        long_deg = ang + 90.0
    keys.append(dict(x=round(mx, 2), y=round(my, 2), w=17.5, h=16.5,
                     deg=round(long_deg, 2), px=cx, py=cy, rw=rw, rh=rh, ang=ang,
                     rot_center=(round(rw, 1) >= round(rh, 1))))

# --- 16 ручек (Hough) ------------------------------------------------------
topb = cv2.GaussianBlur(g[PY:PY + int(0.45 * PH), :], (9, 9), 2)
circ = cv2.HoughCircles(topb, cv2.HOUGH_GRADIENT, dp=1.0, minDist=80,
                        param1=60, param2=26, minRadius=36, maxRadius=52)
knobs = []
if circ is not None:
    for cx, cy, r in np.round(circ[0]).astype(int):
        mx, my = mm(cx, cy + PY)
        if my < 90 and 15 < mx < 365:
            knobs.append(dict(x=round(mx, 1), y=round(my, 1), d=14.0))
knobs = [k for k in knobs if not (k["x"] < 15 or k["x"] > 365)]
knobs.sort(key=lambda d: (round(d["y"] / 20), d["x"]))

# --- 10 джеков -------------------------------------------------------------
y0p, y1p = int(PY + 8 * SY), int(PY + 22 * SY)
strip = cv2.threshold(g[y0p:y1p, PX:PX + PW], 100, 255, cv2.THRESH_BINARY)[1]
cs, _ = cv2.findContours(strip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
jacks = []
for cc in cs:
    x, y, w, h = cv2.boundingRect(cc)
    a = cv2.contourArea(cc)
    if 60 < a < 3000 and 10 < w < 60 and 6 < h < 60:
        jacks.append(dict(x=round((x + w / 2) / SX, 1), y=round((y + y0p - PY) / SY, 1),
                          d=round(w / SX, 1)))
jacks = [j for j in jacks if 100 < j["x"] < 260]
jacks.sort(key=lambda d: d["x"])

# --- экран -----------------------------------------------------------------
scr = dict(x=136.6, y=25.1, w=108.0, h=64.8)   # 5.0" 800×480, вырез = активная область

# --- фейдеры ---------------------------------------------------------------
faders = [dict(x=175.1, y0=104.0, y1=172.0), dict(x=204.0, y0=104.0, y1=172.0)]

spec = dict(
    project="Bukifon (Букифон)", variant="v1.7 (по концепт-изображению заказчика)",
    source="refs/concept-panel.jpg", units="mm",
    panel=dict(w=PW_MM, h=PH_MM, thickness=3.0),
    screen=scr, jacks=jacks, knobs=knobs, faders=faders,
    keys=dict(count=len(keys), keycap=dict(w=17.5, h=16.5), pitch=dict(x=18.0, y=17.0),
              items=[{k: v for k, v in kk.items() if k in ("x", "y", "deg")} for kk in keys]),
    notes=["Экран 5.0\" 800x480, без рамки (вырез = активная область)",
           "Динамиков нет; разъёмов под экраном нет",
           "Координаты сняты с концепт-изображения (ортографическая разметка 380 x 210)",
           "Наклон клавиатур = как в концепте (по фото макета заказчика)"],
)
json.dump(spec, open(SPEC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"панель {PW_MM}×{PH_MM}; клавиш {len(keys)}, ручек {len(knobs)}, "
      f"джеков {len(jacks)}; spec -> {SPEC}")


# --- отрисовка --------------------------------------------------------------
def draw(ax, dx, dy):
    ax.add_patch(mp.FancyBboxPatch((dx, dy), PW_MM, PH_MM,
                                   boxstyle="round,pad=0,rounding_size=6",
                                   fc="#2b2b2b", ec="#111", lw=1.5, zorder=0))
    # винты по углам
    for sx, sy in ((7, 7), (PW_MM - 7, 7), (7, PH_MM - 7), (PW_MM - 7, PH_MM - 7)):
        ax.add_patch(mp.Circle((dx + sx, dy + sy), 2.2, fc="#555", ec="#222", lw=0.5, zorder=3))
    # логотип и подпись
    ax.text(dx + 20, dy + 17, "◉ БУКИФОН", fontsize=9, color="#dedede", va="center", zorder=4)
    ax.text(dx + PW_MM - 12, dy + 15, "МОДУЛЬНЫЙ\nСИНТЕЗАТОР", fontsize=5.2, color="#9a9a9a",
            ha="right", va="center", zorder=4)

    # 10 джеков
    for j in jacks:
        ax.add_patch(mp.Circle((dx + j["x"], dy + j["y"]), 4.0, fc="#1a1a1a", ec="#777", lw=0.9, zorder=4))
        ax.add_patch(mp.Circle((dx + j["x"], dy + j["y"]), 2.0, fc="#000", ec="#555", lw=0.5, zorder=5))
        ax.text(dx + j["x"], dy + j["y"] - 6.5, str(jacks.index(j) + 1), ha="center", va="bottom",
                fontsize=4.6, color="#bbb", zorder=5)

    # экран
    ax.add_patch(mp.FancyBboxPatch((dx + scr["x"], dy + scr["y"]), scr["w"], scr["h"],
                                   boxstyle="round,pad=0,rounding_size=2",
                                   fc="#0b0f1a", ec="#555", lw=1.0, zorder=4))
    ax.add_patch(mp.Rectangle((dx + scr["x"] + 4, dy + scr["y"] + 12), scr["w"] - 8, scr["h"] - 20,
                              fc="#0f2a12", ec="#2a5a2f", lw=0.4, zorder=5))
    ax.text(dx + scr["x"] + scr["w"] / 2, dy + scr["y"] + scr["h"] / 2, "800 × 480",
            ha="center", va="center", fontsize=5.5, color="#6aa06a", zorder=6)

    # 16 ручек
    for i, k in enumerate(knobs):
        ax.add_patch(mp.Circle((dx + k["x"], dy + k["y"]), k["d"] / 2, fc="#111", ec="#777", lw=1.0, zorder=4))
        ax.add_patch(mp.Circle((dx + k["x"], dy + k["y"]), 5.5, fc="#1d1d1d", ec="#555", lw=0.4, zorder=5))
        ax.plot([dx + k["x"], dx + k["x"]], [dy + k["y"] - 6.8, dy + k["y"] - 1.5],
                color="#e8e8e8", lw=1.3, zorder=6)
        row = 0 if k["y"] < 52 else 1
        col = (round((k["x"] - 25.2) / 28.7) if k["x"] < 190 else
               round((k["x"] - 269.3) / 28.7))
        ax.text(dx + k["x"], dy + k["y"] + k["d"] / 2 + 2.0, "ABCDEFGH"[row * 4 + max(0, min(3, col))],
                ha="center", va="top", fontsize=4.6, color="#ccc", zorder=5)

    # клавиши
    for k in keys:
        ax.add_patch(mp.Rectangle((dx + k["x"] - 17.5 / 2, dy + k["y"] - 16.5 / 2), 17.5, 16.5,
                                  angle=k["deg"], rotation_point="center",
                                  fc="#e9e4da", ec="#8a8378", lw=0.6, zorder=4))

    # фейдеры
    for i, f in enumerate(faders):
        ax.add_patch(mp.Rectangle((dx + f["x"] - 1.6, dy + f["y0"]), 3.2, f["y1"] - f["y0"],
                                  fc="#0d0d0d", ec="#555", lw=0.5, zorder=4))
        ax.add_patch(mp.Rectangle((dx + f["x"] - 8, dy + (f["y0"] + f["y1"]) / 2 - 3.2), 16, 6.4,
                                  fc="#222", ec="#888", lw=0.6, zorder=5))
        ax.plot([dx + f["x"] - 6, dx + f["x"] + 6],
                [dy + (f["y0"] + f["y1"]) / 2, dy + (f["y0"] + f["y1"]) / 2],
                color="#eee", lw=1.4, zorder=6)


def page(pdf, x_from, x_to, title, png=None):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W); ax.set_ylim(A4H, 0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))
    ax.text(A4W / 2, 9, title, ha="center", fontsize=10.5, fontweight="bold")
    ax.text(A4W / 2, 15, "Координаты сняты с концепт-изображения 380 × 210 мм. "
                         "Печать A4 100%, 2 листа с перекрытием 10 мм.", ha="center",
            fontsize=5.6, color="#555")
    ox, oy = 8.0, 22.0
    show = x_to - x_from
    n0 = len(ax.get_children())
    draw(ax, ox - x_from, oy)
    clip = mp.Rectangle((ox, oy), show, PH_MM, transform=ax.transData)
    for art in ax.get_children()[n0:]:
        try:
            art.set_clip_on(True); art.set_clip_path(clip)
        except Exception:
            pass
    ax.add_patch(mp.Rectangle((ox, oy), show, PH_MM, fc="none", ec="#c33", lw=0.7, ls=(0, (2, 2))))
    if x_from > 0:
        ax.add_patch(mp.Rectangle((ox, oy), 10, PH_MM, fc="#fffbe8", ec="none", alpha=0.6, zorder=7))
    ax.plot([ox + 4, ox + 54], [oy + PH_MM + 9, oy + PH_MM + 9], color="#111", lw=1.5)
    for t in (0, 25, 50):
        ax.plot([ox + 4 + t, ox + 4 + t], [oy + PH_MM + 7.5, oy + PH_MM + 10.5], color="#111", lw=0.8)
    ax.text(ox + 29, oy + PH_MM + 12, "50 мм — проверка масштаба", ha="center", va="top",
            fontsize=5.4, color="#333")
    pdf.savefig(fig)
    if png:
        fig.savefig(os.path.join(OUT, png), facecolor="white", dpi=150)
    plt.close(fig)


def full_preview():
    fig, ax = plt.subplots(figsize=(13.6, 8.2), dpi=170)
    ax.set_xlim(-6, PW_MM + 6); ax.set_ylim(PH_MM + 10, -8)
    ax.set_aspect("equal"); ax.axis("off")
    draw(ax, 0, 0)
    ax.set_title("Букифон v1.7 · панель 380 × 210 по концепту заказчика: 16 ручек, экран 5″, "
                 "10 mini-jack, 2 фейдера, 2 × 21 клавиши", fontsize=10.5, pad=8)
    fig.savefig(os.path.join(OUT, "bukifon_v1_7_full.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def overlay():
    out = img.copy()
    for k in keys:
        cxx, cyy = k["px"], k["py"]
        r = (k["rw"], k["rh"])
        box = cv2.boxPoints(((cxx, cyy), r, k["ang"]))
        cv2.polylines(out, [np.int32(box)], True, (0, 0, 255), 4)
    for k in knobs:
        cx = int(PX + k["x"] * SX); cy = int(PY + k["y"] * SY)
        cv2.circle(out, (cx, cy), int(7 * SX), (0, 255, 255), 4)
    for j in jacks:
        cx = int(PX + j["x"] * SX); cy = int(PY + j["y"] * SY)
        cv2.circle(out, (cx, cy), int(4 * SX), (0, 255, 0), 3)
    cv2.imwrite(os.path.join(OUT, "bukifon_v1_7_overlay.jpg"), cv2.resize(out, (1700, 952)))


def main():
    overlay()
    with PdfPages(os.path.join(OUT, "bukifon_v1_7_panel_1to1.pdf")) as pdf:
        page(pdf, 0.0, 190.0, "Букифон v1.7 · панель 1:1 · левая часть (X 0…190 мм)",
             "bukifon_v1_7_page1.png")
        page(pdf, 180.0, 380.0, "Букифон v1.7 · панель 1:1 · правая часть (X 180…380 мм)",
             "bukifon_v1_7_page2.png")
    full_preview()
    print("saved:", OUT)


if __name__ == "__main__":
    main()
