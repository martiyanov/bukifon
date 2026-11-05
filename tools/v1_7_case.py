#!/usr/bin/env python3
"""Букифон v1.7 — генератор 3D-корпуса (CadQuery): STL + STEP.

Система координат = spec/panel-spec-v1.7.json: X вправо, Y от задней кромки
к игроку, Z вверх; панель 380 × 210, верх панели Z = 60.

Z-стек (мм):
  -3…0    ножки (резина/TPU Ø10×3, 4 шт.)         → полная высота 63
   0…3    дно скорлупы (PETG 3 мм)
   3…57   полость (стенки 2.4), электроника
  57…60   панель 3 мм (3 детали, S-шов, клеевая)

Детали (все ≤ 190 × 210, стол 220):
  shell_L/R       — половины нижней скорлупы (шов X=190, 6 шипов 8×3 + клей)
  panel_L/C/R     — панель: S-образный шов обходит экран и окна клавиш
  screen_carrier  — рамка экран-модуля 130 × 80 × 2.5
  knob ×16, fader_cap ×2

Запуск: /tmp/cqenv/bin/python -I tools/v1_7_case.py
Выход: mechanical/stl_v17/*.stl, mechanical/step_v17/*.step, отчёт проверки.
"""
import json
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STL = os.path.join(ROOT, "mechanical", "stl_v17")
STEP = os.path.join(ROOT, "mechanical", "step_v17")
os.makedirs(STL, exist_ok=True)
os.makedirs(STEP, exist_ok=True)

SPEC = json.load(open(os.path.join(ROOT, "spec", "panel-spec-v1.7.json")))
PW = SPEC["panel"]["w"]            # 380
PH = SPEC["panel"]["h"]            # 210
PANEL_T = 3.0

# --- Z-уровни ---------------------------------------------------------------
Z_FLOOR_T = 3.0        # дно
WALL = 2.4             # стенки
Z_WALL_TOP = 57.0      # верх стенок = низ панели
Z_PANEL_TOP = 60.0     # верх панели
FIT = 0.25             # зазор сопряжения

# --- электроника (мм; провизор — платы rev.3/rev.2 в работе) ----------------
CHOC_STACK = 11.3      # Choc v1 + колпачок MBK над PCB (8 + 3.3), Keeb.io
Z_DECK_PCB_BOT = Z_PANEL_TOP + 1.0 - CHOC_STACK - 1.6   # 48.1: колпачок +1 над панелью
Z_PANEL1_PCB_BOT = 43.4    # PANEL-1 rev.2 (энкодеры EC11, джеки PJ-307)
Z_CORE_PCB_BOT = 20.0      # CORE-1 rev.3 (200 × 108)
Z_FADER_PCB_BOT = 42.0     # платы фейдеров (слайд-пот 60 мм)
Z_CARRIER = 47.5            # рамка экрана; модуль 50…56.5, стекло в 0.5 от панели
SCREEN_MODULE = dict(w=121.0, h=76.0, t=6.5)   # Waveshare 5" класс (провизор)

# --- крепёж -----------------------------------------------------------------
M3_INSERT, M3_CLEAR = 4.6, 3.3
M25_INSERT, M25_CLEAR = 4.0, 2.8
POST_PANEL_D = 9.0     # стойки панели (M3)
POST_SMALL_D = 7.0     # стойки M2.5 (деки, экран, фейдеры)
CSK_D, CSK_T = 6.6, 1.65

R_OUT = 4.0            # наружный радиус корпуса/панели
R_CAV = R_OUT - WALL   # 1.6

# --- стойки (X, Y) ----------------------------------------------------------
PANEL_POSTS = [(12, 14), (368, 14), (12, 90), (368, 90),
               (166, 86), (214, 86), (168, 204), (212, 204)]
CARRIER_POSTS = [(131, 12), (249, 12), (131, 80), (249, 80)]
DECK_POSTS = [(13, 121), (150, 121), (13, 197), (150, 197),
              (230, 121), (367, 121), (230, 197), (367, 197)]
FADER_POSTS = [(180, 112), (180, 200), (200, 112), (200, 200)]
PANEL1_POSTS = [(30, 20), (350, 20), (30, 90), (350, 90), (160, 20), (220, 20)]
CORE_POSTS = [(100, 86), (280, 86), (100, 174), (280, 174)]

# --- швы --------------------------------------------------------------------
SEAM_X = 190.0                     # скорлупа L/R
S_H = 78.0                         # Y-уровень горизонтального участка S-шва панели
CAP_X0, CAP_X1 = 128.0, 252.0      # «шапка» панели (джеки + экран)
TENONS_Y = [15.0, 60.0, 110.0, 160.0, 195.0]   # шипы скорлупы
DOWELS = [(128, 30), (128, 44), (252, 30), (252, 44),
          (145, 78), (173, 78), (207, 78), (235, 78),
          (190, 96), (190, 202)]   # штифты Ø3.2 панельных швов

# --- задняя стенка (провизор, до CORE-1 rev.3) ------------------------------
REAR = [
    ("USB-C", 60.0, ("rect", 12.0, 7.0)),
    ("DC9V", 100.0, ("circle", 9.0, 0)),
    ("PWR-SW", 130.0, ("rect", 13.0, 10.0)),
    ("MIDI-IN", 232.0, ("circle", 16.2, 0)),
    ("MIDI-OUT", 257.0, ("circle", 16.2, 0)),
    ("BUS1", 302.0, ("rect", 22.0, 9.0)),
    ("BUS2", 330.0, ("rect", 22.0, 9.0)),
    ("RESET", 352.0, ("circle", 4.0, 0)),
]
REAR_Z = 28.0
FEET = [(18, 25), (362, 25), (18, 185), (362, 185)]
VENTS = [(30 + 18 * i, y) for i in range(5) for y in (130, 155, 180)]


def _rr(w, h, t, r):
    """Скруглённый прямоугольник w×h×t, центр в (0,0), R=r."""
    b = cq.Workplane("XY").box(w, h, t)
    return b.edges("|Z").fillet(r)


def solid_of(wp):
    return wp.val()


# ============================================================================
# ПАНЕЛЬ (3 детали, S-шов)
# ============================================================================
R = R_OUT
K = R - R * 0.70710678     # катет между точкой начала дуги и 45° (R·(1−cos45))


def _profile_points(name):
    """Контур детали панели: список точек и дуг R4 на внешних углах.
    Формат: ('M', x, y) старт, ('L', x, y) линия, ('A', x, y, mx, my) дуга."""
    if name == "L":
        return [("M", 4, 0), ("L", CAP_X0, 0), ("L", CAP_X0, S_H),
                ("L", SEAM_X, S_H), ("L", SEAM_X, PH), ("L", 4, PH),
                ("A", 0, PH - 4, K, PH - K), ("L", 0, 4), ("A", 4, 0, K, K)]
    if name == "C":
        return [("M", CAP_X0, 0), ("L", CAP_X1, 0), ("L", CAP_X1, S_H),
                ("L", CAP_X0, S_H)]
    return [("M", CAP_X1, 0), ("L", PW - 4, 0), ("A", PW, 4, PW - K, K),
            ("L", PW, PH - 4), ("A", PW - 4, PH, PW - K, PH - K),
            ("L", SEAM_X, PH), ("L", SEAM_X, S_H), ("L", CAP_X1, S_H)]


def _panel_piece(name):
    wp = None
    for op in _profile_points(name):
        if op[0] == "M":
            wp = cq.Workplane("XY").moveTo(op[1], op[2])
        elif op[0] == "L":
            wp = wp.lineTo(op[1], op[2])
        else:
            wp = wp.threePointArc((op[3], op[4]), (op[1], op[2]))
    return wp.close().extrude(PANEL_T)


def _cut_feature(solid, feat, through=PANEL_T + 2):
    """Вырезать элемент панели: отверстие/окно/паз/цековку."""
    z0, z1 = -1, PANEL_T + 1
    if feat[0] == "hole":                                  # hole, x, y, d
        _, x, y, d = feat
        cut = cq.Workplane("XY").cylinder(z1 - z0, d / 2).translate((x, y, (z0 + z1) / 2))
        solid = solid.cut(cut)
    elif feat[0] == "csk":                                 # csk, x, y (M3)
        _, x, y = feat
        through_h = cq.Workplane("XY").cylinder(PANEL_T + 2, M3_CLEAR / 2) \
            .translate((x, y, PANEL_T / 2))
        # конус цековки: широкая часть у поверхности панели
        head = cq.Workplane(obj=cq.Solid.makeCone(
            CSK_D / 2, M3_CLEAR / 2, CSK_T, cq.Vector(x, y, PANEL_T - CSK_T)))
        solid = solid.cut(through_h).cut(head)
    elif feat[0] == "win":                                 # win, x, y, w, h, r, ang
        _, x, y, w, h, r, ang = feat
        cut = _rr(w, h, PANEL_T + 2, r).rotate((0, 0, 0), (0, 0, 1), ang) \
            .translate((x, y, PANEL_T / 2))
        solid = solid.cut(cut)
    return solid


def build_panel():
    """Три детали панели со всеми вырезами (по spec v1.7)."""
    feats = []
    for j in SPEC["jacks"]:
        feats.append(("hole", j["x"], j["y"], j["hole"]))
    for k in SPEC["knobs"]:
        feats.append(("hole", k["x"], k["y"], 7.2))       # вал EC11 (как в v1.0)
    scr = SPEC["screen"]
    feats.append(("win", scr["x"] + scr["w"] / 2, scr["y"] + scr["h"] / 2,
                  scr["w"], scr["h"], 1.2, 0))
    for f in SPEC["faders"]:
        feats.append(("win", f["x"], (f["y0"] + f["y1"]) / 2, f["slot_w"],
                      f["y1"] - f["y0"], 3.9, 0))
    kb = SPEC["keyboard"]
    for k in kb["keys_42"]:
        feats.append(("win", k["x"], k["y"],
                      kb["keycap"]["w"] + 2 * kb["window_clearance"],
                      kb["keycap"]["h"] + 2 * kb["window_clearance"],
                      1.5, k["angle_deg"]))
    for (x, y) in PANEL_POSTS:
        feats.append(("csk", x, y))
    for (x, y) in DOWELS:
        feats.append(("hole", x, y, 3.2))

    parts = {}
    for name in ("L", "C", "R"):
        solid = _panel_piece(name)
        # каждому элементу — своя деталь по зоне
        pts, _ = _profile_points(name)
        from shapely.geometry import Polygon as SPoly
        zone = SPoly(pts)
        for f in feats:
            xy = (f[1], f[2])
            p = None
            if f[0] in ("hole", "csk"):
                p = SPoly([(xy[0] - 1, xy[1] - 1), (xy[0] + 1, xy[1] - 1),
                           (xy[0] + 1, xy[1] + 1), (xy[0] - 1, xy[1] + 1)])
            else:
                w, h = f[3], f[4]
                p = SPoly([(xy[0] - w / 2 - 1, xy[1] - h / 2 - 1),
                           (xy[0] + w / 2 + 1, xy[1] - h / 2 - 1),
                           (xy[0] + w / 2 + 1, xy[1] + h / 2 + 1),
                           (xy[0] - w / 2 - 1, xy[1] + h / 2 + 1)])
            if zone.intersects(p):
                solid = _cut_feature(solid, f)
        parts[name] = solid
    return parts


# ============================================================================
# НИЖНЯЯ СКОРЛУПА (2 половины)
# ============================================================================
def _post(x, y, z_top, d, insert_d, insert_h=6.0):
    """Стойка от дна (Z=3) до z_top с гнездом термовтулки сверху."""
    h = z_top - Z_FLOOR_T
    p = cq.Workplane("XY").cylinder(h, d / 2).translate((x, y, Z_FLOOR_T + h / 2))
    hole_h = min(insert_h, h - 1.0)
    hole = cq.Workplane("XY").cylinder(hole_h, insert_d / 2) \
        .translate((x, y, z_top - hole_h / 2))
    return p.cut(hole)


def build_shell():
    outer = _rr(PW, PH, Z_WALL_TOP, R_OUT).translate((PW / 2, PH / 2, Z_WALL_TOP / 2))
    cav = _rr(PW - 2 * WALL, PH - 2 * WALL, Z_WALL_TOP, R_CAV) \
        .translate((PW / 2, PH / 2, (Z_WALL_TOP + Z_FLOOR_T) / 2))
    shell = outer.cut(cav)

    # задняя стенка: окна (провизор)
    for name, x, (kind, a, b) in REAR:
        if kind == "circle":
            cut = cq.Workplane("XY").cylinder(WALL + 2, a / 2) \
                .rotate((0, 0, 0), (1, 0, 0), 90) \
                .translate((x, WALL / 2, REAR_Z))
        else:
            cut = cq.Workplane("XZ").box(a, WALL + 2, b).translate((x, WALL / 2, REAR_Z))
        shell = shell.cut(cut)

    # вентиляция дна (пазы 4 × 16)
    for (x, y) in VENTS:
        cut = cq.Workplane("XY").box(4, 16, Z_FLOOR_T + 2) \
            .translate((x, y, Z_FLOOR_T / 2))
        shell = shell.cut(cut)
    # ножки: цековка снаружи Ø8 × 2.5 + проход Ø3.2
    for (x, y) in FEET:
        recess = cq.Workplane("XY").cylinder(2.5, 4.0).translate((x, y, 1.25))
        hole = cq.Workplane("XY").cylinder(Z_FLOOR_T + 2, 1.6) \
            .translate((x, y, Z_FLOOR_T / 2))
        shell = shell.cut(recess).cut(hole)

    # стойки
    for grp, (z_top, d, ins) in (
        (PANEL_POSTS, (Z_WALL_TOP, POST_PANEL_D, M3_INSERT)),
        (CARRIER_POSTS, (Z_CARRIER, POST_SMALL_D, M25_INSERT)),
        (DECK_POSTS, (Z_DECK_PCB_BOT, POST_SMALL_D, M25_INSERT)),
        (FADER_POSTS, (Z_FADER_PCB_BOT, POST_SMALL_D, M25_INSERT)),
        (PANEL1_POSTS, (Z_PANEL1_PCB_BOT, POST_PANEL_D, M3_INSERT)),
        (CORE_POSTS, (Z_CORE_PCB_BOT, POST_PANEL_D, M3_INSERT)),
    ):
        for (x, y) in grp:
            shell = shell.union(_post(x, y, z_top, d, ins))

    # разрез по X = SEAM_X
    half_w = SEAM_X
    left_box = cq.Workplane("XY").box(half_w, PH, Z_WALL_TOP + 4) \
        .translate((half_w / 2, PH / 2, Z_WALL_TOP / 2 - 2))
    right_box = cq.Workplane("XY").box(PW - SEAM_X, PH, Z_WALL_TOP + 4) \
        .translate((SEAM_X + (PW - SEAM_X) / 2, PH / 2, Z_WALL_TOP / 2 - 2))
    sh_l = shell.intersect(left_box)
    sh_r = shell.intersect(right_box)

    # шипы 8×3 на L (выступают за шов), карманы на R
    for y in TENONS_Y:
        tenon = cq.Workplane("XY").box(6.0, 8.0, 3.0).translate((SEAM_X, y, Z_FLOOR_T + 1.5))
        sh_l = sh_l.union(tenon)
        pocket = cq.Workplane("XY").box(3.2, 8.4, 3.2).translate((SEAM_X + 1.5, y, Z_FLOOR_T + 1.5))
        sh_r = sh_r.cut(pocket)
    return sh_l, sh_r


# ============================================================================
# МЕЛКИЕ ДЕТАЛИ
# ============================================================================
def build_carrier():
    w, h, t = 130.0, 80.0, 2.5
    p = _rr(w, h, t, 3.0).translate((PW / 2, 46.0, Z_CARRIER + t / 2))
    for (x, y) in CARRIER_POSTS:
        hole = cq.Workplane("XY").cylinder(t + 2, M25_CLEAR / 2) \
            .translate((x, y, Z_CARRIER + t / 2))
        p = p.cut(hole)
    # отверстия экран-модуля (провизор 121 × 76, шаг 111 × 65)
    for sx in (-1, 1):
        for sy in (-1, 1):
            hole = cq.Workplane("XY").cylinder(t + 2, 1.4) \
                .translate((PW / 2 + sx * 55.5, 46.0 + sy * 32.5, Z_CARRIER + t / 2))
            p = p.cut(hole)
    return p


def build_knob():
    d, h = 14.0, 11.0
    k = cq.Workplane("XY").cylinder(h, d / 2).translate((0, 0, h / 2))
    k = k.faces(">Z").chamfer(1.2)
    hole = cq.Workplane("XY").cylinder(h + 2, 6.1 / 2).translate((0, 0, h / 2))
    flat = cq.Workplane("XY").box(3.0, d + 2, h + 2).translate((3.05 + 1.5, 0, h / 2))
    grub = cq.Workplane("XY").cylinder(6, 2.6 / 2).rotate((0, 0, 0), (0, 1, 0), 90) \
        .translate((-d / 2 - 1.5, 0, 5.0))
    return k.cut(hole).cut(flat).cut(grub)


def build_fader_cap():
    cap = _rr(18.0, 10.0, 9.0, 3.0).translate((0, 0, 4.5))
    groove = cq.Workplane("XY").box(12.0, 2.2, 1.6).translate((0, 0, 9.0))
    pin = cq.Workplane("XY").cylinder(6.0, 1.3).translate((0, 0, 3.0))
    return cap.cut(groove).cut(pin)


# ============================================================================
# ЭКСПОРТ
# ============================================================================
def export(part, name, report):
    s = part.val() if isinstance(part, cq.Workplane) else part
    stl_path = os.path.join(STL, f"bukifon_v1_7_{name}.stl")
    step_path = os.path.join(STEP, f"bukifon_v1_7_{name}.step")
    s.exportStl(stl_path, tolerance=0.05, angularTolerance=0.3)
    s.exportStep(step_path)
    bb = s.BoundingBox()
    ok = bb.xlen <= 220.5 and bb.ylen <= 220.5
    report.append(f"{name:14s} {bb.xlen:7.1f} × {bb.ylen:7.1f} × {bb.zlen:6.1f} мм "
                  f"vol {s.Volume() / 1000:8.1f} см³  {'✔ ≤220' if ok else '✘ БОЛЬШЕ 220'} "
                  f"{'✔ watertight' if s.isValid() else '✘ НЕВАЛИДНА'}")
    return s


def main():
    report = ["Букифон v1.7 — детали корпуса (все размеры мм)",
              "=" * 78]
    parts = {}
    for name, part in build_panel().items():
        parts[f"panel_{name}"] = export(part, f"panel_{name}", report)
    sh_l, sh_r = build_shell()
    parts["shell_L"] = export(sh_l, "shell_L", report)
    parts["shell_R"] = export(sh_r, "shell_R", report)
    parts["screen_carrier"] = export(build_carrier(), "screen_carrier", report)
    parts["knob"] = export(build_knob(), "knob", report)
    parts["fader_cap"] = export(build_fader_cap(), "fader_cap", report)

    # сборка (STEP): панели на Z 57, ручки на 60
    asm = cq.Workplane()
    comp = cq.Compound.makeCompound([
        parts["shell_L"].locate(cq.Location(cq.Vector(0, 0, 0))),
        parts["shell_R"].locate(cq.Location(cq.Vector(0, 0, 0))),
        parts["panel_L"].locate(cq.Location(cq.Vector(0, 0, Z_WALL_TOP))),
        parts["panel_C"].locate(cq.Location(cq.Vector(0, 0, Z_WALL_TOP))),
        parts["panel_R"].locate(cq.Location(cq.Vector(0, 0, Z_WALL_TOP))),
    ])
    comp.exportStep(os.path.join(STEP, "bukifon_v1_7_assembly.step"))

    report.append("=" * 78)
    report.append(f"Сборка: {len(parts)} деталей + assembly.step")
    report.append(f"Z-стек: дно {Z_FLOOR_T}, полость {Z_FLOOR_T}…{Z_WALL_TOP}, "
                  f"панель {Z_WALL_TOP}…{Z_PANEL_TOP}, ножки 3 → всего 63")
    txt = "\n".join(report)
    print(txt)
    with open(os.path.join(ROOT, "mechanical", "fit_check_v17.md"), "w") as f:
        f.write("```text\n" + txt + "\n```\n")


if __name__ == "__main__":
    main()
