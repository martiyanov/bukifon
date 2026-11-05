#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LCD FFC-40 adapter (breakout) for PicoMod / Bukifon — schematic + docs generator.

Purpose: bring-up of the 5.0" 800x480 RGB565 FFC-40 panel (HotLCD TFT-H050A1SVIST4R40,
ST7262) on the P1 bench **before** the PCB exists. The adapter repeats PANEL-2 J12
(FFC-40, 23 signals) 1:1 into test pads and drives the panel FFC-40 through 0R
"pinout jumpers", so the real HotLCD pinout can be dialled in without a board re-spin
(O-15 "адаптер ждёт образец").

Outputs (all in hardware/panel2/adapter-lcd/):
  LCD-ADAPTER.kicad_sch / .pdf / svg/ / .net / erc/  — schematic + exports + ERC
  BOM-lcd-adapter.csv                               — draft BOM
  README.md                                         — what it is, how to order/use
  ../../docs/49-lcd-adapter.md                       — full doc (pinout, FFC rules, bench)

Licence: CERN-OHL-S-2.0
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AD = os.path.abspath(os.path.join(HERE, '..'))          # hardware/panel2/adapter-lcd
P2 = os.path.abspath(os.path.join(AD, '..'))            # hardware/panel2
ROOT = os.path.abspath(os.path.join(P2, '..', '..'))    # repo root
sys.path.insert(0, HERE)
from kicad_sch import Sch  # noqa: E402

FP = {
    'R0603': 'Resistor_SMD:R_0603_1608Metric',
    'C0603': 'Capacitor_SMD:C_0603_1608Metric',
    'FFC40': 'Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal',
    'JST2': 'Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
    'TP': 'TestPoint:TestPoint_Pad_D1.5mm',
    'HOLE': 'MountingHole:MountingHole_3.2mm_M3',
}

MPN = {
    'FFC40_ZIF': 'Hirose FH12-40S-0.5SH (ZIF, 0.5 мм, нижний контакт)',
    'FFC40_KIT': 'FFC-40 0.5 мм шлейф, same/opposite side, 100 мм + 150 мм',
    'JST2': 'JST PH 2-pin (B2B-PH-K) — вход внешнего boost подсветки 18…22 В',
    '0R': 'RC0603FR-070RL', '10k': 'RC0603FR-0710KL',
    '100n': 'CC0603KRX7R9BB104', '10u': 'CL10A106KP8NNNC',
    'TP': 'Test point pad 1.5 мм', 'M3': 'Винт M3 + гайка (крепление панели)',
    'TFT': 'TFT-H050A1SVIST4R40 (HotLCD, 5.0" 800x480 IPS, ST7262, FPC-40)',
}

# --------------------------------------------------------------------------
# J12 PANEL-2 pinout (rev.2, 23 signals) — input FFC-40 of this adapter
# --------------------------------------------------------------------------
J12 = {
    '1': 'GND', '2': 'GND', '3': 'R0', '4': 'R1', '5': 'R2', '6': 'R3', '7': 'R4',
    '8': 'G0', '9': 'G1', '10': 'G2', '11': 'G3', '12': 'G4', '13': 'G5',
    '14': 'B0', '15': 'B1', '16': 'B2', '17': 'B3', '18': 'B4',
    '19': 'GND', '20': 'GND', '21': 'PCLK', '22': 'DE', '23': 'HSYNC', '24': 'VSYNC',
    '25': 'GND', '26': 'GND', '27': 'LCD_3V3', '28': 'LCD_3V3', '29': 'GND',
    '30': 'BL_PWM', '31': 'BL_ANODE', '32': 'BL_CATHODE',
    '33': 'GND', '34': 'GND', '35': 'GND', '36': 'GND', '37': 'GND', '38': 'GND',
    '39': 'GND', '40': 'GND',
}

# --------------------------------------------------------------------------
# Proposed HotLCD TFT-H050A1SVIST4R40 (ST7262) 40-pin pinout — MUST be verified
# against the sample datasheet / multimeter before trusting (O-15).
# --------------------------------------------------------------------------
PANEL_PINOUT = {
    '1': 'LED_K', '2': 'LED_A', '3': 'GND', '4': '3V3', '5': 'GND',
    '6': 'R0', '7': 'R1', '8': 'R2', '9': 'R3', '10': 'R4', '11': 'R5', '12': 'R6', '13': 'R7',
    '14': 'G0', '15': 'G1', '16': 'G2', '17': 'G3', '18': 'G4', '19': 'G5', '20': 'G6', '21': 'G7',
    '22': 'B0', '23': 'B1', '24': 'B2', '25': 'B3', '26': 'B4', '27': 'B5', '28': 'B6', '29': 'B7',
    '30': 'GND', '31': 'PCLK', '32': 'DE', '33': 'HS', '34': 'VS', '35': 'DISP',
    '36': 'GND', '37': '3V3', '38': '3V3', '39': 'GND', '40': 'GND',
}

# --------------------------------------------------------------------------
# RGB565 -> 8 bit/channel mapping (panel LSBs to GND) and jumper sources
# --------------------------------------------------------------------------
def rgb565_map():
    """[(panel_signal, source_net, note)] for the 24 RGB lines + sync + DISP + BL."""
    m = []
    for i in range(8):                       # panel R0..R7
        m.append(('R%d' % i,
                  ('GND' if i < 3 else 'R%d' % (i - 3)),
                  'GND' if i < 3 else 'J12.R%d (PANEL-2)' % (i - 3)))
    for i in range(8):                       # panel G0..G7
        m.append(('G%d' % i,
                  ('GND' if i < 2 else 'G%d' % (i - 2)),
                  'GND' if i < 2 else 'J12.G%d (PANEL-2)' % (i - 2)))
    for i in range(8):                       # panel B0..B7
        m.append(('B%d' % i,
                  ('GND' if i < 3 else 'B%d' % (i - 3)),
                  'GND' if i < 3 else 'J12.B%d (PANEL-2)' % (i - 3)))
    m += [('PCLK', 'PCLK', 'J12.PCLK'), ('DE', 'DE', 'J12.DE'),
          ('HS', 'HSYNC', 'J12.HSYNC'), ('VS', 'VSYNC', 'J12.VSYNC'),
          ('DISP', 'DISP_CTRL', '0R to +3V3 (default ON) / pad for external'), ]
    return m


SIGNALS = rgb565_map()          # 29 entries
BL_SIGNALS = [('LED_K', 'BL_CATHODE', 'J12.BL_CATHODE (или внешний boost J3)'),
              ('LED_A', 'BL_ANODE', 'J12.BL_ANODE (или внешний boost J3)')]

# --------------------------------------------------------------------------
PART_MPN = {
    '0R': 'RC0603FR-070RL', '10k': 'RC0603FR-0710KL',
    '100n': 'CC0603KRX7R9BB104', '10u': 'CL10A106KP8NNNC',
    '10k_r': 'RC0603FR-0710KL',
}


class B:
    def __init__(self):
        self.sch = Sch(os.path.join(AD, 'LCD-ADAPTER.kicad_sch'),
                       'PicoMod/Bukifon LCD FFC-40 adapter (HotLCD ST7262) - '
                       'PRE-FREEZE bench adapter, DO NOT FABRICATE',
                       'A1', 'LCD-ADAPTER')
        self.bom = []
        self.intent = []

    def part(self, lib, name, ref, value, x, y, fp='', note=''):
        p = self.sch.sym(lib, name, ref, value, x, y, fp)
        self.bom.append(dict(ref=ref, value=value, fp=fp, mpn=MPN.get(value, PART_MPN.get(value, '')),
                             note=note))
        return p

    def r(self, ref, value, x, y, note=''):
        return self.part('Device', 'R', ref, value, x, y, FP['R0603'], note)

    def c(self, ref, value, x, y, note=''):
        return self.part('Device', 'C', ref, value, x, y, FP['C0603'], note)

    def net(self, comp, num, name, **kw):
        self.sch.net(comp, name, num=num, **kw)
        self.intent.append((comp['ref'], str(num), name))

    def nc(self, comp, num):
        self.sch.nc_pin(comp, num=num)
        self.intent.append((comp['ref'], str(num), None))

    def done(self):
        return self.sch.write()


b = B()
s = b.sch

# --------------------------------------------------------------------------
# title
# --------------------------------------------------------------------------
s.text('! LCD FFC-40 ADAPTER — PRE-FREEZE BENCH ADAPTER — DO NOT FABRICATE !', (25.4, 25.4), 4.0)
s.text('PANEL-2 J12 (FFC-40, 23 сигнала) -> test pads + panel FFC-40 (HotLCD '
       'TFT-H050A1SVIST4R40, ST7262). Монтаж панели: 120.7 x 75.8, плата ~120 x 76 x 1.6 (2 слоя). '
       'CERN-OHL-S-2.0', (25.4, 34.0), 1.8)
s.text('Назначение: проверка экрана на P1-стенде ДО PCB. Пин-аут панели — ПРЕДПОЛОЖЕНИЕ, '
       'проверять по образцу/мультиметру (O-15): 0R-«перемычки» позволяют переназначить '
       'любую линию без перевыпуска платы. Крепление 4 x M3, внешний boost подсветки 18…22 В.',
       (25.4, 40.0), 1.5)

# --------------------------------------------------------------------------
# J1 — input FFC-40 from PANEL-2 J12
# --------------------------------------------------------------------------
j1 = b.part('Connector_Generic', 'Conn_01x40', 'J1', 'FFC40_ZIF', 63.5, 254.0, FP['FFC40'],
            'Вход: FFC-40 (cable от PANEL-2 J12), ZIF 0.5 мм; pin 1 = красная метка')
for pin, net in J12.items():
    b.net(j1, int(pin), net)

# --------------------------------------------------------------------------
# J2 — panel FFC-40 (proposed HotLCD pinout)
# --------------------------------------------------------------------------
j2 = b.part('Connector_Generic', 'Conn_01x40', 'J2', 'FFC40_ZIF', 457.2, 254.0, FP['FFC40'],
            'Выход: FFC-40 хвост панели TFT-H050A1SVIST4R40 (ZIF 0.5 мм, pinout TBD)')
PANEL_NET = {}
for pin, sig in PANEL_PINOUT.items():
    if sig == 'GND':
        b.net(j2, int(pin), 'GND')
    elif sig == '3V3':
        b.net(j2, int(pin), '+3V3')
    else:
        PANEL_NET[pin] = 'P_' + sig
        b.net(j2, int(pin), 'P_' + sig)

# --------------------------------------------------------------------------
# 0R "pinout jumpers": panel signal pin <-> source (J12 / GND / DISP_CTRL)
# --------------------------------------------------------------------------
jump = list(SIGNALS) + list(BL_SIGNALS)
n_j = 0
for i, (sig, src, note) in enumerate(jump):
    col, row = i % 6, i // 6
    x = 127.0 + col * 38.1
    y = 149.86 + row * 27.94
    n_j += 1
    jr = b.r('R%d' % n_j, '0R', x, y, 'перемычка P_%s <-> %s' % (sig, src))
    b.net(jr, '1', 'P_' + sig)
    b.net(jr, '2', src)
    # test pad on every panel signal
    tp = b.part('Connector', 'TestPoint', 'TP%d' % n_j, 'TP', x - 16.51, y, FP['TP'],
                'TP %s' % sig)
    b.net(tp, '1', 'P_' + sig)

# DISP control: 10k pull-up to 3V3 (DISP default ON) + optional 0R hard tie
r_disp = b.r('R%d' % (n_j + 1), '10k', 400.05, 355.6, 'DISP pull-up (default ON)')
b.net(r_disp, '1', '+3V3'); b.net(r_disp, '2', 'DISP_CTRL')
r_disp2 = b.r('R%d' % (n_j + 2), '0R', 431.8, 355.6, 'DISP hard-tie option (DNP if pull-up enough)')
b.net(r_disp2, '1', 'DISP_CTRL'); b.net(r_disp2, '2', '+3V3')
# DISP pad for external drive (bench)
tp_disp = b.part('Connector', 'TestPoint', 'TP%d' % (n_j + 1), 'TP', 463.55, 355.6, FP['TP'],
                 'TP DISP_CTRL (внешний сигнал со стенда)')
b.net(tp_disp, '1', 'DISP_CTRL')

# --------------------------------------------------------------------------
# J3 — external backlight boost input (18..22 V), alternative to PANEL-2 BL lines
# --------------------------------------------------------------------------
j3 = b.part('Connector_Generic', 'Conn_01x02', 'J3', 'JST2', 431.8, 419.1, FP['JST2'],
            'Внешний boost подсветки 18…22 В / 40 мА (если не используется BL-линия CORE-2)')
b.net(j3, 1, 'BL_EXT_A'); b.net(j3, 2, 'BL_EXT_K')
r_ext_a = b.r('R%d' % (n_j + 3), '0R', 431.8, 444.5, 'внешний boost: +18…22 В -> LED_A (DNP если BL с CORE-2)')
b.net(r_ext_a, '1', 'BL_EXT_A'); b.net(r_ext_a, '2', 'P_LED_A')
r_ext_k = b.r('R%d' % (n_j + 4), '0R', 463.55, 444.5, 'внешний boost: возврат -> LED_K')
b.net(r_ext_k, '1', 'BL_EXT_K'); b.net(r_ext_k, '2', 'P_LED_K')

# --------------------------------------------------------------------------
# +3V3 decoupling for the panel
# --------------------------------------------------------------------------
c_in = b.c('C1', '10u', 355.6, 419.1, '3V3 панель: bulk')
b.net(c_in, '1', '+3V3'); b.net(c_in, '2', 'GND')
for i, ref in enumerate(('C2', 'C3')):
    c = b.c(ref, '100n', 381.0 + i * 25.4, 419.1, '3V3 панель: bypass')
    b.net(c, '1', '+3V3'); b.net(c, '2', 'GND')

# --------------------------------------------------------------------------
# test pads on power rails / BL_PWM (J12 side) for the bench
# --------------------------------------------------------------------------
extra_tp = [('BL_PWM', 'TP_BL_PWM (вход драйвера подсветки CORE-2)'),
            ('+3V3', 'TP +3V3'), ('GND', 'TP GND')]
for i, (netname, note) in enumerate(extra_tp):
    tp = b.part('Connector', 'TestPoint', 'TP%d' % (n_j + 2 + i), 'TP',
                76.2 + i * 38.1, 419.1, FP['TP'], note)
    b.net(tp, '1', netname)

# --------------------------------------------------------------------------
# mounting holes for the panel (TFT-H050A1SVIST4R40 outline 120.7 x 75.8)
# --------------------------------------------------------------------------
for i in range(4):
    b.part('Mechanical', 'MountingHole', 'H%d' % (i + 1), 'M3',
           30.48 + (i % 2) * 88.9, 63.5 + (i // 2) * 38.1, FP['HOLE'],
           'M3: крепление панели/стоек, плата 120 x 76')

# power ports for the only global rails
s.power_anchor('+3V3', 25.4, 457.2)
s.power_anchor('GND', 63.5, 457.2)

PATH = b.done()
print('written', PATH)


# --------------------------------------------------------------------------
# BOM
# --------------------------------------------------------------------------
def write_bom():
    groups = {}
    for part in b.bom:
        groups.setdefault((part['value'], part['fp'], part['mpn']), []).append(part['ref'])
    p = os.path.join(AD, 'BOM-lcd-adapter.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['Номинал', 'Позиционное обозначение', 'Корпус / footprint',
                    'Артикул (черновой)', 'Кол-во', 'Примечание', 'DNP'])
        total = 0
        notes = {'0R': 'перемычки пин-аута (DNP/замена = переназначение линии)',
                 '10k': 'подтяжка DISP (DISP по умолчанию ON)',
                 '100n': 'bypass 3V3 панели', '10u': 'bulk 3V3 панели',
                 'FFC40_ZIF': 'ZIF FFC-40 0.5 мм (Hirose FH12-40S-0.5SH)',
                 'JST2': 'вход внешнего boost подсветки 18…22 В',
                 'TP': 'тестпоинт', 'M3': 'крепление панели M3'}
        for (value, fp, mpn), refs in sorted(groups.items()):
            total += len(refs)
            w.writerow([value, ' '.join(sorted(refs)), fp, mpn, len(refs), notes.get(value, ''), ''])
        w.writerow(['ИТОГО', '', '', '', total, '%d уникальных позиций' % len(groups), ''])
    return p


# --------------------------------------------------------------------------
# docs/49-lcd-adapter.md
# --------------------------------------------------------------------------
def write_doc49():
    L = []
    A = L.append
    A('# 49. LCD FFC-40 адаптер (HotLCD ST7262) — стендовая проверка экрана')
    A('')
    A('**Статус:** DRAFT · **Дата:** 2026-11-06 · **Схема:** '
      '[`hardware/panel2/adapter-lcd/`](../hardware/panel2/adapter-lcd/README.md) · '
      '**Связано:** O-15 (LCD_DISP), D-72 (RGB565 FPC-40), '
      '[`docs/47`](47-display-selection.md), [`docs/29`](29-p1-order.md) (13a/13b).')
    A('')
    A('## 1. Зачем адаптер')
    A('')
    A('Экран 5.0″ 800×480 RGB565 (FPC-40, ST7262) нужно проверить **на P1-стенде до PCB**:')
    A('')
    A('* PANEL-2 J12 — ZIF FFC-40; панель — свой FFC-40 хвост, пин-аут **не подтверждён** (O-15). '
      'Плата PANEL-2 пока pre-freeze, её нельзя заказать для проверки.')
    A('* Адаптер даёт: вход FFC-40 (как J12), **тестпоинты на все линии**, 0R‑«перемычки» '
      'между функцией и каждым пином панели — реальный пин-аут можно набрать после промера '
      'образца **без перевыпуска платы**.')
    A('* Резерв панели (Newhaven NHD-5.0-800480AF-ASXP, 40-pin) проверяется тем же адаптером.')
    A('')
    A('## 2. Подключение')
    A('')
    A('```')
    A('  PANEL-2 J12 (ZIF FFC-40) ──FFC-40 0.5 мм, ≤100 мм──┐')
    A('                                                      ├─ J1  LCD-ADAPTER  J2 ──FFC-40── панель (хвост)')
    A('  внешний boost 18…22 В / 40 мА ──JST PH 2-pin── J3 ──┘')
    A('```')
    A('')
    A('1. FFC-40 от PANEL-2 J12 → **J1** адаптера (одинаковый pinout, шлейф same/opposite side — '
      'проверить контактные площадки: см. §5).')
    A('2. Хвост панели → **J2**. Панель крепится к адаптеру 4 × M3 (планка/стойки) — '
      'перевёрнутая панель = зеркальный pinout, проверить шелкографию pin 1.')
    A('3. Подсветка: по умолчанию LED‑линейка питается от BL_ANODE/BL_CATHODE CORE-2 через J12 '
      '(R30/R31). Если проверяем на стенде без CORE-2 — снять R30/R31 и подать 18…22 В / 40 мА '
      'на **J3** (JST PH), R34/R35 при этом запаяны.')
    A('4. DISP: на адаптере подтянут к +3V3 (10k R32 — см. схему) → панель включена; '
      'для стенда можно подать внешний DISP на TP.')
    A('')
    A('## 3. Pinout: J12 PANEL-2 ↔ J1 ↔ J2 ↔ HotLCD (предложение!)')
    A('')
    A('> ⚠️ Пин-аут HotLCD `TFT-H050A1SVIST4R40` (ST7262) ниже — **рабочее предположение** '
      'для типового 40-pin RGB 8-bit модуля. Перед подачей питания: сверить с даташитом и '
      'прозвонить образец мультиметром (GND/VDD определяются однозначно, дальше — по '
      'даташиту). При расхождении перепаять 0R‑перемычки — плата рассчитана на это.')
    A('')
    A('| J2 pin | панель (предложение) | через 0R к | J12 pin | J12 сигнал PANEL-2 |')
    A('|---:|---|---|---:|---|')
    j12_inv = {}
    for pin, sig in J12.items():
        j12_inv.setdefault(sig, pin)
    for p, sig in PANEL_PINOUT.items():
        if sig == 'GND':
            A('| %s | GND | GND (напрямую) | — | GND |' % p)
            continue
        if sig == '3V3':
            A('| %s | 3V3 | +3V3 (напрямую) | 27, 28 | LCD_3V3 |' % p)
            continue
        if sig in ('LED_A', 'LED_K'):
            src = 'BL_ANODE' if sig == 'LED_A' else 'BL_CATHODE'
            A('| %s | %s | P_%s ↔ J12.%s (или J3) | %s | %s |'
              % (p, sig, sig, j12_inv[src], j12_inv[src], src))
            continue
        if sig == 'DISP':
            A('| %s | DISP | DISP_CTRL (10k→3V3 + TP) | — | O-15 |' % p)
            continue
        src = {'HS': 'HSYNC', 'VS': 'VSYNC'}.get(sig, sig)
        if sig[0] in 'RGB' and sig[1].isdigit():
            base = {'R': 3, 'G': 2, 'B': 3}[sig[0]]
            bit = int(sig[1])
            if bit < base:
                A('| %s | %s | GND (0R) | — | младший бит |' % (p, sig))
                continue
            src = '%s%d' % (sig[0], bit - base)
        A('| %s | %s | P_%s ↔ J12.%s | %s | %s |'
          % (p, sig, sig, j12_inv.get(src, '—'), j12_inv.get(src, '—'), src))
    A('')
    A('Полная таблица «J12 pin → J1 pin → 0R → J2 pin → панель» генерируется в '
      '`hardware/panel2/adapter-lcd/README.md` (§3) и `pinout-adapter.csv`; при любом '
      'изменении пин-аута — перегенерировать (`tools/gen_lcd_adapter.py`).')
    A('')
    A('### 3.1 RGB565 на 24-битной панели (8 бит/канал)')
    A('')
    A('PANEL-2 отдаёт 16 бит: **R0-R4 / G0-G5 / B0-B4**. Панель ждёт R0…R7, G0…G7, B0…B7:')
    A('')
    A('| Панель | Подключение |')
    A('|---|---|')
    A('| R3…R7 | J12 R0…R4 |')
    A('| R0…R2 | GND (через 0R) |')
    A('| G2…G7 | J12 G0…G5 |')
    A('| G0…G1 | GND (через 0R) |')
    A('| B3…B7 | J12 B0…B4 |')
    A('| B0…B2 | GND (через 0R) |')
    A('')
    A('Итого 7 линий младших бит на GND — это штатная схема RGB565→24-bit; при переходе на '
      '18/24 бит их можно перекинуть на J12-линии (R5-R7 и т.д. на PANEL-2 нет — только через '
      'будущую ревизию).')
    A('')
    A('## 4. Что проверить мультиметром (по образцу, до подачи питания)')
    A('')
    A('| # | Проверка | Как | Ожидание |')
    A('|---:|---|---|---|')
    A('| 1 | GND панели | прозвонка J2 pin 3/5/30/36/39/40 ↔ корпус/экран | 0 Ω |')
    A('| 2 | VDD 3.3 В | J2 pin 4/37/38 ↔ 3V3 | 0 Ω; КЗ на GND нет (проверить!) |')
    A('| 3 | LED_A / LED_K | прозвонка LED-цепи: прямое падение ~2.7–3.2 В на диод | 4–6 последовательных |')
    A('| 4 | R0…R7, G0…G7, B0…B7 | соответствие пинов даташиту | по документу |')
    A('| 5 | PCLK/DE/HS/VS | наличие/полярность: осциллограф на TP | DE-only или sync |')
    A('| 6 | DISP | подать 3.3 В на DISP → панель включается | потребление ↑ |')
    A('| 7 | Контакты FFC | same/opposite side, pin 1 | см. §5 |')
    A('')
    A('> **Нельзя проверить без панели:** фактический pinout (O-15), DE-only vs HS/VS, '
      'полярность синхро, timeing (PCLK ~33 МГц, porches), ток подсветки (12 WLED, 18–21 В) '
      'и контактную сторону FFC конкретной партии.')
    A('')
    A('## 5. Правила FFC (обязательно)')
    A('')
    A('* **Тип контактов:** ZIF 0.5 мм, 40 pin. Шлейф бывает **same side** (контакты с одной '
      'стороны) и **opposite side**; у панели контактная сторона задана даташитом. Если '
      'сторона не та — перевернуть шлейф нельзя (pin 1 окажется не там), нужен шлейф другого '
      'типа. Заказать оба варианта (docs/29 поз. 13b).')
    A('* **Pin 1** — красная метка на шлейфе, маркер `1` на шелкографии J1/J2; направление '
      'от разъёма. Проверять до включения.')
    A('* **Длина:** ≤100 мм (на стенде допустимо 150 мм), изгиб не ближе 10 мм к разъёму, '
      'не пережимать/не складывать — PCLK ~33 МГц, длинные шлейфы дают EMI и «дрожание».')
    A('* **Вставка:** ZIF открыть, шлейф до упора, контакты к контактам, закрыть защёлку; '
      'вынимать только с открытой защёлкой.')
    A('* **ESD:** панель 8 кВ; работать на антистатическом коврике, касаться GND перед '
      'подключением.')
    A('')
    A('## 6. Питание подсветки')
    A('')
    A('| Параметр | Значение | Источник |')
    A('|---|---|---|')
    A('| LED-линейка | 12 WLED, ≈18…21 В, ≈40 мА | панель (даташит) |')
    A('| Штатно | `BL_ANODE`/`BL_CATHODE` из CORE-2 (boost MT3608 на CORE-2, `BL_20V`) | J12.31/32 |')
    A('| Стенд | внешний boost 18…22 В / 40 мА (CC) → **J3** JST PH | R34/R35, снять R30/R31 |')
    A('| ШИМ | `BL_PWM` 3.3 В от CORE-2 → драйвер (на CORE-2) | J12.30, TP |')
    A('')
    A('**Не подавать 18–22 В на J12!** Высокое напряжение идёт только через J3 (R34/R35), '
      'линии J12 — 3.3 В. Проверить, что R30/R31 сняты, до подачи внешнего boost.')
    A('')
    A('## 7. Статус и что заказать')
    A('')
    A('* Схема: [`LCD-ADAPTER.kicad_sch`](../hardware/panel2/adapter-lcd/LCD-ADAPTER.kicad_sch), '
      'ERC 0 errors; PDF/SVG/netlist рядом. Плата 2 слоя ~120×76, крепление панели 4×M3.')
    A('* **Заказать:** 2 платы адаптера (JLCPCB/Rezon) + ZIF FFC-40 Hirose FH12-40S-0.5SH ×4 '
      '(2 на адаптер, запас), шлейфы FFC-40 0.5 мм 100 мм ×4 (same + opposite side), '
      'JST PH 2-pin ×2, панель TFT-H050A1SVIST4R40 ×2 (docs/29 поз. 13a).')
    A('* **O-15** (LCD_DISP) — «адаптер ждёт образец»: DISP на адаптере подтянут к 3V3, '
      'внешний сигнал — на TP; решение о пине J12 для DISP принимается после проверки панели.')
    A('')
    with open(os.path.join(ROOT, 'docs', '49-lcd-adapter.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    return os.path.join(ROOT, 'docs', '49-lcd-adapter.md')


# --------------------------------------------------------------------------
# README (adapter dir) + adapter pinout CSV
# --------------------------------------------------------------------------
def write_readme():
    L = []
    A = L.append
    A('# LCD FFC-40 адаптер (HotLCD ST7262) — PRE-FREEZE bench adapter')
    A('')
    A('**Не заказывать плату без ревью.** Назначение — проверить 5.0″ 800×480 RGB565 FFC-40 '
      'панель (MPN **TFT-H050A1SVIST4R40**, ST7262) на P1-стенде до PCB: повторяет pinout '
      'PANEL-2 **J12** (FFC-40, 23 сигнала) и даёт тестпоинты на все линии панели. '
      'Полная документация — [`docs/49-lcd-adapter.md`](../../../docs/49-lcd-adapter.md).')
    A('')
    A('## 1. Файлы')
    A('')
    A('| Файл | Что |')
    A('|---|---|')
    A('| `LCD-ADAPTER.kicad_sch` | схема (KiCad 10, A1, штамп PRE-FREEZE) |')
    A('| `LCD-ADAPTER.pdf`, `svg/` | экспорт схемы |')
    A('| `LCD-ADAPTER.net` | netlist |')
    A('| `erc/LCD-ADAPTER-erc.rpt` | ERC-отчёт (0 errors) |')
    A('| `BOM-lcd-adapter.csv` | BOM (черновой) |')
    A('| `pinout-adapter.csv` | таблица J12 pin ↔ J1 ↔ 0R ↔ J2 pin ↔ панель |')
    A('| `tools/gen_lcd_adapter.py` | генератор схемы/BOM/доков |')
    A('')
    A('## 2. Схема в двух словах')
    A('')
    A('* **J1** — вход FFC-40 (ZIF 0.5 мм), pinout = PANEL-2 J12 (rev.2, 23 сигнала: 16 RGB, '
      'PCLK/DE/HSYNC/VSYNC, BL_PWM, BL_ANODE/BL_CATHODE, LCD_3V3, GND).')
    A('* **J2** — выход FFC-40 на хвост панели (пин-аут — предположение, 0R-перемычки '
      'позволяют переназначить любую линию).')
    A('* **0R-перемычки (R1…R31)** — «pinout jumper»: P_<сигнал> ↔ J12-линия / GND / DISP_CTRL. '
      'Позволяют собрать правильный пин-аут после промера образца.')
    A('* **Тестпоинты** — 31 сигнал панели (R0-R7, G0-G7, B0-B7, PCLK, DE, HS, VS, DISP, '
      'LED_A, LED_K) + BL_PWM, +3V3, GND.')
    A('* **J3** (JST PH 2-pin) — вход внешнего boost подсветки 18…22 В / 40 мА (R34/R35); '
      'штатно подсветка идёт с CORE-2 через J12 (R30/R31).')
    A('* Габарит 120 × 76 мм, 2 слоя, крепление панели 4 × M3 (outline панели 120.7 × 75.8).')
    A('')
    A('## 3. Pinout (генерируется из той же таблицы, что схема)')
    A('')
    A('| J2 pin | панель (предложение) | через 0R к | J12 pin |')
    A('|---:|---|---|---:|')
    j12_inv = {}
    for pin, sig in J12.items():
        j12_inv.setdefault(sig, pin)
    for p, sig in PANEL_PINOUT.items():
        if sig == 'GND':
            continue
        if sig == '3V3':
            A('| %s | 3V3 | +3V3 | %s, %s |' % (p, j12_inv['LCD_3V3'], j12_inv['LCD_3V3']))
            continue
        if sig in ('LED_A', 'LED_K'):
            A('| %s | %s | P_%s ↔ J12.%s / J3 | %s |'
              % (p, sig, sig, j12_inv['BL_ANODE'] if sig == 'LED_A' else j12_inv['BL_CATHODE'],
                 j12_inv['BL_ANODE'] if sig == 'LED_A' else j12_inv['BL_CATHODE']))
            continue
        if sig == 'DISP':
            A('| %s | DISP | DISP_CTRL (10k→3V3, TP) | — |' % p)
            continue
        src = {'HS': 'HSYNC', 'VS': 'VSYNC'}.get(sig, sig)
        if sig[0] in 'RGB' and sig[1].isdigit():
            base = {'R': 3, 'G': 2, 'B': 3}[sig[0]]
            bit = int(sig[1])
            if bit < base:
                A('| %s | %s | GND (0R) | — |' % (p, sig))
                continue
            src = '%s%d' % (sig[0], bit - base)
        A('| %s | %s | P_%s ↔ J12.%s | %s |' % (p, sig, sig, j12_inv.get(src, '—'),
                                                j12_inv.get(src, '—')))
    A('')
    A('## 4. Что проверить до питания')
    A('')
    A('1. Прозвонить GND (J2 3/5/30/36/39/40) и 3V3 (4/37/38) — КЗ нет.')
    A('2. Сверить пин-аут панели с даташитом (O-15): при расхождении перепаять 0R.')
    A('3. Проверить контактную сторону FFC (same/opposite) и pin 1.')
    A('4. Подсветка: не подавать 18…22 В на J12 — только J3 (R34/R35).')
    A('')
    A('## 5. Открытые вопросы')
    A('')
    A('* **O-15** — LCD_DISP: на PANEL-2 J12 DISP нет; на адаптере DISP подтянут к 3V3 '
      '(можно подать внешний на TP). Решение о пине J12 — после проверки образца.')
    A('* Пин-аут HotLCD — предположение, подтверждается мультиметром/даташитом образца.')
    A('* PCB (2 слоя, 120×76) не разводился: сначала заказ/проверка образцов (docs/42 §144).')
    A('')
    with open(os.path.join(AD, 'README.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    # pinout csv
    with open(os.path.join(AD, 'pinout-adapter.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['j2_pin', 'panel_proposed', 'jumper_net', 'source', 'j12_pin', 'note'])
        j12_inv = {}
        for pin, sig in J12.items():
            j12_inv.setdefault(sig, pin)
        for p, sig in PANEL_PINOUT.items():
            if sig == 'GND':
                w.writerow([p, 'GND', 'GND', 'GND', '', 'панель GND'])
                continue
            if sig == '3V3':
                w.writerow([p, '3V3', '+3V3', '+3V3', j12_inv['LCD_3V3'], 'панель VDD'])
                continue
            if sig in ('LED_A', 'LED_K'):
                src = 'BL_ANODE' if sig == 'LED_A' else 'BL_CATHODE'
                w.writerow([p, sig, 'P_' + sig, 'J12.%s или J3 (внешний boost)' % j12_inv[src],
                            j12_inv[src], 'линейка WLED 18…22 В / 40 мА'])
                continue
            if sig == 'DISP':
                w.writerow([p, 'DISP', 'DISP_CTRL', '10k→+3V3 / внешний TP', '', 'O-15, ждёт образец'])
                continue
            src = {'HS': 'HSYNC', 'VS': 'VSYNC'}.get(sig, sig)
            if sig[0] in 'RGB' and sig[1].isdigit():
                base = {'R': 3, 'G': 2, 'B': 3}[sig[0]]
                bit = int(sig[1])
                if bit < base:
                    w.writerow([p, sig, 'P_' + sig, 'GND (0R)', '', 'младший бит RGB565→24'])
                    continue
                src = '%s%d' % (sig[0], bit - base)
            w.writerow([p, sig, 'P_' + sig, 'J12.' + j12_inv.get(src, '?'), j12_inv.get(src, ''),
                        ''])
    return os.path.join(AD, 'README.md')


print('bom  :', write_bom())
print('doc49:', write_doc49())
print('readme:', write_readme())
print('components: %d' % len(b.bom))
