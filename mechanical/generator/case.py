"""Bukifon — параметрический генератор корпуса (Python 3.12+, trimesh + manifold3d + shapely).

Вход:  mechanical/generator/params.py  (все размеры, источник — spec/*.md)
Выход: mechanical/stl/*.stl            — детали по spec/30-mechanics.md §3
       mechanical/generator/assembly.json  — трансформы экземпляров для рендера/сборки
       mechanical/fit_check.md        — отчёт о проверке коллизий (см. fitcheck.py)

Запуск:
    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/case.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon, box as sbox
from shapely import affinity
from trimesh.creation import extrude_polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # .../Синтезатор
STL_DIR = os.path.join(ROOT, "mechanical", "stl")
ASSEMBLY_JSON = os.path.join(HERE, "assembly.json")

os.makedirs(STL_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
#  0. Геометрические утилиты
# ---------------------------------------------------------------------------
def V(x=0.0, y=0.0, z=0.0):
    return np.array([x, y, z], dtype=float)


def box(x0, x1, y0, y1, z0, z1):
    """Прямоугольный параллелепипед по двум углам."""
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation(V((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl_z(r, z0, z1, cx=0.0, cy=0.0, sections=P.SMOOTH_SECTIONS):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    m.apply_translation(V(cx, cy, (z0 + z1) / 2))
    return m


def cyl_x(r, x0, x1, cy=0.0, cz=0.0, sections=P.SMALL_SECTIONS):
    m = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=sections)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    m.apply_translation(V((x0 + x1) / 2, cy, cz))
    return m


def cyl_y(r, y0, y1, cx=0.0, cz=0.0, sections=P.SMALL_SECTIONS):
    m = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=sections)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation(V(cx, (y0 + y1) / 2, cz))
    return m


def cone_frustum(r_top, r_bot, z0, z1, cx=0.0, cy=0.0, sections=P.SMOOTH_SECTIONS):
    """Усечённый конус (для фасок 45° и стоек)."""
    m = trimesh.creation.cone(radius=max(r_bot, r_top), height=z1 - z0,
                              sections=sections)
    # trimesh.cone: основание r на z=-h/2, вершина на z=+h/2. Масштабируем по Z,
    # чтобы получить усечённый конус: проще построить цилиндр и не мучиться.
    m = trimesh.creation.cylinder(radius=1.0, height=z1 - z0, sections=sections)
    verts = m.vertices.copy()
    h = z1 - z0
    t = (verts[:, 2] + h / 2) / h          # 0..1 снизу вверх
    r = r_bot + (r_top - r_bot) * t
    verts[:, 0] *= r
    verts[:, 1] *= r
    m.vertices = verts
    m.apply_translation(V(cx, cy, (z0 + z1) / 2))
    return m


def ext(poly: Polygon, z0, z1):
    """Экструзия shapely-полигона от z0 до z1 (watertight)."""
    m = extrude_polygon(poly, height=z1 - z0)
    m.apply_translation(V(0, 0, z0))
    return m


def U(meshes):
    meshes = [m for m in meshes if m is not None]
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold")


def DIFF(a, cutters):
    cutters = [m for m in cutters if m is not None]
    if not cutters:
        return a
    return trimesh.boolean.difference([a] + cutters, engine="manifold")


def INTER(a, b):
    return trimesh.boolean.intersection([a, b], engine="manifold")


def mirror_x(mesh, width=P.BODY_W):
    """Зеркалирование по X относительно центра width/2."""
    v = mesh.vertices.copy()
    v[:, 0] = width - v[:, 0]
    faces = mesh.faces[:, ::-1]
    m = trimesh.Trimesh(vertices=v, faces=faces, process=False)
    return m


# ---------------------------------------------------------------------------
#  1. 2D-профили (shapely)
# ---------------------------------------------------------------------------
def rrect(x0, x1, y0, y1, r):
    """Скруглённый прямоугольник как shapely-полигон."""
    r = max(0.01, min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
    core = sbox(x0 + r, y0 + r, x1 - r, y1 - r)
    return core.buffer(r, quad_segs=16, join_style=1).simplify(0)


def circle(cx, cy, r, n=48):
    return Point(cx, cy).buffer(r, quad_segs=16)


def rounded_rect_window(cx, cy, w, h, r):
    return rrect(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, r)


def keycap_hole_square(cx, cy, s, r):
    return rrect(cx - s / 2, cx + s / 2, cy - s / 2, cy + s / 2, r)


# ---------------------------------------------------------------------------
#  2. Экспорт
# ---------------------------------------------------------------------------
PARTS = {}          # имя -> Trimesh (mesh уже в глобальных координатах сборки)


def _has_scipy():
    try:
        import scipy  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def add_part(name, mesh, print_note=None):
    # NB: merge_vertices() не вызываем — на CSG-результатах он «склеивает»
    # вершины в местах касания оболочек и ломает watertight-свойство.
    PARTS[name] = mesh
    return mesh


def export_all():
    meta = {}
    for name, mesh in PARTS.items():
        fn = os.path.join(STL_DIR, name + ".stl")
        mesh.export(fn)
        reloaded = trimesh.load(fn)
        rt_ok = bool(reloaded.is_watertight)
        b = mesh.bounds
        meta[name] = {
            "file": os.path.basename(fn),
            "bbox": [round(float(x), 3) for x in (b[1] - b[0])],
            "min": [round(float(x), 3) for x in b[0]],
            "max": [round(float(x), 3) for x in b[1]],
            "watertight": bool(mesh.is_watertight),
            "watertight_reload": rt_ok,
            "volume_mm3": round(float(mesh.volume), 1),
            "shells": int(len(mesh.split(only_watertight=False))) if _has_scipy() else -1,
            "triangles": int(len(mesh.faces)),
        }
        print(f"  STL  {name:22s} {str(meta[name]['bbox']):32s} "
              f"watertight={meta[name]['watertight']}/reload={rt_ok} "
              f"vol={meta[name]['volume_mm3']} mm3")
    return meta


# ---------------------------------------------------------------------------
#  3. Нижняя скорлупа (bottom_L / bottom_R) — spec/30 §1, §2, §4
# ---------------------------------------------------------------------------
def build_bottom_full():
    print("[1/15] нижняя скорлупа …")
    # ---- внешний контур: корпус + рукоятки + «брюхо» -----------------------
    hull = ext(rrect(0, P.BODY_W, 0, P.BODY_D, P.R_OUT),
               P.Z_FLOOR_BOT, P.Z_TOP)

    # левая рукоятка: подушка ладони R22 на внешних углах
    grip = rrect(P.GRIP_X0, P.GRIP_X1, P.GRIP_Y0, P.GRIP_Y1, P.GRIP_R)
    grip = grip.difference(
        sbox(-5, P.GRIP_PALM_R, P.GRIP_Y0 - 1, P.GRIP_Y0 + P.GRIP_PALM_R)
        .difference(circle(P.GRIP_PALM_R, P.GRIP_Y0 + P.GRIP_PALM_R, P.GRIP_PALM_R)))
    grip = grip.difference(
        sbox(-5, P.GRIP_PALM_R, P.GRIP_Y1 - P.GRIP_PALM_R, P.GRIP_Y1 + 1)
        .difference(circle(P.GRIP_PALM_R, P.GRIP_Y1 - P.GRIP_PALM_R, P.GRIP_PALM_R)))
    pod_L = ext(grip, P.GRIP_Z0, P.Z_FLOOR_BOT + 0.2)
    pod_R = mirror_x(pod_L)

    # «брюхо» (bay) 0…8
    bay = ext(rrect((P.BODY_W - P.BAY_EXT_W) / 2, (P.BODY_W + P.BAY_EXT_W) / 2,
                    (P.BODY_D - P.BAY_EXT_D) / 2, (P.BODY_D + P.BAY_EXT_D) / 2,
                    P.R_OUT), 0.0, P.Z_FLOOR_BOT + 0.2)

    solid = U([hull, pod_L, pod_R, bay])

    # ---- полость 11.4…40.6 --------------------------------------------------
    cav = ext(rrect(P.WALL, P.BODY_W - P.WALL, P.WALL, P.BODY_D - P.WALL, P.R_CAV),
              P.Z_FLOOR_TOP, P.Z_CAV_TOP)
    solid = DIFF(solid, [cav])

    # ---- «брюхо»: полость 200×60 и фальц под крышку -------------------------
    bx0 = (P.BODY_W - P.BAY_CAV_W) / 2
    bx1 = (P.BODY_W + P.BAY_CAV_W) / 2
    by0 = (P.BODY_D - P.BAY_CAV_D) / 2
    by1 = (P.BODY_D + P.BAY_CAV_D) / 2
    bay_cav = ext(rrect(bx0, bx1, by0, by1, 4.0), P.BAY_CAV_Z0, P.Z_FLOOR_TOP)
    hatch_reb = ext(rrect((P.BODY_W - P.BAY_REBATE_W) / 2, (P.BODY_W + P.BAY_REBATE_W) / 2,
                          (P.BODY_D - P.BAY_REBATE_D) / 2, (P.BODY_D + P.BAY_REBATE_D) / 2,
                          P.R_OUT), 0.0, P.BAY_REBATE_Z)
    solid = DIFF(solid, [bay_cav, hatch_reb])

    # ---- верхняя стенка: ниша сменного deck 300 × 79 (spec/10 §3) ----------
    niche = ext(rrect(P.DECK_NICHE_X0, P.DECK_NICHE_X1,
                      P.DECK_NICHE_Y0, P.DECK_NICHE_Y1, 3.0),
                P.Z_CAV_TOP, P.Z_TOP + 0.2)
    solid = DIFF(solid, [niche])

    # ---- окно экрана (модуль 85×50 проходит сквозь верхнюю стенку) --------
    scr = rounded_rect_window(P.SCREEN_X, P.SCREEN_Y,
                              P.SCREEN_MODULE_W + 1.0, P.SCREEN_MODULE_H + 1.0, 2.0)
    solid = DIFF(solid, [ext(scr, P.Z_CAV_TOP, P.Z_TOP + 0.2)])

    # ---- окно верхнего дока (36 × 10, R2) ----------------------------------
    dock = rounded_rect_window(P.UPPER_DOCK_X, P.UPPER_DOCK_Y,
                               P.UPPER_DOCK_WIN_W, P.UPPER_DOCK_WIN_H,
                               P.UPPER_DOCK_WIN_R)
    solid = DIFF(solid, [ext(dock, P.Z_CAV_TOP, P.Z_TOP + 0.2)])

    # ---- проходы энкодеров Ø7.6 и плечевых Ø8.6 в верхней стенке ----------
    for (_n, x, y) in P.ENCODERS:
        solid = DIFF(solid, [cyl_z(P.ENC_BODY_CLEAR / 2, P.Z_CAV_TOP, P.Z_TOP + 0.2,
                                   x, y, 32)])
    for (_n, x, y) in P.SHOULDERS:
        solid = DIFF(solid, [cyl_z(P.SHOULDER_CLEAR / 2, P.Z_CAV_TOP, P.Z_TOP + 0.2,
                                   x, y, 32)])

    # ---- внутренние стойки (добавляются после вырезания полости) -----------
    posts = []
    # CORE-1: 4 × M3, Z 16 (стойки 4.6 от пола)
    for (x, y) in P.CORE_POSTS:
        posts.append(cyl_z(3.5, P.Z_FLOOR_TOP, P.CORE_Z, x, y))
    # PANEL-1: 6 × M3 на Z 37 (стойки 5.4 от «полки» — верхней стенки)
    for (x, y) in P.PANEL1_POSTS:
        posts.append(cyl_z(3.5, P.Z_FLOOR_TOP, 34.0, x, y))
        posts.append(cyl_z(4.5, 34.0, P.PANEL1_Z0, x, y))
    # Верхние панельные пластины: 4 × M3, сквозь PANEL-1 до Z 43 (втулка 6 мм)
    for (x, y) in P.UPPER_PLATE_POSTS:
        posts.append(cyl_z(3.0, P.Z_FLOOR_TOP, P.Z_TOP, x, y))   # Ø6 под отв. Ø6.2
    # DECK: 4 × M3, фланец-полка на 37, шейка до 43.5 сквозь DECK PCB
    for (x, y) in P.DECK_POSTS:
        posts.append(cyl_z(P.DECK_POST_FLANGE_D / 2, P.Z_FLOOR_TOP, 34.0, x, y))
        posts.append(cyl_z(P.DECK_POST_FLANGE_D / 2, 34.0, P.DECK_POST_FLANGE_Z1, x, y))
        posts.append(cyl_z(P.DECK_POST_NECK_D / 2, P.DECK_POST_FLANGE_Z1,
                           P.DECK_PLATE_Z0, x, y))
    # Стойки слайдеров: 4 × M2.5 на Z 30 (под корпусом слайдера, под DECK PCB)
    for (x, y) in P.SLIDER_POSTS:
        posts.append(cyl_z(3.0, P.Z_FLOOR_TOP, P.SLIDER_POST_Z1, x, y))
    # Бобышки крышки брюха: 4 × M3 (pillars 2…11.4)
    for (x, y) in P.HATCH_HOLES:
        posts.append(cyl_z(3.5, 2.0, P.Z_FLOOR_TOP, x, y))
    solid = U([solid] + posts)

    # ---- отверстия стоек: втулки M3 / M2.5 ---------------------------------
    holes = []
    for (x, y) in P.CORE_POSTS:            # CORE-1: отверстие M3 сверху (16→11.7)
        holes.append(cyl_z(P.M3_CLEAR_D / 2, 11.7, P.CORE_Z + 0.2, x, y, 24))
    for (x, y) in P.PANEL1_POSTS:          # PANEL-1: втулка 4.6 × 6 сверху (37→31)
        holes.append(cyl_z(P.M3_INSERT_D / 2, 31.0, P.PANEL1_Z0, x, y, 24))
    for (x, y) in P.UPPER_PLATE_POSTS:     # верхние пластины: втулка 4.6 × 6 (43→37)
        holes.append(cyl_z(P.M3_INSERT_D / 2, 37.0, P.Z_TOP, x, y, 24))
    for (x, y) in P.DECK_POSTS:            # DECK: втулка 4.6 × 6 сверху (43.5→37.5)
        holes.append(cyl_z(P.M3_INSERT_D / 2, P.DECK_PLATE_Z0 - 6.0, P.DECK_PLATE_Z0,
                           x, y, 24))
        holes.append(cyl_z(P.DECK_PCB_CLEAR_D / 2, P.DECK_POST_FLANGE_Z1,
                           P.DECK_PLATE_Z0, x, y, 24))
    for (x, y) in P.SLIDER_POSTS:          # M2.5
        holes.append(cyl_z(P.SLIDER_M25_HOLE / 2, P.SLIDER_POST_Z1 - 5.5,
                           P.SLIDER_POST_Z1, x, y, 24))
    for (x, y) in P.HATCH_HOLES:           # M3 сверху вниз в бобышки брюха
        holes.append(cyl_z(P.HATCH_SCREW_D / 2, 2.0, 8.0, x, y, 24))
    solid = DIFF(solid, holes)

    # ---- ушки под ремень Ø3 (2 шт., в задней части рукояток) --------------
    for xc in (30.0, P.BODY_W - 30.0):
        lug = box(xc - 5, xc + 5, 18.0, P.GRIP_Y0 + 0.2, 2.0, 7.0)
        solid = U([solid, lug])
    for xc in (30.0, P.BODY_W - 30.0):
        solid = DIFF(solid, [cyl_y(1.6, 16.0, 26.0, xc, 4.5, 24)])

    # ---- задняя стенка: окно проводки + 6 бобышек под rear_plate -----------
    wx0, wx1, wz0, wz1 = P.REAR_WIRE_OPENING
    solid = DIFF(solid, [box(wx0, wx1, -1.0, 2.6, wz0, wz1)])
    rear_bosses = []
    for (x, z) in P.REAR_SCREWS:
        rear_bosses.append(cyl_y(3.5, P.WALL, 8.0, x, z, 24))
    solid = U([solid, *rear_bosses])
    rear_holes = []
    for (x, z) in P.REAR_SCREWS:
        rear_holes.append(cyl_y(P.M3_INSERT_D / 2, P.WALL, 8.0, x, z, 24))
        rear_holes.append(cyl_y(P.REAR_SCREW_D / 2, -1.0, P.WALL, x, z, 24))
    solid = DIFF(solid, rear_holes)

    # ---- бобышки шва: 4 × M3 × 12 (горизонтальные, доступ из брюха) -------
    # L-бобышка 144…157.5, R-бобышка 157.5…171; отверстие по X.
    seam_bosses = []
    for y in P.SEAM_SCREW_Y:
        seam_bosses.append(box(144.0, 157.5, y - 5, y + 5, 2.0, P.Z_FLOOR_TOP))
        seam_bosses.append(box(157.5, 171.0, y - 5, y + 5, 2.0, P.Z_FLOOR_TOP))
    solid = U([solid] + seam_bosses)
    seam_holes = []
    for y in P.SEAM_SCREW_Y:
        seam_holes.append(cyl_x(P.SEAM_SCREW_D / 2, 143.0, 171.0, y, 6.5, 20))
        seam_holes.append(cyl_x(3.05, 143.0, 152.0, y, 6.5, 20))   # цековка головки
    solid = DIFF(solid, seam_holes)

    # ---- шпоночные пазы под 2 шипа 6 × 3 (шипы — отдельная деталь, см. seam_key) --
    seam_pockets = []
    for y in P.SEAM_TENONS_Y:
        seam_pockets.append(box(P.SEAM_X - 3.0, P.SEAM_X + 3.0,
                                y - 1.5 - 0.25, y + 1.5 + 0.25,
                                P.Z_CAV_TOP + 0.1, P.Z_TOP + 0.05))
    solid = DIFF(solid, seam_pockets)

    print("      ... разрез по X = %.1f" % P.SEAM_X)
    half_L = INTER(solid, box(-10, P.SEAM_X, -20, P.BODY_D + 20, -20, 80))
    half_R = INTER(solid, box(P.SEAM_X, P.BODY_W + 10, -20, P.BODY_D + 20, -20, 80))
    return half_L, half_R


def build_seam_key():
    """2 шипа 6 × 3 × 2.2 по шву (spec/30 §4) — отдельные печатные шпонки."""
    key = box(-3.0, 3.0, -1.5, 1.5, 0.0, 2.2)
    key = DIFF(key, [box(-4, 4, -3, 3, 2.0, 3.0)])   # фаска 2 × 45° сверху
    return key


# ---------------------------------------------------------------------------
#  4. Панельные пластины panel_upper_L/R  (spec/30 §3 №3-4, spec/10 §2)
# ---------------------------------------------------------------------------
def build_panel_upper():
    print("[2/15] панельные пластины panel_upper …")
    z0, z1 = P.PANEL_UPPER_Z0, P.PANEL_UPPER_Z1
    full = rrect(0, P.BODY_W, P.PANEL_UPPER_Y0, P.PANEL_UPPER_Y1, P.R_OUT)

    win = []
    win.append(rounded_rect_window(P.SCREEN_X, P.SCREEN_Y, P.SCREEN_WIN_W,
                                   P.SCREEN_WIN_H, P.SCREEN_WIN_R))
    win.append(rounded_rect_window(P.UPPER_DOCK_X, P.UPPER_DOCK_Y,
                                   P.UPPER_DOCK_WIN_W, P.UPPER_DOCK_WIN_H,
                                   P.UPPER_DOCK_WIN_R))
    for (_n, x, y) in P.ENCODERS:
        win.append(circle(x, y, P.ENC_HOLE / 2))
    for (_n, x, y) in P.SHOULDERS:
        win.append(circle(x, y, P.SHOULDER_HOLE / 2))
    for (x, y) in P.UPPER_PLATE_POSTS:
        win.append(circle(x, y, P.PLATE_SCREW_D / 2))
    for w in win:
        full = full.difference(w)
    plate = ext(full, z0, z1)

    # 4 × M2.5 экрана: резьба непосредственно в 3-мм пластине (глухие 2.6 мм),
    # отдельные бобышки не ставим, чтобы габарит пластины остался 157.5 × 66 × 3.
    cut = []
    for (x, y) in P.SCREEN_POSTS:
        cut.append(cyl_z(P.M2_INSERT_D / 2, z0 - 0.1, z0 + 2.6, x, y, 20))
    plate = DIFF(plate, cut)

    # цековка винтов M3 (8 × по spec/30 §4)
    cs = []
    for (x, y) in P.UPPER_PLATE_POSTS:
        cs.append(cone_frustum(3.3, 1.65, z1 - P.PLATE_COUNTERSINK_T, z1, x, y, 24))
    plate = DIFF(plate, cs)

    L = INTER(plate, box(-5, P.SEAM_X, -5, P.BODY_D + 5, -5, 60))
    R = INTER(plate, box(P.SEAM_X, P.BODY_W + 5, -5, P.BODY_D + 5, -5, 60))
    return L, R


# ---------------------------------------------------------------------------
#  5. Пластины deck_plate (PAD / KEYS)  (spec/30 §3 №5-6, spec/10 §3)
# ---------------------------------------------------------------------------
def _deck_poly(variant):
    """Левая пластина deck 148 × 78: окна PAD (18 шт.) или KEYS (21 шт.) + слайдер."""
    x0, x1 = P.DECK_PLATE_L_X0, P.DECK_PLATE_L_X1
    y0, y1 = P.DECK_PLATE_Y0, P.DECK_PLATE_Y1
    poly = rrect(x0, x1, y0, y1, 6.0)
    # по шву X = 157.5 край прямой (скругления только у внешних углов)
    poly = poly.union(sbox(x1 - 7.0, y0, x1, y1))
    holes = []
    if variant == "pads":
        for x in (22.0, 48.0, 74.0):
            for y in P.PAD_Y:
                holes.append(rounded_rect_window(x, y, P.PAD_WIN, P.PAD_WIN, P.PAD_WIN_R))
    elif variant == "keys":
        for x in P.KEY_X_L:
            for y in P.KEY_Y:
                holes.append(rounded_rect_window(
                    x, y, P.KEY_WIN, P.KEY_WIN, P.KEY_WIN_R))
        for x in P.KEY_THUMB_X_L:
            holes.append(rounded_rect_window(x, P.KEY_THUMB_Y, P.KEY_WIN,
                                             P.KEY_WIN, P.KEY_WIN_R))
    else:
        raise ValueError(variant)
    # прорезь слайдера SL1
    holes.append(rounded_rect_window(137.0, (P.SLIDER_SLOT_Y0 + P.SLIDER_SLOT_Y1) / 2,
                                     P.SLIDER_SLOT_W, P.SLIDER_SLOT_L,
                                     P.SLIDER_SLOT_R))
    # 2 × M3 крепления к стойкам DECK (вне окон обоих вариантов)
    for (x, y) in [(88.0, 138.0), (125.0, 138.0)]:
        holes.append(circle(x, y, P.PLATE_SCREW_D / 2))
    for h in holes:
        poly = poly.difference(h)
    return poly


def build_deck_plates():
    print("[3/15] пластины deck_plate (PAD и KEYS) …")
    z0, z1 = P.DECK_PLATE_Z0, P.DECK_PLATE_Z1
    out = {}
    for variant in ("pads", "keys"):
        poly_L = _deck_poly(variant)
        # зеркальная правая пластина
        poly_R = affinity.scale(poly_L, xfact=-1, yfact=1, origin=(0, 0))
        poly_R = affinity.translate(poly_R, xoff=P.BODY_W)
        for side, poly in (("L", poly_L), ("R", poly_R)):
            m = ext(poly, z0, z1)
            # цековки M3
            cs = []
            holes = [(88.0, 138.0), (125.0, 138.0)] if side == "L" else \
                    [(P.BODY_W - 88.0, 138.0), (P.BODY_W - 125.0, 138.0)]
            for (x, y) in holes:
                cs.append(cone_frustum(3.3, 1.65, z1 - P.PLATE_COUNTERSINK_T, z1,
                                       x, y, 24))
            m = DIFF(m, cs)
            out[f"deck_plate_{side}_{variant}"] = m
    return out


# ---------------------------------------------------------------------------
#  6. Ручка knob Ø18 × 15  (spec/30 §3 №7, spec/10 §2.2)
# ---------------------------------------------------------------------------
def build_knob():
    print("[4/15] ручка knob …")
    D, H = P.KNOB_D, P.KNOB_H
    r = D / 2
    m = cyl_z(r, 0.0, H, 0, 0)
    # нижняя фаска
    m = DIFF(m, [cone_frustum(r + 0.1, r - 1.2, -0.1, 1.2, 0, 0)])
    # накат: 20 вертикальных канавок
    flutes = []
    for i in range(P.KNURL_FLUTES):
        a = 2 * math.pi * i / P.KNURL_FLUTES
        cx, cy = 8.55 * math.cos(a), 8.55 * math.sin(a)
        flutes.append(cyl_z(1.25, 2.0, H - 0.8, cx, cy, 20))
    m = DIFF(m, flutes)
    # указатель: паз 1.4 × 6.5 глубиной 0.8 от центра вверх
    pointer = rounded_rect_window(0.0, 5.0, 1.5, 6.6, 0.5)
    m = DIFF(m, [ext(pointer, H - 0.9, H + 0.1)])
    # окно световода: снизу Ø10 × 2.5
    m = DIFF(m, [cyl_z(5.0, -0.1, 2.5, 0, 0, 40)])
    # отверстие D-вала 6 мм (плоский срез 2.55 от центра), глубина 13
    shaft = INTER(cyl_z(3.1, -0.1, 13.0, 0, 0, 40), box(-6, 2.55, -6, 6, -1, 20))
    m = DIFF(m, [shaft])
    return m


# ---------------------------------------------------------------------------
#  7. Колпачок пэда pad_cap 20 × 20 × 9  (spec/30 §3 №8)
# ---------------------------------------------------------------------------
def build_pad_cap():
    print("[5/15] колпачок pad_cap …")
    w, d, h = P.PAD_CAP_W, P.PAD_CAP_D, P.PAD_CAP_H
    base = rrect(-w / 2, w / 2, -d / 2, d / 2, 2.0)
    m = ext(base, 0.0, h - 1.1)
    m = U([m, ext(rrect(-w / 2 + 0.7, w / 2 - 0.7, -d / 2 + 0.7, d / 2 - 0.7, 1.8),
                  h - 1.1, h - 0.45)])
    m = U([m, ext(rrect(-w / 2 + 1.5, w / 2 - 1.5, -d / 2 + 1.5, d / 2 - 1.5, 1.6),
                  h - 0.45, h)])
    # вогнутая площадка: сфера R40, глубина 0.8
    sph = trimesh.creation.icosphere(subdivisions=4, radius=40.0)
    sph.apply_translation(V(0, 0, h + 40.0 - 0.8))
    m = DIFF(m, [sph])
    # юбка: выборка снизу 16 × 16, центральный толкатель Ø6
    cav = rrect(-8, 8, -8, 8, 2.0).difference(circle(0, 0, 3.2))
    m = DIFF(m, [ext(cav, -0.1, 6.0)])
    return m


# ---------------------------------------------------------------------------
#  8. Колпачок клавиши keycap 17.5 × 16.5 × 8 (MBK-подобный)  (spec/30 §3 №9)
# ---------------------------------------------------------------------------
def build_keycap():
    print("[6/15] клавиша keycap …")
    w, d, h = P.KEYCAP_W, P.KEYCAP_D, P.KEYCAP_H
    m = ext(rrect(-6.0, 6.0, -5.6, 5.6, 1.6), 0.0, 2.0)          # низ (уже)
    m = U([m, ext(rrect(-7.3, 7.3, -6.8, 6.8, 1.8), 0.0, 4.0)])  # середина
    m = U([m, ext(rrect(-8.75, 8.75, -8.25, 8.25, 2.0), 0.0, h - 1.0)])
    m = U([m, ext(rrect(-8.75 + 1.2, 8.75 - 1.2, -8.25 + 1.2, 8.25 - 1.2, 1.8),
                  h - 1.2, h)])
    # вогнутая площадка 0.6
    sph = trimesh.creation.icosphere(subdivisions=4, radius=30.0)
    sph.apply_translation(V(0, 0, h + 30.0 - 0.6))
    m = DIFF(m, [sph])
    # полость снизу + крест Choc
    cav = rrect(-6.5, 6.5, -6.1, 6.1, 1.8)
    m = DIFF(m, [ext(cav, -0.1, 4.6)])
    stem = U([box(-1.8, 1.8, -0.6, 0.6, 0.0, 4.6),
              box(-0.6, 0.6, -2.3, 2.3, 0.0, 4.6)])
    m = U([m, stem])
    # окно световода: сквозь верх, 2.4 × 4.2, у задней кромки
    win = rounded_rect_window(0.0, -5.6, 2.4, 4.2, 0.8)
    m = DIFF(m, [ext(win, 5.4, h + 0.2)])
    return m


# ---------------------------------------------------------------------------
#  9. Колпачок слайдера fader_cap 16 × 9 × 8  (spec/30 §3 №10)
# ---------------------------------------------------------------------------
def build_fader_cap():
    print("[7/15] колпачок fader_cap …")
    w, d, h = P.SLIDER_CAP_W, P.SLIDER_CAP_D, P.SLIDER_CAP_H
    body_h = P.SLIDER_CAP_TOP - P.PANEL_TOP  # 2.5 — видимая часть над панелью
    stem_h = h - body_h                       # 5.5 — ход в прорезь
    stem = box(-1.9, 1.9, -1.6, 1.6, 0.0, stem_h)
    body = ext(rrect(-w / 2, w / 2, -d / 2, d / 2, 2.2), stem_h, h)
    m = U([stem, body])
    # рифление: 3 канавки на каждой длинной стороне
    ribs = []
    for i in (-1, 0, 1):
        for sy in (-1, 1):
            ribs.append(cyl_x(0.9, -w / 2 - 1, w / 2 + 1, sy * (d / 2 + 0.55),
                              stem_h + body_h / 2, 16))
    m = DIFF(m, ribs)
    # вогнутая площадка сверху
    sph = trimesh.creation.icosphere(subdivisions=3, radius=18.0)
    sph.apply_translation(V(0, 0, h + 18.0 - 0.5))
    m = DIFF(m, [sph])
    return m


# ---------------------------------------------------------------------------
# 10. Плечевая кнопка shoulder_cap Ø10 × 4  (spec/30 §3 №11)
# ---------------------------------------------------------------------------
def build_shoulder_cap():
    print("[8/15] плечевая кнопка shoulder_cap …")
    D, H = P.SHOULDER_CAP_D, P.SHOULDER_CAP_H
    m = cyl_z(D / 2, 0.0, H, 0, 0)
    m = DIFF(m, [cone_frustum(D / 2 + 0.1, D / 2 - 0.8, H - 0.8, H + 0.1, 0, 0)])
    # накат 16 флейт
    fl = []
    for i in range(16):
        a = 2 * math.pi * i / 16
        fl.append(cyl_z(0.85, 0.4, H - 0.5, 4.35 * math.cos(a), 4.35 * math.sin(a), 16))
    m = DIFF(m, fl)
    # вогнутая площадка, полость снизу Ø6.4 × 2
    sph = trimesh.creation.icosphere(subdivisions=3, radius=12.0)
    sph.apply_translation(V(0, 0, H + 12.0 - 0.5))
    m = DIFF(m, [sph, cyl_z(3.2, -0.1, 2.0, 0, 0, 24)])
    return m


# ---------------------------------------------------------------------------
# 11. Световод light_guide Ø4 × 6  (spec/30 §3 №12)
# ---------------------------------------------------------------------------
def build_light_guide():
    print("[9/15] световод light_guide …")
    m = cyl_z(2.0, 0.5, 5.0, 0, 0, 32)
    m = U([m, cone_frustum(1.6, 2.0, 5.0, 6.0, 0, 0, 32)])   # купол
    m = U([m, cone_frustum(2.0, 1.85, 0.0, 0.5, 0, 0, 32)])  # фаска снизу
    return m


# ---------------------------------------------------------------------------
# 12. Верхний док dock_cradle 110 × 40 × 20  (spec/30 §3 №13)
# ---------------------------------------------------------------------------
def build_dock_cradle():
    """L-скоба верхнего дока (spec/30 §3 №13), крепится к задней стенке.

    Стоит ЗА корпусом (Y < 0), не накрывает игровое поле и экран:
      • полка 110 × 40 × 3 на Z 43…46 (модуль ставится на неё),
      • задняя стенка 110 × 3 × 20 на Z 46…66,
      • 2 боковины 6 × 40 × 20,
      • 2 крепёжных лапки 10 × 5 × 3 поверх задней кромки панели (2 × M3).
    Номинал spec — 110 × 40 × 20; фактические габариты 110 × 45 × 23 из-за
    лапок крепления (см. README «Отклонения»).
    """
    W, D, H = P.DOCK_CRADLE_W, P.DOCK_CRADLE_D, P.DOCK_CRADLE_H
    cx = P.UPPER_DOCK_X
    x0, x1 = cx - W / 2, cx + W / 2          # 102.5 … 212.5
    y_front, y_back = -2.0, -42.0            # за задней панелью (Y −42…−2)
    z_shelf0, z_shelf1 = 43.0, 46.0
    z_top = z_shelf1 + H                     # 66
    m = box(x0, x1, y_back, y_front, z_shelf0, z_shelf1)          # полка
    m = U([m, box(x0, x1, y_back, y_back + 3.0, z_shelf1, z_top)])  # задняя стенка
    m = U([m, box(x0, x0 + 6.0, y_back, y_front, z_shelf1, z_top)])  # боковина L
    m = U([m, box(x1 - 6.0, x1, y_back, y_front, z_shelf1, z_top)])  # боковина R
    # крепёжные лапки поверх задней кромки панели (Y −2…3), 2 × M3
    for xc in (cx - 27.0, cx + 27.0):
        m = U([m, box(xc - 5.0, xc + 5.0, -2.0, 3.0, z_shelf1, z_shelf1 + 3.0)])
    laps = []
    for xc in (cx - 27.0, cx + 27.0):
        laps.append(cyl_z(P.PLATE_SCREW_D / 2, z_shelf1 - 0.1, z_shelf1 + 3.1, xc, 0.5, 20))
    m = DIFF(m, laps)
    # фаска 45° по верхним кромкам боковин/стенки (печать без поддержек)
    m = DIFF(m, [box(x0 - 1, x1 + 1, y_back - 1, y_front + 1, z_top - 0.001, z_top + 1)])
    return m


# ---------------------------------------------------------------------------
# 13. Крышка брюха bay_hatch 210 × 70 × 2  (spec/30 §1/§3 №14)
# ---------------------------------------------------------------------------
def build_bay_hatch():
    print("[11/15] крышка брюха bay_hatch …")
    W, D, T = P.HATCH_W, P.HATCH_D, P.HATCH_T
    poly = rrect(-W / 2, W / 2, -D / 2, D / 2, P.R_OUT)
    win = rounded_rect_window(0.0, 0.0, P.UPPER_DOCK_WIN_W, P.UPPER_DOCK_WIN_H, 2.0)
    poly = poly.difference(win)
    for (x, y) in [(-95, -25), (95, -25), (-95, 25), (95, 25)]:
        poly = poly.difference(circle(x, y, P.HATCH_SCREW_D / 2))
    m = ext(poly, 0.0, T)
    cs = []
    for (x, y) in [(-95, -25), (95, -25), (-95, 25), (95, 25)]:
        cs.append(cone_frustum(3.3, 1.65, T - P.PLATE_COUNTERSINK_T, T, x, y, 24))
    m = DIFF(m, cs)
    return m


# ---------------------------------------------------------------------------
# 14. Задняя панель rear_plate 300 × 44 × 2  (spec/30 §3 №15, spec/20 §9)
# ---------------------------------------------------------------------------
def build_rear_plate():
    print("[12/15] задняя панель rear_plate …")
    W, H = P.REAR_W, P.REAR_H
    # строим «лёжа» в плоскости (U,V) = (X, Z), затем ставим вертикально
    poly = rrect(0, W, 0, H, 2.0)
    for (name, X, Z, form) in P.REAR_HOLES:
        u, v = X - P.REAR_X0, Z - P.REAR_Z0
        if form[0] == "circle":
            poly = poly.difference(circle(u, v, form[1] / 2))
        else:
            _t, w, h, r = form
            poly = poly.difference(rounded_rect_window(u, v, w, h, r))
    # 6 отверстий M3
    for (X, Z) in P.REAR_SCREWS:
        u, v = X - P.REAR_X0, Z - P.REAR_Z0
        poly = poly.difference(circle(u, v, P.REAR_SCREW_D / 2))
    m = ext(poly, 0.0, P.REAR_T)
    # цековки с наружной стороны (Y = 0 в локальной ориентации)
    cs = []
    for (X, Z) in P.REAR_SCREWS:
        u, v = X - P.REAR_X0, Z - P.REAR_Z0
        cs.append(cone_frustum(3.3, 1.65, -0.1, P.PLATE_COUNTERSINK_T, u, v, 24))
    m = DIFF(m, cs)
    # ставим вертикально: (u, v, w) → (u, -w, v), затем в глобальные координаты
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    # сейчас y = -w ∈ [-2,0], z = v (0…44), x = u (0…300)
    m.apply_translation(V(P.REAR_X0, 0.0, P.REAR_Z0))
    # x 7.5…307.5, y −2…0, z 2…46 — как в сборке
    # Ender-3: 300 мм не влезает в 220 → делим на 2 половины по шву X = 157.5
    L = INTER(m, box(-50.0, P.SEAM_X, -10.0, 10.0, -10.0, 60.0))
    R = INTER(m, box(P.SEAM_X, 400.0, -10.0, 10.0, -10.0, 60.0))
    return L, R


# ---------------------------------------------------------------------------
# 15. Накладки рукояток grip_pad ×2 + ножки-демпферы  (spec/30 §2/§3 №16)
# ---------------------------------------------------------------------------
def build_grip_pad():
    """Накладка рукоятки 55 × 85 × 2 (TPU) + 2 ножки-демпфера Ø10 × 1.5.

    Геометрия нарочно простая (экструзия + цилиндры + канавки-цилиндры):
    все операции дают замкнутый меш, проверено round-trip через STL
    (`trimesh.load(...).is_watertight == True`).
    """
    w, d, t = P.GRIP_PAD_W, P.GRIP_PAD_D, P.GRIP_PAD_T
    pad = rrect(-w / 2, w / 2, -d / 2, d / 2, 6.0)
    m = ext(pad, 0.0, t)
    # 2 ножки-демпфера на нижней стороне, объединение с перекрытием 0.6
    for yy in (-36.0, 36.0):
        m = U([m, cyl_z(P.FOOT_D / 2, -P.FOOT_H, 0.6, 0.0, yy, 32)])
    # 4 канавки под пальцы (R6, шаг 18) — режутся после объединения ножек
    grooves = []
    for yy in (-27.0, -9.0, 9.0, 27.0):
        grooves.append(cyl_x(P.GRIP_GROOVES_R, -w / 2 - 2, w / 2 + 2,
                             yy, 0.0 - P.GRIP_GROOVES_R + 0.8, 24))
    m = DIFF(m, grooves)
    return m


# ---------------------------------------------------------------------------
# 16. Калибровочный крест (spec/30 §7.3) — mechanical/test_fit/
# ---------------------------------------------------------------------------
def build_test_cross():
    print("[15/15] калибровочный крест test_fit …")
    m = box(-15, 15, -8, 8, 0, 4)
    m = U([m, box(-4, 4, -8, 8, 0, 12), box(-15, 15, -3, 3, 0, 12)])
    m = DIFF(m, [cyl_z(P.M3_INSERT_D / 2, 4.0, 10.0, 11.0, 0.0, 20)])
    m = DIFF(m, [cyl_z(P.M3_CLEAR_D / 2, 4.0, 12.1, 0.0, 0.0, 20)])
    # шип 6 × 3 и ответный паз — для проверки зазора 0.25
    m = U([m, box(-12, -9, -3, 3, 12, 15)])
    m = DIFF(m, [box(9, 12.25, -3.25, 3.25, 12, 15.3)])
    return m


# ---------------------------------------------------------------------------
# 17. Сборка: список экземпляров для рендера/документации
# ---------------------------------------------------------------------------
def build_instances():
    inst = []

    def add(name, file, pos=(0, 0, 0), rot=(0, 0, 0)):
        inst.append({"name": name, "file": file, "pos": list(pos), "rot": list(rot)})

    add("bottom_L", "bottom_L.stl")
    add("bottom_R", "bottom_R.stl")
    add("panel_upper_L", "panel_upper_L.stl")
    add("panel_upper_R", "panel_upper_R.stl")
    add("deck_plate_L_pads", "deck_plate_L_pads.stl")
    add("deck_plate_R_pads", "deck_plate_R_pads.stl")
    for i, (_n, x, y) in enumerate(P.ENCODERS):
        add(f"knob_{i+1}", "knob.stl", (x, y, P.KNOB_Z0))
    for x in P.PAD_X:
        for y in P.PAD_Y:
            add("pad_cap", "pad_cap.stl", (x, y, P.PAD_CAP_Z0))
    for (x, y) in [(x, y) for x in P.KEY_X_L for y in P.KEY_Y] + \
                  [(x, P.KEY_THUMB_Y) for x in P.KEY_THUMB_X_L]:
        add("keycap", "keycap.stl", (x, y, P.KEYCAP_Z0))
    for (x, y) in [(P.KEY_MIRROR(x), y) for x in P.KEY_X_L for y in P.KEY_Y] + \
                  [(P.KEY_MIRROR(x), P.KEY_THUMB_Y) for x in P.KEY_THUMB_X_L]:
        add("keycap", "keycap.stl", (x, y, P.KEYCAP_Z0))
    for (n, x) in P.SLIDERS:
        add(f"fader_cap_{n}", "fader_cap.stl",
            (x, (P.SLIDER_SLOT_Y0 + P.SLIDER_SLOT_Y1) / 2, 40.5))
    for (n, x, y) in P.SHOULDERS:
        add(f"shoulder_cap_{n}", "shoulder_cap.stl", (x, y, P.PANEL_TOP))
    for i, (_n, x, y) in enumerate(P.ENCODERS):
        add(f"light_guide_{i+1}", "light_guide.stl", (x, y, P.PANEL1_Z1))
    add("light_guide_status", "light_guide.stl", (157.5, 76.0, P.PANEL1_Z1))
    add("dock_cradle", "dock_cradle.stl", (0.0, 0.0, 0.0))
    add("bay_hatch", "bay_hatch.stl", (P.UPPER_DOCK_X, P.BODY_D / 2, 0.0))
    add("rear_plate_L", "rear_plate_L.stl", (0.0, 0.0, 0.0))
    add("rear_plate_R", "rear_plate_R.stl", (0.0, 0.0, 0.0))
    add("grip_pad_L", "grip_pad.stl", (30.0, 70.0, P.GRIP_PAD_Z))
    add("grip_pad_R", "grip_pad.stl", (P.BODY_W - 30.0, 70.0, P.GRIP_PAD_Z))
    return inst


# ---------------------------------------------------------------------------
# 18. main
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    print("=" * 78)
    print("Bukifon mechanical generator  v%s  |  %s" % (P.VERSION, P.LICENSE))
    print("=" * 78)

    bl, br = build_bottom_full()
    add_part("bottom_L", bl)
    add_part("bottom_R", br)

    pul, pur = build_panel_upper()
    add_part("panel_upper_L", pul)
    add_part("panel_upper_R", pur)

    for name, m in build_deck_plates().items():
        add_part(name, m)

    add_part("knob", build_knob())
    add_part("pad_cap", build_pad_cap())
    add_part("keycap", build_keycap())
    add_part("fader_cap", build_fader_cap())
    add_part("shoulder_cap", build_shoulder_cap())
    add_part("light_guide", build_light_guide())
    add_part("dock_cradle", build_dock_cradle())
    add_part("bay_hatch", build_bay_hatch())
    rp_L, rp_R = build_rear_plate()
    add_part("rear_plate_L", rp_L)
    add_part("rear_plate_R", rp_R)
    add_part("grip_pad", build_grip_pad())
    add_part("seam_key", build_seam_key())

    meta = export_all()

    cross = build_test_cross()
    cross.export(os.path.join(ROOT, "mechanical", "test_fit", "test_cross.stl"))
    print("  STL  test_fit/test_cross.stl  watertight=%s" % cross.is_watertight)

    inst = build_instances()
    with open(ASSEMBLY_JSON, "w") as f:
        json.dump({"parts": meta, "instances": inst}, f, indent=1)
    print(f"\n  assembly.json: {len(inst)} экземпляров")

    # fit_check.md
    try:
        import fitcheck
        fitcheck.run(PARTS, meta, inst)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("!! fit_check не записан:", e)

    print("\nГотово за %.1f c" % (time.time() - t0))


if __name__ == "__main__":
    main()
