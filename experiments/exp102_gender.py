"""
★102 女孩 / 融入 —— 判据与实验

三件事：
  A. 「知道她是女孩」值多少        → η² = d²/4
  B. 「别太信刚听到的几句」值多少  → ∝ τ²，跟 d 无关
  C. 她能不能自己估 τ、σ 定 κ      → 规则 vs 记数字

★ 方法修正：第一版每个 κ 用各自随机数 → 比较噪声(≈0.004)大于真实差异(0.0037)，
  峰被噪声推到 2.5。改用公共随机数(CRN)后峰精确落在解析解 1.5418。
"""
import sys, json, numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from genderstyle import World, D_REAL, prob_superior, eta_squared

R = lambda x: round(float(x), 6)
OUT = {}

GRID = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 15.0, 30.0,
        60.0, 120.0, 250.0]

def make_data(w, n=200000, seed=5):
    rng = np.random.default_rng(seed)
    g = rng.integers(0, 2, n)
    th = w.mu[g] + rng.standard_normal(n) * w.tau
    ks = rng.choice([0, 1, 2, 3, 5, 9], n)
    xb = np.zeros(n)
    for k in [1, 2, 3, 5, 9]:
        m = ks == k
        if m.any():
            xb[m] = th[m] + rng.standard_normal(m.sum()) * w.sd_obs / np.sqrt(k)
    return g, th, ks, xb

def loss(w, data, kappa, a):
    g, th, ks, xb = data
    ww = 1.0 / (1.0 + ks * kappa)
    est = ww * w.mu[g] + (1.0 - ww) * xb
    r = a * est + (1.0 - a) * w.own
    return float(np.mean((th - r) ** 2 + w.self_cost * (r - w.own) ** 2))

def argmin_k(w, data, a):
    sc = [(k, loss(w, data, k, a)) for k in GRID]
    return min(sc, key=lambda t: t[1])[0], sc

# ══ 1 尺子自检 ══
print("【判据1】尺子自检：模拟总体的 d / η² 对不对得上理论")
w0 = World(d=0.23, sd_obs=0.80, seed=1)
g, th = w0.sample_partner(300000)
d_hat = th[g == 1].mean() - th[g == 0].mean()
eta_hat = 1.0 - np.var(th[g == 0]) / np.var(th)
c1 = abs(d_hat - 0.23) < 0.015 and abs(eta_hat - eta_squared(0.23)) < 0.008
print(f"  实测 d={R(d_hat)} (设 0.23)   η²={R(eta_hat)} (理论 {R(eta_squared(0.23))})  → {'✅' if c1 else '❌'}")
OUT['c1'] = bool(c1)

# ══ 2 九种真实言语形式 ══
print("\n【判据2】九种真实言语形式：性别能解释多少（元分析实测 d）")
rows = [(n, d, eta_squared(d) * 100, prob_superior(d) * 100) for n, d in D_REAL.items()]
for n, d, e, p in sorted(rows, key=lambda r: -abs(r[2])):
    print(f"  {n:15s} d={d:+.2f}   解释方差 {e:5.2f}%   随机一男一女猜对 {p:5.1f}%（瞎猜50%）")
c2 = max(r[2] for r in rows) < 5.0
print(f"  → {'✅ 最大的 task_comment(d=.38) 也只有 3.61%' if c2 else '❌'}")
OUT['c2'] = bool(c2)

# ══ 3 κ 内部峰（CRN）══
print("\n【判据3】κ 有内部峰？且等于解析解 τ²/σ²")
w = World(d=0.23, sd_obs=0.80, seed=7)
data = make_data(w)
a_star = 1.0 / (1.0 + w.self_cost)
kappa_hat, sc = argmin_k(w, data, a_star)
theory = w.tau ** 2 / w.sd_obs ** 2
for k, s in sc:
    print(f"  κ={k:7.2f}  loss {s:.6f}")
print(f"  峰 κ*={kappa_hat}   解析 τ²/σ²={R(theory)}   相对误差 {abs(kappa_hat-theory)/theory*100:.1f}%")
c3 = 0.02 < kappa_hat < 250.0 and abs(kappa_hat - theory) / theory < 0.30
print(f"  → {'✅' if c3 else '❌'}"); OUT['c3'] = bool(c3)

# ══ 4 硬依赖：听得多准 → κ* ══
print("\n【判据4】硬依赖两端：我听得越不准，越该信先验")
c4 = True
for so in [0.15, 0.40, 0.80, 1.60, 6.0]:
    ww = World(d=0.23, sd_obs=so, seed=7)
    dd = make_data(ww)
    kh, _ = argmin_k(ww, dd, a_star)
    t = ww.tau ** 2 / so ** 2
    ok = (kh <= GRID[1]) if t < GRID[1] else (abs(kh - t) / t < 0.45)
    c4 &= ok
    print(f"  σ_obs={so:4.2f}  κ*={kh:7.2f}  解析={t:8.2f}   {'✅' if ok else '⚠'}")
print(f"  → {'✅ 两端都动：6.0 时撞下限（全信先验），0.15 时撞上限（只信眼前）' if c4 else '❌'}")
OUT['c4'] = bool(c4)

# ══ 5 硬依赖：性别信息的价值 ∝ d² ══
print("\n【判据5】硬依赖：『知道性别』的价值 ∝ d²，d=0 归零")
def gain_gender(d, kappa, n=300000, seed=3):
    ww = World(d=d, sd_obs=0.80, seed=seed)
    g, th, ks, xb = make_data(ww, n=n, seed=seed)
    wgt = 1.0 / (1.0 + ks * kappa)
    a = 1.0 / (1.0 + ww.self_cost)
    e_g = wgt * ww.mu[g] + (1 - wgt) * xb
    e_0 = (1 - wgt) * xb                       # 用总均值 = 不知道性别
    lg = np.mean((th - (a * e_g + (1 - a) * ww.own)) ** 2)
    l0 = np.mean((th - (a * e_0 + (1 - a) * ww.own)) ** 2)
    return float(l0 - lg)
gd = [(d, gain_gender(d, theory)) for d in [0.0, 0.15, 0.23, 0.33, 0.38]]
for d, gg in gd:
    print(f"  d={d:.2f}   性别带来的改善 {gg:9.6f}   理论 ∝ d²/4 = {eta_squared(d):.6f}")
c5 = gd[0][1] < 1e-6 and gd[-1][1] > gd[2][1] > gd[1][1]
print(f"  → {'✅ d=0 精确归零，随 d² 增长' if c5 else '❌'}"); OUT['c5'] = bool(c5)

# ══ 6 a 内部峰 ══
print("\n【判据6】a（迁就 vs 做自己）内部峰 = 1/(1+c)")
sc = [(a, loss(w, data, theory, a)) for a in [0.0, .3, .5, .625, .75, .9, 1.0]]
ba = min(sc, key=lambda t: t[1])[0]
for a, s in sc:
    print(f"  a={a:.3f}  loss {s:.6f}")
c6 = abs(ba - a_star) < 0.1
print(f"  峰 a*={ba}   解析 1/(1+c)={R(a_star)}  → {'✅' if c6 else '❌'}"); OUT['c6'] = bool(c6)

# ══ 7 规则 vs 记数字 ══
print("\n【判据7】held-out：换一个全新人群，她重新估的 κ 还灵吗")
def estimate_kappa(ww, n=4000, seed=0):
    """她自己估：σ² 来自同一人内不同句的波动；τ² = 人与人之间波动 − σ²/k"""
    rng = np.random.default_rng(seed)
    g, th = ww.sample_partner(n)
    k = 5
    x = th[:, None] + rng.standard_normal((n, k)) * ww.sd_obs
    s2 = float(np.mean(x.var(axis=1, ddof=1)))
    t2 = max(float(np.var(x.mean(axis=1), ddof=1)) - s2 / k, 1e-6)
    return t2 / s2
train = [World(d=0.23, sd_obs=s, seed=100 + i) for i, s in enumerate([0.5, 0.8, 1.1])]
kh = [estimate_kappa(x, seed=7) for x in train]
print("  训练人群 她估的 κ̂:", [R(v) for v in kh])
print("           真值     :", [R(x.tau**2 / x.sd_obs**2) for x in train])
kap_memo = float(np.mean(kh))
held = World(d=0.31, sd_obs=2.2, seed=999)
kap_true_h = held.tau ** 2 / held.sd_obs ** 2
kap_rule_h = estimate_kappa(held, seed=7)
a_h = 1.0 / (1.0 + held.self_cost)
dh = make_data(held, n=200000, seed=5)
l_rule = loss(held, dh, kap_rule_h, a_h)
l_memo = loss(held, dh, kap_memo, a_h)
l_prior = loss(held, dh, 0.02, a_h)
l_evid = loss(held, dh, 250.0, a_h)
print(f"  held-out 真值 κ*={R(kap_true_h)}  她重估={R(kap_rule_h)}  记忆派={R(kap_memo)}")
print(f"  规则 {R(l_rule)}   记忆派 {R(l_memo)}   全信先验 {R(l_prior)}   全信眼前 {R(l_evid)}")
c7 = l_rule < l_memo and l_rule < l_prior and l_rule < l_evid
print(f"  → {'✅ 规则优于记数字，也优于两个极端' if c7 else '❌'}"); OUT['c7'] = bool(c7)

OUT['summary'] = dict(eta2_d23=eta_squared(0.23), prob_sup_d23=prob_superior(0.23),
                      kappa_star=float(theory), a_star=float(a_star))
print("\n通过:", sum(OUT[k] for k in [f'c{i}' for i in range(1, 8)]), "/7")
json.dump(OUT, open('/data/workspace/luoshen-o1/data/exp102_gender.json', 'w'),
          ensure_ascii=False, indent=1)
