"""make_mic_v05.py — встраивание микрофона в корпус v0.5-B-light (docs/71, D-94).

Делает:
 1. панели B-light получают порт Ø1.8 + поролоновую цековку + MEMS-углубление +
    LED MIC ON (исходные 83 выреза из JSON не меняются);
 2. печатает детали: звуковод, клипса на заднюю кромку, короткий держатель на
    верхнюю кромку — STL + 3MF + STEP (через FreeCAD CLI);
 3. добавляет детали в assembly_v05_B_light.json (звуковод идёт с панелью,
    клипса/держатель — отдельные принадлежности) и в сборку 3MF;
 4. печатает вес/время с микрофоном.

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/make_mic_v05.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import mic_v05 as MIC  # noqa: E402
import params_v05 as PV  # noqa: E402
import params_v04 as P04  # noqa: E402

STL_DIR = os.path.join(ROOT, "mechanical", "stl_v05_B_light")
ASSEMBLY = os.path.join(HERE, "assembly_v05_B_light.json")
BACKUP = os.path.join(STL_DIR, "mic_backup_orig")
FREECAD = "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"


def load_json():
    with open(ASSEMBLY) as f:
        return json.load(f)


def save_json(d):
    with open(ASSEMBLY, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)


def panel_with_mic(side):
    fn = os.path.join(STL_DIR, f"panel_{side}.stl")
    m = trimesh.load(fn)
    out = MIC.panel_with_mic(m)
    # сохранить оригинал один раз
    os.makedirs(BACKUP, exist_ok=True)
    b = os.path.join(BACKUP, f"panel_{side}.stl")
    if not os.path.exists(b):
        shutil.copy2(fn, b)
    out.export(fn)
    rt = trimesh.load(fn)
    return out, rt


def stl_to_step(stl_path, step_path):
    """STL → STEP через FreeCAD (меш → shape; для печатных деталей достаточно)."""
    if not os.path.exists(FREECAD):
        return False
    script = os.path.join("/tmp", "stl2step.py")
    with open(script, "w") as f:
        f.write(f"""import Mesh, Part
m = Mesh.Mesh({stl_path!r})
s = Part.Shape()
s.makeShapeFromMesh(m.Topology, 0.05)
s.exportStep({step_path!r})
""")
    try:
        r = subprocess.run([FREECAD, script], capture_output=True, timeout=240)
        return os.path.exists(step_path) and os.path.getsize(step_path) > 500
    except Exception:  # noqa: BLE001
        return False


def main():
    d = load_json()
    parts = d["parts"]
    # ---- 1. панели с портом ------------------------------------------------
    for side in ("L", "R"):
        mesh, rt = panel_with_mic(side)
        parts[f"panel_{side}"]["volume_mm3"] = round(float(mesh.volume), 1)
        parts[f"panel_{side}"]["watertight"] = bool(mesh.is_watertight)
        parts[f"panel_{side}"]["watertight_reload"] = bool(rt.is_watertight)
        print(f"panel_{side}: V={mesh.volume/1000:.2f} cm3 "
              f"watertight={mesh.is_watertight}/{rt.is_watertight}")

    # ---- 2. печатные детали микрофона -------------------------------------
    made = {}
    for name, fn in (("mic_guide", MIC.mic_guide()),
                     ("mic_clip_rear", MIC.mic_clip_rear()),
                     ("mic_holder_top", MIC.mic_holder_top())):
        from case_v05 import clean_mesh
        fn = clean_mesh(fn)
        stl = MIC.export_stl_3mf(fn, STL_DIR, name)
        rt = trimesh.load(stl)
        b = fn.bounds[1] - fn.bounds[0]
        parts[name] = {
            "file": name + ".stl",
            "bbox": [round(float(x), 3) for x in b],
            "min": [round(float(x), 3) for x in fn.bounds[0]],
            "max": [round(float(x), 3) for x in fn.bounds[1]],
            "watertight": bool(fn.is_watertight),
            "watertight_reload": bool(rt.is_watertight),
            "volume_mm3": round(float(fn.volume), 1),
        }
        made[name] = fn
        step = os.path.join(STL_DIR, name + ".step")
        ok = stl_to_step(stl, step)
        print(f"{name}: {b.round(1).tolist()} wt={fn.is_watertight} STEP={ok}")

    # ---- 3. instances + сборка --------------------------------------------
    inst = d["instances"]
    names = {i["name"] for i in inst}
    if "panel_mic_guide" not in names:
        inst.append({"name": "panel_mic_guide", "file": "mic_guide.stl",
                     "pos": [0, 0, 0], "rot": [0, 0, 0], "panel": True,
                     "mic": True})
    if "mic_clip_rear" not in names:
        inst.append({"name": "mic_clip_rear", "file": "mic_clip_rear.stl",
                     "pos": [60, -300, 0], "rot": [0, 0, 0], "mic": True})
    if "mic_holder_top" not in names:
        inst.append({"name": "mic_holder_top", "file": "mic_holder_top.stl",
                     "pos": [120, -300, 0], "rot": [0, 0, 0], "mic": True})
    d["mic"] = {"port": MIC.PORT, "foam": MIC.FOAM, "mems": MIC.MEMS,
                "led": MIC.LED, "socket": MIC.SOCKET_HOLE,
                "clamp_gap": MIC.CLAMP_GAP}
    save_json(d)

    # сборка 3MF (все детали, как в B-light, + микрофон)
    placed = []
    for item in inst:
        m = trimesh.load(os.path.join(STL_DIR, item["file"]))
        m.apply_translation(item["pos"])
        placed.append(m)
    try:
        from case_v05 import _3mf
        _3mf(trimesh.util.concatenate(placed),
             os.path.join(STL_DIR, "bukifon_v05_B_light_assembly.3mf"))
        print("assembly 3MF обновлена")
    except Exception as e:  # noqa: BLE001
        print("3MF:", e)

    # ---- 4. вес/время с микрофоном ----------------------------------------
    def eff(m):
        return m["volume_mm3"] / 1000.0
    dens = {"body": 1.27, "panel": 1.24, "keycap": 1.24, "foot": 1.21,
            "mic": 1.24, "battery": 1.27, "stand": 1.27}
    mass = time = 0.0
    for nm, m in parts.items():
        key = ("body" if nm.startswith("body") else
               "panel" if nm.startswith("panel") else
               "keycap" if nm.startswith("keycap") else
               "foot" if nm.startswith("foot") else "mic")
        cnt = {"keycap_v17": 42, "foot": 4}.get(nm, 1)
        v = eff(m) * cnt
        e = v * 0.36
        mass += e * dens[key]
        time += e / 12.0
    print(f"B-light+mic: eff={sum(eff(m) for m in parts.values()):.1f} cm3, "
          f"масса≈{mass:.0f} г (без батареи), время≈{time:.2f} ч")


if __name__ == "__main__":
    main()
