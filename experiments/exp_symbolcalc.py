#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★89  符号演算与不确定度传播 —— 实验

判据按 ★88 立的第 19 条规矩走：
  ① 建模有没有把权衡写没了
  ② 判据尺度能不能区分"内部峰"和"边界 + 单调"
  ③ 训练分布里那个信号强过噪声没有
"""

from __future__ import annotations
import json, sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core.symbolcalc as S

R = {}
PASS = []
TOL = 0.15          # 外部容差：任务要求的精度，不由她决定


def chk(name, ok, detail=""):
    PASS.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    R[name] = dict(ok=bool(ok), detail=detail)


print("=" * 70)
print("★89  符号演算与不确定度传播")
print("=" * 70)

# ══════════════════════════════════════════════════════
print("\n【一】尺子自检：一阶误差传播 vs 蒙特卡洛")
# ══════════════════════════════════════════════════════
rng = np.random.default_rng(0)
sc = S.ruler_selfcheck(rng, verbose=True)
worst = max(c["rel"] for c in sc)
chk("判据1 一阶传播与蒙特卡洛吻合", worst < 0.02,
    f"最大相对差 {worst:.2%}")

biases = [c["bias"] for c in sc]
chk("判据2 忽略协方差的偏差【方向不定】",
    min(biases) < -0.05 and max(biases) > 0.05,
    f"偏差范围 {min(biases):+.1%} ~ {max(biases):+.1%}")
print('      ★ 方向不定 ⇒ 不能靠“统一乘个系数”修正，只能真的把协方差记下来')

# ══════════════════════════════════════════════════════
print("\n【二】共模 / 竞争：物理建模")
# ══════════════════════════════════════════════════════
sy, ev, B = S.build(seed=0, cm_frac=0.65, chain_len=32)
print(f"      x_i = true_i + b·p_i·c + e_i       p=±1 极性")
print(f"      p 同号 → 共模（同一参考源，源漂一起漂）")
print(f"      p 异号 → 竞争（共享有限资源，此消彼长）")
print(f"      ⇒ Cov(x_i,x_j) = b²·p_i·p_j·σ_iσ_j")

# ══════════════════════════════════════════════════════
print("\n【三】三个旋钮的峰是否都在内部")
# ══════════════════════════════════════════════════════
LAMS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
TAUS = [1, 2, 3, 6, 9, 12, 18, 24, 36, 48, 72, 96]
THS = [0.02, 0.05, 0.08, 0.11, 0.14, 0.16, 0.19, 0.24, 0.30, 0.40, 0.60, 0.90]


def peaks(seed, **kw):
    _, e, _ = S.build(seed, **kw)
    sl = [e(l, 12, 0.16)[0] for l in LAMS]
    st = [e(0.55, t, 0.16)[0] for t in TAUS]
    sh = [e(0.55, 12, t)[0] for t in THS]
    return (LAMS[int(np.argmax(sl))], max(sl), min(sl)), \
           (TAUS[int(np.argmax(st))], max(st), min(st)), \
           (THS[int(np.argmax(sh))], max(sh), min(sh))


pl, pt, ph = peaks(0, cm_frac=0.65, chain_len=32)
chk("判据3 λ（协方差记录密度）峰在内部",
    0 < LAMS.index(pl[0]) < len(LAMS) - 1,
    f"峰 λ={pl[0]:.2f}  峰{pl[1]:+.4f} 谷{pl[2]:+.4f} 跨度{pl[1]-pl[2]:.4f}")
chk("判据4 τ（重标定周期）峰在内部",
    0 < TAUS.index(pt[0]) < len(TAUS) - 1,
    f"峰 τ={pt[0]}  峰{pt[1]:+.4f} 谷{pt[2]:+.4f} 跨度{pt[1]-pt[2]:.4f}")
chk("判据5 θ（接受门槛）峰在内部",
    0 < THS.index(ph[0]) < len(THS) - 1,
    f"峰 θ={ph[0]:.2f}  峰{ph[1]:+.4f} 谷{ph[2]:+.4f} 跨度{ph[1]-ph[2]:.4f}")
print(f"      ★ 峰 θ={ph[0]:.2f} 略高于外部容差 tol={TOL} —— 她留了余量，因为自己估计有偏")

# ══════════════════════════════════════════════════════
print("\n【四】硬依赖（两端对照）")
# ══════════════════════════════════════════════════════
# 依赖1：通道间若无相关，λ 就纯粹是浪费 → 最优应移到 0（边界）
_, e_nocorr, _ = S.build(0, cm_frac=0.65, chain_len=32, correlated=False)
sl_nc = [e_nocorr(l, 12, 0.16)[0] for l in LAMS]
lam_nc = LAMS[int(np.argmax(sl_nc))]
vl, _, _ = pl
chk("判据6a 有关时 λ 峰在内部", vl > 0.0, f"λ*={vl:.2f}")
chk("判据6b 关掉通道相关后 λ 峰移到边界 0",
    lam_nc == 0.0, f"λ* {vl:.2f} → {lam_nc:.2f}")

# 依赖2：若传感器不漂移，标定就纯浪费 → τ 应完全无区分度
sy0, _, _ = S.build(0, cm_frac=0.65, chain_len=32)
sy0.drift = 0.0
st_nodr = [sy0.run(0.55, t, 0.16, tol=TOL)[0] for t in TAUS]
spread_nodr = max(st_nodr) - min(st_nodr)
chk("判据7 关掉漂移后 τ 完全失去区分度",
    spread_nodr < 1e-9,
    f"跨度 {pt[1]-pt[2]:.4f} → {spread_nodr:.2e}")

# ══════════════════════════════════════════════════════
print("\n【五】★ 判据8：正确性的标准不能由她自己定")
# ══════════════════════════════════════════════════════
# 错误做法：correct ⟺ rel_t ≤ θ（θ 既当她的门槛又当正确标准）
def run_selfscored(theta):
    """她自己给自己打分：正确与否也用 θ 判 —— 这是错的，用来对照"""
    tot = 0.0
    for ops, leaves in sy.chains:
        i0, j0 = leaves[0]
        val = S.SymbolSystem._apply(ops[0], sy.true[i0], sy.true[j0])
        g = np.zeros(sy.N)
        da, db = S.SymbolSystem._deriv(ops[0], sy.true[i0], sy.true[j0])
        g[i0] = da; g[j0] = db
        for k in range(1, len(ops)):
            op = ops[k]; li = leaves[k]
            da, db = S.SymbolSystem._deriv(op, val, sy.true[li])
            gn = da * g; gn[li] += db
            val = S.SymbolSystem._apply(op, val, sy.true[li]); g = gn
        amp = np.sqrt(1 + sy.drift * 12)
        Sig = sy.Sigma * amp ** 2
        off = Sig - np.diag(np.diag(Sig))
        Se = np.diag(np.diag(Sig)) + 0.55 * off
        rt = np.sqrt(max(g @ Sig @ g, 0)) / max(abs(val), 1e-9)
        re = np.sqrt(max(g @ Se @ g, 0)) / max(abs(val), 1e-9)
        if re <= theta:
            tot += 1.0 if rt <= theta else -3.0
        else:
            tot -= 0.15
    return tot / len(sy.chains)


self_curve = [run_selfscored(t) for t in THS]
self_peak = THS[int(np.argmax(self_curve))]
chk("判据8 用她自己的 θ 当正确标准 ⇒ θ 单调无峰（对照）",
    self_peak == THS[-1] or self_peak == THS[0],
    f"自评分曲线峰在 θ={self_peak:.2f}（边界）；解耦后峰在 θ={ph[0]:.2f}（内部）")
print("      ★ 这就是 ★55/72/75/77/78/88 的同一族错误：尺子把要测的东西消掉了")

# ══════════════════════════════════════════════════════
print("\n【六】她自己学 —— 学【规则】不是【数字】")
# ══════════════════════════════════════════════════════
# 换身体：传感器老化速率不同（drift），通道结构不同（cm_frac）
# 她能看见的量：自己读出来的噪声水平 p̂（不需要 ground truth）
TRAIN = [(sd, df, cm) for df in (0.006, 0.014, 0.024)
         for cm in (0.45, 0.65) for sd in range(3)]
HELD = [(sd, df, cm) for df in (0.010, 0.019, 0.030)
        for cm in (0.55, 0.80) for sd in range(50, 54)]

BETS = [0.0, 0.3, 0.6, 0.8, 1.0, 1.3, 1.8]
T0S = [0.06, 0.10, 0.14, 0.18, 0.24]
TREF = [3.0, 6.0, 10.0, 16.0, 26.0]
R_REF = 0.014          # 参考漂移率（训练时见过的中位水平）


def drift_hat(sysm, tau_obs=60.0, n_rep=24):
    """
    她自己测的漂移率 —— 不需要 ground truth。
      刚标定后连读两次 → σ̂₀
      隔 tau_obs 再连读两次 → σ̂(τ)
      因为 σ² ∝ (1 + drift·τ)  ⇒  drift̂ = (σ̂(τ)²/σ̂₀² − 1) / τ

    ★ 观测窗口必须够长：drift=0.01 时 10 步只涨 10%，
      而单次 σ̂ 的相对误差就有 ~1/√(2N) ≈ 10% —— 信号被噪声淹没。
      （第一版就是这么废掉的：全部测成 0.0000）
      拉长窗口到 60 步 + 重复 24 次取平均，信号才浮出来。
    """
    s0 = sysm.sigma0
    amp = np.sqrt(max(1.0 + sysm.drift * tau_obs, 1e-9))
    r0 = []; rt = []
    for _ in range(n_rep):
        a1 = sysm.true + sysm.rng.normal(0, s0, sysm.N)
        a2 = sysm.true + sysm.rng.normal(0, s0, sysm.N)
        r0.append(np.var(a1 - a2))
        b1 = sysm.true + sysm.rng.normal(0, s0 * amp, sysm.N)
        b2 = sysm.true + sysm.rng.normal(0, s0 * amp, sysm.N)
        rt.append(np.var(b1 - b2))
    r = float(np.mean(rt) / max(np.mean(r0), 1e-18))
    return float(max((r - 1.0) / tau_obs, 1e-6))


_cache = {}


def env(seed, drift, cm):
    key = (seed, round(drift, 5), round(cm, 5))
    if key not in _cache:
        _cache[key] = S.build(seed, cm_frac=cm, chain_len=32, drift=drift,
                              n_query=48,
                              budget=(90.0 * (32 * 31 / 2) * 0.55 + 260.0 * 48 / 12.0) * 0.95)
    return _cache[key]


def policy_score(params, envs):
    """
    ★ 学的是【规则】不是【数字】：
        τ = τ_ref · (r_ref / r̂)^β          r̂ = 她自己测出的漂移率
      β=1 对应解析预测 τ ∝ 1/drift（保持 σ² 恒定 ⇒ drift·τ 恒定）
      β=0 就是记忆派：不管换什么身体都用同一个 τ
    """
    lam, tref, t0, beta = params
    out = []
    for sd, df, cm in envs:
        syx, e, _ = env(sd, df, cm)
        rh = drift_hat(syx)
        tau = float(np.clip(tref * (R_REF / rh) ** beta, 1.0, 96.0))
        out.append(e(lam, tau, t0)[0])
    return float(np.mean(out))


def learn(envs=TRAIN):
    lam, tref, t0, beta = 0.5, 10.0, 0.14, 0.0     # 盲起点：β=0（不会随身体调整）
    for _ in range(5):
        lam = max(LAMS, key=lambda x: policy_score((x, tref, t0, beta), envs))
        tref = max(TREF, key=lambda x: policy_score((lam, x, t0, beta), envs))
        t0 = max(T0S, key=lambda x: policy_score((lam, tref, x, beta), envs))
        beta = max(BETS, key=lambda x: policy_score((lam, tref, t0, x), envs))
    return float(lam), float(tref), float(t0), float(beta)


hers = learn()
hl, htr, ht0, hb = hers
print(f"  她学的：λ={hl:.2f}  τ_ref={htr:.1f}  θ={ht0:.2f}  β={hb:+.2f}")
print(f"      τ = τ_ref · (r_ref/r̂)^β   —— β 接近 1 即解析预测 τ ∝ 1/漂移率")
print(f"      β=0 = 记忆派：换身体也用同一个 τ")

# 她实际在不同漂移率身体上取用的 τ
print("\n  她在三种老化速率的身体上实际取用的 τ：")
for df in (0.010, 0.019, 0.030):
    syx, _, _ = env(50, df, 0.55)
    rh = drift_hat(syx)
    tau = float(np.clip(htr * (R_REF / rh) ** hb, 1.0, 96.0))
    print(f"      drift={df:.3f}  她测到 r̂={rh:.4f}  →  τ={tau:.1f}")

mine = (1.0, 24.0, TOL, 0.0)        # 我的直觉：协方差全记、标定周期固定、门槛=容差
mem = (hl, htr, ht0, 0.0)           # 记忆派：同样的参数但 β=0，不会随身体调整
rng2 = np.random.default_rng(11)
rand = [(float(rng2.choice(LAMS)), float(rng2.choice(TREF)),
         float(rng2.choice(T0S)), float(rng2.choice(BETS))) for _ in range(40)]

h_hold = policy_score(hers, HELD)
m_hold = policy_score(mine, HELD)
mem_hold = policy_score(mem, HELD)
r_hold = float(np.mean([policy_score(p, HELD) for p in rand]))

print(f"\n  held-out（换身体：老化速率 0.010/0.019/0.030，共 24 个新环境）")
print(f"    她学的(规则)   {h_hold:+.4f}")
print(f"    记忆派(β=0)    {mem_hold:+.4f}")
print(f"    我填的         {m_hold:+.4f}")
print(f"    随机           {r_hold:+.4f}")

chk("判据9 她学的 > 我填的", h_hold > m_hold,
    f"{h_hold:+.4f} vs {m_hold:+.4f}  差 +{h_hold-m_hold:.4f}")
chk("判据10 她学的 > 记忆派（学规则 vs 记数字）",
    h_hold > mem_hold + 1e-9,
    f"{h_hold:+.4f} vs {mem_hold:+.4f}  差 +{h_hold-mem_hold:.4f}")
chk("判据11 她学的 > 随机", h_hold > r_hold,
    f"{h_hold:+.4f} vs {r_hold:+.4f}  差 +{h_hold-r_hold:.4f}")
dist = abs(hl - mine[0]) + abs(htr - mine[1]) / 24.0 + abs(ht0 - mine[2]) * 5
chk("判据12 她的解 ≠ 我填的", dist > 0.3, f"‖她−我‖={dist:.3f}")

# ══════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"通过 {sum(PASS)}/{len(PASS)}")
print("=" * 70)

R["_summary"] = dict(pass_n=int(sum(PASS)), total=int(len(PASS)),
                     ruler=[{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                             for k, v in c.items()} for c in sc],
                     peaks=dict(lam=pl[0], tau=pt[0], theta=ph[0]),
                     hers=dict(lam=hl, tau_ref=htr, theta=ht0, beta=hb),
                     mine=dict(lam=mine[0], tau_ref=mine[1], theta=mine[2], beta=0.0),
                     held=dict(hers=h_hold, mem=mem_hold, mine=m_hold, rand=r_hold))
with open("data/exp89_symbolcalc.json", "w") as f:
    json.dump(R, f, ensure_ascii=False, indent=2, default=str)
print("已写 data/exp89_symbolcalc.json")
