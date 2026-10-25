#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp146 v3 主实验：蠕虫格调度器，双真实地形对照

地形A（真实·无结构）：目录路径 -> 目录内容     pretest ratio 1.0936 NO
地形B（真实·有结构）：文件路径 -> 文件物理属性  pretest ratio 0.6582 YES

世界模型：岭回归闭式解（v2 的 SGD 已证明发散，弃用）
驱动：novelty = 在 path_feat 空间中到已探索集合的最小距离（不偷看 truth）

验收：
  G1 no_drive 自发率 == 0
  G2 地形B 剂量单调：anti > random > curiosity（误差）
  G3 地形A 无差异（好奇退化为随机）—— 真实世界的阴性对照，非合成
"""
import os
import json
import random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def ridge_fit(X, Y, lam=1.0):
    A = X.T @ X + lam * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ Y)


def gen_err(Xs, Ys, scanned):
    """泛化误差：全部节点（含未访问）"""
    if len(scanned) == 0:
        # 未学习：预测 0 向量
        return float(np.mean(np.linalg.norm(Ys, axis=1)))
    idx = sorted(scanned)
    W = ridge_fit(Xs[idx], Ys[idx])
    P = Xs @ W
    return float(np.mean(np.linalg.norm(P - Ys, axis=1)))


def novelty_of(Xs, i, scanned):
    """不确定性估计：到已探索集合的最小距离（不偷看 truth）"""
    if i in scanned:
        return 0.0
    if not scanned:
        return 1.0
    d = np.linalg.norm(Xs[list(scanned)] - Xs[i], axis=1)
    return float(d.min())


def run(Xs, Ys, drive, n_steps=30, seed=0, eps=0.05, w_b=0.3, w_g=0.2):
    rng = random.Random(seed)
    n = len(Xs)
    scanned = set()
    last = {i: -1 for i in range(n)}
    t = 0
    g_self = 1.0
    recent_gain = 0.0
    spont = 0
    curve = []
    base = gen_err(Xs, Ys, scanned)

    for _ in range(n_steps):
        if drive == "no_drive":
            t += 1
            curve.append(gen_err(Xs, Ys, scanned))
            continue

        cand = [i for i in range(n) if i not in scanned]
        if not cand:
            cand = list(range(n))

        nov = {i: novelty_of(Xs, i, scanned) for i in cand}
        bore = {i: (1.0 if last[i] < 0 else
                    min(1.0, (t - last[i]) / max(1, n * 0.5))) for i in cand}
        level = (sum(nov.values()) / len(cand)
                 + w_b * sum(bore.values()) / len(cand)
                 + w_g * (1.0 - g_self))
        if level <= 0.0:
            t += 1
            curve.append(gen_err(Xs, Ys, scanned))
            continue

        if rng.random() < eps:
            pick = rng.choice(cand)
        elif drive == "curiosity":
            pick = max(cand, key=lambda i: nov[i] + w_b * bore[i])
        elif drive == "anti":
            pick = min(cand, key=lambda i: nov[i] + w_b * bore[i])
        else:  # random
            pick = rng.choice(cand)

        before = gen_err(Xs, Ys, scanned)
        scanned.add(pick)
        last[pick] = t
        after = gen_err(Xs, Ys, scanned)
        gain = max(0.0, before - after)
        recent_gain = 0.9 * recent_gain + 0.1 * gain
        g_self = min(1.0, recent_gain / 0.02)
        spont += 1
        t += 1
        curve.append(after)

    return {
        "drive": drive,
        "spont": spont,
        "spont_rate": spont / n_steps,
        "base_err": base,
        "final_err": curve[-1],
        "err_auc": float(np.mean(curve)),
        "coverage": len(scanned) / n,
        "gain": base - curve[-1],
    }


def main():
    out = {"arms": ["no_drive", "anti", "random", "curiosity"],
           "n_steps": 30, "seeds": 10, "res": {}}
    for tag in ["A", "B"]:
        X = np.load(os.path.join(HERE, f"X{'3' if tag=='A' else '4'}.npy"))
        Y = np.load(os.path.join(HERE, f"Y{'3' if tag=='A' else '4'}.npy"))
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
        Ys = (Y - Y.mean(0)) / (Y.std(0) + 1e-9)
        print(f"[terrain {tag}] n={len(Xs)} Xdim={Xs.shape[1]} Ydim={Ys.shape[1]}")
        out["res"][tag] = {"n": int(len(Xs))}
        for arm in out["arms"]:
            runs = [run(Xs, Ys, arm, n_steps=30, seed=s) for s in range(10)]
            agg = {
                "spont_rate": float(np.mean([r["spont_rate"] for r in runs])),
                "final_err": float(np.mean([r["final_err"] for r in runs])),
                "err_auc": float(np.mean([r["err_auc"] for r in runs])),
                "base_err": float(np.mean([r["base_err"] for r in runs])),
                "gain": float(np.mean([r["gain"] for r in runs])),
                "coverage": float(np.mean([r["coverage"] for r in runs])),
                "per_seed_auc": [round(r["err_auc"], 6) for r in runs],
                "per_seed_final": [round(r["final_err"], 6) for r in runs],
            }
            out["res"][tag][arm] = agg
            print(f"  {tag} {arm:10s} spont={agg['spont_rate']:.3f} "
                  f"base={agg['base_err']:.4f} auc={agg['err_auc']:.4f} "
                  f"final={agg['final_err']:.4f} gain={agg['gain']:+.4f}")

    with open(os.path.join(HERE, "result146.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("saved result146.json")


if __name__ == "__main__":
    main()
