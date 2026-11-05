#!/usr/bin/env python3
"""Букифон v1.2 — чертежи: HEAD 62 HP × 3U и сменные деки (Lapka-42 / PAD).

HEAD   : 314.96 × 128.5 мм, динамики над экраном, 8 ручек, 8 кнопок, 2 слайдера,
         патч-полоса разъёмов на нижней части панели (еврорек: разъёмы на панели).
DECK   : 300 × 84 (42 клавиши Lapka-42, splay) или 300 × 72 (18 пэдов).
Запуск : MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python tools/v1_2_layout.py
Выход  : renders/v1_2_head.png, v1_2_deck_lapka.png, v1_2_deck_pads.png, v1_2_report.txt
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lapka42_geometry as L42

W, H = 314.96, 128.50
DECK_W, DECK_H = 310.0, 88.0        # 42 клавиши Lapka-42 с колпачками и splay
PAD_DECK_H = 76.0
KEY_OFFSET_X, KEY_OFFSET_Y = 11.59, 9.98   # из расчёта bbox повёрнутых колпачков

SPEAKERS = [(145.0, 9.0), (170.0, 9.0)]
SPK_D = 16.0
SCREEN = (157.5, 37.0, 46.0, 34.0)
KNOBS = [(x, y) for x in (30.0, 60.0) for y in (26.0, 50.0)] + \
        [(x, y) for x in (255.0, 285.0) for y in (26.0, 50.0)]
SIDE_BTNS = [(96.0, 26.0), (114.0, 26.0), (96.0, 50.0), (114.0, 50.0),
             (201.0, 26.0), (219.0, 26.0), (201.0, 50.0), (219.0, 50.0)]
SHOULDER = [(12.0, 9.0), (30.0, 9.0), (285.0, 9.0), (303.0, 9.0)]
STATUS = (157.5, 56.0)
FADERS = [(80.0, 24.0, 52.0), (237.0, 24.0, 52.0)]
DECK_PORT = (157.5, 121.0, 22.0, 10.0)

ROW1 = [("CV OUT 1", "jack"), ("CV OUT 2", "jack"), ("CV IN 1", "jack"), ("CV IN 2", "jack"),
        ("GATE 1", "jack"), ("GATE 2", "jack"), ("MIDI IN", "jack"), ("MIDI OUT", "jack"),
        ("AUD IN L", "jack"), ("AUD IN R", "jack"), ("AUD OUT L", "jack")]
ROW2 = [("AUD OUT R", "jack"), ("PHONES", "jack"), ("EXPR", "bigjack"), ("DC 12V", "dc"),
        ("USB-C DATA", "usb"), ("USB-C CHARGE", "usb"), ("POWER", "sw"), ("SPK", "sw"),
        ("RESET", "sw"), ("DECK", "idc"), ("SPARE", "jack")]


def key_positions():
    out = []
    for (x, y, rot) in L42.LAPKA42_LEFT:
        out.append((KEY_OFFSET_X + x, KEY_OFFSET_Y + y, rot))
    for (x, y, rot) in L42.LAPKA42_LEFT:
        out.append((DECK_W - KEY_OFFSET_X - x, KEY_OFFSET_Y + y, -rot))
    return out


def circle_jack(ax, x, y, r=3.0, label=None, fs=4.0):
    ax.add_patch(mp.Circle((x, y), r, fc="#e9e9e9", ec="#333", lw=0.8, zorder=6))
    ax.add_patch(mp.Circle((x, y), r * 0.36, fc="#555", ec="#333", lw=0.4, zorder=7))
    if label:
        ax.text(x, y + r + 1.6, label, fontsize=fs, ha="center", va="bottom", color="#444")


def draw_head(ax, title):
    ax.set_xlim(-10, W + 16)
    ax.set_ylim(H + 14, -12)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0, 0), W, H, boxstyle="round,pad=0,rounding_size=5",
                                   lw=2.2, ec="#222", fc="#f8f8f6", zorder=0))
    ax.text(W / 2, -3, "эврорек-панель 62 HP (314.96) × 3U (128.5)", ha="center", va="top",
            fontsize=7, color="#777")

    # динамики
    for i, (x, y) in enumerate(SPEAKERS):
        ax.add_patch(mp.Circle((x, y), SPK_D / 2, fc="#dcdcdc", ec="#333", lw=1.1, zorder=5))
        ax.add_patch(mp.Circle((x, y), SPK_D / 2 - 1.5, fc="#c2c2c2", ec="#777", lw=0.5, zorder=6))
        ax.add_patch(mp.Circle((x, y), 1.9, fc="#888", ec="#555", lw=0.4, zorder=7))
        for k in range(8):
            a = 2 * math.pi * k / 8
            ax.plot([x + 3.1 * math.cos(a), x + 5.6 * math.cos(a)],
                    [y + 3.1 * math.sin(a), y + 5.6 * math.sin(a)], color="#999", lw=0.6, zorder=7)
        ax.text(x, y + 9.6, f"SPK{i+1}", fontsize=4.6, ha="center", color="#666")

    # экран
    cx, cy, sw, sh = SCREEN
    ax.add_patch(mp.Rectangle((cx - sw / 2 - 3, cy - sh / 2 - 3), sw + 6, sh + 6,
                              fc="#e4e4e0", ec="#999", lw=0.7, zorder=4))
    ax.add_patch(mp.Rectangle((cx - sw / 2, cy - sh / 2), sw, sh,
                              fc="#203040", ec="#111", lw=1.1, zorder=5))
    ax.text(cx, cy, '2.0" 320×240', color="#dfe9f3", ha="center", va="center", fontsize=6, zorder=6)

    # ручки
    for i, (x, y) in enumerate(KNOBS):
        ax.add_patch(mp.Circle((x, y), 7.0, fc="#ececec", ec="#333", lw=1.0, zorder=6))
        ax.add_patch(mp.Circle((x, y), 5.2, fc="none", ec="#bbb", lw=0.4, zorder=7))
        ax.plot([x, x], [y - 5.8, y - 1.0], color="#d33", lw=1.2, zorder=8)
        ax.text(x, y + 8.3, f"E{i+1}", fontsize=4.3, ha="center", color="#666")

    # кнопки у экрана
    for i, (x, y) in enumerate(SIDE_BTNS):
        ax.add_patch(mp.FancyBboxPatch((x - 4.5, y - 4.5), 9, 9,
                                       boxstyle="round,pad=0,rounding_size=1.1",
                                       fc="#dde8f2", ec="#4a6b8a", lw=0.8, zorder=6))
        ax.text(x, y, str(i + 1), fontsize=4.3, ha="center", va="center", color="#2c4a63", zorder=7)

    # плечевые
    for i, (x, y) in enumerate(SHOULDER):
        ax.add_patch(mp.Circle((x, y), 4.0, fc="#dde", ec="#334", lw=0.8, zorder=6))
        ax.text(x, y, "L1 L2 R1 R2".split()[i], fontsize=4.0, ha="center", va="center", zorder=7)

    ax.add_patch(mp.Circle(STATUS, 1.6, fc="#2a2", ec="#171", lw=0.6, zorder=6))

    # слайдеры (вертикальные, верхняя зона)
    for i, (x, y0, y1) in enumerate(FADERS):
        ax.add_patch(mp.FancyBboxPatch((x - 4, y0 - 4), 8, (y1 - y0) + 8,
                                       boxstyle="round,pad=0,rounding_size=3",
                                       fc="#dcdcdc", ec="#444", lw=0.8, zorder=6))
        ax.add_patch(mp.Rectangle((x - 7, y0 + 6), 14, 8, fc="#444", ec="#111", lw=0.6, zorder=7))
        ax.text(x, y1 + 7, f"SL{i+1}", fontsize=5.4, ha="center", color="#555")

    # патч-полоса
    ax.plot([8, W - 8], [63, 63], color="#bbb", lw=0.6, ls=(0, (4, 3)))
    ax.text(10, 65.5, "патч-полоса: CV / GATE / MIDI / AUDIO IN-OUT / USB / DC", fontsize=5.2,
            color="#888", va="top")
    for row, (y, items, x0, step) in enumerate([(74, ROW1, 20, 27), (100, ROW2, 34, 27)]):
        for i, (name, kind) in enumerate(items):
            x = x0 + i * step
            if kind == "jack":
                circle_jack(ax, x, y, 3.0, name, fs=3.4)
            elif kind == "bigjack":
                circle_jack(ax, x, y, 4.6, name, fs=3.4)
            elif kind == "usb":
                ax.add_patch(mp.FancyBboxPatch((x - 6, y - 3.5), 12, 7,
                                               boxstyle="round,pad=0,rounding_size=1.2",
                                               fc="#e9e9e9", ec="#333", lw=0.8, zorder=6))
                ax.text(x, y + 5.2, name, fontsize=3.4, ha="center", va="bottom", color="#444")
            elif kind == "dc":
                ax.add_patch(mp.Circle((x, y), 4.5, fc="#e9e9e9", ec="#333", lw=0.8, zorder=6))
                ax.add_patch(mp.Circle((x, y), 1.3, fc="#555", ec="#333", lw=0.4, zorder=7))
                ax.text(x, y + 6.4, name, fontsize=3.4, ha="center", va="bottom", color="#444")
            elif kind == "sw":
                ax.add_patch(mp.Rectangle((x - 5, y - 3), 10, 6, fc="#e9e9e9", ec="#333", lw=0.7, zorder=6))
                ax.text(x, y + 5.6, name, fontsize=3.4, ha="center", va="bottom", color="#444")
            elif kind == "idc":
                ax.add_patch(mp.Rectangle((x - 11, y - 5), 22, 10, fc="#f2e2c0", ec="#a76", lw=0.7, zorder=6))
                ax.text(x, y + 7.6, name, fontsize=3.4, ha="center", va="bottom", color="#444")

    # порт деки
    dx, dy, dw, dh = DECK_PORT
    ax.add_patch(mp.Rectangle((dx - dw / 2, dy - dh / 2), dw, dh, fc="#f2e2c0", ec="#a76",
                              lw=0.9, zorder=6))
    ax.text(dx, dy, "DECK  IDC-16", fontsize=4.2, ha="center", va="center", color="#7a5320", zorder=7)
    ax.text(dx, dy + dh / 2 + 1.5, "шлейф к деке", fontsize=3.6, ha="center", va="bottom", color="#8a6a1f")

    # размеры
    ax.annotate("", xy=(0, H + 6), xytext=(W, H + 6), arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(W / 2, H + 7, "314.96 мм = 62 HP", ha="center", va="top", fontsize=7.2, color="#666")
    ax.annotate("", xy=(W + 6, 0), xytext=(W + 6, H), arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(W + 7, H / 2, "128.5 мм = 3U", va="center", rotation=90, fontsize=7.2, color="#666")
    ax.set_title(title, fontsize=11.5, pad=10)


def draw_deck_lapka(ax, title):
    ax.set_xlim(-10, DECK_W + 16)
    ax.set_ylim(DECK_H + 16, -10)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0, 0), DECK_W, DECK_H, boxstyle="round,pad=0,rounding_size=4",
                                   lw=2.0, ec="#222", fc="#f8f8f6", zorder=0))
    cap_w, cap_h = L42.KEYCAP_W, L42.KEYCAP_H
    for i, (x, y, rot) in enumerate(key_positions()):
        ax.add_patch(mp.Rectangle((x - cap_w / 2, y - cap_h / 2), cap_w, cap_h,
                                  angle=rot, rotation_point="center",
                                  fc="#cfe3f7", ec="#4a6b8a", lw=0.6, zorder=6))
        ax.text(x, y, str(i + 1), fontsize=3.0, ha="center", va="center", color="#24384a", zorder=7)
    ax.text(DECK_W / 2, DECK_H / 2, "LAPKA-42 · splay 18×17 · Choc v1/v2", fontsize=6,
            ha="center", va="center", color="#7d94a8", zorder=8)
    ax.annotate("", xy=(0, DECK_H + 6), xytext=(DECK_W, DECK_H + 6),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(DECK_W / 2, DECK_H + 7, f"{DECK_W:.0f} мм", ha="center", va="top", fontsize=7, color="#666")
    ax.annotate("", xy=(DECK_W + 6, 0), xytext=(DECK_W + 6, DECK_H),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(DECK_W + 7, DECK_H / 2, f"{DECK_H:.0f} мм", va="center", rotation=90, fontsize=7, color="#666")
    ax.set_title(title, fontsize=10.5, pad=10)


def draw_deck_pads(ax, title):
    ax.set_xlim(-10, DECK_W + 16)
    ax.set_ylim(PAD_DECK_H + 14, -10)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0, 0), DECK_W, PAD_DECK_H, boxstyle="round,pad=0,rounding_size=4",
                                   lw=2.0, ec="#222", fc="#f8f8f6", zorder=0))
    size = 20.0
    xs = (24.0, 50.0, 76.0)
    ys = (11.0, 37.0, 63.0)
    left = [(x, y) for x in xs for y in ys]
    for i, (x, y) in enumerate(left):
        ax.add_patch(mp.FancyBboxPatch((x - size / 2, y - size / 2), size, size,
                                       boxstyle="round,pad=0,rounding_size=2",
                                       fc="#f6c85f", ec="#8a6a1f", lw=0.8, zorder=6))
        ax.text(x, y, str(i + 1), fontsize=5, ha="center", va="center", color="#4a3608", zorder=7)
    for i, (x, y) in enumerate(left):
        cx = DECK_W - x
        ax.add_patch(mp.FancyBboxPatch((cx - size / 2, y - size / 2), size, size,
                                       boxstyle="round,pad=0,rounding_size=2",
                                       fc="#f6c85f", ec="#8a6a1f", lw=0.8, zorder=6))
        ax.text(cx, y, str(i + 10), fontsize=5, ha="center", va="center", color="#4a3608", zorder=7)
    ax.text(DECK_W / 2, PAD_DECK_H / 2, "BUKIFON", fontsize=11, ha="center", va="center",
            color="#c9c9c2", zorder=5, fontweight="bold")
    ax.annotate("", xy=(0, PAD_DECK_H + 6), xytext=(DECK_W, PAD_DECK_H + 6),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(DECK_W / 2, PAD_DECK_H + 7, f"{DECK_W:.0f} мм", ha="center", va="top", fontsize=7, color="#666")
    ax.annotate("", xy=(DECK_W + 6, 0), xytext=(DECK_W + 6, PAD_DECK_H),
                arrowprops=dict(arrowstyle="<->", color="#666", lw=0.8))
    ax.text(DECK_W + 7, PAD_DECK_H / 2, f"{PAD_DECK_H:.0f} мм", va="center", rotation=90, fontsize=7, color="#666")
    ax.set_title(title, fontsize=10.5, pad=10)


def save(fig, name):
    fig.tight_layout()
    out = os.path.join(ROOT, "renders", name)
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return out


def check():
    issues = []
    cx, cy, sw, sh = SCREEN
    for i, (x, y) in enumerate(KNOBS):
        if abs(x - cx) < sw / 2 + 7 and abs(y - cy) < sh / 2 + 7:
            issues.append(f"E{i+1} пересекает экран")
    for i, (x, y) in enumerate(SIDE_BTNS):
        if abs(x - cx) < sw / 2 + 4.5 and abs(y - cy) < sh / 2 + 4.5:
            issues.append(f"BTN{i+1} пересекает экран")
    for i, (x, y) in enumerate(SPEAKERS):
        if y + SPK_D / 2 > cy - sh / 2 - 2:
            issues.append(f"SPK{i+1} налезает на экран")
        for j, (kx, ky) in enumerate(KNOBS):
            if math.hypot(x - kx, y - ky) < SPK_D / 2 + 7:
                issues.append(f"SPK{i+1} <-> E{j+1}")
    for j, (fx, fy0, fy1) in enumerate(FADERS):
        for i, (kx, ky) in enumerate(KNOBS):
            if abs(kx - fx) < 11 and fy0 - 6 < ky < fy1 + 6:
                issues.append(f"SL{j+1} <-> E{i+1}")
        for i, (bx, by) in enumerate(SIDE_BTNS):
            if abs(bx - fx) < 8.5 and fy0 - 6 < by < fy1 + 6:
                issues.append(f"SL{j+1} <-> BTN{i+1}")
    # патч-полоса: разъёмы не пересекаются и в габарите
    for row, (y, items, x0, step) in enumerate([(74, ROW1, 20, 27), (100, ROW2, 34, 27)]):
        for i, (name, kind) in enumerate(items):
            x = x0 + i * step
            if not (5 <= x <= W - 5 and 64 <= y <= H - 5):
                issues.append(f"J{row+1}.{i+1} ({name}) вне патч-полосы")
    # клавиши в деке 300×84: проверяем реальные углы повёрнутых колпачков
    hw, hh = L42.KEYCAP_W / 2, L42.KEYCAP_H / 2
    for i, (x, y, rot) in enumerate(key_positions()):
        a = math.radians(rot)
        ca, sa = math.cos(a), math.sin(a)
        xs, ys = [], []
        for sx in (-1, 1):
            for sy in (-1, 1):
                xs.append(x + ca * sx * hw - sa * sy * hh)
                ys.append(y + sa * sx * hw + ca * sy * hh)
        if min(xs) < -0.5 or max(xs) > DECK_W + 0.5 or min(ys) < -0.5 or max(ys) > DECK_H + 0.5:
            issues.append(f"KEY{i+1} выходит за деку: x {min(xs):.1f}…{max(xs):.1f}, y {min(ys):.1f}…{max(ys):.1f}")
    return issues


def main():
    issues = check()
    f1 = plt.subplots(figsize=(13.4, 6.2), dpi=175)
    draw_head(f1[0].gca(), "Букифон v1.2 · HEAD 62 HP × 3U: 2 динамика над экраном, 8 ручек, патч-полоса")
    outs = [save(f1[0], "v1_2_head.png")]

    f2 = plt.subplots(figsize=(12.6, 5.4), dpi=175)
    draw_deck_lapka(f2[0].gca(), f"Букифон v1.2 · дека DECK-KEYS-L42 (310 × 88, 42 клавиши Lapka-42)")
    outs.append(save(f2[0], "v1_2_deck_lapka.png"))

    f3 = plt.subplots(figsize=(12.6, 4.8), dpi=175)
    draw_deck_pads(f3[0].gca(), f"Букифон v1.2 · дека DECK-PAD (310 × 76, 18 пэдов)")
    outs.append(save(f3[0], "v1_2_deck_pads.png"))

    report = "Букифон v1.2 layout check\n\n" + ("\n".join(issues) if issues else "OK: коллизий нет") + "\n"
    with open(os.path.join(ROOT, "renders", "v1_2_report.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    for p in outs:
        print("saved:", p)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
