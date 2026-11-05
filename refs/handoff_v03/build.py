#!/usr/bin/env python3
"""Bukifon v0.3 PRELIMINARY interface layout. Units millimetres.
IMPORTANT: Lapka-42 key switch coordinates are illustrative, NOT PCB-extracted.
"""
from pathlib import Path
import math,json,csv,zipfile
from itertools import combinations
from shapely.geometry import box,Point,Polygon
from shapely.affinity import rotate,translate,scale
import svgwrite,ezdxf
from xml.sax.saxutils import escape

OUT=Path(__file__).parent
W,H=380.0,210.0
LCD_C=(190.0,61.4); LCD_ACTIVE=(108.0,64.8); LCD_BODY=(120.7,75.8)
ENC_X_L=[22.0,49.0,76.0,103.0];ENC_X_R=[277.0,304.0,331.0,358.0];ENC_Y=[30.5,57.5]
JACK_X=[140.5+11*i for i in range(10)];JACK_Y=11.0
FADER_X=[180.0,200.0];FADER_Y=149.0
PANELS=[
 ('controls_L',[(0,0),(124,0),(124,75),(0,75)]),
 ('display',[(124,0),(256,0),(256,103),(124,103)]),
 ('controls_R',[(256,0),(380,0),(380,75),(256,75)]),
 ('deck_L',[(0,75),(124,75),(124,103),(164,103),(164,210),(0,210)]),
 ('faders',[(164,103),(216,103),(216,210),(164,210)]),
 ('deck_R',[(256,75),(380,75),(380,210),(216,210),(216,103),(256,103)]),
]

# PHOTO-DERIVED GEOMETRY: measured manually from IMG_0704.jpg.
# The screenshot crop was generated from image x=60..640,y=410..930 at 1408x1056,
# then enlarged x2. The 21 centre samples and column angles below come from this crop.
# NOTE: these are NOT verified KICAD footprint origins: expected shape error ~1–2 mm.
# Scale 7.65 px/mm chosen from actual Choc key spacing and measured photo image;
# x0/y0 chosen to align with submitted layout and preserve screen/fader clearance.
PHOTO_SCALE_PX_PER_MM=7.65
PHOTO_X0,PHOTO_Y0=12.0,79.0
photo_keys={
   10:(190,168,8), 16:(165,313,8), 19:(140,454,8),
    5:(329,190,8), 11:(305,328,8), 17:(282,467,8),
    1:(510,127,13), 6:(481,258,13), 12:(450,395,13),
    2:(680,134,17), 7:(646,266,17), 13:(598,397,17),
    3:(831,213,22), 8:(786,342,22), 14:(738,476,22),
    4:(988,270,24), 9:(926,390,24), 15:(879,521,24),
   18:(725,670,21),20:(868,745,35),21:(1006,851,44),
}
# Shift agreed in next iteration: L -5.0 mm in X, R +5.0 mm in X, 10.0 mm total gap growth.
# Corrected small image-reading overlaps (<1 mm) by <~1.5 mm movement of K7,K13,K15.
# The physical relative rotation of each key is kept, NOT flattened to ±20 degrees.
def polygon_key(cx,cy,ang):
 return rotate(box(cx-8.75,cy-8.25,cx+8.75,cy+8.25),ang,origin=(cx,cy))
keys=[]
for n,(px,py,ang) in sorted(photo_keys.items()):
 xx=PHOTO_X0+px/PHOTO_SCALE_PX_PER_MM
 yy=PHOTO_Y0+py/PHOTO_SCALE_PX_PER_MM
 for side,cx,angle in [('L',xx-5.0,ang),('R',W-xx+5.0,-ang)]:
  keys.append({'id':f'{side}_K{n:02d}','type':'keycap_photo_ref','cx':cx,'cy':yy,'w':17.5,'h':16.5,
               'angle':angle,'geometry':polygon_key(cx,yy,angle),'photo_x':px,'photo_y':py})

items=[]
for k in keys:items.append(k)
for side,arr in [('L',ENC_X_L),('R',ENC_X_R)]:
 for row,yy in enumerate(ENC_Y):
  for i,xx in enumerate(arr):
   items.append({'id':f'{side}_ENC_{chr(65+row*4+i)}','type':'encoder','cx':xx,'cy':yy,'diameter':14.0,'hole_d':7.2,'angle':0.0,'geometry':Point(xx,yy).buffer(7,quad_segs=40)})
for n,xx in enumerate(JACK_X,1):
 items.append({'id':f'J{n:02d}','type':'mini_jack','cx':xx,'cy':JACK_Y,'diameter':10.0,'hole_d':6.0,'angle':0,'geometry':Point(xx,JACK_Y).buffer(5,quad_segs=40)})
items.append({'id':'LCD','type':'display_active','cx':LCD_C[0],'cy':LCD_C[1],'w':108.0,'h':64.8,'angle':0,'geometry':box(136,29,244,93.8)})
lcd_rect=box(LCD_C[0]-LCD_BODY[0]/2,LCD_C[1]-LCD_BODY[1]/2,LCD_C[0]+LCD_BODY[0]/2,LCD_C[1]+LCD_BODY[1]/2)
items.append({'id':'LCD_body','type':'display_body_envelope','cx':LCD_C[0],'cy':LCD_C[1],'w':120.7,'h':75.8,'angle':0,'geometry':lcd_rect})
for n,xx in enumerate(FADER_X,1):
 # conservative envelope includes fader motor/controller mounts and cap width; actual pot body is 75x9
 items.append({'id':f'F{n}_env','type':'fader_rear_envelope','cx':xx,'cy':FADER_Y,'w':16.0,'h':75.0,'angle':0,'geometry':box(xx-8,111.5,xx+8,186.5)})
 items.append({'id':f'F{n}_slot','type':'fader_slot','cx':xx,'cy':FADER_Y,'w':2.5,'h':63.0,'angle':0,'geometry':box(xx-1.25,117.5,xx+1.25,180.5)})

# the active opening is intentionally inside the module, and slider slots are inside their housings.
# Check only mutually exclusive mechanical component envelopes.
CHECK=[x for x in items if x['type'] in ('keycap_photo_ref','encoder','mini_jack','display_body_envelope','fader_rear_envelope')]
collisions=[];mindist=float('inf');minpair=None
for a,b in combinations(CHECK,2):
 d=a['geometry'].distance(b['geometry'])
 if d<mindist:mindist,minpair=d,[a['id'],b['id']]
 if d<0.49:collisions.append({'a':a['id'],'b':b['id'],'distance_mm':round(d,3),'intersection_area_mm2':round(a['geometry'].intersection(b['geometry']).area,3)})
for i in CHECK:
 bb=i['geometry'].bounds
 if bb[0]<-1e-5 or bb[1]<-1e-5 or bb[2]>W+1e-5 or bb[3]>H+1e-5:
  collisions.append({'out_of_panel':i['id'],'bounds':bb})

def distances(category_a,category_b):
 aa=[it for it in CHECK if it['type']==category_a];bb=[it for it in CHECK if it['type']==category_b]
 return min((a['geometry'].distance(b['geometry']),a['id'],b['id']) for a in aa for b in bb)
checks={
 'status':'PASS_for_photo_traced_approximation_only_NOT_KiCad_source',
 'unit':'mm','panel':[W,H], 'input_accuracy_target_mm':0.5,
 'geometric_min_gap_mm':round(mindist,3),'min_pair':minpair,'collisions':collisions,
 'key_to_display_body_mm':round(distances('keycap_photo_ref','display_body_envelope')[0],3),
 'key_to_fader_envelope_mm':round(distances('keycap_photo_ref','fader_rear_envelope')[0],3),
 'display_body_to_jack_nut_mm':round(distances('display_body_envelope','mini_jack')[0],3),
 'display_body_to_encoder_knob_mm':round(distances('display_body_envelope','encoder')[0],3),
 'fader_to_fader_envelope_mm':round(items[-2]['geometry'].distance(items[-4]['geometry']),3),
 'notes':['All 21 individual key positions and rotations traced from provided photo (image error estimated 1–2mm); source KiCad not retrieved.',
          'Column splay and thumb rotations retained from photo; exact KiCad footprint coordinates still UNVERIFIED.',
          'LCD 120.7x75.8 body assumes active area centered; actual FPC/driver offsets must be verified.',
          'Jack nut Ø10 and rear envelope are provisional. Fader house 75x9 confirmed; clearance checked using 75x16.',
          'M3 backplate mounting and PCB/chassis interface need detailed engineering.']
}
for side in ('L','R'):
 ks=[k['geometry'].bounds for k in keys if k['id'].startswith(side+'_')]
 checks[f'key_{side}_AABB_mm']=[round(min(bb[0] for bb in ks),2),round(min(bb[1] for bb in ks),2),round(max(bb[2] for bb in ks),2),round(max(bb[3] for bb in ks),2)]
(OUT/'collision_report.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
assert not collisions, collisions

# coordinate register for CAD integration
with (OUT/'coordinates.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.writer(f);w.writerow(['id','kind','center_X_mm','center_Y_mm','width_mm','height_mm','angle_deg','nominal_cutout_mm','source'])
 for el in items:
  if el['type']=='display_active':cut='108.0 x 64.8'
  elif el['type']=='mini_jack':cut='D6.0'
  elif el['type']=='encoder':cut='D7.2 (bushing; CONFIRM EC11 model)'
  elif el['type']=='fader_slot':cut='2.5 x 63.0'
  elif el['type']=='keycap_photo_ref':cut='NO cutout, cap reference only'
  else:cut='rear envelope, no through-cut'
  source='PHOTO_TRACED / NOT_KICAD' if el['type']=='keycap_photo_ref' else ('manufacturer dimensions + nominal positions' if el['type'] in ('display_active','display_body_envelope','fader_rear_envelope') else 'layout proposal / verify mating part')
  w.writerow([el['id'],el['type'],f"{el['cx']:.1f}",f"{el['cy']:.1f}",f"{el.get('w',el.get('diameter',0)):.1f}",f"{el.get('h',el.get('diameter',0)):.1f}",f"{el['angle']:.1f}",cut,source])

# DXF: source layers explicitly distinguish production geometry from reference layers
D=ezdxf.new('R2013');D.units=4;ms=D.modelspace()
colors={'OUTLINE':7,'SEAMS':8,'THROUGH_CUT':1,'KEYCAP_PHOTO_REF':4,'LCD_REAR_ENVELOPE':5,'FADER_ENVELOPE':3,'TEXT':7}
for name,num in colors.items():D.layers.new(name,dxfattribs={'color':num})
ms.add_lwpolyline([(0,0),(W,0),(W,H),(0,H)],close=True,dxfattribs={'layer':'OUTLINE'})
for id,pts in PANELS:ms.add_lwpolyline(pts,close=True,dxfattribs={'layer':'SEAMS'})
ms.add_lwpolyline([(136,29),(244,29),(244,93.8),(136,93.8)],close=True,dxfattribs={'layer':'THROUGH_CUT'})
ms.add_lwpolyline([(129.65,23.5),(250.35,23.5),(250.35,99.3),(129.65,99.3)],close=True,dxfattribs={'layer':'LCD_REAR_ENVELOPE'})
for n,x in enumerate(JACK_X,1):ms.add_circle((x,JACK_Y),3.0,dxfattribs={'layer':'THROUGH_CUT'})
for xx in ENC_X_L+ENC_X_R:
 for yy in ENC_Y:ms.add_circle((xx,yy),3.6,dxfattribs={'layer':'THROUGH_CUT'})
for x in FADER_X:
 ms.add_lwpolyline([(x-1.25,117.5),(x+1.25,117.5),(x+1.25,180.5),(x-1.25,180.5)],close=True,dxfattribs={'layer':'THROUGH_CUT'})
 ms.add_lwpolyline([(x-8,111.5),(x+8,111.5),(x+8,186.5),(x-8,186.5)],close=True,dxfattribs={'layer':'FADER_ENVELOPE'})
for k in keys:
 ms.add_lwpolyline(list(k['geometry'].exterior.coords)[:-1],close=True,dxfattribs={'layer':'KEYCAP_PHOTO_REF'})
D.saveas(OUT/'bukifon_v03_panel.dxf')

# SVG front view (mm user coordinates, but enlarged responsive preview)
S=svgwrite.Drawing(str(OUT/'bukifon_v03_panel.svg'),size=('1140px','630px'),viewBox='-16 -17 412 238')
S.add(S.rect(insert=(-16,-17),size=(412,238),fill='#e9ecef'))
S.add(S.rect(insert=(0,0),size=(W,H),fill='#d9dfe2',stroke='#1f2937',stroke_width=0.8,rx=4))
for i,(name,pts) in enumerate(PANELS):
 S.add(S.polygon(pts,fill=['#d9dee2','#e5e9ec','#d9dee2','#cbd2d6','#e0e5e8','#cbd2d6'][i],stroke='#8c969d',stroke_width=0.35))
S.add(S.rect(insert=(129.65,23.5),size=(120.7,75.8),fill='none',stroke='#8b92a0',stroke_width=0.55,stroke_dasharray='2 2'))
S.add(S.rect(insert=(136,29),size=(108,64.8),rx=1,fill='#131e25',stroke='#222f35',stroke_width=0.35))
S.add(S.text('БУКИФОН',insert=(190,53),fill='#d5ebdd',font_size=7.5,text_anchor='middle',font_family='Arial,sans-serif',font_weight='bold'))
S.add(S.text('800 × 480',insert=(190,62.5),fill='#9faeb1',font_size=4,text_anchor='middle',font_family='Arial,sans-serif'))
S.add(S.text('4-PART  ·  8-VOICE  ·  FM',insert=(190,72),fill='#7ca18d',font_size=3.4,text_anchor='middle',font_family='Arial,sans-serif'))
for i,x in enumerate(JACK_X,1):
 S.add(S.circle(center=(x,JACK_Y),r=4.6,fill='#4d5660',stroke='#edf1f4',stroke_width=0.6))
 S.add(S.circle(center=(x,JACK_Y),r=3.0,fill='#101820'))
 S.add(S.text(f'{i}',insert=(x,21),font_size=3.0,text_anchor='middle',fill='#59636a',font_family='Arial,sans-serif'))
for side,arr in [('L',ENC_X_L),('R',ENC_X_R)]:
 for row,yy in enumerate(ENC_Y):
  for col,xx in enumerate(arr):
   S.add(S.circle(center=(xx,yy),r=7,fill='#34383e',stroke='#747b84',stroke_width=0.55))
   S.add(S.circle(center=(xx,yy),r=1.0,fill='#b9c1c7'))
   S.add(S.text(chr(65+row*4+col),insert=(xx,yy+13.6),font_size=4.1,text_anchor='middle',fill='#2e3d45',font_family='Arial,sans-serif'))
for k in keys:
 cr=k['geometry'].exterior.coords
 S.add(S.polygon([(x,y) for x,y in cr],fill='#eef0ea',stroke='#667980',stroke_width=0.5))
 S.add(S.text(k['id'].split('_')[1].replace('K',''),insert=(k['cx'],k['cy']+1.5),fill='#3b4b56',font_size=3.6,text_anchor='middle',font_family='Arial,sans-serif'))
for i,x in enumerate(FADER_X,1):
 S.add(S.rect(insert=(x-8,111.5),size=(16,75),fill='none',stroke='#b59c8d',stroke_width=.4,stroke_dasharray='2.1,1.6'))
 S.add(S.rect(insert=(x-1.25,117.5),size=(2.5,63),rx=1.25,fill='#242c32'))
 S.add(S.rect(insert=(x-8,142),size=(16,12),rx=2,fill='#354049',stroke='#a3aaaf',stroke_width=.5))
 S.add(S.text(f'F{i}',insert=(x,105),text_anchor='middle',font_size=4.3,font_family='Arial,sans-serif',fill='#354b5b'))
S.add(S.text('380 × 210  /  CAD v0.3  /  КЛАВИШИ: ПОВОРОТЫ И СТУПЕНИ С ФОТО; KiCad НЕ ПРОВЕРЕН',insert=(190,217),text_anchor='middle',font_size=4.5,fill='#4b5563',font_family='Arial,sans-serif'))
for x in range(0,381,50):
 S.add(S.line(start=(x,-1.5),end=(x,-4),stroke='#6b7280',stroke_width=.4))
 S.add(S.text(str(x),insert=(x,-6),font_size=4.4,text_anchor='middle',fill='#4b5563',font_family='Arial,sans-serif'))
for y in range(0,211,50):
 S.add(S.line(start=(-1.5,y),end=(-4,y),stroke='#6b7280',stroke_width=.4))
 S.add(S.text(str(y),insert=(-6,y+1.5),font_size=4.4,text_anchor='end',fill='#4b5563',font_family='Arial,sans-serif'))
S.add(S.text('X →',insert=(355,-10),font_size=4.2,fill='#374151'))
S.save()

# OpenSCAD assembly preview; six front pieces, no keyboard deck mechanical retention is specified.
def scadpoly(poly):return '['+','.join(f'[{x:g},{y:g}]' for x,y in poly)+']'
content=['''// BUKIFON v0.3  | UNITS mm | PROVISIONAL CONCEPT / NOT MANUFACTURING READY
// KiCad coordinates and actual Lapka case mounting have NOT been imported.
// Front is 380 x 210 x 3, split into six printable sections <= 220 x 220.
// Normal mounting for low-profile Choc MUST be a separate 1.3-1.6mm switch plate;
// the 3.0mm PETG casing is structural, not a Choc snap-in plate.
$fn=48;
show_keys=true;
show_envelopes=false;
show_chassis=false; // rough 63 mm deep envelope; not a mechanical housing
export_part=-1; // -1 assembled, 0..5 a single printable front tile
module panel2d() {
  square([380,210]);
}
module hole_set() {
  translate([136,29]) square([108,64.8]); // zero-bezel active-area opening
  for(i=[0:9]) translate([140.5+i*11,11]) circle(d=6);
  for(x=[22,49,76,103,277,304,331,358])
    for(y=[30.5,57.5]) translate([x,y]) circle(d=7.2); // verify selected encoder bushing
  for(x=[180,200]) translate([x-1.25,117.5]) square([2.5,63]);
}
module piece(poly) {
  linear_extrude(height=3) difference(){polygon(poly);hole_set();}
}
''']
for i,(name,pts) in enumerate(PANELS):
 colcode=['[0.76,0.80,0.82]','[0.84,0.87,0.88]','[0.76,0.80,0.82]','[0.69,0.74,0.77]','[0.79,0.83,0.85]','[0.69,0.74,0.77]'][i]
 content.append(f'if(export_part==-1 || export_part=={i}) color({colcode}) piece({scadpoly(pts)}); // {name}\n')
content.append('''
if(show_keys && export_part==-1) {
  // Reference visual caps only; they are NOT switch holes or proof of PCB fit.
''')
for k in keys:
 content.append(f'  color([0.94,0.95,0.91]) translate([{k["cx"]:.4f},{k["cy"]:.4f},4]) rotate([0,0,{k["angle"]:.4f}]) translate([-8.75,-8.25,0]) cube([17.5,16.5,5]);\n')
# OpenSCAD y axis visual in model positive up; to resemble SVG positive down, angle negated when displaying, no importance to rectangle mostly.
content.append('}\n')
content.append('''// Encoder knobs, jack rings, fader caps: presentation solids.
if(export_part==-1) for(x=[22,49,76,103,277,304,331,358]) for(y=[30.5,57.5])
  color([0.18,0.20,0.23]) translate([x,y,3]) cylinder(h=8,d=14);
if(export_part==-1) for(i=[0:9]) color([0.25,0.28,0.30]) translate([140.5+i*11,11,3]) difference() {cylinder(h=2,d=9);cylinder(h=2.1,d=5.7);}
if(export_part==-1) for(x=[180,200]) color([0.2,0.24,0.28]) translate([x-8,143,4]) cube([16,12,5]);
// Black physical LCD is hidden behind the nominal 108 x 64.8 window.
if(show_envelopes && export_part==-1) {
 color([0.15,0.3,0.65,0.15]) translate([129.65,23.5,-5]) cube([120.7,75.8,5]);
 for(x=[180,200])color([0.6,0.1,0.1,0.35])translate([x-8,111.5,-8]) cube([16,75,8]);
}
if(show_chassis && export_part==-1){
  // ENVELOPE only: rear skirt 60 mm below 3 mm front, printed as separate parts.
  color([0.25,0.28,0.30,0.35]) translate([0,0,-60]) {
    cube([190,3,60]); translate([190,0,0]) cube([190,3,60]);
    translate([0,207,0]) cube([190,3,60]); translate([190,207,0]) cube([190,3,60]);
    cube([3,210,60]); translate([377,0,0]) cube([3,210,60]);
  }
}
''')
(OUT/'bukifon_v03_mockup.scad').write_text(''.join(content),encoding='utf-8')

notes='''# Букифон v0.3 — реконструкция расположения клавиш по фотографии

Версия v0.3 наследует реконструкцию v0.2 и смещает левую клавиатуру на −5 мм по X, правую на +5 мм по X. Геометрия внутри половин не меняется. По фото сняты 21 положение и
индивидуальные углы. Левая половина — номера клавиш 1…21 с пользовательской фотографии,
правая — зеркальная копия. Использован масштаб 7.65 px/mm, основанный на Choc-шаге;
сдвиг всей группы выбран для максимального сходства с фотомакетом и зазорами.

## ВАЖНЫЙ СТАТУС

Это **фотограмметрическая реконструкция, не заводской чертёж Lapka-42**. Исходные `.kicad_pcb`
репозитория https://github.com/braindefender/lapka-42/ не удалось получить в рабочей среде.
Поэтому размеры 17.5×16.5 мм и идентификаторы ключей заданы по ТЗ; центры и углы
по фото, а не импортированы из KiCad. Погрешность фотооценки ориентировочно ±1–2 мм,
хотя CAD-координаты записаны с разрешением 0.1 мм. Не сверлить, не фрезеровать
и не печатать посадочные детали клавиатуры без исходных KiCad-координат и платы!

## Геометрия

- Панель: 380 × 210 × 3 мм; примерный объём корпуса 380×210×63.
- Изменение от v0.2: L(X) = X_v0.2 − 5 мм; R(X) = X_v0.2 + 5 мм, остальные координаты и углы без изменений.
- Система: X вправо, Y вниз, ноль верхний левый угол.
- 6 групп колонок, индивидуальные углы для левой половины:
  C1 +8°, C2 +8°, C3 +13°, C4 +17°, C5 +22°, C6 +24°.
- Тамб-кластер: клавиши 18 +21°, 20 +35°, 21 +44°.
- Правая половина: отражение относительно оси X=190, углы с обратным знаком.
- 10 джеков сверху, активный дисплей 108×64.8 мм, 2 фейдера без разъёмов под экраном.
- Диаметр ручек 14 мм, вырез 7.2 мм предварительный; джек Ø6.
- При проверке коллизий учтены колпачки, LCD корпус 120.7×75.8,
  энкодеры Ø14, джековые гайки Ø10, тыловые зоны фейдеров 16×75 мм.
- Зазор между колпачками в этой модели нельзя понимать как производственный
  допуск: реальная геометрия Lapka и корпуса будет отличаться.

## Содержание

- bukifon_v03_panel.svg — компоновка со всеми углами и номерами как на фото.
- bukifon_v03_panel.dxf — CAD-слои; KEYCAP_PHOTO_REF лишь визуальная геометрия,
  НЕ отверстия для переключателей.
- bukifon_v03_mockup.scad — объёмный эскиз с теми же углами.
- bukifon_v03_preview.png — чертёж для согласования.
- bukifon_v03_3d_preview.png — схематичная объёмная визуализация.
- photo_trace_overlay.png — совмещение реконструкции с фото на 21 клавишу.
- coordinates.csv — полная таблица центров, углов и других компонентов.
- collision_report.json — расчёт минимальных зазоров.
- build.py / render_3d.py — воспроизводимые скрипты.

Для производственной версии нужно импортировать каждое `SW... (at X Y angle)`
и Edge.Cuts из `.kicad_pcb`, выбрать монтажные отверстия, корпус Choc/hotswap.
'''
(OUT/'README.md').write_text(notes,encoding='utf-8')
try:
 import cairosvg
 cairosvg.svg2png(url=str(OUT/'bukifon_v03_panel.svg'),write_to=str(OUT/'bukifon_v03_preview.png'),output_width=1520,output_height=840)
except Exception as exc:print('PNG preview failed:',exc)
with zipfile.ZipFile(OUT.parent/'bukifon_v03_concept.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for item in sorted(OUT.iterdir()):
  if item.is_file() and item.name!='build.py':z.write(item,arcname=item.name)
print(json.dumps({k:v for k,v in checks.items() if k!='notes'},ensure_ascii=False,indent=2))
print('Files:',*[p.name for p in OUT.iterdir()],sep='\n')
