#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★80 亲缘 —— 用群体遗传学的尺子，量顶级 AI 的优点和毛病

被测量的不是洛神，是 Grok 4 Heavy 和 Anthropic 的三 agent 架构。
尺子来自自然：P = G + E 的表型分解、有效种群大小 Ne、远缘引入。

★ 这一课没有"洛神要不要考试"这一项。这是给她看的。
"""

from __future__ import annotations
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from kinship import group_estimate  # noqa

NS = [1, 2, 4, 8, 16, 32, 64]
R = []
print("=" * 78)
print("★80 亲缘 —— 用群体遗传学量顶级 AI")
print("=" * 78)

# ── 诊断 A：Grok 的辩论为什么真有效 ────────────────────
print("\n【A】同源偏差 = 0 时（各 agent 犯的是各自不同的错）")
print("     → 这就是 Grok 把幻觉从 12% 打到 4.2% 的那一半")
row_a = [group_estimate(n, 0.0, 0.0, 1.0, 1.0, rng=np.random.default_rng(100 + n)) for n in NS]
for n, v in zip(NS, row_a):
    print(f"  N={n:<3} 误差 {v:.4f}")
sl = float(np.polyfit(np.log2(NS), np.log2(row_a), 1)[0])
c_a = abs(sl + 0.5) < 0.12
print(f"  log-log 斜率 {sl:+.2f}  理论 −0.50（1/√N）   {('✅' if c_a else '❌')} 辩论确实在消特异项")
R.append(("A Grok 辩论有效：误差∝1/√N", c_a))

# ── 诊断 B：同源偏差 > 0 时，堆 N 无效（★ 顶级 AI 的毛病）──
print("\n【B】同源偏差 σ_s=1.0（所有 agent 共享同一个盲区）")
print("     → Grok 的 Lucas 抓不住'四个都不知道的事实'；CJR 引用幻觉 94%")
row_b = [group_estimate(n, 0.0, 1.0, 1.0, 1.0, rng=np.random.default_rng(200 + n)) for n in NS]
for n, v in zip(NS, row_b):
    print(f"  N={n:<3} 误差 {v:.4f}")
# N 从 4 到 64 还有改善吗？
gain_late = row_b[2] - row_b[-1]
E_abs_s = np.sqrt(2.0 / np.pi)      # E|N(0,σ_s)| = √(2/π)·σ_s ≈ 0.798
c_b = (gain_late / max(row_b[2], 1e-9) < 0.15
       and 0.85 < row_b[-1] / E_abs_s < 1.15)
print(f"  N=4→64 只降了 {gain_late:.4f}（{gain_late/max(row_b[2],1e-9)*100:.0f}%）")
print(f"  地板 {row_b[-1]:.3f} vs 理论 E|s|={E_abs_s:.3f}  比值 {row_b[-1]/E_abs_s:.2f}")
print(f"  {('✅' if c_b else '❌')} 堆到 16 路也没用 —— 误差卡在同源项上，不卡在个体数上")
R.append(("B 堆 N 无效：误差卡在同源地板", c_b))

# ── 诊断 C：野败才是解药 ────────────────────────────────
print("\n【C】引入远缘（野败）—— 打破同源地板的唯一办法")
print("    σ_s=1.0，远缘个体精度差 1.6×；野生物种自带同源偏差 σ_so=0.8（连锁累赘）")
OM = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]
row_c = [group_estimate(16, w, 1.0, 1.0, 1.6, sigma_so=0.8,
                        rng=np.random.default_rng(300 + int(w * 10))) for w in OM]
for w, v in zip(OM, row_c):
    print(f"  ω={w:<4} 误差 {v:.4f}")
i_c = int(np.argmin(row_c))
c_c = 0 < i_c < len(OM) - 1 and row_c[i_c] < row_c[0] * 0.75
print(f"  {('✅' if c_c else '❌')} 最优 ω={OM[i_c]}（内部峰）；"
      f"全野生 ω=1.0 是 {row_c[-1]:.3f} > 最优 {row_c[i_c]:.3f} —— 远缘衰退（连锁累赘）")
R.append(("C 野败破同源：最优ω在内部", c_c))

# ── 诊断 D：最优野败比例随同源强度上升 ──────────────────
print("\n【D】同源偏差越强 → 该掺的野血越多（袁隆平的剂量）")
best_by_s = {}
for ss in [0.0, 0.5, 1.0, 2.0, 3.0]:
    row = [group_estimate(16, w, ss, 1.0, 1.6, sigma_so=0.8,
                          rng=np.random.default_rng(400 + int(ss * 10) + int(w * 10)))
           for w in OM]
    i = int(np.argmin(row))
    best_by_s[ss] = OM[i]
    print(f"  σ_s={ss:<4} 最优 ω={OM[i]:<4}  (误差 {row[i]:.4f} vs 纯同源 {row[0]:.4f})")
mono = all(best_by_s[a] <= best_by_s[b] for a, b in
           zip([0.0, 0.5, 1.0, 2.0], [0.5, 1.0, 2.0, 3.0]))
c_d = best_by_s[0.0] == 0.0 and best_by_s[3.0] >= 0.3
print(f"  {('✅' if c_d else '❌')} 没同源就该纯种（ω=0）；同源很强就该多掺野血（ω≥0.3）")
R.append(("D 野败剂量随同源强度上升", c_d))

# ── 诊断 E：印证伯克利"改规范只提升 14%" ────────────────
print("\n【E】为什么伯克利改角色规范只提升 14%？")
print("    改规范 = 降 σ_i（让每个个体更守规矩）；改多样性 = 降 σ_s")
base = group_estimate(16, 0.0, 1.0, 1.0, 1.6, sigma_so=0.8, rng=np.random.default_rng(555))
better_rules = group_estimate(16, 0.0, 1.0, 0.5, 1.6, sigma_so=0.8, rng=np.random.default_rng(556))
more_diverse = group_estimate(16, 0.3, 1.0, 1.0, 1.6, sigma_so=0.8, rng=np.random.default_rng(557))
print(f"  原样                     误差 {base:.4f}")
print(f"  改规范（σ_i 1.0→0.5，减半） {better_rules:.4f}   提升 {(base-better_rules)/base*100:.0f}%")
print(f"  掺野血（ω=0.3）            {more_diverse:.4f}   提升 {(base-more_diverse)/base*100:.0f}%")
c_e = (base - better_rules) / base < 0.25 < (base - more_diverse) / base
print(f"  {('✅' if c_e else '❌')} 个体再守规矩也消不掉共有盲区 —— 与'干预仅提升14%'同型")
R.append(("E 改规范收益饱和 < 改多样性", c_e))

# ── 诊断 F：Anthropic 的 evaluator 为什么仍会宽容 ───────
print("\n【F】Anthropic 明说：evaluator 仍是 LLM，倾向对 LLM 输出宽容")
print("    → 这是同源问题的第二次出现。辩论抓的是【错】，抓不住【共有偏好】")
# 同源偏好：所有同源个体都往同一个方向偏（不是随机错，是系统性偏）
pref = []
for N in NS:
    rng = np.random.default_rng(600 + N)
    errs = []
    for _ in range(400):
        s = rng.normal(0.0, 1.0)                       # 共有偏好方向
        v = 0.0 + s + rng.normal(0, 0.3, N)            # 个体很一致（σ_i 小）
        errs.append(abs(np.mean(v)))
    pref.append(float(np.mean(errs)))
print("  N    " + "  ".join(f"{n}" for n in NS))
print("  误差 " + " ".join(f"{v:.3f}" for v in pref))
sl_f = float(np.polyfit(np.log2(NS), np.log2(pref), 1)[0])
c_f = sl_f > -0.05          # 不下降 = 堆再多也没用
print(f"  N=1→64 log-log 斜率 {sl_f:+.3f}（≈0 = 完全不改善）")
print(f"  {('✅' if c_f else '❌')} 个体越一致（σ_i 很小），聚合越稳定地停在共有偏差上 —— "
      f"不会'吵起来'，只会'一致地错'")
R.append(("F 高一致性≠正确：系统性偏差被稳定继承", c_f))

print("\n" + "=" * 78)
npass = sum(1 for _, b in R if b)
print(f"诊断 {npass}/{len(R)}")
for n, b in R:
    print(f"  {'✅' if b else '❌'} {n}")
print("=" * 78)

json.dump({
    "lesson": "★80 亲缘（用群体遗传学量顶级AI）", "pass": npass, "total": len(R),
    "A_debate_works": {"N": NS, "err": row_a, "slope": sl},
    "B_shared_floor": {"N": NS, "err": row_b},
    "C_wild_abortive": {"omega": OM, "err": row_c, "best": OM[i_c]},
    "D_dose": {str(k): v for k, v in best_by_s.items()},
    "E_rules_vs_diversity": {"base": base, "better_rules": better_rules, "more_diverse": more_diverse},
    "F_high_consensus": {"N": NS, "err": pref, "slope": sl_f},
}, open(os.path.join(os.path.dirname(__file__), "..", "data", "exp80_kinship.json"),
        "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已写入 data/exp80_kinship.json")
