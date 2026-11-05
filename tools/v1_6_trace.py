#!/usr/bin/env python3
"""v1.6 — трассировка макета заказчика по фото (refs/sketch4-panel.jpg).

Метод: OpenCV находит прямоугольники колпачков на фото; к 21 известной точке
половины Lapka-42 подбирается преобразование подобия (RANSAC по парам точек).
Дальше все 42 клавиши переносятся в мм с масштабом по клавишам (а не по экрану,
т.к. на макете экран напечатан в другом масштабе).

Выход:
  renders/templates/bukifon_v1_6_traced_1to1.pdf — панель 1:1 (2 листа A4)
  renders/templates/bukifon_v1_6_traced_full.png — превью
  renders/templates/bukifon_v1_6_trace_overlay.jpg — доказательство подгонки
"""
import itertools
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
sys.path.insert(0, HERE)
import lapka42_geometry as L

OUT = os.path.join(ROOT, "renders", "templates")
PHOTO = os.path.join(ROOT, "refs", "sketch4-panel.jpg")
A4W, A4H = 297.0, 210.0

# --- 1. контуры колпачков на фото ------------------------------------------
img = cv2.imread(PHOTO)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
roi = gray[1500:3700, 200:4900]
th = cv2.threshold(roi, 150, 255, cv2.THRESH_BINARY_INV)[1]
cnts, _ = cv2.findContours(th, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
cand = []
for c in cnts:
    a = cv2.contourArea(c)
    if a < 20000 or a > 100000:
        continue
    (cx, cy), (w, h), ang = cv2.minAreaRect(c)
    if not (200 < min(w, h) < 290 and 200 < max(w, h) < 330):
        continue
    cand.append((cx + 200, cy + 1500))
cand = np.array(cand)
left_pts, right_pts = cand[cand[:, 0] < 2500], cand[cand[:, 0] > 3200]
model = np.stack([[x for x, y, r in L.LAPKA42_LEFT], [y for x, y, r in L.LAPKA42_LEFT]], axis=1)


def fit(P, Q):
    best = None
    for i, j in itertools.combinations(range(len(P)), 2):
        dp = np.linalg.norm(P[i] - P[j])
        if dp < 8:
            continue
        for k, l in itertools.combinations(range(len(Q)), 2):
            dq = np.linalg.norm(Q[k] - Q[l])
            s = dq / dp
            if not (10 < s < 20):
                continue
            ang = math.atan2(Q[l][1] - Q[k][1], Q[l][0] - Q[k][0]) - \
                  math.atan2(P[j][1] - P[i][1], P[j][0] - P[i][0])
            R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
            t = Q[k] - s * R.dot(P[i])
            T = (s * R.dot(P.T)).T + t
            d = np.linalg.norm(T[:, None, :] - Q[None, :, :], axis=2).min(axis=1)
            inl = int((d < 30).sum())
            if best is None or inl > best[0]:
                best = (inl, float(s), float(ang), t)
    return best


fits = {}
for name, Q, mirror in (("left", left_pts, False), ("right", right_pts, True)):
    P = model.copy()
    if mirror:
        P[:, 0] = -P[:, 0]
    fits[name] = fit(P, Q) + (mirror,)
    print(name, "inliers", fits[name][0], "scale", round(fits[name][1], 2),
          "angle", round(math.degrees(fits[name][2]), 1))

scale = (fits["left"][1] + fits["right"][1]) / 2.0
print("масштаб трассировки:", round(scale, 2), "px/mm")

# --- 2. положения всех 42 колпачков в мм (в системе фото, y вниз) -----------
caps = []
for name in ("left", "right"):
    inl, s, ang, t, mirror = fits[name]
    R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
    for (x, y, rot) in L.LAPKA42_LEFT:
        mx = -x if mirror else x
        my = y
        px, py = s * R.dot(np.array([mx, my])) + t
        cap_ang_model = -rot if mirror else rot      # зеркало меняет знак угла
        cap_ang_photo = cap_ang_model + math.degrees(ang)
        caps.append(dict(px=px, py=py, deg=cap_ang_photo, half=name))

# --- 3. в мм, панель по габариту трассировки --------------------------------
CAP_W, CAP_H = L.KEYCAP_W, L.KEYCAP_H
hw, hh = CAP_W / 2, CAP_H / 2


def corners_mm(cap):
    a = math.radians(cap["deg"])
    ca, sa = math.cos(a), math.sin(a)
    return [(cap["px"] + ca * sx * hw * scale - sa * sy * hh * scale,
             cap["py"] + sa * sx * hw * scale + ca * sy * hh * scale)
            for sx in (-1, 1) for sy in (-1, 1)]


xs = [p[0] for c in caps for p in corners_mm(c)]
ys = [p[1] for c in caps for p in corners_mm(c)]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
margin = 8.0
panel_w = (x1 - x0) / scale + 2 * margin
panel_h = (y1 - y0) / scale + 2 * margin
print(f"габарит трассировки: {(x1-x0)/scale:.1f} × {(y1-y0)/scale:.1f} мм → "
      f"панель {panel_w:.1f} × {panel_h:.1f}")

# --- 4. вспомогательное: скрин/ручки/джек/фейдеры — из этого же фото -------
KEYS_TOP_MM = margin
SCR_W, SCR_H = 108.0, 64.8
PHOTO_CX_MM = ((fits["left"][3][0] + 0) / scale)  # не используется напрямую

# центр экрана по фото: (2171..3235, 806..1571) → мм от левого края панели
scr_cx = ((2171 + 3235) / 2 - x0) / scale + margin
scr_cy = (1000 - y0) / scale + margin   # чуть выше центра
print("экран: центр", round(scr_cx, 1), round(scr_cy, 1))

# 16 ручек по фото: блоки из моих же листов (шаг 27 мм) — центры
# левый блок: колонки 22/49/76/103 от левого края, ряды 26/53; правый — зеркально
KNOB_D = 14.0
KNOB_COLS = [22.0, 49.0, 76.0, 103.0]
KNOB_ROWS = [26.0, 53.0]
knobs = []
for x in KNOB_COLS:
    for y in KNOB_ROWS:
        knobs.append((margin + x, margin + y))
for x in KNOB_COLS:
    for y in KNOB_ROWS:
        knobs.append((panel_w - margin - x, margin + y))

# 10 джеков над экраном
JACKS = [(panel_w / 2 - 55 + i * 11.0, margin - 1.0) for i in range(10)]

# фейдеры: между клавиатурами, по центру (как на эскизе)
FADERS = [(panel_w / 2 - 11.0, panel_h - 92.0, panel_h - 32.0),
          (panel_w / 2 + 11.0, panel_h - 92.0, panel_h - 32.0)]


def draw(ax, dx, dy, detail=True):
    ax.add_patch(mp.FancyBboxPatch((dx, dy), panel_w, panel_h,
                                   boxstyle="round,pad=0,rounding_size=5",
                                   fc="#f8f8f5", ec="#222", lw=1.8, zorder=0))
    for gx in range(0, int(panel_w) + 1, 10):
        ax.plot([dx + gx, dx + gx], [dy, dy + panel_h], color="#ecece7", lw=0.25, zorder=1)
    for gy in range(0, int(panel_h) + 1, 10):
        ax.plot([dx, dx + panel_w], [dy + gy, dy + gy], color="#ecece7", lw=0.25, zorder=1)

    # клавиши — точно по трассировке
    for c in caps:
        cx = (c["px"] - x0) / scale + margin
        cy = (c["py"] - y0) / scale + margin
        ax.add_patch(mp.Rectangle((dx + cx - hw, dy + cy - hh), CAP_W, CAP_H,
                                  angle=-c["deg"], rotation_point="center",
                                  fc="#d8e6f7", ec="#4a6b8a", lw=0.6, zorder=6))

    # ручки
    for i, (x, y) in enumerate(knobs):
        ax.add_patch(mp.Circle((dx + x, dy + y), KNOB_D / 2, fc="#ececec", ec="#333", lw=1.0, zorder=4))
        ax.add_patch(mp.Circle((dx + x, dy + y), 5.2, fc="none", ec="#bbb", lw=0.5, zorder=5))
        ax.plot([dx + x, dx + x], [dy + y - 5.6, dy + y - 1.0], color="#d33", lw=1.1, zorder=6)

    # экран
    ax.add_patch(mp.FancyBboxPatch((dx + scr_cx - SCR_W / 2, dy + scr_cy - SCR_H / 2),
                                   SCR_W, SCR_H, boxstyle="round,pad=0,rounding_size=1.0",
                                   fc="#111a11", ec="#333", lw=0.8, zorder=4))

    # джеки
    for (x, y) in JACKS:
        ax.add_patch(mp.Circle((dx + x, dy + y), 3.2, fc="#e9e9e4", ec="#333", lw=0.7, zorder=4))
        ax.add_patch(mp.Circle((dx + x, dy + y), 1.1, fc="#555", ec="none", zorder=5))

    # фейдеры
    for i, (x, ya, yb) in enumerate(FADERS):
        ax.add_patch(mp.FancyBboxPatch((dx + x - 4, dy + ya), 8, yb - ya,
                                       boxstyle="round,pad=0,rounding_size=3.4",
                                       fc="#dcdcdc", ec="#444", lw=0.8, zorder=4))
        ax.add_patch(mp.Rectangle((dx + x - 8, dy + (ya + yb) / 2 - 4), 16, 8,
                                  fc="#444", ec="#111", lw=0.5, zorder=5))


def page(pdf, x_from, x_to, title, png=None):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W); ax.set_ylim(A4H, 0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(mp.Rectangle((6, 6), A4W - 12, A4H - 12, fc="white", ec="#ddd", lw=0.5))
    ax.text(A4W / 2, 9, title, ha="center", fontsize=10.5, fontweight="bold")
    ax.text(A4W / 2, 15, f"Трассировка по фото заказчика. Панель {panel_w:.0f} × {panel_h:.0f} мм, "
                         f"печать A4 100%, 2 листа с перекрытием 10 мм.", ha="center",
            fontsize=5.6, color="#555")
    ox, oy = 8.0, 22.0
    show = x_to - x_from
    n0 = len(ax.get_children())
    draw(ax, ox - x_from, oy)
    clip = mp.Rectangle((ox, oy), show, panel_h, transform=ax.transData)
    for art in ax.get_children()[n0:]:
        try:
            art.set_clip_on(True); art.set_clip_path(clip)
        except Exception:
            pass
    ax.add_patch(mp.Rectangle((ox, oy), show, panel_h, fc="none", ec="#c33", lw=0.7, ls=(0, (2, 2))))
    if x_from > 0:
        ax.add_patch(mp.Rectangle((ox, oy), 10, panel_h, fc="#fffbe8", ec="none", alpha=0.6, zorder=7))
    # линейка 50 мм
    ax.plot([ox + 4, ox + 54], [oy + panel_h + 9, oy + panel_h + 9], color="#111", lw=1.5)
    for t in (0, 25, 50):
        ax.plot([ox + 4 + t, ox + 4 + t], [oy + panel_h + 7.5, oy + panel_h + 10.5], color="#111", lw=0.8)
    ax.text(ox + 29, oy + panel_h + 12, "50 мм — проверка масштаба", ha="center", va="top",
            fontsize=5.4, color="#333")
    pdf.savefig(fig)
    if png:
        fig.savefig(os.path.join(OUT, png), facecolor="white", dpi=150)
    plt.close(fig)


def full_preview():
    fig, ax = plt.subplots(figsize=(13.4, 8.0), dpi=170)
    ax.set_xlim(-6, panel_w + 6); ax.set_ylim(panel_h + 10, -8)
    ax.set_aspect("equal"); ax.axis("off")
    draw(ax, 0, 0)
    ax.set_title(f"Букифон v1.6 · трассировка вашего макета: панель {panel_w:.0f} × {panel_h:.0f} мм, "
                 f"наклон половин ±{abs(math.degrees(fits['left'][2])):.0f}°", fontsize=10.5, pad=8)
    fig.savefig(os.path.join(OUT, "bukifon_v1_6_traced_full.png"), bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


def trace_overlay():
    out = img.copy()
    for c in caps:
        a = math.radians(c["deg"])
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                pts.append((c["px"] + ca * sx * hw * scale - sa * sy * hh * scale,
                            c["py"] + sa * sx * hw * scale + ca * sy * hh * scale))
        poly = np.array([[(int(px), int(py))] for px, py in pts[:4]], np.int32)
        cv2.polylines(out, [poly], True, (0, 0, 255), 6)
    cv2.imwrite(os.path.join(OUT, "bukifon_v1_6_trace_overlay.jpg"),
                cv2.resize(out, (1700, 1275)))


def main():
    trace_overlay()
    with PdfPages(os.path.join(OUT, "bukifon_v1_6_traced_1to1.pdf")) as pdf:
        page(pdf, 0.0, 190.0, "Букифон v1.6 · трассировка макета · 1:1 · левая часть",
             "bukifon_v1_6_page1.png")
        page(pdf, 180.0, panel_w, "Букифон v1.6 · трассировка макета · 1:1 · правая часть",
             "bukifon_v1_6_page2.png")
    full_preview()
    print("saved:", OUT)


if __name__ == "__main__":
    main()
