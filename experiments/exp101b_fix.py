# -*- coding: utf-8 -*-
"""★101b 修 ★101 的三处建模污染：标定 / rho 硬依赖 / 解耦样本量"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.aibench import (TOPAI, evaluate, evaluate_ep, topai_like, human_like,
                          opt_theta, register_trial)

R = {}
def rec(k, v): R[k] = v; print(f"  {k}: {v}", flush=True)

print("=" * 68)
print("★101b  修三处建模污染")
print("=" * 68)

# ── 污染一：标定只拟合了顶级AI那一边，人类那边 0.706 vs 文献 0.81 差 0.10
print("\n[A] 重新标定：帕累托表（顶级AI 拟合 0.65 时，人类能到多少）")
tbl = []
for rho in np.arange(0.10, 0.95, 0.10):
    rows = []
    for sig in np.arange(0.02, 0.34, 0.02):
        at, ah = [], []
        for s in range(60):
            rng = np.random.default_rng(3100 + s)
            for _ in range(40): at.append(register_trial(rng, 1.00, rho, sig)[0])
            for _ in range(40): ah.append(register_trial(rng, 0.75, rho, sig)[0])
        rows.append((sig, float(np.mean(at)), float(np.mean(ah))))
    # 取 sig 使顶级AI 最接近 0.65
    b = min(rows, key=lambda x: abs(x[1] - TOPAI['steer_best']))
    tbl.append((round(rho, 2), round(b[0], 2), round(b[1], 4), round(b[2], 4)))
    print(f"  rho={rho:.2f}  sigma={b[0]:.2f}  顶级AI {b[1]:.4f}  人类 {b[2]:.4f}"
          f"  人类误差 {abs(b[2]-TOPAI['steer_human']):.4f}")
best = max(tbl, key=lambda x: -abs(x[3] - TOPAI['steer_human']))
print(f"  → 选 rho={best[0]} sigma={best[1]}：顶级AI {best[2]} 人类 {best[3]}")
RHO, SIG = best[0], best[1]
rec('A_rho', RHO); rec('A_sigma', SIG)
rec('A_顶级AI', best[2]); rec('A_人类', best[3])
rec('A_人类误差', round(abs(best[3] - TOPAI['steer_human']), 4))

W_TRAIN = [(RHO, SIG, a, m, 1.5) for a in (0.40, 0.55, 0.70) for m in (0.05, 0.15, 0.25)]

# ── 污染二：rho 硬依赖被「先验均值 = 总体均值」污染
print("\n[B] rho 硬依赖（★ 承认：prior=0.5 恰好等于 f_true 的总体均值 0.5，")
print("     所以 rho=0 时 shrinkage 本身就有收益 —— 这是真统计，不是 rho 的作用）")
print("     改成：把 prior 移出总体中心（prior=0.15），单独看 rho 的边际贡献")
def reg2(rng, trust, rho, sigma, prior):
    f_true = float(rng.uniform(0.1, 0.9))
    f_prev = float(rng.uniform(0.1, 0.9))
    obs = float(np.clip((1 - rho) * f_true + rho * f_prev + rng.normal(0, sigma), 0, 1))
    ch = float(np.clip((1 - trust) * prior + trust * obs, 0, 1))
    return 1.0 if abs(ch - f_true) <= 0.13 else 0.0

for prior in (0.5, 0.15):
    out = []
    for rho in (0.0, 0.3, 0.7):
        row = []
        for tr in np.arange(0.0, 1.01, 0.1):
            v = []
            for s in range(50):
                rng = np.random.default_rng(5200 + s)
                v += [reg2(rng, tr, rho, SIG, prior) for _ in range(40)]
            row.append((round(tr, 2), float(np.mean(v))))
        b = max(row, key=lambda x: x[1])
        out.append((rho, b[0], round(b[1] - min(x[1] for x in row), 4)))
        print(f"  prior={prior}  rho={rho}  峰 trust={b[0]}  跨度 {b[1]-min(x[1] for x in row):.4f}")
    rec(f'B_prior{prior}', out)
    rec(f'B_prior{prior}_峰位移', float(out[0][1]) - float(out[-1][1]))

# ── 污染三：解耦检验样本量太小，散度盖过信号
print("\n[C] 解耦检验（加大样本：nseed 6→14）")
for w in (0.5, 1.0, 2.0):
    ths = []
    for a in (0.30, 0.50, 0.70, 0.85):
        W = [(RHO, SIG, a, m, w) for m in (0.05, 0.15)]
        row = [(round(th, 2), evaluate([0.75, th], W, nseed=14)['score'])
               for th in np.arange(0.0, 0.96, 0.05)]
        ths.append(max(row, key=lambda x: x[1])[0])
    exp = opt_theta(w) + 0.10
    mn = float(np.mean(ths))
    print(f"  w={w}  各acc实测峰 {ths}  均值 {mn:.3f}  解析(exp+miscal) {exp:.3f}"
          f"  均值误差 {abs(mn-exp):.3f}  峰间极差 {max(ths)-min(ths):.2f}")
    rec(f'C_w{w}_峰', [float(x) for x in ths])
    rec(f'C_w{w}_均值', round(mn, 4)); rec(f'C_w{w}_解析', round(exp, 4))
    rec(f'C_w{w}_均值误差', round(abs(mn - exp), 4))
    rec(f'C_w{w}_极差', round(float(max(ths)) - float(min(ths)), 4))

# ── 补：[5] w=0 时 θ=0 的实测值
print("\n[D] w=0 时门槛该为 0（=文献「vanilla 从不拒绝」）")
for w in (0.0, 1.5):
    W = [(RHO, SIG, a, m, w) for a in (0.40, 0.55, 0.70) for m in (0.10, 0.20)]
    row = [(round(th, 2), evaluate([0.75, th], W, nseed=14)['score'])
           for th in np.arange(0.0, 0.96, 0.05)]
    print(f"  w={w}: " + " ".join(f"{t}:{v:.3f}" for t, v in row[:6]))
    rec(f'D_w{w}_theta0值', round(row[0][1], 4))
    b = max(row, key=lambda x: x[1])
    rec(f'D_w{w}_峰', b[0]); rec(f'D_w{w}_峰值', round(b[1], 4))

json.dump(R, open('data/exp101b_fix.json', 'w'), ensure_ascii=False, indent=1)
print("\n已存 data/exp101b_fix.json")
