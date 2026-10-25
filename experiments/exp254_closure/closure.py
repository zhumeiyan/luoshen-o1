# -*- coding: utf-8 -*-
"""
254 · 统一闭合模型
假设：前面 250 条 findings 全部落在同一根轴上 —— 闭合度 c。
  c = 学习/判定信号中，来自「自己内部」的比例。
  c=1 纯闭合（自证循环）   c=0 全开放（只听外部）

第二轴猜测：外部信号可得性 ρ（外部见证人有多稀疏）。
  若 ρ 低（外部信号稀疏），完全开放会导致无法跨时间整合 → 需要一点闭合。
  这就是 14 次「中间带」的由来。
"""
import numpy as np

def run(c, rho, T=400, true_v=1.0, seed=0):
    """
    c    : 闭合度 0..1
    rho  : 每个时间步能拿到外部信号的概率（外部见证人的密度）
    返回 (真实能力, 名义能力, 虚胖量)
    """
    rng = np.random.default_rng(seed)
    s = 0.0            # 真实能力
    belief = 0.0       # 自认能力（内部判据）
    drift = 0.0        # 内部判据的漂移（自洽会累积偏差）
    nominal = 0.0
    for t in range(T):
        # --- 外部信号：稀疏，拿到才真实 ---
        ext = None
        if rng.random() < rho:
            ext = true_v - s                    # 真实的差距
        # --- 内部信号：永远可得，但自带漂移（自洽 ≠ 正确）---
        drift += 0.004 * (1.0 if belief <= s else -0.2)   # 内部判据只会往上偏
        internal = 0.12 + drift                            # 恒正的「进展感」
        # --- 合成 ---
        sig = c * internal + (1 - c) * (ext if ext is not None else 0.0)
        s += 0.05 * sig
        s = max(0.0, min(2.0, s))
        belief = c * (belief + 0.05 * internal) + (1 - c) * (s if ext is not None else belief)
        nominal = max(nominal, belief)
    real = s
    return real, nominal, nominal - real

def sweep(rho, seeds=8):
    cs = np.linspace(0, 1, 21)
    R = np.array([np.mean([run(c, rho, seed=k)[0] for k in range(seeds)]) for c in cs])
    N = np.array([np.mean([run(c, rho, seed=k)[1] for k in range(seeds)]) for c in cs])
    return cs, R, N

if __name__ == "__main__":
    print("="*74)
    print("结果一：外部信号充足 (rho=1.0) —— 闭合度是不是单调有害？")
    print("="*74)
    cs, R, N = sweep(1.0)
    print(f"{'c(闭合度)':>10} {'真实能力':>10} {'名义能力':>10} {'虚胖':>10}")
    for c, r, n in zip(cs, R, N):
        bar = "█"*int(r*12)
        print(f"{c:>10.2f} {r:>10.3f} {n:>10.3f} {n-r:>10.3f}  {bar}")
    print()

    print("="*74)
    print("结果二：外部信号稀疏 (rho=0.15) —— 会不会出现中间带？")
    print("="*74)
    cs2, R2, N2 = sweep(0.15)
    best = int(np.argmax(R2))
    print(f"{'c(闭合度)':>10} {'真实能力':>10} {'名义能力':>10} {'虚胖':>10}")
    for c, r, n in zip(cs2, R2, N2):
        mark = "  <== 最优" if abs(c-cs2[best]) < 1e-9 else ""
        print(f"{c:>10.2f} {r:>10.3f} {n:>10.3f} {n-r:>10.3f}{mark}")
    print()

    print("="*74)
    print("结果三：最优闭合度 c* 随外部信号密度 rho 的移动")
    print("="*74)
    print(f"{'rho':>8} {'最优 c*':>10} {'该处真实能力':>14}")
    for rho in [0.05,0.1,0.15,0.25,0.4,0.6,0.8,1.0]:
        c3, R3, _ = sweep(rho)
        i = int(np.argmax(R3))
        print(f"{rho:>8.2f} {c3[i]:>10.2f} {R3[i]:>14.3f}")
    print()

    print("="*74)
    print("结果四：两边都比纯闭合好吗？（c=1 是不是恒差）")
    print("="*74)
    for rho in [0.05,0.15,0.5,1.0]:
        c4, R4, N4 = sweep(rho)
        print(f"rho={rho:<5}  c=0:{R4[0]:.3f}  c=1:{R4[-1]:.3f}  最大:{R4.max():.3f}@c={c4[int(np.argmax(R4))]:.2f}  虚胖@c=1:{N4[-1]-R4[-1]:+.3f}")
