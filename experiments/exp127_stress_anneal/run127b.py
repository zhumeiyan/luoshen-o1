# -*- coding: utf-8 -*-
"""127b · 极限测试修正版：P1 打到崩溃 / P2 学习律归一化 / P3 老化非单调 / 前兆AUC"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16)); T1, T2 = 1200, 1500
TAU, BURN, FCH, DRIP = 50.0, 100, 7, 0.05
ETA_R = 0.00014        # 标定：归一化版在 noise=0.4 处 ≈ 原基线 0.103


def train(seed, eta=0.004, burn=BURN, noise=0.4, drought=0.0, normalized=False,
          rng=None, temp_fn=None):
    if rng is None: rng = np.random.default_rng(seed * 7919 + 13)
    lf = Life5(N=8, seed=seed, fg=0.0)
    fg = ma = mf = sa = sf = 0.0
    for t in range(T1):
        if not lf.alive: break
        temp = 1.0 if temp_fn is None else float(temp_fn(t))
        lf.fg = fg; lf.step()
        act = lf.log[-1]['avec'][FCH]
        fb = act * (0.8 + noise * temp * rng.random()) * (1.0 - drought) ** t
        lf.E = min(lf.Emax, lf.E + DRIP)
        ma += (act - ma) / TAU; mf += (fb - mf) / TAU
        sa += (act * act - sa) / TAU; sf += (fb * fb - sf) / TAU
        if t >= burn:
            cov = (act - ma) * (fb - mf)
            if normalized:
                va = max(sa - ma * ma, 1e-12); vf = max(sf - mf * mf, 1e-12)
                cov = cov / np.sqrt(va * vf)
            fg = max(0.0, fg + eta * temp * cov)
    return lf, float(fg)


def stress_phase(lf, fg, stress, T2=T2):
    lf.fg = fg; t0 = lf.t
    b = stress.get('bleed', 0.0); c = stress.get('cost_mult', 1.0); a = stress.get('aging', 1.0)
    tr = []
    while lf.alive and lf.t - t0 < T2:
        lf.step()
        if b: lf.E -= b
        if c != 1.0: lf.E -= (c - 1.0) * 0.004
        if a != 1.0: lf.capacity *= a
        tr.append((float(lf.E), float(lf.capacity.mean())))
    return dict(alive=bool(lf.alive), ticks=int(lf.t - t0), trace=tr)


def auc(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    pos = x[y == 1]; neg = x[y == 0]
    if len(pos) == 0 or len(neg) == 0: return float('nan')
    d = np.sign(1.0)  # 假设指标越高越危险
    return float((np.sum(pos[:, None] > neg[None, :]) + 0.5 * np.sum(pos[:, None] == neg[None, :]))
                 / (len(pos) * len(neg)))


out = {}
print("=" * 70); print("127b · 极限测试修正版"); print("=" * 70)

# ---------- P2：归一化后，噪声还"帮助"学习吗 ----------
print("\n=== P2. 学习律归一化后重测 S5 噪声 ===")
print(f"  {'noise':>7}{'原版fg':>10}{'归一版fg':>10}")
p2 = {}
for nz in [0.4, 1.0, 2.0, 4.0, 8.0, 16.0]:
    a = np.mean([train(s, noise=nz)[1] for s in SEEDS[:8]])
    b = np.mean([train(s, eta=ETA_R, noise=nz, normalized=True)[1] for s in SEEDS[:8]])
    p2[nz] = (a, b)
    print(f"  {nz:>7.1f}{a:10.5f}{b:10.5f}")
out['P2'] = p2
print("  原版：噪声↑ → fg↑（尺度泄漏）  归一版：噪声↑ → fg",
      "↓(正确)" if p2[16.0][1] < p2[0.4][1] else "仍↑(未修复)")

# ---------- P1：应力加到真崩溃 ----------
print("\n=== P1. 应力扫描（加大档位，直到崩溃）===")
BIG = {
    'S1 失血': [('bleed', v) for v in [0.0, 0.01, 0.02, 0.04, 0.06, 0.10, 0.16, 0.24]],
    'S2 发烧': [('cost_mult', v) for v in [1, 5, 10, 20, 35, 50, 70, 100]],
    'S3 老化': [('aging', v) for v in [1.0, 0.999, 0.995, 0.99, 0.98, 0.96, 0.93, 0.90]],
}
for name, levels in BIG.items():
    rows = []
    for k, v in levels:
        al, tk, cap = [], [], []
        for sd in SEEDS:
            lf, f = train(sd)
            r = stress_phase(lf, f, {k: v})
            al.append(float(r['alive'])); tk.append(r['ticks'])
            cap.append(float(lf.capacity.mean()))
        rows.append(dict(level=v, alive=float(np.mean(al)), n=int(np.sum(al)),
                         ticks=float(np.mean(tk)), cap=float(np.mean(cap))))
    out[name] = rows
    print(f"\n  {name}")
    print(f"    {'档位':>9}{'存活':>9}{'撑(拍)':>9}{'末容量':>9}")
    for r in rows:
        print(f"    {r['level']:>9.4f}{int(r['n']):4d}/16{r['ticks']:9.1f}{r['cap']:9.4f}")
    j = max(abs(rows[i + 1]['alive'] - rows[i]['alive']) for i in range(len(rows) - 1))
    print(f"    最大相邻跳变={j:.3f} {'★陡峭' if j >= 0.5 else '渐变'}")

# ---------- P3：老化非单调？ ----------
print("\n=== P3. 老化为什么反而续命：是不是'削减需求' ===")
p3 = []
for v in [1.0, 0.99, 0.96, 0.93, 0.90, 0.85, 0.80]:
    al = []
    caps = []
    for sd in SEEDS[:8]:
        lf, f = train(sd)
        r = stress_phase(lf, f, {'aging': v})
        al.append(float(r['alive'])); caps.append(float(lf.capacity.mean()))
    p3.append(dict(level=v, alive=float(np.mean(al)), cap=float(np.mean(caps))))
    print(f"  aging={v:<6} 存活 {int(np.sum(al))}/8  末容量 {np.mean(caps):.4f}")
out['P3'] = p3

# ---------- 前兆 AUC ----------
print("\n=== 前兆：早期窗口能预测最终崩溃吗（AUC）===")
LC = {}
for name, k, lv in [('S1', 'bleed', 0.10), ('S2', 'cost_mult', 50), ('S3', 'aging', 0.90)]:
    recs = []
    for sd in SEEDS:
        lf, f = train(sd)
        r = stress_phase(lf, f, {k: lv})
        recs.append((r['alive'], r['trace']))
    # 早期窗口 = 前 200 拍
    feats = {'E均值': [], 'E方差': [], 'E斜率': [], '容量斜率': []}
    labels = []
    for alive, tr in recs:
        w = np.array(tr[:200], float)
        if len(w) < 50: continue
        labels.append(1.0 if not alive else 0.0)
        feats['E均值'].append(w[:, 0].mean()); feats['E方差'].append(w[:, 0].var())
        feats['E斜率'].append(np.polyfit(np.arange(len(w)), w[:, 0], 1)[0])
        feats['容量斜率'].append(np.polyfit(np.arange(len(w)), w[:, 1], 1)[0])
    labels = np.array(labels)
    print(f"  {name} (档={lv})  死亡 {(labels == 1).sum():.0f} / 存活 {(labels == 0).sum():.0f}")
    LC[name] = dict(level=lv, n_dead=int((labels == 1).sum()), n_alive=int((labels == 0).sum()))
    for fn, v in feats.items():
        A = auc(np.array(v), labels)
        print(f"     {fn:<8} AUC={A:.3f}  {'★有前兆' if A > 0.75 else ('无' if A < 0.6 else '弱')}")
        LC[name][fn] = A
out['precursor'] = LC
json.dump(out, open('result127B.json', 'w'), ensure_ascii=False, indent=1)
print("\n[saved] result127B.json")
