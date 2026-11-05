"""Букифон v0.5 — три варианта корпуса (A flat / B wedge 8° / C wedge 12° + батарея).

Панель во всех вариантах — ОДНА И ТА ЖЕ, строго из spec/panel-spec-v0.4.json:
плоская деталь 380×210×3, разрез 193+190 мм с шипом/пазом (копии из stl_v04).
Меняется только корпус: наклон верхней плоскости, высоты, батарейный отсек,
подставка и кабельный канал.

Координаты:
  X вправо 0…380; Y от задней кромки к игроку 0…210; Z вверх от стола.
Наклон: панель повёрнута вокруг оси X на угол α (задняя кромка выше передней).

Генератор: mechanical/generator/case_v05.py
"""
from __future__ import annotations

import math
import os

import params_v04 as P04
import params_v17 as P17

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STL_V04 = os.path.join(ROOT, "mechanical", "stl_v04")

# --- общие габариты корпуса (в плане — как v0.4) ---------------------------
W = P04.PANEL_W            # 380
D = P04.PANEL_H            # 210
R_OUT = P04.R_OUT          # 10
WALL = P04.WALL            # 2.5
FLOOR_T = P04.FLOOR_T      # 3
R_CAV = P04.R_CAV
SEAM_X = P04.SEAM_X        # 190
PANEL_T = P04.PANEL_T      # 3

# --- варианты --------------------------------------------------------------
VARIANTS = {
    "A": dict(
        title="A — flat (как v0.4)",
        angle_deg=0.0,
        front_rim=60.0,          # высота стенки у передней кромки (дно=0)
        battery="space",         # батарея в ложементе, без крышки
        stand=False,
        cable_channel=False,
    ),
    "B": dict(
        title="B — wedge 8°",
        angle_deg=8.0,
        front_rim=40.0,          # высота стенки у передней кромки
        battery="space",
        stand=False,
        cable_channel=False,
    ),
    "C": dict(
        title="C — wedge 12° + battery bay + stand",
        angle_deg=12.0,
        front_rim=38.0,
        battery="bay",           # отсек с крышкой на винтах
        stand=True,
        cable_channel=True,
    ),
}
DEFAULT_VARIANT = "B"


def variant(name):
    v = dict(VARIANTS[name])
    a = math.radians(v["angle_deg"])
    v["name"] = name
    v["k"] = math.tan(a)                 # наклон верхней плоскости dz/dy
    v["sin"] = math.sin(a)
    v["cos"] = math.cos(a)
    # высота верхней кромки (плоскости панели) у передней/задней кромок
    v["rear_rim"] = v["front_rim"] + D * v["k"]
    # высота плоскости у центра (Y=105)
    v["center_rim"] = v["front_rim"] + (D / 2) * v["k"]
    # полная высота в сборе: спереди/сзади (панель +3 мм по нормали)
    v["h_front_total"] = v["front_rim"] + PANEL_T * v["cos"]
    v["h_rear_total"] = v["rear_rim"] + PANEL_T * v["cos"]
    return v


# --- посадочные места (X/Y — в координатах панели, как в v0.4) --------------
PANEL1_POSTS = P04.PANEL1_POSTS      # PANEL-2, 6 × M3 (координаты панели)
CORE_POSTS = P17.CORE_POSTS          # CORE-2, 4 × M3 (190×92 по центрам)
CORE_X0, CORE_X1 = P17.CORE_X0, P17.CORE_X1
CORE_Y0, CORE_Y1 = P17.CORE_Y0, P17.CORE_Y1
CORE_Z0, CORE_Z1 = 12.0, 13.6        # CORE-2 горизонтально, как в v0.4
CORE_W, CORE_D = P17.CORE_W, P17.CORE_D
CORE_COMP_TOP = 24.0

PANEL2_OFFSET = 8.0                  # PANEL-2 на 8 мм ниже панели по нормали
PANEL2_T = 1.6
PWR2_W, PWR2_D, PWR2_T = 90.0, 70.0, 1.6
PWR2_X0, PWR2_X1 = 145.0, 235.0
PWR2_Y0, PWR2_Y1 = 65.0, 135.0
PWR2_Z0 = FLOOR_T                    # PWR-2 на дне под CORE-2
PWR2_POSTS = [(152.0, 72.0), (228.0, 72.0), (152.0, 128.0), (228.0, 128.0)]

BAT_X = [302.0, 322.0]               # 2 × 18650 в ряд по X
BAT_D = 18.4
BAT_L = 65.0
BAT_Y0, BAT_Y1 = 56.0, 121.0
BAT_Z0 = FLOOR_T

# батарейный отсек варианта C (внутри корпуса, справа)
BAY_X0, BAY_X1 = 292.0, 372.0
BAY_Y0, BAY_Y1 = 60.0, 128.0
BAY_Z0, BAY_Z1 = 0.0, 24.0
BAY_WALL = 2.5
BAY_LID_W, BAY_LID_D, BAY_LID_T = 86.0, 74.0, 2.5
BAY_SCREW_D = 3.3
BAY_SCREWS = [(300.0, 68.0), (364.0, 68.0), (300.0, 120.0), (364.0, 120.0)]

# подставка варианта C (складная U-скоба, 2 × M3)
STAND_W, STAND_L, STAND_T = 124.0, 58.0, 6.0
STAND_PIVOT_D = 3.4
STAND_PIVOTS = [(110.0, -3.0, 18.0), (270.0, -3.0, 18.0)]   # X, Y, Z (крепление)

# кабельный канал варианта C (в задней стенке)
CABLE_CHANNEL_X = (150.0, 250.0)
CABLE_CHANNEL_Z = (FLOOR_T, FLOOR_T + 9.0)

# корпус: рёбра/вентиляция/ножки (как v0.4)
RIBS_X = [60.0, 130.0, 250.0, 320.0]
RIB_W = 3.0
RIB_H = 40.0
FEET = P17.FEET
FOOT_RECESS_D = P17.FOOT_RECESS_D
FOOT_RECESS_H = P17.FOOT_RECESS_H
USBC = P04.USBC
USBC_CABLE_SLOT = P17.USBC_CABLE_SLOT

# --- сборка экземпляров ----------------------------------------------------
def instances(v):
    inst = [
        {"name": "body_L", "file": "body_L.stl", "pos": [0, 0, 0], "rot": [0, 0, 0]},
        {"name": "body_R", "file": "body_R.stl", "pos": [0, 0, 0], "rot": [0, 0, 0]},
        # панель: плоская деталь, при сборке поворачивается вокруг X на -angle
        {"name": "panel_L", "file": "panel_L.stl", "pos": [0, 0, 0],
         "rot": [0, 0, 0], "panel": True},
        {"name": "panel_R", "file": "panel_R.stl", "pos": [0, 0, 0],
         "rot": [0, 0, 0], "panel": True},
    ]
    for i, (x, y) in enumerate(FEET):
        inst.append({"name": f"foot_{i+1}", "file": "foot.stl",
                     "pos": [x, y, 0.0], "rot": [0, 0, 0]})
    if v["battery"] == "bay":
        inst.append({"name": "battery_lid", "file": "battery_lid.stl",
                     "pos": [0, 0, 0], "rot": [0, 0, 0]})
    if v["stand"]:
        inst.append({"name": "stand", "file": "stand.stl",
                     "pos": [0, 0, 0], "rot": [0, 0, 0], "stowed": True})
    return inst
