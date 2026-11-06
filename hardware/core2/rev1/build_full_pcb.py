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
    placed={};occ=[]
    def clash(x,y,w,h):
        for ox,oy,ow,oh in occ:
            if abs(x-ox)<(w+ow)/2+0.6 and abs(y-oy)<(h+oh)/2+0.6: return True
        for hx,hy in holes:
            nx=min(max(hx,x-w/2),x+w/2); ny=min(max(hy,y-h/2),y+h/2)
            if math.hypot(hx-nx,hy-ny)<2.0: return True
        for (_n,fx0,fy0,fx1,fy1) in forb:
            if x+w/2>fx0 and x-w/2<fx1 and y+h/2>fy0 and y-h/2<fy1: return True
        return False
    refs=sorted(comps, key=lambda r: -(sizes[r][0]*sizes[r][1]))
    x0=6.0;y0=6.0;gap=0.8;x=x0;y=y0;row_h=0
    for ref in refs:
        w,h=sizes[ref]; tries=0
        while True:
            if x-w/2<2: x=w/2+2
            if y-h/2<2: y=h/2+2
            if x+w/2>W-2: x=x0; y+=row_h+gap; row_h=0; tries+=1
            if y+h/2>H-2:
                # fallback: second compact pass at small gap (scaffold; may overlap)
                gap=max(0.15,gap*0.5); x=w/2+2; y=h/2+2; row_h=0; tries+=1
                if tries>200: break
            if not clash(x,y,w,h): break
            x+=w+gap; tries+=1
            if tries>8000: break
        placed[ref]=(x,y,w,h);occ.append((x,y,w,h));row_h=max(row_h,h);x+=w+gap
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
def add_stitching(board,net,W,H,margin=1.2,pitch=8.0):
    x=margin
    while x<W-margin:
        for y in (margin,H-margin):
            v=pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(U(x),U(y)))
            v.SetDrill(U(0.3)); v.SetWidth(U(0.6)); v.SetNet(net); v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); board.Add(v)
        x+=pitch
    y=margin
    while y<H-margin:
        for x in (margin,W-margin):
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
            if k['id'] in ('C6-antenna','screen') and k.get('type')=='rect':
                x0,y0,x1,y1=k['rect_local']; forb.append((k['id'],max(0,x0),H-min(H,y1),min(W,x1),H-max(0,y0)))
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
        if gnd: add_stitching(board,gnd,W,H)
        filler=pcbnew.ZONE_FILLER(board); filler.Fill(board.Zones())
        pcbnew.SaveBoard(path,board)
        print('%-14s comps=%d placed=%d zones=%d' % (bid,len(comps),len(placed),len(board.Zones())))
if __name__=='__main__': main()
