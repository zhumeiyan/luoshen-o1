# -*- coding: utf-8 -*-
"""
126c · open 组 fg_raw=+0.00791 且 CI 不含 0 → 不是反射壁，是【瞬态偏差】。
根因假设：ma/mf 零初始化，训练初期 (act-ma) 与 (fb-mf) 同时为大正数，
          协方差估计器在瞬态期系统性为正 → 不相倚也"学会"。
修法：burn-in 前 B 拍只估均值不学习；B 做剂量扫描。
判据：B 增大后 open 的 fg_raw 应 → 0；closed 不受影响。
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16))
T1, T2, DRIP, ETA, TAU, FCH = 1200, 1500, 0.05, 0.004, 50.0, 7


def run(scheme, seed, burn=100, eta=ETA, T1=T1, T2=T2):
    lf = Life5(N=8, seed=seed, fg=0.0)
    rng = np.random.default_rng(seed * 7919 + 13)
    fg = 0.0
    ma = mf = 0.0
    sa = sf = 0.0          # burn-in 累积器
    nb = 0
    for t in range(T1):
        if not lf.alive:
            break
        lf.fg = fg
        lf.step()
        act = lf.log[-1]['avec'][FCH]
        if scheme == 'closed':
            fb = act * (0.8 + 0.4 * rng.random())
        elif scheme == 'open':
            fb = 0.30 * (0.5 + rng.random())
        else:
            fb = 0.0
        lf.E = min(lf.Emax, lf.E + DRIP)
        if t < burn:
            sa += act; sf += fb; nb += 1
            if nb >= burn:                # burn 结束 → 用样本均值初始化滑动均值
                ma = sa / nb; mf = sf / nb
            continue
        ma += (act - ma) / TAU
        mf += (fb - mf) / TAU
        fg += eta * (act - ma) * (fb - mf)
    fg = max(0.0, fg)
    lf.fg = fg
    t0 = lf.t
    while lf.alive and lf.t - t0 < T2:
        lf.step()
    return dict(fg=float(fg), alive=bool(lf.alive), ticks=int(lf.t - t0))


print("=== 126c · burn-in 剂量扫描（瞬态偏差）===")
print(f"{'burn':>6}{'open fg':>12}{'open活':>9}{'closed fg':>12}{'closed活':>11}")
dose = []
for B in [0, 20, 50, 100, 200, 400]:
    row = dict(burn=B)
    for scheme in ['open', 'closed']:
        rs = [run(scheme, sd, burn=B) for sd in SEEDS]
        fg = np.array([r['fg'] for r in rs], float)
        al = np.array([r['alive'] for r in rs], float)
        row[scheme] = dict(fg=float(fg.mean()), sd=float(fg.std(ddof=1)),
                           alive=float(al.mean()), n=int(al.sum()))
    dose.append(row)
    print(f"{B:6d}{row['open']['fg']:12.5f}{row['open']['n']:6d}/16"
          f"{row['closed']['fg']:12.5f}{row['closed']['n']:8d}/16")

print("\n=== burn=100 下的 CI（open 是否真的学不到）===")
for scheme in ['open', 'closed']:
    rs = [run(scheme, sd, burn=100) for sd in SEEDS]
    fg = np.array([r['fg'] for r in rs], float)
    se = fg.std(ddof=1) / np.sqrt(len(fg))
    lo, hi = fg.mean() - 1.96 * se, fg.mean() + 1.96 * se
    print(f"  {scheme:<8} fg={fg.mean():+.5f}  95%CI[{lo:+.5f},{hi:+.5f}]"
          f"  {'含0 → 无习得' if lo * hi < 0 else '不含0 → 真习得'}")

json.dump(dose, open('/data/workspace/luoshen-o1/experiments/exp126_wean2/result126c.json', 'w'),
          ensure_ascii=False, indent=1)
print("\n[saved] result126c.json")
