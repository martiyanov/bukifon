from PIL import Image, ImageDraw, ImageFont, ImageFilter
import csv, math
from pathlib import Path
p=Path('/mnt/data/bukifon_v03')
rows=list(csv.DictReader((p/'coordinates.csv').open()))
S=5.3
mx,my=100,95
W,H=int(380*S+mx*2),int(210*S+my*2)
base=Image.new('RGB',(W,H),(23,28,35))
d=ImageDraw.Draw(base)
def u(x,y):return int(mx+x*S),int(my+y*S)
def rect(cx,cy,w,h,fill,outline=None,radius=0,wd=1):
 x0,y0=u(cx-w/2,cy-h/2);x1,y1=u(cx+w/2,cy+h/2)
 d.rounded_rectangle((x0,y0,x1,y1),radius=int(radius*S),fill=fill,outline=outline,width=wd)
def circ(x,y,r,fill,outline=None,wd=1):
 cx,cy=u(x,y);R=r*S
 d.ellipse((int(cx-R),int(cy-R),int(cx+R),int(cy+R)),fill=fill,outline=outline,width=wd)
def rr_key(x,y,angle,fill='#e9e8df',border='#858a90'):
 ww,hh=17.5*S,16.5*S
 key=Image.new('RGBA',(int(ww)+18,int(hh)+18),(0,0,0,0))
 kd=ImageDraw.Draw(key)
 kd.rounded_rectangle((5,5,int(ww)+12,int(hh)+12),radius=int(2.2*S),fill=border)
 kd.rounded_rectangle((7,7,int(ww)+10,int(hh)+9),radius=int(2.0*S),fill=fill)
 kd.line([(11,15),(int(ww),15)],fill='#f9f9f2',width=2)
 rot=key.rotate(-angle, resample=Image.Resampling.BICUBIC,expand=True)
 cx,cy=u(x,y)
 base.paste(rot,(cx-rot.width//2,cy-rot.height//2),rot)
# outer shadow
x0,y0=u(0,0);x1,y1=u(380,210)
shadow=Image.new('RGBA',base.size,(0,0,0,0));sd=ImageDraw.Draw(shadow)
sd.rounded_rectangle((x0+11,y0+17,x1+11,y1+17),radius=27,fill=(0,0,0,170))
base=Image.alpha_composite(base.convert('RGBA'),shadow.filter(ImageFilter.GaussianBlur(20)))
d=ImageDraw.Draw(base)
d.rounded_rectangle((x0,y0,x1,y1),radius=20,fill='#79848e',outline='#bec7ce',width=3)
d.rounded_rectangle((x0+7,y0+7,x1-7,y1-7),radius=15,fill='#afb9c0',outline='#7a858d',width=2)
# panel parts - subtle seams
for coords in [(0,75,124,75),(256,75,380,75),(124,0,124,103),(256,0,256,103),(164,103,164,210),(216,103,216,210)]:
 xa,ya,xb,yb=coords
 d.line([u(xa,ya),u(xb,yb)],fill='#87939b',width=2)
rect(190,61.4,121.6,76.8,'#7f8b96',radius=2)
rect(190,61.4,108,64.8,'#142129',radius=1)
# screen decorative but no frame
try:
 f_title=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',38)
 f_med=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',23)
 f_key=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
except:
 f_title=f_med=f_key=ImageFont.load_default()
x,y=u(190,49)
d.text((x,y),'БУКИФОН',font=f_title,fill='#d8ebe4',anchor='mm')
d.text(u(190,64),'4 PART   /   8 VOICE',font=f_med,fill='#a9bcbc',anchor='mm')
d.text(u(190,76),'FM  •  MOD MATRIX',font=f_med,fill='#81aea2',anchor='mm')
# jacks
for row in rows:
 t=row['kind']; x=float(row['center_X_mm']); y=float(row['center_Y_mm'])
 if t=='mini_jack':
  circ(x,y,4.9,'#6b737a','#dce0e2',2)
  circ(x,y,2.8,'#1b222a','#939ca2',1)
  circ(x,y,1.1,'#05090d')
# encoders
for row in rows:
 if row['kind']!='encoder':continue
 x,y=float(row['center_X_mm']),float(row['center_Y_mm'])
 circ(x+.6,y+1,7.35,'#6e7b83')
 circ(x,y,7,'#333d44','#6a7983',2)
 circ(x-.7,y-1.1,5.5,'#434c54','#37434b',1)
 circ(x-.7,y-1.1,.6,'#9cb1b8')
 label=row['id'].split('_')[-1]
 d.text(u(x,y+11.2),label,font=f_med,fill='#33424a',anchor='mm')
# fader grooves and caps
for x in (180,200):
 rect(x,149,4.2,66,'#73818b',radius=2)
 rect(x,149,2.5,63,'#202932',radius=1)
 rect(x+.7,150,16,12,'#7e8a93',radius=1.3)
 rect(x,148.7,16,11,'#333c45','#9da8b0',radius=1.5,wd=2)
# keys after fader drawing
for row in rows:
 if row['kind']!='keycap_photo_ref':continue
 x=float(row['center_X_mm']); y=float(row['center_Y_mm']); a=float(row['angle_deg'])
 rr_key(x,y,a)
 d=ImageDraw.Draw(base)
 d.text(u(x,y),row['id'].split('K')[-1],font=f_key,fill='#44515a',anchor='mm')
# annotations outside panel
d=ImageDraw.Draw(base)
d.text((mx,33),'БУКИФОН  /  ВИД СВЕРХУ',font=f_title,fill='#edf0f3')
d.text((mx,H-45),'380 × 210 мм   •   Ортографический вид   •   Геометрия клавиш восстановлена по фото (не KiCad)',font=f_med,fill='#c2cbd2')
base.convert('RGB').save(p/'bukifon_top_view.png',quality=94)
print(p/'bukifon_top_view.png')
