"""render_v05_A.py — рендеры варианта A (flat 0°, как v0.4).

    /Applications/Blender.app/Contents/MacOS/Blender -b -P \
        mechanical/generator/render_v17.py -- --samples 36 --res 1600 1000

Выход: mechanical/preview_v17/*.png
  1. iso_top.png        — изометрия сверху (концепт-вид: 16 ручек, экран, 2×21 клавиша)
  2. front_panel.png    — вид на панель почти сверху
  3. exploded.png       — разнесённый вид
  4. panel_closeup.png  — крупно панель (клавиши/экран/фейдеры)
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None, n=None):
    if name not in ARGV:
        return default
    i = ARGV.index(name)
    return ARGV[i + 1] if n is None else ARGV[i + 1:i + 1 + n]


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import params_v04 as P  # noqa: E402
import params_v05 as PV  # noqa: E402

STL_DIR = os.path.join(ROOT, "mechanical", "stl_v05_A")
ASSEMBLY = os.path.join(HERE, "assembly_v05_A.json")
OUT = os.path.join(ROOT, "mechanical", "preview_v05_A")
SAMPLES = int(arg("--samples", "36"))
RES = arg("--res", ["1600", "1000"], 2)
RES_X, RES_Y = int(RES[0]), int(RES[1])
os.makedirs(OUT, exist_ok=True)

DATA = json.load(open(ASSEMBLY))
PARTS = DATA["parts"]
INSTANCES = DATA["instances"]
PANEL_M = DATA.get("panel_matrix")

_MATS = {}
_STL = {}
_EXTRA = {}


def mat(name, color, rough=0.45, metal=0.0, transmission=0.0, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if emission:
        b.inputs["Emission Color"].default_value = (*emission[0], 1.0)
        b.inputs["Emission Strength"].default_value = emission[1]
    return m


def materials():
    if _MATS:
        return _MATS
    _MATS.update({
        "BODY": mat("body_petg", (0.055, 0.06, 0.07), rough=0.42),
        "PANEL": mat("panel_petg", (0.045, 0.05, 0.06), rough=0.5),
        "KEY": mat("keycap", (0.80, 0.77, 0.70), rough=0.55),
        "KNOB": mat("knob", (0.02, 0.02, 0.025), rough=0.3),
        "GLASS": mat("screen", (0.005, 0.008, 0.014), rough=0.04,
                     transmission=0.15,
                     emission=((0.04, 0.10, 0.22), 0.30)),
        "METAL": mat("jack_metal", (0.45, 0.46, 0.48), rough=0.28, metal=0.9),
        "DARK": mat("dark", (0.015, 0.015, 0.018), rough=0.6),
        "TPU": mat("tpu", (0.03, 0.03, 0.035), rough=0.8),
        "FLOOR": mat("floor", (0.55, 0.56, 0.58), rough=0.6),
        "LABEL": mat("label", (0.75, 0.76, 0.78), rough=0.5,
                     emission=((0.6, 0.62, 0.65), 0.35)),
    })
    return _MATS


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _STL.clear()
    _EXTRA.clear()
    _MATS.clear()
    PANEL_ALT.clear()


def load_extra(path, key):
    if key not in _EXTRA:
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=path)
        src = [o for o in bpy.data.objects if o not in before][0]
        src.hide_render = True
        src.hide_viewport = True
        _EXTRA[key] = src
    src = _EXTRA[key]
    ob = src.copy()
    ob.data = src.data
    ob.hide_render = False
    ob.hide_viewport = False
    bpy.context.collection.objects.link(ob)
    ob.data.materials.clear()
    return ob


def load(part):
    if part not in _STL:
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=os.path.join(STL_DIR, part + ".stl"))
        src = [o for o in bpy.data.objects if o not in before][0]
        src.hide_render = True
        src.hide_viewport = True
        _STL[part] = src
    src = _STL[part]
    ob = src.copy()
    ob.data = src.data
    ob.hide_render = False
    ob.hide_viewport = False
    bpy.context.collection.objects.link(ob)
    ob.data.materials.clear()
    return ob


PANEL_ALT = []   # объекты, которые нужно повернуть вместе с панелью


def add_box(name, cx, cy, cz, sx, sy, sz, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    ob = bpy.context.object
    ob.name = name
    ob.scale = (sx, sy, sz)
    ob.data.materials.append(materials()[material])
    PANEL_ALT.append(ob)
    return ob


def add_cyl(name, cx, cy, z0, z1, r, material, sections=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=z1 - z0,
                                        vertices=sections,
                                        location=(cx, cy, (z0 + z1) / 2))
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(materials()[material])
    return ob


# ---------------------------------------------------------------------------
def trimesh_translation(x, y, z):
    from mathutils import Matrix
    return Matrix.Translation((x, y, z))


def _M():
    from mathutils import Matrix
    return Matrix(PANEL_M)


def build(explode=False):
    objs = []
    panel_objs = []
    for inst in INSTANCES:
        ob = load(inst["file"][:-4])
        ob.name = inst["name"]
        pos = Vector(inst["pos"])
        if explode:
            key = inst["file"][:-4]
            if key == "body_L":
                pos += Vector((-120, 0, 0))
            elif key == "body_R":
                pos += Vector((120, 0, 0))
            elif key == "panel_L":
                pos += Vector((-20, 0, 150))
            elif key == "panel_R":
                pos += Vector((20, 0, 150))
            elif key == "foot":
                pos += Vector((0, 0, -90))
        ob.location = pos
        if inst["name"].startswith("panel"):
            panel_objs.append(ob)
        ob.data.materials.clear()
        ob.data.materials.append(materials()["PANEL" if "panel" in inst["name"] else "BODY"])
        objs.append(ob)
    dz = 150.0 if explode else 0.0

    def dx_of(x):
        if not explode:
            return 0.0
        return -20.0 if x < P.SEAM_X else 20.0

    # ---- купленные компоненты (плейсхолдеры для визуализации) --------------
    # 16 ручек Ø14 × 12
    for i, k in enumerate(P.KNOBS):
        dx = dx_of(k["x"])
        add_cyl(f"knob_{i}", k["x"] + dx, k["y"], P.PANEL_Z1 + dz,
                P.PANEL_Z1 + P.KNOB_CAP_H + dz, P.KNOB_D / 2, "KNOB", 40)
        add_box(f"knob_ptr_{i}", k["x"] + dx, k["y"] + 4.5,
                P.PANEL_Z1 + P.KNOB_CAP_H + 0.15 + dz, 1.4, 6.0, 0.3, "LABEL")
    # 42 колпачка Choc v1.7 17.5 × 16.5 × 5.5 (печатная деталь keycap_v17),
    # центр (x,y) и поворот angle_deg — строго из JSON
    kc = os.path.join(STL_DIR, "keycap_v17.stl")
    for i, k in enumerate(P.KEYS):
        if os.path.exists(kc):
            ob = load_extra(kc, "keycap_src")
            ob.name = f"key_{i}"
            ob.location = (k["x"] + dx_of(k["x"]), k["y"], P.PANEL_Z1 + dz)
            ob.rotation_euler = (0, 0, math.radians(k["deg"]))
        else:
            ob = add_box(f"key_{i}", k["x"] + dx_of(k["x"]), k["y"],
                         P.PANEL_Z1 + P.KEYCAP_T / 2 + dz,
                         P.KEYCAP_W, P.KEYCAP_H, P.KEYCAP_T, "KEY")
            ob.rotation_euler = (0, 0, math.radians(k["deg"]))
        ob.rotation_euler = (0, 0, math.radians(k["deg"]))
        ob.data.materials.clear()
        ob.data.materials.append(materials()["KEY"])
        PANEL_ALT.append(ob)
    # экран: стекло 108 × 64.8 (активная область) + лёгкая подсветка UI
    s = P.SCREEN
    add_box("screen_glass", s["x"] + s["w"] / 2, s["y"] + s["h"] / 2,
            P.PANEL_Z0 + 0.85 + dz, s["w"] - 0.4, s["h"] - 0.4, 1.4, "GLASS")
    # 10 джеков: гайка Ø8.2 + тёмное гнездо
    for i, j in enumerate(P.JACKS):
        dj = dx_of(j["x"])
        add_cyl(f"jack_nut_{i}", j["x"] + dj, j["y"], P.PANEL_Z1 - 0.9 + dz,
                P.PANEL_Z1 + 0.35 + dz, P.JACK_NUT_D / 2, "METAL", 32)
        add_cyl(f"jack_hole_{i}", j["x"] + dj, j["y"], P.PANEL_Z1 + 0.3 + dz,
                P.PANEL_Z1 + 0.45 + dz, P.JACK_HOLE / 2 - 0.3, "DARK", 32)
    # 2 фейдера: колпачки 12 × 8 × 2.5 в среднем положении
    for i, f in enumerate(P.FADERS):
        add_box(f"fader_{i}", f["x"] + dx_of(f["x"]), f["y"],
                P.PANEL_Z1 + 1.6 + dz, 12.0, 8.0, 3.2, "DARK")
    # --- наклон панели: применяем матрицу к панельным объектам -----------
    M = _M()
    for ob in panel_objs + PANEL_ALT:
        ob.matrix_world = M @ ob.matrix_world
    if explode:
        for ob in panel_objs + PANEL_ALT:
            ob.matrix_world = trimesh_translation(0, 0, 190.0) @ ob.matrix_world
    return objs


# ---------------------------------------------------------------------------
def world(bg=0.32):
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    n = w.node_tree.nodes["Background"]
    n.inputs[0].default_value = (bg, bg, bg * 1.05, 1.0)
    n.inputs[1].default_value = 0.6
    bpy.context.scene.world = w


def light(name, loc, energy, size, rot):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = rot
    bpy.context.collection.objects.link(o)


def setup(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.8
    sc.render.image_settings.file_format = "PNG"
    sc.render.threads_mode = "FIXED"
    sc.render.threads = 8


def camera(loc, target, lens=60, ortho=None, roll=0.0, up="Y"):
    cd = bpy.data.cameras.new("c")
    cd.lens = lens
    cd.clip_start = 1.0
    cd.clip_end = 20000.0        # сцена 380×210, камера до 1.5 м
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    c = bpy.data.objects.new("c", cd)
    c.location = loc
    bpy.context.collection.objects.link(c)
    d = Vector(target) - c.location
    c.rotation_euler = d.to_track_quat("-Z", up).to_euler()
    if roll:
        c.rotation_euler.rotate_axis("Z", roll)
    bpy.context.scene.camera = c


def floor(z=-3.0, size=4000):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(190, 105, z))
    ob = bpy.context.object
    ob.name = "floor"
    ob.data.materials.append(materials()["FLOOR"])
    return ob


def three_point(center=(190, 105, 25)):
    c = Vector(center)
    light("key", c + Vector((-500, -650, 850)), 2400000, 620,
          (math.radians(48), 0, math.radians(-38)))
    light("fill", c + Vector((800, 200, 400)), 900000, 700,
          (math.radians(70), 0, math.radians(75)))
    light("rim", c + Vector((100, 800, 600)), 1400000, 600,
          (math.radians(60), 0, math.radians(185)))


def render(name):
    path = os.path.join(OUT, name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


# ---------------------------------------------------------------------------
def scene_side(name="side_profile.png"):
    """Профиль сбоку (ортокамера, строго вдоль -X): видно угол 8°."""
    from mathutils import Vector as V_
    import bpy as _b
    clear()
    setup(SAMPLES)
    world()
    build()
    floor()
    three_point()
    cd = _b.data.cameras.new("c")
    cd.type = "ORTHO"
    cd.ortho_scale = 250.0
    cd.clip_start = 1.0
    cd.clip_end = 20000.0
    cam = _b.data.objects.new("c", cd)
    _b.context.collection.objects.link(cam)
    cam.location = (1200.0, 105.0, 30.0)
    cam.rotation_euler = (math.pi / 2, 0.0, math.pi / 2)
    _b.context.scene.camera = cam
    render(name)


def scene_iso(explode=False, name="iso_top.png", cam=(-380, 1050, 760),
              target=(190, 100, 20), lens=62, explode_off=(0, 0, 0),
              ortho=None, roll=0.0, floor_off=None, up="Y"):
    clear()
    setup(SAMPLES)
    world()
    build(explode=explode)
    if floor_off is not None:
        floor(z=floor_off)
    else:
        floor()
    three_point()
    camera(Vector(cam) + Vector(explode_off), Vector(target), lens,
           ortho=ortho, roll=roll, up=up)
    render(name)


if __name__ == "__main__":
    only = arg("--only", None)

    def want(k):
        return only in (None, "all", k)

    if want("iso"):
        scene_iso(name="iso_top.png", cam=(-260, 900, 480),
                  target=(190, 105, 30), lens=62)
    if want("front"):
        scene_iso(name="front_panel.png", cam=(190, 760, 190),
                  target=(190, 105, 34), lens=70)
    if want("side"):
        scene_side()
    if want("exploded"):
        scene_iso(explode=True, name="exploded.png", cam=(-620, 1050, 780),
                  target=(190, 100, 120), lens=56)
    if want("top"):
        scene_iso(name="top_ortho.png", cam=(190, 105.0001, 2000),
                  target=(190, 105, 0), lens=50, ortho=430.0, roll=math.pi)
    print("ALL V0.5-A RENDERS DONE ->", OUT)
