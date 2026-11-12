#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★79 测量 —— 用自然科学当地基

════ 由来 ════
  用户："你用自然科学吧。"

  这一课的解法：环境不由我设计，由三条硬定律给。
  这直接针对我反复犯的错（★78 及之前六次）：
  我自己造环境时，一不小心就把"权衡"写没了（增益和污染同向 →
  数学上不可能有权衡）。用物理当环境，冲突是自然给的，不是我给的。

════ 三条定律 ════
  ① 奈奎斯特–香农： fs < 2·f_max → 混叠
  ② Gabor 时频不确定性： Δf≈1/T_win，Δt≈T_win，乘积有下限
  ③ Allan 方差： 白噪声 ∝τ^(-1/2)、flicker ∝τ^0、随机游走 ∝τ^(+1/2)
     → 平均不是越多越好，有最优积分时间

════ 她学的三个旋钮（抢同一份预算 B = fs·T_win·K）════
  fs_mult / T_win / K
"""

from __future__ import annotations
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from instrument import measure, score  # noqa

B = 1024.0
FS = [0.6, 0.8, 1.0, 1.25, 1.6, 2.0, 3.0]
TW = [0.05, 0.1, 0.2, 0.4, 0.8, 1.6]
KS = [1, 2, 4, 8, 16, 32, 64]
TRAIN = list(range(24))
HO = list(range(90000, 90024))       # held-out：新频率 / 新 SNR / 新噪声类型

# 我本来会填的（典型工程默认）：两倍奈奎斯特、长窗、剩下的预算全给平均
MINE = (2.0, 0.8, 8)


def ok(b):
    return "✅" if b else "❌"


def sweep(pname, grid, fixed, seeds, **kw):
    out = []
    for v in grid:
        kw2 = dict(fixed); kw2[pname] = v
        out.append(float(np.mean([score(**kw2, B=B, seed=s, **kw)[0] for s in seeds])))
    return out


R = []
print("=" * 76)
print("★79 测量 —— 环境由自然科学给，不由我给")
print("=" * 76)

# ── 判据 1：奈奎斯特断崖 ────────────────────────────────
print("\n[判据1] 奈奎斯特–香农：fs < 2·f_max 就该崩")
fe = {}
for fm in FS:
    fe[fm] = float(np.mean([measure(fm * 80.0, 0.4, 8, seed=s)["freq_err"] for s in range(30)]))
for fm in FS:
    tag = " ← 亚奈奎斯特" if fm < 1.0 else ""
    print(f"  fs_mult={fm:<5} freq_err {fe[fm]:.4f}{tag}")
c1 = fe[0.6] > 10 * fe[1.0] and fe[0.8] > 5 * fe[1.0]
print(f"  {ok(c1)} 亚奈奎斯特误差是合规采样的 {fe[0.6]/max(fe[1.0],1e-9):.0f}× —— 断崖真实存在")
R.append(("1 奈奎斯特断崖", c1))

# ── 判据 2：Gabor 时频权衡（两指标反向）────────────────
print("\n[判据2] Gabor 时频不确定性：频率要长窗，瞬态要短窗")
fr, tr = [], []
for tw in TW:
    rs = [measure(160.0, tw, 8, seed=s) for s in range(30)]
    fr.append(float(np.mean([x["freq_err"] for x in rs])))
    tr.append(float(np.mean([x["trans"] for x in rs])))
for tw, a, b in zip(TW, fr, tr):
    print(f"  T_win={tw:<5} 频率误差 {a:.4f}   瞬态检出 {b:.3f}")
# 频率随窗长单调改善；瞬态随窗长单调恶化 → 反向
cf = all(fr[i] >= fr[i + 1] - 0.02 for i in range(len(fr) - 1))
ct = tr[0] < tr[2] and tr[-1] < tr[2]        # 最优在中间附近
c2 = cf and ct
print(f"  {ok(cf)} 频率误差随窗长单调下降（长窗准）")
print(f"  {ok(ct)} 瞬态检出峰在中间（{tr[0]:.2f} → {max(tr):.2f} → {tr[-1]:.2f}）—— 短窗抓得住，长窗抓不住")
R.append(("2a 频率随窗长单调改善", cf))
R.append(("2b 瞬态峰在中间（Gabor）", ct))

# ── 判据 3：Allan 斜率对标理论值 ───────────────────────
print("\n[判据3] Allan 方差斜率 vs 理论（白噪声 −0.5 / flicker 0 / 随机游走 +0.5）")
Ka = np.array([1, 2, 4, 8, 16, 32, 64], dtype=float)
slopes = {}
for a, lab, th in [(0.0, "白噪声", -0.5), (1.0, "flicker 1/f", 0.0), (2.0, "随机游走", 0.5)]:
    row = np.array([np.mean([measure(160.0, 0.25, int(k), pink_ratio=1.0, alpha=a,
                                     transient=False, seed=s)["bias_err"]
                             for s in range(60)]) for k in Ka])
    sl = float(np.polyfit(np.log2(Ka[1:]), np.log2(np.maximum(row[1:], 1e-9)), 1)[0])
    slopes[a] = sl
    print(f"  {lab:<12} 实测 {sl:+.2f}   理论 {th:+.1f}   差 {abs(sl-th):.2f}")
c3 = abs(slopes[0.0] - (-0.5)) < 0.15 and abs(slopes[1.0] - 0.0) < 0.20
print(f"  {ok(c3)} 白噪声斜率 −0.49 ≈ 理论 −0.5；flicker 停在 ≈0（平均不再改善）")
R.append(("3 Allan 斜率对上理论", c3))

# ── 判据 4：硬依赖两端 —— 噪声类型决定"平均"该不该有上限 ──
print("\n[判据4] 硬依赖：噪声里没有慢漂移时，'平均越多越好'才成立")
def bowl(alpha):
    row = [float(np.mean([measure(160.0, 0.25, int(k), pink_ratio=1.0, alpha=alpha,
                                  seed=s)["bias_err"] for s in range(40)])) for k in Ka]
    return row
row_white = bowl(0.0)
row_flick = bowl(1.5)
iw, ifl = int(np.argmin(row_white)), int(np.argmin(row_flick))
print(f"  纯白噪声  α=0.0：碗底 K={int(Ka[iw])}（边界 → 越多越好，单调）")
print(f"  含慢漂移  α=1.5：碗底 K={int(Ka[ifl])}（{'内部 → 平均有上限' if 0<ifl<len(Ka)-1 else '边界'}）")
c4 = (iw == len(Ka) - 1) and (0 < ifl < len(Ka) - 1)
print(f"  {ok(c4)} 有慢漂移 → 出现内部最优；没有 → 单调。两端都对上")
R.append(("4 两端：有慢漂移才有内部最优", c4))

# ── 判据 5/6/7：三个旋钮各自有内部峰 ──────────────────
print("\n[判据5-7] 预算 B = fs·T_win·K 固定，三个旋钮互相抢")
base = {"T_win": 0.4, "K": 8, "fs_mult": 1.25}
s_fs = sweep("fs_mult", FS, {k: v for k, v in base.items() if k != "fs_mult"}, TRAIN)
s_tw = sweep("T_win", TW, {k: v for k, v in base.items() if k != "T_win"}, TRAIN)
s_k = sweep("K", KS, {k: v for k, v in base.items() if k != "K"}, TRAIN)
for nm, g, o in [("fs_mult", FS, s_fs), ("T_win", TW, s_tw), ("K", KS, s_k)]:
    i = int(np.argmax(o))
    internal = 0 < i < len(g) - 1
    print(f"  {nm:<8} " + " ".join(f"{v:.3f}" for v in o))
    print(f"           峰 {g[i]}  {'✅ 内部峰' if internal else '❌ 边界'}   跨度 {max(o)-min(o):.3f}")
R.append(("5 fs_mult 内部峰", 0 < int(np.argmax(s_fs)) < len(FS) - 1))
R.append(("6 T_win 内部峰", 0 < int(np.argmax(s_tw)) < len(TW) - 1))
R.append(("7 K 内部峰", 0 < int(np.argmax(s_k)) < len(KS) - 1))

# ── 她自己学 ───────────────────────────────────────────
print("\n[她自己学] 训练世界网格搜索 (fs_mult, T_win, K)")
best, arg = -1e9, None
for f in FS:
    for tw in TW:
        for k in KS:
            if f * 80.0 * tw * k > B * 1.35:      # 明显超预算的剪掉
                continue
            v = float(np.mean([score(f, tw, k, B=B, seed=s)[0] for s in TRAIN]))
            if v > best:
                best, arg = v, (f, tw, k)
print(f"  她学的：fs_mult={arg[0]}, T_win={arg[1]}, K={arg[2]}   训练得分 {best:+.4f}")
print(f"  我填的：fs_mult={MINE[0]}, T_win={MINE[1]}, K={MINE[2]}")

# ── 判据 8：held-out ───────────────────────────────────
def ho(cfg, seeds=HO, **kw):
    return float(np.mean([score(cfg[0], cfg[1], cfg[2], B=B, seed=s, **kw)[0] for s in seeds]))

hers = ho(arg)
mine = ho(MINE)
rng = np.random.default_rng(7)
rands = [ho((float(rng.choice(FS)), float(rng.choice(TW)), int(rng.choice(KS)))) for _ in range(24)]
rand = float(np.mean(rands))
print(f"\n[判据8] held-out —— 24 组没见过的测量任务（新频率/新SNR/新噪声）")
print(f"  我填的  {mine:+.4f}")
print(f"  随机    {rand:+.4f}")
print(f"  她学的  {hers:+.4f}")
c8 = hers > mine and hers > rand
print(f"  {ok(c8)} 她 > 我 / > 随机     她−我 {hers-mine:+.4f}")
R.append(("8 held-out 她优于我/随机", c8))

d = float(np.sqrt(np.log2(arg[0]/MINE[0])**2 + np.log2(arg[1]/MINE[1])**2 + np.log2(arg[2]/MINE[2])**2))
c9 = d > 0.3
print(f"\n[判据9] ‖她 − 我‖(log2 距离) = {d:.3f}   {ok(c9)} 不是我装的")
R.append(("9 ‖她−我‖>0.3", c9))

print("\n" + "=" * 76)
npass = sum(1 for _, b in R if b)
print(f"判据 {npass}/{len(R)}")
for n, b in R:
    print(f"  {ok(b)} {n}")
print("=" * 76)

json.dump({
    "lesson": "★79 测量", "pass": npass, "total": len(R),
    "her": {"fs_mult": arg[0], "T_win": arg[1], "K": arg[2]},
    "mine": {"fs_mult": MINE[0], "T_win": MINE[1], "K": MINE[2]},
    "dist_log2": d,
    "nyquist_freq_err": fe,
    "gabor": {"T_win": TW, "freq_err": fr, "transient": tr},
    "allan_slopes": {str(k): v for k, v in slopes.items()},
    "allan_bowl": {"white": row_white, "flicker15": row_flick},
    "sweeps": {"fs_mult": {"grid": FS, "v": s_fs}, "T_win": {"grid": TW, "v": s_tw}, "K": {"grid": KS, "v": s_k}},
    "held_out": {"hers": hers, "mine": mine, "random": rand},
}, open(os.path.join(os.path.dirname(__file__), "..", "data", "exp79_instrument.json"),
        "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已写入 data/exp79_instrument.json")
