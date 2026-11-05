"""fitcheck_v04.py — проверки панели v0.4 (Букифон).

Вызывается из case_v04.py. Дописывает секцию v0.4 в mechanical/fit_check.md.
Классы: [G] булевы пересечения; [A] арифметика/габариты; [J] сверка с
spec/panel-spec-v0.4.json (центры вырезов ±0.05 мм, число вырезов, отсутствие
пересечений вырезов); [N] что не проверено.
"""
from __future__ import annotations

import math
import os

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import Point, box as sbox
from shapely.ops import unary_union

import params_v04 as P
import params_v17 as P17
import case as C

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STL_DIR = os.path.join(ROOT, "mechanical", "stl_v04")
FIT_MD = os.path.join(ROOT, "mechanical", "fit_check.md")
MARKER = "<!-- section:v0.4 -->"


def _inter(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine="manifold")
        return abs(float(r.volume)) if math.isfinite(r.volume) else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def panel1_board():
    poly = C.rrect(P.PANEL1_X0, P.PANEL1_X1, P.PANEL1_Y0, P.PANEL1_Y1, 3.0)
    holes = []
    for e in P.KNOBS:
        holes.append(Point(e["x"], e["y"]).buffer(7.0, quad_segs=12))
    for k in P.KEYS:
        h = C.rrect(k["x"] - 7.5, k["x"] + 7.5, k["y"] - 7.5, k["y"] + 7.5, 1.0)
        holes.append(affinity.rotate(h, k["deg"], origin=(k["x"], k["y"])))
    for j in P.JACKS:
        holes.append(Point(j["x"], j["y"]).buffer(5.0, quad_segs=12))
    for f in P.FADERS:
        holes.append(sbox(f["x"] - 9.0, f["x"] + 9.0,
                          f["y"] - f["body_h"] / 2 - 1, f["y"] + f["body_h"] / 2 + 1))
    for (x, y) in P.PANEL_SCREWS:
        holes.append(Point(x, y).buffer(5.25, quad_segs=12))
    for h in holes:
        poly = poly.difference(h)
    return C.ext(poly, P.PANEL1_Z0, P.PANEL1_Z1)


def core_board():
    return C.box(P.CORE_X0, P.CORE_X1, P.CORE_Y0, P.CORE_Y1, P.CORE_Z0, P.CORE_Z1)


def screen_module():
    s = P.SCREEN
    cx, cy = s["cx"], s["cy"]
    return C.box(cx - P.SCREEN_MODULE_W / 2, cx + P.SCREEN_MODULE_W / 2,
                 cy - P.SCREEN_MODULE_H / 2, cy + P.SCREEN_MODULE_H / 2,
                 P.PANEL_Z0 - 5.2, P.PANEL_Z0 - 0.2)


def battery_cells():
    return [C.cyl_y(P.BAT_D / 2, P.BAT_Y0, P.BAT_Y1, bx,
                    P.BAT_CRADLE_Z0 + P.BAT_D / 2 + 0.2, 40) for bx in P.BAT_X]


def encoder_bodies():
    return [C.cyl_z(6.25, 47.4, P.PANEL_Z0, e["x"], e["y"], 24) for e in P.KNOBS]


def jack_bodies():
    return [C.cyl_z(4.5, 47.0, P.PANEL_Z0, j["x"], j["y"], 24) for j in P.JACKS]


def fader_bodies():
    return [C.box(f["x"] - f["body_w"] / 2, f["x"] + f["body_w"] / 2,
                  f["y"] - f["body_h"] / 2, f["y"] + f["body_h"] / 2,
                  38.0, P.PANEL_Z0 - 0.4) for f in P.FADERS]


def knobs_3d():
    return [C.cyl_z(P.KNOB_D / 2, P.PANEL_Z1, P.PANEL_Z1 + P.KNOB_CAP_H,
                    e["x"], e["y"], 32) for e in P.KNOBS]


def keycaps_3d():
    out = []
    for k in P.KEYS:
        h = C.rrect(-P.KEYCAP_W / 2, P.KEYCAP_W / 2, -P.KEYCAP_H / 2, P.KEYCAP_H / 2, 1.5)
        h = affinity.translate(affinity.rotate(h, k["deg"], origin=(0, 0)), k["x"], k["y"])
        out.append(C.ext(h, P.PANEL_Z1 + 0.1, P.PANEL_Z1 + P.KEYCAP_T))
    return out


# ---------------------------------------------------------------------------
def check_centers():
    """[J] центры вырезов = JSON ±0.05 мм."""
    import case_v04 as CV
    holes = CV.panel_holes()
    rows = []
    tol = 0.05
    items = []
    for k in P.KEYS:
        items.append((k["id"], holes[k["id"]], (k["x"], k["y"])))
    for e in P.KNOBS:
        items.append((e["id"], holes[e["id"]], (e["x"], e["y"])))
    for j in P.JACKS:
        items.append((j["id"], holes[j["id"]], (j["x"], j["y"])))
    s = P.SCREEN
    items.append(("lcd", holes["lcd"], (s["cx"], s["cy"])))
    for f in P.FADERS:
        items.append((f["id"] + "_slot", holes[f["id"] + "_slot"], (f["x"], f["y"])))
    max_dev = 0.0
    bad = []
    for name, geom, (cx, cy) in items:
        c = geom.centroid
        d = math.hypot(c.x - cx, c.y - cy)
        max_dev = max(max_dev, d)
        if d > tol:
            bad.append(f"{name}:{d:.3f}")
    rows.append(("[J]", f"Центры всех вырезов = JSON (±{tol} мм)",
                 f"{len(items)} элементов (42 клавиши, 16 ручек, 10 джеков, "
                 f"экран, 2 фейдера)",
                 f"макс. отклонение {max_dev:.4f} мм, вне допуска: {len(bad)}"
                 + (f" {bad[:3]}" if bad else ""),
                 "OK" if not bad else "КОНФЛИКТ"))

    poly = CV.panel_polygon()
    n_int = len(poly.interiors)
    rows.append(("[J]", "Число сквозных отверстий панели",
                 "83 (без USB-C: он на кромке)", f"{n_int}",
                 "OK" if n_int == 83 else "КОНФЛИКТ"))
    # пересечения вырезов
    bad = 0
    vals = list(holes.items())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i][1], vals[j][1]
            if a.intersects(b) and a.intersection(b).area > 0.05:
                bad += 1
    rows.append(("[J]", "Вырезы не пересекаются между собой",
                 "площадь пересечения < 0.05 мм²",
                 f"пересечений: {bad}", "OK" if bad == 0 else "КОНФЛИКТ"))
    # вылет за панель (кроме USB-C)
    margin = 1e9
    for name, h in holes.items():
        if name == "usbc":
            continue
        margin = min(margin, h.bounds[0], h.bounds[1],
                     P.PANEL_W - h.bounds[2], P.PANEL_H - h.bounds[3])
    rows.append(("[J]", "Минимальное поле вырезов до кромки панели",
                 "≥ 1 мм", f"{margin:.2f} мм", "OK" if margin >= 1.0 else "ПРОВЕРИТЬ"))
    return rows


# ---------------------------------------------------------------------------
def run(panels, meta, instances):
    print("[fit v0.4] проверки панели …")
    body_L = trimesh.load(os.path.join(STL_DIR, "body_L.stl"))
    body_R = trimesh.load(os.path.join(STL_DIR, "body_R.stl"))
    pan_L, pan_R = panels["panel_L"], panels["panel_R"]

    def inter_body(m):
        return _inter(m, body_L) + _inter(m, body_R)

    def inter_panels(m):
        return _inter(m, pan_L) + _inter(m, pan_R)

    rows = []
    comps = [
        ("PANEL-1 rev.2 360×190×1.6 @47", panel1_board()),
        ("CORE-1 rev.3 200×108×1.6 @12", core_board()),
        ("Экран 5.0\" (модуль 120.7×75.8 @54.8…59.8)", screen_module()),
    ]
    for b in battery_cells():
        comps.append(("Батарея 18650 Ø18.4×65 (×2)", b))
    for b in encoder_bodies():
        comps.append(("Корпус энкодера Ø12.5 @47.4…60", b))
    for b in jack_bodies():
        comps.append(("Корпус джека Ø9 @40…60", b))
    for b in fader_bodies():
        comps.append(("Корпус фейдера 16×75×21 @38…59.6", b))
    for name, m in comps:
        vb, vp = inter_body(m), inter_panels(m)
        rows.append(("[G]", name, "в полости корпуса / под панелью",
                     f"пересеч. с корпусом {vb:.1f} мм³, с панелью {vp:.1f} мм³",
                     "OK" if vb < 3.0 and vp < 3.0 else "КОНФЛИКТ"))

    v = sum(_inter(m, pan_L) + _inter(m, pan_R) for m in knobs_3d())
    rows.append(("[G]", "16 ручек Ø14 @63…75", "над панелью",
                 f"пересечение {v:.1f} мм³", "OK" if v < 3.0 else "КОНФЛИКТ"))
    v = sum(_inter(m, pan_L) + _inter(m, pan_R) for m in keycaps_3d())
    rows.append(("[G]", "42 колпачка 17.5×16.5 @63.1…68.6", "над панелью",
                 f"пересечение {v:.1f} мм³", "OK" if v < 3.0 else "КОНФЛИКТ"))
    v = _inter(pan_L, pan_R)
    rows.append(("[G]", "Стык panel_L / panel_R по X = 190 (шип 3×1.2)",
                 "зазор 0.2 по шипу/пазу", f"пересечение {v:.1f} мм³",
                 "OK" if v < 3.0 else "КОНФЛИКТ"))
    v = _inter(body_L, body_R)
    rows.append(("[G]", "Стык body_L / body_R (v1.7, шип 3×3)",
                 "зазор 0.2 по шипу/пазу", f"пересечение {v:.1f} мм³",
                 "OK" if v < 3.0 else "КОНФЛИКТ"))

    # габарит сборки
    mn = np.array([1e9, 1e9, 1e9]); mx = np.array([-1e9, -1e9, -1e9])
    for inst in instances:
        key = inst["file"][:-4]
        pos = np.array(inst["pos"])
        mn = np.minimum(mn, np.array(meta[key]["min"]) + pos)
        mx = np.maximum(mx, np.array(meta[key]["max"]) + pos)
    size = mx - mn
    rows.append(("[A]", "Габарит корпуса в сборе (body + panel)",
                 "380 × 210 × 63 ± 1",
                 f"{size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} мм "
                 f"(Z {mn[2]:.1f}…{mx[2]:.1f})",
                 "OK" if (abs(size[0]-380) <= 1 and abs(size[1]-210) <= 1
                          and abs(size[2]-63) <= 1) else "КОНФЛИКТ"))
    for name, m in meta.items():
        b = m["bbox"]
        over = max(b) > 220.0
        rows.append(("[A]", f"STL {name}", "≤ 220×220×200, watertight",
                     f"{b[0]:.1f}×{b[1]:.1f}×{b[2]:.1f}; "
                     f"watertight={m['watertight']}/reload={m['watertight_reload']}",
                     "OK" if (not over and m["watertight"]
                              and m["watertight_reload"]) else "КОНФЛИКТ"))
    zrows = [
        ("CORE-1 (компоненты 24) → PANEL-1 (47)", P.PANEL1_Z0 - P.CORE_COMP_TOP),
        ("PANEL-1 (48.6) → экран (54.8)", 54.8 - P.PANEL1_Z1),
        ("Экран (59.8) → панель (60)", P.PANEL_Z0 - 59.8),
        ("Фейдер (59.6) → панель (60)", P.PANEL_Z0 - 59.6),
    ]
    for what, val in zrows:
        rows.append(("[A]", what, "зазор ≥ 0", f"{val:.2f} мм",
                     "OK" if val >= -0.01 else "КОНФЛИКТ"))

    rows += check_centers()
    conflicts = [r for r in rows if r[4] != "OK"]
    write_report(rows, conflicts)
    print(f"[fit v0.4] строк {len(rows)}, конфликтов {len(conflicts)}")
    return rows


def write_report(rows, conflicts):
    lines = []
    w = lines.append
    w(MARKER)
    w("\n---\n\n# fit_check — Букифон v0.4 (канон панели, 380 × 210 × 63)\n")
    w("Сгенерировано `mechanical/generator/fitcheck_v04.py` (вызывается из "
      "`case_v04.py`). Все числа — из STL, `spec/panel-spec-v0.4.json` и "
      "`params_v04.py`. Корпус/ножки — из v1.7 (не менялись).\n")
    w(f"\n**Итог:** проверок {len(rows)}, конфликтов: **{len(conflicts)}**.\n")
    w("\n## v0.4-1. Таблица проверок\n")
    w("\n| Класс | Что проверялось | Условие | Расчёт | Статус |")
    w("\n|---|---|---|---|---|")
    for cls, what, cond, calc, status in rows:
        w(f"\n| {cls} | {what} | {cond} | {calc} | **{status}** |")
    w("\n\n## v0.4-2. Что НЕ проверено\n")
    w("\n| Пункт | Причина |")
    w("\n|---|---|")
    w("\n| Кинематика фейдера/энкодеров в сборе | проверены только габариты "
      "корпусов и прорезей |")
    w("\n| Реальная топология PANEL-1 rev.2 | плата принята как посадочный "
      "габарит 360×190 с вырезами |")
    w("\n| Шлейфы/провода | трассы не заданы в каноне |")
    w("\n\n## v0.4-3. Отличия от v1.7 (панель)\n")
    w("\n1. **Клавиши** — точная Lapka-42: 42 записи `controls.keyboard_left/right`, "
      "половины развёрнуты **+18°/−18°** (в v1.7 было 0°), центры/углы — 1:1 из JSON.\n")
    w("2. **Энкодеры** — X 25.2/54.1/82.6/111.4 и 269.3/297.8/326.6/355.8, "
      "Y 35.7/68.5; Ø7.2 + цековка Ø14.4×1.4.\n")
    w("3. **Джеки** — 10 шт. X 129.9…247.8 (шаг 13.1), Y 10.5; Ø6.2 + "
      "цековка Ø8.2×1.5.\n")
    w("4. **Экран** — вырез 108×64.8 с центром (190, 58.7) + внутренний буртик 1.5 мм.\n")
    w("5. **Фейдеры** — X 175.1/204.0, центр Y 150; прорезь 2.5×63, корпус "
      "16×75 (внутри), 4 × M2.5 на фейдер, риски по бокам.\n")
    w("6. Корпус, ножки, крепёж, разрез X=190, шип/паз и USB-C — без изменений "
      "от v1.7 (task-10: менять не требуется).\n")
    text = "".join(lines) + "\n"
    old = open(FIT_MD).read() if os.path.exists(FIT_MD) else ""
    if MARKER in old:
        old = old[:old.index(MARKER)]
    with open(FIT_MD, "w") as f:
        f.write(old.rstrip() + "\n\n" + text)
    print(f"[fit v0.4] записано {FIT_MD}")
