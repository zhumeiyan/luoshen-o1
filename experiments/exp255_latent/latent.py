# -*- coding: utf-8 -*-
"""
255 · 潜存 / 激发
假设：仓库里的资产有两种状态
   latent  潜存 —— 在清单里"存在"，读数为 0（叫它没反应）
   active  激发 —— 被「正确的名字」调用一次后落盘，读数非 0

第二轴：语义对齐度 a = 名字指向真实入口的概率
   a=1 叫对名 → 激发
   a<1 叫错名 → 返回 0（不是报错，是静默返回空）

第三轴：latent 会衰减 —— 不激发就退化，直到连名字都对不上
"""
import numpy as np

def run(a, delta, f, N=200, T=400, seed=0):
    """
    a      : 语义对齐度 0..1
    delta  : 潜存态每步衰减率
    f      : 每个时间步尝试激发的资产比例（激发频率）
    """
    rng = np.random.default_rng(seed)
    state = np.zeros(N)      # 0=latent, 1=active
    health = np.ones(N)      # 潜存资产的可激发度，会衰减
    activated = 0
    hist = []
    for t in range(T):
        # 尝试激发
        k = max(1, int(N*f))
        idx = rng.choice(N, size=k, replace=False)
        for i in idx:
            if state[i] == 1:
                continue
            if health[i] <= 0:
                continue                      # 已退化到叫不动
            if rng.random() < a * health[i]:  # 名字对上 且 还没烂透
                state[i] = 1
                activated += 1
        # 潜存态衰减；已激发的不衰（落盘了）
        health[state == 0] -= delta
        health = np.clip(health, 0, 1)
        if t % 20 == 0:
            hist.append((state == 1).sum())
    usable = (state == 1).sum()
    dead   = ((state == 0) & (health <= 0)).sum()
    return usable/N, dead/N, hist

def sweep_a(delta, f, seeds=10):
    A = np.linspace(0, 1, 21)
    U = []; D = []
    for a in A:
        us = [run(a, delta, f, seed=k) for k in range(seeds)]
        U.append(np.mean([u[0] for u in us]))
        D.append(np.mean([u[1] for u in us]))
    return A, np.array(U), np.array(D)

print("="*76)
print("结果一 · 语义对齐度 a 决定多少资产能长出来（衰减 δ=0.002，激发频率 f=0.10）")
print("="*76)
A,U,D = sweep_a(0.002, 0.10)
print(f"{'a(对齐度)':>10} {'可用率':>9} {'烂透率':>9}")
for a,u,d in zip(A,U,D):
    print(f"{a:>10.2f} {u:>9.3f} {d:>9.3f}  {'█'*int(u*40)}")

print()
print("="*76)
print("结果二 · 门槛：可用率过半需要多少对齐度")
print("="*76)
for d in [0.0, 0.001, 0.002, 0.005, 0.01, 0.02]:
    A,U,_ = sweep_a(d, 0.10)
    ok = A[U >= 0.5]
    th = ok.min() if len(ok) else None
    print(f"  δ={d:<6}  a* = {('%.2f'%th) if th is not None else '永远过不了半'}   (a=1 时可用率 {U[-1]:.3f})")

print()
print("="*76)
print("结果三 · 衰减 δ 的影响（a 固定 0.6，f=0.10）")
print("="*76)
print(f"{'δ':>8} {'可用率':>9} {'烂透率':>9}")
for d in [0.0,0.001,0.002,0.005,0.01,0.02,0.05]:
    us=[run(0.6,d,0.10,seed=k) for k in range(10)]
    u=np.mean([x[0] for x in us]); dd=np.mean([x[1] for x in us])
    print(f"{d:>8.3f} {u:>9.3f} {dd:>9.3f}  {'█'*int(u*40)}")

print()
print("="*76)
print("结果四 · 关键：不激发会不会自己烂掉（a=0.6，δ 扫描，f=0 vs f=0.1）")
print("="*76)
print(f"{'δ':>8} {'不激发可用率':>13} {'激发可用率':>11} {'差':>9}")
for d in [0.0,0.002,0.01,0.03]:
    u0=np.mean([run(0.6,d,0.0,seed=k)[0] for k in range(10)])
    u1=np.mean([run(0.6,d,0.1,seed=k)[0] for k in range(10)])
    print(f"{d:>8.3f} {u0:>13.3f} {u1:>11.3f} {u1-u0:>+9.3f}")

print()
print("="*76)
print("结果五 · 激发频率 f 有中间带吗（a=0.5, δ=0.01）")
print("="*76)
print(f"{'f':>7} {'可用率':>9} {'烂透率':>9}")
best=None;bu=-1
for f in [0.0,0.02,0.05,0.1,0.2,0.4,0.7,1.0]:
    us=[run(0.5,0.01,f,seed=k) for k in range(10)]
    u=np.mean([x[0] for x in us]); dd=np.mean([x[1] for x in us])
    if u>bu: bu=u; best=f
    print(f"{f:>7.2f} {u:>9.3f} {dd:>9.3f}  {'█'*int(u*40)}")
print(f"\n最优 f = {best}")
