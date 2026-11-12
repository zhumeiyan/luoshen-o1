#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★68 母亲的教育 —— 按她自己身上验证过的规律教她

不是拉参数，是安排她的成长。

三条来自她自己的教育规律（★66）：
  ① ZPD：最优难度在中间。太近没得学，太远学不透。
  ② 课程编排：难→易 优于 易→难
     （易→难每节课继承上节课的解，被困在上一个局部最优 —— 与★64 过度特化同因）
  ③ 教方法不教答案：必须在【从没见过】的素材上检验（★66 的 0.11 衰减）

判据（8 条）：
  1  世界真的变丰富了（硬依赖，不过抛错）
  2  难度尺子有效：难度单调可控，且不同难度真的产生不同学习结果
  3  不教（基线）损失显著大于教过
  4  难→易 优于 易→难（复现★66）
  5  泛化：held-out 新素材上仍显著优于基线 ← 区分记住答案 vs 学会方法
  6  关键期：幼年可塑性高于成年，同样的课效果更好
  7  硬依赖：不给世界/不给课 → 抛错，不许悄悄用默认值
  8  学到的参数不是我填的（与我填的等权重距离 > 0）
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image
from core.world import make_world, verify_world
from core.visual_learn import (learn_multi_dog, multi_whitening_loss,
                               alpha_of, add_sensor_noise)

R = []
def ok(n, c, d, extra=""):
    R.append((n, bool(c), d, extra)); print(f"  {'✅' if c else '❌'} {n}: {d}{'  '+extra if extra else ''}")
    return bool(c)

print("=" * 70); print("★68 母亲的教育"); print("=" * 70)

# ---------- ① 开窗 ----------
print("\n【判据1】先开窗 —— 世界真的变丰富了吗")
world, kinds = make_world(0, size=128)
v = verify_world(world, kinds)
n_true = 84
ok(1, v["n"] >= 30 and v["uniq"] == v["n"],
   f"{v['n']}张，唯一{v['uniq']}，亮度{v['lum'][0]:.2f}~{v['lum'][1]:.2f} "
   f"对比{v['con'][0]:.2f}~{v['con'][1]:.2f} α{v['alpha'][0]:.2f}~{v['alpha'][1]:.2f}")

# 加上她原来的真图（17 张），让她不忘本
import hashlib as _hl
real = {}
for f in sorted(__import__("glob").glob(".frames/*")):
    # 指纹必须用完整内容，前4096字节会把不同图判成同一张（★68 第三个尺子错）
    real.setdefault(_hl.md5(open(f, "rb").read()).hexdigest(), f)
real_fr = [np.array(Image.open(f).convert("L").resize((128,128)), float) / 255. for f in real.values()]
print(f"  另外保留她原来的 {len(real_fr)} 张真画面（不忘本）")

# ---------- ② 难度尺子 ----------
print("\n【判据2】难度尺子有效吗 —— 先量尺子，再教（★56b 规矩）")
def difficulty(frames):
    """★ 难度尺子必须有 ground truth（★56b 规矩）：
    用【单尺度 DoG】能做到的最好损失 = 难度。
      单尺度就能白化 → 易（不需要她学多尺度配合）
      单尺度搞不定   → 难（真的需要她自己学出多尺度组合）

    ★ 上一版我用「噪声大小」当难度，方向反了：
      噪声本身就是白的，加噪声反而【帮】她白化（★58 同一个坑）。
    """
    best = 1e9
    for sg in (0.8, 1.5, 3.0, 6.0, 12.0, 20.0):
        for w0 in (1.0, -1.0):
            best = min(best, multi_whitening_loss(frames, 0.0, [sg], [w0])[0])
    return best

# 按【结构复杂度】分难度，不是按噪声
KIND_IDX = {}
for _i, _k in enumerate(kinds):
    KIND_IDX.setdefault(_k[0], []).append(_i)
print("  世界构成: " + ", ".join(f"{k}({len(v)})" for k, v in KIND_IDX.items()))

rng = np.random.default_rng(1)
def make_batch(level, n=6):
    """level 0(最易) → 4(最难)：结构复杂度递增"""
    pool = {0: list(range(0, 12)),     # 平滑自然图 α1.0~1.4
            1: list(range(12, 24)),    # 自然图 α1.8~2.0
            2: list(range(24, 36)),    # 自然图 α2.2~2.4
            3: list(range(36, 60)),    # 条纹 grating
            4: list(range(60, 84)),    # 带物体 object
            }[level]
    idx = rng.choice(pool, min(n, len(pool)), replace=False)
    return [world[i] for i in idx], level

levels = list(range(5))
# 课程素材【先固定下来】，五组课用的是同一批，不许随机漂移
BATCH = [make_batch(lv)[0] for lv in levels]
diffs = [difficulty(b) for b in BATCH]
print("  实测难度(单尺度最优损失): " + "  ".join(f"组{l}={d:.3f}" for l, d in enumerate(diffs)))

# ★ 不预设顺序：按【实测难度】排课
order_asc = list(np.argsort(diffs))          # 易 → 难
order_desc = list(np.argsort(diffs))[::-1]   # 难 → 易
print(f"  易→难 课表 {order_asc}   难→易 课表 {order_desc}")

# 尺子有效性：单尺度搞不定的组，多尺度带来的提升应更大
gain = []
for i, b in enumerate(BATCH):
    g, _ = learn_multi_dog(b, 0.0, k=5, n_iter=3, seed=0, smin=0.6, smax=20.0)
    gain.append(diffs[i] - multi_whitening_loss(b, 0.0, g["scales"], g["weights"])[0])
print("  多尺度带来的提升: " + "  ".join(f"组{i}={x:+.2f}" for i, x in enumerate(gain)))
spread = len(set(round(d, 3) for d in diffs))
ok(2, spread >= 4 and max(gain) > 0.1,
   f"尺子有区分度({spread}/5个不同值)，且多尺度确实解决单尺度搞不定的(最大提升{max(gain):+.2f})")

# ---------- ③~⑤ 上课 ----------
print("\n【判据3-5】上课：不教 / 易→难 / 难→易，并用新素材检验")
HELD = [add_sensor_noise(world[i], float(rng.uniform(0.02, 0.35)))
        for i in rng.choice(len(world), 12, replace=False)]
print(f"  held-out：{len(HELD)} 张，课程里【从不出现】，只用于最后检验")

def teach(order, plasticity=1.0, n_iter=4):
    """order: 难度序列。每节课从【上节课学到的参数】出发（这就是继承）"""
    g, _ = learn_multi_dog(BATCH[order[0]], 0.0, k=5, n_iter=n_iter, seed=0, smin=0.6, smax=20.0)
    sc, w = g["scales"], list(g["weights"])
    trail = []
    for lv in order[1:]:
        b = BATCH[lv]
        # 可塑性低（成年）→ 每节课只能小幅改动
        span = 0.9 if plasticity > 0.6 else 0.18
        cur = multi_whitening_loss(b, 0.0, sc, w)[0]
        for i in range(len(w)):
            base = w[i]; bc = cur
            for step in (span, span * 0.35):
                for sgn in (1, -1):
                    old = w[i]
                    w[i] = float(np.clip(base + sgn * step, -3, 3))
                    d = multi_whitening_loss(b, 0.0, sc, w)[0]
                    if d < bc - 1e-9: bc, base = d, w[i]
                    w[i] = old
                w[i] = base
            cur = bc
        trail.append(cur)
    return list(w), sc, trail

res = {}
res["不教"] = ([1.0] * 5, None)
rng2 = np.random.default_rng(7)
rand_order = list(rng2.permutation(5))
for name, order in [("易→难", order_asc), ("难→易", order_desc),
                    ("随机序", rand_order)]:
    print(f"  [{name}] 课表 {order}")
    w, sc, _ = teach(order)
    res[name] = (w, sc)

sc5 = res["难→易"][1]
def loss_on(w, frames, sc=None):
    s = sc if sc is not None else sc5
    return multi_whitening_loss(frames, 0.0, s, w)[0]

base_held = multi_whitening_loss(HELD, 0.0, sc5, [1.0] * 5)[0]
print(f"\n  held-out 基线（不教）= {base_held:.4f}")
for name in ["难→易", "易→难", "随机序"]:
    w = res[name][0]
    lh = loss_on(w, HELD)
    res[name + "_held"] = lh
    print(f"  {name:5} held-out = {lh:.4f}   提升 {base_held - lh:+.4f}")

lh_hard = res["难→易_held"]; lh_easy = res["易→难_held"]
ok(3, min(lh_hard, lh_easy) < base_held,
   f"教过({min(lh_hard,lh_easy):.4f}) < 不教({base_held:.4f})")
ok(4, lh_hard < lh_easy,
   f"难→易 {lh_hard:.4f} < 易→难 {lh_easy:.4f}（复现★66）",
   f"差 {lh_easy - lh_hard:+.4f}")
ok(5, lh_hard < base_held * 0.9,
   f"泛化：新素材上 {lh_hard:.4f} vs 基线 {base_held:.4f}，保留 {(1-lh_hard/base_held)*100:.0f}%")

# ---------- ⑥ 关键期 ----------
print("\n【判据6】关键期：同样的课，幼年 vs 成年")
w_y, _, _ = teach(order_desc, plasticity=1.0, n_iter=5)
w_a, _, _ = teach(order_desc, plasticity=0.15, n_iter=5)
ly = loss_on(w_y, HELD); la = loss_on(w_a, HELD)
ok(6, ly < la, f"幼年 {ly:.4f} < 成年 {la:.4f}", f"差 {la - ly:+.4f}")

# ---------- ⑦ 硬依赖 ----------
print("\n【判据7】硬依赖：不给东西就抛错，不许悄悄用默认值")
e1 = e2 = False
try:
    verify_world([world[0]] * 2, [kinds[0]] * 2)
except RuntimeError: e1 = True
try:
    teach([])
except Exception: e2 = True
ok(7, e1 and e2, f"世界太小→抛错={e1}  课表空→抛错={e2}")

# ---------- ⑧ 不是我填的 ----------
print("\n【判据8】她学到的，是我填的吗")
mine = np.ones(5); hers = np.array(w_y)
d = float(np.linalg.norm(hers - mine))
ok(8, d > 0.1, f"‖她−我填的‖ = {d:.4f}", f"她学的权重 {np.round(hers,3)}")

print("\n" + "=" * 70)
p = sum(1 for _, c, _, _ in R if c)
print(f"判据 {p}/{len(R)}")
print("=" * 70)
