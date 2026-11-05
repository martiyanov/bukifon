"""make_assembly_map.py — сборочная карта Букифона v0.5-B-light (S3-base).

Выход: renders/templates/bukifon_assembly_map_1to1.pdf
  стр.1 (A4 landscape) — разнесённая схема слоёв (1:2.5) с подписями, точками
                          крепежа 6×M3 PANEL-2 + 4×M3 панели, шлейфами, линейкой 50 мм;
  стр.2 (A4 portrait, 1:1) — панель, левая половина 193×210: все вырезы, точки
                          крепежа, PANEL-2 (часть), подписи;
  стр.3 (A4 portrait, 1:1) — правая половина 190×210;
  стр.4 (A4 landscape)    — легенда: порядок слоёв, крепёж, шлейфы, чек-лист, линейка.

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/make_assembly_map.py
"""
from __future__ import annotations

import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Polygon, Rectangle
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPEC = json.load(open(os.path.join(ROOT, "spec", "panel-spec-v0.4.json")))
C = SPEC["controls"]
OUT = os.path.join(ROOT, "renders", "templates", "bukifon_assembly_map_1to1.pdf")
PREV = os.path.join(ROOT, "mechanical", "preview_v05_B_light")

A4L = (297.0, 210.0)     # landscape, мм
A4P = (210.0, 297.0)     # portrait, мм

PANEL_W, PANEL_H = 380.0, 210.0
PANEL_POSTS = [(30.0, 46.0), (65.0, 46.0), (150.0, 46.0),
               (230.0, 46.0), (283.0, 46.0), (341.0, 46.0)]
PANEL_SCREWS = [(9.0, 9.0), (371.0, 9.0), (9.0, 201.0), (371.0, 201.0)]

BOARDS = {
    "body": "корпус B-light (body_L + body_R)",
    "pwr": "PWR-2 rev.1 — 90 × 70 × 1.6, Z6",
    "core": "CORE-S3 rev.0 — 200 × 108 × 1.6, Z12",
    "panel2": "PANEL-2 rev.2 — 360 × 190 × 1.6, −8 мм под панелью",
    "lcd": "дисплей 5\" 800×480 — FFC-40, 120.7 × 75.8",
    "bat": "2 × 18650 (опция) — ложемент справа",
}
CABLES = [
    ("FFC-40", "дисплей ↔ CORE-S3 (J15) / PANEL-2 J12", "1 шт, 10–15 см"),
    ("IDC-26", "PANEL-2 J14 ↔ CORE-S3 J14 (аналог/джек)", "1 шт, 10 см"),
    ("IDC-16", "PANEL-2 J13 ↔ CORE-S3 J16 (цифра/питание)", "1 шт, 10 см"),
    ("IDC-20", "PWR-2 J3 ↔ CORE-S3 J17 (силовое)", "1 шт, 8–10 см"),
    ("IDC-12", "PWR-2 J4 ↔ CORE-S3 J18 (управление)", "1 шт, 8–10 см"),
    ("IDC-26 (шина)", "P0/P1/P2 — картриджи/доки", "опция"),
]


def iso(x, y, z, s=0.62):
    """Простая изометрия: X→вправо-вниз, Y→влево-вниз, Z→вверх."""
    px = (x - y) * math.cos(math.radians(30)) * s + 148.0
    py = z * s + (x + y) * math.sin(math.radians(30)) * s * 0.55 + 26.0
    return px, py


def rrect_iso(ax, cx, cy, w, d, z, dz=0.0, color="#ddd", ec="#333", lw=0.8,
              ls="-", label=None, alpha=1.0):
    s = 0.62
    pts = []
    for (x, y) in ((cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2),
                   (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)):
        pts.append(iso(x, y, z + dz, s))
    ax.add_patch(Polygon(pts, closed=True, fc=color, ec=ec, lw=lw, ls=ls,
                         alpha=alpha, zorder=2 + z / 10))
    if label:
        px, py = iso(cx, cy, z + dz, s)
        ax.text(px, py, label, fontsize=4.6, ha="center", va="center", zorder=20,
                color="#111")
    return pts


def leader(ax, x1, y1, x2, y2, text, fs=4.8, color="#111", ha="left"):
    ax.annotate(text, xy=(x1, y1), xytext=(x2, y2), fontsize=fs, color=color,
                ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", lw=0.5, color="#666",
                                shrinkA=0, shrinkB=1))


def ruler(ax, x, y, horizontal=True, label=True):
    L = 50.0
    ax.plot([x, x + L], [y, y], color="#000", lw=1.0)
    for i in range(51):
        h = 4.0 if i % 10 == 0 else (2.4 if i % 5 == 0 else 1.3)
        ax.plot([x + i, x + i], [y, y + h], color="#000", lw=0.5)
    if label:
        ax.text(x + L / 2, y - 4, "50 мм — контроль печати 1:1", ha="center",
                fontsize=6.0)


# ---------------------------------------------------------------------------
def page1_exploded(pdf):
    fig = plt.figure(figsize=(A4L[0] / 25.4, A4L[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4L[0]); ax.set_ylim(0, A4L[1])
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((4, 4), A4L[0] - 8, A4L[1] - 8, fc="white", ec="#ddd", lw=0.4))
    ax.text(A4L[0] / 2, A4L[1] - 9,
            "БУКИФОН v0.5-B-light · СБОРОЧНАЯ КАРТА: ПОРЯДОК СЛОЁВ",
            ha="center", fontsize=11.5, fontweight="bold")
    ax.text(A4L[0] / 2, A4L[1] - 14.5,
            "Разнесённая схема (условный масштаб 1:2.5; линейка 50 мм — контроль печати). "
            "Панель 1:1 — стр.2–3. Сборка снизу вверх, слои 1→7.",
            ha="center", fontsize=5.6, color="#444")

    S = 0.36
    X0, Z0 = 150.0, 40.0
    LEV = {1: 0.0, 2: 10.0, 3: 22.0, 4: 36.0, 5: 52.0, 6: 70.0, 7: 88.0}

    def iso(x, y, lev):
        px = (x - y) * math.cos(math.radians(30)) * S + X0
        py = Z0 + LEV[lev] + (x + y) * math.sin(math.radians(30)) * S * 0.55
        return px, py

    def rect(cx, cy, w, d, lev, color, ec, ls="-", alpha=1.0, lw=0.7):
        pts = [iso(cx - w/2, cy - d/2, lev), iso(cx + w/2, cy - d/2, lev),
               iso(cx + w/2, cy + d/2, lev), iso(cx - w/2, cy + d/2, lev)]
        ax.add_patch(Polygon(pts, closed=True, fc=color, ec=ec, lw=lw, ls=ls,
                             alpha=alpha, zorder=2 + lev))
        return pts

    def badge(lev, num, cx=0.0, cy=0.0):
        px, py = iso(cx, cy, lev)
        ax.add_patch(Circle((px, py), 4.2, fc="#fff", ec="#000", lw=0.7, zorder=50))
        ax.text(px, py, str(num), fontsize=5.0, ha="center", va="center",
                fontweight="bold", zorder=51)

    # слои
    rect(95, 105, 188, 206, 1, "#4a4f55", "#222")
    rect(285, 105, 188, 206, 1, "#4a4f55", "#222")
    badge(1, 1, 95, 190)
    rect(330, 88, 76, 60, 2, "#c9d6e8", "#2c6fbb", ls=(0, (2, 1.4)))
    badge(2, 2, 330, 88)
    rect(190, 100, 90, 70, 3, "#d33", "#700")
    badge(3, 3, 190, 100)
    rect(190, 105, 200, 108, 4, "#2f7d4f", "#174")
    badge(4, 4, 190, 105)
    rect(190, 105, 360, 190, 5, "#2a5f9e", "#123", ls=(0, (3, 2)), alpha=0.85)
    badge(5, 5, 190, 105)
    rect(190, 58, 121, 76, 6, "#0b2a4a", "#89a")
    badge(6, 6, 190, 58)
    for cx in (95, 285):
        rect(cx, 105, 188, 206, 7, "#262626", "#000")
    for src in (C["keyboard_left"], C["keyboard_right"]):
        for k in src:
            x, y = k["center_mm"]
            px, py = iso(x, y, 7)
            ax.add_patch(Rectangle((px - 2.6, py - 2.0), 5.2, 4.0, angle=-k["angle_deg"],
                                   fc="#e8e2d6", ec="#777", lw=0.15, zorder=60))
    for e in C["encoders_left"] + C["encoders_right"]:
        px, py = iso(*e["center_mm"], 7)
        ax.add_patch(Circle((px, py), 2.0, fc="#111", ec="#999", lw=0.2, zorder=61))
    for j in C["jacks"]:
        px, py = iso(*j["center_mm"], 7)
        ax.add_patch(Circle((px, py), 1.2, fc="#ddd", ec="#666", lw=0.2, zorder=61))
    for f in C["faders"]:
        px, py = iso(*f["slot"]["center_mm"], 7)
        ax.add_patch(Rectangle((px - 0.8, py - 4.5), 1.6, 9.0, fc="#000", ec="#999",
                               lw=0.2, zorder=61))
    badge(7, 7, 285, 190)

    # легенда слева сверху
    ax.text(8, 190, "СЛОИ СНИЗУ ВВЕРХ", fontsize=6.4, fontweight="bold")
    legend = [
        "1. Корпус B-light (body_L + body_R,",
        "    шип 3×1.2; дно 1.8, стенки 2.0)",
        "2. Батарея 1S2P 18650 (опция)",
        "3. PWR-2 rev.1 90×70, Z6 — 4×M2.5",
        "4. CORE-S3 rev.0 200×108, Z12 — 4×M3",
        "5. PANEL-2 rev.2 360×190 — 6×M3",
        "6. Дисплей 5\" 120.7×75.8 — FFC-40",
        "7. Панель 193+190 — 4×M3×8; 42 Choc,",
        "    16 ENC, 2 фейдера, 10 джеков",
    ]
    for i, t in enumerate(legend):
        ax.text(9, 184 - i * 4.4, t, fontsize=4.9, color="#222")

    # крепёж
    ax.text(8, 118, "КРЕПЁЖ (по выноскам)", fontsize=6.0, fontweight="bold")
    ax.text(8, 113, "○ красные — 4×M3×8 панель", fontsize=4.8, color="#c00")
    ax.text(8, 108.5, "○ жёлтые — 6×M3×6 PANEL-2", fontsize=4.8, color="#990")
    ax.text(8, 104, "4×M3×6 CORE-S3; 4×M2.5×6 дисплей;", fontsize=4.8, color="#333")
    ax.text(8, 99.5, "8×M2.5×8 фейдеры; 4×M3×16 стяжка", fontsize=4.8, color="#333")
    ax.text(8, 95, "половин корпуса (опция)", fontsize=4.8, color="#333")
    for (x, y) in PANEL_SCREWS:
        px, py = iso(x, y, 7)
        ax.add_patch(Circle((px, py), 2.4, fc="none", ec="#c00", lw=0.9, zorder=70))
    for (x, y) in PANEL_POSTS:
        px, py = iso(x, y, 7)
        ax.add_patch(Circle((px, py), 1.9, fc="none", ec="#aa0", lw=0.8,
                            ls=(0, (1, 1)), zorder=70))

    # шлейфы
    def cable(p1, p2, label, color="#8a4b00", off=(0, 0)):
        ax.annotate("", xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle="<->", lw=0.8, color=color))
        mx = (p1[0] + p2[0]) / 2 + off[0]
        my = (p1[1] + p2[1]) / 2 + off[1]
        ax.text(mx, my, label, fontsize=4.4, color=color, ha="center",
                bbox=dict(fc="white", ec="none", pad=0.3), zorder=80)

    cable(iso(250, 60, 6), iso(250, 60, 4), "FFC-40", "#003", (16, 0))
    cable(iso(120, 150, 5), iso(120, 150, 4), "IDC-26/16", "#420", (-17, 0))
    cable(iso(260, 145, 4), iso(260, 145, 3), "IDC-20/12", "#500", (18, 0))

    # низ: порядок и шлейфы
    ax.text(A4L[0] / 2, 22,
            "ПОРЯДОК: корпус → PANEL-2 → PWR-2 → CORE-S3 → дисплей → шлейфы → панель; "
            "энкодеры/клавиши/джеки — ПОСЛЕ панели.", fontsize=5.1, color="#222",
            ha="center")
    ax.text(A4L[0] / 2, 17, "Шлейфы: FFC-40 (дисплей↔CORE-S3), IDC-26 (PANEL-2 J14↔CORE), "
                            "IDC-16 (J13↔CORE), IDC-20/IDC-12 (PWR-2↔CORE).",
            fontsize=4.7, color="#555", ha="center")
    ax.text(A4L[0] / 2, 12, "Подробно — docs/34-assembly.md. Легенда крепежа/шлейфов — стр.4.",
            fontsize=4.7, color="#555", ha="center")
    ruler(ax, 214, 6)

    fig.savefig(pdf, format="pdf")
    fig.savefig(os.path.join(PREV, "asm_map_p1.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
def _panel_half_page(pdf, side):
    portrait = side in ("L", "R")
    fig = plt.figure(figsize=(A4P[0] / 25.4, A4P[1] / 25.4)) if portrait else None
    W, H = A4P if portrait else A4L
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((3, 3), W - 6, H - 6, fc="white", ec="#ddd", lw=0.4))
    x0, x1 = (0.0, 193.0) if side == "L" else (190.0, 380.0)
    ox = (W - (x1 - x0)) / 2 - x0
    oy = 44.0 if portrait else 20.0
    ax.text(W / 2, H - 8,
            f"БУКИФОН v0.5-B-light · ПАНЕЛЬ, половина {'ЛЕВАЯ' if side=='L' else 'ПРАВАЯ'} "
            f"({x0:.0f}…{x1:.0f} мм) · 1:1", ha="center", fontsize=10,
            fontweight="bold")
    ax.text(W / 2, H - 13.5,
            "Печать A4 100 %, без масштабирования. Линейка ниже = 50 мм. "
            "Стык по X=190: шип 3×1.2 (левая) / паз (правая).",
            ha="center", fontsize=5.6, color="#444")

    # панель (половина)
    ax.add_patch(Rectangle((ox + x0, oy), x1 - x0, 210, fc="#2b2b2b", ec="#000", lw=1.0))
    # PANEL-2 (часть, пунктир)
    bx0, bx1 = 10.0, 370.0
    ax.add_patch(Rectangle((ox + max(bx0, x0), oy + 10), min(bx1, x1) - max(bx0, x0),
                           190, fc="none", ec="#2a5f9e", lw=0.8, ls=(0, (3, 2))))
    ax.text(ox + (max(bx0, x0) + min(bx1, x1)) / 2, oy + 8,
            "PANEL-2 rev.2 360×190 (пунктир)", fontsize=4.6, color="#2a5f9e",
            ha="center", va="top")

    # вырезы: клавиши
    keys = C["keyboard_left"] if side == "L" else C["keyboard_right"]
    for i, k in enumerate(keys):
        x, y = k["center_mm"]
        if not (x0 - 10 <= x <= x1 + 10):
            continue
        ax.add_patch(Rectangle((ox + x - 8.75, oy + 210 - y - 8.25), 17.5, 16.5,
                               angle=-k["angle_deg"], rotation_point="center",
                               fc="#e8e2d6", ec="#777", lw=0.3))

    ax.text(ox + (x0 + x1) / 2, oy + 210 - 196,
            "клавиши Lapka-42 — 21 шт на половину (канон ±18°)",
            fontsize=4.6, color="#eee", ha="center")
    # энкодеры
    enc = C["encoders_left"] if side == "L" else C["encoders_right"]
    names = "ABCDEFGH" if side == "L" else "IJKLMNOP"
    for i, e in enumerate(enc):
        x, y = e["center_mm"]
        if not (x0 - 10 <= x <= x1 + 10):
            continue
        ax.add_patch(Circle((ox + x, oy + 210 - y), 7, fc="#111", ec="#888", lw=0.4))
        ax.add_patch(Circle((ox + x, oy + 210 - y), 3.6, fc="#333", ec="#aaa", lw=0.3))
        ax.text(ox + x, oy + 210 - y - 10, names[i], fontsize=5.0, ha="center",
                color="#ddd")
    # джеки
    for i, j in enumerate(C["jacks"]):
        x, y = j["center_mm"]
        if not (x0 - 10 <= x <= x1 + 10):
            continue
        ax.add_patch(Circle((ox + x, oy + 210 - y), 4.0, fc="#ddd", ec="#555", lw=0.4))
        ax.add_patch(Circle((ox + x, oy + 210 - y), 2.0, fc="#111", ec="#555", lw=0.3))
        ax.text(ox + x, oy + 210 - y + 5.5, str(i + 1), fontsize=4.0, ha="center",
                color="#333")
    # фейдеры
    for f in C["faders"]:
        x = f["slot"]["center_mm"][0]
        if not (x0 - 10 <= x <= x1 + 10):
            continue
        y = f["slot"]["center_mm"][1]
        ax.add_patch(Rectangle((ox + x - 1.25, oy + 210 - (y + 31.5)), 2.5, 63,
                               fc="#000", ec="#777", lw=0.3))
        ax.text(ox + x, oy + 210 - (y + 38), f["id"], fontsize=5.0, ha="center",
                color="#ddd")
    # экран (часть)
    s = C["lcd"]["active_cutout"]
    sx0 = s["center_mm"][0] - s["opening_size_mm"][0] / 2
    sx1 = s["center_mm"][0] + s["opening_size_mm"][0] / 2
    sy0 = s["center_mm"][1] - s["opening_size_mm"][1] / 2
    ax.add_patch(Rectangle((ox + max(sx0, x0), oy + 210 - (sy0 + s["opening_size_mm"][1])),
                           min(sx1, x1) - max(sx0, x0), s["opening_size_mm"][1],
                           fc="#0b2a4a", ec="#89a", lw=0.5))
    # USB-C (только левая? вырез на задней кромке X~350 — правая)
    if side == "R":
        ax.add_patch(Rectangle((ox + 345.3, oy + 210 - 3.6), 9.4, 3.6, fc="#fff",
                               ec="#000", lw=0.4))
        ax.text(ox + 350, oy + 210 - 6, "USB-C", fontsize=4.6, ha="center", color="#333")
    # крепёж
    for (x, y) in PANEL_SCREWS:
        if x0 - 5 <= x <= x1 + 5:
            ax.add_patch(Circle((ox + x, oy + 210 - y), 3.0, fc="none", ec="#c00",
                                lw=0.9))
            ax.text(ox + x - 4, oy + 210 - y + 3.5, "M3", fontsize=3.8, color="#c00",
                    ha="right")
    for (x, y) in PANEL_POSTS:
        if x0 - 5 <= x <= x1 + 5:
            ax.add_patch(Circle((ox + x, oy + 210 - y), 2.4, fc="none", ec="#990",
                                lw=0.8, ls=(0, (1, 1))))
            ax.text(ox + x + 3.0, oy + 210 - y - 4.5, "M3", fontsize=3.6, color="#990")
    # шип/паз по шву
    seam_x = 190.0
    ax.plot([ox + seam_x, ox + seam_x], [oy, oy + 210], color="#ff0", lw=1.2,
            ls=(0, (2, 2)))
    ax.text(ox + seam_x - (4 if side == "L" else -4), oy + 105,
            "шип 3×1.2" if side == "L" else "паз 3.2", fontsize=4.0, color="#aa0",
            ha="right" if side == "L" else "left", rotation=90, va="center")

    # легенда
    ly = oy - 10 if portrait else 12
    ax.text(8, ly, "ТОЧКИ КРЕПЕЖА: ○ M3 панель (4 шт по углам) · ⌀ M3 PANEL-2 (6 шт, "
                   "жёлтый пунктир); крепёж PANEL-2 — ДО панели.", fontsize=5.0,
            color="#333")
    ax.text(8, ly - 6, "КЛАВИШИ: Lapka-42, половины ±18°; номера — как в spec "
                       "(KEY1…21 / KEY22…42). ЭНКОДЕРЫ: A–H (Ø14, гайка Ø14.4). "
                       "ДЖЕКИ: 1–10 (Ø6.2 + цековка Ø8.2×1.5).", fontsize=5.0,
            color="#333")
    ruler(ax, W - 60, 6)
    fig.savefig(pdf, format="pdf")
    fig.savefig(os.path.join(PREV, ("asm_map_p2.png" if side == "L" else "asm_map_p3.png")), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
def page4_legend(pdf):
    fig = plt.figure(figsize=(A4L[0] / 25.4, A4L[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4L[0]); ax.set_ylim(0, A4L[1])
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((4, 4), A4L[0] - 8, A4L[1] - 8, fc="white", ec="#ddd", lw=0.4))
    ax.text(A4L[0] / 2, A4L[1] - 9,
            "БУКИФОН v0.5-B-light (S3-base) · ЛЕГЕНДА, КРЕПЁЖ И ШЛЕЙФЫ",
            ha="center", fontsize=11.5, fontweight="bold")

    # порядок слоёв
    ax.text(14, A4L[1] - 22, "ПОРЯДОК СЛОЁВ (снизу вверх)", fontsize=7.2,
            fontweight="bold")
    layers = [
        "1. body_L + body_R (B-light), шип/паз по X=190",
        "2. Батарея 1S2P 18650 в ложементе (опция, справа)",
        "3. PWR-2 rev.1 90×70 — 4×M2.5, Z6; J17 IDC-20 / J18 IDC-12",
        "4. CORE-S3 rev.0 200×108 — 4×M3×6, Z12; J14/J15/J16",
        "5. PANEL-2 rev.2 360×190 — 6×M3×6, 8 мм под панелью",
        "6. Дисплей 5\" — 4×M2.5×6 к панели, FFC-40",
        "7. Панель 193+190 с шипом — 4×M3×8 по углам",
        "8. Компоненты: 16 энкодеров, 42 Choc, 10 джеков, 2 фейдера",
    ]
    for i, t in enumerate(layers):
        ax.text(16, A4L[1] - 28 - i * 4.6, t, fontsize=5.8)

    # крепёж
    ax.text(14, 124, "КРЕПЁЖ", fontsize=7.2, fontweight="bold")
    fast = [
        ("M3×8 потай", "4", "панель по углам (9/9, 371/9, 9/201, 371/201)"),
        ("M3×6", "6", "PANEL-2 на стойки (30/65/150/230/283/341, Y46)"),
        ("M3×6", "4", "CORE-S3 на стойки (95/285, Y59/151)"),
        ("M2.5×6", "4", "дисплей к панели"),
        ("M2.5×8", "8", "2 фейдера (4 каждый)"),
        ("M3×16", "4", "стяжка половин корпуса (опция; шов панели держит шип)"),
    ]
    ax.text(14, 118, "Винт", fontsize=6.0, fontweight="bold")
    ax.text(52, 118, "Кол-во", fontsize=6.0, fontweight="bold")
    ax.text(66, 118, "Куда", fontsize=6.0, fontweight="bold")
    for i, (a, b, c) in enumerate(fast):
        ax.text(14, 112 - i * 5.2, a, fontsize=5.2)
        ax.text(52, 112 - i * 5.2, b, fontsize=5.2)
        ax.text(66, 112 - i * 5.2, c, fontsize=5.2)

    # шлейфы
    ax.text(160, 124, "ШЛЕЙФЫ (проверить ориентацию ключа!)", fontsize=7.2,
            fontweight="bold")
    ax.text(160, 118, "Тип", fontsize=6.0, fontweight="bold")
    ax.text(188, 118, "Между", fontsize=6.0, fontweight="bold")
    ax.text(252, 118, "Длина", fontsize=6.0, fontweight="bold")
    for i, (a, b, c) in enumerate(CABLES):
        ax.text(160, 112 - i * 5.2, a, fontsize=5.2)
        ax.text(188, 112 - i * 5.2, b, fontsize=5.0)
        ax.text(252, 112 - i * 5.2, c, fontsize=5.0)

    # чек-лист
    ax.text(14, 78, "ПЕРЕД ВКЛЮЧЕНИЕМ (минимум):", fontsize=7.2, fontweight="bold",
            color="#8b0000")
    checks = [
        "• все 4 слоя плат закреплены, шлейфы до конца в разъёмах (ключ совпал);",
        "• полярность 2×18650 и разъёма батареи (переполюсовка = пожар);",
        "• нет короткого замыкания +5/+3V3/±12 на корпус (прозвонить);",
        "• дисплей FFC-40 вставлен, замок закрыт;",
        "• винты затянуты 0.4 Н·м (PETG не перетягивать);",
        "• USB-C/БП: сначала внешний 12 В без батареи, ток ≤0.5 А;",
        "• прошивка: прошить, проверить DECK_ID/PANEL-2 I2C (0x20-0x23);",
        "• калибровка: энкодеры 0…1023, фейдеры, CV out 0/5/10 В.",
    ]
    for i, t in enumerate(checks):
        ax.text(16, 72 - i * 4.6, t, fontsize=5.4)

    ax.text(14, 30, "НЕ ЗАБЫТЬ: PANEL-2 и дисплей — ДО панели; энкодеры/клавиши/джеки/"
                    "фейдеры — ПОСЛЕ укладки панели (гайки сверху).",
            fontsize=5.2, color="#333")
    ax.text(14, 25, "Порядок сборки и предупреждения — docs/34-assembly.md.", fontsize=5.2,
            color="#333")
    ruler(ax, 200, 8)
    fig.savefig(pdf, format="pdf")
    fig.savefig(os.path.join(PREV, "asm_map_p4.png"), dpi=130)
    plt.close(fig)


def main():
    with PdfPages(OUT) as pdf:
        page1_exploded(pdf)
        _panel_half_page(pdf, "L")
        _panel_half_page(pdf, "R")
        page4_legend(pdf)
    print("PDF:", OUT)


if __name__ == "__main__":
    main()
