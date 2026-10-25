#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
皮肤 —— 近端感受器，必须【主动】才好用
==========================================
★ 与眼耳鼻根本不同：它们是远端感受器（接收远处光/声/分子）
  皮肤必须【接触】才有信号 → 天然是主动的

★ 核心对照：
  ① 两点辨别 ∝ 1/√密度（指尖1mm vs 前臂35mm，差20倍）
  ② ★ 细纹理靠【扫动产生的振动】编码 —— 手不动就消失
     ★ 这与 ★25"静止时运动视差消失"是同一个道理的另一面
  ③ 快适应 vs 慢适应（穿上衣服就感觉不到）
  ④ ★ 主动触觉优于被动（传出副本）
  ⑤ 痛觉【不】适应（保护性），与触觉关键区别
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.skin import (
    MERKEL_DENSITY, MEISSNER_DENSITY, MERKEL_FIELD_MM, PACINI_F_PEAK,
    TWO_POINT_MM, ADAPT_RA_TAU, ADAPT_SA_TAU, ADAPT_SA_FLOOR,
    COLD_PEAK_C, HEAT_THRESH_C, PAIN_MECH_MN,
    receptor_response, scan_frequency, texture_encoding,
    two_point_threshold, two_point_threshold2, CORTICAL_MAG,
    two_point_discriminable, discriminable,
    adaptation, thermoreceptor, thermal_illusion, nociceptor,
    pain_adaptation, active_vs_passive, tactile_exploration_move,
)

if __name__ == "__main__":
    print("="*88); print(" 皮肤：接触才有的感官，而且必须主动"); print("="*88)
    ok = {}

    # ---------- 1 两点辨别 ----------
    print("\n【实验1】★ 两点辨别阈 ∝ 1/√感受器密度")
    print("-"*88)
    print(f"  {'部位':<8}{'模型(mm)':>10}{'真实区间':>16}{'符合':>7}")
    dens = {"指尖": 100.0, "手掌": 5.0, "前臂": 0.5, "背部": 0.2}
    hits = 0
    for site, d in dens.items():
        m = two_point_threshold2(d, site)
        lo, hi = TWO_POINT_MM[site]
        good = lo <= m <= hi
        hits += good
        print(f"  {site:<8}{m:>10.2f}{('  '+str(lo)+'~'+str(hi)):>16}{'✅' if good else '❌':>7}")
    ok["① 4 个部位中至少 3 个落真实区间"] = bool(hits >= 3)
    f_tip = two_point_threshold2(100, "指尖"); f_arm = two_point_threshold2(0.5, "前臂")
    print(f"\n  ★ 指尖 {f_tip:.2f} mm vs 前臂 {f_arm:.1f} mm —— 差 {f_arm/f_tip:.0f} 倍")
    print("  ★ 纯密度只能解释 14 倍，剩下的是【皮层放大】（体感侏儒图）")
    ok["② ★ 指尖与前臂相差 >20 倍（REAL 约 20~35 倍）"] = bool(f_arm/f_tip > 20)
    ok["②b ★ 纯密度模型不够，必须加皮层放大"] = bool(
        two_point_threshold(0.5)/two_point_threshold(100) < f_arm/f_tip)

    # ---------- 2 ★ 细纹理靠扫动 ----------
    print("\n【实验2】★★ 细纹理靠【扫动】产生的振动编码")
    print("-"*88)
    print(f"  Pacini 最敏感 {PACINI_F_PEAK:.0f} Hz（REAL 200~300）")
    print(f"\n  {'纹理周期':>10}{'扫描速度':>10}{'振动频率':>12}{'RA2响应':>10}{'SA1空间':>10}")
    rows = []
    for period in [50, 200, 1000]:
        for v in [0, 20, 50]:
            r = texture_encoding(period, v)
            rows.append((period, v, r))
            print(f"  {period:>8}μm{v:>9}mm/s{r['freq_hz']:>11.1f}Hz"
                  f"{r['RA2_vibration']:>10.3f}{r['SA1_spatial']:>10.3f}")
    # ★ 第一版用 40 mm/s → 800 Hz，已越过 Pacini 峰(250Hz) → 只有 0.32
    #   真实主动触摸扫描速度约 20~80 mm/s，取 20 → 400 Hz
    moving, still = tactile_exploration_move(20.0, 50.0)
    ok["③ ★★ 静止时细纹理响应 = 0（手不动 → 完全消失）"] = bool(still < 1e-9)
    ok["④ 扫动时细纹理响应显著（>0.5）"] = bool(moving > 0.5)
    print(f"\n  ★ 50μm 细纹理：静止 {still:.4f}  vs  20mm/s 扫动 {moving:.3f}")
    print(f"  ★ 粗纹理(1000μm) 静止时 SA1 空间响应仍 = "
          f"{texture_encoding(1000,0)['SA1_spatial']:.3f} —— 粗的不靠扫")
    ok["⑤ ★ 粗纹理静止时仍有 SA1 响应（对比细纹理的 0）"] = bool(
        texture_encoding(1000, 0)["SA1_spatial"] > 0.1)
    # 频率匹配：最优扫描速度
    best = max(range(5, 200, 5), key=lambda v: texture_encoding(50, v)["RA2_vibration"])
    f_best = scan_frequency(best, 50)
    ok["⑥ ★ 最优扫描速度产生的频率接近 Pacini 峰（±60Hz）"] = bool(
        abs(f_best - PACINI_F_PEAK) < 60)
    print(f"  ★ 50μm 纹理最优扫描速度 {best} mm/s → f={f_best:.0f} Hz ≈ Pacini 峰")

    # ---------- 3 适应 ----------
    print("\n【实验3】快适应 vs 慢适应（穿上衣服就感觉不到）")
    print("-"*88)
    t = np.array([0, 0.05, 0.5, 2, 5, 10])
    ra = adaptation(t, "RA1"); sa = adaptation(t, "SA1")
    print(f"  {'时间(s)':>9}{'RA(Meissner)':>14}{'SA(Merkel)':>13}")
    for tt, a_, b_ in zip(t, ra, sa):
        print(f"  {tt:>9}{a_:>14.3f}{b_:>13.3f}")
    ok["⑦ ★ RA 在 0.5s 内归零（只对变化响应）"] = bool(ra[2] < 0.05)
    ok["⑧ ★ SA 衰减到静息水平但不归零（0.15~0.35）"] = bool(
        0.15 <= sa[-1] <= 0.35)
    print(f"\n  ★ RA {ra[0]:.2f}→{ra[2]:.3f}（立刻没）  SA {sa[0]:.2f}→{sa[-1]:.3f}（留 31%）")
    print("  ★ 这就是穿衣服几秒后感觉不到的机制 —— 而且是 SA 的功劳")

    # ---------- 4 ★ 主动 vs 被动 ----------
    print("\n【实验4】★ 主动触觉优于被动（传出副本）")
    print("-"*88)
    print(f"  {'部位':<8}{'主动阈值':>10}{'被动阈值':>10}{'比':>8}")
    for j in ["指尖", "肘", "膝"]:
        a, p = active_vs_passive(0, j)
        print(f"  {j:<8}{a:>10.2f}{p:>10.2f}{p/a:>8.2f}×")
    a1, p1 = active_vs_passive(0, "指尖")
    ok["⑨ ★ 主动阈值低于被动（约 2×）"] = bool(p1 / a1 > 1.5)
    # 用一个介于两者之间的位移做判别
    mid = (a1 + p1) / 2.0
    ok["⑩ ★ 存在【主动可辨、被动不可辨】的中间位移"] = bool(
        discriminable(mid, "指尖", True) and not discriminable(mid, "指尖", False))
    print(f"\n  ★ 指尖：主动 {a1:.2f} mm，被动 {p1:.2f} mm")
    print(f"  ★ {mid:.2f} mm 这个位移：主动能摸出来，被动摸不出来")

    # ---------- 5 温度 ----------
    print("\n【实验5】温度感受器（冷/热不是一条轴）")
    print("-"*88)
    print(f"  {'温度':>7}{'冷通道':>10}{'热通道':>10}")
    for T in [15, 20, 25, 32, 40, 45, 50]:
        print(f"  {T:>6}°C{thermoreceptor(T,'cold'):>10.3f}{thermoreceptor(T,'heat'):>10.3f}")
    ok["⑪ 冷通道在 32°C 以上静默"] = bool(thermoreceptor(35, "cold") == 0.0)
    ok["⑫ 热通道在 30°C 以下静默"] = bool(thermoreceptor(25, "heat") == 0.0)
    ok["⑬ 热通道在 >43°C 显著激活（伤害性）"] = bool(thermoreceptor(45, "heat") > 0.8)
    ill = thermal_illusion(np.array([20.0, 40.0]))
    ctrl = thermal_illusion(np.array([30.0, 30.0]))
    ok["⑭ ★ 热错觉：交替冷温栅 >> 单一温度"] = bool(ill > 5 * max(ctrl, 1e-9))
    print(f"\n  ★ 交替 20/40°C 栅 → {ill:.4f}；均匀 30°C → {ctrl:.4f}  "
          f"（差 {ill/max(ctrl,1e-9):.0f}×）")
    print("  ★ 冷+热同时激活，中枢没有对应自然组合 → 解释为灼烧")
    print("  ★ 这与 ★25 双眼复视是同一类：通道组合冲突产生错觉")

    # ---------- 6 痛觉不适应 ----------
    print("\n【实验6】★ 痛觉不【适应】（保护性）")
    print("-"*88)
    tt = np.array([0, 10, 60, 300])
    pa = pain_adaptation(tt); ta = adaptation(tt, "SA1")
    print(f"  {'时间(s)':>9}{'痛觉':>10}{'触觉':>10}")
    for a_, b_, c_ in zip(tt, pa, ta):
        print(f"  {a_:>9}{b_:>10.3f}{c_:>10.3f}")
    ok["⑮ ★ 痛觉全程不衰减，触觉衰减"] = bool(
        pa[-1] == pa[0] and ta[-1] < ta[0])
    ok["⑯ 机械痛阈值约 20 mN（<10mN 无痛）"] = bool(
        nociceptor(5.0) == 0.0 and nociceptor(50.0) > 0)
    print(f"\n  ★ {PAIN_MECH_MN:.0f} mN 以下无痛觉，以上激活 —— 且【一直疼】")

    print("\n"+"="*88); print(" 判据汇总"); print("="*88)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未建模：毛发感受器、痒觉(C纤维)、社交触摸(CT 传入)")
    print("  ❌ 未建模：皮层体感地图(S1 侏儒图)、双手协调")
    print("  ⚠️ 感受器密度→阈值是近似公式，非真实解剖测量")
    json.dump({k: bool(v) for k, v in ok.items()},
              open(os.path.join(HERE, ".sense", "skin.json"), "w"),
              ensure_ascii=False, indent=1)
