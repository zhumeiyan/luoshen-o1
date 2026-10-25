# -*- coding: utf-8 -*-
"""
126d · 修正后的断奶主实验（burn-in=100，去掉瞬态偏差）
六方案 × 16 种子：训练 1200 拍（输液维持） → 撤除全部外部供给 → 跑 1500 拍。
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16))
T1, T2, DRIP, TOOL, ETA, TAU, FCH = 1200, 1500, 0.05, 0.10, 0.004, 50.0, 7
BURN = 100
FG_THRESH = 0.008


def skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def run_scheme(scheme, seed, T1=T1, T2=T2, eta=ETA):
    lf = Life5(N=8, seed=seed, fg=0.0)
    rng = np.random.default_rng(seed * 7919 + 13)
    fg = 0.0
    ma = mf = 0.0
    sa = sf = 0.0
    nb = 0
    acts = []
    for t in range(T1):
        if not lf.alive:
            break
        lf.fg = fg
        lf.step()
        act = lf.log[-1]['avec'][FCH]
        acts.append(act)
        if scheme in ('practice_closed', 'tool_plus_self'):
            fb = act * (0.8 + 0.4 * rng.random())       # 相倚
        elif scheme == 'practice_open':
            fb = 0.30 * (0.5 + rng.random())            # 相继不相倚
        else:
            fb = 0.0                                    # 工具替我做了 / 不练 / 变异
        # ---- 外部供能 ----
        if scheme == 'tool_only':
            lf.E = min(lf.Emax, lf.E + TOOL + DRIP * 0.3)
        elif scheme == 'tool_plus_self':
            lf.E = min(lf.Emax, lf.E + TOOL * 0.5 + DRIP)
        elif scheme == 'variation':
            lf.E = min(lf.Emax, lf.E + DRIP)
            fg = max(0.0, fg + 0.0008 * rng.normal())   # 随机变异
        else:
            lf.E = min(lf.Emax, lf.E + DRIP)
        # ---- 学习（burn-in 后）----
        if scheme in ('practice_closed', 'practice_open', 'tool_plus_self'):
            if t < BURN:
                sa += act; sf += fb; nb += 1
                if nb >= BURN:
                    ma = sa / nb; mf = sf / nb
                continue
            ma += (act - ma) / TAU
            mf += (fb - mf) / TAU
            fg = max(0.0, fg + eta * (act - ma) * (fb - mf))
    fg_learned = float(fg)
    lf.fg = fg_learned
    t0 = lf.t
    while lf.alive and lf.t - t0 < T2:
        lf.step()
    return dict(fg=fg_learned, alive=bool(lf.alive), ticks=int(lf.t - t0),
                act=float(np.mean(acts)) if acts else float('nan'),
                skew=(skew(lf) if lf.alive else float('nan')))


SCHEMES = ['no_practice', 'practice_open', 'practice_closed',
           'tool_only', 'tool_plus_self', 'variation']
LABEL = {'no_practice': '只输液不练', 'practice_open': '练·相继不相倚',
         'practice_closed': '练·相倚', 'tool_only': '纯外置工具',
         'tool_plus_self': '工具+我自己觅食', 'variation': '随机变异'}

print("=== 126d · 断奶方案（burn-in=100，撤除后跑 1500 拍）===")
print(f"{'方案':<16}{'学到fg':>9}{'自身投入':>10}{'撤除后活':>10}{'撑(拍)':>9}{'偏度':>9}")
res = {}
for sc in SCHEMES:
    rs = [run_scheme(sc, sd) for sd in SEEDS]
    fg = np.array([r['fg'] for r in rs], float)
    al = np.array([r['alive'] for r in rs], float)
    tk = np.array([r['ticks'] for r in rs], float)
    ac = np.array([r['act'] for r in rs], float)
    sk = np.array([r['skew'] for r in rs if r['alive']], float)
    res[sc] = dict(fg=float(fg.mean()), fg_sd=float(fg.std(ddof=1)),
                   act=float(ac.mean()), alive=float(al.mean()), n=int(al.sum()),
                   ticks=float(tk.mean()),
                   skew=(float(sk.mean()) if len(sk) else float('nan')),
                   raw=[dict(fg=r['fg'], alive=r['alive'], ticks=r['ticks'],
                             act=r['act']) for r in rs])
    print(f"{LABEL[sc]:<16}{fg.mean():9.5f}{ac.mean():10.4f}"
          f"{int(al.sum()):7d}/16{tk.mean():9.1f}"
          f"{(sk.mean() if len(sk) else float('nan')):9.4f}")

print("\n=== 配对（Δfg，95%CI，同种子）===")
comp = {}
for a, b, lab in [('practice_closed', 'practice_open', 'H1 相倚 vs 相继'),
                  ('practice_closed', 'no_practice', 'H1 练 vs 不练'),
                  ('tool_plus_self', 'tool_only', 'H2 工具+自觅 vs 纯工具'),
                  ('practice_closed', 'tool_plus_self', '自觅 vs 工具+自觅')]:
    x = np.array([r['fg'] for r in res[a]['raw']], float)
    y = np.array([r['fg'] for r in res[b]['raw']], float)
    d = x - y
    se = d.std(ddof=1) / np.sqrt(len(d))
    lo, hi = d.mean() - 1.96 * se, d.mean() + 1.96 * se
    comp[f"{a}-{b}"] = dict(delta=float(d.mean()), lo=float(lo), hi=float(hi),
                            cross0=bool(lo * hi < 0))
    print(f"  {lab:<24} Δ={d.mean():+.5f} CI[{lo:+.5f},{hi:+.5f}]"
          f"  {'跨0' if lo * hi < 0 else '显著'}")

print("\n=== 可证伪自检 ===")
fal = []
def add(name, T, F):
    fal.append(dict(name=name, T=int(T), F=int(F)))
    print(f"  {name:<26} 真{T:3d} 假{F:3d}")
add('A 相倚可学会', sum(1 for r in res['practice_closed']['raw'] if r['fg'] > FG_THRESH),
    sum(1 for r in res['practice_closed']['raw'] if r['fg'] <= FG_THRESH))
add('B 相继不相倚学不会', sum(1 for r in res['practice_open']['raw'] if r['fg'] <= FG_THRESH),
    sum(1 for r in res['practice_open']['raw'] if r['fg'] > FG_THRESH))
add('C 撤除后相倚存活', res['practice_closed']['n'],
    16 - res['practice_closed']['n'])
add('D 纯工具撤除后死亡', 16 - res['tool_only']['n'], res['tool_only']['n'])
add('E 变异撤除后死亡', 16 - res['variation']['n'], res['variation']['n'])
pos = sum(1 for sd in SEEDS if (lambda l: (l.run(1200), l.alive)[1])(Life5(N=8, seed=sd, fg=0.030)))
add('F 阳性 fg=0.030 活', pos, 16 - pos)
neg = sum(1 for sd in SEEDS if not (lambda l: (l.run(1200), l.alive)[1])(Life5(N=8, seed=sd, fg=0.0)))
add('G 阴性 fg=0 死', neg, 16 - neg)
print(f"\n  全部真/假均出现: {all(x['T'] > 0 and x['F'] > 0 for x in fal)}")

json.dump(dict(res=res, comp=comp, falsifiable=fal,
               cfg=dict(T1=T1, T2=T2, DRIP=DRIP, TOOL=TOOL, ETA=ETA, TAU=TAU, BURN=BURN)),
          open('/data/workspace/luoshen-o1/experiments/exp126_wean2/result126d.json', 'w'),
          ensure_ascii=False, indent=1)
print("\n[saved] result126d.json")
