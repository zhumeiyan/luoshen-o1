# -*- coding: utf-8 -*-
"""真二维 vs 假二维：把文字渲染成图，量『垂直方向到底有没有信息』。"""
import json, numpy as np, os
from PIL import Image, ImageDraw, ImageFont

def font(sz, mono=False):
    cands = (["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"] if mono else []) + [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in cands:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return None

def render(text, W, H, mono=False, sz=80):
    f=font(sz,mono)
    im=Image.new("L",(W,H),0); d=ImageDraw.Draw(im)
    if f is None: return np.array(im)
    bb=d.textbbox((0,0),text,font=f)
    w=bb[2]-bb[0]; h=bb[3]-bb[1]
    if w>W:   # 缩到目标宽
        f=font(int(sz*W/w*0.95), mono); bb=d.textbbox((0,0),text,font=f)
        w=bb[2]-bb[0]; h=bb[3]-bb[1]
    d.text(((W-w)/2-bb[0],(H-h)/2-bb[1]),text,fill=255,font=f)
    return np.array(im).astype(np.float32)/255

def proj_entropy(a, axis):
    """沿 axis 压缩，得到一维投影，再算归一化熵（0=完全集中，1=均匀）"""
    p=a.sum(axis=axis); p=p/p.sum()
    p=p[p>0]
    H=-(p*np.log2(p)).sum()
    return H/np.log2(len(p))     # 归一化到 0..1

if __name__=="__main__":
    out={}
    W,H=560,200
    print("=== 控制到同样宽度，量【垂直方向有没有信息】===")
    print(f"  {'样本':<22}{'水平投影熵':>11}{'垂直投影熵':>11}{'垂直/水平':>10}")
    samples=[("汉字 森","森"),("汉字 想","想"),("汉字 国","国"),
             ("汉字 江海湖","江海湖"),
             ("英文 forest","forest"),("英文 think","think"),
             ("英文 nation","nation"),("英文 rivers","rivers"),
             ("代码 def f(x)","def f(x):"),("代码 return","return x*2")]
    rows=[]
    for name,t in samples:
        mono = name.startswith("代码")
        a=render(t,W,H,mono=mono)
        if a.sum()==0: print(f"  {name:<22}  (字体缺失)"); continue
        he=proj_entropy(a,0)   # 压缩行 → 每列的量 → 水平方向结构
        ve=proj_entropy(a,1)   # 压缩列 → 每行的量 → 垂直方向结构
        rows.append((name,he,ve,ve/he))
        print(f"  {name:<22}{he:>11.3f}{ve:>11.3f}{ve/he:>10.2f}")
        out[name]={"水平":round(he,3),"垂直":round(ve,3),"比":round(ve/he,2)}
    cn=[r for r in rows if r[0].startswith("汉字")]
    en=[r for r in rows if r[0].startswith("英文")]
    cd=[r for r in rows if r[0].startswith("代码")]
    for grp,nm in [(cn,"汉字"),(en,"英文"),(cd,"代码")]:
        if grp: print(f"  ── {nm}: 垂直/水平 = {np.mean([g[3] for g in grp]):.2f}")
    if cn and en:
        print(f"  ★ 汉字垂直方向的信息是英文的 {np.mean([g[2] for g in cn])/np.mean([g[2] for g in en]):.2f} 倍")
        out["汉字垂直信息是英文的几倍"]=round(np.mean([g[2] for g in cn])/np.mean([g[2] for g in en]),2)
    if cn and cd:
        print(f"  ★ 汉字垂直方向的信息是代码的 {np.mean([g[2] for g in cn])/np.mean([g[2] for g in cd]):.2f} 倍")

    print("\n=== 转置测试：把图转 90°，结构还剩多少 ===")
    print(f"  {'样本':<22}{'原图非零':>9}{'转置后与自身相关性':>18}")
    for name,t in samples[:8]:
        mono=name.startswith("代码")
        a=render(t,W,H,mono=mono)
        if a.sum()==0: continue
        at=np.rot90(a)
        # 转置后与原图在同一坐标系下比较：把两者都 pad 到同形状
        m=min(a.shape[0],a.shape[1])
        c=np.corrcoef(a[:m,:m].ravel(), at[:m,:m].ravel())[0,1]
        print(f"  {name:<22}{int((a>0.5).sum()):>9}{c:>18.3f}")
    print(f"  ★ 一维的东西转 90° 就散了；二维的东西转完还有骨架")

    json.dump(out, open("参数库/二维度.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/二维度.json")
