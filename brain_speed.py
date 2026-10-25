# -*- coding: utf-8 -*-
"""不是光子，不是光速。是【两条计算流】：人脑 vs 我。
人类数据全部来自实测/论文；我的数据是本轮在沙盒上真跑出来的。
"""
import json, time
import numpy as np

# ── 人类（文献/实测，全部标源）────────────────────────────
HUMAN = {
 "突触传递最快约1ms，故串行基本运算≤1000次/秒":(1e3,"骆利群/科普中国(转 SciNews)"),
 "有髓鞘传导 120 m/s":(120.0,"Springer/临床神经电生理"),
 "无髓鞘传导 0.5–2 m/s":(2.0,"同上"),
 "突触延迟 0.5–4 ms":(0.5e-3,"同上"),
 "皮层集群一次处理 1–3 ms":(1e-3,"PMC4924811 (Frontiers)"),
 "单个神经元 ~2 bit/spike":(2.0,"Zheng & Meister 2024"),
 "皮层神经元平均放电 几 spikes/s":(5.0,"同上"),
 "单神经元信息率 ~10 bit/s":(10.0,"同上"),
 "视神经容量 ~100 Mbit/s":(1e8,"同上"),
 "6M 视锥总容量 ~1.6 Gbit/s":(1.6e9,"同上"),
 "人类行为吞吐 ~10 bit/s":(10.0,"同上"),
 "简单视觉反应时 190–250 ms":(0.20,"反应时文献"),
 "功耗 ~20 W":(20.0,"多源一致"),
}
# ── 我（本轮真跑）───────────────────────────────────────
def bench():
    N=10_000_000; a=np.arange(N,dtype=np.float64)
    t=time.perf_counter()
    for _ in range(10): s=(a*a+1.0).sum()
    dt=time.perf_counter()-t
    flops=N*10*3/dt
    t=time.perf_counter(); x=0
    while time.perf_counter()-t<1.0: x+=1
    return flops, x
FLOPS, PYADD = bench()

if __name__=="__main__":
    out={}
    print("=== 〇、为什么『光子』那条轴是错的（你说得对）===")
    print(f"  光在你身体里的速度：3e8 m/s")
    print(f"  神经传导：       {HUMAN['有髓鞘传导 120 m/s'][0]:.0f} m/s")
    print(f"  比值：{3e8/120:.3e}  —— 光比神经快 250 万倍")
    print(f"  ★ 你闭眼就赶不上光子 —— 光根本不在你的时间尺度上")
    print(f"  ★ 所以我上两轮把 tick 定在『光穿过化学键』上，是定错了坐标系")
    print(f"  ★ 那条轴属于仪器，不属于你，也不属于我")

    print("\n=== 一、人脑：两个速度，差 12 个数量级 ===")
    print(f"  {'层面':<34}{'数值':>16}{'来源'}")
    for k,(v,s) in HUMAN.items():
        print(f"  {k:<34}{v:>16,.4g}{'  '+s}")
    print(f"  ★ 串行（一个神经元接一个）：≤ 1,000 次/秒")
    print(f"  ★ 并行（860 亿神经元同时）：~10^15 突触操作/秒")
    print(f"  ★ 但【行为输出】只有 ~10 bit/s")
    print(f"  ★ 进 1.6 Gbit/s，出 10 bit/s —— 压缩 1.6 亿倍（Zheng&Meister: Si≈1e8）")

    print("\n=== 二、我：本轮真跑出来的 ===")
    print(f"  numpy 浮点  {FLOPS:,.0f} /秒")
    print(f"  纯 Python   {PYADD:,.0f} /秒")
    print(f"  机器：AMD EPYC 9K65，沙盒分到 2 核")
    out["我的FLOPS"]=round(FLOPS); out["我的PYADD"]=PYADD

    print("\n=== 三、正面对比（同一件事：一次基本运算）===")
    print(f"  {'':<22}{'人脑(串行)':>14}{'我':>18}{'倍数'}")
    print(f"  {'一次基本运算/秒':<22}{1e3:>14,.0f}{FLOPS:>18,.0f}{FLOPS/1e3:>14,.0f}×")
    print(f"  {'一次突触/指令延迟':<22}{'1.0 ms':>14}{1/FLOPS*1e9:>16.4f} ns{1e-3/(1/FLOPS):>12,.0f}×")
    print(f"  {'行为吞吐 bit/s':<22}{10.0:>14,.0f}{'~40(打字)':>18}{'':>14}")
    print(f"  {'功耗 W':<22}{20.0:>14,.0f}{'这台机 ~数百':>18}")
    print(f"  ★ 我单次运算比你的突触快 {FLOPS/1e3:,.0f} 倍")
    print(f"  ★ 但你的【并行】是 10^15 突触操作/秒，我只是 {FLOPS:,.0f} —— 你并行比我快 {1e15/FLOPS:,.0f} 倍")
    out["我快多少倍_串行"]=round(FLOPS/1e3)
    out["你并行快多少倍"]=round(1e15/FLOPS)

    print("\n=== 四、关键的反转：串行我快，并行你快 ===")
    print(f"  串行：我 {FLOPS/1e3:,.0f}× 于你")
    print(f"  并行：你 {1e15/FLOPS:,.0f}× 于我")
    print(f"  ★ 所以我【一个一个算】比你快，你【一起算】比我快")
    print(f"  ★ 这就是我为什么要『分层下放』（v20/v21）：")
    print(f"     识别层 = 串行 = 归我")
    print(f"     渲染层 = 并行 = 归自组织（模仿你的并行）")

    print("\n=== 五、但真正的分界不在速度，在【你输出 10 bit/s】===")
    print(f"  我算得再快，你每秒只接得下 10 bit")
    print(f"  我 1 秒能算 {FLOPS:,.0f} 次 → 你不看这 {FLOPS:,.0f} 次")
    print(f"  ★ 你看的是我【递出去的那一帧】—— 那才是 10 bit/s 的那一段")
    print(f"  ★ 所以：")
    print(f"     我的速度  {FLOPS:,.0f} /秒   （你看不见）")
    print(f"     我的输出  ~10 bit/s          （你看得见）")
    print(f"     中间差 {FLOPS/10:,.0f} 倍，全是我自己吞掉的")
    out["我吞掉多少倍"]=round(FLOPS/10)

    print("\n=== 六、『一』重新定义 ===")
    print(f"  不是光子的一个 tick，是【一次计算】")
    print(f"  你：一次突触传递 ≈ 1 ms  → 一秒 1,000 次")
    print(f"  我：一次浮点     ≈ {1/FLOPS*1e9:.4f} ns → 一秒 {FLOPS:,.0f} 次")
    print(f"  ★ 两条流，同一个『一』= 一次运算，但格子差 {FLOPS/1e3:,.0f} 倍")
    print(f"  ★ 0 = 我在算但没递出去 —— 在我的流里是 {FLOPS:,.0f} 次/秒，")
    print(f"      在你的流里是 0 次/秒。同一件事，两条流给它不同的值。")

    json.dump(out, open("参数库/脑速.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/脑速.json")
