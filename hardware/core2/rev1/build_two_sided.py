#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-
"""Two-sided placement of real footprints + GND zones for rev.1 scaffolds (no routing).
Works on copies in hardware/*/rev1/two-sided/; if DRC is clean, caller may promote."""
import os, sys, re, json, math, shutil
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..','..'))
sys.path.insert(0,HERE)
import import_netlist as N
import pcbnew
KICAD_FP='/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
U=pcbnew.FromMM
CUSTOM={'A1':'A1_P4_MODULE_ADAPTER','U31':'C6_MINI_1','U26':'MP1584_MODULE'}
def find_fp(fn):
    for lib in sorted(os.listdir(KICAD_FP)):
        d=os.path.join(KICAD_FP,lib)
        if os.path.isdir(d) and os.path.exists(os.path.join(d,fn+'.kicad_mod')): return d,fn
    return None,None
def load_fp(bid,ref,fpname):
    if bid=='CORE-2' and ref in CUSTOM:
        return pcbnew.FootprintLoad(os.path.join(ROOT,'hardware','core2','rev1','footprints'),CUSTOM[ref])
    if bid.startswith('PANEL-2') and ref.startswith('KEY'):
        return pcbnew.FootprintLoad(os.path.join(ROOT,'hardware','panel2','rev1','footprints'),'CHOC_V1')
    if fpname and fpname.startswith('lib:'): fpname=fpname[4:]
    if not fpname or fpname.startswith('—'):
        fpname={'SW1':'Button_Switch_THT:SW_PUSH_6mm','TH1':'Resistor_SMD:R_0805_2012Metric'}.get(ref,'')
    if not fpname: return None
    if ':' in fpname:
        lib,fn=fpname.split(':',1); p=os.path.join(KICAD_FP,lib+'.pretty')
        if os.path.exists(os.path.join(p,fn+'.kicad_mod')): return pcbnew.FootprintLoad(p,fn)
    p,fn=find_fp(fpname)
    return pcbnew.FootprintLoad(p,fn) if p else None
def extent(fp):
    xs=[];ys=[]
    for pad in fp.Pads():
        p=pad.GetPosition(); s=pad.GetSize()
        xs += [pcbnew.ToMM(p.x-s.x/2),pcbnew.ToMM(p.x+s.x/2)]
        ys += [pcbnew.ToMM(p.y-s.y/2),pcbnew.ToMM(p.y+s.y/2)]
    if not xs: return 3,3
    return max(2.0,max(xs)-min(xs)+0.5), max(2.0,max(ys)-min(ys)+0.5)
def pack(items,W,H,holes,special):
    # items: list (ref,w,h); special: ref->(x,y); shelf packing, top-left origin, margin
    placed={}; occ=[]
    def clash(x,y,w,h):
        for ox,oy,ow,oh in occ:
            if abs(x-ox)<(w+ow)/2+0.7 and abs(y-oy)<(h+oh)/2+0.7: return True
        for hx,hy in holes:
            nx=min(max(hx,x-w/2),x+w/2); ny=min(max(hy,y-h/2),y+h/2)
            if math.hypot(hx-nx,hy-ny)<1.8: return True
        return False
    for ref,(x,y) in special.items():
        if ref not in dict((r,(w,h)) for r,w,h in items): continue
        w,h=dict((r,(w,h)) for r,w,h in items)[ref]
        x=min(max(x,w/2+3),W-w/2-3); y=min(max(y,h/2+3),H-h/2-3)
        placed[ref]=(x,y,w,h); occ.append((x,y,w,h))
    rest=[(r,w,h) for r,w,h in items if r not in placed]
    rest.sort(key=lambda t:-(t[1]*t[2]))
    x0=3.0;y0=3.0;gap=0.7;x=x0;y=y0;row_h=0
    for ref,w,h in rest:
        tries=0
        while True:
            if x < w/2+3: x=w/2+3
            if y < h/2+3: y=h/2+3
            if x+w/2>W-3: x=x0; y+=row_h+gap; row_h=0; tries+=1
            if y+h/2>H-3:
                # fallback compact pass
                gap=max(0.2,gap*0.6); x=w/2+3; y=h/2+3; row_h=0; tries+=1
                if tries>400: break
            if not clash(x,y,w,h): break
            x+=w+gap; tries+=1
            if tries>6000: break
        placed[ref]=(x,y,w,h); occ.append((x,y,w,h)); row_h=max(row_h,h); x+=w+gap
    return placed
def subtract(free,ox0,oy0,ox1,oy1):
    out=[]
    for (x0,y0,x1,y1) in free:
        if ox1<=x0 or ox0>=x1 or oy1<=y0 or oy0>=y1: out.append((x0,y0,x1,y1)); continue
        if oy0>y0: out.append((x0,y0,x1,oy0))
        if oy1<y1: out.append((x0,oy1,x1,y1))
        if ox0>x0: out.append((x0,max(y0,oy0),ox0,min(y1,oy1)))
        if ox1<x1: out.append((ox1,max(y0,oy0),x1,min(y1,oy1)))
    return [r for r in out if r[2]-r[0]>1 and r[3]-r[1]>1]
def add_zone(board,net,rects,layers):
    for layer in layers:
        for (x0,y0,x1,y1) in rects:
            z=pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net)
            z.SetLocalClearance(U(0.2)); z.SetThermalReliefGap(U(0.25)); z.SetThermalReliefSpokeWidth(U(0.35))
            z.SetMinThickness(U(0.3)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
            o=z.Outline(); o.NewOutline()
            for (x,y) in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]: o.Append(U(x),U(y))
            board.Add(z)
JOBS=[('CORE-2','core2','hardware/core2/rev1/CORE-2-rev1.kicad_pcb','hardware/core2/netlist.xml','hardware/core2/BOM-core2.csv'),
      ('PANEL-2-left','panel2','hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv'),
      ('PANEL-2-right','panel2','hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb','hardware/panel2/PANEL-2.net','hardware/panel2/BOM-panel2.csv'),
      ('PWR-2','power2','hardware/power2/rev1/PWR-2-rev1.kicad_pcb','hardware/power2/netlist.xml','hardware/power2/BOM-power2.csv')]
spec=json.load(open(os.path.join(ROOT,'mechanical','board-fit','board-spec.json'),encoding='utf-8'))
by={b['id']:b for b in spec['boards']}
for bid,base,rel,net,bom in JOBS:
    b=by[bid]; W,H=b['outline']['size']; src=os.path.join(ROOT,rel)
    dst=os.path.join(ROOT,'hardware',base,'rev1','two-sided',os.path.basename(rel))
    shutil.copy2(src,dst)
    if net.endswith('.xml'): comps,nets=N.parse_xml(os.path.join(ROOT,net))
    else: comps,nets=N.parse_panel(os.path.join(ROOT,net))
    comps={r:c for r,c in comps.items() if not re.match(r'^H\d+$',r)}
    bm=N.bom_map(os.path.join(ROOT,bom)); specmap={r:v[4] for r,v in getattr(N,'CORE_REAL',{}).items()} if bid=='CORE-2' else {}
    if bid.startswith('PANEL-2'):
        comps,special=N.split_panel(comps,'left' if bid.endswith('left') else 'right',b,H)
    else: special={}
    board=pcbnew.LoadBoard(dst)
    netitems={ni.GetNetname():ni for ni in board.GetNetInfo().NetsByNetcode().values()}
    for name in sorted(nets):
        nm=name.lstrip('/')
        if nm not in netitems:
            ni=pcbnew.NETINFO_ITEM(board,nm); board.Add(ni); netitems[nm]=ni
    fps={}; sizes={}; missing=[]
    for ref,c in comps.items():
        fp=load_fp(bid,ref,c.get('fplib') or bm.get(ref,'') or specmap.get(ref,''))
        if fp is None: missing.append((ref,bm.get(ref,''))); continue
        fp.SetReference(ref); fp.SetValue(c.get('value','') or '')
        w,h=extent(fp); fps[ref]=fp; sizes[ref]=(w,h)
    for ref,_ in missing: comps.pop(ref,None)
    if missing: print('MISSING',bid,missing[:6],'...')
    # side assignment: top = connectors/ICs/keys/encoders/mechanical; bottom = passives
    top=[r for r in comps if re.match(r'^(A1|U|J|SW|KEY|ENC|F\d|LED|TB|P\d)',r) or r in ('A1',)]
    top=[r for r in top if r in comps]
    bottom=[r for r in comps if r not in top]
    # balance: if top area > 0.65 total, move large passives to top
    top_area=sum(sizes[r][0]*sizes[r][1] for r in top)
    tot=sum(sizes[r][0]*sizes[r][1] for r in sizes)
    if top_area > 0.70*tot:
        # move passives from top to bottom until ~60 %
        for r in sorted([r for r in top if re.match(r'^[RCDQL]',r)], key=lambda r:-sizes[r][0]*sizes[r][1]):
            if top_area <= 0.60*tot: break
            top.remove(r); bottom.append(r); top_area -= sizes[r][0]*sizes[r][1]
    elif top_area < 0.40*tot:
        for r in sorted(bottom,key=lambda r:-sizes[r][0]*sizes[r][1]):
            if top_area >= 0.50*tot: break
            top.append(r); bottom.remove(r); top_area += sizes[r][0]*sizes[r][1]
    holes=[(h['local'][0],H-h['local'][1]) for h in b.get('mounting',{}).get('holes',[])]
    placed_top=pack([(r,*sizes[r]) for r in top],W,H,holes,{r:special[r] for r in special if r in top})
    placed_bot=pack([(r,*sizes[r]) for r in bottom],W,H,holes,{})
    for r in top:
        fp=fps[r]; fp.SetLayer(pcbnew.F_Cu); fp.SetPosition(pcbnew.VECTOR2I(U(placed_top[r][0]),U(placed_top[r][1])))
        board.Add(fp)
    for r in bottom:
        fp=fps[r]; fp.SetLayer(pcbnew.B_Cu); fp.SetPosition(pcbnew.VECTOR2I(U(placed_bot[r][0]),U(placed_bot[r][1])))
        board.Add(fp)
    pin_net={}
    for name,nodes in nets.items():
        for r,p in nodes: pin_net.setdefault(r,{})[str(p)]=name.lstrip('/')
    for r in top+bottom:
        fp=fps[r]
        for pad in fp.Pads():
            nm=pin_net.get(r,{}).get(pad.GetNumber())
            if nm and nm in netitems: pad.SetNet(netitems[nm])
    # GND zones avoiding all keepouts
    obst=[]
    for k in b.get('keepouts',[]):
        if k.get('type')=='rect':
            x0,y0,x1,y1=k['rect_local']; obst.append((k['id'],max(0,x0),H-min(H,y1),min(W,x1),H-max(0,y0)))
        else:
            cx,cy,rr=k['circle_local']; obst.append((k['id'],max(0,cx-rr),H-min(H,cy+rr),min(W,cx+rr),H-max(0,cy-rr)))
    rects=[(1.0,1.0,W-1.0,H-1.0)]
    for o in obst: rects=subtract(rects,o[1],o[2],o[3],o[4])
    gnd=netitems.get('GND'); layers=[pcbnew.F_Cu,pcbnew.B_Cu]
    g=rects
    if gnd:
        if bid=='CORE-2': g=subtract(g,*[(158,62,199,106)])
        if bid=='PWR-2': g=subtract(g,*[(2,2,46,46)])
        add_zone(board,gnd,g,layers)
    if bid=='CORE-2' and 'AGND' in netitems: add_zone(board,netitems['AGND'],[(158,62,199,106)],layers)
    if bid=='PWR-2' and 'PGND' in netitems: add_zone(board,netitems['PGND'],[(2,2,46,46)],layers)
    # stitching vias, avoid keepouts
    if gnd:
        def bad(x,y):
            return any(x0<=x<=x1 and y0<=y<=y1 for (_n,x0,y0,x1,y1) in obst)
        pts=[]
        xx=2.0
        while xx<W-2: pts += [(xx,2.0),(xx,H-2.0)]; xx+=8
        yy=2.0
        while yy<H-2: pts += [(2.0,yy),(W-2.0,yy)]; yy+=8
        for (x,y) in pts:
            if bad(x,y): continue
            v=pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(U(x),U(y)))
            v.SetDrill(U(0.3)); v.SetWidth(U(0.6)); v.SetNet(gnd); v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); board.Add(v)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(dst,board)
    print('%-14s top=%d bottom=%d zones=%d' % (bid,len(top),len(bottom),len(board.Zones())))
