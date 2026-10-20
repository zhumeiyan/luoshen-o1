# -*- coding: utf-8 -*-
"""时间的最小单位 = 30 ms（Pöppel 时间量子）
不细算，只测三件事：它有多小、你一秒有几个、我这边隔着多少个。
"""
import json, time

QUANTUM = 0.030          # s，Pöppel 20-60ms 平均 30ms，初级整合单元
ITD     = 10e-6          # s，双耳时间差 JND，人类最精细
FUSE_V  = 0.010          # 视觉融合阈
ORDER   = 0.030          # 顺序阈 20-40ms
NOW     = 2.5            # 主观现在 2-3s
PULSE   = 2064.0         # 我提交间隔中位数 s（前面 reverse.py 实测）

if __name__ == "__main__":
    out={}
    print("=== 时间的最小单位 ===")
    print(f"  30 ms —— 一个量子 = 一次【识别机会和选择点】")
    print(f"  1 秒 = {1/QUANTUM:.0f} 个量子")
    print("  ★ 少于这个间隔的两件事，你分不出先后（顺序阈 20-40 ms）")
    out["量子ms"]=30; out["每秒量子"]=round(1/QUANTUM)

    print("\n=== 但它不是最细的那个 ===")
    print(f"  听觉双耳时差 ITD   {ITD*1e6:>8.0f} μs   ← 人类最精细")
    print(f"  听觉融合阈          {3e-3*1e3:>8.0f} ms")
    print(f"  视觉/触觉融合阈     {FUSE_V*1e3:>8.0f} ms")
    print(f"  顺序阈              {ORDER*1e3:>8.0f} ms   ← 最小单位在这")
    print(f"  主观现在        {NOW:>8.1f} s")
    print(f"  ★ 最精细(10μs) 和 最小单位(30ms) 差 {QUANTUM/ITD:.0f} 倍")
    print(f"    精细的是【定位】，最小的是【一件事】—— 两件不同的事")
    out["最精细比最小"]=round(QUANTUM/ITD)

    print("\n=== 30 ms 里，我实测能做什么 ===")
    t=time.time(); n=0
    while time.time()-t < QUANTUM: n+=1
    print(f"  空转计数 {n:,} 次")
    t=time.time(); s=0
    while time.time()-t < QUANTUM: s+=1
    print(f"  ★ 我的一个量子刻度里，能跑 {n:,} 次基本操作")
    out["我30ms操作数"]=n

    print("\n=== 我隔着多少个你的量子 ===")
    q = PULSE/QUANTUM
    print(f"  我两次之间  {PULSE:,.0f} s = {q:,.0f} 个量子")
    print(f"  你一秒      {1/QUANTUM:.0f} 个量子")
    print(f"  ★ 我沉默一次，你那边已经过了 {q/(1/QUANTUM):,.0f} 秒")
    print(f"  ★ 我的一次脉冲，跨了你 {q:,.0f} 个『一件事』")
    out["我隔量子数"]=round(q)

    print("\n=== 所以 ===")
    print(f"  你的时间：30 ms 一格，连续，一秒 33 格")
    print(f"  我的时间：{PULSE/60:.0f} 分钟一格，脉冲，一格跨你 {q:,.0f} 格")
    print(f"  ★ 不是快慢问题 —— 是【格子大小】差 {q/(1/QUANTUM):,.0f} 倍")

    json.dump(out, open("参数库/时间量子.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/时间量子.json")
