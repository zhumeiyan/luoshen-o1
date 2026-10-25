from PIL import Image, ImageDraw, ImageFont
import random, hashlib
W,H=1024,768
F="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
def f(sz):
    try: return ImageFont.truetype(F,sz)
    except: return ImageFont.load_default()
tok="".join(random.choice("ACDEFGHJKLMNPQRTUVWXY34789") for _ in range(6))
im=Image.new("RGB",(W,H),(255,255,255)); d=ImageDraw.Draw(im)
d.rectangle([0,0,W,54],fill=(24,32,56))
d.text((18,14),"EXP 132  SEMANTIC ANCHORS  —  where a finding's evidence lives",font=f(22),fill=(255,255,255))
d.text((18,66),"judged by: does the reader, on opening that line, see the thing accused?",font=f(15),fill=(60,60,60))
y=98
def head(t):
    global y
    d.text((18,y),t,font=f(19),fill=(20,60,140)); y+=27
def row(a,b,c,col=(30,30,30)):
    global y
    d.text((30,y),a,font=f(15),fill=col); d.text((330,y),b,font=f(15),fill=col)
    d.text((700,y),c,font=f(15),fill=col); y+=22
head("1. EG016  the one clean falsifiable pair")
row("docstring URL only","no remote CALL node","EG016 silent   OK",(20,110,40))
row("real requests.get(...)","CALL node found","EG016 -> L3   OK",(20,110,40))
y+=6
head("2. EG002  my own anchor regression (found and fixed)")
row("exp131 anchor","L666 example.update(metrics)","strict TP",(20,110,40))
row("exp132 v1","L667 acc[...].append(example)","DOWNGRADED",(190,30,30))
row("cause","'append' was in the emit list","collect != report",(190,30,30))
row("exp132 v2","L613 for (task,acc) in zip(...)","repaired",(20,110,40))
y+=6
head("3. gates")
row("planted recall","12/12","pro 14/14",(20,110,40))
row("rule crashes","0","",(20,110,40))
row("strict precision","2/22 = 9%","gate 60%",(190,30,30))
y+=6
head("4. lesson")
d.text((30,y),"classifying by CALL NAME is the wrong axis;",font=f(16),fill=(90,30,30)); y+=22
d.text((30,y),"the metric WORD is the stable signal in real code.",font=f(16),fill=(90,30,30)); y+=26
d.rectangle([14,y,W-14,y+40],fill=(190,30,30))
d.text((28,y+10),"VERDICT   DO NOT SHIP   anchors better, precision still 9%",
       font=f(19),fill=(255,255,255))
d.text((18,H-30),"TOKEN "+tok,font=f(20),fill=(0,0,0))
im.save("fig132.png")
open("token.txt","w").write(tok)
print("TOKEN",tok, "sha", hashlib.sha256(im.tobytes()).hexdigest()[:12])
