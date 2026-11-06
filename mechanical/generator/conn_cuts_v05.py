"""conn_cuts_v05.py — вырезы разъёмов в корпусе (docs/82, board-fit).

Задняя стенка (ось Y): MIDI Ø14 X76, DC Ø9 X90, EXPRESSION Ø8.2 X118 (резерв,
D-44 убран), mic jack Ø8.2 X140 — все на Z17 (10…24), перемычки ≥3 мм и вне
рёбер X60/110/290/340. USB-C окно уже есть (X346…356, верхняя кромка).
Левая стенка (ось X): слот microSD 12×2 (Y150…162, Z8…10).

Координаты сверены: X60 из board-fit пересекал ребро жёсткости X60 → X76.
Панельные 10 джеков (CV/GATE, Y=10.5) — на панели, не на задней стенке;
их оси в JSON, вырезы панели не меняются.
"""
MIDI_X, MIDI_D = 76.0, 14.0
DC_X, DC_D = 91.0, 9.0
EXPR_X, EXPR_D = 120.5, 8.2
MIC_X, MIC_D = 140.0, 8.2
PORT_Z = 17.0
SD = dict(y0=150.0, y1=162.0, z0=8.0, z1=10.0)

REAR = [
    dict(id="midi", x=MIDI_X, z=PORT_Z, d=MIDI_D, note="MIDI (Ø14; при TRS 3.5 — Ø8.2, решить на PCB)"),
    dict(id="dc", x=DC_X, z=PORT_Z, d=DC_D, note="DC 12 В"),
    dict(id="expr", x=EXPR_X, z=PORT_Z, d=EXPR_D, note="EXPRESSION — резерв (D-44 убран)"),
    dict(id="mic", x=MIC_X, z=PORT_Z, d=MIC_D, note="mic/headset 3.5 (docs/71)"),
]
RIBS_REAR = [60.0, 110.0, 290.0, 340.0]   # рёбра жёсткости задней стенки (X, ширина 2)


def cutters(WALL):
    """Возвращает list[trimesh] вырезов для стенки толщиной WALL (мм)."""
    import case as C
    out = []
    for h in REAR:
        out.append(C.cyl_y(h["d"] / 2, -1.0, WALL + 1.0, h["x"], h["z"], 32))
    out.append(C.box(-1.0, WALL + 1.0, SD["y0"], SD["y1"], SD["z0"], SD["z1"]))
    return out
