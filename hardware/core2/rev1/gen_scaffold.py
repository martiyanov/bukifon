#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CORE-2/PANEL-2/PWR-2 rev.1 PCB scaffolds from mechanical/board-fit/board-spec.json.

Generates .kicad_pcb with Edge.Cuts (outline + jack notches), NPTH mounting holes,
copper keepout zones, 6/4-layer stackup (1.6 mm). PRE-FREEZE scaffold: no footprints
except mounting holes, no netlist; DRC must be 0 errors.
"""
import json, os, sys, math, uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SPEC = json.load(open(os.path.join(ROOT, 'mechanical', 'board-fit', 'board-spec.json'), encoding='utf-8'))
U = lambda: str(uuid.uuid4())

LAYERS_COMMON = [
 (32,'B.Adhes','user','B.Adhesive'),(33,'F.Adhes','user','F.Adhesive'),
 (34,'B.Paste','user',None),(35,'F.Paste','user',None),
 (36,'B.SilkS','user','B.Silkscreen'),(37,'F.SilkS','user','F.Silkscreen'),
 (38,'B.Mask','user',None),(39,'F.Mask','user',None),
 (40,'Dwgs.User','user','User.Drawings'),(41,'Cmts.User','user','User.Comments'),
 (42,'Eco1.User','user','User.Eco1'),(43,'Eco2.User','user','User.Eco2'),
 (44,'Edge.Cuts','user',None),(45,'Margin','user',None),
 (46,'B.CrtYd','user','B.Courtyard'),(47,'F.CrtYd','user','F.Courtyard'),
 (48,'B.Fab','user',None),(49,'F.Fab','user',None),
]

def layer_lines(copper):
    out = ['\t(layers']
    for i,(num,name,*rest) in enumerate(copper):
        typ = 'power' if (len(rest) and name.startswith(('In1','In4'))) else 'signal'
        out.append('\t\t(%d "%s" %s)' % (num,name,typ))
    for num,name,typ,user in LAYERS_COMMON:
        if user:
            out.append('\t\t(%d "%s" %s "%s")' % (num,name,typ,user))
        else:
            out.append('\t\t(%d "%s" %s)' % (num,name,typ))
    out.append('\t)')
    return out

def stackup(copper):
    # copper = [(num,name,thickness)] ordered top->bottom
    out = ['\t(setup', '\t\t(stackup',
           '\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))',
           '\t\t\t(layer "F.Paste" (type "Top Solder Paste"))',
           '\t\t\t(layer "F.Mask" (type "Top Solder Mask"))']
    diel = 1
    total_cu = sum(t for _,_,t in copper)
    n_diel = len(copper) - 1
    # distribute remaining dielectric to 1.6 mm total
    d_total = max(0.2, 1.6 - total_cu)
    for i,(num,name,t) in enumerate(copper):
        out.append('\t\t\t(layer "%s" (type "copper") (thickness %s))' % (name, t))
        if i < len(copper)-1:
            th = round(d_total / n_diel, 3)
            out.append('\t\t\t(layer "dielectric %d" (type "core") (thickness %s) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))' % (diel, th))
            diel += 1
    out += ['\t\t\t(layer "B.Mask" (type "Bottom Solder Mask"))',
            '\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))',
            '\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))',
            '\t\t\t(copper_finish "None")',
            '\t\t\t(dielectric_constraints no)',
            '\t\t)',
            '\t\t(pad_to_mask_clearance 0)',
            '\t\t(allow_soldermask_bridges_in_footprints no)',
            '\t)']
    return out

def gr_line(x1,y1,x2,y2,layer='Edge.Cuts',width='0.05'):
    return ('\t(gr_line (start %s %s) (end %s %s)\n\t\t(stroke (width %s) (type solid)) (layer "%s") (uuid "%s")\n\t)'
            % (x1,y1,x2,y2,width,layer,U()))

def gr_arc(x1,y1,xm,ym,x2,y2,layer='Edge.Cuts',width='0.05'):
    return ('\t(gr_arc (start %s %s) (mid %s %s) (end %s %s)\n\t\t(stroke (width %s) (type solid)) (layer "%s") (uuid "%s")\n\t)'
            % (x1,y1,xm,ym,x2,y2,width,layer,U()))

def gr_text(t,x,y,layer='F.SilkS',size='1.5'):
    return ('\t(gr_text "%s" (at %s %s 0)\n\t\t(effects (font (size %s %s)) (justify left bottom))\n\t\t(layer "%s") (uuid "%s")\n\t)'
            % (t,x,y,size,size,layer,U()))

def mounting(ref,x,y,dia,post):
    lib = 'MountingHole_M3_3.4mm' if dia >= 3.3 else 'MountingHole_M2.5_2.8mm'
    return ('\t(footprint "%s"\n'
            '\t\t(layer "F.Cu") (uuid "%s") (at %s %s)\n'
            '\t\t(property "Reference" "%s" (at 0 -4.0 0)\n\t\t\t(effects (font (size 1.0 1.0)) (justify left bottom))\n\t\t)\n'
            '\t\t(property "Value" "MountingHole" (at 0 4.0 0)\n\t\t\t(effects (font (size 1.0 1.0)) (justify left top))\n\t\t)\n'
            '\t\t(attr through_hole exclude_from_pos_files exclude_from_bom)\n'
            '\t\t(pad "" np_thru_hole circle (at 0 0) (size %s %s) (drill %s)\n\t\t\t(layers "*.Cu" "*.Mask")\n\t\t)\n'
            '\t)' % (lib,U(),x,y,ref,dia,dia,dia))

def keepout_rect(name,x0,y0,x1,y1,cu_layers,note):
    if x1 <= x0 or y1 <= y0: return ''
    pts = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    layers = ' '.join('"%s"' % l for l in cu_layers)
    s = ('\t(zone (net 0) (net_name "")')
    s += '\n\t\t(layers %s)' % layers
    s += '\n\t\t(name "%s")' % name
    s += '\n\t\t(hatch edge 0.5)'
    s += '\n\t\t(connect_pads (clearance 0))'
    s += '\n\t\t(min_thickness 0.25)'
    s += '\n\t\t(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed))'
    s += '\n\t\t(polygon (pts'
    for x,y in pts:
        s += ' (xy %s %s)' % (x,y)
    s += '))'
    s += '\n\t\t(uuid "%s")' % U()
    s += '\n\t)'
    return s

NO_NOTCH = os.environ.get('NO_NOTCH') == '1'
NO_ZONES = os.environ.get('NO_ZONES') == '1'

def build_board(b, outpath, cu_count=6, cu_thickness=0.035):
    W,H = b['outline']['size']
    copper_ids = {6:[(0,'F.Cu',cu_thickness),(1,'In1.Cu',cu_thickness),(2,'In2.Cu',cu_thickness),
                     (3,'In3.Cu',cu_thickness),(4,'In4.Cu',cu_thickness),(31,'B.Cu',cu_thickness)],
                  4:[(0,'F.Cu',cu_thickness),(1,'In1.Cu',cu_thickness),(2,'In2.Cu',cu_thickness),
                     (31,'B.Cu',cu_thickness)]}[cu_count]
    cu_names = [n for _,n,_ in copper_ids]
    L = []
    L.append('(kicad_pcb')
    L.append('\t(version 20241229)')
    L.append('\t(generator "pcbnew")')
    L.append('\t(generator_version "9.0")')
    L.append('\t(general (thickness 1.6) (legacy_teardrops no))')
    L.append('\t(paper "A3")')
    L.append('\t(title_block')
    L.append('\t\t(title "%s rev.1 PCB scaffold (PRE-FREEZE)")' % b['id'])
    L.append('\t\t(rev "rev.1")')
    L.append('\t\t(company "PicoMod / Bukifon")')
    L.append('\t\t(comment 1 "Edge.Cuts/keepouts from mechanical/board-fit/board-spec.json; do not fabricate")')
    L.append('\t)')
    L += layer_lines(copper_ids)
    L += stackup(copper_ids)
    L.append('\t(net 0 "")')
    # --- Edge.Cuts: rectangle + jack notches on bottom edge (local y up -> kicad y down) ---
    notches = [] if NO_NOTCH else sorted(b.get('edge_notches', []), key=lambda n: n['local'][0])
    # start at top-left, clockwise
    L.append(gr_line(0,0,W,0))
    L.append(gr_line(W,0,W,H))
    # bottom edge right -> left with inward arcs for notches
    cur_x = W
    for n in reversed(notches):
        cx = n['local'][0]; r = n['radius']; cy_local = n['local'][1]
        cy = H - cy_local          # kicad y of circle centre
        chord = math.sqrt(max(r*r - (cy_local)**2, 0.0))
        x_right = cx + chord; x_left = cx - chord
        if x_right < cur_x:
            L.append(gr_line(cur_x,H,x_right,H))
        # arc into board: mid at top of circle (kicad y = cy - r)
        L.append(gr_arc(x_right,H,cx,cy-r,x_left,H))
        cur_x = x_left
    L.append(gr_line(cur_x,H,0,H))
    L.append(gr_line(0,H,0,0))
    # --- mounting holes (NPTH) ---
    for h in b.get('mounting',{}).get('holes',[]):
        lx,ly = h['local']
        L.append(mounting(h['id'], lx, H-ly, h['dia'], h.get('post_dia', h['dia'])))
    # --- keepouts ---
    for k in ([] if NO_ZONES else b.get('keepouts',[])):
        if k.get('type') == 'rect':
            x0,y0,x1,y1 = k['rect_local']
            # local y-up -> kicad y-down; clip to board
            yk0 = H - y1; yk1 = H - y0
            x0c = max(0.2, x0); x1c = min(W-0.2, x1)
            yk0c = max(0.2, yk0); yk1c = min(H-0.2, yk1)
            if x1c > x0c and yk1c > yk0c:
                L.append(keepout_rect(k['id'], x0c, yk0c, x1c, yk1c, cu_names, k.get('note','')))
    # keepout circles -> approximate with rect? generate octagon keepout
    for k in ([] if NO_ZONES else b.get('keepouts',[])):
        if k.get('type') == 'circle':
            cx,cy_local,r = k['circle_local']; cy = H - cy_local
            r = min(r, cx, W-cx, cy, H-cy) if min(cx,W-cx,cy,H-cy) > 0 else r
            if r <= 0: continue
            import math as _m
            pts = [(cx + r*_m.cos(2*_m.pi*i/12), cy + r*_m.sin(2*_m.pi*i/12)) for i in range(12)]
            s = '\t(zone (net 0) (net_name "")\n\t\t(layers %s)\n\t\t(name "%s")\n\t\t(hatch edge 0.5)\n\t\t(connect_pads (clearance 0))\n\t\t(min_thickness 0.25)\n\t\t(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed))\n\t\t(polygon (pts' % (' '.join('"%s"'%l for l in cu_names), k['id'])
            for x,y in pts: s += ' (xy %.3f %.3f)' % (x,y)
            s += '))\n\t\t(uuid "%s")\n\t)' % U()
            L.append(s)
    # labels
    ly = H*0.55
    L.append(gr_text('%s rev.1 scaffold - PRE-FREEZE, do not fabricate' % b['id'], 2, ly, size='1.6'))
    L.append(gr_text('board %s x %s mm; screw %s; %d Cu layers; 1.6 mm' % (W,H,b.get('mounting',{}).get('screw','M3'),cu_count), 2, ly-4.0, size='1.2'))
    L.append(')')
    open(outpath,'w',encoding='utf-8').write('\n'.join(L)+'\n')
    return W,H

def main():
    jobs = [
      ('CORE-2', 'hardware/core2/rev1/CORE-2-rev1.kicad_pcb', 6, 0.035),
      ('PANEL-2-left', 'hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb', 4, 0.035),
      ('PANEL-2-right', 'hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb', 4, 0.035),
      ('PWR-2', 'hardware/power2/rev1/PWR-2-rev1.kicad_pcb', 4, 0.070),
    ]
    by_id = {b['id']: b for b in SPEC['boards']}
    for bid, rel, cu, t in jobs:
        out = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        W,H = build_board(by_id[bid], out, cu, t)
        print('%-14s %sx%s mm  %d Cu  %s' % (bid, W,H, cu, rel))

if __name__ == '__main__':
    main()
