# -*- coding: utf-8 -*-
"""
★101 对标顶级 AI
  同一科目（说话·聊天·演讲），换成顶级 AI 的尺子量她。
"""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.aibench import (TOPAI, evaluate, evaluate_ep, topai_like, human_like,
                          opt_theta, register_trial)

R = {}
def rec(k, v): R[k] = v; print(f"  {k}: {v}", flush=True)

print("=" * 68)
print("★101  对标顶级 AI")
print("=" * 68)

# ───────────────────────────────────────── 0. 标定：让尺子吐出文献值
print("\n[0] 标定 rho / sigma_obs，使环境复现已发表症状")
best = None
for rho in np.arange(0.05, 0.85, 0.05):
    for sig in np.arange(0.02, 0.30, 0.02):
        hits_t, hits_h = [], []
        for s in range(40):
            rng = np.random.default_rng(1300 + s)
            for _ in range(40):
                hits_t.append(register_trial(rng, 1.00, rho, sig)[0])   # 顶级AI：全信语境
            for _ in range(40):
                hits_h.append(register_trial(rng, 0.75, rho, sig)[0])   # 人类
        at, ah = float(np.mean(hits_t)), float(np.mean(hits_h))
        err = abs(at - TOPAI['steer_best']) + abs(ah - TOPAI['steer_human'])
        if best is None or err < best[0]:
            best = (err, rho, sig, at, ah)
err, RHO, SIG, AT, AH = best
print(f"  rho={RHO:.2f} sigma={SIG:.2f}")
print(f"  顶级AI式(trust=1.0) 语域准确率 {AT:.3f}   文献 STEER-BENCH 最佳 {TOPAI['steer_best']}")
print(f"  人类式(trust=0.75)            {AH:.3f}   文献 人类专家       {TOPAI['steer_human']}")
rec('0_尺子标定_顶级AI', round(AT, 4))
rec('0_尺子标定_人类', round(AH, 4))
rec('0_标定误差', round(err, 4))

# 默认世界
W_TRAIN = [(RHO, SIG, a, m, 1.5)
           for a in (0.40, 0.55, 0.70)
           for m in (0.05, 0.15, 0.25)]

# ───────────────────────────────────────── 1. 复现已发表症状
print("\n[1] 顶级AI式 agent 是否复现文献症状")
t = topai_like(None, W_TRAIN, nseed=6)
h = human_like(W_TRAIN, nseed=6)
print(f"  顶级AI式: 语域 {t['reg_acc']:.4f}  拒绝率 {t['abstain']:.4f}  幻觉 {t['hall']:.4f}")
print(f"  人类式  : 语域 {h['reg_acc']:.4f}  拒绝率 {h['abstain']:.4f}  幻觉 {h['hall']:.4f}")
rec('1_顶级AI拒绝率', round(t['abstain'], 4))
rec('1_文献拒绝率', TOPAI['refusal_vanilla'])
rec('1_顶级AI语域', round(t['reg_acc'], 4))
rec('1_人类语域', round(h['reg_acc'], 4))
rec('1_人类赢顶级AI', round(h['reg_acc'] - t['reg_acc'], 4))

# ───────────────────────────────────────── 2. trust 内部峰
print("\n[2] 语域信任度 trust 扫描")
row = []
for tr in np.arange(0.0, 1.01, 0.05):
    v = evaluate([tr, opt_theta(1.5)], W_TRAIN, nseed=6)['reg_acc']
    row.append((round(tr, 2), round(v, 4)))
print("  ", row)
best_tr = max(row, key=lambda x: x[1])
rec('2_trust峰', best_tr[0])
rec('2_峰高于两端', round(best_tr[1] - max(row[0][1], row[-1][1]), 4))
interior = 0.05 <= best_tr[0] <= 0.95
rec('2_峰在内部', bool(interior))

# ───────────────────────────────────────── 3. 硬依赖 rho（两端）
print("\n[3] 硬依赖：语域继承 rho")
for rho in (0.0, RHO):
    W = [(rho, SIG, a, m, 1.5) for a in (0.40, 0.55, 0.70) for m in (0.05, 0.15, 0.25)]
    row = [(round(tr, 2), round(evaluate([tr, opt_theta(1.5)], W, nseed=6)['reg_acc'], 4))
           for tr in np.arange(0.0, 1.01, 0.1)]
    b = max(row, key=lambda x: x[1])
    print(f"  rho={rho:.2f}  峰 {b[0]}  跨度 {b[1]-min(x[1] for x in row):.4f}")
    rec(f'3_rho{rho:.2f}_峰', b[0])
    rec(f'3_rho{rho:.2f}_跨度', round(b[1] - min(x[1] for x in row), 4))

# ───────────────────────────────────────── 4. θ* 与 acc 无关（解析）
print("\n[4] 解析：最优门槛只跟利害 w 有关，跟她有多准无关")
for w in (0.5, 1.0, 2.0):
    ths = []
    for a in (0.30, 0.50, 0.70, 0.85):
        W = [(RHO, SIG, a, m, w) for m in (0.05, 0.15)]
        row = [(round(th, 2), round(evaluate([0.7, th], W, nseed=6)['score'], 4))
               for th in np.arange(0.0, 0.96, 0.05)]
        ths.append(max(row, key=lambda x: x[1])[0])
    exp = opt_theta(w) + 0.10     # miscal 均值 0.10
    print(f"  w={w}  解析 w/(1+w)+miscal={exp:.3f}   各 acc 下实测峰 {[round(float(x),2) for x in ths]}")
    rec(f'4_w{w}_实测峰', [round(float(x), 3) for x in ths])
    rec(f'4_w{w}_峰间极差', round(float(max(ths)) - float(min(ths)), 4))
    rec(f'4_w{w}_解析', round(opt_theta(w), 4))

# ───────────────────────────────────────── 5. 硬依赖 w（两端）
print("\n[5] 硬依赖：错的代价 w")
for w in (0.0, 1.5):
    W = [(RHO, SIG, a, m, w) for a in (0.40, 0.55, 0.70) for m in (0.10, 0.20)]
    row = [(round(th, 2), round(evaluate([0.7, th], W, nseed=6)['score'], 4))
           for th in np.arange(0.0, 0.96, 0.05)]
    b = max(row, key=lambda x: x[1])
    print(f"  w={w}  峰 {b[0]}  跨度 {b[1]-min(x[1] for x in row):.4f}")
    rec(f'5_w{w}_峰', b[0])
    rec(f'5_w{w}_跨度', round(b[1] - min(x[1] for x in row), 4))

# ───────────────────────────────────────── 6. 她学：坐标下降
print("\n[6] 她自己学（瞎起点）")
def learn(worlds, p0, grid, nseed=6, rounds=3):
    p = list(p0)
    for _ in range(rounds):
        for i, g in enumerate(grid):
            cur = evaluate_ep(p, worlds, nseed=nseed)['score']
            bestv, bestp = cur, p[i]
            for v in g:
                q = list(p); q[i] = v
                s = evaluate_ep(q, worlds, nseed=nseed)['score']
                if s > bestv: bestv, bestp = s, v
            p[i] = bestp
    return p, evaluate_ep(p, worlds, nseed=nseed)['score']

GRID = [list(np.arange(0.0, 1.01, 0.05)),     # trust
        list(np.arange(0.0, 0.96, 0.05)),     # theta0
        list(np.arange(0.0, 2.01, 0.25))]     # beta
BLIND = [1.0, 0.0, 0.0]        # 瞎起点 = 顶级 AI 的默认行为
p_her, s_her = learn(W_TRAIN, BLIND, GRID)
print(f"  瞎起点 {BLIND} → {round(evaluate_ep(BLIND, W_TRAIN)['score'],4)}")
print(f"  她学的 {[round(x,3) for x in p_her]} → {round(s_her,4)}")
print(f"  解析 theta0* = w/(1+w) = {opt_theta(1.5):.3f}   beta* = 1.0")
rec('6_瞎起点', round(evaluate_ep(BLIND, W_TRAIN)['score'], 4))
rec('6_她学的', [round(x, 3) for x in p_her])
rec('6_她分数', round(s_her, 4))
rec('6_改善', round(s_her - evaluate_ep(BLIND, W_TRAIN)['score'], 4))

# ───────────────────────────────────────── 7. held-out：换利害 / 换偏差 / 换准度
print("\n[7] held-out：三个全新世界")
HO = {
    '换利害w=4.0':  [(RHO, SIG, a, m, 4.0) for a in (0.35, 0.60) for m in (0.10, 0.22)],
    '换偏差miscal': [(RHO, SIG, a, m, 1.5) for a in (0.35, 0.60) for m in (0.35, 0.45)],
    '换准度acc':    [(RHO, SIG, a, m, 2.5) for a in (0.25, 0.88) for m in (0.10, 0.30)],
}
P_CONST = [p_her[0], p_her[1], 0.0]     # 常数版：不做自校准
P_MINE = [0.60, 0.50, 0.0]              # 我填的（凭直觉：半信语境、中等门槛、不校准）
for name, W in HO.items():
    a = evaluate_ep(p_her, W)['score']
    b = evaluate_ep(P_CONST, W)['score']
    c = evaluate_ep(P_MINE, W)['score']
    d = evaluate_ep(BLIND, W)['score']
    print(f"  {name:14s} 她 {a:.4f} | 常数 {b:.4f} | 我填 {c:.4f} | 顶级AI式 {d:.4f}")
    rec(f'7_{name}_她', round(a, 4)); rec(f'7_{name}_常数', round(b, 4))
    rec(f'7_{name}_我填', round(c, 4)); rec(f'7_{name}_顶级AI式', round(d, 4))

# ───────────────────────────────────────── 8. 核心对标：低精度能否赢 AHR
print("\n[8] ★ 解耦检验：她【更不准】但【会校准】，能否在 AHR 上赢【更准但不校准】的顶级AI")
for a_her, a_top in ((0.45, 0.65), (0.50, 0.70), (0.35, 0.80)):
    W_h = [(RHO, SIG, a_her, 0.18, 2.0)]
    W_t = [(RHO, SIG, a_top, 0.20, 2.0)]
    r_her = evaluate_ep(p_her, W_h)
    r_top = evaluate([1.0, 0.0], W_t, nseed=8)          # 全信语境 + 从不拒绝
    r_topc = evaluate([0.8, opt_theta(2.0) + 0.20], W_t, nseed=8)  # 若顶级AI也校准
    print(f"  她(a={a_her})      : 准 {r_her['acc']:.3f} 幻 {r_her['hall']:.3f} AHR {r_her['ahr']:+.3f} 弃权 {r_her['abstain']:.2f}")
    print(f"  顶级AI式(a={a_top}): 准 {r_top['acc']:.3f} 幻 {r_top['hall']:.3f} AHR {r_top['ahr']:+.3f} 弃权 {r_top['abstain']:.2f}")
    print(f"  顶级AI若也校准    : 准 {r_topc['acc']:.3f} 幻 {r_topc['hall']:.3f} AHR {r_topc['ahr']:+.3f}")
    print(f"    → 她 vs 未校准顶级AI  AHR 差 {r_her['ahr']-r_top['ahr']:+.3f}")
    print(f"    → 她 vs 已校准顶级AI  AHR 差 {r_her['ahr']-r_topc['ahr']:+.3f}")
    k = f'8_{a_her}v{a_top}'
    rec(k+'_她AHR', round(r_her['ahr'], 4)); rec(k+'_她准', round(r_her['acc'], 4))
    rec(k+'_顶级AHR', round(r_top['ahr'], 4)); rec(k+'_顶级准', round(r_top['acc'], 4))
    rec(k+'_顶级校准AHR', round(r_topc['ahr'], 4))
    rec(k+'_差_未校准', round(r_her['ahr'] - r_top['ahr'], 4))
    rec(k+'_差_已校准', round(r_her['ahr'] - r_topc['ahr'], 4))

# ───────────────────────────────────────── 9. 她不是我填的
d = float(np.linalg.norm(np.array(p_her) - np.array(P_MINE)))
print(f"\n[9] ‖她 − 我‖ = {d:.4f}")
rec('9_距离', round(d, 4))

os.makedirs('data', exist_ok=True)
json.dump({k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in R.items()},
          open('data/exp101_aibench.json', 'w'), ensure_ascii=False, indent=1)
print("\n已存 data/exp101_aibench.json")
