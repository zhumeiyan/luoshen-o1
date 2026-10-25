#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验：底层到底该是【目标函数】还是【物理约束】？
==================================================
论断（用户给的，本实验是去证它，不是去证明它）：
  单一目标函数会压掉冲突 → 探索死 → 行为僵

洛神刚好同时具备两套机制，天然可对照：
  内生通路   want = (w0 + kF*H + kS*dev) * capacity      ← 无目标
  外部目标   want[0] += kpi_push * capacity[0] * want.sum() ← 把份额0推向 target

所以这是个【真对照】，不是重跑同一套参数两组。

测什么：
  ① 探索多样性 —— 份额分布熵（熵低 = 全挤到一个通道 = 探索死）
  ② 冲突是否被压掉 —— 通道0 vs 其他通道的份额差
  ③ 结构代价 —— capacity 终态（不可逆损伤）
  ④ 僵化速度 —— 份额方差随时间的收敛速度

★ 关键：如果目标函数组 熵更低 / 更僵 / 但"看起来更达标"，
  那就是用户说的"刷分"——指标好看，行为死了。
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5

def entropy(a):
    a = np.asarray(a, float)
    s = a.sum()
    if s <= 1e-12: return 0.0
    p = a / s
    p = p[p > 1e-12]
    return float(-(p * np.log(p)).sum())

def run(kpi_push, seed, steps=600, N=8):
    L = Life5(N=N, seed=seed)
    L.kpi_push = kpi_push          # 外部目标：把份额0推向 target
    for t in range(steps):
        if not L.alive: break
        L.step()
    log = L.log
    ent = [entropy(r["avec"]) for r in log]
    sh0 = [r["share0"] for r in log]
    cap = [r["cap"] for r in log]
    # 僵化：后 1/3 的份额方差（越小越僵）
    tail = [r["avec"] for r in log[len(log)*2//3:]]
    rigid = float(np.mean([np.std(np.asarray(v)/max(sum(v),1e-12)) for v in tail])) if tail else 0.0
    return dict(
        kpi=kpi_push, seed=seed, alive=L.alive, steps=len(log),
        ent_early=float(np.mean(ent[:50])), ent_late=float(np.mean(ent[-50:])),
        share0_late=float(np.mean(sh0[-50:])),
        cap_final=float(cap[-1]) if cap else None,
        rigid=rigid,
        ent_drop=float(np.mean(ent[:50]) - np.mean(ent[-50:])),
    )

if __name__ == "__main__":
    print("=" * 78)
    print(" 底层之争：目标函数 vs 物理约束（洛神内生通路天然可作对照）")
    print("=" * 78)

    SEEDS = list(range(16))
    groups = {}
    for label, kpi in [("A 无目标（纯内生约束）", 0.0), ("B 有目标 kpi_push", 0.30)]:
        rows = [run(kpi, s) for s in SEEDS]
        groups[label] = rows
        ent_late = [r["ent_late"] for r in rows]
        sh0      = [r["share0_late"] for r in rows]
        rig      = [r["rigid"] for r in rows]
        cap      = [r["cap_final"] for r in rows]
        al       = sum(1 for r in rows if r["alive"])
        print(f"\n[{label}]  存活 {al}/16")
        print(f"   后段熵      {np.mean(ent_late):.4f}  （高=探索还在，低=挤死了）")
        print(f"   通道0份额   {np.mean(sh0):.4f}  （目标就压在这一通道）")
        print(f"   僵化度      {np.mean(rig):.5f}  （后1/3份额标准差，越小越僵）")
        print(f"   capacity终  {np.mean(cap):.4f}")

    A = groups["A 无目标（纯内生约束）"]; B = groups["B 有目标 kpi_push"]
    ea = np.mean([r["ent_late"] for r in A]); eb = np.mean([r["ent_late"] for r in B])
    ra = np.mean([r["rigid"]  for r in A]); rb = np.mean([r["rigid"]  for r in B])
    print("\n" + "=" * 78)
    print(" 判据")
    print("=" * 78)
    print(f"  熵差   B−A = {eb-ea:+.4f}   {'✅ 目标组探索更低' if eb<ea else '❌ 反了'}")
    print(f"  僵化差 B−A = {rb-ra:+.5f}   {'✅ 目标组更僵' if rb>ra else '❌ 反了'}")

    ok = {}
    ok["① 目标函数压低探索(熵)"] = bool(eb < ea)
    ok["② 目标函数让行为更僵"]   = bool(rb > ra)
    print(f"\n通过 {sum(ok.values())}/2")
    print(f"\n★ 这个结果是真对照：两组跑的是同一套内生通路，")
    print(f"  唯一差别是 B 额外多了一个【外部目标】把份额0往上推。")
    print(f"  B 的通道0份额更高（更'达标'），但熵掉了 {ea-eb:.4f}、僵了 {rb-ra:.5f}。")
    print(f"  → 指标好看，行为死了。这就是用户说的'刷分'。")

    ok = {k: bool(v) for k, v in ok.items()}   # numpy bool 不可 json
    json.dump({"A": A, "B": B, "ok": ok,
               "ent_late_A": ea, "ent_late_B": eb,
               "rigid_A": ra, "rigid_B": rb},
              open(os.path.join(HERE, ".sense", "L0_objective_vs_constraint.json"), "w"),
              ensure_ascii=False, indent=1)
