"""conn_cuts_v05.py — вырезы разъёмов в корпусе (docs/82, board-fit, hardware/core2).

Задняя стенка (ось Y, Z=17): все разъёмы CORE-2 по BOM-core2/interfaces:
  MIDI IN TRS-A J6 — Ø8.2, X30;
  MIDI OUT TRS-A J7 — Ø8.2, X44;
  DC 12 В J12 — Ø9, X91;
  EXPRESSION J13 — Ø8.2, X120.5 (DNP/D-44, резерв);
  mic/headset J20 — Ø8.2, X140;
  LINE OUT L/R J8 (стерео TRS) — Ø8.2, X160;
  PHONES J9 — Ø8.2, X172;
  AUDIO IN L J10 — Ø8.2, X184;
  AUDIO IN R J11 — Ø8.2, X196;
  CV OUT 5 J? — Ø8.2, X208;
  CV OUT 6 — Ø8.2, X220.
Левая стенка (ось X): слот microSD 12×2 (Y150…162, Z8…10).
USB-C окно (X346…356) — уже в корпусе.
MIDI — TRS-A (BOM: J6/J7), поэтому Ø8.2, а не DIN Ø14. Панельные 10 джеков
(CV/GATE, Y=10.5) — на панели, вырезы панели не меняются.
Перемычки между отверстиями/рёбрами (X60/110/290/340) — ≥3 мм.
"""
MIDI_IN_X = 30.0
MIDI_OUT_X = 44.0
DC_X, DC_D = 91.0, 9.0
EXPR_X = 120.5
MIC_X = 140.0
LINE_X = 160.0
PHONES_X = 172.0
AUDIO_IN_L_X = 184.0
AUDIO_IN_R_X = 196.0
CV5_X = 208.0
CV6_X = 220.0
JACK_D = 8.2
PORT_Z = 17.0
SD = dict(y0=150.0, y1=162.0, z0=8.0, z1=10.0)

REAR = [
    dict(id="midi_in", x=MIDI_IN_X, z=PORT_Z, d=JACK_D, note="MIDI IN TRS-A J6"),
    dict(id="midi_out", x=MIDI_OUT_X, z=PORT_Z, d=JACK_D, note="MIDI OUT TRS-A J7"),
    dict(id="dc", x=DC_X, z=PORT_Z, d=DC_D, note="DC 12 В J12"),
    dict(id="expr", x=EXPR_X, z=PORT_Z, d=JACK_D, note="EXPRESSION J13 — резерв (DNP/D-44)"),
    dict(id="mic", x=MIC_X, z=PORT_Z, d=JACK_D, note="mic/headset J20 (docs/71)"),
    dict(id="line_out", x=LINE_X, z=PORT_Z, d=JACK_D, note="LINE OUT L/R (стерео TRS J8)"),
    dict(id="phones", x=PHONES_X, z=PORT_Z, d=JACK_D, note="PHONES J9"),
    dict(id="audio_in_l", x=AUDIO_IN_L_X, z=PORT_Z, d=JACK_D, note="AUDIO IN L J10"),
    dict(id="audio_in_r", x=AUDIO_IN_R_X, z=PORT_Z, d=JACK_D, note="AUDIO IN R J11"),
    dict(id="cv5", x=CV5_X, z=PORT_Z, d=JACK_D, note="CV OUT 5 (задний джек)"),
    dict(id="cv6", x=CV6_X, z=PORT_Z, d=JACK_D, note="CV OUT 6 (задний джек)"),
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
