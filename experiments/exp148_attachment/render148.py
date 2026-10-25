import hashlib, subprocess, os
from PIL import Image, ImageDraw, ImageFont
W,H=1024,768
TOKEN='M4K7XP'
lines=[
 'exp148 MAMMAL RUNG: ATTACHMENT',
 'world = real wall clock broadcast by real process',
 'distance = real relay sleep 40ms per hop',
 'A=0hop B=4hop C=5hop  me=3hop',
 '',
 'REAL ERROR GRADIENT (measured ms)',
 '  errA 18    errB 243    errC 314',
 '',
 'PREFERENCE  best=A in 5/5 runs',
 '  DIFF   pref +0.395  CI[+0.351,+0.449]',
 '  SAME   pref +0.103  null 0.049 [0.007,0.117]',
 '  bestA  DIFF 1.00   SAME 0.80 / 0.20 unstable',
 '',
 'ATTACHMENT SPECIFICITY  deficit(killA)-deficit(killC)',
 '  DIFF    +43.89  CI[+31.39,+55.25]  NOT CROSS 0',
 '  SAME    -10.79  CI[-24.87,+5.69]   CROSS 0  <-control',
 '  NOGATE  +46.68  CI[+36.62,+54.06]  NOT CROSS 0',
 '',
 'EMOTION GATE  NOGATE-DIFF = +2.79  CI[-11.33,+18.39] CROSS 0',
 '  gate shows NO measurable effect (negative result)',
 'PROBE RATE CHANGE ~ 0 : naive protest hypothesis FALSIFIED',
 '',
 'TOKEN %s'%TOKEN,
]
img=Image.new('RGB',(W,H),(255,255,255))
d=ImageDraw.Draw(img)
try: f=ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-micro-hei.ttc',22)
except Exception: f=ImageFont.load_default()
y=30
for ln in lines:
    d.text((40,y),ln,fill=(0,0,0),font=f); y+=34
raw=img.tobytes()
# 转成 BGRA 匹配 fb0 32bpp
b=bytearray()
for i in range(0,len(raw),3):
    b+=bytes((raw[i+2],raw[i+1],raw[i],255))
b=bytes(b)
expect=W*H*4
assert len(b)==expect,(len(b),expect)
fb=open('/dev/fb0','wb'); fb.write(b); fb.flush(); os.fsync(fb.fileno()); fb.close()
fb=open('/dev/fb0','rb'); cap=fb.read(expect); fb.close()
ok = (len(cap)==expect)
sha_w=hashlib.sha256(b).hexdigest()[:12]; sha_c=hashlib.sha256(cap).hexdigest()[:12]
# 回采字节转回 PNG
img2=Image.frombytes('RGB',(W,H),bytes(bytearray(x for i in range(0,expect,4) for x in (cap[i+2],cap[i+1],cap[i]))))
img2.save('captured.png')
out=subprocess.run(['tesseract','captured.png','stdout','--psm','6'],capture_output=True,text=True).stdout
hit=TOKEN in out.replace(' ','')
print('bytes_written=%d bytes_read=%d'% (len(b),len(cap)))
print('sha_write=%s sha_capture=%s IDENTICAL=%s'%(sha_w,sha_c,sha_w==sha_c))
print('TOKEN_HIT=%s'%hit)
print('--- OCR ---'); print(out.strip()[:900])
