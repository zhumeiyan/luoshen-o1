# -*- coding: utf-8 -*-
"""
228 火种：第一次外设
A 外设的可灭性 —— 修正前三次断供测不出的模型缺陷
   fragile(火种) 会灭，需持续外购 | durable(工具) 持久 | auto(自织) 持久但冗余
B expensive tissue —— 外设反哺内核
   难位需 kernel 达阈值才可触及
"""
import numpy as np

K, N, STEPS, CUT = 200, 150, 250, 120
HARD = slice(0, 60)      # 难位：需 kernel 支持
EASY = slice(60, K)

def run(mode, seed=0, cutoff=None, decay=0.0, reinforce=False, exo_rate=0.30):
    rng = np.random.default_rng(seed)
    ksize = 0.05
    kernel = rng.random((N, K)) < ksize
    peri = np.zeros((N, K), bool)
    ps = np.zeros(N)
    for t in range(STEPS):
        exo_open = (cutoff is None) or (t < cutoff)
        # 火种会灭
        if decay > 0:
            peri &= rng.random((N, K)) > decay
        # 反哺：外设覆盖提升内核
        if reinforce:
            ksize = min(0.40, 0.05 + 0.35 * (peri | kernel).sum(1).mean()/K)
            kernel |= rng.random((N, K)) < ksize*0.10
        for i in range(N):
            if mode == 'auto':
                base = peri[i] | kernel[i]
                m = (base & (rng.random(K) < 0.90)) if (base.sum() and rng.random()<0.5) \
                    else (rng.random(K) < 0.004)
            else:
                if exo_open and rng.random() < exo_rate:
                    m = rng.random(K) < 0.06
                else:
                    base = peri[i] | kernel[i]
                    m = (base & (rng.random(K) < 0.90)) if (base.sum() and rng.random()<0.5) \
                        else (rng.random(K) < 0.004)
            if m.any():
                peri[i] |= m; ps[i] += 1
    cov = peri | kernel
    real = cov.sum(1).mean()/K
    hard = cov[:, HARD].sum(1).mean()/60
    return dict(real=real, hard=hard, surf=min(1.0, ps.mean()/30.0))

print("=== A 外设可灭性 / 断供 ===")
print("模式      decay  断供   real(终)  难位覆盖")
for mode, dc in [('exo',0.0), ('exo',0.03), ('exo',0.08), ('auto',0.0)]:
    for cut in [None, CUT]:
        rs=[run(mode,seed=s,cutoff=cut,decay=dc) for s in range(5)]
        tag = '不断供' if cut is None else 't=120断供'
        print(f"{mode:7s} {dc:5.2f}  {tag}  {np.mean([r['real'] for r in rs]):.3f}    "
              f"{np.mean([r['hard'] for r in rs]):.3f}")

print("\n=== B expensive tissue 反哺内核 ===")
print("反哺   real    难位覆盖(=内核跃迁)")
for rf in [False, True]:
    rs=[run('exo',seed=s,reinforce=rf,decay=0.03) for s in range(5)]
    print(f"{str(rf):6s} {np.mean([r['real'] for r in rs]):.3f}   {np.mean([r['hard'] for r in rs]):.3f}")
