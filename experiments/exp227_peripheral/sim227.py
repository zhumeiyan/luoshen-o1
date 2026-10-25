# -*- coding: utf-8 -*-
"""
227: 外设是外购的还是自织的
能力用 64 位 bit 向量表示"覆盖"。内核极小(5%)，其余全靠外设。
- exo  外购外设：来自外部池，与自己独立，有获取成本
- auto 自织外设：自己已有能力的复制+微扰，零成本，但与自身高度相关
指标:
  surface = 外设数量(名义能力)
  real    = 内核∪外设 覆盖的独特位数(真实能力)
  虚胖指数 = surface - real
"""
import numpy as np, json

K, N, STEPS = 64, 300, 600

def run(mode, seed=0, cutoff=400, exo_cost=0.30):
    rng = np.random.default_rng(seed)
    kernel = rng.random((N, K)) < 0.05          # 内核极小
    peri   = np.zeros((N, K), bool)
    pool_size = np.zeros(N)                      # 名义外设数
    diff = 0.25
    hist = []
    for t in range(STEPS):
        if t in (150, 300, 450):
            diff = min(0.85, diff + 0.18)        # 环境漂移/难度跃迁
        if t == cutoff:
            pass                                  # 断供在 standalone 里处理
        for i in range(N):
            if mode == 'exo':
                m = rng.random(K) < 0.20          # 外部池：与自己独立
            elif mode == 'auto':
                base = peri[i] | kernel[i]
                if base.sum() == 0:
                    m = rng.random(K) < 0.05
                else:
                    # 复制已有能力 + 微扰：与自己高度相关
                    m = base & (rng.random(K) < 0.85)
                    m |= (rng.random(K) < 0.02)   # 极少的真新意
            elif mode == 'mixed':
                if rng.random() < exo_cost:
                    m = rng.random(K) < 0.20
                else:
                    base = peri[i] | kernel[i]
                    m = (base & (rng.random(K) < 0.85)) if base.sum() else (rng.random(K) < 0.05)
            else:  # none
                m = np.zeros(K, bool)
            if m.any():
                peri[i] |= m
                pool_size[i] += 1
        real = (peri | kernel).sum(1) / K
        hist.append(dict(t=t, surf=pool_size.mean()/8.0, real=real.mean(),
                         diff=diff))
    return hist

def summarize(mode, seeds=range(6), **kw):
    out = []
    for s in seeds:
        h = run(mode, seed=s, **kw)
        last = h[-1]
        out.append(last)
    return dict(mode=mode,
                surf=np.mean([o['surf'] for o in out]),
                real=np.mean([o['real'] for o in out]),
                bloat=np.mean([o['surf'] for o in out]) - np.mean([o['real'] for o in out]))

res = [summarize(m) for m in ['none','exo','auto','mixed']]
print("模式      名义能力   真实能力   虚胖指数")
for r in res:
    print(f"{r['mode']:8s}  {r['surf']:.3f}     {r['real']:.3f}     {r['bloat']:+.3f}")

# 断供实验
print("\n--- 断供（t=400 起 exo 池关闭，仅 mixed 可自织）---")
def run_cut(seed, cutoff=400):
    rng = np.random.default_rng(seed)
    kernel = rng.random((N,K)) < 0.05
    peri = np.zeros((N,K), bool); ps = np.zeros(N); diff=0.25
    snap = {}
    for t in range(STEPS):
        if t in (150,300,450): diff = min(0.85, diff+0.18)
        exo_open = t < cutoff
        for i in range(N):
            if exo_open and rng.random() < 0.30:
                m = rng.random(K) < 0.20
            else:
                base = peri[i]|kernel[i]
                m = (base & (rng.random(K) < 0.85)) if base.sum() else (rng.random(K)<0.05)
            if m.any(): peri[i] |= m; ps[i]+=1
        if t in (399, 599):
            snap[t] = dict(real=(peri|kernel).sum(1).mean()/K, surf=ps.mean()/8.0)
    return snap
for s in range(6):
    sn = run_cut(s)
    print(f"seed{s}  t=399 real={sn[399]['real']:.3f} surf={sn[399]['surf']:.3f} "
          f"-> t=599 real={sn[599]['real']:.3f} surf={sn[599]['surf']:.3f}")
