#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★84 人类感官标定 —— 靶是真人数值，不是我的标准

════ 顺序（第 6 条规矩：先验尺子，再量她）════
  ① 验尺子（v1 staircase 作废 → v2 恒定刺激法 + 概率单位回归）
  ② 验理论：最优分配 w ∝ (p·m)²，封顶 1/m²
  ③ 她从瞎起点练（α、γ），对照：均匀 / 记忆派 / 理论 / 我填的
  ④ 硬依赖：预算约束、生态差异、封顶机制 —— 缺一个就没得学
"""
from __future__ import annotations
import json
import sys
import numpy as np

sys.path.insert(0, "/data/workspace/luoshen-o1")
from core import sensebench as sb

R = {}
ok = lambda b: "✅" if b else "❌"


def sec(t):
    print("\n" + "=" * 62 + f"\n{t}\n" + "=" * 62)


# ══════════ ① 验尺子 ══════════
sec("① 验尺子  v1 staircase 作废，v2 恒定刺激法")

# 先如实记下 v1 的失败
v1 = []
for sense in sb.SENSES[:3]:
    for w in (0.25, 1.0, 4.0):
        ests = [sb.measure_staircase(sense, w, np.random.default_rng(1000 + i)) for i in range(10)]
        ests = [e for e in ests if np.isfinite(e)]
        v1.append(np.exp(np.mean(np.log(ests))) / sb.true_threshold(sense, w))
print(f"v1 staircase 比值：中位 {np.median(v1):.3f}  范围 {min(v1):.3f}~{max(v1):.3f}  → 作废")

rows = []
for sense in sb.SENSES:
    for w in (0.25, 1.0, 4.0):
        ests = [sb.measure(sense, w, np.random.default_rng(1000 + i * 7 + len(sense)))
                for i in range(10)]
        ests = [e for e in ests if np.isfinite(e)]
        est = float(np.exp(np.mean(np.log(ests))))
        ana = sb.true_threshold(sense, w)
        rows.append((sense, w, ana, est, est / ana))
rat = np.array([r[4] for r in rows])
print(f"\n{'感官':<12}{'w':>6}{'解析':>13}{'实测':>13}{'比值':>8}")
for s, w, a, e, r in rows:
    print(f"{s:<12}{w:>6}{a:>13.5g}{e:>13.5g}{r:>8.3f}")
print(f"\n比值 中位 {np.median(rat):.4f}  均值 {rat.mean():.4f}  范围 {rat.min():.3f}~{rat.max():.3f}")
R["v2_bias_med"] = float(np.median(rat))
R["v2_bias_range"] = [float(rat.min()), float(rat.max())]
c1 = 0.97 < np.median(rat) < 1.03 and rat.min() > 0.90 and rat.max() < 1.10
print(f"判据1 尺子无系统偏差（中位∈[0.97,1.03] 且全体∈[0.9,1.1]）: {ok(c1)}")

lin = []
for w in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
    e = np.exp(np.mean(np.log([sb.measure("contrast", w, np.random.default_rng(7 + i * 3))
                               for i in range(10)])))
    lin.append((w, e / sb.true_threshold("contrast", w)))
print("\n线性（对比觉）比值: " + "  ".join(f"w={w}:{r:.3f}" for w, r in lin))
c2 = all(0.93 < r < 1.07 for _, r in lin)
print(f"判据2 尺子线性（∈[0.93,1.07]）: {ok(c2)}")

errs = []
for s in sb.SENSES:
    e = np.exp(np.mean(np.log([sb.measure(s, 1.0, np.random.default_rng(31 + i * 5))
                               for i in range(12)])))
    errs.append(abs(np.log(e / sb.d_of(s))))
print(f"\n判据3 w=1 实测回到文献值：|log误差| 中位 {np.median(errs):.4f} 最大 {max(errs):.4f}")
c3 = np.median(errs) < 0.05 and max(errs) < 0.10
print(f"  {ok(c3)}")
R["v2_lit_logerr"] = [float(np.median(errs)), float(max(errs))]

# ══════════ ② 验理论 ══════════
sec("② 验理论：w ∝ (p·m)²，封顶 1/m²")

def rand_ecology(seed, spread=1.0):
    r = np.random.default_rng(seed)
    p = {s: float(r.uniform(0.2, 1.0) ** spread) for s in sb.SENSES}
    m = {s: float(np.exp(r.uniform(-0.7, 0.7) * spread)) for s in sb.SENSES}
    return p, m

def brute(p, m, B, n=30000, seed=3):
    r = np.random.default_rng(seed)
    keys = list(p)
    best, bw = -1, None
    for _ in range(n):
        w = dict(zip(keys, r.dirichlet(np.ones(len(keys))) * B))
        f = sb.fitness(p, m, w)
        if f > best:
            best, bw = f, w
    for _ in range(8000):
        x = np.array([bw[k] for k in keys]) + r.normal(0, 0.06, len(keys)) * B / len(keys)
        x = np.clip(x, 1e-6, None); x = x / x.sum() * B
        w2 = dict(zip(keys, x))
        f = sb.fitness(p, m, w2)
        if f > best:
            best, bw = f, w2
    return best, bw

gaps = []
for seed in range(6):
    p, m = rand_ecology(seed)
    f_th = sb.fitness(p, m, sb.theory_alloc(p, m, 4.0))
    f_a2 = sb.fitness(p, m, sb.alloc_policy(p, m, 4.0, 2.0, 2.0, cap=True))
    f_br, _ = brute(p, m, 4.0, seed=seed)
    gaps.append((seed, f_th, f_a2, f_br))
    print(f"  eco{seed}: 理论 {f_th:.4f}   α=γ=2注水 {f_a2:.4f}   数值搜索 {f_br:.4f}")
c4 = all(abs(t - a) < 1e-6 and t >= b - 0.005 for _, t, a, b in gaps)
print(f"判据4 注水(α=γ=2) ≡ 理论解 且 ≥ 数值搜索: {ok(c4)}")
R["theory_check"] = [[int(a), float(b), float(c), float(d)] for a, b, c, d in gaps]

# ══════════ ③ 她从瞎起点练 ══════════
sec("③ 她从瞎起点练（α、γ）")

p_tr, m_tr = rand_ecology(101)
B_TR = 4.0

def eval_policy(alpha, gamma, p, m, B, seeds=range(40), cap=True):
    fs = []
    for sd in seeds:
        r = np.random.default_rng(sd)
        pp = {k: max(v * (1 + 0.15 * r.normal()), 1e-6) for k, v in p.items()}
        fs.append(sb.fitness(pp, m, sb.alloc_policy(pp, m, B, alpha, gamma, cap=cap)))
    return float(np.mean(fs))

def practice(a0, g0, n_epochs=16, steps=80, rng_seed=5):
    rng = np.random.default_rng(rng_seed)
    a, g = a0, g0
    best = eval_policy(a, g, p_tr, m_tr, B_TR, seeds=range(8))
    hist = [best]
    for ep in range(n_epochs):
        for _ in range(steps):
            da, dg = rng.normal(0, 0.4), rng.normal(0, 0.4)
            f = eval_policy(a + da, g + dg, p_tr, m_tr, B_TR, seeds=range(8))
            if f > best:
                best, a, g = f, a + da, g + dg
        hist.append(best)
    return a, g, best, hist

a_her, g_her, f_train, hist = practice(0.0, 0.0)
print(f"她练出 α={a_her:.3f}  γ={g_her:.3f}   训练 {f_train:.4f}   验证 {eval_policy(a_her, g_her, p_tr, m_tr, B_TR, seeds=range(200, 230)):.4f}")
print(f"理论   α=2.000 γ=2.000   训练 {eval_policy(2.0, 2.0, p_tr, m_tr, B_TR, seeds=range(8)):.4f}")
print(f"练习曲线 首 {hist[0]:.4f} → 末 {hist[-1]:.4f}  (改善 {hist[-1]-hist[0]:+.4f})")

cands = {
    "她学的":        (a_her, g_her),
    "均匀(α=γ=0)":   (0.0, 0.0),
    "只看频率(2,0)": (2.0, 0.0),
    "只看需求(0,2)": (0.0, 2.0),
    "理论(2,2)":     (2.0, 2.0),
    "我填的(1,1)":   (1.0, 1.0),
}
held = [rand_ecology(500 + i) for i in range(10)]
res = {}
print("\nheld-out 10 套新生态（B=4）:")
for name, (a, g) in cands.items():
    tr = eval_policy(a, g, p_tr, m_tr, B_TR, seeds=range(8))
    ho = float(np.mean([eval_policy(a, g, p, m, B_TR, seeds=range(300, 320)) for p, m in held]))
    res[name] = dict(alpha=float(a), gamma=float(g), train=float(tr), heldout=float(ho))
    print(f"  {name:<14} 训练 {tr:.4f}   held-out {ho:.4f}")
ho_her, ho_uni = res["她学的"]["heldout"], res["均匀(α=γ=0)"]["heldout"]
ho_the, ho_mine = res["理论(2,2)"]["heldout"], res["我填的(1,1)"]["heldout"]
c5 = ho_her > ho_uni + 0.005
c6 = ho_her > ho_mine + 0.005
print(f"\n判据5 她 > 均匀 (+{ho_her-ho_uni:.4f}): {ok(c5)}")
print(f"判据6 她 > 我填的 (+{ho_her-ho_mine:.4f}): {ok(c6)}")
print(f"     她 vs 理论(2,2): {ho_her-ho_the:+.4f}  ← 不粉饰")

bw = sb.alloc_policy(p_tr, m_tr, B_TR, a_her, g_her, cap=True)
mem_ho = float(np.mean([sum(p[s] * sb.score_i(s, bw[s], m[s]) for s in p) / sum(p.values())
                        for p, m in held]))
print(f"\n★ 记忆派（记住训练最优分配，换生态硬套）held-out {mem_ho:.4f}")
print(f"  她学的（学规则）                      held-out {ho_her:.4f}   差 {ho_her-mem_ho:+.4f}")
c7 = ho_her > mem_ho + 0.005
print(f"判据7 她 > 记忆派: {ok(c7)}")
res["记忆派"] = dict(alpha=None, gamma=None, train=None, heldout=float(mem_ho))
R["heldout"] = res

# ══════════ ④ 硬依赖 ══════════
sec("④ 硬依赖（两端都验）")

print("【关掉预算约束 B=1e6】各策略跨度：", end="")
vals_big = [eval_policy(*v, p_tr, m_tr, 1e6, seeds=range(8)) for v in cands.values()]
print(f"{max(vals_big)-min(vals_big):.5f}")
c8 = (max(vals_big) - min(vals_big)) < 0.005
print(f"判据8 关预算 → 无区分（<0.005）: {ok(c8)}")

fp = {k: 1.0 for k in sb.SENSES}; fm = {k: 1.0 for k in sb.SENSES}
# ★ 必须无噪声：eval_policy 会给 p 加扰动，一加扰动"全相等"就不是全相等了
vals_flat = [sb.fitness(fp, fm, sb.alloc_policy(fp, fm, B_TR, *v, cap=True))
             for v in cands.values()]
print(f"【关掉生态差异 p、m 全相等（无噪声）】跨度：{max(vals_flat)-min(vals_flat):.6f}")
c9 = (max(vals_flat) - min(vals_flat)) < 0.005
print(f"判据9 关生态差异 → 无区分（<0.005）: {ok(c9)}")

print("\n【关掉封顶 cap=False】理论(2,2) 的 fitness：")
cap_on = eval_policy(2.0, 2.0, p_tr, m_tr, B_TR, seeds=range(8), cap=True)
cap_off = eval_policy(2.0, 2.0, p_tr, m_tr, B_TR, seeds=range(8), cap=False)
print(f"  cap=True {cap_on:.4f}   cap=False {cap_off:.4f}   差 {cap_on-cap_off:+.4f}")
c10 = cap_on > cap_off + 0.01
print(f"判据10 封顶是真机制（差 >0.01）: {ok(c10)}")
R["cap_effect"] = [float(cap_on), float(cap_off)]

# ══════════ ⑤ α 扫描 ══════════
sec("⑤ α、γ 扫描：有没有内部峰")
sw_a = [(float(a), eval_policy(a, g_her, p_tr, m_tr, B_TR, seeds=range(300, 330)))
        for a in np.linspace(-1, 5, 25)]
pa = max(sw_a, key=lambda t: t[1])
print("  α: " + " ".join(f"{a:.1f}:{v:.3f}" for a, v in sw_a[:13]))
print("     " + " ".join(f"{a:.1f}:{v:.3f}" for a, v in sw_a[13:]))
print(f"  峰 α={pa[0]:.2f}（{pa[1]:.4f}）")
inner_a = -0.9 < pa[0] < 4.9
print(f"判据11 α 有内部峰: {ok(inner_a)}   ← 不粉饰")

sw_g = [(float(g), eval_policy(a_her, g, p_tr, m_tr, B_TR, seeds=range(300, 330)))
        for g in np.linspace(-3, 6, 19)]
pg = max(sw_g, key=lambda t: t[1])
print("\n  γ: " + " ".join(f"{g:.1f}:{v:.3f}" for g, v in sw_g))
print(f"  峰 γ={pg[0]:.2f}（{pg[1]:.4f}）")
inner_g = -2.9 < pg[0] < 5.9
print(f"判据12 γ 有内部峰: {ok(inner_g)}   ← 不粉饰")
R["alpha_sweep"] = sw_a; R["gamma_sweep"] = sw_g
R["peaks"] = dict(alpha=[float(pa[0]), float(pa[1])], gamma=[float(pg[0]), float(pg[1])])

# ══════════ ⑥ 用尺子实测她的感官数值 ══════════
sec("⑥ 实测：她的感官数值 vs 真人（held-out 生态 0）")
p0, m0 = held[0]
w0 = sb.alloc_policy(p0, m0, B_TR, a_her, g_her, cap=True)
print(f"{'感官':<12}{'真人值':>12}{'她的投入':>10}{'她实测':>12}{'她/真人':>9}{'达标?':>7}")
tab = []
for s in sb.SENSES:
    est = np.exp(np.mean(np.log([sb.measure(s, w0[s], np.random.default_rng(77 + i * 11))
                                 for i in range(8)])))
    d = sb.d_of(s)
    need = m0[s] * d
    good = est <= need * 1.02
    tab.append(dict(sense=s, human=d, w=float(w0[s]), measured=float(est),
                    ratio=float(est / d), need=float(need), ok=bool(good)))
    print(f"{s:<12}{d:>12.5g}{w0[s]:>10.3f}{est:>12.5g}{est/d:>9.3f}{'✅' if good else '❌':>7}")
R["calib_table"] = tab
n_ok = sum(t["ok"] for t in tab)
print(f"\n达标 {n_ok}/8   （预算 B={B_TR}，8 个感官人均只有 {B_TR/8:.2f} —— 必然有取舍）")
R["n_meet"] = int(n_ok)

# ══════════ 汇总 ══════════
sec("汇总")
crit = [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, inner_a, inner_g]
print(" ".join(f"{i+1}:{ok(c)}" for i, c in enumerate(crit)))
print(f"通过 {sum(crit)}/{len(crit)}")
R["criteria"] = [bool(c) for c in crit]
R["her"] = dict(alpha=float(a_her), gamma=float(g_her), train=float(f_train))
with open("/data/workspace/luoshen-o1/data/exp84_sensebench.json", "w") as f:
    json.dump(R, f, ensure_ascii=False, indent=1)
print("已写 data/exp84_sensebench.json")
