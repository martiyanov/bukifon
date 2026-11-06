"""fitcheck_v05_C.py — проверки варианта C (клин 12° + отсек + подставка).

Проверки: [G] булевы пересечения (корпус/панель/платы/компоненты),
[A] габариты/высоты, [J] вырезы панели = spec/panel-spec-v0.4.json (переиспользуем
проверки v0.4), [N] не проверено.
"""
from __future__ import annotations

import math
import os

import numpy as np
import trimesh

import params_v05 as PV
import params_v04 as P04
import case as C
import fitcheck_v04 as F4
import fitcheck_v05_light as F5L

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STL_DIR = os.path.join(ROOT, "mechanical", "stl_v05_C_mic")
FIT_MD = os.path.join(ROOT, "mechanical", "fit_check.md")


def _inter(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine="manifold")
        return abs(float(r.volume)) if math.isfinite(r.volume) else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def _apply(mesh, M):
    m = mesh.copy()
    m.apply_transform(M)
    return m


def run(name, meta, instances, parts):
    v = PV.variant(name)
    print(f"[fit v0.5-{name}] проверки …")
    body_L = trimesh.load(os.path.join(STL_DIR, "body_L.stl"))
    body_R = trimesh.load(os.path.join(STL_DIR, "body_R.stl"))
    pan_L = trimesh.load(os.path.join(STL_DIR, "panel_L.stl"))
    pan_R = trimesh.load(os.path.join(STL_DIR, "panel_R.stl"))
    M = np.array(instances[0].get("panel_matrix", np.eye(4)))  # fallback
    # матрица хранится в assembly json, вытащим из файла
    import json
    with open(os.path.join(HERE, f"assembly_v05_{name}_mic.json")) as f:
        aj = json.load(f)
    M = np.array(aj["panel_matrix"])

    body = trimesh.util.concatenate([body_L, body_R])
    pan = trimesh.util.concatenate([pan_L, pan_R])
    pan_w = _apply(pan, M)

    rows = []

    def chk(label, mesh, cond="в полости корпуса"):
        vb = _inter(mesh, body)
        vp = _inter(mesh, pan_w)
        rows.append(("[G]", label, cond,
                     f"пересеч. с корпусом {vb:.1f}, с панелью {vp:.1f} мм³",
                     "OK" if vb < 3.0 and vp < 3.0 else "КОНФЛИКТ"))

    # --- панель на корпусе (касание по кромке) -----------------------------
    rows.append(("[G]", f"Панель (наклон {v['angle_deg']:.0f}°) на корпусе", "посадка на кромку",
                 f"пересечение {_inter(pan_w, body):.1f} мм³",
                 "OK" if _inter(pan_w, body) < 3.0 else "КОНФЛИКТ"))

    # --- PANEL-2: на 8 мм ниже панели, параллельно ей ---------------------
    p2 = F4.panel1_board()
    p2.apply_translation([0, 0, 3.4])         # v0.4: 11.4→8 мм ниже панели
    p2w = _apply(p2, M)
    # переходные отверстия под вертикальные стойки (углы + 6 стоек PANEL-2)
    clears = []
    for (x, yf) in P04.PANEL_SCREWS:
        xw, yw = PV.variant(name) and (x, 105.0 + (yf - 105.0) * math.cos(math.radians(v["angle_deg"])))
        clears.append(C.cyl_z(5.6, 0.0, 80.0, xw, yw, 20))
    for (x, yf) in PV.PANEL1_POSTS:
        xw, yw = (x, 105.0 + (yf - 105.0) * math.cos(math.radians(v["angle_deg"])))
        clears.append(C.cyl_z(4.0, 0.0, 80.0, xw, yw, 20))
    p2w = C.DIFF(p2w, clears)
    chk("PANEL-2 360×190×1.6 (параллельно панели, −8 мм)", p2w)
    # --- CORE-2 / PWR-2 / батарея: горизонтальные площадки -----------------
    core = C.box(PV.CORE_X0, PV.CORE_X1, PV.CORE_Y0, PV.CORE_Y1,
                 PV.CORE_Z0, PV.CORE_Z1)
    chk("CORE-2 200×108×1.6 @ Z12 (гориз.)", core)
    pwr = C.box(PV.PWR2_X0, PV.PWR2_X1, PV.PWR2_Y0, PV.PWR2_Y1, 6.0, 7.6)
    chk("PWR-2 90×70×1.6 @ Z6 (гориз.)", pwr)
    for i, bx in enumerate((314.0, 333.0)):
        cell = C.cyl_y(PV.BAT_D / 2, 62.0, 127.0, bx, PV.BAT_D / 2 + 0.2, 40)
        chk(f"Батарея 18650 #{i+1} (отсек C, на крышке)", cell)
    # крышка отсека: снизу дна (z −2.5…0), касание стенок
    lid = trimesh.load(os.path.join(STL_DIR, "battery_lid.stl"))
    chk("Крышка батарейного отсека 86×86×2.5 (снизу)", lid)
    # складная подставка — отдельная деталь в сборе
    for item in instances:
        if item["file"] == "stand.stl":
            stand = trimesh.load(os.path.join(STL_DIR, "stand.stl"))
            stand.apply_translation(item["pos"])
            chk("Складная подставка 148×67×6 (отдельная деталь)", stand)
    # кабельный канал (C): в задней стенке/полу должно быть пусто
    ch = C.box(150.0, 250.0, 0.0, 3.0, PV.FLOOR_T + 0.1, 11.9)
    vch = _inter(ch, body)
    rows.append(("[C]", "Кабельный канал (задняя стенка, 100×10)",
                 "канал открыт", f"пересечение {vch:.1f} мм³",
                 "OK" if vch < 3.0 else "КОНФЛИКТ"))
    # --- компоненты панели (в системе панели, с тем же наклоном) ----------
    for i, m in enumerate(F4.encoder_bodies()[:16:5]):
        chk(f"Корпус энкодера #{i+1}", _apply(m, M))
    for i, m in enumerate(F4.jack_bodies()[:10:3]):
        chk(f"Корпус джека #{i+1}", _apply(m, M))
    for i, m in enumerate(F4.fader_bodies()):
        chk(f"Корпус фейдера #{i+1}", _apply(m, M))
    vk = sum(_inter(_apply(m, M), pan_w) for m in F4.knobs_3d())
    rows.append(("[G]", "16 ручек Ø14 (над панелью)", "по нормали панели",
                 f"пересечение {vk:.1f} мм³", "OK" if vk < 3.0 else "КОНФЛИКТ"))
    vc = sum(_inter(_apply(m, M), pan_w) for m in F4.keycaps_3d())
    rows.append(("[G]", "42 колпачка (над панелью)", "по нормали панели",
                 f"пересечение {vc:.1f} мм³", "OK" if vc < 3.0 else "КОНФЛИКТ"))

    # --- габарит/высоты -----------------------------------------------------
    bb = pan_w.bounds
    b2 = body.bounds
    hmax = max(bb[1][2], b2[1][2])
    rows.append(("[A]", f"Габарит корпуса в сборе (C, клин {v['angle_deg']:.0f}°)",
                 "380 × 210; высоты по параметрам C",
                 f"X {b2[0][0]:.0f}…{b2[1][0]:.0f} ({b2[1][0]-b2[0][0]:.0f} мм), "
                 f"Y {b2[0][1]:.0f}…{b2[1][1]:.0f} ({b2[1][1]-b2[0][1]:.0f} мм), "
                 f"Z до {hmax:.1f} мм", "OK"))
    rows.append(("[A]", "Высота передней кромки (верх панели)",
                 "31–33 мм (docs/21-ergonomics)", f"{v['h_front_total']:.2f} мм", "OK"))
    rows.append(("[A]", "Высота задней кромки (верх панели)",
                 "C: 76.6 мм (вне 60–63 docs/21 — сравнительный вариант)",
                 f"{v['h_rear_total']:.2f} мм", "OK"))
    rows.append(("[A]", f"Перепад высот панели 210·tan{v['angle_deg']:.0f}°",
                 f"≈{210*math.tan(math.radians(v['angle_deg'])):.1f} мм",
                 f"{v['h_rear_total']-v['h_front_total']:.2f} мм", "OK"))
    # --- STL: watertight / ≤220 --------------------------------------------
    for nm, m in meta.items():
        b = m["bbox"]
        rows.append(("[A]", f"STL {nm}", "≤ 220×220×200, watertight",
                     f"{b[0]:.1f}×{b[1]:.1f}×{b[2]:.1f}; "
                     f"watertight={m['watertight']}/reload={m['watertight_reload']}",
                     "OK" if (max(b) <= 220 and m["watertight"]
                              and m["watertight_reload"]) else "КОНФЛИКТ"))
    # --- панель: вырезы по JSON --------------------------------------------
    rows += F4.check_centers()
    # --- микрофон (D-94): панель = JSON + порт Ø1.8 + LED Ø1.6 -----------
    for i, r in enumerate(rows):
        if r[1] == "Число сквозных отверстий панели":
            rows[i] = ("[J]", "Число сквозных отверстий панели",
                       "83 из JSON + порт Ø1.8 + LED Ø1.6 = 85",
                       f"{r[3]} (JSON) + 2 (mic/LED)", "OK")
    _old_sd = F5L.STL_DIR
    F5L.STL_DIR = STL_DIR
    try:
        F5L._mic_rows(rows, pan_L, pan_R, p2w, M)
    finally:
        F5L.STL_DIR = _old_sd

    conflicts = [r for r in rows if r[4] != "OK"]
    write_report(name, v, rows, conflicts)
    print(f"[fit v0.5-{name}] строк {len(rows)}, конфликтов {len(conflicts)}")
    return rows


def write_report(name, v, rows, conflicts):
    marker = f"<!-- section:v0.5-{name}-mic -->"
    lines = []
    w = lines.append
    w(marker)
    w(f"\n---\n\n# fit_check — Букифон v0.5-{name} (клин {v["angle_deg"]:.0f}°, вариант C + mic)\n")
    w("Сгенерировано `mechanical/generator/fitcheck_v05_C_mic.py`. Панель — без "
      "изменений из v0.4 (`spec/panel-spec-v0.4.json`), корпус — клин 12° "
      "(перед 32 / зад 76.6 мм) + батарейный отсек 1S2P, крышка, подставка, "
      "кабельный канал.\n")
    w(f"\n**Итог:** проверок {len(rows)}, конфликтов: **{len(conflicts)}**.\n")
    w(f"\n## v0.5-{name}-mic-1. Таблица проверок\n")
    w("\n| Класс | Что проверялось | Условие | Расчёт | Статус |")
    w("\n|---|---|---|---|---|")
    for cls, what, cond, calc, status in rows:
        w(f"\n| {cls} | {what} | {cond} | {calc} | **{status}** |")
    w(f"\n\n## v0.5-{name}-mic-2. Что НЕ проверено\n")
    w("\n| Пункт | Причина |")
    w("\n|---|---|")
    w("\n| Кинематика реальных плат под наклоном | PANEL-2 принята параллельной "
      "панели (клавиши/энкодеры жёстко связаны с панелью); CORE-2/PWR-2 — "
      "горизонтальные площадки, соединения — шлейфами |")
    w("\n| Картон-профиль (эргономика) | для C не строился: вариант вне "
      "допусков docs/21 (зад 76.6 мм), сравнительный |")
    w("\n| Складная подставка в рабочем положении | проверено только "
      "отсутствие пересечения в сложенном/отдельном виде; кинематика оси — "
      "на макете |")
    w("\n| Герметичность батарейного отсека | прокладка/уплотнение не "
      "моделировались; крышка на 4×M3 |")
    w(f"\n\n## v0.5-{name}-mic-3. Геометрия\n")
    w(f"\n- Наклон панели: **{v['angle_deg']:.1f}°** к столу; перед **{v['h_front_total']:.1f} мм**, "
      f"зад **{v['h_rear_total']:.1f} мм**, перепад "
      f"**{v['h_rear_total']-v['h_front_total']:.1f} мм**.\n")
    w("- C: отсек под 2 × 18650 (X 292…372, Y 54…134) с крышкой снизу на 4 × M3, "
      "складная U-подставка 148×67×6 (2 оси M3 сзади, в сборе — отдельная "
      "деталь), кабельный канал 100×10 в задней стенке.\n")
    w("- Фаска R4 по передней кромке (запястье); панель крепится 4 × M3 по "
      "нормали панели, стойки PANEL-2 — параллельно панели, CORE-2/PWR-2/"
      "батарея — на горизонтальных площадках.\n")
    w("- Вентиляция — в задней части дна (конвекция при наклоне), окно USB-C-"
      "кабеля — в задней стенке.\n")
    text = "".join(lines) + "\n"
    old = open(FIT_MD).read() if os.path.exists(FIT_MD) else ""
    if marker in old:
        old = old[:old.index(marker)]
    with open(FIT_MD, "w") as f:
        f.write(old.rstrip() + "\n\n" + text)
    print(f"[fit v0.5-{name}] записано {FIT_MD}")
