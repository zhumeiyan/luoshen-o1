import os, hashlib, subprocess, time
FB='/dev/fb0'; W,H,BPP=1080,1920,4
lines=[
 "172 VIRTUAL HAND selfcheck",
 "TOKEN K7M4QX",
 "real 854.01 us",
 "air 3.78 us",
 "ratio 225.9x",
 "dprime 0.485",
 "dirs with data 64",
 "empty dirs 16",
 "exp166 AIR 0/6",
 "exp168 SOLID 2/2",
 "exp170 SOLID 6/6",
 "exp171 SOLID 4/4",
 "exp155 SOLID 1/1",
 "exp161 SOLID 2/2",
]
try:
    from PIL import Image, ImageDraw, ImageFont
    have=True
except Exception: have=False
print("PIL:",have)
if have:
    img=Image.new('RGB',(W,H),(255,255,255)); d=ImageDraw.Draw(img)
    fp='/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
    try: f=ImageFont.truetype(fp,34)
    except Exception: f=ImageFont.load_default()
    y=60
    for L in lines:
        d.text((40,y),L,fill=(0,0,0),font=f); y+=52
    img.save('expect.png')
    with open(FB,'wb') as fh: fh.write(img.tobytes())
    time.sleep(0.5)
    with open(FB,'rb') as fh: back=fh.read(W*H*BPP)
    exp=img.tobytes()
    print("IDENTICAL:", back==exp, "sha:", hashlib.sha256(back).hexdigest()[:12])
    open('captured.png','wb').write(back[:W*H*BPP])
