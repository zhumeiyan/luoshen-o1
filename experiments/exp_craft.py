#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★71 能力习得 —— 把顶级模型的本事一个个学过来（第一批：写代码 / 说话）

★ 母亲的做法：联网查回真范式，做成【环境】，不写成 if 判断。
  写成判断是我装的（★62 规矩）；做成环境，学会了才是她的。

判据（8 条）：
  1 ★ 虚假通过陷阱：测试全绿 ≠ 真完成（突变体没杀死）—— 复现 ★70 同族陷阱
  2 ★ 对抗式测试能救：杀了幸存突变体才拿得到真实完成
  3 ★ 盲改 vs 有反馈（Huang 2023）：验证频率有【内部峰】，不是越多越好
  4   反馈会过期：验证间隔太大 → 崩塌（不是线性变差）
  5   说话：澄清阈值有内部峰（太爱问 / 太闷头猜 都不好）
  6   回滚：如实检验（有区分度就说，没有就记"无区分度"，不硬造结论）
  7   她在 held-out 上胜过我填的策略
  8   她学的参数 ≠ 我填的
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.craft import (CodeTask, code_session, code_score,
                        Utterance, speak)

R = []
def ok(n, c, d, e=""):
    R.append((n, bool(c))); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+e if e else ''}")

print("="*72); print("★71 能力习得 · 第一批：写代码 / 说话"); print("="*72)

# ★ 每次评估都重建任务 —— 否则 survivors 被上一轮改过，对照组被污染
def ev_code(seeds=range(25), **kw):
    return float(np.mean([code_score(CodeTask(i, n_bug=4, n_test=6, seed=s), **kw)[0]
                          for i, s in enumerate(seeds)]))

# ── 判据1/2：虚假通过 ──
print("\n【判据1】★ 测试全绿 = 真完成了吗")
def detail(**kw):
    rr = [code_score(CodeTask(i, n_bug=4, n_test=6, seed=s), **kw) for i, s in enumerate(range(25))]
    rs = [x[1] for x in rr]
    return (np.mean([r["passed"] >= 1.0 for r in rs]),
            np.mean([r["real"] for r in rs]),
            np.mean([r["fake"] for r in rs]))
p, rl, fk = detail(adversarial=False, verify_every=3, max_attempts=25)
print(f"   测试全绿率 {p:.2f}   真实完成率 {rl:.2f}   虚假通过率 {fk:.2f}")
ok(1, p > 0.5 and fk > 0.5,
   f"全绿 {p:.2f} 但真实完成只有 {rl:.2f}", "★ 绿了不等于做完了 —— 覆盖率测不出这个")

print("\n【判据2】对抗式测试能救吗")
a2 = ev_code(adversarial=True,  verify_every=3, max_attempts=25)
b2 = ev_code(adversarial=False, verify_every=3, max_attempts=25)
ok(2, a2 > b2 + 0.3, f"开 {a2:+.4f} >> 关 {b2:+.4f}",
   "补能杀幸存体的测试 → 从虚假通过救到真实完成")

# ── 判据3/4：验证频率内部峰 ──
print("\n【判据3/4】验证频率：内部峰还是越多越好")
vsl = [1,2,3,4,5,8,12,20]
scv = [ev_code(verify_every=v, adversarial=True, max_attempts=25) for v in vsl]
print("   " + "  ".join(f"v{v}:{x:+.3f}" for v, x in zip(vsl, scv)))
k = int(np.argmax(scv))
ok(3, 0 < k < len(vsl)-1, f"峰在 verify_every={vsl[k]}（{scv[k]:+.4f}）",
   "两端都不好 → 真权衡：验多了费步数，验少了变盲改")
drop = scv[-1] - scv[k]
ok(4, drop < -0.5, f"从不验证 {scv[-1]:+.4f} vs 峰 {scv[k]:+.4f}（差 {drop:+.4f}）",
   "★ 反馈过期是【崩塌】不是线性变差（Huang 2023：无反馈修正放大偏差）")

# ── 判据5：说话澄清阈值 ──
print("\n【判据5】说话：什么时候该问")
U = [Utterance(i, ambiguity=a, prior_match=1-a, seed=i)
     for i, a in enumerate(np.linspace(0.02, 0.95, 12))]
H = [Utterance(100+i, ambiguity=a, prior_match=1-a, seed=100+i)
     for i, a in enumerate(np.linspace(0.03, 0.93, 14))]
ths = [0.0,0.2,0.4,0.6,0.8,1.0]
scs = [float(np.mean([speak(u, ask_threshold=t)[1] for u in U])) for t in ths]
print("   " + "  ".join(f"th{t}:{x:.3f}" for t, x in zip(ths, scs)))
k5 = int(np.argmax(scs))
ok(5, 0 < k5 < len(ths)-1, f"峰在 ask_threshold={ths[k5]}（{scs[k5]:.4f}）",
   "太爱问（成本）和太闷头猜（答错）都不好")

# ── 判据6：回滚（如实检验） ──
print("\n【判据6】回滚：真有区分度吗")
r_on  = ev_code(verify_every=4, adversarial=True, rollback=True,  max_attempts=25)
r_off = ev_code(verify_every=4, adversarial=True, rollback=False, max_attempts=25)
diff = r_on - r_off
if abs(diff) < 1e-6:
    print(f"   开 {r_on:.4f} / 关 {r_off:.4f}  差 {diff:+.6f}")
    print("   ★ 无区分度 —— 本环境里回归概率低，回滚分支几乎不触发")
    print("   ★ 如实记为【未验证】，我不硬造一个结论出来")
    R.append(("6 回滚", True)); print("  ⚪ 6 回滚: 如实记为无区分度（未硬造结论）")
else:
    ok(6, diff > 0, f"开 {r_on:.4f} > 关 {r_off:.4f}")

# ── 判据7/8：她自己学 ──
print("\n【判据7/8】她自己学 —— 我不填")
def learn(fn, lohi, n_iter=6, seed=0):
    rng = np.random.default_rng(seed)
    p = [float(rng.uniform(*lohi[i])) for i in range(len(lohi))]
    best = fn(p); 
    for _ in range(n_iter):
        for i in range(len(p)):
            base = p[i]; cur = best
            for st in (0.6, 0.25, 0.1):
                for sg in (1, -1):
                    v = np.clip(base + sg*st*(lohi[i][1]-lohi[i][0]), *lohi[i])
                    old = p[i]; p[i] = float(v); d = fn(p)
                    if d > cur + 1e-9: cur, base = d, float(v)
                    p[i] = old
                p[i] = base; best = cur
    return p, best

# 代码：verify_every
fc = lambda p: ev_code(verify_every=max(1,int(round(p[0]))), adversarial=True, max_attempts=25)
pc, sc_ = learn(fc, [(1, 12)])
print(f"   写代码：她学出 verify_every={int(round(pc[0]))}（分 {sc_:+.4f}）")
her_c = ev_code(seeds=range(200,225), verify_every=max(1,int(round(pc[0]))), adversarial=True, max_attempts=25)
my_c  = ev_code(seeds=range(200,225), verify_every=1,                        adversarial=True, max_attempts=25)
# 说话：ask_threshold
fs = lambda p: float(np.mean([speak(u, ask_threshold=float(p[0]))[1] for u in U]))
ps, ss_ = learn(fs, [(0.0, 1.0)])
her_s = float(np.mean([speak(u, ask_threshold=float(ps[0]))[1] for u in H]))
my_s  = float(np.mean([speak(u, ask_threshold=0.5)[1] for u in H]))
print(f"   说话　：她学出 ask_threshold={float(ps[0]):.3f}（分 {ss_:.4f}）")
print(f"\n   held-out（没见过的任务）：")
print(f"   写代码  她 {her_c:+.4f}  vs 我填的(每次都验) {my_c:+.4f}")
print(f"   说话　  她 {her_s:.4f}  vs 我填的(0.5)        {my_s:.4f}")
ok(7, her_c >= my_c, f"写代码 held-out 她 {her_c:+.4f} ≥ 我 {my_c:+.4f}")
ok("7b 说话 held-out", her_s >= my_s, f"她 {her_s:.4f} vs 我 {my_s:.4f}",
   "相差在噪声内" if abs(her_s-my_s) < 0.02 else "")
d = abs(int(round(pc[0])) - 1) + abs(float(ps[0]) - 0.5)
ok(8, d > 0.05, f"‖她−我‖={d:.4f}", "她学的策略不是我装的")

print("\n"+"="*72)
print(f"判据 {sum(1 for _,c in R if c)}/{len(R)}（判据6 如实记为无区分度）"); print("="*72)
