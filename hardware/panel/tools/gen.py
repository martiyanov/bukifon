#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bukifon hardware/panel schematic generator.

Generates three KiCad (format 20250114) schematics directly as S-expressions:
  panel-1/panel-1.kicad_sch    PANEL-1   300 x 132 x 1.6
  deck-pad/deck-pad.kicad_sch  DECK-PAD  290 x  78 x 1.6
  deck-keys/deck-keys.kicad_sch DECK-KEYS 290 x 78 x 1.6

Source of truth: spec/10-panel-ui.md (§2-5) and spec/20-electronics.md (§6).
Connectivity in the schematic is label/net-name driven (each pin gets a 2.54 mm
stub + net label or power port), which is exactly how generated netlists are
normally drawn; exported netlists are verified by tools/verify_netlist.py.

Licence: CERN-OHL-S-2.0
"""
import os
import sys
import csv
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL_DIR = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from kicad_sch import Sch, pin, pin_by_name  # noqa: E402

# --------------------------------------------------------------------------
# footprints (verified against the KiCad 10.0.4 stock footprint libraries)
# --------------------------------------------------------------------------
FP = {
    'R0603': 'Resistor_SMD:R_0603_1608Metric',
    'C0603': 'Capacitor_SMD:C_0603_1608Metric',
    'EC11': 'Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm',
    'SW6': 'Button_Switch_THT:SW_PUSH_6mm',
    'SW12': 'Button_Switch_THT:SW_PUSH-12mm',
    'CHOC': '',   # custom Kailh Choc hot-swap footprint (not in stock libs), see README
    'LED2020': 'LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm',
    'SK6812': 'LED_SMD:LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount',
    '1N4148': 'Diode_SMD:D_SOD-323',
    'HC165': 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    'HC4067': 'Package_SO:SOIC-24W_7.5x15.4mm_P1.27mm',
    'MCP23017': 'Package_DIP:DIP-28_W7.62mm',
    '2N7002': 'Package_TO_SOT_SMD:SOT-23',
    'SC70': 'Package_TO_SOT_SMD:SOT-23-5',
    'LCD14': 'Connector_PinHeader_2.54mm:PinHeader_1x14_P2.54mm_Vertical',
    'IDC16': 'Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical',
    'IDC32': 'Connector_PinHeader_2.54mm:PinHeader_2x16_P2.54mm_Vertical',
    'POT30': 'Potentiometer_THT:Potentiometer_Bourns_PTA3043_Single_Slide',
    'FSR': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
}

MPN = {
    '10k': 'RC0603FR-0710KL',
    '33k': 'RC0603FR-0733KL',
    '4.7k': 'RC0603FR-074K7L',
    '3.3k': 'RC0603FR-073K3L',
    '1k': 'RC0603FR-071KL',
    '330R': 'RC0603FR-07330RL',
    '100R': 'RC0603FR-07100RL',
    '33R': 'RC0603FR-0733RL',
    '100n': 'CC0603KRX7R9BB104',
    'EC11': 'EC11E15244G1 (Bourns/Alps)',
    '74HC165': '74HC165D',
    '74HC4067': 'CD74HC4067M',
    'MCP23017': 'MCP23017-E/SP',
    'WS2812B-2020': 'WS2812B-2020',
    'SK6812MINI-E': 'SK6812MINI-E',
    '1N4148': '1N4148W',
    '2N7002': '2N7002',
    '74HCT1G125': '74HCT1G125 (символ 74AHCT1G125 - TTL-совместимый буфер, VCC 5 В)',
    'SW_PUSH_6mm': 'TS-1088-AR02016',
    'SW_PUSH-12mm': 'TS-1088-AR02016 (12x12x5)',
    'POT30': 'Bourns PTA3043-2015DPB103 (10k, 30 mm)',
    'CHOC': 'Kailh Choc v1 hot-swap socket (CPG1350)',
    'LCD14': '1x14 2.54 mm pin header / FPC adapter',
    'IDC16': 'IDC-16 2x8 box header 2.54 mm',
    'IDC32': 'IDC-32 2x16 box header 2.54 mm',
    'FSR': '2-pin pad for FSR film lead',
}

BOM_NOTE = {
    '10k': 'RC-фильтры фаз энкодеров / подтяжки / FSR-делители / затвор BL',
    '1k': 'RC слайдеров/FSR перед MCP3208, индикаторы режима',
    '100n': 'фильтры фаз энкодеров, блокировка ИС и LED, RC входов АЦП',
    '330R': 'последовательный резистор LED_DATA (WS2812)',
    '33R': 'токоограничение анода подсветки LCD',
    '100R': 'затвор Q1 подсветки',
    '4.7k': 'подтяжка I2C0 (сегмент деки); делитель DECK_ID в старой ревизии',
    '3.3k': 'делитель DECK_ID: 33k/3.3k = 0.30 В (PAD), 3.3k/33k = 3.00 В (KEYS)',
    '74HCT1G125': 'буфер LED_DATA, VCC = 5 В (вход TTL-совместим с 3.3 В)',
    '2N7002': 'ключ подсветки LCD (ШИМ GP15)',
    '33k': 'делитель DECK_ID',
    'EC11': 'энкодер гладкий с кнопкой, D-вал 6 мм, 8 шт.',
    '74HC165': 'сдвиговый регистр, каскад 6 шт. = 48 бит',
    '74HC4067': '16:1 аналоговый мультиплексор для FSR (опция velocity)',
    'MCP23017': 'I2C expander 0x20, матрица пэдов/клавиш + INT',
    'WS2812B-2020': 'RGB 2.0x2.0 мм, цепочка 3.3 В (ограничение яркости в прошивке)',
    'SK6812MINI-E': 'RGB 3.2x2.8 мм reverse-mount, цепочка 3.3 В',
    '1N4148': 'диод матрицы 6x7 (анод = клавиша, катод = столбец)',
    '2N7002': 'ключ подсветки LCD (ШИМ GP15)',
    'SW_PUSH_6mm': 'плечевая кнопка 6x6 мм, 4 шт.',
    'SW_PUSH-12mm': 'тактовая кнопка 12x12x5 мм, 18 шт.',
    'POT30': 'слайдер 30 мм, 10 кОм, линейный',
    'CHOC': 'Kailh Choc v1, hot-swap гнездо (footprint нарисовать, см. README)',
    'LCD14': 'разъём экрана 1x14 2.54 мм (ST7789 2.8")',
    'IDC16': 'IDC-16 2x8, шлейф деки',
    'IDC32': 'IDC-32 2x16 (или 2x16 pin header), шлейф к CORE-1',
    'FSR_PAD': 'посадочное место под вывод плёнки FSR (опция)',
    'LCD_ST7789_1x14': 'разъём экрана 1x14 2.54 мм (ST7789 2.8", SPI)',
}

# --------------------------------------------------------------------------
# spec coordinates (spec/10-panel-ui.md) -- panel coordinate system, mm
#   X: 0..315 left->right, Y: 0..145 back->front
# --------------------------------------------------------------------------
ENC_POS = {1: (30.0, 24.0), 2: (66.0, 24.0), 3: (30.0, 56.0), 4: (66.0, 56.0),
           5: (249.0, 24.0), 6: (285.0, 24.0), 7: (249.0, 56.0), 8: (285.0, 56.0)}
ENC_FUNC = {1: 'CUTOFF', 2: 'RESONANCE', 3: 'ATTACK', 4: 'DECAY',
            5: 'SUSTAIN', 6: 'RELEASE', 7: 'LEVEL/MIX', 8: 'TEMPO'}

BTN_POS = {'BTN_L1': (16.0, 8.0, 'L1'), 'BTN_L2': (52.0, 8.0, 'L2'),
           'BTN_R1': (263.0, 8.0, 'R1'), 'BTN_R2': (299.0, 8.0, 'R2')}
BTN_FUNC = {'BTN_L1': 'OCT-', 'BTN_L2': 'OCT+', 'BTN_R1': 'SHIFT', 'BTN_R2': 'PLAY/STOP'}

# DECK-PAD: 3x3 groups, pitch 26 mm
PAD_POS = {}
for i, y in enumerate((78.0, 104.0, 130.0)):
    for j, x in enumerate((22.0, 48.0, 74.0)):
        PAD_POS[i * 3 + j + 1] = (x, y)
    for j, x in enumerate((241.0, 267.0, 293.0)):
        PAD_POS[10 + i * 3 + j] = (x, y)

SL_POS = {1: (137.0, 98.0, 128.0), 2: (178.0, 98.0, 128.0)}
SL_FUNC = {1: 'CUTOFF', 2: 'MIX'}

# DECK-KEYS: 21 + 21, pitch 18 x 17 mm
KEY_POS = {}
_k = 1
for y in (74.0, 91.0, 108.0):
    for x in (20.0, 38.0, 56.0, 74.0, 92.0, 110.0):
        KEY_POS[_k] = (x, y); _k += 1
for x in (39.0, 57.0, 75.0):
    KEY_POS[_k] = (x, 126.0); _k += 1          # KEY19..21 (left thumb)
for y in (74.0, 91.0, 108.0):
    for x in (205.0, 223.0, 241.0, 259.0, 277.0, 295.0):
        KEY_POS[_k] = (x, y); _k += 1
for x in (240.0, 258.0, 276.0):
    KEY_POS[_k] = (x, 126.0); _k += 1          # KEY40..42 (right thumb)

# matrix cell of every key: (row 1..6, col 1..7)
KEY_MATRIX = {}
for n in range(1, 19):                          # left main 3x6, row-major
    KEY_MATRIX[n] = ((n - 1) // 6 + 1, (n - 1) % 6 + 1)
for i, n in enumerate((19, 20, 21)):            # left thumbs -> col 7
    KEY_MATRIX[n] = (i + 1, 7)
for n in range(22, 40):                         # right main 3x6
    KEY_MATRIX[n] = ((n - 22) // 6 + 4, (n - 22) % 6 + 1)
for i, n in enumerate((40, 41, 42)):            # right thumbs -> col 7
    KEY_MATRIX[n] = (i + 4, 7)

# PAD matrix: row 1..3 (Y), col 1..6 (X)
PAD_MATRIX = {}
for n in range(1, 10):
    PAD_MATRIX[n] = ((n - 1) // 3 + 1, (n - 1) % 3 + 1)
for n in range(10, 19):
    PAD_MATRIX[n] = ((n - 10) // 3 + 1, (n - 10) % 3 + 4)


# Library symbols that are KiCad "derived" symbols (extends) are embedded flattened,
# which makes ERC report lib_symbol_mismatch. Use the generic/base symbol instead and put
# the real part number in Value + Footprint (standard KiCad practice for generic parts);
# the exported netlist/BOM then carries the correct part.
SYM_ALIAS = {
    ('74xx', '74HC165'): ('74xx', '74LS165'),
    ('Diode', '1N4148'): ('Diode', '1N4001'),
    ('LED', 'SK6812MINI-E'): ('LED', 'SK6812'),
    ('Interface_Expansion', 'MCP23017x-x-SP'): ('Interface_Expansion', 'MCP23017x-x-SO'),
    ('Transistor_FET', '2N7002'): ('Transistor_FET', 'Q_NMOS_GSD'),
    # 74AHCT1G125 is a derived symbol in the KiCad library -> use its base
    # (74LVC1G125, same SOT-23-5 pinout) and keep the real part in Value.
    ('74xGxx', '74AHCT1G125'): ('74xGxx', '74LVC1G125'),
}

# --------------------------------------------------------------------------
# board builder
# --------------------------------------------------------------------------
class Board:
    def __init__(self, slug, title, paper):
        self.slug = slug
        self.title = title
        self.paper = paper
        self.sch = Sch(os.path.join(PANEL_DIR, slug, slug + '.kicad_sch'),
                       title, paper, slug)
        self.bom = []
        self.intent = []        # (ref, pin_number, pin_name, net or None for NC)
        self._n = 0

    # -- generic part -----------------------------------------------------
    def part(self, lib, name, ref, value, x, y, fp='', note='', props=None):
        lib, name = SYM_ALIAS.get((lib, name), (lib, name))
        p = self.sch.sym(lib, name, ref, value, x, y, fp)
        self.bom.append(dict(board=self.slug, ref=ref, value=value, fp=fp,
                             mpn=MPN.get(value, ''), note=note))
        return p

    def r(self, ref, value, x, y, note=''):
        return self.part('Device', 'R', ref, value, x, y, FP['R0603'], note)

    def c(self, ref, value, x, y, note=''):
        return self.part('Device', 'C', ref, value, x, y, FP['C0603'], note)

    # -- net helpers (every connection is recorded as "design intent") ----
    def _intent(self, comp, net, num=None, pname=None):
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
        self.sch.net(comp, name, num=num, **kw)
        self._intent(comp, name, num=num)

    def nc(self, comp, num):
        self.sch.nc_pin(comp, num=num)
        self._intent(comp, None, num=num)

    def nc_pin(self, comp, pname):
        self.sch.nc_pin(comp, pname=pname)
        self._intent(comp, None, pname=pname)

    def done(self):
        self.sch.write()
        return self.sch.path


# --------------------------------------------------------------------------
# PANEL-1
# --------------------------------------------------------------------------
def panel_1():
    b = Board('panel-1', 'Bukifon PANEL-1 - 300x132x1.6 - 8xEC11 / 6x74HC165 / ST7789 2.8" / 9xWS2812B', 'A1')
    s = b.sch
    s.text('PANEL-1  Bukifon  v1.0  (spec/20-electronics.md 6.1)  300 x 132 x 1.6 mm  '
           'CERN-OHL-S-2.0   upper part Y 0..66, deck niche Y 66..145 (spec 10-panel-ui 3)',
           (25.4, 25.4), 2.2)
    s.text('Coordinates of all controls = spec/10-panel-ui.md (ENC1..8, BTN_L1/L2/R1/R2, '
           'deck IDC-16, screen 1x14).  Connectivity is net-label based.', (25.4, 33.02), 1.5)

    # ---------------------------------------------------------------- buses
    # 74HC165 bit map (bit index 0 = first encoder, see matrix-tables.md)
    bits = {}
    for i in range(1, 9):
        bits[(i - 1) * 2] = 'ENC%d_A' % i
        bits[(i - 1) * 2 + 1] = 'ENC%d_B' % i
    for i in range(1, 9):
        bits[16 + i - 1] = 'ENC%d_PUSH' % i
    bits[24] = 'BTN_L1'; bits[25] = 'BTN_L2'; bits[26] = 'BTN_R1'; bits[27] = 'BTN_R2'

    # ------------------------------------------------------------ encoders
    ex0, eystep, ey = 38.1, 86.36, 63.5
    encs = {}
    for i in range(1, 9):
        x = ex0 + (i - 1) * eystep
        c = b.part('Device', 'RotaryEncoder_Switch', 'ENC%d' % i, 'EC11',
                   x, ey, FP['EC11'], 'EC11 smooth, with push switch; %s' % ENC_FUNC[i])
        encs[i] = c
        b.net(c, 'A', 'ENC%d_A' % i)
        b.net(c, 'B', 'ENC%d_B' % i)
        b.net(c, 'C', 'GND')
        b.net(c, 'S1', 'ENC%d_PUSH' % i)
        b.net(c, 'S2', 'GND')
        # phase RC: 10k pull-up (the R of the RC) + 100n to GND, x2 per encoder
        for k, ph in enumerate(('A', 'B')):
            xr = x + k * 25.4
            r = b.r('R%d' % (100 + (i - 1) * 3 + k), '10k', xr, ey + 50.8,
                    'ENC%d phase %s pull-up / RC' % (i, ph))
            b.rail(r, '1', '+3V3'); b.net(r, '2', 'ENC%d_%s' % (i, ph))
            cp = b.c('C%d' % (100 + (i - 1) * 2 + k), '100n', xr, ey + 78.74,
                     'ENC%d phase %s 100n filter' % (i, ph))
            b.net(cp, '1', 'ENC%d_%s' % (i, ph)); b.rail(cp, '2', 'GND')
        rsw = b.r('R%d' % (200 + i), '10k', x + 50.8, ey + 50.8, 'ENC%d push pull-up' % i)
        b.rail(rsw, '1', '+3V3'); b.net(rsw, '2', 'ENC%d_PUSH' % i)

    s.text('8 x EC11 (smooth, with push switch) + 16 x RC 10k/100n on A/B + 8 x 10k '
           'push pull-up', (25.4, 96.52), 2.0)

    # ------------------------------------------------------- 74HC165 chain
    hx0, hstep, hy = 76.2, 111.76, 279.4
    hc = {}
    for k in range(1, 7):
        x = hx0 + (k - 1) * hstep
        u = b.part('74xx', '74HC165', 'U%d' % k, '74HC165', x, hy, FP['HC165'],
                   '8-bit PISO, stage %d of 6 (bits %d..%d)' % (k, (k - 1) * 8, k * 8 - 1))
        hc[k] = u
        for j in range(8):
            bit = (k - 1) * 8 + j
            b.net_pin(u, 'D%d' % j, bits.get(bit, 'GND'))
        b.net_pin(u, 'CP', 'HC_CP')
        b.net_pin(u, '~{PL}', 'HC_PL')
        b.net_pin(u, '~{CE}', 'GND')
        b.net_pin(u, 'VCC', '+3V3')
        b.net_pin(u, 'GND', 'GND')
        b.nc_pin(u, '~{Q7}')
        if k == 6:
            b.net_pin(u, 'Q7', 'HC_QH')
        else:
            b.net_pin(u, 'Q7', 'HC_SER%d' % k)
        if k == 1:
            b.net_pin(u, 'DS', 'GND')
        else:
            b.net_pin(u, 'DS', 'HC_SER%d' % (k - 1))
        dc = b.c('C%d' % (200 + k), '100n', x, hy + 43.18, '74HC165 U%d decoupling' % k)
        b.rail(dc, '1', '+3V3'); b.rail(dc, '2', 'GND')

    s.text('6 x 74HC165 cascade = 48 bits.  CP=HC_CP(GP2)  PL=HC_PL(GP6)  QH=HC_QH(GP4/MISO).  '
           'bits 0..15 encoders A/B, 16..23 encoder push, 24..27 shoulder, 28..47 reserved(GND).',
           (25.4, 243.84), 2.0)

    # ------------------------------------------------------ shoulder buttons
    for i, (name, (px, py, short)) in enumerate(BTN_POS.items()):
        x = 63.5 + i * 40.64
        y = 368.3
        sw = b.part('Switch', 'SW_Push', name, 'SW_PUSH_6mm', x, y, FP['SW6'],
                    'shoulder button %s (%s), 6x6 mm' % (short, BTN_FUNC[name]))
        b.net(sw, '1', name); b.rail(sw, '2', 'GND')
        r = b.r('R%d' % (210 + i), '10k', x, y - 25.4, '%s pull-up' % name)
        b.rail(r, '1', '+3V3'); b.net(r, '2', name)

    s.text('4 x shoulder button 6x6 mm -> 74HC165 bits 24..27 (BTN_L1/L2/R1/R2), '
           'active low, 10k pull-up', (25.4, 337.82), 2.0)

    # ----------------------------------------------------- WS2812B chain x9
    chain = ['LED_ENC%d' % i for i in range(1, 9)] + ['LED_STATUS']
    lx0, lstep, ly = 63.5, 58.42, 419.1
    # LED_DATA (GP7, 3.3 V) -> 74HCT1G125 (VCC = 5 V, TTL input) -> 330R -> LED_IN.
    # The whole WS2812 chain runs from +5 V (spec/20-electronics.md 2/3/6.1).
    buf = b.part('74xGxx', '74AHCT1G125', 'U7', '74HCT1G125', 76.2, 393.7, FP['SC70'],
                 'LED_DATA buffer: 3.3 V in -> 5 V out, VCC = +5V')
    b.net(buf, '2', 'LED_DATA')      # A
    b.net(buf, '1', 'GND')           # /OE = enable
    b.net(buf, '5', '+5V')           # VCC
    b.net(buf, '3', 'GND')
    b.net(buf, '4', 'LED_BUF')       # Y
    cbuf = b.c('C500', '100n', 139.7, 393.7, 'U7 buffer decoupling (+5V)')
    b.rail(cbuf, '1', '+5V'); b.rail(cbuf, '2', 'GND')
    r330 = b.r('R300', '330R', 109.22, 393.7, 'LED_DATA (5 V) series resistor after buffer')
    b.net(r330, '1', 'LED_BUF'); b.net(r330, '2', 'LED_IN')
    prev = 'LED_IN'
    for i, ref in enumerate(chain):
        x = lx0 + i * lstep
        led = b.part('LED', 'WS2812B-2020', ref, 'WS2812B-2020', x, ly, FP['LED2020'],
                     'addressable RGB, %s' % ('status' if ref == 'LED_STATUS' else 'knob ring'))
        b.net_pin(led, 'DIN', prev)
        b.net_pin(led, 'VDD', '+5V')
        b.net_pin(led, 'VSS', 'GND')
        out = 'LED_CHAIN%d' % (i + 1) if i < len(chain) - 1 else 'LED_OUT'
        b.net_pin(led, 'DOUT', out)
        prev = out
        dc = b.c('C%d' % (300 + i), '100n', x, ly + 30.48, '%s decoupling (+5V rail)' % ref)
        b.rail(dc, '1', '+5V'); b.rail(dc, '2', 'GND')

    s.text('9 x WS2812B-2020 (8 knob rings + status) from +5V. GP7 (3V3) -> U7 74HCT1G125 '
           '(VCC = +5V, TTL input) -> R300 330R -> LED_IN ... LED_OUT -> deck chain. '
           'Chain current is limited by firmware brightness (spec/40). DECK_ID/DECK_INT: '
           'see notes at J-DECK/J-CORE.', (25.4, 469.9), 1.6)

    # ------------------------------------------------------------- LCD 1x14
    lcd = b.part('Connector_Generic', 'Conn_01x14', 'J-LCD', 'LCD_ST7789_1x14',
                 96.52, 533.4, FP['LCD14'], '2.8" ST7789 SPI module, 1x14 pin header')
    lcd_map = {
        '1': 'GND', '2': '+3V3',
        '3': 'LCD_CS', '4': 'LCD_DC', '5': 'LCD_RST',
        '6': 'LCD_SCK', '7': 'LCD_MOSI', '8': 'GND',
        '9': 'LCD_BL_A', '10': 'LCD_BL_K',
        '11': 'GND', '12': 'GND', '13': 'GND', '14': 'GND',
    }
    for num, net in lcd_map.items():
        b.rail(lcd, num, net)

    # backlight low-side switch 2N7002 (PWM GP15) + series LED resistor
    rbl = b.r('R301', '33R', 139.7, 508.0, 'backlight LED anode series resistor')
    b.rail(rbl, '1', '+3V3'); b.net(rbl, '2', 'LCD_BL_A')
    q = b.part('Transistor_FET', '2N7002', 'Q1', '2N7002', 190.5, 520.7,
               FP['2N7002'], 'backlight low-side switch, PWM GP15')
    b.net_pin(q, 'D', 'LCD_BL_K')
    b.net_pin(q, 'S', 'GND')
    b.net_pin(q, 'G', 'Q1_G')
    rg = b.r('R302', '100R', 165.1, 508.0, 'BL gate series')
    b.net(rg, '1', 'LCD_BL'); b.net(rg, '2', 'Q1_G')
    rpd = b.r('R303', '10k', 165.1, 546.1, 'BL gate pull-down')
    b.net(rpd, '1', 'Q1_G'); b.rail(rpd, '2', 'GND')

    s.text('LCD 2.8" ST7789 320x240 on SPI1 (SCK/MOSI), CS/DC/RST, BL via Q1 2N7002 (PWM GP15). '
           'Pin 1 is marked by the square pad; module pinouts differ - check the module before '
           'soldering the 1x14 header.', (25.4, 490.22), 1.6)

    # --------------------------------------------------- deck connector 2x8
    jd = b.part('Connector_Generic', 'Conn_02x08_Odd_Even', 'J-DECK', 'IDC16',
                292.1, 533.4, FP['IDC16'], 'deck ribbon IDC-16 (spec 20-electronics 6.2)')
    deck_map = {
        '1': '+3V3', '2': 'GND', '3': 'SDA', '4': 'SCL',
        '5': 'DECK_INT', '6': 'GND', '7': 'LED_OUT', '8': 'GND',
        '9': 'SL1_RAW', '10': 'GND', '11': 'SL2_RAW', '12': 'GND',
        '13': 'DECK_ID', '14': 'GND', '15': 'FSR_RAW', '16': '+5V',
    }
    for num, net in deck_map.items():
        b.rail(jd, num, net)

    # slider RC (1k + 100n) before the core ADC, per spec 6.2
    for i, (raw, net_, refr, refc) in enumerate((('SL1_RAW', 'SL1', 'R310', 'C310'),
                                                 ('SL2_RAW', 'SL2', 'R311', 'C311'))):
        x = 355.6 + i * 30.48
        r = b.r(refr, '1k', x, 505.46, '%s series RC (ADC anti-alias)' % net_)
        b.net(r, '1', raw); b.net(r, '2', net_)
        c = b.c(refc, '100n', x, 535.94, '%s 100n to GND' % net_)
        b.net(c, '1', net_); b.rail(c, '2', 'GND')

    rf = b.r('R312', '1k', 416.56, 505.46, 'FSR series RC')
    b.net(rf, '1', 'FSR_RAW'); b.net(rf, '2', 'FSR')
    cf = b.c('C312', '100n', 416.56, 535.94, 'FSR 100n to GND')
    b.net(cf, '1', 'FSR'); b.rail(cf, '2', 'GND')

    cid = b.c('C313', '100n', 447.04, 535.94, 'DECK_ID filter')
    b.net(cid, '1', 'DECK_ID'); b.rail(cid, '2', 'GND')

    # I2C pull-ups for the deck segment (core has its own 4.7k)
    for i, (net_, ref) in enumerate((('SDA', 'R320'), ('SCL', 'R321'))):
        x = 477.52 + i * 25.4
        r = b.r(ref, '4.7k', x, 505.46, 'I2C0 %s pull-up for deck ribbon' % net_)
        b.rail(r, '1', '+3V3'); b.net(r, '2', net_)

    s.text('J-DECK IDC-16 pinout = spec/20-electronics.md 6.2 (odd pins = signal, even = GND). '
           'SL1/SL2 get the 1k/100n RC on PANEL-1 before the MCP3208 (CH0/CH1), FSR -> CH6, '
           'DECK_ID -> GP27, DECK_INT -> GP28 (spec/20 2: GP28 = DECK_INT, GATE1 = GP22, '
           'GATE2 = GP26).',
           (25.4, 573.0), 1.5)

    # --------------------------------------------------- IDC-32 to CORE-1
    jp = b.part('Connector_Generic', 'Conn_02x16_Odd_Even', 'J-CORE', 'IDC32',
                736.6, 520.7, FP['IDC32'], 'ribbon to CORE-1 J-PANEL, IDC-32 2x16')
    core_map = {
        '1': '+3V3', '2': 'GND',
        '3': 'LCD_SCK', '4': 'LCD_MOSI',
        '5': 'LCD_CS', '6': 'LCD_DC',
        '7': 'LCD_RST', '8': 'LCD_BL',
        '9': 'HC_CP', '10': 'HC_PL',
        '11': 'HC_QH', '12': 'LED_DATA',
        '13': 'SDA', '14': 'SCL',
        '15': 'SL1', '16': 'SL2',
        '17': 'FSR', '18': 'DECK_ID',
        '19': 'DECK_INT', '20': 'GND',
        '21': '+5V', '22': 'GND',
        '23': 'GND', '24': 'GND', '25': 'GND', '26': 'GND',
        '27': 'GND', '28': 'GND', '29': 'GND', '30': 'GND',
        '31': 'GND', '32': 'GND',
    }
    for num, net in core_map.items():
        b.rail(jp, num, net)

    s.text('J-CORE IDC-32 (2x16) -> CORE-1 J-PANEL:  SPI1 display (SCK/MOSI/CS/DC/RST/BL), '
           'SPI0 SCK(HC_CP)+MISO(HC_QH), HC_PL, LED_DATA, I2C0 (SDA/SCL) + deck analog '
           '(SL1/SL2/FSR/DECK_ID/DECK_INT), 3V3, 5V, GND.', (560.0, 380.0), 1.8)
    s.text('PINOUT OF J-CORE (2x16, odd = signal / even = GND)', (560.0, 390.0), 1.8)
    for i in range(16):
        odd = core_map[str(2 * i + 1)]
        s.text('%2d  %-10s   %2d  GND' % (2 * i + 1, odd, 2 * i + 2),
               (560.0, 398.0 + i * 6.35), 1.4)

    # power anchors (net drivers for ERC)
    for i, rail in enumerate(('+3V3', '+5V', 'GND')):
        s.power_anchor(rail, 40.64 + i * 30.48, 200.66)

    return b


# --------------------------------------------------------------------------
# DECK-PAD
# --------------------------------------------------------------------------
def deck_pad():
    b = Board('deck-pad', 'Bukifon DECK-PAD - 290x78 - 18 pads 12x12 / 18xWS2812B / 2 faders / MCP23017 / 2x74HC4067 FSR', 'A1')
    s = b.sch
    s.text('DECK-PAD  Bukifon  v1.0  290 x 78 x 1.6 mm  (spec/10-panel-ui.md 3.1, '
           'spec/20-electronics.md 6.3)  CERN-OHL-S-2.0', (25.4, 25.4), 2.5)
    s.text('18 tactile 12x12x5 + 18x WS2812B-2020 + 2x 30 mm fader (10k, 3V3) + MCP23017 (0x20, '
           'matrix 3x6) + 2x 74HC4067 (FSR option) + IDC-16', (25.4, 33.02), 1.5)

    # --------------------------------------------------------- pad matrix
    pads = {}
    for n in range(1, 19):
        row, col = PAD_MATRIX[n]
        x = 63.5 + (col - 1) * 50.8
        y = 114.3 + (row - 1) * 45.72
        px, py = PAD_POS[n]
        sw = b.part('Switch', 'SW_Push', 'PAD%d' % n, 'SW_PUSH-12mm', x, y, FP['SW12'],
                    'pad %d, panel X=%.1f Y=%.1f' % (n, px, py))
        pads[n] = sw
        b.net(sw, '1', 'ROW%d' % row)
        b.net(sw, '2', 'COL%d' % col)

    s.text('PAD1..PAD18 matrix 3 rows x 6 columns (ROW1..3 = MCP23017 GPA0..GPA2 driven low, '
           'COL1..6 = GPB0..GPB5 read with external 10k pull-up R21..R26). Panel coordinates '
           'in matrix-tables.md.', (25.4, 89.9), 1.8)

    # ------------------------------------------------------------- LEDs
    lp = 'LED_IN'
    for n in range(1, 19):
        row, col = PAD_MATRIX[n]
        x = 63.5 + (col - 1) * 50.8
        y = 292.1 + (row - 1) * 45.72
        led = b.part('LED', 'WS2812B-2020', 'LED_PAD%d' % n, 'WS2812B-2020', x, y,
                     FP['LED2020'], 'RGB under pad %d (chain from +5V, pin 16 J-DECK)' % n)
        b.net_pin(led, 'DIN', lp)
        b.net_pin(led, 'VDD', '+5V')
        b.net_pin(led, 'VSS', 'GND')
        if n < 18:
            lp = 'LED_CH%d' % n
            b.net_pin(led, 'DOUT', lp)
        else:
            b.nc_pin(led, 'DOUT')          # end of the deck chain

    s.text('18 x WS2812B-2020 in one chain after LED_IN from PANEL-1, powered from +5V '
           '(J-DECK pin 16), 100n per LED. Last DOUT = no connect. Brightness is limited by '
           'firmware (total 9+18 or 9+42 LEDs).', (25.4, 267.97), 1.8)

    # decoupling caps for LEDs
    for n in range(1, 19):
        row, col = PAD_MATRIX[n]
        x = 63.5 + (col - 1) * 50.8
        y = 419.1 + (row - 1) * 35.56
        c = b.c('C%d' % (100 + n), '100n', x, y, 'LED_PAD%d decoupling (+5V)' % n)
        b.rail(c, '1', '+5V'); b.rail(c, '2', 'GND')

    # ------------------------------------------------------------- faders
    pots = {}
    for i, n in enumerate((1, 2)):
        x = 440.69 + i * 45.72
        pt = b.part('Device', 'R_Potentiometer', 'SL%d' % n, 'POT30',
                    x, 152.4, FP['POT30'], '30 mm fader %d (%s), 10k linear, 3V3' % (n, SL_FUNC[n]))
        pots[n] = pt
        b.rail(pt, '1', '+3V3')
        b.rail(pt, '3', 'GND')
        b.net(pt, '2', 'SL%d_RAW' % n)

    s.text('SL1/SL2 = 30 mm slide pots (10k) across 3V3, wipers on the ribbon; the 1k/100n RC '
           'is on PANEL-1 before the MCP3208 CH0/CH1.', (416.56, 106.68), 1.8)

    # --------------------------------------------------------- MCP23017
    u = b.part('Interface_Expansion', 'MCP23017x-x-SP', 'U1', 'MCP23017', 584.2, 152.4,
               FP['MCP23017'], 'I2C I/O expander, address 0x20 (A0..A2 = GND)')
    for n in range(1, 4):
        b.net_pin(u, 'GPA%d' % (n - 1), 'ROW%d' % n)
    for n in range(1, 7):
        b.net_pin(u, 'GPB%d' % (n - 1), 'COL%d' % n)
    b.net_pin(u, 'GPA3', 'MUX_S0')
    b.net_pin(u, 'GPA4', 'MUX_S1')
    b.net_pin(u, 'GPA5', 'MUX_S2')
    b.net_pin(u, 'GPA6', 'MUX_S3')
    b.nc_pin(u, 'GPA7')
    b.net_pin(u, 'GPB6', 'MUX_EN1')
    b.net_pin(u, 'GPB7', 'MUX_EN2')
    b.net_pin(u, 'SCK', 'SCL')
    b.net_pin(u, 'SDA', 'SDA')
    b.net_pin(u, 'V_{DD}', '+3V3')
    b.net_pin(u, 'V_{SS}', 'GND')
    for a in ('A0', 'A1', 'A2'):
        b.net_pin(u, a, 'GND')
    b.net_pin(u, 'INTA', 'DECK_INT')
    b.nc_pin(u, 'INTB')
    rrst = b.r('R1', '10k', 584.2 - 30.48, 106.68, 'MCP23017 /RESET pull-up')
    b.rail(rrst, '1', '+3V3'); b.net(rrst, '2', 'MCP_RST')
    b.net_pin(u, '~{RESET}', 'MCP_RST')
    cdec = b.c('C1', '100n', 584.2 + 30.48, 106.68, 'MCP23017 decoupling')
    b.rail(cdec, '1', '+3V3'); b.rail(cdec, '2', 'GND')
    # external column pull-ups (MCP23017 internal is 100k - too weak over the ribbon)
    for col in range(1, 7):
        r = b.r('R%d' % (20 + col), '10k', 520.7 + (col - 1) * 20.32, 215.9,
                'COL%d pull-up (matrix read)' % col)
        b.rail(r, '1', '+3V3'); b.net(r, '2', 'COL%d' % col)
    # NC pins 11 / 14 are left open (pin type "unconnected" in the library symbol)

    # ------------------------------------------------- mux 74HC4067 x2
    mux1 = b.part('74xx', 'CD74HC4067M', 'U2', '74HC4067', 685.8, 165.1, FP['HC4067'],
                  '16:1 analog mux, FSR1..FSR16 (velocity option)')
    mux2 = b.part('74xx', 'CD74HC4067M', 'U3', '74HC4067', 685.8, 368.3, FP['HC4067'],
                  '16:1 analog mux, FSR17/FSR18 (channels 2..15 unused, tied to GND)')
    for mux, en, chans in ((mux1, 'MUX_EN1', 16), (mux2, 'MUX_EN2', 2)):
        for i, sn in enumerate(('S0', 'S1', 'S2', 'S3')):
            b.net_pin(mux, sn, 'MUX_S%d' % i)
        b.net_pin(mux, '~{E}', en)
        b.net_pin(mux, 'COM', 'FSR')
        b.net_pin(mux, 'VCC', '+3V3')
        b.net_pin(mux, 'GND', 'GND')
        for ch in range(16):
            if ch < chans:
                b.net_pin(mux, 'I%d' % ch, 'FSR%d' % (ch + 1 + (0 if mux is mux1 else 16)))
            else:
                b.net_pin(mux, 'I%d' % ch, 'GND')
    for j, (mux, ref) in enumerate(((mux1, 'C4'), (mux2, 'C5'))):
        c = b.c(ref, '100n', 685.8, mux is mux1 and 205.74 or 408.94, 'mux decoupling')
        b.rail(c, '1', '+3V3'); b.rail(c, '2', 'GND')

    s.text('FSR option: 18 x 2-pin pad (film lead) + 10k pull-up to 3V3, one node per mux channel; '
           'channel select S0..S3 = MCP23017 GPA3..GPA6, enable = GPB6/GPB7. When the FSR film is '
           'not fitted the channel reads full scale (3V3) - normal.', (25.4, 254.0), 1.6)

    # ----------------------------------------------------- FSR landing pads
    for n in range(1, 19):
        y = 88.9 + (n - 1) * 25.4
        p = b.part('Connector_Generic', 'Conn_01x02', 'FSR%d' % n, 'FSR_PAD', 787.4, y,
                   FP['FSR'], 'FSR %d landing pad (option)' % n)
        b.rail(p, '1', 'FSR%d' % n); b.rail(p, '2', 'GND')
        r = b.r('R%d' % (60 + n), '10k', 736.6, y - 8.89, 'FSR%d pull-up' % n)
        b.rail(r, '1', '+3V3'); b.net(r, '2', 'FSR%d' % n)

    s.text('FSR pads (option): FSR1..FSR16 -> U2 I0..I15, FSR17/FSR18 -> U3 I0/I1.',
           (711.2, 71.12), 1.8)

    # --------------------------------------------------------- DECK_ID
    rid1 = b.r('R10', '33k', 450.34, 457.2, 'DECK_ID top (33k)')
    b.rail(rid1, '1', '+3V3'); b.net(rid1, '2', 'DECK_ID')
    rid2 = b.r('R11', '3.3k', 450.34, 487.68, 'DECK_ID bottom (3.3k)')
    b.net(rid2, '1', 'DECK_ID'); b.rail(rid2, '2', 'GND')
    s.text('DECK_ID for DECK-PAD: 33k / 3.3k -> 3.3*3.3/36.3 = 0.30 V '
           '(spec/20-electronics.md 6.2: 0.30 V +-0.15 V)', (475.0, 472.44), 1.5)

    # ---------------------------------------------------------- IDC-16
    j = b.part('Connector_Generic', 'Conn_02x08_Odd_Even', 'J-DECK', 'IDC16',
               292.1, 533.4, FP['IDC16'], 'deck ribbon, IDC-16 2x8 (spec 6.2)')
    deck_map = {
        '1': '+3V3', '2': 'GND', '3': 'SDA', '4': 'SCL',
        '5': 'DECK_INT', '6': 'GND', '7': 'LED_IN', '8': 'GND',
        '9': 'SL1_RAW', '10': 'GND', '11': 'SL2_RAW', '12': 'GND',
        '13': 'DECK_ID', '14': 'GND', '15': 'FSR', '16': '+5V',
    }
    for num, net in deck_map.items():
        b.rail(j, num, net)

    s.power_anchor('+3V3', 520.7, 546.1)
    s.power_anchor('+5V', 543.56, 546.1)
    s.power_anchor('GND', 566.42, 546.1)
    return b


# --------------------------------------------------------------------------
# DECK-KEYS
# --------------------------------------------------------------------------
def deck_keys():
    b = Board('deck-keys', 'Bukifon DECK-KEYS - 290x78 - 42x Kailh Choc hotswap / 42x1N4148 matrix 6x7 / 42x SK6812MINI-E / 2 faders / MCP23017', 'A0')
    s = b.sch
    s.text('DECK-KEYS  Bukifon  v1.0  290 x 78 x 1.6 mm  (spec/10-panel-ui.md 3.2, '
           'spec/20-electronics.md 6.4)  CERN-OHL-S-2.0', (25.4, 25.4), 2.5)
    s.text('42 x Kailh Choc (hot-swap socket) + 42 x 1N4148, matrix 6 rows x 7 columns on MCP23017 '
           '(0x20) + 42 x SK6812MINI-E + 2 x 30 mm fader + IDC-16', (25.4, 33.02), 1.5)

    # ------------------------------------------------------ key matrix 6x7
    for n in range(1, 43):
        row, col = KEY_MATRIX[n]
        x = 63.5 + (col - 1) * 50.8
        y = 114.3 + (row - 1) * 50.8
        kx, ky = KEY_POS[n]
        sw = b.part('Switch', 'SW_Push', 'KEY%d' % n, 'CHOC', x, y, FP['CHOC'],
                    'Kailh Choc v1, panel X=%.1f Y=%.1f' % (kx, ky))
        b.net(sw, '1', 'ROW%d' % row)
        b.net(sw, '2', 'KEY%d_N' % n)
        d = b.part('Diode', '1N4148', 'D%d' % n, '1N4148', x, y + 25.4, FP['1N4148'],
                   'matrix diode KEY%d (anode = switch, cathode = column)' % n)
        b.net(d, '2', 'KEY%d_N' % n)     # anode
        b.net(d, '1', 'COL%d' % col)     # cathode

    s.text('Matrix 6 rows x 7 cols: ROW1..3 = left half, ROW4..6 = right half, COL1..6 = main '
           'columns, COL7 = thumb row. ROWn = MCP23017 GPA0..GPA5 (driven low), COLn = GPB0..GPB6 '
           '(read with pull-up). Full KEYn <-> (row,col) <-> panel coordinate table: '
           'matrix-tables.md', (25.4, 89.9), 1.6)

    # ---------------------------------------------------------- 42 LEDs
    lp = 'LED_IN'
    for n in range(1, 43):
        row, col = KEY_MATRIX[n]
        x = 63.5 + (col - 1) * 50.8
        y = 419.1 + (row - 1) * 50.8
        led = b.part('LED', 'SK6812MINI-E', 'LED_KEY%d' % n, 'SK6812MINI-E', x, y,
                     FP['SK6812'], 'RGB per key %d (reverse mount, chain from +5V)' % n)
        b.net_pin(led, 'DIN', lp)
        b.net_pin(led, 'VDD', '+5V')
        b.net_pin(led, 'VSS', 'GND')
        if n < 42:
            lp = 'LED_CH%d' % n
            b.net_pin(led, 'DOUT', lp)
        else:
            b.nc_pin(led, 'DOUT')          # end of the deck chain
    s.text('42 x SK6812MINI-E, chain after LED_IN from PANEL-1, powered from +5V '
           '(J-DECK pin 16), 100n per LED; last DOUT = no connect.', (25.4, 384.81), 1.8)

    # LED decoupling
    for n in range(1, 43):
        row, col = KEY_MATRIX[n]
        x = 63.5 + (col - 1) * 50.8
        y = 419.1 + (row - 1) * 50.8 + 20.32
        c = b.c('C%d' % (100 + n), '100n', x, y, 'LED_KEY%d decoupling (+5V)' % n)
        b.rail(c, '1', '+5V'); b.rail(c, '2', 'GND')

    # --------------------------------------------------------- MCP23017
    u = b.part('Interface_Expansion', 'MCP23017x-x-SP', 'U1', 'MCP23017', 573.0, 152.4,
               FP['MCP23017'], 'I2C I/O expander, address 0x20 (A0..A2 = GND)')
    for r in range(1, 7):
        b.net_pin(u, 'GPA%d' % (r - 1), 'ROW%d' % r)
    for c in range(1, 8):
        b.net_pin(u, 'GPB%d' % (c - 1), 'COL%d' % c)
    b.nc_pin(u, 'GPA6')
    b.net_pin(u, 'GPA7', 'LED_MODE1_K')
    b.net_pin(u, 'SCK', 'SCL')
    b.net_pin(u, 'SDA', 'SDA')
    b.net_pin(u, 'V_{DD}', '+3V3')
    b.net_pin(u, 'V_{SS}', 'GND')
    for a in ('A0', 'A1', 'A2'):
        b.net_pin(u, a, 'GND')
    b.net_pin(u, 'INTA', 'DECK_INT')
    b.nc_pin(u, 'INTB')
    b.net_pin(u, '~{RESET}', 'MCP_RST')
    rrst = b.r('R1', '10k', 520.7, 106.68, 'MCP23017 /RESET pull-up')
    b.rail(rrst, '1', '+3V3'); b.net(rrst, '2', 'MCP_RST')
    cdec = b.c('C1', '100n', 520.7, 142.24, 'MCP23017 decoupling')
    b.rail(cdec, '1', '+3V3'); b.rail(cdec, '2', 'GND')

    # 2 mode indicator LEDs: the matrix uses 13 pins, so GPA7 and GPB7 are free
    for i, (gpio, refd, refr) in enumerate((('LED_MODE1_K', 'LED_MODE1', 'R2'),
                                            ('LED_MODE2_K', 'LED_MODE2', 'R3'))):
        x = 640.08 + i * 45.72
        d = b.part('Device', 'LED', refd, 'LED', x, 457.2, 'LED_SMD:LED_0603_1608Metric',
                   'deck mode indicator %d (central zone)' % (i + 1))
        b.net_pin(d, 'K', gpio)
        b.net_pin(d, 'A', '+3V3')
        r = b.r(refr, '1k', x, 495.3, '%s series resistor' % refd)
        b.net(r, '1', gpio); b.rail(r, '2', 'GND')
    b.net_pin(u, 'GPB7', 'LED_MODE2_K')
    for col in range(1, 8):
        r = b.r('R%d' % (20 + col), '10k', 520.7 + (col - 1) * 20.32, 520.7,
                'COL%d pull-up (matrix read)' % col)
        b.rail(r, '1', '+3V3'); b.net(r, '2', 'COL%d' % col)

    s.text('Matrix 42 keys uses GPA0..5 + GPB0..6; GPA7/GPB7 drive the 2 central-zone mode '
           'indicators (1k series, active low).', (25.4, 400.05), 1.5)

    # ------------------------------------------------------------ faders
    for i, n in enumerate((1, 2)):
        x = 440.69 + i * 45.72
        pt = b.part('Device', 'R_Potentiometer', 'SL%d' % n, 'POT30', x, 152.4,
                    FP['POT30'], '30 mm fader %d (%s), 10k linear, 3V3' % (n, SL_FUNC[n]))
        b.rail(pt, '1', '+3V3'); b.rail(pt, '3', 'GND')
        b.net(pt, '2', 'SL%d_RAW' % n)

    s.text('SL1/SL2 in the central zone (x 110..205, same coordinates as DECK-PAD): 30 mm slide '
           'pots across 3V3, 1k/100n RC on PANEL-1.', (416.56, 106.68), 1.8)

    # --------------------------------------------------------- DECK_ID
    rid1 = b.r('R4', '3.3k', 450.34, 330.2, 'DECK_ID top (3.3k)')
    b.rail(rid1, '1', '+3V3'); b.net(rid1, '2', 'DECK_ID')
    rid2 = b.r('R5', '33k', 450.34, 360.68, 'DECK_ID bottom (33k)')
    b.net(rid2, '1', 'DECK_ID'); b.rail(rid2, '2', 'GND')
    s.text('DECK_ID for DECK-KEYS: 3.3k / 33k -> 3.3*33/36.3 = 3.00 V '
           '(spec/20-electronics.md 6.2: 3.00 V +-0.15 V)', (475.0, 345.44), 1.5)

    # ------------------------------------------------------------ IDC-16
    j = b.part('Connector_Generic', 'Conn_02x08_Odd_Even', 'J-DECK', 'IDC16',
               711.2, 723.9, FP['IDC16'], 'deck ribbon, IDC-16 2x8 (spec 6.2)')
    deck_map = {
        '1': '+3V3', '2': 'GND', '3': 'SDA', '4': 'SCL',
        '5': 'DECK_INT', '6': 'GND', '7': 'LED_IN', '8': 'GND',
        '9': 'SL1_RAW', '10': 'GND', '11': 'SL2_RAW', '12': 'GND',
        '13': 'DECK_ID', '14': 'GND', '15': 'GND', '16': '+5V',
    }
    for num, net in deck_map.items():
        b.rail(j, num, net)
    s.text('J-DECK pin 15 (FSR) is not used on DECK-KEYS -> GND; pin 16 = +5V (LED chain).',
           (711.2, 754.38), 1.5)

    s.power_anchor('+3V3', 900.0, 700.0)
    s.power_anchor('+5V', 922.86, 700.0)
    s.power_anchor('GND', 945.72, 700.0)
    return b


# --------------------------------------------------------------------------
# documentation tables (matrix-tables.md)
# --------------------------------------------------------------------------
def write_matrix_tables(boards):
    p = os.path.join(PANEL_DIR, 'matrix-tables.md')
    L = []
    A = L.append
    A('# Bukifon PANEL-1 / DECK-PAD / DECK-KEYS — таблицы соединений')
    A('')
    A('Сгенерировано `tools/gen.py` из тех же структур данных, что и схемы; сверено с')
    A('экспортированными netlist-ами скриптом `tools/verify_netlist.py` (см. `erc/` и README).')
    A('Координаты — в системе панели `spec/10-panel-ui.md` §1 (X 0…315 вправо, Y 0…145 вперёд), мм.')
    A('')
    A('---')
    A('')
    A('## 1. PANEL-1: 74HC165 — карта 48 бит')
    A('')
    A('6 × 74HC165 включены каскадом: `U1.Q7 → U2.DS → … → U6.Q7 = HC_QH` (MISO).')
    A('Первым из линии читается `U6.H` (бит 47), последним — `U1.A` (бит 0).')
    A('Тактирование: `HC_CP` = GP2 (SPI0 SCK), загрузка: `HC_PL` = GP6, данные: `HC_QH` = GP4.')
    A('')
    A('| Бит | 74HC165 | Вход | Цепь | Функция |')
    A('|---:|---|---|---|---|')
    b = boards['panel-1']
    bits = {}
    for i in range(1, 9):
        bits[(i - 1) * 2] = ('ENC%d_A' % i, 'ENC%d фаза A' % i)
        bits[(i - 1) * 2 + 1] = ('ENC%d_B' % i, 'ENC%d фаза B' % i)
    for i in range(1, 9):
        bits[16 + i - 1] = ('ENC%d_PUSH' % i, 'ENC%d кнопка (нажатие)' % i)
    bits[24] = ('BTN_L1', 'плечевая L1 (OCT−)')
    bits[25] = ('BTN_L2', 'плечевая L2 (OCT+)')
    bits[26] = ('BTN_R1', 'плечевая R1 (SHIFT)')
    bits[27] = ('BTN_R2', 'плечевая R2 (PLAY/STOP)')
    for bit in range(48):
        stage = bit // 8 + 1
        letter = 'ABCDEFGH'[bit % 8]
        net, func = bits.get(bit, ('GND', 'резерв (подтянут к GND)'))
        A('| %d | U%d | D%d | `%s` | %s |' % (bit, stage, bit % 8, net, func))
    A('')
    A('Соответствие пинов 74HC165: D0…D7 = выводы 11,12,13,14,3,4,5,6; CP = 2, ~PL = 1,')
    A('~CE = 15 (GND), DS = 10, Q7 = 9, ~Q7 = 7 (не используется, no-connect), VCC = 16, GND = 8.')
    A('')
    A('## 2. PANEL-1: координаты ↔ цепи')
    A('')
    A('### 2.1 Энкодеры EC11 (`spec/10-panel-ui.md` §2.2)')
    A('')
    A('| Имя | X | Y | Функция v1.0 | Цепи |')
    A('|---|---:|---:|---|---|')
    for i in range(1, 9):
        x, y = ENC_POS[i]
        A('| ENC%d | %.1f | %.1f | %s | `ENC%d_A`, `ENC%d_B` (74HC165 биты %d/%d), '
          '`ENC%d_PUSH` (бит %d) |' % (i, x, y, ENC_FUNC[i], i, i, (i - 1) * 2, (i - 1) * 2 + 1,
                                       i, 16 + i - 1))
    A('')
    A('RC-фильтр на каждой фазе: 10 kΩ к +3V3 (он же подтяжка) + 100 nF на GND.')
    A('Кнопка энкодера: 10 kΩ к +3V3, второй контакт на GND, активный низкий.')
    A('')
    A('### 2.2 Плечевые кнопки (`spec/10-panel-ui.md` §2.3)')
    A('')
    A('| Имя | X | Y | Ø | Функция | Бит 74HC165 |')
    A('|---|---:|---:|---:|---|---:|')
    for name, (x, y, short) in BTN_POS.items():
        bit = 24 + list(BTN_POS).index(name)
        A('| %s | %.0f | %.0f | 8 | %s | %d |' % (name, x, y, BTN_FUNC[name], bit))
    A('')
    A('### 2.3 Экран 2.8" ST7789 — разъём `J-LCD` 1×14')
    A('')
    A('| Pin | Цепь | К CORE-1 |')
    A('|---:|---|---|')
    lcd = {'1': 'GND', '2': '+3V3', '3': 'LCD_CS', '4': 'LCD_DC', '5': 'LCD_RST',
           '6': 'LCD_SCK', '7': 'LCD_MOSI', '8': 'GND', '9': 'LCD_BL_A',
           '10': 'LCD_BL_K', '11': 'GND', '12': 'GND', '13': 'GND', '14': 'GND'}
    lcd_core = {'1': '—', '2': '—', '3': 'GP12', '4': 'GP13', '5': 'GP14', '6': 'GP10 (SPI1 SCK)',
                '7': 'GP11 (SPI1 MOSI)', '8': '—', '9': 'через 33 Ω от +3V3',
                '10': 'сток Q1 2N7002', '11': '—', '12': '—', '13': '—', '14': '—'}
    for k in map(str, range(1, 15)):
        A('| %s | `%s` | %s |' % (k, lcd[k], lcd_core[k]))
    A('')
    A('Подсветка: `LCD_BL` (GP15, ШИМ) → 100 Ω → затвор Q1 (2N7002), 10 kΩ на GND,')
    A('сток Q1 = `LCD_BL_K` (pin 10), исток = GND; анод (pin 9) через 33 Ω на +3V3.')
    A('')
    A('### 2.4 LED-цепочка PANEL-1 (9 × WS2812B-2020)')
    A('')
    A('Цепочка питается от **+5 В**. `LED_DATA` (GP7, 3.3 В) → U7 `74HCT1G125` (VCC = +5 В, '
      'TTL-вход) → R300 330 Ω → `LED_IN` = LED_ENC1 → … → LED_ENC8 → LED_STATUS → '
      '`LED_OUT` (pin 7 J-DECK → LED_IN деки). 100 нФ на каждый светодиод — на +5 В.')
    A('')
    A('| # | Позиция | Цепь DIN | Цепь DOUT |')
    A('|---:|---|---|---|')
    for i in range(1, 10):
        name = 'LED_ENC%d' % i if i <= 8 else 'LED_STATUS'
        din = 'LED_IN' if i == 1 else 'LED_CHAIN%d' % (i - 1)
        dout = 'LED_CHAIN%d' % i if i < 9 else 'LED_OUT'
        A('| %d | %s | `%s` | `%s` |' % (i, name, din, dout))
    A('')
    A('### 2.5 Разъём деки `J-DECK` IDC-16 (2×8) — `spec/20-electronics.md` §6.2')
    A('')
    A('| Pin | Сигнал PANEL | Pin | Сигнал |')
    A('|---:|---|---:|---|')
    dp = {'1': '+3V3', '2': 'GND', '3': 'SDA', '4': 'SCL', '5': 'DECK_INT', '6': 'GND',
          '7': 'LED_OUT', '8': 'GND', '9': 'SL1_RAW', '10': 'GND', '11': 'SL2_RAW',
          '12': 'GND', '13': 'DECK_ID', '14': 'GND', '15': 'FSR_RAW', '16': '+5V'}
    for i in range(8):
        A('| %d | `%s` | %d | `%s` |' % (2 * i + 1, dp[str(2 * i + 1)],
                                         2 * i + 2, dp[str(2 * i + 2)]))
    A('')
    A('Pin 16 = **+5 В** — питание LED-цепочек деки (`spec/20-electronics.md` §6.2); данные')
    A('`LED_IN` приходят с панели с уровнем 5 В, поэтому уровни светодиодов деки и данных совпадают.')
    A('SL1/SL2: на PANEL-1 RC 1 kΩ + 100 nF → `SL1`/`SL2` → MCP3208 CH0/CH1 (CORE-1).')
    A('FSR: RC 1 kΩ + 100 nF → `FSR` → MCP3208 CH6. DECK_ID → GP27 (ADC1/ADC2 вход Pico).')
    A('Interrupt деки → `DECK_INT` → **GP28** (`spec/20-electronics.md` §2: «GP28 — DECK_INT,')
    A('прерывание MCP23017 деки»; GATE1 = GP22, GATE2 = GP26, DECK_ID = GP27).')
    A('На PANEL-1 цепь идёт: pin 5 J-DECK → pin 19 J-CORE → GP28 CORE-1.')
    A('')
    A('### 2.6 `J-CORE` IDC-32 (2×16) → CORE-1 `J-PANEL`')
    A('')
    A('| Pin | Сигнал | Пины Pico (CORE-1) | Pin | Сигнал |')
    A('|---:|---|---|---:|---|')
    core = {1: ('+3V3', 'LDO 3.3 В'), 3: ('LCD_SCK', 'GP10'), 5: ('LCD_CS', 'GP12'),
            7: ('LCD_RST', 'GP14'), 9: ('HC_CP', 'GP2'), 11: ('HC_QH', 'GP4'),
            13: ('SDA', 'GP8'), 15: ('SL1', 'MCP3208 CH0'), 17: ('FSR', 'MCP3208 CH6'),
            19: ('DECK_INT', 'GP28 (DECK_INT)'), 21: ('+5V', 'MP1584 / LED-цепочка'), 23: ('GND', '—'),
            25: ('GND', '—'), 27: ('GND', '—'), 29: ('GND', '—'), 31: ('GND', '—')}
    pairs = [(1, 2, 'GND'), (3, 4, 'LCD_MOSI / GP11'), (5, 6, 'LCD_DC / GP13'),
             (7, 8, 'LCD_BL / GP15'), (9, 10, 'HC_PL / GP6'), (11, 12, 'LED_DATA / GP7'),
             (13, 14, 'SCL / GP9'), (15, 16, 'SL2 / MCP3208 CH1'), (17, 18, 'DECK_ID / GP27'),
             (19, 20, 'GND'), (21, 22, 'GND'), (23, 24, 'GND'), (25, 26, 'GND'),
             (27, 28, 'GND'), (29, 30, 'GND'), (31, 32, 'GND')]
    for odd, even, second in pairs:
        a, an = core[odd]
        A('| %d | `%s` | %s | %d | %s |' % (odd, a, an, even, second))
    A('')
    A('Чётные пины 2, 6…20 — GND; 22…32 — GND (шлейф, экран). Полная таблица — в схеме')
    A('(`Text` у разъёма) и в `panel-1/panel-1.kicad_sch`.')
    A('')
    A('---')
    A('')
    A('## 3. DECK-PAD: матрица 3×6 на MCP23017 (адрес 0x20)')
    A('')
    A('Строки `ROW1..ROW3` — выходы GPA0..GPA2 (поочерёдно 0), столбцы `COL1..COL6` —')
    A('входы GPB0..GPB5 с внешней подтяжкой 10 кΩ к +3V3 (R21..R26), активный низкий уровень.')
    A('')
    A('| Пэд | ROW | COL | X | Y | Цепь строки | Цепь столбца |')
    A('|---|---:|---:|---:|---:|---|---|')
    for n in range(1, 19):
        row, col = PAD_MATRIX[n]
        x, y = PAD_POS[n]
        A('| PAD%d | %d | %d | %.0f | %.0f | `ROW%d` (GPA%d) | `COL%d` (GPB%d) |'
          % (n, row, col, x, y, row, row - 1, col, col - 1))
    A('')
    A('`INT` (INTA, вывод 20) → `DECK_INT` (pin 5 J-DECK); `A0..A2` = GND → адрес 0x20;')
    A('`/RESET` через 10 kΩ на +3V3; NC (выводы 11, 14) не подключены.')
    A('')
    A('### 3.1 74HC4067 / FSR (опция velocity)')
    A('')
    A('S0..S3 = GPA3..GPA6 (общие для обоих мультиплексоров), ~E1 = GPB6, ~E2 = GPB7.')
    A('`COM` обоих мультиплексоров объединён в цепь `FSR` → pin 15 J-DECK → MCP3208 CH6.')
    A('Каждый канал: +3V3 → 10 kΩ → узел `FSRn` → плёнка FSR → GND; узел на вход Ix.')
    A('')
    A('| MUX | Канал | Цепь | Пэд | ROW/COL пэда | X | Y |')
    A('|---|---:|---|---|---:|---:|---:|')
    for n in range(1, 19):
        mux = 'U2' if n <= 16 else 'U3'
        ch = (n - 1) if n <= 16 else (n - 17)
        row, col = PAD_MATRIX[n]
        x, y = PAD_POS[n]
        A('| %s | I%d | `FSR%d` | PAD%d | %d/%d | %.0f | %.0f |'
          % (mux, ch, n, n, row, col, x, y))
    A('')
    A('Если плёнка FSR не установлена, узел подтянут к +3V3 → канал читается как максимум;')
    A('это нормально, velocity-режим просто выключен в прошивке.')
    A('')
    A('### 3.2 DECK-PAD: слайдеры и DECK_ID')
    A('')
    A('| Имя | X | Ход Y | Функция | Цепь |')
    A('|---|---:|---|---|---|')
    for n in (1, 2):
        x, y0, y1 = SL_POS[n]
        A('| SL%d | %.1f | %d…%d | %s | `SL%d_RAW` (pin %d J-DECK) |'
          % (n, x, y0, y1, SL_FUNC[n], n, 9 if n == 1 else 11))
    A('')
    A('DECK_ID (pin 13): 33 kΩ на +3V3, 3.3 kΩ на GND → 3.3 × 3.3 / 36.3 = **0.30 В**')
    A('(`spec/20-electronics.md` §6.2: DECK_PAD = 0.30 В ±0.15 В).')
    A('')
    A('---')
    A('')
    A('## 4. DECK-KEYS: матрица 6×7 на MCP23017 (адрес 0x20)')
    A('')
    A('ROW1..ROW3 — левая половина, ROW4..ROW6 — правая; COL1..COL6 — основные колонки,')
    A('COL7 — ряд больших пальцев. ROWn = GPA(n−1) (низкий активный), COLn = GPB(n−1)')
    A('с внешней подтяжкой 10 кΩ к +3V3 (R21..R27). Диод 1N4148: анод = клавиша, катод = столбец.')
    A('GPA7 / GPB7 свободны → 2 индикатора режима (`LED_MODE1`, `LED_MODE2`, 1 kΩ, активный низкий).')
    A('')
    A('| Клавиша | ROW | COL | X | Y | Диод |')
    A('|---|---:|---:|---:|---:|---|')
    for n in range(1, 43):
        row, col = KEY_MATRIX[n]
        x, y = KEY_POS[n]
        A('| KEY%d | %d | %d | %.0f | %.0f | D%d (анод=клавиша, катод=`COL%d`) |'
          % (n, row, col, x, y, n, col))
    A('')
    A('DECK_ID (pin 13): 3.3 kΩ на +3V3, 33 kΩ на GND → 3.3 × 33 / 36.3 = **3.00 В**')
    A('(`spec/20-electronics.md` §6.2: DECK_KEYS = 3.00 В ±0.15 В).')
    A('')
    A('### 4.1 DECK-KEYS: LED-цепочка (42 × SK6812MINI-E)')
    A('')
    A('`LED_IN` (pin 7 J-DECK) → LED_KEY1 → … → LED_KEY42 → `LED_END` (последний DOUT, без')
    A('нагрузки). Порядок = порядок номеров KEYn (левая половина 1…21, правая 22…42).')
    A('')
    A('| # | Цепь DIN | Цепь DOUT | Клавиша | X | Y |')
    A('|---:|---|---|---|---:|---:|')
    for n in range(1, 43):
        x, y = KEY_POS[n]
        din = 'LED_IN' if n == 1 else 'LED_CH%d' % (n - 1)
        dout = 'LED_CH%d' % n if n < 42 else 'LED_END'
        A('| %d | `%s` | `%s` | KEY%d | %.0f | %.0f |' % (n, din, dout, n, x, y))
    A('')
    A('---')
    A('')
    A('## 5. Сводка по шинам питания (по схемам)')
    A('')
    A('| Плата | +5V (оценка) | +3V3 (оценка) | Что питается |')
    A('|---|---|---|---|')
    A('| PANEL-1 | 9 LED × ~10 мА + буфер U7 (5 мА) | ≈ 100 мА (экран 60 мА) | 9×WS2812B-2020 '
      '(+5 В), 74HCT1G125, 8×EC11 (RC), 6×74HC165, ST7789, Q1 BL |')
    A('| DECK-PAD | 18 LED × ~10 мА (pin 16 J-DECK) | MCP23017 (1 мА) + 2 мультиплексора + '
      'матрица | 18×WS2812B-2020 (+5 В), 18×12 мм кнопок, FSR-делители |')
    A('| DECK-KEYS | 42 LED × ~10 мА (pin 16 J-DECK) | MCP23017 + матрица + 2 fader | '
      '42×SK6812MINI-E (+5 В) |')
    A('')
    A('Все LED-цепочки питаются от **+5 В**: панель — напрямую (J-CORE pin 21), деки — через')
    A('pin 16 IDC-16 (`spec/20-electronics.md` §6.2). Данные `LED_DATA` (GP7, 3.3 В) проходят')
    A('через буфер U7 `74HCT1G125` (VCC = +5 В) и далее идут по цепочке с уровнем 5 В, включая')
    A('`LED_IN` деки — уровни светодиодов и данных совпадают, даташитные ограничения соблюдены.')
    A('')
    A('Ограничение яркости — обязанность прошивки (`spec/40-firmware.md`): 9 LED на панели и 18/42')
    A('в деке; при 10 мА на LED суммарно по +5 В ≈ 120…200 мА (бюджет +5 В — до 0.8 А).')
    A('')
    A('## 6. Обозначения для прошивки')
    A('')
    A('| Сущность | Обозначение в схеме | Индексы |')
    A('|---|---|---|')
    A('| Энкодеры | `ENC1..ENC8` (+ `ENCn_A`, `ENCn_B`, `ENCn_PUSH`) | 1…8 |')
    A('| Плечевые | `BTN_L1`, `BTN_L2`, `BTN_R1`, `BTN_R2` | — |')
    A('| Пэды | `PAD1..PAD18` (+ `ROW1..3`, `COL1..6`) | 1…18 |')
    A('| Клавиши | `KEY1..KEY42` (+ `ROW1..6`, `COL1..7`) | 1…42 |')
    A('| Слайдеры | `SL1`, `SL2` (+ `SL1_RAW`, `SL2_RAW`) | 1…2 |')
    A('| RGB панели | `LED_ENC1..8`, `LED_STATUS` | 9 |')
    A('| RGB пэдов | `LED_PAD1..18` | 18 |')
    A('| RGB клавиш | `LED_KEY1..42` | 42 |')
    A('| Тип деки | `DECK_ID` | PAD = 0.41 В, KEYS = 2.89 В |')
    A('')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    return p


# --------------------------------------------------------------------------
# BOM (hardware BOM for the three boards)
# --------------------------------------------------------------------------
def write_bom(boards):
    p = os.path.join(PANEL_DIR, 'BOM-panel.csv')
    rows = []
    for slug, b in boards.items():
        groups = {}
        for part in b.bom:
            key = (part['value'], part['fp'], part['mpn'])
            g = groups.setdefault(key, dict(refs=[], note=part['note']))
            g['refs'].append(part['ref'])
            if part['note'] and part['note'] not in g['note']:
                g['note'] = part['note']
        for (value, fp, mpn), g in groups.items():
            rows.append(dict(board=slug, refs=' '.join(sorted(g['refs'])),
                             value=value, footprint=fp, mpn=mpn,
                             qty=len(g['refs']), note=BOM_NOTE.get(value, '')))
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['Плата', 'Позиционное обозначение', 'Номинал', 'Корпус / footprint',
                    'Артикул (предложение)', 'Кол-во', 'Примечание'])
        order = ['panel-1', 'deck-pad', 'deck-keys']
        for slug in order:
            sub = [r for r in rows if r['board'] == slug]
            for r in sorted(sub, key=lambda r: (-r['qty'], r['value'])):
                w.writerow([slug, r['refs'], r['value'], r['footprint'], r['mpn'],
                            r['qty'], r['note']])
            w.writerow([slug, 'ИТОГО позиций', '', '', '', sum(r['qty'] for r in sub),
                        '%d уникальных номиналов' % len(sub)])
        w.writerow(['ВСЕГО', '', '', '', '', sum(r['qty'] for r in rows), ''])
    return p


# --------------------------------------------------------------------------
def write_intent(boards):
    import json
    out = {}
    for slug, b in boards.items():
        out[slug] = [list(x) for x in b.intent]
    p = os.path.join(HERE, 'netlist-intent.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    return p


# --------------------------------------------------------------------------
# machine-readable panel coordinates for the mechanics team
# (spec/10-panel-ui.md; panel frame X 0..315 right, Y 0..145 towards the player)
# --------------------------------------------------------------------------
def write_coords():
    p = os.path.join(PANEL_DIR, 'coords-panel.csv')
    rows = []
    rows.append(('panel', 'J-LCD', 157.5, 37.0, 'window 60x46 R2', 'screen 2.8" ST7789, active 57.6x43.2'))
    for i in range(1, 9):
        x, y = ENC_POS[i]
        rows.append(('panel', 'ENC%d' % i, x, y, 'hole D7.2; knob D18x15; bushing M7',
                     'EC11 smooth + push, %s' % ENC_FUNC[i]))
    for name, (x, y, short) in BTN_POS.items():
        rows.append(('panel', name, x, y, 'hole D8', 'shoulder %s, %s' % (short, BTN_FUNC[name])))
    for n in range(1, 19):
        x, y = PAD_POS[n]
        rows.append(('deck-pad', 'PAD%d' % n, x, y, 'pad 20x20, travel 1.2',
                     'tactile 12x12x5, matrix ROW%d/COL%d' % PAD_MATRIX[n]))
    for n in (1, 2):
        x, y0, y1 = SL_POS[n]
        for board in ('deck-pad', 'deck-keys'):
            rows.append((board, 'SL%d' % n, x, (y0 + y1) / 2.0,
                         'slot 8x34 R4; travel 30 (Y %d..%d)' % (y0, y1),
                         'fader 30 mm 10k, %s' % SL_FUNC[n]))
    for n in range(1, 43):
        x, y = KEY_POS[n]
        rows.append(('deck-keys', 'KEY%d' % n, x, y, 'cap 17.5x16.5; window 14.2x14.2',
                     'Kailh Choc, matrix ROW%d/COL%d' % KEY_MATRIX[n]))
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['board', 'entity', 'x_mm', 'y_mm', 'mechanical', 'note'])
        for r in rows:
            w.writerow(['%s' % r[0], r[1], '%.1f' % r[2], '%.1f' % r[3], r[4], r[5]])
    return p


def main():
    boards = {}
    for fn, slug in ((panel_1, 'panel-1'), (deck_pad, 'deck-pad'), (deck_keys, 'deck-keys')):
        b = fn()
        path = b.done()
        boards[slug] = b
        print('written %s (%d components)' % (path, len(b.bom)))
    print('tables:', write_matrix_tables(boards))
    print('bom   :', write_bom(boards))
    print('intent:', write_intent(boards))
    print('coords:', write_coords())


if __name__ == '__main__':
    main()
