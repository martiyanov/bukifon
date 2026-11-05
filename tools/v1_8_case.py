#!/usr/bin/env python3
"""Букифон v1.8 — генератор 3D-корпуса (CadQuery): STL + STEP.

Геометрия панели — строго из spec/panel-spec-v1.8.json (handoff заказчика v0.3).
Система координат: X вправо, Y вниз от задней кромки, Z вверх; верх панели Z=60.

Z-стек (мм): ножки 3 → дно 3 → полость 3…57 → панель 57…60. Всего 63.

Детали (≤ 190×210):
  shell_L/R   — нижняя скорлупа, шов X=190 (6 шипов + клей)
  panel_L/C/R — панель: «шапка» X 131.2…249.1 до Y=98 (джеки+экран),
                ниже Т-образные детали, вертикальный шов X=190 между фейдерами
  screen_carrier, knob ×16, fader_cap ×2

Запуск: /tmp/cqenv/bin/python -I tools/v1_8_case.py
"""
import json
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STL = os.path.join(ROOT, "mechanical", "stl_v18")
STEP = os.path.join(ROOT, "mechanical", "step_v18")
os.makedirs(STL, exist_ok=True)
os.makedirs(STEP, exist_ok=True)

SPEC = json.load(open(os.path.join(ROOT, "spec", "panel-spec-v1.8.json")))
PW, PH, PANEL_T = SPEC["panel"]["w"], SPEC["panel"]["h"], SPEC["panel"]["thickness"]

Z_FLOOR_T = 3.0
WALL = 2.4
Z_WALL_TOP = 57.0
Z_PANEL_TOP = 60.0

CHOC_STACK = 11.3                       # Choc v1 + MBK над PCB
Z_DECK_PCB_BOT = 48.1                   # колпачок +1 мм над панелью
Z_PANEL1_PCB_BOT = 43.4                 # PANEL-1 rev.2 (провизор)
Z_CORE_PCB_BOT = 20.0                   # CORE-1 rev.3 (провизор)
Z_FADER_PCB_BOT = 42.0
Z_CARRIER = 47.5                        # рамка экрана (модуль 50…56.5)

M3_INSERT, M3_CLEAR = 4.6, 3.3
M25_INSERT, M25_CLEAR = 4.0, 2.8
POST_PANEL_D = 9.0
POST_SMALL_D = 7.0
CSK_D, CSK_T = 6.6, 1.65
R_OUT = 4.0

SEAM = SPEC["seam_s"]                   # x1=131.2, x2=249.1, y_h=98
SX1, SX2, SYH = SEAM["x1"], SEAM["x2"], SEAM["y_h"]
SEAM_X = 190.0
TENONS_Y = [15.0, 60.0, 110.0, 160.0, 195.0]

# Стойки панели (M3, цековка сверху) — в монолитных зонах v0.3-раскладки
PANEL_POSTS = [(12, 16), (368, 16), (12, 80), (368, 80),
               (162, 106), (218, 106), (168, 204), (212, 204)]
CARRIER_POSTS = [(131, 27.4), (249, 27.4), (131, 95.4), (249, 95.4)]
DECK_POSTS = [(20, 100), (145, 100), (20, 196), (145, 196),
              (235, 100), (360, 100), (235, 196), (360, 196)]   # провизор до KiCad
FADER_POSTS = [(180, 113), (180, 185), (200, 113), (200, 185)]
PANEL1_POSTS = [(30, 25), (350, 25), (30, 63), (350, 63), (160, 15), (220, 15)]
CORE_POSTS = [(100, 86), (280, 86), (100, 174), (280, 174)]

DOWELS = [(SX1, 24), (SX1, 60), (SX2, 24), (SX2, 60),
          (150, SYH), (175, SYH), (205, SYH), (225, SYH),
          (190, 104), (190, 196)]

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
VENTS = [(28 + 18 * i, y) for i in range(4) for y in (130, 155, 180)]


def _rr(w, h, t, r):
    return cq.Workplane("XY").box(w, h, t).edges("|Z").fillet(r)


# ---------------------------------------------------------------- панель
K4 = R_OUT - R_OUT * 0.70710678


def _profile(name):
    if name == "L":   # Т-образная: сверху 0…SX1, снизу 0…190
        return [("M", 4, 0), ("L", SX1, 0), ("L", SX1, SYH), ("L", SEAM_X, SYH),
                ("L", SEAM_X, PH), ("L", 4, PH),
                ("A", 0, PH - 4, K4, PH - K4), ("L", 0, 4), ("A", 4, 0, K4, K4)]
    if name == "C":   # «шапка»: джеки + экран
        return [("M", SX1, 0), ("L", SX2, 0), ("L", SX2, SYH), ("L", SX1, SYH)]
    return [("M", SX2, 0), ("L", PW - 4, 0), ("A", PW, 4, PW - K4, K4),
            ("L", PW, PH - 4), ("A", PW - 4, PH, PW - K4, PH - K4),
            ("L", SEAM_X, PH), ("L", SEAM_X, SYH), ("L", SX2, SYH)]


def _panel_piece(name):
    wp = None
    for op in _profile(name):
        if op[0] == "M":
            wp = cq.Workplane("XY").moveTo(op[1], op[2])
        elif op[0] == "L":
            wp = wp.lineTo(op[1], op[2])
        else:
            wp = wp.threePointArc((op[3], op[4]), (op[1], op[2]))
    return wp.close().extrude(PANEL_T)


def build_panel():
    feats = []
    for j in SPEC["jacks"]:
        feats.append(("hole", j["x"], j["y"], j["hole"]))
    for k in SPEC["knobs"]:
        feats.append(("hole", k["x"], k["y"], 7.2))
    s = SPEC["screen"]
    feats.append(("win", s["x"] + s["w"] / 2, s["y"] + s["h"] / 2, s["w"], s["h"], 1.2, 0.0))
    for f in SPEC["faders"]:
        feats.append(("win", f["x"], (f["y0"] + f["y1"]) / 2, f["slot_w"],
                      f["y1"] - f["y0"], 1.1, 0.0))
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

    from shapely.geometry import Polygon as SPoly

    def zone_of(name):
        if name == "L":
            return SPoly([(0, 0), (SX1, 0), (SX1, SYH), (SEAM_X, SYH),
                          (SEAM_X, PH), (0, PH)])
        if name == "C":
            return SPoly([(SX1, 0), (SX2, 0), (SX2, SYH), (SX1, SYH)])
        return SPoly([(SX2, 0), (PW, 0), (PW, PH), (SEAM_X, PH),
                      (SEAM_X, SYH), (SX2, SYH)])

    parts = {}
    for name in ("L", "C", "R"):
        solid = _panel_piece(name)
        zone = zone_of(name)
        for f in feats:
            x, y = f[1], f[2]
            w = (f[3] if f[0] == "win" else 8.0)
            h = (f[4] if f[0] == "win" else 8.0)
            p = SPoly([(x - w / 2 - 1, y - h / 2 - 1), (x + w / 2 + 1, y - h / 2 - 1),
                       (x + w / 2 + 1, y + h / 2 + 1), (x - w / 2 - 1, y + h / 2 + 1)])
            if zone.intersects(p):
                solid = _cut(solid, f)
        parts[name] = solid
    return parts


def _cut(solid, f):
    if f[0] == "hole":
        _, x, y, d = f
        return solid.cut(cq.Workplane("XY").cylinder(PANEL_T + 2, d / 2)
                         .translate((x, y, PANEL_T / 2)))
    if f[0] == "csk":
        _, x, y = f
        through = cq.Workplane("XY").cylinder(PANEL_T + 2, M3_CLEAR / 2) \
            .translate((x, y, PANEL_T / 2))
        head = cq.Workplane(obj=cq.Solid.makeCone(
            CSK_D / 2, M3_CLEAR / 2, CSK_T, cq.Vector(x, y, PANEL_T - CSK_T)))
        return solid.cut(through).cut(head)
    _, x, y, w, h, r, ang = f
    cut = _rr(w, h, PANEL_T + 2, r).rotate((0, 0, 0), (0, 0, 1), ang) \
        .translate((x, y, PANEL_T / 2))
    return solid.cut(cut)


# ---------------------------------------------------------------- скорлупа
def _post(x, y, z_top, d, insert_d, insert_h=6.0):
    h = z_top - Z_FLOOR_T
    p = cq.Workplane("XY").cylinder(h, d / 2).translate((x, y, Z_FLOOR_T + h / 2))
    hole_h = min(insert_h, h - 1.0)
    hole = cq.Workplane("XY").cylinder(hole_h, insert_d / 2) \
        .translate((x, y, z_top - hole_h / 2))
    return p.cut(hole)


def build_shell():
    outer = _rr(PW, PH, Z_WALL_TOP, R_OUT).translate((PW / 2, PH / 2, Z_WALL_TOP / 2))
    cav = _rr(PW - 2 * WALL, PH - 2 * WALL, Z_WALL_TOP, R_OUT - WALL) \
        .translate((PW / 2, PH / 2, (Z_WALL_TOP + Z_FLOOR_T) / 2))
    shell = outer.cut(cav)

    for name, x, (kind, a, b) in REAR:
        if kind == "circle":
            cut = cq.Workplane("XY").cylinder(WALL + 2, a / 2) \
                .rotate((0, 0, 0), (1, 0, 0), 90).translate((x, WALL / 2, REAR_Z))
        else:
            cut = cq.Workplane("XZ").box(a, WALL + 2, b).translate((x, WALL / 2, REAR_Z))
        shell = shell.cut(cut)

    for (x, y) in VENTS:
        shell = shell.cut(cq.Workplane("XY").box(4, 16, Z_FLOOR_T + 2)
                          .translate((x, y, Z_FLOOR_T / 2)))
    for (x, y) in FEET:
        shell = shell.cut(cq.Workplane("XY").cylinder(2.5, 4.0)
                          .translate((x, y, 1.25)))
        shell = shell.cut(cq.Workplane("XY").cylinder(Z_FLOOR_T + 2, 1.6)
                          .translate((x, y, Z_FLOOR_T / 2)))

    for grp, z_top, d, ins in (
        (PANEL_POSTS, Z_WALL_TOP, POST_PANEL_D, M3_INSERT),
        (CARRIER_POSTS, Z_CARRIER, POST_SMALL_D, M25_INSERT),
        (DECK_POSTS, Z_DECK_PCB_BOT, POST_SMALL_D, M25_INSERT),
        (FADER_POSTS, Z_FADER_PCB_BOT, POST_SMALL_D, M25_INSERT),
        (PANEL1_POSTS, Z_PANEL1_PCB_BOT, POST_PANEL_D, M3_INSERT),
        (CORE_POSTS, Z_CORE_PCB_BOT, POST_PANEL_D, M3_INSERT),
    ):
        for (x, y) in grp:
            shell = shell.union(_post(x, y, z_top, d, ins))

    left_box = cq.Workplane("XY").box(SEAM_X, PH, Z_WALL_TOP + 4) \
        .translate((SEAM_X / 2, PH / 2, Z_WALL_TOP / 2 - 2))
    right_box = cq.Workplane("XY").box(PW - SEAM_X, PH, Z_WALL_TOP + 4) \
        .translate((SEAM_X + (PW - SEAM_X) / 2, PH / 2, Z_WALL_TOP / 2 - 2))
    sh_l = shell.intersect(left_box)
    sh_r = shell.intersect(right_box)
    for y in TENONS_Y:
        tenon = cq.Workplane("XY").box(6.0, 8.0, 3.0) \
            .translate((SEAM_X, y, Z_FLOOR_T + 1.5))
        sh_l = sh_l.union(tenon)
        pocket = cq.Workplane("XY").box(3.2, 8.4, 3.2) \
            .translate((SEAM_X + 1.5, y, Z_FLOOR_T + 1.5))
        sh_r = sh_r.cut(pocket)
    return sh_l, sh_r


# ---------------------------------------------------------------- мелочь
def build_carrier():
    w, h, t = 130.0, 80.0, 2.5
    p = _rr(w, h, t, 3.0).translate((PW / 2, 61.4, Z_CARRIER + t / 2))
    for (x, y) in CARRIER_POSTS:
        p = p.cut(cq.Workplane("XY").cylinder(t + 2, M25_CLEAR / 2)
                  .translate((x, y, Z_CARRIER + t / 2)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = p.cut(cq.Workplane("XY").cylinder(t + 2, 1.4)
                      .translate((PW / 2 + sx * 55.5, 61.4 + sy * 32.5,
                                  Z_CARRIER + t / 2)))
    return p


def build_knob():
    d, h = 14.0, 11.0
    k = cq.Workplane("XY").cylinder(h, d / 2).translate((0, 0, h / 2))
    k = k.faces(">Z").chamfer(1.2)
    hole = cq.Workplane("XY").cylinder(h + 2, 6.1 / 2).translate((0, 0, h / 2))
    flat = cq.Workplane("XY").box(3.0, d + 2, h + 2).translate((4.55, 0, h / 2))
    grub = cq.Workplane("XY").cylinder(6, 2.6 / 2).rotate((0, 0, 0), (0, 1, 0), 90) \
        .translate((-d / 2 - 1.5, 0, 5.0))
    return k.cut(hole).cut(flat).cut(grub)


def build_fader_cap():
    cap = _rr(18.0, 10.0, 9.0, 3.0).translate((0, 0, 4.5))
    groove = cq.Workplane("XY").box(12.0, 2.2, 1.6).translate((0, 0, 9.0))
    pin = cq.Workplane("XY").cylinder(6.0, 1.3).translate((0, 0, 3.0))
    return cap.cut(groove).cut(pin)


# ---------------------------------------------------------------- экспорт
def export(part, name, report):
    s = part.val() if isinstance(part, cq.Workplane) else part
    s.exportStl(os.path.join(STL, f"bukifon_v1_8_{name}.stl"),
                tolerance=0.05, angularTolerance=0.3)
    s.exportStep(os.path.join(STEP, f"bukifon_v1_8_{name}.step"))
    bb = s.BoundingBox()
    ok = bb.xlen <= 220.5 and bb.ylen <= 220.5
    report.append(f"{name:14s} {bb.xlen:7.1f} × {bb.ylen:7.1f} × {bb.zlen:6.1f} мм "
                  f"vol {s.Volume() / 1000:8.1f} см³  {'✔ ≤220' if ok else '✘ >220'} "
                  f"{'✔ valid' if s.isValid() else '✘ INVALID'}")
    return s


def main():
    report = ["Букифон v1.8 — детали корпуса (геометрия панели: handoff v0.3)",
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

    comp = cq.Compound.makeCompound([
        parts["shell_L"], parts["shell_R"],
        parts["panel_L"].locate(cq.Location(cq.Vector(0, 0, Z_WALL_TOP))),
        parts["panel_C"].locate(cq.Location(cq.Vector(0, 0, Z_WALL_TOP))),
        parts["panel_R"].locate(cq.Location(cq.Vector(0, 0, Z_WALL_TOP))),
    ])
    comp.exportStep(os.path.join(STEP, "bukifon_v1_8_assembly.step"))

    report.append("=" * 78)
    report.append("Стойки: панель 8×M3, экран 4×M2.5, деки 8×M2.5 (провизор),")
    report.append("фейдеры 4×M2.5, PANEL-1 6×M3 (провизор), CORE 4×M3 (провизор)")
    txt = "\n".join(report)
    print(txt)
    with open(os.path.join(ROOT, "mechanical", "fit_check_v18.md"), "w") as f:
        f.write("```text\n" + txt + "\n```\n")


if __name__ == "__main__":
    main()
