"""make_mic_variants.py — порт микрофона (D-94) для вариантов B и C.

Создаёт НОВЫЕ папки, не ломая текущие B/C:
  mechanical/stl_v05_B_mic/ (+ assembly_v05_B_mic.json)
  mechanical/stl_v05_C_mic/ (+ assembly_v05_C_mic.json)

В панелях режутся: порт Ø1.8 в (122.0, 5.5) + цековка Ø3.4×0.7, MEMS-углубление
Ø5×1.2 снизу, LED Ø1.6 в (116.0, 10.5) (см. mic_v05.py). B-light не трогаем —
он уже с микрофоном.

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/make_mic_variants.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import mic_v05 as MIC  # noqa: E402
from case_v05 import _3mf  # noqa: E402

LIGHT = os.path.join(ROOT, "mechanical", "stl_v05_B_light")
MIC_PARTS = ("mic_guide", "mic_clip_rear", "mic_holder_top")
VARIANTS = {
    "B": dict(src="stl_v05_B", acc=[60, -300, 0], spec="B (клин 8°) + mic"),
    "C": dict(src="stl_v05_C", acc=[60, -320, 0], spec="C (клин 12°) + mic"),
}


def main():
    for name, cfg in VARIANTS.items():
        src = os.path.join(ROOT, "mechanical", cfg["src"])
        dst = os.path.join(ROOT, "mechanical", f"stl_v05_{name}_mic")
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"\n=== {name}: {src} -> {dst}")

        # ---- панели с портом ------------------------------------------------
        for side in ("L", "R"):
            fn = os.path.join(dst, f"panel_{side}.stl")
            m = trimesh.load(fn)
            out = MIC.panel_with_mic(m)
            out.export(fn)
            rt = trimesh.load(fn)
            print(f"  panel_{side}: V={out.volume/1000:.2f} cm3 "
                  f"watertight={out.is_watertight}/{rt.is_watertight}")
            if out.is_watertight is False or rt.is_watertight is False:
                raise SystemExit("panel not watertight")

        # ---- mic-детали (копии из B-light) + STEP ---------------------------
        for part in MIC_PARTS:
            for ext in (".stl", ".3mf", ".step"):
                s = os.path.join(LIGHT, part + ext)
                if os.path.exists(s):
                    shutil.copy2(s, os.path.join(dst, part + ext))

        # ---- assembly json ---------------------------------------------------
        aj = json.load(open(os.path.join(HERE, f"assembly_v05_{name}.json")))
        parts = aj["parts"]
        for side in ("L", "R"):
            m = trimesh.load(os.path.join(dst, f"panel_{side}.stl"))
            parts[f"panel_{side}"]["volume_mm3"] = round(float(m.volume), 1)
            parts[f"panel_{side}"]["watertight"] = bool(m.is_watertight)
            parts[f"panel_{side}"]["watertight_reload"] = bool(m.is_watertight)
        light = json.load(open(os.path.join(HERE, "assembly_v05_B_light.json")))
        for part in MIC_PARTS:
            parts[part] = dict(light["parts"][part])
        inst = aj["instances"]
        inst.append({"name": "panel_mic_guide", "file": "mic_guide.stl",
                     "pos": [0, 0, 0], "rot": [0, 0, 0], "panel": True,
                     "mic": True})
        inst.append({"name": "mic_clip_rear", "file": "mic_clip_rear.stl",
                     "pos": cfg["acc"], "rot": [0, 0, 0], "mic": True})
        inst.append({"name": "mic_holder_top", "file": "mic_holder_top.stl",
                     "pos": [cfg["acc"][0] + 70, cfg["acc"][1], 0],
                     "rot": [0, 0, 0], "mic": True})
        aj["mic"] = {"port": MIC.PORT, "foam": MIC.FOAM, "mems": MIC.MEMS,
                     "led": MIC.LED, "socket": MIC.SOCKET_HOLE,
                     "clamp_gap": MIC.CLAMP_GAP, "variant": cfg["spec"]}
        out_json = os.path.join(HERE, f"assembly_v05_{name}_mic.json")
        json.dump(aj, open(out_json, "w"), indent=1, ensure_ascii=False)
        print(f"  assembly: {os.path.basename(out_json)}")

        # ---- сборка 3MF ------------------------------------------------------
        placed = []
        for item in inst:
            m = trimesh.load(os.path.join(dst, item["file"]))
            m.apply_translation(item["pos"])
            placed.append(m)
        _3mf(trimesh.util.concatenate(placed),
             os.path.join(dst, f"bukifon_v05_{name}_mic_assembly.3mf"))
        print("  assembly 3MF ok")

        # ---- масса/время (та же модель, что B/C) ----------------------------
        def vol(n):
            return parts[n]["volume_mm3"] / 1000.0
        dens = {"body": 1.27, "panel": 1.24, "keycap": 1.24, "foot": 1.21,
                "mic": 1.24, "battery_lid": 1.27, "stand": 1.27}
        cnt = {"keycap_v17": 42, "foot": 4}
        eff = 0.36
        mass = time = 0.0
        solid = 0.0
        for nm, m in parts.items():
            key = ("body" if nm.startswith("body") else
                   "panel" if nm.startswith("panel") else
                   "keycap" if nm.startswith("keycap") else
                   "foot" if nm.startswith("foot") else
                   "battery_lid" if nm.startswith("battery") else
                   "stand" if nm.startswith("stand") else "mic")
            v = vol(nm) * cnt.get(nm, 1)
            solid += v
            mass += v * eff * dens[key]
            time += v * eff / 12.0
        print(f"  ≈{mass:.0f} г / ≈{time:.1f} ч (solid {solid:.0f} см³)")


if __name__ == "__main__":
    main()
