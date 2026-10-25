import pathlib, random
W,H=1024,768
try:
    v=pathlib.Path("/sys/class/graphics/fb0/virtual_size").read_text().split(",")
    W,H=int(v[0]),int(v[1])
except Exception: pass
from PIL import Image, ImageDraw, ImageFont
fp="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
f=ImageFont.truetype(fp,25); f2=ImageFont.truetype(fp,18)
TOKEN="M8R4VX"
img=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(img)
lines=[
 f"TOKEN {TOKEN}",
 "exp134 independent corpus 7 new repos",
 "recall planted 17 rules pro 16 rules crash 0",
 "gate G3 line-level 15 of 29 = 51.7 pct FAIL",
 "gate G4 file-level 1 of 16 = 6.2 pct FAIL",
 "syntax EG005 EG006 EGP01 EGP04 15 of 16 = 93.8",
 "methodology 1 of 29 = 3.4 pct",
 "loose standard 42 of 45 = 93.3 but REJECTED exp131",
 "EG002 no baseline 0 of 2 on new corpus",
 "bare except EG006 7 of 8 div EG005 6 of 6",
 "split is syntax vs methodology not present absent",
 "VERDICT DO NOT SHIP METHODOLOGY RULES",
]
y=48
for i,t in enumerate(lines):
    d.text((50,y),t,fill="black",font=f if i<2 else f2); y+=50
img.save("render134.png")
raw=img.convert("RGBA").tobytes()
pathlib.Path("/dev/fb0").write_bytes(raw)
cap=pathlib.Path("/dev/fb0").read_bytes()[:len(raw)]
print("bytes wrote",len(raw),"read",len(cap),"equal:",raw==cap)
