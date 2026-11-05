# -*- coding: utf-8 -*-
"""Букифон v1.8 — рендеры сборки (Blender headless).

Импортирует STL v1.8, ставит панели на Z=57, добавляет ручки/колпачки/джеки/
экран (из spec JSON), рендерит: вид 3/4, сверху, спереди, взрыв-схему.

Запуск: /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/v1_8_render.py
"""
import bpy  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402

ROOT = "<repo>"
STL = os.path.join(ROOT, "mechanical", "stl_v18")
OUT = os.path.join(ROOT, "renders", "v1_8")
os.makedirs(OUT, exist_ok=True)
SPEC = json.load(open(os.path.join(ROOT, "spec", "panel-spec-v1.8.json")))
PW, PH = SPEC["panel"]["w"], SPEC["panel"]["h"]
Z_PANEL_TOP = 60.0
Y_MAX = PH  # Y вниз в спеке → в Blender Y вверх: y_b = PH − y_spec


def yb(y):
    return PH - y


# ---- сцена -----------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1100
scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.06, 0.065, 0.07, 1.0)
bg.inputs[1].default_value = 1.0

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.location = (520, -420, 480)
cam.rotation_euler = (math.radians(63), 0, math.radians(40))
scene.collection.objects.link(cam)
scene.camera = cam
bpy.ops.object.light_add(type="SUN", location=(300, -200, 600))
sun = bpy.context.object
sun.data.energy = 3.2
sun.data.angle = math.radians(12)
sun.rotation_euler = (math.radians(35), math.radians(8), math.radians(30))
bpy.ops.object.light_add(type="AREA", location=(0, 300, 500))
bpy.context.object.data.energy = 80000
bpy.context.object.data.size = 500

mats = {}


def mat(name, color, rough=0.55, metal=0.0, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metal
    if emit:
        e = m.node_tree.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*emit, 1.0)
        e.inputs["Strength"].default_value = 2.5
        m.node_tree.links.new(e.outputs[0], m.node_tree.nodes["Material Output"].inputs[0])
    mats[name] = m
    return m


mat("body", (0.13, 0.135, 0.15), 0.6)
mat("panel", (0.16, 0.165, 0.18), 0.5)
mat("knob", (0.07, 0.072, 0.08), 0.35)
mat("cap", (0.78, 0.76, 0.70), 0.5)
mat("jack", (0.75, 0.72, 0.62), 0.3, 0.8)
mat("screen", (0.02, 0.05, 0.03), 0.2, emit=(0.25, 0.75, 0.45))
mat("accent", (0.85, 0.30, 0.12), 0.4)


def import_stl(path, m, loc=(0, 0, 0)):
    try:
        bpy.ops.wm.stl_import(filepath=path)
    except Exception:
        bpy.ops.import_mesh.stl(filepath=path)
    o = bpy.context.selected_objects[0]
    # STL в координатах спека (Y вниз): зеркалим относительно Y=0
    # и сдвигаем на +PH, чтобы координаты совпали с yb() = PH - y_spec
    o.scale = (1, -1, 1)
    bpy.ops.object.transform_apply(scale=True)
    o.location = (0, PH, loc[2])
    o.data.materials.append(m)
    return o


def add_box(name, size, loc, m, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rot_z))
    o = bpy.context.object
    o.name = name
    o.scale = size
    o.data.materials.append(m)
    return o


def add_cyl(name, d, h, loc, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=d / 2, depth=h, location=loc,
                                        rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    return o


# ---- корпус ----------------------------------------------------------------
groups = {"shell": [], "panel": [], "inner": []}
for side in ("L", "R"):
    o = import_stl(os.path.join(STL, f"bukifon_v1_8_shell_{side}.stl"), mats["body"])
    groups["shell"].append(o)
for p in ("L", "C", "R"):
    o = import_stl(os.path.join(STL, f"bukifon_v1_8_panel_{p}.stl"), mats["panel"],
                   loc=(0, 0, 57.0))
    groups["panel"].append(o)
o = import_stl(os.path.join(STL, "bukifon_v1_8_screen_carrier.stl"), mats["body"])
groups["inner"].append(o)

# ---- фурнитура из spec ------------------------------------------------------
for k in SPEC["knobs"]:
    add_cyl("knob", 14, 11, (k["x"], yb(k["y"]), Z_PANEL_TOP + 5.5), mats["knob"])
kb = SPEC["keyboard"]
for k in kb["keys_42"]:
    w, h = kb["keycap"]["w"], kb["keycap"]["h"]
    add_box("key", (w, 2.6, h), (k["x"], yb(k["y"]), Z_PANEL_TOP + 0.2), mats["cap"],
            math.radians(-k["angle_deg"]))
for j in SPEC["jacks"]:
    add_cyl("jack", 6, 1.2, (j["x"], yb(j["y"]), Z_PANEL_TOP + 0.1), mats["jack"])
s = SPEC["screen"]
scr = add_box("screen", (s["w"] - 2, s["h"] - 2, 0.6),
              (s["x"] + s["w"] / 2, yb(s["y"] + s["h"] / 2), Z_PANEL_TOP - 0.5),
              mats["screen"])
for f in SPEC["faders"]:
    add_box("fcap", (16, 1.6, 10), (f["x"], yb(140), Z_PANEL_TOP + 4), mats["knob"])

# ножки
for (x, y) in ((18, 25), (362, 25), (18, 185), (362, 185)):
    add_cyl("foot", 10, 3, (x, yb(y), -1.5), mats["knob"])

bpy.ops.object.select_all(action="DESELECT")


def render(name, cam_loc=None, cam_rot=None, fname=None):
    if cam_loc:
        cam.location = cam_loc
    if cam_rot:
        cam.rotation_euler = cam_rot
    scene.render.filepath = os.path.join(OUT, fname or (name + ".png"))
    bpy.ops.render.render(write_still=True)


# вид 3/4
render("hero")
# вид сверху (как эталон)
render("top", (PW / 2, yb(PH / 2), 620), (0, 0, 0), "top.png")
# вид спереди
render("front", (PW / 2, -460, 140), (math.radians(78), 0, 0), "front.png")

# взрыв-схема: панели +z, фурнитура +z
for o in groups["panel"]:
    o.location.z += 130
for o in groups["shell"]:
    o.location.z -= 60
render("exploded", (700, -520, 620), (math.radians(62), 0, math.radians(42)),
       "exploded.png")

print("рендеры:", OUT)
