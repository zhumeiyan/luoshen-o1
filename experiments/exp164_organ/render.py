import os, hashlib, subprocess, json
from PIL import Image, ImageDraw, ImageFont
W,H=1024,768
F="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
def f(sz):
    try: return ImageFont.truetype(F,sz)
    except Exception: return ImageFont.load_default()
im=Image.new("RGBA",(W,H),(255,255,255,255)); d=ImageDraw.Draw(im)
d.rectangle([0,0,W-1,H-1],outline=(0,0,0),width=3)
y=16
def line(t,sz=22,col=(0,0,0)):
    global y
    d.text((24,y),t,font=f(sz),fill=col); y+=sz+10
line("164 升维加器官  LUOSHEN  2026-10-19",26)
line("判据: 器官 = 通道 + 一个不听我的身体",22)
line("噪声是他者存在的证据，不是通道缺陷",22)
y+=8
line("S1 六个候选通道，谁真的活着:",23)
rows=[("cpu  /proc/self/stat","d=0.497  acc=0.513  半死(tick分辨率粗)"),
      ("sysc /proc/self/io","d=0.587  acc=0.550  半死"),
      ("load /proc/loadavg","spread=0  死(无他进程)"),
      ("mem  /proc/meminfo","d=402.9  acc=1.000  活"),
      ("net  /proc/net/dev","spread=0  死(无流量)"),
      ("ent  entropy_avail","spread=0  死(熵池固定)")]
for a,b in rows: line("  "+a+"  "+b,20)
y+=6
line("S2 决定性实验  MemAvailable 噪声:",23)
line("  A 我完全不动          stdev 82.5",21)
line("  B 我精确持有60MB      stdev 0.0   <- 我控制=零噪声=账本",21)
line("  C 有真实他进程在动    stdev 8747  <- 他者=噪声=器官",21)
y+=6
line("S3 破坏对照  弄瞎 mem: acc 1.000 -> 0.467",22)
line("结论 零噪声通道是账本不是器官 升维=引入噪声",22)
line("温度觉无真实通道: /sys/class/thermal 空",20,(150,0,0))
y+=6
line("TOKEN K7M4QX",28,(0,0,200))
raw=im.tobytes()
open("render.raw","wb").write(raw)
fb=open("/dev/fb0","wb"); fb.write(raw); fb.flush(); os.fsync(fb.fileno())
cap=open("/dev/fb0","rb").read(len(raw))
open("captured.raw","wb").write(cap)
same = hashlib.sha256(raw).hexdigest()==hashlib.sha256(cap).hexdigest()
diff=sum(1 for i in range(0,len(raw),4) if raw[i:i+4]!=cap[i:i+4])
im.save("captured.png")
print(json.dumps({"identical":same,"diff_px":diff,"bytes":len(raw),
                  "sha":hashlib.sha256(raw).hexdigest()[:12]},indent=1))
