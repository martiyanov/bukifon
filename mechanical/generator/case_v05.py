"""Букифон v0.5 — генератор трёх вариантов корпуса.

A — flat (копия v0.4); B — клин 8°; C — клин 12° + батарейный отсек 1S2P
+ складная подставка + кабельный канал. Панель во всех вариантах — копия
panel_L/R из stl_v04 (плоская, 193+190 с шипом, все 83 выреза из v0.4 JSON).

Выход на вариант:
  mechanical/stl_v05_<A|B|C>/*.stl|*.3mf + assembly_v05_<A|B|C>.json
  mechanical/preview_v05_<A|B|C>/ (рендеры — render_v05.py)
  секция v0.5-<X> в mechanical/fit_check.md (fitcheck_v05.py)

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/case_v05.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

import numpy as np
import trimesh
from shapely.geometry import box as sbox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params_v05 as P
import params_v04 as P04
import case as C
import case_v04 as C04

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STL_V04 = os.path.join(ROOT, "mechanical", "stl_v04")


# ---------------------------------------------------------------------------
def _rrect(x0, x1, y0, y1, r):
    return C.rrect(x0, x1, y0, y1, r)


def _panel_to_world(v, xy):
    """(x, y) в координатах панели → (x, y_world) на наклонной плоскости."""
    x, yf = xy
    yw = 105.0 + (yf - 105.0) * v["cos"]
    return float(x), float(yw)


def _rim_z(v, yw):
    """Z верхней кромки корпуса (плоскость панели) в точке y_world."""
    return v["center_rim"] - (yw - 105.0) * v["k"]


def _plane_cutter(v, dz=0.0, above=True):
    """Полупространство выше (above) или ниже плоскости панели, сдвинутой
    по нормали на dz. Возвращает меш-резак."""
    a = v["k"]
    box = trimesh.creation.box(extents=[900, 900, 600])
    box.apply_translation([0, 0, 300 if above else -300])   # нижняя грань z=0
    Rx = trimesh.transformations.rotation_matrix(-np.arctan(a), [1, 0, 0])
    box.apply_transform(Rx)
    # dz > 0 — плоскость сдвинута ВЫШЕ (по нормали панели)
    zc = v["center_rim"] + dz * v["cos"]
    yc = 105.0 + dz * v["sin"]
    box.apply_translation([190.0, yc, zc])
    return box


def _rotated_cyl(v, r, top_xyz, depth, sections=24):
    """Цилиндр-отверстие радиусом r, ось вдоль нормали панели, от top_xyz вниз."""
    m = trimesh.creation.cylinder(radius=r, height=depth, sections=sections)
    m.apply_transform(trimesh.transformations.rotation_matrix(
        -np.arctan(v["k"]), [1, 0, 0]))
    m.apply_translation(top_xyz)
    return m


def _post_hole_along_normal(v, r, top_xyz, depth):
    n = np.array([0.0, v["sin"], v["cos"]])
    centre = np.array(top_xyz) - n * (depth / 2.0)
    return _rotated_cyl(v, r, centre, depth)


# ---------------------------------------------------------------------------
def build_body(v):
    """Нижняя скорлупа (body_L/body_R) под выбранный вариант."""
    name = v["name"]
    if name == "A":
        # A — точная копия v0.4: берём готовые STL
        out = {}
        for part in ("body_L", "body_R"):
            src = os.path.join(STL_V04, part + ".stl")
            m = trimesh.load(src)
            out[part] = m
        return out

    Hmax = v["rear_rim"] + 6.0
    outer = C.ext(_rrect(0, 380, 0, 210, P.R_OUT), 0.0, Hmax)
    inner = C.ext(_rrect(P.WALL, 380 - P.WALL, P.WALL, 210 - P.WALL, P.R_CAV),
                  P.FLOOR_T, Hmax)
    cav = C.INTER(inner, _plane_cutter(v, above=False, dz=0.6))
    solid = C.DIFF(outer, [cav])

    # ---- внутренние тела: стойки/рёбра/ложемент/отсек ---------------------
    feats = []
    # стойки панели (4 × M3) — верх по плоскости панели
    for (x, yf) in P04.PANEL_SCREWS:
        xw, yw = _panel_to_world(v, (x, yf))
        feats.append(C.cyl_z(4.5, P.FLOOR_T - 0.6, Hmax, xw, yw, 32))
    # стойки PANEL-2 (6 × M3) — на 8 мм ниже панели по нормали
    for (x, yf) in P.PANEL1_POSTS:
        xw, yw = _panel_to_world(v, (x, yf))
        # плоскость PANEL-2: исходная точка (x,yw0) сдвинута на -8 по нормали
        yw0 = yw + P.PANEL2_OFFSET * v["sin"]
        z2 = _rim_z(v, yw0) - P.PANEL2_OFFSET * v["cos"]
        feats.append(C.cyl_z(3.5, P.FLOOR_T - 0.6, z2, xw, yw, 28))
    # стойки CORE-2 (4 × M3) — горизонтально, Z 12
    for (x, y) in P.CORE_POSTS:
        feats.append(C.cyl_z(3.5, P.FLOOR_T - 0.6, P.CORE_Z0, x, y, 28))
    # стойки PWR-2 (4 × M2.5) — Z 6, горизонтально
    for (x, y) in P.PWR2_POSTS:
        feats.append(C.cyl_z(3.0, P.FLOOR_T - 0.6, 6.0, x, y, 24))
    # рёбра жёсткости
    for x in (60.0, 110.0, 290.0, 340.0):
        feats.append(C.box(x - 1.5, x + 1.5, P.WALL - 0.6, P.WALL + 5.6,
                           P.FLOOR_T - 0.6, Hmax))
        feats.append(C.box(x - 1.5, x + 1.5, 210 - P.WALL - 5.6, 210 - P.WALL + 0.6,
                           P.FLOOR_T - 0.6, Hmax))
    # батарея: A/B — открытые седла; C — закрытый отсек с крышкой
    if v["battery"] == "space":
        for yy in (P.BAT_Y0 - 1.0, 88.0, P.BAT_Y1 - 6.0):
            saddle = C.box(min(P.BAT_X) - 11.0, max(P.BAT_X) + 11.0,
                           yy, yy + 6.0, 2.4, 23.0)
            for bx in P.BAT_X:
                saddle = C.DIFF(saddle, [C.cyl_y(P.BAT_D / 2 + 0.2, yy - 1.0,
                                                 yy + 7.0, bx, 3.0 + P.BAT_D / 2 + 0.2, 32)])
            feats.append(saddle)
    else:
        x0, x1, y0, y1 = 292.0, 372.0, 54.0, 134.0
        walls = [
            C.box(x0, x0 + 6.0, y0, y1, 0.0, 24.0),
            C.box(x1 - 6.0, x1, y0, y1, 0.0, 24.0),
            C.box(x0 + 6.0, x1 - 6.0, y0, y0 + 6.0, 0.0, 24.0),
            C.box(x0 + 6.0, x1 - 6.0, y1 - 6.0, y1, 0.0, 24.0),
        ]
        feats += walls
        # бобышки крышки в стенках (4 × M3)
        for (bx, by) in ((295.0, 57.0), (369.0, 57.0), (295.0, 131.0), (369.0, 131.0)):
            feats.append(C.cyl_z(3.5, 0.0, 24.0, bx, by, 24))
        solid = C.DIFF(solid, [C.box(x0 + 6.0, x1 - 6.0, y0 + 6.0, y1 - 6.0,
                                     -1.0, 24.0)])
    solid = C.U([solid] + feats)

    # ---- срез верхней плоскости (наклон) ---------------------------------
    solid = C.DIFF(solid, [_plane_cutter(v, above=True)])

    # ---- фаска R4 передней кромки (запястье, docs/21-ergonomics) ----------
    if v["angle_deg"] > 0:
        rf = v["front_rim"]
        corner = C.box(-5, 385, 205.9, 211, rf - 5.0, rf + 2.0)
        cyl = C.cyl_x(4.0, -5, 385, 206.0, rf - 4.0, 48)
        solid = C.DIFF(solid, [C.DIFF(corner, [cyl])])

    # ---- отверстия --------------------------------------------------------
    cuts = []
    # втулки панели M3 — по нормали панели (6 мм от верхней плоскости)
    for (x, yf) in P04.PANEL_SCREWS:
        xw, yw = _panel_to_world(v, (x, yf))
        top = (xw, yw, _rim_z(v, yw) + 0.1)
        cuts.append(_post_hole_along_normal(v, P.M3_INSERT_D / 2, top, 6.2))
    # PANEL-2: втулки M3 сверху стоек
    for (x, yf) in P.PANEL1_POSTS:
        xw, yw = _panel_to_world(v, (x, yf))
        yw0 = yw + P.PANEL2_OFFSET * v["sin"]
        z2 = _rim_z(v, yw0) - P.PANEL2_OFFSET * v["cos"]
        cuts.append(C.cyl_z(P.M3_INSERT_D / 2, z2 - 6.0, z2 + 0.1, xw, yw, 24))
    # CORE-2 / PWR-2: резьбовые отверстия
    for (x, y) in P.CORE_POSTS:
        cuts.append(C.cyl_z(P.M3_CLEAR_D / 2, P.CORE_Z0 - 6.0, P.CORE_Z0 + 0.1, x, y, 24))
    for (x, y) in P.PWR2_POSTS:
        cuts.append(C.cyl_z(1.35, 4.0, 6.1, x, y, 20))
    # гнёзда ножек
    for (x, y) in P.FEET:
        cuts.append(C.cyl_z(P.FOOT_RECESS_D / 2, -0.1, P.FOOT_RECESS_H, x, y, 32))
    # вентиляционные щели — в задней части дна (конвекция при наклоне)
    for x in (70.0, 100.0, 130.0, 250.0, 280.0, 310.0):
        cuts.append(C.box(x - 1.25, x + 1.25, 22.0, 44.0, -0.1, P.FLOOR_T + 0.1))
    # окно USB-C-кабеля в задней стенке (у верхней кромки)
    cuts.append(C.box(346.0, 356.0, -1.0, 3.5,
                      v["rear_rim"] - 9.0, v["rear_rim"] + 1.0))
    # кабельный канал снизу сзади (C)
    if v["cable_channel"]:
        cuts.append(C.box(150.0, 250.0, -1.0, 10.0, P.FLOOR_T, 12.0))
        for cx in (170.0, 230.0):
            cuts.append(C.cyl_z(2.0, -0.1, P.FLOOR_T + 0.1, cx, 6.0, 16))
    # отверстия под подставку (C): горизонтальные M3 сзади, ось Y
    if v["stand"]:
        for sx in (116.0, 264.0):
            cuts.append(C.cyl_y(2.3, -1.0, 9.0, sx, 8.0, 20))
            cuts.append(C.cyl_y(P.M3_CLEAR_D / 2, 2.0, 9.0, sx, 8.0, 20))
    solid = C.DIFF(solid, cuts)

    # ---- разрез X = 190 + шип пола ---------------------------------------
    half_L = C.INTER(solid, C.box(-5, P.SEAM_X, -5, 215, -5, 200))
    half_R = C.INTER(solid, C.box(P.SEAM_X, 385, -5, 215, -5, 200))
    # Шов — прямой стык (без шипа в дне): половины центрируются шипом панели
    # 3 × 1.2 (panel_L/R) и стягиваются 4 винтами M3 по углам панели.
    return {"body_L": half_L, "body_R": half_R}


# ---------------------------------------------------------------------------
def build_battery_lid():
    """Крышка батарейного отсека C: 86 × 86 × 2.5, 4 × M3, цековка снизу."""
    w = d = 86.0
    holes = [(295.0 - 332.0, 57.0 - 94.0), (369.0 - 332.0, 57.0 - 94.0),
             (295.0 - 332.0, 131.0 - 94.0), (369.0 - 332.0, 131.0 - 94.0)]
    poly = _rrect(-w / 2, w / 2, -d / 2, d / 2, 3.0)
    for (hx, hy) in holes:
        circ = __import__("shapely.geometry", fromlist=["Point"]).Point(hx, hy).buffer(1.65, 24)
        poly = poly.difference(circ)
    m = C.ext(poly, 0.0, 2.5)
    cuts = []
    for (hx, hy) in holes:
        # цековка Ø6.6 × 1.3 снизу + сквозное Ø3.3
        cuts.append(C.cyl_z(3.3, -0.1, 1.3, hx, hy, 24))
        cuts.append(C.cyl_z(1.65, 1.2, 2.6, hx, hy, 24))
    return C.DIFF(m, cuts)


def build_stand():
    """Складная U-подставка C: 148 × 67 × 6, 2 × Ø3.4 под оси."""
    m = C.ext(_rrect(-74, 74, -6, 61, 3.0), 0.0, 6.0)
    # облегчение: проём между ногами
    m = C.DIFF(m, [C.ext(_rrect(-62, 62, -3, 49, 2.0), -0.1, 6.1)])
    holes = [(-68.0, 3.0), (68.0, 3.0)]
    cuts = []
    for (hx, hy) in holes:
        cuts.append(C.cyl_z(1.7, -0.1, 6.1, hx, hy, 24))
    return C.DIFF(m, cuts)


# ---------------------------------------------------------------------------
def _3mf(mesh, path):
    import zipfile
    v = np.asarray(mesh.vertices)
    f = np.asarray(mesh.faces)
    verts = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v)
    tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="ru-RU" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources><object id="1" type="model"><mesh><vertices>{verts}</vertices>'
             f'<triangles>{tris}</triangles></mesh></object></resources>'
             '<build><item objectid="1"/></build></model>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def clean_mesh(m):
    """Убирает дегенеративные грани и микро-обломки CSG (0-объёмные слайверы)."""
    try:
        m.update_faces(m.nondegenerate_faces())
        m.update_faces(m.unique_faces())
        m.remove_unreferenced_vertices()
        comps = m.split(only_watertight=False)
        big = [c for c in comps if abs(float(c.volume)) > 1.0]
        if big and len(big) != len(comps):
            m = trimesh.util.concatenate(big)
            m.update_faces(m.nondegenerate_faces())
            m.remove_unreferenced_vertices()
    except Exception:  # noqa: BLE001
        pass
    return m


def export_variant(v, stl_dir, parts):
    meta = {}
    for name, mesh in parts.items():
        mesh = clean_mesh(mesh)
        fn = os.path.join(stl_dir, name + ".stl")
        mesh.export(fn)
        try:
            _3mf(mesh, os.path.join(stl_dir, name + ".3mf"))
        except Exception:  # noqa: BLE001
            pass
        rt = trimesh.load(fn)
        b = mesh.bounds[1] - mesh.bounds[0]
        meta[name] = {
            "file": os.path.basename(fn),
            "bbox": [round(float(x), 3) for x in b],
            "min": [round(float(x), 3) for x in mesh.bounds[0]],
            "max": [round(float(x), 3) for x in mesh.bounds[1]],
            "watertight": bool(mesh.is_watertight),
            "watertight_reload": bool(rt.is_watertight),
            "volume_mm3": round(float(mesh.volume), 1),
        }
        print(f"  [{v['name']}] {name:14s} {str(meta[name]['bbox']):30s} "
              f"watertight={meta[name]['watertight']}/{rt.is_watertight}")
    return meta


def copy_shared(stl_dir):
    """Панель (v0.4 JSON), ножки, колпачок — копии без изменений.

    Источники по приоритету: mechanical/stl_v04 → mechanical/stl_v05_B →
    archive/v0.4/mechanical/stl_v04 (после архивации версий).
    """
    src_dirs = [STL_V04,
                os.path.join(ROOT, "mechanical", "stl_v05_B"),
                os.path.join(ROOT, "archive", "v0.4", "mechanical", "stl_v04")]
    for part in ("panel_L", "panel_R", "foot", "keycap_v17"):
        for ext in (".stl", ".3mf"):
            for src in src_dirs:
                srcf = os.path.join(src, part + ext)
                if os.path.exists(srcf):
                    shutil.copy2(srcf, os.path.join(stl_dir, part + ext))
                    break


def main():
    t0 = time.time()
    print("=" * 78)
    print("Букифон v0.5 — 3 варианта корпуса (A flat / B 8° / C 12° + battery)")
    print("=" * 78)
    import sys as _sys
    names = [a for a in _sys.argv[1:] if a in ("A", "B", "C")] or ["B"]
    for name in names:
        v = P.variant(name)
        stl_dir = os.path.join(ROOT, "mechanical", f"stl_v05_{name}")
        os.makedirs(stl_dir, exist_ok=True)
        print(f"\n=== Вариант {name}: {v['title']}  "
              f"(угол {v['angle_deg']}°, высоты: перед {v['h_front_total']:.2f}, "
              f"зад {v['h_rear_total']:.2f}) ===")
        copy_shared(stl_dir)
        parts = build_body(v)
        if v["battery"] == "bay":
            lid = build_battery_lid()
            # крышка закрывает отсек СНИЗУ (z −2.5…0), впотай под дном
            lid.apply_translation([332.0, 94.0, -2.5])
            parts["battery_lid"] = lid
        if v["stand"]:
            parts["stand"] = build_stand()
        meta = export_variant(v, stl_dir, parts)
        for part in ("panel_L", "panel_R", "foot", "keycap_v17"):
            m = trimesh.load(os.path.join(stl_dir, part + ".stl"))
            b = m.bounds[1] - m.bounds[0]
            meta[part] = {
                "file": part + ".stl",
                "bbox": [round(float(x), 3) for x in b],
                "min": [round(float(x), 3) for x in m.bounds[0]],
                "max": [round(float(x), 3) for x in m.bounds[1]],
                "watertight": bool(m.is_watertight),
                "watertight_reload": bool(m.is_watertight),
                "volume_mm3": round(float(m.volume), 1),
            }
        inst = P.instances(v)
        # матрица установки панели: поворот на -angle вокруг X,
        # центр панели (Y=105, Z=60) → (Y=105, Z=center_rim)
        a = np.radians(v["angle_deg"])
        M = (trimesh.transformations.translation_matrix([0, 105.0, v["center_rim"]])
             @ trimesh.transformations.rotation_matrix(-a, [1, 0, 0])
             @ trimesh.transformations.translation_matrix([0, -105.0, -60.0]))
        with open(os.path.join(HERE, f"assembly_v05_{name}.json"), "w") as f:
            json.dump({"variant": name,
                       "params": {k: v[k] for k in
                                  ("angle_deg", "front_rim", "rear_rim",
                                   "center_rim", "h_front_total", "h_rear_total")},
                       "panel_matrix": [[round(float(x), 6) for x in row] for row in M],
                       "parts": meta, "instances": inst}, f, indent=1,
                      ensure_ascii=False)
        placed = []
        for item in inst:
            m = trimesh.load(os.path.join(stl_dir, item["file"]))
            m.apply_translation(item["pos"])
            placed.append(m)
        _3mf(trimesh.util.concatenate(placed),
             os.path.join(stl_dir, f"bukifon_v05_{name}_assembly.3mf"))
        try:
            if name == "C":
                import fitcheck_v05_C
                fitcheck_v05_C.run(name, meta, inst, parts)
            else:
                import fitcheck_v05
                fitcheck_v05.run(name, meta, inst, parts)
        except Exception:  # noqa: BLE001
            import traceback
            traceback.print_exc()
    print("\nГотово за %.1f c" % (time.time() - t0))


if __name__ == "__main__":
    main()
