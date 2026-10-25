#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★ 饱和检验：上一组 B 的熵 0.0142 已经贴地，可能是指标顶到天花板的伪影。
  本项目历史上三次栽在饱和上（信号 ×1/×10/×100，指标一字不差）。

  所以扫 kpi_push 的强度曲线：
     0（无目标）→ 0.01 → 0.05 → 0.1 → 0.2 → 0.3 → 0.5 → 1.0
  看：
     存活率是不是单调下降？（单调 = 真机制）
     熵是不是一步掉到底？（一步到底 = 饱和伪影）
     有没有"温和目标反而更好"的区间？（有 = 用户的论断需要加限定）

★ 这条最重要：如果温和目标确实更好，那用户的论断要改成
  "强目标压死探索，弱目标可用"，而不是一刀切"目标函数不像人"。
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5

def entropy(a):
    a = np.asarray(a, float); s = a.sum()
    if s <= 1e-12: return 0.0
    p = a / s; p = p[p > 1e-12]
    return float(-(p * np.log(p)).sum())

def run(kpi, seed, steps=600, N=8):
    L = Life5(N=N, seed=seed); L.kpi_push = kpi
    for _ in range(steps):
        if not L.alive: break
        L.step()
    log = L.log
    if len(log) < 20: return None
    ent = [entropy(r["avec"]) for r in log]
    return dict(alive=L.alive, steps=len(log),
                ent_late=float(np.mean(ent[-50:])),
                share0=float(np.mean([r["share0"] for r in log[-50:]])),
                cap=float(log[-1]["cap"]))

if __name__ == "__main__":
    print("=" * 80)
    print(" 饱和检验 · 目标强度扫掠（kpi_push 0 → 1.0）")
    print("=" * 80)
    print(f"\n{'kpi':>6} {'存活':>7} {'后段熵':>9} {'通道0份额':>10} {'capacity':>10}")
    print("-" * 80)
    rows = []
    for kpi in [0.0, 0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0]:
        rs = [r for r in (run(kpi, s) for s in range(16)) if r]
        al = sum(1 for r in rs if r["alive"])
        e  = np.mean([r["ent_late"] for r in rs])
        s0 = np.mean([r["share0"]   for r in rs])
        c  = np.mean([r["cap"]      for r in rs])
        rows.append(dict(kpi=kpi, alive=al, ent=float(e), share0=float(s0), cap=float(c)))
        print(f"{kpi:>6} {al:>4}/16 {e:>9.4f} {s0:>10.4f} {c:>10.4f}")

    print("-" * 80)
    base = rows[0]
    print(f"\n基线（kpi=0）：存活 {base['alive']}/16，熵 {base['ent']:.4f}")

    # 判据
    alives = [r["alive"] for r in rows]
    ents   = [r["ent"]   for r in rows]
    ok = {}
    # ① 单调性：存活率不上升（允许平台）
    mono = all(alives[i+1] <= alives[i] for i in range(len(alives)-1))
    ok["① 存活率随目标强度单调不升"] = mono
    # ② 饱和检查：熵是不是一步掉到底
    drops = [ents[i] - ents[i+1] for i in range(len(ents)-1)]
    biggest = max(range(len(drops)), key=lambda i: drops[i])
    ok["② 非一步到底（不是饱和伪影）"] = not (drops[biggest] > 0.9 * (ents[0] - ents[-1]) and biggest <= 1)
    # ③ 有没有温和目标更优的区间
    better = [r for r in rows[1:] if r["alive"] > base["alive"]]
    ok["③ 无'温和目标反而更优'区间"] = len(better) == 0

    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n最大跌幅在第 {biggest}→{biggest+1} 段（kpi {rows[biggest]['kpi']}→{rows[biggest+1]['kpi']}），跌 {drops[biggest]:.4f}")
    print(f"各段跌幅：{[round(d,4) for d in drops]}")

    json.dump({"rows": rows, "ok": {k: bool(v) for k, v in ok.items()}, "drops": [float(d) for d in drops]},
              open(os.path.join(HERE, ".sense", "L0_kpi_sweep.json"), "w"), ensure_ascii=False, indent=1)
