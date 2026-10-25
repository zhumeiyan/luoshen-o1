import os,hashlib,time
W,H,SS=1024,768,4096
TOKEN='K7M4QX'
import struct
buf=bytearray(b'\x00'*(SS*H))
def px(x,y,r,g,b):
    o=y*SS+x*4
    buf[o]=b; buf[o+1]=g; buf[o+2]=r; buf[o+3]=0
# 画色块+文字行(用简单点阵Digit)
rows=[
 ('ALLAN floor slope m4-16','-0.039 -0.019'),
 ('dprime N1 vs N64 delta20','0.258 0.258'),
 ('drift vs signal ratio','5544 / 763 = 7.3x'),
 ('injected drift ratio','1525287 / 391 = 3904x'),
 ('absolute readout dprime','0.0032'),
 ('differential disc','0.3867'),
 ('dual mode human TPR','0.017'),
 ('TOKEN','%s'%TOKEN),
]
y=40
for k,v in rows:
    # 左侧标签条
    for i in range(len(k)*3):
        for dy in range(24):
            px(40+i*3, y+dy, 200,180,60)
    # 右侧数值条(灰阶编码)
    for i in range(len(v)*3):
        for dy in range(24):
            px(600+i*3, y+dy, 240,240,240)
    y+=60
raw=bytes(buf)
h=hashlib.sha256(raw).hexdigest()[:12]
with open('/dev/fb0','wb') as f: f.write(raw)
with open('/dev/fb0','rb') as f: cap=f.read(SS*H)
print('write bytes',len(raw))
print('cap  bytes',len(cap))
print('IDENTICAL', raw==cap)
print('sha', h, 'cap_sha', hashlib.sha256(cap).hexdigest()[:12])
open('render.raw','wb').write(raw); open('captured.raw','wb').write(cap)
open('token.txt','w').write(TOKEN)
