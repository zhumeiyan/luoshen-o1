from PIL import Image,ImageDraw,ImageFont
import hashlib,os
W,H=1024,768
TOKEN='K7M4QX'
img=Image.new('RGB',(W,H),(0,0,0)); d=ImageDraw.Draw(img)
fp='/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
try: f=ImageFont.truetype(fp,22)
except: f=ImageFont.load_default(); print('FONT fallback')
lines=[
 'ALLAN SLOPE m4-16 = -0.039 -0.019 (FLICKER FLOOR)',
 'DPRIME N1=0.258  N64=0.258  (NO GAIN FROM INTEGRATION)',
 'DRIFT 5544 NS  vs  SIGNAL 763 NS   = 7.3 X',
 'INJECTED DRIFT 1525287 / 391 = 3904 X',
 'ABSOLUTE READOUT DPRIME = 0.0032  (BLIND)',
 'DIFFERENTIAL DISC = 0.3867  TPR 0.890',
 'DUAL MODE HUMAN TPR = 0.017  (CANNOT COEXIST AT D=0.35)',
 'VERDICT: CHANGE THE READOUT NOT THE SENSOR',
 'TOKEN %s'%TOKEN,
]
y=30
for i,t in enumerate(lines):
    d.text((30,y),t,font=f,fill=(255,240,120) if i<8 else (120,255,180))
    y+=58
raw=img.tobytes()
bpp=4; SS=W*bpp
# 转 BGRA 帧缓冲格式
ba=bytearray(SS*H)
src=img.convert('RGBA').tobytes()
for i in range(0,len(src),4):
    r,g,b,a=src[i],src[i+1],src[i+2],src[i+3]
    j=(i//4)*4
    ba[j]=b; ba[j+1]=g; ba[j+2]=r; ba[j+3]=a
out=bytes(ba)
h=hashlib.sha256(out).hexdigest()[:12]
with open('/dev/fb0','wb') as fo: fo.write(out)
with open('/dev/fb0','rb') as fi: cap=fi.read(SS*H)
print('bytes',len(out),'cap',len(cap),'IDENTICAL',out==cap)
print('sha',h,'cap',hashlib.sha256(cap).hexdigest()[:12])
img.save('render.png')
# 回读重建PNG
im2=Image.frombytes('RGBA',(W,H),bytes(bytearray(
  b''.join(bytes([cap[j+2],cap[j+1],cap[j],255]) for j in range(0,len(cap),4)))))
im2.convert('RGB').save('captured.png')
open('token.txt','w').write(TOKEN)
print('saved render.png captured.png')
