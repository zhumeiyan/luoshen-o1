# -*- coding: utf-8 -*-
"""
127d · 三个自查
【自查1】前兆 AUC=0.000/1.000 完美分离，可疑：可能只是"已经在死"的影子。
         → 只保留 ticks>300 的样本（早期窗口结束时还活着），重算 AUC。
           若仍高 = 真前兆；若塌到 0.5 = 后见之明。
【自查2】坏世界续学后 fg 反而涨 11%（保住率 1.11）—— 疑似 126 的
         【下限反射壁 max(0,...)】第三次复发：零漂移随机游走被下界反弹成正漂移。
         → 加【好世界续学】配对对照：同 seed、同初始 fg、同温度，只有世界不同。
           看的是【差值】，共同的正漂移偏差被抵消。
【自查3】退火速率：太快学不到(fast fg=0.012)，不降不稳(constant 漂移3.3e-4)
         → 扫降温时长，找权衡区间。不调参到想要答案，只报告形状。
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16)); T1, T2 = 1200, 1500
TAU, BURN, FCH, DRIP = 50.0, 100, 7, 0.05
ETA_R = 0.00014
T_HI, T_LO = 3.0, 0.10


def train(seed, eta=ETA_R, noise=0.4, temp_fn=None, T=T1, burn=BURN,
          world='good', rng=None, fg0=0.0):
    if rng is None: rng = np.random.default_rng(seed * 7919 + 13)
    lf = Life5(N=8, seed=seed, fg=0.0)
    fg = fg0; ma = mf = sa = sf = 0.0; hist = []
    for t in range(T):
        if not lf.alive: break
        temp = 1.0 if temp_fn is None else float(temp_fn(t))
        lf.fg = fg; lf.step()
        act = lf.log[-1]['avec'][FCH]
        if world == 'good':  fb = act * (0.8 + noise * temp * rng.random())
        else:                fb = 0.30 * (0.5 + rng.random())     # 不相倚
        lf.E = min(lf.Emax, lf.E + DRIP)
        ma += (act - ma) / TAU; mf += (fb - mf) / TAU
        sa += (act * act - sa) / TAU; sf += (fb * fb - sf) / TAU
        if t >= burn:
            cov = (act - ma) * (fb - mf)
            va = max(sa - ma * ma, 1e-12); vf = max(sf - mf * mf, 1e-12)
            fg = max(0.0, fg + eta * temp * cov / np.sqrt(va * vf))
        hist.append(fg)
    return lf, float(fg), hist


def auc(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    p = x[y == 1]; n = x[y == 0]
    if len(p) == 0 or len(n) == 0: return float('nan')
    return float((np.sum(p[:, None] > n[None, :]) + 0.5 * np.sum(p[:, None] == n[None, :]))
                 / (len(p) * len(n)))


print("=" * 70); print("127d · 三个自查"); print("=" * 70)

# ---------- 自查1：前兆是不是"已经在死" ----------
print("\n=== 自查1：前兆 = 真预警 还是 后见之明 ===")
CASES = [('S1 bleed', 'bleed', 0.04), ('S2 cost', 'cost_mult', 10)]
r1 = {}
for nm, key, lv in CASES:
    recs = []
    for sd in SEEDS:
        lf, f, _ = train(sd)
        lf.fg = f; t0 = lf.t
        b = lv if key == 'bleed' else 0.0
        c = lv if key == 'cost_mult' else 1.0
        tr = []
        while lf.alive and lf.t - t0 < T2:
            lf.step()
            if b: lf.E -= b
            if c != 1.0: lf.E -= (c - 1.0) * 0.004
            tr.append((float(lf.E), float(lf.capacity.mean())))
        recs.append((bool(lf.alive), int(lf.t - t0), tr))
    for tag, filt in [('全部样本', lambda a, tk: True),
                      ('仅活过300拍', lambda a, tk: tk > 300)]:
        lab = []; F = {'E方差': [], 'E斜率': []}
        for alive, tk, tr in recs:
            if not filt(alive, tk): continue
            w = np.array(tr[:200], float)
            if len(w) < 200: continue
            lab.append(0.0 if alive else 1.0)
            F['E方差'].append(w[:, 0].var())
            F['E斜率'].append(np.polyfit(np.arange(len(w)), w[:, 0], 1)[0])
        lab = np.array(lab)
        nd = int((lab == 1).sum()); na = int((lab == 0).sum())
        line = f"  {nm:<9} {tag:<11} 死{nd}/活{na}  "
        if nd == 0 or na == 0:
            line += "样本不足"
            print(line); continue
        r1[f"{nm}|{tag}"] = dict(dead=nd, alive=na)
        for fn, v in F.items():
            A = auc(np.array(v), lab)
            line += f"{fn}={A:.3f}  "
            r1[f"{nm}|{tag}"][fn] = A
        print(line)

# ---------- 自查2：好/坏世界续学配对（抵消反射壁正漂移）----------
print("\n=== 自查2：好/坏世界续学【配对差值】（抵消 max(0,..) 正漂移偏差）===")
def sched(kind, tau_ratio=1.0 / 3):
    if kind == 'cool':      return lambda t: 1.0
    if kind == 'constant':  return lambda t: T_HI
    if kind == 'slow':      return lambda t: T_LO + (T_HI - T_LO) * np.exp(-t / (T1 * tau_ratio))
    if kind == 'fast':      return lambda t: T_LO + (T_HI - T_LO) * max(0.0, 1 - t / (T1 / 10))
    if kind == 'quench':    return lambda t: T_HI if t < T1 * 0.7 else T_LO
    raise ValueError(kind)

print(f"  {'方案':<10}{'练后fg':>9}{'好续Δ':>9}{'坏续Δ':>9}{'差(好-坏)':>11}{'存活':>8}")
r2 = {}
for kind in ['cool', 'constant', 'slow', 'quench']:
    fn = sched(kind)
    f0, dg, db, al = [], [], [], []
    for sd in SEEDS:
        _, f, _ = train(sd, temp_fn=fn)
        f0.append(f)
        outs = {}
        for w in ['good', 'bad']:
            rng = np.random.default_rng(sd * 104729 + 5)
            lf2, f2, _ = train(sd, temp_fn=lambda t: fn(T1 + t), T=500,
                               world=w, rng=rng, fg0=f)
            outs[w] = f2 - f
        dg.append(outs['good']); db.append(outs['bad'])
        lf3, _, _ = train(sd, temp_fn=fn)
        lf3.fg = f + outs['bad']; t0 = lf3.t
        while lf3.alive and lf3.t - t0 < T2: lf3.step()
        al.append(float(lf3.alive))
    dg = np.array(dg); db = np.array(db); d = dg - db
    se = d.std(ddof=1) / np.sqrt(len(d))
    r2[kind] = dict(fg=float(np.mean(f0)), dgood=float(dg.mean()), dbad=float(db.mean()),
                    delta=float(d.mean()), se=float(se),
                    lo=float(d.mean() - 1.96 * se), hi=float(d.mean() + 1.96 * se),
                    alive=float(np.mean(al)))
    print(f"  {kind:<10}{np.mean(f0):9.5f}{dg.mean():+9.5f}{db.mean():+9.5f}"
          f"{d.mean():+11.5f}{int(np.sum(al)):5d}/16")
    print(f"            差值95%CI [{d.mean()-1.96*se:+.5f},{d.mean()+1.96*se:+.5f}] "
          f"{'跨0' if (d.mean()-1.96*se)*(d.mean()+1.96*se) < 0 else '显著'}")

# ---------- 自查3：退火速率剂量 ----------
print("\n=== 自查3：降温时长剂量（不调参到想要答案，只报形状）===")
r3 = []
for ratio in [0.02, 0.05, 0.1, 0.2, 0.333, 0.6, 1.0, 3.0]:
    fn = lambda t, r=ratio: T_LO + (T_HI - T_LO) * np.exp(-t / (T1 * r))
    fgs, dr = [], []
    for sd in SEEDS[:10]:
        _, f, h = train(sd, temp_fn=fn)
        fgs.append(f)
        dr.append(float(np.mean(np.abs(np.diff(h[-300:])))))
    r3.append(dict(ratio=ratio, fg=float(np.mean(fgs)), drift=float(np.mean(dr))))
    print(f"  tau_ratio={ratio:<6} 学到fg={np.mean(fgs):.5f}  漂移={np.mean(dr):.5f}")

json.dump(dict(precursor=r1, continue_pair=r2, anneal_dose=r3),
          open('result127D.json', 'w'), ensure_ascii=False, indent=1)
print("\n[saved] result127D.json")
