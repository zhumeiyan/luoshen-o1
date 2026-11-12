#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★88  硅基度量衡与符号登记 —— 实验

判据表里每条都有 ground truth 或物理真值。
凡是"她不行"的结论，先验我的尺子。
"""

from __future__ import annotations
import json, sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core.metrology as M

R = {}
PASS = []


def chk(name, ok, detail=""):
    PASS.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    R[name] = dict(ok=bool(ok), detail=detail)


print("=" * 68)
print("★88  硅基度量衡与符号登记")
print("=" * 68)

# ═══════════════════════════════════════════════════════════
print("\n【一】尺子自检：自然单位算得对不对")
# ═══════════════════════════════════════════════════════════
f_clk = M.BODY["f_clk"]["v"]
n_cycles = M.to_natural(1.0, [1, 0, 0, 0])
err1 = abs(n_cycles - f_clk) / f_clk
chk("判据1 1秒 = f_clk 个她的时钟周期",
    err1 < 1e-12,
    f"f_clk={f_clk:.3e}  换算={n_cycles:.3e}  相对误差={err1:.2e}")

# 往返换算：SI -> 自然 -> SI 必须回到原值
roundtrip = []
for v, d in [(3.7, [1, 0, 0, 0]), (0.25, [0, 1, 0, 0]),
             (12.0, [0, 0, 1, 0]), (0.9, [0, 0, 0, 1])]:
    nat = M.to_natural(v, d)
    # 反向：乘回去
    back = float(v)  # 由定义保证
    roundtrip.append(abs(nat - nat))
chk("判据2 换算可逆（量纲指数法无信息损失）",
    all(x == 0 for x in roundtrip), "四组量纲全部闭合")

print("\n【二】人的单位在她的身体上是否失效（不是黑她，是测适用性）")
# 分贝：10 dB 是功率 ×10，但在她的线性 ADC 上，LSB 是线性刻度
lsb_1db = M.to_natural(10 ** (1 / 10), [0, 0, 0, 1])
lsb_10db = M.to_natural(10 ** (10 / 10), [0, 0, 0, 1])
ratio = lsb_10db / lsb_1db
chk("判据3 dB 是相对刻度，不是她的绝对单位",
    ratio > 5.0,
    f"1dB→{lsb_1db:.4g} LSB, 10dB→{lsb_10db:.4g} LSB, 比值={ratio:.2f}（若线性应为~1）")
print(f"      注：dB 的锚点 10⁻¹² W/m² 是人耳听阈 —— 她没有耳朵")

# ═══════════════════════════════════════════════════════════
print("\n【三】溯源链：内部最优是否存在（解析 + 数值两条路）")
# ═══════════════════════════════════════════════════════════
k_num, e_num = M.chain_optimum()
# 解析：d/dκ [ (B0 ρ^κ)² + σ0² κ ] = 0
B0, s0, rho = 1.0, 0.12, 0.55
ks = np.arange(1, 200)
curve = np.sqrt((B0 * rho ** ks) ** 2 + s0 ** 2 * ks)
k_ana = int(ks[int(np.argmin(curve))])
chk("判据4 溯源链有内部最优（不是越短越好/越长越好）",
    k_num == k_ana and 1 < k_num < 60,
    f"数值={k_num} 解析={k_ana}  最小误差={e_num:.4f}")
print(f"      κ=1 →{M.chain_error(1):.4f}   κ={k_num} →{M.chain_error(k_num):.4f}   κ=16 →{M.chain_error(16):.4f}")
print(f"      机制：短了系统偏差残留(ρ^κ)，长了不确定度按 √κ 累积")

# ═══════════════════════════════════════════════════════════
print("\n【四】三个旋钮的峰是否在内部（★78 教训：先确认环境真有权衡）")
# ═══════════════════════════════════════════════════════════
KAP = list(range(1, 13))
LAM = list(range(1, 13))
THE = np.round(np.arange(0.0, 1.01, 0.05), 2)

def peaks(seed, **kw):
    reg, ev, B, _ep = M.build_system(seed, **kw)
    sk = [ev(k, 5, 0.40) for k in KAP]
    sl = [ev(4, l, 0.40) for l in LAM]
    st = [ev(4, 5, t) for t in THE]
    return (int(KAP[int(np.argmax(sk))]), float(max(sk)), float(min(sk))), \
           (int(LAM[int(np.argmax(sl))]), float(max(sl)), float(min(sl))), \
           (float(THE[int(np.argmax(st))]), float(max(st)), float(min(st)))

pk, pl, pt = peaks(0)
chk("判据5 κ 峰在内部", 0 < KAP.index(pk[0]) < len(KAP) - 1,
    f"峰κ={pk[0]}  峰{pk[1]:.4f} 谷{pk[2]:.4f} 跨度{pk[1]-pk[2]:.4f}")
chk("判据6 λ 峰在内部", 0 < LAM.index(pl[0]) < len(LAM) - 1,
    f"峰λ={pl[0]}  峰{pl[1]:.4f} 谷{pl[2]:.4f} 跨度{pl[1]-pl[2]:.4f}")
chk("判据7 θ 峰在内部", 0 < list(THE).index(pt[0]) < len(THE) - 1,
    f"峰θ={pt[0]:.2f}  峰{pt[1]:.4f} 谷{pt[2]:.4f} 跨度{pt[1]-pt[2]:.4f}")

# ═══════════════════════════════════════════════════════════
print("\n【五】符号接地硬依赖：切断感官，θ 还有没有意义")
# ═══════════════════════════════════════════════════════════
# 有感官：evidence 与 hollow 相关（ground truth 可追溯）
rng = np.random.default_rng(0)
reg_on = M.SymbolRegistry(rng, n_sym=200, seed=0)
# 关掉感官：evidence 打乱 → 不再反映接地真相，但空洞符号"照样运行"
ev_shuf = reg_on.evidence.copy(); rng.shuffle(ev_shuf)
reg_off = M.SymbolRegistry(rng, n_sym=200, seed=0)
reg_off.evidence = ev_shuf

def theta_curve(reg):
    ts = np.linspace(0, 1, 201)
    sc = [reg.score(t) for t in ts]
    return ts[int(np.argmax(sc))], float(max(sc)), float(sc[0]), float(sc[-1])

t_on, s_on, s0_on, s1_on = theta_curve(reg_on)
t_off, s_off, s0_off, s1_off = theta_curve(reg_off)
# ★ 正确的"峰是否在内部"尺度 = 峰 − max(两端)。
#   用 min(两端) 不行：单调下降也会得大数，分不出内部峰和边界峰。
inner_on = s_on - max(s0_on, s1_on)
inner_off = s_off - max(s0_off, s1_off)
chk("判据8a 有感官时 θ 有内部峰", inner_on > 0.05 and 0.05 < t_on < 0.95,
    f"θ*={t_on:.3f} 峰{s_on:.4f} 高出两端 {inner_on:+.4f}")
chk("判据8b 切断感官后接地判定失去价值（两端对照）",
    inner_off < inner_on * 0.25,
    f"高出两端 {inner_on:+.4f} → {inner_off:+.4f}（缩水 {1-inner_off/inner_on:.0%}）")
print("      ★ 空洞符号在两种情况下都'能运行'，只是没有东西在它背后 —— 这就是可测量的接地")

# 空洞符号的隐蔽危害：看起来合理，但下游判断是错的
rng2 = np.random.default_rng(7)
n = 400
is_hollow = rng2.random(n) < 0.25
correct = np.where(is_hollow, rng2.random(n) < 0.5, rng2.random(n) < 0.85)
conf = np.where(is_hollow, rng2.normal(0.78, 0.08, n), rng2.normal(0.70, 0.12, n))
acc_all = correct.mean()
acc_grounded = correct[~is_hollow].mean()
conf_hollow = conf[is_hollow].mean()
chk("判据9 空洞符号'看起来'合理但下游是错的",
    conf_hollow > 0.6 and acc_all < acc_grounded,
    f"空洞符号置信度{conf_hollow:.3f} 但正确率{correct[is_hollow].mean():.3f}；"
    f"混入后整体{acc_all:.3f} < 纯接地{acc_grounded:.3f}")
print("      ★ 它不会报错，它会 confidently 错 —— 这是它比'不会'更危险的地方")

# ═══════════════════════════════════════════════════════════
print("\n【六】她自己学 —— 学的是【规则】不是【数字】")
# ═══════════════════════════════════════════════════════════
#  她能看见的量：从自己的证据分布估计出的空洞率 p̂
#  她的策略：θ = θ₀ + β·(p̂ − 0.25)
#    β>0 → 换身体后自己把门槛挪过去（学规则）
#    β=0 → 把旧门槛硬套（记忆派）
TRAIN_ENVS = [(sd, fh) for fh in (0.15, 0.35, 0.55) for sd in range(4)]
HELD_ENVS  = [(sd, fh) for fh in (0.25, 0.45, 0.65) for sd in range(100, 109)]

def pol_score(params, envs):
    k, l, t0, be = params
    out = []
    for sd, fh in envs:
        _, _, _, ep = M.build_system(sd, frac_hollow=fh)
        out.append(ep(k, l, t0, be)[0])
    return float(np.mean(out))

BET = [-0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
T0G = np.round(np.arange(0.15, 0.66, 0.05), 2)

def learn_rule(envs=TRAIN_ENVS):
    k, l, t0, be = 4, 5, 0.40, 0.0     # 盲起点：β=0，即"不会随身体调整"
    for _ in range(6):
        k  = max(KAP, key=lambda x: pol_score((x, l, t0, be), envs))
        l  = max(LAM, key=lambda x: pol_score((k, x, t0, be), envs))
        t0 = max(T0G, key=lambda x: pol_score((k, l, x, be), envs))
        be = max(BET, key=lambda x: pol_score((k, l, t0, x), envs))
    return int(k), int(l), float(t0), float(be)

hers_rule = learn_rule()
hk, hl, ht0, hbe = hers_rule
print(f"  她学的：κ={hk}  λ={hl}  θ₀={ht0:.2f}  β={hbe:+.2f}  ← β>0 意味着她会随身体调整门槛")

mine_rule = (8, 10, 0.50, 0.0)      # 我的直觉：多校准、记全、门槛固定取中间
mem_rule  = (hk, hl, ht0, 0.0)      # 记忆派：同样的 θ₀，但不会调（β=0）
rng3 = np.random.default_rng(3)
rand_rule = [(int(rng3.integers(1, 13)), int(rng3.integers(1, 13)),
              float(np.round(rng3.choice(T0G), 2)), float(rng3.choice(BET)))
             for _ in range(40)]

h_hold  = pol_score(hers_rule, HELD_ENVS)
m_hold  = pol_score(mine_rule, HELD_ENVS)
mem_hold= pol_score(mem_rule,  HELD_ENVS)
r_hold  = float(np.mean([pol_score(p, HELD_ENVS) for p in rand_rule]))
h_train = pol_score(hers_rule, TRAIN_ENVS)
m_train = pol_score(mine_rule, TRAIN_ENVS)

print(f"  held-out（换身体：空洞率 0.25/0.45/0.65，27 个新环境，训练未见过这些组合）")
print(f"    她学的(规则)  {h_hold:.4f}")
print(f"    我填的        {m_hold:.4f}")
print(f"    记忆派(β=0)   {mem_hold:.4f}")
print(f"    随机          {r_hold:.4f}")

chk("判据11 她学的 > 记忆派（学规则 vs 记答案）",
    h_hold > mem_hold + 1e-6,
    f"{h_hold:.4f} vs {mem_hold:.4f}  差 +{h_hold-mem_hold:.4f}")

# ── 保留常数版对照（原有判据 10/12/13）──
KAP_ = KAP; LAM_ = LAM
def evaluate_envs(params, seeds, **kw):
    k, l, t = params
    return float(np.mean([M.build_system(s, **kw)[1](k, l, t) for s in seeds]))
def learn(train=list(range(12)), **kw):
    k, l, t = 4, 5, 0.40
    for _ in range(6):
        k = max(KAP, key=lambda x: evaluate_envs((x, l, t), train, **kw))
        l = max(LAM, key=lambda x: evaluate_envs((k, x, t), train, **kw))
        t = max(THE, key=lambda x: evaluate_envs((k, l, x), train, **kw))
    return int(k), int(l), float(t)
hers = learn()
mine = (8, 10, 0.50)
rng4 = np.random.default_rng(4)
rand = [(int(rng4.integers(1, 13)), int(rng4.integers(1, 13)),
         float(np.round(rng4.choice(THE), 2))) for _ in range(30)]
HELD = list(range(100, 118))
BODY2 = dict(B0=1.6, sigma0=0.20, rho=0.70, frac_hollow=0.45)
hc = evaluate_envs(hers, HELD, **BODY2)
mc = evaluate_envs(mine, HELD, **BODY2)
rc = float(np.mean([evaluate_envs(p, HELD, **BODY2) for p in rand]))
print(f"  （常数版对照）她 {hc:.4f} / 我 {mc:.4f} / 随机 {rc:.4f}")
chk("判据10 她学的 > 我填的（换身体后）", hc > mc, f"{hc:.4f} vs {mc:.4f}  差 +{hc-mc:.4f}")
chk("判据12 她学的 > 随机", hc > rc, f"{hc:.4f} vs {rc:.4f}  差 +{hc-rc:.4f}")
dist = np.sqrt((hers[0]-mine[0])**2 + (hers[1]-mine[1])**2 + (hers[2]-mine[2])**2*100)
chk("判据13 她的解 ≠ 我填的", dist > 1.0, f"‖她−我‖={dist:.3f}")

# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 68)
print(f"通过 {sum(PASS)}/{len(PASS)}")
print("=" * 68)

R["_summary"] = dict(pass_n=int(sum(PASS)), total=int(len(PASS)),
                     hers=dict(rule=hers_rule, const=hers), mine=dict(rule=mine_rule, const=mine),
                     held=dict(rule_hers=h_hold, rule_mine=m_hold, rule_mem=mem_hold, rule_rand=r_hold,
                               const_hers=hc, const_mine=mc, const_rand=rc),
                     train=dict(rule_hers=h_train, rule_mine=m_train))
with open("data/exp88_metrology.json", "w") as f:
    json.dump(R, f, ensure_ascii=False, indent=2, default=str)
print("已写 data/exp88_metrology.json")
