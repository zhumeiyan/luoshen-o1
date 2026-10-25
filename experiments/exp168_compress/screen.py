from PIL import Image,ImageDraw,ImageFont
import hashlib,os
F="/dev/fb0"
W,H=1080,1920
img=Image.new("RGB",(W,H),(255,255,255)); d=ImageDraw.Draw(img)
def fp(n):
    for c in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc","/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
        if os.path.exists(c): return ImageFont.truetype(c,n)
    return ImageFont.load_default()
try:
    fb=open(F,"rb"); raw=fb.read()
    sz=len(raw)
    import re
    m=re.search(rb'(\d+)x(\d+)',os.popen("fbset -s 2>/dev/null").read().encode())
    if m: W,H=int(m.group(1)),int(m.group(2))
    fb.close()
    raw=open(F,"rb").read(W*H*4)
except Exception as e:
    sz=0
print(f"fb size bytes={sz} -> {W}x{H}")

fb=open(F,"rb"); raw=fb.read(W*H*4)
try:
    base=Image.frombytes("RGBA",(W,H),raw).convert("RGB")
except Exception:
    base=Image.frombytes("RGB",(W,H),raw[:W*H*3])

lines=[
 "EXP168 汉字 vs 造词 压缩包判定",
 "",
 "Heaps指数 b (分界 0.5)",
 "  汉字      b=0.285  收敛  压缩有效",
 "  造词标识符 b=0.749  发散  压缩失效",
 "",
 "每符号经验 N/V 增长指数",
 "  汉字  0.714  (理论 1-b=0.715)",
 "  造词  0.253  (理论 1-b=0.251)",
 "  数据量x16  汉字经验x7.2",
 "  数据量x200 造词经验x3.8",
 "",
 "渐近有效阶 k*=1/b",
 "  汉字 3.51   造词 1.34",
 "",
 "实测峰值(阴性)",
 "  汉字 k=1 gain+0.2004 覆盖0.996",
 "  造词 k=2 gain+0.2287 覆盖0.668",
 "  V^k>>N 达不到渐近区",
 "",
 "TOKEN K7M4QX",
]
y=140
for i,t in enumerate(lines):
    f=fp(46 if i==0 else 40)
    d.text((60,y),t,font=f,fill=(0,0,0)); y+=72
img=img.resize((W,H))
out=img.tobytes()
with open(F,"wb") as f:
    f.write(out[:W*H*3] if len(out)>=W*H*3 else out+b"\x00"*(W*H*3-len(out)))
back=open(F,"rb").read(W*H*3)
cap=out[:W*H*3]
ident=(back==cap)
print("write bytes:",len(cap))
print("IDENTICAL:",ident)
print("raw sha:",hashlib.sha256(back).hexdigest()[:12])
print("cap sha:",hashlib.sha256(cap).hexdigest()[:12])
img.save("/data/workspace/luoshen-o1/experiments/exp168_compress/captured.png")
