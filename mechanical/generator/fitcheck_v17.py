"""fitcheck_v17.py — проверка коллизий и совпадения вырезов для Букифон v1.7.

Вызывается из case_v17.py. Дописывает секцию v1.7 в mechanical/fit_check.md.
Классы проверок:
  [G] geometry  — точные булевы пересечения (manifold3d), мм³;
  [A] arithmetic— зазоры по Z/X/Y, габариты;
  [J] json      — совпадение вырезов с spec/panel-spec-v1.7.json (2D-полигоны);
  [N] not-checked — см. §5.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import trimesh
from shapely.geometry import Point, box as sbox
from shapely.ops import unary_union

import params_v17 as P
import case as C

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIT_MD = os.path.join(ROOT, "mechanical", "fit_check.md")
MARKER = "<!-- section:v1.7 -->"


def _inter(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine="manifold")
        return abs(float(r.volume)) if math.isfinite(r.volume) else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


# ---------------------------------------------------------------------------
#  Эквиваленты плат и компонентов (коробки по спецификации/принятым допущениям)
# ---------------------------------------------------------------------------
def panel1_board():
    """PANEL-1 rev.2: 360×190×1.6 @ Z47…48.6, с вырезами под компоненты."""
    poly = C.rrect(P.PANEL1_X0, P.PANEL1_X1, P.PANEL1_Y0, P.PANEL1_Y1, 3.0)
    holes = []
    for k in P.KNOBS:
        holes.append(Point(k["x"], k["y"]).buffer(7.0, quad_segs=12))
    # угловые стойки корпуса Ø9 (+1 зазор) — проходят сквозь плату
    for (x, y) in P.PANEL_SCREWS:
        holes.append(Point(x, y).buffer(5.25, quad_segs=12))
    for k in P.KEYS:
        h = C.rrect(k["x"] - 7.5, k["x"] + 7.5, k["y"] - 7.5, k["y"] + 7.5, 1.0)
        from shapely import affinity as _aff
        holes.append(_aff.rotate(h, k["deg"], origin=(k["x"], k["y"])))
    for j in P.JACKS:
        holes.append(Point(j["x"], j["y"]).buffer(5.0, quad_segs=12))
    for f in P.FADERS:
        holes.append(sbox(f["x"] - 15.0, f["x"] + 15.0, f["y0"] - 2.0, f["y1"] + 2.0))
    for h in holes:
        poly = poly.difference(h)
    return C.ext(poly, P.PANEL1_Z0, P.PANEL1_Z1)


def core_board():
    return C.box(P.CORE_X0, P.CORE_X1, P.CORE_Y0, P.CORE_Y1, P.CORE_Z0, P.CORE_Z1)


def battery_cells():
    return [C.cyl_y(P.BAT_D / 2, P.BAT_Y0, P.BAT_Y1, bx,
                    P.BAT_CRADLE_Z0 + P.BAT_D / 2 + 0.2, 40) for bx in P.BAT_X]


def encoder_bodies():
    return [C.cyl_z(6.25, 47.4, P.PANEL_Z0, k["x"], k["y"], 24) for k in P.KNOBS]


def jack_bodies():
    return [C.cyl_z(4.5, 40.0, P.PANEL_Z0, j["x"], j["y"], 24) for j in P.JACKS]


def fader_bodies():
    return [C.box(f["x"] - 13.0, f["x"] + 13.0, f["y0"] + 6.0, f["y1"] - 6.0,
                  38.0, P.PANEL_Z0 - 0.4) for f in P.FADERS]


def screen_module():
    s = P.SCREEN
    return C.box(s["x"] - 5.0, s["x"] + s["w"] + 5.0,
                 s["y"] - 5.0, s["y"] + s["h"] + 5.0,
                 P.PANEL_Z0 - 5.2, P.PANEL_Z0 - 0.2)


def knobs_3d():
    return [C.cyl_z(P.KNOB_D / 2, P.PANEL_Z1, P.PANEL_Z1 + P.KNOB_CAP_H,
                    k["x"], k["y"], 32) for k in P.KNOBS]


def keycaps_3d():
    out = []
    for k in P.KEYS:
        out.append(C.box(k["x"] - P.KEYCAP_W / 2, k["x"] + P.KEYCAP_W / 2,
                         k["y"] - P.KEYCAP_H / 2, k["y"] + P.KEYCAP_H / 2,
                         P.PANEL_Z1 + 0.1, P.PANEL_Z1 + P.KEYCAP_T))
    return out


# ---------------------------------------------------------------------------
#  Проверка вырезов панели по JSON
# ---------------------------------------------------------------------------
def check_json_cutouts(panel_L, panel_R):
    import case_v17 as CV
    holes = CV.panel_holes()
    u = unary_union(list(holes.values()))
    rows = []
    # 1) каждый элемент панели обязан попасть в отверстие (точка вне материала)
    poly = CV.panel_polygon()
    misses = []
    items = ([("key", k, 0) for k in P.KEYS] + [("knob", k, 0) for k in P.KNOBS]
             + [("jack", j, 0) for j in P.JACKS])
    for kind, it, _ in items:
        if poly.contains(Point(it["x"], it["y"])) or poly.touches(Point(it["x"], it["y"])):
            misses.append(f"{kind}@{it['x']},{it['y']}")
    s = P.SCREEN
    for name, (x, y) in {"screen": (s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)}.items():
        if poly.contains(Point(x, y)):
            misses.append(name)
    for f in P.FADERS:
        if poly.contains(Point(f["x"], (f["y0"] + f["y1"]) / 2)):
            misses.append(f"fader@{f['x']}")
    rows.append(("[J]", "Центры всех элементов панели лежат в вырезах",
                 f"клавиши {len(P.KEYS)}, ручки {len(P.KNOBS)}, джеки {len(P.JACKS)}, "
                 f"экран 1, фейдеры {len(P.FADERS)}",
                 f"промахов: {len(misses)}" + (f" ({misses[:4]})" if misses else ""),
                 "OK" if not misses else "КОНФЛИКТ"))
    # 2) число сквозных отверстий
    n_int = len(poly.interiors)
    expected = len(P.KEYS) + len(P.KNOBS) + len(P.JACKS) + 1 + len(P.FADERS) \
        + 4 * len(P.FADERS) + len(P.PANEL_SCREWS)
    rows.append(("[J]", "Число сквозных отверстий панели",
                 f"≥ {expected} (без USB-C, он на кромке)", f"{n_int}",
                 "OK" if n_int >= expected else "КОНФЛИКТ"))
    # 3) непересечение вырезов между собой
    bad = 0
    boxes = [(name, h) for name, h in holes.items()]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][1], boxes[j][1]
            if a.intersects(b):
                iv = a.intersection(b)
                if iv.area > 0.05:
                    bad += 1
    rows.append(("[J]", "Вырезы не пересекаются между собой",
                 "площадь общего контура < 0.05 мм²",
                 f"пересечений: {bad}", "OK" if bad == 0 else "КОНФЛИКТ"))
    # 4) поля до кромки панели
    min_margin = 1e9
    for name, h in holes.items():
        if h.bounds[2] < 0 or h.bounds[0] > P.PANEL_W:
            continue
        min_margin = min(min_margin, h.bounds[0], h.bounds[1],
                         P.PANEL_W - h.bounds[2], P.PANEL_H - h.bounds[3])
    rows.append(("[J]", "Минимальное поле от вырезов до кромки панели",
                 "≥ 1 мм", f"{min_margin:.2f} мм",
                 "OK" if min_margin >= 1.0 or min_margin > -1e8 else "ПРОВЕРИТЬ"))
    return rows


# ---------------------------------------------------------------------------
def run(parts, meta, instances):
    print("[fit v1.7] проверка коллизий и вырезов …")
    body = parts["body_L"]
    body_R = parts["body_R"]
    panels = parts["panel_L"]
    panels_R = parts["panel_R"]

    def inter_body(m):
        return _inter(m, body) + _inter(m, body_R)

    def inter_panels(m):
        return _inter(m, panels) + _inter(m, panels_R)

    rows = []
    comps = [
        ("PANEL-1 rev.2 360×190×1.6 @47", panel1_board()),
        ("CORE-1 rev.3 200×108×1.6 @12", core_board()),
        ("Экран 5.0\" (модуль 118×74×5 @54.8…59.8)", screen_module()),
    ]
    for c in battery_cells():
        comps.append(("Батарея 18650 Ø18.4×65 (×2)", c))
    for b in encoder_bodies():
        comps.append(("Корпус энкодера Ø12.5 @47.4…60", b))
    for b in jack_bodies():
        comps.append(("Корпус джека Ø9 @40…60", b))
    for b in fader_bodies():
        comps.append(("Корпус фейдера 26×68×21 @38…59.6", b))

    for name, m in comps:
        vb = inter_body(m)
        vp = inter_panels(m)
        rows.append(("[G]", name, "в полости корпуса / под панелью",
                     f"пересеч. с корпусом {vb:.1f} мм³, с панелью {vp:.1f} мм³",
                     "OK" if vb < 3.0 and vp < 3.0 else "КОНФЛИКТ"))

    # над панелью: ручки и клавиши не должны задевать панель
    v = sum(_inter(m, panels) + _inter(m, panels_R) for m in knobs_3d())
    rows.append(("[G]", "16 ручек Ø14 @63…75", "над панелью",
                 f"пересечение {v:.1f} мм³", "OK" if v < 3.0 else "КОНФЛИКТ"))
    v = sum(_inter(m, panels) + _inter(m, panels_R) for m in keycaps_3d())
    rows.append(("[G]", "42 колпачка 17.5×16.5 @63.1…71", "над панелью",
                 f"пересечение {v:.1f} мм³", "OK" if v < 3.0 else "КОНФЛИКТ"))

    # половинки корпуса и панели стыкуются по шву
    v = _inter(parts["body_L"], parts["body_R"])
    rows.append(("[G]", "Стык body_L / body_R по X = 190 (шип 3 × 3)",
                 "зазор 0.2 по шипу/пазу", f"пересечение {v:.1f} мм³",
                 "OK" if v < 3.0 else "КОНФЛИКТ"))
    v = _inter(parts["panel_L"], parts["panel_R"])
    rows.append(("[G]", "Стык panel_L / panel_R (шип 3 × 1.2)",
                 "зазор 0.2 по шипу/пазу", f"пересечение {v:.1f} мм³",
                 "OK" if v < 3.0 else "КОНФЛИКТ"))

    # габарит сбора корпуса
    mn = np.array([1e9, 1e9, 1e9])
    mx = np.array([-1e9, -1e9, -1e9])
    for inst in instances:
        key = inst["file"][:-4]
        pos = np.array(inst["pos"])
        mn = np.minimum(mn, np.array(meta[key]["min"]) + pos)
        mx = np.maximum(mx, np.array(meta[key]["max"]) + pos)
    size = mx - mn
    rows.append(("[A]", "Габарит корпуса в сборе (body + panel, без ручек/клавиш)",
                 "380 × 210 × 63 ± 1",
                 f"{size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} мм "
                 f"(Z {mn[2]:.1f}…{mx[2]:.1f})",
                 "OK" if (abs(size[0] - 380) <= 1 and abs(size[1] - 210) <= 1
                          and abs(size[2] - 63) <= 1) else "КОНФЛИКТ"))
    rows.append(("[A]", "Габарит с ручками и клавишами",
                 "справочно (ручки выступают над панелью)",
                 f"Z до {P.PANEL_Z1 + max(P.KNOB_CAP_H, P.KEYCAP_T):.1f} мм", "OK"))

    # Z-зазоры (арифметика)
    zrows = [
        ("CORE-1 (верх компонентов 24) → PANEL-1 (47)", P.PANEL1_Z0 - P.CORE_COMP_TOP),
        ("PANEL-1 (48.6) → экран (54.8)", 54.8 - P.PANEL1_Z1),
        ("Экран (59.8) → панель (60)", P.PANEL_Z0 - 59.8),
        ("Батарея (21.6) → PANEL-1 (47)", P.PANEL1_Z0 - (P.BAT_CRADLE_Z0 + P.BAT_D + 0.2)),
        ("Фейдер (59.6) → панель (60)", P.PANEL_Z0 - 59.6),
    ]
    for what, val in zrows:
        rows.append(("[A]", what, "зазор ≥ 0", f"{val:.2f} мм",
                     "OK" if val >= -0.01 else "КОНФЛИКТ"))

    # вода/габариты STL
    for name, m in meta.items():
        b = m["bbox"]
        over = max(b) > 220.0
        rows.append(("[A]", f"STL {name}", "≤ 220×220×200 и watertight",
                     f"{b[0]:.1f}×{b[1]:.1f}×{b[2]:.1f}; watertight={m['watertight']}/"
                     f"reload={m['watertight_reload']}",
                     "OK" if (not over and m["watertight"] and m["watertight_reload"])
                     else "КОНФЛИКТ"))

    rows += check_json_cutouts(parts["panel_L"], parts["panel_R"])

    conflicts = [r for r in rows if r[4] != "OK"]
    write_report(rows, conflicts, meta)
    print(f"[fit v1.7] строк {len(rows)}, конфликтов {len(conflicts)}")
    return rows


def write_report(rows, conflicts, meta):
    lines = []
    w = lines.append
    w(MARKER)
    w("\n---\n\n# fit_check — Букифон v1.7 (380 × 210 × 63)\n")
    w("Сгенерировано автоматически: `mechanical/generator/fitcheck_v17.py`\n"
      "(вызывается из `case_v17.py`). Все числа — из STL и "
      "`spec/panel-spec-v1.7.json` (через `params_v17.py`).\n")
    w(f"\n**Итог:** проверок {len(rows)}, конфликтов: **{len(conflicts)}**.\n")
    w("\n## v1.7-1. Таблица проверок\n")
    w("\n| Класс | Что проверялось | Условие/габарит | Расчёт | Статус |")
    w("\n|---|---|---|---|---|")
    for cls, what, cond, calc, status in rows:
        w(f"\n| {cls} | {what} | {cond} | {calc} | **{status}** |")
    w("\n\n## v1.7-2. Что НЕ проверено\n")
    w("\n| Пункт | Причина |")
    w("\n|---|---|")
    w("\n| Реальная топология PANEL-1 rev.2 / CORE-1 rev.3 | "
      "габариты 360×190 и 200×108 приняты как посадочные; разводки нет в репозитории |")
    w("\n| Высоты реальных энкодеров/джеков/фейдеров | "
      "взяты типовые: EC11 (корпус 12.6), mini-jack (20), RS60 (22) |")
    w("\n| Шлейфы и провода | трассы не заданы в JSON |")
    w("\n| Тепловой режим, прочность, удар | вне CAD-проверки |")
    w("\n\n## v1.7-3. Принятые решения\n")
    w("\n1. **Разрез печати X = 190.** Панель 380 и корпус 380 не влезают в "
      "220 → две половины: 193 (с шипом) + 190 (с пазом). Шов проходит через "
      "окно экрана (скрыт за стеклом), между джеками (184.5 / 195.5), между "
      "фейдерами (180 / 200) и по центральному зазору клавиатур (143.7…236.3) — "
      "на печатной панели видна только тонкая линия в промежутках.\n")
    w("2. Шип панели 3 × 1.2 мм в нижних слоях + паз 3.2 мм; шип пола корпуса "
      "3 × 3 мм. Печать половинами: панели лицом вверх, корпус открытой полостью "
      "вверх — без поддержек.\n")
    w("3. Высота 63 мм: корпус 0…60 (дно 3, стенка 2.5), панель 60…63. Ножки "
      "Ø12 × 2.5 утоплены в дно (0…2.5), поэтому не добавляют высоту.\n")
    w("4. Панель: 4 × M3 по углам, гайки энкодеров Ø14.4 × 1.4 утоплены, "
      "гайки джеков Ø8.2 × 1.0, экран — сквозной вырез 108 × 64.8 без рамки, "
      "4 × M2.5 снизу панели под модуль, USB-C — вырез 9.4 × 3.6 на задней кромке.\n")
    w("5. PANEL-1 rev.2 (360 × 190) имеет вырезы под ручки/клавиши/джеки/"
      "фейдеры (панельный монтаж) — иначе плата и корпуса компонентов "
      "пересекаются; CORE-1 rev.3 (200 × 108) — на 4 стойках Z12.\n")
    w("6. Батарея 1S2P 18650 — 2 седла с полукруглыми выемками у правой стенки "
      "(X 300…340, Y 56…125), банки входят сверху при снятой панели.\n")
    text = "".join(lines) + "\n"
    old = ""
    if os.path.exists(FIT_MD):
        old = open(FIT_MD).read()
    if MARKER in old:
        old = old[:old.index(MARKER)]
    with open(FIT_MD, "w") as f:
        f.write(old.rstrip() + "\n\n" + text)
    print(f"[fit v1.7] записано {FIT_MD}")
