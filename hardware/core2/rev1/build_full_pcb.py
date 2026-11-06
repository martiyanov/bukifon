#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-
"""CORE-2/PANEL-2/PWR-2 rev.1: real footprints for ALL components + GND/AGND/PGND zones
+ via stitching. No routing. Run with KiCad Python 3.9."""
import os, sys, re, json, math
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..','..'))
sys.path.insert(0,HERE); import import_netlist as N
import pcbnew
KICAD_FP='/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
U=pcbnew.FromMM
CUSTOM={'A1':'A1_P4_MODULE_ADAPTER','U31':'C6_MINI_1','U26':'MP1584_MODULE'}
def _find(fn):
    for lib in sorted(os.listdir(KICAD_FP)):
        d=os.path.join(KICAD_FP,lib)
        if os.path.isdir(d) and os.path.exists(os.path.join(d,fn+'.kicad_mod')): return d,fn
    return None,None
def load_fp(bid, ref, fpname):
    if ref in CUSTOM and bid=='CORE-2':
        d=os.path.join(ROOT,'hardware','core2','rev1','footprints'); return pcbnew.FootprintLoad(d,CUSTOM[ref])
    if bid.startswith('PANEL-2') and ref.startswith('KEY'):
        d=os.path.join(ROOT,'hardware','panel2','rev1','footprints'); return pcbnew.FootprintLoad(d,'CHOC_V1')
    if fpname and fpname.startswith('lib:'): fpname=fpname[4:]
    if not fpname or fpname.startswith('—'): 
        fpname={'SW1':'Button_Switch_THT:SW_PUSH_6mm','TH1':'Resistor_SMD:R_0805_2012Metric'}.get(ref,'')
    if not fpname: return None
    if ':' in fpname:
        lib,fn=fpname.split(':',1); p=os.path.join(KICAD_FP,lib+'.pretty')
        if os.path.exists(os.path.join(p,fn+'.kicad_mod')): return pcbnew.FootprintLoad(p,fn)
    p,fn=_find(fpname)
    if p: return pcbnew.FootprintLoad(p,fn)
    return None
def pad_extent(fp):
    xs=[];ys=[]
    for pad in fp.Pads():
        p=pad.GetPosition(); xs.append(pcbnew.ToMM(p.x)); ys.append(pcbnew.ToMM(p.y))
        s=pad.GetSize(); xs += [pcbnew.ToMM(p.x-s.x/2), pcbnew.ToMM(p.x+s.x/2)]
        ys += [pcbnew.ToMM(p.y-s.y/2), pcbnew.ToMM(p.y+s.y/2)]
    if not xs: return 3.0,3.0
    return max(2.0,max(xs)-min(xs)+0.8), max(2.0,max(ys)-min(ys)+0.8)
def place(comps,W,H,holes,forb,sizes):
    """MaxRects bin packing into board rectangle; obstacles = keepouts + holes."""
    free=[(0.0,0.0,W,H)]
    def subtract(free, ox0,oy0,ox1,oy1):
        out=[]
        for (x0,y0,x1,y1) in free:
            if ox1<=x0 or ox0>=x1 or oy1<=y0 or oy0>=y1: out.append((x0,y0,x1,y1)); continue
            if oy0>y0: out.append((x0,y0,x1,oy0))
            if oy1<y1: out.append((x0,oy1,x1,y1))
            if ox0>x0: out.append((x0,max(y0,oy0),ox0,min(y1,oy1)))
            if ox1<x1: out.append((ox1,max(y0,oy0),x1,min(y1,oy1)))
        return [r for r in out if r[2]-r[0]>0.4 and r[3]-r[1]>0.4]
    for (_n,fx0,fy0,fx1,fy1) in forb:
        free=subtract(free,fx0-0.8,fy0-0.8,fx1+0.8,fy1+0.8)
    for (hx,hy) in holes:
        free=subtract(free,hx-4.0,hy-4.0,hx+4.0,hy+4.0)
    placed={}
    refs=sorted(comps, key=lambda r: -(sizes[r][0]*sizes[r][1]))
    for ref in refs:
        w,h=sizes[ref]; w+=0.6; h+=0.6
        best=None
        for (x0,y0,x1,y1) in free:
            fw=x1-x0; fh=y1-y0
            if w<=fw and h<=fh:
                score=min(fw-w, fh-h)
                if best is None or score<best[0]: best=(score,x0,y0,x1,y1)
        if best is None:
            placed[ref]=(W/2,H/2,sizes[ref][0],sizes[ref][1]); continue
        _,x0,y0,x1,y1=best
        px=x0+w/2; py=y0+h/2
        placed[ref]=(px,py,sizes[ref][0],sizes[ref][1])
        free=subtract(free,x0,y0,px+w/2,py+h/2)
    return placed

def split_rect(W,H,forb):
    rects=[(0.5,0.5,W-0.5,H-0.5)]
    for (_n,fx0,fy0,fx1,fy1) in forb:
        out=[]
        for (x0,y0,x1,y1) in rects:
            if fx1<=x0 or fx0>=x1 or fy1<=y0 or fy0>=y1: out.append((x0,y0,x1,y1)); continue
            if fy0>y0: out.append((x0,y0,x1,fy0))
            if fy1<y1: out.append((x0,fy1,x1,y1))
            if fx0>x0: out.append((x0,max(y0,fy0),fx0,min(y1,fy1)))
            if fx1<x1: out.append((fx1,max(y0,fy0),x1,min(y1,fy1)))
        rects=out
    return [r for r in rects if r[2]-r[0]>1.0 and r[3]-r[1]>1.0]
def add_zone(board,net,rects,layer):
    for (x0,y0,x1,y1) in rects:
        z=pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net)
        z.SetLocalClearance(U(0.25)); z.SetThermalReliefGap(U(0.3)); z.SetThermalReliefSpokeWidth(U(0.4))
        z.SetMinThickness(U(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        o=z.Outline(); o.NewOutline()
        for (x,y) in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]: o.Append(U(x),U(y))
        board.Add(z)
def add_stitching(board,net,W,H,margin=1.2,pitch=8.0,skip=None):
    x=margin
    while x<W-margin:
        for y in (margin,H-margin):
            if skip and skip(x,y): continue
            v=pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(U(x),U(y)))
            v.SetDrill(U(0.3)); v.SetWidth(U(0.6)); v.SetNet(net); v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); board.Add(v)
        x+=pitch
    y=margin
    while y<H-margin:
        for x in (margin,W-margin):
            if skip and skip(x,y): continue
            v=pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(U(x),U(y)))
            v.SetDrill(U(0.3)); v.SetWidth(U(0.6)); v.SetNet(net); v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); board.Add(v)
        y+=pitch
def main():
    spec=json.load(open(os.path.join(ROOT,'mechanical','board-fit','board-spec.json'),encoding='utf-8'))
    by={b['id']:b for b in spec['boards']}
    jobs=[('CORE-2','core2','hardware/core2/rev1/CORE-2-rev1.kicad_pcb','hardware/core2/netlist.xml','hardware/core2/BOM-core2.csv'),
          ('PANEL-2-left','panel2','hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv'),
          ('PANEL-2-right','panel2','hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv'),
          ('PWR-2','power2','hardware/power2/rev1/PWR-2-rev1.kicad_pcb','hardware/power2/netlist.xml','hardware/power2/BOM-power2.csv')]
    for bid,base,rel,net,bom in jobs:
        path=os.path.join(ROOT,rel)
        if net.endswith('.xml'): comps,nets=N.parse_xml(os.path.join(ROOT,net))
        else: comps,nets=N.parse_panel(os.path.join(ROOT,net))
        comps={r:c for r,c in comps.items() if not re.match(r'^H\d+$',r)}
        bm=N.bom_map(os.path.join(ROOT,bom)); bdef=by[bid]; W,H=bdef['outline']['size']
        if bid.startswith('PANEL-2'):
            comps,special=N.split_panel(comps,'left' if bid.endswith('left') else 'right',bdef,H)
        board=pcbnew.LoadBoard(path)
        netitems={ni.GetNetname():ni for ni in board.GetNetInfo().NetsByNetcode().values()}
        # add missing nets
        for name in sorted(nets):
            nm=name.lstrip('/')
            if nm not in netitems:
                ni=pcbnew.NETINFO_ITEM(board,nm); board.Add(ni); netitems[nm]=ni
        # load footprints, sizes
        specmap={r:v[4] for r,v in getattr(N,'CORE_REAL',{}).items()} if bid=='CORE-2' else {}
        fps={}; sizes={}
        missing=[]
        for ref,c in comps.items():
            fpname=c.get('fplib') or bm.get(ref,'') or specmap.get(ref,'')
            fp=load_fp(bid,ref,fpname)
            if fp is None: missing.append((ref,fpname)); continue
            fp.SetReference(ref); fp.SetValue(c.get('value','') or '')
            board.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(0,0))
            fps[ref]=fp; sizes[ref]=pad_extent(fp)
        if missing:
            print('  MISSING fps:',missing)
            for ref,_ in missing: comps.pop(ref,None)
        holes=[(h['local'][0],H-h['local'][1]) for h in bdef.get('mounting',{}).get('holes',[])]
        forb=[]
        for k in bdef.get('keepouts',[]):
            if k.get('type')=='rect':
                x0,y0,x1,y1=k['rect_local']
                forb.append((k['id'],max(0,x0),H-min(H,y1),min(W,x1),H-max(0,y0)))
            else:
                cx,cy,r=k['circle_local']; forb.append((k['id'],max(0,cx-r),H-min(H,cy+r),min(W,cx+r),H-max(0,cy-r)))
        placed=place(comps,W,H,holes,forb,sizes)
        pin_net={}
        for name,nodes in nets.items():
            for r,p in nodes: pin_net.setdefault(r,{})[str(p)]=name.lstrip('/')
        for ref,fp in fps.items():
            x,y,w,h=placed[ref]; fp.SetPosition(pcbnew.VECTOR2I(U(x),U(y)))
            for pad in fp.Pads():
                nm=pin_net.get(ref,{}).get(pad.GetNumber())
                if nm and nm in netitems: pad.SetNet(netitems[nm])
        # zones
        gnd=netitems.get('GND'); agnd=netitems.get('AGND'); pgnd=netitems.get('PGND')
        rects=split_rect(W,H,forb)
        cu=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu]
        if bid=='CORE-2': cu=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.In3_Cu,pcbnew.In4_Cu,pcbnew.B_Cu]
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if gnd: add_zone(board,gnd,rects,layer)
        if bid=='CORE-2' and agnd:
            add_zone(board,agnd,[(162,10,198,34)],pcbnew.F_Cu)   # analog right-top in kicad coords
            add_zone(board,agnd,[(162,10,198,34)],pcbnew.B_Cu)
        if bid=='PWR-2' and pgnd:
            add_zone(board,pgnd,[(2,2,44,44)],pcbnew.F_Cu); add_zone(board,pgnd,[(2,2,44,44)],pcbnew.B_Cu)
        if gnd:
            def inside_keepout(x,y):
                for (_n,fx0,fy0,fx1,fy1) in forb:
                    if fx0<=x<=fx1 and fy0<=y<=fy1: return True
                return False
            add_stitching(board,gnd,W,H,skip=inside_keepout)
        filler=pcbnew.ZONE_FILLER(board); filler.Fill(board.Zones())
        pcbnew.SaveBoard(path,board)
        print('%-14s comps=%d placed=%d zones=%d' % (bid,len(comps),len(placed),len(board.Zones())))
if __name__=='__main__': main()
