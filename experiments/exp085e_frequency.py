# -*- coding: utf-8 -*-
"""
实验 085e · 同样总能量，"偶尔看一眼" vs "被持续投喂"
------------------------------------------------------------------
085d 的副产品：receipt 相同(=3.0)时
   (amp=0.02, 开门150次) drift=0.114  ← 少次·高幅·像"去看一眼"
   (amp=0.005,开门600次) drift=0.183  ← 多次·低幅·像"被持续投喂"
→ 提示：决定后果的不只是总量，还有【接收的时间形态】。

085e 正式检验：固定 receipt，只变 (amp, 开门次数) 的组合
   sparse : p=0.25（150 次，高幅）
   dense  : p=1.00（600 次，低幅）
   二者 receipt 严格相同，信息内容相同（同一个真实世界向量）
   同 seed 配对 + 共同存活子集 + bootstrap CI
"""
import json, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'core')); sys.path.insert(0, ROOT)
from core.life5 import Life5

STEPS = 600
SEEDS = list(range(32))
N = 8
WCH = [0, 1, 2]
OUT = os.path.join(ROOT, 'experiments', 'result_085e.json')
_w = json.load(open(os.path.join(ROOT, 'evidence', 'raw_data', 'world_085b.json')))
WV = np.array(_w['world'], float).mean(axis=0)


def capn(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return c / c.mean()


def sim(seed, n_open, amp):
    rng = np.random.default_rng(seed * 977 + 13)
    m = np.zeros(STEPS, bool)
    if n_open > 0:
        m[rng.choice(STEPS, n_open, replace=False)] = True
    lf = Life5(N=N, seed=seed, ratio=0.45, sigma_in=0.10)
    for t in range(STEPS):
        push = np.zeros(N)
        if m[t]: push[WCH] = amp * WV
        lf.net_push = push
        lf.step()
        if not lf.alive: break
    return lf


def boot_ci(d, B=6000, seed=11):
    d = np.asarray(d, float)
    if len(d) < 2: return float('nan'), float('nan'), float('nan')
    r = np.random.default_rng(seed)
    bs = np.array([r.choice(d, len(d), replace=True).mean() for _ in range(B)])
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    print("=" * 68)
    print("实验 085e · 同样总能量：偶尔看一眼 vs 被持续投喂")
    print("=" * 68)
    base = {s: sim(s, 0, 0.0) for s in SEEDS}
    bal = [s for s in SEEDS if base[s].alive]
    print(f"[基线] 无感官存活 {len(bal)}/{len(SEEDS)}")

    R_grid = [(1.5, 150, 600), (3.0, 150, 600), (6.0, 150, 600)]
    res = []
    for R, n_sparse, n_dense in R_grid:
        a_sparse, a_dense = R / n_sparse, R / n_dense
        S = {s: sim(s, n_sparse, a_sparse) for s in bal}
        D = {s: sim(s, n_dense, a_dense) for s in bal}
        common = [s for s in bal if S[s].alive and D[s].alive]
        dd = [float(np.mean(np.abs(capn(S[s]) - capn(base[s])))) -
              float(np.mean(np.abs(capn(D[s]) - capn(base[s])))) for s in common]
        m, lo, hi = boot_ci(dd)
        dS = float(np.mean([np.mean(np.abs(capn(S[s]) - capn(base[s]))) for s in common])) if common else float('nan')
        dD = float(np.mean([np.mean(np.abs(capn(D[s]) - capn(base[s]))) for s in common])) if common else float('nan')
        row = dict(receipt=R, amp_sparse=a_sparse, amp_dense=a_dense,
                   n_sparse=n_sparse, n_dense=n_dense,
                   alive_sparse=int(sum(S[s].alive for s in bal)),
                   alive_dense=int(sum(D[s].alive for s in bal)),
                   n_base=len(bal), n_common=len(common),
                   drift_sparse=dS, drift_dense=dD,
                   delta=m, ci_lo=lo, ci_hi=hi)
        res.append(row)
        flag = "★显著" if (lo > 0 or hi < 0) else "跨0"
        print(f"\n  receipt={R}  sparse(amp={a_sparse:.4f}×{n_sparse}次) vs "
              f"dense(amp={a_dense:.4f}×{n_dense}次)")
        print(f"    存活 sparse={row['alive_sparse']}/{len(bal)}  "
              f"dense={row['alive_dense']}/{len(bal)}  共同={len(common)}")
        print(f"    drift sparse={dS:.5f}  dense={dD:.5f}")
        print(f"    Δ(sparse-dense)={m:+.5f} CI[{lo:+.5f},{hi:+.5f}] {flag}")

    json.dump(dict(rows=res, common_note="共同存活子集，防死亡筛选"),
              open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"\n[OK] {OUT}")


if __name__ == '__main__':
    main()
