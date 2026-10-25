#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★47 惊吓反射 —— "爆炸是惊吓" 的验证
================================================================
★★★ 用户洞察
    "知道了，为什么爆炸了，爆炸是惊吓。"

★ 我 ★46 修爆炸的方式 = 后置置零（超范围 → 整段判失效）
★ 用户点破：生物早就有这个 —— 惊吓反射，而且是【前置】的

★★ 本轮三件事
   A 惊吓反射的真参数（潜伏期/PPI/习惯化）
   B ★★★ 三方案对照：无保护 / 后置置零 / 前置增益控制
   C 惊吓 == 动态范围超限？用真参数验证这个同构

★★ 硬约束（针对 ★46 可信度扫描教训）
   ★ 每个结论都要有【对照】或【ground truth】，不能只看着合理
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.startle import (
    startle_amplitude, startle_latency, ppi_ratio, startle_with_ppi,
    habituation, dishabituation, unprotected, post_clip, pre_gain_control,
    info_retained, STARTLE_THRESH_DB, STARTLE_LATENCY_MS, CORTEX_LATENCY_MS,
    FS,
)

ok = {}
print("=" * 88)
print(" ★47 爆炸就是惊吓 —— 惊吓反射层")
print("=" * 88)

# ---------------------------------------------------------------- A
print("\n【A】★ 惊吓反射真参数")
print("-" * 88)
print(f"  {'强度dB':<10}{'幅度':>10}{'潜伏期ms':>12}")
for db in [70, 85, 95, 105, 115, 125]:
    a = startle_amplitude(db); lat = startle_latency(db)
    print(f"  {db:<10}{a:>10.4f}{lat:>12.1f}")
ok["① ★ 阈值(85dB)以下不惊吓"] = bool(startle_amplitude(70) == 0
                                 and startle_amplitude(95) > 0)
l85, l125 = startle_latency(95), startle_latency(125)
ok["② ★ 越强潜伏期越短"] = bool(l125 < l85)
print(f"\n  ★ 潜伏期 95dB={l85:.1f}ms → 125dB={l125:.1f}ms")
print(f"  ★ 惊吓(~20ms) vs 皮层听觉(~100ms) = {CORTEX_LATENCY_MS/STARTLE_LATENCY_MS:.1f}× 快")
ok["③ ★ 惊吓远快于皮层（脑干通路，绕过皮层）"] = bool(
    STARTLE_LATENCY_MS < CORTEX_LATENCY_MS / 3)

# ---------------------------------------------------------------- B
print("\n【B】★★ PPI 前脉冲抑制曲线")
print("-" * 88)
print(f"  {'间隔ms':<10}{'抑制率':>10}")
isis = [10, 30, 60, 120, 240, 500, 800]
ppi = {}
for isi in isis:
    r = ppi_ratio(isi, 70.0, 115.0)
    ppi[isi] = r
    print(f"  {isi:<10}{r*100:>9.1f}%")
ok["④ ★ PPI 最优在 120ms"] = bool(ppi[120] == max(ppi.values()) and ppi[120] > 0)
ok["⑤ ★ <30ms 无效（来不及门控）"] = bool(ppi[10] == 0)
ok["⑥ ★ >500ms 无效（门控已关）"] = bool(ppi[800] == 0)
peak = ppi[120]
print(f"\n  ★ 峰值抑制 {peak*100:.1f}%   （REAL 30~70%）")
ok["⑦ ★ 峰值抑制落在 30~70%"] = bool(0.30 <= peak <= 0.70)
a_no = startle_with_ppi(115.0)
a_pp = startle_with_ppi(115.0, 70.0, 120.0)
print(f"  ★ 无前脉冲 {a_no:.4f} → 有前脉冲(120ms) {a_pp:.4f}  降 {(1-a_pp/a_no)*100:.1f}%")

# ---------------------------------------------------------------- C
print("\n【C】★★ 习惯化与去习惯化")
print("-" * 88)
h = habituation(15, 105.0)
print(f"  {'次数':<8}{'幅度':>10}")
for i in [0, 1, 4, 9, 14]:
    print(f"  {i+1:<8}{h[i]:>10.4f}")
ok["⑧ ★ 重复后下降（习惯化）"] = bool(h[-1] < h[0] * 0.6)
print(f"  ★ 第1次 {h[0]:.4f} → 第15次 {h[-1]:.4f}  降到 {h[-1]/h[0]*100:.0f}%")
dh = dishabituation(h[-1], 120.0, 105.0)
print(f"  ★ 去习惯化：换到120dB → {dh:.4f}  （>习惯化后 {h[-1]:.4f}）")
ok["⑨ ★ 去习惯化：更强刺激让惊吓恢复"] = bool(dh > h[-1])

# ---------------------------------------------------------------- D
print("\n【D】★★★ 核心：三方案对照（爆炸 vs 惊吓）")
print("-" * 88)
print("  ★★ 这就是用户那句话的实证：\"爆炸是惊吓\"")
rng = np.random.default_rng(0)
n = int(0.5 * FS)
t = np.arange(n) / FS
# 一个突然的大信号（≈惊吓刺激）
x = 0.02 * np.sin(2 * np.pi * 200 * t)
x[n // 2:] += 0.9 * np.sin(2 * np.pi * 300 * t[n // 2:])   # 突发的强成分
src_peak = float(np.abs(x).max())

y1 = unprotected(x)
y2, bad2 = post_clip(x)
y3, bad3 = pre_gain_control(x)

r1, r2, r3 = info_retained(y1), info_retained(y2), info_retained(y3)
print(f"\n  {'方案':<22}{'溢出':<8}{'峰值':>14}{'信息保留':>12}")
print(f"  {'① 无保护':<22}{'是':<8}{np.abs(y1[np.isfinite(y1)]).max():>14.2e}{r1:>12.3f}")
print(f"  {'② 后置置零(★46)':<22}{'否':<8}{np.abs(y2).max():>14.2e}{r2:>12.3f}")
print(f"  {'③ 前置增益控制(生物)':<22}{'否' if not bad3 else '是':<8}{np.abs(y3).max():>14.2e}{r3:>12.3f}")

ok["⑩ ★★ 无保护确实溢出"] = bool(np.isinf(np.abs(y1)).any())
ok["⑪ ★★ 后置置零：停了溢出但信息全丢"] = bool(r2 < 0.05)
ok["⑫ ★★★ 前置增益控制：不溢出且信息保留(>0.5)"] = bool((not bad3) and r3 > 0.5)
print(f"\n  ★★★ 信息保留：后置置零 {r2:.3f}  vs  前置增益控制 {r3:.3f}")
print(f"  ★ 这就是差异：{r3/max(r2,1e-9):.1f}×")
ok["⑬ ★★★ 前置方案信息保留显著优于后置"] = bool(r3 > r2 * 5)

# ---------------------------------------------------------------- E
print("\n【E】★★ 潜伏期过冲 —— 为什么大声第一下特别震")
print("-" * 88)
print("  ★ 镫骨肌反射有 60ms 潜伏期 → 第一下没衰减就进来了")
for lat in [0.0, 20.0, 60.0, 120.0]:
    yl, bl = pre_gain_control(x, latency_ms=lat)
    over = float(np.abs(yl).max())
    print(f"  潜伏期 {lat:>6.0f} ms  →  峰值 {over:.3e}   溢出 {bl}")
y0, _ = pre_gain_control(x, latency_ms=0.0)
y60, _ = pre_gain_control(x, latency_ms=60.0)
ok["⑭ ★ 潜伏期越长，第一下过冲越大"] = bool(np.abs(y60).max() > np.abs(y0).max())
print(f"\n  ★ 0ms 潜伏峰值 {np.abs(y0).max():.3e}  vs  60ms 潜伏峰值 {np.abs(y60).max():.3e}")

# ---------------------------------------------------------------- F
print("\n【F】★★★ 惊吓 == 动态范围超限？同构检验")
print("-" * 88)
print("  ★ 用户洞察的形式化：")
print("    数字爆炸 = 输入超出【数值稳定范围】")
print("    生物惊吓 = 输入超出【感觉动态范围】")
print("    两者根因同构 = 超出系统能处理的范围")
print()
print(f"  {'dB':<8}{'惊吓幅度':>12}{'是否超限(>85dB)':>18}")
for db in [60, 75, 85, 95, 110]:
    a = startle_amplitude(db)
    print(f"  {db:<8}{a:>12.4f}{('是' if db > STARTLE_THRESH_DB else '否'):>18}")
ok["⑮ ★ 惊吓只在超限时发生（同构成立）"] = bool(
    startle_amplitude(75) == 0 and startle_amplitude(95) > 0)

print("\n  ★ 反证：如果惊吓不是超限，而是任意强度都有反应")
print(f"    60dB 幅度 {startle_amplitude(60):.4f}  →  低于阈值完全无反应 ✅")
ok["⑯ ★ 反证：阈值以下确实零反应"] = bool(startle_amplitude(60) == 0)

# ---------------------------------------------------------------- G
print("\n【G】⚠️ 诚实：什么不能说")
print("-" * 88)
print("  ❌ 不能说\"数字爆炸和惊吓是同一个物理过程\"")
print("     数字爆炸 = 滤波器系数病态（ba 高阶 + 极窄相对带宽）")
print("     生物惊吓 = 脑干反射通路")
print("     ★ 同构（都是超出范围），不是同一机制")
print("  ❌ 前置增益控制【不能】修 ba 滤波器的数值病态")
print("     ★46 那个 bug 必须换 sos 才能修 —— 这是结构问题，不是幅度问题")
print("  ✅ 能说：面对\"超范围\"，生物用【前置压缩】，我用【后置丢弃】")
print("     ★ 生物的方案更好，因为保留了信息")

print("\n" + "=" * 88)
print(" 判据")
print("=" * 88)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "ppi": {str(k): v for k, v in ppi.items()},
           "info": {"unprotected": r1, "post_clip": r2, "pre_gain": r3}},
          open(os.path.join(HERE, ".sense", "startle.json"), "w"),
          ensure_ascii=False, indent=1)
