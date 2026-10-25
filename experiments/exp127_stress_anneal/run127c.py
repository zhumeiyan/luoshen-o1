# -*- coding: utf-8 -*-
"""
127c · 前兆(用混合档) + 退火
【前兆修正】127b 选档失败：三档全是「全死」或「全活」，无混合样本 → AUC 恒 nan。
           本轮先扫出存活率≈50%的档再做 AUC。
【退火】预注册 H_B：退火的价值是【稳】不是【大】。
   真正的"固化"检验不是看 fg 多大，而是看【降温后还改不改得动】：
   → 退火/恒温之后，进入【坏世界】继续学习 500 拍，看 fg 被改写多少。
     退火好的：学习率已冷，fg 保住；恒温高温的：继续被坏经验改写，fg 塌陷。
   阴性对照：若慢/快/淬火三档无差异 → 说明"退火速率"这个变量根本没起作用。
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16)); T1, T2 = 1200, 1500
TAU, BURN, FCH, DRIP = 50.0, 100, 7, 0.05
ETA_R = 0.00014
T_HI, T_LO = 3.0, 0.10


def train(seed, eta=ETA_R, noise=0.4, normalized=True, temp_fn=None, burn=BURN,
          T=T1, bad_world=False, rng=None):
    """bad_world=True：世界不回应（不相倚），用来检验能力是否被改写"""
    if rng is None: rng = np.random.default_rng(seed * 7919 + 13)
    lf = Life5(N=8, seed=seed, fg=0.0)
    fg = ma = mf = sa = sf = 0.0
    hist = []
    for t in range(T):
        if not lf.alive: break
        temp = 1.0 if temp_fn is None else float(temp_fn(t))
        lf.fg = fg; lf.step()
        act = lf.log[-1]['avec'][FCH]
        if bad_world:
            fb = 0.30 * (0.5 + rng.random())          # 相继不相倚
        else:
            fb = act * (0.8 + noise * temp * rng.random())
        lf.E = min(lf.Emax, lf.E + DRIP)
        ma += (act - ma) / TAU; mf += (fb - mf) / TAU
        sa += (act * act - sa) / TAU; sf += (fb * fb - sf) / TAU
        if t >= burn:
            cov = (act - ma) * (fb - mf)
            if normalized:
                va = max(sa - ma * ma, 1e-12); vf = max(sf - mf * mf, 1e-12)
                cov = cov / np.sqrt(va * vf)
            fg = max(0.0, fg + eta * temp * cov)
        hist.append(fg)
    return lf, float(fg), hist


def wean(lf, fg, T2=T2):
    lf.fg = fg; t0 = lf.t
    while lf.alive and lf.t - t0 < T2: lf.step()
    return bool(lf.alive), int(lf.t - t0)


def auc(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    pos = x[y == 1]; neg = x[y == 0]
    if len(pos) == 0 or len(neg) == 0: return float('nan')
    return float((np.sum(pos[:, None] > neg[None, :]) + 0.5 * np.sum(pos[:, None] == neg[None, :]))
                 / (len(pos) * len(neg)))


print("=" * 70); print("127c · 前兆(混合档) + 退火"); print("=" * 70)

# ---------- 1. 先扫出存活率≈50%的档 ----------
def surv_at(stress):
    lfs = []
    for sd in SEEDS:
        lf, f, _ = train(sd)
        lfs.append((lf, f))
    al = []
    for lf, f in lfs:
        lf.fg = f; t0 = lf.t
        b = stress.get('bleed', 0.0); c = stress.get('cost_mult', 1.0); a = stress.get('aging', 1.0)
        while lf.alive and lf.t - t0 < T2:
            lf.step()
            if b: lf.E -= b
            if c != 1.0: lf.E -= (c - 1.0) * 0.004
            if a != 1.0: lf.capacity *= a
        al.append(float(lf.alive))
    return float(np.mean(al))

print("\n=== 1. 找 50% 崩溃档 ===")
cand = {'S1 bleed': [0.03, 0.04, 0.05, 0.06],
        'S2 cost': [10, 13, 15, 17],
        'S3 aging': [0.7, 0.5, 0.3, 0.2, 0.1]}
picks = {}
for nm, vs in cand.items():
    key = {'S1 bleed': 'bleed', 'S2 cost': 'cost_mult', 'S3 aging': 'aging'}[nm]
    rs = [(v, surv_at({key: v})) for v in vs]
    print(f"  {nm}: " + "  ".join(f"{v}→{a:.2f}" for v, a in rs))
    best = min(rs, key=lambda r: abs(r[1] - 0.5))
    picks[nm] = (key, best[0], best[1])
    print(f"    选 {key}={best[0]} (存活 {best[1]:.2f})")
json.dump({k: [v[0], v[1], v[2]] for k, v in picks.items()}, open('picks.json', 'w'))

# ---------- 2. 前兆 AUC（混合档）----------
print("\n=== 2. 前兆：早期窗口预测最终崩溃（AUC）===")
pre = {}
for nm, (key, lv, sr) in picks.items():
    recs = []
    for sd in SEEDS:
        lf, f, _ = train(sd)
        lf.fg = f; t0 = lf.t
        b = key == 'bleed' and lv or 0.0
        c = lv if key == 'cost_mult' else 1.0
        a = lv if key == 'aging' else 1.0
        tr = []
        while lf.alive and lf.t - t0 < T2:
            lf.step()
            if b: lf.E -= b
            if c != 1.0: lf.E -= (c - 1.0) * 0.004
            if a != 1.0: lf.capacity *= a
            tr.append((float(lf.E), float(lf.capacity.mean())))
        recs.append((bool(lf.alive), tr))
    lab = []; F = {'E均值': [], 'E方差': [], 'E斜率': []}
    for alive, tr in recs:
        w = np.array(tr[:200], float)
        if len(w) < 50: continue
        lab.append(0.0 if alive else 1.0)     # 1 = 最终死亡
        F['E均值'].append(w[:, 0].mean()); F['E方差'].append(w[:, 0].var())
        F['E斜率'].append(np.polyfit(np.arange(len(w)), w[:, 0], 1)[0])
    lab = np.array(lab)
    print(f"  {nm} 档={lv}  死{(lab==1).sum():.0f}/活{(lab==0).sum():.0f}")
    pre[nm] = dict(level=lv, dead=int((lab == 1).sum()))
    if (lab == 1).sum() == 0 or (lab == 0).sum() == 0:
        print("     ★仍无混合样本，AUC 不可算")
        continue
    for fn, v in F.items():
        A = auc(np.array(v), lab)
        dev = abs(A - 0.5)
        direc = '高→死' if A > 0.5 else '高→活'
        print(f"     {fn:<6} AUC={A:.3f} ({direc})  "
              f"{'★前兆' if dev >= 0.25 else ('弱' if dev >= 0.1 else '无')}")
        pre[nm][fn] = A

# ---------- 3. 退火 ----------
print("\n=== 3. 退火：降温后还改不改得动 ===")
def sched(kind):
    if kind == 'constant':  return lambda t: T_HI
    if kind == 'cool':      return lambda t: 1.0            # 常温对照（无高温）
    if kind == 'slow':      return lambda t: T_LO + (T_HI - T_LO) * np.exp(-t / (T1 / 3))
    if kind == 'fast':      return lambda t: T_LO + (T_HI - T_LO) * max(0.0, 1 - t / (T1 / 10))
    if kind == 'quench':    return lambda t: T_HI if t < T1 * 0.7 else T_LO
    raise ValueError(kind)

print(f"  {'方案':<10}{'练后fg':>9}{'漂移':>9}{'坏世界后fg':>12}{'保住率':>9}{'存活':>8}")
rows = {}
for kind in ['cool', 'constant', 'slow', 'fast', 'quench']:
    fn = sched(kind)
    fgs, drifts, after, alives = [], [], [], []
    for sd in SEEDS:
        lf, f, hist = train(sd, temp_fn=fn)
        # 漂移 = 最后 300 拍 |Δfg|
        drift = float(np.mean(np.abs(np.diff(hist[-300:])))) if len(hist) > 300 else float('nan')
        # 坏世界继续学习 500 拍（温度已冷，但学习律仍在跑）
        fn2 = (lambda t: fn(T1 + t))
        lf2, f2, _ = train(sd, temp_fn=lambda t: fn(T1 + t), T=500,
                           bad_world=True, rng=np.random.default_rng(sd * 104729 + 5))
        # 注意：上面是新个体，应接续。改为在同一 lf 上续跑：
        fgs.append(f); drifts.append(drift)
        # 同一 lf 续跑坏世界
        rng = np.random.default_rng(sd * 104729 + 5)
        ma = mf = sa = sf = 0.0; g = f
        for t in range(500):
            if not lf.alive: break
            temp = float(fn(T1 + t))
            lf.fg = g; lf.step()
            act = lf.log[-1]['avec'][FCH]
            fb = 0.30 * (0.5 + rng.random())
            lf.E = min(lf.Emax, lf.E + DRIP)
            ma += (act - ma) / TAU; mf += (fb - mf) / TAU
            sa += (act * act - sa) / TAU; sf += (fb * fb - sf) / TAU
            cov = (act - ma) * (fb - mf)
            va = max(sa - ma * ma, 1e-12); vf = max(sf - mf * mf, 1e-12)
            g = max(0.0, g + ETA_R * temp * cov / np.sqrt(va * vf))
        after.append(g)
        a, tk = wean(lf, g)
        alives.append(float(a))
    rows[kind] = dict(fg=float(np.mean(fgs)), drift=float(np.mean(drifts)),
                      after=float(np.mean(after)),
                      keep=float(np.mean(after) / max(np.mean(fgs), 1e-12)),
                      alive=float(np.mean(alives)))
    r = rows[kind]
    print(f"  {kind:<10}{r['fg']:9.5f}{r['drift']:9.5f}{r['after']:12.5f}"
          f"{r['keep']:9.2f}{int(np.sum(alives)):5d}/16")

print("\n  退火速率对照（阴性检验：若三者无差异 → 退火变量没起作用）")
for a, b in [('slow', 'constant'), ('fast', 'constant'), ('quench', 'constant'),
             ('slow', 'quench'), ('slow', 'fast')]:
    d = rows[a]['keep'] - rows[b]['keep']
    print(f"    {a:<9} vs {b:<9} 保住率差 {d:+.3f}")
json.dump(dict(precursor=pre, anneal=rows), open('result127C.json', 'w'),
          ensure_ascii=False, indent=1)
print("\n[saved] result127C.json")
