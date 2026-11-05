#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CORE-S3 (народная версия, ESP32-S3-WROOM-1-N16R8) schematic generator.

Derived from CORE-2 rev.2: the analog/CV/MIDI/panel/rear sections are reused,
the P4+C6 MCU + C6 rail + MT3608 #1/#2 + MC34063 + BMS + MP1584/AP2112 rails are
removed; 3V3 is made by a TPS63000 buck-boost from VSYS (D-41); the LCD is SPI.
PRE-FREEZE / DO NOT FABRICATE.
"""
import os, sys, csv, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, '..', 'core2'))
sys.path.insert(0, os.path.join(HERE, '..', 'core2', 'tools'))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import gen_core2_sch as g2          # read-only reuse of helpers/sections
import board_s3 as BS

PROJECT = 'CORE-S3'
g2.HERE = HERE
g2.PROJECT = PROJECT
g2.build_custom_lib()
KICAD_CLI = g2.KICAD_CLI
FP = g2.FP
P, D, A, V, M, R, N = 'POWER', 'MCU', 'AUDIO', 'CV', 'MIDI', 'BUS', 'PANEL'

REMOVE = set('''
A1 U31 R27 C53 C54 C55
U24 L1 D4 R10 R11 C9 C10 C11 C12 R12
U25 L2 D5 R13 R14 C13 C14 C15 C16 R15
U28 R16 C27 L3 D6 R17 R18 C28 C29 C30
U23 Q1 Q2 R7 C8 J2 TH1 R5
U26 C17 C18 C19 FB1 C20 C21 C22
U27 C24 C25 C26 U30 C35 C36 C37
J13 TB2 R73 C99 R74 C100 R105 U44 R90 TP7 TP19 TP21 TP22
'''.split())

RENET = {
 '3V3_MCU': '3V3', '3V3_MCU_RAW': '3V3',
 'CHIP_PU': 'EN_S3',
 'USB_HS_DP': 'USB_FS_DP', 'USB_HS_DM': 'USB_FS_DM',
 'SD_CLK': 'SPI3_SCK', 'SD_CMD': 'SPI3_MOSI', 'SD_D0': 'SPI3_MISO',
 'SD_D1': 'NC', 'SD_D2': 'NC', 'SD_D3': 'SD_CS',
 'SPI2_SCK': 'SPI3_SCK', 'SPI2_MOSI': 'SPI3_MOSI', 'SPI2_MISO': 'SPI3_MISO',
 'LCD_DISP': 'NC', 'STRAP36': 'NC', 'VBUS_DET': 'NC',
}
DROP_NETS = {'3V3_C6', 'BATT_N', 'BQ_BAT', 'TS', 'G_BMS_C', 'G_BMS_D', 'BMS_MID',
             'MC_A', 'MC_SW', 'MC_TC', 'MC_FB', 'SW12', 'FB12', 'EN12',
             'SW5', 'FB5', 'EN5', '12V_BUS', 'SPARE_ADC', 'EXPR', 'EXPR_ADC'}

def new_a1():
    nets = {
     '1':'DGND','2':'3V3','3':'EN_S3','4':'SPI3_SCK','5':'SPI3_MOSI','6':'SPI3_MISO',
     '7':'MCP3208_CS','8':'SD_CS','9':'I2C0_SDA','10':'I2C0_SCL','11':'I2S_MCLK',
     '12':'LCD_RST','13':'USB_FS_DM','14':'USB_FS_DP','15':'GATE2_GPIO','16':'NC','17':'LCD_DC',
     '18':'LCD_CS','19':'LCD_MOSI','20':'LCD_SCK','21':'PWR_GOOD','22':'SD_CD','23':'BL_PWM',
     '24':'PANEL_IRQ','25':'GATE1_GPIO','26':'NC','27':'BOOT','28':'NC','29':'NC','30':'NC',
     '31':'I2S_DAC_DIN','32':'I2S_ADC_DOUT','33':'MIDI_TX','34':'MIDI_RX','35':'LED_GPIO',
     '36':'UART0_RX','37':'UART0_TX','38':'I2S_LRCK','39':'I2S_BCK','40':'DGND','41':'DGND',
    }
    return dict(ref='A1', lib=('RF_Module','ESP32-S3-WROOM-1'),
                val='ESP32-S3-WROOM-1-N16R8 (16 MB flash, 8 MB octal PSRAM)',
                nets=nets, fp='', note='ESP32-S3 module; USB FS; 8 MB octal PSRAM (GPIO33-37 unavailable)',
                sec=M, section=M, unit=1, on_board=True)

def build_C():
    C = []
    for c in g2.C:
        if c['ref'] in REMOVE:
            continue
        nets = {}
        for p, n in c['nets'].items():
            n2 = RENET.get(n, n)
            if n2 in DROP_NETS or n2 == 'NC':
                if n2 == 'NC':
                    nets[p] = 'NC'
                continue
            nets[p] = n2
        c2 = dict(c); c2['nets'] = nets
        C.append(c2)
    C.append(new_a1())
    # SPI display connector J15 (mechanical PANEL-2 J12 FFC-40, SPI subset)
    for c in C:
        if c['ref'] == 'J15':
            c['val'] = 'PANEL-2 J12 (FFC-40) SPI LCD [CORE-S3]'
            c['note'] = 'SPI display subset on PANEL-2 J12 connector: SCK/MOSI/CS/DC/RST/BL; RGB565 pins NC'
            c['nets'] = {str(p): n for p, n in BS.J15_DISPLAY}
    # microSD: SPI mode on SPI3
    sd = {'1':'NC','2':'SD_CS','3':'SPI3_MOSI','4':'3V3','5':'SPI3_SCK','6':'DGND',
          '7':'SPI3_MISO','8':'NC','9':'SD_CD','SH':'DGND'}
    for c in C:
        if c['ref'] == 'J5':
            c['val'] = 'microSD (SPI mode)'
            c['note'] = 'microSD in SPI mode on SPI3 (shared with MCP3208)'
            c['nets'] = sd
        if c['ref'] in ('R30','R31','R32','R33'):
            continue  # SD pullups not needed in SPI mode
    # TPS63000 3V3 buck-boost from VSYS (D-41)
    C.extend([
     dict(ref='U46', lib=('Regulator_Switching','TPS63000'), val='TPS63000 (3.3 V buck-boost)',
          nets={'1':'3V3','2':'LX2','3':'PGND','4':'LX1','5':'VSYS','6':'VSYS',
                '7':'VSYS','8':'VSYS','9':'PGND','10':'FB3V3','11':'PGND'},
          fp='Package_SON:VSON-10-1EP_3x3mm_P0.5mm_EP1.65x2.4mm', note='D-41: 3V3 from VSYS (3.0-4.4 V), 1 A',
          sec=P, section=P, unit=1, on_board=True),
     dict(ref='L5', lib=('Device','L'), val='1.5uH', nets={'1':'LX1','2':'LX2'},
          fp='Inductor_SMD:L_1210_3225Metric', note='TPS63000 inductor', sec=P, section=P, unit=1, on_board=True),
     dict(ref='C122', lib=('Device','C'), val='10uF/10V', nets={'1':'VSYS','2':'PGND'},
          fp=FP['C'], note='', sec=P, section=P, unit=1, on_board=True),
     dict(ref='C123', lib=('Device','C_Polarized'), val='22uF/6.3V', nets={'1':'3V3','2':'PGND'},
          fp=FP['CP'], note='', sec=P, section=P, unit=1, on_board=True),
     dict(ref='C124', lib=('Device','C'), val='22uF/6.3V', nets={'1':'3V3','2':'PGND'},
          fp=FP['C'], note='', sec=P, section=P, unit=1, on_board=True),
     dict(ref='C125', lib=('Device','C'), val='100pF', nets={'1':'3V3','2':'FB3V3'},
          fp=FP['C'], note='feed-forward', sec=P, section=P, unit=1, on_board=True),
     dict(ref='R106', lib=('Device','R'), val='560k', nets={'1':'3V3','2':'FB3V3'},
          fp=FP['R'], note='FB divider: 3.3 V = 0.5*(1+560k/100k)', sec=P, section=P, unit=1, on_board=True),
     dict(ref='R107', lib=('Device','R'), val='100k', nets={'1':'FB3V3','2':'PGND'},
          fp=FP['R'], note='', sec=P, section=P, unit=1, on_board=True),
     dict(ref='C126', lib=('Device','C'), val='100nF', nets={'1':'VSYS','2':'PGND'},
          fp=FP['C'], note='', sec=P, section=P, unit=1, on_board=True),
    ])
    return C

C = build_C()


# test points: drop P4/C6-specific ones, add SPI/PWR_GOOD probes
TPS = [(t, n, w) for (t, n, w) in g2.B.TPS if t not in ('TP7','TP19','TP21','TP22')]
TPS += [('TP23','LCD_SCK','SPI display clock'), ('TP24','LCD_CS','SPI display CS'),
        ('TP25','PWR_GOOD','PWR-2 supervisor')]

FLAGS = ['VBUS_CHG', 'VBUS_F', 'PGND', '12V', '-12V', '5V',
         'VREF33', 'DGND', 'AGND', 'N12_EXT']

SEC_TITLES = dict(BS.SECTIONS)

class Section(g2.Section):
    pass

def make_schematic():
    k = g2.k
    sch = k.Sch(os.path.join(HERE, PROJECT + '.kicad_sch'),
                'CORE-S3 PRE-FREEZE / DO NOT FABRICATE - ESP32-S3 (not for fabrication)',
                paper=g2.PAPER, project=PROJECT)
    sch.text('PRE-FREEZE / DO NOT FABRICATE', (28, 20), size=7.0)
    sch.text('CORE-S3 research schematic - ESP32-S3-WROOM-1-N16R8 (USB FS, 8 MB PSRAM). '
             'Do not order boards before P1 benchmark and spec/90 sign-off.', (28, 26), size=2.6)
    sch.text('GPIO conflicts: 0 (check_pinmap.py). Docs: README.md, pinmap.md, power-tree.md, '
             'interfaces.md, comparison in README. PRE-FREEZE.', (28, 30), size=2.3)
    colA, colB, colC = 22.0, 407.0, 792.0
    top = 46.0
    order = {'POWER': (colA, 0), 'MCU': (colB, 0), 'AUDIO': (colC, 0),
             'CV': (colC, 1), 'MIDI': (colB, 1), 'BUS': (colC, 2),
             'PANEL': (colB, 2), 'TP': (colB, 3)}
    comps = {}; sections = {}; ypos = {colA: top, colB: top, colC: top}
    for secname in ['POWER', 'MCU', 'AUDIO', 'CV', 'MIDI', 'BUS', 'PANEL', 'TP']:
        x0, _ = order[secname]
        sec = Section(sch, SEC_TITLES.get(secname, secname), x0, ypos[x0])
        sections[secname] = sec
        for comp in C:
            if comp['sec'] != secname:
                continue
            c = sec.place(comp, unit=comp['unit'])
            comps.setdefault(comp['ref'], []).append((c, comp))
        ypos[x0] = sec.end_y() + 12.0
    fy = sections['TP'].end_y() + 14.0
    sch.text('POWER FLAGS (net drivers for ERC)', (colB, fy - 4), size=3.0)
    for i, net in enumerate(FLAGS):
        fx = colB + (i % 5) * 20.0
        fyy = fy + 10.0 + (i // 5) * 20.0
        fc = sch.sym('power', 'PWR_FLAG', '#FLG%02d' % (i+1), 'PWR_FLAG', fx, fyy,
                     hide_ref=True, ref_off=(2, -3), val_off=(2, 3))
        sch.net(fc, net, num='1')
    for ref, lst in comps.items():
        for c, comp in lst:
            for p in g2.pin_span(comp['lib'], comp['unit']):
                net = comp['nets'].get(p[0])
                if net is None:
                    continue
                if net == 'NC':
                    sch.nc_pin(c, num=p[0])
                else:
                    sch.net(c, net, num=p[0])
    for ref, lst in comps.items():
        for c, comp in lst:
            for p in g2.pin_span(comp['lib'], comp['unit']):
                if p[0] not in comp['nets']:
                    sch.nc_pin(c, num=p[0])
    sch.write()
    return sch, comps, sections

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout.strip()[:1200])
    if r.returncode != 0: print('STDERR:', r.stderr.strip()[:1500])
    return r

def sanitize():
    import re
    targets = ['netlist.net', 'netlist.xml', PROJECT + '.svg', os.path.join('svg', PROJECT + '.svg'),
               os.path.join('erc', 'erc.rpt'), os.path.join('erc', 'erc.json')]
    for rel in targets:
        path = os.path.join(HERE, rel)
        if not os.path.exists(path): continue
        txt = open(path, encoding='utf-8', errors='ignore').read()
        txt = txt.replace(HERE + os.sep, 'hardware/cores3/').replace('hardware/core2/', 'hardware/cores3/')
        txt = re.sub(r'/(?:' + 'Users|home)/[^"\s<>,;]*', 'hardware/cores3/' + PROJECT + '.kicad_sch', txt)
        open(path, 'w', encoding='utf-8').write(txt)

def exports():
    schfile = os.path.join(HERE, PROJECT + '.kicad_sch')
    os.makedirs(os.path.join(HERE, 'erc'), exist_ok=True)
    prl = os.path.join(HERE, PROJECT + '.kicad_prl')
    if os.path.exists(prl): os.remove(prl)
    warm = os.path.join(HERE, '.warmup')
    subprocess.run([KICAD_CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', warm, schfile],
                   capture_output=True, text=True)
    if os.path.exists(warm): os.remove(warm)
    run([KICAD_CLI, 'sch', 'erc', '--severity-all', '--format', 'report',
         '-o', os.path.join(HERE, 'erc', 'erc.rpt'), schfile])
    run([KICAD_CLI, 'sch', 'export', 'pdf', '-o', os.path.join(HERE, PROJECT + '.pdf'), schfile])
    run([KICAD_CLI, 'sch', 'export', 'svg', '--output', os.path.join(HERE, 'svg'), schfile])
    import shutil
    src = os.path.join(HERE, 'svg', PROJECT + '.svg')
    if os.path.exists(src): shutil.copy(src, os.path.join(HERE, PROJECT + '.svg'))
    run([KICAD_CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
         '-o', os.path.join(HERE, 'netlist.net'), schfile])
    run([KICAD_CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml',
         '-o', os.path.join(HERE, 'netlist.xml'), schfile])
    sanitize()

def write_bom():
    groups = {}
    for c in C:
        key = (c['val'], c['fp'])
        groups.setdefault(key, []).append(c['ref'])
    rows = []
    for i, ((val, fp), refs) in enumerate(sorted(groups.items(), key=lambda kv: kv[0][0])):
        rows.append(['PM-S3-%03d' % (i+1), '', val, str(len(refs)), ' '.join(sorted(refs)),
                     fp or '-', ''])
    with open(os.path.join(HERE, 'BOM-cores3.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['Артикул', 'MPN (draft)', 'Номинал/Тип', 'Кол-во', 'Позиции', 'Корпус', 'Примечание'])
        w.writerows(rows)
    print('BOM rows:', len(rows), '| refs:', len(C))

def write_lib_and_project():
    import json
    custom = g2.build_custom_lib()
    libpath = os.path.join(HERE, 'picomod.kicad_sym')
    with open(libpath, 'w', encoding='utf-8') as fh:
        fh.write('(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "gen_cores3_sch.py")\n'
                 '\t(generator_version "9.0")\n')
        for nm in sorted(custom):
            body = '\n'.join('\t' + ln for ln in custom[nm].split('\n'))
            fh.write(body + '\n')
        fh.write(')\n')
    tbl = open(os.path.join('..', 'core2', 'sym-lib-table'), encoding='utf-8').read()
    tbl = tbl.replace('PicoMod CORE-2 project symbols', 'PicoMod CORE-S3 project symbols')
    open(os.path.join(HERE, 'sym-lib-table'), 'w', encoding='utf-8').write(tbl)
    pro = {'board': {'design_settings': {}}, 'meta': {'filename': PROJECT + '.kicad_pro', 'version': 1},
           'schematic': {'legacy_lib_dir': '', 'legacy_lib_list': []},
           'sheets': [[PROJECT + '.kicad_sch', '']],
           'libraries': {'pinned_footprint_libs': [], 'pinned_symbol_libs': []}}
    open(os.path.join(HERE, PROJECT + '.kicad_pro'), 'w', encoding='utf-8').write(json.dumps(pro, indent=2))

if __name__ == '__main__':
    write_lib_and_project()
    make_schematic()
    exports()
    write_bom()
