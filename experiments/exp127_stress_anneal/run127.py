# -*- coding: utf-8 -*-
"""
127 · 极限测试（A部分）：断奶后的个体能扛多大应力？崩溃前有前兆吗？
预注册： H_A1 五维应力各有【陡峭临界】（非渐变）
         H_A2 崩溃【有】可测前兆：早期窗口指标能预测最终死亡（AUC 明显 >0.5）
纪律：操纵校验 / burn-in 复核 / 共同存活子集 / 判据不饱和 / 效应量+CI 同报
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16))
T1, T2 = 1200, 1500
ETA, TAU = 0.004, 50.0
FCH = 7
DRIP = 0.05


def train(seed, T1=T1, eta=ETA, burn=100, noise=0.4, drought=0.0, rng=None):
    """相倚训练 → 返回 (lf, 学到的fg)"""
    if rng is None:
        rng = np.random.default_rng(seed * 7919 + 13)
    lf = Life5(N=8, seed=seed, fg=0.0)
    fg, ma, mf = 0.0, 0.0, 0.0
    for t in range(T1):
        if not lf.alive:
            break
        lf.fg = fg
        lf.step()
        act = lf.log[-1]['avec'][FCH]
        fb = act * (0.8 + noise * rng.random()) * (1.0 - drought) ** t
        lf.E = min(lf.Emax, lf.E + DRIP)
        ma += (act - ma) / TAU
        mf += (fb - mf) / TAU
        if t >= burn:
            fg = max(0.0, fg + eta * (act - ma) * (fb - mf))
    return lf, float(fg)


def stress_phase(lf, fg, stress, T2=T2):
    """撤除供给 + 施加应力 → 存活 / 撑多久 / 逐拍 trace"""
    lf.fg = fg
    t0 = lf.t
    bleed = stress.get('bleed', 0.0)
    cost = stress.get('cost_mult', 1.0)
    aging = stress.get('aging', 1.0)
    tr = []
    while lf.alive and lf.t - t0 < T2:
        lf.step()
        if bleed: lf.E -= bleed
        if cost != 1.0: lf.E -= (cost - 1.0) * 0.004
        if aging != 1.0: lf.capacity *= aging
        tr.append((float(lf.E), float(lf.capacity.mean())))
    return dict(alive=bool(lf.alive), ticks=int(lf.t - t0), trace=tr)


print("=" * 70)
print("127 · 极限测试")
print("=" * 70)

# ---------- 0a. burn-in 复核（126 假象一的正反两面）----------
print("\n=== 0a. burn-in 复核：burn 对 closed 与 open 的影响相反吗 ===")
def train_with(seed, contingent=True, burn=100):
    rng = np.random.default_rng(seed * 7919 + 13)
    lf = Life5(N=8, seed=seed, fg=0.0)
    fg = ma = mf = 0.0
    for t in range(T1):
        if not lf.alive: break
        lf.fg = fg; lf.step()
        act = lf.log[-1]['avec'][FCH]
        fb = act * (0.8 + 0.4 * rng.random()) if contingent else 0.30 * (0.5 + rng.random())
        lf.E = min(lf.Emax, lf.E + DRIP)
        ma += (act - ma) / TAU; mf += (fb - mf) / TAU
        if t >= burn: fg = max(0.0, fg + ETA * (act - ma) * (fb - mf))
    return float(fg)
for burn in [0, 20, 100]:
    c = np.mean([train_with(s, True, burn) for s in SEEDS[:8]])
    o = np.mean([train_with(s, False, burn) for s in SEEDS[:8]])
    print(f"  burn={burn:<4} closed fg={c:.5f}   open fg={o:.5f}   差={c-o:+.5f}")

# ---------- 0b. 操纵校验（相对差判据，不用 1e-6 的松判据）----------
print("\n=== 0b. 操纵校验：应力是否真的改变了被操纵的量 ===")
_, fg0 = train(0)
base_E = []
lf0, _ = train(1)
r = stress_phase(lf0, 0.10, {})
base_ticks = r['ticks']
for nm, st in [('bleed 0.004', dict(bleed=0.004)), ('cost 3.0', dict(cost_mult=3.0)),
               ('aging 0.999', dict(aging=0.999))]:
    lf, f = train(1)
    r = stress_phase(lf, f, st)
    rel = abs(r['ticks'] - base_ticks) / max(base_ticks, 1)
    print(f"  {nm:<13} ticks {base_ticks:5d} → {r['ticks']:5d}  相对变化 {rel:6.2%} "
          f"{'已操纵' if rel > 0.02 else '★几乎没被操纵'}")

# ---------- A. 五维应力扫描 ----------
print("\n=== A. 应力扫描（撤除供给后，找崩溃临界）===")
STRESS = {
    'S1 失血 bleed':   [('bleed', v) for v in [0.0, 0.001, 0.002, 0.004, 0.008, 0.016]],
    'S2 发烧 cost':    [('cost_mult', v) for v in [1.0, 2.0, 3.0, 4.0, 6.0, 9.0]],
    'S3 老化 aging':   [('aging', v) for v in [1.0, 0.9995, 0.999, 0.998, 0.996, 0.993]],
    'S4 训练期干旱':   [('drought', v) for v in [0.0, 0.0005, 0.001, 0.002, 0.004, 0.008]],
    'S5 训练期噪声':   [('noise', v) for v in [0.4, 1.0, 2.0, 4.0, 8.0, 16.0]],
}
res = {}
for name, levels in STRESS.items():
    rows = []
    for k, v in levels:
        st = {k: v}
        al, tk, fgs = [], [], []
        for sd in SEEDS:
            if k in ('drought', 'noise'):
                lf, f = train(sd, **{('drought' if k == 'drought' else 'noise'): v})
                r = stress_phase(lf, f, {})
            else:
                lf, f = train(sd)
                r = stress_phase(lf, f, st)
            al.append(float(r['alive'])); tk.append(r['ticks']); fgs.append(f)
        rows.append(dict(level=v, alive=float(np.mean(al)), n=int(np.sum(al)),
                         ticks=float(np.mean(tk)), fg=float(np.mean(fgs))))
    res[name] = rows
    print(f"\n  {name}")
    print(f"    {'档位':>10}{'存活':>10}{'撑(拍)':>10}{'学到fg':>10}")
    for r in rows:
        print(f"    {r['level']:>10.4f}{int(r['n']):5d}/16{r['ticks']:10.1f}{r['fg']:10.5f}")
    # 陡峭度：相邻档存活率最大跳变
    jumps = [abs(rows[i+1]['alive'] - rows[i]['alive']) for i in range(len(rows)-1)]
    print(f"    最大相邻跳变 = {max(jumps):.3f}  "
          f"{'★陡峭(阈值型)' if max(jumps) >= 0.5 else '渐变'}")

json.dump(res, open('result127A.json', 'w'), ensure_ascii=False, indent=1)
print("\n[saved] result127A.json")
