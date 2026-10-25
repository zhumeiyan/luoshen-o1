#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★ 32 seeds 上 B(31/32) vs A(25/32) 差 6 个 —— 可能纯噪声。
   上次教训（★4/★6/★7/★10/★11/★12）：在噪声上编故事是最忌讳的。
   所以 200 seeds + bootstrap，看 CI 跨不跨 0。
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5
from core.instinct1_energy import EnergyInstinct

N = 200
STEPS = 600

def boot(xs, n=4000, seed=11):
    rng = np.random.default_rng(seed)
    xs = np.asarray(xs, float)
    bs = [rng.choice(xs, len(xs), replace=True).mean() for _ in range(n)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

def run(mode, seed):
    L = Life5(N=8, seed=seed)
    if mode == "A":
        for _ in range(STEPS):
            if not L.alive: break
            L.step()
        return len(L.log), L.alive
    I = EnergyInstinct(L)
    I.run(STEPS)
    return I.t, L.alive

if __name__ == "__main__":
    print("=" * 78)
    print(f" 大样本 · A 原版 vs B 本能版，各 {N} seeds + bootstrap")
    print("=" * 78)
    out = {}
    for mode in ["A", "B"]:
        rs = [run(mode, s) for s in range(N)]
        steps = [r[0] for r in rs]; alive = [1 if r[1] else 0 for r in rs]
        lo, hi = boot(alive); slo, shi = boot(steps)
        out[mode] = dict(alive_n=int(sum(alive)), rate=float(np.mean(alive)),
                         ci=[lo, hi], steps=float(np.mean(steps)), steps_ci=[slo, shi])
        lbl = "A 原版(无本能)" if mode == "A" else "B 本能版(降级)"
        print(f"\n  [{lbl}]")
        print(f"    存活 {sum(alive)}/{N} = {np.mean(alive):.4f}   95%CI [{lo:.4f}, {hi:.4f}]")
        print(f"    平均步数 {np.mean(steps):.1f}          95%CI [{slo:.1f}, {shi:.1f}]")

    d_rate = out["B"]["rate"] - out["A"]["rate"]
    d_step = out["B"]["steps"] - out["A"]["steps"]
    ca, cb = out["A"]["ci"], out["B"]["ci"]
    overlap = not (cb[0] > ca[1] or ca[0] > cb[1])

    print(f"\n" + "=" * 78)
    print(f" 存活率差 B−A = {d_rate:+.4f}")
    print(f" 步数差   B−A = {d_step:+.1f}")
    print(f" 存活率 CI 重叠吗: {'是 —— 不显著' if overlap else '否 —— 显著'}")
    print(f"   A CI [{ca[0]:.4f}, {ca[1]:.4f}]")
    print(f"   B CI [{cb[0]:.4f}, {cb[1]:.4f}]")

    ok = {}
    ok["① 节能带来更高存活率（显著）"] = bool((d_rate > 0) and (not overlap))
    print(f"\n  {'✅' if ok['① 节能带来更高存活率（显著）'] else '❌'} ① 节能→更耐活 —— "
          f"{'显著' if (d_rate>0 and not overlap) else ('方向对但不显著' if d_rate>0 else '无证据')}")

    json.dump({"A": out["A"], "B": out["B"], "d_rate": float(d_rate),
               "d_step": float(d_step), "overlap": bool(overlap),
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "instinct1_n200.json"), "w"),
              ensure_ascii=False, indent=1)
