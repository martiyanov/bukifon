"""mic_v05.py — механика микрофона для корпуса v0.5-B-light (docs/71, D-94).

Панель: акустический порт Ø1.8 + поролоновая цековка Ø3.4×0.7, углубление под
MEMS/звуковод Ø5×1.2 снизу, отверстие LED MIC ON Ø1.6 (цековка Ø2.8×0.5).
Порт — на верхней (задней) кромке слева от экрана: центр (X=122, Y=5.5),
свободно от джеков (X≥125.8) и энкодеров (X≤111.4).

Печатные детали (2 варианта держателя гусиной шеи 3.5 мм + звуковод):
  mic_guide.stl      — звуковод: флянец Ø8 под панель, раструб Ø6→Ø7, канал
                       Ø2.0→Ø4.5, высота 8 мм (до PANEL-2);
  mic_clip_rear.stl  — клипса на заднюю кромку панели (зев 3.6 мм), гнездо
                       Ø6.8 × 8 мм под гусиную шею 3.5 мм;
  mic_holder_top.stl — короткий держатель на верхнюю кромку (зев 3.6 мм,
                       низкий профиль), гнездо Ø6.8 × 5 мм.

Единицы: мм. Панель в локальных координатах z 60…63 (как STL v0.4).
"""
from __future__ import annotations

import math
import os

import numpy as np
import trimesh

import case as C

# ---- параметры порта / LED -------------------------------------------------
PORT = dict(x=122.0, y=5.5, d=1.8)
FOAM = dict(d=3.4, depth=0.7)          # цековка под сетку/поролон (сверху)
MEMS = dict(d=5.0, depth=1.2)          # углубление под MEMS/звуковод (снизу)
LED = dict(x=116.0, y=10.5, d=1.6, recess_d=2.8, recess_depth=0.5)
PANEL_TOP, PANEL_BOT = 63.0, 60.0      # локальные z панели
PANEL2_OFFSET = 12.0                   # PANEL-2 ∥ панели: верх 12 мм ниже панели

# ---- держатели -------------------------------------------------------------
GOOSE_D = 3.5                          # гусиная шея 3.5 мм
SOCKET_D = 6.8                         # наружный Ø гнезда
SOCKET_HOLE = 3.6                      # отверстие под 3.5 мм
CLAMP_GAP = 3.6                        # зев под панель 3 мм (запас 0.6)
CLIP_SIZE = (18.0, 12.0, 12.0)        # клипса (X, Y, Z)
HOLDER_SIZE = (20.0, 14.0, 10.0)       # короткий держатель
GUIDE_H = PANEL2_OFFSET - 0.5          # 11.5 мм до PANEL-2 (зазор 0.5)


def _cyl(r, z0, z1, cx=0.0, cy=0.0, sections=32):
    return C.cyl_z(r, z0, z1, cx, cy, sections)


def panel_cuts():
    """Вырезы в панели (локальные координаты z 60…63)."""
    cuts = []
    # сквозной акустический порт Ø1.8
    cuts.append(_cyl(PORT["d"] / 2, PANEL_BOT - 1.0, PANEL_TOP + 1.0,
                     PORT["x"], PORT["y"]))
    # цековка под сетку/поролон снаружи (0.7 мм)
    cuts.append(_cyl(FOAM["d"] / 2, PANEL_TOP - FOAM["depth"],
                     PANEL_TOP + 0.1, PORT["x"], PORT["y"]))
    # углубление под MEMS/флянец звуковода снизу (1.2 мм)
    cuts.append(_cyl(MEMS["d"] / 2, PANEL_BOT - 0.1,
                     PANEL_BOT + MEMS["depth"], PORT["x"], PORT["y"]))
    # LED MIC ON: сквозное Ø1.6 + цековка Ø2.8×0.5
    cuts.append(_cyl(LED["d"] / 2, PANEL_BOT - 0.5, PANEL_TOP + 0.1,
                     LED["x"], LED["y"]))
    cuts.append(_cyl(LED["recess_d"] / 2, PANEL_TOP - LED["recess_depth"],
                     PANEL_TOP + 0.1, LED["x"], LED["y"]))
    return cuts


def panel_with_mic(panel_mesh):
    """Панель (v0.4 STL) + вырезы микрофона; исходные 83 выреза не тронуты."""
    m = C.DIFF(panel_mesh.copy(), panel_cuts())
    return C.clean_mesh(m) if hasattr(C, "clean_mesh") else m


# ---------------------------------------------------------------------------
def mic_guide():
    """Звуковод: флянец Ø8×1 под панелью + раструб до PANEL-2, канал 2→4.5."""
    z_top = PANEL_BOT
    z_bot = PANEL_BOT - GUIDE_H
    flange = _cyl(4.0, z_top - 1.0, z_top - 0.1, PORT["x"], PORT["y"])
    outer = C.cone_frustum(3.5, 3.0, z_bot, z_top - 1.0,
                           PORT["x"], PORT["y"], 40)
    body = trimesh.boolean.union([flange, outer], engine="manifold")
    inner = C.cone_frustum(2.2, 1.0, z_bot - 0.2, z_top - 0.9,
                           PORT["x"], PORT["y"], 40)
    return trimesh.boolean.difference([body, inner], engine="manifold")


def _rounded_box(cx, cy, cz, sx, sy, sz, r=1.0):
    try:
        poly = C._rrect(cx - sx / 2 + r, cx + sx / 2 - r,
                        cy - sy / 2 + r, cy + sy / 2 - r, r)
        return C.ext(poly, cz - sz / 2, cz + sz / 2)
    except Exception:  # noqa: BLE001
        return C.box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2,
                     cz - sz / 2, cz + sz / 2)


def mic_clip_rear():
    """Клипса на заднюю кромку панели: зев 3.6 мм, гнездо Ø6.8×8 (гусиная шея)."""
    W, D, H = 18.0, 8.0, 10.0
    gap = CLAMP_GAP
    # две губы C-образного зажима (толщина 2 мм)
    lower = C.box(-W / 2, W / 2, -D, D, 0.0, 2.0)
    upper = C.box(-W / 2, W / 2, -D, D, gap + 2.0, gap + 4.0)
    spine = C.box(-W / 2, W / 2, -D, -D + 2.0, 0.0, gap + 4.0)
    clamp = C.U([lower, upper, spine])
    # гнездо под гусиную шею (вертикальное), на верхней губе
    sock_out = _cyl(SOCKET_D / 2, gap + 4.0, gap + 4.0 + H - 4.0, 0.0, 0.0)
    sock_in = _cyl(SOCKET_HOLE / 2, gap + 4.0 - 0.2, gap + 4.0 + H - 3.8, 0.0, 0.0)
    body = C.U([clamp, sock_out])
    body = C.DIFF(body, [sock_in])
    return body


def mic_holder_top():
    """Короткий держатель на верхнюю кромку: низкий профиль, гнездо Ø6.8×5."""
    W, D = 20.0, 10.0
    gap = CLAMP_GAP
    base = C.box(-W / 2, W / 2, -D, D, 0.0, 2.5)
    lip = C.box(-W / 2, W / 2, D - 2.0, D, gap + 2.5, gap + 5.0)
    hook = C.box(-W / 2, W / 2, -D, -D + 2.0, 0.0, gap + 2.5)
    clamp = C.U([base, lip, hook])
    sock_out = _cyl(SOCKET_D / 2, gap + 2.5, gap + 2.5 + 5.0, 0.0, 0.0)
    sock_in = _cyl(SOCKET_HOLE / 2, gap + 2.3, gap + 2.5 + 4.8, 0.0, 0.0)
    return C.DIFF(C.U([clamp, sock_out]), [sock_in])


# ---------------------------------------------------------------------------
def export_stl_3mf(mesh, stl_dir, name):
    os.makedirs(stl_dir, exist_ok=True)
    mesh = mesh.copy()
    fn = os.path.join(stl_dir, name + ".stl")
    mesh.export(fn)
    try:
        from case_v05 import _3mf
        _3mf(mesh, os.path.join(stl_dir, name + ".3mf"))
    except Exception:  # noqa: BLE001
        pass
    return fn
