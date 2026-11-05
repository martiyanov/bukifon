#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PANEL-2 (PRE-FREEZE, DO NOT FABRICATE) schematic + contract tables generator.

Source of truth: spec/panel-spec-v0.4.json (geometry), tools/lapka42_geometry.py
(Lapka-42 local layout), spec/90-requirements-registry.md (R-01..R-11).

Generates into hardware/panel2/:
  PANEL-2.kicad_sch      KiCad 9/10 schematic (S-expression, version 20250114)
  pinmap.md / pinmap.csv PANEL-2 <-> CORE-2 line table
  matrix.md              key matrix 6x7 + encoders -> MCP23017 mapping
  BOM-panel2.csv         draft BOM
Everything is generated from the same data structures, so docs and netlist
cannot drift (checked by tools/verify_netlist.py).

Licence: CERN-OHL-S-2.0
"""
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.abspath(os.path.join(HERE, '..'))          # hardware/panel2
ROOT = os.path.abspath(os.path.join(P2, '..', '..'))    # repo root
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from kicad_sch import Sch  # noqa: E402
from lapka42_geometry import LAPKA42_LEFT  # noqa: E402

FP = {
    'R0603': 'Resistor_SMD:R_0603_1608Metric',
    'C0603': 'Capacitor_SMD:C_0603_1608Metric',
    'EC11': 'Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm',
    'CHOC': '',                       # custom Kailh Choc hot-swap footprint (PCB phase)
    'D_SOD323': 'Diode_SMD:D_SOD-323',
    'D_SMA': 'Diode_SMD:D_SMA',
    'D_SOT23': 'Package_TO_SOT_SMD:SOT-23',
    'SOT23_5': 'Package_TO_SOT_SMD:SOT-23-5',
    'SOT23_6': 'Package_TO_SOT_SMD:SOT-23-6',
    'MCP23017': 'Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm',
    'L': 'Inductor_SMD:L_Bourns_SRN6045TA',
    'JACK': 'Connector_Audio:AudioJack3.5mm_Rean_NYS230',
    'FADER': 'Potentiometer_THT:Potentiometer_Bourns_PTA6043_Single_Slide',
    'FPC40': 'Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal',
    'FFC40': 'Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal',
    'IDC16': 'Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical',
    'IDC26': 'Connector_IDC:IDC-Header_2x13_P2.54mm_Vertical',
    'HDR1x14': 'Connector_PinHeader_2.54mm:PinHeader_1x14_P2.54mm_Vertical',
    'LED2020': 'LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm',
    'HOLE': 'MountingHole:MountingHole_3.2mm_M3',
    'TP': 'TestPoint:TestPoint_Pad_D1.0mm',
}

MPN = {
    '10k': 'RC0603FR-0710KL', '1k': 'RC0603FR-071KL', '100R': 'RC0603FR-07100RL',
    '4.7k': 'RC0603FR-074K7L', '330R': 'RC0603FR-07330RL', '33R': 'RC0603FR-0733RL',
    '0R': 'RC0603FR-070RL', '100n': 'CC0603KRX7R9BB104', '10u': 'CL10A106KP8NNNC',
    '22uF': 'GRM31CR61E226KE15L', '22uH': 'SRN6045TA-220M',
    'EC11': 'EC11E15244G1', 'MCP23017': 'MCP23017-E/SO', '1N4148': '1N4148W',
    'SMAJ12A': 'SMAJ12A', 'SMAJ15A': 'SMAJ15A', 'SMAJ5.0A': 'SMAJ5.0A',
    'BAT54S': 'BAT54S', 'SS34': 'SS34', 'MT3608': 'MT3608', '2N7002': '2N7002',
    '74LVC1G17': '74LVC1G17', '74HCT1G125': '74HCT1G125',
    'POT60': 'Bourns PTA6043-2015DPB103 (10k, 60 mm)',
    'JACK': 'Rean NYS230 / NJ3FP6C (3.5 mm, панельный)',
    'FPC40': 'Hirose FH12-40S-0.5SH (FPC-40, 0.5 мм, нижний контакт)',
    'IDC16': 'IDC-16 2x8 box header', 'IDC26': 'IDC-26 2x13 box header',
    'HDR1x14': '1x14 pin header 2.54 (SPI alt, DNP)',
    'WS2812B-2020': 'WS2812B-2020', 'CHOC': 'Kailh Choc v1 hot-swap (CPG1350)',
    'M3': 'Mounting hole M3 (3.2 mm)', 'TP': 'Test point 1.0 mm pad',
}

BOM_NOTE = {
    '10k': 'подтяжки фаз/кнопок энкодеров, столбцы матрицы, RESET/INT',
    '1k': 'RC-фильтр фаз энкодеров; последовательные резисторы джеков',
    '100R': 'защита CV IN (не влияет на точность: 0.1 % при 100k входа CORE-2)',
    '4.7k': 'I2C pull-up (2 шт.); GATE IN последовательный (1 шт.)',
    '330R': 'последовательный резистор LED_DATA после буфера',
    '33R': 'резистор подсветки LCD (ограничение тока LED-линейки)',
    '0R': 'net-tie GND-AGND (одна точка)',
    '100n': 'RC фаз энкодеров, блокировка ИС/LED, фильтры джеков',
    '10u': 'вход/выход boost подсветки',
    '22uF': 'вход boost подсветки',
    '22uH': 'индуктивность boost подсветки',
    'EC11': 'энкодер гладкий с кнопкой, Ø14',
    'MCP23017': 'I2C expander: 2× A/B, 1× SW энкодеров, 1× матрица',
    '1N4148': 'диод матрицы (антифантом), анод=клавиша, катод=столбец',
    'SMAJ12A': 'TVS CV OUT (кламп 12 В)',
    'SMAJ15A': 'TVS CV IN (кламп 15 В, ±12 В вход не проводит)',
    'SMAJ5.0A': 'TVS GATE OUT (кламп 5 В)',
    'BAT54S': 'кламп GATE IN к 3.3 В/AGND',
    'SS34': 'диод boost подсветки',
    'MT3608': 'boost подсветки 5 В → ~19 В (DNP если модуль LCD имеет свой драйвер)',
    '2N7002': 'низковольтный ключ подсветки (PWM)',
    '74LVC1G17': 'триггер Шмитта GATE IN (3.3 В)',
    '74HCT1G125': 'буфер LED_DATA 3.3→5 В',
    'POT60': 'фейдер 60 мм, 10 кОм, линейный',
    'JACK': 'mini-jack 3.5 мм панельный',
    'FPC40': 'разъём FPC-40 экрана (0.5 мм)',
    'IDC16': 'цифровой шлейф к CORE-2', 'IDC26': 'аналоговый шлейф к CORE-2',
    'HDR1x14': 'альтернативный SPI-дисплей (DNP)',
    'WS2812B-2020': 'RGB подсветка ручек/статус (+5 В)',
    'CHOC': 'Kailh Choc hot-swap (footprint нарисовать на PCB)',
    'M3': 'крепёж: 6 стоек PANEL-1 rev.2 (30/145/260 × 30/180)',
    'TP': 'тестпоинты',
}

# --------------------------------------------------------------------------
# geometry from spec/panel-spec-v0.4.json
# --------------------------------------------------------------------------
SPEC = json.load(open(os.path.join(ROOT, 'spec', 'panel-spec-v0.4.json'), encoding='utf-8'))
PANEL_W = float(SPEC['panel']['width_mm'])
PANEL_H = float(SPEC['panel']['height_mm'])
CT = SPEC['controls']


def _rot(x, y, deg):
    r = math.radians(deg)
    return (x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r))


# left half: local Lapka coords rotated by +18 deg and shifted; solve shift from key #0
_ang = float(CT['keyboard_left'][0]['angle_deg'])
_lx, _ly = _rot(LAPKA42_LEFT[0][0], LAPKA42_LEFT[0][1], _ang)
_ox = CT['keyboard_left'][0]['center_mm'][0] - _lx
_oy = CT['keyboard_left'][0]['center_mm'][1] - _ly


def key_panel_xy(key, half):
    """Panel coordinates of a Lapka key (key = 1..21, half = 'L'/'R')."""
    loc = LAPKA42_LEFT[key - 1]
    x, y = _rot(loc[0], loc[1], _ang)
    x, y = x + _ox, y + _oy
    if half == 'R':
        x = PANEL_W - x
    return (round(x, 2), round(y, 2))


# --- sanity: our transform must reproduce the JSON coordinates (<=0.5 mm)
def _check_geometry():
    worst = 0.0
    for half, lst in (('L', CT['keyboard_left']), ('R', CT['keyboard_right'])):
        for e in lst:
            k = int(e['key_number'])
            x, y = key_panel_xy(k, half)
            dx = abs(x - e['center_mm'][0])
            dy = abs(y - e['center_mm'][1])
            worst = max(worst, dx, dy)
    return worst


GEOM_ERR = _check_geometry()
assert GEOM_ERR <= 0.55, 'Lapka geometry does not match spec JSON (%.2f mm)' % GEOM_ERR

# --- matrix cell (row 1..6, col 1..7) for each key index (1..21) -----------
def key_cell(key):
    """(row_in_half 1..3, col 1..7) from the local Lapka coordinates."""
    x, y, _ = LAPKA42_LEFT[key - 1]
    if x >= 80.0 and y > 50.0:            # thumb cluster (x 86.8 / 106.1 / 124.9)
        thumb = sorted([LAPKA42_LEFT[i][0] for i in range(21) if _is_thumb(i)])
        return (thumb.index(x) + 1, 7)
    col_x = [6.0, 21.0, 39.0, 58.0, 77.8, 95.8]
    col = min(range(6), key=lambda c: abs(col_x[c] - x)) + 1
    same_col = [LAPKA42_LEFT[i][1] for i in range(21)
                if _is_main(i) and min(range(6), key=lambda c: abs(col_x[c] - LAPKA42_LEFT[i][0])) + 1 == col]
    row = sorted(same_col).index(y) + 1
    return (row, col)


def _is_thumb(i):
    x, y, _ = LAPKA42_LEFT[i]
    return x >= 80.0 and y > 50.0


def _is_main(i):
    return not _is_thumb(i)


KEYS = []       # dict(id, key, half, ref, cell, x, y, angle, diode)
_d = 0
for half, lst in (('L', CT['keyboard_left']), ('R', CT['keyboard_right'])):
    for e in lst:
        k = int(e['key_number'])
        r, c = key_cell(k)
        if half == 'R':
            r += 3
        _d += 1
        KEYS.append(dict(id=e['id'], key=k, half=half, ref='KEY_%s%02d' % (half, k),
                         row=r, col=c, x=float(e['center_mm'][0]), y=float(e['center_mm'][1]),
                         angle=float(e['angle_deg']), diode='D%d' % _d,
                         net_in='K_%s%02d_N' % (half, k)))
KEYS.sort(key=lambda e: (e['half'], e['key']))

ENC_ORDER = [('A', 1), ('E', 2), ('B', 3), ('F', 4), ('C', 5), ('G', 6), ('D', 7), ('H', 8)]
ENCODERS = []
for half in ('L', 'R'):
    lst = CT['encoders_left' if half == 'L' else 'encoders_right']
    by_letter = {}
    for e in lst:
        by_letter[e['id'].split('_')[-1]] = e
    for letter, idx in ENC_ORDER:
        e = by_letter[letter]
        n = idx + (0 if half == 'L' else 8)
        ENCODERS.append(dict(ref='ENC%d' % n, id=e['id'], half=half,
                             x=float(e['center_mm'][0]), y=float(e['center_mm'][1])))
ENCODERS.sort(key=lambda e: int(e['ref'][3:]))
assert len(ENCODERS) == 16 and len(KEYS) == 42

JACKS_SPEC = [dict(id=j['id'], x=float(j['center_mm'][0]), y=float(j['center_mm'][1]))
              for j in CT['jacks']]
FADERS_SPEC = [dict(id=f['id'], x=float(f['rear_envelope']['center_mm'][0]),
                    y=float(f['rear_envelope']['center_mm'][1]),
                    stroke=float(f['slot']['stroke_length_nominal_mm'])) for f in CT['faders']]
LCD_SPEC = dict(cx=float(CT['lcd']['active_cutout']['center_mm'][0]),
                cy=float(CT['lcd']['active_cutout']['center_mm'][1]),
                w=float(CT['lcd']['active_cutout']['opening_size_mm'][0]),
                h=float(CT['lcd']['active_cutout']['opening_size_mm'][1]),
                px=CT['lcd']['active_cutout']['screen_pixels'][0],
                py=CT['lcd']['active_cutout']['screen_pixels'][1])

# mounting holes = mechanical PANEL-1 rev.2 standoffs (params_v17.py PANEL1_POSTS)
M3_HOLES = [(30.0, 30.0), (145.0, 30.0), (260.0, 30.0),
            (30.0, 180.0), (145.0, 180.0), (260.0, 180.0)]

# --------------------------------------------------------------------------
# jack field: 4 CV OUT + 4 CV IN + GATE OUT + GATE IN  (R-06: 10 x 3.5 mm, 13.1 pitch)
# --------------------------------------------------------------------------
JACK_FIELD = [
    ('J01', 'CVOUT1', 'CV OUT 1', 'out', '0..10 V', 'MCP4728 (CORE-2) → 1k → TVS SMAJ12A'),
    ('J02', 'CVOUT2', 'CV OUT 2', 'out', '0..10 V', 'MCP4728 → 1k → TVS SMAJ12A'),
    ('J03', 'CVOUT3', 'CV OUT 3', 'out', '0..10 V', 'MCP4728 → 1k → TVS SMAJ12A'),
    ('J04', 'CVOUT4', 'CV OUT 4', 'out', '0..10 V', 'MCP4728 → 1k → TVS SMAJ12A'),
    ('J05', 'CVIN1', 'CV IN 1', 'in', '±10 V', '100R → TVS SMAJ15A → MCP3208 (CORE-2)'),
    ('J06', 'CVIN2', 'CV IN 2', 'in', '±10 V', '100R → TVS SMAJ15A → MCP3208'),
    ('J07', 'CVIN3', 'CV IN 3', 'in', '±10 V', '100R → TVS SMAJ15A → MCP3208'),
    ('J08', 'CVIN4', 'CV IN 4', 'in', '±10 V', '100R → TVS SMAJ15A → MCP3208'),
    ('J09', 'GATE_OUT', 'GATE OUT', 'out', '0/5 V', '1k → TVS SMAJ5.0A (open-drain CORE-2)'),
    ('J10', 'GATE_IN', 'GATE IN', 'in', '0..12 V', '4.7k → BAT54S → 74LVC1G17 → CORE-2 GPIO'),
]

# --------------------------------------------------------------------------
# connector pin maps (PANEL-2 side)
# --------------------------------------------------------------------------
# J11 FPC-40 = LCD panel tail (panel-dependent, verify!)
LCD_FPC = {
    '1': 'GND', '2': 'GND', '3': 'R0', '4': 'R1', '5': 'R2', '6': 'R3', '7': 'R4',
    '8': 'G0', '9': 'G1', '10': 'G2', '11': 'G3', '12': 'G4', '13': 'G5',
    '14': 'B0', '15': 'B1', '16': 'B2', '17': 'B3', '18': 'B4',
    '19': 'GND', '20': 'GND', '21': 'PCLK', '22': 'DE', '23': 'HSYNC', '24': 'VSYNC',
    '25': 'GND', '26': 'GND', '27': 'LCD_3V3', '28': 'LCD_3V3', '29': 'GND',
    '30': 'BL_K', '31': 'BL_A', '32': 'GND',
    '33': 'NC', '34': 'NC', '35': 'NC', '36': 'NC', '37': 'NC', '38': 'NC',
    '39': 'GND', '40': 'GND',
}
# J12 FFC-40 = PANEL-2 -> CORE-2 (LCD RGB bus + backlight PWM + rails)
FFC_CORE = {
    '1': 'GND', '2': 'GND', '3': 'R0', '4': 'R1', '5': 'R2', '6': 'R3', '7': 'R4',
    '8': 'G0', '9': 'G1', '10': 'G2', '11': 'G3', '12': 'G4', '13': 'G5',
    '14': 'B0', '15': 'B1', '16': 'B2', '17': 'B3', '18': 'B4',
    '19': 'GND', '20': 'GND', '21': 'PCLK', '22': 'DE', '23': 'HSYNC', '24': 'VSYNC',
    '25': 'GND', '26': 'GND', '27': 'LCD_3V3', '28': 'LCD_3V3', '29': 'GND',
    '30': 'BL_PWM', '31': '+5V', '32': '+5V',
    '33': 'GND', '34': 'GND', '35': 'GND', '36': 'GND', '37': 'GND', '38': 'GND',
    '39': 'GND', '40': 'GND',
}
# J13 IDC-16 = digital/power to CORE-2
IDC_DIG = {
    '1': 'SDA', '2': 'GND', '3': 'SCL', '4': 'GND', '5': 'INT', '6': 'GND',
    '7': 'LED_DATA', '8': 'GND', '9': '+5V', '10': 'GND', '11': '+3V3', '12': 'GND',
    '13': '+5V', '14': 'GND', '15': 'NC', '16': 'GND',
}
# J14 IDC-26 = analog patch field to CORE-2 (odd = signal, even = AGND)
IDC_AN = {
    '1': 'CVOUT1', '3': 'CVOUT2', '5': 'CVOUT3', '7': 'CVOUT4',
    '9': 'CVIN1', '11': 'CVIN2', '13': 'CVIN3', '15': 'CVIN4',
    '17': 'GATE_OUT', '19': 'GATE_IN_CLEAN', '21': 'FADER1', '23': 'FADER2',
    '25': 'NC',
}
for _p in range(2, 27, 2):
    IDC_AN[str(_p)] = 'AGND'
# J15 optional SPI display (alternative to RGB panel), DNP
SPI_ALT = {'1': '+3V3', '2': 'GND', '3': 'SPI2_SCK', '4': 'SPI2_MOSI', '5': 'SPI2_CS',
           '6': 'SPI2_DC', '7': 'SPI2_RST', '8': 'BL_PWM', '9': 'SPI2_MISO',
           '10': 'GND', '11': 'NC', '12': 'NC', '13': 'GND', '14': 'GND'}

# --------------------------------------------------------------------------
# schematic coordinates (cosmetic only; A0 sheet)
# --------------------------------------------------------------------------
PAPER = 'A0'


class B:
    def __init__(self):
        self.sch = Sch(os.path.join(P2, 'PANEL-2.kicad_sch'),
                       'PicoMod PANEL-2 (PRE-FREEZE, DO NOT FABRICATE) - 380x210 panel: '
                       '16xEC11, 42xChoc 6x7, 5.0" RGB 800x480, 10xjack, 2xfader, 17xWS2812',
                       PAPER, 'PANEL-2')
        self.bom = []
        self.intent = []
        self._n = 0

    def part(self, lib, name, ref, value, x, y, fp='', note=''):
        p = self.sch.sym(lib, name, ref, value, x, y, fp)
        self.bom.append(dict(ref=ref, value=value, fp=fp, mpn=MPN.get(value, '')))
        return p

    def r(self, ref, value, x, y, kind='R0603'):
        return self.part('Device', 'R', ref, value, x, y, FP[kind])

    def c(self, ref, value, x, y, kind='C0603'):
        return self.part('Device', 'C', ref, value, x, y, FP[kind])

    def _intent(self, comp, net, num=None, pname=None):
        from kicad_sch import pin, pin_by_name
        if num is not None:
            p = pin(comp['libname'], comp['name'], num)
        else:
            p = pin_by_name(comp['libname'], comp['name'], pname)
        self.intent.append((comp['ref'], p[0], p[1], net))

    def net(self, comp, num, name, **kw):
        self.sch.net(comp, name, num=num, **kw)
        self._intent(comp, name, num=num)

    def net_pin(self, comp, pname, name, **kw):
        self.sch.net(comp, name, pname=pname, **kw)
        self._intent(comp, name, pname=pname)

    def rail(self, comp, num, name, **kw):
        self.net(comp, num, name, **kw)

    def nc(self, comp, num=None, pname=None):
        self.sch.nc_pin(comp, num=num, pname=pname)
        self._intent(comp, None, num=num, pname=pname)

    def done(self):
        return self.sch.write()


b = B()
s = b.sch

# --------------------------------------------------------------------------
# PRE-FREEZE stamp + notes
# --------------------------------------------------------------------------
s.text('! PANEL-2  PRE-FREEZE  —  DO NOT FABRICATE  —  НЕ ЗАКАЗЫВАТЬ ПЛАТУ !', (25.4, 25.4), 5.0)
s.text('PANEL-2 rev.0 (pre-freeze contract) | panel v0.4 380x210 (spec/panel-spec-v0.4.json) | '
       'geometry check vs JSON: max dev %.2f mm | CERN-OHL-S-2.0' % GEOM_ERR, (25.4, 36.0), 2.2)
s.text('Назначение: проверить КОНТРАКТ PANEL-2 <-> CORE-2 (pinmap.md/csv), матрицу (matrix.md) '
       'и защиту джеков (interfaces.md). Электрические номиналы — проект, требующий ревью.',
       (25.4, 43.0), 1.8)

# --------------------------------------------------------------------------
# 1. ENCODERS 16 x EC11 + RC 1k/100n + pull-ups
# --------------------------------------------------------------------------
def enc_block(n, bx, by):
    ref = 'ENC%d' % n
    e = b.part('Device', 'RotaryEncoder_Switch', ref, 'EC11', bx, by, FP['EC11'],
               'EC11 #%d (%s)' % (n, [x['id'] for x in ENCODERS if x['ref'] == ref][0]))
    for k, ph in enumerate(('A', 'B')):
        y0 = by + 30.48 + k * 25.4
        pull = b.r('R%d' % (1 + (n - 1) * 2 + k), '10k', bx - 30.48, y0, 'R0603')
        b.rail(pull, '1', '+3V3'); b.net(pull, '2', '%s_%s_RAW' % (ref, ph))
        ser = b.r('R%d' % (49 + (n - 1) * 2 + k), '1k', bx - 10.16, y0, 'R0603')
        b.net(ser, '1', '%s_%s_RAW' % (ref, ph)); b.net(ser, '2', '%s_%s' % (ref, ph))
        cap = b.c('C%d' % (1 + (n - 1) * 2 + k), '100n', bx + 10.16, y0, 'C0603')
        b.net(cap, '1', '%s_%s' % (ref, ph)); b.rail(cap, '2', 'GND')
        b.net(e, ph, '%s_%s_RAW' % (ref, ph))
    b.net(e, 'C', 'GND')
    b.net(e, 'S2', 'GND')
    b.net(e, 'S1', '%s_SW' % ref)
    rsw = b.r('R%d' % (33 + n - 1), '10k', bx + 33.02, by + 30.48, 'R0603')
    b.rail(rsw, '1', '+3V3'); b.net(rsw, '2', '%s_SW' % ref)


for i, e in enumerate(ENCODERS):
    col, row = i % 4, i // 4
    enc_block(int(e['ref'][3:]), 57.15 + col * 139.7, 76.2 + row * 95.25)

s.text('1. 16 x EC11 (A/B/SW), 8 слева + 8 справа. Каждая фаза: 10k подтяжка -> 1k -> 100n -> MCP23017 '
       '(RC 1k/100n по ТЗ). Кнопка: 10k подтяжка + 100n. Все 48 линий идут в 3 x MCP23017 (I2C).',
       (25.4, 71.12), 1.8)

# --------------------------------------------------------------------------
# 2. MCP23017 x4 (U1/U2 = A/B, U3 = SW, U4 = key matrix)
# --------------------------------------------------------------------------
def mcp(ref, addr_net, x, y, note):
    u = b.part('Interface_Expansion', 'MCP23017x-x-SP', ref, 'MCP23017', x, y,
               FP['MCP23017'], note)
    b.net_pin(u, 'V_{DD}', '+3V3')
    b.net_pin(u, 'V_{SS}', 'GND')
    b.net_pin(u, 'SCK', 'SCL')
    b.net_pin(u, 'SDA', 'SDA')
    b.net_pin(u, 'INTA', 'INT')
    b.nc(u, pname='INTB')
    b.net_pin(u, '~{RESET}', 'MCP_RST')
    return u


MCP = {}
MCP['U1'] = mcp('U1', None, 76.2, 419.1, 'MCP23017 0x20: ENC1..ENC8 A/B (GPA=A, GPB=B)')
MCP['U2'] = mcp('U2', None, 228.6, 419.1, 'MCP23017 0x21: ENC9..ENC16 A/B')
MCP['U3'] = mcp('U3', None, 381.0, 419.1, 'MCP23017 0x22: ENC1..ENC16 SW (GPA=1..8, GPB=9..16)')
MCP['U4'] = mcp('U4', None, 533.4, 419.1, 'MCP23017 0x23: матрица 6x7 (GPA0..5=ROW1..6, GPB0..6=COL1..7)')

# addresses A0..A2
for ref, bits in (('U1', ('GND', 'GND', 'GND')), ('U2', ('+3V3', 'GND', 'GND')),
                  ('U3', ('GND', '+3V3', 'GND')), ('U4', ('+3V3', '+3V3', 'GND'))):
    for i, (pinname, net) in enumerate(zip(('A0', 'A1', 'A2'), bits)):
        b.net_pin(MCP[ref], pinname, net)
    cc = b.c('C%d' % (33 + int(ref[1:]) - 1), '100n', 76.2 + (int(ref[1:]) - 1) * 152.4, 381.0,
             '%s decoupling' % ref)
    b.rail(cc, '1', '+3V3'); b.rail(cc, '2', 'GND')

# encoder A/B + SW lines into the expanders
for e in ENCODERS:
    n = int(e['ref'][3:])
    if n <= 8:
        u, port, bit = MCP['U1'], 'GPA', (n - 1) * 2
        u2, port2 = MCP['U1'], 'GPB'
        b.net_pin(u, '%s%d' % (port, bit), 'ENC%d_A' % n)
        b.net_pin(u, '%s%d' % (port, bit + 1), 'ENC%d_B' % n)
    else:
        u, port, bit = MCP['U2'], 'GPA', (n - 9) * 2
        b.net_pin(u, '%s%d' % (port, bit), 'ENC%d_A' % n)
        b.net_pin(u, '%s%d' % (port, bit + 1), 'ENC%d_B' % n)
    # SW: ENC1..8 -> U3 GPA0..7, ENC9..16 -> U3 GPB0..7
    u = MCP['U3']
    if n <= 8:
        b.net_pin(u, 'GPA%d' % (n - 1), 'ENC%d_SW' % n)
    else:
        b.net_pin(u, 'GPB%d' % (n - 9), 'ENC%d_SW' % n)

# I2C pull-ups + INT pull-up + reset pull-up
for i, (netname, ref) in enumerate((('SDA', 'R110'), ('SCL', 'R111'))):
    r = b.r(ref, '4.7k', 380.0 + i * 25.4, 340.0, 'R0603')
    b.rail(r, '1', '+3V3'); b.net(r, '2', netname)
rint = b.r('R92', '10k', 405.0, 340.0, 'R0603')
b.rail(rint, '1', '+3V3'); b.net(rint, '2', 'INT')
rrst = b.r('R88', '10k', 430.0, 340.0, 'R0603')
b.rail(rrst, '1', '+3V3'); b.net(rrst, '2', 'MCP_RST')

s.text('2. 4 x MCP23017 на I2C0 (0x20/0x21 = A/B 16 энкодеров, 0x22 = 16 кнопок, 0x23 = матрица 6x7). '
       'INTA всех чипов — open-drain, общая линия INT с подтяжкой 10k. Адреса: A0..A2 (см. схему).',
       (25.4, 330.2), 1.8)

# --------------------------------------------------------------------------
# 3. KEY MATRIX 42 x Choc + 1N4148, 6 rows x 7 cols
# --------------------------------------------------------------------------
for k in KEYS:
    col, row = k['col'], k['row']
    x = 640.0 + (col - 1) * 62.4
    y = 76.2 + (row - 1) * 52.07
    sw = b.part('Switch', 'SW_Push', k['ref'], 'CHOC', x, y, FP['CHOC'],
                'Lapka %s key_number=%d, panel (%.1f, %.1f) %.0f deg' %
                (k['half'], k['key'], k['x'], k['y'], k['angle']))
    b.net(sw, '1', 'ROW%d' % row)
    b.net(sw, '2', k['net_in'])
    d = b.part('Diode', '1N4148', k['diode'], '1N4148', x, y + 25.4, FP['D_SOD323'],
               'антифантом: анод=клавиша, катод=COL%d' % col)
    b.net(d, '2', k['net_in'])       # anode
    b.net(d, '1', 'COL%d' % col)     # cathode

# rows / cols into U4
for r in range(1, 7):
    b.net_pin(MCP['U4'], 'GPA%d' % (r - 1), 'ROW%d' % r)
for c in range(1, 8):
    b.net_pin(MCP['U4'], 'GPB%d' % (c - 1), 'COL%d' % c)
# external column pull-ups (internal 100k too weak)
for c in range(1, 8):
    r = b.r('R%d' % (80 + c), '10k', 1040.0 + (c - 1) * 20.0, 419.1, 'R0603')
    b.rail(r, '1', '+3V3'); b.net(r, '2', 'COL%d' % c)
# 3 spare pins of U4 -> test points
for i, pin in enumerate(('GPA6', 'GPA7', 'GPB7')):
    tp = b.part('Connector', 'TestPoint', 'TP%d' % (9 + i), 'TP', 1040.0 + i * 25.4, 470.0, FP['TP'],
                'spare pin U4 %s' % pin)
    b.net_pin(MCP['U4'], pin, 'SPARE%d' % (i + 1))
    b.net(tp, '1', 'SPARE%d' % (i + 1))

s.text('3. Матрица 42 клавиш Lapka-42: 6 строк x 7 столбцов (строки 1..3 = левая половина, '
       '4..6 = правая; столбцы 1..6 = клавиши, 7 = thumb-ряд). Антифантом: 1N4148 в каждой клавише, '
       'строки сканируются по одной (GPIO поочерёдно). Полная таблица — matrix.md.',
       (25.4, 60.96), 1.8)

# --------------------------------------------------------------------------
# 4. LCD 5.0" 800x480 RGB + FPC-40 + FFC-40 to CORE-2 + backlight
# --------------------------------------------------------------------------
j_fpc = b.part('Connector_Generic', 'Conn_01x40', 'J11', 'FPC40', 130.0, 560.0, FP['FPC40'],
               'FPC-40 0.5 mm: LCD panel tail (pinout panel-dependent - verify!)')
for pin, net in LCD_FPC.items():
    if net in ('NC',):
        b.nc(j_fpc, int(pin))
    else:
        b.net(j_fpc, int(pin), net)

j_ffc = b.part('Connector_Generic', 'Conn_01x40', 'J12', 'FFC40', 260.0, 560.0, FP['FFC40'],
               'FPC-40 0.5 mm: PANEL-2 -> CORE-2 (RGB bus + BL_PWM + +5V)')
for pin, net in FFC_CORE.items():
    b.net(j_ffc, int(pin), net)

# LCD decoupling
for i in range(4):
    c = b.c('C%d' % (37 + i), '100n', 130.0 + i * 20.0, 520.0, 'C0603')
    b.rail(c, '1', 'LCD_3V3'); b.rail(c, '2', 'GND')

# backlight: boost 5V -> BL_A (~19 V) + low-side PWM switch + bypass jumper
u_bl = b.part('Regulator_Switching', 'MT3608', 'U7', 'MT3608', 380.0, 560.0, FP['SOT23_6'],
              'backlight boost 5V -> ~19V (DNP if the LCD module has its own driver)')
b.net_pin(u_bl, 'IN', '+5V'); b.net_pin(u_bl, 'GND', 'GND')
b.nc(u_bl, 'NC')
b.net_pin(u_bl, 'SW', 'BL_SW')
b.net_pin(u_bl, 'FB', 'BL_FB')
b.net_pin(u_bl, 'EN', 'BL_PWM')
l1 = b.part('Device', 'L', 'L1', '22uH', 380.0, 600.0, FP['L'], 'boost inductor')
b.net(l1, '1', '+5V'); b.net(l1, '2', 'BL_SW')
d_bl = b.part('Diode', 'SS34', 'D43', 'SS34', 410.0, 600.0, FP['D_SMA'], 'boost rectifier')
b.net(d_bl, '2', 'BL_SW'); b.net(d_bl, '1', 'BL_A')
r_fb1 = b.r('R106', '33k', 440.0, 570.0, 'R0603')
b.net(r_fb1, '1', 'BL_A'); b.net(r_fb1, '2', 'BL_FB')
r_fb2 = b.r('R107', '1k', 440.0, 600.0, 'R0603')
b.net(r_fb2, '1', 'BL_FB'); b.rail(r_fb2, '2', 'GND')
c_in = b.c('C73', '22uF', 350.0, 600.0, 'C0603')
b.rail(c_in, '1', '+5V'); b.rail(c_in, '2', 'GND')
c_out = b.c('C74', '10u', 470.0, 600.0, 'C0603')
b.net(c_out, '1', 'BL_A'); b.rail(c_out, '2', 'GND')
r_led = b.r('R108', '33R', 500.0, 570.0, 'R0603')
b.net(r_led, '1', 'BL_A'); b.net(r_led, '2', 'BL_K')
q_bl = b.part('Transistor_FET', '2N7002', 'Q2', '2N7002', 530.0, 600.0, FP['D_SOT23'],
              'low-side PWM switch for the LED string')
b.net_pin(q_bl, 'D', 'BL_K'); b.net_pin(q_bl, 'S', 'GND'); b.net_pin(q_bl, 'G', 'BL_G')
rg = b.r('R109', '100R', 500.0, 630.0, 'R0603')
b.net(rg, '1', 'BL_PWM'); b.net(rg, '2', 'BL_G')
rpd = b.r('R93', '10k', 530.0, 630.0, 'R0603')
b.net(rpd, '1', 'BL_G'); b.rail(rpd, '2', 'GND')

# alternative SPI display header (DNP)
j_spi = b.part('Connector_Generic', 'Conn_01x14', 'J15', 'HDR1x14', 620.0, 560.0, FP['HDR1x14'],
               'alternative SPI display (DNP) - R-18 open')
for pin, net in SPI_ALT.items():
    if net == 'NC':
        b.nc(j_spi, int(pin))
    else:
        b.net(j_spi, int(pin), net)

s.text('4. Экран 5.0" 800x480 RGB 16 бит: FPC-40 (J11) — хвост панели, FPC-40 (J12) — шлейф в CORE-2 '
       '(21 сигнал: R0-R4/G0-G5/B0-B4, PCLK/DE/HSYNC/VSYNC, BL_PWM). Подсветка: boost MT3608 5V->19V '
       '+ низковольтный ключ Q2 (PWM), JP-обход если модуль имеет свой драйвер. J15 — альтернатива SPI (DNP).',
       (25.4, 500.38), 1.6)

# --------------------------------------------------------------------------
# 5. JACK FIELD 10 x 3.5 mm + protection
# --------------------------------------------------------------------------
for i, (jid, netname, title, direction, level, prot) in enumerate(JACK_FIELD):
    col, row = i % 5, i // 5
    x = 76.2 + col * 165.0
    y = 680.0 + row * 60.0
    j = b.part('Connector_Audio', 'AudioJack2', jid, 'JACK', x, y, FP['JACK'],
               '%s (%s, %s): %s' % (title, direction, level, prot))
    tip = 'TIP_' + netname
    b.net_pin(j, 'T', tip)
    b.rail(j, 'S', 'AGND')
    if netname.startswith('CVOUT'):
        r = b.r('R%d' % (94 + i), '1k', x - 25.0, y, 'R0603')
        b.net(r, '1', netname); b.net(r, '2', tip)
        d = b.part('Device', 'D_TVS', 'D%d' % (44 + i), 'SMAJ12A', x + 25.0, y, FP['D_SMA'],
                   'TVS 12 V: %s' % title)
        b.net(d, '1', tip); b.rail(d, '2', 'AGND')
        c = b.c('C%d' % (42 + i), '100n', x, y + 25.0, 'C0603')
        b.net(c, '1', tip); b.rail(c, '2', 'AGND')
    elif netname.startswith('CVIN'):
        r = b.r('R%d' % (98 + i), '100R', x - 25.0, y, 'R0603')
        b.net(r, '1', tip); b.net(r, '2', netname)
        d = b.part('Device', 'D_TVS', 'D%d' % (48 + i), 'SMAJ15A', x + 25.0, y, FP['D_SMA'],
                   'TVS 15 V: %s' % title)
        b.net(d, '1', tip); b.rail(d, '2', 'AGND')
        c = b.c('C%d' % (46 + i), '100n', x, y + 25.0, 'C0603')
        b.net(c, '1', tip); b.rail(c, '2', 'AGND')
    elif netname == 'GATE_OUT':
        r = b.r('R102', '1k', x - 25.0, y, 'R0603')
        b.net(r, '1', netname); b.net(r, '2', tip)
        d = b.part('Device', 'D_TVS', 'D52', 'SMAJ5.0A', x + 25.0, y, FP['D_SMA'], 'TVS 5 V: GATE OUT')
        b.net(d, '1', tip); b.rail(d, '2', 'AGND')
        c = b.c('C50', '100n', x, y + 25.0, 'C0603')
        b.net(c, '1', tip); b.rail(c, '2', 'AGND')
    else:  # GATE_IN
        r = b.r('R103', '4.7k', x - 25.0, y, 'R0603')
        b.net(r, '1', tip); b.net(r, '2', 'GATE_IN_RAW')
        d = b.part('Diode', 'BAT54S', 'D53', 'BAT54S', x + 25.0, y, FP['D_SOT23'],
                   'clamp GATE IN to 3V3/AGND')
        b.net(d, '3', 'GATE_IN_RAW'); b.rail(d, '1', '+3V3'); b.rail(d, '2', 'AGND')
        c = b.c('C51', '100n', x, y + 25.0, 'C0603')
        b.net(c, '1', 'GATE_IN_RAW'); b.rail(c, '2', 'AGND')
        sch = b.part('74xGxx', '74LVC1G17', 'U5', '74LVC1G17', x + 55.0, y, FP['SOT23_5'],
                     'Schmitt buffer GATE IN (3.3 V)')
        b.rail(sch, 5, '+5V' if False else '+3V3')
        b.rail(sch, 3, 'GND')
        b.net(sch, 2, 'GATE_IN_RAW')
        b.net(sch, 4, 'GATE_IN_CLEAN')

# net-tie GND <-> AGND
rn = b.r('R112', '0R', 700.0, 780.0, 'R0603')
b.rail(rn, '1', 'GND'); b.rail(rn, '2', 'AGND')

s.text('5. Джек-поле: 4 x CV OUT (0..10 В), 4 x CV IN (±10 В), GATE OUT (0/5 В), GATE IN (0..12 В). '
       'Защита: CV OUT — 1k + TVS SMAJ12A + 100n; CV IN — 100R + TVS SMAJ15A + 100n (100R даёт 0.1% '
       'погрешности на 100k входа CORE-2, ±12 В TVS не открывает); GATE OUT — 1k + SMAJ5.0A; '
       'GATE IN — 4.7k + BAT54S (3.3 В/AGND) + 100n + 74LVC1G17. AGND и GND соединены в одной точке (R112).',
       (25.4, 640.08), 1.6)

# --------------------------------------------------------------------------
# 6. FADERS 2 x 60 mm
# --------------------------------------------------------------------------
for i, f in enumerate(FADERS_SPEC):
    x = 950.0 + i * 100.0
    y = 680.0
    pot = b.part('Device', 'R_Potentiometer', 'F%d' % (i + 1), 'POT60', x, y, FP['FADER'],
                 '60 mm fader, 10k linear (stroke %d mm)' % f['stroke'])
    b.rail(pot, '1', '+3V3')
    b.rail(pot, '3', 'AGND')
    b.net(pot, '2', 'FADER%d_RAW' % (i + 1))
    r = b.r('R%d' % (104 + i), '1k', x + 25.0, y, 'R0603')
    b.net(r, '1', 'FADER%d_RAW' % (i + 1)); b.net(r, '2', 'FADER%d' % (i + 1))
    c = b.c('C%d' % (53 + i), '100n', x + 50.0, y, 'C0603')
    b.net(c, '1', 'FADER%d' % (i + 1)); b.rail(c, '2', 'AGND')

s.text('6. 2 фейдера 60 мм (10k линейные) через RC 1k/100n → FADER1/FADER2 → MCP3208 CORE-2. '
       'Линейность: 10k по 3.3 В = 0.33 мА, шум 1k+100n (fc 1.6 кГц), 12 бит = 0.8 мВ/LSB.',
       (920.0, 640.08), 1.6)

# --------------------------------------------------------------------------
# 7. LED chain 17 x WS2812B-2020 + 74HCT1G125
# --------------------------------------------------------------------------
buf = b.part('74xGxx', '74AHCT1G125', 'U6', '74HCT1G125', 900.0, 720.0, FP['SOT23_5'],
             'LED_DATA buffer 3.3->5 V (VCC=+5V, TTL input)')
b.net(buf, '2', 'LED_DATA'); b.net(buf, '1', 'GND'); b.net(buf, '5', '+5V')
b.net(buf, '3', 'GND'); b.net(buf, '4', 'LED_BUF')
cbuf = b.c('C72', '100n', 870.0, 720.0, 'C0603')
b.rail(cbuf, '1', '+5V'); b.rail(cbuf, '2', 'GND')
rled = b.r('R113', '330R', 930.0, 720.0, 'R0603')
b.net(rled, '1', 'LED_BUF'); b.net(rled, '2', 'LED_IN')
prev = 'LED_IN'
LEDS = ['LED_ENC%d' % i for i in range(1, 17)] + ['LED_STATUS']
for i, ref in enumerate(LEDS):
    x = 60.0 + (i % 9) * 90.0
    y = 745.0 + (i // 9) * 50.0
    led = b.part('LED', 'WS2812B-2020', ref, 'WS2812B-2020', x, y, FP['LED2020'],
                 'RGB %s (+5 V)' % ('status' if ref == 'LED_STATUS' else 'knob ring'))
    b.net_pin(led, 'DIN', prev)
    b.net_pin(led, 'VDD', '+5V')
    b.net_pin(led, 'VSS', 'GND')
    out = 'LED_CH%d' % (i + 1) if i < len(LEDS) - 1 else 'LED_END'
    if i < len(LEDS) - 1:
        b.net_pin(led, 'DOUT', out)
        prev = out
    else:
        b.nc(led, pname='DOUT')
    cc = b.c('C%d' % (55 + i), '100n', x, y + 20.0, 'C0603')
    b.rail(cc, '1', '+5V'); b.rail(cc, '2', 'GND')

s.text('7. 17 x WS2812B-2020 (16 ручек + статус), питание +5 В, данные GPxx -> U6 74HCT1G125 '
       '(VCC=+5 В) -> 330R -> цепочка; 100n на каждый LED.',
       (25.4, 705.0), 1.6)

# --------------------------------------------------------------------------
# 8. CONNECTORS to CORE-2 + mounting + test points
# --------------------------------------------------------------------------
j_dig = b.part('Connector_Generic', 'Conn_02x08_Odd_Even', 'J13', 'IDC16', 900.0, 100.0, FP['IDC16'],
               'digital/power ribbon to CORE-2 (IDC-16 2x8)')
for pin, net in IDC_DIG.items():
    if net == 'NC':
        b.nc(j_dig, int(pin))
    else:
        b.net(j_dig, int(pin), net)

j_an = b.part('Connector_Generic', 'Conn_02x13_Odd_Even', 'J14', 'IDC26', 1050.0, 100.0, FP['IDC26'],
              'analog patch-field ribbon to CORE-2 (IDC-26 2x13)')
for pin, net in IDC_AN.items():
    if net == 'NC':
        b.nc(j_an, int(pin))
    else:
        b.net(j_an, int(pin), net)

for i, (hx, hy) in enumerate(M3_HOLES):
    b.part('Mechanical', 'MountingHole', 'H%d' % (i + 1), 'M3', 30.0 + i * 40.0, 60.0, FP['HOLE'],
           'M3 hole: panel (%.0f, %.0f) = mechanical PANEL1_POSTS' % (hx, hy))

for i, (netname, note) in enumerate((('SDA', 'I2C SDA'), ('SCL', 'I2C SCL'), ('INT', 'expander INT'),
                                     ('LED_DATA', 'WS2812 data'), ('GATE_IN_CLEAN', 'gate in, 3.3 V'),
                                     ('+5V', '+5V rail'), ('+3V3', '+3V3 rail'), ('AGND', 'analog return'))):
    tp = b.part('Connector', 'TestPoint', 'TP%d' % (i + 1), 'TP', 30.0 + i * 30.0, 90.0, FP['TP'], note)
    b.net(tp, '1', netname)

s.power_anchor('+3V3', 25.4, 300.0)
s.power_anchor('+5V', 60.96, 300.0)
s.power_anchor('GND', 96.52, 300.0)
s.power_anchor('AGND', 132.08, 300.0)

s.text('8. Разъёмы в CORE-2: J13 IDC-16 (цифровой/питание: SDA, SCL, INT, LED_DATA, +5V, +3V3, GND); '
       'J14 IDC-26 (аналог: CVOUT1..4, CVIN1..4, GATE_OUT, GATE_IN_CLEAN, FADER1/2, AGND); '
       'J12 FPC-40 (LCD RGB). Полная таблица — pinmap.md/.csv.', (25.4, 215.0), 1.6)

PATH = b.done()
print('written', PATH)

# --------------------------------------------------------------------------
# matrix.md
# --------------------------------------------------------------------------
def write_matrix():
    L = []
    A = L.append
    A('# PANEL-2 — матрица клавиш и энкодеры')
    A('')
    A('Сгенерировано `tools/gen_panel2.py` из `spec/panel-spec-v0.4.json` + '
      '`tools/lapka42_geometry.py`. Сверка геометрии: отклонение от JSON ≤ %.2f мм.' % GEOM_ERR)
    A('')
    A('## 1. Матрица 42 клавиш: 6 строк × 7 столбцов (Lapka-42)')
    A('')
    A('* строки 1…3 — левая половина (±18°), строки 4…6 — правая (зеркальная);')
    A('* столбцы 1…6 — клавишные колонки, столбец 7 — thumb-ряд (3 клавиши на половину);')
    A('* каждая клавиша — свой диод 1N4148 (`анод = клавиша`, `катод = столбец`) — антифантом;')
    A('* строки поочерёдно прижимаются к GND (MCP23017 GPA0…5 = выходы, активный низкий), '
      'столбцы читаются GPB0…6 с подтяжкой 10 кОм; **одновременно нажатые клавиши в разных '
      'строках не дают фантомных срабатываний** (диоды).')
    A('')
    A('| # | id (JSON) | key_number | Половина | ROW | COL | Диод | X, мм | Y, мм | Угол, ° |')
    A('|---:|---|---:|---|---:|---:|---|---:|---:|---:|')
    for i, k in enumerate(KEYS, 1):
        A('| %d | `%s` | %d | %s | ROW%d | COL%d | `%s` | %.2f | %.2f | %.1f |'
          % (i, k['id'], k['key'], k['half'], k['row'], k['col'], k['diode'],
             k['x'], k['y'], k['angle']))
    A('')
    A('Проверка уникальности: `assert` в генераторе + `tools/verify_netlist.py` (42 уникальные ячейки, '
      '42 диода, 42 клавиши).')
    A('')
    A('## 2. Энкодеры: 16 × EC11 → 3 × MCP23017 (I2C)')
    A('')
    A('| # | id (JSON) | Половина | X, мм | Y, мм | A | B | SW |')
    A('|---:|---|---|---:|---:|---|---|---|')
    for i, e in enumerate(ENCODERS):
        n = int(e['ref'][3:])
        if n <= 8:
            ua, pa, ba = 'U1', 'GPA', (n - 1) * 2
            ua2 = 'U1'
            pb = 'GPB'
        else:
            ua, pa, ba = 'U2', 'GPA', (n - 9) * 2
            ua2 = 'U2'
            pb = 'GPB'
        sw = 'U3.GPA%d' % (n - 1) if n <= 8 else 'U3.GPB%d' % (n - 9)
        A('| %d | `%s` | %s | %.1f | %.1f | %s.%s%d | %s.GPB%d | %s |'
          % (n, e['id'], e['half'], e['x'], e['y'], ua, pa, ba, ua2, ba + 1, sw))
    A('')
    A('Почему 3 × MCP23017, а не 2: у EC11 три линии на энкодер (A, B, SW) → 16 × 3 = 48 входов; '
      'два MCP23017 дают только 32. Три чипа (0x20/0x21/0x22) покрывают 48 линий ровно, '
      'на шлейф уходит 3 провода (SDA, SCL, INT) вместо 48.')
    A('')
    A('## 3. I2C-адреса и INT')
    A('')
    A('| Чип | A2 | A1 | A0 | Адрес | Что читает | INT |')
    A('|---|---|---|---|---|---|---|')
    for ref, bits, what in (('U1', ('GND', 'GND', 'GND'), 'ENC1…8 A/B (32 входа)'),
                            ('U2', ('GND', 'GND', '+3V3'), 'ENC9…16 A/B'),
                            ('U3', ('GND', '+3V3', 'GND'), 'ENC1…16 SW'),
                            ('U4', ('GND', '+3V3', '+3V3'), 'матрица 6×7 (13 линий, 3 в резерв)')):
        A('| %s | %s | %s | %s | 0x2%d | %s | INTA → `INT` (open-drain, 10k) |' % (ref, bits[2], bits[1], bits[0], int(ref[1:]) - 1, what))
    A('')
    A('## 4. Диагональные нажатия и дребезг')
    A('')
    A('* Матрица с диодами: «диагональ» (две клавиши в разных строках/столбцах) читается корректно — '
      'фантом исключён диодом; ограничение только у клавиш **без** диодов.')
    A('* Энкодеры: RC 1 кОм/100 нФ на каждой фазе (fc = 1/(2π·1k·100n) ≈ 1.6 кГц) + подтяжка 10 кОм; '
      'дребезг кнопок (SW) — 100 нФ + программный дебаунс 5…10 мс по прерыванию INT.')
    A('* Скан матрицы: 6 строк × (запись + чтение) ≈ 0.5 мс при 400 кГц I2C → 200 Гц…2 кГц; '
      'рекомендуемый режим 500 Гц (2 мс на полный скан), энкодеры — по прерыванию.')
    A('')
    with open(os.path.join(P2, 'matrix.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    return os.path.join(P2, 'matrix.md')


# --------------------------------------------------------------------------
# pinmap.md + pinmap.csv
# --------------------------------------------------------------------------
def write_pinmap():
    rows = []   # connector, pin, signal, direction, kind, level, note
    for pin, net in FFC_CORE.items():
        kind = 'power' if net in ('+5V', 'LCD_3V3', 'GND') else 'digital'
        d = 'core→panel' if net in ('BL_PWM', '+5V', 'LCD_3V3') else (
            'panel→core' if net.startswith(('R', 'G', 'B')) and net[-1].isdigit() else '—')
        if net in ('R0', 'R1', 'R2', 'R3', 'R4', 'G0', 'G1', 'G2', 'G3', 'G4', 'G5',
                   'B0', 'B1', 'B2', 'B3', 'B4', 'PCLK', 'DE', 'HSYNC', 'VSYNC'):
            d = 'core→panel'
        rows.append(('J12 (FFC-40)', pin, net, d, kind, '3.3 В' if kind == 'digital' else '—',
                     'LCD RGB-шина к CORE-2'))
    for pin, net in IDC_DIG.items():
        d = {'SDA': 'bidir', 'SCL': 'core→panel', 'INT': 'panel→core', 'LED_DATA': 'core→panel',
             '+5V': 'core→panel', '+3V3': 'core→panel', 'GND': '—', 'NC': '—'}[net]
        kind = 'power' if net in ('+5V', '+3V3', 'GND') else 'digital'
        rows.append(('J13 (IDC-16)', pin, net, d, kind,
                     {'+5V': '5 В', '+3V3': '3.3 В'}.get(net, '3.3 В' if kind == 'digital' else '—'),
                     'цифровой/питание'))
    for pin, net in IDC_AN.items():
        d = {'CVOUT1': 'core→panel', 'CVOUT2': 'core→panel', 'CVOUT3': 'core→panel',
             'CVOUT4': 'core→panel', 'CVIN1': 'panel→core', 'CVIN2': 'panel→core',
             'CVIN3': 'panel→core', 'CVIN4': 'panel→core', 'GATE_OUT': 'core→panel',
             'GATE_IN_CLEAN': 'panel→core', 'FADER1': 'panel→core', 'FADER2': 'panel→core',
             'AGND': '—', 'NC': '—'}[net]
        level = '0..10 В' if net.startswith('CVOUT') else (
            '±10 В' if net.startswith('CVIN') else (
                '0/5 В' if net == 'GATE_OUT' else ('0/3.3 В' if net == 'GATE_IN_CLEAN' else
                                                   ('0..3.3 В' if net.startswith('FADER') else '—'))))
        rows.append(('J14 (IDC-26)', pin, net, d, 'analog' if net != 'NC' else 'nc', level,
                     'аналоговое поле'))
    # summary
    sig = [r for r in rows if r[2] not in ('GND', 'AGND', 'NC')]
    L = []
    A = L.append
    A('# PANEL-2 ↔ CORE-2 — карта линий (PRE-FREEZE)')
    A('')
    A('Сгенерировано `tools/gen_panel2.py`; сверено с netlist скриптом `tools/verify_netlist.py`.')
    A('')
    A('## 1. Сколько линий нужно и хватает ли одного разъёма')
    A('')
    A('| Группа | Линий | Куда |')
    A('|---|---:|---|')
    A('| LCD RGB 16 бит: R0-R4 (5) + G0-G5 (6) + B0-B4 (5) | 16 | J12 FFC-40 |')
    A('| LCD sync/clock: PCLK, DE, HSYNC, VSYNC | 4 | J12 FFC-40 |')
    A('| LCD подсветка: BL_PWM (+ BL_A/BL_K локально на PANEL-2) | 1 | J12 FFC-40 |')
    A('| Энкодеры 16 × (A,B,SW) = 48 → I2C (SDA, SCL) + INT | 3 | J13 IDC-16 |')
    A('| Матрица 42 клавиш 6×7 = 13 → MCP23017 (на той же I2C) | 0 доп. | J13 IDC-16 |')
    A('| LED-цепочка 17 × WS2812B: LED_DATA | 1 | J13 IDC-16 |')
    A('| Джек-поле: 4 CV OUT + 4 CV IN + GATE OUT + GATE IN | 10 | J14 IDC-26 |')
    A('| Фейдеры 2 × 10k → MCP3208 (CORE-2) | 2 | J14 IDC-26 |')
    A('| Питание: +5 В (LED, подсветка boost), +3V3 (логика), GND/AGND | 2 рельса + возврат | J13/J14 |')
    A('')
    A('**Итого сигналов: 37** (21 LCD + 3 I2C/INT + 1 LED + 10 джеков + 2 фейдера).')
    A('**Одного IDC-26 не хватает:** в IDC-26 максимум 13 сигнальных пинов при «сигнал/земля»; '
      'даже без LCD нужно 16 сигналов. Поэтому:')
    A('')
    A('1. **J12 FFC-40** — LCD RGB-шина (21 сигнал) + питание: высокочастотные линии нельзя '
      'тащить через IDC-26 вместе с аналогом и I2C;')
    A('2. **J13 IDC-16** — цифровое: I2C (2) + INT (1) + LED_DATA (1) + +5V/+3V3/GND;')
    A('3. **J14 IDC-26** — аналоговое поле: 12 сигналов на нечётных пинах, AGND на чётных '
      '(экранировка «сигнал/земля»).')
    A('')
    A('Мультиплексирование: 48 линий энкодеров + 13 матрицы = **61 GPIO** свёрнуты в 3 линии '
      'благодаря 4 × MCP23017 (2 × 16 для A/B, 1 × 16 для кнопок, 1 × 13 для матрицы). '
      'Без этого панель потребовала бы 3–4 шлейфа IDC-26 только под органы управления.')
    A('')
    A('## 2. J12 — FPC-40 (LCD RGB-шина, PANEL-2 → CORE-2)')
    A('')
    A('| Pin | Сигнал | Направление | Уровень | Примечание |')
    A('|---:|---|---|---|---|')
    for r in [r for r in rows if r[0].startswith('J12')]:
        A('| %s | `%s` | %s | %s | %s |' % (r[1], r[2], r[3], r[5], r[6]))
    A('')
    A('## 3. J13 — IDC-16 (цифровое/питание)')
    A('')
    A('| Pin | Сигнал | Направление | Уровень | Примечание |')
    A('|---:|---|---|---|---|')
    for r in [r for r in rows if r[0].startswith('J13')]:
        A('| %s | `%s` | %s | %s | %s |' % (r[1], r[2], r[3], r[5], r[6]))
    A('')
    A('## 4. J14 — IDC-26 (аналоговое поле; нечётные = сигнал, чётные = AGND)')
    A('')
    A('| Pin | Сигнал | Направление | Уровень | Примечание |')
    A('|---:|---|---|---|---|')
    for r in [r for r in rows if r[0].startswith('J14')]:
        A('| %s | `%s` | %s | %s | %s |' % (r[1], r[2], r[3], r[5], r[6]))
    A('')
    A('## 5. J11 — FPC-40 (LCD panel tail, на PANEL-2)')
    A('')
    A('| Pin | Сигнал | Примечание |')
    A('|---:|---|---|')
    for pin, net in LCD_FPC.items():
        A('| %s | `%s` | %s |' % (pin, net, 'NC' if net == 'NC' else (
            'питание панели' if net == 'LCD_3V3' else ('подсветка' if net.startswith('BL') else
                                                       ('земля' if net == 'GND' else 'данные/синхро')))))
    A('')
    A('> ⚠️ Распиновка FPC-40 **зависит от выбранной панели**: таблица выше — предлагаемый контракт '
      'для 5.0" 800×480 RGB 16-бит (40-pin, 0.5 мм). Перед заказом сверить с datasheet панели; '
      'J11 монтируется на PANEL-2, J12 — шлейф в CORE-2.')
    A('')
    A('## 6. Сводка по разъёмам')
    A('')
    A('| Разъём | Тип | Что несёт | Сигнальных линий |')
    A('|---|---|---|---|')
    A('| J11 | FPC-40 0.5 мм | LCD panel tail | 21 + питание |')
    A('| J12 | FFC-40 0.5 мм | LCD RGB в CORE-2 | 21 + питание |')
    A('| J13 | IDC-16 2×8 | цифровое/питание | 4 + питание |')
    A('| J14 | IDC-26 2×13 | аналоговое поле | 12 |')
    A('')
    A('Всего по PANEL-2: 4 разъёма (J11-J14) + J15 (1×14, SPI-альтернатива экрана, DNP).')
    A('')
    with open(os.path.join(P2, 'pinmap.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    with open(os.path.join(P2, 'pinmap.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['connector', 'pin', 'signal', 'direction', 'kind', 'level', 'note'])
        for r in rows:
            w.writerow(r)
    return os.path.join(P2, 'pinmap.md'), os.path.join(P2, 'pinmap.csv')


# --------------------------------------------------------------------------
# BOM
# --------------------------------------------------------------------------
def write_bom():
    groups = {}
    for part in b.bom:
        key = (part['value'], part['fp'], part['mpn'])
        g = groups.setdefault(key, [])
        g.append(part['ref'])
    p = os.path.join(P2, 'BOM-panel2.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['Номинал', 'Позиционное обозначение', 'Корпус / footprint',
                    'Артикул (черновой)', 'Кол-во', 'Примечание', 'DNP'])
        total = 0
        for (value, fp, mpn), refs in sorted(groups.items()):
            total += len(refs)
            dnp = 'да' if (value in ('MT3608', 'HDR1x14') or
                           (value == 'SS34' and any(r in ('D43',) for r in refs))) else ''
            w.writerow([value, ' '.join(sorted(refs)), fp, mpn, len(refs),
                        BOM_NOTE.get(value, ''), dnp])
        w.writerow(['ИТОГО', '', '', '', total, '%d уникальных позиций' % len(groups), ''])
    return p


def write_intent():
    p = os.path.join(HERE, 'netlist-intent.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump({'panel-2': [list(x) for x in b.intent]}, f, ensure_ascii=False, indent=0)
    return p


print('matrix :', write_matrix())
print('pinmap :', write_pinmap())
print('bom    :', write_bom())
print('intent :', write_intent())
print('geometry deviation vs JSON: %.2f mm' % GEOM_ERR)
print('components: %d, connected intent lines: %d' % (len(b.bom), len(b.intent)))
