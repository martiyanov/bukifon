"""render_blender.py — рендеры Bukifon для структуры mechanical/preview/.

Запуск (Blender 5.x headless):
    /Applications/Blender.app/Contents/MacOS/Blender -b -P mechanical/generator/render_blender.py -- \
        --stl mechanical/stl --assembly mechanical/generator/assembly.json \
        --out mechanical/preview [--samples 48] [--res 1600 1000] [--quick]
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
    if n is None:
        return ARGV[i + 1]
    return ARGV[i + 1:i + 1 + n]


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STL_DIR = arg("--stl", os.path.join(ROOT, "mechanical", "stl"))
ASSEMBLY = arg("--assembly", os.path.join(HERE, "assembly.json"))
OUT = arg("--out", os.path.join(ROOT, "mechanical", "preview"))
SAMPLES = int(arg("--samples", "48"))
RES = arg("--res", ["1600", "1000"], 2)
QUICK = "--quick" in ARGV
if QUICK:
    SAMPLES = 8
RES_X, RES_Y = int(RES[0]), int(RES[1])
os.makedirs(OUT, exist_ok=True)

with open(ASSEMBLY) as f:
    DATA = json.load(f)
PARTS = DATA["parts"]
INSTANCES = DATA["instances"]


# ---------------------------------------------------------------------------
#  Материалы
# ---------------------------------------------------------------------------
def mat(name, color, rough=0.45, metal=0.0, transmission=0.0, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if transmission:
        bsdf.inputs["Transmission Weight"].default_value = transmission
        bsdf.inputs["IOR"].default_value = 1.5
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission[0], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission[1]
    return m


_MATS = {}


def materials():
    """Материалы создаются лениво: clear_scene() стирает данные Blender."""
    if _MATS:
        return _MATS
    _MATS.update({
        "PETG": mat("PETG_dark", (0.10, 0.115, 0.13), rough=0.42),
        "PANEL": mat("panel_pla", (0.055, 0.06, 0.07), rough=0.5),
        "DECK": mat("deck_pla", (0.16, 0.165, 0.18), rough=0.5),
        "TPU": mat("tpu_pad", (0.035, 0.035, 0.04), rough=0.75),
        "KNOB": mat("knob_clear", (0.75, 0.78, 0.8), rough=0.25, transmission=0.35),
        "CAP": mat("caps_light", (0.55, 0.57, 0.6), rough=0.5),
        "GUIDE": mat("light_guide", (0.9, 0.95, 1.0), rough=0.15, transmission=0.8,
                     emission=((1.0, 0.85, 0.6), 2.0)),
        "METAL": mat("rear_alu", (0.35, 0.36, 0.38), rough=0.35, metal=0.85),
        "LABEL": mat("label", (0.85, 0.88, 0.92), rough=0.6,
                     emission=((0.7, 0.75, 0.8), 0.6)),
        "FLOOR": mat("floor", (0.55, 0.56, 0.58), rough=0.6),
        "GLASS": mat("screen_glass", (0.004, 0.006, 0.012), rough=0.06,
                     emission=((0.06, 0.10, 0.16), 0.35)),
        "SCREEN": mat("screen_bezel", (0.03, 0.032, 0.036), rough=0.45),
    })
    return _MATS


MAT_BY_PART = {
    "bottom": "PETG", "panel_upper": "PANEL", "deck_plate": "DECK",
    "knob": "KNOB", "pad_cap": "TPU", "keycap": "CAP", "fader_cap": "DECK",
    "shoulder_cap": "CAP", "light_guide": "GUIDE", "dock_cradle": "METAL",
    "bay_hatch": "PETG", "rear_plate": "METAL", "grip_pad": "TPU",
    "seam_key": "PETG",
}


def material_for(part):
    mm = materials()
    for k, m in MAT_BY_PART.items():
        if part.startswith(k):
            return mm[m]
    return mm["PETG"]


# ---------------------------------------------------------------------------
#  Сцена
# ---------------------------------------------------------------------------
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _STL_CACHE.clear()
    _MATS.clear()


def load_stl(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    ob = new[0]
    ob.rotation_mode = "XYZ"
    return ob


_STL_CACHE = {}


def inst_object(part, name):
    if part not in _STL_CACHE:
        ob = load_stl(os.path.join(STL_DIR, part + ".stl"))
        ob.name = "src_" + part
        ob.hide_render = True
        ob.hide_viewport = True
        _STL_CACHE[part] = ob
    src = _STL_CACHE[part]
    ob = src.copy()
    ob.data = src.data
    ob.hide_render = False
    ob.hide_viewport = False
    ob.name = name
    bpy.context.collection.objects.link(ob)
    ob.data.materials.clear()
    ob.data.materials.append(material_for(part))
    return ob


def build_assembly(explode=False, variant="pads"):
    """Собирает объекты; explode=True — разносит узлы для взрыв-схемы."""
    objs = []
    for inst in INSTANCES:
        part = inst["file"][:-4]
        # вариант deck: в сборке только pads или только keys
        if part.startswith("deck_plate") and variant == "keys" and "_pads" in part:
            part = part.replace("_pads", "_keys")
        if part.startswith("deck_plate") and variant == "pads" and "_keys" in part:
            continue
        if part.startswith("keycap") and variant == "pads":
            continue
        if part.startswith("pad_cap") and variant == "keys":
            continue
        if part.startswith("fader_cap") and variant == "keys":
            continue
        ob = inst_object(part, inst["name"])
        ob.rotation_euler = [math.radians(a) for a in inst.get("rot", [0, 0, 0])]
        pos = Vector(inst["pos"])
        if explode:
            pos += explode_offset(part, inst["name"])
        ob.location = pos
        objs.append((part, ob))
    return objs


def explode_offset(part, name):
    if part.startswith("bottom_L"):
        return Vector((-70, 0, 0))
    if part.startswith("bottom_R"):
        return Vector((70, 0, 0))
    if part.startswith("panel_upper"):
        return Vector((0, 0, 90))
    if part.startswith("deck_plate"):
        return Vector((0, 0, 70))
    if part.startswith("knob"):
        return Vector((0, 0, 130))
    if part.startswith("pad_cap"):
        return Vector((0, 0, 45))
    if part.startswith("keycap"):
        return Vector((0, 0, 45))
    if part.startswith("fader_cap"):
        return Vector((0, 0, 55))
    if part.startswith("shoulder_cap"):
        return Vector((0, 0, 110))
    if part.startswith("light_guide"):
        return Vector((0, 0, 40))
    if part.startswith("dock_cradle"):
        return Vector((0, 0, 150))
    if part.startswith("bay_hatch"):
        return Vector((0, 0, -70))
    if part.startswith("rear_plate"):
        return Vector((0, -90, 0))
    if part.startswith("grip_pad"):
        return Vector((0, 0, -40))
    return Vector((0, 0, 0))


def add_screen(explode=False):
    """Купленный модуль экрана 85×50 (spec/10 §2.1): корпус + тёмное стекло."""
    mm = materials()
    dz = 60.0 if explode else 0.0
    bpy.ops.mesh.primitive_cube_add(size=1, location=(157.5, 37.0, 43.3 + dz))
    body = bpy.context.object
    body.scale = (85.0, 50.0, 5.0)
    body.name = "screen_module"
    body.data.materials.append(mm["SCREEN"])
    bpy.ops.mesh.primitive_cube_add(size=1, location=(157.5, 37.0, 45.6 + dz))
    glass = bpy.context.object
    glass.scale = (58.0, 44.0, 0.8)
    glass.name = "screen_glass"
    glass.data.materials.append(mm["GLASS"])
    return [body, glass]


def setup_world(bg=0.32):
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    bg_node = w.node_tree.nodes["Background"]
    bg_node.inputs[0].default_value = (bg, bg, bg * 1.15, 1.0)
    bg_node.inputs[1].default_value = 0.55
    bpy.context.scene.world = w


def add_light(name, kind, loc, energy, size=6.0, rot=(0, 0, 0)):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    if kind == "AREA":
        data.size = size
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    ob.rotation_euler = rot
    bpy.context.collection.objects.link(ob)
    return ob


def add_floor(z=-4.0, size=3000):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    floor = bpy.context.object
    floor.name = "floor"
    floor.data.materials.append(materials()["FLOOR"])
    return floor


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_camera(loc, target, lens=70.0):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = lens
    cam = bpy.data.objects.new("cam", cam_data)
    cam.location = loc
    bpy.context.collection.objects.link(cam)
    look_at(cam, target)
    bpy.context.scene.camera = cam
    return cam


def setup_render(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.9
    sc.render.image_settings.file_format = "PNG"
    sc.render.threads_mode = "FIXED"
    sc.render.threads = 8


def lights_three_point(center=(157.5, 72.5, 20)):
    c = Vector(center)
    add_light("key", "AREA", c + Vector((-380, -420, 560)), 1600000,
              size=460, rot=(math.radians(48), 0, math.radians(-38)))
    add_light("fill", "AREA", c + Vector((520, 120, 240)), 650000,
              size=520, rot=(math.radians(70), 0, math.radians(75)))
    add_light("rim", "AREA", c + Vector((60, 520, 380)), 900000,
              size=400, rot=(math.radians(60), 0, math.radians(185)))


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


def scene_iso(explode=False, name="iso_assembly.png", variant="pads",
              center=(157.5, 70.0, 22), cam=(90, 780, 560), lens=78):
    clear_scene()
    setup_render(SAMPLES)
    setup_world()
    build_assembly(explode=explode, variant=variant)
    add_screen(explode=explode)
    add_floor()
    lights_three_point(center)
    add_camera(Vector(cam), Vector(center), lens=lens)
    render_to(os.path.join(OUT, name))


def scene_top(name="front_panel.png"):
    """Вид спереди-сверху: панель как её видит игрок."""
    clear_scene()
    setup_render(SAMPLES)
    setup_world()
    build_assembly(variant="pads")
    add_screen()
    add_floor()
    lights_three_point((157.5, 72.5, 10))
    add_camera(Vector((157.5, 400, 830)), Vector((157.5, 68, 24)), lens=88)
    render_to(os.path.join(OUT, name))


def scene_rear(name="rear_connectors.png"):
    """Вид сзади: все разъёмы задней панели."""
    clear_scene()
    setup_render(SAMPLES)
    setup_world()
    build_assembly(variant="pads")
    add_screen()
    add_floor()
    lights_three_point((157.5, 72.5, 20))
    add_camera(Vector((157.5, -520, 130)), Vector((157.5, 10, 24)), lens=82)
    render_to(os.path.join(OUT, name))


def scene_keys(name="iso_assembly_keys.png"):
    """Изометрия с клавиатурным deck'ом."""
    clear_scene()
    setup_render(SAMPLES)
    setup_world()
    build_assembly(variant="keys")
    add_screen()
    add_floor()
    lights_three_point((157.5, 72.5, 20))
    add_camera(Vector((-560, 560, 470)), Vector((157.5, 72, 22)), lens=80)
    render_to(os.path.join(OUT, name))


def scene_parts(name="parts_all.png"):
    """Покомпонентный расклад: все STL в сетке с подписями."""
    clear_scene()
    setup_render(SAMPLES)
    setup_world(0.08)
    objs = []
    files = sorted(PARTS.keys())
    cols = 5
    gap = 30.0
    cell_w = 300.0
    for i, part in enumerate(files):
        ob = inst_object(part, "part_" + part)
        ob.location = (0, 0, 0)
        bpy.context.view_layer.update()
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        size = mx - mn
        row, col = divmod(i, cols)
        x = col * cell_w - (cols - 1) * cell_w / 2
        y = -row * 260.0 + 520.0
        ob.location = Vector((x - (mn.x + mx.x) / 2, y - (mn.y + mx.y) / 2, -mn.z))
        objs.append(ob)
        # подпись
        bpy.ops.object.text_add(location=(x, y - 105, 2))
        txt = bpy.context.object
        txt.data.body = part.replace("deck_plate_", "deck_")
        txt.data.size = 16
        txt.data.align_x = "CENTER"
        txt.data.align_y = "CENTER"
        txt.rotation_euler = (math.radians(90), 0, 0)
        txt.data.materials.append(materials()["LABEL"])
    add_floor(z=-1.0, size=4000)
    add_light("key", "AREA", (0, 120, 900), 420000, size=900,
              rot=(math.radians(15), 0, 0))
    add_light("fill", "AREA", (-900, -500, 500), 160000, size=800,
              rot=(math.radians(55), 0, math.radians(-50)))
    add_camera(Vector((0, 260, 980)), Vector((0, 40, 0)), lens=60)
    render_to(os.path.join(OUT, name))


def scene_bottom_grip(name="bottom_grip.png"):
    """Вид снизу-сзади: рукоятки, подушка R22, 4 канавки под пальцы, ножки."""
    clear_scene()
    setup_render(SAMPLES)
    setup_world()
    build_assembly(variant="pads")
    add_screen()
    c = (157.5, 72.5, 0)
    add_light("key", "AREA", (60, 420, -340), 1900000, size=520,
              rot=(math.radians(-60), 0, math.radians(15)))
    add_light("fill", "AREA", (-420, -120, -180), 420000, size=500,
              rot=(math.radians(-70), 0, math.radians(-70)))
    add_light("rim", "AREA", (420, 260, 220), 600000, size=420,
              rot=(math.radians(50), 0, math.radians(80)))
    add_camera(Vector((-90, 560, -430)), Vector((157.5, 88, 10)), lens=62)
    render_to(os.path.join(OUT, name))


def scene_deck_pad(name="deck_pad_closeup.png"):
    clear_scene()
    setup_render(SAMPLES)
    setup_world()
    build_assembly(variant="pads")
    add_screen()
    add_floor()
    lights_three_point((157.5, 100, 40))
    add_camera(Vector((300, 320, 240)), Vector((157.5, 105, 44)), lens=95)
    render_to(os.path.join(OUT, name))


def scene_deck_keys(name="deck_keys_closeup.png"):
    clear_scene()
    setup_render(SAMPLES)
    setup_world()
    build_assembly(variant="keys")
    add_screen()
    add_floor()
    lights_three_point((157.5, 100, 40))
    add_camera(Vector((300, 330, 250)), Vector((157.5, 103, 47)), lens=95)
    render_to(os.path.join(OUT, name))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    only = arg("--only", None)
    if only in (None, "all", "iso"):
        scene_iso()
    if only in (None, "all", "front"):
        scene_top()
    if only in (None, "all", "rear"):
        scene_rear()
    if only in (None, "all", "keys"):
        scene_keys()
    if only in (None, "all", "exploded"):
        scene_iso(explode=True, name="exploded.png",
                  cam=(720, 760, 640), lens=70)
    if only in (None, "all", "parts"):
        scene_parts()
    if only in (None, "all", "deck"):
        scene_deck_pad()
        scene_deck_keys()
    if only in (None, "all", "bottom"):
        scene_bottom_grip()
    print("ALL RENDERS DONE ->", OUT)
