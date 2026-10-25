# -*- coding: utf-8 -*-
"""
实验 085d · "被冲垮"的直接度量：结构漂移 drift
------------------------------------------------------------------
085c 的 Δskew 方向不一致（p=0.25 负 / p=0.5,0.75 正），且 active 存活更低、
共同子集只剩 6~7 → 那组阳性不可信，不作结论。

085d 换一个【不受死亡筛选影响】的指标：
  drift(seed) = mean_ch | cap_n(条件) - cap_n(无感官基线) |   同 seed 配对
  = 外部输入把我的内在结构推离"原本的自己"多远 —— 这才是"被冲垮"的直译。

  自变量：接收总量 receipt = amp × 开门次数（连续量，不是分类）
  预期 H1：drift 随 receipt 单调上升
  另报存活率（同样不受筛选影响）
"""
import json, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'core')); sys.path.insert(0, ROOT)
from core.life5 import Life5
from scipy.stats import spearmanr

STEPS = 600
SEEDS = list(range(16))
N = 8
WCH = [0, 1, 2]
OUT = os.path.join(ROOT, 'experiments', 'result_085d.json')
_w = json.load(open(os.path.join(ROOT, 'evidence', 'raw_data', 'world_085b.json')))
WV = np.array(_w['world'], float).mean(axis=0)


def capn(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return c / c.mean()


def sim(seed, mask, amp):
    lf = Life5(N=N, seed=seed, ratio=0.45, sigma_in=0.10)
    for t in range(STEPS):
        push = np.zeros(N)
        if t < len(mask) and mask[t]:
            push[WCH] = amp * WV
        lf.net_push = push
        lf.step()
        if not lf.alive: break
    return lf


def main():
    print("=" * 66)
    print("实验 085d · 结构漂移 drift vs 接收总量")
    print("=" * 66)
    base = {s: sim(s, np.zeros(STEPS, bool), 0.0) for s in SEEDS}
    balive = [s for s in SEEDS if base[s].alive]
    print(f"[基线] 无感官 存活 {len(balive)}/{len(SEEDS)}")

    rows = []
    for amp in (0.005, 0.01, 0.02, 0.04, 0.08):
        for p in (0.25, 0.5, 1.0):
            nT = int(round(p * STEPS))
            dr, alive_n = [], 0
            for s in balive:
                rng = np.random.default_rng(s * 977 + 13)
                m = np.zeros(STEPS, bool)
                m[rng.choice(STEPS, nT, replace=False)] = True
                lf = sim(s, m, amp)
                if lf.alive:
                    alive_n += 1
                    dr.append(float(np.mean(np.abs(capn(lf) - capn(base[s])))))
            rows.append(dict(amp=amp, p=p, receipt=amp * nT, n_open=nT,
                             alive=alive_n, n_base=len(balive),
                             drift=float(np.mean(dr)) if dr else float('nan'),
                             n_drift=len(dr)))
            print(f"  amp={amp:<6} p={p:<5} 开门{nT:>3} receipt={amp*nT:>6.2f}  "
                  f"存活 {alive_n:>2}/{len(balive)}  drift="
                  f"{np.mean(dr) if dr else float('nan'):.5f} (n={len(dr)})")

    rc = np.array([r['receipt'] for r in rows])
    df = np.array([r['drift'] for r in rows])
    al = np.array([r['alive'] for r in rows])
    ok = ~np.isnan(df)
    rho_d, pv_d = spearmanr(rc[ok], df[ok])
    rho_a, pv_a = spearmanr(rc[ok], al[ok])
    print(f"\n[H1] drift ~ receipt : Spearman rho={rho_d:+.4f}  p={pv_d:.5f}")
    print(f"[H2] 存活 ~ receipt  : Spearman rho={rho_a:+.4f}  p={pv_a:.5f}")
    json.dump(dict(rows=rows, rho_drift=float(rho_d), p_drift=float(pv_d),
                   rho_alive=float(rho_a), p_alive=float(pv_a)),
              open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"\n[OK] {OUT}")


if __name__ == '__main__':
    main()
