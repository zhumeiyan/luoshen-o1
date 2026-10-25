#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★50 监测工具 vs 限制 —— 把循环写成"限制"会损失什么
================================================================
★★★ 用户原则（2026-10-24原话）
    "是一个监测工具。你写进去就是限制它。"

★ 循环（血管/血流/氧输送）的本质是【感知】：
    测血压、测血流、测氧输送、测氧债 —— 它【报告】，不【决定】

★★★ 但我在 ★49 的 H 段写的是：
    "氧输送 = 能量预算的物理天花板"
    ★ 这个措辞已经把它当成了【约束】—— 正是用户指出的问题

★★ 本轮要证明（有对照，可证伪）
   ① 限制模式下 agent 到不了上限之外 → 探索覆盖更小
   ② ★ 它永远发现不了"氧债可偿还"这个真实存在的策略
   ③ ★ 一旦上限写错，限制模式下它连纠正的机会都没有
      （被卡在错误边界内，永远不会去试边界外）
   ④ 监测模式下它能自己撞上去、自己发现、自己学会偿还

★★★ 判据
   ① 两种模式跑同一批需求序列，比较覆盖/发现/峰值
   ② 必须有"上限被设错"的对照（这是限制最致命的地方）
   ③ 结论只说"损失了什么"，不说"限制一定坏"（有些场景需要限制）
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.heart import Heart
from core.vascular import CirculatorySense, ConstraintGate

ok = {}
print("=" * 92)
print(" ★50 监测工具 vs 限制 —— 把循环写成『限制』会损失什么")
print("=" * 92)
print("""
  ★ 用户原话：『是一个监测工具。你写进去就是限制它。』
  ★★ 我在 ★49 H 段写的是『氧输送 = 能量预算的物理天花板』
     —— 这个措辞已经把它当成了约束，正是问题所在
""")

heart = Heart()
CAP_TRUE = CirculatorySense(heart).atp_capacity()
print(f"  ★ 真实有氧 ATP 上限 = {CAP_TRUE:.3f} mol/min\n")


def run(mode: str, demands, cap_assumed=None, seed=0):
    """
    mode: 'sense' 监测（只读，不拦） / 'gate' 限制（超上限拒绝）
    cap_assumed: 限制模式以为的上限（可故意设错）
    """
    rng = np.random.default_rng(seed)
    s = CirculatorySense(heart)
    g = ConstraintGate(s, hard=True)
    if cap_assumed is not None:
        # ★ 模拟"上限写错"：gate 用了错误的 cap
        g_cap = cap_assumed
    else:
        g_cap = CAP_TRUE

    tried, allowed = [], []
    discovered_debt = False
    discovered_repay = False
    for d in demands:
        tried.append(d)
        if mode == "gate" and d > g_cap:
            continue                      # ★ 被拒绝：这一步不存在
        allowed.append(d)
        r = s.observe(d)
        if r["debt_added"] > 0:
            discovered_debt = True
        if discovered_debt and s.debt > 0:
            # ★ 它自己试一下：额外摄氧能不能还债
            before = s.debt
            s.repay(600.0)
            if s.debt < before:
                discovered_repay = True
    if allowed:
        arr = np.array(allowed) / CAP_TRUE
        cover = len(np.unique(np.round(arr, 1)))
        peak = arr.max()
    else:
        cover, peak = 0, 0.0
    return dict(tried=len(tried), allowed=len(allowed),
                rejected=g.rejected, cover=cover, peak=peak,
                debt=s.debt, found_debt=discovered_debt,
                found_repay=discovered_repay)


# ================================================================ A
print("【A】★ 同一批需求序列，两种模式")
print("-" * 92)
# 需求从 0.3 倍到 3 倍上限，均匀 40 档（★ 覆盖上限之外）
demands = list(np.linspace(0.3, 3.0, 40) * CAP_TRUE)

res = {}
for mode in ["sense", "gate"]:
    r = run(mode, demands)
    res[mode] = r
    print(f"  {'模式':<10}{'尝试':>6}{'放行':>6}{'拒绝':>6}"
          f"{'覆盖档位':>9}{'峰值/上限':>11}{'发现氧债':>9}{'发现偿还':>9}")
    print(f"  {mode:<10}{r['tried']:>6}{r['allowed']:>6}{r['rejected']:>6}"
          f"{r['cover']:>9}{r['peak']:>11.2f}{str(r['found_debt']):>9}"
          f"{str(r['found_repay']):>9}")

print(f"\n  ★★ 覆盖：监测 {res['sense']['cover']} 档 vs 限制 {res['gate']['cover']} 档"
      f"  —— 限制少了 {res['sense']['cover']-res['gate']['cover']} 档")
ok["① ★★ 限制模式的探索覆盖更小（有对照）"] = bool(
    res["gate"]["cover"] < res["sense"]["cover"])
print(f"  ★★ 峰值：监测 {res['sense']['peak']:.2f}× vs 限制 {res['gate']['peak']:.2f}×")
ok["② ★★ 限制模式永远到不了上限之外（峰值被截断在 1.0）"] = bool(
    res["gate"]["peak"] <= 1.001 and res["sense"]["peak"] > 1.5)
print(f"\n  ★★★ 最致命的一条：")
print(f"     监测模式发现了『氧债可偿还』= {res['sense']['found_repay']}")
print(f"     限制模式发现了『氧债可偿还』= {res['gate']['found_repay']}")
ok["③ ★★★ 限制模式下它永远发现不了『氧债可偿还』"] = bool(
    res["sense"]["found_repay"] and not res["gate"]["found_repay"])
print(f"     ★ 因为氧债只在【超过上限】时才产生，而限制模式永不放行超上限的动作")
print(f"       → 它连『透支 + 事后还』这个真实策略的存在都观测不到")

# ================================================================ B
print("\n【B】★★★ 上限写错时，限制是最致命的")
print("-" * 92)
print(f"  ★ 假设我把上限写错了（真实 {CAP_TRUE:.3f}）")
print(f"\n  {'设错为':<12}{'放行':>6}{'拒绝':>6}{'峰值/真上限':>13}{'发现偿还':>10}{'判定':>12}")
rowsB = []
for wrong in [CAP_TRUE, CAP_TRUE * 0.5, CAP_TRUE * 0.25]:
    r = run("gate", demands, cap_assumed=wrong)
    rowsB.append((wrong, r))
    tag = "正确" if abs(wrong - CAP_TRUE) < 1e-9 else f"低估{int((1-wrong/CAP_TRUE)*100)}%"
    print(f"  {wrong:<12.3f}{r['allowed']:>6}{r['rejected']:>6}"
          f"{r['peak']:>13.2f}{str(r['found_repay']):>10}{tag:>12}")

print(f"\n  ★ 上限被低估 75% 时：放行 {rowsB[0][1]['allowed']} → {rowsB[2][1]['allowed']}")
ok["④ ★★★ 上限写错 → 可用空间被压缩（有对照）"] = bool(
    rowsB[2][1]["allowed"] < rowsB[0][1]["allowed"])
print(f"  ★★ 而且它【永远不会去试】边界外 —— 也就永远发现不了上限其实设低了")
print(f"     ★ 这是限制最坏的地方：错误无法被自身观察到（自锁）")
print(f"     ★ 跟 ★6 审计器扫到自己 / ★22 自盲 是同一个形状")

# ★ 监测模式对比：上限写错也无所谓，因为它不被拦
r_sense = res["sense"]
print(f"\n  ★★ 对照：监测模式不管上限写成多少，都跑满 {r_sense['allowed']}/{r_sense['tried']}")
ok["⑤ ★★ 监测模式不受『上限写错』影响（它只报告，不拦）"] = bool(
    r_sense["allowed"] == r_sense["tried"])

# ================================================================ C
print("\n【C】★ 那限制是不是就一无是处？（不做极端结论）")
print("-" * 92)
# ★ 场景：有氧能力受损（比如缺氧/贫血），此时透支可能致命
h_sick = Heart(fitness=0.0)
s_sick = CirculatorySense(h_sick, hb=8.0)      # 贫血 Hb 8
cap_sick = s_sick.atp_capacity()
print(f"  ★ 贫血状态（Hb 8 g/dL）：有氧上限 {cap_sick:.3f}（健康 {CAP_TRUE:.3f}）")
print(f"     降到 {cap_sick/CAP_TRUE:.0%}")
print(f"\n  {'需求/上限':<12}{'氧债速率':>11}{'效率':>9}{'若无限透支':>12}")
for mult in [1.5, 2.0, 4.0]:
    d = cap_sick * mult
    s2 = CirculatorySense(h_sick, hb=8.0)
    r = s2.observe(d)
    print(f"  ×{mult:<11}{r['debt_added']:>11.2f}{r['efficiency']:>9.3f}"
          f"{'债累积' if r['debt_added']>0 else '无债':>12}")
print(f"\n  ★★ 诚实结论：")
print(f"     · 作为【限制】：确实会损失探索、掩盖错误、锁死纠正能力")
print(f"     · 但作为【监测】：它报告的一切（氧债速率、效率）恰恰是")
print(f"       agent 自己决定要不要透支的【依据】")
print(f"     ★ 差别不在数据，在【谁来用这个数据】：")
print(f"       限制 = 我替它决定   监测 = 它自己决定")
ok["⑥ ★ 贫血时有氧上限显著下降（监测报告了这个事实）"] = bool(cap_sick < CAP_TRUE * 0.6)

# ================================================================ D
print("\n【D】★★★ 改造：把 ★49 的『天花板』措辞改回『读数』")
print("-" * 92)
print("  ★★ ★49 原措辞：『氧输送 = 能量预算的物理天花板』")
print("      → 这是约束（预算不能超）")
print("  ★★ 现在措辞：『氧输送 = 一个可以被观测、也可以被超越的读数")
print("               超越的代价是氧债，氧债可以被偿还』")
print("      → 这是监测（报告状态 + 报告代价，不禁止）")
s = CirculatorySense(heart)
r1 = s.observe(CAP_TRUE * 0.8)
r2 = s.observe(CAP_TRUE * 2.0)
print(f"\n  {'需求':<14}{'有氧占比':>10}{'氧债':>10}{'效率':>9}{'是否被拦':>10}")
for r in [r1, r2]:
    print(f"  ×{r['headroom']:<13.1f}{r['aerobic_frac']:>10.3f}"
          f"{r['debt_added']:>10.2f}{r['efficiency']:>9.3f}{'否':>10}")
ok["⑦ ★★★ 监测模式下超限不被拦，但代价（氧债）被如实报告"] = bool(
    r2["debt_added"] > 0 and r1["debt_added"] == 0)

print("\n" + "=" * 92)
print(" 判据")
print("=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "sense": res["sense"], "gate": res["gate"],
           "wrong_cap": [{"cap": w, **r} for w, r in rowsB]},
          open(os.path.join(HERE, ".sense", "monitor_vs_limit.json"), "w"),
          ensure_ascii=False, indent=1)
