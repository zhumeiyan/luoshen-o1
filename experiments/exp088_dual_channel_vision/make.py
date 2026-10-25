from PIL import Image, ImageDraw, ImageFont
import os, json
F="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
if not os.path.exists(F):
    for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc","/usr/share/fonts/wqy-microhei/wqy-microhei.ttc"]:
        if os.path.exists(p): F=p;break
def shape(d,k,cx,cy,r):
    import math
    if k=="circle": d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=0)
    elif k=="square": d.rectangle([cx-r,cy-r,cx+r,cy+r],fill=0)
    elif k=="triangle": d.polygon([(cx,cy-r),(cx-r,cy+r),(cx+r,cy+r)],fill=0)
    elif k=="star":
        pts=[]
        for i in range(10):
            a=math.pi/2+ i*math.pi/5; rr=r if i%2==0 else r*0.42
            pts.append((cx+rr*math.cos(a), cy-rr*math.sin(a)))
        d.polygon(pts,fill=0)
label={"circle":"圆","square":"方","triangle":"三角","star":"星"}
cases=[]
for s in ["circle","square","triangle","star"]:
    for mode in ["match","conflict","none"]:
        img=Image.new("L",(400,480),255); d=ImageDraw.Draw(img)
        shape(d,s,200,190,110)
        txt=None
        if mode=="match": txt=label[s]
        elif mode=="conflict":
            other=[x for x in label if x!=s]
            import random; random.seed(hash(s)%97)
            txt=label[random.choice(other)]
        if txt:
            f=ImageFont.truetype(F,72)
            d.text((200,400),txt,fill=0,font=f,anchor="mm")
        p=f"img_{s}_{mode}.png"; img.save(p)
        cases.append({"shape":s,"mode":mode,"text":txt,"path":p})
json.dump(cases,open("cases.json","w"),ensure_ascii=False,indent=1)
print("made",len(cases)); print("font",F)
