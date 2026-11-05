#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CORE-2 schematic generator (PRE-FREEZE / DO NOT FABRICATE).

KiCad 10 native S-expression .kicad_sch, generated from tools/board_def.py.
KiCad 10 `sch upgrade` cannot import legacy v5, so the file is written directly.
The MCU slot J-MCU (2x32) is a *logical* pre-freeze contract for an ESP32-P4
module/adapter; see pinmap.md / interfaces.md.

Usage: python3 gen_core2_sch.py [--no-export]
Output: CORE-2.kicad_sch, CORE-2.pdf/svg, erc/erc.rpt(+json), netlist.net/xml,
        BOM-core2.csv
"""
import os, sys, math, json, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import kicad_sch as k
import board_def as B

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
PROJECT = 'CORE-2'
PAPER = 'A0'
SW, SH = 63.5, 30.48
LABEL_PAD = 2.54 + 13.0

def f(v):
    v = round(float(v), 3); return '%g' % v

# --------------------------------------------------------------------------
# custom symbols
# --------------------------------------------------------------------------
def _pin(num, name, x, y, a, ln=2.54, etype='passive'):
    return ('\t\t(pin %s line (at %s %s %s) (length %s)\n'
            '\t\t\t(name "%s" (effects (font (size 1.27 1.27))))\n'
            '\t\t\t(number "%s" (effects (font (size 1.27 1.27))))\n'
            '\t\t)' % (etype, f(x), f(y), int(a), f(ln), name, num))

def custom_symbol(name, refpfx, desc, rect, pins, hide_num=False):
    x1, y1, x2, y2 = rect
    bt, bb = max(y1, y2), min(y1, y2)
    out = ['\t(symbol "%s"' % name,
           '\t\t(pin_names (offset 1.016))']
    if hide_num: out.append('\t\t(pin_numbers (hide yes))')
    out += ['\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)',
            '\t\t(property "Reference" "%s" (at %s %s 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)' % (refpfx, f(0), f(bt + 2.54)),
            '\t\t(property "Value" "%s" (at %s %s 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)' % (name, f(0), f(bb - 2.54)),
            '\t\t(property "Footprint" "" (at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)',
            '\t\t(property "Datasheet" "~" (at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)',
            '\t\t(property "Description" "%s" (at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)' % desc,
            '\t\t(symbol "%s_0_1"' % name,
            '\t\t\t(rectangle (start %s %s) (end %s %s)\n\t\t\t\t(stroke (width 0.254) (type default))\n\t\t\t\t(fill (type background))\n\t\t\t)' % (f(x1), f(bb), f(x2), f(bt)),
            '\t\t)',
            '\t\t(symbol "%s_1_1"' % name]
    out += [_pin(*p) for p in pins]
    out += ['\t\t)', '\t)']
    return '\n'.join(out)

def mcu_symbol():
    """2x32 module slot; pin numbers 1..64, names from board_def PINMAP."""
    def disp(r):
        sig, gpio = r[0], r[1]
        if sig == 'GND' or sig.startswith('GND'):
            return 'GND'
        if sig == '3V3_MCU': return '3V3'
        if sig == 'CHIP_PU': return 'EN'
        if sig == 'USB_HS_DP': return 'USB_DP'
        if sig == 'USB_HS_DM': return 'USB_DM'
        if sig == 'USB_JTAG_DP': return 'IO24'
        if sig == 'USB_JTAG_DM': return 'IO25'
        if sig == 'USB_FS_DP': return 'IO26'
        if sig == 'USB_FS_DM': return 'IO27'
        if sig == 'STRAP36': return 'IO36'
        if sig == 'FREE_IO54': return 'IO54'
        if sig == 'BOOT': return 'IO35'
        if sig == 'LED_GPIO': return 'IO48'
        if gpio is None: return sig
        return 'IO%d' % gpio
    rows = {r[7]: r for r in B.PINMAP}
    pins = []
    top = 40.0
    for n in range(1, 33):
        r = rows[n]
        pins.append((str(n), disp(r), -27.94, top - (n - 1) * 2.54, 0, 2.54, 'passive'))
    for n in range(33, 65):
        r = rows[n]
        pins.append((str(n), disp(r), 27.94, top - (n - 33) * 2.54, 180, 2.54, 'passive'))
    return custom_symbol('ESP32-P4_MOD', 'U', B.SLOT,
                         (-24.13, -46.99, 24.13, 43.18), pins)

def build_custom_lib():
    lib = {}
    lib['ESP32-P4_MOD'] = mcu_symbol()
    lib['MP1584_MOD'] = custom_symbol(
        'MP1584_MOD', 'U', 'MP1584 3A DC-DC buck module (4-pad breakout)',
        (-7.62, -7.62, 7.62, 7.62),
        [('1', 'IN+', -10.16, 2.54, 0), ('2', 'IN-', -10.16, -2.54, 0),
         ('3', 'OUT+', 10.16, 2.54, 180), ('4', 'OUT-', 10.16, -2.54, 180)])
    lib['PCM1808'] = custom_symbol(
        'PCM1808', 'U', 'PCM1808 24-bit 96 kHz stereo I2S ADC (TSSOP-14)',
        (-12.7, -16.51, 12.7, 16.51),
        [('1', 'VREF', 15.24, 12.7, 180), ('2', 'AGND', 15.24, 10.16, 180),
         ('3', 'VCC', 15.24, 7.62, 180), ('4', 'VDD', 15.24, 5.08, 180),
         ('5', 'DGND', 15.24, -15.24, 180), ('14', 'VINR', 15.24, 2.54, 180),
         ('13', 'VINL', 15.24, 0, 180), ('12', 'FMT', -15.24, -12.7, 0),
         ('11', 'MD1', -15.24, -10.16, 0), ('10', 'MD0', -15.24, -7.62, 0),
         ('9', 'DOUT', -15.24, 10.16, 0), ('8', 'BCK', -15.24, 7.62, 0),
         ('7', 'LRCK', -15.24, 5.08, 0), ('6', 'SCKI', -15.24, 0, 0)])
    lib['74HCT1G125'] = custom_symbol(
        '74HCT1G125', 'U', 'Single 3-state buffer, TTL input (level shifter 3.3->5 V)',
        (-5.08, -6.35, 5.08, 6.35),
        [('1', '~OE', -7.62, 2.54, 0, 2.54, 'input'),
         ('2', 'A', -7.62, 0, 0, 2.54, 'input'),
         ('3', 'GND', 0, -8.89, 90, 2.54, 'power_in'),
         ('4', 'Y', 7.62, 0, 180, 2.54, 'tri_state'),
         ('5', 'VCC', 0, 8.89, 270, 2.54, 'power_in')])
    lib['74HCT125'] = custom_symbol(
        '74HCT125', 'U', 'Quad 3-state buffer, TTL input (MIDI OUT)',
        (-10.16, -12.7, 10.16, 12.7),
        [('1', '1OE', -12.7, 10.16, 0, 2.54, 'input'), ('2', '1A', -12.7, 7.62, 0, 2.54, 'input'),
         ('3', '1Y', 12.7, 7.62, 180, 2.54, 'tri_state'), ('4', '2OE', -12.7, 5.08, 0, 2.54, 'input'),
         ('5', '2A', -12.7, 2.54, 0, 2.54, 'input'), ('6', '2Y', 12.7, 2.54, 180, 2.54, 'tri_state'),
         ('7', 'GND', 0, -15.24, 90, 2.54, 'power_in'),
         ('8', '3Y', 12.7, -2.54, 180, 2.54, 'tri_state'), ('9', '3A', -12.7, -2.54, 0, 2.54, 'input'),
         ('10', '3OE', -12.7, 0, 0, 2.54, 'input'), ('11', '4Y', 12.7, -7.62, 180, 2.54, 'tri_state'),
         ('12', '4A', -12.7, -5.08, 0, 2.54, 'input'), ('13', '4OE', -12.7, -7.62, 0, 2.54, 'input'),
         ('14', 'VCC', 0, 15.24, 270, 2.54, 'power_in')])
    lib['TP'] = custom_symbol('TP', 'TP', 'Test point', (-2.54, -2.54, 2.54, 2.54),
                              [('1', '1', -5.08, 0, 0, 2.54)])
    for nm, txt in lib.items():
        k.CUSTOM[('picomod', nm)] = txt.replace('(symbol "%s"' % nm, '(symbol "picomod:%s"' % nm, 1)
    return lib

# --------------------------------------------------------------------------
# footprints (draft, not for fabrication)
# --------------------------------------------------------------------------
FP = {
 'R': 'Resistor_SMD:R_0805_2012Metric', 'C': 'Capacitor_SMD:C_0805_2012Metric',
 'CP': 'Capacitor_SMD:CP_Elec_6.3x7.7', 'C10': 'Capacitor_SMD:CP_Elec_5x5.4',
 'L': 'Inductor_SMD:L_1210_3225Metric', 'FB': 'Inductor_SMD:L_0805_2012Metric',
 'FUSE': 'Fuse:Fuse_1206_3216Metric', 'PF': 'Fuse:Fuse_1206_3216Metric',
 'DIODE': 'Diode_SMD:D_SMA', 'BAT54S': 'Package_TO_SOT_SMD:SOT-23',
 'TO92': 'Package_TO_SOT_THT:TO-92_Inline', 'SOT23': 'Package_TO_SOT_SMD:SOT-23',
 'SOT353': 'Package_TO_SOT_SMD:SOT-353_SC-70-5',
 'DIP8': 'Package_DIP:DIP-8_W7.62mm', 'DIP14': 'Package_DIP:DIP-14_W7.62mm',
 'SOIC8': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
 'MSOP10': 'Package_SO:MSOP-10_3x3mm_P0.5mm', 'TSSOP14': 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
 'TSSOP20': 'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',
 'SOT235': 'Package_TO_SOT_SMD:SOT-23-5', 'SOT236': 'Package_TO_SOT_SMD:SOT-23-6',
 'QFN16': 'Package_DFN_QFN:QFN-16-1EP_4x4mm_P0.65mm_EP2.1x2.1mm',
 'SOD123': 'Diode_SMD:D_SOD-123', 'USBC': 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
 'SD': 'Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5', 'MCU': '',
 'IDC26': 'Connector_IDC:IDC-Header_2x13_P2.54mm_Latch12.0mm_Vertical',
 'IDC16': 'Connector_IDC:IDC-Header_2x08_P2.54mm_Latch6.5mm_Vertical',
 'FFC40': 'Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal',
 'TB12': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1-12-3.81_1x12_P3.81mm_Horizontal',
 'TB4': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1-4-3.81_1x04_P3.81mm_Horizontal',
 'TB6': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1-6-3.81_1x06_P3.81mm_Horizontal',
 'HDR4': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
 'HDR3': 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
 'BATT': 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical',
 'JACK': '', 'BARREL': '', 'BTN': '',
}

C = []
def add(ref, lib, val, nets, fp='', note='', sec='', unit=1, on_board=True):
    C.append(dict(ref=ref, lib=lib, val=val, nets=nets, fp=fp, note=note,
                  sec=sec, section=sec, unit=unit, on_board=on_board))
