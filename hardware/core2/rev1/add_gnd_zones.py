#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-
"""Add filled GND/AGND/PGND zones + edge stitching vias to rev.1 scaffolds (no routing).
Zones avoid all board-fit keepouts; vias are not placed inside keepouts."""
import os, sys, json, math
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..','..'))
import pcbnew
U=pcbnew.FromMM
JOBS=[('CORE-2','hardware/core2/rev1/CORE-2-rev1.kicad_pcb'),
      ('PANEL-2-left','hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb'),
      ('PANEL-2-right','hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb'),
      ('PWR-2','hardware/power2/rev1/PWR-2-rev1.kicad_pcb')]
spec=json.load(open(os.path.join(ROOT,'mechanical','board-fit','board-spec.json'),encoding='utf-8'))
by={b['id']:b for b in spec['boards']}
def subtract(free,ox0,oy0,ox1,oy1):
    out=[]
    for (x0,y0,x1,y1) in free:
        if ox1<=x0 or ox0>=x1 or oy1<=y0 or oy0>=y1: out.append((x0,y0,x1,y1)); continue
        if oy0>y0: out.append((x0,y0,x1,oy0))
        if oy1<y1: out.append((x0,oy1,x1,y1))
        if ox0>x0: out.append((x0,max(y0,oy0),ox0,min(y1,oy1)))
        if ox1<x1: out.append((ox1,max(y0,oy0),x1,min(y1,oy1)))
    return [r for r in out if r[2]-r[0]>1.0 and r[3]-r[1]>1.0]
def add_zone(board,net,rects,layer):
    for (x0,y0,x1,y1) in rects:
        z=pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net)
        z.SetLocalClearance(U(0.25)); z.SetThermalReliefGap(U(0.3)); z.SetThermalReliefSpokeWidth(U(0.4))
        z.SetMinThickness(U(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        o=z.Outline(); o.NewOutline()
        for (x,y) in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]: o.Append(U(x),U(y))
        board.Add(z)
def stitching(board,net,W,H,keep,obst):
    def bad(x,y):
        for (_n,x0,y0,x1,y1) in obst:
            if x0<=x<=x1 and y0<=y<=y1: return True
        return False
    pts=[]
    x=1.2
    while x<W-1.2: pts += [(x,1.2),(x,H-1.2)]; x+=8
    y=1.2
    while y<H-1.2: pts += [(1.2,y),(W-1.2,y)]; y+=8
    for (x,y) in pts:
        if bad(x,y): continue
        v=pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(U(x),U(y)))
        v.SetDrill(U(0.3)); v.SetWidth(U(0.6)); v.SetNet(net); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); board.Add(v)
for bid,rel in JOBS:
    b=by[bid]; W,H=b['outline']['size']; path=os.path.join(ROOT,rel)
    board=pcbnew.LoadBoard(path)
    nets={ni.GetNetname():ni for ni in board.GetNetInfo().NetsByNetcode().values()}
    obst=[]
    for k in b.get('keepouts',[]):
        if k.get('type')=='rect':
            x0,y0,x1,y1=k['rect_local']; obst.append((k['id'],max(0,x0),H-min(H,y1),min(W,x1),H-max(0,y0)))
        else:
            cx,cy,r=k['circle_local']; obst.append((k['id'],max(0,cx-r),H-min(H,cy+r),min(W,cx+r),H-max(0,cy-r)))
    rects=[(0.5,0.5,W-0.5,H-0.5)]
    for o in obst: rects=subtract(rects,o[1],o[2],o[3],o[4])
    gnd=nets.get('GND')
    if gnd:
        # reserve AGND/PGND sub-regions: subtract their rects from GND
        reserve=[]
        if bid=='CORE-2': reserve.append((150,68,199.5,107.5))   # analog right-top (kicad coords)
        if bid=='PWR-2': reserve.append((1,1,48,48))
        g=rects
        for r in reserve: g=subtract(g,*r)
        for layer in (pcbnew.F_Cu,pcbnew.B_Cu): add_zone(board,gnd,g,layer)
        stitching(board,gnd,W,H,None,obst)
    if bid=='CORE-2' and 'AGND' in nets:
        r=[(150,68,199.5,107.5)]
        for layer in (pcbnew.F_Cu,pcbnew.B_Cu): add_zone(board,nets['AGND'],r,layer)
    if bid=='PWR-2' and 'PGND' in nets:
        r=[(1,1,48,48)]
        for layer in (pcbnew.F_Cu,pcbnew.B_Cu): add_zone(board,nets['PGND'],r,layer)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path,board)
    print(bid,'zones',len(board.Zones()))
