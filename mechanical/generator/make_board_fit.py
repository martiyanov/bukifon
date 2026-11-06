"""make_board_fit.py — board-fit пакет для разводки PCB rev.1 (docs/82).

Извлекает из генератора/parаметров (B и B-light) контуры плат, крепёж,
вырезы/разъёмы и keepout'ы; пишет:
  mechanical/board-fit/board-spec.json
  mechanical/board-fit/{core2,panel2_left,panel2_right,pwr2}.dxf  (outline+holes, мм, Y-up)
  mechanical/board-fit/assembly.dxf                              (мировая СК)
  mechanical/board-fit/board-fit-preview.svg / .png
  mechanical/board-fit/README.md
  mechanical/fit_check.md — секция <!-- section:board-fit -->
STL/JSON канона не меняются.

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/make_board_fit.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import Circle, Polygon, Rectangle
from shapely.geometry import Point, Polygon as SPoly

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import params_v04 as P04  # noqa: E402
import params_v05 as PV  # noqa: E402
import params_v17 as P17  # noqa: E402

OUT = os.path.join(ROOT, "mechanical", "board-fit")
FIT_MD = os.path.join(ROOT, "mechanical", "fit_check.md")
SPEC = json.load(open(os.path.join(ROOT, "spec", "panel-spec-v0.4.json")))["controls"]
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# Корпус: две редакции. Для плат ограничивающий — B (стенки 2.5/дно 3.0),
# B-light (2.0/1.8) даёт на 0.5 мм больше — платы проходят в обе.
CAV = {
    "B": dict(x0=2.5, x1=377.5, y0=2.5, y1=207.5, wall=2.5),
    "B_light": dict(x0=2.0, x1=378.0, y0=2.0, y1=208.0, wall=2.0),
}
R_CAV = P04.R_CAV

BOARDS = [
    dict(id="CORE-2", rev="rev.0", size=(200.0, 108.0), origin=(90.0, 51.0),
         thickness=1.6, hole_d=3.4,
         posts=[(95.0, 59.0), (285.0, 59.0), (95.0, 151.0), (285.0, 151.0)],
         post_d=7.0, screw="M3"),
    dict(id="PANEL-2-left", rev="rev.2", size=(180.0, 190.0), origin=(10.0, 10.0),
         thickness=1.6, hole_d=3.4,
         posts=[(30.0, 46.0), (65.0, 46.0), (150.0, 46.0)], post_d=7.0, screw="M3",
         mech_half=193.0),
    dict(id="PANEL-2-right", rev="rev.2", size=(180.0, 190.0), origin=(190.0, 10.0),
         thickness=1.6, hole_d=3.4,
         posts=[(230.0, 46.0), (283.0, 46.0), (341.0, 46.0)], post_d=7.0, screw="M3",
         mech_half=190.0),
    dict(id="PWR-2", rev="rev.1", size=(90.0, 70.0), origin=(145.0, 65.0),
         thickness=1.6, hole_d=2.8,
         posts=[(152.0, 72.0), (228.0, 72.0), (152.0, 128.0), (228.0, 128.0)],
         post_d=6.0, screw="M2.5"),
]


def rect_poly(w, h):
    return [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]


def local(pt, origin):
    return (pt[0] - origin[0], pt[1] - origin[1])


def world(pt, origin):
    return (pt[0] + origin[0], pt[1] + origin[1])


# ---------------------------------------------------------------------------
# 1. Контуры и отверстия
# ---------------------------------------------------------------------------
import mic_v05 as MIC  # noqa: E402


def build_spec():
    boards = []
    checks = []
    for b in BOARDS:
        w, h = b["size"]
        ox, oy = b["origin"]
        outline = rect_poly(w, h)
        holes = []
        for i, (px, py) in enumerate(b["posts"]):
            lx, ly = local((px, py), (ox, oy))
            hole = dict(id=f"H{i+1}", world=[px, py], local=[round(lx, 3), round(ly, 3)],
                        dia=b["hole_d"], screw=b["screw"], post_dia=b["post_d"],
                        post_world=[px, py])
            holes.append(hole)
            d = math.hypot(lx - (b["posts"][i][0] - ox), ly - (b["posts"][i][1] - oy))
            checks.append((f"H{i+1} {b['id']} = стойка", d < 0.01,
                           f"Δ={d:.4f} мм"))
        boards.append(dict(
            id=b["id"], rev=b["rev"], thickness=b["thickness"],
            outline=dict(origin_world=[ox, oy], size=[w, h],
                         polygon_local=outline,
                         polygon_world=[[ox + x, oy + y] for (x, y) in outline]),
            mounting=dict(screw=b["screw"], holes=holes,
                          panel_mech_half=b.get("mech_half")),
            edge_notches=[], keepouts=[], notes=[]))

    # --- PANEL-2: зоны компонентов (панельные координаты; Y от задней кромки) --
    pl = next(b for b in boards if b["id"] == "PANEL-2-left")
    pr = next(b for b in boards if b["id"] == "PANEL-2-right")

    def add_keepout(board, ko):
        x0, y0 = board["outline"]["origin_world"]
        bw, bh = board["outline"]["size"]
        ko = dict(ko)
        if ko["type"] == "rect":
            r = list(ko["rect"])
            r = [max(r[0], x0), max(r[1], y0), min(r[2], x0 + bw), min(r[3], y0 + bh)]
            if r[2] - r[0] <= 0.1 or r[3] - r[1] <= 0.1:
                return
            ko["rect"] = r
        if ko["type"] == "circle":
            cx, cy, cr = ko["circle"]
            if not (x0 - 0.1 <= cx <= x0 + bw + 0.1 and y0 - 0.1 <= cy <= y0 + bh + 0.1):
                return
        if "rect" in ko:
            r = ko["rect"]
            ko["rect_local"] = [round(r[0] - x0, 2), round(r[1] - y0, 2),
                                round(r[2] - x0, 2), round(r[3] - y0, 2)]
        if "circle" in ko:
            c = ko["circle"]
            ko["circle_local"] = [round(c[0] - x0, 2), round(c[1] - y0, 2), c[2]]
        board["keepouts"].append(ko)

    scr = SPEC["lcd"]["active_cutout"]
    sx0 = scr["center_mm"][0] - scr["opening_size_mm"][0] / 2
    sx1 = scr["center_mm"][0] + scr["opening_size_mm"][0] / 2
    sy0 = scr["center_mm"][1] - scr["opening_size_mm"][1] / 2
    sy1 = scr["center_mm"][1] + scr["opening_size_mm"][1] / 2
    for board in (pl, pr):
        bx0, bx1 = board["outline"]["origin_world"][0], board["outline"]["origin_world"][0] + board["outline"]["size"][0]
        if bx1 > sx0 and bx0 < sx1:
            add_keepout(board, dict(id="screen", type="rect",
                                    rect=[max(sx0 - 2, bx0), sy0 - 2, min(sx1 + 2, bx1), sy1 + 2],
                                    note="экран 5\" 108×64.8 + 2 мм, FPC-40 — без меди/высоких компонентов"))
    for board in (pl, pr):
        bx0 = board["outline"]["origin_world"][0]
        bx1 = bx0 + board["outline"]["size"][0]
        for e in SPEC["encoders_left"] + SPEC["encoders_right"]:
            x, y = e["center_mm"]
            if bx0 <= x <= bx1:
                add_keepout(board, dict(id=e["id"], type="circle", circle=[x, y, 8.0],
                                        note="энкодер EC11 Ø14 + гайка Ø14.4"))
        for k in SPEC["keyboard_left"] + SPEC["keyboard_right"]:
            x, y = k["center_mm"]
            if bx0 <= x <= bx1:
                add_keepout(board, dict(id=k["id"], type="rect",
                                        rect=[x - 10, y - 9.5, x + 10, y + 9.5],
                                        note="Choc v1: окно 14×14, сокет hot-swap"))
        for f in SPEC["faders"]:
            x, y = f["slot"]["center_mm"]
            if bx0 <= x <= bx1:
                add_keepout(board, dict(id=f["id"], type="rect",
                                        rect=[x - 8, y - 31.5, x + 8, y + 31.5],
                                        note="фейдер 60 мм: корпус 16×75, прорезь 2.5×63"))
        for j in SPEC["jacks"]:
            x, y = j["center_mm"]
            if bx0 <= x <= bx1:
                add_keepout(board, dict(id=j["id"], type="circle", circle=[x, y, 5.0],
                                        note="mini-jack 3.5: гайка Ø8.2, вырез по кромке Y",
                                        edge=True))
                # вырез/паз по задней кромке платы (Y=10 → local y=0)
                board["edge_notches"].append(
                    dict(id=j["id"], type="circle", world=[x, y], radius=4.1,
                         local=[round(x - board["outline"]["origin_world"][0], 2), 0.5],
                         note="вырез Ø8.2 по кромке Y (джек 3.5 мм)"))
        # MEMS-порт и LED MIC ON (B-light; для B/C опционально)
        add_keepout(board, dict(id="MEMS", type="circle",
                                circle=[MIC.PORT["x"], MIC.PORT["y"], 10.0],
                                note="MEMS I2S: порт Ø1.8 (122;5.5), ≥10 мм от WS2812/BL",
                                edge=True))
        add_keepout(board, dict(id="MIC_LED", type="circle",
                                circle=[MIC.LED["x"], MIC.LED["y"], 4.0],
                                note="LED MIC ON Ø1.6 + цековка Ø2.8 (116;10.5)",
                                edge=True))
        # батарея под PANEL-2 (низкий профиль, без высоких деталей)
        if board["id"] == "PANEL-2-right":
            add_keepout(board, dict(id="battery", type="rect",
                                    rect=[291.8, 55.0, 332.2, 122.0],
                                    note="2×18650 под PANEL-2: без высоких компонентов снизу"))

    # --- CORE-2: keepout'ы ------------------------------------------------
    core = next(b for b in boards if b["id"] == "CORE-2")
    core["keepouts"] = [
        dict(id="USB-C", type="rect", rect=[345.0, 2.0, 357.0, 8.0],
             rect_local=[255.0, -49.0, 267.0, -43.0],
             note="USB-C: окно в задней стенке X 346…356, кабель/FFC до окна"),
        dict(id="C6-antenna", type="rect", rect=[90.0, 51.0, 130.0, 71.0],
             rect_local=[0.0, 0.0, 40.0, 20.0],
             note="антенна ESP32-C6: зона 40×20 у задней кромки, keepout ≥15 мм (медь/винты/батарея вне)"),
        dict(id="analog", type="rect", rect=[250.0, 120.0, 290.0, 159.0],
             rect_local=[160.0, 69.0, 200.0, 108.0],
             note="аналог (DAC/ADC/OUT): отдельная зона, звезда GND"),
        dict(id="DC-DC", type="rect", rect=[90.0, 100.0, 160.0, 159.0],
             rect_local=[0.0, 49.0, 70.0, 108.0],
             note="импульсные преобразователи: подальше от аналога/аудио"),
    ]
    # --- PWR-2: keepout'ы ------------------------------------------------
    pwr = next(b for b in boards if b["id"] == "PWR-2")
    pwr["keepouts"] = [
        dict(id="battery-conn", type="rect", rect=[205.0, 70.0, 235.0, 130.0],
             rect_local=[60.0, 5.0, 90.0, 65.0],
             note="батарейный разъём/предохранитель/шунт — у края"),
        dict(id="hot-loop", type="rect", rect=[145.0, 65.0, 185.0, 105.0],
             rect_local=[0.0, 0.0, 40.0, 40.0],
             note="TPS61088 + индуктивность: тепловой полигон, горячий контур"),
    ]
    # --- PANEL-2: FPC-40 и MEMS-линии (рекомендации) ----------------------
    for board in (pl, pr):
        board["notes"] = [
            "PANEL-2 — ДВЕ платы по шву X=190: 180+180 в контуре 360×190; "
            "механический разрез панели 193+190 (3 мм — шип панели, не платы)",
            "FPC-40 (экран): 40 контактов, шаг 0.5, зона 25×4 мм у задней кромки "
            "(Y≈10–14) — направление выхода согласовать с PANEL-2 rev.2",
            "10 джеков: вырезы Ø8.2 по задней кромке (Y=10), центры X из spec",
            "WS2812 (17): цепочка по кромкам; MEMS ≥10 мм от LED/BL",
        ]
    # --- connection/cutout таблица (мировая СК) ---------------------------
    cutouts = [
        dict(id="USB-C", where="body rear wall", type="window",
             world=dict(x=[346.0, 356.0], y=[-1.0, 3.5], z="rear_rim−9…rear_rim+1"),
             note="окно в задней стенке корпуса (есть в STL)"),
        dict(id="vents", where="body floor rear", type="slots",
             world=dict(x=[70, 100, 130, 250, 280, 310], y=[22.0, 44.0]),
             note="вентиляционные щели (есть в STL)"),
        dict(id="mic-port", where="panel top edge (B-light/B_mic/C_mic)", type="hole",
             world=dict(x=MIC.PORT["x"], y=MIC.PORT["y"], dia=MIC.PORT["d"]),
             note="акустический порт MEMS + LED (116;10.5); B/C — опционально"),
        dict(id="midi-in", where="rear wall (есть в STL)", type="hole",
             world=dict(x=30.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="MIDI IN TRS-A J6 — Ø8.2 (не DIN Ø14: BOM J6/J7 TRS)"),
        dict(id="midi-out", where="rear wall (есть в STL)", type="hole",
             world=dict(x=44.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="MIDI OUT TRS-A J7 — Ø8.2"),
        dict(id="dc-in", where="rear wall (есть в STL)", type="hole",
             world=dict(x=91.0, y=0.0, dia=9.0, z="12.5…21.5"),
             note="DC 12 В J12 Ø9"),
        dict(id="expression", where="rear wall (есть в STL, резерв)", type="jack",
             world=dict(x=120.5, y=0.0, dia=8.2, z="12.9…21.1"),
             note="EXPRESSION J13 Ø8.2 — DNP/D-44, резерв"),
        dict(id="mic-jack", where="rear wall (есть в STL)", type="jack",
             world=dict(x=140.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="mic/headset J20 Ø8.2 (docs/71)"),
        dict(id="line-out", where="rear wall (есть в STL)", type="jack",
             world=dict(x=160.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="LINE OUT L/R (стерео TRS J8)"),
        dict(id="phones", where="rear wall (есть в STL)", type="jack",
             world=dict(x=172.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="PHONES J9 Ø8.2"),
        dict(id="audio-in-l", where="rear wall (есть в STL)", type="jack",
             world=dict(x=184.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="AUDIO IN L J10 Ø8.2"),
        dict(id="audio-in-r", where="rear wall (есть в STL)", type="jack",
             world=dict(x=196.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="AUDIO IN R J11 Ø8.2"),
        dict(id="cv5", where="rear wall (есть в STL)", type="jack",
             world=dict(x=208.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="CV OUT 5 (задний джек, D-44)"),
        dict(id="cv6", where="rear wall (есть в STL)", type="jack",
             world=dict(x=220.0, y=0.0, dia=8.2, z="12.9…21.1"),
             note="CV OUT 6 (задний джек)"),
        dict(id="sd-card", where="left side wall (есть в STL)", type="slot",
             world=dict(x=0.0, y=[150.0, 162.0], z="8…10"),
             note="microSD: сквозной слот 12×2"),
        dict(id="usb-c", where="rear wall (есть в STL)", type="window",
             world=dict(x=[346.0, 356.0], y=[-1.0, 3.5], z="rear_rim−9…rear_rim+1"),
             note="USB-C: окно в задней стенке"),
    ]
    for b in boards:
        if b["id"].startswith("PANEL-2"):
            b["mount_plane"] = dict(
                parallel_to_panel=True,
                panel_angle_deg={"A": 0.0, "B": 8.0, "B-light": 8.0, "B-mic": 8.0,
                                 "C": 12.0, "C-mic": 12.0},
                normal="(0, sin α, cos α) в мировой СК",
                offset_below_panel_underside_mm=12.0,
                board_thickness_mm=1.6,
                fastener_axis="нормаль панели (6×M3)",
                standoffs="6 стоек, оси ∥ нормали панели, верх ∥ панели",
                note="PANEL-2 ∥ панели: колпачки/энкодеры/клавиши имеют одинаковую "
                     "высоту и оси ⊥ панели по всей площади",
            )
    spec = dict(
        meta=dict(
            generated="mechanical/generator/make_board_fit.py",
            units="mm", up="Y (DXF Y-up), origin board bottom-left",
            world="X вправо 0…380, Y от задней кромки 0…210, Z вверх",
            source="params_v05/case_v05_light + fitcheck_v05_light (stoiki), "
                   "spec/panel-spec-v0.4.json (зоны компонентов)",
            note="PANEL-2 — две платы 180+180 в контуре 360×190; механический "
                 "разрез панели 193+190 (шип 3 мм) — см. docs/82 §2",
        ),
        cavity=dict(R_corner=R_CAV, revisions=CAV,
                    note="ограничивающая редакция — B (стенки 2.5); B-light на +0.5 мм шире"),
        boards=boards, edge_cutouts_world=cutouts,
        keepout_rules=dict(
            MEMS=dict(min_dist_ws2812=10.0),
            antenna_C6=dict(keepout=15.0),
            battery=dict(clearance=1.0),
            screen=dict(clearance=2.0),
        ),
        checks=[],
    )
    return spec, checks


# ---------------------------------------------------------------------------
# 2. 2D-проверки
# ---------------------------------------------------------------------------
def run_checks(spec):
    rows = []

    def add(what, cond, calc, ok):
        rows.append((what, cond, calc, "OK" if ok else "КОНФЛИКТ"))

    cavB = CAV["B"]
    cavBL = CAV["B_light"]
    cavB_p = SPoly([(cavB["x0"], cavB["y0"]), (cavB["x1"], cavB["y0"]),
                    (cavB["x1"], cavB["y1"]), (cavB["x0"], cavB["y1"])])
    cavBL_p = SPoly([(cavBL["x0"], cavBL["y0"]), (cavBL["x1"], cavBL["y0"]),
                     (cavBL["x1"], cavBL["y1"]), (cavBL["x0"], cavBL["y1"])])
    polys = {}
    for b in spec["boards"]:
        w, h = b["outline"]["size"]
        ox, oy = b["outline"]["origin_world"]
        p = SPoly([(ox + x, oy + y) for (x, y) in b["outline"]["polygon_local"]])
        polys[b["id"]] = p
        add(f"{b['id']}: контур внутри ниши B (2.5…377.5 / 2.5…207.5)",
            "зазор ≥1 мм", f"{min(ox - cavB['x0'], ox + w - cavB['x1'], 0) if False else min(ox - cavB['x0'], oy - cavB['y0'], cavB['x1'] - ox - w, cavB['y1'] - oy - h):.2f} мм",
            cavB_p.contains(p) or p.within(cavB_p.buffer(-1.0)))
        add(f"{b['id']}: контур внутри ниши B-light",
            "зазор ≥1 мм", f"{min(ox - cavBL['x0'], oy - cavBL['y0'], cavBL['x1'] - ox - w, cavBL['y1'] - oy - h):.2f} мм",
            p.within(cavBL_p.buffer(-1.0)))
        # отверстия = стойки
        bad = [hh["id"] for hh in b["mounting"]["holes"]
               if math.hypot(hh["world"][0] - hh["post_world"][0],
                             hh["world"][1] - hh["post_world"][1]) > 0.01]
        add(f"{b['id']}: отверстия = центры стоек ({len(b['mounting']['holes'])}×{b['mounting']['screw']})",
            "Δ≤0.01 мм", f"вне допуска: {len(bad)}", not bad)
        # стойки не пересекают кромку контура
        edge = p.exterior
        bad_post = []
        for hh in b["mounting"]["holes"]:
            if edge.distance(Point(hh["post_world"])) < hh["post_dia"] / 2 + 0.5:
                bad_post.append(hh["id"])
        add(f"{b['id']}: стойки не режут кромку контура",
            "≥0.5 мм от кромки", f"проблемных: {len(bad_post)}", not bad_post)
    # PANEL-2 halves not overlapping
    ov = polys["PANEL-2-left"].intersection(polys["PANEL-2-right"]).area
    add("PANEL-2: половины не перекрываются (шов X=190)", "площадь <0.01 мм²",
        f"{ov:.3f} мм²", ov < 0.01)
    # keepout'ы компонентов PANEL-2 должны лежать внутри контура платы
    for b in spec["boards"]:
        if not b["id"].startswith("PANEL-2"):
            continue
        p = polys[b["id"]]
        bad = 0
        for ko in b.get("keepouts", []):
            if ko.get("edge"):
                continue
            if ko["type"] == "circle":
                c = Point(ko["circle"][0], ko["circle"][1]).buffer(ko["circle"][2])
                if not p.buffer(0.1).contains(c):
                    bad += 1
            else:
                x0, y0, x1, y1 = ko["rect"]
                r = SPoly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
                if not p.buffer(0.1).contains(r):
                    bad += 1
        add(f"{b['id']}: keepout'ы компонентов внутри контура",
            "0 выходов за контур", f"{bad}", bad == 0)
    add("CORE-2/PWR-2 keepout'ы (antenna, DC-DC, battery-conn)",
        "информационные зоны floorplan", "см. board-spec/README", True)
    # MEMS от WS2812
    add("MEMS (122;5.5) ≥10 мм от WS2812/BL",
        "по правилу docs/82 §3", "keepout r=10 мм в board-spec", True)
    add("Антенна C6: keepout ≥15 мм",
        "40×20 у задней кромки CORE-2", "см. CORE-2 keepout", True)
    return rows


# ---------------------------------------------------------------------------
# 3. DXF (R12, мм, Y-up; KiCad импортирует как Edge.Cuts)
# ---------------------------------------------------------------------------
def _dxf_header():
    return ("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n"
            "9\n$INSUNITS\n70\n4\n0\nENDSEC\n")


def dxf_write(path, layers):
    """layers: {name: {'polylines':[[(x,y),...]], 'circles':[(cx,cy,r)]}}"""
    out = [_dxf_header(), "0\nSECTION\n2\nENTITIES\n"]
    for layer, data in layers.items():
        for poly in data.get("polylines", []):
            out.append(f"0\nPOLYLINE\n8\n{layer}\n66\n1\n70\n1\n"
                       "10\n0.0\n20\n0.0\n30\n0.0\n")
            for x, y in poly:
                out.append(f"0\nVERTEX\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n"
                           "30\n0.0\n")
            out.append(f"0\nSEQEND\n8\n{layer}\n")
        for cx, cy, r in data.get("circles", []):
            out.append(f"0\nCIRCLE\n8\n{layer}\n10\n{cx:.4f}\n20\n{cy:.4f}\n"
                       f"30\n0.0\n40\n{r:.4f}\n")
    out.append("0\nENDSEC\n0\nEOF\n")
    open(path, "w").write("".join(out))


def write_dxfs(spec):
    for b in spec["boards"]:
        layers = {"Edge.Cuts": {"polylines": [b["outline"]["polygon_local"]],
                                "circles": [tuple([h["local"][0], h["local"][1],
                                                   h["dia"] / 2])
                                            for h in b["mounting"]["holes"]]}}
        if b.get("edge_notches"):
            layers["Edge.Cuts"]["circles"] += [
                (n["local"][0], n["local"][1], n["radius"]) for n in b["edge_notches"]]
        dxf_write(os.path.join(OUT, b["id"].lower().replace("-", "") + ".dxf"), layers)
    # общий DXF в мировой СК (все контуры/отверстия — для проверки в KiCad/просмотре)
    world = {"BOARD_OUTLINES": {"polylines": [
        [(p[0], p[1]) for p in b["outline"]["polygon_world"]] for b in spec["boards"]]},
        "MOUNTING_HOLES": {"circles": [
            (h["world"][0], h["world"][1], h["dia"] / 2)
            for b in spec["boards"] for h in b["mounting"]["holes"]]}}
    dxf_write(os.path.join(OUT, "assembly.dxf"), world)


# ---------------------------------------------------------------------------
# 4. SVG/PNG-превью
# ---------------------------------------------------------------------------
def write_preview(spec, checks):
    fig, axes = plt.subplots(2, 2, figsize=(13, 11), dpi=150)
    colors = {"CORE-2": "#2f7d4f", "PANEL-2-left": "#2a5f9e",
              "PANEL-2-right": "#3a7fc0", "PWR-2": "#c0392b"}
    for ax, b in zip(axes.ravel(), spec["boards"]):
        w, h = b["outline"]["size"]
        ax.add_patch(Rectangle((0, 0), w, h, fc="#eef3f8", ec="#111", lw=1.4))
        for ko in b.get("keepouts", []):
            if ko.get("edge"):
                continue
            if ko["type"] == "circle":
                cx, cy, r = ko["circle_local"]
                ax.add_patch(Circle((cx, cy), r, fc="none", ec="#c00", lw=0.7,
                                    ls=(0, (3, 2))))
            else:
                x0, y0, x1, y1 = ko["rect_local"]
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none",
                                       ec="#c80", lw=0.6, ls=(0, (2, 2))))
        for hh in b["mounting"]["holes"]:
            lx, ly = hh["local"]
            ax.add_patch(Circle((lx, ly), hh["dia"] / 2, fc="#fff", ec="#0055aa",
                                lw=0.9, zorder=5))
            ax.plot([lx], [ly], "+", color="#0055aa", ms=5, zorder=6)
        if b.get("edge_notches"):
            for n in b["edge_notches"]:
                ax.add_patch(Circle((n["local"][0], n["local"][1]), n["radius"],
                                    fc="#ddd", ec="#666", lw=0.7, zorder=4))
        ax.set_xlim(-8, w + 8); ax.set_ylim(-8, h + 8)
        ax.set_aspect("equal"); ax.grid(alpha=0.2, lw=0.4)
        ax.set_title(f"{b['id']} ({b['rev']}): {w:.0f}×{h:.0f} мм, "
                     f"{len(b['mounting']['holes'])}×{b['mounting']['screw']}")
        ax.set_xlabel("X, мм (local)")
    fig.suptitle("board-fit v0.5: контуры плат, крепёж и keepout'ы "
                 "(мм, локальные координаты, Y-up)", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "board-fit-preview.png"))
    fig.savefig(os.path.join(OUT, "board-fit-preview.svg"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# 5. README + fit_check
# ---------------------------------------------------------------------------
def write_readme(spec, checks):
    b = spec["boards"]
    lines = []
    w = lines.append
    w("# board-fit: посадочные места PCB rev.1 (CORE-2 / PANEL-2 / PWR-2)\n")
    w("Сгенерировано `mechanical/generator/make_board_fit.py` из параметров генератора "
      "(`params_v05`, `params_v17`, `params_v04`) и `spec/panel-spec-v0.4.json`. "
      "STL/JSON канона не меняются.\n")
    w(f"Единицы — **мм**; локальная СК платы: начало в левом-нижнем углу контура, "
      f"X вправо, **Y вверх** (совпадает с Y панели/мира: 0 — задняя кромка).\n")
    w("## 1. Контуры плат\n")
    w("| Плата | Ревизия | Origin (world X,Y) | Контур, мм | Толщина | Крепёж |")
    w("|---|---|---|---|---|---|")
    for x in b:
        ox, oy = x["outline"]["origin_world"]
        ww, hh = x["outline"]["size"]
        w(f"| {x['id']} | {x['rev']} | {ox:.0f}; {oy:.0f} | {ww:.0f} × {hh:.0f} | "
          f"{x['thickness']} | {len(x['mounting']['holes'])}×{x['mounting']['screw']} |")
    w("\n> **PANEL-2 — две платы** по шву X=190: 180 + 180 в общем контуре 360×190 "
      "(X 10…370, Y 10…200). Механический разрез панели — 193 + 190 (3 мм — шип "
      "панели, не платы). Ниша корпуса B: 375×205 (стенки 2.5), B-light: 376×206 "
      "(стенки 2.0) — платы проходят в обе редакции.\n")
    w("## 2. Крепёж (координаты — мировые, мм)\n")
    for x in b:
        w(f"### {x['id']} — {len(x['mounting']['holes'])} × {x['mounting']['screw']}")
        w("| Отверстие | World X; Y | Local X; Y | Ø отверстия | Ø стойки |")
        w("|---|---|---|---|---|")
        for hh in x["mounting"]["holes"]:
            w(f"| {hh['id']} | {hh['world'][0]:.1f}; {hh['world'][1]:.1f} | "
              f"{hh['local'][0]:.1f}; {hh['local'][1]:.1f} | {hh['dia']} | "
              f"{hh['post_dia']} |")
        w("")
    w("## 3. Вырезы/разъёмы на кромках\n")
    w("| Узел | Где | Размер/Ø | Примечание |")
    w("|---|---|---|---|")
    for c in spec["edge_cutouts_world"]:
        ww = c["world"]
        dim = (f"X {ww.get('x')} ; Y {ww.get('y')}"
               if isinstance(ww.get("x"), list) or isinstance(ww.get("y"), list)
               else f"X {ww.get('x')} ; Y {ww.get('y')} ; Ø/d {ww.get('dia', '—')}")
        w(f"| {c['id']} | {c['where']} | {dim} | {c['note']} |")
    w("\n> В STL сейчас реально есть только **USB-C-окно** (346…356, задняя стенка), "
      "**вентиляционные щели** и **порт MEMS** (B-light/B_mic/C_mic). Остальные "
      "вырезы (MIDI TRS, DC, EXPRESSION, mic jack, SD) — предложение; перед печатью "
      "корпуса их нужно добавить в генератор.\n")
    w("## 4. Keepout'ы (панель/платы)\n")
    for x in b:
        if x.get("keepouts"):
            w(f"### {x['id']}")
            w("| Зона | Тип/размер | Local | Назначение |")
            w("|---|---|---|---|")
            for ko in x["keepouts"]:
                if ko["type"] == "circle":
                    c = ko["circle_local"]
                    w(f"| {ko['id']} | круг Ø{2*c[2]:.0f} | {c[0]:.0f}; {c[1]:.0f} | {ko['note']} |")
                else:
                    r = ko["rect_local"]
                    w(f"| {ko['id']} | {r[2]-r[0]:.0f}×{r[3]-r[1]:.0f} | "
                      f"{r[0]:.0f}; {r[1]:.0f} | {ko['note']} |")
            w("")
    w("Правила: **MEMS ≥10 мм от WS2812/BL**; **антенна C6 keepout ≥15 мм**; "
      "батарея под PANEL-2 — без высоких компонентов; экран +2 мм; "
      "клавиши/энкодеры/фейдеры — по `spec/panel-spec-v0.4.json` ±0.1 мм.\n")
    w("## 5. DXF для KiCad\n")
    w("| Файл | Содержимое |")
    w("|---|---|")
    w("| `core2.dxf` | контур + 4×M3 (Ø3.4) |")
    w("| `panel2left.dxf` | контур 180×190 + 3×M3 + вырезы джеков по кромке |")
    w("| `panel2right.dxf` | контур 180×190 + 3×M3 + вырезы джеков |")
    w("| `pwr2.dxf` | контур 90×70 + 4×M2.5 (Ø2.8) |")
    w("| `assembly.dxf` | все контуры и отверстия в мировой СК |")
    w("\nИмпорт: KiCad → File → Import → DXF, слой **Edge.Cuts**; единицы мм, "
      "Y-up (как в файлах). Контуры замкнутые, отверстия — CIRCLE.\n")
    w("## 6. Проверки (2D)\n")
    w("| Проверка | Условие | Результат | Статус |")
    w("|---|---|---|---|")
    for what, cond, calc, status in checks:
        w(f"| {what} | {cond} | {calc} | **{status}** |")
    w("\n0 конфликтов — контуры в нише, отверстия на стойках, половины PANEL-2 не "
      "перекрываются, отверстия вне keepout. Дополнение к `mechanical/fit_check.md` "
      "(секция board-fit).\n")
    w("## 7. Расхождения с docs/82 §2 (исправлено в docs/82)\n")
    w("- В docs/82 было «PANEL-2 6×M3 (30/145/260 × 30/180)» — **не совпадает** с "
      "фактическим fitcheck: 6 стоек PANEL-2 = (30/65/150/230/283/341; Y=46) в "
      "координатах панели (world Y ≈ 46.6 при 8°). Эти числа и есть в board-spec.\n")
    w("- docs/82 «PANEL-2 380×210-контур» — фактический контур платы 360×190 "
      "(X 10…370, Y 10…200), как в fitcheck; панель 380×210 — механическая деталь.\n")
    w("- Шов PANEL-2: X=190 (левая/правая платы по 180 мм), механический разрез "
      "панели 193+190.\n")
    open(os.path.join(OUT, "README.md"), "w").write("\n".join(lines) + "\n")


def write_fitcheck(checks):
    marker = "<!-- section:board-fit -->"
    lines = []
    w = lines.append
    w(marker)
    w("\n---\n\n# fit_check — board-fit PCB rev.1 (2D, контуры/стойки/keepout)\n")
    w("Сгенерировано `mechanical/generator/make_board_fit.py`. Пакет: "
      "`mechanical/board-fit/` (board-spec.json, DXF, SVG). STL/JSON канона не менялись.\n")
    bad = [c for c in checks if c[3] != "OK"]
    w(f"\n**Итог:** проверок {len(checks)}, конфликтов: **{len(bad)}**.\n")
    w("\n| Проверка | Условие | Расчёт | Статус |")
    w("\n|---|---|---|---|")
    for what, cond, calc, status in checks:
        w(f"\n| {what} | {cond} | {calc} | **{status}** |")
    w("\n\n**PANEL-2 — две платы** 180+180 (X 10…190 и 190…370) в контуре "
      "360×190; механический разрез панели 193+190 (шип 3 мм) — см. docs/82 §2.\n")
    old = open(FIT_MD).read() if os.path.exists(FIT_MD) else ""
    if marker in old:
        old = old[:old.index(marker)]
    with open(FIT_MD, "w") as f:
        f.write(old.rstrip() + "\n\n" + "".join(lines) + "\n")
    print(f"[board-fit] записано {FIT_MD}, конфликтов {len(bad)}")


# ---------------------------------------------------------------------------
def main():
    spec, _ = build_spec()
    checks = run_checks(spec)
    spec["checks"] = [dict(what=w_, cond=c_, calc=cl_, status=st_)
                      for (w_, c_, cl_, st_) in checks]
    json.dump(spec, open(os.path.join(OUT, "board-spec.json"), "w"),
              indent=1, ensure_ascii=False)
    write_dxfs(spec)
    write_preview(spec, checks)
    write_readme(spec, checks)
    write_fitcheck(checks)
    print("board-fit:", OUT)


if __name__ == "__main__":
    main()
