#!/usr/bin/env python3
"""Букифон v1.7 — обоснование габарита панели по точной геометрии Lapka-42.

Считает AABB каждой половины (по колпачкам) при наклоне 0…20°, минимальную ширину
панели (2 половины + зона фейдеров) и минимальную высоту (экран/ручки сверху +
клавиатура снизу). Заодно сверяет spec/panel-spec-v1.5.json с собственной раскладкой.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lapka42_geometry as L

CAP_W, CAP_H = L.KEYCAP_W, L.KEYCAP_H


def cap_bbox(keys):
    """AABB по колпачкам: каждая клавиша (x, y, rot), колпачок CAP_W × CAP_H."""
    xs, ys = [], []
    for x, y, rot in keys:
        a = math.radians(rot)
        ca, sa = math.cos(a), math.sin(a)
        hw, hh = CAP_W / 2, CAP_H / 2
        for sx in (-1, 1):
            for sy in (-1, 1):
                xs.append(x + ca * sx * hw - sa * sy * hh)
                ys.append(y + sa * sx * hw + ca * sy * hh)
    return min(xs), min(ys), max(xs), max(ys)


def rotate_keys(keys, deg, cx=None, cy=None):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    if cx is None:
        pts = [(x, y) for x, y, _ in keys]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for x, y, rot in keys:
        dx, dy = x - cx, y - cy
        out.append((cx + ca * dx - sa * dy, cy + sa * dx + ca * dy, rot + deg))
    return out


print("== Исходная половина Lapka-42 (без наклона) ==")
b = cap_bbox(L.LAPKA42_LEFT)
print(f"  AABB по колпачкам: {b[2]-b[0]:.2f} × {b[3]-b[1]:.2f} мм (ожидание 146.48 × 85.5)")

FADER_ZONE = 42.0    # 2 фейдера: шаг 20 + колпачок 16 + зазоры 2×3
EDGE = 5.0           # минимальный поля панели до колпачков
SCREEN_BOT = 76.3    # низ выреза экрана (Y при screen y=11.5, h=64.8)
KNOB_BOT = 53 + 14 / 2 + 2   # низ ручек 2-го ряда + зазор 2

print("\n== Наклон: AABB половины и потребный габарит ==")
print(f"{'угол':>5} {'W полу':>8} {'H полу':>8} {'MIN PW':>8} {'KEY_TOP':>8} {'MIN PH':>8}")
rows = {}
for tilt in (0, 5, 10, 12.5, 15, 17.5, 20):
    k = rotate_keys(L.LAPKA42_LEFT, tilt)
    bb = cap_bbox(k)
    W, H = bb[2] - bb[0], bb[3] - bb[1]
    min_pw = 2 * W + FADER_ZONE + 2 * EDGE
    # верх клавиатуры: не выше ручек (по бокам) и не выше экрана+зазор (центр)
    key_top = max(KNOB_BOT + 2, SCREEN_BOT - 18)  # у наклонённой половины верх у края
    min_ph = key_top + H + EDGE
    rows[tilt] = (W, H, min_pw, key_top, min_ph)
    print(f"{tilt:>5} {W:>8.1f} {H:>8.1f} {min_pw:>8.1f} {key_top:>8.1f} {min_ph:>8.1f}")

print("\nВывод: ширина слабо зависит от угла (159→167 при 10→20°),")
print("высота растёт: H(15°)≈{:.1f}, H(20°)≈{:.1f}.".format(rows[15][1], rows[20][1]))

# --- сверка с v1.5 JSON -----------------------------------------------------
print("\n== spec/panel-spec-v1.5.json: пересчёт AABB по keys_42 ==")
with open(os.path.join(os.path.dirname(HERE), "spec", "panel-spec-v1.5.json")) as f:
    spec = json.load(f)
k42 = spec["keyboard"]["keys_42"]
left = [(k["x"], k["y"], k["angle_deg"]) for k in k42[:21]]
right = [(k["x"], k["y"], k["angle_deg"]) for k in k42[21:]]
bl, br = cap_bbox(left), cap_bbox(right)
print(f"  левая : X {bl[0]:.1f}…{bl[2]:.1f}, Y {bl[1]:.1f}…{bl[3]:.1f}  "
      f"({bl[2]-bl[0]:.1f} × {bl[3]-bl[1]:.1f})")
print(f"  правая: X {br[0]:.1f}…{br[2]:.1f}, Y {br[1]:.1f}…{br[3]:.1f}  "
      f"({br[2]-br[0]:.1f} × {br[3]-br[1]:.1f})")
print(f"  зазор между половинами: {br[0]-bl[2]:.1f} мм (панель 380)")

# жёсткость: расстояния между парами клавиш до/после поворота (проверка, что
# v1.5 не масштабировал геометрию)
p0 = L.LAPKA42_LEFT
for i, j in ((0, 20), (9, 20), (1, 19)):
    d0 = math.dist(p0[i][:2], p0[j][:2])
    d1 = math.dist(left[i][:2], left[j][:2])
    print(f"  dist key{i+1}-key{j+1}: исходно {d0:.2f}, в v1.5 {d1:.2f} "
          f"{'OK' if abs(d0-d1) < 0.05 else 'РАЗМЯТО?!'}")

# угол поворота половины в v1.5 (по вектору между крайними клавишами)
v0 = (p0[20][0] - p0[0][0], p0[20][1] - p0[0][1])
v1 = (left[20][0] - left[0][0], left[20][1] - left[0][1])
a0 = math.degrees(math.atan2(v0[1], v0[0]))
a1 = math.degrees(math.atan2(v1[1], v1[0]))
print(f"  угол оси половины: исходно {a0:.1f}°, в v1.5 {a1:.1f}° → поворот {a1-a0:+.1f}°")
