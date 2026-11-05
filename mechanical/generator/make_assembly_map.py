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
            "БУКИФОН v0.5-B-light · СБОРОЧНАЯ КАРТА (разнесённая схема, 1:2.5)",
            ha="center", fontsize=12, fontweight="bold")
    ax.text(A4L[0] / 2, A4L[1] - 14.5,
            "Печать A4 100 %. Слои снизу вверх; точки крепежа и шлейфы — по выноскам. "
            "1:1 — панельные листы стр.2–3.",
            ha="center", fontsize=5.8, color="#444")

    # ---------- слои (снизу вверх), центр панели (190,105) ----------
    S = 0.62
    # 1 корпус (2 половины)
    rrect_iso(ax, 95, 105, 188, 208, 0, color="#4a4f55", ec="#222", label="body_L")
    rrect_iso(ax, 285, 105, 188, 208, 0, color="#4a4f55", ec="#222", label="body_R")
    leader(ax, *iso(95, 105, 0), 14, 24,
           "1. КОРПУС B-light: body_L + body_R (193+190 с шипом), дно 1.8, стенки 2.0",
           fs=4.8)
    # 2 батарея (опция) справа внутри
    rrect_iso(ax, 330, 88, 80, 62, 10, color="#c9d6e8", ec="#2c6fbb", ls=(0, (2, 1.5)),
              label="2×18650")
    leader(ax, *iso(330, 88, 10), 214, 24,
           "2. Батарея 1S2P 18650 (опция) — ложемент справа X300…340",
           fs=4.6, color="#2c6fbb")
    # 3 PWR-2
    rrect_iso(ax, 190, 100, 90, 70, 28, color="#c33", ec="#600", label="PWR-2",
              alpha=0.9)
    leader(ax, *iso(190, 100, 28), 14, 42,
           "3. PWR-2 rev.1 90×70 (Z6, 4×M2.5): ±12 В / +5 В / 5V_LED",
           fs=4.6, color="#900")
    # 4 CORE-S3
    rrect_iso(ax, 190, 105, 200, 108, 48, color="#2f7d4f", ec="#174", label="CORE-S3",
              alpha=0.92)
    leader(ax, *iso(190, 105, 48), 14, 58,
           "4. CORE-S3 rev.0 200×108 (Z12, 4×M3): J14/J15/J16 ↔ PANEL-2, J17/J18 ↔ PWR-2",
           fs=4.6, color="#174")
    # 5 PANEL-2
    rrect_iso(ax, 190, 105, 360, 190, 74, color="#2a5f9e", ec="#123", ls=(0, (3, 2)),
              label="PANEL-2", alpha=0.75)
    leader(ax, *iso(190, 105, 74), 214, 58,
           "5. PANEL-2 rev.2 360×190 (8 мм под панелью, 6×M3×6): J12 FFC-40, "
           "J13 IDC-16, J14 IDC-26", fs=4.6, color="#123")
    # 6 дисплей
    rrect_iso(ax, 190, 58, 121, 76, 94, color="#0b2a4a", ec="#89a", label="LCD 5\"")
    leader(ax, *iso(190, 58, 94), 214, 76,
           "6. Дисплей 5\" 800×480 (120.7×75.8) — FFC-40, стекло в окно 108×64.8",
           fs=4.6, color="#123")
    # 7 панель L/R (сверху), с эскизом органов
    rrect_iso(ax, 95, 105, 188, 208, 116, color="#222", ec="#000", label="")
    rrect_iso(ax, 285, 105, 188, 208, 116, color="#222", ec="#000", label="")
    for k in C["keyboard_left"]:
        x, y = k["center_mm"]
        px, py = iso(x, y, 116, S)
        ax.add_patch(Rectangle((px - 4, py - 3), 8, 6, fc="#e8e2d6", ec="#777", lw=0.2,
                               zorder=30, angle=-k["angle_deg"]))
    for k in C["keyboard_right"]:
        x, y = k["center_mm"]
        px, py = iso(x, y, 116, S)
        ax.add_patch(Rectangle((px - 4, py - 3), 8, 6, fc="#e8e2d6", ec="#777", lw=0.2,
                               zorder=30, angle=-k["angle_deg"]))
    for e in C["encoders_left"] + C["encoders_right"]:
        px, py = iso(*e["center_mm"], 116, S)
        ax.add_patch(Circle((px, py), 2.6, fc="#111", ec="#888", lw=0.2, zorder=31))
    for j in C["jacks"]:
        px, py = iso(*j["center_mm"], 116, S)
        ax.add_patch(Circle((px, py), 1.6, fc="#ddd", ec="#666", lw=0.2, zorder=31))
    for f in C["faders"]:
        px, py = iso(*f["slot"]["center_mm"], 116, S)
        ax.add_patch(Rectangle((px - 1, py - 6), 2, 12, fc="#000", ec="#999", lw=0.2,
                               zorder=31))
    leader(ax, *iso(285, 105, 116), 214, 94,
           "7. ПАНЕЛЬ v0.4 193+190 (1:1 на стр.2–3): 42 клавиши, 16 энкодеров, "
           "2 фейдера, 10 джеков, 4×M3×8", fs=4.8, color="#000")
    ax.text(148, 6, "ПОРЯДОК СБОРКИ — СНИЗУ ВВЕРХ (1→7); шлейфы — после установки PANEL-2 "
                    "и CORE-S3; дисплей — до закрытия панели", fontsize=5.4,
            ha="center", color="#333")

    # стрелки «вверх» и легенда
    ax.annotate("", xy=(278, 150), xytext=(278, 30),
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#666"))
    ax.text(281, 90, "сборка\nснизу\nвверх", fontsize=5.2, color="#666", va="center")

    # точки крепежа
    for (x, y) in PANEL_SCREWS:
        px, py = iso(x, y, 116, S)
        ax.add_patch(plt.Circle((px, py), 3.0, fc="none", ec="#c00", lw=0.9,
                                zorder=40))
    ax.text(20, 128, "○ 4×M3×8 — панель по углам", fontsize=4.8, color="#c00")
    for (x, y) in PANEL_POSTS:
        px, py = iso(x, y, 116, S)
        ax.add_patch(plt.Circle((px, py), 2.2, fc="none", ec="#ff0", lw=0.8,
                                zorder=40, ls=(0, (1, 1))))
    ax.text(20, 123, "○ 6×M3×6 — PANEL-2 (жёлтые) + 4×M3×6 CORE-S3 / 4×M2.5 PWR-2",
            fontsize=4.6, color="#990")
    ruler(ax, 20, 8)

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
        ax.text(ox + x, oy + 210 - y, f"{i+1}", fontsize=3.4, ha="center", va="center",
                color="#333")
    # энкодеры
    enc = C["encoders_left"] if side == "L" else C["encoders_right"]
    names = "ABCDEFGH"
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
            ax.text(ox + x + 4, oy + 210 - y + 3, "M3", fontsize=3.8, color="#c00")
    for (x, y) in PANEL_POSTS:
        if x0 - 5 <= x <= x1 + 5:
            ax.add_patch(Circle((ox + x, oy + 210 - y), 2.4, fc="none", ec="#990",
                                lw=0.8, ls=(0, (1, 1))))
            ax.text(ox + x + 3.5, oy + 210 - y - 4, "M3", fontsize=3.6, color="#990")
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

    ax.text(14, 30, "НЕ ЗАБЫТЬ: энкодеры ставить ДО панели? — нет: панель лежит сверху, "
                    "энкодеры/клавиши/джеки — после панели (гайки сверху).",
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
