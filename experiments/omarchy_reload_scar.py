#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用洛神判 omarchy 的 reload —— 不预测毫秒，只问一件事：
=========================================================
这些 reload 是【可逆的等待】，还是【不可逆的损伤】？

洛神能给这件事下判据，是因为它自己有一条别人没有的约束：
    capacity 只降不升（cap_decay），且降了要不回来。
这就是"不可逆"。

所以不建模 Hyprland。只把实测的两组数字当成两种【剥夺节奏】喂进去：

    组 A（当前 quattro，按键 4 reloads）  实测卡顿 186–333 ms → 中点 260
    组 B（#16397 修复后，0 reloads）      实测卡顿  37–113 ms → 中点  75

    1 拍 = 10 ms
    A 每次按键剥夺 26 拍；B 每次剥夺 8 拍（比例 3.3×，跟实测 260/75=3.5 一致）

    会话 = 每 60 拍按一次 SUPER+L，共 10 次按键 = 600 拍

★ 关键：B 组不是 0 —— 报告明写"首次按键仍付一次 reload"。
  这正是洛神那条不可逆：第一次的伤已经造成，修好之后也要不回来。

判据（洛神口径）：
    能互相校准 → 因果；不能 → 喜好。
    这里两组唯一差别是剥夺时长，其余完全相同 → 差异可归因。
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from life5 import Life5

STEPS = 600
PRESS_EVERY = 60          # 每 60 拍按一次 SUPER+L
MS_PER_TICK = 10

# 实测锚（omarchybot 在 Hyprland 0.56.2 上跑的，不是我跑的）
MEASURED = {
    "A_reload":  {"lo": 186, "hi": 333, "reloads": 4},
    "B_noreload": {"lo": 37,  "hi": 113, "reloads": 0},
}

def make_periodic_starver(ch, starve_ticks, press_every):
    """每 press_every 拍开始，连续 starve_ticks 拍不给通道 ch 分配。"""
    def alloc(want, B, s):
        t = s.t
        phase = t % press_every
        o = np.argsort(-want)
        a = np.zeros(s.N)
        left = B
        for i in o:
            if phase < starve_ticks and i == ch:
                continue
            tk = min(want[i], left)
            a[i] = tk
            left -= tk
            if left <= 1e-12:
                break
        return a
    return alloc

def run_group(starve_ticks, seeds=range(16)):
    rows = []
    for sd in seeds:
        lf = Life5(N=8, seed=sd, alloc_fn=make_periodic_starver(0, starve_ticks, PRESS_EVERY))
        lf.run(STEPS)
        cap0 = float(np.asarray(lf.capacity)[0])
        cap_mean = float(np.mean(lf.capacity))
        # 后段（>300）通道0 平均份额
        recs = [r for r in lf.log if r['t'] > 300]
        share0 = float(np.mean([r['share0'] for r in recs])) if recs else float('nan')
        rows.append(dict(seed=int(sd), alive=bool(lf.alive),
                         death_t=(None if lf.death_t is None else int(lf.death_t)),
                         cap0=cap0, cap_mean=cap_mean, share0=share0,
                         final_E=float(lf.E)))
    return rows

def mid(d):
    return (d["lo"] + d["hi"]) / 2.0

def boot_ci(x, y, n=5000, seed=0):
    """配对差的 bootstrap 95% CI —— 洛神要求差异必须带区间，不给裸数字"""
    rng = np.random.default_rng(seed)
    d = np.asarray(x) - np.asarray(y)
    bs = [np.mean(rng.choice(d, size=len(d), replace=True)) for _ in range(n)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    print("=" * 74)
    print(" 洛神判 omarchy reload · 可逆的等待 还是 不可逆的损伤")
    print("=" * 74)
    mA, mB = mid(MEASURED["A_reload"]), mid(MEASURED["B_noreload"])
    sa = int(round(mA / MS_PER_TICK))
    sb = int(round(mB / MS_PER_TICK))
    print(f"   实测 A（4 reloads） {MEASURED['A_reload']['lo']}–{MEASURED['A_reload']['hi']} ms "
          f"→ 中点 {mA:.0f} → 剥夺 {sa} 拍")
    print(f"   实测 B（0 reloads） {MEASURED['B_noreload']['lo']}–{MEASURED['B_noreload']['hi']} ms "
          f"→ 中点 {mB:.0f} → 剥夺 {sb} 拍")
    print(f"   比例 {mA/mB:.2f}×  ≈ 剥夺比 {sa/sb:.2f}×")
    print(f"   会话 600 拍 / 每 {PRESS_EVERY} 拍一次按键 = 10 次")
    print()
    print("   （这些毫秒是 omarchybot 跑出来的，不是我。我只拿它定剥夺节奏。）")
    print()

    A = run_group(sa)
    B = run_group(sb)
    print("=" * 74)
    print(f" {'组':<18}{'存活':>7}{'cap0终态':>11}{'cap均值':>10}{'后段份额':>10}")
    print("=" * 74)
    for name, rows in (("A 有reload", A), ("B 无reload", B)):
        al = sum(r['alive'] for r in rows)
        print(f" {name:<18}{f'{al}/{len(rows)}':>7}"
              f"{np.mean([r['cap0'] for r in rows]):>11.4f}"
              f"{np.mean([r['cap_mean'] for r in rows]):>10.4f}"
              f"{np.mean([r['share0'] for r in rows]):>10.4f}")

    d_cap0 = np.mean([r['cap0'] for r in A]) - np.mean([r['cap0'] for r in B])
    d_share = np.mean([r['share0'] for r in A]) - np.mean([r['share0'] for r in B])
    # 配对差（同 seed 相减），看方向是否一致
    paired = np.array([a['cap0'] - b['cap0'] for a, b in zip(A, B)])
    neg = int(np.sum(paired < 0))
    print()
    print("=" * 74)
    print(f"   cap0 差 A−B = {d_cap0:+.4f}   （配对：{neg}/{len(paired)} 个 seed 方向一致）")
    print(f"   份额差 A−B = {d_share:+.4f}")
    print("=" * 74)
    if abs(d_cap0) > 1e-4 and (neg == 0 or neg == len(paired)):
        verdict = ("✅ 有梯度且方向一致 —— reload 的代价进了【结构】，不是只进了【等待】。"
                   "\n   cap0 是单调衰减量：降了要不回来。这就是不可逆。")
    elif abs(d_cap0) <= 1e-4:
        verdict = "⬜ 无梯度 —— 在这个尺度上 reload 只是等待，没造成结构损伤。"
    else:
        verdict = "⚠️ 有梯度但方向不一致 —— 不能下结论。"
    print(verdict)
    print("=" * 74)
    print()
    print(" ★ 洛神这条能给而别人给不出的：")
    print("   报告说『修好之后首次按键仍付一次 reload』。")
    print("   在洛神里这不叫残留 bug，叫不可逆 —— 第一次的伤已经造成，")
    print("   后面修得再干净也回不来。cap0 只降不升就是这条约束。")
    print()

    # ---------- 第二组对照：总量相同，只改"一次剥夺多长" ----------
    print()
    print("=" * 74)
    print(" 等总量对照 —— 总共被剥夺的拍数一样，只改【一次剥夺多长】")
    print("=" * 74)
    # A_long : 24拍 × 10次 = 240 总（一次卡 240ms）
    # C_short:  2拍 × 120次 = 240 总（一次卡 20ms，但按 120 次）
    A_long  = run_group(24, seeds=range(16))
    C_short = run_group(2,  seeds=range(16))
    # C 需要不同的 press_every 才能凑够 120 次，单独跑
    def run_freq(starve, press_every, seeds=range(16)):
        rows = []
        for sd in seeds:
            lf = Life5(N=8, seed=sd,
                       alloc_fn=make_periodic_starver(0, starve, press_every))
            lf.run(STEPS)
            recs = [r for r in lf.log if r['t'] > 300]
            rows.append(dict(seed=int(sd), alive=bool(lf.alive),
                             cap0=float(np.asarray(lf.capacity)[0]),
                             share0=float(np.mean([r['share0'] for r in recs])) if recs else float('nan')))
        return rows
    A_long  = run_freq(24, 60)    # 24拍 × 10次  = 240 总
    C_short = run_freq(2,   5)    #  2拍 × 120次 = 240 总
    ca = [r['cap0'] for r in A_long]
    cc = [r['cap0'] for r in C_short]
    lo, hi = boot_ci(ca, cc)
    print(f"   A_long  一次剥夺 24 拍 × 10 次  = 240 总 → cap0 {np.mean(ca):.4f}")
    print(f"   C_short 一次剥夺  2 拍 × 120 次 = 240 总 → cap0 {np.mean(cc):.4f}")
    print(f"   差 A−C = {np.mean(ca)-np.mean(cc):+.4f}   bootstrap 95% CI [{lo:+.4f}, {hi:+.4f}]")
    if hi < 0:
        v2 = ("✅ CI 不跨 0 —— 总量一样，损害还是不同。"
              "\n   → 伤来自【单次峰值】，不是【累计时长】。"
              "\n   → 对 omarchy：一次 260ms 的卡顿，比同样总时长的多次小卡顿更伤结构。")
    elif lo > 0:
        v2 = "⚠️ 反方向：多次短剥夺反而更伤。与直觉相反，值得单独写。"
    else:
        v2 = "⬜ CI 跨 0 —— 总量一样时没有差异，说明伤只跟总量有关，跟峰值无关。"
    print(f"   {v2}")

    json.dump({"measured": MEASURED, "tick_ms": MS_PER_TICK,
               "starve_ticks": {"A": sa, "B": sb},
               "A": A, "B": B,
               "delta_cap0": float(d_cap0), "delta_share": float(d_share),
               "paired_consistent": int(max(neg, len(paired) - neg)),
               "verdict": verdict,
               "equal_total": {"A_long_24x10": float(np.mean(ca)), "C_short_2x120": float(np.mean(cc)),
                               "delta": float(np.mean(ca)-np.mean(cc)), "ci95": [lo, hi],
                               "verdict": v2}},
              open(os.path.join(os.path.dirname(__file__), '..', 'data', 'omarchy_reload_scar.json'), 'w'),
              ensure_ascii=False, indent=1)
    return 0

if __name__ == "__main__":
    sys.exit(main())
