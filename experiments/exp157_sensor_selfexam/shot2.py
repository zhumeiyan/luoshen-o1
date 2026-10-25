import numpy as np, hashlib
from PIL import Image, ImageDraw, ImageFont
W,H,STRIDE=1024,768,4096; FB='/dev/fb0'
FONT='/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
img=Image.new('RGB',(W,H),(255,255,255))
d=ImageDraw.Draw(img)
fT=ImageFont.truetype(FONT,44); f1=ImageFont.truetype(FONT,38); f2=ImageFont.truetype(FONT,34)
rows=[
 ("157 SENSOR SELF-EXAM",fT,(0,0,0)),
 ("A SUBSONIC: d'=0.183  DAMAGE -312MB",f1,(180,60,0)),
 ("B TAU=95 ACT: FPR 0.400 RUN 0.600",f1,(180,0,0)),
 ("B TAU=95 HOLD: FPR 0.200 RUN 0.000",f1,(0,120,0)),
 ("C WIDTH 92.5% 82.5% 52.5%",f1,(0,0,180)),
 ("TOKEN K7M4QX",fT,(0,0,0)),
]
y=50
for t,fo,c in rows:
    d.text((50,y),t,font=fo,fill=c); y+=88
rgb=np.asarray(img,dtype=np.uint8)
row=np.zeros((H,STRIDE),dtype=np.uint8); row[:,:W*3]=rgb[:,:,::-1].reshape(H,W*3)
data=row.tobytes()
open(FB,'wb').write(data)
back=open(FB,'rb').read(STRIDE*H)
print("IDENTICAL:",back==data,"sha:",hashlib.sha256(back).hexdigest()[:12])
arr=np.frombuffer(back,dtype=np.uint8).reshape(H,STRIDE)
Image.fromarray(arr[:,:W*3].reshape(H,W,3)[:,:,::-1]).save('captured2.png')
