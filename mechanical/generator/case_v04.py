"""Букифон v0.4 — генератор ТОЛЬКО панели (380 × 210 × 3) по канону
spec/panel-spec-v0.4.json. Корпус/ножки — копии из v1.7 (не меняются).

Выход:
  mechanical/stl_v04/panel_L.stl, panel_R.stl (+ .3mf)
  mechanical/stl_v04/body_L.stl, body_R.stl, foot.stl — копии v1.7
  mechanical/stl_v04/bukifon_v04_assembly.3mf
  mechanical/generator/assembly_v04.json
  mechanical/fit_check.md — секция v0.4 (см. fitcheck_v04.py)

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/case_v04.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import Point, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params_v04 as P
import case as C

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STL_V17 = os.path.join(ROOT, "mechanical", "stl_v17")
STL_DIR = os.path.join(ROOT, "mechanical", "stl_v04")
ASSEMBLY_JSON = os.path.join(HERE, "assembly_v04.json")
os.makedirs(STL_DIR, exist_ok=True)

PARTS = {}


# ---------------------------------------------------------------------------
def _c(cx, cy, r):
    return Point(cx, cy).buffer(r, quad_segs=16)


def _rr(x0, x1, y0, y1, r):
    r = max(0.01, min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3))
    return sbox(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=12, join_style=1)


def panel_holes():
    """2D-отверстия панели v0.4. Ключи словаря = id из JSON (+ суффиксы)."""
    holes = {}
    s = P.SCREEN
    holes["lcd"] = _rr(s["x"], s["x"] + s["w"], s["y"], s["y"] + s["h"], P.SCREEN_R)
    for k in P.KEYS:
        sq = _rr(k["x"] - P.KEY_WIN / 2, k["x"] + P.KEY_WIN / 2,
                 k["y"] - P.KEY_WIN / 2, k["y"] + P.KEY_WIN / 2, P.KEY_WIN_R)
        holes[k["id"] or f"key_{k['x']}_{k['y']}"] = affinity.rotate(
            sq, k["deg"], origin=(k["x"], k["y"]))
    for e in P.KNOBS:
        holes[e["id"] or f"enc_{e['x']}_{e['y']}"] = _c(e["x"], e["y"], P.KNOB_HOLE / 2)
    for j in P.JACKS:
        holes[j["id"] or f"jack_{j['x']}"] = _c(j["x"], j["y"], P.JACK_HOLE / 2)
    for f in P.FADERS:
        holes[f["id"] + "_slot"] = _rr(f["x"] - f["slot_w"] / 2, f["x"] + f["slot_w"] / 2,
                                       f["y"] - f["slot_l"] / 2, f["y"] + f["slot_l"] / 2,
                                       P.FADER_SLOT_R)
        for i, yy in enumerate(P.FADER_M25_Y):
            for sgn in (-1, 1):
                holes[f"{f['id']}_m{i}{sgn}"] = _c(f["x"] + sgn * P.FADER_M25_DX, yy,
                                                   P.FADER_M25_HOLE / 2)
    for i, (x, y) in enumerate(P.PANEL_SCREWS):
        holes[f"screw{i+1}"] = _c(x, y, P.PANEL_SCREW_D / 2)
    holes["usbc"] = _rr(P.USBC["cx"] - P.USBC["w"] / 2, P.USBC["cx"] + P.USBC["w"] / 2,
                        -2.0, P.USBC["depth"], P.USBC["r"])
    return holes


def panel_polygon():
    poly = _rr(0, P.PANEL_W, 0, P.PANEL_H, P.R_OUT)
    for h in panel_holes().values():
        poly = poly.difference(h)
    return poly


# ---------------------------------------------------------------------------
def build_panels():
    print("[1/2] панели panel_L / panel_R v0.4 (шип/паз X = 190) …")
    z0, z1 = P.PANEL_Z0, P.PANEL_Z1
    plate = C.ext(panel_polygon(), z0, z1)
    holes = panel_holes()

    cuts = []
    for e in P.KNOBS:
        cuts.append(C.cyl_z(P.KNOB_NUT_D / 2, z1 - P.KNOB_NUT_DEPTH, z1 + 0.1,
                            e["x"], e["y"], 40))
    for j in P.JACKS:
        cuts.append(C.cyl_z(P.JACK_NUT_D / 2, z1 - P.JACK_NUT_DEPTH, z1 + 0.1,
                            j["x"], j["y"], 32))
    for (x, y) in P.PANEL_SCREWS:
        cuts.append(C.cone_frustum(P.PANEL_SCREW_D / 2, P.PANEL_SCREW_D,
                                   z1 - P.PANEL_CSK_T, z1 + 0.1, x, y, 24))
    for (x, y) in P.SCREEN_M25_POS:     # глухие M2.5 снизу панели
        cuts.append(C.cyl_z(P.SCREEN_M25_HOLE / 2, z0 - 0.1, z0 + 2.5, x, y, 20))
    plate = C.DIFF(plate, cuts)

    # буртик окна экрана 1.5 мм (модуль не проваливается)
    s = P.SCREEN
    lo = _rr(s["x"], s["x"] + s["w"], s["y"], s["y"] + s["h"], P.SCREEN_R)
    li = _rr(s["x"] + P.SCREEN_LEDGE, s["x"] + s["w"] - P.SCREEN_LEDGE,
             s["y"] + P.SCREEN_LEDGE, s["y"] + s["h"] - P.SCREEN_LEDGE, 1.0)
    plate = C.U([plate, C.ext(lo.difference(li), z0, z0 + 0.8)])

    # шкалы-риски у фейдеров (0.35 мм)
    ticks = []
    for f in P.FADERS:
        n = 11
        for i in range(n):
            yy = f["y"] - f["slot_l"] / 2 + 2.0 + i * (f["slot_l"] - 4.0) / (n - 1)
            for sgn in (-1, 1):
                ticks.append(C.box(f["x"] + sgn * 5.0 - 1.3, f["x"] + sgn * 5.0 + 1.3,
                                   yy - 0.4, yy + 0.4, z1 - 0.35, z1 + 0.1))
    plate = C.DIFF(plate, ticks)

    # разрез X = 190 + шип/паз
    half_L = C.INTER(plate, C.box(-5, P.SEAM_X, -5, P.PANEL_H + 5, -5, 80))
    half_R = C.INTER(plate, C.box(P.SEAM_X, P.PANEL_W + 5, -5, P.PANEL_H + 5, -5, 80))
    hole_union = unary_union(list(holes.values()))
    tongue_poly = sbox(P.SEAM_X, 1.0, P.SEAM_X + P.SEAM_TONGUE_L, P.PANEL_H - 1.0)
    tongue_poly = tongue_poly.difference(hole_union)
    if tongue_poly.geom_type == "Polygon":
        tongue = C.ext(tongue_poly, z0, z0 + P.SEAM_TONGUE_T)
    else:
        tongue = C.U([C.ext(g, z0, z0 + P.SEAM_TONGUE_T)
                      for g in tongue_poly.geoms if g.area > 0.01])
    half_L = C.U([half_L, tongue])
    groove = C.box(P.SEAM_X, P.SEAM_X + P.SEAM_TONGUE_L + 0.2,
                   0.8, P.PANEL_H - 0.8, z0 - 0.1, z0 + P.SEAM_TONGUE_T + 0.1)
    half_R = C.DIFF(half_R, [groove])
    return half_L, half_R


# ---------------------------------------------------------------------------
def _xml_escape(s_):
    return s_.replace("&", "&amp;").replace("<", "&lt;")


def export_3mf(mesh, path):
    import zipfile
    v = np.asarray(mesh.vertices)
    f = np.asarray(mesh.faces)
    verts = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v)
    tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="ru-RU" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">Bukifon v0.4 panel</metadata>'
             f'<resources><object id="1" type="model"><mesh><vertices>{verts}</vertices>'
             f'<triangles>{tris}</triangles></mesh></object></resources>'
             '<build><item objectid="1"/></build></model>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def export_panel(name, mesh):
    fn = os.path.join(STL_DIR, name + ".stl")
    mesh.export(fn)
    export_3mf(mesh, os.path.join(STL_DIR, name + ".3mf"))
    reloaded = trimesh.load(fn)
    b = mesh.bounds[1] - mesh.bounds[0]
    meta = {
        "file": os.path.basename(fn),
        "bbox": [round(float(v), 3) for v in b],
        "min": [round(float(v), 3) for v in mesh.bounds[0]],
        "max": [round(float(v), 3) for v in mesh.bounds[1]],
        "watertight": bool(mesh.is_watertight),
        "watertight_reload": bool(reloaded.is_watertight),
        "volume_mm3": round(float(mesh.volume), 1),
    }
    print(f"  STL  {name:10s} {str(meta['bbox']):28s} "
          f"watertight={meta['watertight']}/reload={reloaded.is_watertight} "
          f"vol={meta['volume_mm3']} mm3")
    return meta


def copy_body_parts():
    """Корпус/ножки v1.7 копируются как есть (task-10: не меняются)."""
    meta = {}
    for name, src in (("body_L", "body_L.stl"), ("body_R", "body_R.stl"),
                      ("foot", "foot.stl"), ("keycap_v17", "keycap_v17.stl")):
        dst = os.path.join(STL_DIR, name + ".stl")
        shutil.copy2(os.path.join(STL_V17, src), dst)
        m = trimesh.load(dst)
        b = m.bounds[1] - m.bounds[0]
        meta[name] = {
            "file": os.path.basename(dst),
            "bbox": [round(float(v), 3) for v in b],
            "min": [round(float(v), 3) for v in m.bounds[0]],
            "max": [round(float(v), 3) for v in m.bounds[1]],
            "watertight": bool(m.is_watertight),
            "watertight_reload": bool(trimesh.load(dst).is_watertight),
            "volume_mm3": round(float(m.volume), 1),
        }
        print(f"  COPY {name:10s} ← stl_v17/{src}  {meta[name]['bbox']}")
    # 3MF корпуса тоже копируем (если есть)
    for name in ("body_L", "body_R", "foot", "keycap_v17"):
        try:
            shutil.copy2(os.path.join(STL_V17, name + ".3mf"),
                         os.path.join(STL_DIR, name + ".3mf"))
        except FileNotFoundError:
            pass
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
    print("Букифон v0.4 — панель 380 × 210 × 3 (точная Lapka-42, ±18°)")
    print("=" * 78)
    panel_L, panel_R = build_panels()
    meta = {}
    meta["panel_L"] = export_panel("panel_L", panel_L)
    meta["panel_R"] = export_panel("panel_R", panel_R)
    meta.update(copy_body_parts())
    inst = build_instances()
    with open(ASSEMBLY_JSON, "w") as f:
        json.dump({"parts": meta, "instances": inst}, f, indent=1)
    # 3MF сборки
    placed = []
    for item in inst:
        m = trimesh.load(os.path.join(STL_DIR, item["file"]))
        m.apply_translation(item["pos"])
        placed.append(m)
    export_3mf(trimesh.util.concatenate(placed),
               os.path.join(STL_DIR, "bukifon_v04_assembly.3mf"))
    print(f"  assembly_v04.json: {len(inst)} экземпляров")
    try:
        import fitcheck_v04
        fitcheck_v04.run({"panel_L": panel_L, "panel_R": panel_R}, meta, inst)
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("!! fit_check v0.4 не записан")
    print("\nГотово за %.1f c" % (time.time() - t0))


if __name__ == "__main__":
    main()
