#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-
"""Inject netlist components using KiCad's pcbnew Python API (real library footprints).
Run with KiCad bundled Python 3.9:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 import_pcbnew.py
"""
import os, sys, re, json, math, importlib.util
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..','..'))
sys.path.insert(0,HERE)
import import_netlist as N   # parsers/placement helpers (no pcbnew dependency)
import pcbnew
KICAD_FP='/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
U=pcbnew.FromMM

def lib_path(name):
    lib,fn=name.split(':',1)
    return os.path.join(KICAD_FP,lib+'.pretty'), fn

def _find_in_libs(fn):
    for lib in sorted(os.listdir(KICAD_FP)):
        p=os.path.join(KICAD_FP,lib)
        if os.path.isdir(p) and os.path.exists(os.path.join(p,fn+'.kicad_mod')):
            return p, fn
    return None, None

def load_fp(bid, ref, fpname):
    if not fpname: return None
    if ':' in fpname:
        p,fn=lib_path(fpname)
    else:
        rev1=os.path.join(ROOT,'hardware','core2','rev1' if 'core2' in HERE or bid.startswith('CORE-2') else ('panel2' if bid.startswith('PANEL-2') else 'power2'),'rev1','footprints')
        p=os.path.join(ROOT,'hardware',('core2' if bid.startswith('CORE-2') else ('panel2' if bid.startswith('PANEL-2') else 'power2')),'rev1','footprints'); fn=fpname
        if not os.path.exists(os.path.join(p,fn+'.kicad_mod')):
            p,fn=_find_in_libs(fn)
    if not p or not os.path.exists(os.path.join(p,fn+'.kicad_mod')): return None
    return pcbnew.FootprintLoad(p, fn)

def generic_fp(board, ref, val, pins):
    fp=pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID('rev1', 'PLACEHOLDER_'+ref))
    pins=sorted([str(p) for p in pins], key=lambda x:(len(x),x)) or ['1','2']
    n=len(pins); cols=max(1,int(math.ceil(math.sqrt(n)))); rows=max(1,int(math.ceil(n/cols)))
    for i,pin in enumerate(pins):
        pad=pcbnew.PAD(fp); pad.SetNumber(pin)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT); pad.SetSize(pcbnew.VECTOR2I(U(0.8),U(1.2)))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        ls=pcbnew.LSET(); ls.addLayer(pcbnew.F_Cu); ls.addLayer(pcbnew.F_Paste); ls.addLayer(pcbnew.F_Mask)
        pad.SetLayerSet(ls)
        c=i%cols; r=i//cols
        pad.SetPosition(pcbnew.VECTOR2I(U((c-(cols-1)/2.0)*1.0), U((r-(rows-1)/2.0)*1.0)))
        fp.Add(pad)
    return fp

def place(comps, W, H, holes, special, forbidden, fp_sizes):
    placed={}; occ=[]
    def clash(x,y,w,h):
        for ox,oy,ow,oh in occ:
            if abs(x-ox) < (w+ow)/2+1.0 and abs(y-oy) < (h+oh)/2+1.0: return True
        for hx,hy in holes:
            if math.hypot(x-hx,y-hy) < 5.0: return True
        for (_n,fx0,fy0,fx1,fy1) in forbidden:
            if x+w/2>fx0 and x-w/2<fx1 and y+h/2>fy0 and y-h/2<fy1: return True
        return False
    def put(ref):
        x,y=special[ref]; w,h=fp_sizes[ref]
        x=min(max(x,12),W-12); y=min(max(y,12),H-12)
        placed[ref]=(x,y,w,h); occ.append((x,y,w,h))
    for ref in comps:
        if ref in special: put(ref)
    refs=sorted([r for r in comps if r not in special], key=lambda r: -(fp_sizes[r][0]*fp_sizes[r][1]))
    x0=12.0; y0=12.0; gap=1.5; row_h=0; x=x0; y=y0
    for ref in refs:
        w,h=fp_sizes[ref]; tries=0
        while True:
            if x+w/2>W-2: x=x0; y+=row_h+gap; row_h=0; tries+=1
            if y+h/2>H-2:
                x=max(12,min(W-12,x0+((len(placed)*7)%max(1,int((W-24)//5)))*5)); y=H/2
            if not clash(x,y,w,h): break
            x+=w+gap; tries+=1
            if tries>5000: break
        placed[ref]=(x,y,w,h); occ.append((x,y,w,h)); row_h=max(row_h,h); x+=w+gap
    return placed

def main():
    jobs=[('CORE-2','hardware/core2/rev1/CORE-2-rev1.kicad_pcb','hardware/core2/netlist.xml','hardware/core2/BOM-core2.csv',(200,108),{'J1':(165,102),'U31':(52,96),'A1':(100,55)},[('C6-antenna',0,88,40,108)]),
          ('PANEL-2-left','hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv',(180,190),{},[]),
          ('PANEL-2-right','hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv',(180,190),{},[]),
          ('PWR-2','hardware/power2/rev1/PWR-2-rev1.kicad_pcb','hardware/power2/netlist.xml','hardware/power2/BOM-power2.csv',(90,70),{},[])]
    spec=json.load(open(os.path.join(ROOT,'mechanical','board-fit','board-spec.json'),encoding='utf-8'))
    for bid,rel,net,bom,(W,H),special,forb in jobs:
        path=os.path.join(ROOT,rel)
        if net.endswith('.xml'): comps,nets=N.parse_xml(os.path.join(ROOT,net))
        else: comps,nets=N.parse_panel(os.path.join(ROOT,net))
        comps={r:c for r,c in comps.items() if not re.match(r'^H\d+$',r)}
        bm=N.bom_map(os.path.join(ROOT,bom))
        bdef={b['id']:b for b in spec['boards']}[bid]
        if bid.startswith('PANEL-2'):
            comps,special=N.split_panel(comps,'left' if bid.endswith('left') else 'right',bdef,H)
        board=pcbnew.LoadBoard(path)
        # nets
        netmap={}
        for name in sorted(nets):
            nm=name.lstrip('/')
            ni=pcbnew.NETINFO_ITEM(board, nm); board.Add(ni); netmap[name]=ni
        # footprint sizes / load
        fps={}; sizes={}
        for ref,c in comps.items():
            fpname=c.get('fplib') or bm.get(ref,'') or ('PLACEHOLDER_'+ref)
            fp=load_fp(bid, ref, fpname)
            if fp is None and bid.startswith('PANEL-2') and ref.startswith('KEY'):
                fp=load_fp(bid, ref, 'CHOC_V1')
            if fp is None: fp=generic_fp(board, ref, c['value'], c['pins'])
            fp.SetReference(ref); fp.SetValue(c['value'] or '')
            board.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(0,0))
            bb=fp.GetBoundingBox(); w=max(3.0,pcbnew.ToMM(bb.GetWidth())); h=max(3.0,pcbnew.ToMM(bb.GetHeight()))
            sizes[ref]=(w,h); fps[ref]=fp
        holes=[(h['local'][0], H-h['local'][1]) for h in bdef.get('mounting',{}).get('holes',[])]
        placed=place(comps,W,H,holes,special,forb,sizes)
        # add and wire
        pin_net={}
        for name,nodes in nets.items():
            for r,p in nodes: pin_net.setdefault(r,{})[str(p)]=netmap[name]
        for ref,fp in fps.items():
            x,y,w,h=placed[ref]
            fp.SetPosition(pcbnew.VECTOR2I(U(x),U(y)))
            if ref in pin_net:
                for pad in fp.Pads():
                    pn=pad.GetNumber()
                    if pn in pin_net[ref]: pad.SetNet(pin_net[ref][pn])
        pcbnew.SaveBoard(path, board)
        print('%-14s refs=%d nets=%d' % (bid,len(comps),len(nets)))

if __name__=='__main__': main()
