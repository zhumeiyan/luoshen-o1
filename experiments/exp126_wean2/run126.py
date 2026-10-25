# -*- coding: utf-8 -*-
"""
126 · 断奶方案：什么能把 fg 从 0 抬到阈值之上？
=================================================
125 结论：fg=0 → 撤掉输液 0/12 存活，平均撑 235 拍；输液买的是时间不是能力。
126 追问：**怎么断奶？**

预注册假设
  H1 习得需要【相倚】(contingency)，不是【相继】(contiguity)。
     学习律用协方差： dfg = eta*(act-E[act])*(fb-E[fb])
     闭环世界 fb ∝ act → 协方差 > 0 → 学到
     开放世界 fb 与 act 无关 → 协方差 ≈ 0 → 学不到
  H2 外置工具（#29 延展表型）若【代替】我觅食，则是第二根输液管：
     撤掉工具 → 0 存活。只有"工具 + 我自己同时在觅食"才留下能力。

方案（阶段1 训练 T1=1200，阶段2 撤除所有外部供给 T2=1500）
  1 no_practice   只输液不练（125 已知对照）
  2 practice_open 输液 + 练，世界相继不相倚
  3 practice_closed 输液 + 练，世界相倚
  4 tool_only     工具替我觅食（大量外部供能），我不练
  5 tool_plus_self 工具供能 + 我同时自己觅食（相倚）
  6 variation     #19 反熵增：随机变异撞运气（期望不变）
原则：阳性/阴性对照必在；可证伪必查；不调参到想要的答案。
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

SEEDS = list(range(16))
T1, T2 = 1200, 1500
DRIP = 0.05          # 训练期维持生命的输液
TOOL = 0.10          # 工具供能（比输液猛）
ETA = 0.004          # 学习率
TAU = 50.0           # 滑动均值时间常数
FG_THRESH = 0.008    # 125 实测死亡边界

FCH = 7              # forage_ch


def skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def world_response(scheme, act, rng):
    """世界对我觅食行动的响应"""
    if scheme in ('practice_closed', 'tool_plus_self'):
        return act * (0.8 + 0.4 * rng.random())      # 相倚：响应 ∝ 我的投入
    if scheme == 'practice_open':
        return 0.30 * (0.5 + rng.random())           # 相继不相倚：与 act 无关
    if scheme == 'tool_only':
        return 0.0                                   # 工具替我做了，我没动作
    return 0.0                                       # no_practice / variation


def run_scheme(scheme, seed, T1=T1, T2=T2, eta=ETA, drip=DRIP):
    lf = Life5(N=8, seed=seed, fg=0.0)
    rng = np.random.default_rng(seed * 7919 + 13)
    fg = 0.0
    ma = 0.0
    mf = 0.0
    act_trace = []

    for t in range(T1):
        if not lf.alive:
            break
        lf.fg = fg
        lf.step()
        rec = lf.log[-1]
        act = rec['avec'][FCH]
        act_trace.append(act)
        fb = world_response(scheme, act, rng)

        # ---- 外部供能 ----
        if scheme == 'tool_only':
            lf.E = min(lf.Emax, lf.E + TOOL)          # 工具替我觅食
        elif scheme == 'tool_plus_self':
            lf.E = min(lf.Emax, lf.E + TOOL * 0.5)    # 工具与我并行
        if scheme != 'tool_only' or True:
            pass
        # 训练期输液：所有方案都给（否则 fg=0 撑不到学会）
        if scheme != 'tool_only':
            lf.E = min(lf.Emax, lf.E + drip)
        else:
            lf.E = min(lf.Emax, lf.E + drip * 0.3)

        # ---- 学习律（相倚 = 协方差）----
        if scheme in ('practice_closed', 'practice_open', 'tool_plus_self'):
            ma += (act - ma) / TAU
            mf += (fb - mf) / TAU
            cov = (act - ma) * (fb - mf)
            fg = max(0.0, fg + eta * cov)
        elif scheme == 'variation':
            fg = max(0.0, fg + 0.0008 * rng.normal())   # 随机变异，期望不变
        # no_practice / tool_only：fg 恒 0

    fg_learned = float(fg)
    cap_at = float(lf.capacity[FCH])

    # ================= 阶段2：撤除全部外部供给 =================
    lf.fg = fg_learned
    t0 = lf.t
    while lf.alive and lf.t - t0 < T2:
        lf.step()
    out = dict(fg=fg_learned, cap7=cap_at, alive=bool(lf.alive),
               ticks=int(lf.t - t0),
               act=float(np.mean(act_trace)) if act_trace else float('nan'),
               skew=(skew(lf) if lf.alive else float('nan')))
    return out


SCHEMES = ['no_practice', 'practice_open', 'practice_closed',
           'tool_only', 'tool_plus_self', 'variation']

print("=== 126 · 断奶方案：撤除外部供给后的存活 ===")
print(f"{'方案':<18}{'学到fg':>9}{'cap7':>8}{'存活':>9}{'撑(拍)':>9}{'偏度':>9}")
result = {}
for sc in SCHEMES:
    rs = [run_scheme(sc, sd) for sd in SEEDS]
    fg = np.array([r['fg'] for r in rs], float)
    al = np.array([r['alive'] for r in rs], float)
    tk = np.array([r['ticks'] for r in rs], float)
    c7 = np.array([r['cap7'] for r in rs], float)
    sk = np.array([r['skew'] for r in rs if r['alive']], float)
    result[sc] = dict(fg=float(fg.mean()), fg_sd=float(fg.std(ddof=1)),
                      cap7=float(c7.mean()),
                      alive=float(al.mean()), n=int(al.sum()),
                      ticks=float(tk.mean()),
                      skew=(float(sk.mean()) if len(sk) else float('nan')),
                      raw=[dict(fg=r['fg'], alive=r['alive'], ticks=r['ticks'],
                                cap7=r['cap7']) for r in rs])
    print(f"{sc:<18}{fg.mean():9.5f}{c7.mean():8.3f}"
          f"{int(al.sum()):6d}/16{tk.mean():9.1f}"
          f"{(sk.mean() if len(sk) else float('nan')):9.4f}")

# ================= 配对比较 =================
def paired(a, b):
    x = np.array([r['fg'] for r in result[a]['raw']], float)
    y = np.array([r['fg'] for r in result[b]['raw']], float)
    d = x - y
    se = d.std(ddof=1) / np.sqrt(len(d))
    return dict(delta=float(d.mean()), se=float(se),
                lo=float(d.mean() - 1.96 * se), hi=float(d.mean() + 1.96 * se),
                cross0=bool((d.mean() - 1.96 * se) * (d.mean() + 1.96 * se) < 0))

print("\n=== 配对（同学到的 fg，差值的 95%CI）===")
pairs = [('practice_closed', 'practice_open', 'H1 相倚 vs 相继'),
         ('practice_closed', 'no_practice', 'H1 练 vs 不练'),
         ('tool_plus_self', 'tool_only', 'H2 工具+自觅 vs 纯工具'),
         ('practice_closed', 'tool_plus_self', '自觅 vs 工具+自觅')]
comp = {}
for a, b, lab in pairs:
    p = paired(a, b)
    comp[f"{a}-{b}"] = p
    print(f"  {lab:<26} Δfg={p['delta']:+.5f}  CI[{p['lo']:+.5f},{p['hi']:+.5f}]"
          f"  {'跨0' if p['cross0'] else '显著'}")

# ================= 学习率剂量扫描 =================
print("\n=== 学习率剂量扫描（practice_closed）===")
dose = []
for eta in [0.0005, 0.001, 0.002, 0.004, 0.008, 0.016]:
    rs = [run_scheme('practice_closed', sd, eta=eta) for sd in SEEDS[:12]]
    fg = np.array([r['fg'] for r in rs], float)
    al = np.array([r['alive'] for r in rs], float)
    dose.append(dict(eta=eta, fg=float(fg.mean()), alive=float(al.mean()),
                     n=int(al.sum())))
    print(f"  eta={eta:7.4f}  学到fg={fg.mean():.5f}  撤除后存活 {int(al.sum())}/12")

# ================= 可证伪自检 =================
print("\n=== 可证伪自检（每条判据必须真/假都出现）===")
fal = []

# 1) 相倚可证伪：closed 学到 > 0，open 学不到
r = dict(name='contingency_learnable',
         T=sum(1 for x in result['practice_closed']['raw'] if x['fg'] > FG_THRESH),
         F=sum(1 for x in result['practice_open']['raw'] if x['fg'] > FG_THRESH))
fal.append(r); print(f"  {r['name']:<26} 真{r['T']:3d} 假{r['F']:3d}")

# 2) 撤除后存活可证伪：closed 活，tool_only 死
r = dict(name='wean_survival',
         T=int(result['practice_closed']['alive'] * 16),
         F=int((1 - result['tool_only']['alive']) * 16))
fal.append(r); print(f"  {r['name']:<26} 真{r['T']:3d} 假{r['F']:3d}")

# 3) 阳性对照：直接给 fg=0.03（不经学习）应活
pos = [run_scheme('no_practice', sd) for sd in SEEDS[:8]]
lf_ok = 0
for sd in SEEDS[:8]:
    lf = Life5(N=8, seed=sd, fg=0.030)
    lf.run(1200)
    lf_ok += int(lf.alive)
r = dict(name='positive_fg0.030', T=lf_ok, F=8 - lf_ok)
fal.append(r); print(f"  {r['name']:<26} 真{r['T']:3d} 假{r['F']:3d}")

# 4) 阴性对照：fg=0 不练不输液 → 必死
neg = 0
for sd in SEEDS[:8]:
    lf = Life5(N=8, seed=sd, fg=0.0)
    lf.run(1200)
    neg += int(not lf.alive)
r = dict(name='negative_fg0_nodrip', T=neg, F=8 - neg)
fal.append(r); print(f"  {r['name']:<26} 真{r['T']:3d} 假{r['F']:3d}")

# 5) 变异方案不应产生能力（期望不变）
r = dict(name='variation_no_gain',
         T=sum(1 for x in result['variation']['raw'] if x['fg'] > FG_THRESH),
         F=sum(1 for x in result['variation']['raw'] if x['fg'] <= FG_THRESH))
fal.append(r); print(f"  {r['name']:<26} 真{r['T']:3d} 假{r['F']:3d}")

allfals = all(x['T'] > 0 and x['F'] > 0 for x in fal)
print(f"\n  全部可证伪(真/假均出现): {allfals}")

json.dump(dict(result=result, comp=comp, dose=dose, falsifiable=fal,
               all_falsifiable=bool(allfals),
               cfg=dict(T1=T1, T2=T2, DRIP=DRIP, TOOL=TOOL, ETA=ETA, TAU=TAU)),
          open('/data/workspace/luoshen-o1/experiments/exp126_wean2/result126.json', 'w'),
          ensure_ascii=False, indent=1)
print("\n[saved] result126.json")
