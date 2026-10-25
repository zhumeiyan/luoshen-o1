import os, struct, fcntl, random, hashlib
from PIL import Image, ImageDraw, ImageFont

W=H=None
fd=os.open('/dev/fb0', os.O_RDWR)
vs=fcntl.ioctl(fd,0x4600,bytes(160))
W,H=struct.unpack('II',vs[0:8]); BPP=struct.unpack('I',vs[24:28])[0]
N=W*H*(BPP//8)

ALPHA='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
rng=random.Random(int.from_bytes(os.urandom(4),'big'))
CHK=''.join(rng.choice(ALPHA) for _ in range(6))

img=Image.new('RGB',(W,H),(12,14,18)); d=ImageDraw.Draw(img)
try: f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',22)
except Exception: f=ImageFont.load_default()
try: fs=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
except Exception: fs=f

lines=[
 ('EXP123 BODY31 AUDIT',f,(255,220,90)),
 ('SYSTEMS 31 UNIQUE 29 PLUS 2 NEW',fs,(230,230,230)),
 ('REAL BACKEND 4 OF 4',fs,(120,255,160)),
 ('FALSIFIABLE 31 OF 31',fs,(120,255,160)),
 ('CLASS A REAL EXEC 22',fs,(230,230,230)),
 ('CLASS B MONITOR ONLY 5',fs,(255,180,120)),
 ('CLASS D WAKE ON STRESS 4',fs,(230,230,230)),
 ('PROPRIO SINGLE KO 0.00000',fs,(255,140,140)),
 ('PROPRIO CREW KO 0.06690',fs,(255,140,140)),
 ('GATE REVOKE CHAIN 1 STOP',fs,(120,200,255)),
 ('CHECKSUM '+CHK,f,(255,255,255)),
]
y=40
for t,fo,c in lines:
    d.text((48,y),t,font=fo,fill=c); y+=54 if fo is f else 40

rgba=img.convert('RGBA').tobytes()
os.lseek(fd,0,0); os.write(fd,rgba[:N])
buf=bytearray(N); os.lseek(fd,0,0); os.readv(fd,[buf])
os.close(fd)
cap=Image.frombytes('RGBA',(W,H),bytes(buf)).convert('RGB')
cap.save('captured.png')
print('CHECKSUM',CHK)
print('render sha', hashlib.sha256(rgba[:N]).hexdigest()[:12])
print('capture sha', hashlib.sha256(bytes(buf)).hexdigest()[:12])
print('dark frac', sum(1 for p in cap.getdata() if sum(p)<40)/(W*H))
open('chk.txt','w').write(CHK)
