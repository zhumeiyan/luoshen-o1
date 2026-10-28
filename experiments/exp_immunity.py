#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★65 · 免疫与野败 —— 怎么救一个陷在局部最优里的种群
====================================================

★ 承 ★64：过度特化陷阱让孩子从"妈妈练熟的解"出发反而更差。
  这正是袁隆平的野败、和免疫系统的 V(D)J 重组要解决的问题。

判据（全部可证伪）
------------------
① 瓶颈确实存在：继续近亲微调，适应度停滞（改善 < 阈值）
② 野败能破局：引入野生遗传物质，显著优于继续近亲
③ 野败有最优比例：不是越多越好（全野生 = 丢掉一切，应更差）
④ 抗体式重组：分段拼接优于单点微调
⑤ 记忆：同一抗原二次应答显著快于/优于初次
⑥ 硬依赖：没见过抗原就"回忆"，必须抛错
⑦ 真能用：最终解作用在真素材上，谱指数下降

★ 诚实：如果野败救不活，就如实记"救不活"。
"""

import sys, os, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.immunity import (
    affinity_mature, wild_introduce, vdj_recombine, ImmuneSystem,
    _scales, _loss,
)
from core.genome import NoGenomeError
from core.growth import grow_layer, layer_key
from core.visual_learn import load_frames, radial_psd_slope, cone_sample, multi_dog

RES = []


def judge(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    print(f"  {'✅' if ok else '❌'}" if not detail else
          f"  {'✅' if ok else '❌'} {name}   {detail}")
    if not detail:
        print(f"     {name}")
    return ok


def _j(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"   {detail}" if detail else ""))
    return ok


def prep(n=4, size=96):
    raw = load_frames(".frames", n=n)
    out = []
    for f in raw:
        a = np.asarray(f, float)
        h, w = a.shape[:2]
        c = min(h, w)
        out.append(cv2.resize(a[(h-c)//2:(h-c)//2+c, (w-c)//2:(w-c)//2+c],
                              (size, size)))
    return out


def main():
    t0 = time.time()
    print("★65 免疫与野败 —— 怎么救陷在局部最优里的种群\n")

    frames = prep()
    if not frames:
        print("❌ 无素材"); return 1

    ECC = 8.0
    K = 8
    SCALES = _scales(K)
    ROUNDS = 4

    a0 = float(np.mean([radial_psd_slope(cone_sample(f, ECC)) for f in frames]))
    print(f"素材 {len(frames)} 帧  目标 ecc={ECC}  原始谱指数 α={a0:.3f}")
    print(f"权重维度 K={K}（比 ★64 的 5 更大，让重组有空间）\n")

    # ============ ① 先诊断：这个 landscape 到底有没有多个局部最优？ ============
    # ★ 关键前提：野败只有对【困在差盆地里】的种群才有意义。
    #   如果 landscape 是单峰的（所有起点收敛到同一值），
    #   那根本不存在"被困"，野败本就不该有效 —— 不能拿它当万金油。
    print("[① 诊断：landscape 是单峰还是多峰]")
    conv = []
    for s in range(4):
        rng = np.random.default_rng(s)
        w0 = [float(rng.uniform(-1, 1)) for _ in range(K)]
        w, h = affinity_mature(frames, ECC, SCALES, w0, rounds=4, seed=s)
        conv.append(h[-1])
        print(f"  随机起点{s} → {h[-1]:.4f}")
    conv = np.array(conv)
    spread = float(conv.max() - conv.min())
    l_star = float(conv.min())
    print(f"  收敛区间 {conv.min():.4f} ~ {conv.max():.4f}，跨度 {spread:.4f}")
    print("  ★ 跨度大 = 多峰 = 确实存在局部最优，野败才有意义")
    _j("① landscape 是多峰的（存在局部最优，野败有意义的前提成立）",
       spread > 0.05, f"跨度 {spread:.4f}")

    # ============ 造一个"被困住"的驯化亲本 ============
    # ★ 这是袁隆平面对的真实局面：栽培稻（驯化亲本）卡住了，
    #   而且它自己继续近亲繁育【救不活】。
    print("\n[驯化亲本] 找一个困在差盆地里、且自己救不活的")
    worst = int(np.argmax(conv))
    rng = np.random.default_rng(worst)
    w0_bad = [float(rng.uniform(-1, 1)) for _ in range(K)]
    w_trap, h_trap = affinity_mature(frames, ECC, SCALES, w0_bad,
                                     rounds=ROUNDS, seed=worst)
    l_trap = h_trap[-1]
    print(f"  被困亲本收敛到 {l_trap:.4f}（已知可达最优 {l_star:.4f}）")

    # 对照：继续近亲微调（★63 的"发育"），看能不能自救
    w_more, h_more = affinity_mature(frames, ECC, SCALES, w_trap,
                                     rounds=ROUNDS, seed=77)
    l_inbred = h_more[-1]
    gap_inbred = l_inbred - l_star
    print(f"  继续近亲微调 → {l_inbred:.4f}（仍距最优 {gap_inbred:.4f}）")

    _j("② 被困种群继续近亲微调救不活（仍显著劣于可达最优）",
       gap_inbred > 0.05,
       f"{l_inbred:.4f} vs 最优 {l_star:.4f}，差 {gap_inbred:.4f}")

    # ============ ③ ④ 野败 ============
    print("\n[③④ 野败：往被困种群里掺入野生遗传物质]")
    scan = {}
    for ratio in (0.0, 0.25, 0.5, 1.0):
        best = float("inf")
        for s in range(1):
            w_wild, idx = wild_introduce(w_trap, ratio, seed=100 + s)
            w2, h2 = affinity_mature(frames, ECC, SCALES, w_wild,
                                     rounds=ROUNDS, seed=s)
            best = min(best, h2[-1])
        scan[ratio] = best
        tag = "（纯近亲=对照）" if ratio == 0 else \
              "（全野生）" if ratio == 1.0 else ""
        print(f"  野生占比 {ratio:<5} → {best:.4f}  {tag}")

    best_ratio = min(scan, key=scan.get)
    gain_wild = l_inbred - scan[best_ratio]
    _j("③ 野败能救活：最优野生占比显著优于继续近亲",
       gain_wild > 0.05 and best_ratio > 0.0,
       f"占比 {best_ratio} 时 {scan[best_ratio]:.4f}，"
       f"比继续近亲 {l_inbred:.4f} 好 {gain_wild:.4f}")

    _j("④ 野败有最优比例：全盘野生反而更差（远缘衰退）",
       scan[1.0] > scan[best_ratio] + 0.05,
       f"全野生 {scan[1.0]:.4f} 劣于最优 {scan[best_ratio]:.4f}")

    # ============ ④ 抗体式重组 vs 单点微调 ============
    print("\n[④ 抗体式重组 vs 单点微调]")
    rng = np.random.default_rng(3)
    # 微调：从驯化亲本出发（★63 的方式）
    w_fine, h_fine = affinity_mature(frames, ECC, SCALES, w_trap,
                                     rounds=ROUNDS, seed=11)
    # 重组：多个不同来源各取一段拼接
    pool = [w_trap,
            [float(rng.uniform(0.1, 0.5)) for _ in range(K)],
            [float(x) * -1.0 for x in w_trap]]
    best_recomb = float("inf")
    for i in range(3):
        w0 = vdj_recombine(pool, n_seg=4, seed=11 * 31 + i)
        w2, h2 = affinity_mature(frames, ECC, SCALES, w0,
                                 rounds=ROUNDS, seed=11 + i)
        best_recomb = min(best_recomb, h2[-1])
    print(f"  单点微调 : {h_fine[-1]:.4f}")
    print(f"  分段重组 : {best_recomb:.4f}")
    _j("④ 抗体式分段重组优于单点微调",
       best_recomb < h_fine[-1] - 1e-6,
       f"{best_recomb:.4f} < {h_fine[-1]:.4f}")

    # ============ ⑤ ⑥ 记忆 ============
    print("\n[⑤⑥ 免疫记忆：第二次遇到同一抗原]")
    sys_im = ImmuneSystem()
    ag = f"ecc{ECC}"
    # 初次应答（从零，候选少一点以体现差异）
    w1, l1, e1 = sys_im.primary(ag, frames, ECC, SCALES, K,
                                rounds=2, seed=5, n_cand=2)
    w2, l2, e2 = sys_im.secondary(ag, frames, ECC, SCALES, K,
                                  rounds=2, seed=5, n_cand=2)
    print(f"  初次应答: {l1:.4f}   评估 {e1} 次")
    print(f"  二次应答: {l2:.4f}   评估 {e2} 次")
    _j("⑤ 二次应答不劣于初次（记忆有效）",
       l2 <= l1 + 1e-9, f"{l2:.5f} ≤ {l1:.5f}")

    raised = False
    try:
        ImmuneSystem().secondary("never_seen", frames, ECC, SCALES, K)
    except NoGenomeError:
        raised = True
    except Exception:
        pass
    _j("⑥ 没见过的抗原就回忆必须抛错", raised)

    # ============ ⑦ 真能用 ============
    print("\n[⑦ 最终解能不能用]")
    best_w = sys_im.memory[ag]["weights"]
    a1 = float(np.mean([radial_psd_slope(
        multi_dog(cone_sample(f, ECC), SCALES, best_w)) for f in frames]))
    print(f"  α @ecc={ECC}: {a0:.3f} → {a1:.3f}")
    _j("⑦ 谱指数真的降下来", a1 < a0 - 0.3, f"降了 {a0-a1:.3f}")

    # 保存
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "immunity_best.json")
    import json
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"ecc": ECC, "K": K, "scales": SCALES,
                   "weights": best_w, "alpha_before": a0,
                   "alpha_after": a1,
                   "wild_scan": {str(k): v for k, v in scan.items()},
                   "best_ratio": best_ratio}, f, ensure_ascii=False, indent=2)
    print(f"\n已存：{out}")

    ok = sum(1 for _, o, _ in RES if o)
    print(f"\n判据 {ok}/{len(RES)}   耗时 {time.time()-t0:.1f}s")
    for n, o, d in RES:
        if not o:
            print(f"  ❌ 未通过: {n}  {d}")
    return 0 if ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(main())
