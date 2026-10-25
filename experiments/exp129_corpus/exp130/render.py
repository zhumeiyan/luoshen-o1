import pathlib
from PIL import Image, ImageDraw, ImageFont
W,H=1024,768
img=Image.new("RGBA",(W,H),(255,255,255,255))
d=ImageDraw.Draw(img)
try: f=ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",19)
except Exception: f=ImageFont.load_default()
fs=None
for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
    try: fs=ImageFont.truetype(p,17)
    except Exception: pass
fs=fs or f
TOKEN="K7M4QX"
rows=[("evalguard v0.4 -- exp130 localisation",fs),
 ("",fs),
 ("real corpus 27 files / 9 frameworks",fs),
 ("pre-gate   findings 44   unlocalised 38   86.4%",fs),
 ("post-gate  findings 35   unlocalised  0    0.0%",fs),
 ("",fs),
 ("hand triage  TP 2   FP 33   precision 5.7%",fs),
 ("ship gate 60%  ->  FAIL  not for sale",fs),
 ("",fs),
 ("recall planted 12/12   pro 15/15",fs),
 ("clean_eval 0    pro_clean 6 (known FP)",fs),
 ("crashes 0",fs),
 ("",fs),
 ("TOKEN "+TOKEN,fs)]
y=40
for t,fo in rows:
    d.text((60,y),t,font=fo,fill=(0,0,0,255)); y+=34
img.save("render130.png")
open("token.txt","w").write(TOKEN)
print("rendered", img.size)
