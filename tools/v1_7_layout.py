#!/usr/bin/env python3
"""Букифон v1.7 — финальная 2D-раскладка панели 380 × 210, наклон клавиатур ±20°.

Исправление против spec v1.5: в JSON v1.5 половины были повёрнуты в НЕВЕРНУЮ
сторону (зеркально макету: тамбы наружу). Правильное направление («V» наружу,
тамбы к центру-внизу, как на фото заказчика) — левая половина −20° в координатах
панели (Y вниз). При нём X-проекция половины РАСТЁТ с наклоном (146.5 при 0° →
153.2 при 15° → ~157 при 20°), поэтому 340 × 185 не влезает ни при каком наклоне
(уже при 0° нужно ~345 мм) — панель 380 × 210 обоснована.

Выход: spec/panel-spec-v1.7.json, renders/templates/bukifon_v1_7_full.png,
renders/v1_7_layout_report.txt.
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mp
import matplotlib.pyplot as plt
from shapely.geometry import box as Box, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lapka42_geometry as L

# ============================================================================
# ПАРАМЕТРЫ v1.7 (числа и их обоснование — в отчёте и spec/70-v1.7.md)
# ============================================================================
PW, PH = 380.0, 210.0        # макет заказчика (бумажная сборка v1.5, фото IMG_0704)
TILT = 20.0                  # наклон наружу; фото: 10–15° визуально, ТЗ: 15–20°,
                             # бумажный макет заказчика собран с 20° — берём его
EDGE = 7.0                   # поле от окон клавиш до края панели (5 min + 2 запас)

KNOB_D = 14.0
KNOB_COLS = [22.0, 49.0, 76.0, 103.0]      # шаг 27 (ТЗ), левый блок
KNOB_ROWS = [26.0, 53.0]
KNOBS_L = [(x, y) for x in KNOB_COLS for y in KNOB_ROWS]
KNOBS_R = [(PW - x, y) for x in KNOB_COLS for y in KNOB_ROWS]  # 277…358

SCREEN_W, SCREEN_H = 108.0, 64.8
SCREEN_X, SCREEN_Y = (PW - SCREEN_W) / 2, 11.5    # 136…244

JACK_D, JACK_Y = 6.0, 7.0
JACK_X0 = (PW - 9 * 11.0) / 2                     # 135.5, шаг 11, 10 шт.
JACKS = [JACK_X0 + 11.0 * i for i in range(10)]

FADER_PITCH = 20.0
FADER_XS = [PW / 2 - 10.0, PW / 2 + 10.0]         # 180 / 200
FADER_SLOT_W = 8.0
FADER_SLOT_Y0, FADER_SLOT_Y1 = 116.0, 196.0       # 80: ход 60 + колпачок 12 + зазоры
FADER_CAP_W = 16.0

CAP_W, CAP_H = L.KEYCAP_W, L.KEYCAP_H             # 17.5 × 16.5
KEY_WIN_CLEAR = 1.0                               # окно в панели = колпачок + 1 мм


def _cap_poly(x, y, rot, grow=KEY_WIN_CLEAR):
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    hw, hh = CAP_W / 2 + grow, CAP_H / 2 + grow
    pts = [(x + ca * sx * hw - sa * sy * hh, y + sa * sx * hw + ca * sy * hh)
           for sx in (-1, 1) for sy in (-1, 1)]
    return Polygon(pts).convex_hull


def build_keys(tilt=TILT):
    """Половины Lapka-42, наклон наружу («V»), тамбы к центру-внизу.
    Левая: поворот −tilt (координаты панели, Y вниз); правая: зеркало +tilt."""
    raw = L.LAPKA42_LEFT
    c = (sum(p[0] for p in raw) / len(raw), sum(p[1] for p in raw) / len(raw))
    out = {}
    for side, ang in (("L", -tilt), ("R", tilt)):
        a = math.radians(ang)
        ca, sa = math.cos(a), math.sin(a)
        ks = []
        for (x, y, r) in raw:
            dx, dy = x - c[0], y - c[1]
            if side == "R":
                dx, r = -dx, -r
            ks.append((c[0] + ca * dx - sa * dy, c[1] + sa * dx + ca * dy, r + ang))
        u = unary_union([_cap_poly(x, y, r) for x, y, r in ks])
        x0, y0, x1, y1 = u.bounds
        ty = (PH - EDGE) - y1                     # прижать к нижней кромке
        tx = EDGE - x0 if side == "L" else (PW - EDGE) - x1
        out[side] = [(x + tx, y + ty, r) for x, y, r in ks]
    return out


def main():
    keys = build_keys()
    polys = {s: [_cap_poly(x, y, r) for x, y, r in ks] for s, ks in keys.items()}
    uL, uR = unary_union(polys["L"]), unary_union(polys["R"])
    uKB = unary_union([uL, uR])
    rep, fails = [], []

    w = rep.append
    w("Букифон v1.7 — раскладка панели %.0f × %.0f, наклон клавиатур ±%.0f°" % (PW, PH, TILT))
    w("=" * 74)
    w("")
    w("[Габарит] 380 × 210, а не 340 × 185 (обоснование):")
    w("  Правильный наклон (V наружу, тамбы к центру — как на макете заказчика)")
    w("  УВЕЛИЧИВАЕТ X-проекцию половины: 0° → 146.5 мм, 15° → 153.2, 20° → ~157.")
    w("  Минимум по ширине при 20°: 2 × 157 + фейдеры 40 + поля 2 × 7 = 368 ≤ 380 ✔")
    w("  (при 15°: 2 × 153.2 + 40 + 14 = 360.4 — экономия всего 20 мм,")
    w("   а бумажный макет заказчика уже собран с 20° на 380 × 210)")
    for s, u in (("L", uL), ("R", uR)):
        x0, y0, x1, y1 = u.bounds
        w("  половина %s: X %.1f…%.1f  Y %.1f…%.1f  (%.1f × %.1f)"
          % (s, x0, x1, y0, y1, x1 - x0, y1 - y0))
    w("  центральный канал на уровне фейдеров: X %.1f … %.1f (ширина %.1f)"
      % (uL.bounds[2], uR.bounds[0], uR.bounds[0] - uL.bounds[2]))
    w("")

    w("[Проверки пересечений]")
    screen = Box(SCREEN_X, SCREEN_Y, SCREEN_X + SCREEN_W, SCREEN_Y + SCREEN_H)
    jacks_g = unary_union([Point(x, JACK_Y).buffer(JACK_D / 2 + 1.0) for x in JACKS])
    knobs_g = unary_union([Point(x, y).buffer(KNOB_D / 2 + 1.0)
                           for x, y in KNOBS_L + KNOBS_R])
    fader_zone = Box(min(FADER_XS) - FADER_CAP_W / 2 - 1.0, FADER_SLOT_Y0 - 2,
                     max(FADER_XS) + FADER_CAP_W / 2 + 1.0, FADER_SLOT_Y1 + 2)
    panel = Box(0, 0, PW, PH)

    def check(name, a, b, min_gap=0.0):
        d = a.distance(b)
        ok = d >= min_gap
        if not ok:
            fails.append(name)
        w("  %-46s зазор %6.2f  %s" % (name, d, "✔" if ok else "✘"))

    check("джеки ↔ экран", jacks_g, screen)
    check("джеки ↔ кромка Y=0", jacks_g, Box(0, -99, PW, 0))
    check("джеки ↔ ручки", jacks_g, knobs_g)
    check("ручки ↔ экран", knobs_g, screen)
    check("клавиатура L ↔ R", uL, uR, 6.0)
    check("клавиатуры ↔ ручки", uKB, knobs_g, 2.0)
    check("клавиатуры ↔ экран", uKB, screen, 2.0)
    check("клавиатуры ↔ фейдеры", uKB, fader_zone, 2.0)
    off = [p for p in polys["L"] + polys["R"] if not panel.contains(p)]
    w("  %-46s %s" % ("окна клавиш внутри панели", "✔" if not off else "✘ %d шт" % len(off)))
    if off:
        fails.append("окна за краем")
    strip = Box(0, FADER_SLOT_Y0 - 2, PW, FADER_SLOT_Y1 + 2).difference(uKB)
    okf = strip.contains(fader_zone)
    w("  %-46s %s" % ("зона фейдеров свободна по всей длине", "✔" if okf else "✘"))
    if not okf:
        fails.append("fader_strip")
    w("")
    w("ИТОГ: %s" % ("ВСЁ ЧИСТО ✔" if not fails else "ОШИБКИ: %s" % fails))

    spec = {
        "project": "Bukifon (Букифон)", "variant": "v1.7",
        "panel": {"w": PW, "h": PH, "thickness": 3.0, "units": "mm",
                  "origin": "x right, y from rear edge"},
        "screen": {"x": SCREEN_X, "y": SCREEN_Y, "w": SCREEN_W, "h": SCREEN_H},
        "jacks": [{"x": round(x, 2), "y": JACK_Y, "type": "3.5mm", "hole": JACK_D}
                  for x in JACKS],
        "faders": [{"x": x, "y0": FADER_SLOT_Y0, "y1": FADER_SLOT_Y1,
                    "slot_w": FADER_SLOT_W} for x in FADER_XS],
        "knobs": [dict(x=x, y=y, d=KNOB_D) for x, y in KNOBS_L + KNOBS_R],
        "keyboard": {
            "model": "Lapka-42 split, Choc v1/v2, 2 × 21, splay",
            "keycap": {"w": CAP_W, "h": CAP_H}, "pitch": {"x": 18.0, "y": 17.0},
            "rotation_deg": TILT, "rotation_dir": "V-наружу, тамбы к центру-внизу",
            "window_clearance": KEY_WIN_CLEAR,
            "keys_42": [dict(x=round(x, 2), y=round(y, 2), angle_deg=round(r, 2), half=s)
                        for s in ("L", "R") for (x, y, r) in keys[s]],
        },
        "fixes_vs_v1.5": [
            "v1.5 JSON содержал зеркальный (неверный) наклон половин — исправлено",
            "направление проверено по фото макета (V наружу, тамбы к центру)",
        ],
        "notes": [
            "Экран без рамки: вырез = активная область 108 × 64.8",
            "Динамиков нет; разъёмов под экраном нет",
            "380 × 210: единственный габарит, вмещающий наклон как на макете",
        ],
    }
    with open(os.path.join(ROOT, "spec", "panel-spec-v1.7.json"), "w") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "renders", "v1_7_layout_report.txt"), "w") as f:
        f.write("\n".join(rep) + "\n")
    print("\n".join(rep))

    # --- превью ---
    fig, ax = plt.subplots(figsize=(13.4, 7.6), dpi=160)
    ax.set_xlim(-8, PW + 8)
    ax.set_ylim(PH + 8, -10)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(mp.FancyBboxPatch((0, 0), PW, PH, boxstyle="round,pad=0,rounding_size=4",
                                   fc="#f8f8f5", ec="#222", lw=1.8))
    for gx in range(0, int(PW) + 1, 10):
        ax.plot([gx, gx], [0, PH], color="#eeeee9", lw=0.25, zorder=1)
    for gy in range(0, int(PH) + 1, 10):
        ax.plot([0, PW], [gy, gy], color="#eeeee9", lw=0.25, zorder=1)
    for (x, y) in KNOBS_L + KNOBS_R:
        ax.add_patch(mp.Circle((x, y), KNOB_D / 2, fc="#ececec", ec="#333", lw=1.0, zorder=4))
        ax.plot([x, x], [y + 2.2, y + 6.4], color="#0a0", lw=1.2, zorder=5)
    ax.add_patch(mp.FancyBboxPatch((SCREEN_X, SCREEN_Y), SCREEN_W, SCREEN_H,
                                   boxstyle="round,pad=0,rounding_size=1.2",
                                   fc="#101a10", ec="#333", lw=0.8, zorder=4))
    ax.text(SCREEN_X + SCREEN_W / 2, SCREEN_Y + SCREEN_H / 2,
            "5.0″ 800×480\nвырез 108 × 64.8", ha="center", va="center",
            fontsize=6.5, color="#7fae7f", zorder=5)
    for x in JACKS:
        ax.add_patch(mp.Circle((x, JACK_Y), JACK_D / 2, fc="#e9e9e4", ec="#333", lw=0.7, zorder=4))
    for x in FADER_XS:
        ax.add_patch(mp.FancyBboxPatch(
            (x - FADER_SLOT_W / 2, FADER_SLOT_Y0), FADER_SLOT_W,
            FADER_SLOT_Y1 - FADER_SLOT_Y0, boxstyle="round,pad=0,rounding_size=4",
            fc="#dcdcdc", ec="#444", lw=0.8, zorder=4))
        ax.add_patch(mp.Rectangle((x - FADER_CAP_W / 2, 150), FADER_CAP_W, 10,
                                  fc="#333", ec="#111", lw=0.5, zorder=5))
    for s in ("L", "R"):
        for (x, y, r) in keys[s]:
            ax.add_patch(mp.Rectangle((x - CAP_W / 2, y - CAP_H / 2), CAP_W, CAP_H,
                                      angle=r, rotation_point="center",
                                      fc="#d8e6f7", ec="#4a6b8a", lw=0.6, zorder=6))
    ax.set_title("Букифон v1.7 · панель 380 × 210 · наклон ±%.0f° (V наружу, как на макете) · "
                 "16 ручек, экран 5″ 108×64.8, 10 mini-jack, 2 фейдера, 2 × 21 Lapka-42" % TILT,
                 fontsize=10, pad=8)
    fig.savefig(os.path.join(ROOT, "renders", "templates", "bukifon_v1_7_full.png"),
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("\nJSON + превью + отчёт записаны")


if __name__ == "__main__":
    main()
