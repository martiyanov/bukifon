"""Букифон v1.7 — параметры корпуса 380 × 210 × 63 мм.

Единственный источник чисел: spec/panel-spec-v1.7.json (утверждён заказчиком),
refs/concept-panel.jpg (внешний вид), task-9. Все координаты панели берутся
из JSON, а не хардкодятся — так панель и корпус остаются синхронными.

Система координат: X вправо (0…380), Y от задней кромки к игроку (0…210),
Z вверх от низа корпуса (0…63). Панель — верхние 3 мм (Z 60…63).

Генератор: mechanical/generator/case_v17.py
    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/case_v17.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPEC_JSON = os.path.join(ROOT, "spec", "panel-spec-v1.7.json")

# ---------------------------------------------------------------------------
# 0. Панель (spec/panel-spec-v1.7.json)
# ---------------------------------------------------------------------------
_SPEC = json.load(open(SPEC_JSON))

PANEL_W = float(_SPEC["panel"]["w"])          # 380
PANEL_H = float(_SPEC["panel"]["h"])          # 210
PANEL_T = float(_SPEC["panel"]["thickness"])  # 3

# ---------------------------------------------------------------------------
# 1. Габарит корпуса (task-9: высота 63 ±1, стенки 2.4–3)
# ---------------------------------------------------------------------------
BODY_H = 60.0            # низ 0 … верх стенок 60
TOTAL_H = 63.0           # 60 + панель 3  → 63.0
WALL = 2.5               # стенка 2.4–3
FLOOR_T = 3.0            # дно 0…3
R_OUT = 10.0             # скругление корпуса/панели по концепту
R_CAV = R_OUT - WALL     # 7.5 — внутренний радиус
SEAM_X = PANEL_W / 2     # 190 — разрез печати: панель/корпус на 2 половины
SPLIT_CLEAR = 0.25       # зазор в сопряжениях (как в v1.0)

# ---------------------------------------------------------------------------
# 2. Панель: окна/отверстия (все координаты — из JSON)
# ---------------------------------------------------------------------------
PANEL_Z0 = BODY_H                    # 60
PANEL_Z1 = BODY_H + PANEL_T          # 63

SCREEN = _SPEC["screen"]             # x, y, w, h (активная область 108 × 64.8)
SCREEN_R = 2.0
SCREEN_M25_HOLE = 2.7                # 4 × M2.5 крепления модуля снизу панели
SCREEN_M25_POS = [(SCREEN["x"] - 4.0, SCREEN["y"] + 6.0),
                  (SCREEN["x"] + SCREEN["w"] + 4.0, SCREEN["y"] + 6.0),
                  (SCREEN["x"] - 4.0, SCREEN["y"] + SCREEN["h"] - 6.0),
                  (SCREEN["x"] + SCREEN["w"] + 4.0, SCREEN["y"] + SCREEN["h"] - 6.0)]

KNOBS = _SPEC["knobs"]               # 16 шт.: x, y, d=14 (2 половины × 4 × 2 ряда)
KNOB_D = 14.0
KNOB_HOLE = 7.2                      # Ø7 под вал EC11
KNOB_NUT_D = 14.4                    # гайка/втулка M7 — Ø14.4 (спека: Ø14/16)
KNOB_NUT_DEPTH = 1.4                 # утоплена в панель с верхней стороны
KNOB_CAP_H = 12.0                    # высота ручки для рендеров

JACKS = _SPEC["jacks"]               # 10 шт.: x, y=7.0, hole=6.0
JACK_HOLE = 6.2                      # Ø6 + 0.2 зазор под 3.5 мм mini-jack
JACK_NUT_D = 8.2                     # гайка Ø8 (по ТЗ) + 0.2; до экрана (y 11.5) ~0.4 мм
JACK_NUT_DEPTH = 1.5    # цековка Ø8.2 × 1.5 под гайку (Lead)

FADERS = _SPEC["faders"]             # 2 шт.: x=180/200, y0=116, y1=196, slot_w=8
FADER_SLOT_W = float(FADERS[0].get("slot_w", 8.0))
FADER_SLOT_R = 4.0
FADER_SLOT_Y0 = float(FADERS[0]["y0"])      # 116
FADER_SLOT_Y1 = float(FADERS[0]["y1"])      # 196
FADER_M25_HOLE = 2.7                 # 4 × M2.5 на фейдер
FADER_M25_DX = 8.0        # гнёзда M2.5: 172/188 и 192/208 — не слипаются
FADER_M25_Y = [FADER_SLOT_Y0 + 2.0, FADER_SLOT_Y1 - 2.0]

# 42 клавиши: в JSON v1.7 — keyboard.keys_42 (x, y, angle_deg, half);
# нормализуем к полям x / y / deg, чтобы код был один на обе ревизии JSON.
_KEYS_RAW = _SPEC.get("keys", {}).get("items") or _SPEC["keyboard"]["keys_42"]
KEYS = [{"x": float(k["x"]), "y": float(k["y"]),
         "deg": float(k.get("deg", k.get("angle_deg", 0.0)))} for k in _KEYS_RAW]
KEY_WIN = 14.0                       # квадрат под Choc (13.8 + зазор)
KEY_WIN_R = 0.6
_KC = _SPEC.get("keys", {}).get("keycap") or _SPEC["keyboard"]["keycap"]
KEYCAP_W = float(_KC["w"])           # 17.5
KEYCAP_H = float(_KC["h"])           # 16.5
KEYCAP_T = 5.5                       # высота колпачка v1.7 (Lead: 5.5 мм)
KEYCAP_R = 1.5                       # скругление колпачка
KEYCAP_DISH = 0.45                   # лёгкая вогнутость площадки
KEYCAP_BOTTOM_W, KEYCAP_BOTTOM_D = 15.4, 14.4   # низ (посадка на Choc)
SCREEN_LEDGE = 1.5                   # внутренний буртик экрана, мм

PANEL_SCREW_D = 3.3                  # 4 × M3 по углам (как на концепте)
PANEL_SCREW_INSET = 9.0
PANEL_SCREWS = [(PANEL_SCREW_INSET, PANEL_SCREW_INSET),
                (PANEL_W - PANEL_SCREW_INSET, PANEL_SCREW_INSET),
                (PANEL_SCREW_INSET, PANEL_H - PANEL_SCREW_INSET),
                (PANEL_W - PANEL_SCREW_INSET, PANEL_H - PANEL_SCREW_INSET)]
PANEL_CSK_D = 6.6                    # зенковка под потай M3
PANEL_CSK_T = 1.65

USBC = dict(cx=350.0, w=9.4, depth=3.6, r=1.8)   # вырез на задней кромке (Y=0)

# ---------------------------------------------------------------------------
# 3. Внутренние платы (посадочные места; габариты — принятые допущения)
# ---------------------------------------------------------------------------
# PANEL-1 rev.2 — 360 × 190 × 1.6, Z 47…48.6 (под панелью, на 6 стойках).
PANEL1_W, PANEL1_D, PANEL1_T = 360.0, 190.0, 1.6
PANEL1_X0, PANEL1_X1 = (PANEL_W - PANEL1_W) / 2, (PANEL_W + PANEL1_W) / 2   # 10…370
PANEL1_Y0, PANEL1_Y1 = 10.0, 200.0
PANEL1_Z0, PANEL1_Z1 = 47.0, 48.6
PANEL1_POSTS = [(30.0, 30.0), (145.0, 30.0), (260.0, 30.0),
                (30.0, 180.0), (145.0, 180.0), (260.0, 180.0)]    # 6 × M3
# средняя пара сдвинута с X=190, чтобы не пересекать корпуса фейдеров (180/200)
# Вырезы в PANEL-1 под панельные компоненты (панельный монтаж + разводка):
# ручки, клавиши, джеки, экран, фейдеры — с запасом 1 мм на сторону.
PANEL1_CUTS = dict(knob_d=14.0, key=15.0, jack_d=10.0,
                   screen_pad=4.0, fader=(30.0, 76.0))

# CORE-1 rev.3 — 200 × 108 × 1.6, Z 12…13.6 на 4 стойках (190 × 92 по центрам).
CORE_W, CORE_D, CORE_T = 200.0, 108.0, 1.6
CORE_X0, CORE_X1 = (PANEL_W - CORE_W) / 2, (PANEL_W + CORE_W) / 2    # 90…290
CORE_Y0, CORE_Y1 = (PANEL_H - CORE_D) / 2, (PANEL_H + CORE_D) / 2    # 51…159
CORE_Z0, CORE_Z1 = 12.0, 13.6
CORE_POSTS = [(95.0, 59.0), (285.0, 59.0), (95.0, 151.0), (285.0, 151.0)]
CORE_COMP_TOP = 24.0                  # верх компонентов (для проверки зазоров)

# ---------------------------------------------------------------------------
# 4. Батарея 1S2P 18650 (hardware/power/README.md §7: 2 банки вне платы)
# ---------------------------------------------------------------------------
BAT_N = 2
BAT_D = 18.4                          # Ø18650
BAT_L = 65.0                          # длина банки
BAT_X = [310.0, 330.0]                # центры банок (шаг 20)
BAT_Y0, BAT_Y1 = 58.0, 123.0          # банки вдоль Y
BAT_Z0, BAT_Z1 = FLOOR_T, FLOOR_T + BAT_D      # лежат на дне
BAT_CRADLE_Y = [BAT_Y0 - 1.0, (BAT_Y0 + BAT_Y1) / 2 - 3.0, BAT_Y1 + 1.0 - 6.0]
BAT_CRADLE_Z0 = FLOOR_T
BAT_CRADLE_Z1 = BAT_Z1 + 1.0

# ---------------------------------------------------------------------------
# 5. Стойки/крепёж/печать
# ---------------------------------------------------------------------------
M3_INSERT_D = 4.6                     # термовтулка M3 4.6 × 6
M3_INSERT_DEPTH = 6.0
M3_CLEAR_D = 3.3
M2_INSERT_D = 2.7

POST_CORNER_D = 9.0                   # стойки панели Ø9 (4 шт. по углам)
BODY_POST_CORE_D = 7.0
BODY_POST_PANEL_D = 7.0

FOOT_D = 12.0                         # ножки Ø12 × 2.5, утоплены в дно
FOOT_H = 2.5
FOOT_RECESS_D = 13.0
FOOT_RECESS_H = 2.5
FEET = [(28.0, 28.0), (PANEL_W - 28.0, 28.0),
        (28.0, PANEL_H - 28.0), (PANEL_W - 28.0, PANEL_H - 28.0)]

VENT_SLOT_W = 2.5                      # вентиляционные щели в дне
VENT_SLOT_L = 22.0
VENT_SLOTS = [(x, 181.0) for x in (70.0, 100.0, 130.0, 250.0, 280.0, 310.0)]

RIB_W = 3.0                            # рёбра жёсткости по внутренним стенкам
RIB_D = 8.0
RIB_H = 42.0             # верх рёбер 45 < PANEL-1 (47)
RIBS = [(60.0, "rear"), (130.0, "rear"), (250.0, "rear"), (320.0, "rear"),
        (60.0, "front"), (130.0, "front"), (250.0, "front"), (320.0, "front")]

USBC_CABLE_SLOT = (344.0, 356.0, 3.0, 8.0)   # окно под кабель USB-C в задней стенке

# ---------------------------------------------------------------------------
# 6. Шов печати X = 190: шип/паз + 2 шпонки
# ---------------------------------------------------------------------------
SEAM_TONGUE_T = 1.2                    # tongue панели (нижние 1.2 мм из 3)
SEAM_TONGUE_L = 3.0                    # вылет по X
SEAM_FLOOR_TAB_Z = FLOOR_T             # шип пола корпуса (0…3)
SEAM_KEY_L = 8.0                       # печатные шпонки 8 × 3 × 5 (2 шт.)
SEAM_KEY_W = 3.0
SEAM_KEY_H = 5.0
SEAM_KEY_Y = [40.0, 170.0]

# ---------------------------------------------------------------------------
# 7. Комплектация
# ---------------------------------------------------------------------------
PARTS_V17 = ["body_L", "body_R", "panel_L", "panel_R", "foot"]
COUNTS_V17 = {"body_L": 1, "body_R": 1, "panel_L": 1, "panel_R": 1, "foot": 4,
              "seam_key": 2}
PETG_DENSITY = 1.27
PLA_DENSITY = 1.24
TPU_DENSITY = 1.21
EFFECTIVE_FILL = 0.36
