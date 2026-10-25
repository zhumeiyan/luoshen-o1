import os,subprocess,hashlib,json,time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ["WenQuanYi Micro Hei","Noto Sans CJK SC"]:
    try:
        font_manager.findfont(f,fallback_to_default=False)
        plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False

OUT="/data/workspace/luoshen-o1/experiments/exp169_fourcodes"
TOKEN="K7M4QX"
lines=[
 "EXP169  四种语言系统的关系   TOKEN "+TOKEN,
 "统一 N=66379   语料: 判据核汉字 / Python注释docstring英文 / 标识符 / 数字",
 "",
 "Heaps指数 b (符号集是否封闭):",
 "  数字 0.000   V=10 恒定  零维",
 "  汉字 0.310   收敛侧",
 "  英文 0.643   发散侧",
 "  代码 0.671   发散侧",
 "",
 "2gram空间占用 V2/V1^2:",
 "  数字 1.0000  完全饱和",
 "  汉字 0.0139",
 "  英文 0.0007",
 "  代码 0.0008",
 "",
 "受控对照 V0=1000 N=78724 (消除N/V混杂):",
 "  出度  汉字 32.02   英文 33.64   代码 29.99   差异<6%",
 "  结论: 汉字组合自由度与英文代码无本质差别",
 "",
 "共同覆盖子集 held-out 冗余 (三折符号一致):",
 "  数字 -0.0323   汉字 -0.0223   英文 -0.0218   代码 -0.0464",
 "  全部为负(协同) -> 该指标不区分四系统",
 "",
 "二阶增益/一阶增益 gb/g1:",
 "  数字 6.44   代码 2.15   英文 1.80   汉字 1.41",
 "",
 "阴性: 汉字多维在序列统计层不成立",
 "照报: 结构层(部件/形声/二维)本机无拆分数据, 造不出",
]
fig=plt.figure(figsize=(10,12),dpi=100)
fig.patch.set_facecolor("white")
plt.axis("off")
y=0.97
for i,t in enumerate(lines):
    bold = (i==0) or t.startswith("阴性") or t.startswith("照报") or t.startswith("结论")
    size=13 if i==0 else (11 if bold else 10)
    plt.text(0.02,y,t,fontsize=size,fontweight="bold" if bold else "normal",
             va="top",family=plt.rcParams["font.sans-serif"][0])
    y-= 0.045 if i==0 else 0.037
plt.savefig(f"{OUT}/render169.png",facecolor="white")
print("render ok")

# ---- 写 fb0 并回采 ----
FB="/dev/fb0"
res={"fb_exists":os.path.exists(FB)}
if os.path.exists(FB):
    subprocess.run(["python3","-c","""
import numpy as np,struct
from PIL import Image
im=Image.open('%s/render169.png').convert('RGB')
W,H=1280,720
im=im.resize((W,H))
a=np.asarray(im,dtype=np.uint8)
# BGR888 -> 16bpp RGB565
r=(a[:,:,0]>>3).astype(np.uint16); g=(a[:,:,1]>>2).astype(np.uint16); b=(a[:,:,2]>>3).astype(np.uint16)
px=(r<<11)|(g<<5)|b
buf=px.astype('<u2').tobytes()
open('/tmp/fb.bin','wb').write(buf)
"""%OUT],check=True)
    data=open("/tmp/fb.bin","rb").read()
    n=len(data)
    res["bytes_written"]=n
    res["sha_write"]=hashlib.sha256(data).hexdigest()[:12]
    with open(FB,"wb") as f:
        f.write(data)
    time.sleep(0.3)
    with open(FB,"rb") as f:
        back=f.read(n)
    res["bytes_read"]=len(back)
    res["sha_read"]=hashlib.sha256(back).hexdigest()[:12]
    res["IDENTICAL"]=(back==data)
    res["diff_bytes"]=sum(1 for x,y in zip(data,back) if x!=y)
    # 回采存图
    subprocess.run(["python3","-c","""
import numpy as np
from PIL import Image
d=open('/dev/fb0','rb').read(%d)
a=np.frombuffer(d,dtype='<u2').reshape(720,1280)
r=((a>>11)&31).astype(np.uint8)*8; g=((a>>5)&63).astype(np.uint8)*4; b=(a&31).astype(np.uint8)*8
Image.fromarray(np.stack([r,g,b],axis=2)).save('%s/captured.png')
"""% (n,OUT)],check=True)
    res["ocr"]=subprocess.run(["tesseract",f"{OUT}/captured.png","stdout","--psm","6","-l","eng+chi_sim"],
                              capture_output=True,text=True).stdout[:1500]
print(json.dumps(res,ensure_ascii=False,indent=1))
json.dump(res,open(f"{OUT}/selfcheck.json","w"),ensure_ascii=False,indent=1)
