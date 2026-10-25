import numpy as np, subprocess, os, hashlib, json, time
from PIL import Image, ImageDraw, ImageFont
W,H,STRIDE=1024,768,4096
FB='/dev/fb0'
FONT=None
for p in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
          '/usr/share/fonts/opentype/wqy/wqy-microhei.ttc',
          '/nix/store/']:
    if os.path.exists(p) and p.endswith('.ttc'): FONT=p; break
if FONT is None:
    r=subprocess.run(['bash','-c','fc-list 2>/dev/null | grep -i -m1 wqy'],capture_output=True,text=True)
    if r.stdout:
        FONT=r.stdout.split(':')[0].strip()
print("FONT:",FONT)
img=Image.new('RGB',(W,H),(16,18,26))
d=ImageDraw.Draw(img)
f1=ImageFont.truetype(FONT,34) if FONT else ImageFont.load_default()
f2=ImageFont.truetype(FONT,26) if FONT else ImageFont.load_default()
fs=ImageFont.truetype(FONT,22) if FONT else ImageFont.load_default()
lines=[
 ("157 传感器自检: 次声 / 痛阈 / 工作区",(120,220,255)),
 ("",(255,255,255)),
 ("A 次声: 抖动传感器 d'=0.183 但内存真实损伤 -312MB",(255,200,90)),
 ("   -> 每一刻都测不到, 伤害真实累积 (400MB底线前主动停)",(200,200,200)),
 ("",(255,255,255)),
 ("B 高增益: tau=95 过灵敏",(255,200,90)),
 ("   行动: FPR 0.400 失控率 0.600 终末抖动 36795ns",(255,140,140)),
 ("   禁行: FPR 0.200 失控率 0.000 终末抖动  3070ns",(140,255,140)),
 ("   -> 闸门有效; 应对本身也拖慢8倍(3032->25215)",(200,200,200)),
 ("",(255,255,255)),
 ("C 工作区宽度随信噪比收窄",(255,200,90)),
 ("   d'=129.6 -> 92.5% ; d'=24.9 -> 82.5% ; d'=8.5 -> 52.5%",(200,200,200)),
 ("",(255,255,255)),
 ("TOKEN K7M4QX   ALL PASS",(120,255,120)),
]
y=40
for t,c in lines:
    fo=f1 if y<80 else (fs if len(t)>0 and t.startswith('   ') else f2)
    d.text((60,y),t,font=fo,fill=c); y+= 44 if y<80 else 40
rgb=np.asarray(img,dtype=np.uint8)
row=np.zeros((H,STRIDE),dtype=np.uint8)
row[:,:W*3]=rgb[:,:,::-1].reshape(H,W*3)
data=row.tobytes()
with open(FB,'wb') as f: f.write(data)
with open(FB,'rb') as f: back=f.read(STRIDE*H)      # 同进程立即回采
ident = (back==data)
print("IDENTICAL:",ident,"sha:",hashlib.sha256(back).hexdigest()[:12])
img.save('render157.png')
open('fb_raw.bin','wb').write(back)
# 还原成png供OCR
arr=np.frombuffer(back,dtype=np.uint8).reshape(H,STRIDE)
img2=Image.fromarray(arr[:,:W*3].reshape(H,W,3)[:,:,::-1])
img2.save('captured.png')
print("saved")
