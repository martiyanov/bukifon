"""Букифон v0.4 — канон панели 380 × 210 (точная Lapka-42, половины ±18°).

Все координаты — ТОЛЬКО из spec/panel-spec-v0.4.json.
Корпус (body_L/R, ножки, крепёж, разрез X=190) — без изменений от v1.7
(mechanical/generator/params_v17.py), см. case_v04.py.

Система координат JSON: origin — верхний левый угол панели, X вправо,
Y вниз (к игроку), угол положительный = по часовой на виде сверху.
Наша 3D-система: X вправо, Y от задней кромки к игроку, Z вверх — совпадает.

Генератор: mechanical/generator/case_v04.py
"""
from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPEC_JSON = os.path.join(ROOT, "spec", "panel-spec-v0.4.json")

_SPEC = json.load(open(SPEC_JSON))
_C = _SPEC["controls"]

PANEL_W = float(_SPEC["panel"]["width_mm"])       # 380
PANEL_H = float(_SPEC["panel"]["height_mm"])       # 210
PANEL_T = float(_SPEC["panel"]["front_panel_thickness_mm"])   # 3
TOTAL_H = float(_SPEC["panel"]["overall_depth_mm"])           # 63

# --- корпус/крепёж/разрез — те же, что в v1.7 ------------------------------
import params_v17 as P17  # noqa: E402

BODY_H = P17.BODY_H
WALL = P17.WALL
FLOOR_T = P17.FLOOR_T
R_OUT = P17.R_OUT
R_CAV = P17.R_CAV
SEAM_X = P17.SEAM_X
PANEL_Z0 = P17.PANEL_Z0
PANEL_Z1 = P17.PANEL_Z1
SEAM_TONGUE_T = P17.SEAM_TONGUE_T
SEAM_TONGUE_L = P17.SEAM_TONGUE_L
M3_INSERT_D = P17.M3_INSERT_D
M3_INSERT_DEPTH = P17.M3_INSERT_DEPTH
M3_CLEAR_D = P17.M3_CLEAR_D
M2_INSERT_D = P17.M2_INSERT_D
PANEL_SCREW_D = P17.PANEL_SCREW_D
PANEL_CSK_D = P17.PANEL_CSK_D
PANEL_CSK_T = P17.PANEL_CSK_T
PANEL_SCREWS = P17.PANEL_SCREWS
USBC = P17.USBC
SCREEN_LEDGE = P17.SCREEN_LEDGE
FADER_M25_HOLE = P17.FADER_M25_HOLE
FOOT_D = P17.FOOT_D
FOOT_H = P17.FOOT_H
FEET = P17.FEET

# --- клавиши: точная Lapka-42, половины ±18° -------------------------------
def _leaf(x):
    return x["leaf"] if "leaf" in x else x


_KL = _C["keyboard_left"]
_KR = _C["keyboard_right"]


def _keys(lst):
    out = []
    for k in lst:
        cx, cy = k["center_mm"]
        out.append({
            "id": k.get("id", ""),
            "x": float(cx), "y": float(cy),
            "deg": float(k.get("angle_deg", 0.0)),
            "w": float(k.get("size_mm", [17.5, 16.5])[0]),
            "h": float(k.get("size_mm", [17.5, 16.5])[1]),
            "half": k.get("half", ""),
        })
    return out


KEYS = _keys(_KL) + _keys(_KR)          # 42 записи
KEY_WIN = 14.0                           # окно Choc 14 × 14 (защёлки)
KEY_WIN_R = 0.6
KEYCAP_W, KEYCAP_H = 17.5, 16.5
KEYCAP_T = P17.KEYCAP_T                  # 5.5 (колпачок v1.7 без изменений)

# --- энкодеры ---------------------------------------------------------------
KNOBS = [{"x": float(e["center_mm"][0]), "y": float(e["center_mm"][1]),
          "d": 14.0, "id": e.get("id", "")}
         for e in (_C["encoders_left"] + _C["encoders_right"])]
KNOB_D = 14.0
KNOB_HOLE = 7.2
KNOB_NUT_D = 14.4
KNOB_NUT_DEPTH = 1.4
KNOB_CAP_H = P17.KNOB_CAP_H

# --- джеки ------------------------------------------------------------------
JACKS = [{"x": float(j["center_mm"][0]), "y": float(j["center_mm"][1]),
          "id": j.get("id", "")} for j in _C["jacks"]]
JACK_HOLE = 6.2
JACK_NUT_D = 8.2                          # нут заявлен Ø8.0 + 0.2 зазор
JACK_NUT_DEPTH = 1.5                      # цековка Ø8 × 1.5 (task-10)

# --- экран 5.0" -------------------------------------------------------------
_lcd = _C["lcd"]
SCR = _lcd["active_cutout"]
SCREEN = {"x": float(SCR["center_mm"][0] - SCR["opening_size_mm"][0] / 2),
          "y": float(SCR["center_mm"][1] - SCR["opening_size_mm"][1] / 2),
          "w": float(SCR["opening_size_mm"][0]),
          "h": float(SCR["opening_size_mm"][1]),
          "cx": float(SCR["center_mm"][0]),
          "cy": float(SCR["center_mm"][1])}
SCREEN_R = 2.0
SCREEN_M25_HOLE = 2.7
SCREEN_MODULE_W = float(_lcd["body_envelope"]["rear_envelope_size_mm"][0])  # 120.7
SCREEN_MODULE_H = float(_lcd["body_envelope"]["rear_envelope_size_mm"][1])  # 75.8
SCREEN_M25_POS = [(SCREEN["x"] - 4.0, SCREEN["y"] + 6.0),
                  (SCREEN["x"] + SCREEN["w"] + 4.0, SCREEN["y"] + 6.0),
                  (SCREEN["x"] - 4.0, SCREEN["y"] + SCREEN["h"] - 6.0),
                  (SCREEN["x"] + SCREEN["w"] + 4.0, SCREEN["y"] + SCREEN["h"] - 6.0)]

# --- фейдеры ----------------------------------------------------------------
FADERS = []
for f in _C["faders"]:
    slot = f["slot"]
    FADERS.append({
        "id": f.get("id", ""),
        "x": float(slot["center_mm"][0]),
        "y": float(slot["center_mm"][1]),
        "slot_w": float(slot["slot_size_mm"][0]),      # 2.5
        "slot_l": float(slot["slot_size_mm"][1]),      # 63
        "body_w": float(f["rear_envelope"]["rear_envelope_size_mm"][0]),  # 16
        "body_h": float(f["rear_envelope"]["rear_envelope_size_mm"][1]),  # 75
    })
FADER_SLOT_R = 1.25                        # скругление концов 2.5 × 63
FADER_M25_DX = 6.0                         # 4 × M2.5 на фейдер (в коробе 16×75)
FADER_M25_Y = [150.0 - 33.0, 150.0 + 33.0]

# --- панель: 4 × M3 по углам, USB-C на задней кромке ------------------------
# PANEL_SCREWS / USBC — из v1.7 без изменений (корпус/крепёж не меняются).

# --- сборочные узлы внутри (без изменений от v1.7) --------------------------
PANEL1_W, PANEL1_D = P17.PANEL1_W, P17.PANEL1_D
PANEL1_X0, PANEL1_X1 = P17.PANEL1_X0, P17.PANEL1_X1
PANEL1_Y0, PANEL1_Y1 = P17.PANEL1_Y0, P17.PANEL1_Y1
PANEL1_Z0, PANEL1_Z1 = P17.PANEL1_Z0, P17.PANEL1_Z1
PANEL1_T = P17.PANEL1_T
PANEL1_POSTS = P17.PANEL1_POSTS
CORE_X0, CORE_X1 = P17.CORE_X0, P17.CORE_X1
CORE_Y0, CORE_Y1 = P17.CORE_Y0, P17.CORE_Y1
CORE_Z0, CORE_Z1 = P17.CORE_Z0, P17.CORE_Z1
CORE_T = P17.CORE_T
BAT_X = P17.BAT_X
BAT_D = P17.BAT_D
BAT_Y0, BAT_Y1 = P17.BAT_Y0, P17.BAT_Y1
BAT_CRADLE_Z0 = P17.BAT_CRADLE_Z0
CORE_COMP_TOP = P17.CORE_COMP_TOP
