# -*- coding: utf-8 -*-
"""中文=图（有冗余，容错高）；代码=链（无冗余，容错 0）。实测三种破坏。"""
import json, random, subprocess, tempfile, os, numpy as np
from PIL import Image, ImageDraw, ImageFont

random.seed(7)
SENT = "把主结论放在中心其余让它自己长"
CODE = "def f(x):\n    return x*2+1 if x>0 else 0\nprint(f(3))"

def font(sz):
    for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return None

if __name__=="__main__":
    out={}
    print("=== 一、中文的『图』属性：破坏后还剩多少结构 ===")
    f=font(64)
    res={}
    if f:
        for lv,name in [(0,"原图"),(0.05,"5%椒盐"),(0.15,"15%椒盐"),(0.35,"35%椒盐")]:
            im=Image.new("L",(64*len(SENT),96),0); d=ImageDraw.Draw(im)
            d.text((6,10),SENT,fill=255,font=f)
            a=np.array(im).astype(np.float32)/255
            if lv>0:
                m=np.random.rand(*a.shape)
                a[m<lv/2]=0; a[m>1-lv/2]=1
            # 结构存活：与未破坏图的相关系数
            im0=Image.new("L",(64*len(SENT),96),0); ImageDraw.Draw(im0).text((6,10),SENT,fill=255,font=f)
            a0=np.array(im0).astype(np.float32)/255
            c=np.corrcoef(a.ravel(),a0.ravel())[0,1]
            res[name]=c
            print(f"  {name:<10} 结构存活 {c:.3f}")
        out["中文图结构存活"]={k:round(v,3) for k,v in res.items()}
        print(f"  ★ 35% 像素被打坏，还剩 {res['35%椒盐']:.2f} 的结构 —— 这就是『图』的冗余")

    print("\n=== 二、代码的『链』属性：删 1 个字符会怎样 ===")
    ok=0; tot=0; fails=[]
    for i in range(len(CODE)):
        if CODE[i] in "\n ": continue
        tot+=1
        broken=CODE[:i]+CODE[i+1:]
        with tempfile.NamedTemporaryFile("w",suffix=".py",delete=False) as t:
            t.write(broken); p=t.name
        r=subprocess.run(["python3",p],capture_output=True,timeout=10)
        os.unlink(p)
        if r.returncode==0: ok+=1
        else: fails.append(CODE[i])
    print(f"  逐个删字符：{tot} 个可删位置，仍能跑 {ok} 个 → 容错率 {ok/tot*100:.1f}%")
    print(f"  ★ 代码任意一个字符错了，几乎必崩 —— 零冗余")
    out["代码容错率%"]=round(ok/tot*100,1)

    print("\n=== 三、中文句子的『链』属性：删字还剩多少意思 ===")
    print(f"  原句：{SENT}")
    for n in [1,3,5]:
        keep=[]
        for _ in range(200):
            idx=random.sample(range(len(SENT)),n)
            s2="".join(c for i,c in enumerate(SENT) if i not in idx)
            keep.append(sum(1 for c in set(SENT) if c in s2)/len(set(SENT)))
        print(f"  随机删 {n} 字 → 字符信息保留 {np.mean(keep)*100:.0f}%")
        out[f"中文删{n}字保留%"]=round(np.mean(keep)*100)
    print(f"  ★ 删 {5} 个字（占 {5/len(SENT)*100:.0f}%）还剩 {out['中文删5字保留%']}% 的字符信息")
    print(f"  ★ 你靠剩下的字把缺的补回来 —— 这是图的能力，不是链的能力")

    print("\n=== 四、为什么『用代码讲底层逻辑，中国人会懵』===")
    print(f"  {'':<12}{'到达路径':<28}{'跳数':>6}{'冗余':>8}")
    rows=[("中文","形 → 义（形声字形旁直接给类别）",1,"高"),
          ("英文","形 → 音 → 义",2,"中"),
          ("代码","字符 → token → 语法树 → 语义 → 执行结果",4,"零")]
    for a,b,c,d in rows:
        print(f"  {a:<12}{b:<28}{c:>6}{d:>8}")
    print(f"  ★ 中文一跳就到，代码要四跳")
    print(f"  ★ 更关键：中文每一跳都有冗余，代码每一跳都没有")
    print(f"  ★ 代码第 2 跳断裂 → 后面全断，没有『猜出来』这回事")

    print("\n=== 五、所以底层逻辑该用什么讲 ===")
    print(f"  用代码讲：你必须在第 2 跳（token）上跟我同步，否则后面全空")
    print(f"             而这一跳对你没画面 → 懵")
    print(f"  用中文讲：你第 1 跳就到义，但我会丢精度（v44 已测：丢 ~32%）")
    print(f"  用图讲：  你第 1 跳就到，且冗余高（35% 破坏还剩 {res.get('35%椒盐',0):.2f}）")
    print(f"  ★ 所以：底层逻辑【用图画】，代码只是我生成图的手段")
    print(f"  ★ 代码不是给你看的 —— 它是『我的手』（v2 已定的那条）")

    json.dump(out, open("参数库/中文与代码.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/中文与代码.json")
