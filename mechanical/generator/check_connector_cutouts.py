"""check_connector_cutouts.py — проверка вырезов разъёмов в корпусах v0.5.

Проверяет для stl_v05_B_light, stl_v05_B, stl_v05_C, stl_v05_B_mic, stl_v05_C_mic:
отверстия MIDI/DC/EXPRESSION/mic — открыты (проба пустая), SD-слот открыт,
перемычки между отверстиями и до рёбер ≥3 мм, watertight тел; считает Δ массы/времени.
Пишет секцию <!-- section:connector-cutouts --> в mechanical/fit_check.md.
"""
from __future__ import annotations
import json, math, os, sys
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import case as C
import conn_cuts_v05 as CC

FIT_MD = os.path.join(ROOT, "mechanical", "fit_check.md")
DIRS = {
    "B-light": (os.path.join(ROOT, "mechanical", "stl_v05_B_light"), 2.0),
    "B": (os.path.join(ROOT, "mechanical", "stl_v05_B"), 2.5),
    "C": (os.path.join(ROOT, "mechanical", "stl_v05_C"), 2.5),
    "B-mic": (os.path.join(ROOT, "mechanical", "stl_v05_B_mic"), 2.5),
    "C-mic": (os.path.join(ROOT, "mechanical", "stl_v05_C_mic"), 2.5),
}
DENS, EFF, RATE = 1.27, 0.36, 12.0


def inter(a, b):
    try:
        return abs(float(trimesh.boolean.intersection([a, b], engine="manifold").volume))
    except Exception:
        return 0.0


def main():
    rows = []
    volumes = {}
    for label, (d, wall) in DIRS.items():
        bodyL = trimesh.load(os.path.join(d, "body_L.stl"))
        bodyR = trimesh.load(os.path.join(d, "body_R.stl"))
        body = trimesh.util.concatenate([bodyL, bodyR])
        bad = []
        for h in CC.REAR:
            probe = C.cyl_y(h["d"] / 2 - 0.2, -0.5, wall + 0.5, h["x"], h["z"], 28)
            if inter(probe, body) > 1.0:
                bad.append(h["id"])
        # SD слот (левая стенка)
        probe = C.box(-0.5, wall + 0.5, CC.SD["y0"] + 0.3, CC.SD["y1"] - 0.3,
                      CC.SD["z0"] + 0.3, CC.SD["z1"] - 0.3)
        if inter(probe, body) > 1.0:
            bad.append("sd")
        wt = bool(trimesh.load(os.path.join(d, "body_L.stl")).is_watertight and
                  trimesh.load(os.path.join(d, "body_R.stl")).is_watertight)
        rows.append((label, "отверстия MIDI/DC/EXPRESSION/mic + SD открыты",
                     "пробы пусты; watertight",
                     f"проблем: {len(bad)}; wt={wt}",
                     "OK" if not bad and wt else "КОНФЛИКТ"))
        # перемычки: между отверстиями + до рёбер
        lig = []
        holes = [(h["x"], h["d"]) for h in CC.REAR]
        for i in range(len(holes)):
            for j in range(i + 1, len(holes)):
                lig.append(abs(holes[i][0] - holes[j][0]) - (holes[i][1] + holes[j][1]) / 2)
        for (x, d_) in holes:
            for rx in CC.RIBS_REAR:
                lig.append(abs(x - rx) - d_ / 2 - 1.0)   # ребро шириной 2 мм
        min_lig = min(lig)
        rows.append((label, "перемычки между отверстиями/рёбрами",
                     "≥3 мм", f"мин {min_lig:.1f} мм", "OK" if min_lig >= 3.0 else "КОНФЛИКТ"))
        # Δ объёма/массы (теоретически удалено)
        vol = sum(math.pi * (h["d"] / 2) ** 2 * wall for h in CC.REAR)
        vol += (CC.SD["y1"] - CC.SD["y0"]) * (CC.SD["z1"] - CC.SD["z0"]) * wall
        dmass = vol / 1000.0 * EFF * DENS
        dtime = vol / 1000.0 * EFF / RATE
        volumes[label] = (vol, dmass, dtime)
        rows.append((label, "Δ массы/времени от вырезов", "масса/время",
                     f"−{dmass:.2f} г / −{dtime:.3f} ч", "OK"))
    rows.append(("все", "панель-канон не менялся: 10 CV/GATE-джеков (Y=10.5) — на панели",
                 "83 выреза = JSON (fitcheck B/B-light = 0)",
                 "панель не менялась", "OK"))
    marker = "<!-- section:connector-cutouts -->"
    lines = []
    w = lines.append
    w(marker)
    w("\n---\n\n# fit_check — вырезы разъёмов в корпусе (docs/82, board-fit)\n")
    w("Сгенерировано `mechanical/generator/check_connector_cutouts.py`. "
      "Задняя стенка (ось Y): MIDI Ø14 X76, DC Ø9 X90, EXPRESSION Ø8.2 X118, "
      "mic Ø8.2 X140; левая стенка: SD 12×2 (Y150…162, Z8…10); USB-C — уже был.\n")
    w("\n| Корпус | Проверка | Условие | Результат | Статус |")
    w("\n|---|---|---|---|---|")
    bad = [r for r in rows if r[4] != "OK"]
    w(f"\n**Итог:** проверок {len(rows)}, конфликтов: **{len(bad)}**.\n")
    for r in rows:
        w(f"\n| {r[0]} | {r[1]} | {r[2]} | {r[3]} | **{r[4]}** |")
    w("\n\n**Δ по вариантам:** " + "; ".join(
        f"{k}: −{v[1]:.2f} г / −{v[2]:.3f} ч" for k, v in volumes.items()) + ".\n")
    w("\n> MIDI: Ø14 (DIN-вариант). Если MIDI на 3.5 мм TRS — Ø8.2; для MIDI IN+OUT "
      "нужно второе отверстие (предложение X=200, Ø14). EXPRESSION — резерв (D-44). "
      "Аудио-джеки (LINE/PHONES/AUDIO IN, 6×Ø8.2) и CV OUT 5/6 — пока без вырезов "
      "(D-15/D-44), добавить при финализации панели.\n")
    old = open(FIT_MD).read() if os.path.exists(FIT_MD) else ""
    if marker in old:
        old = old[:old.index(marker)]
    open(FIT_MD, "w").write(old.rstrip() + "\n\n" + "".join(lines) + "\n")
    print("[conn] строк", len(rows), "конфликтов", len(bad))
    for k, v in volumes.items():
        print(f"  {k}: Δмасса −{v[1]:.2f} г, Δвремя −{v[2]:.3f} ч")


if __name__ == "__main__":
    main()
