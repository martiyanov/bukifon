#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CORE-1 schematic generator for Bukifon.

Emits a KiCad 10 S-expression schematic (version 20250114) directly -- KiCad 10
`kicad-cli sch upgrade` no longer imports legacy EESchema v5 files, so the
schema is generated in the native format. Then runs ERC / PDF / SVG / netlist
exports and builds BOM + wiring tables.

Usage:  python3 gen_core_sch.py [--no-export]
Output: CORE-1.kicad_sch, bukifon.kicad_sym, sym-lib-table, CORE-1.kicad_pro,
        erc/erc.rpt, CORE-1.pdf, CORE-1.svg, netlist.net, BOM-core.csv,
        wiring-jacks.md, README.md
"""
import os, sys, math, json, subprocess, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import kicad_sch as k

KICAD_CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
PROJECT = 'CORE-1'
PAPER = 'A0'
SW = 63.5      # slot width  (50 x 1.27 mm)
SH = 30.48     # slot height (24 x 1.27 mm)
LABEL_PAD = 2.54 + 13.0   # escape stub + label text allowance

# --------------------------------------------------------------------------
# custom project library symbols
# --------------------------------------------------------------------------
def _pin(num, name, x, y, a, ln=2.54, etype='passive'):
    return ('\t\t(pin %s line (at %s %s %s) (length %s)\n'
            '\t\t\t(name "%s" (effects (font (size 1.27 1.27))))\n'
            '\t\t\t(number "%s" (effects (font (size 1.27 1.27))))\n'
            '\t\t)' % (etype, f(x), f(y), int(a), f(ln), name, num))

def f(v):
    v = round(float(v), 3)
    return ('%g' % v)

def custom_symbol(name, refpfx, desc, rect, pins, extra_props=None):
    """rect=(x1,y1,x2,y2); pins=[(num,name,x,y,angle,length,etype)]"""
    x1, y1, x2, y2 = rect
    bt = max(y1, y2); bb = min(y1, y2)
    body = [ '\t(symbol "%s"' % name,
             '\t\t(pin_names (offset 1.016))',
             '\t\t(exclude_from_sim no)',
             '\t\t(in_bom yes)',
             '\t\t(on_board yes)',
             '\t\t(property "Reference" "%s" (at %s %s 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)' % (refpfx, f(0), f(bt + 2.54)),
             '\t\t(property "Value" "%s" (at %s %s 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)' % (name, f(0), f(bb - 2.54)),
             '\t\t(property "Footprint" "" (at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)',
             '\t\t(property "Datasheet" "~" (at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)',
             '\t\t(property "Description" "%s" (at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)' % desc ]
    for p in (extra_props or []):
        body.append('\t\t(property "%s" "%s" (at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)' % p)
    body.append('\t\t(symbol "%s_0_1"' % name)
    body.append('\t\t\t(rectangle (start %s %s) (end %s %s)\n\t\t\t\t(stroke (width 0.254) (type default))\n\t\t\t\t(fill (type background))\n\t\t\t)' % (f(x1), f(bb), f(x2), f(bt)))
    body.append('\t\t)')
    body.append('\t\t(symbol "%s_1_1"' % name)
    for num, nm, px, py, a, ln, et in pins:
        body.append(_pin(num, nm, px, py, a, ln, et))
    body.append('\t\t)')
    body.append('\t)')
    return '\n'.join(body)

def build_custom_lib():
    """returns {name: text_with_plain_name} for .kicad_sym and fills k.CUSTOM"""
    lib = {}
    lib['MP1584_MOD'] = custom_symbol(
        'MP1584_MOD', 'U', 'MP1584 5.1V/3A step-down module (4-pad breakout)',
        (-7.62, -7.62, 7.62, 7.62),
        [('1', 'IN+', -10.16, 2.54, 0, 2.54, 'passive'),
         ('2', 'IN-', -10.16, -2.54, 0, 2.54, 'passive'),
         ('3', 'OUT+', 10.16, 2.54, 180, 2.54, 'passive'),
         ('4', 'OUT-', 10.16, -2.54, 180, 2.54, 'passive')])
    lib['POT_DUAL'] = custom_symbol(
        'POT_DUAL', 'RP', 'Dual-gang logarithmic potentiometer 10k (MASTER VOL)',
        (-7.62, -10.16, 7.62, 10.16),
        [('1', 'A1', -10.16, 7.62, 0, 2.54, 'passive'),
         ('3', 'A2', -10.16, 2.54, 0, 2.54, 'passive'),
         ('4', 'B1', -10.16, -2.54, 0, 2.54, 'passive'),
         ('6', 'B2', -10.16, -7.62, 0, 2.54, 'passive'),
         ('2', 'AW', 10.16, 7.62, 180, 2.54, 'passive'),
         ('5', 'BW', 10.16, -7.62, 180, 2.54, 'passive')])
    lib['PICO_DEBUG'] = custom_symbol(
        'PICO_DEBUG', 'J', 'Raspberry Pi Pico bottom SWD pads (DEBUG)',
        (-5.08, -5.08, 5.08, 5.08),
        [('1', 'SWDIO', 7.62, 2.54, 180, 2.54, 'passive'),
         ('2', 'SWCLK', 7.62, 0, 180, 2.54, 'passive'),
         ('3', 'GND', 7.62, -2.54, 180, 2.54, 'passive')])
    lib['74HCT125'] = custom_symbol(
        '74HCT125', 'U', 'Quad 3-state non-inverting buffer, TTL input (MIDI OUT driver)',
        (-10.16, -12.7, 10.16, 12.7),
        [('1', '1OE', -12.7, 10.16, 0, 2.54, 'input'),
         ('2', '1A', -12.7, 7.62, 0, 2.54, 'input'),
         ('3', '1Y', 12.7, 7.62, 180, 2.54, 'tri_state'),
         ('4', '2OE', -12.7, 5.08, 0, 2.54, 'input'),
         ('5', '2A', -12.7, 2.54, 0, 2.54, 'input'),
         ('6', '2Y', 12.7, 2.54, 180, 2.54, 'tri_state'),
         ('7', 'GND', 0, -15.24, 90, 2.54, 'power_in'),
         ('8', '3Y', 12.7, -2.54, 180, 2.54, 'tri_state'),
         ('9', '3A', -12.7, -2.54, 0, 2.54, 'input'),
         ('10', '3OE', -12.7, 0, 0, 2.54, 'input'),
         ('11', '4Y', 12.7, -7.62, 180, 2.54, 'tri_state'),
         ('12', '4A', -12.7, -5.08, 0, 2.54, 'input'),
         ('13', '4OE', -12.7, -7.62, 0, 2.54, 'input'),
         ('14', 'VCC', 0, 15.24, 270, 2.54, 'power_in')])
    # embedded copies (lib id = bukifon:NAME)
    for nm, txt in lib.items():
        emb = txt.replace('(symbol "%s"' % nm, '(symbol "bukifon:%s"' % nm, 1)
        k.CUSTOM[('bukifon', nm)] = emb
    return lib

# --------------------------------------------------------------------------
# footprints (draft; PCB layout is a later step)
# --------------------------------------------------------------------------
FP = {
 'R': 'Resistor_SMD:R_0805_2012Metric',
 'C': 'Capacitor_SMD:C_0805_2012Metric',
 'CP': 'Capacitor_SMD:CP_Elec_6.3x7.7',
 'L': 'Inductor_SMD:L_1210_3225Metric',
 'FB': 'Inductor_SMD:L_0805_2012Metric',
 'FUSE': 'Fuse:Fuse_1206_3216Metric',
 'DIODE': 'Diode_SMD:D_SMA',
 'BAT54S': 'Package_TO_SOT_SMD:SOT-23',
 'TO92': 'Package_TO_SOT_THT:TO-92_Inline',
 'SOT23': 'Package_TO_SOT_SMD:SOT-23',
 'DIP8': 'Package_DIP:DIP-8_W7.62mm',
 'DIP14': 'Package_DIP:DIP-14_W7.62mm',
 'DIP16': 'Package_DIP:DIP-16_W7.62mm',
 'SOIC14': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
 'MSOP10': 'Package_SO:MSOP-10_3x3mm_P0.5mm',
 'TSSOP20': 'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',
 'SOT235': 'Package_TO_SOT_SMD:SOT-23-5',
 'IDC26': 'Connector_IDC:IDC-Header_2x13_P2.54mm_Latch_Vertical',
 'IDC32': '',
 'TB12': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1-12-3.81_1x12_P3.81mm_Horizontal',
 'TB4': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1-4-3.81_1x04_P3.81mm_Horizontal',
 'SWD': 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
 'PICO': 'Module:RaspberryPi_Pico_SMD',
 'BARREL': '', 'JACK': '', 'POT': '', 'BTN': '', 'POWSW': '',
}

# --------------------------------------------------------------------------
# component table: (ref, lib, value, pin->net, footprint, note, section,
#                    unit, on_board)
# --------------------------------------------------------------------------
C = []
def add(ref, lib, val, nets, fp='', note='', sec='', unit=1, on_board=True):
    C.append(dict(ref=ref, lib=lib, val=val, nets=nets, fp=fp, note=note,
                  sec=sec, section=sec, unit=unit, on_board=on_board))

P = 'POWER'; D = 'DIGITAL'; A = 'AUDIO'; V = 'CV'; R = 'PORTS'; N = 'PANEL'

# ---- POWER ---------------------------------------------------------------
add('J14', ('Connector','Barrel_Jack'), 'DC 5.5/2.1 12V', {'1':'12V_J','2':'PGND'}, FP['BARREL'], 'внешний БП, не на CORE-1', P, on_board=False)
add('SW1', ('Switch','SW_SPST'), 'POWER', {'1':'12V_J','2':'12V_SW'}, FP['POWSW'], 'тумблер питания (задняя стенка), не на CORE-1', P, on_board=False)
add('F1', ('Device','Fuse'), '2A', {'1':'12V_SW','2':'12V_F'}, FP['FUSE'], '', P)
add('D2', ('Diode','SMAJ15A'), 'SMAJ15A', {'1':'12V_F','2':'PGND'}, FP['DIODE'], 'TVS 15V', P)
add('C1', ('Device','C_Polarized'), '1000uF/25V', {'1':'12V_F','2':'PGND'}, FP['CP'], '', P)
add('C2', ('Device','C'), '100nF/50V', {'1':'12V_F','2':'PGND'}, FP['C'], '', P)
add('D1', ('Diode','SS34'), 'SS34', {'1':'12V','2':'12V_F'}, FP['DIODE'], 'защита от переполюсовки', P)
add('C3', ('Device','C'), '100nF/50V', {'1':'12V','2':'PGND'}, FP['C'], '', P)
add('U1', ('bukifon','MP1584_MOD'), 'MP1584 5.1V/3A', {'1':'12V','2':'PGND','3':'5V','4':'PGND'}, '', 'модуль DC-DC', P)
add('C4', ('Device','C_Polarized'), '100uF/10V', {'1':'5V','2':'PGND'}, FP['CP'], '', P)
add('C5', ('Device','C'), '100nF/25V', {'1':'5V','2':'PGND'}, FP['C'], '', P)
add('U2', ('Regulator_Linear','AP2112K-3.3'), 'AP2112K-3.3', {'1':'5V','2':'DGND','3':'5V','4':'NC','5':'3V3'}, FP['SOT235'], 'LDO 3.3V 600mA', P)
add('C6', ('Device','C'), '1uF/10V', {'1':'5V','2':'DGND'}, FP['C'], '', P)
add('C7', ('Device','C'), '1uF/10V', {'1':'3V3','2':'DGND'}, FP['C'], '', P)
add('C8', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', P)
add('U3', ('Regulator_Switching','MC34063AP'), 'MC34063', {'1':'MC_A','2':'MC_SW','3':'MC_TC','4':'-12V','5':'MC_FB','6':'12V','7':'MC_A','8':'MC_A'}, FP['DIP8'], 'инвертор -12V', P)
add('R74', ('Device','R'), '0.33', {'1':'12V','2':'MC_A'}, FP['R'], 'токовый шунт', P)
add('C59', ('Device','C'), '1.5nF', {'1':'MC_TC','2':'-12V'}, FP['C'], '', P)
add('L1', ('Device','L'), '220uH/0.5A', {'1':'MC_SW','2':'-12V'}, FP['L'], '', P)
add('D3', ('Diode','SS34'), 'SS34', {'1':'MC_SW','2':'PGND'}, FP['DIODE'], '', P)
add('R75', ('Device','R'), '33k', {'1':'PGND','2':'MC_FB'}, FP['R'], '', P)
add('R76', ('Device','R'), '3.9k', {'1':'MC_FB','2':'-12V'}, FP['R'], '', P)
add('C9', ('Device','C_Polarized'), '220uF/25V', {'1':'PGND','2':'-12V'}, FP['CP'], 'полярность: + на PGND', P)
add('C10', ('Device','C'), '100nF/50V', {'1':'12V','2':'-12V'}, FP['C'], '', P)
add('C11', ('Device','C_Polarized'), '100uF/25V', {'1':'12V','2':'PGND'}, FP['CP'], '', P)
add('FB1', ('Device','FerriteBead'), '600R@100MHz', {'1':'12V','2':'12V_B'}, FP['FB'], '', P)
add('C12', ('Device','C_Polarized'), '100uF/25V', {'1':'12V_B','2':'PGND'}, FP['CP'], '', P)
add('FB2', ('Device','FerriteBead'), '600R@100MHz', {'1':'-12V','2':'-12V_B'}, FP['FB'], '', P)
add('C13', ('Device','C_Polarized'), '100uF/25V', {'1':'PGND','2':'-12V_B'}, FP['CP'], 'полярность: + на PGND', P)
add('FB3', ('Device','FerriteBead'), '600R@100MHz', {'1':'5V','2':'5V_B'}, FP['FB'], '', P)
add('C14', ('Device','C_Polarized'), '100uF/10V', {'1':'5V_B','2':'PGND'}, FP['CP'], '', P)
add('FB4', ('Device','FerriteBead'), '600R@100MHz', {'1':'3V3','2':'3V3_B'}, FP['FB'], '', P)
add('C15', ('Device','C'), '10uF/10V', {'1':'3V3_B','2':'DGND'}, FP['C'], '', P)
add('NT1', ('Device','NetTie_2'), 'AGND=DGND', {'1':'AGND','2':'DGND'}, 'NetTie:NetTie-2_SMD_Pad0.5mm', 'net-tie AGND-DGND (одна точка)', P)
add('NT2', ('Device','NetTie_2'), 'DGND=PGND', {'1':'DGND','2':'PGND'}, 'NetTie:NetTie-2_SMD_Pad0.5mm', 'net-tie DGND-PGND (одна точка)', P)

# ---- DIGITAL -------------------------------------------------------------
pico_nets = {
 '1':'UART_TX','2':'UART_RX','3':'DGND','4':'SPI_SCK','5':'SPI_MOSI','6':'SPI_MISO',
 '7':'ADC_CS','8':'DGND','9':'HC165_PL','10':'LED_G','11':'I2C_SDA','12':'I2C_SCL',
 '13':'DGND','14':'SPI1_SCK','15':'SPI1_MOSI','16':'LCD_CS','17':'LCD_DC','18':'DGND',
 '19':'LCD_RST','20':'LCD_BL_P','21':'I2S_BCK','22':'I2S_LRCK','23':'DGND','24':'I2S_DIN',
 '25':'PORT0_CS','26':'PORT1_CS','27':'PORT2_CS','28':'DGND','29':'GATE1_G','30':'RUN',
 '31':'GATE2_G','32':'DECK_ID','33':'AGND','34':'DECK_INT','35':'3V3','36':'NC',
 '37':'NC','38':'DGND','39':'VSYS','40':'NC'}
add('A1', ('MCU_Module','RaspberryPi_Pico'), 'Raspberry Pi Pico (RP2040)', pico_nets, FP['PICO'], 'SMD-пайка на кастеляцию, гребёнки опционально', D)
add('C16', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', D)
add('C17', ('Device','C'), '10uF/10V', {'1':'3V3','2':'DGND'}, FP['C'], '', D)
add('C18', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], 'ADC_VREF', D)
add('D4', ('Diode','SS34'), 'SS34', {'1':'VSYS','2':'5V'}, FP['DIODE'], 'VSYS через Шоттки', D)
add('C19', ('Device','C'), '10uF/10V', {'1':'VSYS','2':'DGND'}, FP['C'], '', D)
add('R1', ('Device','R'), '10k', {'1':'3V3','2':'RUN'}, FP['R'], 'pull-up RESET', D)
add('SW2', ('Switch','SW_Push'), 'RESET', {'1':'RUN','2':'DGND'}, FP['BTN'], 'кнопка RESET (задняя стенка), не на CORE-1', D, on_board=False)
add('C20', ('Device','C'), '100nF', {'1':'RUN','2':'DGND'}, FP['C'], '', D)
add('R2', ('Device','R'), '330', {'1':'LED_G','2':'LED_DATA'}, FP['R'], 'WS2812 data', D)
add('R3', ('Device','R'), '4.7k', {'1':'3V3','2':'I2C_SDA'}, FP['R'], 'I2C pull-up', D)
add('R4', ('Device','R'), '4.7k', {'1':'3V3','2':'I2C_SCL'}, FP['R'], 'I2C pull-up', D)
add('U4', ('Analog_DAC','MCP4728'), 'MCP4728A0-E/UN (0x60)', {'1':'3V3','2':'I2C_SCL','3':'I2C_SDA','4':'DGND','5':'NC','6':'DAC_A','7':'DAC_B','8':'DAC_C','9':'DAC_D','10':'AGND'}, FP['MSOP10'], '4x12bit I2C DAC, Vref 2.048V', D)
add('C21', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', D)
add('C22', ('Device','C'), '10uF/10V', {'1':'3V3','2':'AGND'}, FP['C'], '', D)
add('U5', ('Memory_EEPROM','24LC32'), '24LC32', {'1':'3V3','2':'3V3','3':'3V3','4':'DGND','5':'I2C_SDA','6':'I2C_SCL','7':'DGND','8':'3V3'}, FP['DIP8'], 'калибровка CV, адрес 0x57 (A2..A0=1)', D)
add('U16', ('Analog_DAC','MCP4728'), 'MCP4728A1-E/UN (0x61)', {'1':'3V3','2':'I2C_SCL','3':'I2C_SDA','4':'DGND','5':'NC','6':'DAC_E','7':'DAC_F','8':'NC','9':'NC','10':'AGND'}, FP['MSOP10'], 'MCP4728 #2 (CV OUT 1/2), адрес 0x61 (EEPROM)', D)
add('C60', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', D)
add('C61', ('Device','C'), '10uF/10V', {'1':'3V3','2':'AGND'}, FP['C'], '', D)
add('C23', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', D)
add('U6', ('Analog_ADC','MCP3208'), 'MCP3208', {'1':'SL1_ADC','2':'SL2_ADC','3':'CVIN1_ADC','4':'CVIN2_ADC','5':'AGND','6':'AGND','7':'FSR_ADC','8':'SYS_MON','9':'DGND','10':'ADC_CS','11':'SPI_MOSI','12':'SPI_MISO','13':'SPI_SCK','14':'AGND','15':'VREF33','16':'3V3'}, FP['DIP16'], '8x12bit SPI ADC', D)
add('FB5', ('Device','FerriteBead'), '600R@100MHz', {'1':'3V3','2':'VREF33'}, FP['FB'], '', D)
add('C24', ('Device','C'), '10uF/10V', {'1':'VREF33','2':'AGND'}, FP['C'], '', D)
add('C25', ('Device','C'), '100nF', {'1':'VREF33','2':'AGND'}, FP['C'], '', D)
add('C26', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', D)
add('U7', ('Isolator','6N137'), '6N137', {'1':'NC','2':'MIDI_A','3':'MIDI_IN_T','4':'NC','5':'DGND','6':'UART_RX','7':'5V','8':'5V'}, FP['DIP8'], 'оптрон MIDI IN', D)
add('R5', ('Device','R'), '220', {'1':'MIDI_IN_R','2':'MIDI_A'}, FP['R'], '', D)
add('R6', ('Device','R'), '4.7k', {'1':'3V3','2':'UART_RX'}, FP['R'], 'pull-up 6N137 (3.3V)', D)
add('U8', ('bukifon','74HCT125'), '74HCT125', {'1':'DGND','2':'UART_TX','3':'MIDI_DRV','4':'5V','5':'DGND','6':'NC','7':'DGND','8':'NC','9':'DGND','10':'5V','11':'NC','12':'DGND','13':'5V','14':'5V'}, FP['SOIC14'], 'MIDI OUT буфер', D)
add('R7', ('Device','R'), '33', {'1':'MIDI_DRV','2':'MIDI_OUT_T'}, FP['R'], '', D)
add('R8', ('Device','R'), '220', {'1':'5V','2':'MIDI_OUT_R'}, FP['R'], '', D)
add('Q1', ('Transistor_FET','2N7000'), '2N7000', {'1':'DGND','2':'G1','3':'GATE1'}, FP['TO92'], 'open-drain GATE1', D)
add('R9', ('Device','R'), '1k', {'1':'GATE1_G','2':'G1'}, FP['R'], '', D)
add('R10', ('Device','R'), '100k', {'1':'G1','2':'DGND'}, FP['R'], '', D)
add('R11', ('Device','R'), '4.7k', {'1':'5V_B','2':'GATE1'}, FP['R'], 'pull-up GATE1', D)
add('Q2', ('Transistor_FET','2N7000'), '2N7000', {'1':'DGND','2':'G2','3':'GATE2'}, FP['TO92'], 'open-drain GATE2', D)
add('R12', ('Device','R'), '1k', {'1':'GATE2_G','2':'G2'}, FP['R'], '', D)
add('R13', ('Device','R'), '100k', {'1':'G2','2':'DGND'}, FP['R'], '', D)
add('R14', ('Device','R'), '4.7k', {'1':'5V_B','2':'GATE2'}, FP['R'], 'pull-up GATE2', D)
add('Q3', ('Transistor_FET','2N7002'), '2N7002', {'1':'LCD_BL_G','2':'DGND','3':'LCD_BL'}, FP['SOT23'], 'ключ подсветки LCD', D)
add('R15', ('Device','R'), '1k', {'1':'LCD_BL_P','2':'LCD_BL_G'}, FP['R'], '', D)
add('R16', ('Device','R'), '100k', {'1':'LCD_BL_G','2':'DGND'}, FP['R'], '', D)

# ---- AUDIO ---------------------------------------------------------------
add('U9', ('Audio','PCM5102A'), 'PCM5102A', {'1':'3V3','2':'CP_P','3':'AGND','4':'CP_M','5':'VNEG','6':'DAC_L','7':'DAC_R','8':'3V3','9':'AGND','10':'DGND','11':'DGND','12':'DGND','13':'I2S_BCK','14':'I2S_DIN','15':'I2S_LRCK','16':'DGND','17':'XSMT','18':'LDOO','19':'DGND','20':'3V3'}, FP['TSSOP20'], 'I2S ЦАП 112dB', A)
add('C27', ('Device','C'), '1uF/10V', {'1':'CP_P','2':'CP_M'}, FP['C'], 'charge-pump flying cap', A)
add('C28', ('Device','C_Polarized'), '1uF/10V', {'1':'AGND','2':'VNEG'}, FP['CP'], 'полярность: + на AGND', A)
add('C29', ('Device','C'), '100nF', {'1':'LDOO','2':'AGND'}, FP['C'], '', A)
add('C30', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', A)
add('C31', ('Device','C'), '100nF', {'1':'3V3','2':'DGND'}, FP['C'], '', A)
add('C32', ('Device','C'), '100nF', {'1':'3V3','2':'AGND'}, FP['C'], '', A)
add('C33', ('Device','C'), '10uF/10V', {'1':'3V3','2':'AGND'}, FP['C'], '', A)
add('R17', ('Device','R'), '10k', {'1':'3V3','2':'XSMT'}, FP['R'], 'unmute', A)
add('C34', ('Device','C'), '100nF', {'1':'XSMT','2':'AGND'}, FP['C'], '', A)
add('C35', ('Device','C_Polarized'), '10uF/16V', {'1':'DAC_L','2':'AUD_L_IN'}, FP['CP'], 'AC-развязка L', A)
add('C36', ('Device','C_Polarized'), '10uF/16V', {'1':'DAC_R','2':'AUD_R_IN'}, FP['CP'], 'AC-развязка R', A)
add('R18', ('Device','R'), '10k', {'1':'AUD_L_IN','2':'SUML'}, FP['R'], '', A)
add('R19', ('Device','R'), '10k', {'1':'AUD_R_IN','2':'SUMR'}, FP['R'], '', A)
for i in range(3):
    add('R%d' % (20+i), ('Device','R'), '1k', {'1':'AUD_P%d' % i, '2':'AUDC%d' % i}, FP['R'], 'защита аудиовхода порта %d' % i, A)
    add('D%d' % (5+i), ('Diode','BAT54S'), 'BAT54S', {'1':'-12V','2':'12V','3':'AUDC%d' % i}, FP['BAT54S'], 'клэмп ±12V', A)
    add('C%d' % (37+i), ('Device','C'), '100pF', {'1':'AUDC%d' % i,'2':'AGND'}, FP['C'], '', A)
    add('R%d' % (23+2*i), ('Device','R'), '22k', {'1':'AUDC%d' % i,'2':'SUML'}, FP['R'], '', A)
    add('R%d' % (24+2*i), ('Device','R'), '22k', {'1':'AUDC%d' % i,'2':'SUMR'}, FP['R'], '', A)
# U10 TL074 audio
add('U10', ('Amplifier_Operational','TL074'), 'TL074', {'1':'AUDL_SUM','2':'SUML','3':'AGND'}, FP['DIP14'], 'сумматор L', A, unit=1)
add('U10', ('Amplifier_Operational','TL074'), 'TL074', {'7':'AUDR_SUM','6':'SUMR','5':'AGND'}, FP['DIP14'], 'сумматор R', A, unit=2)
add('U10', ('Amplifier_Operational','TL074'), 'TL074', {'8':'AUDIN_B','9':'AUDIN_B','10':'AUDIN_D'}, FP['DIP14'], 'буфер AUD_IN x0.5', A, unit=3)
add('U10', ('Amplifier_Operational','TL074'), 'TL074', {'14':'SPARE_A','13':'SPARE_A','12':'AGND'}, FP['DIP14'], 'резервный ОУ (заземлён)', A, unit=4)
add('U10', ('Amplifier_Operational','TL074'), 'TL074', {'4':'12V','11':'-12V'}, FP['DIP14'], 'питание', A, unit=5)
add('R70', ('Device','R'), '22k', {'1':'AUDL_SUM','2':'SUML'}, FP['R'], 'Rf сумматора L', A)
add('R71', ('Device','R'), '22k', {'1':'AUDR_SUM','2':'SUMR'}, FP['R'], 'Rf сумматора R', A)
add('C40', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', A)
add('C41', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', A)
add('C42', ('Device','C_Polarized'), '10uF/16V', {'1':'DAC_L','2':'AUDIN_C'}, FP['CP'], 'AUD_IN из DAC L', A)
add('R72', ('Device','R'), '10k', {'1':'AUDIN_C','2':'AUDIN_D'}, FP['R'], 'делитель x0.5', A)
add('R73', ('Device','R'), '10k', {'1':'AUDIN_D','2':'AGND'}, FP['R'], 'делитель x0.5', A)
add('R29', ('Device','R'), '1k', {'1':'AUDIN_B','2':'AUD_IN'}, FP['R'], 'выход AUD_IN на шину', A)
add('RP1', ('bukifon','POT_DUAL'), '10k log dual', {'1':'AUDL_SUM','3':'AGND','2':'AUDL_POT','4':'AUDR_SUM','6':'AGND','5':'AUDR_POT'}, FP['POT'], 'MASTER VOL (задняя стенка), не на CORE-1', A, on_board=False)
add('U11', ('Amplifier_Operational','TL072'), 'TL072', {'1':'AUDL_BUF','2':'AUDL_BUF','3':'AUDL_POT'}, FP['DIP8'], 'буфер L', A, unit=1)
add('U11', ('Amplifier_Operational','TL072'), 'TL072', {'7':'AUDR_BUF','6':'AUDR_BUF','5':'AUDR_POT'}, FP['DIP8'], 'буфер R', A, unit=2)
add('U11', ('Amplifier_Operational','TL072'), 'TL072', {'8':'12V','4':'-12V'}, FP['DIP8'], 'питание', A, unit=3)
add('C43', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', A)
add('C44', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', A)
add('R30', ('Device','R'), '100', {'1':'AUDL_BUF','2':'AUDL_OUT'}, FP['R'], '', A)
add('R31', ('Device','R'), '100', {'1':'AUDR_BUF','2':'AUDR_OUT'}, FP['R'], '', A)
add('C45', ('Device','C'), '100pF', {'1':'AUDL_OUT','2':'AGND'}, FP['C'], '', A)
add('C46', ('Device','C'), '100pF', {'1':'AUDR_OUT','2':'AGND'}, FP['C'], '', A)
add('J1', ('Connector_Audio','AudioJack3'), 'LINE OUT 3.5mm stereo', {'T':'AUDL_OUT','R':'AUDR_OUT','S':'AGND'}, FP['JACK'], 'панельный джек, к клеммнику TB1', A, on_board=False)
add('J2', ('Connector_Audio','AudioJack3'), 'PHONES 3.5mm stereo', {'T':'AUDL_OUT','R':'AUDR_OUT','S':'AGND'}, FP['JACK'], 'панельный джек, к клеммнику TB1', A, on_board=False)

# ---- CV ------------------------------------------------------------------
# TL074 #1: four x4.9 non-inverting CV output buffers + power unit
add('U12', ('Amplifier_Operational','TL074'), 'TL074', {'1':'CVR0','2':'CVS0','3':'DAC_A'}, FP['DIP14'], 'буфер CV1 x4.9', V, unit=1)
add('U12', ('Amplifier_Operational','TL074'), 'TL074', {'7':'CVR1','6':'CVS1','5':'DAC_B'}, FP['DIP14'], 'буфер CV2 x4.9', V, unit=2)
add('U12', ('Amplifier_Operational','TL074'), 'TL074', {'8':'CVR2','9':'CVS2','10':'DAC_C'}, FP['DIP14'], 'буфер CV3 x4.9', V, unit=3)
add('U12', ('Amplifier_Operational','TL074'), 'TL074', {'14':'CVR3','13':'CVS3','12':'DAC_D'}, FP['DIP14'], 'буфер CV4 x4.9', V, unit=4)
add('U12', ('Amplifier_Operational','TL074'), 'TL074', {'4':'12V','11':'-12V'}, FP['DIP14'], 'питание', V, unit=5)
for i in range(4):
    add('R%d' % (32+i), ('Device','R'), '39k', {'1':'CVS%d'%i,'2':'CVR%d'%i}, FP['R'], 'Rf CV%d x4.9' % (i+1), V)
    add('R%d' % (36+i), ('Device','R'), '10k', {'1':'CVS%d'%i,'2':'AGND'}, FP['R'], 'Rg CV%d x4.9' % (i+1), V)
    add('R%d' % (40+i), ('Device','R'), '1k', {'1':'CVR%d'%i,'2':'CV%d'%(i+1)}, FP['R'], 'выход CV%d' % (i+1), V)
    add('D%d' % (9+i), ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'12V','3':'CV%d'%(i+1)}, FP['BAT54S'], 'защита CV%d' % (i+1), V)
# TL074 #2: CV IN level shift
add('U13', ('Amplifier_Operational','TL074'), 'TL074', {'1':'CVIN1_RAW','2':'CVIN1_N','3':'CVREF_B'}, FP['DIP14'], 'CV IN1 сдвиг 1.65В', V, unit=1)
add('U13', ('Amplifier_Operational','TL074'), 'TL074', {'7':'CVIN2_RAW','6':'CVIN2_N','5':'CVREF_B'}, FP['DIP14'], 'CV IN2 сдвиг 1.65В', V, unit=2)
add('U13', ('Amplifier_Operational','TL074'), 'TL074', {'8':'CVREF_B','9':'CVREF_B','10':'CVREF'}, FP['DIP14'], 'буфер 1.65В', V, unit=3)
add('U13', ('Amplifier_Operational','TL074'), 'TL074', {'14':'SPARE_B','13':'SPARE_B','12':'AGND'}, FP['DIP14'], 'резервный ОУ (заземлён)', V, unit=4)
add('U13', ('Amplifier_Operational','TL074'), 'TL074', {'4':'12V','11':'-12V'}, FP['DIP14'], 'питание', V, unit=5)
# TL074 #3: CV OUT 5/6 buffers (second MCP4728 channels A/B) + spare units
add('U17', ('Amplifier_Operational','TL074'), 'TL074', {'1':'CVR4','2':'CVS4','3':'DAC_E'}, FP['DIP14'], 'буфер CV5 x4.9', V, unit=1)
add('U17', ('Amplifier_Operational','TL074'), 'TL074', {'7':'CVR5','6':'CVS5','5':'DAC_F'}, FP['DIP14'], 'буфер CV6 x4.9', V, unit=2)
add('U17', ('Amplifier_Operational','TL074'), 'TL074', {'8':'SPARE_C','9':'SPARE_C','10':'AGND'}, FP['DIP14'], 'резервный ОУ (заземлён)', V, unit=3)
add('U17', ('Amplifier_Operational','TL074'), 'TL074', {'14':'SPARE_D','13':'SPARE_D','12':'AGND'}, FP['DIP14'], 'резервный ОУ (заземлён)', V, unit=4)
add('U17', ('Amplifier_Operational','TL074'), 'TL074', {'4':'12V','11':'-12V'}, FP['DIP14'], 'питание', V, unit=5)
add('R77', ('Device','R'), '39k', {'1':'CVS4','2':'CVR4'}, FP['R'], 'Rf CV5 x4.9', V)
add('R78', ('Device','R'), '39k', {'1':'CVS5','2':'CVR5'}, FP['R'], 'Rf CV6 x4.9', V)
add('R79', ('Device','R'), '10k', {'1':'CVS4','2':'AGND'}, FP['R'], 'Rg CV5 x4.9', V)
add('R80', ('Device','R'), '10k', {'1':'CVS5','2':'AGND'}, FP['R'], 'Rg CV6 x4.9', V)
add('R81', ('Device','R'), '1k', {'1':'CVR4','2':'CV5'}, FP['R'], 'выход CV5 (джек CV OUT 1)', V)
add('R82', ('Device','R'), '1k', {'1':'CVR5','2':'CV6'}, FP['R'], 'выход CV6 (джек CV OUT 2)', V)
add('D17', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'12V','3':'CV5'}, FP['BAT54S'], 'защита CV5', V)
add('D18', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'12V','3':'CV6'}, FP['BAT54S'], 'защита CV6', V)
add('C62', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', V)
add('C63', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', V)
add('J5', ('Connector_Audio','AudioJack2'), 'CV OUT 1 (CV5)', {'T':'CV5','S':'AGND'}, FP['JACK'], 'панельный джек', V, on_board=False)
add('J6', ('Connector_Audio','AudioJack2'), 'CV OUT 2 (CV6)', {'T':'CV6','S':'AGND'}, FP['JACK'], 'панельный джек', V, on_board=False)
add('R44', ('Device','R'), '100k', {'1':'CVIN1_IN','2':'CVIN1_N'}, FP['R'], '', V)
add('R45', ('Device','R'), '16.5k', {'1':'CVIN1_N','2':'CVIN1_RAW'}, FP['R'], 'Rf, gain 0.165', V)
add('R46', ('Device','R'), '100k', {'1':'CVIN2_IN','2':'CVIN2_N'}, FP['R'], '', V)
add('R47', ('Device','R'), '16.5k', {'1':'CVIN2_N','2':'CVIN2_RAW'}, FP['R'], 'Rf, gain 0.165', V)
add('R48', ('Device','R'), '1k', {'1':'CVIN1_RAW','2':'CVIN1_ADC'}, FP['R'], '', V)
add('R49', ('Device','R'), '1k', {'1':'CVIN2_RAW','2':'CVIN2_ADC'}, FP['R'], '', V)
add('C47', ('Device','C'), '100nF', {'1':'CVIN1_ADC','2':'AGND'}, FP['C'], '', V)
add('C48', ('Device','C'), '100nF', {'1':'CVIN2_ADC','2':'AGND'}, FP['C'], '', V)
add('D13', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'3V3','3':'CVIN1_ADC'}, FP['BAT54S'], '', V)
add('D14', ('Diode','BAT54S'), 'BAT54S', {'1':'AGND','2':'3V3','3':'CVIN2_ADC'}, FP['BAT54S'], '', V)
add('R50', ('Device','R'), '47k', {'1':'3V3','2':'CVREF'}, FP['R'], '1.65V', V)
add('R51', ('Device','R'), '47k', {'1':'CVREF','2':'AGND'}, FP['R'], '1.65V', V)
add('C49', ('Device','C'), '100nF', {'1':'CVREF','2':'AGND'}, FP['C'], '', V)
add('C50', ('Device','C'), '100nF', {'1':'12V','2':'AGND'}, FP['C'], '', V)
add('C51', ('Device','C'), '100nF', {'1':'-12V','2':'AGND'}, FP['C'], '', V)
add('R64', ('Device','R'), '1k', {'1':'SL1_IN','2':'SL1_ADC'}, FP['R'], '', V)
add('C54', ('Device','C'), '100nF', {'1':'SL1_ADC','2':'AGND'}, FP['C'], '', V)
add('R65', ('Device','R'), '1k', {'1':'SL2_IN','2':'SL2_ADC'}, FP['R'], '', V)
add('C55', ('Device','C'), '100nF', {'1':'SL2_ADC','2':'AGND'}, FP['C'], '', V)
add('R66', ('Device','R'), '1k', {'1':'FSR_IN','2':'FSR_ADC'}, FP['R'], '', V)
add('C56', ('Device','C'), '100nF', {'1':'FSR_ADC','2':'AGND'}, FP['C'], '', V)
add('R67', ('Device','R'), '12k', {'1':'5V','2':'SYS_MON'}, FP['R'], '+5V делитель', V)
add('R68', ('Device','R'), '18k', {'1':'SYS_MON','2':'AGND'}, FP['R'], '+5V делитель', V)
add('C57', ('Device','C'), '100nF', {'1':'SYS_MON','2':'AGND'}, FP['C'], '', V)
add('R69', ('Device','R'), '1k', {'1':'DECK_ID_IN','2':'DECK_ID'}, FP['R'], '', V)
add('C58', ('Device','C'), '100nF', {'1':'DECK_ID','2':'AGND'}, FP['C'], '', V)
add('J7', ('Connector_Audio','AudioJack2'), 'CV IN 1', {'T':'CVIN1_IN','S':'AGND'}, FP['JACK'], 'панельный джек', V, on_board=False)
add('J8', ('Connector_Audio','AudioJack2'), 'CV IN 2', {'T':'CVIN2_IN','S':'AGND'}, FP['JACK'], 'панельный джек', V, on_board=False)
add('J9', ('Connector_Audio','AudioJack2'), 'GATE 1', {'T':'GATE1','S':'AGND'}, FP['JACK'], 'панельный джек', V, on_board=False)
add('J10', ('Connector_Audio','AudioJack2'), 'GATE 2', {'T':'GATE2','S':'AGND'}, FP['JACK'], 'панельный джек', V, on_board=False)
add('J11', ('Connector_Audio','AudioJack3'), 'MIDI IN (TRS-A)', {'T':'MIDI_IN_T','R':'MIDI_IN_R','S':'DGND'}, FP['JACK'], 'панельный джек', V, on_board=False)
add('J12', ('Connector_Audio','AudioJack3'), 'MIDI OUT (TRS-A)', {'T':'MIDI_OUT_T','R':'MIDI_OUT_R','S':'DGND'}, FP['JACK'], 'панельный джек', V, on_board=False)

# ---- PORTS ---------------------------------------------------------------
for i in range(3):
    nets = {
     '1':'12V_B','2':'DGND','3':'-12V_B','4':'DGND','5':'5V_B','6':'DGND',
     '7':'3V3_B','8':'DGND','9':'CV1','10':'AGND','11':'CV2','12':'AGND',
     '13':'CV3','14':'AGND','15':'CV4','16':'AGND',
     '17':'GATE1','18':'GATE2','19':'AUD_IN','20':'AUD_P%d'%i,
     '21':'I2C_SDA','22':'I2C_SCL','23':'SPI_SCK','24':'SPI_MOSI','25':'SPI_MISO',
     '26':'PORT%d_CS'%i}
    add('P%d'%(i+1), ('Connector_Generic','Conn_02x13_Odd_Even'), 'Bukifon Bus IDC-26 PORT%d'%(i+1), nets, FP['IDC26'], 'порт %d'%(i+1), R)

# ---- PANEL / TERMINALS ---------------------------------------------------
jp = {'1':'3V3','2':'DGND','3':'SPI1_SCK','4':'DGND','5':'SPI1_MOSI','6':'DGND',
      '7':'LCD_CS','8':'DGND','9':'LCD_DC','10':'LCD_RST','11':'LCD_BL','12':'DGND',
      '13':'SPI_SCK','14':'DGND','15':'SPI_MISO','16':'DGND','17':'HC165_PL','18':'DGND',
      '19':'DECK_INT','20':'LED_DATA','21':'I2C_SDA','22':'I2C_SCL','23':'5V','24':'DGND',
      '25':'SL1_IN','26':'AGND','27':'SL2_IN','28':'AGND','29':'FSR_IN','30':'AGND',
      '31':'DECK_ID_IN','32':'DGND'}
add('J15', ('Connector_Generic','Conn_02x16_Odd_Even'), 'IDC-32 to PANEL-1', jp, FP['IDC32'], 'шлейф 15 см', N)
tb1 = {'1':'AUDL_OUT','2':'AUDR_OUT','3':'AGND','4':'AUDL_OUT','5':'AUDR_OUT','6':'AGND',
       '7':'CV5','8':'AGND','9':'CV6','10':'AGND','11':'CVIN1_IN','12':'AGND'}
add('TB1', ('Connector_Generic','Conn_01x12'), 'Jacks: LINE/PHONES/CV1/CV2/CVIN1', tb1, FP['TB12'], 'клеммник 3.81 мм', N)
tb2 = {'1':'CVIN2_IN','2':'AGND','3':'GATE1','4':'AGND','5':'GATE2','6':'AGND',
       '7':'MIDI_IN_T','8':'MIDI_IN_R','9':'DGND','10':'MIDI_OUT_T','11':'MIDI_OUT_R','12':'DGND'}
add('TB2', ('Connector_Generic','Conn_01x12'), 'Jacks: CVIN2/GATE/MIDI', tb2, FP['TB12'], 'клеммник 3.81 мм', N)
add('J16', ('Connector_Generic','Conn_01x03'), 'SWD', {'1':'SWDIO','2':'SWCLK','3':'DGND'}, FP['SWD'], 'SWD 1x3', N)
add('J13', ('bukifon','PICO_DEBUG'), 'Pico SWD pads', {'1':'SWDIO','2':'SWCLK','3':'DGND'}, '', 'контактные площадки Pico (DEBUG)', N)

# --------------------------------------------------------------------------
# PWR_FLAG net drivers (nets carrying power_in pins but no power_out source)
# --------------------------------------------------------------------------
FLAGS = ['5V', '12V', '-12V', 'VSYS', 'VREF33']

# --------------------------------------------------------------------------
# layout helpers
# --------------------------------------------------------------------------
def pin_span(lib, unit):
    ps = [p for p in k.pins(*lib) if p[6] in (0, unit)]
    if not ps: return []
    return ps

def comp_size(lib, unit):
    ps = pin_span(lib, unit)
    xs = [p[2] for p in ps]; ys = [p[3] for p in ps]
    left = any(p[4] == 0 for p in ps); right = any(p[4] == 180 for p in ps)
    top = any(p[4] == 270 for p in ps); bot = any(p[4] == 90 for p in ps)
    w = (max(xs) - min(xs)) if ps else 0
    h = (max(ys) - min(ys)) if ps else 0
    w += (LABEL_PAD if left else 0) + (LABEL_PAD if right else 0)
    h += 4.0 if (top or bot) else 0.0
    if top and bot: h += 4.0
    wslots = max(1, int(math.ceil(w / SW)))
    hslots = max(1, int(math.ceil(h / SH)))
    return wslots, hslots

class Section:
    def __init__(self, sch, name, x0, y0, cols=6):
        self.sch = sch; self.name = name; self.x0 = x0; self.y0 = y0
        self.cols = cols; self.col = 0; self.row = 0; self.shelf = 0
        self.placed = []
        sch.text(name, (x0, y0 - 3.0), size=4.0)
    def place(self, comp, unit=1):
        w, h = comp_size(comp['lib'], unit)
        if self.col + w > self.cols:
            self.col = 0; self.row += self.shelf; self.shelf = 0
        x = self.x0 + (self.col + w/2.0) * SW
        y = self.y0 + 12.0 + (self.row + h/2.0) * SH
        c = self.sch.sym(comp['lib'][0], comp['lib'][1], comp['ref'], comp['val'],
                         x, y, footprint=comp['fp'], unit=unit,
                         on_board=comp['on_board'],
                         ref_off=(-w*SW/2 + 4, -h*SH/2 + 3.0),
                         val_off=(-w*SW/2 + 4, -h*SH/2 + 6.0))
        c['note'] = comp['note']; c['section'] = comp['section']
        self.placed.append((c, unit))
        self.shelf = max(self.shelf, h); self.col += w
        return c
    def end_y(self):
        return self.y0 + 12.0 + (self.row + self.shelf) * SH

def make_schematic():
    sch = k.Sch(os.path.join(HERE, PROJECT + '.kicad_sch'),
                'Bukifon CORE-1', paper=PAPER, project=PROJECT)
    sections = {}
    # column A: POWER, CV ; column B: DIGITAL, PANEL ; column C: AUDIO, PORTS
    colA, colB, colC = 22.0, 407.0, 792.0
    top = 34.0
    sec_power = Section(sch, 'POWER: 12V input, +5.1V, +3.3V, -12V, filters, star GND', colA, top)
    sec_digital = Section(sch, 'DIGITAL: Pico, I2C DAC/EEPROM, SPI ADC, MIDI, gates', colB, top)
    sec_audio = Section(sch, 'AUDIO: PCM5102A, TL074 summer, MASTER VOL, TL072, LINE/PHONES', colC, top)
    sections['POWER'] = sec_power; sections['DIGITAL'] = sec_digital; sections['AUDIO'] = sec_audio

    # place in component-table order grouped by section
    comps = {}
    for comp in C:
        if comp['sec'] not in sections:
            continue
        sec = sections[comp['sec']]
        c = sec.place(comp, unit=comp['unit'])
        comps.setdefault(comp['ref'], []).append((c, comp))

    # next sections stacked in each column
    sec_cv = Section(sch, 'CV: MCP4728 buffers x4.9 (TL074), CV IN +/-10V level shift', colA, sec_power.end_y() + 12.0)
    sec_panel = Section(sch, 'PANEL/TERMINALS: IDC-32, jack terminal blocks, SWD', colB, sec_digital.end_y() + 12.0)
    sec_ports = Section(sch, 'PORTS: P0/P1/P2 (IDC-26) Bukifon bus', colC, sec_audio.end_y() + 12.0)
    sections['CV'] = sec_cv; sections['PANEL'] = sec_panel; sections['PORTS'] = sec_ports
    for comp in C:
        if comp['sec'] in ('CV', 'PANEL', 'PORTS'):
            c = sections[comp['sec']].place(comp, unit=comp['unit'])
            comps.setdefault(comp['ref'], []).append((c, comp))

    # PWR_FLAG drivers
    fy = sec_panel.end_y() + 14.0
    sch.text('POWER FLAGS (net drivers for ERC)', (sec_panel.x0, fy - 4), size=3.0)
    flags = []
    for i, net in enumerate(FLAGS):
        fx = sec_panel.x0 + (i % 4) * 20.0
        fyy = fy + 10.0 + (i // 4) * 20.0
        fc = sch.sym('power', 'PWR_FLAG', '#FLG%02d' % (i+1), 'PWR_FLAG', fx, fyy,
                     hide_ref=True, ref_off=(2, -3), val_off=(2, 3))
        sch.net(fc, net, num='1')
        flags.append(fc)

    # ---- wire all pins by labels
    for ref, lst in comps.items():
        for c, comp in lst:
            unit = comp['unit']
            unit_pins = [p for p in k.pins(*comp['lib']) if p[6] in (0, unit)]
            for p in unit_pins:
                num, nam = p[0], p[1]
                net = comp['nets'].get(num)
                if net is None:
                    continue
                if net == 'NC':
                    sch.nc_pin(c, num=num)
                else:
                    sch.net(c, net, num=num)
    # explicitly requested no-connects
    for ref, lst in comps.items():
        for c, comp in lst:
            unit = comp['unit']
            for p in [p for p in k.pins(*comp['lib']) if p[6] in (0, unit)]:
                if p[0] not in comp['nets']:
                    sch.nc_pin(c, num=p[0])
    sch.write()
    return sch, comps, sections

# --------------------------------------------------------------------------
# export + reports
# --------------------------------------------------------------------------
def run(cmd, **kw):
    print('+', ' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.stdout.strip(): print(r.stdout.strip()[:2000])
    if r.returncode != 0:
        print('STDERR:', r.stderr.strip()[:3000])
    return r

def exports():
    schfile = os.path.join(HERE, PROJECT + '.kicad_sch')
    os.makedirs(os.path.join(HERE, 'erc'), exist_ok=True)
    run([KICAD_CLI, 'sch', 'erc', '--severity-all', '--format', 'report',
         '-o', os.path.join(HERE, 'erc', 'erc.rpt'), schfile])
    run([KICAD_CLI, 'sch', 'erc', '--severity-all', '--format', 'json',
         '-o', os.path.join(HERE, 'erc', 'erc.json'), schfile])
    run([KICAD_CLI, 'sch', 'export', 'pdf', '-o', os.path.join(HERE, PROJECT + '.pdf'), schfile])
    run([KICAD_CLI, 'sch', 'export', 'svg', '--output', os.path.join(HERE, 'svg'), schfile])
    import shutil
    src = os.path.join(HERE, 'svg', PROJECT + '.svg')
    if os.path.exists(src):
        shutil.copy(src, os.path.join(HERE, PROJECT + '.svg'))
    run([KICAD_CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
         '-o', os.path.join(HERE, 'netlist.net'), schfile])
    run([KICAD_CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml',
         '-o', os.path.join(HERE, 'netlist.xml'), schfile])

def parse_erc():
    p = os.path.join(HERE, 'erc', 'erc.rpt')
    if not os.path.exists(p): return None
    txt = open(p, encoding='utf-8').read()
    import re
    m = re.search(r'Errors (\d+)\s+Warnings (\d+)', txt)
    return {'errors': int(m.group(1)) if m else -1,
            'warnings': int(m.group(2)) if m else -1, 'text': txt}


# --------------------------------------------------------------------------
# BOM + documentation generation (from the same component table as schematic)
# --------------------------------------------------------------------------
SPEC_NAMES = {
 'J14': 'J-DC', 'J15': 'J-PANEL', 'J16': 'HDR-EXT',
 'R74': 'Rsc', 'C59': 'Ct', 'R75': 'Rfb1', 'R76': 'Rfb2',
}
PORT_SIG = {  # Bukifon Bus pin -> (signal, direction)
 1:'+12V', 2:'GND', 3:'-12V', 4:'GND', 5:'+5V', 6:'GND', 7:'+3V3', 8:'GND',
 9:'CV1', 10:'GND', 11:'CV2', 12:'GND', 13:'CV3', 14:'GND', 15:'CV4', 16:'GND',
 17:'GATE1', 18:'GATE2', 19:'AUD_IN', 20:'AUD_OUT', 21:'SDA', 22:'SCL', 23:'SCK',
 24:'MOSI', 25:'MISO', 26:'CS'}
PORT_DIR = {1:'пит.',2:'',3:'пит.',4:'',5:'пит.',6:'',7:'пит.',8:'',9:'core→mod',10:'',
 11:'core→mod',12:'',13:'core→mod',14:'',15:'core→mod',16:'',17:'core→mod',
 18:'core→mod',19:'core→mod',20:'mod→core',21:'I2C',22:'I2C',23:'SPI0',24:'SPI0',
 25:'SPI0',26:'core→mod/CS'}
PANEL32 = [  # J15 IDC-32 pin -> function
 (1,'+3V3','питание PANEL'), (2,'DGND',''), (3,'SPI1_SCK','GP10'), (4,'DGND',''),
 (5,'SPI1_MOSI','GP11'), (6,'DGND',''), (7,'LCD_CS','GP12'), (8,'DGND',''),
 (9,'LCD_DC','GP13'), (10,'LCD_RST','GP14'), (11,'LCD_BL','GP15 через 2N7002 Q3'),
 (12,'DGND',''), (13,'SPI_SCK','GP2 (HC165 CP + MCP3208)'), (14,'DGND',''),
 (15,'SPI_MISO','GP4 (HC165 QH + MCP3208 DOUT)'), (16,'DGND',''),
 (17,'HC165_PL','GP6'), (18,'DGND',''), (19,'DECK_INT','GP28 (MCP23017 INTA)'), (20,'LED_DATA','GP7 через 330R'),
 (21,'I2C_SDA','GP8'), (22,'I2C_SCL','GP9'), (23,'+5V','питание PANEL'),
 (24,'DGND',''), (25,'SL1_IN','→ MCP3208 CH0'), (26,'AGND',''),
 (27,'SL2_IN','→ MCP3208 CH1'), (28,'AGND',''), (29,'FSR_IN','→ MCP3208 CH6'),
 (30,'AGND',''), (31,'DECK_ID_IN','GP27 через 1k'), (32,'DGND','')]
MCP3208_MAP = [('CH0','SL1_ADC','слайдер SL1 (PANEL-1 / DECK)'),
 ('CH1','SL2_ADC','слайдер SL2'), ('CH2','CVIN1_ADC','CV IN 1 (джек J7)'),
 ('CH3','CVIN2_ADC','CV IN 2 (джек J8)'), ('CH4','AGND','резерв (притянут к AGND)'),
 ('CH5','AGND','резерв (притянут к AGND)'), ('CH6','FSR_ADC','FSR / deck velocity'),
 ('CH7','SYS_MON','+5V делитель 12k/18k')]
MPN = {'U4': 'MCP4728A0-E/UN', 'U16': 'MCP4728A1-E/UN'}
MCP4728_MAP = [('U4 (0x60)','CHA','DAC_A','CV1 (шина P0/P1/P2 pin 9)'),
 ('U4 (0x60)','CHB','DAC_B','CV2 (шина pin 11)'), ('U4 (0x60)','CHC','DAC_C','CV3 (шина pin 13)'),
 ('U4 (0x60)','CHD','DAC_D','CV4 (шина pin 15)'),
 ('U16 (0x61)','CHA','DAC_E','CV5 (джек CV OUT 1)'),
 ('U16 (0x61)','CHB','DAC_F','CV6 (джек CV OUT 2)')]

def _refkey(r):
    import re
    m = re.match(r'([A-Za-z#]+)(\d*)', r)
    return (m.group(1), int(m.group(2) or 0), r)

def _natural(refs):
    return sorted(refs, key=_refkey)

def write_bom():
    groups = {}
    seen = set()
    offboard = {}
    for c in C:
        if c['ref'] in seen:
            continue
        seen.add(c['ref'])
        key = (c['val'], c['fp'], c['note'])
        groups.setdefault(key, []).append(c['ref'])
        offboard[c['ref']] = not c['on_board']
    rows = []
    n = 0
    for (val, fp, note), refs in groups.items():
        n += 1
        refs = _natural(refs)
        off = all(offboard[r] for r in refs)
        nm = []
        if off:
            nm.append('не на CORE-1 (панельный разъём)')
        spec = [SPEC_NAMES[r] for r in refs if r in SPEC_NAMES]
        if spec:
            nm.append('spec: ' + '/'.join(spec))
        note2 = (note or '').replace(';', ',')
        for frag in ('не на CORE-1',):
            note2 = note2.replace(frag, '')
        note2 = note2.strip(' ,;')
        if note2:
            nm.append(note2)
        seen_note = []
        for x in nm:
            if x not in seen_note: seen_note.append(x)
        mpns = sorted({MPN[r] for r in refs if r in MPN})
        rows.append(dict(code='PM-CORE-%03d' % n, value=val, qty=len(refs),
                         refs=' '.join(refs), fp=fp, note='; '.join(seen_note),
                         mpn='/'.join(mpns)))
    rows.sort(key=lambda r: r['code'])
    import csv
    with open(os.path.join(HERE, 'BOM-core.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['Артикул', 'MPN', 'Номинал/Тип', 'Кол-во', 'Позиции', 'Корпус', 'Примечание'])
        for r in rows:
            w.writerow([r['code'], r['mpn'], r['value'], r['qty'], r['refs'], r['fp'], r['note']])
    return rows

def _pin_locs():
    """net -> list of (ref, pin) for connectors/terminals of interest."""
    loc = {}
    for c in C:
        for pin, net in c['nets'].items():
            if net == 'NC': continue
            loc.setdefault(net, []).append((c['ref'], pin))
    return loc

def write_wiring():
    loc = _pin_locs()
    def locstr(net, kinds=('TB1','TB2','P1','P2','P3','J15','J16')):
        if net in ('AGND', 'DGND', 'PGND'):
            return '%s (общий, звезда на PCB)' % net
        out = []
        for ref, pin in loc.get(net, []):
            if ref in kinds:
                out.append('%s.%s' % (ref, pin))
        return ', '.join(out) if out else '—'
    lines = []
    A = lines.append
    A('# CORE-1 — таблица соединений джеков и клеммников\n')
    A('Сгенерировано `gen_core_sch.py` из той же таблицы, что и схема. '
      'Джеки — панельные (вне платы), подключаются проводами к клеммникам TB1/TB2 '
      '3.81 мм; на CORE-1 нет паяных джеков (см. `spec/20-electronics.md` §8).\n')
    A('## 1. Джеки → цепь → клеммник → CORE-1\n')
    A('| Джек | Контакт | Цепь | Клеммник | Шина P1..P3 | PANEL J15 | Примечание |')
    A('|---|---|---|---|---|---|---|')
    jacks = [(c['ref'], c['val']) for c in C if c['lib'][0] == 'Connector_Audio']
    for ref, val in jacks:
        comp = [c for c in C if c['ref'] == ref][0]
        for pin in ('T', 'R', 'S'):
            net = comp['nets'].get(pin)
            if not net:
                continue
            ports = ', '.join('%s.%s' % (r, p) for r, p in loc.get(net, []) if r in ('P1','P2','P3'))
            pan = ', '.join('%s.%s' % (r, p) for r, p in loc.get(net, []) if r == 'J15')
            if net in ('AGND', 'DGND', 'PGND'):
                ports = pan = '—'
            A('| %s | %s | `%s` | %s | %s | %s | %s |' % (
                ref, {'T':'Tip','R':'Ring','S':'Sleeve'}[pin], net, locstr(net),
                ports or '—', pan or '—', val))
    A('\n## 2. Клеммники TB1 / TB2 (3.81 мм, 2×12)\n')
    A('| Клеммник | Пин | Цепь | Что на плате | Шина |')
    A('|---|---|---|---|---|')
    for tbref in ('TB1', 'TB2'):
        comp = [c for c in C if c['ref'] == tbref][0]
        for pin in [str(i) for i in range(1, 13)]:
            net = comp['nets'].get(pin, '')
            if net in ('AGND','DGND'):
                A('| %s | %s | `%s` | общий провод | — |' % (tbref, pin, net)); continue
            ports = ', '.join('%s.%s' % (r, p) for r, p in loc.get(net, []) if r in ('P1','P2','P3')) or '—'
            others = ', '.join('%s.%s' % (r, p) for r, p in loc.get(net, [])
                               if r not in ('TB1','TB2','P1','P2','P3','J15','J16') and not r.startswith('J'))
            A('| %s | %s | `%s` | %s | %s |' % (tbref, pin, net, others or '—', ports))
    A('\n## 3. Шина Bukifon (P1/P2/P3, IDC-26)\n')
    A('| Pin | Сигнал (spec §7) | Направление | Цепь в схеме |')
    A('|---|---|---|---|')
    p0 = [c for c in C if c['ref'] == 'P1'][0]
    for pin in range(1, 27):
        net = p0['nets'].get(str(pin), '')
        A('| %d | %s | %s | `%s` |' % (pin, PORT_SIG[pin], PORT_DIR[pin], net))
    A('\n## 4. J-PANEL (J15, IDC-32)\n')
    A('| Pin | Функция | Цепь |')
    A('|---|---|---|')
    for pin, fn, note in PANEL32:
        A('| %d | %s | `%s` |' % (pin, fn, {c['ref']: c for c in C}['J15']['nets'].get(str(pin), '')))
    A('\n## 5. MCP3208 (U6) — карта каналов\n')
    A('| Канал | Цепь | Назначение |')
    A('|---|---|---|')
    for ch, net, why in MCP3208_MAP:
        A('| %s | `%s` | %s |' % (ch, net, why))
    A('\n## 6. MCP4728 — карта каналов (2 корпуса)\n')
    A('| Корпус (адрес) | Канал | Цепь | Назначение |')
    A('|---|---|---|---|')
    for u, ch, net, why in MCP4728_MAP:
        A('| %s | %s | `%s` | %s |' % (u, ch, net, why))
    A('\n## 7. Pico (A1) — карта пинов (по spec §2)\n')
    A('| GPIO | Функция | Цепь |')
    A('|---|---|---|')
    picomap = [('GP0','UART0 TX','UART_TX'),('GP1','UART0 RX','UART_RX'),
     ('GP2','SPI0 SCK','SPI_SCK'),('GP3','SPI0 MOSI','SPI_MOSI'),('GP4','SPI0 MISO','SPI_MISO'),
     ('GP5','MCP3208 CS','ADC_CS'),('GP6','74HC165 PL','HC165_PL'),('GP7','LED_DATA','LED_G'),
     ('GP8','I2C0 SDA','I2C_SDA'),('GP9','I2C0 SCL','I2C_SCL'),('GP10','SPI1 SCK','SPI1_SCK'),
     ('GP11','SPI1 MOSI','SPI1_MOSI'),('GP12','LCD_CS','LCD_CS'),('GP13','LCD_DC','LCD_DC'),
     ('GP14','LCD_RST','LCD_RST'),('GP15','LCD_BL PWM','LCD_BL_P'),('GP16','I2S BCK','I2S_BCK'),
     ('GP17','I2S LRCK','I2S_LRCK'),('GP18','I2S DIN','I2S_DIN'),('GP19','PORT0_CS','PORT0_CS'),
     ('GP20','PORT1_CS','PORT1_CS'),('GP21','PORT2_CS','PORT2_CS'),('GP22','GATE1','GATE1_G'),
     ('GP26','GATE2','GATE2_G'),('GP27','ADC1 DECK_ID','DECK_ID'),('GP28','DECK_INT','DECK_INT')]
    for gp, fn, net in picomap:
        A('| %s | %s | `%s` |' % (gp, fn, net))
    open(os.path.join(HERE, 'wiring-jacks.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

if __name__ == '__main__':
    custom = build_custom_lib()
    # project library + table + project file
    libpath = os.path.join(HERE, 'bukifon.kicad_sym')
    with open(libpath, 'w', encoding='utf-8') as fh:
        fh.write('(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "gen_core_sch.py")\n'
                 '\t(generator_version "9.0")\n')
        for nm in sorted(custom):
            body = '\n'.join('\t' + ln for ln in custom[nm].split('\n'))
            fh.write(body + '\n')
        fh.write(')\n')
    src = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/sym-lib-table'
    tbl = open(src, encoding='utf-8').read().rstrip()
    tbl = tbl[:-1].rstrip() + '\n\t(lib (name "bukifon") (type "KiCad") (uri "${KIPRJMOD}/bukifon.kicad_sym") (options "") (descr "Bukifon project symbols"))\n)\n'
    open(os.path.join(HERE, 'sym-lib-table'), 'w', encoding='utf-8').write(tbl)
    pro = {'board': {'design_settings': {}}, 'meta': {'filename': PROJECT + '.kicad_pro', 'version': 1},
           'schematic': {'legacy_lib_dir': '', 'legacy_lib_list': []},
           'sheets': [['%s.kicad_sch' % PROJECT, '']],
           'libraries': {'pinned_footprint_libs': [], 'pinned_symbol_libs': []}}
    open(os.path.join(HERE, PROJECT + '.kicad_pro'), 'w', encoding='utf-8').write(json.dumps(pro, indent=2))

    sch, comps, sections = make_schematic()
    print('placed components:', sum(len(v) for v in comps.values()), 'symbols:', len(sch.comps))
    if '--no-export' not in sys.argv:
        exports()
        erc = parse_erc()
        if erc:
            print('ERC: errors=%d warnings=%d' % (erc['errors'], erc['warnings']))
        rows = write_bom()
        write_wiring()
        print('BOM rows:', len(rows))
