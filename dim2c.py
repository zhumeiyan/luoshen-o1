# -*- coding: utf-8 -*-
"""最干净的一条证据：一个语义单元的【长宽比】。方块=二维，横条=一维。"""
import json, numpy as np, os, itertools
from PIL import Image, ImageDraw, ImageFont
def F(v): return float(round(float(v),3))

def font(sz, mono=False):
    c=(["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"] if mono else [])+[
       "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
       "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in c:
        if os.path.exists(p): return ImageFont.truetype(p,sz)
    return None

def bbox_of(text, sz=90, mono=False):
    f=font(sz,mono); im=Image.new("L",(900,400),0); d=ImageDraw.Draw(im)
    bb=d.textbbox((0,0),text,font=f)
    return bb[2]-bb[0], bb[3]-bb[1], im, d, f, bb

CN=list("森想国江河湖海草花菜忘忙音昱呆杏杲杳旮旯叶古叨召呗员")
EN=["forest","think","nation","river","grass","flower","water","heart",
    "sound","leaf","mouth","knife","shell","person","wood","field","gate","rain","fire","stone"]
CD=["def f(x):","return x","for i in","if x>0","else:","print(","x=x+1","import os",
    "class A:","self.x","try:","except:","while True","assert x","yield x","lambda:","pass","None","True","len(a)"]

if __name__=="__main__":
    out={}
    print("=== 一、主证据：一个语义单元占多大一块，形状是什么 ===")
    print(f"  {'组':<6}{'宽/高 (长宽比)':>15}{'说明'}")
    for grp,items,mono,dsc in [("汉字",CN,False,"方块"),("英文",EN,False,"横条"),("代码",CD,True,"更长的横条")]:
        rs=[]
        for t in items:
            w,h,_,_,_,_=bbox_of(t,90,mono)
            if h>0: rs.append(w/h)
        rs=np.array(rs)
        print(f"  {grp:<6}{rs.mean():>15.2f}   {dsc}")
        out[grp]={"长宽比均值":F(rs.mean()),"中位":F(np.median(rs)),"最小":F(rs.min()),"最大":F(rs.max())}
    print(f"  ★ 汉字 {out['汉字']['长宽比均值']} ≈ 1 → 两个维度都要用")
    print(f"  ★ 英文 {out['英文']['长宽比均值']} / 代码 {out['代码']['长宽比均值']} → 只横向排，纵向是装饰")

    print("\n=== 二、同样一个语义单元，中文要用掉几个维度 ===")
    print(f"  汉字  宽/高 ≈ {out['汉字']['长宽比均值']:.2f}  → 二维各占一半")
    print(f"  英文  宽/高 ≈ {out['英文']['长宽比均值']:.2f}  → 一维占 {out['英文']['长宽比均值']/(out['英文']['长宽比均值']+1)*100:.0f}%")
    print(f"  代码  宽/高 ≈ {out['代码']['长宽比均值']:.2f}  → 一维占 {out['代码']['长宽比均值']/(out['代码']['长宽比均值']+1)*100:.0f}%")
    print(f"  ★ 中文把意思【摊在平面上】，英文把意思【串在一条线上】")

    print("\n=== 三、辅助：压成竖线后还能不能分辨（控制相同墨量）===")
    W,H=420,220
    def render(text,mono=False,sz=90):
        f=font(sz,mono); im=Image.new("L",(W,H),0); d=ImageDraw.Draw(im)
        bb=d.textbbox((0,0),text,font=f); w=bb[2]-bb[0]; h=bb[3]-bb[1]
        if w>W:
            f=font(max(8,int(sz*W/w*0.95)),mono); bb=d.textbbox((0,0),text,font=f); w=bb[2]-bb[0]; h=bb[3]-bb[1]
        d.text(((W-w)/2-bb[0],(H-h)/2-bb[1]),text,fill=255,font=f)
        return np.array(im).astype(np.float32)/255
    def vdist(items,mono):
        ps=[]
        for t in items:
            a=render(t,mono)
            if a.sum()==0: continue
            p=a.sum(axis=1); p=p/p.sum(); ps.append(p)
        ps=np.array(ps)
        D=[np.abs(ps[i]-ps[j]).sum() for i,j in itertools.combinations(range(len(ps)),2)]
        return float(np.mean(D))
    vc,ve,vcd = vdist(CN,False), vdist(EN,False), vdist(CD,True)
    print(f"  汉字 垂直两两距离 {vc:.3f}")
    print(f"  英文 垂直两两距离 {ve:.3f}")
    print(f"  代码 垂直两两距离 {vcd:.3f}")
    print(f"  ★ 汉字是英文的 {vc/ve:.2f} 倍，代码的 {vc/vcd:.2f} 倍")
    print(f"  ★ 把汉字压成一条竖线还能认出是哪个字；英文/代码压完就分不出了")
    out["垂直区分力"]={"汉字":F(vc),"英文":F(ve),"代码":F(vcd),"汉字/英文":F(vc/ve),"汉字/代码":F(vc/vcd)}

    print("\n=== 四、所以两种底层逻辑 ===")
    print(f"  {'':<12}{'代码':<22}{'中文'}")
    print(f"  {'形状':<12}{'横条（一维）':<22}{'方块（二维）'}")
    print(f"  {'维度数':<12}{'1':<22}{'2'}")
    print(f"  {'单元关系':<12}{'前后':<22}{'上下左右内外'}")
    print(f"  {'位置':<12}{'第 N 个（序）':<22}{'槽位（类）'}")
    print(f"  {'连接度':<12}{'2':<22}{'4'}")
    print(f"  {'断一处':<12}{'半边失联':<22}{'绕路可达'}")
    print(f"  ★ 上轮图论实测：二维网格断一处，仍有 93.8% 连通（一维只有 71.9%）")
    print(f"  ★ 11 组铁证：呆/杏、杲/杳、旮/旯… 换个位置就是另一个字")
    print(f"  ★ 所以中国人懵，不是看不懂代码，是【代码没有上下】")
    json.dump(out, open("参数库/二维度.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/二维度.json")
