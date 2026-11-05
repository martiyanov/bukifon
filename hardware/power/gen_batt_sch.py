#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PWR-BATT-1 — встроенный аккумуляторный блок питания Bukifon (KiCad 10 schematic).

Генерирует hardware/power/PWR-BATT-1.kicad_sch (нативный S-expr, version 20250114),
затем сам запускает kicad-cli: ERC, netlist, PDF, SVG, BOM.

Схема = таблица компонентов + net-label на каждом выводе (как в hardware/core и
hardware/panel): это даёт детерминированную топологию и проверяемый netlist.

Источники истины: spec/20-electronics.md §3 (питание), §8 (разъёмы), §5 (АЦП),
hardware/core/README.md (что уже есть на CORE-1).

Лицензия: CERN-OHL-S-2.0
"""
import os
import sys
import csv
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
from kicad_sch import Sch, pins  # noqa: E402

KC = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
BOARD = 'PWR-BATT-1'
PAPER = 'A2'

FP = {
    'USBC': 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
    'ESOP8': 'Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm',
    'SOT23': 'Package_TO_SOT_SMD:SOT-23',
    'SOT236': 'Package_TO_SOT_SMD:SOT-23-6',
    'R0603': 'Resistor_SMD:R_0603_1608Metric',
    'C0805': 'Capacitor_SMD:C_0805_2012Metric',
    'C1210': 'Capacitor_SMD:C_1210_3225Metric',
    'CP': 'Capacitor_SMD:CP_Elec_6.3x7.7',
    'L': 'Inductor_SMD:L_Bourns-SRN6028',
    'SMA': 'Diode_SMD:D_SMA',
    'FUSE': 'Fuse:Fuse_1206_3216Metric',
    'LED': 'LED_SMD:LED_0603_1608Metric',
    'HOLDER': 'Battery:BatteryHolder_Keystone_1042_1x18650',
    'HDR4': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    'HDR3': 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
    'TB3': 'TerminalBlock_4Ucon:TerminalBlock_4Ucon_1x03_P3.50mm_Vertical',
    'TB2': 'TerminalBlock_4Ucon:TerminalBlock_4Ucon_1x02_P3.50mm_Vertical',
    'SWSPDT': '',   # слайдер MSK-12C02 / SS-12D00, шаг 2.54 — футпринт проектный (см. README)
    'TP': 'TestPoint:TestPoint_Pad_D1.5mm',
    'NTC': '',      # NTC 10k в составе батарейного отсека
}

# (ref, lib, symbol, value, footprint, mpn, note, {pin: net or None(nc)})
PARTS = [
 # ---------------- 1. USB-C зарядный вход ----------------
 ('J1', 'Connector', 'USB_C_Receptacle_USB2.0_16P', 'USB-C 16P (заряд)',
  FP['USBC'], 'HRO TYPE-C-31-M-12', 'зарядный вход 5 В; data-линии не используются (MIDI — на Pico)', {
   'A4': 'USB_VBUS', 'A9': 'USB_VBUS', 'B4': 'USB_VBUS', 'B9': 'USB_VBUS',
   'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'SH': 'GND',
   'A5': 'USB_CC1', 'B5': 'USB_CC2',
   'A6': None, 'A7': None, 'B6': None, 'B7': None, 'A8': None, 'B8': None}),
 ('R1', 'Device', 'R', '5.1k', FP['R0603'], 'RC0603FR-075K1L', 'CC1 → GND: UFP-резистор, разрешает 5 В от USB-C', {'1': 'USB_CC1', '2': 'GND'}),
 ('R2', 'Device', 'R', '5.1k', FP['R0603'], 'RC0603FR-075K1L', 'CC2 → GND: второй UFP-резистор', {'1': 'USB_CC2', '2': 'GND'}),
 ('U1', 'Power_Protection', 'USBLC6-2SC6', 'USBLC6-2SC6', FP['SOT236'], 'USBLC6-2SC6',
  'ESD-защита: I/O на VBUS (данные не используются), т.к. порт только зарядный', {
   '1': 'USB_VBUS', '6': 'USB_VBUS', '3': 'USB_CC1', '4': 'USB_CC1', '5': 'USB_VBUS', '2': 'GND'}),
 ('F2', 'Device', 'Polyfuse', '1.1 A', FP['FUSE'], 'MF-MSMF110 / 1206L110',
  'самовосстанавливающийся предохранитель по VBUS (заряд ≤ 1 А)', {'1': 'USB_VBUS', '2': 'CHG_IN'}),

 # ---------------- 2. Зарядное устройство TP4056 ----------------
 ('U2', 'Battery_Management', 'TP4056-42-ESOP8', 'TP4056', FP['ESOP8'], 'TP4056-42-ESOP8',
  'линейный заряд Li-ion 4.2 В, 1 А; BMS-защита стоит между BAT и банками', {
   '4': 'CHG_IN', '8': 'CHG_IN', '3': 'GND', '9': 'GND', '5': 'SYS_BAT_P',
   '2': 'TP_PROG', '1': 'TEMP_NTC', '6': 'LED_STDBY', '7': 'LED_CHRG'}),
 ('R3', 'Device', 'R', '1.2k', FP['R0603'], 'RC0603FR-071K2L', 'PROG: Iзар = 1000 мА (R = 1200 Ом)', {'1': 'TP_PROG', '2': 'GND'}),
 ('R4', 'Device', 'R', '1k', FP['R0603'], 'RC0603FR-071KL', 'ток LED «ИДЁТ ЗАРЯД» (~3 мА)', {'1': 'CHG_IN', '2': 'LED_A_CHG'}),
 ('R5', 'Device', 'R', '1k', FP['R0603'], 'RC0603FR-071KL', 'ток LED «ЗАРЯД ОКОНЧЕН»', {'1': 'CHG_IN', '2': 'LED_A_STDBY'}),
 ('LED1', 'Device', 'LED', 'RED заряд', FP['LED'], '', 'индикация CHRG (красный)', {'1': 'LED_CHRG', '2': 'LED_A_CHG'}),
 ('LED2', 'Device', 'LED', 'GREEN готово', FP['LED'], '', 'индикация STDBY (зелёный)', {'1': 'LED_STDBY', '2': 'LED_A_STDBY'}),
 ('C1', 'Device', 'C', '10uF', FP['C0805'], 'CL21B106KOQNNNE', 'вход TP4056', {'1': 'CHG_IN', '2': 'GND'}),
 ('C2', 'Device', 'C', '1uF', FP['C0805'], 'CL21B105KBFNNNE', 'выход BAT TP4056', {'1': 'SYS_BAT_P', '2': 'GND'}),
 ('R6', 'Device', 'R', '10k', FP['R0603'], 'RC0603FR-0710KL',
  'верх плеча NTC: TEMP = 5 В · Rntc/(Rntc+10k) → 45…80 % VCC = рабочий диапазон TP4056', {'1': 'CHG_IN', '2': 'TEMP_NTC'}),
 ('TH1', 'Device', 'Thermistor_NTC', 'NTC 10k B3950', FP['NTC'], 'NTC 10k B3950 (в батарейном отсеке)',
  'термистор НА БАНКАХ, подключается через J3 pin3 (второй вывод — B−)', {'1': 'TEMP_NTC', '2': 'BATT_BM'}),
 ('R7', 'Device', 'R', '200k', FP['R0603'], 'RC0603FR-07200KL', 'делитель для АЦП 1/2 (см. R8); нагрузка плеча NTC ≈ 2 %', {'1': 'TEMP_NTC', '2': 'TEMP_ADC'}),
 ('R8', 'Device', 'R', '200k', FP['R0603'], 'RC0603FR-07200KL', 'нижнее плечо TEMP_ADC', {'1': 'TEMP_ADC', '2': 'GND'}),
 ('C3', 'Device', 'C', '100n', FP['C0805'], 'CL21B104KBCNNNC', 'RC-фильтр TEMP_ADC', {'1': 'TEMP_ADC', '2': 'GND'}),

 # ---------------- 3. Батарея 1S2P + BMS + предохранитель + выключатель ----------------
 ('BT1', 'Device', 'Battery_Cell', '18650 3.6V 3.5Ah', FP['HOLDER'], 'LiitoKala / Samsung INR18650-35E',
  'банка 1 из 2 (параллельно); холдер в брюшном отсеке, не на плате', {'1': 'BATT_CELL_P', '2': 'BATT_BM'}),
 ('BT2', 'Device', 'Battery_Cell', '18650 3.6V 3.5Ah', FP['HOLDER'], 'LiitoKala / Samsung INR18650-35E',
  'банка 2 из 2 (параллельно); холдер в брюшном отсеке, не на плате', {'1': 'BATT_CELL_P', '2': 'BATT_BM'}),
 ('J2', 'Connector_Generic', 'Conn_01x04', 'BMS 1S 2P', FP['HDR4'], 'BMS 1S 2P 5 A (DW01A+FS8205A)',
  'готовый BMS-модуль: B−, B+, P−, P+ (защита от переразряда/перезаряда/КЗ)', {
   '1': 'BATT_BM', '2': 'BATT_CELL_P', '3': 'GND', '4': 'SYS_BAT_P'}),
 ('J3', 'Connector_Generic', 'Conn_01x03', 'BAT PACK 3P', FP['TB3'], 'KF128-3P / 3.81 мм',
  'батарейный отсек: 1 = B+, 2 = B−, 3 = NTC', {'1': 'BATT_CELL_P', '2': 'BATT_BM', '3': 'TEMP_NTC'}),
 ('F3', 'Device', 'Polyfuse', '2 A', FP['FUSE'], 'MF-MSMF200 / 1206L200',
  'защита выхода батареи до выключателя (КЗ в шлейфе/плате)', {'1': 'SYS_BAT_P', '2': 'BATT_PROT'}),
 ('SW1', 'Switch', 'SW_SPDT', 'BATT ON/OFF', FP['SWSPDT'], 'MSK-12C02 (SPDT слайдер)',
  'выключатель батареи: полностью отключает банки (хранение/транспорт); положение 2 = OFF', {
   '1': 'BATT_PROT', '2': 'VBAT_SW', '3': None}),
 ('C4', 'Device', 'C', '22uF', FP['C1210'], 'CL32A226KOJNNNE', 'вход буста (импульсный ток)', {'1': 'VBAT_SW', '2': 'GND'}),
 ('R9', 'Device', 'R', '100k', FP['R0603'], 'RC0603FR-07100KL', 'pull-up EN буста (MT3608 включается при EN > 1.5 В)', {'1': 'VBAT_SW', '2': 'BOOST_EN'}),
 ('Q1', 'Transistor_FET', 'Q_NMOS_GSD', '2N7002', FP['SOT23'], '2N7002',
  'гасит EN буста, когда есть внешние 12 В → батарея не разряжается', {'1': 'EXT_DET', '2': 'GND', '3': 'BOOST_EN'}),
 ('C5', 'Device', 'C', '100n', FP['C0805'], 'CL21B104KBCNNNC', 'фильтр EN', {'1': 'BOOST_EN', '2': 'GND'}),
 ('R10', 'Device', 'R', '100k', FP['R0603'], 'RC0603FR-07100KL', 'делитель EXT_DET: 12 В → 2.16 В', {'1': '12V_EXT_F', '2': 'EXT_DET'}),
 ('R11', 'Device', 'R', '22k', FP['R0603'], 'RC0603FR-0722KL', 'нижнее плечо EXT_DET', {'1': 'EXT_DET', '2': 'GND'}),
 ('C6', 'Device', 'C', '100n', FP['C0805'], 'CL21B104KBCNNNC', 'задержка/фильтр EXT_DET (мягкий переход источник→батарея)', {'1': 'EXT_DET', '2': 'GND'}),

 # ---------------- 4. Повышающий преобразователь 12.2 В (MT3608) ----------------
 ('U3', 'Regulator_Switching', 'MT3608', 'MT3608', FP['SOT236'], 'MT3608',
  'boost 1.2 МГц, ключ 2 А; Vout = 0.6·(1+91k/4.7k) = 12.22 В (ОС снимается ПОСЛЕ D2)', {
   '5': 'VBAT_SW', '2': 'GND', '1': 'BOOST_SW', '3': 'FB_NET', '4': 'BOOST_EN', '6': None}),
 ('L1', 'Device', 'L', '22uH / 3A', FP['L'], 'Bourns SRN6028-220M',
  'индуктивность буста (насыщение ≥ 3 А — пиковый ток при 3.6 В → 12 В)', {'1': 'VBAT_SW', '2': 'BOOST_SW'}),
 ('D2', 'Device', 'D_Schottky', 'SS34', FP['SMA'], 'SS34 (SMA)',
  'диод ИЛИ батарейного плеча: не даёт шине 12 В утекать в буст и обратно', {'2': 'BOOST_SW', '1': '12V_BUS'}),
 ('R12', 'Device', 'R', '91k', FP['R0603'], 'RC0603FR-0791KL', 'верх ОС: 12.22 В', {'1': '12V_BUS', '2': 'FB_NET'}),
 ('R13', 'Device', 'R', '4.7k', FP['R0603'], 'RC0603FR-074K7L', 'низ ОС: Vref 0.6 В', {'1': 'FB_NET', '2': 'GND'}),
 ('C7', 'Device', 'C', '22uF/25V', FP['C1210'], 'CL32A226KOJNNNE', 'выход буста 1', {'1': '12V_BUS', '2': 'GND'}),
 ('C8', 'Device', 'C', '22uF/25V', FP['C1210'], 'CL32A226KOJNNNE', 'выход буста 2 (пульсации)', {'1': '12V_BUS', '2': 'GND'}),

 # ---------------- 5. Внешний 12 В, приоритет источника, выходы, контроль ----------------
 ('J4', 'Connector_Generic', 'Conn_01x02', '12V IN', FP['TB2'], 'KF128-2P / 3.81 мм',
  'вход внешнего БП 12 В: идёт с панельного J-DC (5.5/2.1) через пигтейл', {'1': '12V_EXT', '2': 'GND'}),
 ('F1', 'Device', 'Fuse', '2 A', FP['FUSE'], 'MF-MSMF200 / 1206L200',
  'защита входа 12 В (повторяет F1 CORE-1, стоит до пигтейла)', {'1': '12V_EXT', '2': '12V_EXT_F'}),
 ('D3', 'Device', 'D_Schottky', 'SS34', FP['SMA'], 'SS34 (SMA)',
  'диод ИЛИ внешнего плеча + защита от переполюсовки', {'2': '12V_EXT_F', '1': '12V_BUS'}),
 ('D4', 'Device', 'D_TVS', 'SMAJ15A', FP['SMA'], 'SMAJ15A',
  'TVS на входе 12 В (импульсы БП, статика)', {'1': '12V_EXT_F', '2': 'GND'}),
 ('C9', 'Device', 'C', '100uF/25V', FP['CP'], 'Low ESR 100 мкФ 25 В',
  'входной электролит (CORE-1 имеет свой 1000 мкФ после J-DC)', {'1': '12V_EXT_F', '2': 'GND'}),
 ('LED3', 'Device', 'LED', 'GREEN внешний', FP['LED'], '', 'индикатор «внешний БП подключён»', {'2': 'LED_A_EXT', '1': 'GND'}),
 ('R14', 'Device', 'R', '2.2k', FP['R0603'], 'RC0603FR-072K2L', 'ток LED3 ≈ 4.5 мА от 12 В', {'1': '12V_EXT_F', '2': 'LED_A_EXT'}),
 ('LED4', 'Device', 'LED', 'BLUE батарея', FP['LED'], '', 'индикатор «батарея включена» (после SW1)', {'2': 'LED_A_BAT', '1': 'GND'}),
 ('R15', 'Device', 'R', '1k', FP['R0603'], 'RC0603FR-071KL', 'ток LED4 ≈ 1.6 мА', {'1': 'VBAT_SW', '2': 'LED_A_BAT'}),
 ('J5', 'Connector_Generic', 'Conn_01x02', '12V OUT → CORE-1', FP['TB2'], 'KF128-2P / 3.81 мм',
  'выход 12 В на CORE-1 (вход J-DC платы ядра) — все рельсы CORE-1 работают без переделки', {'1': '12V_BUS', '2': 'GND'}),
 ('J6', 'Connector_Generic', 'Conn_01x03', 'MON → MCP3208', FP['HDR3'], 'PH-3P / XH-3P',
  'контроль: 1 = BAT_ADC (CH4), 2 = TEMP_ADC (CH5), 3 = GND', {'1': 'BAT_ADC', '2': 'TEMP_ADC', '3': 'GND'}),
 ('R16', 'Device', 'R', '100k', FP['R0603'], 'RC0603FR-07100KL',
  'делитель VBAT: 3.0 В → 0.96 В, 4.2 В → 1.34 В (шкала АЦП 0…3.3 В)', {'1': 'SYS_BAT_P', '2': 'BAT_ADC'}),
 ('R17', 'Device', 'R', '47k', FP['R0603'], 'RC0603FR-0747KL', 'нижнее плечо BAT_ADC', {'1': 'BAT_ADC', '2': 'GND'}),
 ('C10', 'Device', 'C', '100n', FP['C0805'], 'CL21B104KBCNNNC', 'RC-фильтр BAT_ADC (с R16/R17: 1 кГц)', {'1': 'BAT_ADC', '2': 'GND'}),

 # ---------------- 6. Контрольные точки ----------------
 ('TP1', 'Connector', 'TestPoint', 'VBAT', FP['TP'], '', 'контроль напряжения банок', {'1': 'SYS_BAT_P'}),
 ('TP2', 'Connector', 'TestPoint', '12V_OUT', FP['TP'], '', 'контроль 12.2 В на выходе буста', {'1': '12V_BUS'}),
 ('TP3', 'Connector', 'TestPoint', 'GND', FP['TP'], '', 'земля для измерений', {'1': 'GND'}),
]

FLAGS = ['GND', 'USB_VBUS', 'CHG_IN', 'BATT_PROT', 'VBAT_SW',
         '12V_EXT', '12V_EXT_F', '12V_BUS', 'BATT_CELL_P', 'BATT_BM']

CELL_W, CELL_H = 68.0, 50.0
COLS = 8
X0, Y0 = 30.0, 52.0


def main():
    sch = Sch(os.path.join(HERE, BOARD + '.kicad_sch'),
              'PWR-BATT-1 — аккумуляторный блок питания Bukifon (1S2P Li-ion + USB-C + boost 12.2 В)',
              paper=PAPER, project=BOARD)
    order = sorted(sch.power_rails)

    # ---- titles / block notes -------------------------------------------
    notes = [
        'PWR-BATT-1: 1S2P Li-ion (2x18650, 3.0...4.2 V, 5...7 Ah) -> boost 12.2 V -> J-DC CORE-1',
        '1. J1/R1/R2/U1/F2   USB-C 5 V charge input: UFP 5.1k on CC1/CC2, USBLC6-2SC6 ESD, polyfuse',
        '2. U2/R3..R8/TH1     TP4056 1 A charger (PROG=1.2k), NTC temperature window, ADC dividers',
        '3. BT1/BT2/J2/J3/F3/SW1  battery pack 1S2P + BMS 1S2P (B-/B+/P-/P+) + polyfuse + OFF switch',
        '4. U3/L1/D2/R12/R13  MT3608 boost 12.22 V (Vout=0.6*(1+91k/4.7k), sense AFTER D2)',
        '5. J4/F1/D3/D4/C9     external 12 V input with SS34 OR-ing + TVS; priority = external',
        '6. J5/J6/TP1..TP3    12 V OUT to CORE-1; BAT_ADC/TEMP_ADC to MCP3208 CH4/CH5; test points',
        'Auto source: external 12 V -> EXT_DET (R10/R11) -> Q1 pulls MT3608 EN low -> boost off,',
        'battery not drained. External removed: Q1 off, R9 pulls EN up, boost restarts at 12.22 V.',
        'GND here is one net; on CORE-1 it lands on the PGND/AGND star point (NT1/NT2).',
    ]
    for i, t in enumerate(notes):
        sch.text(t, (X0, 360 + i * 5.4), size=1.6)

    layout = {}
    for i, p in enumerate(PARTS):
        layout[p[0]] = (X0 + (i % COLS) * CELL_W, Y0 + (i // COLS) * CELL_H)

    comps = {}
    for (ref, lib, sym, val, fp, mpn, note, nets) in PARTS:
        x, y = layout[ref]
        c = sch.sym(lib, sym, ref, val, x, y, footprint=fp,
                    props={'MPN': mpn, 'Note': note},
                    ref_off=(0, -10.16), val_off=(0, 10.16))
        comps[ref] = c
        for num, netname in nets.items():
            if netname is None:
                sch.nc_pin(c, num=num)
            else:
                sch.net(c, netname, num=num)

    # ---- PWR_FLAG: ERC требует драйвер на каждой цепи с power_in ---------
    fxs = 560.07   # = 394 * 1.27, на контактной сетке
    for i, net in enumerate(FLAGS):
        y = 39.37 + i * 25.4
        f = sch.sym('power', 'PWR_FLAG', '#FLG%02d' % (i + 1), 'PWR_FLAG', fxs, y, hide_ref=True)
        px, py, _a, _n = sch.pinpt(f, num='1')
        sch.wire((px, py), (px, py + 5.08))
        sch.label(net, (px, py + 5.08), angle=0, justify='left')
        sch.text(net, (px + 14, py + 5.08), size=1.5)

    # ---- net-class note about grounds -----------------------------------


    path = sch.write()
    pro = os.path.join(HERE, BOARD + '.kicad_pro')
    with open(pro, 'w', encoding='utf-8') as f:
        f.write('{\n  "board": {"design_settings": {}},\n  "meta": {"filename": "%s.kicad_pro", "version": 1},\n'
                '  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},\n'
                '  "sheets": [["%s.kicad_sch", ""]],\n'
                '  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []}\n}\n' % (BOARD, BOARD))
    print('written', path, len(PARTS), 'components')

    # ---- exports ---------------------------------------------------------
    os.makedirs(os.path.join(HERE, 'erc'), exist_ok=True)
    os.makedirs(os.path.join(HERE, 'svg'), exist_ok=True)
    schf = os.path.join(HERE, BOARD + '.kicad_sch')
    env = dict(os.environ, XDG_CACHE_HOME='/tmp/kicad-cache-power')
    os.makedirs(env['XDG_CACHE_HOME'], exist_ok=True)

    def run(*args):
        r = subprocess.run([KC] + list(args), capture_output=True, text=True, env=env)
        out = (r.stdout or '') + (r.stderr or '')
        print('  %-42s rc=%d %s' % (args[-1].split('/')[-1], r.returncode, out.strip()[:300]))
        return r

    run('sch', 'erc', '--severity-all', '--format', 'report', '-o',
        os.path.join(HERE, 'erc', 'erc.rpt'), schf)
    run('sch', 'erc', '--severity-all', '--format', 'json', '-o',
        os.path.join(HERE, 'erc', 'erc.json'), schf)
    run('sch', 'export', 'netlist', '-o', os.path.join(HERE, 'netlist.net'), schf)
    run('sch', 'export', 'netlist', '--format', 'kicadxml', '-o', os.path.join(HERE, 'netlist.xml'), schf)
    run('sch', 'export', 'pdf', '-o', os.path.join(HERE, BOARD + '.pdf'), schf)
    run('sch', 'export', 'svg', '-o', os.path.join(HERE, 'svg'), schf)

    # ---- BOM (наш формат: артикул / номинал / корпус / кол-во / MPN) ------
    rows = []
    for i, (ref, lib, sym, val, fp, mpn, note, nets) in enumerate(PARTS):
        rows.append({
            'Артикул': 'PM-PWR-%03d' % (i + 1),
            'Позиция': ref,
            'Номинал / тип': val,
            'Корпус / посадка': fp.split(':')[-1] if fp else '— (в отсеке)',
            'Кол-во': 1,
            'MPN / замены': mpn,
            'Примечание': note,
            'Цена, ₽': '',
        })
    with open(os.path.join(HERE, 'BOM-power.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=';')
        w.writeheader()
        w.writerows(rows)
    print('written BOM-power.csv', len(rows), 'lines')

    # ---- net count sanity -------------------------------------------------
    nets = {}
    for (ref, lib, sym, val, fp, mpn, note, ns) in PARTS:
        for num, n in ns.items():
            if n:
                nets.setdefault(n, []).append('%s.%s' % (ref, num))
    print('nets: %d' % len(nets))
    for n in sorted(nets):
        print('  %-14s %s' % (n, ' '.join(nets[n])))
    return nets


if __name__ == '__main__':
    main()
