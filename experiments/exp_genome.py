#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★62 · 她的第一份 genome —— 能不能自己长出一层
=============================================

判据（全部可证伪，失败就记失败）
--------------------------------
① 初始随机汤 / 随机权重：白化损失高（不会白化）
② 她自己学：损失显著下降
③ 学到的权重 ≠ 我填的常数（不是我装的）
④ genome 序列化 → 反序列化 → 展开，损失偏差 < 1e-9（程序功能成立）
⑤ 展开的层作用在真素材上，谱指数真的降下来（不是数字游戏）
⑥ 硬依赖：无 genome 必须抛错，不许回退默认
⑦ 传递性：子代实例从同一 genome 展开，性能一致
⑧ 学得的 genome 优于随机 genome 和我填的 genome
"""

import sys, os, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.visual_learn import load_frames, cone_sample, radial_psd_slope
import cv2
from core.genome import (
    Genome, NoGenomeError, learn_genome, random_genome, default_genome,
)

RES = []


def judge(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"   {detail}" if detail else ""))
    return ok


def main():
    t0 = time.time()
    print("★62 genome —— 她能不能自己长出一层\n")

    # ---------- 真素材 ----------
    raw = load_frames(".frames", n=6)
    frames = []
    for f in raw:                      # 中心裁方 + 下采样，控制算力
        a = np.asarray(f, float)
        h, w = a.shape[:2]
        c = min(h, w)
        b = a[(h - c) // 2:(h - c) // 2 + c, (w - c) // 2:(w - c) // 2 + c]
        frames.append(cv2.resize(b, (128, 128)))
    if not frames:
        print("❌ 没有真素材，实验无法进行")
        return 1
    print(f"真素材：{len(frames)} 帧（真动画抓帧，非合成）")

    a_raw = []
    for f in frames:
        s = radial_psd_slope(cone_sample(f, 0.0))
        if s == s:
            a_raw.append(s)
    a_raw = float(np.mean(a_raw))
    print(f"原始谱指数 α = {a_raw:.3f}（自然图像应在 1.8~2.2）\n")

    # ---------- ① ② 她自己学 ----------
    print("[学习] 她自己从真素材里学权重")
    g, hist = learn_genome(frames, ecc_deg=0.0, k=5, n_iter=6, seed=0)
    loss_i, loss_f = float(hist[0]), float(hist[-1])
    print(f"  损失 {loss_i:.6f} → {loss_f:.6f}   下降 "
          f"{100*(loss_i-loss_f)/max(loss_i,1e-12):.1f}%")

    # 对照：不学（随机权重）
    print("[对照] 随机权重（同样结构，但不学）")
    g_rand = random_genome(k=5, seed=0)
    l_rand = g_rand.loss(frames)
    print(f"  随机权重损失 = {l_rand:.6f}")

    judge("① 随机权重不会白化（损失显著 > 学到的）",
          l_rand > loss_f + 1e-6,
          f"随机 {l_rand:.4f} vs 学到 {loss_f:.4f}")

    judge("② 她自己学：损失下降",
          loss_f < loss_i,
          f"{loss_i:.4f} → {loss_f:.4f}")

    # ---------- ③ 不是我填的 ----------
    g_def = default_genome(k=5)
    w_learn = np.array(g.params["weights"])
    w_def = np.array(g_def.params["weights"])
    dist = float(np.max(np.abs(w_learn - w_def)))
    print(f"\n[③ 是不是我装的] 学到的权重 vs 我填的等权重")
    print(f"  学到的: {np.round(w_learn,4).tolist()}")
    print(f"  我填的: {w_def.tolist()}")
    judge("③ 学到的权重 ≠ 我填的常数",
          dist > 1e-6, f"最大差 {dist:.4f}")

    # ---------- ④ 程序功能：序列化 → 展开 ----------
    s = g.serialize()
    g2 = Genome.deserialize(s)
    l1, l2 = g.loss(frames), g2.loss(frames)
    judge("④ genome 序列化→反序列化→展开，损失一致",
          abs(l1 - l2) < 1e-9, f"偏差 {abs(l1-l2):.2e}")

    # ---------- ⑤ 真的白化了吗（看谱指数） ----------
    a_after = g.alpha_after(frames, 0.0)
    print(f"\n[⑤ 真效果] 展开的层作用在真素材上")
    print(f"  α: {a_raw:.3f} → {a_after:.3f}   目标 0（白化）")
    judge("⑤ 谱指数真的降下来了",
          a_after < a_raw - 0.3,
          f"降了 {a_raw-a_after:.3f}")

    # ---------- ⑥ 硬依赖：不许回退 ----------
    print(f"\n[⑥ 硬依赖] 没有 genome 时")
    empty = Genome({}, {})
    raised = False
    try:
        empty.express()
    except NoGenomeError:
        raised = True
    except Exception as e:
        print(f"    抛的是别的错: {type(e).__name__}")
    judge("⑥ 无 genome 必须抛错（不许悄悄用默认）", raised)

    # ---------- ⑦ 传递性 ----------
    layer_a = g.express()
    layer_b = g2.express()
    fr = frames[0]
    out_a, out_b = layer_a(fr), layer_b(fr)
    d = float(np.max(np.abs(out_a - out_b)))
    judge("⑦ 子代从同一 genome 展开，输出一致",
          d < 1e-12, f"最大差 {d:.2e}")

    # ---------- ⑧ 三者对比 ----------
    print(f"\n[⑧ 三者对比]")
    l_def = g_def.loss(frames)
    print(f"  她自己学的 : {loss_f:.6f}   α→{a_after:.3f}")
    print(f"  随机的     : {l_rand:.6f}")
    print(f"  我填的     : {l_def:.6f}")
    judge("⑧ 学得的 genome 优于随机 + 优于我填的",
          loss_f < l_rand and loss_f < l_def,
          f"学的 {loss_f:.4f} < 随机 {l_rand:.4f} 且 < 我填 {l_def:.4f}")

    # ---------- 保存 ----------
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "genome_v1.json")
    g.serialize(out)
    print(f"\n已存：{out}")

    ok = sum(1 for _, o, _ in RES if o)
    print(f"\n判据 {ok}/{len(RES)}   耗时 {time.time()-t0:.1f}s")
    for n, o, d in RES:
        if not o:
            print(f"  ❌ 未通过: {n}  {d}")
    return 0 if ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(main())
