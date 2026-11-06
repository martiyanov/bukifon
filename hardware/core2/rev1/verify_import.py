#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify netlist import into PCB scaffolds: every ref, footprint assigned, pad count,
placeholder list, DRC counters, antenna keepout clear."""
import os, re, json, sys, subprocess
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..','..'))
sys.path.insert(0,HERE); import import_netlist as N

JOBS=[('CORE-2','CORE-2','hardware/core2/rev1/CORE-2-rev1.kicad_pcb','hardware/core2/netlist.xml'),
      ('PANEL-2-left','PANEL-2-left','hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb','hardware/panel2/PANEL-2.net'),
      ('PANEL-2-right','PANEL-2-right','hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb','hardware/panel2/PANEL-2.net'),
      ('PWR-2','PWR-2','hardware/power2/rev1/PWR-2-rev1.kicad_pcb','hardware/power2/netlist.xml')]
KICAD='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
bad=0; rows=[]
for bid, specid, rel, net in JOBS:
    if net.endswith('.xml'): comps,_=N.parse_xml(os.path.join(ROOT,net))
    else: comps,_=N.parse_panel(os.path.join(ROOT,net))
    comps={r:c for r,c in comps.items() if not re.match(r'^H\d+$',r)}
    spec=json.load(open(os.path.join(ROOT,'mechanical','board-fit','board-spec.json'),encoding='utf-8'))
    bdef={b['id']:b for b in spec['boards']}[specid]
    if bid.startswith('PANEL-2'):
        comps,_=N.split_panel(comps, 'left' if bid.endswith('left') else 'right', bdef, 190)
    # panel split must match importer
    txt=open(os.path.join(ROOT,rel),encoding='utf-8').read()
    fps=re.findall(r'\n\t\(footprint "([^"]+)"\n\t\t\(layer "F\.Cu"\) \(uuid "[^"]+"\) \(at ([-\d.]+) ([-\d.]+)\)',txt)
    refs=[r for r in re.findall(r'\(property "Reference" "([^"]+)"',txt) if not re.match(r'^H\d+$',r)]
    pads=re.findall(r'\(pad "([^"]+)" smd',txt)
    ph=[f for f in fps if f[0].startswith('PLACEHOLDER_')]
    # DRC report counters
    rpt=os.path.join(ROOT,rel.replace('.kicad_pcb','.drc.rpt'))
    rtxt=open(rpt,encoding='utf-8').read() if os.path.exists(rpt) else ''
    m_viol=re.search(r'Found (\d+) DRC violations',rtxt); viol=int(m_viol.group(1)) if m_viol else -1
    m_unc=re.search(r'Found (\d+) unconnected',rtxt); unc=int(m_unc.group(1)) if m_unc else -1
    expected=len(comps)
    ok = (len(refs)==expected and len(pads)>=expected and viol==0)
    # antenna keepout (CORE-2): local 0..40 x y_up 0..20 -> kicad y H-20..H
    ant=0
    if bid=='CORE-2':
        for name,xs,ys in fps:
            if name.startswith('MountingHole'): continue
            x=float(xs); y=float(ys)
            if x-4 < 40 and x+4 > 0 and y+4 > 88 and y-4 < 108:
                ant+=1; print('  ANTENNA overlap:',name,round(x,1),round(y,1))
    if ant: ok=False
    if not ok: bad+=1
    rows.append((bid,expected,len(refs),len(fps),len(ph),len(pads),viol,unc,ant))
print('%-14s %-7s %-7s %-8s %-11s %-6s %-5s %-7s %-6s' % ('board','refs','onPCB','fprints','placeholders','pads','DRC','unconn','antenna'))
for r in rows: print('%-14s %-7d %-7d %-8d %-11d %-6d %-5d %-7d %-6d' % r)
print('\nPLACEHOLDERS (need real footprints before routing):')
for bid,specid,rel,net in JOBS:
    txt=open(os.path.join(ROOT,rel),encoding='utf-8').read()
    ph=sorted(set(re.findall(r'\(footprint "(PLACEHOLDER_[^"]+)"',txt)))
    if ph: print(' ',bid,':',', '.join(p.replace('PLACEHOLDER_','') for p in ph))
print('\nVERIFY:', 'PASS' if bad==0 else 'FAIL (%d)'%bad)
sys.exit(1 if bad else 0)
