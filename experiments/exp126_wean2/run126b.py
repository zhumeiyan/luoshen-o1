# -*- coding: utf-8 -*-
"""
126b · 126 里 open 与 variation 组"学到了" fg>0 —— 怀疑是【反射壁假象】。
零漂移随机游走 + 下限 max(0, ·) → 系统性正漂移。
本轮隔离：同时记录 fg_raw（不钳）与 fg_clamped（钳）。
判据：若 open 的 fg_raw 均值 ≈ 0 而 fg_clamped > 0，则"练习有效"是数学假象。
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16))
T1, T2, DRIP, TAU, FCH = 1200, 1500, 0.05, 50.0, 7


def run(scheme, seed, eta=0.004, clamp=True, T1=T1, T2=T2):
    lf = Life5(N=8, seed=seed, fg=0.0)
    rng = np.random.default_rng(seed * 7919 + 13)
    fg_raw = 0.0
    ma = mf = 0.0
    for t in range(T1):
        if not lf.alive:
            break
        lf.fg = max(0.0, fg_raw) if clamp else fg_raw
        lf.step()
        act = lf.log[-1]['avec'][FCH]
        if scheme == 'closed':
            fb = act * (0.8 + 0.4 * rng.random())
        elif scheme == 'open':
            fb = 0.30 * (0.5 + rng.random())
        elif scheme == 'variation':
            fb = 0.0
        else:
            fb = 0.0
        lf.E = min(lf.Emax, lf.E + DRIP)
        if scheme in ('closed', 'open'):
            ma += (act - ma) / TAU
            mf += (fb - mf) / TAU
            fg_raw += eta * (act - ma) * (fb - mf)
        elif scheme == 'variation':
            fg_raw += 0.0008 * rng.normal()
    fg_learned = max(0.0, fg_raw)          # 撤除期一律用钳后值（能力不能为负）
    lf.fg = fg_learned
    t0 = lf.t
    while lf.alive and lf.t - t0 < T2:
        lf.step()
    return dict(fg_raw=float(fg_raw), fg_clamped=float(fg_learned),
                alive=bool(lf.alive), ticks=int(lf.t - t0))


print("=== 126b · 反射壁假象隔离（训练 1200 拍）===")
print(f"{'方案':<12}{'钳':<5}{'fg_raw':>11}{'fg_clamped':>13}{'存活':>9}{'撑(拍)':>9}")
out = {}
for scheme in ['closed', 'open', 'variation']:
    for clamp in (True, False):
        rs = [run(scheme, sd, clamp=clamp) for sd in SEEDS]
        fr = np.array([r['fg_raw'] for r in rs], float)
        fc = np.array([r['fg_clamped'] for r in rs], float)
        al = np.array([r['alive'] for r in rs], float)
        tk = np.array([r['ticks'] for r in rs], float)
        key = f"{scheme}_{'clamp' if clamp else 'raw'}"
        out[key] = dict(fg_raw=float(fr.mean()), fg_raw_sd=float(fr.std(ddof=1)),
                        fg_clamped=float(fc.mean()), alive=float(al.mean()),
                        n=int(al.sum()), ticks=float(tk.mean()))
        print(f"{scheme:<12}{str(clamp):<5}{fr.mean():11.5f}{fc.mean():13.5f}"
              f"{int(al.sum()):6d}/16{tk.mean():9.1f}")

print("\n=== 判据：open / variation 的 fg_raw 是否 ≈ 0 ===")
for scheme in ['open', 'variation']:
    k = f"{scheme}_raw"
    m, sd = out[k]['fg_raw'], out[k]['fg_raw_sd']
    se = sd / np.sqrt(16)
    lo, hi = m - 1.96 * se, m + 1.96 * se
    print(f"  {scheme:<11} fg_raw = {m:+.5f}  95%CI[{lo:+.5f},{hi:+.5f}]"
          f"  {'含0 → 无真实习得' if lo * hi < 0 else '不含0 → 真习得'}")

print("\n=== 反射壁假象强度（fg_clamped - fg_raw，同种子）===")
for scheme in ['closed', 'open', 'variation']:
    a = out[f"{scheme}_clamp"]['fg_clamped']
    b = out[f"{scheme}_raw"]['fg_raw']
    print(f"  {scheme:<11} 钳 {a:.5f}  vs  不钳 {b:+.5f}   差 {a - b:+.5f}")

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp126_wean2/result126b.json', 'w'),
          ensure_ascii=False, indent=1)
print("\n[saved] result126b.json")
