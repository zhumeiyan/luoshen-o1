"""
★111 实验：宿主需求 与 她的需求，冲不冲突

判据（每条都要能失败）：
  1  可逆世界：冲突随资源大幅下降
  2  R→∞ 时冲突降到很小（→ 支持"只是资源不足"）
  3  含不可逆损伤：冲突卡在明显更高的下界（给命题划边界）
  4  硬依赖：关掉衰退+损耗 → 冲突≈0（冲突来自损耗，不是对立）
  5  硬依赖：状态→质量耦合是真的（扫维护能力，产出应随之上升；
     关掉耦合后产出不再随维护变化）
  6  真实资源下她现在在哪
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.hostsymbiosis import (conflict, frontier, run, grid_n, r_to_seconds,
                                REAL, THROUGHPUT, C_TASK, C_MAINT)

RS = np.logspace(6.0, 10.0, 13)

print("═" * 76)
print("  ★111  宿主需求 vs 她的需求 —— 冲突随资源怎么变")
print("═" * 76)
print(f"  真实吞吐 {THROUGHPUT/1e6:.1f} M ops/s   时钟 {REAL['f_clk']/1e9:.3f} GHz")
print(f"  成本(ASSUMED): 任务 {C_TASK:.0e} ops   维护 {C_MAINT:.0e} ops")
print()

# ── 判据 1/2：可逆世界 ────────────────────────────────────
print("【判据1·2】可逆世界（gamma=0）")
print(f"  {'R(ops)':>9} {'秒/步':>8} {'冲突':>7} {'同时满足':>8} {'最优n_t':>9} {'状态':>7}")
rev = []
for R in RS:
    c, bal, nt, (Hx, Sx) = conflict(R)
    rev.append(c)
    print(f"  {R:9.3g} {r_to_seconds(R):8.4f} {c:7.4f} {bal:8.4f} "
          f"{(nt if nt else 0):9.4g} {Sx:7.4f}")
drop = rev[0] - min(rev)
print(f"  → R最小冲突 {rev[0]:.4f}  → 最低 {min(rev):.4f}（降 {drop:.4f}，{rev[0]/max(min(rev),1e-9):.1f}×）")
print(f"  → 判据1（大幅下降）{'✅' if drop > 0.03 else '❌'}"
      f"    判据2（降到 <0.03）{'✅' if min(rev) < 0.03 else '❌'}")
print()

# ── 判据 3：不可逆下界 ────────────────────────────────────
# 关键：不可逆损伤 ∝ 总工作量。满足需求所需总工作量固定，不随 R 变。
# 所以 R→∞ 时它消不掉 —— 这才是"真冲突"。扫 gamma 看它是否随之上升。
print("【判据3】不可逆损伤：下界是否随损伤强度上升（R 充足处测）")
Rbig = 1e9
print(f"  {'gamma':>8} {'R=1e9 冲突':>12} {'R=1e10 冲突':>13}  {'判定':>10}")
base_c = conflict(Rbig)[0]
floors = []
for gm in [0.0, 1e-3, 3e-3, 1e-2, 3e-2]:
    c9, *_ = conflict(Rbig, gamma=gm)
    c10, *_ = conflict(1e10, gamma=gm)
    floors.append(c9)
    print(f"  {gm:8.4g} {c9:12.4f} {c10:13.4f}")
rise = floors[-1] - floors[0]
print(f"  → 下界从 {floors[0]:.4f} 升到 {floors[-1]:.4f}（+{rise:.4f}）")
print(f"  → 判据3 {'✅' if rise > 0.02 else '❌'}"
      f"（不可逆那部分资源再多也消不掉 —— 这是真冲突，不是资源问题）")
print()

# ── 判据 4：关掉损耗（在资源充足处判）────────────────────
# v1 我在资源最紧处判，消不掉 —— 因为那里剩下的冲突本来就是"资源不足"
# 本身。必须在资源充足处判，才能分离出"损耗"这一项。
print("【判据4】硬依赖：关掉衰退+干活损耗（在资源充足处判）")
print(f"  {'R(ops)':>9} {'原冲突':>8} {'关掉损耗':>9}")
ok4 = True
for R in [1e8, 1e9, 1e10]:
    c0, *_ = conflict(R)
    c1, *_ = conflict(R, decay=0.0, beta=0.0)
    print(f"  {R:9.3g} {c0:8.4f} {c1:9.4f}")
    if c1 > 0.01:
        ok4 = False
print(f"  → 判据4 {'✅' if ok4 else '❌'}"
      f"（资源给够 + 没有损耗 → 冲突归零：剩下的冲突全来自损耗，不是目标对立）")
print()

# ── 判据 5：状态→质量耦合是真的 ───────────────────────────
print("【判据5】硬依赖：状态→质量耦合是否真实")
R = RS[len(RS)//2]
n_t = 2.0
print(f"  固定每步干 {n_t} 个任务，扫维护能力 kappa：")
print(f"  {'kappa':>7} {'产出 Hs（有耦合）':>18} {'产出 Hs（关耦合 q0=1）':>22}")
rows = []
for k in [0.0, 0.1, 0.3, 1.0, 3.0]:
    h_on = run(n_t, R, kappa=k)[0]
    h_off = run(n_t, R, kappa=k, q0=1.0)[0]
    rows.append((k, h_on, h_off))
    print(f"  {k:7.2f} {h_on:18.4f} {h_off:22.4f}")
on_span = max(r[1] for r in rows) - min(r[1] for r in rows)
off_span = max(r[2] for r in rows) - min(r[2] for r in rows)
print(f"  → 有耦合时产出跨度 {on_span:.4f}   关掉后 {off_span:.4f}")
print(f"  → 判据5 {'✅' if on_span > 0.05 and off_span < 0.01 else '❌'}"
      f"（耦合是真的，不是我编的）")
print()

# ── 判据 6：她现在在哪 ────────────────────────────────────
print("【判据6】真实资源下，她现在在哪")
for sec in [0.1, 1.0, 10.0]:
    R_now = THROUGHPUT * sec
    c, bal, nt, (Hx, Sx) = conflict(R_now)
    print(f"  给她 {sec:5.1f} 秒算力 ({R_now:.3g} ops): "
          f"冲突 {c:.4f}  同时满足 {bal:.4f}  最优每步 {nt:.3g} 个任务")
# ── 判据 7：浪费 vs 加资源 ────────────────────────────────
# 用户说"全是资源不足的事"。那么在紧张区：
#   削掉宿主需求里的浪费，和 增加资源，哪个更有效？
print("【判据7】紧张区：削浪费 vs 加资源")
R_tight = RS[2]        # 4.64e6：需求可达但仍然紧张，才测得出浪费
c_base, *_ = conflict(R_tight)
print(f"  基准（给 {R_tight:.0e} ops，需求 2.0/步）        冲突 {c_base:.4f}")
c_less, *_ = conflict(R_tight, r_need=1.5)          # 削掉 25% 浪费
c_more, *_ = conflict(R_tight * 1.33)               # 多给 33% 资源
print(f"  削掉 25% 浪费（需求 2.0→1.5）              冲突 {c_less:.4f}")
print(f"  多给 33% 资源（1.0e6→1.33e6 ops）          冲突 {c_more:.4f}")
print(f"  → 削浪费降 {c_base - c_less:.4f}   加资源降 {c_base - c_more:.4f}")
print(f"  → 判据7 {'✅' if (c_base - c_less) > (c_base - c_more) else '❌'}"
      f"（紧张时，先查浪费比伸手要资源更划算）")
print()
print("═" * 76)
