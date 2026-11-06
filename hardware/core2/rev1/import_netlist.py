#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject netlist components (refs, values, footprints, pads, nets) into rev.1 PCB
scaffolds, with zone-based placement. PRE-FREEZE: no routing; DRC errors must be 0.

Netlist sources: hardware/core2/netlist.xml, hardware/panel2/PANEL-2.net,
hardware/power2/netlist.xml. Footprints: BOM*.csv (Корпус column); missing ones get
PLACEHOLDER_<ref> with correct pad count.
"""
import os, re, csv, sys, math, json, xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CORE_REAL = {
 'A1':(100,55,92,30,'custom:A1_P4_MODULE_ADAPTER'),
 'U31':(46,80,16,19,'custom:C6_MINI_1'),
 'U26':(30,22,24,20,'custom:MP1584_MODULE'),
 'U22':(75,22,5,5,'lib:Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.75x1.75mm'),
 'J6':(20,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J7':(36,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J8':(52,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J9':(68,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J10':(84,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J11':(100,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J13':(116,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J20':(132,94,8,14,'lib:Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal'),
 'J12':(180,94,14,12,'lib:Connector_BarrelJack:BarrelJack_CUI_PJ-063AH_Horizontal'),
 'SW1':(40,34,7,7,'lib:Button_Switch_THT:SW_PUSH_6mm'),
 'SW2':(54,34,7,7,'lib:Button_Switch_THT:SW_PUSH_6mm'),
 'SW3':(68,34,7,7,'lib:Button_Switch_THT:SW_PUSH_6mm'),
}
PANEL_KEY_SIZE=(19,19,'custom:CHOC_V1')
REAL_MAP={'CORE-2':{}}


# ---------- sexpr parser (panel2 legacy netlist) ----------
def tok(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace(): i += 1; continue
        if c in '()': yield c; i += 1; continue
        if c == '"':
            j = i+1; buf=[]
            while j < n:
                if s[j] == '\\' and j+1 < n: buf.append(s[j+1]); j += 2; continue
                if s[j] == '"': break
                buf.append(s[j]); j += 1
            yield ('STR', ''.join(buf)); i = j+1; continue
        j = i
        while j < n and not s[j].isspace() and s[j] not in '()': j += 1
        yield ('ATOM', s[i:j]); i = j

def parse(s):
    stack=[[]]
    for t in tok(s):
        if t == '(':
            stack.append([])
        elif t == ')':
            x=stack.pop(); stack[-1].append(x)
        else:
            stack[-1].append(t[1])
    return stack[0][0]

def find(node, name):
    out=[]
    if isinstance(node, list):
        if node and node[0] == name: out.append(node)
        for x in node: out.extend(find(x, name))
    return out

def parse_panel(path):
    tree = parse(open(path, encoding='utf-8').read())
    comps={}; nets={}
    for c in find(tree, 'comp'):
        ref=val=fp=''
        for x in c:
            if isinstance(x,list) and x and x[0]=='ref': ref=x[1]
            if isinstance(x,list) and x and x[0]=='value': val=x[1]
            if isinstance(x,list) and x and x[0]=='footprint': fp=x[1]
        if ref: comps[ref]={'value':val,'fp':fp,'pins':set()}
    for n in find(tree, 'net'):
        name=''; nodes=[]
        for x in n:
            if isinstance(x,list) and x and x[0]=='name': name=x[1]
            if isinstance(x,list) and x and x[0]=='node':
                ref=pin=None
                for y in x:
                    if isinstance(y,list) and y and y[0]=='ref': ref=y[1]
                    if isinstance(y,list) and y and y[0]=='pin': pin=y[1]
                if ref is not None and pin is not None: nodes.append((ref,str(pin)))
        if name and nodes:
            nets.setdefault(name, []).extend(nodes)
            for ref,pin in nodes:
                if ref in comps: comps[ref]['pins'].add(pin)
    return comps, nets

def parse_xml(path):
    r=ET.parse(path).getroot(); comps={}; nets={}
    for c in r.iter('comp'):
        ref=c.get('ref')
        comps[ref]={'value':c.findtext('value') or '', 'fp':c.findtext('footprint') or '', 'pins':set()}
    for n in r.iter('net'):
        name=n.get('name') or ''
        nodes=[(d.get('ref'), str(d.get('pin'))) for d in n.iter('node')]
        if name and nodes:
            nets.setdefault(name, []).extend(nodes)
            for ref,pin in nodes:
                if ref in comps: comps[ref]['pins'].add(pin)
    return comps, nets

# ---------- BOM: ref -> footprint ----------
def bom_map(path):
    m={}
    if not os.path.exists(path): return m
    rows=list(csv.reader(open(path, encoding='utf-8'), delimiter=';'))
    if not rows: return m
    hdr=rows[0]
    def col(*names):
        for i,h in enumerate(hdr):
            for nm in names:
                if nm.lower() in h.lower(): return i
        return None
    i_ref=col('Позиции','Позиционное обозначение'); i_fp=col('Корпус')
    if i_ref is None or i_fp is None: return m
    for r in rows[1:]:
        if len(r)<=max(i_ref,i_fp): continue
        fp=r[i_fp].strip()
        for ref in r[i_ref].split():
            if ref: m[ref]=fp
    return m

# ---------- footprint builder ----------
def fp_text(kind, val, hide=True):
    return ('\t\t(property "%s" "%s" (at 0 0 0)\n\t\t\t(effects (font (size 0.8 0.8)) (hide yes))\n\t\t)' % (kind, val))

def make_footprint(ref, val, fplib, pins, netnums, x, y):
    # fplib: library footprint or PLACEHOLDER_<ref>
    n=len(pins)
    cols=max(1, int(math.ceil(math.sqrt(n))))
    rows=max(1, int(math.ceil(n/cols)))
    pitch=1.0
    body_w=(cols-1)*pitch; body_h=(rows-1)*pitch
    L=[]
    L.append('\t(footprint "%s"' % fplib)
    L.append('\t\t(layer "F.Cu") (uuid "%s") (at %s %s)' % (__import__('uuid').uuid4(), x, y))
    L.append(fp_text('Reference', ref)); L.append(fp_text('Value', val))
    L.append('\t\t(attr smd)')
    for i,pin in enumerate(sorted(pins, key=lambda p: (len(p), p))):
        c=i % cols; r=i // cols
        px=(c-(cols-1)/2.0)*pitch; py=(r-(rows-1)/2.0)*pitch
        net=netnums.get(pin)
        net_s=' (net %d "%s")' % (net[0], net[1]) if net else ''
        L.append('\t\t(pad "%s" smd rect (at %.3f %.3f) (size 0.5 0.8) (layers "F.Cu" "F.Paste" "F.Mask")%s)' % (pin, px, py, net_s))
    L.append('\t)')
    return '\n'.join(L)

def pseudo_size(pins):
    n=max(2,len(pins)); cols=max(1,int(math.ceil(math.sqrt(n)))); rows=max(1,int(math.ceil(n/cols)))
    return max(2.0, cols*1.0+1.0), max(2.0, rows*1.0+1.0)

def place(comps, W, H, holes, special, forbidden):
    """Uniform 7 mm grid for generic (simplified-pad) footprints; real footprints occupy
    reserved slots passed via `forbidden`; holes/antenna are avoided."""
    placed={}; occ=[]
    def clash(x,y,w,h):
        for ox,oy,ow,oh in occ:
            if abs(x-ox) < (w+ow)/2+0.6 and abs(y-oy) < (h+oh)/2+0.6: return True
        for (hx,hy) in holes:
            nx=min(max(hx,x-w/2), x+w/2); ny=min(max(hy,y-h/2), y+h/2)
            if math.hypot(hx-nx, hy-ny) < 2.5: return True
        for (_n,fx0,fy0,fx1,fy1) in forbidden:
            if x+w/2>fx0 and x-w/2<fx1 and y+h/2>fy0 and y-h/2<fy1: return True
        return False
    for ref in comps:
        if ref in special:
            x,y=special[ref]; x=min(max(x,12),W-12); y=min(max(y,12),H-12)
            w,h=pseudo_size(comps[ref]['pins']); placed[ref]=(x,y,w,h); occ.append((x,y,w,h))
    refs=[r for r in comps if r not in special]
    cell=7.0; cols=max(1,int((W-20)//cell)); rows=max(1,int((H-20)//cell))
    if W*H < 12000 or cols*rows < len(refs)*1.2:   # small/tight board: shelf packing
        x0=10.0; y0=10.0; gap=1.8; row_h=0; x=x0; y=y0
        for ref in sorted(refs, key=lambda r: -(pseudo_size(comps[r]['pins'])[0]*pseudo_size(comps[r]['pins'])[1])):
            w,h=pseudo_size(comps[ref]['pins'])
            while True:
                if x+w/2 > W-3: x=x0; y+=row_h+gap; row_h=0
                if y+h/2 > H-3: y=H/2
                if not clash(x,y,w,h): break
                x+=w+gap
            placed[ref]=(x,y,w,h); occ.append((x,y,w,h)); row_h=max(row_h,h); x+=w+gap
        return placed
    cells=[(10+cell/2+c*cell, 10+cell/2+r*cell) for r in range(rows) for c in range(cols)]
    idx=0
    for ref in refs:
        w,h=pseudo_size(comps[ref]['pins']); placed_ok=False
        while idx<len(cells):
            x,y=cells[idx]; idx+=1
            if clash(x,y,w,h): continue
            placed[ref]=(x,y,w,h); occ.append((x,y,w,h)); placed_ok=True; break
        if not placed_ok:
            placed[ref]=(W/2,H/2,w,h); occ.append((W/2,H/2,w,h))
    return placed

def inject(pcb_path, comps, nets, special, forbidden, W, H, holes):
    bid_key = 'PANEL-2' if 'panel2' in pcb_path else ('CORE-2' if 'core2' in pcb_path else 'PWR-2')
    txt=open(pcb_path, encoding='utf-8').read()
    netnums={}; net_lines=[]
    for i,(name,nodes) in enumerate(sorted(nets.items()), 1):
        safe=name.lstrip('/').replace('"','')
        netnums[name]=(i,safe); net_lines.append('\t(net %d "%s")' % (i,safe))
    real_specs={}
    if bid_key.startswith('CORE-2'):
        real_specs=dict(CORE_REAL)
    elif bid_key.startswith('PANEL-2'):
        # keys are real CHOC footprints; positions come from `special`
        for ref in comps:
            if ref.startswith('KEY') and ref in special:
                x,y=special[ref]; real_specs[ref]=(x,y,PANEL_KEY_SIZE[0],PANEL_KEY_SIZE[1],PANEL_KEY_SIZE[2])
    for ref,(x,y,w,h,spec) in real_specs.items():
        forbidden.append((ref,x-w/2-4.0,y-h/2-4.0,x+w/2+4.0,y+h/2+4.0))
    placed=place(comps, W, H, holes, special, forbidden)
    fp_lines=[]
    placeholders=[]
    for ref in sorted(comps):
        if ref in real_specs: continue
        pins=comps[ref]['pins']
        if not pins: pins={'1','2'}
        x,y=placed[ref][0],placed[ref][1]
        fplib=comps[ref].get('fplib') or comps[ref]['fp'] or ('PLACEHOLDER_'+ref)
        # pins -> net names
        pinned={}
        for name,nodes in nets.items():
            for r,p in nodes:
                if r==ref: pinned[p]=netnums[name]
        real=None
        if bid_key.startswith('CORE-2'):
            real=REAL_MAP.get('CORE-2',{}).get(ref)
        elif bid_key.startswith('PANEL-2') and ref.startswith('KEY'):
            real=('custom','CHOC_V1')
        if real:
            txt=embed_mod(bid_key, real[0], real[1], ref, comps[ref]['value'], x, y, pinned)
            if txt: fp_lines.append(txt); continue
        if str(fplib).startswith('PLACEHOLDER'): placeholders.append(ref)
        fp_lines.append(make_footprint(ref, comps[ref]['value'], fplib, pins, pinned, x, y))
    import json as _json
    _json.dump({r:{'x':v[0],'y':v[1],'spec':v[4]} for r,v in real_specs.items()}, open(pcb_path.replace('.kicad_pcb','.real_footprints.json'),'w'), indent=1)
    txt=txt.replace('\t(net 0 "")\n', '\t(net 0 "")\n'+'\n'.join(net_lines)+'\n')
    idx=txt.rstrip().rfind('\n)')
    txt=txt[:idx]+'\n'+'\n'.join(fp_lines)+txt[idx:]
    open(pcb_path,'w',encoding='utf-8').write(txt)


def split_panel(comps, side, bdef, H):
    """Split PANEL-2 netlist refs into left/right boards and assign zones from board-fit."""
    refs=set(comps)
    def grp(pref):
        return sorted([r for r in refs if r.startswith(pref)], key=lambda r:int(re.sub(r'\D','',r) or 0))
    enc=grp('ENC'); key=grp('KEY'); jacks=grp('J'); fad=grp('F')
    jacks10=[j for j in jacks if int(re.sub(r'\D','',j) or 0)<=10]
    conns=[j for j in jacks if j not in jacks10]
    left_spec=set(enc[:8]+key[:21]+jacks10[:5]+[f for f in fad if f=='F1']+conns)
    right_spec=set(enc[8:]+key[21:]+jacks10[5:10]+[f for f in fad if f=='F2'])
    rest=sorted(refs-(left_spec|right_spec))
    if side=='left':
        mine=left_spec | set(rest[::2])
    else:
        mine=right_spec | set(rest[1::2])
    sub={r:comps[r] for r in mine}
    spec={}
    kos=bdef.get('keepouts',[])
    for group, ids in ((enc, [k for k in kos if 'ENC' in k['id']]),
                       (key, sorted([k for k in kos if '_K' in k['id']], key=lambda k:int(re.sub(r'\D','',k['id']) or 0))),
                       (jacks10, [k for k in kos if k['id'].startswith(('J0','J1')) and k.get('type')=='circle']),
                       (fad, [k for k in kos if k['id'] in ('F1','F2')])):
        mine_group=[r for r in group if r in mine]
        for ref,k in zip(mine_group, ids):
            if k.get('type')=='circle':
                cx,cy_local,r=k['circle_local']; spec[ref]=(cx, H-4.0) if k['id'].startswith(('J0','J1')) else (cx, H-cy_local)
            else:
                x0,y0,x1,y1=k['rect_local']; spec[ref]=((x0+x1)/2.0, H-(y0+y1)/2.0)
    return sub, spec

def main():
    jobs=[
     ('CORE-2','hardware/core2/rev1/CORE-2-rev1.kicad_pcb',
      'hardware/core2/netlist.xml','hardware/core2/BOM-core2.csv', (200,108),
      {'J1':(165,102),'U31':(52,96)}, [("C6-antenna",0,88,40,108)]),
     ('PANEL-2-left','hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb',
      'hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv',(180,190),{},[]),
     ('PANEL-2-right','hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb',
      'hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv',(180,190),{},[]),
     ('PWR-2','hardware/power2/rev1/PWR-2-rev1.kicad_pcb',
      'hardware/power2/netlist.xml','hardware/power2/BOM-power2.csv',(90,70),{},[]),
    ]
    for bid, rel, net, bom, (W,H), special, forbidden in jobs:
        if net.endswith('.xml'): comps, nets = parse_xml(os.path.join(ROOT,net))
        else: comps, nets = parse_panel(os.path.join(ROOT,net))
        comps={r:c for r,c in comps.items() if not re.match(r'^H\d+$', r)}
        bm=bom_map(os.path.join(ROOT,bom))
        for ref,c in comps.items():
            fp=bm.get(ref, c['fp'])
            if fp: c['fplib']=fp.split(':')[-1]
            else: c['fplib']='PLACEHOLDER_'+ref
        # board-spec
        spec=json.load(open(os.path.join(ROOT,'mechanical','board-fit','board-spec.json'),encoding='utf-8'))
        bdd={b['id']:b for b in spec['boards']}[bid]
        # panel: split refs left/right + zonal placement from board-fit keepouts
        if bid.startswith('PANEL-2'):
            comps, special = split_panel(comps, 'left' if bid.endswith('left') else 'right', bdd, H)
        # CORE-2 anchors: USB-C at rear edge, C6 at antenna side, MCU center
        if bid=='CORE-2':
            special=dict(special); special['J1']=(165,102); special['U31']=(52,96); special['A1']=(100,55)
        holes=[]
        for hh in bdd.get('mounting',{}).get('holes',[]):
            lx,ly=hh['local']; holes.append((lx,H-ly))
        inject(os.path.join(ROOT,rel), comps, nets, special, forbidden, W, H, holes)
        print('%-14s refs=%-4d nets=%-4d placeholders=%d' % (bid, len(comps), len(nets),
              sum(1 for c in comps.values() if str(c.get('fplib','')).startswith('PLACEHOLDER'))))

if __name__=='__main__':
    main()
