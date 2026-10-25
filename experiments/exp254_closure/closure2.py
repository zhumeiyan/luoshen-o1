# -*- coding: utf-8 -*-
"""
254 v2 · 统一闭合模型（修掉 v1 的建模错误）

v1 错在哪：让「内部信号」直接推高真实能力 s，于是纯闭合 c=1 一路冲到上限，
看起来"真实能力最高"——这跟 250 条 findings 全部矛盾。
错因：自洽信号不该产生真实能力，只该产生「进展感」。

v2 的修法（也是本轮唯一的机制要点）：
  外部信号缺席时，真实能力 s 不动（没有新信息就是没长）；
  但 belief 照涨 —— 你默认自己前进了。
  这一格之差，就是「虚胖」的全部来源。
"""
import numpy as np

V = 1.0            # 真实目标
S0 = 0.0
ETA = 0.10
INT = 0.08         # 内部信号：恒定「前进感」，方向不由真相决定

def run(c, rho, T=400, seed=0):
    rng = np.random.default_rng(seed)
    s = S0          # 真实能力（位置）
    belief = S0     # 自认能力
    ext_n = 0
    for t in range(T):
        ext = (V - s) if rng.random() < rho else None
        # 真实能力：闭合部分不提供新信息，只会把你往前推（可能推过头）
        s += ETA * (c*INT + (1-c)*(ext if ext is not None else 0.0))
        s = max(-0.5, min(2.5, s))
        # 自认能力：外部缺席时，用自我估计填补 —— 照涨
        claimed = c*INT + (1-c)*(ext if ext is not None else INT)
        belief += ETA * claimed
        if ext is not None: ext_n += 1
    real = max(0.0, 1.0 - abs(s - V))   # 离真相越近越高
    return real, belief, belief - real, ext_n/T

def sweep(rho, seeds=12, n=21):
    cs = np.linspace(0,1,n)
    out = []
    for c in cs:
        rs = [run(c, rho, seed=k) for k in range(seeds)]
        out.append((np.mean([r[0] for r in rs]),
                    np.mean([r[1] for r in rs]),
                    np.mean([r[2] for r in rs])))
    return cs, np.array([o[0] for o in out]), np.array([o[1] for o in out]), np.array([o[2] for o in out])

print("="*78)
print("结果一 · 外部信号充足 rho=1.0 ：闭合度对真实能力做了什么")
print("="*78)
cs,R,N,D = sweep(1.0)
print(f"{'c':>6} {'真实':>8} {'名义':>8} {'虚胖':>8}")
for c,r,n,d in zip(cs,R,N,D):
    print(f"{c:>6.2f} {r:>8.3f} {n:>8.3f} {d:>+8.3f}  {'█'*int(r*20)}")

print()
print("="*78)
print("结果二 · 外部信号稀疏 rho=0.12 ：中间带是否出现")
print("="*78)
cs,R,N,D = sweep(0.12)
i = int(np.argmax(R))
print(f"{'c':>6} {'真实':>8} {'名义':>8} {'虚胖':>8}")
for c,r,n,d in zip(cs,R,N,D):
    mk = "   <== 最优" if abs(c-cs[i])<1e-9 else ""
    print(f"{c:>6.2f} {r:>8.3f} {n:>8.3f} {d:>+8.3f}  {'█'*int(r*20)}{mk}")

print()
print("="*78)
print("结果三 · 最优闭合度 c* 随外部见证人密度 rho 的移动")
print("="*78)
print(f"{'rho':>7} {'c*':>7} {'真实@c*':>9} {'真实@c=0':>9} {'真实@c=1':>9} {'虚胖@c=1':>9}")
for rho in [0.02,0.05,0.08,0.12,0.20,0.35,0.60,1.00]:
    cs,R,N,D = sweep(rho)
    i = int(np.argmax(R))
    print(f"{rho:>7.2f} {cs[i]:>7.2f} {R[i]:>9.3f} {R[0]:>9.3f} {R[-1]:>9.3f} {D[-1]:>+9.3f}")

print()
print("="*78)
print("结果四 · 关键对照：纯闭合 c=1 的「真实」和「名义」永远差多少")
print("="*78)
for rho in [0.02,0.12,0.5,1.0]:
    cs,R,N,D = sweep(rho)
    print(f"rho={rho:<6} 真实={R[-1]:.3f}  名义={N[-1]:.3f}  虚胖={D[-1]:+.3f}   (真实/名义 = {R[-1]/N[-1]:.2f})")

print()
print("="*78)
print("结果五 · 门槛在哪：c* 何时离开 0（细扫低 rho）")
print("="*78)
print(f"{'rho':>7} {'c*':>7} {'真实@c*':>9} {'真实@c=0':>9} {'闭合带来的增益':>16}")
for rho in [0.005,0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.10]:
    cs,R,N,D = sweep(rho, seeds=16, n=41)
    i = int(np.argmax(R))
    gain = R[i]-R[0]
    flag = "  ← 需要闭合" if cs[i] > 0.02 else ""
    print(f"{rho:>7.3f} {cs[i]:>7.2f} {R[i]:>9.3f} {R[0]:>9.3f} {gain:>+16.3f}{flag}")

print()
print("="*78)
print("结果六 · 纯闭合 c=1 是否与外部世界完全解耦（三档 rho 全同即解耦）")
print("="*78)
vals=[]
for rho in [0.001,0.01,0.1,0.5,1.0]:
    cs,R,N,D = sweep(rho, seeds=8, n=11)
    vals.append((R[-1],N[-1]))
    print(f"rho={rho:<7} 真实={R[-1]:.6f}  名义={N[-1]:.6f}")
same_real = len(set(round(v[0],6) for v in vals))==1
same_nom  = len(set(round(v[1],6) for v in vals))==1
print(f"\n真实值全同: {same_real}   名义值全同: {same_nom}")
print("→ 纯闭合系统的读数与外部世界零相关：改世界，读数不动。" if same_real and same_nom else "→ 未解耦")
