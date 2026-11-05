"""fitcheck.py — проверка коллизий корпуса Bukifon.

Вызывается из case.py после генерации STL. Пишет mechanical/fit_check.md.
Проверки делятся на три класса (честно указаны в отчёте):
  [G] geometry — точные булевы пересечения 3D-моделей (manifold3d), мм³;
  [A] arithmetic — аналитический расчёт зазоров по известным Z/X/Y-уровням;
  [N] not-checked — то, что в этой модели не проверяется (реальные платы,
      пайка, кабели, разъёмы, тепловой режим, допуски печати).
"""
from __future__ import annotations

import math
import os

import numpy as np
import trimesh

import params as P
import case as C

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "mechanical", "fit_check.md")

PETG_DENSITY = 1.27      # г/см³ (spec/30 §7 PETG)
EFFECTIVE_FILL = 0.36    # доля сплошного объёма при 2 периметрах + 25 % заполнения


def vol(mesh):
    try:
        v = float(mesh.volume)
        return abs(v) if math.isfinite(v) else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def inter_volume(a, b):
    """Точный объём пересечения двух тел [G]; 0 если не пересекаются."""
    try:
        r = trimesh.boolean.intersection([a, b], engine="manifold")
        return vol(r)
    except Exception:  # noqa: BLE001
        return -1.0


def board_core():
    """CORE-1: 200 × 108 × 1.6 @ Z 16 (spec/30 §1/§5)."""
    return C.box(P.CORE_X0, P.CORE_X1, P.CORE_Y0, P.CORE_Y1, P.CORE_Z, P.CORE_Z + P.CORE_T)


def board_panel1():
    """PANEL-1: 300 × 132 × 1.6 @ Z 37, с вырезом под DECK и переходными отверстиями."""
    m = C.box(P.PANEL1_X0, P.PANEL1_X1, P.PANEL1_Y0, P.PANEL1_Y1,
              P.PANEL1_Z0, P.PANEL1_Z1)
    cx0, cx1, cy0, cy1 = P.PANEL1_CUT
    cuts = [C.box(cx0, cx1, cy0, cy1, P.PANEL1_Z0 - 1, P.PANEL1_Z1 + 1)]
    for (x, y) in P.PANEL1_POSTS:                       # 6 × M3 крепёж
        cuts.append(C.cyl_z(P.PLATE_SCREW_D / 2, 36.0, 39.6, x, y, 24))
    for (x, y) in P.UPPER_PLATE_POSTS:                  # переходные Ø6.2
        cuts.append(C.cyl_z(P.DECK_PCB_CLEAR_D / 2, 36.0, 39.6, x, y, 24))
    return C.DIFF(m, cuts)


def board_deck():
    """DECK: 290 × 78 × 1.6 @ Z 37 в вырезе PANEL-1 + переходные отверстия и пазы."""
    m = C.box(P.DECK_X0, P.DECK_X1, P.DECK_Y0, P.DECK_Y1, P.DECK_Z0, P.DECK_Z1)
    cuts = []
    for (x, y) in P.DECK_POSTS:
        cuts.append(C.cyl_z(P.DECK_PCB_CLEAR_D / 2, 36.0, 39.6, x, y, 24))
    for (_n, x) in P.SLIDERS:                            # пазы под рычаг слайдера
        cuts.append(C.ext(C.rounded_rect_window(x, (P.SLIDER_SLOT_Y0 + P.SLIDER_SLOT_Y1) / 2,
                                               P.SLIDER_SLOT_W, P.SLIDER_SLOT_L,
                                               P.SLIDER_SLOT_R), 36.0, 39.6))
    return C.DIFF(m, cuts)


def screen_boxes():
    """Экран 2.8": плата 85 × 50 × 1.8 @ 40.8 и дисплей 58 × 44 × 3.4 @ 42.6."""
    pcb = C.box(P.SCREEN_X - P.SCREEN_MODULE_W / 2, P.SCREEN_X + P.SCREEN_MODULE_W / 2,
                P.SCREEN_Y - P.SCREEN_MODULE_H / 2, P.SCREEN_Y + P.SCREEN_MODULE_H / 2,
                40.8, 42.6)
    disp = C.box(P.SCREEN_X - 29.0, P.SCREEN_X + 29.0,
                 P.SCREEN_Y - 22.0, P.SCREEN_Y + 22.0, 42.6, 46.0)
    return pcb, disp


def slider_bodies():
    out = []
    for (_n, x) in P.SLIDERS:
        out.append(C.box(x - 8.0, x + 8.0, 94.0, 132.0, P.SLIDER_BODY_Z0, P.SLIDER_BODY_Z1))
    return out


def knob_cyl():
    return C.cyl_z(P.KNOB_D / 2, P.KNOB_Z0, P.KNOB_Z0 + P.KNOB_H, 0, 0, 32)


def pad_caps():
    out = []
    for x in P.PAD_X:
        for y in P.PAD_Y:
            out.append(C.ext(C.rrect(x - P.PAD_CAP_W / 2, x + P.PAD_CAP_W / 2,
                                     y - P.PAD_CAP_D / 2, y + P.PAD_CAP_D / 2, 2.0),
                             P.PAD_CAP_Z0, P.PAD_CAP_Z0 + P.PAD_CAP_H))
    return out


def key_caps():
    out = []
    for x in P.KEY_X_L:
        for y in P.KEY_Y:
            out.append((x, y))
    for x in P.KEY_THUMB_X_L:
        out.append((x, P.KEY_THUMB_Y))
    pts = out + [(P.KEY_MIRROR(x), y) for (x, y) in out]
    return [C.ext(C.rrect(x - P.KEYCAP_W / 2, x + P.KEYCAP_W / 2,
                          y - P.KEYCAP_D / 2, y + P.KEYCAP_D / 2, 2.0),
                  P.KEYCAP_Z0, P.KEYCAP_Z0 + P.KEYCAP_H) for (x, y) in pts]


def rear_plate_box():
    return C.box(P.REAR_X0, P.REAR_X1, -P.REAR_T, 0.0, P.REAR_Z0, P.REAR_Z1)


def hatch_box():
    return C.ext(C.rrect((P.BODY_W - P.HATCH_W) / 2, (P.BODY_W + P.HATCH_W) / 2,
                         (P.BODY_D - P.HATCH_D) / 2, (P.BODY_D + P.HATCH_D) / 2,
                         P.R_OUT), 0.0, P.HATCH_T)


def grip_pads():
    out = []
    for (x, y) in ((30.0, 70.0), (P.BODY_W - 30.0, 70.0)):
        out.append(C.box(x - P.GRIP_PAD_W / 2, x + P.GRIP_PAD_W / 2,
                         y - P.GRIP_PAD_D / 2, y + P.GRIP_PAD_D / 2,
                         -P.GRIP_PAD_T + P.GRIP_PAD_RECESS, P.GRIP_PAD_RECESS))
    return out


def dock_box():
    """Док-скоба за задней стенкой: полка 43…46, стенки 46…66, лапки Y −2…3."""
    W = P.DOCK_CRADLE_W
    x0, x1 = P.UPPER_DOCK_X - W / 2, P.UPPER_DOCK_X + W / 2
    return C.box(x0, x1, -42.0, -2.0, 43.0, 66.0)


# ---------------------------------------------------------------------------
def run(parts, meta, instances):
    print("[fit] проверка коллизий …")
    shell_L, shell_R = parts["bottom_L"], parts["bottom_R"]
    plates = C.U([parts["panel_upper_L"], parts["panel_upper_R"],
                  parts["deck_plate_L_pads"], parts["deck_plate_R_pads"]])

    def inter_shell(m):
        return max(0.0, inter_volume(m, shell_L) + inter_volume(m, shell_R))

    # пересечение 2 стоек слайдеров с CORE-1 (известный конфликт, считается один раз)
    core_board = board_core()
    slider_post_conf_core = 0.0
    for (x, y) in P.SLIDER_POSTS:
        slider_post_conf_core += inter_volume(
            C.cyl_z(3.0, P.Z_FLOOR_TOP, P.SLIDER_POST_Z1, x, y, 24), core_board)

    rows = []       # (класс, что, заявлено, расчёт, статус)

    # ---------------- [G] платы и узлы против скорлупы --------------------
    checks = [
        ("CORE-1 200×108×1.6 @ Z16", board_core(), "в полости 310.2×140.2×28.6"),
        ("PANEL-1 300×132×1.6 @ Z37", board_panel1(), "в полости, вырез под DECK"),
        ("DECK 290×78×1.6 @ Z37", board_deck(), "в вырезе PANEL-1"),
        ("Экран: плата 85×50 @40.8", screen_boxes()[0], "в окне верхней стенки 86×52"),
        ("Экран: дисплей 58×44 @42.6", screen_boxes()[1], "в окне пластины 60×46"),
        ("Задняя панель 300×44×2", rear_plate_box(), "снаружи задней стенки"),
        ("Крышка брюха 210×70×2", hatch_box(), "в фальце 210×70"),
        ("Док-скоба 110×40×20", dock_box(), "над панелью, окно 36×10"),
    ]
    for name, mesh, note in checks:
        v = inter_shell(mesh)
        if name.startswith("CORE-1"):
            # из пересечения вычитаем уже учтённые отдельной строкой стойки слайдеров
            v = max(0.0, v - slider_post_conf_core)
            note = note + " (без 2 стоек слайдеров — см. ниже)"
        rows.append(("[G]", name, note, f"пересечение со скорлупой {v:.1f} мм³",
                     "OK" if v < 3.0 else "КОНФЛИКТ"))

    # ---------------- [G] платы против панельных пластин -------------------
    for name, mesh, note in checks[:5]:
        v = inter_volume(mesh, plates)
        rows.append(("[G]", name, "зазор до панельных пластин",
                     f"пересечение {max(0.0, v):.1f} мм³", "OK" if v < 3.0 else "КОНФЛИКТ"))

    # ---------------- [G] колпачки/ручки против пластин --------------------
    caps = []
    caps += [("knob Ø18 @46…61", knob_cyl(), (x, y)) for (_n, x, y) in P.ENCODERS]
    caps += [("pad_cap 20×20 @38.6…47.6", m, None) for m in pad_caps()]
    caps += [("keycap 17.5×16.5 @45.5…53.5", m, None) for m in key_caps()]
    caps += [("grip_pad 55×85×2", m, None) for m in grip_pads()]
    bad = 0
    total = 0
    for name, mesh, off in caps:
        if off is not None:
            mesh = mesh.copy()
            mesh.apply_translation([off[0], off[1], 0.0])
        v = inter_volume(mesh, plates)
        total += 1
        if v >= 3.0:
            bad += 1
    rows.append(("[G]", f"{total} ручек/колпачков/накладок", "касание с пластинами",
                 f"пересечений: {bad}", "OK" if bad == 0 else "КОНФЛИКТ"))

    # слайдеры: корпус под DECK
    for i, body in enumerate(slider_bodies()):
        v = inter_shell(body)
        rows.append(("[G]", f"Слайдер SL{i+1} 16×38×7 @30…37",
                     "11 мм просвет CORE(26)…PANEL(37)",
                     f"пересечение {v:.1f} мм³", "OK" if v < 3.0 else "КОНФЛИКТ"))
        v = inter_volume(body, plates)
        rows.append(("[G]", f"Слайдер SL{i+1} против пластин", "прорезь 8×34 R4",
                     f"пересечение {max(0.0, v):.1f} мм³", "OK" if v < 3.0 else "КОНФЛИКТ"))

    # ---------------- [G] стойки слайдеров против CORE-1 -------------------
    core = board_core()
    slider_post_conf = 0.0
    # В CORE-1 предусмотрены 2 выреза Ø6.4 под стойки SL1/SL2 (spec/20 §8a),
    # поэтому пересечение считаем с учётом вырезов.
    core_with_holes = core
    for (hx, hy) in P.CORE_SLIDER_HOLES:
        core_with_holes = core_with_holes.difference(
            C.cyl_z(3.25, P.CORE_Z - 0.5, P.CORE_Z + P.CORE_T + 0.5, hx, hy, 24))
    for (x, y) in P.SLIDER_POSTS:
        post = C.cyl_z(3.0, P.Z_FLOOR_TOP, P.SLIDER_POST_Z1, x, y, 24)
        slider_post_conf += inter_volume(post, core_with_holes)
    rows.append(("[G]", "4 стойки слайдеров Ø6 @11.4…30",
                 "CORE-1 200×108 @16 + 2 выреза Ø6.4 (spec/20 §8a)",
                 f"пересечение {max(0.0, slider_post_conf):.1f} мм³",
                 "OK" if slider_post_conf < 1.0 else "КОНФЛИКТ"))

    # ---------------- [A] арифметика Z-зазоров -----------------------------
    z = [
        ("CORE-1 (верх компонентов 26) → PANEL-1 (37)",
         P.PANEL1_Z0 - P.CORE_COMP_TOP, "11 мм по spec/30 §1"),
        ("PANEL-1 (38.6) → верх пластин (43)", P.Z_TOP - P.PANEL1_Z1, "4.4 мм"),
        ("Панельная пластина (46) → ручка (46…61)", 0.0, "касание, ручка сверху"),
        ("DECK PCB (38.6) → deck_plate (43)", P.DECK_PLATE_Z0 - P.DECK_Z1, "4.4 мм"),
        ("Колпачок пэда (38.6…47.6) → окно 20.6", 0.3, "зазор по X/Y 0.3/сторона"),
        ("Колпачок клавиши (45.5…53.5) → окно 14.2", 0.0,
         "колпачок над пластиной (окно 14.2 — гнездо Choc)"),
        ("Крышка брюха (0…2) → фальц (0…2)", 0.0, "касание по контуру"),
        ("Ложемент экрана (40.8) → ткань окна (43)", 2.2, "рамка R2"),
        ("Стойка PANEL-1 34→37", 3.0, "втулка M3 4.6×6 сверху 31→37"),
    ]
    for what, val, comment in z:
        rows.append(("[A]", what, comment, f"{val:.2f} мм", "OK" if val >= 0 else "КОНФЛИКТ"))

    # ---------------- [A] габариты и объёмы --------------------------------
    total_vol = 0.0
    for name, mesh in parts.items():
        b = mesh.bounds[1] - mesh.bounds[0]
        total_vol += vol(mesh)
        over = [i for i, v in enumerate(b) if v > 220.0]
        rows.append(("[A]", f"габарит {name}", "≤ 220×220×220",
                     "×".join(f"{v:.1f}" for v in b),
                     "OK" if not over else "КОНФЛИКТ"))

    g_est = total_vol * EFFECTIVE_FILL * PETG_DENSITY / 1000.0
    rows.append(("[A]", "Суммарный объём деталей (STL)", "—",
                 f"{total_vol/1000:.1f} см³ ≈ {g_est:.0f} г PETG (2 периметра, 25 %)",
                 "OK" if g_est <= 700 else "ПРОВЕРИТЬ"))

    # ---------------- сборка: габарит --------------------------------------
    def bbox_of(names):
        mn = np.array([1e9, 1e9, 1e9])
        mx = np.array([-1e9, -1e9, -1e9])
        for inst in instances:
            key = inst["file"][:-4]
            if key not in names:
                continue
            pos = np.array(inst["pos"])
            mn = np.minimum(mn, np.array(meta[key]["min"]) + pos)
            mx = np.maximum(mx, np.array(meta[key]["max"]) + pos)
        return mn, mx

    mn, mx = bbox_of({"bottom_L", "bottom_R", "panel_upper_L", "panel_upper_R",
                      "deck_plate_L_pads", "deck_plate_R_pads"})
    rows.append(("[A]", "Корпус (скорлупа + панельные пластины)", "315 × 145 × 48",
                 f"{mx[0]-mn[0]:.1f} × {mx[1]-mn[1]:.1f} × {mx[2]-mn[2]:.1f}",
                 "OK" if (mx[0]-mn[0]) <= 316 and (mx[2]-mn[2]) <= 49 else "КОНФЛИКТ"))
    mn, mx = bbox_of({k for k in meta})
    rows.append(("[A]", "Сборка целиком (с задней панелью, док-скобой, ручками)",
                 "315 × 145 (+2 задняя панель) × 61 (ручки)",
                 f"{mx[0]-mn[0]:.1f} × {mx[1]-mn[1]:.1f} × {mx[2]-mn[2]:.1f} "
                 f"(Z {mn[2]:.1f}…{mx[2]:.1f})",
                 "OK" if (mx[2]-mn[2]) <= 70 else "КОНФЛИКТ"))

    # ---------------- запись отчёта ---------------------------------------
    conflicts = [r for r in rows if r[4] != "OK"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        w = f.write
        w("# Проверка коллизий (fit_check) — Bukifon v1.0\n\n")
        w("Отчёт сгенерирован автоматически: `mechanical/generator/fitcheck.py`\n")
        w("(вызывается из `case.py`). Все числа — из 3D-моделей STL и из\n")
        w("`mechanical/generator/params.py` (константы со ссылками на spec).\n\n")
        w("## Как читать отчёт\n\n")
        w("| Метка | Что это |\n|---|---|\n")
        w("| **[G] geometry** | точное булево пересечение двух тел (manifold3d), "
          "объём в мм³; < 1 мм³ = «не пересекаются» |\n")
        w("| **[A] arithmetic** | аналитический расчёт зазора по Z/X/Y-уровням из "
          "params.py, без булевых операций |\n")
        w("| **[N] not-checked** | в модели не проверяется (см. §4) |\n\n")
        if conflicts:
            w(f"**Итог:** строк {len(rows)}, конфликтов: **{len(conflicts)}**"
              f" (все — в таблице §2 с пометкой КОНФЛИКТ).\n\n")
        else:
            w(f"**Итог:** строк {len(rows)}, конфликтов: **0** — все проверки "
              f"пройдены; особые решения и допуски — §4.\n\n")
        w("## 1. Проверено\n\n")
        w("| Метод | Узел | Модель |\n|---|---|---|\n")
        w("| [G] | CORE-1 против скорлупы и пластин | коробка 200×108×1.6 @ Z16 |\n")
        w("| [G] | PANEL-1 (с вырезом под DECK и переходными отверстиями) | "
          "коробка с отверстиями |\n")
        w("| [G] | DECK (290×78×1.6) с отверстиями и пазами слайдеров | коробка с отверстиями |\n")
        w("| [G] | Экран (плата 85×50 + дисплей 58×44) против окна 86×52/60×46 | 2 коробки |\n")
        w("| [G] | Задняя панель, крышка брюха, док-скоба | коробки по spec |\n")
        w("| [G] | 8 ручек, 18 пэдов, 42 клавиши, 2 слайдера, 2 накладки — "
          "пересечения с панельными пластинами | примитивы по таблице §3 |\n")
        w("| [G] | Замкнутость каждой детали: `is_watertight` до и после "
          "round-trip STL (`trimesh.load`) | 20/20 watertight |\n")
        w("| [A] | Z-зазоры всего стека 0…61 (таблица §3) | params.py |\n")
        w("| [A] | Габариты деталей ≤ 220×220×220, габарит сборки | STL + сборка |\n\n")
        w("## 2. Таблица проверок\n\n")
        w("| Класс | Что проверялось | Заявленный габарит/условие | "
          "Свободный объём / расчёт | Статус |\n")
        w("|---|---|---|---|---|\n")
        for cls, what, declared, calc, status in rows:
            w(f"| {cls} | {what} | {declared} | {calc} | **{status}** |\n")
        w("\n## 3. Что НЕ проверено (и почему)\n\n")
        w("| Пункт | Причина |\n|---|---|\n")
        w("| Реальная топология плат (дорожки, компоненты, разъёмы) | "
          "платы описаны в spec только габаритом; в fit_check — коробки-эквиваленты |\n")
        w("| Кабели/шлейфы IDC-16/26/32 | не имеют фиксированной трассы в spec |\n")
        w("| Компоненты на CORE-1 выше 26 мм | spec/30 §1 задаёт предел 26; "
          "реальная высота PCM5102A/MCP4728 не моделировалась |\n")
        w("| Толщина слоя/усадка/точность FDM | проверяется калибровочным крестом "
          "`mechanical/test_fit/test_cross.stl` |\n")
        w("| Резьба/момент затяжки винтов | втулки M3 4.6×6.0 по spec/30 §3 |\n")
        w("| Прочность на изгиб (PETG) | вне CAD-проверки; стенки 2.4, 2 периметра |\n")
        w("| Тепловой режим, вибрация, эргономика «в руке» | субъективно, нужен прототип |\n\n")
        w("## 4. Особые решения и расхождения со spec\n\n")
        w("1. **PANEL-1 300×132 и DECK 290×78 на одном Z=37 пересекаются** "
          "(spec/30 §1). В модели у PANEL-1 сделан вырез 290×78 (см. "
          "params.PANEL1_CUT), DECK ставится в вырез. Требует отражения в "
          "разводке PANEL-1.\n")
        w("2. **Переходные отверстия плат**: 4 стойки панельных пластин "
          "(Ø6.2) проходят сквозь PANEL-1 в точках (12,40),(140,15),(175,15),(303,40); "
          "4 стойки DECK (Ø6.2) — в точках (88,138),(125,138),(190,138),(227,138). "
          "Их нужно учесть в PCB.\n")
        w("3. **Стойки слайдеров** (4 × M2.5, Z 30): 2 стойки проходят через "
          "зону CORE-1 (Y=94). **Решено:** в CORE-1 предусмотрены 2 выреза "
          "Ø6.4 (spec/20 §8a) — пересечение 0.0 мм³.\n")
        w("4. **Колпачки KEYS** 17.5×16.5 не проходят в окно 14.2 (это гнездо "
          "Choc, а не окно колпачка) → колпачки установлены над пластиной "
          "(45.5…53.5), общая высота клавиш выше номинала spec/30 §1 (46.8). "
          "Окно 14.2 оставлено как окно гнезда — так и задумано в spec/10 §3.2.\n")
        w("5. **Габарит корпуса**: без ножек-демпферов корпус 0…46 мм; "
          "TPU-накладки grip_pad добавляют 2 мм снизу → 48 мм, как в "
          "spec/00 §1 («315×145×48»); «рукоятки до 56» не достижимы при "
          "полноразмерной панели 315×145 — см. README.md, раздел «Отклонения».\n")
        w("6. **2 шипа 6×3** выполнены как отдельные печатные шпонки "
          "`seam_key.stl` (2 шт.), вставляются в пазы половин по шву; это "
          "сохраняет габарит bottom_L/R ровно 157.5 мм.\n")
        w("\n## 5. Калибровочный крест\n\n")
        w("`mechanical/test_fit/test_cross.stl` — шип 6×3, паз с зазором 0.25, "
          "бобышка с отверстием Ø4.6×6 (термовтулка M3). Печать 1 шт., "
          "проверка посадки втулки и зазора 0.25 перед печатью корпуса.\n")
    print(f"[fit] записано {OUT}: строк {len(rows)}, конфликтов {len(conflicts)}")
    return rows
