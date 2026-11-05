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
    lib['ESP32-C6-MINI-1'] = custom_symbol(
        'ESP32-C6-MINI-1', 'U', 'ESP32-C6-MINI-1 Wi-Fi 6 / BLE 5.3 coprocessor (esp-hosted SPI). '
        'PCB antenna: keep-out >=15 mm from metal/battery/walls. DNP for ESP32-S3 build.',
        (-10.16, -10.16, 10.16, 10.16),
        [('1', '3V3', 0, 12.7, 270, 2.54, 'power_in'),
         ('2', 'GND', -5.08, -12.7, 90, 2.54, 'power_in'),
         ('3', 'EN', -12.7, 5.08, 0, 2.54, 'input'),
         ('4', 'SPI_SCK', -12.7, 2.54, 0, 2.54, 'input'),
         ('5', 'SPI_MOSI', -12.7, 0, 0, 2.54, 'input'),
         ('6', 'SPI_MISO', -12.7, -2.54, 0, 2.54, 'output'),
         ('7', 'SPI_CS', -12.7, -5.08, 0, 2.54, 'input'),
         ('8', 'HANDSHAKE', 12.7, 2.54, 180, 2.54, 'bidirectional'),
         ('9', 'DATA_READY', 12.7, 0, 180, 2.54, 'bidirectional'),
         ('10', 'GND', 5.08, -12.7, 90, 2.54, 'power_in')])
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
 'SOIC14': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
 'DIP8': 'Package_DIP:DIP-8_W7.62mm', 'DIP14': 'Package_DIP:DIP-14_W7.62mm',
 'DIP16': 'Package_DIP:DIP-16_W7.62mm',
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

# ==========================================================================
# CORE-2 component table.  PRE-FREEZE / DO NOT FABRICATE.
# ==========================================================================
P, D, A, V, M, R, N = 'POWER', 'MCU', 'AUDIO', 'CV', 'MIDI', 'BUS', 'PANEL'

# ---------------------------- POWER ---------------------------------------
add('J1', ('Connector','USB_C_Receptacle_USB2.0_16P'), 'USB-C 16P (data+charge)',
    {'A1':'DGND','A4':'VBUS_CHG','A5':'CC1','A6':'USB_DP_C','A7':'USB_DM_C','A8':'NC',
     'A9':'VBUS_CHG','A12':'DGND','B1':'DGND','B4':'VBUS_CHG','B5':'CC2','B6':'USB_DP_C',
     'B7':'USB_DM_C','B8':'NC','B9':'VBUS_CHG','B12':'DGND','SH':'DGND'},
    FP['USBC'], 'USB 2.0 HS composite: HID+MIDI+UAC2+CDC (TinyUSB); rear wall', P)
add('U20', ('Power_Protection','USBLC6-2SC6'), 'USBLC6-2SC6',
    {'1':'USB_DP_C','2':'DGND','3':'USB_DM_C','4':'USB_HS_DM','5':'VBUS_CHG','6':'USB_HS_DP'},
    FP['SOT236'], 'ESD/клэмп USB HS пары', P)
add('R28', ('Device','R'), '5.1k', {'1':'CC1','2':'DGND'}, FP['R'], 'UFP CC1', P)
add('R29', ('Device','R'), '5.1k', {'1':'CC2','2':'DGND'}, FP['R'], 'UFP CC2', P)
add('D1', ('Diode','SMAJ5.0A'), 'SMAJ5.0A', {'1':'VBUS_CHG','2':'PGND'}, FP['DIODE'], 'TVS по VBUS', P)
add('F1', ('Device','Polyfuse'), '1.5A', {'1':'VBUS_CHG','2':'VBUS_F'}, FP['PF'], 'polyfuse USB', P)
add('C1', ('Device','C'), '10uF/10V', {'1':'VBUS_F','2':'PGND'}, FP['C'], '', P)
add('C2', ('Device','C'), '100nF/16V', {'1':'VBUS_F','2':'PGND'}, FP['C'], '', P)
add('U22', ('Battery_Management','BQ24074RGT'), 'BQ24074RGT',
    {'1':'TS','2':'BATT_P','3':'BATT_P','4':'PGND','5':'VBUS_CHG','6':'VBUS_CHG',
     '7':'NC','8':'PGND','9':'CHG','10':'VSYS','11':'VSYS','12':'ILIM','13':'VBUS_F',
     '14':'TMR','15':'ITERM','16':'ISET','17':'PGND'},
    'Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm', 'charger + power-path (1.5 A)', P)
add('R1', ('Device','R'), '1.5k', {'1':'ILIM','2':'PGND'}, FP['R'], 'ILIM 1.5 A', P)
add('R2', ('Device','R'), '1.5k', {'1':'ISET','2':'PGND'}, FP['R'], 'charge current ~1 A', P)
add('R3', ('Device','R'), '2k', {'1':'ITERM','2':'PGND'}, FP['R'], 'termination', P)
add('R4', ('Device','R'), '100k', {'1':'TMR','2':'PGND'}, FP['R'], 'safety timer', P)
add('R5', ('Device','R'), '10k', {'1':'VBUS_F','2':'TS'}, FP['R'], 'TS network', P)
add('TH1', ('Device','Thermistor_NTC'), 'NTC 10k', {'1':'TS','2':'PGND'}, FP['R'], 'battery NTC', P)
add('C3', ('Device','C'), '100nF', {'1':'TS','2':'PGND'}, FP['C'], '', P)
add('R6', ('Device','R'), '1k', {'1':'VBUS_CHG','2':'CHG_LED'}, FP['R'], '', P)
add('D3', ('Device','LED'), 'CHG', {'1':'CHG','2':'CHG_LED'}, FP['C'], 'charge LED (open-collector CHG)', P)
add('C4', ('Device','C'), '10uF/10V', {'1':'VSYS','2':'PGND'}, FP['C'], '', P)
add('C5', ('Device','C'), '100nF', {'1':'VSYS','2':'PGND'}, FP['C'], '', P)
add('C6', ('Device','C'), '10uF/10V', {'1':'BATT_P','2':'PGND'}, FP['C'], '', P)
add('C7', ('Device','C'), '100nF', {'1':'BATT_P','2':'PGND'}, FP['C'], '', P)
add('J2', ('Connector_Generic','Conn_01x02'), 'BATTERY 1S2P', {'1':'BATT_P','2':'BATT_N'}, FP['BATT'], '18650 1S2P pack (protected, with NTC)', P)
add('U23', ('Battery_Management','BQ297xy'), 'BQ29700DSER', {'1':'NC','2':'G_BMS_C','3':'G_BMS_D','4':'BATT_N','5':'BQ_BAT','6':'PGND'}, FP['SOT236'], '1S BMS protector', P)
add('R7', ('Device','R'), '330', {'1':'BATT_P','2':'BQ_BAT'}, FP['R'], 'BMS supply filter', P)
add('C8', ('Device','C'), '100nF', {'1':'BQ_BAT','2':'BATT_N'}, FP['C'], '', P)
add('Q1', ('Transistor_FET','Q_NMOS_GDS'), 'AO3400A', {'1':'G_BMS_C','2':'BMS_MID','3':'BATT_N'}, FP['SOT23'], 'charge FET (BMS)', P)
add('Q2', ('Transistor_FET','Q_NMOS_GDS'), 'AO3400A', {'1':'G_BMS_D','2':'BMS_MID','3':'PGND'}, FP['SOT23'], 'discharge FET (BMS)', P)
# +12V boost
add('U24', ('Regulator_Switching','MT3608'), 'MT3608 (+12V)', {'1':'SW12','2':'PGND','3':'FB12','4':'EN12','5':'VSYS','6':'NC'}, FP['SOT236'], 'boost 12.1 V (bus + analog)', P)
add('L1', ('Device','L'), '22uH', {'1':'VSYS','2':'SW12'}, FP['L'], '', P)
add('D4', ('Diode','SS34'), 'SS34', {'1':'SW12','2':'12V'}, FP['DIODE'], '', P)
add('R10', ('Device','R'), '91k', {'1':'12V','2':'FB12'}, FP['R'], 'FB 12.1 V', P)
add('R11', ('Device','R'), '4.7k', {'1':'FB12','2':'PGND'}, FP['R'], '', P)
add('C9', ('Device','C'), '100pF', {'1':'12V','2':'FB12'}, FP['C'], 'feed-forward', P)
add('R12', ('Device','R'), '100k', {'1':'VSYS','2':'EN12'}, FP['R'], 'enable', P)
add('C10', ('Device','C'), '10uF/10V', {'1':'VSYS','2':'PGND'}, FP['C'], '', P)
add('C11', ('Device','C_Polarized'), '220uF/25V', {'1':'12V','2':'PGND'}, FP['CP'], '', P)
add('C12', ('Device','C'), '100nF/50V', {'1':'12V','2':'PGND'}, FP['C'], '', P)
# +5V boost
add('U25', ('Regulator_Switching','MT3608'), 'MT3608 (+5V)', {'1':'SW5','2':'PGND','3':'FB5','4':'EN5','5':'VSYS','6':'NC'}, FP['SOT236'], 'boost 5.1 V (LED/panel/audio)', P)
add('L2', ('Device','L'), '22uH', {'1':'VSYS','2':'SW5'}, FP['L'], '', P)
add('D5', ('Diode','SS34'), 'SS34', {'1':'SW5','2':'5V'}, FP['DIODE'], '', P)
add('R13', ('Device','R'), '75k', {'1':'5V','2':'FB5'}, FP['R'], 'FB 5.1 V', P)
add('R14', ('Device','R'), '10k', {'1':'FB5','2':'PGND'}, FP['R'], '', P)
add('C13', ('Device','C'), '100pF', {'1':'5V','2':'FB5'}, FP['C'], '', P)
add('R15', ('Device','R'), '100k', {'1':'VSYS','2':'EN5'}, FP['R'], 'enable', P)
add('C14', ('Device','C'), '10uF/10V', {'1':'VSYS','2':'PGND'}, FP['C'], '', P)
add('C15', ('Device','C_Polarized'), '220uF/10V', {'1':'5V','2':'PGND'}, FP['CP'], '', P)
add('C16', ('Device','C'), '100nF', {'1':'5V','2':'PGND'}, FP['C'], '', P)
# +3V3_MCU buck
add('U26', ('picomod','MP1584_MOD'), 'MP1584 3.3V/3A (MCU)', {'1':'5V','2':'PGND','3':'3V3_MCU_RAW','4':'PGND'}, '', 'buck 5V->3.3V for P4/PSRAM', P)
add('C17', ('Device','C'), '10uF/10V', {'1':'5V','2':'PGND'}, FP['C'], '', P)
add('C18', ('Device','C_Polarized'), '100uF/10V', {'1':'3V3_MCU_RAW','2':'PGND'}, FP['CP'], '', P)
add('C19', ('Device','C'), '100nF', {'1':'3V3_MCU_RAW','2':'PGND'}, FP['C'], '', P)
add('FB1', ('Device','FerriteBead'), '600R@100MHz', {'1':'3V3_MCU_RAW','2':'3V3_MCU'}, FP['FB'], '', P)
add('C20', ('Device','C'), '10uF/10V', {'1':'3V3_MCU','2':'DGND'}, FP['C'], '', P)
add('C21', ('Device','C'), '100nF', {'1':'3V3_MCU','2':'DGND'}, FP['C'], '', P)
add('C22', ('Device','C'), '100nF', {'1':'3V3_MCU','2':'DGND'}, FP['C'], '', P)
# +3V3 periph
add('U27', ('Regulator_Linear','AP2112K-3.3'), 'AP2112K-3.3', {'1':'5V','2':'DGND','3':'5V','4':'NC','5':'3V3'}, FP['SOT235'], 'LDO 3.3 V peripherals/analog', P)
add('C24', ('Device','C'), '1uF', {'1':'5V','2':'DGND'}, FP['C'], '', P)
add('C25', ('Device','C'), '1uF', {'1':'3V3','2':'DGND'}, FP['C'], '', P)
add('C26', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', P)
# -12V inverter
add('U28', ('Regulator_Switching','MC34063AP'), 'MC34063', {'1':'MC_A','2':'MC_SW','3':'MC_TC','4':'-12V','5':'MC_FB','6':'12V','7':'MC_A','8':'MC_A'}, FP['DIP8'], 'inverting -12 V (bus/opamps)', P)
add('R16', ('Device','R'), '0.33', {'1':'12V','2':'MC_A'}, FP['R'], '', P)
add('C27', ('Device','C'), '1.5nF', {'1':'MC_TC','2':'-12V'}, FP['C'], '', P)
add('L3', ('Device','L'), '220uH', {'1':'MC_SW','2':'-12V'}, FP['L'], '', P)
add('D6', ('Diode','SS34'), 'SS34', {'1':'MC_SW','2':'PGND'}, FP['DIODE'], '', P)
add('R17', ('Device','R'), '33k', {'1':'PGND','2':'MC_FB'}, FP['R'], '', P)
add('R18', ('Device','R'), '3.9k', {'1':'MC_FB','2':'-12V'}, FP['R'], '', P)
add('C28', ('Device','C_Polarized'), '220uF/25V', {'1':'PGND','2':'-12V'}, FP['CP'], 'polarity + to PGND', P)
add('C29', ('Device','C'), '100nF/50V', {'1':'12V','2':'-12V'}, FP['C'], '', P)
add('C30', ('Device','C_Polarized'), '100uF/25V', {'1':'12V','2':'PGND'}, FP['CP'], '', P)
# BL +20V boost
add('U29', ('Regulator_Switching','MT3608'), 'MT3608 (+20V BL)', {'1':'SWBL','2':'PGND','3':'FBBL','4':'ENBL','5':'5V','6':'NC'}, FP['SOT236'], 'backlight boost 20 V (panel LED string)', P)
add('L4', ('Device','L'), '22uH', {'1':'5V','2':'SWBL'}, FP['L'], '', P)
add('D7', ('Diode','SS34'), 'SS34', {'1':'SWBL','2':'BL_20V'}, FP['DIODE'], '40 V Schottky', P)
add('R19', ('Device','R'), '100k', {'1':'5V','2':'ENBL'}, FP['R'], 'enable', P)
add('R20', ('Device','R'), '100k', {'1':'BL_20V','2':'FBBL'}, FP['R'], 'FB 20.4 V', P)
add('R21', ('Device','R'), '3.09k', {'1':'FBBL','2':'PGND'}, FP['R'], '', P)
add('C31', ('Device','C'), '100pF', {'1':'BL_20V','2':'FBBL'}, FP['C'], '', P)
add('C32', ('Device','C'), '10uF/10V', {'1':'5V','2':'PGND'}, FP['C'], '', P)
add('C33', ('Device','C'), '10uF/35V', {'1':'BL_20V','2':'PGND'}, FP['C'], '', P)
add('C34', ('Device','C'), '100nF/50V', {'1':'BL_20V','2':'PGND'}, FP['C'], '', P)
# +3V3_C6 LDO
add('U30', ('Regulator_Linear','AP2112K-3.3'), 'AP2112K-3.3 (C6)', {'1':'5V','2':'DGND','3':'5V','4':'NC','5':'3V3_C6'}, FP['SOT235'], 'dedicated LDO for Wi-Fi/BLE coprocessor', P)
add('C35', ('Device','C'), '1uF', {'1':'5V','2':'DGND'}, FP['C'], '', P)
add('C36', ('Device','C'), '22uF/10V', {'1':'3V3_C6','2':'DGND'}, FP['C'], '', P)
add('C37', ('Device','C'), '100nF', {'1':'3V3_C6','2':'DGND'}, FP['C'], '', P)
# filtered rails / external 12 V
add('D2', ('Diode','SS34'), 'SS34', {'1':'12V_EXT','2':'12V'}, FP['DIODE'], 'diode-OR external 12 V (PWR-2)', P)
add('C110', ('Device','C_Polarized'), '100uF/25V', {'1':'12V_EXT','2':'PGND'}, FP['CP'], '', P)
add('C111', ('Device','C'), '100nF/50V', {'1':'12V_EXT','2':'PGND'}, FP['C'], '', P)
add('FB2', ('Device','FerriteBead'), '600R@100MHz', {'1':'12V','2':'12V_B'}, FP['FB'], 'bus +12V', P)
add('C38', ('Device','C_Polarized'), '100uF/25V', {'1':'12V_B','2':'PGND'}, FP['CP'], '', P)
add('FB3', ('Device','FerriteBead'), '600R@100MHz', {'1':'-12V','2':'-12V_B'}, FP['FB'], 'bus -12V', P)
add('C39', ('Device','C_Polarized'), '220uF/25V', {'1':'PGND','2':'-12V_B'}, FP['CP'], 'polarity + to PGND', P)
add('FB4', ('Device','FerriteBead'), '600R@100MHz', {'1':'5V','2':'5V_PANEL'}, FP['FB'], 'panel +5V', P)
add('C40', ('Device','C_Polarized'), '100uF/10V', {'1':'5V_PANEL','2':'PGND'}, FP['CP'], '', P)
add('FB5', ('Device','FerriteBead'), '600R@100MHz', {'1':'3V3','2':'3V3_PANEL'}, FP['FB'], 'panel +3V3', P)
add('C41', ('Device','C'), '10uF/10V', {'1':'3V3_PANEL','2':'DGND'}, FP['C'], '', P)
add('NT1', ('Device','NetTie_2'), 'AGND=DGND', {'1':'AGND','2':'DGND'}, 'NetTie:NetTie-2_SMD_Pad0.5mm', 'single-point analog/digital ground', P)
add('NT2', ('Device','NetTie_2'), 'DGND=PGND', {'1':'DGND','2':'PGND'}, 'NetTie:NetTie-2_SMD_Pad0.5mm', 'single-point digital/power ground', P)

# ---------------------------- MCU / USB / C6 / SD -------------------------
def mcu_module_nets():
    nets = {}
    for r in B.PINMAP:
        sig = r[0]
        net = {'GND':'DGND', '3V3_MCU':'3V3_MCU', 'CHIP_PU':'CHIP_PU',
               'USB_HS_DP':'USB_HS_DP', 'USB_HS_DM':'USB_HS_DM'}.get(sig, sig)
        nets[str(r[7])] = net
    return nets
add('A1', ('picomod','ESP32-P4_MOD'), 'ESP32-P4NRW32 + 32MB PSRAM (module TBD)', mcu_module_nets(), FP['MCU'], 'PRE-FREEZE: 2x32 logical module slot; adapter/physical module TBD after P1 benchmark', M)
for i, ref in enumerate(['C42','C43','C44','C45','C46','C47']):
    add(ref, ('Device','C'), '100nF', {'1':'3V3_MCU','2':'DGND'}, FP['C'], 'P4 decoupling', M)
add('C48', ('Device','C'), '10uF/10V', {'1':'3V3_MCU','2':'DGND'}, FP['C'], '', M)
add('C49', ('Device','C'), '10uF/10V', {'1':'3V3_MCU','2':'DGND'}, FP['C'], '', M)
add('SW1', ('Switch','SW_Push'), 'BOOT', {'1':'BOOT','2':'DGND'}, FP['BTN'], 'boot strap GPIO35 (download boot)', M)
add('R22', ('Device','R'), '10k', {'1':'3V3_MCU','2':'BOOT'}, FP['R'], 'BOOT pull-up', M)
add('SW2', ('Switch','SW_Push'), 'RESET', {'1':'CHIP_PU','2':'DGND'}, FP['BTN'], 'reset', M)
add('R23', ('Device','R'), '10k', {'1':'3V3_MCU','2':'CHIP_PU'}, FP['R'], 'CHIP_PU pull-up', M)
add('C51', ('Device','C'), '100nF', {'1':'CHIP_PU','2':'DGND'}, FP['C'], 'reset RC', M)
add('R24', ('Device','R'), '10k', {'1':'STRAP36','2':'3V3_MCU'}, FP['R'], 'GPIO36 strap PU (joint download boot reachable)', M)
add('J4', ('Connector_Generic','Conn_01x03'), 'UART0 TP', {'1':'DGND','2':'UART0_TX','3':'UART0_RX'}, FP['HDR3'], 'UART0 testpoints/boot log', M)
add('R25', ('Device','R'), '100k', {'1':'VBUS_CHG','2':'VBUS_DET'}, FP['R'], 'VBUS detect divider', M)
add('R26', ('Device','R'), '100k', {'1':'VBUS_DET','2':'DGND'}, FP['R'], '', M)
add('C52', ('Device','C'), '100nF', {'1':'VBUS_DET','2':'DGND'}, FP['C'], '', M)
add('U31', ('picomod','ESP32-C6-MINI-1'), 'ESP32-C6-MINI-1 (Wi-Fi6/BLE5.3)',
    {'1':'3V3_C6','2':'DGND','3':'C6_RST','4':'SPI2_SCK','5':'SPI2_MOSI','6':'SPI2_MISO',
     '7':'C6_CS','8':'C6_HS','9':'C6_DR','10':'DGND'}, '',
    'Wi-Fi/BLE coprocessor; DNP if ESP32-S3 build; antenna keep-out >=15 mm', M)
add('R27', ('Device','R'), '10k', {'1':'3V3_C6','2':'C6_RST'}, FP['R'], 'C6 EN pull-up', M)
add('C53', ('Device','C'), '22uF/10V', {'1':'3V3_C6','2':'DGND'}, FP['C'], '', M)
add('C54', ('Device','C'), '100nF', {'1':'3V3_C6','2':'DGND'}, FP['C'], '', M)
add('C55', ('Device','C'), '100nF', {'1':'3V3_C6','2':'DGND'}, FP['C'], '', M)
# microSD
add('J5', ('Connector','Micro_SD_Card_Det1'), 'microSD (SDIO 4-bit)',
    {'1':'SD_D2','2':'SD_D3','3':'SD_CMD','4':'3V3','5':'SD_CLK','6':'DGND',
     '7':'SD_D0','8':'SD_D1','9':'SD_CD','SH':'DGND'}, FP['SD'], 'SDMMC slot0, 4-bit', M)
for i, (net) in enumerate(['SD_CMD','SD_D0','SD_D1','SD_D2','SD_D3']):
    add('R%d' % (30+i), ('Device','R'), '10k', {'1':'3V3','2':net}, FP['R'], 'SDIO pull-up', M)
add('R35', ('Device','R'), '10k', {'1':'3V3','2':'SD_CD'}, FP['R'], 'card detect pull-up', M)
add('C56', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', M)
add('C57', ('Device','C'), '10uF/10V', {'1':'3V3','2':'DGND'}, FP['C'], '', M)

# ---------------------------- AUDIO ---------------------------------------
add('U32', ('Audio','PCM5102A'), 'PCM5102A',
    {'1':'3V3','2':'CP_P','3':'AGND','4':'CP_M','5':'VNEG','6':'DAC_L','7':'DAC_R',
     '8':'3V3','9':'AGND','10':'DGND','11':'DGND','12':'I2S_MCLK','13':'I2S_BCK',
     '14':'I2S_DAC_DIN','15':'I2S_LRCK','16':'DGND','17':'XSMT','18':'LDOO',
     '19':'DGND','20':'3V3'}, FP['TSSOP20'], 'I2S DAC 112 dB (24/96)', A)
add('C58', ('Device','C'), '1uF/10V', {'1':'CP_P','2':'CP_M'}, FP['C'], 'charge-pump flying cap', A)
add('C59', ('Device','C_Polarized'), '1uF/10V', {'1':'AGND','2':'VNEG'}, FP['CP'], 'polarity + to AGND', A)
add('C60', ('Device','C'), '100nF', {'1':'LDOO','2':'AGND'}, FP['C'], '', A)
add('C61', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', A)
add('C62', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', A)
add('C63', ('Device','C'), '10uF/10V', {'1':'3V3','2':'AGND'}, FP['C'], '', A)
add('C64', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', A)
add('R36', ('Device','R'), '10k', {'1':'3V3','2':'XSMT'}, FP['R'], 'unmute', A)
add('C65', ('Device','C'), '100nF', {'1':'XSMT','2':'AGND'}, FP['C'], 'mute RC: XSMT low at power-up', A)
add('C66', ('Device','C_Polarized'), '10uF/16V', {'1':'DAC_L','2':'AUD_L_IN'}, FP['CP'], 'AC coupling L', A)
add('C67', ('Device','C_Polarized'), '10uF/16V', {'1':'DAC_R','2':'AUD_R_IN'}, FP['CP'], 'AC coupling R', A)
add('R37', ('Device','R'), '100k', {'1':'AUD_L_IN','2':'AGND'}, FP['R'], 'bias/DC path', A)
add('R38', ('Device','R'), '100k', {'1':'AUD_R_IN','2':'AGND'}, FP['R'], '', A)
add('U33', ('Amplifier_Operational','TL072'), 'TL072', {'1':'AUDL_BUF','2':'AUDL_BUF','3':'AUD_L_IN'}, FP['DIP8'], 'LINE/PHONES buffer L', A, unit=1)
add('U33', ('Amplifier_Operational','TL072'), 'TL072', {'7':'AUDR_BUF','6':'AUDR_BUF','5':'AUD_R_IN'}, FP['DIP8'], 'LINE/PHONES buffer R', A, unit=2)
add('U33', ('Amplifier_Operational','TL072'), 'TL072', {'8':'12V','4':'-12V'}, FP['DIP8'], 'power', A, unit=3)
add('C68', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', A)
add('C69', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', A)
add('R39', ('Device','R'), '100', {'1':'AUDL_BUF','2':'AUDOUT_L'}, FP['R'], 'LINE OUT L (rear)', A)
add('R40', ('Device','R'), '100', {'1':'AUDR_BUF','2':'AUDOUT_R'}, FP['R'], 'LINE OUT R (rear)', A)
add('R41', ('Device','R'), '100', {'1':'AUDL_BUF','2':'PHONES_L'}, FP['R'], 'PHONES L', A)
add('R42', ('Device','R'), '100', {'1':'AUDR_BUF','2':'PHONES_R'}, FP['R'], 'PHONES R', A)
add('C70', ('Device','C'), '100pF', {'1':'AUDOUT_L','2':'AGND'}, FP['C'], '', A)
add('C71', ('Device','C'), '100pF', {'1':'AUDOUT_R','2':'AGND'}, FP['C'], '', A)
# PCM1808 ADC
add('U34', ('picomod','PCM1808'), 'PCM1808PWR',
    {'1':'VREF_ADC','2':'AGND','3':'5V','4':'3V3','5':'DGND','6':'I2S_MCLK','7':'I2S_LRCK',
     '8':'I2S_BCK','9':'I2S_ADC_DOUT','10':'DGND','11':'DGND','12':'DGND',
     '13':'AUDIN_L_C','14':'AUDIN_R_C'}, FP['TSSOP14'], 'I2S ADC 24/96 (sampler/effector input)', A)
add('C72', ('Device','C_Polarized'), '10uF/10V', {'1':'VREF_ADC','2':'AGND'}, FP['CP'], '', A)
add('C73', ('Device','C'), '100nF', {'1':'VREF_ADC','2':'AGND'}, FP['C'], '', A)
add('C74', ('Device','C_Polarized'), '10uF/10V', {'1':'5V','2':'AGND'}, FP['CP'], 'VCC 5 V analog', A)
add('C75', ('Device','C'), '100nF', {'1':'5V','2':'AGND'}, FP['C'], '', A)
add('C76', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], 'VDD 3.3 V digital', A)
add('R43', ('Device','R'), '1k', {'1':'AUDIN_L','2':'AUDIN_L_F'}, FP['R'], 'input protection', A)
add('D8', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'5V','3':'AUDIN_L_F'}, FP['BAT54S'], 'clamp', A)
add('C77', ('Device','C'), '100pF', {'1':'AUDIN_L_F','2':'AGND'}, FP['C'], '', A)
add('C78', ('Device','C'), '1uF/16V', {'1':'AUDIN_L_F','2':'AUDIN_L_C'}, FP['C'], 'AC coupling to VINL', A)
add('R44', ('Device','R'), '1k', {'1':'AUDIN_R','2':'AUDIN_R_F'}, FP['R'], '', A)
add('D9', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'5V','3':'AUDIN_R_F'}, FP['BAT54S'], '', A)
add('C79', ('Device','C'), '100pF', {'1':'AUDIN_R_F','2':'AGND'}, FP['C'], '', A)
add('C80', ('Device','C'), '1uF/16V', {'1':'AUDIN_R_F','2':'AUDIN_R_C'}, FP['C'], '', A)

# ---------------------------- CV ------------------------------------------
add('U35', ('Analog_DAC','MCP4728'), 'MCP4728A0-E/UN (0x60)',
    {'1':'3V3','2':'I2C0_SCL','3':'I2C0_SDA','4':'DGND','5':'NC','6':'DAC_A','7':'DAC_B',
     '8':'DAC_C','9':'DAC_D','10':'AGND'}, FP['MSOP10'], 'CV1..CV4 (bus), I2C 0x60', V)
add('C81', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', V)
add('C82', ('Device','C'), '10uF/10V', {'1':'3V3','2':'AGND'}, FP['C'], '', V)
add('U36', ('Analog_DAC','MCP4728'), 'MCP4728A1-E/UN (0x61)',
    {'1':'3V3','2':'I2C0_SCL','3':'I2C0_SDA','4':'DGND','5':'NC','6':'DAC_E','7':'DAC_F',
     '8':'NC','9':'NC','10':'AGND'}, FP['MSOP10'], 'CV5/CV6 (panel jacks), I2C 0x61', V)
add('C83', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', V)
add('C84', ('Device','C'), '10uF/10V', {'1':'3V3','2':'AGND'}, FP['C'], '', V)
# TL074 #1: CV1..CV4 buffers (units 1..4) + power
for i in range(4):
    net_out = 'CVR%d' % i; net_sum = 'CVS%d' % i
    dac = 'DAC_' + 'ABCD'[i]
    nets = {'1':'CVR0','2':'CVS0','3':'DAC_A'} if i == 0 else {}
    add('U35' if False else 'U37', ('Amplifier_Operational','TL074'), 'TL074',
        {'%d' % (1 + i*0): ''}, FP['DIP14'], 'CV%d x4.9 buffer' % (i+1), V, unit=i+1)
# fix nets of the four U37 units
for i, nets in enumerate([
        {'1':'CVR0','2':'CVS0','3':'DAC_A'},
        {'7':'CVR1','6':'CVS1','5':'DAC_B'},
        {'8':'CVR2','9':'CVS2','10':'DAC_C'},
        {'14':'CVR3','13':'CVS3','12':'DAC_D'}]):
    C[-4+i]['nets'] = nets
C[-4]['note'] = 'CV1 x4.9 buffer'; C[-3]['note'] = 'CV2 x4.9 buffer'
C[-2]['note'] = 'CV3 x4.9 buffer'; C[-1]['note'] = 'CV4 x4.9 buffer'
add('U37', ('Amplifier_Operational','TL074'), 'TL074', {'4':'12V','11':'-12V'}, FP['DIP14'], 'power', V, unit=5)
for i in range(4):
    add('R%d' % (45+i), ('Device','R'), '39k', {'1':'CVS%d'%i,'2':'CVR%d'%i}, FP['R'], 'Rf CV%d' % (i+1), V)
    add('R%d' % (51+i), ('Device','R'), '10k', {'1':'CVS%d'%i,'2':'AGND'}, FP['R'], 'Rg CV%d' % (i+1), V)
    add('R%d' % (57+i), ('Device','R'), '1k', {'1':'CVR%d'%i,'2':'CVOUT%d'%(i+1)}, FP['R'], 'output CV%d' % (i+1), V)
    add('D%d' % (10+i), ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'12V','3':'CVOUT%d'%(i+1)}, FP['BAT54S'], 'CV%d protection' % (i+1), V)
# TL074 #2: CV5/CV6 buffers + 2 spare + power
add('U38', ('Amplifier_Operational','TL074'), 'TL074', {'1':'CVR4','2':'CVS4','3':'DAC_E'}, FP['DIP14'], 'CV5 x4.9 buffer', V, unit=1)
add('U38', ('Amplifier_Operational','TL074'), 'TL074', {'7':'CVR5','6':'CVS5','5':'DAC_F'}, FP['DIP14'], 'CV6 x4.9 buffer', V, unit=2)
add('U38', ('Amplifier_Operational','TL074'), 'TL074', {'8':'SPARE_C','9':'SPARE_C','10':'AGND'}, FP['DIP14'], 'spare (grounded)', V, unit=3)
add('U38', ('Amplifier_Operational','TL074'), 'TL074', {'14':'SPARE_D','13':'SPARE_D','12':'AGND'}, FP['DIP14'], 'spare (grounded)', V, unit=4)
add('U38', ('Amplifier_Operational','TL074'), 'TL074', {'4':'12V','11':'-12V'}, FP['DIP14'], 'power', V, unit=5)
for i, ch in enumerate([4, 5]):
    add('R%d' % (49+i), ('Device','R'), '39k', {'1':'CVS%d'%ch,'2':'CVR%d'%ch}, FP['R'], 'Rf CV%d' % (ch+1), V)
    add('R%d' % (55+i), ('Device','R'), '10k', {'1':'CVS%d'%ch,'2':'AGND'}, FP['R'], 'Rg CV%d' % (ch+1), V)
    add('R%d' % (61+i), ('Device','R'), '1k', {'1':'CVR%d'%ch,'2':'CVOUT%d'%(ch+1)}, FP['R'], 'output CV%d (panel)' % (ch+1), V)
    add('D%d' % (14+i), ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'12V','3':'CVOUT%d'%(ch+1)}, FP['BAT54S'], 'CV%d protection' % (ch+1), V)
add('C85', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', V)
add('C86', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', V)
add('C87', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', V)
add('C88', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', V)
# TL074 #3: CV IN level shift (2 ch + 1.65 V ref + spare)
add('U39', ('Amplifier_Operational','TL074'), 'TL074', {'1':'CVIN1_RAW','2':'CVIN1_N','3':'CVREF_B'}, FP['DIP14'], 'CV IN1 level shift', V, unit=1)
add('U39', ('Amplifier_Operational','TL074'), 'TL074', {'7':'CVIN2_RAW','6':'CVIN2_N','5':'CVREF_B'}, FP['DIP14'], 'CV IN2 level shift', V, unit=2)
add('U39', ('Amplifier_Operational','TL074'), 'TL074', {'8':'CVREF_B','9':'CVREF_B','10':'CVREF'}, FP['DIP14'], '1.65 V reference buffer', V, unit=3)
add('U39', ('Amplifier_Operational','TL074'), 'TL074', {'14':'SPARE_E','13':'SPARE_E','12':'AGND'}, FP['DIP14'], 'spare (grounded)', V, unit=4)
add('U39', ('Amplifier_Operational','TL074'), 'TL074', {'4':'12V','11':'-12V'}, FP['DIP14'], 'power', V, unit=5)
add('R63', ('Device','R'), '100k', {'1':'CVIN1','2':'CVIN1_N'}, FP['R'], '', V)
add('R64', ('Device','R'), '16.5k', {'1':'CVIN1_N','2':'CVIN1_RAW'}, FP['R'], 'gain 0.165', V)
add('R65', ('Device','R'), '100k', {'1':'CVIN2','2':'CVIN2_N'}, FP['R'], '', V)
add('R66', ('Device','R'), '16.5k', {'1':'CVIN2_N','2':'CVIN2_RAW'}, FP['R'], 'gain 0.165', V)
add('R67', ('Device','R'), '1k', {'1':'CVIN1_RAW','2':'CVIN1_ADC'}, FP['R'], '', V)
add('R68', ('Device','R'), '1k', {'1':'CVIN2_RAW','2':'CVIN2_ADC'}, FP['R'], '', V)
add('C89', ('Device','C'), '100nF', {'1':'CVIN1_ADC','2':'AGND'}, FP['C'], '', V)
add('C90', ('Device','C'), '100nF', {'1':'CVIN2_ADC','2':'AGND'}, FP['C'], '', V)
add('D16', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'3V3','3':'CVIN1_ADC'}, FP['BAT54S'], '', V)
add('D17', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'3V3','3':'CVIN2_ADC'}, FP['BAT54S'], '', V)
add('R69', ('Device','R'), '47k', {'1':'3V3','2':'CVREF'}, FP['R'], '1.65 V', V)
add('R70', ('Device','R'), '47k', {'1':'CVREF','2':'AGND'}, FP['R'], '', V)
add('C91', ('Device','C'), '100nF', {'1':'CVREF','2':'AGND'}, FP['C'], '', V)
add('C92', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', V)
add('C93', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', V)
# MCP3208 ADC + input chains
add('U40', ('Analog_ADC','MCP3208'), 'MCP3208',
    {'1':'CVIN1_ADC','2':'CVIN2_ADC','3':'FADER1_ADC','4':'FADER2_ADC','5':'EXPR_ADC',
     '6':'SPARE_ADC','7':'BATT_MON','8':'TEMP_MON','9':'DGND','10':'MCP3208_CS',
     '11':'SPI2_MOSI','12':'SPI2_MISO','13':'SPI2_SCK','14':'AGND','15':'VREF33','16':'3V3'},
    FP['DIP16'], '8-ch 12-bit SPI ADC', V)
add('FB6', ('Device','FerriteBead'), '600R@100MHz', {'1':'3V3','2':'VREF33'}, FP['FB'], 'ADC reference filter', V)
add('C94', ('Device','C'), '10uF/10V', {'1':'VREF33','2':'AGND'}, FP['C'], '', V)
add('C95', ('Device','C'), '100nF', {'1':'VREF33','2':'AGND'}, FP['C'], '', V)
add('C96', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', V)
add('R71', ('Device','R'), '1k', {'1':'FADER1','2':'FADER1_ADC'}, FP['R'], '', V)
add('C97', ('Device','C'), '100nF', {'1':'FADER1_ADC','2':'AGND'}, FP['C'], '', V)
add('R72', ('Device','R'), '1k', {'1':'FADER2','2':'FADER2_ADC'}, FP['R'], '', V)
add('C98', ('Device','C'), '100nF', {'1':'FADER2_ADC','2':'AGND'}, FP['C'], '', V)
add('R73', ('Device','R'), '1k', {'1':'EXPR','2':'EXPR_ADC'}, FP['R'], 'expression pedal', V)
add('C99', ('Device','C'), '100nF', {'1':'EXPR_ADC','2':'AGND'}, FP['C'], '', V)
add('R74', ('Device','R'), '1k', {'1':'SPARE_ADC','2':'AGND'}, FP['R'], 'reserved channel to AGND', V)
add('C100', ('Device','C'), '100nF', {'1':'SPARE_ADC','2':'AGND'}, FP['C'], '', V)
add('R75', ('Device','R'), '100k', {'1':'BATT_P','2':'BATT_MON'}, FP['R'], 'battery divider', V)
add('R76', ('Device','R'), '47k', {'1':'BATT_MON','2':'AGND'}, FP['R'], '', V)
add('C101', ('Device','C'), '100nF', {'1':'BATT_MON','2':'AGND'}, FP['C'], '', V)
add('TH2', ('Device','Thermistor_NTC'), 'NTC 10k', {'1':'3V3','2':'TEMP_MON'}, FP['R'], 'pack temperature', V)
add('R77', ('Device','R'), '10k', {'1':'TEMP_MON','2':'AGND'}, FP['R'], '', V)
add('C102', ('Device','C'), '100nF', {'1':'TEMP_MON','2':'AGND'}, FP['C'], '', V)
add('R78', ('Device','R'), '2.2k', {'1':'3V3','2':'I2C0_SDA'}, FP['R'], 'I2C pull-up', V)
add('R79', ('Device','R'), '2.2k', {'1':'3V3','2':'I2C0_SCL'}, FP['R'], 'I2C pull-up', V)
add('U41', ('Memory_EEPROM','24LC32'), '24LC32A', {'1':'3V3','2':'3V3','3':'3V3','4':'DGND',
    '5':'I2C0_SDA','6':'I2C0_SCL','7':'DGND','8':'3V3'}, FP['DIP8'], 'calibration EEPROM 0x57 (A2..A0=1)', V)
add('C103', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', V)

# ---------------------------- MIDI ----------------------------------------
add('U42', ('Isolator','6N137'), '6N137', {'1':'NC','2':'MIDI_A','3':'MIDI_IN_T','4':'NC',
    '5':'DGND','6':'MIDI_RX','7':'5V','8':'5V'}, FP['DIP8'], 'MIDI IN optocoupler', M)
add('R80', ('Device','R'), '220', {'1':'MIDI_IN_R','2':'MIDI_A'}, FP['R'], '', M)
add('R81', ('Device','R'), '4.7k', {'1':'3V3','2':'MIDI_RX'}, FP['R'], '6N137 pull-up', M)
add('U43', ('picomod','74HCT125'), '74HCT125', {'1':'DGND','2':'MIDI_TX','3':'MIDI_DRV',
    '4':'5V','5':'DGND','6':'NC','7':'DGND','8':'NC','9':'DGND','10':'5V','11':'NC',
    '12':'DGND','13':'5V','14':'5V'}, FP['SOIC14'], 'MIDI OUT buffer (5 V)', M)
add('R82', ('Device','R'), '33', {'1':'MIDI_DRV','2':'MIDI_OUT_T'}, FP['R'], '', M)
add('R83', ('Device','R'), '220', {'1':'5V','2':'MIDI_OUT_R'}, FP['R'], '', M)

# ---------------------------- GATE / LED level shifter ---------------------
add('Q3', ('Transistor_FET','2N7000'), '2N7000', {'1':'DGND','2':'G1','3':'GATE1'}, FP['TO92'], 'GATE1 open-drain', M)
add('R84', ('Device','R'), '1k', {'1':'GATE1_GPIO','2':'G1'}, FP['R'], '', M)
add('R85', ('Device','R'), '100k', {'1':'G1','2':'DGND'}, FP['R'], 'gate pull-down', M)
add('R86', ('Device','R'), '4.7k', {'1':'5V','2':'GATE1'}, FP['R'], 'GATE1 pull-up', M)
add('Q4', ('Transistor_FET','2N7000'), '2N7000', {'1':'DGND','2':'G2','3':'GATE2'}, FP['TO92'], 'GATE2 open-drain', M)
add('R87', ('Device','R'), '1k', {'1':'GATE2_GPIO','2':'G2'}, FP['R'], '', M)
add('R88', ('Device','R'), '100k', {'1':'G2','2':'DGND'}, FP['R'], 'gate pull-down', M)
add('R89', ('Device','R'), '4.7k', {'1':'5V','2':'GATE2'}, FP['R'], 'GATE2 pull-up', M)
add('U44', ('picomod','74HCT1G125'), '74HCT1G125', {'1':'DGND','2':'LED_GPIO','3':'DGND',
    '4':'LED_5V','5':'5V'}, FP['SOT353'], 'WS2812 level shifter 3.3->5 V', M)
add('R90', ('Device','R'), '330', {'1':'LED_5V','2':'LED_DATA'}, FP['R'], 'series resistor', M)

# ---------------------------- MODULE BUS (2 x IDC-26) ----------------------
for p in range(2):
    Pn = p + 1
    nets = {'1': '12V_P%d' % Pn, '2': 'PGND', '3': 'N12V_P%d' % Pn, '4': 'PGND',
            '5': 'CVOUT1', '6': 'AGND', '7': 'CVOUT2', '8': 'AGND', '9': 'CVOUT3',
            '10': 'AGND', '11': 'CVOUT4', '12': 'AGND', '13': 'GATE1', '14': 'DGND',
            '15': 'GATE2', '16': 'DGND', '17': 'AUDIN_L', '18': 'AGND',
            '19': 'AUDIN_R', '20': 'AGND', '21': 'AUDOUT_L', '22': 'AGND',
            '23': 'AUDOUT_R', '24': 'AGND', '25': 'NC', '26': 'NC'}
    add('P%d' % Pn, ('Connector_Generic','Conn_02x13_Odd_Even'), 'PicoMod analog bus IDC-26 PORT%d' % (p+1), nets, FP['IDC26'], 'bus: +-12V, CV1..4, GATE1/2, audio', R)
add('F2', ('Device','Polyfuse'), '0.5A', {'1':'12V_B','2':'12V_P1'}, FP['PF'], 'port1 +12V', R)
add('D18', ('Diode','SS34'), 'SS34', {'1':'12V_P1','2':'12V_B'}, FP['DIODE'], 'reverse protection', R)
add('F3', ('Device','Polyfuse'), '0.3A', {'1':'-12V_B','2':'N12V_P1'}, FP['PF'], 'port1 -12V', R)
add('D19', ('Diode','SS34'), 'SS34', {'1':'-12V_B','2':'N12V_P1'}, FP['DIODE'], 'reverse protection', R)
add('D20', ('Diode','SMAJ15A'), 'SMAJ15A', {'1':'12V_P1','2':'PGND'}, FP['DIODE'], 'TVS port1', R)
add('C104', ('Device','C'), '100nF/50V', {'1':'12V_P1','2':'PGND'}, FP['C'], '', R)
add('C105', ('Device','C_Polarized'), '10uF/25V', {'1':'12V_P1','2':'PGND'}, FP['CP'], '', R)
add('C106', ('Device','C'), '100nF/50V', {'1':'N12V_P1','2':'PGND'}, FP['C'], '', R)
add('F4', ('Device','Polyfuse'), '0.5A', {'1':'12V_B','2':'12V_P2'}, FP['PF'], 'port2 +12V', R)
add('D21', ('Diode','SS34'), 'SS34', {'1':'12V_P2','2':'12V_B'}, FP['DIODE'], '', R)
add('F5', ('Device','Polyfuse'), '0.3A', {'1':'-12V_B','2':'N12V_P2'}, FP['PF'], 'port2 -12V', R)
add('D22', ('Diode','SS34'), 'SS34', {'1':'-12V_B','2':'N12V_P2'}, FP['DIODE'], '', R)
add('D23', ('Diode','SMAJ15A'), 'SMAJ15A', {'1':'12V_P2','2':'PGND'}, FP['DIODE'], 'TVS port2', R)
add('C107', ('Device','C'), '100nF/50V', {'1':'12V_P2','2':'PGND'}, FP['C'], '', R)
add('C108', ('Device','C_Polarized'), '10uF/25V', {'1':'12V_P2','2':'PGND'}, FP['CP'], '', R)
add('C109', ('Device','C'), '100nF/50V', {'1':'N12V_P2','2':'PGND'}, FP['C'], '', R)

# ---------------------------- PANEL-2 connectors + rear I/O ----------------
PANEL_MAP = {'3V3':'3V3_PANEL', '5V':'5V_PANEL', 'DGND':'DGND', 'AGND':'AGND',
             'BL_ANODE':'BL_20V', 'BL_CATHODE':'BL_CATHODE'}
def conn_nets(pins):
    out = {}
    for p, sig, kind in pins:
        out[str(p)] = PANEL_MAP.get(sig, sig)
    return out
add('J14', ('Connector_Generic','Conn_02x13_Odd_Even'), 'PANEL-2 J14 (IDC-26) control/analog',
    conn_nets(B.J_PANEL), FP['IDC26'], 'I2C, encoders/matrix (via expanders), faders, CV, GATE, LED', N)
add('J15', ('Connector_Generic','Conn_02x20_Odd_Even'), 'PANEL-2 J12 (FFC-40) LCD+I2C+INT+BL',
    conn_nets(B.J_LCD), FP['FFC40'], '25 signals: RGB565 + I2C + INT + BL_PWM + BL_ANODE/CATHODE', N)
add('J16', ('Connector_Generic','Conn_02x08_Odd_Even'), 'J-DIG-EXP (IDC-16) smart-module digital',
    conn_nets([(p, s, k) for p, s, k in B.J_DIG]), FP['IDC16'], 'TDM/I2S + SPI mailbox + I2C (R-22)', N)
add('R95', ('Device','R'), '0R', {'1':'BL_CATHODE','2':'PGND'}, FP['R'], 'backlight LED return path', N)
# rear panel connectors (off-board, wired via TB1/TB2)
add('J6', ('Connector_Audio','AudioJack3'), 'MIDI IN TRS-A', {'T':'MIDI_IN_T','R':'MIDI_IN_R','S':'DGND'}, '', 'rear panel jack', N, on_board=False)
add('J7', ('Connector_Audio','AudioJack3'), 'MIDI OUT TRS-A', {'T':'MIDI_OUT_T','R':'MIDI_OUT_R','S':'DGND'}, '', 'rear panel jack', N, on_board=False)
add('J8', ('Connector_Audio','AudioJack3'), 'LINE OUT L/R 3.5mm', {'T':'AUDOUT_L','R':'AUDOUT_R','S':'AGND'}, '', 'rear panel jack', N, on_board=False)
add('J9', ('Connector_Audio','AudioJack3'), 'PHONES 3.5mm', {'T':'PHONES_L','R':'PHONES_R','S':'AGND'}, '', 'rear panel jack', N, on_board=False)
add('J10', ('Connector_Audio','AudioJack2'), 'AUDIO IN L 3.5mm', {'T':'AUDIN_L','S':'AGND'}, '', 'rear panel jack', N, on_board=False)
add('J11', ('Connector_Audio','AudioJack2'), 'AUDIO IN R 3.5mm', {'T':'AUDIN_R','S':'AGND'}, '', 'rear panel jack', N, on_board=False)
add('J12', ('Connector','Barrel_Jack'), 'DC 12V 5.5/2.1', {'1':'12V_EXT','2':'PGND'}, '', 'rear panel jack (from PWR-2)', N, on_board=False)
add('J13', ('Connector_Audio','AudioJack3'), 'EXPRESSION TRS', {'T':'EXPR','R':'3V3','S':'AGND'}, '', 'rear panel jack', N, on_board=False)
add('TB1', ('Connector_Generic','Conn_01x12'), 'Rear audio terminal block', {
    '1':'AUDOUT_L','2':'AUDOUT_R','3':'AGND','4':'PHONES_L','5':'PHONES_R','6':'AGND',
    '7':'AUDIN_L','8':'AUDIN_R','9':'AGND','10':'AGND','11':'AGND','12':'AGND'}, FP['TB12'], 'jacks -> CORE-2 rear', N)
add('TB2', ('Connector_Generic','Conn_01x10'), 'Rear MIDI/DC/EXPR terminal block', {
    '1':'MIDI_IN_T','2':'MIDI_IN_R','3':'DGND','4':'MIDI_OUT_T','5':'MIDI_OUT_R',
    '6':'DGND','7':'12V_EXT','8':'PGND','9':'EXPR','10':'3V3'}, 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1-10-3.81_1x10_P3.81mm_Horizontal', '', N)

# ---------------------------- test points + power flags -------------------
for i, (tp, net, why) in enumerate(B.TPS):
    add(tp, ('Connector','TestPoint'), net, {'1': net}, '', why, 'TP', on_board=True)
FLAGS = ['VBUS_CHG', 'BATT_N', 'PGND', '12V', '-12V', '5V', '3V3_MCU', 'DGND', 'AGND']
