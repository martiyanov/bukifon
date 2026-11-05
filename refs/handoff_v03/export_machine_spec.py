from pathlib import Path
import csv,json,zipfile
from copy import deepcopy
from collections import Counter
from ezdxf import readfile
from ezdxf.math import Matrix44
p=Path('/mnt/data/bukifon_v03')
rows=list(csv.DictReader((p/'coordinates.csv').open(encoding='utf-8')))
R=lambda s: round(float(s),2)
model={
  'schema':'bukifon.panel_layout.v1',
  'revision':'v0.3-photo-layout-keyboards-separated-5mm-each',
  'date':'2026-11-05',
  'units':'mm',
  'coordinate_system':{
   'view':'top_orthographic_front_face',
   'origin':'top-left-corner-of-panel',
   'x_positive':'right','y_positive':'down',
   'element_position':'center',
   'angle_unit':'degrees',
   'angle_positive':'clockwise_in_top_view',
   'rotate_each_element_around':'own_center',
   'panel_bounds_mm':{'xmin':0,'ymin':0,'xmax':380,'ymax':210},
   'dxf_native_coordinates':'bottom-left origin; x right, y up; y_cad = 210-y_layout; theta_cad=-theta_layout'
  },
  'panel':{
    'width_mm':380,'height_mm':210,'front_panel_thickness_mm':3,'overall_depth_mm':63,
    'material':'PETG','max_print_area_mm':[220,220],
    'shape':'rectangle; rounded corners are cosmetic and have no validated radius',
    'no_speakers':True,'no_jacks_below_screen':True
  },
  'revision_delta':{
    'baseline':'bukifon v0.2 photograph-traced reference geometry',
    'left_keyboard':{'translate_x_mm':-5,'translate_y_mm':0,'rotate_deg':0},
    'right_keyboard':{'translate_x_mm':5,'translate_y_mm':0,'rotate_deg':0},
    'total_center_gap_increase_mm':10,
    'other_components_unchanged':True,
    'keyboard_internal_key_relative_geometry_unchanged':True
  },
  'accuracy_and_approval':{
    'design_coordinate_reporting_resolution_mm':0.1,
    'target_final_cad_accuracy_mm':0.5,
    'estimated_accuracy_photo_traced_key_centers_mm':'±1–2',
    'keycap_coordinates_source':'manually traced from user photograph; NOT extracted from Lapka-42 KiCad PCB',
    'verified_manufacturing_ready':False,
    'mandatory_before_manufacture':['Import switch footprint centers, rotations, PCB Edge.Cuts and mounting holes from braindefender/lapka-42 KiCad.','Select and verify actual LCD, jacks, encoders, faders including rear envelopes, cables and connectors.','Recheck mechanical clashes and clearances against tolerances.'],
    'source_repo_reference':'https://github.com/braindefender/lapka-42'
  },
  'geometry_types':{
     'keycap': 'rotated rectangle width 17.5 height 16.5; visual reference only, no drilled mounting hole',
     'encoder': 'outer cylindrical knob diameter 14; nominal pilot hole diameter 7.2 (verify part)',
     'jack': 'front nut outer diameter 10; cut hole diameter 6 (verify part)',
     'lcd_active': 'rectangular cutout 108x64.8; panel must not hide active area',
     'lcd_body': 'rear-case envelope 120.7x75.8, assumed centered on active area',
     'fader_rear': 'rear mounting envelope 16x75, provisional',
     'fader_slot': 'through slot rectangle 2.5x63, center coincides with fader body'
  },
  'controls':{
    'keyboard_left':[], 'keyboard_right':[],
    'encoders_left':[],'encoders_right':[], 'jacks':[],
    'lcd':{}, 'faders':[]
  }
}
for row in rows:
 c={'id':row['id'], 'center_mm':[R(row['center_X_mm']),R(row['center_Y_mm'])],
  'angle_deg':R(row['angle_deg'])}
 t=row['kind']
 if t=='keycap_photo_ref':
  c.update({'key_number':int(row['id'].split('K')[1]),'shape':'rotated_rectangle',
    'size_mm':[17.5,16.5], 'through_cut':False,'source':'photo_reference_not_kicad'})
  model['controls']['keyboard_left' if row['id'].startswith('L_') else 'keyboard_right'].append(c)
 elif t=='encoder':
  c.update({'shape':'circle','knob_outer_diameter_mm':14, 'nominal_panel_hole_diameter_mm':7.2, 'hole_size_confirmed':False})
  model['controls']['encoders_left' if row['id'].startswith('L_') else 'encoders_right'].append(c)
 elif t=='mini_jack':
  c.update({'shape':'circle','outer_nut_diameter_mm':10, 'panel_hole_diameter_mm':6, 'verify_actual_part':True})
  model['controls']['jacks'].append(c)
 elif t=='display_active':
  c.update({'shape':'rectangle','opening_size_mm':[108,64.8], 'screen_pixels':[800,480], 'bezel':'no decorative frame'})
  model['controls']['lcd']['active_cutout']=c
 elif t=='display_body_envelope':
  c.update({'shape':'rectangle','rear_envelope_size_mm':[120.7,75.8], 'verify_display_mounting_and_connector':True})
  model['controls']['lcd']['body_envelope']=c
 elif t=='fader_rear_envelope':
  c.update({'shape':'rectangle','rear_envelope_size_mm':[16,75]})
  model['controls']['faders'].append({'id':row['id'].split('_')[0]+'', 'rear_envelope':c})
 elif t=='fader_slot':
  c.update({'shape':'rectangle','slot_size_mm':[2.5,63], 'stroke_length_nominal_mm':60})
  next(f for f in model['controls']['faders'] if f['id']==row['id'].split('_')[0])['slot']=c
for side in ('keyboard_left','keyboard_right'):
 model['controls'][side].sort(key=lambda k:k['key_number'])
assert len(model['controls']['keyboard_left'])==21 and len(model['controls']['keyboard_right'])==21
for a,b in zip(model['controls']['keyboard_left'],model['controls']['keyboard_right']):
 assert a['key_number']==b['key_number']
 assert abs(a['center_mm'][0]+b['center_mm'][0]-380)<1e-5
 assert a['center_mm'][1]==b['center_mm'][1]
 assert a['angle_deg']==-b['angle_deg']
model['collision_check_photo_geometry_only']=json.loads((p/'collision_report.json').read_text(encoding='utf-8'))
(p/'bukifon_layout_v03.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Create conventional native CAD DXF directly in X-right, Y-up coordinates.
# This avoids ezdxf OCS/extrusion surprises associated with reflecting circles.
import ezdxf
from shapely.geometry import box
from shapely.affinity import rotate
D=ezdxf.new('R2013'); D.units=4
ms=D.modelspace()
for name,color in {'OUTLINE':7,'SEAMS':8,'THROUGH_CUT':1,'KEYCAP_PHOTO_REF':4,
                   'LCD_REAR_ENVELOPE':5,'FADER_ENVELOPE':3}.items():
 D.layers.new(name,dxfattribs={'color':color})
H=210.0
def from_screen(points):return [(float(x),float(H-y)) for x,y in points]
def poly_screen(points,layer):
 ms.add_lwpolyline(from_screen(points),close=True,dxfattribs={'layer':layer})
def rect_screen(cx,cy,w,h,layer):
 poly_screen([(cx-w/2,cy-h/2),(cx+w/2,cy-h/2),(cx+w/2,cy+h/2),(cx-w/2,cy+h/2)],layer)
poly_screen([(0,0),(380,0),(380,210),(0,210)],'OUTLINE')
for pts in [
  [(0,0),(124,0),(124,75),(0,75)],
  [(124,0),(256,0),(256,103),(124,103)],
  [(256,0),(380,0),(380,75),(256,75)],
  [(0,75),(124,75),(124,103),(164,103),(164,210),(0,210)],
  [(164,103),(216,103),(216,210),(164,210)],
  [(256,75),(380,75),(380,210),(216,210),(216,103),(256,103)]
 ]:poly_screen(pts,'SEAMS')
lcd=model['controls']['lcd']
rect_screen(*lcd['active_cutout']['center_mm'],108,64.8,'THROUGH_CUT')
rect_screen(*lcd['body_envelope']['center_mm'],120.7,75.8,'LCD_REAR_ENVELOPE')
for jack in model['controls']['jacks']:
 x,y=jack['center_mm'];ms.add_circle((x,H-y),3.0,dxfattribs={'layer':'THROUGH_CUT'})
for enc in model['controls']['encoders_left']+model['controls']['encoders_right']:
 x,y=enc['center_mm'];ms.add_circle((x,H-y),3.6,dxfattribs={'layer':'THROUGH_CUT'})
for f in model['controls']['faders']:
 x,y=f['slot']['center_mm']; rect_screen(x,y,2.5,63,'THROUGH_CUT')
 x,y=f['rear_envelope']['center_mm']; rect_screen(x,y,16,75,'FADER_ENVELOPE')
for key in model['controls']['keyboard_left']+model['controls']['keyboard_right']:
 x,y=key['center_mm']
 r=rotate(box(x-8.75,y-8.25,x+8.75,y+8.25),key['angle_deg'],origin=(x,y))
 poly_screen(list(r.exterior.coords)[:-1],'KEYCAP_PHOTO_REF')
dxf=p/'bukifon_v03_panel.dxf'
D.saveas(dxf)
check=ezdxf.readfile(dxf); mm=check.modelspace()
jacks=[e for e in mm.query('CIRCLE') if abs(e.dxf.radius-3)<0.0001]
assert len(jacks)==10 and abs(jacks[0].dxf.center.x-140.5)<0.01 and abs(jacks[0].dxf.center.y-199)<0.01
boundary=list(mm.query('LWPOLYLINE'))[0].get_points('xy')
assert min(x for x,y in boundary)==0 and max(x for x,y in boundary)==380, boundary
# Clarify DXF convention in a plain-language handoff.
readme='''# Букифон v0.3 — машинная спецификация панели / HANDOFF

Это **раскладка v0.2 после смещения клавиатур**. Геометрия клавиатур восстановлена по фотографии и НЕ является KiCad Lapka-42.

## Главный файл
`bukifon_layout_v03.json` — полный список центров/углов/размеров **всех** 42 колпачков, 16 энкодеров, 10 mini-jack, LCD, двух фейдеров, размеров панели и ограничений. Не заменять этот файл оценками с PNG.

## Система координат JSON/CSV/SVG/OpenSCAD
- Вид строго сверху, передняя поверхность панели. Левый верхний угол = (0,0).
- X растёт вправо; Y растёт вниз. Все координаты — **центры**.
- Положительный угол означает поворот **по часовой стрелке на виде сверху**. Поворот каждого колпачка — относительно собственного центра, без дополнительного поворота целой половины.
- Размеры 380 × 210 × 3 мм, предварительная глубина корпуса 63 мм.
- Клавиши имеют видимый прямоугольник 17,5 × 16,5 мм и не задают конструкцию посадочных отверстий.

## Важное про DXF
`bukifon_v03_panel.dxf` адаптирован для классической CAD-системы с **Y вверх и началом снизу слева**. Следовательно: Y_DXF = 210 − Y_JSON, угол_DXF = −угол_JSON. DXF-слой `KEYCAP_PHOTO_REF` содержит визуальные границы колпачков, **не вырезы под Kailh Choc**. Сквозные отверстия — `THROUGH_CUT`.

## Изменения относительно v0.2
- Левые 21 колпачков: X_new = X_v02 − 5 мм.
- Правые 21 колпачков: X_new = X_v02 + 5 мм.
- Y, размеры и индивидуальные углы прежние; зазор по центру увеличен на 10 мм.
- Энкодеры, 10 джеков, экран, 2 фейдера и размер корпуса НЕ изменены.

## Точность
Целевой допуск проекта ±0,5 мм **пока недостижим по фото**: погрешность реконструкции клавиш ориентировочно ±1–2 мм. Для производства требуется оригинальный файл Lapka-42 `.kicad_pcb` и согласование компонентных посадочных размеров. Проверка пересечений отражает только эту приближённую геометрию.

## Рекомендованный порядок использования другим агентом
1. Открыть JSON и построить геометрию без дополнительных художественных допущений.
2. При загрузке DXF применять CAD-конвенцию Y вверх. Не удваивать преобразование зеркала.
3. Обеспечить совпадение вида строго сверху с `bukifon_top_view.png`.
4. Не считать приблизительные колпачки реальными координатами переключателей.
5. До получения KiCad не создавать окончательные отверстия переключателей или крепления PCB.

## Состав
- `bukifon_layout_v03.json` — каноническая машинная спецификация.
- `coordinates.csv` — линейный список всех элементов (JSON-конвенция Y вниз).
- `bukifon_v03_panel.dxf` — CAD-элементы Y вверх, прямой импорт.
- `bukifon_v03_panel.svg` — векторный вид сверху.
- `bukifon_v03_mockup.scad` — черновая параметрическая 3D-панель (ориентацию вида следует согласовывать с JSON).
- `bukifon_top_view.png` — эталон внешнего вида сверху.
- `collision_report.json` — отчёт по расчётным коллизиям.
- `build.py`, `make_top_view.py` — воспроизводимое построение чертежа и изображения; `build.py` создаёт исходный Y-вниз DXF, а `export_machine_spec.py` делает конвертацию в CAD Y-вверх.
'''
(p/'HANDOFF.md').write_text(readme,encoding='utf-8')
with zipfile.ZipFile('/mnt/data/bukifon_v03_handoff.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for name in ['bukifon_layout_v03.json','coordinates.csv','bukifon_v03_panel.dxf','bukifon_v03_panel.svg','bukifon_v03_mockup.scad','bukifon_top_view.png','collision_report.json','HANDOFF.md','build.py','make_top_view.py','export_machine_spec.py']:
  z.write(p/name,arcname=name)
print('validated JSON:',len(model['controls']['keyboard_left']),len(model['controls']['keyboard_right']))
print('DXF jack y after conversion:',jacks[0].dxf.center.y)
print('archive bytes',Path('/mnt/data/bukifon_v03_handoff.zip').stat().st_size)
