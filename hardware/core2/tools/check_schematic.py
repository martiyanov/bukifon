#!/usr/bin/env python3
import sys as _sys; _sys.dont_write_bytecode = True
# -*- coding: utf-8 -*-
"""Cross-check generated CORE-2 netlist against tools/board_def.py:
 - every MCU-module slot pin is on the expected net;
 - every PANEL/BUS/DIG/aux connector pin is on the expected net;
 - no GPIO signal is missing/short-circuited (net must contain the module pin
   and all its peripheral pins);
 - report conflicts count (must be 0 for PRE-FREEZE hand-off).
Exit code != 0 on mismatch."""
import os, sys, xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import board_def as B

MAP = {'3V3': '3V3_PANEL', '5V': '5V_PANEL', 'DGND': 'DGND', 'AGND': 'AGND',
       'BL_ANODE': 'BL_20V', 'BL_CATHODE': 'BL_CATHODE'}

def expected():
    exp = {}
    # MCU module slot
    for r in B.PINMAP:
        sig = r[0]
        net = {'GND':'DGND','3V3_MCU':'3V3_MCU','CHIP_PU':'CHIP_PU',
               'USB_HS_DP':'USB_HS_DP','USB_HS_DM':'USB_HS_DM'}.get(sig, sig)
        exp[('A1', str(r[7]))] = net
    # connectors
    def add_conn(ref, pins):
        for p, sig, *_ in pins:
            exp[(ref, str(p))] = MAP.get(sig, sig)
    for ref, lst in (('J14', B.J14_REV2), ('J15', B.J15_REV2), ('J16', B.J16_REV2),
                     ('J17', [(p, s) for p, s, *_ in B.J_PWR3]),
                     ('J18', [(p, s) for p, s, *_ in B.J_PWR4])):
        for p, sig in lst:
            exp[(ref, str(p))] = sig
    for p, sig, kind in B.J_BUS:
        n = p
        port = 'P1' if True else ''
        # per-port nets are generated in the schematic: 12V_P1/2, N12V_P1/2
    # bus per-port nets
    for idx, ref in enumerate(('P1', 'P2'), 1):
        for p, sig, kind in B.J_BUS:
            net = MAP.get(sig, sig)
            if sig == '12V_B': net = '12V_P%d' % idx
            elif sig == '-12V_B': net = 'N12V_P%d' % idx
            exp[(ref, str(p))] = net
    # rear TB
    for p, sig, tb in B.TB_REAR:
        exp[(tb.split('.')[0], tb.split('.')[1])] = sig  # rear TB: unfiltered rails
    # USB-C
    usb = {'A1':'DGND','A4':'VBUS_CHG','A5':'CC1','A6':'USB_DP_C','A7':'USB_DM_C',
           'A8':'NC','A9':'VBUS_CHG','A12':'DGND','B1':'DGND','B4':'VBUS_CHG',
           'B5':'CC2','B6':'USB_DP_C','B7':'USB_DM_C','B8':'NC','B9':'VBUS_CHG',
           'B12':'DGND','SH':'DGND'}
    for p, n in usb.items(): exp[('J1', p)] = n
    sd = {'1':'NC','2':'NC','3':'SD_CMD','4':'3V3','5':'SD_CLK','6':'DGND',
          '7':'SD_D0','8':'NC','9':'SD_CD','SH':'DGND'}
    for p, n in sd.items(): exp[('J5', p)] = n
    # J19 mic canon (mates PANEL-2 J16 1:1): 1 BCK, 2 GND, 3 WS, 4 GND, 5 DATA, 6 +3V3
    j19 = {'1':'MIC_BCK','2':'DGND','3':'MIC_WS','4':'DGND','5':'MIC_DATA','6':'3V3_MIC'}
    for p, n in j19.items(): exp[('J19', p)] = n
    return exp

def main():
    r = ET.parse(os.path.join(HERE, 'netlist.xml')).getroot()
    act = {}
    for n in r.iter('net'):
        nm = (n.get('name') or '').lstrip('/')
        for d in n.iter('node'):
            act[(d.get('ref'), d.get('pin'))] = nm
    exp = expected()
    bad = 0
    for k, v in sorted(exp.items()):
        if v == 'NC' or v in ('SPARE1', 'SPARE2'):
            continue
        a = act.get(k)
        if a is None:
            print('MISSING pin', k, 'expected', v); bad += 1
        elif a != v:
            print('MISMATCH', k, 'expected', v, 'got', a); bad += 1
    # all PINMAP GPIO signals must exist in netlist
    for row in B.PINMAP:
        if row[1] is None: continue
        sig = row[0]
        if sig in ('GND','3V3_MCU','CHIP_PU'): continue
        found = any(n == sig for n in act.values())
        if not found:
            print('GPIO net missing in netlist:', sig); bad += 1
    print('CORE-2 schematic check: %s (%d mismatches)' % ('PASS' if not bad else 'FAIL', bad))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
