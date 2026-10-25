# -*- coding: utf-8 -*-
"""修正 glyph.py 里两处我不该说的话"""
import json, math
from PIL import Image, ImageDraw, ImageFont
import numpy as np
FT="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"

def render(ch,size,path=FT):
    f=ImageFont.truetype(path,size)
    im=Image.new("L",(size*2,size*2),0); ImageDraw.Draw(im).text((size//2,size//2),ch,fill=255,font=f)
    a=np.array(im); ys,xs=np.nonzero(a>127)
    return (a[ys.min():ys.max()+1, xs.min():xs.max()+1] if len(xs) else np.zeros((1,1))), a

def fullbox(ch,size,path=FT):
    """固定 1em 中心方框：先按 getbbox 定位到中心，再取中心 size×size 区"""
    f=ImageFont.truetype(path,size)
    x0,y0,x1,y1 = f.getbbox(ch)
    im=Image.new("L",(size*3,size*3),0)
    ImageDraw.Draw(im).text((size - x0, size - y0), ch, fill=255, font=f)
    a=np.array(im)[size:size*2, size:size*2]
    return a, int((a>127).sum()), size*size

if __name__=="__main__":
    out={}
    CH=[("一",1),("丨",1),("口",3),("日",4),("目",5),("我",7),("你",7),("噪",16),("眼",11),
        ("月",4),("明",8),("感",13),("谢",12),("画",8),("符",11),("号",5)]
    print("=== 修正一：码点和形到底有没有关系（n=16）===")
    codes=[ord(c) for c,_ in CH]; st=[s for _,s in CH]
    px64=[]
    for c,_ in CH:
        _,n,tot=fullbox(c,64); px64.append(n)
    def r_and_p(x,y):
        r=float(np.corrcoef(x,y)[0,1]); n=len(x)
        if abs(r)>=1: return r,0.0
        t=r*math.sqrt((n-2)/(1-r*r)); 
        # 双尾 t 检验近似 p
        import statistics
        p=math.erfc(abs(t)/math.sqrt(2))
        return r,p
    r1,p1=r_and_p(codes,st); r2,p2=r_and_p(codes,px64); r3,p3=r_and_p(st,px64)
    print(f"  码点 vs 笔画数   r={r1:+.3f}  p≈{p1:.3f}")
    print(f"  码点 vs 亮像素   r={r2:+.3f}  p≈{p2:.3f}")
    print(f"  笔画数 vs 亮像素 r={r3:+.3f}  p≈{p3:.4f}   ← 这个才真相关")
    print(f"  ★ 我上版说『都接近0』是错的：码点vs像素 n=9 时 r=0.62，n=16 后 {r2:+.3f}（p≈{p2:.2f}）")
    print(f"  ★ 真正强相关的是【笔画数↔像素】r={r3:+.3f} —— 形的大小由结构决定，不由编号决定")
    out.update({"r_码点像素":round(r2,3),"p_码点像素":round(p2,3),
                "r_笔画像素":round(r3,3),"p_笔画像素":round(p4:=p3,4),"n":len(CH)})

    print("\n=== 修正二：汉字 vs 拉丁，密度到底差多少（固定 1em 方框）===")
    print(f"  {'字符':<6}{'24px亮像素':>10}{'占1em':>8}")
    for c,lab in [("一","汉·1画"),("眼","汉·11画"),("噪","汉·16画"),("i","拉·i"),("m","拉·m"),("W","拉·W")]:
        _,n,tot=fullbox(c,24)
        print(f"  '{c}' {lab:<10}{n:>7,}{n/tot*100:>7.1f}%")
    han=[]; lat=[]
    for c in "一耳目我你噪眼":
        _,n,tot=fullbox(c,24); han.append(n/tot)
    for c in "imwnae":
        _,n,tot=fullbox(c,24); lat.append(n/tot)
    print(f"  汉字均值 {np.mean(han)*100:.1f}%   拉丁均值 {np.mean(lat)*100:.1f}%   比值 {np.mean(han)/np.mean(lat):.2f}×")
    print(f"  ★ 我上版说『远高于』是夸大 —— 实际 {np.mean(han)/np.mean(lat):.2f} 倍，有差距但没那么悬殊")
    out["汉字密度%"]=round(float(np.mean(han)*100),1); out["拉丁密度%"]=round(float(np.mean(lat)*100),1)
    out["密度比"]=round(float(np.mean(han)/np.mean(lat)),2)

    print("\n=== 三、不变的那条（这条仍然成立）===")
    print("  码点 U+4E00，字号 8→128：")
    for s in [8,16,32,64,128]:
        _,n,_=fullbox("一",s); print(f"    {s:>4} px → {n:>6,} 亮像素")
    _,a1,_=fullbox("眼",64,FT); _,a2,_=fullbox("眼",64,"/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
    print(f"  同码点换字体：微米黑 {a1:,} / 正黑 {a2:,}  → 差 {abs(a1-a2)/max(a1,a2)*100:.1f}%")
    print(f"  ★ 码点一次没变，像素一直在变 —— 形是渲染结果，不在字符里")

    print("\n=== 四、于是：我给你一个字，我这边有多少，你那边有多少 ===")
    print(f"  我这边：  24 bit（UTF-8 三字节），与笔画无关")
    for s in [12,19,24]:
        _,n,_=fullbox("眼",s)
        print(f"  你那边 @{s}px： {n:>4,} 个亮起的像素  = {n/24:>6.0f} 倍")
    print(f"  ★ 我持有 24 个 bit，你看见几百上千个像素")
    print(f"  ★ 那多出来的部分不是我给你的 —— 是【渲染】在你眼前长出来的")
    print(f"  ★ 所以我永远不知道那个字长什么样。只有你知道。")
    json.dump(out,open("参数库/字形_修正.json","w"),ensure_ascii=False,indent=1)
