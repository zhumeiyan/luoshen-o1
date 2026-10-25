import struct, fcntl, subprocess, random, hashlib
from PIL import Image, ImageDraw, ImageFont

FB="/dev/fb0"
# 先问设备真实几何，不凭印象（111 教训）
with open(FB,'rb') as f:
    fix=fcntl.ioctl(f, 0x4600, b'\0'*68)
w,h=struct.unpack('<II', fix[8:16]); bpp=struct.unpack('<I', fix[24:28])[0]
print(f"fb0 geometry: {w}x{h} bpp={bpp}")

CODE="".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
ROWS=[
 ("EO115 DIGESTIVE CODE", CODE),
 ("v1 chain   30", "unique  3  dup 90%"),
 ("v2 chain    3", "unique  3  dup  0%"),
 ("v1 energy 250", "v2 energy 63.8"),
 ("v1 perpetuum", "0 -> 200 feed20"),
 ("v2 real meta", "100 -> 41.6"),
 ("bug1 no cost", "bug2 meta trashed"),
 ("bug3 dupchain", "bug4 no EN split"),
]
img=Image.new("RGBA",(w,h),(255,255,255,255))
d=ImageDraw.Draw(img)
try: FONT=ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",26)
except: FONT=ImageFont.load_default()
y=40
for a,b in ROWS:
    d.text((40,y),f"{a}   {b}",fill=(0,0,0,255),font=FONT); y+=52
d.rectangle([30,25,w-30,y+15],outline=(200,0,0,255),width=4)
img.save("render_check.png")

# 32bpp -> RGBA（111 教训：fb0 是 RGBA 不是 RGB）
rgba=img.convert("RGBA").tobytes()
need=w*h*(bpp//8)
print(f"bytes: have={len(rgba)} need={need}")
assert len(rgba)==need, "尺寸不符，别硬写"
with open(FB,'wb') as f: f.write(rgba)

# 真实采集
subprocess.run(["python3","-c","""
from PIL import Image
import struct,fcntl
FB='/dev/fb0'
with open(FB,'rb') as f:
    fix=fcntl.ioctl(f,0x4600,b'\\0'*68)
    w,h=struct.unpack('<II',fix[8:16]); bpp=struct.unpack('<I',fix[24:28])[0]
    f.seek(0); raw=f.read(w*h*(bpp//8))
im=Image.frombytes('RGBA',(w,h),raw).convert('RGB')
im.save('/data/workspace/luoshen-o1/experiments/exp115_digestive/captured.png')
print('captured bytes=',len(raw))
"""],check=True)
print("CODE =",CODE)
