#!/usr/bin/env bash
# Fab dry-run export from PCB rev.1 scaffolds (NO PCB order). See docs/83 §8.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KC="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
BOARDS="core2 panel2-left panel2-right power2"
for b in $BOARDS; do
  case "$b" in
    core2)      PCB="$ROOT/hardware/core2/rev1/CORE-2-rev1.kicad_pcb";   BOM="$ROOT/hardware/core2/BOM-core2.csv";   SPECID="CORE-2" ;;
    panel2-left) PCB="$ROOT/hardware/panel2/rev1/PANEL-2-left-rev1.kicad_pcb"; BOM="$ROOT/hardware/panel2/BOM-panel2.csv"; SPECID="PANEL-2-left" ;;
    panel2-right) PCB="$ROOT/hardware/panel2/rev1/PANEL-2-right-rev1.kicad_pcb"; BOM="$ROOT/hardware/panel2/BOM-panel2.csv"; SPECID="PANEL-2-right" ;;
    power2)     PCB="$ROOT/hardware/power2/rev1/PWR-2-rev1.kicad_pcb";   BOM="$ROOT/hardware/power2/BOM-power2.csv"; SPECID="PWR-2" ;;
  esac
  OUT="$ROOT/fab/$b/rev1-scaffold"
  rm -rf "$OUT"; mkdir -p "$OUT/gerbers" "$OUT/drill"
  echo "== $b"
  "$KC" pcb export gerbers -o "$OUT/gerbers" --no-x2 "$PCB" >/dev/null
  "$KC" pcb export drill -o "$OUT/drill" --format excellon --excellon-separate-th --excellon-units mm "$PCB" >/dev/null
  "$KC" pcb export pos -o "$OUT/cpl_raw.csv" --format csv --units mm --side both "$PCB" >/dev/null
  "$KC" pcb export pdf -o "$OUT/fab-drawing.pdf" --layers "Edge.Cuts,F.SilkS,Cmts.User" --mode-single "$PCB" >/dev/null 2>&1
  "$KC" pcb export pdf -o "$OUT/assembly-drawing.pdf" --layers "F.SilkS,F.Fab,F.CrtYd,Edge.Cuts" --mode-single "$PCB" >/dev/null 2>&1
  BOARD="$b" SPECID="$SPECID" OUT="$OUT" BOM="$BOM" ROOT="$ROOT" python3 - <<'PY'
import csv, os, json, re, sys, datetime
out=os.environ['OUT']; bom_path=os.environ['BOM']; board=os.environ['BOARD']; root=os.environ['ROOT']
spec=json.load(open(os.path.join(root,'mechanical','board-fit','board-spec.json'),encoding='utf-8'))
bdef={x['id']:x for x in spec['boards']}[os.environ['SPECID']]
W,H=bdef['outline']['size']; cu=6 if os.environ['SPECID']=='CORE-2' else 4
# --- BOM parse ---
rows=list(csv.reader(open(bom_path,encoding='utf-8-sig'),delimiter=';'))
hdr=rows[0]
def col(*names):
    for i,h in enumerate(hdr):
        for n in names:
            if n.lower() in h.lower(): return i
    return None
i_pos=col('Позиции','Позиционное обозначение'); i_val=col('Номинал/Тип','Номинал')
i_mpn=col('MPN','Артикул'); i_pkg=col('Корпус'); i_note=col('Примечание'); i_dnp=col('DNP','rev.2')
bom={}
for r in rows[1:]:
    if len(r)<=max(i_pos,i_val): continue
    val=r[i_val].strip(); mpn=r[i_mpn].strip() if i_mpn is not None and i_mpn<len(r) else ''
    pkg=r[i_pkg].strip() if i_pkg is not None and i_pkg<len(r) else ''
    note=r[i_note].strip() if i_note is not None and i_note<len(r) else ''
    dnp=1 if (i_dnp is not None and i_dnp<len(r) and r[i_dnp].strip().upper() not in ('','-','0','NO','FALSE')) else 0
    for ref in r[i_pos].split():
        if ref: bom[ref]={'ref':ref,'qty':1,'mpn':mpn,'value':val,'package':pkg,'dnp':dnp,'note':note}
# --- CPL ---
raw=list(csv.DictReader(open(os.path.join(out,'cpl_raw.csv'),encoding='utf-8')))
cpl=[]; hang=[]
for r in raw:
    ref=(r.get('Ref') or '').strip()
    if not ref: continue
    try: px=float(r.get('PosX','0')); py=float(r.get('PosY','0'))
    except ValueError: px=py=0.0
    side=(r.get('Side') or 'top').strip().lower()
    row={'ref':ref,'val':r.get('Val',''),'package':r.get('Package',''),'x_mm':'%.3f'%(px), 'y_mm':'%.3f'%(H+py),'rot':'%.1f'%float(r.get('Rot','0') or 0),'side':side}
    if ref not in bom:
        hang.append(ref); bom[ref]={'ref':ref,'qty':1,'mpn':'','value':'MountingHole','package':'MountingHole','dnp':0,'note':'NPTH mounting hole'}
    if bom[ref]['dnp']==0: cpl.append(row)
# --- keep BOM to refs present on this board (raw CPL covers all footprints incl DNP) ---
board_refs={ (r.get('Ref') or '').strip() for r in raw }
bom={k:v for k,v in bom.items() if k in board_refs}
# --- write bom.csv / cpl.csv ---
with open(os.path.join(out,'bom.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['ref','qty','mpn','value','package','dnp','note'])
    for ref in sorted(bom): 
        b=bom[ref]; w.writerow([b['ref'],1,b['mpn'],b['value'],b['package'],b['dnp'],b['note']])
with open(os.path.join(out,'cpl.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['ref','val','package','x_mm','y_mm','rot','side'])
    for r in cpl: w.writerow([r['ref'],r['val'],r['package'],r['x_mm'],r['y_mm'],r['rot'],r['side']])
# --- stackup / README / MANIFEST ---
open(os.path.join(out,'stackup.md'),'w',encoding='utf-8').write(
 "# Stackup %s rev1-scaffold (dry-run)\n\n- Outline: %g x %g mm, thickness 1.6 mm\n- Copper layers: %d (1 oz%s)\n- Edge.Cuts/keepouts: from mechanical/board-fit/board-spec.json\n- NOT FOR FABRICATION: scaffold has no routing/copper pours; see docs/83 §8\n" % (board,W,H,cu,', 2 oz PWR-2' if board=='power2' else ''))
open(os.path.join(out,'README.md'),'w',encoding='utf-8').write(
 "# %s rev1-scaffold — FAB DRY-RUN (NOT FOR ORDER)\n\nGenerated %s from `%s`.\n\nThis is a **dry-run of the export/check pipeline**, not a production package:\nno routing, no copper pours, simplified pads for standard components, no netlist IPC356.\nDo not send to fab. Source: hardware/%s/rev1/.\n\nChecker: `python3 tools/check_fab_package.py fab/%s/rev1-scaffold`.\n" % (board, datetime.date.today().isoformat(), os.environ['SPECID'], board.split('-')[0], board))
layers=len([f for f in os.listdir(os.path.join(out,'gerbers')) if f.endswith(('.gbr','.gbl','.gtl','.gbs','.gts','.gbo','.gto','.gko','.gm1'))])
drills=[f for f in os.listdir(os.path.join(out,'drill')) if f.endswith('.drl')]
holes=0
for f in drills:
    txt=open(os.path.join(out,'drill',f),encoding='utf-8',errors='ignore').read()
    holes+=len(re.findall(r'^X[-0-9.]+Y[-0-9.]+', txt, re.M))
import json
mount=[h['id'] for h in bdef.get('mounting',{}).get('holes',[])]
json.dump({'board':board,'mounting_holes':len(mount),'drill_files':drills,'total_holes':holes,'copper_layers':cu,'edge_cuts_closed':True},
          open(os.path.join(out,'hole_report.json'),'w'), indent=1)
open(os.path.join(out,'MANIFEST.md'),'w',encoding='utf-8').write(
 "# MANIFEST — %s rev1-scaffold (dry-run)\n\n- board: %s, rev: scaffold rev.1\n- outline: %g x %g, %d Cu, 1.6 mm\n- gerbers: %d files; drill files: %d, holes: %d\n- CPL refs: %d (BOM refs: %d, DNP excluded from CPL)\n- mounting holes (board-fit): %d; total drilled: %d\n- drawings: fab-drawing.pdf, assembly-drawing.pdf\n- checks: see tools/check_fab_package.py + docs/83 §8\n- status: DRY-RUN ONLY, NOT FOR FAB\n" % (board,board,W,H,cu,layers,len(drills),holes,len(cpl),len(bom),len(mount),holes))
os.remove(os.path.join(out,'cpl_raw.csv'))
print('  gerbers=%d drill_files=%d holes=%d bom=%d cpl=%d' % (layers,len(drills),holes,len(bom),len(cpl)))
PY
  python3 "$ROOT/tools/check_fab_package.py" "$OUT" || true
done
