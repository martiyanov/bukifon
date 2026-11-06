#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-
"""Add real footprints for placeholder refs (sidecar *.real_footprints.json) via pcbnew."""
import os, sys, json, re, math
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..','..'))
sys.path.insert(0,HERE); import import_netlist as N
import pcbnew
KICAD_FP='/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
U=pcbnew.FromMM
JOBS=[('CORE-2','hardware/core2/rev1/CORE-2-rev1','hardware/core2/netlist.xml','hardware/core2/BOM-core2.csv'),
      ('PANEL-2-left','hardware/panel2/rev1/PANEL-2-left-rev1','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv'),
      ('PANEL-2-right','hardware/panel2/rev1/PANEL-2-right-rev1','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv'),
      ('PWR-2','hardware/power2/rev1/PWR-2-rev1','hardware/power2/netlist.xml','hardware/power2/BOM-power2.csv')]
def load(spec, bid):
    if spec.startswith('custom:'):
        name=spec.split(':',1)[1]; d=os.path.join(ROOT,'hardware',('core2' if bid=='CORE-2' else 'panel2'),'rev1','footprints')
        return pcbnew.FootprintLoad(d,name)
    lib,name=spec.split(':',2)[1:]
    return pcbnew.FootprintLoad(os.path.join(KICAD_FP,lib+'.pretty'), name)
for bid,base,net,bom in JOBS:
    path=os.path.join(ROOT,base+'.kicad_pcb'); side=os.path.join(ROOT,base+'.real_footprints.json')
    if not os.path.exists(side): continue
    specs=json.load(open(side)); 
    if not specs: print(bid,'no real refs'); continue
    if net.endswith('.xml'): comps,_=N.parse_xml(os.path.join(ROOT,net))
    else: comps,_=N.parse_panel(os.path.join(ROOT,net))
    board=pcbnew.LoadBoard(path)
    # build net map
    netitems={}
    for code,ni in board.GetNetInfo().NetsByNetcode().items():
        netitems[ni.GetNetname()]=ni
    # pins -> net per ref from netlist
    nets={}
    if net.endswith('.xml'):
        import xml.etree.ElementTree as ET
        r=ET.parse(os.path.join(ROOT,net)).getroot()
        for n in r.iter('net'):
            for d in n.iter('node'):
                nets.setdefault(d.get('ref'),{})[str(d.get('pin'))]=(n.get('name') or '').lstrip('/')
    else:
        _,nmap=N.parse_panel(os.path.join(ROOT,net))
        for nm,nodes in nmap.items():
            for ref,pin in nodes: nets.setdefault(ref,{})[str(pin)]=nm.lstrip('/')
    for ref,info in specs.items():
        fp=load(info['spec'],bid)
        if fp is None: print('FAIL load',ref,info['spec']); continue
        board.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(U(info['x']),U(info['y'])))
        fp.SetReference(ref); fp.SetValue(comps.get(ref,{}).get('value','') or '')
        for pad in fp.Pads():
            nm=nets.get(ref,{}).get(pad.GetNumber())
            if nm and nm in netitems: pad.SetNet(netitems[nm])
    pcbnew.SaveBoard(path, board)
    print(bid,'added real:',len(specs))
