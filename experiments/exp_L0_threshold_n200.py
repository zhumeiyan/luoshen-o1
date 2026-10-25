#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★ 上一轮的问题：16 seeds 上 13 vs 14 只差 1 个，可能纯噪声。
  在噪声上编故事，正是本项目最忌讳的（★4/★6/★7/★10 全是这类）。

  所以：kpi ∈ {0, 0.05} 各跑 200 seeds，用 bootstrap 看差异的置信区间。
  如果 CI 跨 0 → 那个"温和目标更优"是噪声，必须撤回。
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5

def run(kpi, seed, steps=600, N=8):
    L = Life5(N=N, seed=seed); L.kpi_push = kpi
    for _ in range(steps):
        if not L.alive: break
        L.step()
    log = L.log
    if len(log) < 20: return None
    return dict(alive=1 if L.alive else 0,
                steps=len(log),
                ent=float(np.mean([np.std(r["avec"])/max(sum(r["avec"]),1e-12)
                                   for r in log[-50:]])))

def boot_ci(xs, n=4000, seed=7):
    rng = np.random.default_rng(seed)
    xs = np.asarray(xs, float)
    bs = [rng.choice(xs, size=len(xs), replace=True).mean() for _ in range(n)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

if __name__ == "__main__":
    N_SEED = 200
    print("=" * 78)
    print(f" 大样本检验 · kpi=0 vs kpi=0.05 各 {N_SEED} seeds")
    print("=" * 78)

    res = {}
    for kpi in [0.0, 0.05]:
        rs = [r for r in (run(kpi, s) for s in range(N_SEED)) if r]
        al = [r["alive"] for r in rs]
        lo, hi = boot_ci(al)
        res[kpi] = dict(n=len(rs), alive=int(sum(al)), rate=float(np.mean(al)),
                        ci=[lo, hi], steps=float(np.mean([r["steps"] for r in rs])))
        print(f"\n  kpi={kpi:<6} 存活 {sum(al)}/{len(rs)} = {np.mean(al):.4f}"
              f"   95%CI [{lo:.4f}, {hi:.4f}]")
        print(f"           平均存活步数 {np.mean([r['steps'] for r in rs]):.1f}")

    d = res[0.05]["rate"] - res[0.0]["rate"]
    print(f"\n" + "=" * 78)
    print(f" 存活率差 (0.05 − 0) = {d:+.4f}")
    ci0, ci5 = res[0.0]["ci"], res[0.05]["ci"]
    overlap = not (ci5[0] > ci0[1] or ci0[0] > ci5[1])
    print(f" 两个 CI 重叠吗: {'是 —— 差异不显著' if overlap else '否 —— 差异显著'}")
    print(f"   kpi=0   CI [{ci0[0]:.4f}, {ci0[1]:.4f}]")
    print(f"   kpi=0.05 CI [{ci5[0]:.4f}, {ci5[1]:.4f}]")

    ok = {}
    key = "① 大样本下无[温和目标更优]证据"
    ok[key] = bool(d <= 0 or overlap)
    tail = "无证据（上轮那个 14>13 是噪声）" if (d <= 0 or overlap) else "真显著"
    mark = "✅" if ok[key] else "❌"
    print("\n  " + mark + " " + key + " —— " + tail)

    json.dump({str(k): v for k, v in res.items()},
              open(os.path.join(HERE, ".sense", "L0_threshold_n200.json"), "w"),
              ensure_ascii=False, indent=1)
