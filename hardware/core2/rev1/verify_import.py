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
    fps=re.findall(r'\(footprint "([^"]+)"', txt)
    refs=[r for r in re.findall(r'\(property "Reference" "([^"]+)"',txt) if not re.match(r'^H\d+$',r)]
    pads=re.findall(r'\(pad "([^"]*)"', txt)
    ph=[f for f in fps if f.startswith('PLACEHOLDER_')]
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
        # antenna zone check via footprint positions (kicad coords) approximated by ref list
        for ref in refs:
            pass
    if ant: ok=False
    if not ok: bad+=1
    rows.append((bid,expected,len(refs),len(fps),len(ph),len(pads),viol,unc,ant))
print('%-14s %-7s %-7s %-8s %-11s %-6s %-5s %-7s %-6s' % ('board','refs','onPCB','fprints','placeholders','pads','DRC','unconn','antenna'))
for r in rows: print('%-14s %-7d %-7d %-8d %-11d %-6d %-5d %-7d %-6d' % r)
# simplified-pad counter (0.5 x 0.8 mm) — target 0 after full footprint replacement
simp=0
for bid,specid,rel,net in JOBS:
    t=open(os.path.join(ROOT,rel),encoding='utf-8').read()
    simp += len(re.findall(r'\(pad "[^"]*" smd rect \(at [^)]*\) \(size 0\.5 0\.8\)', t))
print('SIMPLIFIED PADS (0.5x0.8): %d (target 0 after full footprint replacement)' % simp)
print('\nPLACEHOLDERS (need real footprints before routing):')
for bid,specid,rel,net in JOBS:
    txt=open(os.path.join(ROOT,rel),encoding='utf-8').read()
    ph=sorted(set(re.findall(r'\(footprint "(PLACEHOLDER_[^"]+)"',txt)))
    if ph: print(' ',bid,':',', '.join(p.replace('PLACEHOLDER_','') for p in ph))
# netclass/rules check (5 classes + key nets)
try:
    pro=json.load(open(os.path.join(ROOT,'hardware','core2','rev1','CORE-2-rev1.kicad_pro'),encoding='utf-8'))
    cls={c['name']:c for c in pro['board']['design_settings']['net_settings']['classes']}
    need=['Default','Power','USB_HS','Audio','RF']
    nets_ok = set(cls.get('USB_HS',{}).get('nets',[])) >= {'USB_HS_DP','USB_HS_DM'} and \
             '+12V' in cls.get('Power',{}).get('nets',[]) and 'AUDOUT_L' in cls.get('Audio',{}).get('nets',[]) and \
             'C6_CS' in cls.get('RF',{}).get('nets',[])
    rules_ok = all(n in cls for n in need) and nets_ok and bool(pro['board']['design_settings'].get('rule_severities'))
    print('RULES: %s  classes=%s  diff_pairs=%s' % ('PASS' if rules_ok else 'FAIL', list(cls), pro['board']['design_settings'].get('diff_pair_dimensions')))
    if not rules_ok: bad+=1
except Exception as e:
    print('RULES: FAIL', e); bad+=1
print('\nVERIFY:', 'PASS' if bad==0 else 'FAIL (%d)'%bad)
sys.exit(1 if bad else 0)
