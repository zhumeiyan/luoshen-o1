#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电子鼻 == 嗅觉是【高维且没有坐标轴】的
========================================
用户：「鼻子按电子鼻也行。」

★ 与视觉/听觉的根本不同（本层要证明）：
    视觉 3 个感受器 → 3 维，有坐标轴
    听觉 基底膜     → 1 维频率轴
    ★ 嗅觉 ~400 受体 → 400 维，【没有自然相邻关系】，靠组合编码

★ 四组对照（每组都有"测别的"的那个量）：
  ① 交叉敏感：单个不选择 vs 阵列选择（★ 交叉敏感是设计不是缺陷）
  ② 维数扫描：可分性随维数升并饱和
  ③ 漂移 vs 再生：电子鼻漂，生物鼻靠受体再生重置
  ④ 混合物：线性相加 vs 竞争结合（REAL 抑制）
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.electronic_nose import (
    OR_GENES_FUNC, OR_TOTAL, OSN_COUNT, GLOMERULI, EPITHELIUM_CM2,
    REGENERATE_DAYS, MOS_TEMP_C, T90_RESP_S, T90_RECOV_S,
    DRIFT_PCT_DAY, DRIFT_PCT_MONTH, LOD_PPB, RH_SENS, TEMP_SENS,
    make_receptor_matrix, receptor_response, receptor_K, make_dataset,
    normalize_response, separability, single_vs_array, dim_sweep,
    apply_drift, biological_renewal, drift_curve,
    env_effect, env_compensate, olfactory_adaptation, sensor_saturation,
    recovery, competitive_binding, mixture_suppression,
)

if __name__ == "__main__":
    print("="*88)
    print(" 电子鼻：交叉敏感 → 阵列 → 漂移 → 竞争结合")
    print("="*88)
    print(f"\n  生物鼻 REAL：受体 {OR_GENES_FUNC} 种（总 {OR_TOTAL}，约一半假基因）")
    print(f"               嗅神经元 {OSN_COUNT/1e6:.0f} 百万   肾小球 {GLOMERULI}")
    print(f"               嗅上皮 {EPITHELIUM_CM2} cm²   再生周期 {REGENERATE_DAYS:.0f} 天")
    print(f"  电子鼻 REAL：MOS {MOS_TEMP_C:.0f}°C   响应 t90 {T90_RESP_S:.0f}s   "
          f"恢复 {T90_RECOV_S:.0f}s")
    print(f"               漂移 {DRIFT_PCT_DAY}%/天（{DRIFT_PCT_MONTH}%/月）   "
          f"检出限 {LOD_PPB:.0f} ppb")
    ok = {}
    rng0 = np.random.default_rng(0)
    N_ODOR = 20
    M = make_receptor_matrix(N_ODOR, 16, rng=rng0)
    chance = 1.0 / N_ODOR

    # ---------- 实验1：交叉敏感 ----------
    print("\n【实验1】★ 交叉敏感不是缺陷，是【设计】")
    print("-"*88)
    a1, aa = single_vs_array(M, seed=1)
    b1, ba = single_vs_array(M, seed=1, norm=False)
    print(f"  {'':<18}{'单传感器':>12}{'整列阵列':>12}{'提升':>10}")
    print(f"  {'做浓度归一化':<18}{a1:>12.3f}{aa:>12.3f}{aa/max(a1,1e-9):>9.1f}×")
    print(f"  {'不做归一化(对照)':<18}{b1:>12.3f}{ba:>12.3f}{ba/max(b1,1e-9):>9.1f}×")
    print(f"\n  随机水平 = 1/{N_ODOR} = {chance:.3f}")
    print(f"  ★ 单个传感器 {a1:.3f}，只比随机高一点点 —— 它【不选择】")
    print(f"  ★ 整列阵列 {aa:.3f} —— 组合起来才选择")
    ok["① ★ 整列阵列显著优于单传感器（>3×）"] = bool(aa > 3*a1)
    ok["② 单传感器识别率接近随机（<3×随机）"] = bool(a1 < 3*chance)
    ok["③ 阵列识别率远超随机（>8×随机）"] = bool(aa > 8*chance)

    # ---------- 实验2：维数扫描 ----------
    print("\n【实验2】维数决定可分性（★ 并会饱和）")
    print("-"*88)
    print(f"  {'维数':>7}{'20类识别率':>14}{'100类识别率':>14}")
    d20 = dict(dim_sweep(n_odor=20, dims=(1,2,4,8,16,32,64,128,400), seed=2))
    d100 = dict(dim_sweep(n_odor=100, dims=(1,2,4,8,16,32,64,128,400), seed=5))
    for d in (1,2,4,8,16,32,64,128,400):
        print(f"  {d:>7}{d20[d]:>14.3f}{d100[d]:>14.3f}")
    ok["④ 可分性随维数单调上升（20类，1→16维）"] = bool(
        d20[16] > d20[4] > d20[1])
    ok["⑤ ★ 高维饱和：400维不再优于128维（±0.02）"] = bool(
        abs(d20[400]-d20[128]) < 0.02)
    ok["⑥ ★ 类数越多越难：100类在同样维数下识别率更低"] = bool(
        d100[16] < d20[16])
    print(f"\n  ★ 16 维时：20类 {d20[16]:.3f}  vs  100类 {d100[16]:.3f}")
    print(f"  ★ 嗅觉要 {OR_GENES_FUNC} 维，正因为要分辨的气味种类极多")

    # ---------- 实验3：漂移 vs 再生 ----------
    print("\n【实验3】★ 漂移（电子鼻致命伤） vs 再生（生物鼻的解法）")
    print("-"*88)
    print(f"  {'天数':>7}{'电子鼻':>10}{'生物鼻':>10}{'已再生受体':>12}")
    dc = drift_curve(M, seed=3)
    for d, ae, ab, fr in dc:
        print(f"  {d:>7}{ae:>10.3f}{ab:>10.3f}{fr:>12.2f}")
    acc_e0 = dc[0][1]; acc_e365 = dc[-1][1]
    ok["⑦ ★ 电子鼻识别率随天数下降"] = bool(acc_e365 < acc_e0)
    ok["⑧ 生物鼻因受体再生而不崩（365天仍>0.8）"] = bool(dc[-1][2] > 0.8)
    ok["⑨ ★ 365 天时生物鼻优于电子鼻"] = bool(dc[-1][2] > dc[-1][1])
    print(f"\n  365天：电子鼻 {dc[-1][1]:.3f}  生物鼻 {dc[-1][2]:.3f}")
    print("  ★ 生物鼻的解法不是更稳的传感器，而是【定期换掉传感器】——45天换一批")

    # ---------- 实验4：混合物竞争 ----------
    print("\n【实验4】★ 混合物抑制：A+B ≠ A+B（竞争结合）")
    print("-"*88)
    K = receptor_K(16, np.random.default_rng(7))
    rA, rB, lin, comp = competitive_binding(M[0], M[1], 1.0, 1.0, K)
    ratio = comp.sum() / lin.sum()
    print(f"  线性相加 Σ     = {lin.sum():.4f}")
    print(f"  竞争结合 Σ     = {comp.sum():.4f}")
    print(f"  ★ 抑制比       = {ratio:.3f}  （REAL 混合物抑制 0.5~0.9）")
    ok["⑩ ★ 混合物响应低于线性相加（比值<1）"] = bool(ratio < 1.0)
    ok["⑪ 抑制强度落 REAL 区间 0.5~0.95"] = bool(0.5 <= ratio <= 0.95)
    # 浓度扫描：浓度越高抑制越强
    print(f"\n  {'浓度':>8}{'抑制比':>10}")
    for c in [0.1, 0.5, 1.0, 5.0, 20.0]:
        _, _, l2, c2 = competitive_binding(M[0], M[1], c, c, K)
        print(f"  {c:>8.1f}{c2.sum()/l2.sum():>10.3f}")
    lo = competitive_binding(M[0],M[1],0.1,0.1,K)[3].sum()/competitive_binding(M[0],M[1],0.1,0.1,K)[2].sum()
    hi = competitive_binding(M[0],M[1],20.,20.,K)[3].sum()/competitive_binding(M[0],M[1],20.,20.,K)[2].sum()
    ok["⑫ ★ 浓度越高抑制越强（受体饱和）"] = bool(hi < lo)

    # ---------- 实验5：适应 vs 饱和 ----------
    print("\n【实验5】★ 生物【适应】 vs 电子鼻【饱和】（关键区别）")
    print("-"*88)
    t = np.array([0, 5, 10, 30, 60, 120, 300])
    ad = olfactory_adaptation(t); sa = sensor_saturation(t)
    print(f"  {'时间(s)':>9}{'生物适应':>12}{'电子鼻响应':>12}")
    for tt, a_, s_ in zip(t, ad, sa):
        print(f"  {tt:>9}{a_:>12.3f}{s_:>12.3f}")
    ok["⑬ ★ 生物响应会【衰减】（适应），电子鼻只升不降（饱和）"] = bool(
        ad[-1] < ad[0] and sa[-1] > sa[0])
    print(f"\n  ★ 生物：{ad[0]:.3f} → {ad[-1]:.3f}（衰减到 {ad[-1]:.0%}）")
    print(f"  ★ 电子鼻：{sa[0]:.3f} → {sa[-1]:.3f}（只升不降）")
    print(f"  ★ 生物适应到 {ad[-1]:.0%} 就【不再下降】（不会完全归零）")

    # ---------- 实验6：温湿度 ----------
    print("\n【实验6】温湿度依赖与补偿")
    print("-"*88)
    R, labels, _ = make_dataset(M, 30, np.random.default_rng(9))
    Rn = normalize_response(R)
    base_acc = separability(Rn, labels, np.random.default_rng(9))
    rows = []
    print(f"  {'RH':>6}{'温度':>7}{'未补偿':>10}{'已补偿':>10}")
    for rh, tc in [(0.5,25.0),(0.8,25.0),(0.2,25.0),(0.5,40.0),(0.9,35.0)]:
        Rw = env_effect(R, rh, tc)
        Rc = env_compensate(Rw, rh, tc)
        a_w = separability(normalize_response(Rw), labels, np.random.default_rng(9))
        a_c = separability(normalize_response(Rc), labels, np.random.default_rng(9))
        rows.append((rh,tc,a_w,a_c))
        print(f"  {rh:>6.1f}{tc:>7.1f}{a_w:>10.3f}{a_c:>10.3f}")
    ok["⑭ ★ 补偿后识别率恢复（各条件均 ≥ 未补偿）"] = bool(
        all(c >= w - 1e-9 for _,_,w,c in rows))
    print(f"\n  基线（标准环境）{base_acc:.3f}")
    print("  ★ 补偿前提：你【测了】温湿度。没测就补不了。")

    print("\n"+"="*88)
    print(" 判据汇总")
    print("="*88)
    for k,v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未建模：气味空间的【化学结构轴】（分子特征决定受体亲和度）")
    print("  ❌ 未建模：嗅球侧抑制、嗅皮层稀疏编码、气味记忆")
    print("  ❌ 未建模：气流/吸附动力学、鼻腔层流与嗅裂解剖")
    print("  ⚠️ 受体响应矩阵是随机生成的，不是真实 OR-odor 亲和度数据")
    json.dump({k:bool(v) for k,v in ok.items()},
              open(os.path.join(HERE,".sense","nose.json"),"w"),
              ensure_ascii=False, indent=1)
