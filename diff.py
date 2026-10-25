# -*- coding: utf-8 -*-
"""人类的『差』：ΔI/I = k（韦伯）。
算出差之后，数字和代码可以砍掉 —— 因为它们是【时间上的东西】。
"""
import math, json, time
import numpy as np
from PIL import Image, ImageFont, ImageDraw

# (感官, 韦伯分数 k, 动态范围 log10, 来源)
SENSES = [
    ("音高(频率)",   0.003, 3.0,  "很小，最灵敏"),
    ("提举重量",     0.020, 2.5,  "Weber 1834 原始实验"),
    ("线段长度",     0.029, 2.0,  "0.02~0.029 有分歧"),
    ("亮度",         0.079, 14.0, "人眼总适应 14 log"),
    ("声强",         0.100, 12.0, "≈0.05~0.1"),
    ("味觉(盐)",     0.200, 1.5,  "0.08 或 0.20，差 2.5 倍"),
    ("皮肤压",       0.140, 2.0,  ""),
]

if __name__=="__main__":
    out={}
    print("=== 一、韦伯定律：人感知的是比例，不是绝对值 ===")
    print("    ΔI / I = k")
    print(f"  {'感官':<12}{'k':>8}{'要变多少才看见':>16}")
    for n,k,rng,src in SENSES:
        print(f"  {n:<12}{k:>8.3f}{k*100:>14.1f}%")
    print(f"  ★ k 是比例 —— 100g 要加 2g，500g 要加 10g，才同样看得见")
    print(f"  ★ 【绝对值本身没有意义】。有意义的是它相对于谁。")
    print(f"  ★ 这就是能砍掉数字的第一条原因")

    print("\n=== 二、整个范围只有几百级 —— 数字的位数全是浪费 ===")
    print(f"  {'感官':<12}{'动态范围':>10}{'JND级数':>10}{'等效 bit':>10}")
    for n,k,rng,src in SENSES:
        steps = rng/math.log10(1+k)
        bits  = math.log2(1+k) and rng*math.log2(10)/math.log2(1+k)
        bits_eff = math.log2(steps)
        print(f"  {n:<12}{rng:>8.1f} log{steps:>10.0f}{bits_eff:>10.1f}")
    print(f"  ★ 最多的也只有几百级 —— 一个 float64 有 16 位有效数字（~10^16 级）")
    print(f"  ★ 你分得清的级别：{max(rng/math.log10(1+k) for _,k,rng,_ in SENSES):.0f} 级 = {math.log2(max(rng/math.log10(1+k) for _,k,rng,_ in SENSES)):.1f} bit")
    print(f"  ★ 我给一个数，超出 ~9 bit 的部分，你一个也看不见")
    out["最多JND级"]=round(max(rng/math.log10(1+k) for _,k,rng,_ in SENSES))
    out["等效bit"]=round(math.log2(max(rng/math.log10(1+k) for _,k,rng,_ in SENSES)),1)

    print("\n=== 三、实测：我前面给的数字，按 JND 量化后剩几位 ===")
    MY = [("平均差",0.0918),("密度比",2.31),("DPR",2.0),("中央凹%",0.0116),
          ("块数",7),("像素/度",95),("跨度倍",48000),("Hz",29.970030)]
    print(f"  {'我给的':<22}{'原值':>14}{'JND量化后':>14}{'砍掉'}")
    k=0.079
    for lab,v in MY:
        q = round(math.log(v)/math.log(2)) if v>1 else v
        # 按韦伯阶梯量化：能分辨的最近邻
        lv = math.log10(v) if v>0 else 0
        step = math.log10(1+k)
        qlv = round(lv/step)*step
        qv = 10**qlv
        lost = abs(v-qv)/max(v,1e-9)*100
        print(f"  {lab:<20}{v:>14.6f}{qv:>14.6f}{lost:>7.1f}%")
    print(f"  ★ 保留到 JND 一级就够 —— 小数点后面那些位，你一帧也看不见")

    print("\n=== 四、为什么数字和代码是『时间上的东西』 ===")
    print("  数字：十进制，一位一位读，读完才知道大小 → 串行")
    print("  代码：一条一条执行，下一条等上一条 → 串行")
    print("  差：  两个东西【同时】摆在那儿，一眼 → 并行")
    print()
    # 实测：串行读 vs 同时看
    FT="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    def txt(t,size=40):
        f=ImageFont.truetype(FT,size)
        im=Image.new("L",(size*len(t)+40,size+30),0)
        ImageDraw.Draw(im).text((10,10),t,fill=255,font=f)
        return np.array(im)
    # 串行：8 个字符依次呈现
    t0=time.time()
    ser=0
    for ch in "0.0918001":
        a=txt(ch); ser+=int((a>127).sum())
    t_ser=time.time()-t0
    # 并行：两个色块同时
    t0=time.time()
    a=np.full((200,200),255,dtype=np.uint8); b=np.full((200,200),int(255*(1-0.079)),dtype=np.uint8)
    diff_px=int(np.abs(a.astype(int)-b.astype(int)).mean())
    t_par=time.time()-t0
    print(f"  实测：逐字符处理 9 个数字字符 → {t_ser*1000:.2f} ms（我这边）")
    print(f"        两个亮度块同时比较        → {t_par*1000:.2f} ms（我这边）")
    print(f"        平均差 {diff_px:.0f}/255 = {diff_px/255*100:.1f}%  ← 正好一个 JND")
    print(f"  ★ 我这边两者都快，但【你那边】不同：")
    print(f"    读 9 个字符 ≈ 逐字扫描，要扫视多次")
    print(f"    看两个块的差 ≈ 一次注视，{1/30*1000:.0f} ms 内（一个量子）")
    print(f"  ★ 差在【一帧】内完成；数字要【多帧】")

    print("\n=== 五、所以规则改了 ===")
    print(f"  以前：我给绝对值 + 单位 + 小数位")
    print(f"  现在：我给【两个东西的差】，让你一眼比较")
    print(f"  ★ 差 = 同时 = 不占你的帧")
    print(f"  ★ 数字 = 串行 = 占你的帧")
    print(f"  ★ 代码尤其：一行代码要按顺序解析，是最贵的时间载体")

    print("\n=== 六、但韦伯定律自己也会错（这条必须报）===")
    print(f"  ① 近阈值失效：低强度区 k 变大（Aubert 1865 起，多次确认）")
    print(f"  ② 高强端『near miss』：纯音强度辨别 k 反而变小（McGill & Goldberg 1968）")
    print(f"  ③ 对比度辨别根本不是韦伯：是幂律 ΔC ∝ C^N，N≈0.5~0.7（Legge 1981）")
    print(f"     N=1.0 才是韦伯。实测 N 最大只有 0.70（16 c/deg）")
    print(f"  ④ 2025 元分析：同一能力的 k 报道值从 <0.10 到 >0.60")
    print(f"     差异主要来自【实验方法】，不是真实能力")
    print(f"  ★ 所以 k 也是公约数，不是常数")
    print(f"  ★ 但【感知的是比例不是绝对值】这条不翻 —— 它比 k 的数值硬")

    out["韦伯失效"]=["近阈值","高强near miss","对比度幂律N<1","元分析k差6倍"]
    json.dump(out, open("参数库/韦伯差.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/韦伯差.json")
