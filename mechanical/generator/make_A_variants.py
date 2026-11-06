"""make_A_variants.py — вариант A (flat) с актуальными вырезами и опцией микрофона.

Создаёт:
  mechanical/stl_v05_A/       — body копии v0.4 (archive) + вырезы 11 задних
                               разъёмов + SD-слот + USB-C окно; панель канона.
  mechanical/stl_v05_A_mic/   — то же + порт MEMS/LED + звуковод/клипса/держатель.
B/B-light/C не трогаются.

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/make_A_variants.py
"""
from __future__ import annotations
import json, os, shutil, sys
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import case as C
import conn_cuts_v05 as CC
import mic_v05 as MIC
from case_v05 import _3mf, clean_mesh
import params_v05 as PV

ARCH = os.path.join(ROOT, "mechanical", "stl_v05_A")
SRC_PANEL = os.path.join(ROOT, "mechanical", "stl_v05_B")   # канон панели/ножки/колпачок
MIC_PARTS = ("mic_guide", "mic_clip_rear", "mic_holder_top")
LIGHT = os.path.join(ROOT, "mechanical", "stl_v05_B_light")


def build_dir(dst, mic):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    # тела v0.4 + вырезы
    bodies = {}
    for n in ("body_L", "body_R"):
        m = trimesh.load(os.path.join(ARCH, n + ".stl"))
        m = C.DIFF(m, CC.cutters(2.5))
        # USB-C окно (в v0.4 его не было): X 346…356, Y -1…3.5, Z 51…61
        m = C.DIFF(m, [C.box(346.0, 356.0, -1.0, 3.5, 51.0, 61.0)])
        m = clean_mesh(m)
        bodies[n] = m
        m.export(os.path.join(dst, n + ".stl"))
        _3mf(m, os.path.join(dst, n + ".3mf"))
        rt = trimesh.load(os.path.join(dst, n + ".stl"))
        print(f"  {n}: V={m.volume/1000:.1f} cm3 watertight={m.is_watertight}/{rt.is_watertight}")
    for part in ("panel_L", "panel_R", "foot", "keycap_v17"):
        for ext in (".stl", ".3mf"):
            shutil.copy2(os.path.join(SRC_PANEL, part + ext), os.path.join(dst, part + ext))
    if mic:
        for side in ("L", "R"):
            fn = os.path.join(dst, f"panel_{side}.stl")
            m = trimesh.load(fn)
            out = MIC.panel_with_mic(m)
            out.export(fn)
            print(f"  panel_{side}+mic: watertight={out.is_watertight}/"
                  f"{trimesh.load(fn).is_watertight}")
        for part in MIC_PARTS:
            for ext in (".stl", ".3mf", ".step"):
                s = os.path.join(LIGHT, part + ext)
                if os.path.exists(s):
                    shutil.copy2(s, os.path.join(dst, part + ext))
    # assembly json
    aj = json.load(open(os.path.join(HERE, "assembly_v05_A.json")))
    parts = aj["parts"]
    for n, m in bodies.items():
        parts[n].update(dict(volume_mm3=round(float(m.volume), 1),
                             watertight=bool(m.is_watertight),
                             watertight_reload=bool(trimesh.load(
                                 os.path.join(dst, n + ".stl")).is_watertight)))
    if mic:
        for side in ("L", "R"):
            m = trimesh.load(os.path.join(dst, f"panel_{side}.stl"))
            parts[f"panel_{side}"].update(dict(
                volume_mm3=round(float(m.volume), 1),
                watertight=bool(m.is_watertight),
                watertight_reload=bool(m.is_watertight)))
        light = json.load(open(os.path.join(HERE, "assembly_v05_B_light.json")))
        for part in MIC_PARTS:
            parts[part] = dict(light["parts"][part])
        inst = aj["instances"]
        inst.append({"name": "panel_mic_guide", "file": "mic_guide.stl",
                     "pos": [0, 0, 0], "rot": [0, 0, 0], "panel": True, "mic": True})
        inst.append({"name": "mic_clip_rear", "file": "mic_clip_rear.stl",
                     "pos": [60, -300, 0], "rot": [0, 0, 0], "mic": True})
        inst.append({"name": "mic_holder_top", "file": "mic_holder_top.stl",
                     "pos": [130, -300, 0], "rot": [0, 0, 0], "mic": True})
        aj["mic"] = {"port": MIC.PORT, "foam": MIC.FOAM, "mems": MIC.MEMS,
                     "led": MIC.LED, "socket": MIC.SOCKET_HOLE,
                     "clamp_gap": MIC.CLAMP_GAP, "variant": "A (flat) + mic"}
    suffix = "_mic" if mic else ""
    out_json = os.path.join(HERE, f"assembly_v05_A{suffix}.json")
    json.dump(aj, open(out_json, "w"), indent=1, ensure_ascii=False)
    # 3MF-сборка
    placed = []
    for item in aj["instances"]:
        m = trimesh.load(os.path.join(dst, item["file"]))
        m.apply_translation(item["pos"])
        placed.append(m)
    _3mf(trimesh.util.concatenate(placed),
         os.path.join(dst, f"bukifon_v05_A{suffix}_assembly.3mf"))
    print("  assembly:", os.path.basename(out_json))


def main():
    print("=== A (flat) + вырезы разъёмов")
    build_dir(os.path.join(ROOT, "mechanical", "stl_v05_A"), mic=False)
    print("=== A_mic (flat) + вырезы + порт микрофона")
    build_dir(os.path.join(ROOT, "mechanical", "stl_v05_A_mic"), mic=True)


if __name__ == "__main__":
    main()
