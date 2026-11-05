#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PWR-2 schematic generator (PRE-FREEZE / DO NOT FABRICATE).

Energy board of the CORE-2 / PANEL-2 / PWR-2 triad:
  pack 1S2P 18650 -> fuse 5 A -> reverse-FET -> BMS (BQ297xy + 2x N-MOS)
  -> VBAT (to CORE-2 BQ24074 BAT).  Charger stays on CORE-2 (power-path).
  PWR-2 converters run ONLY from CORE-2 BQ24074 OUT/VSYS:
    +12 V  TPS61088 sync boost          (bus, budget 330 mA)
    -12 V  LMR33630 inverting buck-boost (floating GND, budget 95 mA)
    +5 V   TPS61088 sync boost          (logic/audio/BL input, budget 1.0 A)
    +5V_LED switched branch (AO3401A + 2N7002-class driver)
  Fuel gauge MAX17048 (I2C 0x36) + analog backup via CORE-2 MCP3208 CH6
  (PWR-2 provides only the sense/raw lines - the ADC dividers stay on CORE-2).

KiCad 10 native S-expression; ERC via kicad-cli.  See power-tree-pwr2.md,
interfaces.md, README.md, docs/schema/pwr2.md.

Licence: CERN-OHL-S-2.0
"""
import os
import sys
import csv
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import kicad_sch as k  # noqa: E402

KICAD_CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
PROJECT = 'PWR-2'
PAPER = 'A0'
SW, SH = 61.0, 33.0      # grid cell for auto-placement
LABEL_PAD = 2.54 + 15.0


def f(v):
    v = round(float(v), 3)
    return '%g' % v


# --------------------------------------------------------------------------
# custom symbols (project library, lib id "picomod2")
# --------------------------------------------------------------------------
def _pin(num, name, x, y, a, ln=2.54, etype='passive'):
    return ('\t\t(pin %s line (at %s %s %s) (length %s)\n'
            '\t\t\t(name "%s" (effects (font (size 1.27 1.27))))\n'
            '\t\t\t(number "%s" (effects (font (size 1.27 1.27))))\n'
            '\t\t)' % (etype, f(x), f(y), int(a), f(ln), name, num))


def custom_symbol(name, refpfx, desc, rect, pins, hide_num=False):
    x1, y1, x2, y2 = rect
    bt, bb = max(y1, y2), min(y1, y2)
    out = ['\t(symbol "%s"' % name, '\t\t(pin_names (offset 1.016))']
    if hide_num:
        out.append('\t\t(pin_numbers (hide yes))')
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


def build_custom_lib():
    lib = {}
    # TPS61088: 10-A synchronous boost, 2.7-12 V in, 4.5-12.6 V out.
    # PINOUT IS DRAFT (PRE-FREEZE): verify pin numbers against the TI datasheet
    # before any layout work; names/units are correct for the architecture.
    lib['TPS61088'] = custom_symbol(
        'TPS61088', 'U', 'TPS61088 10-A synchronous boost (draft pinout, verify vs datasheet)',
        (-10.16, -12.7, 10.16, 12.7),
        [('1', 'VIN', -12.7, 7.62, 0, 2.54, 'power_in'),
         ('2', 'EN', -12.7, 5.08, 0, 2.54, 'input'),
         ('3', 'SS', -12.7, 2.54, 0, 2.54, 'passive'),
         ('4', 'FB', -12.7, 0, 0, 2.54, 'input'),
         ('5', 'MODE', -12.7, -2.54, 0, 2.54, 'input'),
         ('6', 'GND', -5.08, -15.24, 90, 2.54, 'power_in'),
         ('7', 'PGND', -2.54, -15.24, 90, 2.54, 'power_in'),
         ('8', 'SW', 12.7, 7.62, 180, 2.54, 'passive'),
         ('9', 'SW', 12.7, 5.08, 180, 2.54, 'passive'),
         ('10', 'VOUT', 12.7, 2.54, 180, 2.54, 'power_out'),
         ('11', 'VOUT', 12.7, 0, 180, 2.54, 'power_out'),
         ('12', 'AGND', 0, -15.24, 90, 2.54, 'power_in'),
         ('13', 'EP', 2.54, -15.24, 90, 2.54, 'power_in')])
    # MAX17048: 1-cell ModelGauge fuel gauge, I2C address 0x36.
    lib['MAX17048'] = custom_symbol(
        'MAX17048', 'U', 'MAX17048 1-cell fuel gauge (I2C 0x36, draft pinout, verify vs datasheet)',
        (-7.62, -7.62, 7.62, 7.62),
        [('1', 'VDD', -10.16, 5.08, 0, 2.54, 'power_in'),
         ('2', 'GND', -10.16, 2.54, 0, 2.54, 'power_in'),
         ('3', 'SDA', -10.16, 0, 0, 2.54, 'bidirectional'),
         ('4', 'SCL', -10.16, -2.54, 0, 2.54, 'input'),
         ('5', 'ALRT', 10.16, 5.08, 180, 2.54, 'open_collector'),
         ('6', 'QSTRT', 10.16, 2.54, 180, 2.54, 'input'),
         ('7', 'CTG', 10.16, 0, 180, 2.54, 'passive'),
         ('8', 'CELL', 10.16, -2.54, 180, 2.54, 'passive')])
    for nm, txt in lib.items():
        k.CUSTOM[('picomod2', nm)] = txt.replace('(symbol "%s"' % nm, '(symbol "picomod2:%s"' % nm, 1)
    return lib


# --------------------------------------------------------------------------
# footprints (draft - PRE-FREEZE, not for fabrication)
# --------------------------------------------------------------------------
FP = {
    'R': 'Resistor_SMD:R_0603_1608Metric',
    'R1206': 'Resistor_SMD:R_1206_3216Metric',
    'C': 'Capacitor_SMD:C_0805_2012Metric',
    'C1210': 'Capacitor_SMD:C_1210_3225Metric',
    'CP': 'Capacitor_SMD:CP_Elec_6.3x7.7',
    'L': 'Inductor_SMD:L_Bourns-SRN6045',
    'L10': 'Inductor_SMD:L_Bourns-SRN6045',
    'QFN20': 'Package_DFN_QFN:QFN-20-1EP_3x3mm_P0.4mm_EP1.8x1.8mm',
    'SOIC8': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    'SOT23': 'Package_TO_SOT_SMD:SOT-23',
    'SOT23_6': 'Package_TO_SOT_SMD:SOT-23-6',
    'DIP8': 'Package_DIP:DIP-8_W7.62mm',
    'SMA': 'Diode_SMD:D_SMA',
    'PF': 'Fuse:Fuse_1206_3216Metric',
    'IDC20': 'Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical',
    'IDC12': 'Connector_IDC:IDC-Header_2x06_P2.54mm_Vertical',
    'TB3': 'TerminalBlock_4Ucon:TerminalBlock_4Ucon_1x03_P3.50mm_Vertical',
    'HDR2': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    'SW': '',            # панельный тумблер/слайдер (механика), footprint проектный
    'TP': 'TestPoint:TestPoint_Pad_D1.5mm',
    'HOLDER': 'Battery:BatteryHolder_Keystone_1042_1x18650',
    'NTC': '',
}

# --------------------------------------------------------------------------
# component table: (ref, lib, value, {pin: net|None}, footprint, note, section)
# --------------------------------------------------------------------------
C = []


def add(ref, lib, val, nets, fp, note, sec, on_board=True):
    C.append(dict(ref=ref, lib=lib, val=val, nets=nets, fp=fp, note=note, sec=sec,
                  on_board=on_board))


N12 = 'N12_SW'   # отрицательный узел IBB = "земля" микросхемы buck

# ============================ 1. PACK + PROTECTION ========================
add('J1', ('Connector_Generic', 'Conn_01x03'), 'PACK 3P',
    {'1': 'BATT_CELL_P', '2': 'BATT_BM', '3': 'NTC_PACK'}, FP['TB3'],
    'батарейный отсек: 1=B+, 2=B-, 3=NTC (термистор на банке)', 'PACK')
add('BT1', ('Device', 'Battery_Cell'), '18650 3.6V 3.5Ah',
    {'1': 'BATT_CELL_P', '2': 'BATT_BM'}, FP['HOLDER'],
    'банка 1/2 (параллель); холдер в батарейном отсеке, не на плате', 'PACK', on_board=False)
add('BT2', ('Device', 'Battery_Cell'), '18650 3.6V 3.5Ah',
    {'1': 'BATT_CELL_P', '2': 'BATT_BM'}, FP['HOLDER'],
    'банка 2/2 (параллель); ХОЛДЕРЫ С КЛЮЧОМ от переполюсовки', 'PACK', on_board=False)
add('F1', ('Device', 'Polyfuse'), '5 A', {'1': 'BATT_CELL_P', '2': 'PACK_F'}, FP['PF'],
    'предохранитель пакета 4-5 А (по ТЗ): защита от КЗ и от переполюсовки одной банки', 'PACK')
add('Q1', ('Transistor_FET', 'AO3401A'), 'AO3401A P-FET', {'1': 'BATT_BM', '2': 'PACK_F', '3': 'VBAT'},
    FP['SOT23'], 'защита от переполюсовки пакета: затвор на B-, при обратной банке закрыт', 'PACK')
add('R1', ('Device', 'R'), '100k', {'1': 'PACK_F', '2': 'BATT_BM'}, FP['R'],
    'подтяжка затвора Q1 (OFF при обрыве)', 'PACK')
add('D1', ('Device', 'D_TVS'), 'SMBJ5.0A', {'1': 'PACK_F', '2': 'BATT_BM'}, FP['SMA'],
    'TVS на пакете (ESD/импульсы при hot-plug)', 'PACK')
add('TH1', ('Device', 'Thermistor_NTC'), 'NTC 10k B3950', {'1': 'NTC_PACK', '2': 'BATT_BM'}, FP['NTC'],
    'термистор на банке: -> TS BQ24074 (CORE-2) и -> CH7 (TEMP_MON)', 'PACK', on_board=False)
add('R2', ('Device', 'R'), '100R', {'1': 'VBAT', '2': 'BMS_BAT'}, FP['R'],
    'RC-фильтр BAT BQ297xy', 'BMS')
add('C1', ('Device', 'C'), '100n', {'1': 'BMS_BAT', '2': 'BATT_BM'}, FP['C'],
    'RC-фильтр BAT BQ297xy', 'BMS')
add('R3', ('Device', 'R'), '1k', {'1': 'CS_BMS', '2': 'PGND'}, FP['R'],
    'токовый сенс BQ297xy (V-) к P-', 'BMS')
add('U1', ('Battery_Management', 'BQ297xy'), 'BQ297xy', {
    '1': None, '2': 'G_CHG', '3': 'G_DIS', '4': 'BATT_BM', '5': 'BMS_BAT', '6': 'CS_BMS'},
    FP['SOT23_6'], 'BMS 1S: OVP 4.25-4.30 В, UVP 2.35-2.50 В, OCP/SCP (внешние NMOS)', 'BMS')
add('Q2', ('Transistor_FET', 'AO3400A'), 'AO3400A', {'1': 'G_DIS', '2': 'BMS_MID', '3': 'BATT_BM'},
    FP['SOT23'], 'разрядный ключ BMS (общий исток с Q3)', 'BMS')
add('Q3', ('Transistor_FET', 'AO3400A'), 'AO3400A', {'1': 'G_CHG', '2': 'BMS_MID', '3': 'PGND'},
    FP['SOT23'], 'зарядный ключ BMS (общий исток с Q2)', 'BMS')
add('R4', ('Device', 'R'), '100k', {'1': 'G_DIS', '2': 'BMS_MID'}, FP['R'], 'gate-source Q2', 'BMS')
add('R5', ('Device', 'R'), '100k', {'1': 'G_CHG', '2': 'BMS_MID'}, FP['R'], 'gate-source Q3', 'BMS')

# ============================ 2. MASTER LOAD SWITCH ======================
add('Q4', ('Transistor_FET', 'AO3401A'), 'AO3401A P-FET', {'1': 'G_MASTER', '2': 'VSYS', '3': 'VSYS_MID'},
    FP['SOT23'], 'back-to-back P-FET 1/2 (reverse blocking, 11 мОм-класс)', 'LOADS')
add('Q5', ('Transistor_FET', 'AO3401A'), 'AO3401A P-FET', {'1': 'G_MASTER', '2': 'VSYS_MID', '3': 'VSYS_SW'},
    FP['SOT23'], 'back-to-back P-FET 2/2', 'LOADS')
add('R6', ('Device', 'R'), '100k', {'1': 'VSYS', '2': 'G_MASTER'}, FP['R'], 'подтяжка затворов (OFF)', 'LOADS')
add('Q6', ('Transistor_BJT', 'Q_NPN_BCE'), 'MMBT3904', {'1': 'Q6_B', '2': 'G_MASTER', '3': 'PGND'},
    FP['SOT23'], 'драйвер высокого плеча: ON = затворы к PGND', 'LOADS')
add('R7', ('Device', 'R'), '10k', {'1': 'MASTER_SW', '2': 'Q6_B'}, FP['R'], 'база Q6', 'LOADS')
add('R8', ('Device', 'R'), '100k', {'1': 'Q6_B', '2': 'PGND'}, FP['R'], 'база Q6 -> PGND (OFF по умолчанию)', 'LOADS')
add('R9', ('Device', 'R'), '100k', {'1': 'MASTER_SW', '2': 'PGND'}, FP['R'], 'MASTER_SW -> PGND (обрыв = OFF)', 'LOADS')
add('C2', ('Device', 'C'), '100n', {'1': 'G_MASTER', '2': 'VSYS_SW'}, FP['C'], 'сглаживание затвора (turn-on/off)', 'LOADS')
add('J2', ('Connector_Generic', 'Conn_01x02'), 'SW panel', {'1': 'VSYS', '2': 'MASTER_SW'}, FP['HDR2'],
    'вывод на панельный тумблер питания (параллельно SW1)', 'LOADS')
add('SW1', ('Switch', 'SW_SPDT'), 'POWER OFF/ON', {'1': 'VSYS', '2': 'MASTER_SW', '3': None}, FP['SW'],
    'местный слайдер питания (запасной/для макета)', 'LOADS')
add('D2', ('Device', 'D_TVS'), 'SMBJ5.0A', {'1': 'VSYS_SW', '2': 'PGND'}, FP['SMA'],
    'TVS после load switch', 'LOADS')
add('C3', ('Device', 'C'), '22uF', {'1': 'VSYS_SW', '2': 'PGND'}, FP['C1210'],
    'вход всех преобразователей', 'LOADS')

# ============================ 3. FUEL GAUGE ==============================
add('U2', ('picomod2', 'MAX17048'), 'MAX17048', {
    '1': 'VGAUGE', '2': 'PGND', '3': 'FUEL_SDA', '4': 'FUEL_SCL',
    '5': 'FUEL_ALRT', '6': 'PGND', '7': None, '8': None},
    FP['SOT23_6'], 'fuel gauge 1S, I2C 0x36, +-7.5 мВ, без шунта; VDD = Kelvin на банку', 'GAUGE')
add('R10', ('Device', 'R'), '10R', {'1': 'BATT_CELL_P', '2': 'VGAUGE'}, FP['R'],
    'Kelvin-питание/сенс банки для гейджа (ток ~25 мкА)', 'GAUGE')
add('C4', ('Device', 'C'), '1uF', {'1': 'VGAUGE', '2': 'PGND'}, FP['C'], 'VDD гейджа', 'GAUGE')
add('C5', ('Device', 'C'), '100n', {'1': 'VGAUGE', '2': 'PGND'}, FP['C'], 'VDD гейджа ВЧ', 'GAUGE')
add('R11', ('Device', 'R'), '22R', {'1': 'FUEL_SDA', '2': 'FUEL_SDA_C'}, FP['R'],
    'серия I2C SDA (защита/развязка от длинного кабеля)', 'GAUGE')
add('R12', ('Device', 'R'), '22R', {'1': 'FUEL_SCL', '2': 'FUEL_SCL_C'}, FP['R'],
    'серия I2C SCL', 'GAUGE')
add('R13', ('Device', 'R'), '1k', {'1': 'BATT_CELL_P', '2': 'BATT_MON'}, FP['R'],
    'резервный аналоговый контроль: сырой VBAT -> делитель CH6 на CORE-2', 'GAUGE')

# ============================ 4. +12 V (TPS61088) ========================
add('U3', ('picomod2', 'TPS61088'), 'TPS61088', {
    '1': 'VSYS_SW', '2': 'EN_BUS12', '3': 'SS_12', '4': 'FB_12', '5': 'PGND',
    '6': 'PGND', '7': 'PGND', '8': 'SW_12', '9': 'SW_12', '10': '12V_SW',
    '11': '12V_SW', '12': 'PGND', '13': 'PGND'},
    FP['QFN20'], 'sync boost 10-A ключ: +12.15 В / 330 мА (запас 4x по току)', '12V')
add('L1', ('Device', 'L'), '10uH / 4A', {'1': 'VSYS_SW', '2': 'SW_12'}, FP['L'],
    'индуктор +12 В (Isat >= 4 А)', '12V')
add('C6', ('Device', 'C'), '22uF', {'1': 'VSYS_SW', '2': 'PGND'}, FP['C1210'], 'вход +12 В', '12V')
add('C7', ('Device', 'C'), '22uF', {'1': 'VSYS_SW', '2': 'PGND'}, FP['C1210'], 'вход +12 В', '12V')
add('C8', ('Device', 'C'), '100n', {'1': 'VSYS_SW', '2': 'PGND'}, FP['C'], 'вход +12 В ВЧ', '12V')
add('R14', ('Device', 'R'), '100k', {'1': '12V_SW', '2': 'FB_12'}, FP['R'],
    'ОС: Vout = 1.204*(1+100k/11k) = 12.15 В', '12V')
add('R15', ('Device', 'R'), '11k', {'1': 'FB_12', '2': 'PGND'}, FP['R'], 'низ ОС +12 В', '12V')
add('C9', ('Device', 'C'), '100n', {'1': 'SS_12', '2': 'PGND'}, FP['C'], 'soft-start +12 В', '12V')
add('R16', ('Device', 'R'), '100k', {'1': 'VSYS_SW', '2': 'EN_BUS12'}, FP['R'],
    'EN по умолчанию ON (CORE-2 может тянуть вниз для секвенирования)', '12V')
add('L2', ('Device', 'L'), '4.7uH', {'1': '12V_SW', '2': '12V_F'}, FP['L10'],
    'pi-фильтр +12 В: L', '12V')
add('C10', ('Device', 'C'), '47uF/25V', {'1': '12V_F', '2': 'PGND'}, FP['CP'], 'pi-фильтр +12 В: C1', '12V')
add('C11', ('Device', 'C'), '47uF/25V', {'1': '12V_F', '2': 'PGND'}, FP['CP'], 'pi-фильтр +12 В: C2', '12V')
add('C12', ('Device', 'C'), '100n', {'1': '12V_F', '2': 'PGND'}, FP['C'], 'pi-фильтр +12 В: HF', '12V')
add('F2', ('Device', 'Polyfuse'), '0.5 A', {'1': '12V_F', '2': '12V_BUS'}, FP['PF'],
    'полифьюз шины +12 В (шина модулей <= 300 мА)', '12V')
add('D3', ('Device', 'D_TVS'), 'SMAJ15A', {'1': '12V_BUS', '2': 'PGND'}, FP['SMA'],
    'TVS шины +12 В', '12V')
add('R17', ('Device', 'R'), '4.7k', {'1': '12V_BUS', '2': 'PGND'}, FP['R'], 'разрядный резистор +12 В', '12V')
add('C13', ('Device', 'C'), '100n', {'1': '12V_BUS', '2': 'PGND'}, FP['C'], 'ВЧ на шине +12 В', '12V')

# ============================ 5. -12 V (LMR33630 IBB) ====================
add('U4', ('Regulator_Switching', 'LMR33630ADDA'), 'LMR33630', {
    '1': N12, '2': 'VSYS_SW', '3': 'EN_N12_IC', '4': None, '5': 'FB_N12',
    '6': 'VCC_N12', '7': 'BOOT_N12', '8': 'SW_N12', '9': N12},
    FP['SOIC8'],
    'синхронный buck в инвертирующем IBB: GND МС = -12 В, VIN = VSYS+12 В = 15.7 В', '12VN')
add('L3', ('Device', 'L'), '22uH / 2A', {'1': 'SW_N12', '2': 'PGND'}, FP['L'],
    'IBB: индуктор SW -> PGND (выход buck = системная земля)', '12VN')
add('C14', ('Device', 'C'), '100n', {'1': 'BOOT_N12', '2': 'SW_N12'}, FP['C'], 'bootstrap -12 В', '12VN')
add('C15', ('Device', 'C'), '1uF', {'1': 'VCC_N12', '2': N12}, FP['C'], 'VCC МС (внутр. LDO) -> GND МС', '12VN')
add('C16', ('Device', 'C'), '22uF/25V', {'1': 'VSYS_SW', '2': N12}, FP['C1210'],
    'вход IBB: 15.7 В (25 В керамика!)', '12VN')
add('C17', ('Device', 'C'), '100n', {'1': 'VSYS_SW', '2': N12}, FP['C'], 'вход IBB ВЧ', '12VN')
add('C18', ('Device', 'C'), '22uF/25V', {'1': 'PGND', '2': N12}, FP['C1210'], 'выход IBB 1', '12VN')
add('C19', ('Device', 'C'), '22uF/25V', {'1': 'PGND', '2': N12}, FP['C1210'], 'выход IBB 2', '12VN')
add('R19', ('Device', 'R'), '110k', {'1': 'PGND', '2': 'FB_N12'}, FP['R'],
    'ОС IBB: Vout = 1.0*(1+110k/10k) = 12.0 В', '12VN')
add('R20', ('Device', 'R'), '10k', {'1': 'FB_N12', '2': N12}, FP['R'], 'низ ОС -12 В', '12VN')
add('U5', ('Isolator', 'PC817'), 'PC817', {'1': 'OPT_ANODE', '2': 'PGND', '3': 'EN_N12_IC', '4': 'VSYS_SW'},
    FP['DIP8'], 'оптопара: уровень EN из домена PGND в домен -12 В', '12VN')
add('R21', ('Device', 'R'), '1k', {'1': 'EN_N12', '2': 'OPT_ANODE'}, FP['R'], 'ток LED оптопары ~2.6 мА', '12VN')
add('R22', ('Device', 'R'), '100k', {'1': 'EN_N12', '2': 'VSYS_SW'}, FP['R'],
    'EN по умолчанию ON (CORE-2 тянет вниз для OFF)', '12VN')
add('R23', ('Device', 'R'), '100k', {'1': 'EN_N12_IC', '2': N12}, FP['R'], 'EN -> GND МС (OFF)', '12VN')
add('C20', ('Device', 'C'), '100n', {'1': 'EN_N12_IC', '2': N12}, FP['C'], 'фильтр EN -12 В', '12VN')
add('L4', ('Device', 'L'), '10uH', {'1': N12, '2': 'N12_F'}, FP['L10'], 'pi-фильтр -12 В: L', '12VN')
add('C21', ('Device', 'C'), '47uF/25V', {'1': 'PGND', '2': 'N12_F'}, FP['CP'], 'pi-фильтр -12 В: C1', '12VN')
add('C22', ('Device', 'C'), '47uF/25V', {'1': 'PGND', '2': 'N12_F'}, FP['CP'], 'pi-фильтр -12 В: C2', '12VN')
add('C23', ('Device', 'C'), '100n', {'1': 'PGND', '2': 'N12_F'}, FP['C'], 'pi-фильтр -12 В: HF', '12VN')
add('F3', ('Device', 'Polyfuse'), '0.3 A', {'1': 'N12_F', '2': 'N12_BUS'}, FP['PF'],
    'полифьюз -12 В (шина <= 95 мА; 25%+ запас)', '12VN')
add('D4', ('Device', 'D_TVS'), 'SMAJ15A', {'1': 'PGND', '2': 'N12_BUS'}, FP['SMA'], 'TVS -12 В', '12VN')
add('R24', ('Device', 'R'), '4.7k', {'1': 'N12_BUS', '2': 'PGND'}, FP['R'], 'разрядный резистор -12 В', '12VN')
add('C24', ('Device', 'C'), '100n', {'1': 'PGND', '2': 'N12_BUS'}, FP['C'], 'ВЧ на -12 В', '12VN')

# ============================ 6. +5 V (TPS61088) =========================
add('U6', ('picomod2', 'TPS61088'), 'TPS61088', {
    '1': 'VSYS_SW', '2': 'EN_5', '3': 'SS_5', '4': 'FB_5', '5': 'PGND',
    '6': 'PGND', '7': 'PGND', '8': 'SW_5', '9': 'SW_5', '10': '5V_SW',
    '11': '5V_SW', '12': 'PGND', '13': 'PGND'},
    FP['QFN20'], 'sync boost: +5.10 В / 1.0 А (аудио, MIDI, логика, вход BL)', '5V')
add('L5', ('Device', 'L'), '10uH / 4A', {'1': 'VSYS_SW', '2': 'SW_5'}, FP['L'], 'индуктор +5 В', '5V')
add('C25', ('Device', 'C'), '22uF', {'1': 'VSYS_SW', '2': 'PGND'}, FP['C1210'], 'вход +5 В', '5V')
add('C26', ('Device', 'C'), '22uF', {'1': 'VSYS_SW', '2': 'PGND'}, FP['C1210'], 'вход +5 В', '5V')
add('C27', ('Device', 'C'), '100n', {'1': 'VSYS_SW', '2': 'PGND'}, FP['C'], 'вход +5 В ВЧ', '5V')
add('R25', ('Device', 'R'), '100k', {'1': '5V_SW', '2': 'FB_5'}, FP['R'],
    'ОС: Vout = 1.204*(1+100k/30.9k) = 5.10 В', '5V')
add('R26', ('Device', 'R'), '30.9k', {'1': 'FB_5', '2': 'PGND'}, FP['R'], 'низ ОС +5 В', '5V')
add('C28', ('Device', 'C'), '100n', {'1': 'SS_5', '2': 'PGND'}, FP['C'], 'soft-start +5 В', '5V')
add('R27', ('Device', 'R'), '100k', {'1': 'VSYS_SW', '2': 'EN_5'}, FP['R'], 'EN +5 В = ON', '5V')
add('L6', ('Device', 'L'), '4.7uH', {'1': '5V_SW', '2': '5V_F'}, FP['L10'], 'pi-фильтр +5 В: L', '5V')
add('C29', ('Device', 'C'), '47uF', {'1': '5V_F', '2': 'PGND'}, FP['CP'], 'pi-фильтр +5 В: C1', '5V')
add('C30', ('Device', 'C'), '47uF', {'1': '5V_F', '2': 'PGND'}, FP['CP'], 'pi-фильтр +5 В: C2', '5V')
add('C31', ('Device', 'C'), '100n', {'1': '5V_F', '2': 'PGND'}, FP['C'], 'pi-фильтр +5 В: HF', '5V')
add('F4', ('Device', 'Polyfuse'), '2 A', {'1': '5V_F', '2': '5V_BUS'}, FP['PF'],
    'полифьюз +5 В (логика/аудио/BL)', '5V')
add('D5', ('Device', 'D_TVS'), 'SMBJ5.0A', {'1': '5V_BUS', '2': 'PGND'}, FP['SMA'], 'TVS +5 В', '5V')
add('R28', ('Device', 'R'), '1k', {'1': '5V_BUS', '2': 'PGND'}, FP['R'], 'разрядный резистор +5 В', '5V')
add('C32', ('Device', 'C'), '100n', {'1': '5V_BUS', '2': 'PGND'}, FP['C'], 'ВЧ на +5 В', '5V')

# ============================ 7. +5V_LED SWITCH ==========================
add('Q7', ('Transistor_FET', 'AO3401A'), 'AO3401A P-FET', {'1': 'G_LED', '2': '5V_BUS', '3': '5V_LED_F'},
    FP['SOT23'], 'ключ LED-ветки: WS2812 питаются только при EN_LED5 (brightness cap снизу)', 'LED5')
add('R29', ('Device', 'R'), '100k', {'1': '5V_BUS', '2': 'G_LED'}, FP['R'], 'подтяжка затвора (OFF)', 'LED5')
add('Q8', ('Transistor_BJT', 'Q_NPN_BCE'), 'MMBT3904', {'1': 'Q8_B', '2': 'G_LED', '3': 'PGND'},
    FP['SOT23'], 'драйвер ключа LED', 'LED5')
add('R30', ('Device', 'R'), '10k', {'1': 'EN_LED5', '2': 'Q8_B'}, FP['R'], 'база Q8', 'LED5')
add('R31', ('Device', 'R'), '100k', {'1': 'Q8_B', '2': 'PGND'}, FP['R'], 'OFF по умолчанию', 'LED5')
add('F5', ('Device', 'Polyfuse'), '2.5 A', {'1': '5V_LED_F', '2': '5V_LED'}, FP['PF'],
    'полифьюз LED-шины (74 WS2812, прошивочный cap)', 'LED5')
add('C33', ('Device', 'C'), '47uF', {'1': '5V_LED', '2': 'PGND'}, FP['CP'], 'буфер LED-импульсов', 'LED5')
add('C34', ('Device', 'C'), '100n', {'1': '5V_LED', '2': 'PGND'}, FP['C'], 'HF LED-шины', 'LED5')
add('D6', ('Device', 'D_TVS'), 'SMBJ5.0A', {'1': '5V_LED', '2': 'PGND'}, FP['SMA'], 'TVS LED-шины', 'LED5')
add('R32', ('Device', 'R'), '1k', {'1': '5V_LED', '2': 'PGND'}, FP['R'], 'разрядный резистор LED', 'LED5')

# ============================ 8. SUPERVISOR + EN INPUTS ==================
add('U7', ('Power_Supervisor', 'MCP130-xxxDxTO'), 'MCP130-300', {
    '2': 'VSYS_SW', '3': 'PGND', '1': 'PWR_GOOD'}, FP['SOT23'],
    'супервизор 3.00 В: PWR_GOOD = open-drain, LOW = VSYS ниже нормы', 'CTRL')
add('R33', ('Device', 'R'), '100R', {'1': 'EN_BUS12_C', '2': 'EN_BUS12'}, FP['R'], 'серия EN +12 В', 'CTRL')
add('C35', ('Device', 'C'), '100n', {'1': 'EN_BUS12', '2': 'PGND'}, FP['C'], 'RC/EMI на EN +12 В', 'CTRL')
add('R34', ('Device', 'R'), '100R', {'1': 'EN_N12_C', '2': 'EN_N12'}, FP['R'], 'серия EN -12 В', 'CTRL')
add('C36', ('Device', 'C'), '100n', {'1': 'EN_N12', '2': 'PGND'}, FP['C'], 'RC/EMI на EN -12 В', 'CTRL')
add('R35', ('Device', 'R'), '100R', {'1': 'EN_LED5_C', '2': 'EN_LED5'}, FP['R'], 'серия EN LED', 'CTRL')
add('C37', ('Device', 'C'), '100n', {'1': 'EN_LED5', '2': 'PGND'}, FP['C'], 'RC/EMI на EN LED', 'CTRL')

# ============================ 9. CONNECTORS ==============================
add('J3', ('Connector_Generic', 'Conn_02x10_Odd_Even'), 'J-PWR (IDC-20)', {
    '1': 'VSYS', '2': 'VSYS', '3': 'VBAT', '4': 'VBAT',
    '5': '12V_BUS', '6': '12V_BUS', '7': 'PGND', '8': 'PGND',
    '9': 'N12_BUS', '10': 'N12_BUS', '11': 'PGND', '12': 'PGND',
    '13': '5V_BUS', '14': '5V_BUS', '15': 'PGND', '16': 'PGND',
    '17': '5V_LED', '18': '5V_LED', '19': 'PGND', '20': 'PGND'},
    FP['IDC20'],
    'PWR-2 <-> CORE-2: питание (пары) + возвраты; +12/-12/+5/5V_LED', 'CONN')
add('J4', ('Connector_Generic', 'Conn_02x06_Odd_Even'), 'J-CTRL (IDC-12)', {
    '1': 'BATT_MON', '2': 'NTC_PACK', '3': 'FUEL_SDA_C', '4': 'FUEL_SCL_C',
    '5': 'FUEL_ALRT', '6': 'PWR_GOOD', '7': 'EN_BUS12_C', '8': 'EN_N12_C',
    '9': 'EN_LED5_C', '10': 'MASTER_SW', '11': 'PGND', '12': 'PGND'},
    FP['IDC12'],
    'PWR-2 <-> CORE-2: сенс/гейдж/статус/EN (MASTER_SW -> CORE-2 для секвенирования)', 'CONN')

# ============================ 10. TEST POINTS ============================
for i, (tp, net, why) in enumerate([
        ('TP1', 'BATT_CELL_P', 'напряжение банок'), ('TP2', 'VBAT', 'выход BMS (P+)'),
        ('TP3', 'VSYS_SW', 'вход преобразователей'), ('TP4', '12V_BUS', 'шина +12 В'),
        ('TP5', 'N12_BUS', 'шина -12 В'), ('TP6', '5V_BUS', 'шина +5 В'),
        ('TP7', '5V_LED', 'LED-шина'), ('TP8', 'PWR_GOOD', 'статус питания'),
        ('TP9', 'PGND', 'силовая земля для измерений')]):
    add(tp, ('Connector', 'TestPoint'), net, {'1': net}, FP['TP'], why, 'TP')

FLAGS = ['PGND', 'VSYS', 'VSYS_SW', 'VBAT', 'BATT_CELL_P', 'BATT_BM', 'BMS_BAT',
         '12V_BUS', 'N12_BUS', '5V_BUS', '5V_LED', 'VGAUGE', '12V_SW', N12, '5V_SW',
         '12V_F', 'N12_F', '5V_F', 'VSYS_MID']

SEC_TITLES = {
    'PACK': 'PACK 1S2P: 2x18650 parallel, J1 pack, F1 5 A, Q1 reverse-FET, D1 TVS, TH1 NTC',
    'BMS': 'BMS 1S: BQ297xy + 2x AO3400A (common source), OVP/UVP/OCP/SCP; VBAT = P+ -> BQ24074 BAT',
    'LOADS': 'MASTER LOAD SWITCH: back-to-back AO3401A, MMBT3904 driver, panel switch J2/SW1, TVS',
    'GAUGE': 'FUEL GAUGE MAX17048 (I2C 0x36) + Kelvin sense + analog backup BATT_MON',
    '12V': 'BUS +12 V: TPS61088 sync boost -> pi-filter -> polyfuse 0.5 A -> TVS (budget 330 mA)',
    '12VN': 'BUS -12 V: LMR33630 inverting buck-boost (floating GND) + opto EN -> pi-filter -> polyfuse 0.3 A (budget 95 mA)',
    '5V': 'LOGIC/AUDIO +5 V: TPS61088 sync boost -> pi-filter -> polyfuse 2 A (budget 1.0 A)',
    'LED5': 'SWITCHED +5 V LED BRANCH: AO3401A key + MMBT3904 driver, EN_LED5, polyfuse 2.5 A',
    'CTRL': 'SUPERVISOR + EN INPUTS: MCP130-300 (PWR_GOOD open-drain), 100R/100n EN filters',
    'CONN': 'INTERFACE: J3 IDC-20 power, J4 IDC-12 control',
    'TP': 'TEST POINTS TP1..TP9',
}

SECTION_ORDER = ['PACK', 'BMS', 'LOADS', 'GAUGE', '12V', '12VN', '5V', 'LED5', 'CTRL', 'CONN', 'TP']
COLUMNS = {
    'PACK': 0, 'BMS': 0, 'LOADS': 0,
    'GAUGE': 1, '12V': 1, '12VN': 1,
    '5V': 2, 'LED5': 2, 'CTRL': 2, 'CONN': 2, 'TP': 2,
}
COL_X = [25.0, 400.0, 775.0]


# --------------------------------------------------------------------------
class Section:
    def __init__(self, sch, name, x0, y0, cols=5):
        self.sch = sch
        self.name = name
        self.x0 = x0
        self.y0 = y0
        self.cols = cols
        self.col = 0
        self.row = 0
        self.shelf = 0
        sch.text(name, (x0, y0 - 3.5), size=2.6)

    def place(self, comp):
        w, h = comp_size(comp['lib'])
        if self.col + w > self.cols:
            self.col = 0
            self.row += self.shelf
            self.shelf = 0
        x = self.x0 + (self.col + w / 2.0) * SW
        y = self.y0 + 11.0 + (self.row + h / 2.0) * SH
        c = self.sch.sym(comp['lib'][0], comp['lib'][1], comp['ref'], comp['val'],
                         x, y, footprint=comp['fp'], on_board=comp['on_board'],
                         ref_off=(-w * SW / 2 + 4, -h * SH / 2 + 3.0),
                         val_off=(-w * SW / 2 + 4, -h * SH / 2 + 6.0))
        c['note'] = comp['note']
        self.shelf = max(self.shelf, h)
        self.col += w
        return c

    def end_y(self):
        return self.y0 + 11.0 + (self.row + self.shelf) * SH


def _pin_span(lib):
    return k.pins(*lib)


def comp_size(lib):
    ps = _pin_span(lib)
    if not ps:
        return 1, 1
    xs = [p[2] for p in ps]
    ys = [p[3] for p in ps]
    left = any(p[4] == 0 for p in ps)
    right = any(p[4] == 180 for p in ps)
    top = any(p[4] == 270 for p in ps)
    bot = any(p[4] == 90 for p in ps)
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    w += (LABEL_PAD if left else 0) + (LABEL_PAD if right else 0)
    h += 4.0 if top else 0.0
    h += 4.0 if bot else 0.0
    return max(1, int(-(-w // SW))), max(1, int(-(-h // SH)))


def make_schematic():
    build_custom_lib()
    sch = k.Sch(os.path.join(HERE, PROJECT + '.kicad_sch'),
                'PWR-2 PRE-FREEZE / DO NOT FABRICATE - battery + bus rails (1S2P, +-12 V, +5 V)',
                paper=PAPER, project=PROJECT)
    sch.text('PRE-FREEZE / DO NOT FABRICATE', (28, 20), size=7.0)
    sch.text('PWR-2 rev.1 research schematic - 1S2P 18650 + BMS + MAX17048 + TPS61088/+12 V '
             '+ LMR33630 IBB/-12 V + TPS61088/+5 V.', (28, 27), size=3.0)
    sch.text('Charger/power-path (BQ24074) stays on CORE-2: PWR-2 converters are fed ONLY by '
             'VSYS (BQ24074 OUT). No MC34063, no charge pump.', (28, 31.5), size=2.5)
    sch.text('Docs: README.md, power-tree-pwr2.md, interfaces.md, docs/schema/pwr2.md',
             (28, 35.5), size=2.5)

    comps = {}
    sections = {}
    ypos = {0: 50.0, 1: 50.0, 2: 50.0}
    for sec in SECTION_ORDER:
        col = COLUMNS[sec]
        s = Section(sch, SEC_TITLES[sec], COL_X[col], ypos[col])
        sections[sec] = s
        for comp in C:
            if comp['sec'] != sec:
                continue
            c = s.place(comp)
            comps[comp['ref']] = (c, comp)
        ypos[col] = s.end_y() + 16.0

    # power flags column (bottom right)
    fy = max(ypos.values()) + 8.0
    sch.text('POWER FLAGS (net drivers for ERC)', (COL_X[2], fy), size=2.6)
    for i, net in enumerate(FLAGS):
        fx = COL_X[2] + (i % 5) * 26.0
        fyy = fy + 10.0 + (i // 5) * 22.0
        fc = sch.sym('power', 'PWR_FLAG', '#FLG%02d' % (i + 1), 'PWR_FLAG', fx, fyy,
                     hide_ref=True, ref_off=(2, -3), val_off=(2, 3))
        sch.net(fc, net, num='1')

    # wire every pin by label, nc the rest
    for ref, (c, comp) in comps.items():
        for p in _pin_span(comp['lib']):
            net = comp['nets'].get(p[0])
            if net is None:
                sch.nc_pin(c, num=p[0])
            else:
                sch.net(c, net, num=p[0])
    sch.write()
    return sch, comps, sections


# --------------------------------------------------------------------------
def export(sch):
    env = dict(os.environ, XDG_CACHE_HOME='/tmp/kicad-cache-pwr2')
    os.makedirs(env['XDG_CACHE_HOME'], exist_ok=True)
    os.makedirs(os.path.join(HERE, 'erc'), exist_ok=True)
    os.makedirs(os.path.join(HERE, 'svg'), exist_ok=True)
    schf = os.path.join(HERE, PROJECT + '.kicad_sch')

    def run(*args, quiet=True):
        r = subprocess.run([KICAD_CLI] + list(args), capture_output=True, text=True, env=env)
        out = ((r.stdout or '') + (r.stderr or '')).replace('Fontconfig', '')
        if not quiet:
            print('  rc=%d %s' % (r.returncode, out.strip()[:300]))
        return r, out

    run('sch', 'erc', '--severity-all', '--format', 'report', '-o',
        os.path.join(HERE, 'erc', 'erc.rpt'), schf)
    run('sch', 'erc', '--severity-all', '--format', 'json', '-o',
        os.path.join(HERE, 'erc', 'erc.json'), schf)
    run('sch', 'export', 'netlist', '-o', os.path.join(HERE, 'netlist.net'), schf)
    run('sch', 'export', 'netlist', '--format', 'kicadxml', '-o',
        os.path.join(HERE, 'netlist.xml'), schf)
    run('sch', 'export', 'pdf', '-o', os.path.join(HERE, PROJECT + '.pdf'), schf)
    run('sch', 'export', 'svg', '-o', os.path.join(HERE, 'svg'), schf)

    # ---- BOM: артикул;MPN;номинал;кол-во;позиции;корпус;примечание ----
    rows = []
    for i, comp in enumerate(C):
        rows.append({
            'Артикул': 'PM-PWR2-%03d' % (i + 1),
            'MPN': MPN.get(comp['val'], ''),
            'Номинал': comp['val'],
            'Кол-во': 1,
            'Позиции': comp['ref'],
            'Корпус': comp['fp'].split(':')[-1] if comp['fp'] else '— (вне платы)',
            'Примечание': comp['note'],
        })
    with open(os.path.join(HERE, 'BOM-power2.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=';')
        w.writeheader()
        w.writerows(rows)
    print('BOM-power2.csv: %d строк' % len(rows))


MPN = {
    'TPS61088': 'TPS61088RHLR (QFN-20)',
    'LMR33630': 'LMR33630ADDA (SOIC-8 PowerPAD, 36 В)',
    'MAX17048': 'MAX17048G+T (TDFN-8)',
    'BQ297xy': 'BQ29700DSER (1S, OVP 4.275 В)',
    'MCP130-300': 'MCP130-300DI/TO (3.00 В)',
    'PC817': 'PC817C (DIP-4)',
    'AO3401A': 'AO3401A (P-FET 30 В, Rds 60 мОм)',
    'AO3400A': 'AO3400A (N-FET 30 В)',
    'MMBT3904': 'MMBT3904',
    'SMBJ5.0A': 'SMBJ5.0A',
    'SMAJ15A': 'SMAJ15A',
    'Battery_Cell_placeholder': '',
}


def main():
    sch, comps, sections = make_schematic()
    print('written %s.kicad_sch: %d компонентов' % (PROJECT, len(C)))
    pro = os.path.join(HERE, PROJECT + '.kicad_pro')
    with open(pro, 'w', encoding='utf-8') as fh:
        fh.write('{\n  "board": {"design_settings": {}},\n  "meta": {"filename": "%s.kicad_pro", "version": 1},\n'
                 '  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},\n'
                 '  "sheets": [["%s.kicad_sch", ""]],\n'
                 '  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []}\n}\n'
                 % (PROJECT, PROJECT))
    export(sch)
    # net summary for the docs
    nets = {}
    for comp in C:
        for num, n in comp['nets'].items():
            if n:
                nets.setdefault(n, []).append('%s.%s' % (comp['ref'], num))
    print('цепей: %d' % len(nets))
    for n in sorted(nets):
        print('  %-12s %s' % (n, ' '.join(nets[n])))
    return nets


if __name__ == '__main__':
    main()
