"""Букифон v1.7 — параметрический генератор корпуса 380 × 210 × 63 мм.

Вход:  mechanical/generator/params_v17.py (читает spec/panel-spec-v1.7.json)
Выход: mechanical/stl_v17/*.stl + assembly_v17.json
       mechanical/fit_check.md (секция v1.7) — см. fitcheck_v17.py

Разрез печати X = 190:
  * панель 380 мм → 2 половины 193 + 190 мм (шип 3 × 1.2 по шву, паз 3.2);
  * корпус 380 мм → 2 половины 193 + 190 мм (шип пола 3 × 3 по шву, паз 3.2);
  * шов проходит через окно экрана (скрыт за стеклом), между джеками и
    клавиатурами, между фейдерами — см. fit_check §v1.7.
  * обе половины ≤ 220 × 220 → печать на Ender-3 без поддержек.

Запуск:
    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/case_v17.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box as sbox
from shapely.ops import unary_union as s_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P0           # noqa: E402  (v1.0: только утилиты экспорта)
import params_v17 as P        # noqa: E402
import case as C              # noqa: E402  (переиспользуем геометрические утилиты v1.0)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STL_DIR = os.path.join(ROOT, "mechanical", "stl_v17")
ASSEMBLY_JSON = os.path.join(HERE, "assembly_v17.json")
os.makedirs(STL_DIR, exist_ok=True)

PARTS = {}


# ---------------------------------------------------------------------------
#  2D-профиль панели: все отверстия — из JSON
# ---------------------------------------------------------------------------
def _c(cx, cy, r):
    return Point(cx, cy).buffer(r, quad_segs=16)


def _rr(x0, x1, y0, y1, r):
    r = max(0.01, min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
    return sbox(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=12, join_style=1)


def ext_any(poly, z0, z1):
    """Экструзия Polygon или MultiPolygon (шинка/шпонка может распасться)."""
    if poly.geom_type == "Polygon":
        return C.ext(poly, z0, z1)
    parts = [C.ext(g, z0, z1) for g in poly.geoms if g.area > 0.01]
    return C.U(parts)


def panel_holes():
    """Список 2D-отверстий панели (по JSON) + крепёж; используется и для
    PANEL-1 rev.2 (с запасом), и для проверки совпадения вырезов."""
    holes = {}
    # экран 5.0": вырез = активная область, без рамки
    s = P.SCREEN
    holes["screen"] = _rr(s["x"], s["x"] + s["w"], s["y"], s["y"] + s["h"], P.SCREEN_R)
    # 42 клавиши Choc: квадрат 14 × 14 с защёлками, повёрнут на deg
    for i, k in enumerate(P.KEYS):
        sq = _rr(k["x"] - P.KEY_WIN / 2, k["x"] + P.KEY_WIN / 2,
                 k["y"] - P.KEY_WIN / 2, k["y"] + P.KEY_WIN / 2, P.KEY_WIN_R)
        holes[f"key{i+1}"] = affinity.rotate(sq, k["deg"], origin=(k["x"], k["y"]))
    # 16 энкодеров: Ø7.2 под вал
    for i, k in enumerate(P.KNOBS):
        holes[f"knob{i+1}"] = _c(k["x"], k["y"], P.KNOB_HOLE / 2)
    # 10 mini-jack: Ø6.2
    for i, j in enumerate(P.JACKS):
        holes[f"jack{i+1}"] = _c(j["x"], j["y"], P.JACK_HOLE / 2)
    # 2 фейдера: окно 8 × 68 R4 + 4 × M2.5 на каждый
    for i, f in enumerate(P.FADERS):
        holes[f"fader{i+1}"] = _rr(f["x"] - P.FADER_SLOT_W / 2, f["x"] + P.FADER_SLOT_W / 2,
                                   f["y0"], f["y1"], P.FADER_SLOT_R)
        for j, dy in enumerate(P.FADER_M25_Y):
            for sgn in (-1, 1):
                holes[f"fader{i+1}_m{j}{sgn}"] = _c(f["x"] + sgn * P.FADER_M25_DX, dy,
                                                    P.FADER_M25_HOLE / 2)
    # 4 × M3 по углам
    for i, (x, y) in enumerate(P.PANEL_SCREWS):
        holes[f"screw{i+1}"] = _c(x, y, P.PANEL_SCREW_D / 2)
    # вырез USB-C на задней кромке
    holes["usbc"] = _rr(P.USBC["cx"] - P.USBC["w"] / 2, P.USBC["cx"] + P.USBC["w"] / 2,
                        -2.0, P.USBC["depth"], P.USBC["r"])
    return holes


def panel_polygon():
    poly = _rr(0, P.PANEL_W, 0, P.PANEL_H, P.R_OUT)
    for h in panel_holes().values():
        poly = poly.difference(h)
    return poly


# ---------------------------------------------------------------------------
#  Панель: 2 половины + шип/паз по шву
# ---------------------------------------------------------------------------
def build_panels():
    print("[1/3] панели panel_L / panel_R (шип/паз по X = 190) …")
    holes = panel_holes()
    poly = panel_polygon()
    z0, z1 = P.PANEL_Z0, P.PANEL_Z1
    plate = C.ext(poly, z0, z1)

    # --- крепёж: утопленные гайки энкодеров, гайки джеков, зенковки M3 -------
    cuts = []
    for k in P.KNOBS:
        cuts.append(C.cyl_z(P.KNOB_NUT_D / 2, z1 - P.KNOB_NUT_DEPTH, z1 + 0.1,
                            k["x"], k["y"], 40))
    for j in P.JACKS:
        cuts.append(C.cyl_z(P.JACK_NUT_D / 2, z1 - P.JACK_NUT_DEPTH, z1 + 0.1,
                            j["x"], j["y"], 32))
    for (x, y) in P.PANEL_SCREWS:
        cuts.append(C.cone_frustum(P.PANEL_SCREW_D / 2,
                                   P.PANEL_SCREW_D, z1 - P.PANEL_CSK_T, z1 + 0.1,
                                   x, y, 24))
    # 4 × M2.5 экрана — глухие отверстия снизу панели (2.5 мм)
    for (x, y) in P.SCREEN_M25_POS:
        cuts.append(C.cyl_z(P.SCREEN_M25_HOLE / 2, z0 - 0.1, z0 + 2.5, x, y, 20))
    plate = C.DIFF(plate, cuts)

    # --- внутренний буртик экрана 1.5 мм (модуль не проваливается) ----------
    s_ = P.SCREEN
    ledge_outer = _rr(s_["x"], s_["x"] + s_["w"], s_["y"], s_["y"] + s_["h"],
                      P.SCREEN_R)
    ledge_inner = _rr(s_["x"] + P.SCREEN_LEDGE, s_["x"] + s_["w"] - P.SCREEN_LEDGE,
                      s_["y"] + P.SCREEN_LEDGE,
                      s_["y"] + s_["h"] - P.SCREEN_LEDGE, 1.0)
    ledge_poly = ledge_outer.difference(ledge_inner)
    ledge = C.ext(ledge_poly, z0, z0 + 0.8)
    plate = C.U([plate, ledge])

    # --- шкалы-риски у фейдеров (неглубокие, 0.35 мм) ----------------------
    tick_cuts = []
    for f in P.FADERS:
        n = 11
        for i in range(n):
            y = f["y0"] + 2.0 + i * (f["y1"] - f["y0"] - 4.0) / (n - 1)
            for sgn in (-1, 1):
                tick_cuts.append(C.box(f["x"] + sgn * 6.0 - 1.6,
                                       f["x"] + sgn * 6.0 + 1.6, y - 0.45, y + 0.45,
                                       z1 - 0.35, z1 + 0.1))
    plate = C.DIFF(plate, tick_cuts)

    # --- разрез X = 190 -------------------------------------------------------
    half_L = C.INTER(plate, C.box(-5, P.SEAM_X, -5, P.PANEL_H + 5, -5, 80))
    half_R = C.INTER(plate, C.box(P.SEAM_X, P.PANEL_W + 5, -5, P.PANEL_H + 5, -5, 80))

    # --- шип панели (L): нижние 1.2 мм из 3, вылет 3 мм; паз (R) ------------
    hole_union = s_union(list(holes.values()))
    tongue_poly = sbox(P.SEAM_X, 1.0, P.SEAM_X + P.SEAM_TONGUE_L, P.PANEL_H - 1.0)
    tongue_poly = tongue_poly.difference(hole_union)
    tongue = ext_any(tongue_poly, z0, z0 + P.SEAM_TONGUE_T)
    half_L = C.U([half_L, tongue])
    groove = C.box(P.SEAM_X, P.SEAM_X + P.SEAM_TONGUE_L + 0.2,
                   0.8, P.PANEL_H - 0.8, z0 - 0.1, z0 + P.SEAM_TONGUE_T + 0.1)
    half_R = C.DIFF(half_R, [groove])
    return half_L, half_R


# ---------------------------------------------------------------------------
#  Корпус: скорлупа 380 × 210 × 60 + стойки, батарея, рёбра, вентиляция
# ---------------------------------------------------------------------------
def build_body_full():
    print("[2/3] корпус body_L / body_R (стойки, батарея 1S2P, рёбра, ножки) …")
    z_top = P.BODY_H
    outer = C.ext(_rr(0, P.PANEL_W, 0, P.PANEL_H, P.R_OUT), 0.0, z_top)
    cav = C.ext(_rr(P.WALL, P.PANEL_W - P.WALL, P.WALL, P.PANEL_H - P.WALL,
                    P.R_CAV), P.FLOOR_T, z_top + 1.0)
    solid = C.DIFF(outer, [cav])

    posts = []
    # 4 стойки панели M3 (по углам, как 4 винта на концепте)
    for (x, y) in P.PANEL_SCREWS:
        posts.append(C.cyl_z(P.POST_CORNER_D / 2, P.FLOOR_T, z_top, x, y, 32))
    # 6 стоек PANEL-1 rev.2 (Z 47)
    for (x, y) in P.PANEL1_POSTS:
        posts.append(C.cyl_z(P.BODY_POST_PANEL_D / 2, P.FLOOR_T, P.PANEL1_Z0, x, y, 28))
    # 4 стойки CORE-1 rev.3 (Z 12)
    for (x, y) in P.CORE_POSTS:
        posts.append(C.cyl_z(P.BODY_POST_CORE_D / 2, P.FLOOR_T, P.CORE_Z0, x, y, 28))
    # рёбра жёсткости по внутренним стенкам
    for (x, side) in P.RIBS:
        if side == "rear":
            posts.append(C.box(x - P.RIB_W / 2, x + P.RIB_W / 2,
                               P.WALL, P.WALL + P.RIB_D, P.FLOOR_T, P.FLOOR_T + P.RIB_H))
        else:
            posts.append(C.box(x - P.RIB_W / 2, x + P.RIB_W / 2,
                               P.PANEL_H - P.WALL - P.RIB_D, P.PANEL_H - P.WALL,
                               P.FLOOR_T, P.FLOOR_T + P.RIB_H))
    # ложемент батареи: 3 седла с полукруглыми выемками под 2 × 18650
    cradle = []
    for y in P.BAT_CRADLE_Y:
        saddle = C.box(min(P.BAT_X) - 11.0, max(P.BAT_X) + 11.0,
                       y, y + 6.0, P.BAT_CRADLE_Z0, P.BAT_CRADLE_Z1)
        for bx in P.BAT_X:
            saddle = C.DIFF(saddle, [C.cyl_y(P.BAT_D / 2 + 0.2, y - 1.0, y + 7.0,
                                             bx, P.BAT_CRADLE_Z0 + P.BAT_D / 2 + 0.2, 32)])
        cradle.append(saddle)
    posts.extend(cradle)
    solid = C.U([solid] + posts)

    cuts = []
    # втулки M3: панель (сверху), PANEL-1 (сверху 47), CORE-1 (сверху 12)
    for (x, y) in P.PANEL_SCREWS:
        cuts.append(C.cyl_z(P.M3_INSERT_D / 2, z_top - P.M3_INSERT_DEPTH, z_top + 0.1,
                            x, y, 24))
    for (x, y) in P.PANEL1_POSTS:
        cuts.append(C.cyl_z(P.M3_INSERT_D / 2, P.PANEL1_Z0 - P.M3_INSERT_DEPTH,
                            P.PANEL1_Z0 + 0.1, x, y, 24))
    for (x, y) in P.CORE_POSTS:
        cuts.append(C.cyl_z(P.M3_CLEAR_D / 2, P.CORE_Z0 - 6.0, P.CORE_Z0 + 0.1, x, y, 24))
    # посадочные гнёзда ножек снизу
    for (x, y) in P.FEET:
        cuts.append(C.cyl_z(P.FOOT_RECESS_D / 2, -0.1, P.FOOT_RECESS_H, x, y, 32))
    # вентиляционные щели в дне
    for (x, y) in P.VENT_SLOTS:
        cuts.append(C.box(x - P.VENT_SLOT_W / 2, x + P.VENT_SLOT_W / 2,
                          y - P.VENT_SLOT_L / 2, y + P.VENT_SLOT_L / 2,
                          -0.1, P.FLOOR_T + 0.1))
    # окно под кабель USB-C в задней стенке
    x0, x1, z0, z1 = P.USBC_CABLE_SLOT
    cuts.append(C.box(x0, x1, -1.0, P.WALL + 1.0, z0, z1))
    solid = C.DIFF(solid, cuts)

    # --- разрез X = 190 -------------------------------------------------------
    half_L = C.INTER(solid, C.box(-5, P.SEAM_X, -5, P.PANEL_H + 5, -5, 80))
    half_R = C.INTER(solid, C.box(P.SEAM_X, P.PANEL_W + 5, -5, P.PANEL_H + 5, -5, 80))

    # --- шип пола (L): 3 мм вылета, 0…3 мм; паз (R) -------------------------
    tab = C.box(P.SEAM_X, P.SEAM_X + 3.0, 0.0, P.PANEL_H,
                0.0, P.SEAM_FLOOR_TAB_Z)
    half_L = C.U([half_L, tab])
    groove = C.box(P.SEAM_X, P.SEAM_X + 3.2, 0.0, P.PANEL_H,
                   -0.1, P.SEAM_FLOOR_TAB_Z + 0.2)
    half_R = C.DIFF(half_R, [groove])
    return half_L, half_R




# ---------------------------------------------------------------------------
#  Колпачок Choc v1.7: 17.5 × 16.5 × 5.5, R1.5, вогнутость, паз-крест Choc
# ---------------------------------------------------------------------------
def build_keycap_v17():
    print("[2.5/3] колпачок keycap_v17 (17.5 × 16.5 × 5.5) …")
    w, d, h = P.KEYCAP_W, P.KEYCAP_H, P.KEYCAP_T
    bw, bd = P.KEYCAP_BOTTOM_W, P.KEYCAP_BOTTOM_D
    # ступенчатая «юбка» с наклоном ~15°: низ → верх
    steps = 5
    m = None
    for i in range(steps):
        t0 = h * i / steps
        t1 = h * (i + 1) / steps
        ww = bw + (w - bw) * (i + 1) / steps
        dd = bd + (d - bd) * (i + 1) / steps
        seg = C.ext(_rr(-ww / 2, ww / 2, -dd / 2, dd / 2,
                        P.KEYCAP_R * (0.8 + 0.2 * (i + 1) / steps)), t0 - 0.01, t1)
        m = seg if m is None else C.U([m, seg])
    # вогнутая площадка (сфера R30, глубина 0.45)
    sph = trimesh.creation.icosphere(subdivisions=4, radius=30.0)
    sph.apply_translation(C.V(0, 0, h + 30.0 - P.KEYCAP_DISH))
    m = C.DIFF(m, [sph])
    # полость снизу + паз-крест Choc
    m = C.DIFF(m, [C.ext(_rr(-6.4, 6.4, -5.9, 5.9, 1.6), -0.1, 3.2)])
    cross = C.U([C.box(-1.9, 1.9, -0.65, 0.65, -0.1, 2.4),
                 C.box(-0.65, 0.65, -2.4, 2.4, -0.1, 2.4)])
    m = C.DIFF(m, [cross])
    m.apply_translation(C.V(0, 0, 0))
    return m


# ---------------------------------------------------------------------------
#  Ножки (TPU, утоплены в дно — высота в сборе остаётся 63)
# ---------------------------------------------------------------------------
def build_foot():
    print("[3/3] ножка foot (TPU) …")
    # слегка суженная шайба (без булевых резов — гарантированный watertight
    # после round-trip STL; печатается TPU)
    return C.cone_frustum(P.FOOT_D / 2 - 0.5, P.FOOT_D / 2, 0.0, P.FOOT_H,
                          0.0, 0.0, 48)




# ---------------------------------------------------------------------------
#  Минимальный 3MF-writer (без networkx/lxml, который требует trimesh 5.x)
# ---------------------------------------------------------------------------
def _xml_escape(s_):
    return s_.replace("&", "&amp;").replace("<", "&lt;")


def export_3mf(mesh, path):
    import zipfile
    v = np.asarray(mesh.vertices)
    f = np.asarray(mesh.faces)
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                 '</Types>')
    parts.append('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                 'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
                 '</Relationships>')
    verts = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>'
                    for x, y, z in v)
    tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="ru-RU" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">Bukifon v1.7</metadata>'
             '<resources><object id="1" type="model"><mesh>'
             f'<vertices>{verts}</vertices><triangles>{tris}</triangles>'
             '</mesh></object></resources>'
             '<build><item objectid="1"/></build></model>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", parts[0])
        z.writestr("_rels/.rels", parts[1])
        z.writestr("3D/3dmodel.model", model)


# ---------------------------------------------------------------------------
#  Экспорт и сборка
# ---------------------------------------------------------------------------
def export_all():
    meta = {}
    for name, mesh in PARTS.items():
        fn = os.path.join(STL_DIR, name + ".stl")
        mesh.export(fn)
        # 3MF (для слайсеров и обмена): каждая деталь отдельно
        export_3mf(mesh, os.path.join(STL_DIR, name + ".3mf"))
        reloaded = trimesh.load(fn)
        b = mesh.bounds[1] - mesh.bounds[0]
        meta[name] = {
            "file": os.path.basename(fn),
            "bbox": [round(float(v), 3) for v in b],
            "min": [round(float(v), 3) for v in mesh.bounds[0]],
            "max": [round(float(v), 3) for v in mesh.bounds[1]],
            "watertight": bool(mesh.is_watertight),
            "watertight_reload": bool(reloaded.is_watertight),
            "volume_mm3": round(float(mesh.volume), 1),
            "triangles": int(len(mesh.faces)),
        }
        print(f"  STL  {name:10s} {str(meta[name]['bbox']):28s} "
              f"watertight={meta[name]['watertight']}/reload={reloaded.is_watertight} "
              f"vol={meta[name]['volume_mm3']} mm3")
    return meta


def build_instances():
    inst = [
        {"name": "body_L", "file": "body_L.stl", "pos": [0, 0, 0], "rot": [0, 0, 0]},
        {"name": "body_R", "file": "body_R.stl", "pos": [0, 0, 0], "rot": [0, 0, 0]},
        {"name": "panel_L", "file": "panel_L.stl", "pos": [0, 0, 0], "rot": [0, 0, 0]},
        {"name": "panel_R", "file": "panel_R.stl", "pos": [0, 0, 0], "rot": [0, 0, 0]},
    ]
    for i, (x, y) in enumerate(P.FEET):
        inst.append({"name": f"foot_{i+1}", "file": "foot.stl",
                     "pos": [x, y, 0.0], "rot": [0, 0, 0]})
    return inst


def main():
    t0 = time.time()
    print("=" * 78)
    print("Букифон v1.7 — генератор корпуса 380 × 210 × 63")
    print("=" * 78)
    panel_L, panel_R = build_panels()
    PARTS["panel_L"] = panel_L
    PARTS["panel_R"] = panel_R
    body_L, body_R = build_body_full()
    PARTS["body_L"] = body_L
    PARTS["body_R"] = body_R
    PARTS["foot"] = build_foot()
    PARTS["keycap_v17"] = build_keycap_v17()
    meta = export_all()
    inst = build_instances()
    with open(ASSEMBLY_JSON, "w") as f:
        json.dump({"parts": meta, "instances": inst}, f, indent=1)
    # 3MF сборки (все детали на своих местах) — для предпросмотра/слайсера
    placed = []
    for item in inst:
        m = trimesh.load(os.path.join(STL_DIR, item["file"]))
        m.apply_translation(item["pos"])
        placed.append(m)
    export_3mf(trimesh.util.concatenate(placed),
               os.path.join(STL_DIR, "bukifon_v17_assembly.3mf"))
    print(f"\n  assembly_v17.json: {len(inst)} экземпляров")

    try:
        import fitcheck_v17
        fitcheck_v17.run(PARTS, meta, inst)
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("!! fit_check для v1.7 не записан")
    print("\nГотово за %.1f c" % (time.time() - t0))


if __name__ == "__main__":
    main()
