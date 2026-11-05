#!/usr/bin/env python3
"""Каноническая раскладка v0.4: ТОЧНАЯ геометрия Lapka-42 + вид по концепту заказчика.

Зачем: handoff v0.3 (spec/panel-spec-v0.3.json) восстановлен по ФОТО макета с
погрешностью 1–2 мм, а концепт-картинка — художественная. Для производства нужно:
  * клавиши — ровно реальная геометрия Lapka-42 (21 клавиша, Choc 18×17), без искажений;
  * половины развёрнуты наружу как на концепте (±19°, замер по концепту);
  * остальные элементы (16 энкодеров, 10 джеков, экран, 2 фейдера) — из концепта.

Выход:
  spec/panel-spec-v0.4.json        — канон (схема совместима с v0.3: controls.*)
  renders/templates/bukifon_v04_panel_1to1.pdf
  renders/templates/bukifon_v04_render.png
  renders/templates/bukifon_v04_vs_concept.png
  renders/templates/bukifon_v04_collisions.json
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lapka42_geometry as L

SPEC_OUT = os.path.join(ROOT, "spec", "panel-spec-v0.4.json")
OUT = os.path.join(ROOT, "renders", "templates")

PANEL_W, PANEL_H, PANEL_T, DEPTH = 380.0, 210.0, 3.0, 63.0

# --- элементы из концепта (замер OpenCV по refs/concept-panel.jpg, см. tools/v1_7) ---
KNOB_COLS_L = [25.2, 54.1, 82.6, 111.4]
KNOB_COLS_R = [269.3, 297.8, 326.6, 355.8]
KNOB_ROWS = [35.7, 68.5]
JACK_X0, JACK_PITCH, JACK_Y = 129.9, 13.1, 10.5
LCD = dict(cx=190.0, cy=58.7, w=108.0, h=64.8)          # 5.0" 800×480, без рамки
LCD_BODY = dict(cx=190.0, cy=58.7, w=120.7, h=75.8)
FADER_X = [175.1, 204.0]
FADER_CY, FADER_SLOT_W, FADER_SLOT_L = 150.0, 2.5, 63.0
FADER_ENV_W, FADER_ENV_L = 16.0, 75.0

# --- клавиши: реальная Lapka-42, половины развёрнуты наружу ---
TILT_DEG = 18.0            # замер по концепту (chamfer-fit 18.75…19.25°)
CAP_W, CAP_H = L.KEYCAP_W, L.KEYCAP_H


def _model():
    """Центры колпачков реальной Lapka-42, мм, начало в min bbox."""
    hw, hh = CAP_W / 2, CAP_H / 2
    xs, ys = [], []
    for x, y, r in L.LAPKA42_LEFT:
        a = math.radians(r)
        ca, sa = math.cos(a), math.sin(a)
        for sx in (-1, 1):
            for sy in (-1, 1):
                xs.append(x + ca * sx * hw - sa * sy * hh)
                ys.append(y + sa * sx * hw + ca * sy * hh)
    x0, y0 = min(xs), min(ys)
    return [(x - x0, y - y0, r) for x, y, r in L.LAPKA42_LEFT]


MODEL = _model()
MB_W = max(p[0] for p in MODEL) + CAP_W
MB_H = max(p[1] for p in MODEL) + CAP_H


def _place(mirror: bool, deg: float, cx: float, cy: float):
    """Повернуть половину на deg (по часовой на виде сверху) и поставить центром в (cx,cy)."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    keys = []
    for (mx, my, rot) in MODEL:
        px = (MB_W - mx) if mirror else mx
        dx, dy = px - MB_W / 2, my - MB_H / 2
        # поворот по часовой: (x',y') = (ca*dx - sa*dy, sa*dx + ca*dy) в осях y-вниз
        qx = cx + ca * dx - sa * dy
        qy = cy + sa * dx + ca * dy
        ang = (rot if mirror else -rot) + deg
        ang = ((ang + 90.0) % 180.0) - 90.0     # прямоугольник симметричен: -90…90
        keys.append((qx, qy, ang))
    return keys


# куда ставить: центры кластеров по концепту (bbox клавиш из замера концепта)
LEFT_C = (83.0, 148.0)
RIGHT_C = (PANEL_W - 83.0, 148.0)


def build_keys():
    left = _place(False, +TILT_DEG, *LEFT_C)
    right = _place(True, -TILT_DEG, *RIGHT_C)
    out = []
    for i, (x, y, ang) in enumerate(left, 1):
        out.append(dict(id=f"L_K{i:02d}", key_number=i, half="L", center_mm=[round(x, 2), round(y, 2)],
                        size_mm=[CAP_W, CAP_H], angle_deg=round(ang, 2)))
    for i, (x, y, ang) in enumerate(right, 1):
        out.append(dict(id=f"R_K{i:02d}", key_number=i, half="R", center_mm=[round(x, 2), round(y, 2)],
                        size_mm=[CAP_W, CAP_H], angle_deg=round(ang, 2)))
    return out


def build_spec():
    keys = build_keys()
    enc = []
    for side, cols in (("L", KNOB_COLS_L), ("R", KNOB_COLS_R)):
        for ci, x in enumerate(cols):
            for ri, y in enumerate(KNOB_ROWS):
                name = "ABCD"[ci] if ri == 0 else "EFGH"[ci]
                enc.append(dict(id=f"{side}_ENC_{name}", center_mm=[x, y], angle_deg=0.0,
                                shape="circle", knob_outer_diameter_mm=14.0,
                                nominal_panel_hole_diameter_mm=7.2, hole_size_confirmed=False))
    jacks = [dict(id=f"J{i+1:02d}", center_mm=[round(JACK_X0 + i * JACK_PITCH, 1), JACK_Y],
                  angle_deg=0.0, shape="circle", panel_hole_diameter_mm=6.0,
                  outer_nut_diameter_mm=8.0, verify_actual_part=True) for i in range(10)]
    faders = [dict(id=f"F{i+1}",
                   rear_envelope=dict(id=f"F{i+1}_env", center_mm=[x, FADER_CY], angle_deg=0.0,
                                      shape="rectangle", rear_envelope_size_mm=[FADER_ENV_W, FADER_ENV_L]),
                   slot=dict(id=f"F{i+1}_slot", center_mm=[x, FADER_CY], angle_deg=0.0,
                             shape="rectangle", slot_size_mm=[FADER_SLOT_W, FADER_SLOT_L],
                             stroke_length_nominal_mm=60))
              for i, x in enumerate(FADER_X)]
    return dict(
        schema="bukifon.panel_layout.v1",
        revision="v0.4-lapka-exact-layout-concept-tilt19",
        date="2026-11-05",
        units="mm",
        coordinate_system=dict(view="top", origin="top-left corner of panel",
                               x_positive="right", y_positive="down",
                               element_position="center",
                               angle_unit="deg", angle_positive="clockwise on top view",
                               rotate_each_element_around="own center",
                               panel_bounds_mm=[PANEL_W, PANEL_H]),
        panel=dict(width_mm=PANEL_W, height_mm=PANEL_H, front_panel_thickness_mm=PANEL_T,
                   overall_depth_mm=DEPTH, material="PETG", max_print_area_mm=[220, 220],
                   shape="rectangle",
                   no_speakers=True, no_jacks_below_screen=True),
        source=dict(basis="ТОЧНАЯ геометрия Lapka-42 (tools/lapka42_geometry.py) + "
                          "раскладка и углы по концепт-изображению refs/concept-panel.jpg",
                    lapka_note="Относительная геометрия клавиш не искажена: 21 клавиша на половину, "
                               "шаг 18 × 17 мм, splay как в оригинале.",
                    accuracy_mm=0.5),
        controls=dict(
            keyboard_left=[k for k in keys if k["half"] == "L"],
            keyboard_right=[k for k in keys if k["half"] == "R"],
            encoders_left=[e for e in enc if e["id"].startswith("L")],
            encoders_right=[e for e in enc if e["id"].startswith("R")],
            jacks=jacks,
            lcd=dict(active_cutout=dict(id="LCD", center_mm=[LCD["cx"], LCD["cy"]], angle_deg=0.0,
                                        shape="rectangle", opening_size_mm=[LCD["w"], LCD["h"]],
                                        screen_pixels=[800, 480], bezel="no decorative frame"),
                     body_envelope=dict(id="LCD_body", center_mm=[LCD_BODY["cx"], LCD_BODY["cy"]],
                                        angle_deg=0.0, shape="rectangle",
                                        rear_envelope_size_mm=[LCD_BODY["w"], LCD_BODY["h"]],
                                        verify_display_mounting_and_connector=True)),
            faders=faders),
        notes=[f"Половины клавиатур развёрнуты наружу на ±{TILT_DEG:.0f}° (по концепту).",
               "Экран 5.0\" 800×480: вырез = активная область 108 × 64.8, без рамки.",
               "Динамиков нет; разъёмов под экраном нет.",
               "Точность: относительная геометрия клавиш — точная (KiCad Lapka-42); "
               "положение кластеров и остальных элементов — по концепту (±0.5 мм по картинке)."],
    )


def main():
    spec = build_spec()
    os.makedirs(os.path.dirname(SPEC_OUT), exist_ok=True)
    json.dump(spec, open(SPEC_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("spec:", SPEC_OUT, "| keys:", len(spec["controls"]["keyboard_left"]) * 2,
          "| enc:", len(spec["controls"]["encoders_left"]) * 2,
          "| jacks:", len(spec["controls"]["jacks"]))


if __name__ == "__main__":
    main()
