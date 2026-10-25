# -*- coding: utf-8 -*-
"""
227b 修正版：避免饱和
- K=256 容量, STEPS=300（不足填满）
- 难度线性上升，real 永远追不上，形成梯度
- exo  : 每步带来独立新位（外购，与自己无关）
- auto : 主要复制已有位（冗余），只有极少新意
- mixed: 按比例混合
指标: real=独特覆盖/K, surface=外设数/上限, 虚胖=surface-real, 缺口=难度-real
"""
import numpy as np

K, N, STEPS = 256, 200, 300
CAP = 40.0  # surface 归一化上限

def run(mode, seed=0, exo_rate=0.30, cutoff=None):
    rng = np.random.default_rng(seed)
    kernel = rng.random((N, K)) < 0.05
    peri   = np.zeros((N, K), bool)
    ps = np.zeros(N)
    for t in range(STEPS):
        diff = 0.05 + 0.85 * t / STEPS
        exo_open = (cutoff is None) or (t < cutoff)
        for i in range(N):
            if mode == 'exo':
                m = rng.random(K) < 0.06
            elif mode == 'auto':
                base = peri[i] | kernel[i]
                if base.sum() and rng.random() < 0.5:
                    m = base & (rng.random(K) < 0.90)      # 纯冗余
                else:
                    m = rng.random(K) < 0.004               # 极少新意
            elif mode == 'mixed':
                if exo_open and rng.random() < exo_rate:
                    m = rng.random(K) < 0.06
                else:
                    base = peri[i] | kernel[i]
                    m = (base & (rng.random(K) < 0.90)) if (base.sum() and rng.random()<0.5) \
                        else (rng.random(K) < 0.004)
            else:
                m = np.zeros(K, bool)
            if m.any():
                peri[i] |= m; ps[i] += 1
    diff = 0.05 + 0.85*(STEPS-1)/STEPS
    real = (peri | kernel).sum(1).mean()/K
    surf = min(1.0, ps.mean()/CAP)
    return dict(real=real, surf=surf, bloat=surf-real, gap=diff-real)

print("模式      真实能力   名义能力   虚胖指数   能力缺口(越低越好)")
for m in ['none','exo','auto','mixed']:
    rs = [run(m, seed=s) for s in range(6)]
    print(f"{m:8s}  {np.mean([r['real'] for r in rs]):.3f}     "
          f"{np.mean([r['surf'] for r in rs]):.3f}     "
          f"{np.mean([r['bloat'] for r in rs]):+.3f}     "
          f"{np.mean([r['gap'] for r in rs]):.3f}")

print("\n--- exo 占比扫描（mixed）---")
print("外购率   真实能力   虚胖指数   能力缺口")
for q in [0.0,0.1,0.2,0.3,0.5,0.7,1.0]:
    rs = [run('mixed', seed=s, exo_rate=q) for s in range(6)]
    print(f"{q:5.2f}    {np.mean([r['real'] for r in rs]):.3f}     "
          f"{np.mean([r['bloat'] for r in rs]):+.3f}     {np.mean([r['gap'] for r in rs]):.3f}")

print("\n--- 断供（t=150 关闭外购池）---")
for s in range(6):
    a = run('mixed', seed=s, cutoff=150)
    b = run('mixed', seed=s, cutoff=None)
    print(f"seed{s}  断供 real={a['real']:.3f} surf={a['surf']:.3f} | "
          f"不断供 real={b['real']:.3f} surf={b['surf']:.3f}")
