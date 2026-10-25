#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
味觉 —— 化学感受，也是【分子手性】暴露得最彻底的一层
==========================================================
★ 与前面所有层的根本不同：
    眼耳鼻感受【物理量】，味觉直接感受【化学键的立体构型】

★ 核心：
  ① ★★ 味觉地图是假的（教科书级假货，1942 误译）
  ② ★★★ 分子手性：阿斯巴甜 L,L 甜 / D,D 苦 —— 甜苦完全反转
  ③ ★★ 辣不是味觉，是 TRPV1 痛觉（与 ★27 皮肤同一个受体）
  ④ ★ 风味 = 味觉 + 鼻后嗅觉（捏鼻子分不出苹果洋葱）
  ⑤ 苦阈值是甜的 1/1250 —— 毒物检测
  ⑥ 味觉细胞是上皮细胞，10~14 天换一批
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.taste import (
    THRESHOLD_MM, HILL_N, T1R_COUNT, T2R_COUNT, SWEETNESS_X,
    TASTE_CELL_LIFETIME_DAYS, OLFACTORY_CELL_LIFETIME_DAYS,
    TRPV1_THRESHOLD_C, TRPM8_PEAK_C,
    CLASSIC_MAP, REAL_MAP,
    hill, taste_response, threshold_curve, bitter_advantage,
    taste_map, map_discrepancy,
    chirality_valence, aspartame, chirality_sweep, limonene,
    chirality_kinds, no_chirality_control,
    trpv1_threshold, trpm8_threshold, pungency, coolness, is_taste,
    flavor, pinch_nose, apple_vs_onion, turnover_fraction,
    adaptation, salt_then_water, acid_enhances_salt,
)

if __name__ == "__main__":
    print("="*88); print(" 味觉：直接感受分子立体构型的一层"); print("="*88)
    ok = {}

    # ---------- 1 五种味觉阈值 ----------
    print("\n【实验1】五种基本味觉的检测阈值（REAL）")
    print("-"*88)
    print(f"  {'味觉':<6}{'阈值(mM)':>12}{'受体':>12}{'REAL对照':>20}")
    notes = {"甜": "蔗糖 10mM", "咸": "NaCl 10mM", "鲜": "MSG 1.5mM",
             "酸": "HCl 1mM", "苦": "奎宁 0.008mM"}
    for m in ["甜", "咸", "鲜", "酸", "苦"]:
        rec = "T2R×25" if m == "苦" else ("ENaC" if m == "咸"
              else ("OTOP1" if m == "酸" else "T1R"))
        print(f"  {m:<6}{THRESHOLD_MM[m]:>12}{rec:>12}{notes[m]:>20}")
    adv = bitter_advantage()
    ok["① ★ 苦的阈值最低（毒物检测优先）"] = bool(
        THRESHOLD_MM["苦"] == min(THRESHOLD_MM.values()))
    ok["② ★ 苦/甜阈值比 > 500（REAL 约 1250）"] = bool(adv["苦阈值/甜阈值"] > 500)
    ok["③ ★ 苦受体数 >> 甜受体组合数（25 vs 1）"] = bool(T2R_COUNT > 10 * 1)
    print(f"\n  ★ 苦的阈值 {THRESHOLD_MM['苦']} mM，是甜 {THRESHOLD_MM['甜']} mM 的 "
          f"1/{adv['苦阈值/甜阈值']:.0f}")
    print(f"  ★ 苦有 {T2R_COUNT} 种受体，甜只有 1 种组合")
    print("  ★★ 甜只需检测糖（一种分子），苦要检测成千上万种毒物")
    print("     ★ 受体多样性对应【待检测物的多样性】—— 这是设计约束，不是偶然")

    # ---------- 2 ★★ 味觉地图是假的 ----------
    print("\n【实验2】★★ 味觉地图是假的（教科书级假货）")
    print("-"*88)
    print(f"  {'部位':<8}{'味觉':<6}{'经典地图':>10}{'真实':>10}{'差':>8}")
    worst = map_discrepancy()
    for site in REAL_MAP:
        for mod in ["甜", "咸", "酸", "苦"]:
            c = taste_map(site, mod, real=False)
            r = taste_map(site, mod, real=True)
            mark = "  ★" if (site, mod) == (worst["site"], worst["modality"]) else ""
            print(f"  {site:<8}{mod:<6}{c:>10.2f}{r:>10.2f}{r-c:>8.2f}{mark}")
    nz_classic = sum(1 for s in CLASSIC_MAP for m in CLASSIC_MAP[s]
                     if CLASSIC_MAP[s][m] > 0)
    nz_real = sum(1 for s in REAL_MAP for m in REAL_MAP[s] if REAL_MAP[s][m] > 0)
    ok["④ ★ 经典地图只有 4/16 格非零（绝对分区）"] = bool(nz_classic == 4)
    ok["⑤ ★ 真实地图 16/16 格全非零（所有区域所有味觉）"] = bool(nz_real == 16)
    ok["⑥ ★ 舌根甜：经典 0，真实 >0.5"] = bool(
        taste_map("舌根", "甜", False) == 0 and taste_map("舌根", "甜", True) > 0.5)
    allv = [REAL_MAP[s][m] for s in REAL_MAP for m in REAL_MAP[s]]
    ok["⑦ ★ 真实敏感度极差 < 2 倍（Hänig 原测是相对量）"] = bool(
        max(allv) / min(allv) < 2.0)
    print(f"\n  ★ 经典地图断言：舌根尝不出甜（0.00）")
    print(f"  ★ 真实：舌根甜味敏感度 {taste_map('舌根','甜',True):.2f} —— 尝得出")
    print(f"  ★ 来源：1901 Hänig 测的是【相对敏感度】，1942 Boring 英译时")
    print(f"        把相对量画成了【绝对分区图】，从此流传")
    print("  ★★ 与 ★26'解剖手性≠功能手性'同一类：教科书上的图 ≠ 真实机制")

    # ---------- 3 ★★★ 分子手性 ----------
    print("\n【实验3】★★★ 分子手性：阿斯巴甜的甜苦反转")
    print("-"*88)
    print(f"  {'手性c':>8}{'甜度':>10}{'苦度':>10}{'净价态':>12}{'感知':>8}")
    for c in [1.0, 0.5, 0.0, -0.5, -1.0]:
        a = aspartame(c)
        print(f"  {c:>+8.1f}{a['sweet']:>10.2f}{a['bitter']:>10.2f}"
              f"{a['valence']:>+12.2f}{a['percept']:>8}")
    p, n = aspartame(+1.0), aspartame(-1.0)
    ok["⑧ ★★ L,L(c=+1) 判为甜，D,D(c=−1) 判为苦"] = bool(
        p["percept"] == "甜" and n["percept"] == "苦")
    ok["⑨ ★★ 价态符号在手性翻转时【反转】"] = bool(
        p["valence"] > 0 and n["valence"] < 0)
    sw = chirality_sweep()
    # ★ 第一版写 np.all(np.diff(valence) < 0)：c 从 −1 到 +1，价态是【递增】的
    #   → 方向写反，判据必然失败
    ok["⑩ ★ 价态随手性单调变化（无跳变）"] = bool(
        np.all(np.diff(sw["valence"]) > 0))
    ctrl = no_chirality_control()
    ok["⑪ ★★ 对照：去掉手性维度(c=0) → 不能反转（价态恒正）"] = bool(
        not ctrl["reversible"] and ctrl["valence"] > 0)
    print(f"\n  ★ 同一个分子式、同样的原子组成：")
    print(f"    L,L → 甜 {p['sweet']:.0f}×蔗糖      D,D → 苦 {n['bitter']:.0f}")
    print(f"  ★ 去掉手性维度，甜苦就锁死了（c=0 时价态 {ctrl['valence']:+.2f} 恒正）")
    print("  ★★ 手性维度是【必需】的 —— 没有它就产生不了这个现象")
    kinds = chirality_kinds()
    print(f"\n  ★ 两种手性效应要区分：")
    print(f"    阿斯巴甜 = 【价态反转】{kinds['阿斯巴甜']['L,L']} ↔ {kinds['阿斯巴甜']['D,D']}")
    print(f"    柠檬烯   = 【身份变化】{kinds['柠檬烯']['R(+)']} ↔ {kinds['柠檬烯']['S(-)']}")
    ok["⑫ ★ 柠檬烯是身份变化（都是好气味），不是价态反转"] = bool(
        limonene(+1.0) != limonene(-1.0))
    print("  ★★ 天然氨基酸全是 L 型，天然糖全是 D 型 —— 生命本身就是手性的")

    # ---------- 4 ★★ 辣不是味觉 ----------
    print("\n【实验4】★★ 辣不是味觉，是痛觉（TRPV1）")
    print("-"*88)
    print(f"  {'辣椒素(μM)':>12}{'TRPV1阈值(°C)':>16}{'辣度(37°C)':>14}")
    for cap in [0, 1, 2, 5, 10, 20]:
        print(f"  {cap:>12}{trpv1_threshold(cap):>16.1f}{pungency(cap):>14.2f}")
    ok["⑬ ★ 无辣椒素时阈值 43°C > 体温 37°C → 不辣"] = bool(
        trpv1_threshold(0) > 37.0 and pungency(0) == 0.0)
    ok["⑭ ★ 辣椒素把阈值拉到体温以下 → 辣"] = bool(
        trpv1_threshold(10) < 37.0 and pungency(10) > 0)
    print(f"\n  {'薄荷醇(mM)':>12}{'TRPM8阈值(°C)':>16}{'凉度(37°C)':>14}")
    for m in [0, 1, 3, 5, 10]:
        print(f"  {m:>12}{trpm8_threshold(m):>16.1f}{coolness(m):>14.2f}")
    ok["⑮ ★ 薄荷醇把 TRPM8 阈值推到体温以上 → 凉"] = bool(
        trpm8_threshold(5) > 37.0 and coolness(5) > 0)
    ok["⑯ ★ 辣/凉都不属于味觉（走三叉神经 CN V）"] = bool(
        not is_taste("辣") and not is_taste("凉") and is_taste("甜"))
    print(f"\n  ★★ 辣 = TRPV1 被化学拉低阈值（★27 皮肤的热痛通道，43°C）")
    print(f"  ★★ 凉 = TRPM8 被化学推高阈值（★27 皮肤的冷通道，峰值 25°C）")
    print(f"  ★ 这两个受体与 ★27 皮肤【是同一个】—— 口腔里的体感")
    print(f"  ★ 传导：辣凉走三叉神经 CN V，甜咸酸苦鲜走 CN VII/IX/X")

    # ---------- 5 ★ 风味 ----------
    print("\n【实验5】★ 风味 = 味觉 + 鼻后嗅觉")
    print("-"*88)
    f = flavor(np.zeros(5), np.zeros(400), 0.0)
    print(f"  味觉维度 {f['taste_dim']}   鼻后嗅觉维度 {f['retronasal_dim']}   "
          f"合计 {f['total_dim']}")
    print(f"  捏鼻子（鼻后通路断）→ 只剩 {pinch_nose(0.0):.0f} 维")
    print(f"  ★ 苹果 vs 洋葱：{apple_vs_onion(True)} / {apple_vs_onion(False)}")
    ok["⑰ ★ 捏鼻子后维度从 ~400 掉到 5"] = bool(pinch_nose(0.0) < 10)
    ok["⑱ ★ 捏鼻子分不出苹果和洋葱"] = bool(
        apple_vs_onion(False).startswith("分不出"))
    print("\n  ★ 味觉本身只有 5 个维度，风味的丰富度几乎【全来自嗅觉】")
    print("  ★ 鼻后通路（retronasal）从口腔后部进鼻腔")
    print("  ★ 与 ★26 鼻子共用同一套受体，只是入口不同")
    print("  ★ 感冒鼻塞吃东西没味道 —— 就是这个通路断了")

    # ---------- 6 细胞更新 ----------
    print("\n【实验6】★ 味觉细胞是【上皮细胞】，10~14 天换一批")
    print("-"*88)
    print(f"  {'天数':>8}{'更新比例':>12}")
    for d in [1, 3, 7, 12, 21, 30]:
        print(f"  {d:>8}{float(turnover_fraction(np.array([d]))[0]):>12.1%}")
    tau = sum(TASTE_CELL_LIFETIME_DAYS) / 2.0
    tau_o = sum(OLFACTORY_CELL_LIFETIME_DAYS) / 2.0
    ok["⑲ ★ 12 天时更新过半（REAL 寿命 10~14 天）"] = bool(
        0.5 < float(turnover_fraction(np.array([12.0]))[0]) < 0.8)
    ok["⑳ ★ 味觉更新快于嗅觉（12 天 vs 45 天）"] = bool(tau < tau_o)
    print(f"\n  ★ 味觉 {tau:.0f} 天 vs 嗅觉（★26）{tau_o:.0f} 天 —— 味觉快约 "
          f"{tau_o/tau:.1f} 倍")
    print("  ★ 原因：口腔环境恶劣（温度剧变、机械磨损、pH 波动）")

    # ---------- 7 适应与对比 ----------
    print("\n【实验7】适应与对比增强")
    print("-"*88)
    t = np.array([0, 1, 3, 6, 12])
    a = adaptation(100.0, t)
    print(f"  {'持续(s)':>9}{'甜响应':>10}")
    for tt, v in zip(t, a):
        print(f"  {tt:>9}{v:>10.3f}")
    ok["21 ★ 持续刺激响应衰减（6 秒后 <10%）"] = bool(a[3] < 0.1)
    w = salt_then_water(100.0)
    ok["22 ★★ 盐水漱口后，水【变甜】（交叉适应）"] = bool(w > 0.3)
    e1 = taste_response(5.0, "咸"); e2 = acid_enhances_salt(2.0, 5.0)
    ok["23 ★ 酸能增强咸味感知"] = bool(e2 > e1)
    print(f"\n  ★ 100mM 盐水漱口后，纯水甜度 {w:.3f}（原本 0）")
    print(f"  ★ 5mM 咸味：纯咸 {e1:.3f} → 加 2mM 酸后 {e2:.3f}（+{(e2/e1-1):.0%}）")
    print("  ★ 应用：少放盐，加点柠檬汁会显得更咸")

    print("\n"+"="*88); print(" 判据汇总"); print("="*88)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未建模：脂肪味(oleogustus, CD36)—— 候选第六味")
    print("  ❌ 未建模：超级品尝者(TAS2R38/PROP，约 25% 人群)")
    print("  ❌ 未建模：味觉的中枢编码（NTS→VPMpc→岛叶）")
    print("  ⚠️ 阿斯巴甜甜苦曲线用高斯近似，非真实剂量反应数据")
    json.dump({k: bool(v) for k, v in ok.items()},
              open(os.path.join(HERE, ".sense", "taste.json"), "w"),
              ensure_ascii=False, indent=1)
