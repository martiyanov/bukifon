#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify PCB scaffolds against mechanical/board-fit/board-spec.json (±0.05 mm)."""
import json, os, re, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SPEC = json.load(open(os.path.join(ROOT, 'mechanical', 'board-fit', 'board-spec.json'), encoding='utf-8'))
TOL = 0.05
JOBS = [
  ('CORE-2', 'hardware/core2/rev1/CORE-2-rev1.kicad_pcb', 6),
  ('PANEL-2-left', 'hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb', 4),
  ('PANEL-2-right', 'hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb', 4),
  ('PWR-2', 'hardware/power2/rev1/PWR-2-rev1.kicad_pcb', 4),
]
by = {b['id']: b for b in SPEC['boards']}
bad = 0
print('%-14s %-22s %-22s %-9s %s' % ('board','size (mm)','outline bbox','area mm2','checks'))
for bid, rel, cu in JOBS:
    p = os.path.join(ROOT, rel); txt = open(p, encoding='utf-8').read()
    b = by[bid]; W,H = b['outline']['size']
    # copper layer count
    cu_ids = re.findall(r'\n\t\t\((\d+) "([FB]\.Cu|In\d+\.Cu)" (?:signal|power)\)', txt)
    # geometry bbox from gr_line / gr_arc
    xs=[]; ys=[]
    for m in re.finditer(r'\(gr_line \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\)', txt):
        xs += [float(m.group(1)), float(m.group(3))]; ys += [float(m.group(2)), float(m.group(4))]
    for m in re.finditer(r'\(gr_arc \(start ([-\d.]+) ([-\d.]+)\) \(mid ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\)', txt):
        xs += [float(m.group(1)), float(m.group(3)), float(m.group(5))]
        ys += [float(m.group(2)), float(m.group(4)), float(m.group(6))]
    ok = True
    if not xs: ok=False
    bb = (min(xs), min(ys), max(xs), max(ys)) if xs else (0,0,0,0)
    if abs(bb[0])>TOL or abs(bb[1])>TOL or abs(bb[2]-W)>TOL or abs(bb[3]-H)>TOL: ok=False
    if len(cu_ids) != cu: ok=False
    # thickness
    if 'thickness 1.6' not in txt: ok=False
    # holes
    holes = b.get('mounting',{}).get('holes',[])
    found = re.findall(r'\(footprint "MountingHole[^"]*"\n\t\t\(layer "F\.Cu"\) \(uuid "[^"]+"\) \(at ([-\d.]+) ([-\d.]+)\)', txt)
    if len(found) != len(holes): ok=False
    hm = []
    for (x,y), h in zip(found, holes):
        lx, ly = float(x), H-float(y)
        sx, sy = h['local']
        if abs(lx-sx)>TOL or abs(ly-sy)>TOL: ok=False
        hm.append('%s:(%.2f,%.2f)' % (h['id'], lx, ly))
    # notches: gr_arc count should equal edge_notches count; radius check
    arcs = re.findall(r'\(gr_arc \(start ([-\d.]+) ([-\d.]+)\) \(mid ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\)', txt)
    notches = b.get('edge_notches', [])
    if len(arcs) != len(notches): ok=False
    # generator emits bottom-edge arcs right-to-left, so match reversed notch order
    for a, n in zip(arcs, list(reversed(notches))):
        x1,y1,xm,ym,x2,y2 = map(float, a)
        cx = n['local'][0]; cy = H - n['local'][1]; r = n['radius']
        for px,py in ((x1,y1),(xm,ym),(x2,y2)):
            if abs(math.hypot(px-cx, py-cy) - r) > TOL: ok=False
    # keepouts: count only those that intersect the board (generator clips/skips outside)
    inside = 0
    for k in b.get('keepouts', []):
        if k.get('type') == 'rect':
            x0,y0,x1,y1 = k['rect_local']
            if min(x1,W) > max(x0,0) and min(H-y0,H) > max(H-y1,0): inside += 1
        else:
            inside += 1
    zones = txt.count('(keepout ')
    if zones != inside: ok=False
    if not ok: bad += 1
    print('%-14s %-22s %-22s %-9.1f %s' % (bid, '%g x %g' % (W,H),
          '(%.2f,%.2f)-(%.2f,%.2f)' % bb, W*H, 'PASS' if ok else 'FAIL'))
    print('    holes:', ' '.join(hm), '| notches:', len(arcs), '| keepouts:', zones, '| Cu:', len(cu_ids))
print('VERIFY:', 'PASS' if bad==0 else 'FAIL (%d)' % bad)
sys.exit(1 if bad else 0)
