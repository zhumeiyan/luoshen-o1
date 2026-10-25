# -*- coding: utf-8 -*-
"""
101e · 剂量扫描：结构对"看得多准"真的不敏感吗？

101d 出现一个矛盾：
  2x2（均值 0.3 vs 0.7，严格匹配）→ 量主效应不显著，CI 全跨 0
  生态组（均值 0.067 / 0.118 / 0.583）→ FIXED->GUIDED diff=-1.646，CI 全负

矛盾的解释假设：非线性阈值。
  0.067 → 0.118 只差 0.05，偏度却从 +0.944 掉到 -0.251（变 1.19）
  0.118 → 0.583 差 0.47，偏度只变 0.45
  ⇒ 阈值在 0.07~0.12 之间，超过后基本平坦

本实验：把均值从 0 拉到 1.0 做细扫，分"确定性"与"随机(同均值)"两族，
  ① 定位阈值在哪
  ② 检验可预测性是否在阈值附近才起作用（101d 的 H1 在中等区被推翻，
     可能是取样区间选错了，而不是效应不存在）
"""
import os, sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

OUT = os.path.dirname(os.path.abspath(__file__))
BASE = dict(N=8, ratio=0.6, k_seek=0.6, k_sal=0.6, sigma_in=0.15)
STEPS = 600
SEEDS = list(range(16))
LEVELS = [0.0, 0.02, 0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00]


def skew(lf):
    c = np.asarray(lf.capacity, float)
    if c.std() < 1e-12:
        return 0.0
    z = (c - c.mean()) / c.std()
    return float((z ** 3).mean())


def run(level, stoch, seed, mode='sense'):
    lf = Life5(seed=seed, **BASE) if mode == 'sense' else \
         Life5(seed=seed, **{**BASE, 'k_seek': 0.0, 'k_sal': 0.0})
    rng = np.random.default_rng(seed * 977 + 13)
    lo, hi = 0.0, min(1.0, 2.0 * level)      # 二值切换，同均值
    p_hi = 0.0 if hi <= 0 else level / hi
    for t in range(STEPS):
        if mode == 'sense':
            v = (hi if rng.random() < p_hi else lo) if stoch else level
            lf.input_val = float(v)
            lf.sal = np.full(lf.N, float(np.clip(v, 0, 1)))
        lf.step()
        if not lf.alive:
            break
    return lf


res = {}
SK = {}
print("=== 剂量扫描（确定性 vs 随机，均值匹配）===")
print(f"{'level':>6} | {'det 偏度':>18} | {'stoch 偏度':>18} | {'diff':>9}")
for lv in LEVELS:
    row = {}
    for tag, st in [('det', False), ('stoch', True)]:
        sk = []
        al = 0
        for sd in SEEDS:
            lf = run(lv, st, sd)
            if lf.alive:
                al += 1
                sk.append(skew(lf))
        sk = np.array(sk)
        SK[(lv, tag)] = sk
        row[tag] = dict(alive=al, n=len(sk),
                        mean=float(sk.mean()) if len(sk) else None,
                        sd=float(sk.std()) if len(sk) > 1 else 0.0)
    a, b = SK[(lv, 'det')], SK[(lv, 'stoch')]
    n = min(len(a), len(b))
    d = float((b[:n] - a[:n]).mean()) if n else float('nan')
    row['diff_stoch_minus_det'] = d
    res[f"{lv:.2f}"] = row
    print(f"{lv:6.2f} | {row['det']['mean']:+.6f}±{row['det']['sd']:.3f} "
          f"(n={row['det']['n']:2d}) | {row['stoch']['mean']:+.6f}±{row['stoch']['sd']:.3f} "
          f"(n={row['stoch']['n']:2d}) | {d:+.4f}")

# 无感官基线
nb = []
for sd in SEEDS:
    lf = run(0.0, False, sd, 'none')
    if lf.alive:
        nb.append(skew(lf))
nb = np.array(nb)
res['_none'] = dict(n=len(nb), mean=float(nb.mean()) if len(nb) else None,
                    sd=float(nb.std()) if len(nb) > 1 else 0.0)
print(f"\n无感官基线 偏度={res['_none']['mean']:+.6f}±{res['_none']['sd']:.3f} (n={len(nb)})")

# 相邻水平配对，找最大跳变（阈值）
print("\n=== 相邻水平跳变（定位阈值）===")
jumps = []
for i in range(1, len(LEVELS)):
    prev, cur = LEVELS[i - 1], LEVELS[i]
    A, B = SK[(prev, 'det')], SK[(cur, 'det')]
    n = min(len(A), len(B))
    if n == 0:
        continue
    D = B[:n] - A[:n]
    boot = np.array([np.random.default_rng(k).choice(D, n, replace=True).mean()
                     for k in range(4000)])
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
    step = cur - prev
    jumps.append(dict(frm=prev, to=cur, step=step, diff=float(D.mean()),
                      ci=ci, sig=not (ci[0] <= 0 <= ci[1]),
                      per_unit=float(D.mean() / step) if step > 0 else 0.0))
    print(f"  {prev:.2f}->{cur:.2f}  Δ={D.mean():+.6f} CI=[{ci[0]:+.4f},{ci[1]:+.4f}] "
          f"{'显著' if not (ci[0] <= 0 <= ci[1]) else '不显著'}  每单位斜率={D.mean()/step:+.3f}")
res['jumps'] = jumps
if jumps:
    mx = max(jumps, key=lambda j: abs(j['per_unit']))
    res['steepest'] = mx
    print(f"\n最陡区间: {mx['frm']:.2f} -> {mx['to']:.2f}  (每单位 {mx['per_unit']:+.3f})")

res['_meta'] = dict(LEVELS=LEVELS, STEPS=STEPS, SEEDS=len(SEEDS))
json.dump(res, open(os.path.join(OUT, 'result_101e.json'), 'w'),
          ensure_ascii=False, indent=1)
print("\nsaved result_101e.json")
