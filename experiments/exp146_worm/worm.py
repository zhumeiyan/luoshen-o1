#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp146 v2 蠕虫格：自发起意调度器

修正 v1 两个失效：
  [bug1] 置换特征不破坏结构 -> 阴性对照逐位相同（退化对照，第3次复发）
  [bug2] 首次访问 pred=v 使误差立刻归零 -> "模型误差"实为覆盖率代理，
         两个指标量同一件事，不独立

v2 设计（让"选点"真正有信息价值）：
  可观测线索  path_feat：从路径字符串算，随时可看，不需要动作（廉价）
  昂贵动作    scan：真 listdir，得到 content_feat
  世界模型    W: path_feat(8) -> content_feat(9)，在线 SGD
  泛化误差    mean_i ||W·pf_i - truth_i||  【含未访问节点】
  驱动        好奇 = 去 path_feat 空间中离已探索区最远的未访问节点
              （不确定性估计，不需要偷看 truth）

阴性对照：truth 换成与 path_feat 无关的随机噪声 -> W 学不到任何规律
          -> 所有策略泛化误差都应降不下去 -> 好奇必须退化为随机

验收（能真能假）：
  G1 no_drive 自发率 == 0
  G2 real 地形：curiosity < random < anti（剂量单调，不只报一个方向）
  G3 阴性地形：三者差异塌缩（好奇退化为随机）
"""

import os
import json
import math
import random

BASE = "/data/workspace/luoshen-o1"
PF = 8    # path feature dim
CF = 9    # content feature dim


# ---------- 真实地形 ----------

def discover_nodes(root, max_nodes=60):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        if len(out) >= max_nodes:
            break
        if not dirnames and not filenames:
            continue
        out.append(dirpath)
    return out[:max_nodes]


def path_feat(path):
    """廉价线索：只看路径字符串，不需要动作"""
    name = os.path.basename(path) or "."
    depth = float(path.count(os.sep))
    ln = float(len(path))
    nlen = float(len(name))
    has_digit = 1.0 if any(c.isdigit() for c in name) else 0.0
    has_und = 1.0 if "_" in name else 0.0
    # 关键词（整词匹配，避免子串误伤：判据核 #23）
    toks = set(name.lower().replace("-", "_").split("_"))
    kw = ["exp", "result", "fig", "data", "log", "test"]
    kvec = [1.0 if k in toks else 0.0 for k in kw[:2]]
    return [depth, ln / 100.0, nlen / 20.0, has_digit, has_und,
            kvec[0], kvec[1], 1.0]


def content_feat(path):
    """昂贵动作：真 listdir"""
    try:
        entries = os.listdir(path)
    except (PermissionError, OSError):
        return None
    nfile = ndir = 0
    ext = {}
    for e in entries:
        p = os.path.join(path, e)
        if os.path.isdir(p):
            ndir += 1
        else:
            nfile += 1
            x = os.path.splitext(e)[1].lower()
            ext[x] = ext.get(x, 0) + 1
    for k in [".py", ".md", ".json", ".png", ".txt"]:
        ext.setdefault(k, 0)
    return [float(nfile) / 10.0, float(ndir) / 5.0,
            float(ext.get(".py", 0)) / 5.0,
            float(ext.get(".md", 0)) / 5.0,
            float(ext.get(".json", 0)) / 5.0,
            float(ext.get(".png", 0)) / 5.0,
            float(ext.get(".txt", 0)) / 5.0,
            float(len(ext)) / 8.0,
            1.0]


# ---------- 线性世界模型 ----------

def matvec(W, x):
    return [sum(w[j] * x[j] for j in range(len(x))) for w in W]


class Model:
    def __init__(self, dim_in, dim_out, eta=0.05):
        self.W = [[0.0] * dim_in for _ in range(dim_out)]
        self.eta = eta

    def predict(self, x):
        return matvec(self.W, x)

    def update(self, x, y):
        p = self.predict(x)
        for o in range(len(y)):
            e = y[o] - p[o]
            for j in range(len(x)):
                self.W[o][j] += self.eta * e * x[j]


def d(a, b):
    return math.sqrt(sum((u - v) ** 2 for u, v in zip(a, b)))


# ---------- 调度器 ----------

class Worm:
    def __init__(self, pfs, drive, seed=0, eps=0.05):
        self.pfs = pfs
        self.n = len(pfs)
        self.drive = drive
        self.rng = random.Random(seed)
        self.eps = eps
        self.scanned = set()
        self.last = {i: -1 for i in range(self.n)}
        self.t = 0
        self.g_self = 1.0
        self.recent_gain = 0.0
        self.model = Model(PF, CF)

    def novelty(self, i):
        """到已探索集合的最小距离 —— 不确定性估计，不偷看 truth"""
        if i in self.scanned:
            return 0.0
        if not self.scanned:
            return 1.0
        return min(d(self.pfs[i], self.pfs[j]) for j in self.scanned)

    def boredom(self, i):
        if self.last[i] < 0:
            return 1.0
        return min(1.0, (self.t - self.last[i]) / max(1, self.n))

    def drive_level(self):
        if self.drive == "no_drive":
            return 0.0
        c = sum(self.novelty(i) for i in range(self.n)) / self.n
        b = sum(self.boredom(i) for i in range(self.n)) / self.n
        return c + 0.3 * b + 0.2 * (1.0 - self.g_self)

    def choose(self):
        if self.drive_level() <= 0.0:
            return None
        cand = [i for i in range(self.n) if i not in self.scanned]
        if not cand:
            cand = list(range(self.n))
        if self.rng.random() < self.eps:
            return self.rng.choice(cand)
        if self.drive == "curiosity":
            return max(cand, key=lambda i: self.novelty(i))
        if self.drive == "anti":
            return min(cand, key=lambda i: self.novelty(i))
        if self.drive == "random":
            return self.rng.choice(cand)
        return None

    def act(self, i, y):
        self.model.update(self.pfs[i], y)
        self.scanned.add(i)
        self.last[i] = self.t
        self.t += 1
        return 1.0


def gen_error(model, pfs, truth):
    """泛化误差：含未访问节点"""
    tot = 0.0
    for i in range(len(pfs)):
        tot += d(model.predict(pfs[i]), truth[i])
    return tot / len(pfs)


def run(pfs, truth, drive, n_steps=45, seed=0):
    n = len(pfs)
    w = Worm(pfs, drive, seed=seed)
    base = gen_error(w.model, pfs, truth)      # 未学习时的基线
    spont = 0
    curve = []
    for _ in range(n_steps):
        i = w.choose()
        if i is None:
            w.t += 1
            curve.append(gen_error(w.model, pfs, truth))
            continue
        spont += 1
        w.act(i, truth[i])
        curve.append(gen_error(w.model, pfs, truth))
    return {
        "drive": drive, "spont": spont, "spont_rate": spont / n_steps,
        "base_err": base,
        "final_err": curve[-1],
        "err_auc": sum(curve) / max(1, len(curve)),
        "coverage": len(w.scanned) / n,
        "curve": curve,
    }


def noise_truth(pfs, seed=0):
    """与 path_feat 无关的随机内容 —— 真阴性地形"""
    rng = random.Random(seed)
    scale = [sum(abs(v) for v in p) / len(p) for p in zip(*[f for f in pfs])]
    out = []
    for _ in pfs:
        v = [rng.random() * (s if s > 0 else 1.0) for s in
             ([1.0] * CF)]
        out.append(v)
    return out


def main():
    nodes = discover_nodes(os.path.join(BASE, "experiments"), max_nodes=60)
    pfs, truth, keep = [], [], []
    for p in nodes:
        c = content_feat(p)
        if c is None:
            continue
        pfs.append(path_feat(p))
        truth.append(c)
        keep.append(p)
    n = len(pfs)
    print(f"[terrain] real nodes = {n}")

    arms = ["no_drive", "anti", "random", "curiosity"]
    seeds = list(range(10))
    n_steps = 45
    out = {"n_nodes": n, "n_steps": n_steps, "seeds": len(seeds), "res": {}}

    for terrain in ["real", "noise"]:
        tr = truth if terrain == "real" else noise_truth(pfs, seed=7)
        out["res"][terrain] = {}
        for arm in arms:
            runs = [run(pfs, tr, arm, n_steps=n_steps, seed=s) for s in seeds]
            agg = {
                "spont_rate": sum(r["spont_rate"] for r in runs) / len(runs),
                "final_err": sum(r["final_err"] for r in runs) / len(runs),
                "err_auc": sum(r["err_auc"] for r in runs) / len(runs),
                "base_err": sum(r["base_err"] for r in runs) / len(runs),
                "coverage": sum(r["coverage"] for r in runs) / len(runs),
                "per_seed_final": [round(r["final_err"], 6) for r in runs],
                "per_seed_auc": [round(r["err_auc"], 6) for r in runs],
            }
            out["res"][terrain][arm] = agg
            print(f"[{terrain:6s}] {arm:10s} spont={agg['spont_rate']:.3f} "
                  f"base={agg['base_err']:.4f} auc={agg['err_auc']:.4f} "
                  f"final={agg['final_err']:.4f} cov={agg['coverage']:.3f}")

    with open(os.path.join(os.path.dirname(__file__), "result146.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
